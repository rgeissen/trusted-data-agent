# trusted_data_agent/mcp/adapter.py
import json
import logging
import re
from datetime import datetime, timedelta

from langchain_mcp_adapters.tools import load_mcp_tools
from trusted_data_agent.llm import handler as llm_handler
from trusted_data_agent.core.config import APP_CONFIG, AppConfig

app_logger = logging.getLogger("quart.app")

VIZ_TOOL_DEFINITION = {
    "name": "viz_createChart",
    "description": "Generates a data visualization based on provided data. You must specify the chart type and map the data fields to the appropriate visual roles.",
    "args": {
        "chart_type": {
            "type": "string",
            "description": "The type of chart to generate (e.g., 'bar', 'pie', 'line', 'scatter'). This MUST be one of the types listed in the 'Charting Guidelines'.",
            "required": True
        },
        "data": {
            "type": "list[dict]",
            "description": "The data to be visualized, passed directly from the output of another tool.",
            "required": True
        },
        "title": {
            "type": "string",
            "description": "A descriptive title for the chart.",
            "required": True
        },
        "mapping": {
            "type": "dict",
            "description": "A dictionary that maps data keys to chart axes or roles (e.g., {'x_axis': 'product_name', 'y_axis': 'sales_total'}). The required keys for this mapping depend on the selected chart_type.",
            "required": True
        }
    }
}

UTIL_TOOL_DEFINITIONS = [
    {
        "name": "util_getCurrentDate",
        "description": "Returns the current system date in YYYY-MM-DD format. Use this as the first step for any user query involving relative dates like 'today', 'yesterday', or 'this week'.",
        "args": {}
    },
    {
        "name": "util_calculateDateRange",
        "description": "Calculates a list of dates based on a start date and a natural language phrase (e.g., 'past 3 days', 'last week'). This is a necessary second step for multi-day queries.",
        "args": {
            "start_date": {
                "type": "string",
                "description": "The anchor date for the calculation, usually today's date from `util_getCurrentDate`. Must be in YYYY-MM-DD format.",
                "required": True
            },
            "date_phrase": {
                "type": "string",
                "description": "The natural language phrase describing the desired range (e.g., 'past 3 days', 'last 2 weeks').",
                "required": True
            }
        }
    }
]

CORE_LLM_TASK_DEFINITION = {
    "name": "CoreLLMTask",
    "description": "Performs internal, LLM-driven tasks that are not direct calls to the Teradata database. This tool is used for text synthesis, summarization, and formatting based on a specific 'task_description' provided by the LLM itself.",
    "args": {
        "task_description": {
            "type": "string",
            "description": "A natural language description of the internal task to be executed (e.g., 'describe the table in a business context', 'format final output'). The LLM infers this from the workflow plan.",
            "required": True
        },
        "source_data": {
            "type": "list[string]",
            "description": "A list of keys (e.g., 'result_of_phase_1') identifying which data from the workflow history is relevant for this task. This is critical for providing the correct context.",
            "required": True
        },
        "synthesized_answer": {
            "type": "string",
            "description": "The final, synthesized natural language answer, provided directly by the planner when it can confidently answer from history.",
            "required": False
        }
    }
}


def _extract_and_clean_description(description: str | None) -> tuple[str, str]:
    """
    Parses a description string to find a datatype hint (e.g., "(type: str)")
    and cleans the description, returning both the cleaned description and the type.
    """
    if not isinstance(description, str):
        return "", "unknown"

    datatype = "unknown"
    match = re.search(r'\s*\((type:\s*(str|int|float|bool))\)', description, re.IGNORECASE)
    
    if match:
        datatype = match.group(2).lower()
        cleaned_description = description.replace(match.group(0), "").strip()
    else:
        cleaned_description = description
        
    return cleaned_description, datatype

def _extract_prompt_type_from_description(description: str | None) -> tuple[str, str]:
    """
    Parses a prompt's description to find a prompt_type hint, returning the
    cleaned description and the type ('reporting' or 'context'). Defaults to
    'reporting' if no tag is found.
    """
    if not isinstance(description, str):
        return "", "reporting"

    prompt_type = "reporting"
    match = re.search(r'\s*\((prompt_type:\s*(reporting|context))\)', description, re.IGNORECASE)
    
    if match:
        prompt_type = match.group(2).lower()
        cleaned_description = description.replace(match.group(0), "").strip()
    else:
        cleaned_description = description
        
    return cleaned_description, prompt_type

