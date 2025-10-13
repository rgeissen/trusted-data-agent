# trusted_data_agent/agent/planner.py
import re
import json
import logging
import copy
import uuid
from typing import TYPE_CHECKING

from langchain_mcp_adapters.prompts import load_mcp_prompt

from trusted_data_agent.core import session_manager
from trusted_data_agent.core.config import APP_CONFIG
from trusted_data_agent.agent.prompts import (
    WORKFLOW_META_PLANNING_PROMPT,
    TASK_CLASSIFICATION_PROMPT
)

if TYPE_CHECKING:
    from trusted_data_agent.agent.executor import PlanExecutor


app_logger = logging.getLogger("quart.app")


def get_prompt_text_content(prompt_obj):
    """
    Extracts the text content from a loaded prompt object, handling different
    potential formats returned by the MCP adapter.
    """
    if isinstance(prompt_obj, str):
        return prompt_obj
    if (isinstance(prompt_obj, list) and
        len(prompt_obj) > 0 and
        hasattr(prompt_obj[0], 'content') and
        isinstance(prompt_obj[0].content, str)):
        return prompt_obj[0].content
    elif (isinstance(prompt_obj, dict) and 
        'messages' in prompt_obj and
        isinstance(prompt_obj['messages'], list) and 
        len(prompt_obj['messages']) > 0 and
        'content' in prompt_obj['messages'][0] and
        isinstance(prompt_obj['messages'][0]['content'], dict) and
        'text' in prompt_obj['messages'][0]['content']):
        return prompt_obj['messages'][0]['content']['text']
    
    return ""


