# src/trusted_data_agent/agent/execution_service.py
import logging
import json
import re

# --- MODIFICATION START: Remove Quart import ---
# from quart import current_app # No longer needed
# --- MODIFICATION END ---

from trusted_data_agent.agent.executor import PlanExecutor
from trusted_data_agent.core.config import APP_STATE
# --- MODIFICATION START: Import add_to_history ---
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
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                app_logger.warning(f"Could not decode event JSON: {line}")
                data = {"raw_content": line[5:].strip()}
        elif line.startswith('event:'):
            event_type = line[6:].strip()
    return data, event_type

# --- MODIFICATION START: Add user_uuid parameter ---
async def run_agent_execution(
    user_uuid: str, # Added user_uuid
    session_id: str,
    user_input: str,
    event_handler,
    active_prompt_name: str = None,
    prompt_arguments: dict = None,
    disabled_history: bool = False,
    source: str = "text"
    # replay parameters will be added later
):
# --- MODIFICATION END ---
    """
    The central, abstracted service for running the PlanExecutor.
    """
    final_result_payload = None
    try:
        # --- MODIFICATION START: Pass user_uuid to get_session ---
        session_data = session_manager.get_session(user_uuid, session_id)
        # --- MODIFICATION END ---

        # Check if session exists *after* trying to load it
        if not session_data:
             app_logger.error(f"Execution service: Session {session_id} not found for user {user_uuid}.")
             # Raise an error that the caller (routes/rest_routes) can catch
             # Or handle the error by sending an SSE event and returning
             await event_handler({"error": f"Session '{session_id}' not found."}, "error")
             return None # Indicate failure

        # --- MODIFICATION START: Add user input to session_history ---
        # Save the user's message to the history used for UI rendering.
        if user_input: # Only save if there's actual input
            session_manager.add_to_history(user_uuid, session_id, 'user', user_input)
            app_logger.debug(f"Added user input to session_history for {session_id}")
        # --- MODIFICATION END ---

        previous_turn_data = session_data.get("last_turn_data", {})

        # --- MODIFICATION START: Pass user_uuid to PlanExecutor ---
        executor = PlanExecutor(
            user_uuid=user_uuid, # Pass the user UUID
            session_id=session_id,
            original_user_input=user_input,
            dependencies={'STATE': APP_STATE},
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
        app_logger.error(f"An unhandled error occurred in the agent execution service for user {user_uuid}, session {session_id}: {e}", exc_info=True)
        # Ensure the handler is called with the error information
        await event_handler({"error": str(e)}, "error")
        # Re-raise the exception so the caller (e.g., REST background task) knows it failed
        raise

    return final_result_payload