def _get_arg_descriptions_from_string(description: str) -> tuple[str, dict]:
    """
    Parses the "Arguments" or "Args" section of a description string to extract
    a simple map of {arg_name: arg_description}.
    """
    if not description:
        return "", {}

    args_section_match = re.search(r'\n\s*(Arguments|Args):\s*\n', description, re.IGNORECASE)
    if not args_section_match:
        return description, {}

    cleaned_description = description[:args_section_match.start()].strip()
    args_section_text = description[args_section_match.end():]
    
    pattern = re.compile(r'^\s*(?P<name>\w+)\s*[-:]\s*(?P<desc>.+)')
    descriptions = {}
    
    for line in args_section_text.split('\n'):
        match = pattern.match(line.strip())
        if match:
            data = match.groupdict()
            descriptions[data['name']] = data['desc'].strip()
            
    return cleaned_description, descriptions

def _get_type_from_schema(schema: dict) -> str:
    """Extracts a simple type name from a JSON schema property."""
    if not isinstance(schema, dict):
        return "any"
    if "type" in schema:
        return schema["type"]
    if "anyOf" in schema and isinstance(schema["anyOf"], list):
        for type_option in schema["anyOf"]:
            if isinstance(type_option, dict) and type_option.get("type") != "null":
                return type_option.get("type", "any")
    return "any"


