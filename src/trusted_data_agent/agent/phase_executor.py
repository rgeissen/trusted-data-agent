# trusted_data_agent/agent/phase_executor.py
import re
import json
import logging
import copy
import uuid
from typing import TYPE_CHECKING, Tuple, Dict, Any, List
from abc import ABC, abstractmethod

from trusted_data_agent.core import session_manager
from trusted_data_agent.mcp import adapter as mcp_adapter
from trusted_data_agent.core.config import APP_CONFIG, AppConfig
from trusted_data_agent.agent.prompts import (
    ERROR_RECOVERY_PROMPT,
    WORKFLOW_TACTICAL_PROMPT,
    TACTICAL_SELF_CORRECTION_PROMPT,
    TACTICAL_SELF_CORRECTION_PROMPT_COLUMN_ERROR,
    TACTICAL_SELF_CORRECTION_PROMPT_TABLE_ERROR,
)
from trusted_data_agent.agent import orchestrators
from trusted_data_agent.agent.response_models import CanonicalResponse

if TYPE_CHECKING:
    from trusted_data_agent.agent.executor import PlanExecutor, DefinitiveToolError


app_logger = logging.getLogger("quart.app")


DEFINITIVE_TOOL_ERRORS = {
    "Invalid query": "The generated query was invalid and could not be run against the database.",
    "3523": "The user does not have the necessary permissions for the requested object."
}

RECOVERABLE_TOOL_ERRORS = {
    "table_not_found": r"Object '([\w\.]+)' does not exist",
    "column_not_found": r"Column '(\w+)' does not exist"
}

