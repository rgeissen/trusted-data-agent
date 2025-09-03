# trusted_data_agent/agent/orchestrators.py
import json
import logging
from datetime import datetime, timedelta

from trusted_data_agent.mcp import adapter as mcp_adapter
from trusted_data_agent.llm import handler as llm_handler

app_logger = logging.getLogger("quart.app")

def _format_sse(data: dict, event: str = None) -> str:
    """Helper to format data for Server-Sent Events."""
    msg = f"data: {json.dumps(data)}\n"
    if event is not None:
        msg += f"event: {event}\n"
    return f"{msg}\n"

async def execute_date_range_orchestrator(executor, command: dict, date_param_name: str, date_phrase: str):
    """
    Executes a tool over a calculated date range when the tool itself
    only supports a single date parameter.
    """
    tool_name = command.get("tool_name")
    yield _format_sse({
        "step": "System Orchestration", "type": "workaround",
        "details": f"Detected date range query ('{date_phrase}') for single-day tool ('{tool_name}')."
    })

    # Get the current date to resolve relative phrases like "yesterday"
    date_command = {"tool_name": "util_getCurrentDate"}
    date_result, _, _ = await mcp_adapter.invoke_mcp_tool(executor.dependencies['STATE'], date_command)
    if not (date_result and date_result.get("status") == "success" and date_result.get("results")):
        raise RuntimeError("Date Range Orchestrator failed to fetch current date.")
    current_date_str = date_result["results"][0].get("current_date")

    # Use an LLM to convert the natural language phrase into a concrete start/end date
    conversion_prompt = (
        f"Given the current date is {current_date_str}, "
        f"what are the start and end dates for '{date_phrase}'? "
        "Respond with ONLY a JSON object with 'start_date' and 'end_date' in YYYY-MM-DD format."
    )
    reason = "Calculating date range."
    yield _format_sse({"step": "Calling LLM", "details": reason})
    yield _format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
    range_response_str, _, _ = await executor._call_llm_and_update_tokens(
        prompt=conversion_prompt, reason=reason,
        system_prompt_override="You are a JSON-only responding assistant.", raise_on_error=True
    )
    yield _format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")
    
    try:
        range_data = json.loads(range_response_str)
        start_date = datetime.strptime(range_data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(range_data['end_date'], '%Y-%m-%d').date()
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise RuntimeError(f"Date Range Orchestrator failed to parse date range. Error: {e}")

    # Loop through the date range and execute the tool for each day
    all_results = []
    yield _format_sse({"target": "db", "state": "busy"}, "status_indicator_update")
    current_date_in_loop = start_date
    while current_date_in_loop <= end_date:
        date_str = current_date_in_loop.strftime('%Y-%m-%d')
        yield _format_sse({"step": f"Processing data for: {date_str}"})
        
        day_command = {**command, 'arguments': {**command['arguments'], date_param_name: date_str}}
        day_result, _, _ = await mcp_adapter.invoke_mcp_tool(executor.dependencies['STATE'], day_command)
        
        if isinstance(day_result, dict) and day_result.get("status") == "success" and day_result.get("results"):
            all_results.extend(day_result["results"])
        
        current_date_in_loop += timedelta(days=1)
    yield _format_sse({"target": "db", "state": "idle"}, "status_indicator_update")
    
    final_tool_output = {
        "status": "success",
        "metadata": {"tool_name": tool_name, "comment": f"Consolidated results for {date_phrase}"},
        "results": all_results
    }
    executor._add_to_structured_data(final_tool_output)
    executor.last_tool_output = final_tool_output

async def execute_column_iteration(executor, command: dict):
    """
    Executes a tool over multiple columns of a table, including checks for
    data type compatibility.
    """
    tool_name = command.get("tool_name")
    base_args = command.get("arguments", {})
    db_name, table_name = base_args.get("database_name"), base_args.get("table_name")

    # First, get the list of all columns for the target table
    cols_command = {"tool_name": "base_columnDescription", "arguments": {"database_name": db_name, "table_name": table_name}}
    yield _format_sse({"target": "db", "state": "busy"}, "status_indicator_update")
    cols_result, _, _ = await mcp_adapter.invoke_mcp_tool(executor.dependencies['STATE'], cols_command)
    yield _format_sse({"target": "db", "state": "idle"}, "status_indicator_update")
    
    if not (cols_result and isinstance(cols_result, dict) and cols_result.get('status') == 'success' and cols_result.get('results')):
        raise ValueError(f"Failed to retrieve column list for iteration. Response: {cols_result}")
    
    all_columns_metadata = cols_result.get('results', [])
    all_column_results = [cols_result]
    
    # --- MODIFICATION START: Add LLM indicator events ---
    yield _format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
    tool_constraints = await executor._get_tool_constraints(tool_name)
    yield _format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")
    # --- MODIFICATION END ---
    required_type = tool_constraints.get("dataType") if tool_constraints else None
    
    # Loop through each column and execute the tool
    yield _format_sse({"target": "db", "state": "busy"}, "status_indicator_update")
    for column_info in all_columns_metadata:
        column_name = column_info.get("ColumnName")
        col_type = next((v for k, v in column_info.items() if "type" in k.lower()), "").upper()

        # Skip columns that don't match the required data type
        if required_type and col_type != "UNKNOWN":
            is_numeric = any(t in col_type for t in ["INT", "NUMERIC", "DECIMAL", "FLOAT"])
            is_char = any(t in col_type for t in ["CHAR", "VARCHAR", "TEXT"])
            if (required_type == "numeric" and not is_numeric) or \
               (required_type == "character" and not is_char):
                skipped_result = {"status": "skipped", "metadata": {"tool_name": tool_name, "column_name": column_name}, "results": [{"reason": f"Tool requires {required_type}, but '{column_name}' is {col_type}."}]}
                all_column_results.append(skipped_result)
                yield _format_sse({"step": "Skipping incompatible column", "details": skipped_result}, "tool_result")
                continue

        iter_command = {"tool_name": tool_name, "arguments": {**base_args, 'column_name': column_name}}
        col_result, _, _ = await mcp_adapter.invoke_mcp_tool(executor.dependencies['STATE'], iter_command)
        all_column_results.append(col_result)
    yield _format_sse({"target": "db", "state": "idle"}, "status_indicator_update")

    executor._add_to_structured_data(all_column_results)
    executor.last_tool_output = {"metadata": {"tool_name": tool_name}, "results": all_column_results, "status": "success"}

async def execute_hallucinated_loop(executor, phase: dict):
    """
    Handles cases where the planner hallucinates a loop over a list of natural
    language strings instead of a proper data source. It uses an LLM to
    semantically understand the intent and then executes a deterministic loop.
    """
    tool_name = phase.get("relevant_tools", [None])[0]
    hallucinated_items = phase.get("loop_over", [])
    
    yield _format_sse({
        "step": "System Correction", "type": "workaround",
        "details": f"Planner hallucinated a loop. Correcting with generalized orchestrator for items: {hallucinated_items}"
    })

    # If the list contains a single item that looks like a date phrase, reroute to the date orchestrator
    if len(hallucinated_items) == 1 and isinstance(hallucinated_items[0], str):
        # A simple heuristic to check for date-like phrases
        date_keywords = ["day", "week", "month", "year", "past", "last", "next"]
        if any(keyword in hallucinated_items[0].lower() for keyword in date_keywords):
            # This assumes the tool takes a 'date' parameter. This is a reasonable assumption for this specific failure mode.
            # A more advanced version could infer the parameter name as well.
            command_for_date_orchestrator = {"tool_name": tool_name, "arguments": {}}
            async for event in execute_date_range_orchestrator(executor, command_for_date_orchestrator, 'date', hallucinated_items[0]):
                yield event
            return

    # For all other cases, use the generalized LLM-based approach
    semantic_prompt = (
        f"Given the tool `{tool_name}` and the list of items `{json.dumps(hallucinated_items)}`, "
        "what single tool argument name do these items represent? "
        "Respond with only a JSON object, like `{{\"argument_name\": \"table_name\"}}`."
    )
    reason = "Semantically analyzing hallucinated loop items."
    yield _format_sse({"step": "Calling LLM", "details": reason})
    yield _format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
    response_str, _, _ = await executor._call_llm_and_update_tokens(
        prompt=semantic_prompt, reason=reason,
        system_prompt_override="You are a JSON-only responding assistant.", raise_on_error=True
    )
    yield _format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")
    
    try:
        semantic_data = json.loads(response_str)
        argument_name = semantic_data.get("argument_name")
        if not argument_name:
            raise ValueError("LLM did not provide an 'argument_name'.")
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"Failed to semantically understand hallucinated loop items. Error: {e}")

    # Execute a deterministic loop using the understood argument name
    all_results = []
    yield _format_sse({"target": "db", "state": "busy"}, "status_indicator_update")
    for item in hallucinated_items:
        yield _format_sse({"step": f"Processing item: {item}"})
        command = {"tool_name": tool_name, "arguments": {argument_name: item}}
        result, _, _ = await mcp_adapter.invoke_mcp_tool(executor.dependencies['STATE'], command)
        all_results.append(result)
    yield _format_sse({"target": "db", "state": "idle"}, "status_indicator_update")

    executor._add_to_structured_data(all_results)
    executor.last_tool_output = {"metadata": {"tool_name": tool_name}, "results": all_results, "status": "success"}