async def load_and_categorize_mcp_resources(STATE: dict):
    mcp_client = STATE.get('mcp_client')
    llm_instance = STATE.get('llm')
    if not mcp_client or not llm_instance:
        raise Exception("MCP or LLM client not initialized.")

    server_name = APP_CONFIG.CURRENT_MCP_SERVER_NAME
    if not server_name:
        raise Exception("MCP server name not found in configuration.")

    async with mcp_client.session(server_name) as temp_session:
        app_logger.info("--- Loading and classifying MCP tools and prompts... ---")

        list_tools_result = await temp_session.list_tools()
        raw_tools = list_tools_result.tools if hasattr(list_tools_result, 'tools') else []
        
        processed_tools = []
        class SimpleTool:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        for raw_tool in raw_tools:
            tool_name = raw_tool.name
            tool_desc = raw_tool.description or ""
            processed_args = []
            cleaned_description = tool_desc

            if hasattr(raw_tool, 'inputSchema') and raw_tool.inputSchema and 'properties' in raw_tool.inputSchema:
                cleaned_description, arg_desc_map = _get_arg_descriptions_from_string(tool_desc)
                schema = raw_tool.inputSchema
                required_args = schema.get('required', []) or []
                
                for arg_name, arg_schema in schema['properties'].items():
                    processed_args.append({
                        "name": arg_name,
                        "type": _get_type_from_schema(arg_schema),
                        "required": arg_name in required_args,
                        "description": arg_desc_map.get(arg_name, arg_schema.get('title', 'No description.'))
                    })
            else:
                 cleaned_description, processed_args = _parse_arguments_from_mcp_tool_parameter_description(tool_desc)
            
            processed_tools.append(SimpleTool(
                name=tool_name,
                description=cleaned_description,
                args={arg['name']: arg for arg in processed_args}
            ))

        loaded_tools = processed_tools
        
        loaded_prompts = []
        try:
            list_prompts_result = await temp_session.list_prompts()
            if hasattr(list_prompts_result, 'prompts'):
                loaded_prompts = list_prompts_result.prompts
        except Exception as e:
            app_logger.error(f"CRITICAL ERROR while loading prompts: {e}", exc_info=True)
        
        viz_tool_obj = SimpleTool(**VIZ_TOOL_DEFINITION)
        loaded_tools.append(viz_tool_obj)
        for util_tool_def in UTIL_TOOL_DEFINITIONS:
            loaded_tools.append(SimpleTool(**util_tool_def))
        loaded_tools.append(SimpleTool(**CORE_LLM_TASK_DEFINITION))


        STATE['mcp_tools'] = {tool.name: tool for tool in loaded_tools}
        if loaded_prompts:
            STATE['mcp_prompts'] = {prompt.name: prompt for prompt in loaded_prompts}

        all_capabilities = []
        all_capabilities.extend([f"- {tool.name} (tool): {tool.description}" for tool in loaded_tools])
        
        for p in loaded_prompts:
            prompt_str = f"- {p.name} (prompt): {p.description or 'No description available.'}"
            if hasattr(p, 'arguments') and p.arguments:
                prompt_str += "\n  - Arguments:"
                for arg in p.arguments:
                    arg_dict = arg.model_dump()
                    arg_name = arg_dict.get('name', 'unknown_arg')
                    prompt_str += f"\n    - `{arg_name}`"
            all_capabilities.append(prompt_str)

        capabilities_list_str = "\n".join(all_capabilities)

        classification_prompt = (
            "You are a helpful assistant that analyzes a list of technical capabilities (tools and prompts) for a Teradata database system and classifies them. "
            "For each capability, you must determine a single user-friendly 'category' for a UI. "
            "Example categories might be 'Data Quality', 'Table Management', 'Performance', 'Utilities', 'Database Information', etc. Be concise and consistent.\n\n"
            "Your response MUST be a single, valid JSON object. The keys of this object must be the capability names, "
            "and the value for each key must be another JSON object containing only the 'category' you determined.\n\n"
            "Example format:\n"
            "{\n"
            '  "capability_name_1": {"category": "Some Category"},\n'
            '  "capability_name_2": {"category": "Another Category"}\n'
            "}\n\n"
            f"--- Capability List ---\n{capabilities_list_str}"
        )
        categorization_system_prompt = "You are an expert assistant that only responds with valid JSON."
        
        classified_capabilities_str, _, _ = await llm_handler.call_llm_api(
            llm_instance, classification_prompt, raise_on_error=True,
            system_prompt_override=categorization_system_prompt
        )
        
        match = re.search(r'\{.*\}', classified_capabilities_str, re.DOTALL)
        if match is None:
            raise ValueError(f"LLM failed to return a valid JSON for capability classification. Response: '{classified_capabilities_str}'")
        
        cleaned_str = match.group(0)
        classified_data = json.loads(cleaned_str)

        STATE['structured_tools'] = {}
        disabled_tools_list = STATE.get("disabled_tools", [])
        
        for tool in loaded_tools:
            classification = classified_data.get(tool.name, {})
            category = classification.get("category", "Uncategorized")

            if category not in STATE['structured_tools']:
                STATE['structured_tools'][category] = []
            
            processed_args = []
            if hasattr(tool, 'args') and isinstance(tool.args, dict):
                for arg_name, arg_details in tool.args.items():
                    if isinstance(arg_details, dict):
                        processed_args.append({
                            "name": arg_name,
                            "type": arg_details.get("type", "any"),
                            "description": arg_details.get("description", "No description available."),
                            "required": arg_details.get("required", False)
                        })

            STATE.setdefault('tool_scopes', {})
            required_args_raw = {arg['name'] for arg in processed_args if arg.get('required')}
            
            canonical_required_args = set()
            for arg_name in required_args_raw:
                found_canonical = False
                for canonical, synonyms in AppConfig.ARGUMENT_SYNONYM_MAP.items():
                    if arg_name in synonyms:
                        canonical_required_args.add(canonical)
                        found_canonical = True
                        break
                if not found_canonical:
                    canonical_required_args.add(arg_name)
            
            for scope, required_set in AppConfig.TOOL_SCOPE_HIERARCHY:
                if required_set.issubset(canonical_required_args):
                    STATE['tool_scopes'][tool.name] = scope
                    break 

            is_disabled = tool.name in disabled_tools_list
            STATE['structured_tools'][category].append({
                "name": tool.name,
                "description": tool.description,
                "arguments": processed_args,
                "disabled": is_disabled
            })

        tool_context_parts = ["--- Available Tools ---"]
        for category, tools in sorted(STATE['structured_tools'].items()):
            enabled_tools_in_category = [t for t in tools if not t['disabled']]
            if enabled_tools_in_category:
                tool_context_parts.append(f"--- Category: {category} ---")
                for tool_info in enabled_tools_in_category:
                    tool_obj = STATE['mcp_tools'][tool_info['name']]
                    tool_str = f"- `{tool_obj.name}` (tool): {tool_obj.description}"
                    args_dict = tool_obj.args if isinstance(tool_obj.args, dict) else {}

                    if args_dict:
                        tool_str += "\n  - Arguments:"
                        for arg_name, arg_details in args_dict.items():
                            arg_type = arg_details.get('type', 'any')
                            is_required = arg_details.get('required', False)
                            req_str = "required" if is_required else "optional"
                            arg_desc = arg_details.get('description', 'No description.')
                            tool_str += f"\n    - `{arg_name}` ({arg_type}, {req_str}): {arg_desc}"
                    tool_context_parts.append(tool_str)
        
        STATE['tools_context'] = "\n".join(tool_context_parts)

        STATE['structured_prompts'] = {}
        disabled_prompts_list = STATE.get("disabled_prompts", [])
        
        if loaded_prompts:
            for prompt_obj in loaded_prompts:
                classification = classified_data.get(prompt_obj.name, {})
                category = classification.get("category", "Uncategorized")
                
                if category not in STATE['structured_prompts']:
                    STATE['structured_prompts'][category] = []

                is_disabled = prompt_obj.name in disabled_prompts_list
                
                cleaned_prompt_desc, prompt_type = _extract_prompt_type_from_description(prompt_obj.description)

                processed_args = []
                if hasattr(prompt_obj, 'arguments') and prompt_obj.arguments:
                    for arg in prompt_obj.arguments:
                        arg_dict = arg.model_dump()
                        cleaned_arg_desc, arg_type = _extract_and_clean_description(arg_dict.get("description"))
                        arg_dict['description'] = cleaned_arg_desc
                        arg_dict['type'] = arg_type
                        processed_args.append(arg_dict)
                
                STATE['structured_prompts'][category].append({
                    "name": prompt_obj.name,
                    "description": cleaned_prompt_desc or "No description available.",
                    "arguments": processed_args,
                    "disabled": is_disabled,
                    "prompt_type": prompt_type
                })

        prompt_context_parts = ["--- Available Prompts ---"]
        for category, prompts in sorted(STATE['structured_prompts'].items()):
            enabled_prompts_in_category = [p for p in prompts if not p['disabled']]
            if enabled_prompts_in_category:
                prompt_context_parts.append(f"--- Category: {category} ---")
                for prompt_info in enabled_prompts_in_category:
                    prompt_description = prompt_info.get("description", "No description available.")
                    prompt_str = f"- `{prompt_info['name']}` (prompt): {prompt_description}"
                    
                    processed_args = prompt_info.get('arguments', [])
                    if processed_args:
                        prompt_str += "\n  - Arguments:"
                        for arg_details in processed_args:
                            arg_name = arg_details.get('name', 'unknown')
                            arg_type = arg_details.get('type', 'any')
                            is_required = arg_details.get('required', False)
                            req_str = "required" if is_required else "optional"
                            arg_desc = arg_details.get('description', 'No description.')
                            prompt_str += f"\n    - `{arg_name}` ({arg_type}, {req_str}): {arg_desc}"
                    prompt_context_parts.append(prompt_str)

        if len(prompt_context_parts) > 1:
            STATE['prompts_context'] = "\n".join(prompt_context_parts)
        else:
            STATE['prompts_context'] = "--- No Prompts Available ---"
            
        tool_args = set()
        for tool in STATE['mcp_tools'].values():
            if hasattr(tool, 'args') and isinstance(tool.args, dict):
                tool_args.update(tool.args.keys())
        
        prompt_args = set()
        for prompt_list in STATE['structured_prompts'].values():
            for prompt_info in prompt_list:
                if 'arguments' in prompt_info and isinstance(prompt_info['arguments'], list):
                    for arg_details in prompt_info['arguments']:
                        if 'name' in arg_details:
                            prompt_args.add(arg_details['name'])
                            
        STATE['all_known_mcp_arguments'] = {
            "tool": list(tool_args),
            "prompt": list(prompt_args)
        }
        app_logger.info(f"Dynamically identified {len(tool_args)} tool and {len(prompt_args)} prompt arguments for context enrichment.")


