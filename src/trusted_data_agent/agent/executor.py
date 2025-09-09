# trusted_data_agent/agent/executor.py
import re
import json
import logging
import copy
from enum import Enum, auto

from trusted_data_agent.agent.formatter import OutputFormatter
from trusted_data_agent.core import session_manager
from trusted_data_agent.llm import handler as llm_handler
from trusted_data_agent.core.config import APP_CONFIG
from trusted_data_agent.agent.prompts import GENERATE_FINAL_SUMMARY
from trusted_data_agent.agent.response_models import CanonicalResponse
from trusted_data_agent.mcp import adapter as mcp_adapter


# Refactored components
from trusted_data_agent.agent.planner import Planner
from trusted_data_agent.agent.phase_executor import PhaseExecutor


app_logger = logging.getLogger("quart.app")


class DefinitiveToolError(Exception):
    """Custom exception for unrecoverable tool errors."""
    def __init__(self, message, friendly_message):
        super().__init__(message)
        self.friendly_message = friendly_message


class AgentState(Enum):
    PLANNING = auto()
    EXECUTING = auto()
    SUMMARIZING = auto()
    DONE = auto()
    ERROR = auto()


def unwrap_exception(e: BaseException) -> BaseException:
    """Recursively unwraps ExceptionGroups to find the root cause."""
    if isinstance(e, ExceptionGroup) and e.exceptions:
        return unwrap_exception(e.exceptions[0])
    return e


