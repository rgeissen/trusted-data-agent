# src/trusted_data_agent/agent/execution_service.py
import logging
import json
import re

from quart import current_app

from trusted_data_agent.agent.executor import PlanExecutor
# --- MODIFICATION START: Direct import of APP_STATE and session_manager ---
from trusted_data_agent.core.config import APP_STATE
from trusted_data_agent.core import session_manager
# --- MODIFICATION END ---


app_logger = logging.getLogger("quart.app")


def _parse_sse_event(event_str: str) -> tuple[dict, str]:
    """
    Parses a raw SSE event string into its data and event type.
    """
    data = {}
    event_type = None
    for line in event_str.strip().split('\n'):
        if line.startswith('data:'):
            try:
                # Strip "data:" prefix and load JSON
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                app_logger.warning(f"Could not decode event JSON: {line}")
                # Fallback for non-json data lines if necessary
                data = {"raw_content": line[5:].strip()}
        elif line.startswith('event:'):
            event_type = line[6:].strip()
    return data, event_type

# --- MODIFICATION START: Update function signature to accept all necessary arguments ---
async def run_agent_execution(
    session_id: str,
    user_input: str,
    event_handler,
    active_prompt_name: str = None,
    prompt_arguments: dict = None,
    disabled_history: bool = False,
    source: str = "text"
):
# --- MODIFICATION END ---
    """
    The central, abstracted service for running the PlanExecutor.
    """
    final_result_payload = None
    try:
        # --- MODIFICATION START: Use direct imports instead of current_app ---
        session_data = session_manager.get_session(session_id)
        previous_turn_data = session_data.get("last_turn_data", {}) if session_data else {}
        
        executor = PlanExecutor(
            session_id=session_id,
            original_user_input=user_input,
            dependencies={'STATE': APP_STATE},
            # Pass through all optional arguments
            active_prompt_name=active_prompt_name,
            prompt_arguments=prompt_arguments,
            disabled_history=disabled_history,
            previous_turn_data=previous_turn_data,
            source=source
        )
        # --- MODIFICATION END ---

        async for event_str in executor.run():
            event_data, event_type = _parse_sse_event(event_str)
            await event_handler(event_data, event_type)

            if event_type == "final_answer":
                final_result_payload = event_data

    except Exception as e:
        app_logger.error(f"An unhandled error occurred in the agent execution service: {e}", exc_info=True)
        # Ensure the handler is called with the error information
        await event_handler({"error": str(e)}, "error")
        # Re-raise the exception so the caller (e.g., REST background task) knows it failed
        raise

    return final_result_payload