def _transform_chart_data(data: any) -> list[dict]:
    """
    Cleans and transforms raw data from various tool outputs into a flat list
    of dictionaries suitable for G2Plot charting. This acts as a deterministic
    pre-processing step to prevent common data formatting errors.
    """
    if isinstance(data, list) and all(isinstance(item, dict) and 'results' in item for item in data):
        app_logger.info("Detected nested tool output. Flattening data for charting.")
        flattened_data = []
        for item in data:
            results_list = item.get("results")
            if isinstance(results_list, list):
                flattened_data.extend(results_list)
        return flattened_data

    if isinstance(data, dict) and 'labels' in data and 'values' in data:
        app_logger.warning("Correcting hallucinated chart data format from labels/values to list of dicts.")
        labels = data.get('labels', [])
        values = data.get('values', [])
        if isinstance(labels, list) and isinstance(values, list) and len(labels) == len(values):
            return [{"label": l, "value": v} for l, v in zip(labels, values)]
    if isinstance(data, dict) and 'columns' in data and 'rows' in data:
        app_logger.warning("Correcting hallucinated chart data format from columns/rows to list of dicts.")
        if isinstance(data.get('rows'), list):
            return data['rows']
    
    if isinstance(data, list) and data and isinstance(data[0], dict):
        if "ColumnName" in data[0] and "DistinctValue" in data[0] and "DistinctValueCount" in data[0]:
            app_logger.info("Detected qlty_distinctCategories output pattern. Renaming 'ColumnName' to 'SourceColumnName'.")
            transformed_data = []
            for row in data:
                new_row = row.copy()
                if "ColumnName" in new_row:
                    new_row["SourceColumnName"] = new_row.pop("ColumnName")
                transformed_data.append(new_row)
            return transformed_data

    return data