class PlanExecutor:
    AgentState = AgentState

    def _get_prompt_info(self, prompt_name: str) -> dict | None:
        """Helper to find prompt details from the structured prompts in the global state."""
        if not prompt_name:
            return None
        structured_prompts = self.dependencies['STATE'].get('structured_prompts', {})
        for category_prompts in structured_prompts.values():
            for prompt in category_prompts:
                if prompt.get("name") == prompt_name:
                    return prompt
        return None

    def __init__(self, session_id: str, original_user_input: str, dependencies: dict, active_prompt_name: str = None, prompt_arguments: dict = None, execution_depth: int = 0, disabled_history: bool = False, previous_turn_data: list = None, force_history_disable: bool = False, source: str = "text", is_delegated_task: bool = False, force_final_summary: bool = False):
        self.session_id = session_id
        self.original_user_input = original_user_input
        self.dependencies = dependencies
        self.state = self.AgentState.PLANNING
        
        self.structured_collected_data = {}
        self.workflow_state = {} 
        self.turn_action_history = []
        self.meta_plan = None
        self.current_phase_index = 0
        self.last_tool_output = None
        
        self.active_prompt_name = active_prompt_name
        self.prompt_arguments = prompt_arguments or {}
        self.workflow_goal_prompt = ""

        prompt_info = self._get_prompt_info(active_prompt_name)
        self.prompt_type = prompt_info.get("prompt_type", "reporting") if prompt_info else "reporting"

        self.is_in_loop = False
        self.current_loop_items = []
        self.processed_loop_items = []
        
        self.tool_constraints_cache = {}
        self.globally_skipped_tools = set()
        self.temp_data_holder = None
        self.last_failed_action_info = "None"
        self.events_to_yield = []
        self.last_action_str = None 
        
        self.llm_debug_history = []
        self.max_steps = 40
        
        self.execution_depth = execution_depth
        self.MAX_EXECUTION_DEPTH = 5
        
        self.disabled_history = disabled_history or force_history_disable
        self.previous_turn_data = previous_turn_data or []
        self.is_synthesis_from_history = False
        self.is_conversational_plan = False
        self.source = source
        self.is_delegated_task = is_delegated_task
        self.force_final_summary = force_final_summary
        
        self.is_complex_prompt_workflow = False
        self.final_canonical_response = None


    @staticmethod
    def _format_sse(data: dict, event: str = None) -> str:
        msg = f"data: {json.dumps(data)}\n"
        if event is not None:
            msg += f"event: {event}\n"
        return f"{msg}\n"
        
    async def _call_llm_and_update_tokens(self, prompt: str, reason: str, system_prompt_override: str = None, raise_on_error: bool = False, disabled_history: bool = False, active_prompt_name_for_filter: str = None) -> tuple[str, int, int]:
        """A centralized wrapper for calling the LLM that handles token updates."""
        final_disabled_history = disabled_history or self.disabled_history
        
        response_text, statement_input_tokens, statement_output_tokens = await llm_handler.call_llm_api(
            self.dependencies['STATE']['llm'], prompt, self.session_id,
            dependencies=self.dependencies, reason=reason,
            system_prompt_override=system_prompt_override, raise_on_error=raise_on_error,
            disabled_history=final_disabled_history,
            active_prompt_name_for_filter=active_prompt_name_for_filter
        )
        self.llm_debug_history.append({"reason": reason, "response": response_text})
        app_logger.debug(f"LLM RESPONSE (DEBUG): Reason='{reason}', Response='{response_text}'")
        return response_text, statement_input_tokens, statement_output_tokens

    def _add_to_structured_data(self, tool_result: dict, context_key_override: str = None):
        """Adds tool results to the structured data dictionary."""
        context_key = context_key_override or f"Plan Results: {self.active_prompt_name or 'Ad-hoc'}"
        if context_key not in self.structured_collected_data:
            self.structured_collected_data[context_key] = []
        
        if isinstance(tool_result, list):
             self.structured_collected_data[context_key].extend(tool_result)
        else:
             self.structured_collected_data[context_key].append(tool_result)
        app_logger.info(f"Added tool result to structured data under key: '{context_key}'.")

    def _distill_data_for_llm_context(self, data: any) -> any:
        """
        Recursively distills large data structures into metadata summaries to protect the LLM context window.
        """
        if isinstance(data, dict):
            if 'results' in data and isinstance(data['results'], list):
                results_list = data['results']
                is_large = (len(results_list) > APP_CONFIG.CONTEXT_DISTILLATION_MAX_ROWS or 
                            len(json.dumps(results_list)) > APP_CONFIG.CONTEXT_DISTILLATION_MAX_CHARS)

                if is_large and all(isinstance(item, dict) for item in results_list):
                    distilled_result = {
                        "status": data.get("status", "success"),
                        "metadata": {
                            "row_count": len(results_list),
                            "columns": list(results_list[0].keys()) if results_list else [],
                            **data.get("metadata", {})
                        },
                        "comment": "Full data is too large for context. This is a summary."
                    }
                    return distilled_result
            
            return {key: self._distill_data_for_llm_context(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [self._distill_data_for_llm_context(item) for item in data]
        
        return data

    def _resolve_arguments(self, arguments: dict) -> dict:
        """
        Scans tool arguments for placeholders (e.g., 'result_of_phase_1') and
        replaces them with the actual data from the workflow state.
        This version now supports a basic 'length' filter.
        """
        if not isinstance(arguments, dict):
            return arguments

        resolved_args = {}
        for key, value in arguments.items():
            if isinstance(value, str):
                # Check for placeholders like 'result_of_phase_1' or '{{...}}'
                placeholder_match = re.fullmatch(r"result_of_phase_(\d+)", value)
                jinja_match = re.search(r"\{\{\s*result_of_phase_(\d+)\s*\|\s*length\s*\}\}", value)

                if jinja_match:
                    phase_num = int(jinja_match.group(1))
                    source_key = f"result_of_phase_{phase_num}"
                    if source_key in self.workflow_state:
                        data = self.workflow_state[source_key]
                        data_length = 0
                        # This logic needs to be robust to find the list to measure
                        if isinstance(data, list) and data and isinstance(data[0], dict) and 'results' in data[0]:
                             data_length = len(data[0].get('results', []))
                        elif isinstance(data, list):
                             data_length = len(data)
                        
                        # Replace the Jinja expression with the calculated length
                        resolved_value = value.replace(jinja_match.group(0), str(data_length))
                        resolved_args[key] = resolved_value
                        app_logger.info(f"Resolved Jinja expression '{value}' to '{resolved_value}'")
                    else:
                        resolved_args[key] = value

                elif placeholder_match:
                    phase_num = int(placeholder_match.group(1))
                    source_key = f"result_of_phase_{phase_num}"
                    
                    if source_key in self.workflow_state:
                        data = self.workflow_state[source_key]
                        
                        # Heuristic to extract a single scalar value if appropriate
                        if (isinstance(data, list) and len(data) == 1 and 
                            isinstance(data[0], dict) and "results" in data[0] and
                            isinstance(data[0]["results"], list) and len(data[0]["results"]) == 1 and
                            isinstance(data[0]["results"][0], dict) and len(data[0]["results"][0]) == 1):
                            
                            extracted_value = next(iter(data[0]["results"][0].values()))
                            resolved_args[key] = extracted_value
                        else:
                            resolved_args[key] = data
                    else:
                        app_logger.warning(f"Could not resolve placeholder '{value}': key '{source_key}' not in workflow state.")
                        resolved_args[key] = value 
                else:
                    resolved_args[key] = value
            elif isinstance(value, list):
                resolved_list = []
                for item in value:
                    if isinstance(item, dict):
                        resolved_list.append(self._resolve_arguments(item))
                    else:
                        resolved_list.append(item)
                resolved_args[key] = resolved_list
            elif isinstance(value, dict):
                 resolved_args[key] = self._resolve_arguments(value)
            else:
                resolved_args[key] = value
        
        return resolved_args

    async def run(self):
        """The main, unified execution loop for the agent."""
        final_answer_override = None
        try:
            if self.is_delegated_task:
                async for event in self._run_delegated_prompt():
                    yield event
                return
            
            # --- PLANNING STATE ---
            if self.state == self.AgentState.PLANNING:
                planner = Planner(self)
                should_replan = False
                planning_is_disabled_history = self.disabled_history

                replan_attempt = 0
                max_replans = 1
                while True: # Loop for planning and potential re-planning
                    replan_context = None
                    if replan_attempt > 0:
                        prompts_in_plan = [p['executable_prompt'] for p in (self.meta_plan or []) if 'executable_prompt' in p]
                        context_parts = [
                            "\n--- CONTEXT FOR RE-PLANNING ---",
                            "Your previous plan was inefficient because it used a high-level prompt in a multi-step plan. You MUST create a new, more detailed plan that achieves the same goal using ONLY tools.",
                            "\n**CRITICAL ARCHITECTURAL RULE:** Your new tool-only plan must still adhere to all primary directives. This includes the rule that all synthesis or summarization tasks must be consolidated into a single, final `TDA_LLMTask` phase. Avoid creating redundant, back-to-back summary steps.\n",
                            "To help you, here is the description of the prompt(s) you previously selected. You must replicate their logic using basic tools:"
                        ]
                        for prompt_name in prompts_in_plan:
                            prompt_info = self._get_prompt_info(prompt_name)
                            if prompt_info:
                                context_parts.append(f"\n- Instructions for '{prompt_name}': {prompt_info.get('description', 'No description.')}")
                        replan_context = "\n".join(context_parts)

                    # Generate and refine the plan using the Planner component
                    async for event in planner.generate_and_refine_plan(
                        force_disable_history=planning_is_disabled_history,
                        replan_context=replan_context
                    ):
                        yield event

                    # Check for conditions that might trigger a re-plan
                    plan_has_prompt = self.meta_plan and any('executable_prompt' in phase for phase in self.meta_plan)
                    replan_triggered = False
                    if plan_has_prompt:
                        has_other_significant_tool = any('executable_prompt' not in phase and phase.get('relevant_tools') != ['TDA_LLMTask'] for phase in self.meta_plan)
                        is_single_phase_prompt = len(self.meta_plan) == 1
                        if has_other_significant_tool and not is_single_phase_prompt:
                            replan_triggered = True

                    if self.execution_depth == 0 and replan_triggered and replan_attempt < max_replans:
                        replan_attempt += 1
                        yield self._format_sse({
                            "step": "Re-planning for Efficiency", "type": "plan_optimization",
                            "details": {
                                "summary": "Initial plan uses a sub-prompt alongside other tools. Agent is re-planning to create a more efficient, tool-only workflow.",
                                "original_plan": copy.deepcopy(self.meta_plan)
                            }
                        })
                        continue
                    
                    break # Exit planning loop if no re-plan is needed

                is_single_prompt_plan = (self.meta_plan and len(self.meta_plan) == 1 and 'executable_prompt' in self.meta_plan[0] and not self.is_delegated_task)

                if is_single_prompt_plan:
                    # Handle the special case of a plan that is just a single prompt call
                    async for event in self._handle_single_prompt_plan(planner):
                        yield event

                if self.is_conversational_plan:
                    app_logger.info("Detected a conversational plan. Bypassing execution.")
                    self.state = self.AgentState.SUMMARIZING
                else:
                    self.state = self.AgentState.EXECUTING

            # --- EXECUTION STATE ---
            try:
                if self.state == self.AgentState.EXECUTING:
                    async for event in self._run_plan(): yield event
            except DefinitiveToolError as e:
                app_logger.error(f"Execution halted by definitive tool error: {e.friendly_message}")
                yield self._format_sse({"step": "Unrecoverable Error", "details": e.friendly_message, "type": "error"}, "tool_result")
                final_answer_override = f"I could not complete the request. Reason: {e.friendly_message}"
                self.state = self.AgentState.SUMMARIZING
            
            # --- SUMMARIZING STATE ---
            if self.state == self.AgentState.SUMMARIZING:
                async for event in self._handle_summarization(final_answer_override):
                    yield event

        except Exception as e:
            root_exception = unwrap_exception(e)
            app_logger.error(f"Error in state {self.state.name}: {root_exception}", exc_info=True)
            self.state = self.AgentState.ERROR
            yield self._format_sse({"error": "Execution stopped due to an unrecoverable error.", "details": str(root_exception)}, "error")
        finally:
            if not self.disabled_history:
                session_manager.update_last_turn_data(self.session_id, self.turn_action_history)
                app_logger.debug(f"Saved last turn data to session {self.session_id}")
    
    async def _handle_single_prompt_plan(self, planner: Planner):
        """Orchestrates the logic for expanding a single-prompt plan."""
        single_phase = self.meta_plan[0]
        prompt_name = single_phase.get('executable_prompt')
        prompt_args = single_phase.get('arguments', {})

        yield self._format_sse({
            "step": "System Correction", "type": "workaround",
            "details": f"Single Prompt('{prompt_name}') identified. Expanding plan in-process to improve efficiency."
        })

        prompt_info = self._get_prompt_info(prompt_name)
        if prompt_info:
            required_args = {arg['name'] for arg in prompt_info.get('arguments', []) if arg.get('required')}
            missing_args = required_args - set(prompt_args.keys())
            
            if missing_args:
                # Enrich missing arguments if possible
                yield self._format_sse({
                    "step": "System Correction", "type": "workaround",
                    "details": f"Prompt '{prompt_name}' is missing required arguments: {missing_args}. Attempting to extract from user query."
                })

                enrichment_prompt = (
                    f"You are an expert argument extractor. From the user's query, extract the values for the following missing arguments: {list(missing_args)}. "
                    f"User Query: \"{self.original_user_input}\"\n"
                    "Respond with only a single, valid JSON object mapping the argument names to their extracted values."
                )
                reason = f"Extracting missing arguments for prompt '{prompt_name}'"
                
                yield self._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
                response_text, _, _ = await self._call_llm_and_update_tokens(
                    prompt=enrichment_prompt, reason=reason,
                    system_prompt_override="You are a JSON-only responding assistant.",
                    raise_on_error=True
                )
                yield self._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")

                try:
                    extracted_args = json.loads(response_text)
                    prompt_args.update(extracted_args)
                    app_logger.info(f"Successfully enriched arguments: {extracted_args}")
                except (json.JSONDecodeError, AttributeError) as e:
                    app_logger.error(f"Failed to parse extracted arguments: {e}. The prompt may fail.")

        self.active_prompt_name = prompt_name
        self.prompt_arguments = self._resolve_arguments(prompt_args)
        self.prompt_type = prompt_info.get("prompt_type", "reporting") if prompt_info else "reporting"
        
        # Regenerate the plan with the expanded context
        async for event in planner.generate_and_refine_plan():
            yield event

    async def _run_plan(self):
        """Executes the generated meta-plan, delegating to the PhaseExecutor."""
        if not self.meta_plan:
            raise RuntimeError("Cannot execute plan: meta_plan is not generated.")
        
        phase_executor = PhaseExecutor(self)

        if not APP_CONFIG.SUB_PROMPT_FORCE_SUMMARY and self.execution_depth > 0 and len(self.meta_plan) > 1:
            last_phase = self.meta_plan[-1]
            if last_phase.get('relevant_tools') == ['TDA_LLMTask']:
                app_logger.info(f"Sub-process (depth {self.execution_depth}) is skipping its final summary phase.")
                yield self._format_sse({
                    "step": "Plan Optimization", "type": "plan_optimization",
                    "details": "Sub-process is skipping its final summary task to prevent redundant work. The main process will generate the final report."
                })
                self.meta_plan = self.meta_plan[:-1]

        while self.current_phase_index < len(self.meta_plan):
            current_phase = self.meta_plan[self.current_phase_index]
            current_phase["arguments"] = self._resolve_arguments(current_phase.get("arguments", {}))

            is_delegated_prompt_phase = 'executable_prompt' in current_phase and self.execution_depth < self.MAX_EXECUTION_DEPTH
            
            if is_delegated_prompt_phase:
                prompt_name = current_phase.get('executable_prompt')
                prompt_args = current_phase.get('arguments', {})
                async for event in self._run_sub_prompt(prompt_name, prompt_args):
                    yield event
            else:
                async for event in phase_executor.execute_phase(current_phase):
                    yield event
            
            self.current_phase_index += 1

        app_logger.info("Meta-plan has been fully executed. Transitioning to summarization.")
        self.state = self.AgentState.SUMMARIZING

    async def _run_sub_prompt(self, prompt_name: str, prompt_args: dict, is_delegated_task: bool = False):
        """Creates and runs a sub-executor for a delegated prompt."""
        yield self._format_sse({
            "step": "Prompt Execution Granted",
            "details": f"Executing prompt '{prompt_name}' as part of the plan.",
            "type": "workaround"
        })
        
        sub_executor = PlanExecutor(
            session_id=self.session_id,
            original_user_input=f"Executing prompt: {prompt_name}",
            dependencies=self.dependencies,
            active_prompt_name=prompt_name,
            prompt_arguments=prompt_args,
            execution_depth=self.execution_depth + 1,
            disabled_history=self.disabled_history,
            previous_turn_data=self.turn_action_history,
            source=self.source,
            is_delegated_task=is_delegated_task,
            force_final_summary=APP_CONFIG.SUB_PROMPT_FORCE_SUMMARY
        )
        
        async for event in sub_executor.run():
            yield event
        
        # Absorb state from the sub-run
        self.structured_collected_data.update(sub_executor.structured_collected_data)
        self.workflow_state.update(sub_executor.workflow_state)
        self.turn_action_history.extend(sub_executor.turn_action_history)
        self.last_tool_output = sub_executor.last_tool_output

        if sub_executor.state == self.AgentState.ERROR:
            app_logger.error(f"Sub-executor for prompt '{prompt_name}' failed.")
            self.last_tool_output = {"status": "error", "error_message": f"Sub-prompt '{prompt_name}' failed."}
        else:
            self.last_tool_output = {"status": "success"}

    async def _run_delegated_prompt(self):
        """
        Executes a single, delegated prompt without generating a new meta-plan.
        This is used for sub-executors created during self-correction.
        """
        if not self.active_prompt_name:
            app_logger.error("Delegated task started without an active_prompt_name.")
            self.state = self.AgentState.ERROR
            return

        self.meta_plan = [{"phase": 1, "goal": f"Delegated execution of prompt: {self.active_prompt_name}", "executable_prompt": self.active_prompt_name, "arguments": self.prompt_arguments}]
        self.state = self.AgentState.EXECUTING
        async for event in self._run_plan():
            yield event

    async def _handle_summarization(self, final_answer_override: str | None):
        """Orchestrates the final summarization and answer formatting."""
        final_summary_content = None

        if self.execution_depth > 0 and not self.force_final_summary:
            app_logger.info(f"Sub-planner (depth {self.execution_depth}) completed. Bypassing final summary.")
            self.state = self.AgentState.DONE
        elif self.prompt_type == 'context':
            app_logger.info(f"'{self.active_prompt_name}' is a 'context' prompt. Skipping final summary.")
            self.state = self.AgentState.DONE
        elif final_answer_override:
            final_summary_content = CanonicalResponse(direct_answer=final_answer_override)
        elif self.is_conversational_plan:
            response_text = self.temp_data_holder or "I'm sorry, I don't have a response for that."
            final_summary_content = CanonicalResponse(direct_answer=response_text)
        elif self.final_canonical_response:
            final_summary_content = self.final_canonical_response
            if self.is_complex_prompt_workflow:
                # Yield status updates around the await call
                yield self._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
                final_summary_content = await self._format_complex_prompt_report(final_summary_content)
                yield self._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")
        else:
            async for event in self._generate_final_summary():
                if isinstance(event, CanonicalResponse):
                    final_summary_content = event
                else:
                    yield event

        if final_summary_content:
            async for event in self._format_and_yield_final_answer(final_summary_content):
                yield event
            self.state = self.AgentState.DONE

    async def _format_complex_prompt_report(self, summary_content: CanonicalResponse) -> str:
        """Handles the second-stage LLM call for presentation formatting."""
        app_logger.info("Complex prompt workflow detected. Initiating Stage 2: Presentation Formatting.")
        presentation_prompt = (
            "You are a formatting expert. Your task is to take a structured JSON data payload and present it as a final, user-facing report "
            "based on the original prompt's formatting instructions.\n\n"
            "--- STRUCTURED DATA PAYLOAD ---\n"
            f"{summary_content.model_dump_json(indent=2)}\n\n"
            "--- ORIGINAL FORMATTING INSTRUCTIONS ---\n"
            f"{self.workflow_goal_prompt}\n\n"
            "--- FINAL INSTRUCTIONS ---\n"
            "Your output MUST be only the final, formatted markdown text that directly fulfills the original instructions. "
            "Do not include the JSON payload or any conversational text in your response."
        )
        formatted_text, _, _ = await self._call_llm_and_update_tokens(
            prompt=presentation_prompt,
            reason="Stage 2: Formatting final report based on complex prompt instructions."
        )
        return formatted_text

    async def _generate_final_summary(self):
        """
        Orchestrates the generation of the final summary, yielding the structured CanonicalResponse.
        """
        async for event in self._call_llm_for_final_summary():
            yield event

    async def _call_llm_for_final_summary(self):
        """
        Calls the LLM to synthesize a final summary and returns a structured
        CanonicalResponse object.
        """
        # This logic is now simpler as it relies on the Planner's distillation.
        final_summary_prompt_text = GENERATE_FINAL_SUMMARY.format(
            all_collected_data=json.dumps(self.workflow_state, indent=2)
        )
        core_llm_command = {
            "tool_name": "TDA_LLMTask",
            "arguments": {
                "task_description": final_summary_prompt_text,
                "user_question": self.original_user_input
            }
        }
        
        yield self._format_sse({"step": "Calling LLM to write final report", "details": "Synthesizing structured summary."})
        yield self._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")
        summary_result, input_tokens, output_tokens = await mcp_adapter.invoke_mcp_tool(self.dependencies['STATE'], core_llm_command, session_id=self.session_id)
        yield self._format_sse({"target": "llm", "state": "idle"}, "status_indicator_update")

        updated_session = session_manager.get_session(self.session_id)
        if updated_session:
            yield self._format_sse({ "statement_input": input_tokens, "statement_output": output_tokens, "total_input": updated_session.get("input_tokens", 0), "total_output": updated_session.get("output_tokens", 0) }, "token_update")

        if (summary_result and summary_result.get("status") == "success"):
            try:
                response_str = summary_result.get("results", [{}])[0].get("response", "{}")
                json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
                if not json_match: raise json.JSONDecodeError("No valid JSON object found in the LLM response string.", response_str, 0)
                
                clean_json_str = json_match.group(0)
                inner_json = json.loads(clean_json_str)
                report_arguments = inner_json.get("arguments", inner_json)
                
                structured_response = CanonicalResponse.model_validate(report_arguments)
                yield structured_response
                return
            except (json.JSONDecodeError, AttributeError, IndexError, KeyError) as e:
                app_logger.error(f"Failed to parse or validate LLM summary: {e}", exc_info=True)
                app_logger.error(f"Problematic summary_result from TDA_LLMTask: {summary_result}")
                yield CanonicalResponse(direct_answer="The agent has completed its work, but an issue occurred while structuring the final summary.")
                return
        
        app_logger.error(f"TDA_LLMTask for summary failed or returned unexpected data. Result: {summary_result}")
        yield CanonicalResponse(direct_answer="The agent has completed its work, but an issue occurred while generating the final summary.")

    async def _format_and_yield_final_answer(self, final_content: str | CanonicalResponse):
        """
        Formats a raw summary string OR a CanonicalResponse object and yields
        the final SSE event to the UI.
        """
        if isinstance(final_content, CanonicalResponse):
            formatter = OutputFormatter(
                canonical_response=final_content,
                collected_data=self.structured_collected_data,
                original_user_input=self.original_user_input,
                active_prompt_name=self.active_prompt_name
            )
        else:
            formatter = OutputFormatter(
                llm_response_text=str(final_content),
                collected_data=self.structured_collected_data,
                original_user_input=self.original_user_input,
                active_prompt_name=self.active_prompt_name
            )
        
        final_html, tts_payload = formatter.render()
        
        session_manager.add_to_history(self.session_id, 'assistant', final_html)
        
        clean_summary_for_thought = "The agent has completed its work."
        if isinstance(final_content, CanonicalResponse):
            clean_summary_for_thought = final_content.direct_answer
        elif isinstance(final_content, str):
            clean_summary_for_thought = final_content.replace("FINAL_ANSWER:", "").strip()

        yield self._format_sse({"step": "LLM has generated the final answer", "details": clean_summary_for_thought}, "llm_thought")

        yield self._format_sse({
            "final_answer": final_html,
            "tts_payload": tts_payload,
            "source": self.source
        }, "final_answer")
