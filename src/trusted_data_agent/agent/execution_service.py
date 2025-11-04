# src/trusted_data_agent/agent/execution_service.py
import logging
import json
import re

from trusted_data_agent.agent.executor import PlanExecutor
from trusted_data_agent.core.config import APP_STATE
from trusted_data_agent.core import session_manager

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

# --- MODIFICATION START: Add plan_to_execute and is_replay parameters ---
async def run_agent_execution(
    user_uuid: str,
    session_id: str,
    user_input: str,
    event_handler,
    active_prompt_name: str = None,
    prompt_arguments: dict = None,
    disabled_history: bool = False,
    source: str = "text",
    plan_to_execute: list = None, # Added optional plan
    is_replay: bool = False # Added replay flag
):
# --- MODIFICATION END ---
    """
    The central, abstracted service for running the PlanExecutor.
    """
    final_result_payload = None
    try:
        session_data = session_manager.get_session(user_uuid, session_id)

        if not session_data:
             app_logger.error(f"Execution service: Session {session_id} not found for user {user_uuid}.")
             await event_handler({"error": f"Session '{session_id}' not found."}, "error")
             return None # Indicate failure

        # Send an event with the latest model usage
        await event_handler({
            "session_id": session_id,
            "models_used": session_data.get("models_used", []),
            "last_updated": session_data.get("last_updated", session_data.get("created_at"))
        }, "session_model_update")

        # Save the user's message to the history used for UI rendering.
        # --- MODIFICATION START: Only add user input if not a replay ---
        # Don't add user input again if we are replaying a previous query
        if user_input and not is_replay:
            # --- MODIFICATION START: Use add_message_to_histories ---
            session_manager.add_message_to_histories(
                user_uuid,
                session_id,
                'user',
                user_input,
                html_content=None # User input is plain text for both
            )
            # --- MODIFICATION END ---
            app_logger.debug(f"Added user input to session_history for {session_id}")
        # --- MODIFICATION END ---

        previous_turn_data = session_data.get("last_turn_data", {})

        # --- MODIFICATION START: Pass new parameters to PlanExecutor ---
        executor = PlanExecutor(
            user_uuid=user_uuid,
            session_id=session_id,
            original_user_input=user_input,
            dependencies={'STATE': APP_STATE},
            active_prompt_name=active_prompt_name,
            prompt_arguments=prompt_arguments,
            disabled_history=disabled_history,
            previous_turn_data=previous_turn_data,
            source=source,
            plan_to_execute=plan_to_execute, # Pass the plan
            is_replay=is_replay # Pass the flag
        )
        # --- MODIFICATION END ---

        async for event_str in executor.run():
            event_data, event_type = _parse_sse_event(event_str)
            await event_handler(event_data, event_type)

            if event_type == "final_answer":
                final_result_payload = event_data

    except Exception as e:
        app_logger.error(f"An unhandled error occurred in the agent execution service for user {user_uuid}, session {session_id}: {e}", exc_info=True)
        await event_handler({"error": str(e)}, "error")
        raise

    return final_result_payload