def _build_g2plot_spec(args: dict, data: list[dict]) -> dict:
    chart_type = args.get("chart_type", "").lower()
    mapping = args.get("mapping", {})
    
    canonical_map = {
        'x_axis': 'xField', 
        'y_axis': 'yField', 
        'color': 'seriesField',
        'angle': 'angleField',
        'category': 'xField', 
        'value': 'yField'      
    }

    reverse_canonical_map = {
        alias.lower(): canonical for canonical, aliases in canonical_map.items() 
        for alias in [canonical] + [key for key in aliases]
    }
    
    options = {"title": {"text": args.get("title", "Generated Chart")}}
    
    first_row_keys_lower = {k.lower(): k for k in data[0].keys()} if data and data[0] else {}
    
    processed_mapping = {}
    for llm_key, data_col_name in mapping.items():
        canonical_key = reverse_canonical_map.get(llm_key.lower())
        if canonical_key:
            actual_col_name = first_row_keys_lower.get(data_col_name.lower())
            if not actual_col_name:
                raise KeyError(f"The mapped column '{data_col_name}' (from '{llm_key}') was not found in the provided data.")
            processed_mapping[canonical_map[canonical_key]] = actual_col_name
        else:
            app_logger.warning(f"Unknown mapping key from LLM: '{llm_key}'. Skipping.")

    options.update(processed_mapping)

    if chart_type == 'pie' and 'seriesField' in options:
        options['colorField'] = options.pop('seriesField')

    final_data = []
    if data:
        for row in data:
            new_row = row.copy()
            for g2plot_key, actual_col_name in options.items():
                if g2plot_key in ['yField', 'angleField', 'size']:
                    cell_value = new_row.get(actual_col_name)
                    if cell_value is not None:
                        try:
                            new_row[actual_col_name] = float(cell_value)
                        except (ValueError, TypeError):
                            app_logger.warning(f"Non-numeric value '{cell_value}' encountered for numeric field '{actual_col_name}'. Conversion failed.")
            final_data.append(new_row)
    
    options["data"] = final_data
    
    g2plot_type_map = {
        "bar": "Column", "column": "Column", "line": "Line", "area": "Area",
        "pie": "Pie", "scatter": "Scatter", "histogram": "Histogram", 
        "heatmap": "Heatmap", "boxplot": "Box", "wordcloud": "WordCloud"
    }
    g2plot_type = g2plot_type_map.get(chart_type, chart_type.capitalize())

    return {"type": g2plot_type, "options": options}