class Planner:
    """
    Encapsulates all logic related to plan generation, validation, and refinement.
    It is instantiated by the PlanExecutor and maintains a reference to it for state
    and helper method access.
    """
    def __init__(self, executor: 'PlanExecutor'):
        self.executor = executor

    def _create_summary_from_history(self, history: dict) -> str:
        """
        Creates a token-efficient, high-signal summary of a history dictionary
        by formatting it into a canonical JSON structure for the planner.
        """
        if not history or not isinstance(history, dict) or "workflow_history" not in history:
            return json.dumps({"workflow_history": []}, indent=2)
        return json.dumps(history, indent=2)

    def _hydrate_plan_from_previous_turn(self):
        """
        Detects if a plan starts with a loop that depends on data from the
        previous turn, and if so, injects that data into the current state.
        This is the "plan injection" feature.
        """
        if not self.executor.meta_plan or not self.executor.previous_turn_data:
            return

        first_phase = self.executor.meta_plan[0]
        is_candidate = (
            first_phase.get("type") == "loop" and
            isinstance(first_phase.get("loop_over"), str) and
            first_phase.get("loop_over").startswith("result_of_phase_")
        )

        if not is_candidate:
            return

        looping_phase_num = first_phase.get("phase")
        source_phase_key = first_phase.get("loop_over")
        source_phase_num_match = re.search(r'\d+', source_phase_key)
        if not source_phase_num_match:
            return 
        source_phase_num = int(source_phase_num_match.group())

        if source_phase_num >= looping_phase_num:
            data_to_inject = None
            
            workflow_history = self.executor.previous_turn_data.get("workflow_history", [])
            if not isinstance(workflow_history, list):
                 return

            for turn in reversed(workflow_history):
                if not isinstance(turn, dict): continue
                execution_trace = turn.get("execution_trace", [])
                for entry in reversed(execution_trace):
                    result_summary = entry.get("tool_output_summary", {})
                    if (isinstance(result_summary, dict) and
                        result_summary.get("status") == "success"):
                        
                        data_to_inject = {
                            "status": "success",
                            "metadata": result_summary.get("metadata", {}),
                            "comment": "Data injected from previous turn's summary."
                        }
                        if "results" in result_summary:
                            data_to_inject["results"] = result_summary["results"]
                        
                        break
                if data_to_inject:
                    break
            
            if data_to_inject:
                injection_key = "injected_previous_turn_data"
                self.executor.workflow_state[injection_key] = [data_to_inject]
                
                original_loop_source = self.executor.meta_plan[0]['loop_over']
                self.executor.meta_plan[0]['loop_over'] = injection_key
                
                app_logger.info(f"PLAN INJECTION: Hydrated plan with data from previous turn. Loop source changed from '{original_loop_source}' to '{injection_key}'.")
                
                yield self.executor._format_sse({
                    "step": "Plan Optimization",
                    "type": "plan_optimization",
                    "details": f"PLAN HYDRATION: Injected data from the previous turn to fulfill the request: '{self.executor.original_user_input}'."
                })

    def _validate_and_correct_plan(self):
        """
        Deterministically validates the generated meta-plan for common LLM errors,
        such as misclassifying prompts as tools, and corrects them in place.
        """
        if not self.executor.meta_plan:
            return

        all_prompts = self.executor.dependencies['STATE'].get('mcp_prompts', {})
        all_tools = self.executor.dependencies['STATE'].get('mcp_tools', {})

        for phase in self.executor.meta_plan:
            original_phase = copy.deepcopy(phase)
            correction_made = False

            if 'relevant_tools' in phase and isinstance(phase['relevant_tools'], list) and phase['relevant_tools']:
                capability_name = phase['relevant_tools'][0]
                if capability_name in all_prompts:
                    app_logger.warning(f"PLAN CORRECTION: Planner wrongly classified prompt '{capability_name}' as a tool. Correcting.")
                    phase['executable_prompt'] = capability_name
                    del phase['relevant_tools']
                    correction_made = True

            elif 'executable_prompt' in phase and isinstance(phase['executable_prompt'], str):
                capability_name = phase['executable_prompt']
                if capability_name in all_tools:
                    app_logger.warning(f"PLAN CORRECTION: Planner wrongly classified tool '{capability_name}' as a prompt. Correcting.")
                    phase['relevant_tools'] = [capability_name]
                    del phase['executable_prompt']
                    correction_made = True
            
            if correction_made:
                yield self.executor._format_sse({
                    "step": "System Correction",
                    "type": "workaround",
                    "details": {
                        "summary": "Planner misclassified a capability. The system has corrected the plan to ensure proper execution.",
                        "correction": {
                            "from": original_phase,
                            "to": phase
                        }
                    }
                })

    def _ensure_final_report_phase(self):
        """
        Deterministically checks and adds a final reporting phase. It is context-aware
        and will not add a report phase to sub-processes where it is not required,
        preventing redundant plan modifications.
        """
        if not self.executor.meta_plan or self.executor.is_conversational_plan:
            return
            
        is_sub_process_without_summary = (
            self.executor.execution_depth > 0 and 
            not self.executor.force_final_summary and
            not APP_CONFIG.SUB_PROMPT_FORCE_SUMMARY
        )
        if is_sub_process_without_summary:
            app_logger.info("Skipping final report check for non-summarizing sub-process.")
            return

        last_phase = self.executor.meta_plan[-1]
        last_phase_tools = last_phase.get("relevant_tools", [])
        is_already_finalized = any(tool in ["TDA_FinalReport", "TDA_ComplexPromptReport"] for tool in last_phase_tools)
        is_synthesis_plan = any("TDA_ContextReport" in p.get("relevant_tools", []) for p in self.executor.meta_plan)

        if is_already_finalized or is_synthesis_plan:
            return

        app_logger.warning("PLAN CORRECTION: The generated plan is missing a final reporting step. System is adding it now.")
        
        reporting_tool_name = "TDA_ComplexPromptReport" if self.executor.source == 'prompt_library' else "TDA_FinalReport"
        
        new_phase_number = len(self.executor.meta_plan) + 1
        final_phase = {
            "phase": new_phase_number,
            "goal": "Generate the final report based on the data gathered.",
            "relevant_tools": [reporting_tool_name],
            "arguments": {}
        }
        self.executor.meta_plan.append(final_phase)
        
        yield self.executor._format_sse({
            "step": "System Correction",
            "type": "workaround",
            "details": {
                "summary": "The agent's plan was missing a final reporting step. The system has automatically added it to ensure a complete response.",
                "correction": { "added_phase": final_phase }
            }
        })


    async def _rewrite_plan_for_multi_loop_synthesis(self):
        """
        Surgically corrects plans where multiple, parallel loops feed into a
        final summary. It inserts a new, intermediate distillation phase to
        transform the raw data into high-level insights before the final
        summary is generated.
        """
        if not self.executor.meta_plan or len(self.executor.meta_plan) < 3:
            return

        made_change = False
        i = 0
        while i < len(self.executor.meta_plan) - 1:
            if (self.executor.meta_plan[i].get("type") == "loop" and 
                self.executor.meta_plan[i+1].get("type") == "loop"):
                
                loop_block_start_index = i
                loop_block = [self.executor.meta_plan[i]]
                base_loop_source = self.executor.meta_plan[i].get("loop_over")
                
                if not base_loop_source:
                    i += 1
                    continue

                j = i + 1
                while j < len(self.executor.meta_plan) and self.executor.meta_plan[j].get("type") == "loop" and self.executor.meta_plan[j].get("loop_over") == base_loop_source:
                    loop_block.append(self.executor.meta_plan[j])
                    j += 1
                
                if len(loop_block) >= 2 and j < len(self.executor.meta_plan):
                    final_phase = self.executor.meta_plan[j]
                    is_final_summary = final_phase.get("relevant_tools") == ["TDA_LLMTask"]
                    
                    if is_final_summary:
                        app_logger.warning(
                            "PLAN REWRITE: Detected inefficient multi-loop plan. "
                            "Injecting an intermediate distillation phase."
                        )
                        original_plan_snippet = copy.deepcopy(self.executor.meta_plan[loop_block_start_index : j+1])
                        
                        synthesis_phase_num = j + 1
                        source_data_keys = [f"result_of_phase_{p['phase']}" for p in loop_block]
                        
                        synthesis_task = {
                            "phase": synthesis_phase_num,
                            "goal": f"Distill the raw data from phases {loop_block[0]['phase']}-{loop_block[-1]['phase']} into a concise, per-item summary.",
                            "relevant_tools": ["TDA_LLMTask"],
                            "arguments": {
                                "task_description": (
                                    "Analyze the voluminous raw data from the previous loops. Your task is to distill this information. "
                                    "For each item (e.g., table) processed, produce a concise, one-paragraph summary of the most critical findings. "
                                    "Your output MUST be a clean list of these summary objects, each containing the item's name and the summary text."
                                ),
                                "source_data": source_data_keys
                            }
                        }
                        
                        self.executor.meta_plan.insert(j, synthesis_task)
                        
                        for phase_index in range(j + 1, len(self.executor.meta_plan)):
                            self.executor.meta_plan[phase_index]["phase"] += 1
                        
                        final_summary_phase = self.executor.meta_plan[j+1]
                        new_source_key = f"result_of_phase_{synthesis_phase_num}"
                        final_summary_phase["arguments"]["source_data"] = [new_source_key]
                        
                        made_change = True
                        
                        yield self.executor._format_sse({
                            "step": "System Correction",
                            "type": "workaround",
                            "details": {
                                "summary": "The agent's plan was inefficient. The system has automatically rewritten it to include a data distillation step, improving the quality and reliability of the final report.",
                                "correction": {
                                    "from": original_plan_snippet,
                                    "to": copy.deepcopy(self.executor.meta_plan[loop_block_start_index : j+2])
                                }
                            }
                        })
                        
                        i = j + 1 
                        continue
            i += 1
        
        if made_change:
            app_logger.info(f"PLAN REWRITE (Multi-Loop): Final rewritten plan: {self.executor.meta_plan}")

    async def _rewrite_plan_for_corellmtask_loops(self):
        """
        Surgically corrects plans where the LLM has incorrectly placed a
        `TDA_LLMTask` inside a loop for an aggregation-style task. It transforms
        the loop into a standard, single-execution phase. This now uses a
        classifier LLM call to determine if the task is appropriate for this optimization.
        """
        if not self.executor.meta_plan:
            return

        made_change = False
        for phase in self.executor.meta_plan:
            is_inefficient_loop = (
                phase.get("type") == "loop" and
                phase.get("relevant_tools") == ["TDA_LLMTask"]
            )

            if is_inefficient_loop:
                task_description = phase.get("arguments", {}).get("task_description", "")
                
                if not task_description:
                    task_type = "aggregation"
                    app_logger.warning("TDA_LLMTask loop has no task_description. Defaulting to 'aggregation' for rewrite.")
                else:
                    classification_prompt = TASK_CLASSIFICATION_PROMPT.format(task_description=task_description)
                    reason = "Classifying TDA_LLMTask loop intent for optimization."
                    
                    call_id = str(uuid.uuid4())
                    yield self.executor._format_sse({"step": "Analyzing Plan Efficiency", "type": "plan_optimization", "details": {"summary": "Checking if an iterative task can be optimized into a single batch operation.", "call_id": call_id}})
                    yield self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
                    
                    response_text, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
                        prompt=classification_prompt, 
                        reason=reason,
                        system_prompt_override="You are a JSON-only responding assistant.", 
                        raise_on_error=False,
                        disabled_history=True,
                        source=self.executor.source
                    )
                    
                    updated_session = session_manager.get_session(self.executor.session_id)
                    if updated_session:
                        yield self.executor._format_sse({ "statement_input": input_tokens, "statement_output": output_tokens, "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0), "call_id": call_id }, "token_update")
                    
                    yield self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")

                    try:
                        classification_data = json.loads(response_text)
                        task_type = classification_data.get("classification", "synthesis")
                    except (json.JSONDecodeError, AttributeError):
                        app_logger.error(f"Failed to parse task classification. Defaulting to 'synthesis' to be safe. Response: {response_text}")
                        task_type = "synthesis"

                if task_type == "aggregation":
                    app_logger.warning(
                        f"PLAN REWRITE: Detected inefficient AGGREGATION TDA_LLMTask loop in phase {phase.get('phase')}. "
                        "Transforming to a standard phase."
                    )
                    
                    original_phase = copy.deepcopy(phase)

                    phase.pop("type", None)
                    loop_source = phase.pop("loop_over", None)
                    
                    if "arguments" not in phase: phase["arguments"] = {}
                    if "source_data" not in phase["arguments"] and loop_source:
                        phase["arguments"]["source_data"] = [loop_source]
                    if "task_description" not in phase["arguments"]:
                         phase["arguments"]["task_description"] = phase.get("goal", "Perform the required task.")

                    yield self.executor._format_sse({
                        "step": "System Correction",
                        "type": "workaround",
                        "details": {
                            "summary": "The agent's plan was inefficient. The system has automatically rewritten it to perform the analysis in a single, efficient step.",
                            "correction": {"from": original_phase, "to": phase}
                        }
                    })
                    made_change = True
                else:
                    app_logger.info(f"PLAN REWRITE SKIPPED: Task classified as 'synthesis'. Preserving loop for phase {phase.get('phase')}.")

        if made_change:
            app_logger.info(f"PLAN REWRITE (TDA_LLMTask): Final rewritten plan: {self.executor.meta_plan}")


    def _rewrite_plan_for_date_range_loops(self):
        """
        Deterministically rewrites a plan where a `TDA_DateRange` tool
        is not followed by a necessary loop, correcting a common planning flaw.
        This runs after the main plan generation and before execution.
        """
        if not self.executor.meta_plan or len(self.executor.meta_plan) < 2:
            return

        i = 0
        made_change = False
        while i < len(self.executor.meta_plan) - 1:
            current_phase = self.executor.meta_plan[i]
            next_phase = self.executor.meta_plan[i+1]

            is_date_range_phase = (
                "TDA_DateRange" in current_phase.get("relevant_tools", [])
            )
            is_missing_loop = (
                next_phase.get("type") != "loop"
            )
            
            uses_date_range_output = False
            if isinstance(next_phase.get("arguments"), dict):
                for arg_value in next_phase["arguments"].values():
                    if isinstance(arg_value, str) and arg_value == f"result_of_phase_{current_phase['phase']}":
                         uses_date_range_output = True
                         break

            if is_date_range_phase and is_missing_loop and uses_date_range_output:
                app_logger.warning(
                    f"PLAN REWRITE: Detected TDA_DateRange at phase {current_phase['phase']} "
                    f"not followed by a loop. Rewriting phase {next_phase['phase']}."
                )
                
                original_next_phase = copy.deepcopy(next_phase)

                next_phase["type"] = "loop"
                next_phase["loop_over"] = f"result_of_phase_{current_phase['phase']}"
                
                # Replace the placeholder with a loop_item reference
                for arg_name, arg_value in next_phase["arguments"].items():
                    if (isinstance(arg_value, str) and 
                        arg_value == f"result_of_phase_{current_phase['phase']}"):
                        
                        next_phase["arguments"][arg_name] = {
                            "source": "loop_item",
                            "key": "date" 
                        }
                        break

                yield self.executor._format_sse({
                    "step": "System Correction",
                    "type": "workaround",
                    "details": {
                        "summary": "The agent's plan was inefficiently structured. The system has automatically rewritten it to correctly process each item in the date range.",
                        "correction": {
                            "from": original_next_phase,
                            "to": next_phase
                        }
                    }
                })
                made_change = True
            
            i += 1

        if made_change:
            app_logger.info(f"PLAN REWRITE (Date-Range): Final rewritten plan: {self.executor.meta_plan}")

    async def generate_and_refine_plan(self, force_disable_history: bool = False, replan_context: str = None):
        """
        The main public method to generate a plan and then run all validation and
        refinement steps.
        """
        async for event in self._generate_meta_plan(
            force_disable_history=force_disable_history,
            replan_context=replan_context
        ):
            yield event
        
        async for event in self._rewrite_plan_for_multi_loop_synthesis():
            yield event
        async for event in self._rewrite_plan_for_corellmtask_loops():
            yield event
        for event in self._rewrite_plan_for_date_range_loops():
            yield event
        for event in self._validate_and_correct_plan():
            yield event
        for event in self._hydrate_plan_from_previous_turn():
            yield event
        for event in self._ensure_final_report_phase():
            yield event


        yield self.executor._format_sse({
            "step": "Strategic Meta-Plan Generated",
            "type": "plan_generated",
            "details": self.executor.meta_plan
        })

    async def _generate_meta_plan(self, force_disable_history: bool = False, replan_context: str = None):
        """The universal planner. It generates a meta-plan for ANY request."""
        prompt_obj = None
        explicit_parameters_section = ""
        
        if self.executor.active_prompt_name:
            yield self.executor._format_sse({"step": "Loading Workflow Prompt", "type": "system_message", "details": f"Loading '{self.executor.active_prompt_name}'"})
            mcp_client = self.executor.dependencies['STATE'].get('mcp_client')
            if not mcp_client: raise RuntimeError("MCP client is not connected.")
            
            prompt_def = self.executor._get_prompt_info(self.executor.active_prompt_name)

            if not prompt_def:
                raise ValueError(f"Could not find a definition for prompt '{self.executor.active_prompt_name}' in the local cache.")

            required_args = {arg['name'] for arg in prompt_def.get('arguments', []) if arg.get('required')}
            
            enriched_args = self.executor.prompt_arguments.copy()

            missing_args = {arg for arg in required_args if arg not in enriched_args or enriched_args.get(arg) is None}
            if missing_args:
                raise ValueError(
                    f"Cannot execute prompt '{self.executor.active_prompt_name}' because the following required arguments "
                    f"are missing: {missing_args}"
                )
            
            self.executor.prompt_arguments = enriched_args

            try:
                server_name = APP_CONFIG.CURRENT_MCP_SERVER_NAME
                if not server_name:
                    raise RuntimeError("MCP server name is not configured.")
                async with mcp_client.session(server_name) as temp_session:
                    prompt_obj = await load_mcp_prompt(
                        temp_session, name=self.executor.active_prompt_name, arguments=self.executor.prompt_arguments
                    )
            except Exception as e:
                app_logger.error(f"Failed to load MCP prompt '{self.executor.active_prompt_name}': {e}", exc_info=True)
                raise ValueError(f"Prompt '{self.executor.active_prompt_name}' could not be loaded from the MCP server.") from e

            if not prompt_obj: raise ValueError(f"Prompt '{self.executor.active_prompt_name}' could not be loaded.")
            
            self.executor.workflow_goal_prompt = get_prompt_text_content(prompt_obj)
            if not self.executor.workflow_goal_prompt:
                raise ValueError(f"Could not extract text content from rendered prompt '{self.executor.active_prompt_name}'.")

            param_items = [f"- {key}: {json.dumps(value)}" for key, value in self.executor.prompt_arguments.items()]
            explicit_parameters_section = (
                "\n--- EXPLICIT PARAMETERS ---\n"
                "The following parameters were explicitly provided for this prompt execution:\n"
                + "\n".join(param_items) + "\n"
            )
        else:
            self.executor.workflow_goal_prompt = self.executor.original_user_input

        call_id = str(uuid.uuid4())
        summary = f"Generating a strategic meta-plan for the goal"
        details_payload = {
            "summary": summary,
            "full_text": self.executor.workflow_goal_prompt,
            "call_id": call_id
        }
        yield self.executor._format_sse({"step": "Calling LLM for Planning", "type": "system_message", "details": details_payload})

        previous_turn_summary_str = self._create_summary_from_history(self.executor.previous_turn_data)
        
        active_prompt_context_section = ""
        if self.executor.active_prompt_name:
            active_prompt_context_section = f"\n- Active Prompt: You are currently executing the '{self.executor.active_prompt_name}' prompt. Do not call it again."

        decision_making_process_str = ""
        if APP_CONFIG.ALLOW_SYNTHESIS_FROM_HISTORY:
            decision_making_process_str = (
                "2.  **Check History First**: If the `Workflow History` contains enough information to fully answer the user's `GOAL`, your response **MUST be a single JSON object** for a one-phase plan. This plan **MUST** call the `TDA_ContextReport` tool. You **MUST** write the complete, final answer text inside the `answer_from_context` argument within that tool call. **You are acting as a planner; DO NOT use the `FINAL_ANSWER:` format.**\n\n"
                "3.  **Default to Data Gathering**: If the history is insufficient, you **MUST** create a new plan to gather the necessary data using the available tools. Your primary objective is to answer the user's `GOAL` using data from these tools."
            )
        else:
            decision_making_process_str = (
                "2.  **Data Gathering**: Your primary objective is to answer the user's `GOAL` by creating a plan to gather the necessary data using the available tools."
            )
        
        constraints_section = self.executor.dependencies['STATE'].get("constraints_context", "")

        sql_consolidation_rule_str = ""
        opt_prompts = APP_CONFIG.SQL_OPTIMIZATION_PROMPTS
        opt_tools = APP_CONFIG.SQL_OPTIMIZATION_TOOLS
        
        if opt_prompts or opt_tools:
            favored_capabilities = []
            if opt_prompts:
                favored_capabilities.extend([f"`{p}` (prompt)" for p in opt_prompts])
            if opt_tools:
                favored_capabilities.extend([f"`{t}` (tool)" for t in opt_tools])

            sql_consolidation_rule_str = (
                "**CRITICAL STRATEGY (SQL Consolidation):** Before creating a multi-step plan, first consider if the user's entire request can be fulfilled with a single, consolidated SQL query. "
                "If the goal involves a sequence of filtering, joining, or looking up data (e.g., \"find all tables in a database that contains X\"), you **MUST** favor using one of the following capabilities "
                f"to write a single statement that performs the entire operation: {', '.join(favored_capabilities)}. "
                "Avoid creating multiple `base_...List` steps if a single query would be more efficient."
            )

        reporting_tool_name_injection = ""
        if self.executor.source == 'prompt_library':
            reporting_tool_name_injection = "TDA_ComplexPromptReport"
        else:
            reporting_tool_name_injection = "TDA_FinalReport"
        
        planning_prompt = WORKFLOW_META_PLANNING_PROMPT.format(
            workflow_goal=self.executor.workflow_goal_prompt,
            explicit_parameters_section=explicit_parameters_section,
            original_user_input=self.executor.original_user_input,
            turn_action_history=previous_turn_summary_str,
            execution_depth=self.executor.execution_depth,
            active_prompt_context_section=active_prompt_context_section,
            decision_making_process=decision_making_process_str,
            mcp_system_name=APP_CONFIG.MCP_SYSTEM_NAME,
            replan_instructions=replan_context or "",
            constraints_section=constraints_section,
            sql_consolidation_rule=sql_consolidation_rule_str,
            reporting_tool_name=reporting_tool_name_injection
        )
        
        yield self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
        response_text, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
            prompt=planning_prompt, 
            reason=f"Generating a strategic meta-plan for the goal: '{self.executor.workflow_goal_prompt[:100]}'",
            disabled_history=force_disable_history,
            active_prompt_name_for_filter=self.executor.active_prompt_name,
            source=self.executor.source
        )
        yield self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")

        app_logger.info(
            f"\n--- Meta-Planner Turn ---\n"
            f"** CONTEXT **\n"
            f"Original User Input: {self.executor.original_user_input}\n"
            f"Execution Depth: {self.executor.execution_depth}\n"
            f"Previous Turn History Summary (for prompt):\n{previous_turn_summary_str}\n"
            f"** GENERATED PLAN **\n{response_text}\n"
            f"-------------------------"
        )

        updated_session = session_manager.get_session(self.executor.session_id)
        if updated_session:
            yield self.executor._format_sse({ "statement_input": input_tokens, "statement_output": output_tokens, "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0), "call_id": call_id }, "token_update")
        
        try:
            json_str = response_text
            if response_text.strip().startswith("```json"):
                match = re.search(r"```json\s*\n(.*?)\n\s*```", response_text, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()

            plan_object = json.loads(json_str)
            
            if isinstance(plan_object, dict) and plan_object.get("plan_type") == "conversational":
                self.executor.is_conversational_plan = True
                self.executor.temp_data_holder = plan_object.get("response", "I'm sorry, I don't have a response for that.")
                yield self.executor._format_sse({"step": "Conversational Response Identified", "type": "system_message", "details": self.executor.temp_data_holder})
                return

            plan_object_is_dict = isinstance(plan_object, dict)
            is_direct_tool = plan_object_is_dict and "tool_name" in plan_object
            is_direct_prompt = plan_object_is_dict and ("prompt_name" in plan_object or "executable_prompt" in plan_object)

            if is_direct_tool or is_direct_prompt:
                yield self.executor._format_sse({
                    "step": "System Correction",
                    "type": "workaround",
                    "details": "Planner returned a direct action instead of a plan. System is correcting the format."
                })
                
                phase = {
                    "phase": 1,
                    "goal": f"Execute the action for the user's request: '{self.executor.original_user_input}'",
                    "arguments": plan_object.get("arguments", {})
                }
                
                if is_direct_tool:
                    phase["relevant_tools"] = [plan_object["tool_name"]]
                elif is_direct_prompt:
                    phase["executable_prompt"] = plan_object.get("prompt_name") or plan_object.get("executable_prompt")
                
                self.executor.meta_plan = [phase]
            elif not isinstance(plan_object, list) or not plan_object:
                raise ValueError("LLM response for meta-plan was not a non-empty list.")
            else:
                self.executor.meta_plan = plan_object

        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Failed to generate a valid meta-plan from the LLM. Response: {response_text}. Error: {e}")

        if self.executor.active_prompt_name and self.executor.meta_plan:
            if len(self.executor.meta_plan) > 1 or any(phase.get("type") == "loop" for phase in self.executor.meta_plan):
                self.executor.is_complex_prompt_workflow = True
                app_logger.info(f"'{self.executor.active_prompt_name}' has been qualified as a complex prompt workflow based on the generated plan.")