class CorrectionStrategy(ABC):
    """Abstract base class for all self-correction strategies."""

    def __init__(self, executor: 'PlanExecutor'):
        self.executor = executor

    @abstractmethod
    def can_handle(self, error_data_str: str) -> bool:
        """Determines if this strategy can handle the given error."""
        pass

    @abstractmethod
    async def generate_correction(self, failed_action: Dict[str, Any], error_result: Dict[str, Any]) -> Tuple[Dict | None, List]:
        """Generates a corrected action or concludes the task."""
        pass

    async def _call_correction_llm(self, prompt: str, reason: str, system_prompt_override: str, failed_action: Dict[str, Any]) -> Tuple[Dict | None, List]:
        """A helper method to standardize the LLM call for correction."""
        events = []
        call_id = str(uuid.uuid4())
        events.append(self.executor._format_sse({"step": "Calling LLM for Self-Correction", "type": "system_message", "details": {"summary": reason, "call_id": call_id}}))
        events.append(self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update"))
        
        response_str, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
            prompt=prompt,
            reason=reason,
            system_prompt_override=system_prompt_override,
            raise_on_error=False,
            source=self.executor.source
        )
        events.append(self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update"))
        
        updated_session = session_manager.get_session(self.executor.session_id)
        if updated_session:
            events.append(self.executor._format_sse({
                "statement_input": input_tokens, "statement_output": output_tokens,
                "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0),
                "call_id": call_id
            }, "token_update"))

        if "FINAL_ANSWER:" in response_str:
            app_logger.info("Self-correction resulted in a FINAL_ANSWER. Halting retries.")
            final_answer_text = response_str.split("FINAL_ANSWER:", 1)[1].strip()
            return {"FINAL_ANSWER": final_answer_text}, events

        try:
            json_match = re.search(r"```json\s*\n(.*?)\n\s*```|(\{.*\})", response_str, re.DOTALL)
            if not json_match: raise json.JSONDecodeError("No JSON object found", response_str, 0)
            
            json_str = json_match.group(1) or json_match.group(2)
            if not json_str: raise json.JSONDecodeError("Extracted JSON is empty", response_str, 0)
            
            corrected_data = json.loads(json_str.strip())

            if "prompt_name" in corrected_data and "arguments" in corrected_data:
                events.append(self.executor._format_sse({"step": "System Self-Correction", "type": "workaround", "details": {"summary": f"LLM proposed switching to prompt '{corrected_data['prompt_name']}'.", "details": corrected_data}}))
                return corrected_data, events

            if "tool_name" in corrected_data and "arguments" in corrected_data:
                events.append(self.executor._format_sse({"step": "System Self-Correction", "type": "workaround", "details": {"summary": f"LLM proposed retrying with tool '{corrected_data['tool_name']}'.", "details": corrected_data}}))
                return corrected_data, events
            
            new_args = corrected_data.get("arguments", corrected_data)
            if isinstance(new_args, dict):
                corrected_action = {**failed_action, "arguments": new_args}
                events.append(self.executor._format_sse({"step": "System Self-Correction", "type": "workaround", "details": {"summary": "LLM proposed new arguments.", "details": new_args}}))
                return corrected_action, events
            
        except (json.JSONDecodeError, TypeError):
            events.append(self.executor._format_sse({"step": "System Self-Correction", "type": "error", "details": {"summary": "LLM failed to provide a valid JSON correction.", "details": response_str}}))

        return None, events

class TableNotFoundStrategy(CorrectionStrategy):
    """Handles errors where a specified table does not exist."""
    def can_handle(self, error_data_str: str) -> bool:
        return bool(re.search(RECOVERABLE_TOOL_ERRORS["table_not_found"], error_data_str, re.IGNORECASE))

    async def generate_correction(self, failed_action: Dict[str, Any], error_result: Dict[str, Any]) -> Tuple[Dict | None, List]:
        error_data_str = str(error_result.get('data', ''))
        table_error_match = re.search(RECOVERABLE_TOOL_ERRORS["table_not_found"], error_data_str, re.IGNORECASE)
        invalid_table = table_error_match.group(1)
        invalid_table_name_only = invalid_table.split('.')[-1]
        failed_args = failed_action.get("arguments", {})
        db_name = failed_args.get("database_name", "the specified database")
        
        app_logger.warning(f"Detected recoverable 'table_not_found' error for table: {invalid_table}")
        
        prompt = TACTICAL_SELF_CORRECTION_PROMPT_TABLE_ERROR.format(
            user_question=self.executor.original_user_input,
            tool_name=failed_action.get("tool_name"),
            failed_arguments=json.dumps(failed_args),
            invalid_table_name=invalid_table_name_only,
            database_name=db_name,
            tools_context=self.executor.dependencies['STATE'].get('tools_context', ''),
            prompts_context=self.executor.dependencies['STATE'].get('prompts_context', '')
        )
        reason = f"Fact-based recovery for non-existent table '{invalid_table_name_only}'"
        system_prompt = "You are an expert troubleshooter. Follow the recovery directives precisely."
        
        return await self._call_correction_llm(prompt, reason, system_prompt, failed_action)

class ColumnNotFoundStrategy(CorrectionStrategy):
    """Handles errors where a specified column does not exist."""
    def can_handle(self, error_data_str: str) -> bool:
        return bool(re.search(RECOVERABLE_TOOL_ERRORS["column_not_found"], error_data_str, re.IGNORECASE))

    async def generate_correction(self, failed_action: Dict[str, Any], error_result: Dict[str, Any]) -> Tuple[Dict | None, List]:
        error_data_str = str(error_result.get('data', ''))
        column_error_match = re.search(RECOVERABLE_TOOL_ERRORS["column_not_found"], error_data_str, re.IGNORECASE)
        invalid_column = column_error_match.group(1)
        
        app_logger.warning(f"Detected recoverable 'column_not_found' error for column: {invalid_column}")
        
        prompt = TACTICAL_SELF_CORRECTION_PROMPT_COLUMN_ERROR.format(
            user_question=self.executor.original_user_input,
            tool_name=failed_action.get("tool_name"),
            failed_arguments=json.dumps(failed_action.get("arguments", {})),
            invalid_column_name=invalid_column,
            tools_context=self.executor.dependencies['STATE'].get('tools_context', ''),
            prompts_context=self.executor.dependencies['STATE'].get('prompts_context', '')
        )
        reason = f"Fact-based recovery for non-existent column '{invalid_column}'"
        system_prompt = "You are an expert troubleshooter. Follow the recovery directives precisely."

        return await self._call_correction_llm(prompt, reason, system_prompt, failed_action)

class GenericCorrectionStrategy(CorrectionStrategy):
    """The default fallback strategy for any other recoverable error."""
    def can_handle(self, error_data_str: str) -> bool:
        return True # It's the fallback, so it can always handle the error.

    async def generate_correction(self, failed_action: Dict[str, Any], error_result: Dict[str, Any]) -> Tuple[Dict | None, List]:
        tool_name = failed_action.get("tool_name")
        tool_def = self.executor.dependencies['STATE'].get('mcp_tools', {}).get(tool_name)
        if not tool_def:
            return None, []

        prompt = TACTICAL_SELF_CORRECTION_PROMPT.format(
            tool_definition=json.dumps(vars(tool_def), default=str),
            failed_command=json.dumps(failed_action),
            error_message=json.dumps(error_result.get('data', 'No error data.')),
            user_question=self.executor.original_user_input,
            tools_context=self.executor.dependencies['STATE'].get('tools_context', ''),
            prompts_context=self.executor.dependencies['STATE'].get('prompts_context', '')
        )
        reason = f"Generic self-correction for failed tool call: {tool_name}"
        system_prompt = "You are an expert troubleshooter. Follow the recovery directives precisely."

        return await self._call_correction_llm(prompt, reason, system_prompt, failed_action)

class CorrectionHandler:
    """Manages and executes the appropriate correction strategy."""
    def __init__(self, executor: 'PlanExecutor'):
        self.strategies = [
            TableNotFoundStrategy(executor),
            ColumnNotFoundStrategy(executor),
            GenericCorrectionStrategy(executor)
        ]

    async def attempt_correction(self, failed_action: Dict[str, Any], error_result: Dict[str, Any]) -> Tuple[Dict | None, List]:
        error_data_str = str(error_result.get('data', ''))
        
        for strategy in self.strategies:
            if strategy.can_handle(error_data_str):
                app_logger.info(f"Using correction strategy: {strategy.__class__.__name__}")
                return await strategy.generate_correction(failed_action, error_result)
        
        return None, []


class PhaseExecutor:
    """
    Handles the tactical execution of a single phase of a plan. It is instantiated
    by the PlanExecutor (Orchestrator) and maintains a reference to it for state
    and helper method access.
    """
    def __init__(self, executor: 'PlanExecutor'):
        self.executor = executor

    async def execute_phase(self, phase: dict):
        """
        The main public entry point to execute a single phase. It determines the
        phase type and delegates to the appropriate specialized execution method.
        """
        if phase.get("type") == "loop":
            async for event in self._execute_looping_phase(phase):
                yield event
        else:
            async for event in self._execute_standard_phase(phase):
                yield event

    def _extract_loop_items(self, source_phase_key: str) -> list:
        """
        Intelligently extracts the list of items to iterate over from a previous phase's results.
        It now correctly handles and flattens results from a previous looping phase.
        """
        if source_phase_key not in self.executor.workflow_state:
            app_logger.warning(f"Loop source '{source_phase_key}' not found in workflow state.")
            return []

        source_data = self.executor.workflow_state[source_phase_key]

        if isinstance(source_data, list) and all(isinstance(item, dict) and 'results' in item for item in source_data):
            flattened_results = []
            for tool_result in source_data:
                if isinstance(tool_result.get('results'), list):
                    flattened_results.extend(tool_result['results'])
            
            if flattened_results:
                app_logger.info(f"Extracted and flattened {len(flattened_results)} items from previous loop phase '{source_phase_key}'.")
                return flattened_results

        def find_results_list(data):
            if isinstance(data, list):
                for item in data:
                    found = find_results_list(item)
                    if found is not None: return found
            elif isinstance(data, dict):
                if 'results' in data and isinstance(data['results'], list):
                    return data['results']
                for value in data.values():
                    found = find_results_list(value)
                    if found is not None: return found
            return None

        items = find_results_list(source_data)
        
        if items is None:
            app_logger.warning(f"Could not find a 'results' list in '{source_phase_key}' using fallback. Returning empty list.")
            return []
            
        return items

    async def _execute_looping_phase(self, phase: dict):
        """
        Orchestrates the execution of a looping phase. It uses a "fast path" for simple,
        repetitive tool calls to improve performance, and a standard, LLM-driven path
        for complex or synthesis-based loops.
        """
        phase_goal = phase.get("goal", "No goal defined.")
        phase_num = phase.get("phase", self.executor.current_phase_index + 1)
        loop_over_key = phase.get("loop_over")
        relevant_tools = phase.get("relevant_tools", [])

        yield self.executor._format_sse({
            "step": f"Starting Plan Phase {phase_num}/{len(self.executor.meta_plan)}",
            "type": "phase_start",
            "details": {
                "phase_num": phase_num,
                "total_phases": len(self.executor.meta_plan),
                "goal": phase_goal,
                "phase_details": phase,
                "execution_depth": self.executor.execution_depth
            }
        })

        self.executor.current_loop_items = self._extract_loop_items(loop_over_key)
        
        if not self.executor.current_loop_items:
            yield self.executor._format_sse({"step": "Skipping Empty Loop", "type": "system_message", "details": f"No items found from '{loop_over_key}' to loop over."})
            yield self.executor._format_sse({
                "step": f"Ending Plan Phase {phase_num}/{len(self.executor.meta_plan)}",
                "type": "phase_end",
                "details": {"phase_num": phase_num, "total_phases": len(self.executor.meta_plan), "status": "skipped"}
            })
            return

        is_fast_path_candidate = (
            len(relevant_tools) == 1 and 
            relevant_tools[0] not in ["TDA_LLMTask", "TDA_Charting", "TDA_FinalReport", "TDA_ComplexPromptReport"]
        )

        if is_fast_path_candidate:
            tool_name = relevant_tools[0]
            
            raw_phase_args = phase.get("arguments", {})
            args_to_prune = [
                arg_name for arg_name, arg_value in raw_phase_args.items()
                if arg_value == loop_over_key
            ]
            if args_to_prune:
                modified_args = raw_phase_args.copy()
                for arg_name in args_to_prune:
                    app_logger.info(f"System Correction: Pruning redundant loop argument '{arg_name}' from phase '{phase_goal}'.")
                    del modified_args[arg_name]
                
                phase['arguments'] = modified_args
                
                yield self.executor._format_sse({
                    "step": "System Correction",
                    "type": "workaround",
                    "details": {
                        "summary": "The agent's plan contained a redundant argument in a loop. The system has automatically removed it to prevent an error.",
                        "correction_type": "redundant_argument_pruning",
                        "pruned_arguments": args_to_prune
                    }
                })
            
            tool_scope = self.executor.dependencies['STATE'].get('tool_scopes', {}).get(tool_name)

            if tool_scope == 'column':
                yield self.executor._format_sse({"step": "Plan Optimization", "type": "plan_optimization", "details": f"FASTPATH Data Expansion: Preparing column-level iteration for '{tool_name}'."})
                
                yield self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
                tool_constraints, constraint_events = await self._get_tool_constraints(tool_name)
                for event in constraint_events:
                    yield event
                yield self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")

                required_type = tool_constraints.get("dataType")

                expanded_loop_items = []
                tables_to_process = self.executor.current_loop_items
                db_name = phase.get("arguments", {}).get("database_name")

                if not db_name:
                    raise RuntimeError(f"Cannot perform column-level FASTPATH for tool '{tool_name}' because 'database_name' is missing from the phase arguments.")

                yield self.executor._format_sse({"target": "db", "state": "busy"}, "status_indicator_update")
                for table_item in tables_to_process:
                    table_name = next((v for k, v in table_item.items() if k in AppConfig.ARGUMENT_SYNONYM_MAP.get('object_name', {})), None)
                    if not table_name: continue

                    args_for_col_tool = {'database_name': db_name}
                    for synonym in AppConfig.ARGUMENT_SYNONYM_MAP.get('object_name', {}):
                        args_for_col_tool[synonym] = table_name
                    
                    cols_command = {"tool_name": "base_columnDescription", "arguments": args_for_col_tool}
                    cols_result, _, _ = await mcp_adapter.invoke_mcp_tool(self.executor.dependencies['STATE'], cols_command, session_id=self.executor.session_id)

                    if cols_result and isinstance(cols_result, dict) and cols_result.get('status') == 'success' and cols_result.get('results'):
                        columns_metadata = cols_result.get('results', [])
                        for col_info in columns_metadata:
                            col_name = col_info.get("ColumnName")
                            if not col_name: continue
                            
                            col_type = next((v for k, v in col_info.items() if "type" in k.lower()), "").upper()
                            if required_type and col_type != "UNKNOWN":
                                is_numeric = any(t in col_type for t in ["INT", "NUMERIC", "DECIMAL", "FLOAT", "BYTEINT", "SMALLINT", "BIGINT"])
                                is_char = any(t in col_type for t in ["CHAR", "VARCHAR", "TEXT", "DATE", "TIMESTAMP"])
                                if (required_type == "numeric" and not is_numeric) or (required_type == "character" and not is_char):
                                    skip_details = f"Tool '{tool_name}' requires a {required_type} column, but '{col_name}' is '{col_type}'. Skipping."
                                    yield self.executor._format_sse({"step": "Skipping Incompatible Column", "type": "plan_optimization", "details": skip_details})
                                    continue
                            
                            expanded_loop_items.append({**table_item, "ColumnName": col_name})
                    else:
                        app_logger.warning(f"Data expansion: Failed to get columns for table '{table_name}'. Tool `base_columnDescription` may have failed. Result: {cols_result}")
                
                yield self.executor._format_sse({"target": "db", "state": "idle"}, "status_indicator_update")
                self.executor.current_loop_items = expanded_loop_items
                
                if not self.executor.current_loop_items:
                    yield self.executor._format_sse({"step": "Skipping Empty Loop", "type": "system_message", "details": f"No compatible columns found for '{tool_name}'."})
                    yield self.executor._format_sse({"step": f"Ending Plan Phase {phase_num}/{len(self.executor.meta_plan)}", "type": "phase_end", "details": {"phase_num": phase_num, "total_phases": len(self.executor.meta_plan), "status": "skipped"}})
                    return
            
            yield self.executor._format_sse({
                "step": "Plan Optimization", 
                "type": "plan_optimization",
                "details": f"FASTPATH enabled for tool loop: '{tool_name}'"
            })
            
            static_phase_args = phase.get("arguments", {})
            
            all_loop_results = []
            yield self.executor._format_sse({"target": "db", "state": "busy"}, "status_indicator_update")
            for i, item in enumerate(self.executor.current_loop_items):
                yield self.executor._format_sse({"step": f"Processing Loop Item {i+1}/{len(self.executor.current_loop_items)}", "type": "system_message", "details": item})
                
                item_data = item if isinstance(item, dict) else {}
                resolved_item_args = self.executor._resolve_arguments(static_phase_args, loop_item=item_data)
                merged_args = {**resolved_item_args, **item_data}
                
                tool_def = self.executor.dependencies['STATE'].get('mcp_tools', {}).get(tool_name)
                pruned_args = merged_args.copy()
                
                if tool_def and hasattr(tool_def, 'args') and isinstance(tool_def.args, dict):
                    official_tool_args = set(tool_def.args.keys())
                    
                    pruned_args = {
                        key: value for key, value in merged_args.items()
                        if key in official_tool_args
                    }
                    
                    if len(pruned_args) < len(merged_args):
                        pruned_keys = set(merged_args.keys()) - set(pruned_args.keys())
                        app_logger.info(f"Proactively pruned superfluous arguments for tool '{tool_name}': {pruned_keys}")
                        # --- MODIFICATION START: Add System Correction Event ---
                        yield self.executor._format_sse({
                            "step": "System Correction",
                            "type": "workaround",
                            "details": {
                                "summary": "Automatically pruned superfluous arguments to prevent a tool execution error.",
                                "correction_type": "proactive_argument_pruning",
                                "pruned_arguments": list(pruned_keys),
                                "tool_name": tool_name
                            }
                        })
                        # --- MODIFICATION END ---
                
                command = {"tool_name": tool_name, "arguments": pruned_args}

                async for event in self._execute_tool(command, phase, is_fast_path=True):
                    yield event
                
                enriched_tool_output = copy.deepcopy(self.executor.last_tool_output)
                if (isinstance(enriched_tool_output, dict) and 
                    enriched_tool_output.get("status") == "success" and 
                    isinstance(item, dict)):
                    
                    if 'results' in enriched_tool_output and isinstance(enriched_tool_output['results'], list):
                        for result_row in enriched_tool_output['results']:
                            if isinstance(result_row, dict):
                                for key, value in item.items():
                                    if key not in result_row:
                                        result_row[key] = value
                
                self.executor.turn_action_history.append({"action": command, "result": enriched_tool_output})
                all_loop_results.append(enriched_tool_output)

            yield self.executor._format_sse({"target": "db", "state": "idle"}, "status_indicator_update")
            
            phase_result_key = f"result_of_phase_{phase_num}"
            self.executor.workflow_state[phase_result_key] = all_loop_results
            self.executor._add_to_structured_data(all_loop_results)
            self.executor.last_tool_output = all_loop_results

        else: 
            self.executor.is_in_loop = True
            self.executor.processed_loop_items = []
            
            for i, item in enumerate(self.executor.current_loop_items):
                yield self.executor._format_sse({"step": f"Processing Loop Item {i+1}/{len(self.executor.current_loop_items)}", "type": "system_message", "details": item})
                
                try:
                    async for event in self._execute_standard_phase(phase, is_loop_iteration=True, loop_item=item):
                        yield event
                except Exception as e:
                    error_message = f"Error processing item {item}: {e}"
                    app_logger.error(error_message, exc_info=True)
                    error_result = {
                        "status": "error", 
                        "item": item, 
                        "error_message": {
                            "summary": f"An error occurred while processing the item.",
                            "details": str(e)
                        }
                    }
                    self.executor._add_to_structured_data(error_result)
                    yield self.executor._format_sse({"step": "Loop Item Failed", "details": error_result, "type": "error"}, "tool_result")

                self.executor.processed_loop_items.append(item)

            self.executor.is_in_loop = False
            self.executor.current_loop_items = []
            self.executor.processed_loop_items = []

        yield self.executor._format_sse({
            "step": f"Ending Plan Phase {phase_num}/{len(self.executor.meta_plan)}",
            "type": "phase_end",
            "details": {"phase_num": phase_num, "total_phases": len(self.executor.meta_plan), "status": "completed"}
        })

    def _is_numeric(self, value: any) -> bool:
        """Checks if a value can be reliably converted to a number."""
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value.replace(',', ''))
                return True
            except (ValueError, TypeError):
                return False
        return False

    async def _execute_standard_phase(self, phase: dict, is_loop_iteration: bool = False, loop_item: dict = None):
        """Executes a single, non-looping phase or a single iteration of a complex loop."""
        phase_goal = phase.get("goal", "No goal defined.")
        phase_num = phase.get("phase", self.executor.current_phase_index + 1)
        relevant_tools = phase.get("relevant_tools", [])
        strategic_args = self.executor._resolve_arguments(phase.get("arguments", {}), loop_item=loop_item)
        executable_prompt = phase.get("executable_prompt")

        if not is_loop_iteration:
            yield self.executor._format_sse({
                "step": f"Starting Plan Phase {phase_num}/{len(self.executor.meta_plan)}",
                "type": "phase_start",
                "details": {
                    "phase_num": phase_num,
                    "total_phases": len(self.executor.meta_plan),
                    "goal": phase_goal,
                    "phase_details": phase,
                    "execution_depth": self.executor.execution_depth
                }
            })
        
        if len(relevant_tools) > 1 and not is_loop_iteration:
            yield self.executor._format_sse({
                "step": "System Correction",
                "type": "workaround",
                "details": f"Multi-tool phase detected. The agent will execute {len(relevant_tools)} tools sequentially."
            })
            
            all_phase_results = []
            for tool_name in relevant_tools:
                fast_path_action = {"tool_name": tool_name, "arguments": strategic_args}
                async for event in self._execute_action_with_orchestrators(fast_path_action, phase):
                    yield event
                all_phase_results.append(self.executor.last_tool_output)
            
            phase_result_key = f"result_of_phase_{phase_num}"
            self.executor.workflow_state[phase_result_key] = all_phase_results
            self.executor._add_to_structured_data(all_phase_results)
            self.executor.last_tool_output = all_phase_results

            yield self.executor._format_sse({
                "step": f"Ending Plan Phase {phase_num}/{len(self.executor.meta_plan)}",
                "type": "phase_end",
                "details": {"phase_num": phase_num, "total_phases": len(self.executor.meta_plan), "status": "completed"}
            })
            return
        elif len(relevant_tools) > 1 and is_loop_iteration:
             yield self.executor._format_sse({
                "step": "System Correction",
                "type": "workaround",
                "details": f"Multi-tool phase detected. The agent will execute {len(relevant_tools)} tools sequentially for each item."
            })
             
             all_loop_item_results = []
             for tool_name in relevant_tools:
                item_args = {}
                if isinstance(loop_item, dict):
                    for key, value in loop_item.items():
                        item_args[key] = value

                merged_args = {**strategic_args, **item_args}
                fast_path_action = {"tool_name": tool_name, "arguments": merged_args}

                async for event in self._execute_action_with_orchestrators(fast_path_action, phase):
                    yield event
                all_loop_item_results.append(self.executor.last_tool_output)
             
             phase_result_key = f"result_of_phase_{phase_num}"
             if phase_result_key not in self.executor.workflow_state:
                 self.executor.workflow_state[phase_result_key] = []

             self.executor.workflow_state[phase_result_key].extend(all_loop_item_results)
             self.executor._add_to_structured_data(all_loop_item_results)
             self.executor.last_tool_output = all_loop_item_results
             return

        tool_name = relevant_tools[0] if len(relevant_tools) == 1 else None
        
        is_fast_path_candidate = False
        if tool_name:
            all_tools = self.executor.dependencies['STATE'].get('mcp_tools', {})
            tool_def = all_tools.get(tool_name)
            if tool_def:
                required_args = {name for name, details in (tool_def.args.items() if hasattr(tool_def, 'args') and isinstance(tool_def.args, dict) else {}) if details.get('required')}
                if required_args.issubset(strategic_args.keys()):
                    is_fast_path_candidate = True
        
        if is_fast_path_candidate:
            yield self.executor._format_sse({
                "step": "Plan Optimization", 
                "type": "plan_optimization",
                "details": f"FASTPATH initiated for '{tool_name}'."
            })

            fast_path_action = {"tool_name": tool_name, "arguments": strategic_args}
            
            if tool_name == "TDA_LLMTask" and is_loop_iteration and loop_item:
                modified_args = fast_path_action["arguments"].copy()
                task_desc = modified_args.get("task_description", "")
                loop_item_str = json.dumps(loop_item)
                
                modified_args["task_description"] = (
                    f"{task_desc}\n\n"
                    f"CRITICAL CONTEXT: You MUST focus your response on the following item provided from the loop: {loop_item_str}"
                )
                
                fast_path_action["arguments"] = modified_args
                app_logger.info(f"Injected loop context into TDA_LLMTask description for item: {loop_item_str}")

            async for event in self._execute_action_with_orchestrators(fast_path_action, phase):
                yield event
            
            call_id_for_completion = None
            if isinstance(self.executor.last_tool_output, dict):
                call_id_for_completion = self.executor.last_tool_output.get("metadata", {}).get("call_id")

            completion_event_payload = {"target": "context", "state": "processing_complete"}
            if call_id_for_completion:
                completion_event_payload["call_id"] = call_id_for_completion

            yield self.executor._format_sse(completion_event_payload, "context_state_update")

            if not is_loop_iteration:
                yield self.executor._format_sse({
                    "step": f"Ending Plan Phase {phase_num}/{len(self.executor.meta_plan)}",
                    "type": "phase_end",
                    "details": {"phase_num": phase_num, "total_phases": len(self.executor.meta_plan), "status": "completed"}
                })
            return

        phase_attempts = 0
        max_phase_attempts = 5
        tactical_call_id = None
        while True:
            phase_attempts += 1
            if phase_attempts > max_phase_attempts:
                app_logger.error(f"Phase '{phase_goal}' failed after {max_phase_attempts} attempts. Attempting LLM recovery.")
                async for event in self._recover_from_phase_failure(phase_goal):
                    yield event
                return 

            enriched_args, enrich_events, _ = self._enrich_arguments_from_history(relevant_tools)
            
            for event in enrich_events:
                self.executor.events_to_yield.append(event)
            
            tactical_call_id = str(uuid.uuid4())
            yield self.executor._format_sse({"step": "Calling LLM for Tactical Action", "type": "system_message", "details": {"summary": f"Deciding next action for phase goal: '{phase_goal}'", "call_id": tactical_call_id}})
            yield self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
            
            next_action, input_tokens, output_tokens = await self._get_next_tactical_action(
                phase_goal, relevant_tools, enriched_args, strategic_args, executable_prompt
            )
            
            yield self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")
            
            current_action_str = json.dumps(next_action, sort_keys=True)
            if current_action_str == self.executor.last_action_str:
                app_logger.warning(f"LOOP DETECTED: Repeating action: {current_action_str}")
                self.executor.last_failed_action_info = "Your last attempt failed because it was an exact repeat of the previous failed action. You MUST choose a different tool or different arguments."
                yield self.executor._format_sse({"step": "System Error", "details": "Repetitive action detected.", "type": "error"}, "tool_result")
                self.executor.last_action_str = None 
                continue
            self.executor.last_action_str = current_action_str
            
            if self.executor.events_to_yield:
                for event in self.executor.events_to_yield: yield event
                self.executor.events_to_yield = []

            updated_session = session_manager.get_session(self.executor.session_id)
            if updated_session:
                yield self.executor._format_sse({ "statement_input": input_tokens, "statement_output": output_tokens, "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0), "call_id": tactical_call_id }, "token_update")

            if isinstance(next_action, str) and next_action == "SYSTEM_ACTION_COMPLETE":
                self.executor.state = self.executor.AgentState.SUMMARIZING
                return

            if not isinstance(next_action, dict):
                raise RuntimeError(f"Tactical LLM failed to provide a valid action. Received: {next_action}")

            async for event in self._execute_action_with_orchestrators(next_action, phase):
                yield event
            
            is_standard_success = (isinstance(self.executor.last_tool_output, dict) and self.executor.last_tool_output.get("status") == "success")
            is_chart_success = (isinstance(self.executor.last_tool_output, dict) and self.executor.last_tool_output.get("type") == "chart")

            if self.executor.last_tool_output and (is_standard_success or is_chart_success):
                if next_action.get("tool_name") == "TDA_Charting":
                    is_valid_chart = True
                    spec = self.executor.last_tool_output.get("spec", {})
                    options = spec.get("options", {})
                    mapping_keys = ['xField', 'yField', 'seriesField', 'angleField', 'colorField']
                    if not any(key in options for key in mapping_keys):
                        is_valid_chart = False
                        self.executor.last_failed_action_info = "The last attempt to create a chart failed because the 'mapping' argument was incorrect or missing. You MUST provide a valid mapping with the correct keys (e.g., 'angle', 'color')."
                    
                    if is_valid_chart:
                        mapping = next_action.get("arguments", {}).get("mapping", {})
                        data = next_action.get("arguments", {}).get("data", [])
                        if data and mapping:
                            first_row = data[0]
                            numeric_roles = ['angle', 'y_axis', 'value']
                            for role, column_name in mapping.items():
                                if role.lower() in numeric_roles:
                                    if column_name in first_row and not self._is_numeric(first_row[column_name]):
                                        is_valid_chart = False
                                        self.executor.last_failed_action_info = f"The last attempt failed. You mapped the non-numeric column '{column_name}' to the '{role}' role, which requires a number. You MUST map a numeric column to this role."
                                        break
                    
                    if not is_valid_chart:
                        app_logger.warning(f"Silent chart failure detected. Reason: {self.executor.last_failed_action_info}")
                        continue
                
                self.executor.last_action_str = None
                break 
            else:
                app_logger.warning(f"Action failed. Attempt {phase_attempts}/{max_phase_attempts} for phase.")
        
        yield self.executor._format_sse(
            {"target": "context", "state": "processing_complete", "call_id": tactical_call_id}, 
            "context_state_update"
        )
        if not is_loop_iteration:
            yield self.executor._format_sse({
                "step": f"Ending Plan Phase {phase_num}/{len(self.executor.meta_plan)}",
                "type": "phase_end",
                "details": {"phase_num": phase_num, "total_phases": len(self.executor.meta_plan), "status": "completed"}
            })

    async def _execute_action_with_orchestrators(self, action: dict, phase: dict):
        """
        A wrapper that runs pre-flight checks (orchestrators) before executing a tool.
        These orchestrators act as a safety net for common planning mistakes.
        """
        tool_name = action.get("tool_name")
        prompt_name = action.get("prompt_name")

        if not tool_name and not prompt_name:
            raise ValueError("Action from tactical LLM is missing a 'tool_name' or 'prompt_name'.")

        if prompt_name:
            yield self.executor._format_sse({
                "step": "Prompt Execution Granted",
                "details": f"Executing prompt '{prompt_name}' as a sub-task.",
                "type": "workaround"
            })
            async for event in self.executor._run_sub_prompt(prompt_name, action.get("arguments", {})):
                yield event
            return

        is_range_candidate, date_param_name, tool_supports_range = self._is_date_query_candidate(action)

        is_orchestrator_target = (
            is_range_candidate and
            not tool_supports_range and
            tool_name not in ["TDA_DateRange", "TDA_CurrentDate"]
        )

        if is_orchestrator_target:
            yield self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
            async for event in self._classify_date_query_type(): yield event
            yield self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")

            if self.executor.temp_data_holder and self.executor.temp_data_holder.get('type') == 'range':
                async for event in orchestrators.execute_date_range_orchestrator(
                    self.executor, action, date_param_name, self.executor.temp_data_holder.get('phrase'), phase
                ):
                    yield event
                return

        tool_scope = self.executor.dependencies['STATE'].get('tool_scopes', {}).get(tool_name)
        has_column_arg = "column_name" in action.get("arguments", {})
        if tool_scope == 'column' and not has_column_arg:
             async for event in orchestrators.execute_column_iteration(self.executor, action):
                 yield event
             return
        
        async for event in self._execute_tool(action, phase):
            yield event

    async def _proactively_refine_arguments(self, action: dict, phase: dict):
        """
        Performs an intelligent, LLM-driven pre-flight check on tool arguments. It
        detects and corrects mismatches between the planner's provided arguments
        and the tool's actual schema, preventing validation errors.
        """
        tool_name = action.get("tool_name")
        if not tool_name:
            return

        tool_def = self.executor.dependencies['STATE'].get('mcp_tools', {}).get(tool_name)
        if not tool_def or not hasattr(tool_def, 'args') or not isinstance(tool_def.args, dict):
            return

        provided_args = action.get("arguments", {})
        official_arg_names = set(tool_def.args.keys())
        provided_arg_names = set(provided_args.keys())

        if provided_arg_names == official_arg_names:
            return

        app_logger.warning(f"Argument mismatch for tool '{tool_name}'. Planner provided: {provided_arg_names}, Tool requires: {official_arg_names}. Initiating LLM-based refinement.")

        yield self.executor._format_sse({
            "step": "System Correction",
            "type": "workaround",
            "details": {
                "summary": f"Detected an argument mismatch for tool '{tool_name}'. Agent is proactively correcting the arguments.",
                "correction_type": "argument_refinement"
            }
        })
        
        tool_schema_str = json.dumps({name: details for name, details in tool_def.args.items()}, indent=2)
        
        refinement_prompt = (
            "You are an expert argument mapper. Your task is to correct a failed tool call by re-mapping the provided arguments to the tool's official schema.\n\n"
            f"--- GOAL ---\n{phase.get('goal', self.executor.original_user_input)}\n\n"
            f"--- FAILED ARGUMENTS ---\n{json.dumps(provided_args, indent=2)}\n\n"
            f"--- CORRECT TOOL SCHEMA ---\n{tool_schema_str}\n\n"
            "--- INSTRUCTIONS ---\n"
            "1. Analyze the `GOAL` and the `FAILED ARGUMENTS` to understand the user's intent and what data is available.\n"
            "2. Examine the `CORRECT TOOL SCHEMA` to understand the exact argument names and structure the tool expects.\n"
            "3. Create a new, valid set of arguments by mapping the values from the `FAILED ARGUMENTS` to the correct names in the `CORRECT TOOL SCHEMA`.\n"
            "4. Discard any arguments from the failed call that do not exist in the correct schema.\n"
            "5. Your response MUST be a single JSON object containing only the corrected arguments.\n\n"
            "Example:\n"
            "`{{\"sql\": \"SELECT * FROM ...\"}}`"
        )

        reason = f"Proactively refining arguments for '{tool_name}' to prevent tool failure."
        call_id = str(uuid.uuid4())
        yield self.executor._format_sse({"step": "Calling LLM for Argument Refinement", "type": "system_message", "details": {"summary": reason, "call_id": call_id}})
        yield self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")

        response_text, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
            prompt=refinement_prompt, reason=reason,
            system_prompt_override="You are a JSON-only responding assistant.",
            raise_on_error=True,
            source=self.executor.source
        )
        
        yield self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")
        updated_session = session_manager.get_session(self.executor.session_id)
        if updated_session:
            yield self.executor._format_sse({ "statement_input": input_tokens, "statement_output": output_tokens, "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0), "call_id": call_id }, "token_update")
        
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match: raise ValueError("No JSON object found in refinement response.")

            corrected_args = json.loads(json_match.group(0))
            if isinstance(corrected_args, dict):
                action['arguments'] = corrected_args
                app_logger.info(f"Argument refinement successful. New args for '{tool_name}': {corrected_args}")
            else:
                 app_logger.warning("Argument refinement failed: LLM did not return a valid dictionary.")
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            app_logger.error(f"Failed to parse argument refinement response: {e}. Original arguments will be used.")

    async def _execute_tool(self, action: dict, phase: dict, is_fast_path: bool = False):
        """Executes a single tool call with a built-in retry and recovery mechanism."""
        
        if not is_fast_path:
            async for event in self._proactively_refine_arguments(action, phase):
                yield event
        
        tool_name = action.get("tool_name")
        arguments = action.get("arguments", {})
        
        if tool_name == "TDA_ContextReport" or (tool_name == "TDA_LLMTask" and "synthesized_answer" in arguments):
            if tool_name == "TDA_ContextReport":
                answer_key = "answer_from_context"
                log_message = f"Bypassing execution. Using context-based answer from planner via {tool_name}."
            else: # Legacy support
                answer_key = "synthesized_answer"
                log_message = "Bypassing TDA_LLMTask execution. Using synthesized answer from planner."

            app_logger.info(log_message)
            self.executor.is_synthesis_from_history = True
            self.executor.last_tool_output = {
                "status": "success",
                "metadata": {"tool_name": tool_name},
                "results": [{"response": arguments.get(answer_key)}]
            }
            if not is_fast_path:
                yield self.executor._format_sse({"step": "Tool Execution Result", "details": self.executor.last_tool_output, "tool_name": tool_name}, "tool_result")
                self.executor.turn_action_history.append({"action": action, "result": self.executor.last_tool_output})
                phase_num = phase.get("phase", self.executor.current_phase_index + 1)
                phase_result_key = f"result_of_phase_{phase_num}"
                self.executor.workflow_state.setdefault(phase_result_key, []).append(self.executor.last_tool_output)
                self.executor._add_to_structured_data(self.executor.last_tool_output)
            return
        
        max_retries = 3
        
        if tool_name == "TDA_LLMTask" and self.executor.is_synthesis_from_history:
            app_logger.info("Preparing TDA_LLMTask for 'full_context' execution.")
            session_data = session_manager.get_session(self.executor.session_id)
            session_history = session_data.get("session_history", []) if session_data else []
            
            action.setdefault("arguments", {})["mode"] = "full_context"
            action.setdefault("arguments", {})["session_history"] = session_history
            action["arguments"]["user_question"] = self.executor.original_user_input
        
        for attempt in range(max_retries):
            if 'notification' in action:
                yield self.executor._format_sse({"step": "System Notification", "details": action['notification'], "type": "workaround"})
                del action['notification']

            if tool_name == "TDA_LLMTask" and not self.executor.is_synthesis_from_history:
                distilled_workflow_state = self.executor._distill_data_for_llm_context(copy.deepcopy(self.executor.workflow_state))
                action.setdefault("arguments", {})["data"] = distilled_workflow_state
            
            if not is_fast_path:
                yield self.executor._format_sse({"step": "Tool Execution Intent", "details": action}, "tool_result")
            
            status_target = "db"
            call_id_for_tool = None
            
            if tool_name in ["TDA_LLMTask", "TDA_LLMFilter", "TDA_CurrentDate", "TDA_DateRange", "TDA_FinalReport", "TDA_ComplexPromptReport"]:
                status_target = "llm"
                call_id_for_tool = str(uuid.uuid4())
                
                reason_map = {
                    "TDA_LLMTask": action.get("arguments", {}).get("task_description", "Executing LLM-based task."),
                    "TDA_LLMFilter": action.get("arguments", {}).get("goal", "Filtering data with LLM."),
                    "TDA_FinalReport": "Synthesizing final user-facing report.",
                    "TDA_ComplexPromptReport": "Synthesizing final prompt-based report."
                }
                reason = reason_map.get(tool_name, f"Executing client-side tool: {tool_name}")

                yield self.executor._format_sse({
                    "step": f"Calling LLM for {tool_name}",
                    "type": "system_message",
                    "details": {"summary": reason, "call_id": call_id_for_tool}
                })
            
            yield self.executor._format_sse({"target": status_target, "state": "busy"}, "status_indicator_update")
            
            full_context_for_tool = {
                "original_user_input": self.executor.original_user_input,
                "workflow_goal_prompt": self.executor.workflow_goal_prompt,
                **self.executor.workflow_state
            }

            tool_result, input_tokens, output_tokens = await mcp_adapter.invoke_mcp_tool(
                self.executor.dependencies['STATE'], 
                action, 
                session_id=self.executor.session_id, 
                call_id=call_id_for_tool,
                workflow_state=full_context_for_tool
            )

            yield self.executor._format_sse({"target": status_target, "state": "idle"}, "status_indicator_update")

            if input_tokens > 0 or output_tokens > 0:
                updated_session = session_manager.get_session(self.executor.session_id)
                if updated_session:
                    final_call_id = tool_result.get("metadata", {}).get("call_id") if isinstance(tool_result, dict) else None
                    yield self.executor._format_sse({
                        "statement_input": input_tokens,
                        "statement_output": output_tokens,
                        "total_input": updated_session.get("input_tokens", 0),
                        "total_output": updated_session.get("output_tokens", 0),
                        "call_id": final_call_id
                    }, "token_update")
            
            self.executor.last_tool_output = tool_result 
            
            if isinstance(tool_result, dict) and tool_result.get("status") == "error":
                yield self.executor._format_sse({"details": tool_result, "tool_name": tool_name}, "tool_error")
                
                error_data_str = str(tool_result.get('data', ''))
                
                for error_pattern, friendly_message in DEFINITIVE_TOOL_ERRORS.items():
                    if re.search(error_pattern, error_data_str, re.IGNORECASE):
                        from trusted_data_agent.agent.executor import DefinitiveToolError
                        raise DefinitiveToolError(error_data_str, friendly_message)
                
                if attempt < max_retries - 1:
                    correction_details = {
                        "summary": f"Tool failed. Attempting self-correction ({attempt + 1}/{max_retries - 1}).",
                        "details": tool_result
                    }
                    yield self.executor._format_sse({"step": "System Self-Correction", "type": "workaround", "details": correction_details})
                    
                    correction_handler = CorrectionHandler(self.executor)
                    corrected_action, correction_events = await correction_handler.attempt_correction(action, tool_result)
                    
                    for event in correction_events:
                        yield event
                    
                    if corrected_action:
                        if "FINAL_ANSWER" in corrected_action:
                            final_answer_from_correction = corrected_action["FINAL_ANSWER"]
                            self.executor.last_tool_output = {"status": "success", "results": [{"response": f"FINAL_ANSWER: {final_answer_from_correction}"}]}
                            break
                        
                        if "prompt_name" in corrected_action:
                            async for event in self.executor._run_sub_prompt(
                                corrected_action['prompt_name'],
                                corrected_action.get("arguments", {}),
                                is_delegated_task=True
                            ):
                                yield event
                            
                            if self.executor.state == self.executor.AgentState.ERROR:
                                app_logger.error(f"Recovery prompt '{corrected_action['prompt_name']}' failed. Continuing retry loop.")
                                self.executor.last_tool_output = {"status": "error", "data": "The recovery prompt failed to execute."}
                                continue 
                            else:
                                app_logger.info(f"Successfully recovered from tool failure by executing prompt '{corrected_action['prompt_name']}'.")
                                break 

                        action = corrected_action
                        continue
                    else:
                        correction_failed_details = {
                            "summary": "Unable to find a correction. Aborting retries for this action.",
                            "details": tool_result
                        }
                        yield self.executor._format_sse({"step": "System Self-Correction Failed", "type": "error", "details": correction_failed_details})
                        break
                else:
                    persistent_failure_details = {
                        "summary": f"Tool '{tool_name}' failed after {max_retries} attempts.",
                        "details": tool_result
                    }
                    yield self.executor._format_sse({"step": "Persistent Failure", "type": "error", "details": persistent_failure_details})
            else:
                if not is_fast_path:
                    yield self.executor._format_sse({"step": "Tool Execution Result", "details": tool_result, "tool_name": tool_name}, "tool_result")
                break 
        
        if not is_fast_path:
            self.executor.turn_action_history.append({"action": action, "result": self.executor.last_tool_output})
            phase_num = phase.get("phase", self.executor.current_phase_index + 1)
            phase_result_key = f"result_of_phase_{phase_num}"
            self.executor.workflow_state.setdefault(phase_result_key, []).append(self.executor.last_tool_output)
            self.executor._add_to_structured_data(self.executor.last_tool_output)

    def _enrich_arguments_from_history(self, relevant_tools: list[str], current_args: dict = None) -> tuple[dict, list, bool]:
        """
        Scans the current turn's action history to find missing arguments for a tool call.
        It now only uses arguments from tool calls that were definitively successful.
        """
        events_to_yield = []
        initial_args = current_args.copy() if current_args else {}
        enriched_args = initial_args.copy()
        
        all_tools = self.executor.dependencies['STATE'].get('mcp_tools', {})
        required_args_for_phase = set()
        for tool_name in relevant_tools:
            tool = all_tools.get(tool_name)
            if not tool: continue
            args_dict = tool.args if isinstance(tool.args, dict) else {}
            for arg_name, arg_details in args_dict.items():
                if arg_details.get('required', False):
                    required_args_for_phase.add(arg_name)

        args_to_find = {arg for arg in required_args_for_phase if arg not in enriched_args or not enriched_args.get(arg)}
        if not args_to_find:
            return enriched_args, [], False

        for entry in reversed(self.executor.turn_action_history):
            if not args_to_find: break
            
            result = entry.get("result", {})
            is_successful_data_action = (
                isinstance(result, dict) and 
                result.get('status') == 'success' and 
                'results' in result
            )
            is_successful_chart_action = (
                isinstance(result, dict) and
                result.get('type') == 'chart' and
                'spec' in result
            )

            if not (is_successful_data_action or is_successful_chart_action):
                continue

            action_args = entry.get("action", {}).get("arguments", {})
            for arg_name in list(args_to_find):
                if arg_name in action_args and action_args[arg_name] is not None:
                    enriched_args[arg_name] = action_args[arg_name]
                    args_to_find.remove(arg_name)

            if isinstance(result, dict):
                result_metadata = result.get("metadata", {})
                if result_metadata:
                    metadata_to_arg_map = {
                        "database": "database_name",
                        "table": "table_name",
                        "column": "column_name"
                    }
                    for meta_key, arg_name in metadata_to_arg_map.items():
                        if arg_name in args_to_find and meta_key in result_metadata:
                            enriched_args[arg_name] = result_metadata[meta_key]
                            args_to_find.remove(arg_name)
        
        was_enriched = enriched_args != initial_args
        if was_enriched:
            for arg_name, value in enriched_args.items():
                if arg_name not in initial_args:
                    app_logger.info(f"Proactively inferred '{arg_name}' from turn history: '{value}'")
                    events_to_yield.append(self.executor._format_sse({
                        "step": "System Correction",
                        "details": f"System inferred '{arg_name}: {value}' from the current turn's actions.",
                        "type": "workaround",
                        "correction_type": "inferred_argument"
                    }))

        return enriched_args, events_to_yield, was_enriched

    async def _get_next_tactical_action(self, current_phase_goal: str, relevant_tools: list[str], enriched_args: dict, strategic_args: dict, executable_prompt: str = None) -> tuple[dict | str, int, int]:
        """Makes a tactical LLM call to decide the single next best action for the current phase."""
        
        permitted_tools_with_details = ""
        all_tools = self.executor.dependencies['STATE'].get('mcp_tools', {})
        
        for tool_name in relevant_tools:
            tool = all_tools.get(tool_name)
            if not tool: continue

            tool_str = f"\n- Tool: `{tool.name}`\n  - Description: {tool.description}"
            args_dict = tool.args if isinstance(tool.args, dict) else {}
            
            if args_dict:
                tool_str += "\n  - Arguments:"
                for arg_name, arg_details in args_dict.items():
                    is_required = arg_details.get('required', False)
                    arg_type = arg_details.get('type', 'any')
                    req_str = "required" if is_required else "optional"
                    arg_desc = arg_details.get('description', 'No description.')
                    tool_str += f"\n    - `{arg_name}` ({arg_type}, {req_str}): {arg_desc}"
            permitted_tools_with_details += tool_str + "\n"
        
        permitted_prompts_with_details = "None"
        if executable_prompt:
            all_prompts = self.executor.dependencies['STATE'].get('structured_prompts', {})
            prompt_info = None
            for category, prompts in all_prompts.items():
                for p in prompts:
                    if p['name'] == executable_prompt:
                        prompt_info = p
                        break
                if prompt_info: break
            
            if prompt_info:
                prompt_str = f"\n- Prompt: `{prompt_info['name']}`\n  - Description: {prompt_info.get('description', 'No description.')}"
                if prompt_info.get('arguments'):
                    prompt_str += "\n  - Arguments:"
                    for arg in prompt_info['arguments']:
                        req_str = "required" if arg.get('required') else "optional"
                        prompt_str += f"\n    - `{arg['name']}` ({arg.get('type', 'any')}, {req_str}): {arg.get('description', 'No description.')}"
                permitted_prompts_with_details = prompt_str + "\n"


        context_enrichment_section = ""
        if enriched_args:
            context_items = [f"- `{name}`: `{value}`" for name, value in enriched_args.items()]
            context_enrichment_section = (
                "\n--- CONTEXT FROM HISTORY ---\n"
                "The following critical information has been inferred from the conversation history. You MUST use it to fill in missing arguments.\n"
                + "\n".join(context_items) + "\n"
            )

        loop_context_section = ""
        if self.executor.is_in_loop:
            next_item = next((item for item in self.executor.current_loop_items if item not in self.executor.processed_loop_items), None)
            if next_item:
                loop_context_section = (
                    f"\n--- LOOP CONTEXT ---\n"
                    f"- You are currently in a loop to process multiple items.\n"
                    f"- All Items in Loop: {json.dumps(self.executor.current_loop_items)}\n"
                    f"- Items Already Processed: {json.dumps(self.executor.processed_loop_items)}\n"
                    f"- Your task is to process this single item next: {json.dumps(next_item)}\n"
                )

        strategic_arguments_section = "None provided."
        if strategic_args:
            strategic_arguments_section = json.dumps(strategic_args, indent=2)

        distilled_workflow_state = self.executor._distill_data_for_llm_context(copy.deepcopy(self.executor.workflow_state))
        distilled_turn_history = self.executor._distill_data_for_llm_context(copy.deepcopy(self.executor.turn_action_history))

        tactical_system_prompt = WORKFLOW_TACTICAL_PROMPT.format(
            workflow_goal=self.executor.workflow_goal_prompt,
            current_phase_goal=current_phase_goal,
            strategic_arguments_section=strategic_arguments_section,
            permitted_tools_with_details=permitted_tools_with_details,
            permitted_prompts_with_details=permitted_prompts_with_details,
            last_attempt_info=self.executor.last_failed_action_info,
            turn_action_history=json.dumps(distilled_turn_history, indent=2),
            all_collected_data=json.dumps(distilled_workflow_state, indent=2),
            loop_context_section=loop_context_section,
            context_enrichment_section=context_enrichment_section
        )

        response_text, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
            prompt="Determine the next action based on the instructions and state provided in the system prompt.",
            reason=f"Deciding next tactical action for phase: {current_phase_goal}",
            system_prompt_override=tactical_system_prompt,
            disabled_history=True,
            source=self.executor.source
        )
        
        self.executor.last_failed_action_info = "None"

        if "FINAL_ANSWER:" in response_text.upper() or "SYSTEM_ACTION_COMPLETE" in response_text.upper():
            return "SYSTEM_ACTION_COMPLETE", input_tokens, output_tokens

        try:
            json_match = re.search(r"```json\s*\n(.*?)\n\s*```|(\{.*\})", response_text, re.DOTALL)
            if not json_match: raise json.JSONDecodeError("No JSON object found", response_text, 0)
            
            json_str = json_match.group(1) or json_match.group(2)
            if not json_str: raise json.JSONDecodeError("Extracted JSON is empty", response_text, 0)

            raw_action = json.loads(json_str.strip())
            
            action_details = raw_action
            tool_name_synonyms = ["tool_name", "name", "tool", "action_name"]
            prompt_name_synonyms = ["prompt_name", "prompt"]
            arg_synonyms = ["arguments", "args", "tool_input", "action_input", "parameters"]
            
            possible_wrapper_keys = ["action", "tool_call", "tool", "prompt_call", "prompt"]
            for key in possible_wrapper_keys:
                if key in action_details and isinstance(action_details[key], dict):
                    action_details = action_details[key]
                    break 

            found_tool_name = None
            for key in tool_name_synonyms:
                if key in action_details:
                    found_tool_name = action_details.pop(key)
                    break
            
            found_prompt_name = None
            for key in prompt_name_synonyms:
                if key in action_details:
                    found_prompt_name = action_details.pop(key)
                    break

            found_args = None
            for key in arg_synonyms:
                if key in action_details and isinstance(action_details[key], dict):
                    found_args = action_details[key]
                    break
            
            if found_args is None:
                found_args = action_details

            normalized_action = {
                "tool_name": found_tool_name,
                "prompt_name": found_prompt_name,
                "arguments": found_args if isinstance(found_args, dict) else {}
            }

            if not normalized_action.get("tool_name") and not normalized_action.get("prompt_name"):
                if len(relevant_tools) == 1:
                    normalized_action["tool_name"] = relevant_tools[0]
                    self.executor.events_to_yield.append(self.executor._format_sse({
                        "step": "System Correction",
                        "type": "workaround",
                        "correction_type": "inferred_tool_name",
                        "details": f"LLM omitted tool_name. System inferred '{relevant_tools[0]}'."
                    }))
                elif executable_prompt:
                    normalized_action["prompt_name"] = executable_prompt
                    self.executor.events_to_yield.append(self.executor._format_sse({
                        "step": "System Correction",
                        "type": "workaround",
                        "correction_type": "inferred_prompt_name",
                        "details": f"LLM omitted prompt_name. System inferred '{executable_prompt}'."
                    }))
            
            if not normalized_action.get("tool_name") and not normalized_action.get("prompt_name"):
                 raise ValueError("Could not determine tool_name or prompt_name from LLM response.")

            return normalized_action, input_tokens, output_tokens
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Failed to get a valid JSON action from the tactical LLM. Response: {response_text}. Error: {e}")

    def _is_date_query_candidate(self, command: dict) -> tuple[bool, str, bool]:
        """Checks if a command is a candidate for the date-range orchestrator."""
        tool_name = command.get("tool_name")
        tool_spec = self.executor.dependencies['STATE'].get('mcp_tools', {}).get(tool_name)
        if not tool_spec or not hasattr(tool_spec, 'args') or not isinstance(tool_spec.args, dict):
            return False, None, False

        tool_arg_names = set(tool_spec.args.keys())
        tool_supports_range = 'start_date' in tool_arg_names and 'end_date' in tool_arg_names
        
        args = command.get("arguments", {})
        date_param_name = next((param for param in args if 'date' in param.lower()), None)
        
        return bool(date_param_name), date_param_name, tool_supports_range

    async def _classify_date_query_type(self):
        """Uses LLM to classify a date query as 'single' or 'range'."""
        classification_prompt = (
            f"You are a query classifier. Analyze the following query: '{self.executor.original_user_input}'. "
            "Determine if it refers to a 'single' date or a 'range' of dates. "
            "Extract the specific phrase that describes the date or range. "
            "Your response MUST be ONLY a JSON object with two keys: 'type' and 'phrase'."
        )
        reason="Classifying date query."
        call_id = str(uuid.uuid4())
        yield self.executor._format_sse({"step": "Calling LLM", "details": {"summary": reason, "call_id": call_id}})
        response_str, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
            prompt=classification_prompt, reason=reason,
            system_prompt_override="You are a JSON-only responding assistant.", raise_on_error=True,
            source=self.executor.source
        )
        updated_session = session_manager.get_session(self.executor.session_id)
        if updated_session:
            yield self.executor._format_sse({ "statement_input": input_tokens, "statement_output": output_tokens, "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0), "call_id": call_id }, "token_update")
        try:
            self.executor.temp_data_holder = json.loads(response_str)
        except (json.JSONDecodeError, KeyError):
            self.executor.temp_data_holder = {'type': 'single', 'phrase': self.executor.original_user_input}

    async def _get_tool_constraints(self, tool_name: str) -> Tuple[dict, list]:
        """
        Uses an LLM to determine if a tool requires numeric or character columns.
        Returns the constraints and a list of events to be yielded by the caller.
        """
        if tool_name in self.executor.tool_constraints_cache:
            return self.executor.tool_constraints_cache[tool_name], []

        events = []
        tool_definition = self.executor.dependencies['STATE'].get('mcp_tools', {}).get(tool_name)
        constraints = {}
        
        if tool_definition:
            prompt_modifier = ""
            if any(k in tool_name.lower() for k in ["univariate", "standarddeviation", "negativevalues"]):
                prompt_modifier = "This tool is for quantitative analysis and requires a 'numeric' data type for `column_name`."
            elif any(k in tool_name.lower() for k in ["distinctcategories"]):
                prompt_modifier = "This tool is for categorical analysis and requires a 'character' data type for `column_name`."

            prompt = (
                f"Analyze the tool to determine if its `column_name` argument is for 'numeric', 'character', or 'any' type.\n"
                f"Tool: `{tool_definition.name}`\nDescription: \"{tool_definition.description}\"\nHint: {prompt_modifier}\n"
                "Respond with a single JSON object: {\"dataType\": \"numeric\" | \"character\" | \"any\"}"
            )
            
            reason="Determining tool constraints for column iteration."
            call_id = str(uuid.uuid4())
            events.append(self.executor._format_sse({"step": "Calling LLM", "type": "system_message", "details": {"summary": reason, "call_id": call_id}}))
            
            response_text, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
                prompt=prompt, reason=reason,
                system_prompt_override="You are a JSON-only responding assistant.",
                raise_on_error=True,
                source=self.executor.source
            )

            updated_session = session_manager.get_session(self.executor.session_id)
            if updated_session:
                events.append(self.executor._format_sse({
                    "statement_input": input_tokens,
                    "statement_output": output_tokens,
                    "total_input": updated_session.get("input_tokens", 0),
                    "total_output": updated_session.get("output_tokens", 0),
                    "call_id": call_id
                }, "token_update"))

            try:
                constraints = json.loads(re.search(r'\{.*\}', response_text, re.DOTALL).group(0))
            except (json.JSONDecodeError, AttributeError):
                constraints = {}
        
        self.executor.tool_constraints_cache[tool_name] = constraints
        return constraints, events

    async def _recover_from_phase_failure(self, failed_phase_goal: str):
        """
        Attempts to recover from a persistently failing phase by generating a new plan.
        This version is robust to conversational text mixed with the JSON output.
        """
        call_id = str(uuid.uuid4())
        yield self.executor._format_sse({"step": "Attempting LLM-based Recovery", "type": "system_message", "details": {"summary": "The current plan is stuck. Asking LLM to generate a new plan.", "call_id": call_id}})

        last_error = "No specific error message found."
        failed_tool_name = "N/A (Phase Failed)"
        for action in reversed(self.executor.turn_action_history):
            result = action.get("result", {})
            if isinstance(result, dict) and result.get("status") == "error":
                last_error = result.get("data", result.get("error", "Unknown error"))
                failed_tool_name = action.get("action", {}).get("tool_name", failed_tool_name)
                self.executor.globally_skipped_tools.add(failed_tool_name)
                break
        
        distilled_workflow_state = self.executor._distill_data_for_llm_context(copy.deepcopy(self.executor.workflow_state))

        recovery_prompt = ERROR_RECOVERY_PROMPT.format(
            user_question=self.executor.original_user_input,
            error_message=last_error,
            failed_tool_name=failed_tool_name,
            all_collected_data=json.dumps(distilled_workflow_state, indent=2),
            workflow_goal_and_plan=f"The agent was trying to achieve this goal: '{failed_phase_goal}'"
        )
        
        reason = "Recovering from persistent phase failure."
        yield self.executor._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
        response_text, input_tokens, output_tokens = await self.executor._call_llm_and_update_tokens(
            prompt=recovery_prompt, 
            reason=reason,
            raise_on_error=True,
            source=self.executor.source
        )
        yield self.executor._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")
        
        updated_session = session_manager.get_session(self.executor.session_id)
        if updated_session:
            yield self.executor._format_sse({"statement_input": input_tokens, "statement_output": output_tokens, "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0), "call_id": call_id}, "token_update")

        try:
            json_match = re.search(r'(\[.*\]|\{.*\})', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No valid JSON plan or action found in the recovery response.")
            
            json_str = json_match.group(1)
            plan_object = json.loads(json_str)

            if isinstance(plan_object, dict) and ("tool_name" in plan_object or "prompt_name" in plan_object):
                app_logger.warning("Recovery LLM returned a direct action; wrapping it in a plan.")
                tool_name = plan_object.get("tool_name") or plan_object.get("prompt_name")
                new_plan = [{
                    "phase": 1,
                    "goal": f"Recovered plan: Execute the action for the user's request: '{self.executor.original_user_input}'",
                    "relevant_tools": [tool_name]
                }]
            elif isinstance(plan_object, list):
                new_plan = plan_object
            else:
                raise ValueError("Recovered plan is not a valid list or action object.")

            yield self.executor._format_sse({"step": "Recovery Plan Generated", "type": "system_message", "details": new_plan})
            
            self.executor.meta_plan = new_plan
            self.executor.current_phase_index = 0
            self.executor.turn_action_history.append({"action": "RECOVERY_REPLAN", "result": {"status": "success"}})

        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"LLM-based recovery failed. The LLM did not return a valid new plan. Response: {response_text}. Error: {e}")

    async def _attempt_tool_self_correction(self, failed_action: dict, error_result: dict) -> tuple[dict | None, list]:
        """
        Delegates the correction task to the CorrectionHandler, which uses the
        Strategy Pattern to find and execute the appropriate recovery logic.
        """
        correction_handler = CorrectionHandler(self.executor)
        return await correction_handler.attempt_correction(failed_action, error_result)