async def _invoke_core_llm_task(STATE: dict, command: dict, session_history: list = None, mode: str = "standard", session_id: str = None) -> tuple[dict, int, int]:
    """
    Executes a task handled by the LLM itself and returns the result along with token counts.
    Supports two modes:
    - 'standard': Synthesizes an answer from structured data provided in the 'source_data' argument.
    - 'full_context': Synthesizes an answer by analyzing the full conversational history.
    """
    args = command.get("arguments", {})
    user_question = args.get("user_question", "No user question provided.")
    llm_instance = STATE.get('llm')
    final_prompt = ""
    reason = ""

    if mode == 'full_context':
        app_logger.info(f"Executing client-side LLM task in 'full_context' mode.")
        reason = f"Synthesizing answer for '{user_question}' from conversation history."

        history_str_parts = []
        if session_history:
            for entry in session_history:
                role = entry.get('role', 'unknown')
                content = entry.get('content', '')
                history_str_parts.append(f"--- Role: {role.capitalize()} ---\n{content}\n--- End Entry ---")
        history_str = "\n".join(history_str_parts)

        final_prompt = (
            "You are an expert data analyst and synthesizer. Your task is to answer the user's question by carefully analyzing the provided conversation history.\n"
            "The history contains the full dialogue, including the user's requests and the assistant's detailed, formatted HTML responses from previous turns.\n"
            "The answer to the current question is likely already present in this history.\n\n"
            "--- CURRENT USER QUESTION ---\n"
            f"{user_question}\n\n"
            "--- FULL CONVERSATION HISTORY ---\n"
            f"{history_str}\n\n"
            "--- INSTRUCTIONS ---\n"
            "1. Read the 'CURRENT USER QUESTION' to understand the user's goal.\n"
            "2. Thoroughly review the 'FULL CONVERSATION HISTORY' to find the previous turn where this question was successfully answered.\n"
            "3. Extract the relevant information from the assistant's previous HTML response.\n"
            "4. Synthesize a new, clean final answer that directly addresses the current user question.\n"
            "5. Your response MUST follow the same semantic content and markdown formatting as the original answer found in the history. Do NOT add conversational intros like \"I found this in the history...\". Simply provide the answer as if you were generating it for the first time."
        )

    else: # Standard mode
        task_description = args.get("task_description")
        source_data_keys = args.get("source_data", [])
        formatting_instructions = args.get("formatting_instructions")
        full_workflow_state = args.get("data", {})
        
        app_logger.info(f"Executing client-side LLM task in 'standard' mode: {task_description}")
        reason = f"Executing CoreLLMTask: {task_description}"

        focused_data_for_task = {}
        if isinstance(full_workflow_state, dict):
            for key in source_data_keys:
                if key in full_workflow_state:
                    focused_data_for_task[key] = full_workflow_state[key]
        
        if not focused_data_for_task and source_data_keys:
            app_logger.warning(f"CoreLLMTask was called for '{task_description}' but no source data was found for keys: {source_data_keys}. Passing all data as a fallback.")
            focused_data_for_task = full_workflow_state

        known_context = {}
        if isinstance(full_workflow_state, dict):
            for phase_results in full_workflow_state.values():
                if isinstance(phase_results, list):
                    for result in phase_results:
                        if isinstance(result, dict) and "metadata" in result:
                            metadata = result.get("metadata", {})
                            if "database" in metadata and "database_name" not in known_context:
                                known_context["database_name"] = metadata["database"]
                            if "table" in metadata and "table_name" not in known_context:
                                known_context["table_name"] = metadata["table"]

        known_context_str = "\n".join([f"- {key}: {value}" for key, value in known_context.items()]) if known_context else "None"

        final_prompt = "You are a highly capable text processing and synthesis assistant.\n\n"

        if user_question:
            final_prompt += (
                "--- PRIMARY GOAL ---\n"
                f"Your most important task is to directly answer the user's original question: '{user_question}'.\n"
                "You MUST begin your response with the direct answer. Do not repeat the user's question or use conversational intros like 'Here is...'. "
                "After providing the direct answer, you may then proceed with a more general summary or analysis of the data.\n\n"
            )

        final_prompt += (
            "--- TASK ---\n"
            f"{task_description}\n\n"
            "--- RELEVANT DATA (Selected from Previous Phases) ---\n"
            f"{json.dumps(focused_data_for_task, indent=2)}\n\n"
            "--- KNOWN CONTEXT ---\n"
            "The following key information has already been established in previous steps. You MUST use this information to populate header fields like 'Table Name' or 'Database Name'.\n"
            f"{known_context_str}\n\n"
            "--- SEMANTIC GUIDANCE ---\n"
            "When the 'TASK' asks for a 'description', 'analysis', or 'summary', you MUST synthesize new content that reflects the *semantic intent* of the request.\n"
            "For example:\n"
            "- If the 'TASK' asks for a 'business description of a table', you MUST explain its purpose from an organizational, functional, or analytical viewpoint, and the business significance of its columns. Do NOT simply reiterate technical DDL (Data Definition Language) information, even if it is present in the `RELEVANT DATA`.\n"
            "- If the 'TASK' asks for a 'summary of errors', you MUST provide a concise overview of the issues, not just a list of error codes.\n"
            "Always prioritize generating content that matches the *meaning* and *purpose* of the 'TASK', interpreting the raw data to produce the desired semantic output.\n\n"
            "--- CRITICAL RULES ---\n"
            "1. **Separate Data from Description:** If the 'TASK' requires you to output header fields (like `***Table Name:***` or `***Database Name:***`) AND a main description, you MUST treat these as separate steps. First, populate the header fields using the 'KNOWN CONTEXT'. Then, write the main description. Do NOT merge context data (like the database name) into a single header field.\n"
            "2. **Content and Formatting Precision:** You MUST adhere to any and all formatting instructions contained in the 'TASK' description with absolute precision. Do not deviate, simplify, or change the requested format in any way. You MUST generate content that genuinely fulfills the semantic goal of the 'TASK'.\n"
            "3. **Key Name Adherence:** If the 'TASK' description provides an example format, you MUST use the exact key names (e.g., `***Description:***`, `***Table Name:***`) shown in the example. Do not invent new key names or use synonyms like 'Table Description'.\n"
            "4. **Column Placeholder Replacement:** If the 'TASK' involves describing table columns and the formatting guidelines include a placeholder like `***ColumnX:***` or `***[Column Name]:***`, you MUST replace that placeholder with the actual name of the column you are describing (e.g., `***CUST_ID:***`, `***FIRSTNAME:***`). Do not use generic, numbered placeholders like 'Column1', 'Column2', etc.\n"
            "5. **Layout and Line Breaks:** Each key-value pair or list item specified in the formatting guidelines MUST be on its own separate line. Do not combine multiple items onto a single line.\n\n"
        )

        if formatting_instructions:
            final_prompt += f"--- ADDITIONAL FORMATTING INSTRUCTIONS ---\n{formatting_instructions}\n\n"

        final_prompt += "Your response should be the direct result of the task. Do not add any conversational text or extra formatting unless explicitly requested by the task description."

    response_text, input_tokens, output_tokens = await llm_handler.call_llm_api(
        llm_instance=llm_instance,
        prompt=final_prompt,
        reason=reason,
        system_prompt_override="You are a text processing and synthesis assistant.",
        raise_on_error=True,
        session_id=session_id
    )

    refusal_phrases = [
        "i'm unable to", "i cannot", "unable to generate", "no specific task", 
        "as an ai model", "i can't provide"
    ]
    
    if any(phrase in response_text.lower() for phrase in refusal_phrases):
        app_logger.error(f"CoreLLMTask failed due to detected LLM refusal. Response: '{response_text}'")
        result = {
            "status": "error", 
            "error_message": "LLM refused to perform the synthesis task.",
            "data": response_text
        }
    else:
        result = {"status": "success", "results": [{"response": response_text}]}

    return result, input_tokens, output_tokens

