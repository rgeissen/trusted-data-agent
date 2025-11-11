# trusted_data_agent/agent/executor.py
import re
import json
import logging
import copy
import uuid
import asyncio
from enum import Enum, auto
from typing import Tuple, List
# --- MODIFICATION START: Import datetime and timezone ---
from datetime import datetime, timezone
# --- MODIFICATION END ---

from trusted_data_agent.agent.formatter import OutputFormatter
from trusted_data_agent.core import session_manager
from trusted_data_agent.llm import handler as llm_handler
from trusted_data_agent.core.config import APP_CONFIG
from trusted_data_agent.agent.response_models import CanonicalResponse, PromptReportResponse
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

    # --- MODIFICATION START: Add plan_to_execute and is_replay ---
    def __init__(self, session_id: str, user_uuid: str, original_user_input: str, dependencies: dict, active_prompt_name: str = None, prompt_arguments: dict = None, execution_depth: int = 0, disabled_history: bool = False, previous_turn_data: dict = None, force_history_disable: bool = False, source: str = "text", is_delegated_task: bool = False, force_final_summary: bool = False, plan_to_execute: list = None, is_replay: bool = False, task_id: str = None):
        self.session_id = session_id
        self.user_uuid = user_uuid
        # --- MODIFICATION END ---
        self.original_user_input = original_user_input
        self.dependencies = dependencies
        self.state = self.AgentState.PLANNING

        # --- MODIFICATION START: Snapshot model and provider for this turn ---
        self.current_model = APP_CONFIG.CURRENT_MODEL
        self.current_provider = APP_CONFIG.CURRENT_PROVIDER
        # --- MODIFICATION END ---

        self.structured_collected_data = {}
        self.workflow_state = {}
        self.turn_action_history = []
        self.meta_plan = None
        self.original_plan_for_history = None # Added to store original plan
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
        self.previous_turn_data = previous_turn_data or {}
        self.is_synthesis_from_history = False
        self.is_conversational_plan = False
        self.source = source
        self.is_delegated_task = is_delegated_task
        self.force_final_summary = force_final_summary

        self.is_complex_prompt_workflow = False
        self.final_canonical_response = None
        self.is_single_prompt_plan = False
        self.final_summary_text = ""

        # --- MODIFICATION START: Store replay flags ---
        self.plan_to_execute = plan_to_execute # Store the plan if provided for replay
        self.is_replay = is_replay # Flag indicating if this is a replay
        # --- MODIFICATION END ---
        # --- MODIFICATION START: Add instance variable for turn number ---
        self.current_turn_number = 0 # Will be calculated once in run()
        # --- MODIFICATION END ---
        # --- MODIFICATION START: Store task_id ---
        self.task_id = task_id
        # --- MODIFICATION END ---
        self.turn_input_tokens = 0
        self.turn_output_tokens = 0


    def _log_system_event(self, event_data: dict, event_name: str = None):
        """Logs a system-level event to the turn action history for replay and debugging."""
        # Avoid logging token updates or status indicators
        if event_name in ["token_update", "status_indicator_update"] or "state" in event_data:
            return

        # Avoid logging the final answer event as it's not a step in the process
        if event_name == "final_answer":
            return

        action_for_history = {
            "tool_name": "TDA_SystemLog",
            "arguments": {
                "message": event_data.get("step"),
                "details": event_data.get("details")
            },
            "metadata": {
                "execution_depth": self.execution_depth,
                "type": event_data.get("type")
            }
        }
        result = {"status": "info"}
        if event_data.get("type") in ["error", "cancelled"]:
            result["status"] = event_data.get("type")

        self.turn_action_history.append({"action": action_for_history, "result": result})


    @staticmethod
    def _format_sse(data: dict, event: str = None) -> str:
        msg = f"data: {json.dumps(data)}\n"
        if event is not None:
            msg += f"event: {event}\n"
        return f"{msg}\n"

    async def _call_llm_and_update_tokens(self, prompt: str, reason: str, system_prompt_override: str = None, raise_on_error: bool = False, disabled_history: bool = False, active_prompt_name_for_filter: str = None, source: str = "text") -> tuple[str, int, int]:
        """A centralized wrapper for calling the LLM that handles token updates."""
        final_disabled_history = disabled_history or self.disabled_history

        response_text, statement_input_tokens, statement_output_tokens, actual_provider, actual_model = await llm_handler.call_llm_api(
            self.dependencies['STATE']['llm'], prompt,
            # --- MODIFICATION START: Pass user_uuid and session_id ---
            user_uuid=self.user_uuid, session_id=self.session_id,
            # --- MODIFICATION END ---
            dependencies=self.dependencies, reason=reason,
            system_prompt_override=system_prompt_override, raise_on_error=raise_on_error,
            disabled_history=final_disabled_history,
            active_prompt_name_for_filter=active_prompt_name_for_filter,
            source=source
        )
        self.llm_debug_history.append({"reason": reason, "response": response_text})
        app_logger.debug(f"LLM RESPONSE (DEBUG): Reason='{reason}', Response='{response_text}'")

        # --- MODIFICATION START: Update session_manager with actual provider/model ---
        session_manager.update_models_used(self.user_uuid, self.session_id, actual_provider, actual_model)
        # --- MODIFICATION END ---

        self.turn_input_tokens += statement_input_tokens
        self.turn_output_tokens += statement_output_tokens

        return response_text, statement_input_tokens, statement_output_tokens

    async def _get_tool_constraints(self, tool_name: str) -> Tuple[dict, list]:
        """
        Uses an LLM to determine if a tool requires numeric or character columns.
        Returns the constraints and a list of events to be yielded by the caller.
        """
        if tool_name in self.tool_constraints_cache:
            return self.tool_constraints_cache[tool_name], []

        events = []
        tool_definition = self.dependencies['STATE'].get('mcp_tools', {}).get(tool_name)
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
            events.append(self._format_sse({"step": "Calling LLM", "type": "system_message", "details": {"summary": reason, "call_id": call_id}}))

            response_text, input_tokens, output_tokens = await self._call_llm_and_update_tokens(
                prompt=prompt, reason=reason,
                system_prompt_override="You are a JSON-only responding assistant.",
                raise_on_error=True,
                source=self.source
            )

            updated_session = session_manager.get_session(self.user_uuid, self.session_id)
            if updated_session:
                events.append(self._format_sse({
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

        self.tool_constraints_cache[tool_name] = constraints
        return constraints, events

    def _add_to_structured_data(self, tool_result: dict, context_key_override: str = None):
        """Adds tool results to the structured data dictionary."""
        context_key = context_key_override or f"Plan Results: {self.active_prompt_name or 'Ad-hoc'}"
        if context_key not in self.structured_collected_data:
            self.structured_collected_data[context_key] = []

        if isinstance(tool_result, list):
             self.structured_collected_data[context_key].extend(tool_result)
        else:
             self.structured_collected_data[context_key].append(tool_result)
        app_logger.debug(f"Added tool result to structured data under key: '{context_key}'.")

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

    def _find_value_by_key(self, data_structure: any, target_key: str) -> any:
        """Recursively searches a nested data structure for the first value of a given key."""
        if isinstance(data_structure, dict):
            # Check for a direct match, but be case-insensitive for robustness
            for key, value in data_structure.items():
                if key.lower() == target_key.lower():
                    return value

            # If no direct match, recurse into values
            for value in data_structure.values():
                found = self._find_value_by_key(value, target_key)
                if found is not None:
                    return found

        elif isinstance(data_structure, list):
            for item in data_structure:
                found = self._find_value_by_key(item, target_key)
                if found is not None:
                    return found
        return None

    def _unwrap_single_value_from_result(self, data_structure: any) -> any:
        """
        Deterministically unwraps a standard tool result structure to extract a
        single primary value, if one exists.
        """
        is_single_value_structure = (
            isinstance(data_structure, list) and len(data_structure) == 1 and
            isinstance(data_structure[0], dict) and "results" in data_structure[0] and
            isinstance(data_structure[0]["results"], list) and len(data_structure[0]["results"]) == 1 and
            isinstance(data_structure[0]["results"][0], dict) and len(data_structure[0]["results"][0]) == 1
        )

        if is_single_value_structure:
            # Extract the single value from the nested structure
            return next(iter(data_structure[0]["results"][0].values()))

        # If the structure doesn't match, return the original data structure
        return data_structure

    def _resolve_arguments(self, arguments: dict, loop_item: dict = None) -> dict:
        """
        Scans tool arguments for placeholders and resolves them based on the
        current context (workflow state and the optional loop_item).
        """
        if not isinstance(arguments, dict):
            return arguments

        resolved_args = {}

        placeholder_pattern = re.compile(r'(\s*\{[\s\n]*"source":\s*"[^"]+"(?:,[\s\n]*"key":\s*"[^"]+")?[\s\n]*\}\s*)')

        def _resolve_embedded_placeholder(match):
            """Callback function for re.sub to resolve a matched placeholder string."""
            placeholder_str = match.group(1).strip()
            try:
                placeholder_data = json.loads(placeholder_str)
                source_key = placeholder_data.get("source")
                target_key = placeholder_data.get("key")

                data_from_source = None
                if source_key == "loop_item" and loop_item:
                    data_from_source = loop_item
                elif source_key and source_key.startswith("result_of_phase_"):
                    data_from_source = self.workflow_state.get(source_key)
                elif source_key and source_key.startswith("phase_"):
                    data_from_source = self.workflow_state.get(f"result_of_{source_key}")
                elif source_key:
                    data_from_source = self.workflow_state.get(source_key)

                if data_from_source is None:
                    app_logger.warning(f"Could not resolve embedded placeholder: source '{source_key}' not found.")
                    return match.group(1)

                if target_key:
                    found_value = self._find_value_by_key(data_from_source, target_key)
                else:
                    found_value = self._unwrap_single_value_from_result(data_from_source)

                if found_value is not None:
                    app_logger.info(f"Resolved embedded placeholder '{placeholder_str}' to value '{found_value}'.")
                    return str(found_value)
                else:
                    app_logger.warning(f"Could not resolve embedded placeholder: key '{target_key}' not found in source '{source_key}'.")
                    return match.group(1)

            except (json.JSONDecodeError, AttributeError):
                return match.group(1)

        for key, value in arguments.items():
            if isinstance(value, str) and '"source":' in value and not placeholder_pattern.fullmatch(value.strip()):
                resolved_value = placeholder_pattern.sub(_resolve_embedded_placeholder, value)
                resolved_args[key] = resolved_value
                continue

            source_phase_key = None
            target_data_key = None
            is_placeholder = False
            original_placeholder = copy.deepcopy(value)

            if isinstance(value, dict) and value.get("source") == "loop_item" and loop_item:
                loop_key = value.get("key")
                # --- MODIFICATION START ---
                # If a key is specified, get that value. If no key is specified, pass the entire loop_item.
                resolved_args[key] = loop_item.get(loop_key) if loop_key else loop_item
                # --- MODIFICATION END ---
                continue

            if isinstance(value, str):
                match = re.match(r"(result_of_phase_\d+|phase_\d+|injected_previous_turn_data)", value)
                if match:
                    source_phase_key = match.group(1)
                    is_placeholder = True

            elif isinstance(value, dict):
                if "source" in value and "key" in value:
                    source_phase_key = value["source"]
                    target_data_key = value["key"]
                    is_placeholder = True

                elif "source" in value and "key" not in value:
                    source_phase_key = value["source"]
                    target_data_key = None
                    is_placeholder = True
                    self.events_to_yield.append(self._format_sse({
                        "step": "System Correction", "type": "workaround",
                        "details": {
                            "summary": "The agent's plan used an incomplete placeholder. The system will automatically extract the primary value from the source.",
                            "correction_type": "placeholder_unwrapping",
                            "from": original_placeholder,
                            "to": f"Unwrapped value from '{source_phase_key}'"
                        }
                    }))

                else:
                    for k, v in value.items():
                        if re.match(r"result_of_phase_\d+", k):
                            source_phase_key = k
                            target_data_key = v
                            is_placeholder = True

                            canonical_value = {"source": source_phase_key, "key": target_data_key}
                            self.events_to_yield.append(self._format_sse({
                                "step": "System Correction", "type": "workaround",
                                "details": {
                                    "summary": "The agent's plan contained a non-standard placeholder. The system has automatically normalized it to ensure correct data flow.",
                                    "correction_type": "placeholder_normalization",
                                    "from": original_placeholder,
                                    "to": canonical_value
                                }
                            }))
                            value = canonical_value
                            break

            if is_placeholder:
                if source_phase_key and source_phase_key.startswith("phase_"):
                    source_phase_key = f"result_of_{source_phase_key}"

                if source_phase_key in self.workflow_state:
                    data_from_phase = self.workflow_state[source_phase_key]

                    if target_data_key:
                        found_value = self._find_value_by_key(data_from_phase, target_data_key)
                        if found_value is not None:
                            resolved_args[key] = found_value
                        else:
                            app_logger.warning(f"Could not resolve placeholder: key '{target_data_key}' not found in '{source_phase_key}'.")
                            resolved_args[key] = None
                    else:
                        unwrapped_value = self._unwrap_single_value_from_result(data_from_phase)
                        resolved_args[key] = unwrapped_value
                        app_logger.info(f"Resolved placeholder for '{key}' by unwrapping the result of '{source_phase_key}'.")

                else:
                    app_logger.warning(f"Could not resolve placeholder: source '{source_phase_key}' not in workflow state.")
                    resolved_args[key] = value

            elif isinstance(value, dict):
                resolved_args[key] = self._resolve_arguments(value, loop_item)

            elif isinstance(value, list):
                resolved_list = [self._resolve_arguments(item, loop_item) if isinstance(item, dict) else item for item in value]
                resolved_args[key] = resolved_list

            else:
                resolved_args[key] = value

        return resolved_args

    async def _generate_session_name(self, query: str) -> str:
        """
        Uses the LLM to generate a concise name for the session based on the initial query.
        """
        prompt = (
            f"Based on the following user query, generate a concise and descriptive name (3-5 words) "
            f"suitable for a chat session history list. Do not include any punctuation or extra text.\n\n"
            f"User Query: \"{query}\"\n\n"
            f"Session Name:"
        )
        reason = "Generating session name from initial query."
        system_prompt = "You generate short, descriptive titles. Only respond with the title text."

        try:
            name_text, _, _ = await self._call_llm_and_update_tokens(
                prompt=prompt,
                reason=reason,
                system_prompt_override=system_prompt,
                raise_on_error=True,
                disabled_history=True, # Don't need history for naming
                source="system" # Indicate system-initiated call
            )
            # Basic cleaning: remove extra quotes, trim whitespace
            cleaned_name = name_text.strip().strip('"\'')
            if cleaned_name:
                app_logger.info(f"Generated session name: '{cleaned_name}'")
                return cleaned_name
            else:
                app_logger.warning("LLM returned an empty session name.")
                return "New Chat" # Fallback
        except Exception as e:
            app_logger.error(f"Failed to generate session name: {e}", exc_info=True)
            return "New Chat" # Fallback on error


    async def run(self):
        """The main, unified execution loop for the agent."""
        final_answer_override = None
        # --- MODIFICATION START: Calculate turn number once and store on self ---
        self.current_turn_number = 1
        session_data = session_manager.get_session(self.user_uuid, self.session_id)
        if session_data and isinstance(session_data.get("last_turn_data", {}).get("workflow_history"), list):
            self.current_turn_number = len(session_data["last_turn_data"]["workflow_history"]) + 1
        app_logger.info(f"PlanExecutor initialized for turn: {self.current_turn_number}")
        # --- MODIFICATION END ---

        try:
            # --- MODIFICATION START: Handle Replay ---
            if self.plan_to_execute:
                app_logger.info(f"Starting replay execution for user {self.user_uuid}, session {self.session_id}.")
                self.meta_plan = copy.deepcopy(self.plan_to_execute) # Use the provided plan
                self.state = self.AgentState.EXECUTING # Skip planning
                # Inject a status event indicating replay
                replay_type_text = "Optimized" if "optimized" in str(self.is_replay).lower() else "Original" # Basic type check
                # Find the turn ID where this plan originally came from
                original_turn_id = "..." # Default if not found
                if session_data and isinstance(session_data.get("last_turn_data", {}).get("workflow_history"), list):
                    for idx, turn in enumerate(session_data["last_turn_data"]["workflow_history"]):
                        if turn.get("original_plan") == self.plan_to_execute:
                            original_turn_id = str(idx + 1)
                            break

                event_data = {
                    "step": f"🔄 Replaying {replay_type_text} Plan (from Turn {original_turn_id})",
                    "type": "system_message",
                    "details": f"Re-executing {'optimized' if replay_type_text == 'Optimized' else 'original'} plan..."
                }
                self._log_system_event(event_data)
                yield self._format_sse(event_data)
            # --- MODIFICATION END ---
            else:
                if self.is_delegated_task:
                    async for event in self._run_delegated_prompt():
                        yield event
                    return # Exit early for delegated tasks

                # --- Planning Phase ---
                if self.state == self.AgentState.PLANNING:
                    planner = Planner(self)
                    should_replan = False
                    planning_is_disabled_history = self.disabled_history

                    replan_attempt = 0
                    max_replans = 1
                    while True:
                        replan_context = None
                        is_replan = replan_attempt > 0

                        if is_replan:
                            prompts_in_plan = {p['executable_prompt'] for p in (self.meta_plan or []) if 'executable_prompt' in p}
                            granted_prompts_in_plan = {p for p in prompts_in_plan if p in APP_CONFIG.GRANTED_PROMPTS_FOR_EFFICIENCY_REPLANNING}
                            non_granted_prompts_to_deconstruct = {p for p in prompts_in_plan if p not in granted_prompts_in_plan}

                            context_parts = ["\n--- CONTEXT FOR RE-PLANNING ---"]
                            deconstruction_instruction = (
                                "Your previous plan was inefficient because it contained high-level prompts that must be broken down. "
                                "You MUST create a new, more detailed plan that achieves the same overall goal."
                            )
                            context_parts.append(deconstruction_instruction)
                            if granted_prompts_in_plan:
                                preservation_rule = (
                                    f"\n**CRITICAL PRESERVATION RULE:** The following prompts are explicitly granted and you **MUST** "
                                    f"include them as phases in the new plan: `{list(granted_prompts_in_plan)}`. "
                                    "You should rebuild the other parts of the plan around these required steps.\n"
                                )
                                context_parts.append(preservation_rule)
                            if non_granted_prompts_to_deconstruct:
                                deconstruction_directive = (
                                    "\n**CRITICAL REPLANNING DIRECTIVE:** You **MUST** replicate the logical goal of the following discarded prompt(s) "
                                    "using **only basic tools**. To help you, here are their original goals:"
                                )
                                context_parts.append(deconstruction_directive)
                                for prompt_name in non_granted_prompts_to_deconstruct:
                                    prompt_info = self._get_prompt_info(prompt_name)
                                    if prompt_info:
                                        context_parts.append(f"- The goal of the discarded prompt `{prompt_name}` was: \"{prompt_info.get('description', 'No description.')}\"")
                            replan_context = "\n".join(context_parts)

                        async for event in planner.generate_and_refine_plan(
                            force_disable_history=planning_is_disabled_history,
                            replan_context=replan_context
                        ):
                            # --- MODIFICATION START: Capture and log planner corrections ---
                            # Check if the yielded event is a system correction and log it to the history.
                            if "system_correction" in event.lower() or '"type": "workaround"' in event.lower():
                                try:
                                    # The event is a JSON string, parse it.
                                    event_data = json.loads(event.replace("data: ", "").strip())
                                    self.turn_action_history.append({"action": "system_correction", "result": event_data})
                                except json.JSONDecodeError:
                                    app_logger.warning(f"Could not parse planner event for history logging: {event}")
                            # --- MODIFICATION END ---
                            yield event

                        # --- MODIFICATION START: Store original plan AFTER refinement ---
                        # Store the plan that was actually generated and refined before any execution begins
                        self.original_plan_for_history = copy.deepcopy(self.meta_plan)
                        app_logger.debug("Stored original plan (post-refinement) for history.")
                        # --- MODIFICATION END ---

                        plan_has_prompt = self.meta_plan and any('executable_prompt' in phase for phase in self.meta_plan)
                        replan_triggered = False
                        if plan_has_prompt:
                            prompts_in_plan = {phase['executable_prompt'] for phase in self.meta_plan if 'executable_prompt' in phase}
                            non_granted_prompts = [p for p in prompts_in_plan if p not in APP_CONFIG.GRANTED_PROMPTS_FOR_EFFICIENCY_REPLANNING]
                            has_other_significant_tool = any('executable_prompt' not in phase and phase.get('relevant_tools') != ['TDA_LLMTask'] for phase in self.meta_plan)
                            is_single_phase_prompt = len(self.meta_plan) == 1
                            if has_other_significant_tool and not is_single_phase_prompt and non_granted_prompts:
                                replan_triggered = True

                        if self.execution_depth == 0 and replan_triggered and replan_attempt < max_replans:
                            replan_attempt += 1
                            event_data = {
                                "step": "Re-planning for Efficiency", "type": "plan_optimization",
                                "details": {
                                    "summary": "Initial plan uses a sub-prompt alongside other tools. Agent is re-planning to create a more efficient, tool-only workflow.",
                                    "original_plan": copy.deepcopy(self.meta_plan) # Log the plan *before* this replan
                                }
                            }
                            self._log_system_event(event_data)
                            yield self._format_sse(event_data)
                            continue # Loop back to replan
                        break # Exit planning loop

                    # Handle single prompt plan expansion (if applicable)
                    self.is_single_prompt_plan = (self.meta_plan and len(self.meta_plan) == 1 and 'executable_prompt' in self.meta_plan[0] and not self.is_delegated_task)

                    if self.is_single_prompt_plan:
                        async for event in self._handle_single_prompt_plan(planner):
                            yield event
                        # --- MODIFICATION START: Re-capture plan if single prompt expansion happened ---
                        # If the plan was expanded from a single prompt, update the stored original plan
                        self.original_plan_for_history = copy.deepcopy(self.meta_plan)
                        app_logger.debug("Re-stored plan after single-prompt expansion for history.")
                        # --- MODIFICATION END ---


                    # Check for conversational plan
                    if self.is_conversational_plan:
                        app_logger.info("Detected a conversational plan. Bypassing execution.")
                        self.state = self.AgentState.SUMMARIZING
                    else:
                        self.state = self.AgentState.EXECUTING

            # --- Execution Phase ---
            try:
                if self.state == self.AgentState.EXECUTING:
                    async for event in self._run_plan(): yield event
            except DefinitiveToolError as e:
                app_logger.error(f"Execution halted by definitive tool error: {e.friendly_message}")
                event_data = {"step": "Unrecoverable Error", "details": e.friendly_message, "type": "error"}
                self._log_system_event(event_data, "tool_result")
                yield self._format_sse(event_data, "tool_result")
                final_answer_override = f"I could not complete the request. Reason: {e.friendly_message}"
                self.state = self.AgentState.SUMMARIZING # Go to summarization even on error

            # --- Summarization Phase ---
            if self.state == self.AgentState.SUMMARIZING:
                async for event in self._handle_summarization(final_answer_override):
                    yield event

        except asyncio.CancelledError:
            # Handle cancellation specifically
            app_logger.info(f"PlanExecutor execution cancelled for user {self.user_uuid}, session {self.session_id}.")
            self.state = self.AgentState.ERROR # Mark as error to prevent history update
            # Yield a specific event to the frontend
            event_data = {"step": "Execution Stopped", "details": "The process was stopped by the user.", "type": "cancelled"}
            self._log_system_event(event_data, "cancelled")
            yield self._format_sse(event_data, "cancelled")
            # Re-raise so the caller (routes.py) knows it was cancelled
            raise

        except Exception as e:
            # Handle other general exceptions
            root_exception = unwrap_exception(e)
            app_logger.error(f"Error in state {self.state.name} for user {self.user_uuid}, session {self.session_id}: {root_exception}", exc_info=True)
            self.state = self.AgentState.ERROR
            event_data = {"error": "Execution stopped due to an unrecoverable error.", "details": str(root_exception), "step": "Unrecoverable Error", "type": "error"}
            self._log_system_event(event_data, "error")
            yield self._format_sse(event_data, "error")

        finally:
            # --- Cleanup Phase (Always runs) ---
            # --- MODIFICATION START: Only top-level executor (depth 0) saves history ---
            # Update history only if the execution wasn't cancelled, errored,
            # AND this is the top-level executor instance.
            if self.state != self.AgentState.ERROR and self.execution_depth == 0:
            # --- MODIFICATION END ---
                # --- MODIFICATION START: Include model/provider and use self.current_turn_number ---
                turn_summary = {
                    "turn": self.current_turn_number, # Use the authoritative instance variable
                    "user_query": self.original_user_input, # Store the original query
                    "original_plan": self.original_plan_for_history, # Store the actual plan used
                    "execution_trace": self.turn_action_history,
                    "final_summary": self.final_summary_text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "provider": self.current_provider, # Add snapshot of provider
                    "model": self.current_model,       # Add snapshot of model
                    "task_id": self.task_id,            # Add the task_id
                    "turn_input_tokens": self.turn_input_tokens,
                    "turn_output_tokens": self.turn_output_tokens
                }
                # --- MODIFICATION END ---
                session_manager.update_last_turn_data(self.user_uuid, self.session_id, turn_summary)
                app_logger.debug(f"Saved last turn data to session {self.session_id} for user {self.user_uuid}")

                # Session Naming Logic (remains unchanged)
                # --- MODIFICATION START: Use self.current_turn_number for check ---
                if self.current_turn_number == 1 and session_data and session_data.get("name") == "New Chat":
                # --- MODIFICATION END ---
                    app_logger.info(f"First turn detected for session {self.session_id}. Attempting to generate name.")
                    new_name = await self._generate_session_name(self.original_user_input)
                    if new_name != "New Chat":
                        try:
                            session_manager.update_session_name(self.user_uuid, self.session_id, new_name)
                            yield self._format_sse({
                                "session_id": self.session_id,
                                "newName": new_name
                            }, "session_name_update")
                            app_logger.info(f"Successfully updated session {self.session_id} name to '{new_name}'.")
                        except Exception as name_e:
                            app_logger.error(f"Failed to save or emit updated session name '{new_name}': {name_e}", exc_info=True)

            else:
                 # --- MODIFICATION START: Update log message to include depth ---
                 app_logger.info(
                     f"Skipping history save for user {self.user_uuid}, session {self.session_id}. "
                     f"Final state: {self.state.name}, Execution Depth: {self.execution_depth}"
                 )
                 # --- MODIFICATION END ---
    # --- END of run method ---


    async def _handle_single_prompt_plan(self, planner: Planner):
        """Orchestrates the logic for expanding a single-prompt plan."""
        single_phase = self.meta_plan[0]
        prompt_name = single_phase.get('executable_prompt')
        prompt_args = single_phase.get('arguments', {})

        event_data = {
            "step": "System Correction", "type": "workaround",
            "details": f"Single Prompt('{prompt_name}') identified. Expanding plan in-process to improve efficiency."
        }
        self._log_system_event(event_data)
        yield self._format_sse(event_data)

        prompt_info = self._get_prompt_info(prompt_name)
        if prompt_info:
            required_args = {arg['name'] for arg in prompt_info.get('arguments', []) if arg.get('required')}
            missing_args = required_args - set(prompt_args.keys())

            if missing_args:
                event_data = {
                    "step": "System Correction", "type": "workaround",
                    "details": f"Prompt '{prompt_name}' is missing required arguments: {missing_args}. Attempting to extract from user query."
                }
                self._log_system_event(event_data)
                yield self._format_sse(event_data)

                enrichment_prompt = (
                    f"You are an expert argument extractor. From the user's query, extract the values for the following missing arguments: {list(missing_args)}. "
                    f"User Query: \"{self.original_user_input}\"\n"
                    "Respond with only a single, valid JSON object mapping the argument names to their extracted values."
                )
                reason = f"Extracting missing arguments for prompt '{prompt_name}'"

                call_id = str(uuid.uuid4())
                event_data = {
                    "step": "Calling LLM for Argument Enrichment",
                    "type": "system_message",
                    "details": {"summary": reason, "call_id": call_id}
                }
                self._log_system_event(event_data)
                yield self._format_sse(event_data)
                yield self._format_sse({"target": "llm", "state": "busy"}, "status_indicator_update")

                response_text, input_tokens, output_tokens = await self._call_llm_and_update_tokens(
                    prompt=enrichment_prompt, reason=reason,
                    system_prompt_override="You are a JSON-only responding assistant.",
                    raise_on_error=True,
                    source=self.source
                )

                updated_session = session_manager.get_session(self.user_uuid, self.session_id)
                if updated_session:
                    yield self._format_sse({
                        "statement_input": input_tokens, "statement_output": output_tokens,
                        "total_input": updated_session.get("input_tokens", 0),
                        "total_output": updated_session.get("output_tokens", 0),
                        "call_id": call_id
                    }, "token_update")

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

        # Regenerate the plan based on the expanded prompt
        async for event in planner.generate_and_refine_plan():
            yield event

    async def _run_plan(self):
        """Executes the generated meta-plan, delegating to the PhaseExecutor."""
        if not self.meta_plan:
            raise RuntimeError("Cannot execute plan: meta_plan is not generated.")

        phase_executor = PhaseExecutor(self) # Pass self (PlanExecutor instance)

        # Skip final summary check (remains unchanged)
        if not APP_CONFIG.SUB_PROMPT_FORCE_SUMMARY and self.execution_depth > 0 and len(self.meta_plan) > 1:
            last_phase = self.meta_plan[-1]
            last_phase_tools = last_phase.get('relevant_tools', [])
            is_final_report_phase = any(tool in ["TDA_FinalReport", "TDA_ComplexPromptReport"] for tool in last_phase_tools)

            if is_final_report_phase:
                app_logger.info(f"Sub-process (depth {self.execution_depth}) is skipping its final summary phase.")
                event_data = {
                    "step": "Plan Optimization", "type": "plan_optimization",
                    "details": "Sub-process is skipping its final summary task to prevent redundant work. The main process will generate the final report."
                }
                self._log_system_event(event_data)
                yield self._format_sse(event_data)
                self.meta_plan = self.meta_plan[:-1]


        while self.current_phase_index < len(self.meta_plan):
            current_phase = self.meta_plan[self.current_phase_index]
            is_delegated_prompt_phase = 'executable_prompt' in current_phase and self.execution_depth < self.MAX_EXECUTION_DEPTH

            # --- MODIFICATION START: Add replay status prefix ---
            replay_prefix = ""
            if self.is_replay:
                replay_type_text = "Optimized" if "optimized" in str(self.is_replay).lower() else "Original"
                # Find original turn ID (similar logic as in run method)
                original_turn_id = "..."
                session_data = session_manager.get_session(self.user_uuid, self.session_id)
                if session_data and isinstance(session_data.get("last_turn_data", {}).get("workflow_history"), list):
                    for idx, turn in enumerate(session_data["last_turn_data"]["workflow_history"]):
                        if turn.get("original_plan") == self.plan_to_execute: # Compare against the plan being replayed
                            original_turn_id = str(idx + 1)
                            break
                replay_prefix = f"🔄 Replay ({replay_type_text} from Turn {original_turn_id}): "
            # --- MODIFICATION END ---


            if is_delegated_prompt_phase:
                prompt_name = current_phase.get('executable_prompt')
                prompt_args = current_phase.get('arguments', {})
                async for event in self._run_sub_prompt(prompt_name, prompt_args):
                    yield event
            else:
                # --- MODIFICATION START: Pass replay prefix conceptually ---
                # PhaseExecutor needs modification to accept and use this prefix
                # For now, just logging it here. Actual prefixing requires PhaseExecutor changes.
                if replay_prefix:
                    app_logger.debug(f"Passing replay prefix to PhaseExecutor: '{replay_prefix}'")
                async for event in phase_executor.execute_phase(current_phase): # Assuming execute_phase will handle the prefix internally
                    yield event
                # --- MODIFICATION END ---

            self.current_phase_index += 1

        app_logger.debug("Meta-plan has been fully executed. Transitioning to summarization.")
        self.state = self.AgentState.SUMMARIZING

    async def _run_sub_prompt(self, prompt_name: str, prompt_args: dict, is_delegated_task: bool = False):
        """
        Creates and runs a sub-executor for a delegated prompt, adopting its
        final state upon completion to ensure a continuous and complete workflow.
        """
        event_data = {
            "step": "Prompt Execution Granted",
            "details": f"Executing prompt '{prompt_name}' as part of the plan.",
            "type": "workaround"
        }
        self._log_system_event(event_data)
        yield self._format_sse(event_data)

        force_disable_sub_history = is_delegated_task
        if force_disable_sub_history:
            app_logger.info(f"Token Optimization: Disabling history for delegated recovery task '{prompt_name}'.")

        sub_executor = PlanExecutor(
            session_id=self.session_id,
            user_uuid=self.user_uuid,
            original_user_input=f"Executing prompt: {prompt_name}",
            dependencies=self.dependencies,
            active_prompt_name=prompt_name,
            prompt_arguments=prompt_args,
            execution_depth=self.execution_depth + 1,
            disabled_history=self.disabled_history or force_disable_sub_history,
            previous_turn_data=self.previous_turn_data,
            source="prompt_library",
            is_delegated_task=is_delegated_task,
            force_final_summary=APP_CONFIG.SUB_PROMPT_FORCE_SUMMARY
        )

        sub_executor.workflow_state = self.workflow_state
        sub_executor.structured_collected_data = self.structured_collected_data



        async for event in sub_executor.run():
            yield event

        self.structured_collected_data = sub_executor.structured_collected_data
        self.workflow_state = sub_executor.workflow_state
        
        # --- MODIFICATION START: Append sub-trace, don't overwrite ---
        if sub_executor.turn_action_history:
            self.turn_action_history.extend(sub_executor.turn_action_history)
        # --- MODIFICATION END ---
            
        self.last_tool_output = sub_executor.last_tool_output
        


        if sub_executor.state == self.AgentState.ERROR:
            app_logger.error(f"Sub-executor for prompt '{prompt_name}' failed.")
            if not self.last_tool_output or self.last_tool_output.get("status") != "error":
                self.last_tool_output = {"status": "error", "error_message": f"Sub-prompt '{prompt_name}' failed."}
        else:
             if self.last_tool_output is None:
                self.last_tool_output = {"status": "success"}

    async def _run_delegated_prompt(self):
        """
        Executes a single, delegated prompt by immediately expanding it into a
        concrete plan. This is used for sub-executors created during
        self-correction to avoid redundant planning and recursion.
        """
        if not self.active_prompt_name:
            app_logger.error("Delegated task started without an active_prompt_name.")
            self.state = self.AgentState.ERROR
            return

        planner = Planner(self)
        app_logger.info(f"Delegated task: Directly expanding prompt '{self.active_prompt_name}' into a concrete plan.")

        async for event in planner.generate_and_refine_plan():
            yield event
        # --- MODIFICATION START: Store plan for history even in delegated ---
        # Ensure the plan generated for the delegated task is also stored
        self.original_plan_for_history = copy.deepcopy(self.meta_plan)
        app_logger.info("Stored delegated prompt plan for history.")
        # --- MODIFICATION END ---


        self.state = self.AgentState.EXECUTING
        async for event in self._run_plan():
            yield event

    async def _handle_summarization(self, final_answer_override: str | None):
        """Orchestrates the final summarization and answer formatting."""
        final_content = None

        # Summarization logic remains largely the same
        if self.is_synthesis_from_history:
            app_logger.info("Bypassing summarization. Using direct synthesized answer from planner.")
            synthesized_answer = "Could not extract synthesized answer."
            if self.last_tool_output and isinstance(self.last_tool_output.get("results"), list) and self.last_tool_output["results"]:
                synthesized_answer = self.last_tool_output["results"][0].get("response", synthesized_answer)
            final_content = CanonicalResponse(direct_answer=synthesized_answer)
        elif self.execution_depth > 0 and not self.force_final_summary:
            app_logger.info(f"Sub-planner (depth {self.execution_depth}) completed. Bypassing final summary.")
            self.state = self.AgentState.DONE
        elif final_answer_override:
            final_content = CanonicalResponse(direct_answer=final_answer_override)
        elif self.is_conversational_plan:
            response_text = self.temp_data_holder or "I'm sorry, I don't have a response for that."
            final_content = CanonicalResponse(direct_answer=response_text)
        elif self.last_tool_output and self.last_tool_output.get("status") == "success":
            results = self.last_tool_output.get("results", [{}])
            if not results:
                final_content = CanonicalResponse(direct_answer="The agent has completed its work, but the final step produced no data.")
            else:
                last_result = results[0]
                tool_name = self.last_tool_output.get("metadata", {}).get("tool_name")

                if self.active_prompt_name and tool_name == "TDA_ComplexPromptReport":
                    final_content = PromptReportResponse.model_validate(last_result)
                elif tool_name == "TDA_FinalReport":
                    final_content = CanonicalResponse.model_validate(last_result)
                else:
                    final_content = CanonicalResponse(direct_answer="The agent has completed its work, but a final report was not generated.")
        else:
            final_content = CanonicalResponse(direct_answer="The agent has completed its work, but an issue occurred in the final step.")

        if final_content:
            async for event in self._format_and_yield_final_answer(final_content):
                yield event
            self.state = self.AgentState.DONE

    async def _format_and_yield_final_answer(self, final_content: CanonicalResponse | PromptReportResponse):
        """
        Formats a raw summary string OR a CanonicalResponse object and yields
        the final SSE event to the UI. Also saves the final HTML to session history.
        Includes the turn number in the final event payload.
        """
        formatter_kwargs = {
            "collected_data": self.structured_collected_data,
            "original_user_input": self.original_user_input,
            "active_prompt_name": self.active_prompt_name
        }
        if isinstance(final_content, PromptReportResponse):
            formatter_kwargs["prompt_report_response"] = final_content
        else:
            formatter_kwargs["canonical_response"] = final_content

        formatter = OutputFormatter(**formatter_kwargs)
        final_html, tts_payload = formatter.render()

        # --- MODIFICATION START: Decouple UI and LLM history ---
        # First, determine the clean text summary for the LLM
        clean_summary_for_llm = "The agent has completed its work."
        if hasattr(final_content, 'direct_answer'):
            clean_summary_for_llm = final_content.direct_answer
        elif hasattr(final_content, 'executive_summary'):
            clean_summary_for_llm = final_content.executive_summary
        
        # Store this clean summary in self.final_summary_text *before* saving
        self.final_summary_text = clean_summary_for_llm

        # Now, save both versions to their respective histories
        session_manager.add_message_to_histories(
            self.user_uuid,
            self.session_id,
            'assistant',
            content=self.final_summary_text, # Clean text for LLM's chat_object
            html_content=final_html          # Rich HTML for UI's session_history
        )
        # --- MODIFICATION END ---

        # The clean summary is already in self.final_summary_text
        event_data = {"step": "LLM has generated the final answer", "details": self.final_summary_text}
        self._log_system_event(event_data, "llm_thought")
        yield self._format_sse(event_data, "llm_thought")

        # --- MODIFICATION START: Use self.current_turn_number ---
        # Remove the separate, buggy calculation and use the instance variable
        yield self._format_sse({
            "final_answer": final_html,
            "tts_payload": tts_payload,
            "source": self.source,
            "turn_id": self.current_turn_number # Use the authoritative instance variable
        }, "final_answer")
        # --- MODIFICATION END ---