async def _invoke_util_calculate_date_range(STATE: dict, command: dict, session_id: str = None) -> dict:
    """
    Calculates a list of dates from a start date and a phrase using a multi-layered approach.
    It first tries a robust deterministic method and falls back to an LLM for complex phrases.
    """
    args = command.get("arguments", {})
    start_date_str = args.get("start_date")
    date_phrase = args.get("date_phrase", "").lower().strip()
    
    app_logger.info(f"Executing client-side tool: util_calculateDateRange with start: '{start_date_str}', phrase: '{date_phrase}'")

    if not start_date_str or not date_phrase:
        return {"status": "error", "error_message": "Missing start_date or date_phrase."}

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = None
    
    try:
        if "yesterday" in date_phrase:
            start_date = start_date - timedelta(days=1)
            end_date = start_date
        elif "today" in date_phrase:
            end_date = start_date
        elif "past weekend" in date_phrase or "last weekend" in date_phrase:
            days_since_sunday = (start_date.weekday() - 6) % 7
            end_date = start_date - timedelta(days=days_since_sunday)
            start_date = end_date - timedelta(days=1)
        elif "last week" in date_phrase or "past week" in date_phrase:
            start_of_last_week = start_date - timedelta(days=start_date.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            start_date, end_date = start_of_last_week, end_of_last_week
        elif "last month" in date_phrase or "past month" in date_phrase:
            first_day_of_current_month = start_date.replace(day=1)
            last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
            first_day_of_last_month = last_day_of_last_month.replace(day=1)
            start_date, end_date = first_day_of_last_month, last_day_of_last_month
        elif "last year" in date_phrase or "past year" in date_phrase:
            first_day_of_last_year = start_date.replace(year=start_date.year - 1, month=1, day=1)
            last_day_of_last_year = start_date.replace(year=start_date.year - 1, month=12, day=31)
            start_date, end_date = first_day_of_last_year, last_day_of_last_year
        else:
            match = re.search(r'(\d+)\s+(day|week|month|year)s?', date_phrase)
            if match:
                quantity = int(match.group(1))
                unit = match.group(2)
                
                if "past" in date_phrase or "last" in date_phrase:
                    if unit == "day":
                        end_date = start_date - timedelta(days=1)
                        start_date = end_date - timedelta(days=quantity - 1)
                    elif unit == "week":
                        end_date = start_date - timedelta(days=start_date.weekday() + 1)
                        start_date = end_date - timedelta(weeks=quantity - 1) - timedelta(days=end_date.weekday())
                    elif unit == "month":
                        end_date = start_date.replace(day=1) - timedelta(days=1)
                        start_date = end_date.replace(day=1)
                        for _ in range(quantity - 1):
                            start_date = (start_date - timedelta(days=1)).replace(day=1)
                    elif unit == "year":
                        end_date = start_date.replace(month=1, day=1) - timedelta(days=1)
                        start_date = end_date.replace(year=end_date.year - (quantity - 1), month=1, day=1)

    except Exception as e:
        app_logger.warning(f"Deterministic date parsing failed with error: {e}. This may be expected for complex phrases.")
        end_date = None

    if end_date is None:
        app_logger.info(f"Deterministic logic failed for '{date_phrase}'. Falling back to LLM-based date extraction.")
        
        llm_prompt = (
            f"Given the current date is {start_date_str}, analyze the phrase '{date_phrase}'. "
            "Determine the exact start and end dates for this phrase. "
            "Your response MUST be ONLY a single, valid JSON object with two keys: 'start_date' and 'end_date', both in 'YYYY-MM-DD' format."
        )
        
        response_text, _, _ = await llm_handler.call_llm_api(
            llm_instance=STATE.get('llm'),
            prompt=llm_prompt,
            reason=f"LLM fallback for complex date phrase: {date_phrase}",
            system_prompt_override="You are a helpful assistant that only responds with valid JSON.",
            raise_on_error=True,
            session_id=session_id
        )
        
        try:
            date_data = json.loads(response_text)
            start_date = datetime.strptime(date_data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(date_data['end_date'], '%Y-%m-%d').date()
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            error_msg = f"LLM fallback for date range failed to produce a valid result. Response: '{response_text}'. Error: {e}"
            app_logger.error(error_msg)
            return {"status": "error", "error_message": error_msg}

    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append({"date": current_date.strftime('%Y-%m-%d')})
        current_date += timedelta(days=1)

    return {
        "status": "success",
        "metadata": {"tool_name": "util_calculateDateRange"},
        "results": date_list
    }

async def invoke_mcp_tool(STATE: dict, command: dict, session_id: str = None) -> tuple[any, int, int]:
    mcp_client = STATE.get('mcp_client')
    tool_name = command.get("tool_name")
    
    if tool_name == "CoreLLMTask":
        args = command.get("arguments", {})
        mode = args.pop("mode", "standard")
        session_history = args.pop("session_history", None)
        return await _invoke_core_llm_task(STATE, command, session_history=session_history, mode=mode, session_id=session_id)

    if tool_name == "util_getCurrentDate":
        app_logger.info("Executing client-side tool: util_getCurrentDate")
        current_date = datetime.now().strftime('%Y-%m-%d')
        result = {
            "status": "success",
            "metadata": {"tool_name": "util_getCurrentDate"},
            "results": [{"current_date": current_date}]
        }
        return result, 0, 0

    if tool_name == "util_calculateDateRange":
        result = await _invoke_util_calculate_date_range(STATE, command, session_id=session_id)
        return result, 0, 0

    if tool_name == "viz_createChart":
        app_logger.info(f"Handling abstract chart generation for: {command}")
        
        try:
            args = command.get("arguments", {})
            data = args.get("data")
            data = _transform_chart_data(data) 
            
            if not isinstance(data, list) or not data:
                result = {"error": "Validation failed", "data": "The 'data' argument must be a non-empty list of dictionaries."}
                return result, 0, 0
            
            chart_spec = _build_g2plot_spec(args, data)
            
            result = {"type": "chart", "spec": chart_spec, "metadata": {"tool_name": "viz_createChart"}}
            return result, 0, 0
        except Exception as e:
            app_logger.error(f"Error building G2Plot spec: {e}", exc_info=True)
            result = {"error": "Chart Generation Failed", "data": str(e)}
            return result, 0, 0

    args = {}
    if isinstance(command, dict):
        potential_arg_keys = [
            "arguments", "args", "tool_args", "parameters", 
            "tool_input", "action_input", "tool_arguments"
        ]
        
        found_args = None
        for key in potential_arg_keys:
            if key in command and isinstance(command[key], dict):
                found_args = command[key]
                break
        
        if found_args is not None:
            args = found_args
        else:
            possible_wrapper_keys = ["action", "tool"]
            for wrapper_key in possible_wrapper_keys:
                if wrapper_key in command and isinstance(command[wrapper_key], dict):
                    for arg_key in potential_arg_keys:
                        if arg_key in command[wrapper_key] and isinstance(command[wrapper_key][arg_key], dict):
                            found_args = command[wrapper_key][arg_key]
                            break
                    if found_args is not None:
                        break
            
            if found_args is not None:
                args = found_args

    synonym_map = {
        "database": "database_name", "db": "database_name", 
        "table": "table_name", "tbl": "table_name", "tablename": "table_name",
        "column": "column_name", "col": "column_name"
    }
    normalized_args = {synonym_map.get(k.lower(), k): v for k, v in args.items()}
    if normalized_args != args:
        app_logger.info(f"Normalized tool arguments for '{tool_name}'. Original: {args}, Corrected: {normalized_args}")
        args = normalized_args


    app_logger.debug(f"Invoking tool '{tool_name}' with args: {args}")
    try:
        server_name = APP_CONFIG.CURRENT_MCP_SERVER_NAME
        if not server_name:
            raise Exception("MCP server name not found in configuration.")
            
        async with mcp_client.session(server_name) as temp_session:
            call_tool_result = await temp_session.call_tool(tool_name, args)
    except Exception as e:
        app_logger.error(f"Error during tool invocation for '{tool_name}': {e}", exc_info=True)
        result = {"status": "error", "error": f"An exception occurred while invoking tool '{tool_name}'.", "data": str(e)}
        return result, 0, 0
    
    if hasattr(call_tool_result, 'content') and isinstance(call_tool_result.content, list) and len(call_tool_result.content) > 0:
        text_content = call_tool_result.content[0]
        if hasattr(text_content, 'text') and isinstance(text_content.text, str):
            try:
                result = json.loads(text_content.text)
                return result, 0, 0
            except json.JSONDecodeError:
                app_logger.warning(f"Tool '{tool_name}' returned a non-JSON string: '{text_content.text}'")
                result = {"status": "error", "error": "Tool returned non-JSON string", "data": text_content.text}
                return result, 0, 0
    
    raise RuntimeError(f"Unexpected tool result format for '{tool_name}': {call_tool_result}")
