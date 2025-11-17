# src/trusted_data_agent/core/session_manager.py
import uuid
import os
import json
import logging
from datetime import datetime
from pathlib import Path # Use pathlib for better path handling
import shutil # For potential cleanup later if needed
import asyncio # For sending notifications asynchronously

import google.generativeai as genai
from trusted_data_agent.agent.prompts import PROVIDER_SYSTEM_PROMPTS
# --- MODIFICATION START: Import APP_CONFIG ---
from trusted_data_agent.core.config import APP_STATE, APP_CONFIG
from trusted_data_agent.core.utils import generate_session_id # Import generate_session_id
# --- MODIFICATION END ---


# --- Define SESSIONS_DIR relative to project root ---
# Assume this script is in src/trusted_data_agent/core
# Go up three levels to get to the project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
SESSIONS_DIR = _PROJECT_ROOT / "tda_sessions"


app_logger = logging.getLogger("quart.app") # Use quart logger for consistency

def _initialize_sessions_dir():
    """Creates the main sessions directory if it doesn't exist."""
    try:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        app_logger.info(f"Session directory ensured at: {SESSIONS_DIR}")
    except OSError as e:
        app_logger.error(f"Could not create session directory '{SESSIONS_DIR}'. Session persistence will fail. Error: {e}", exc_info=True)
        raise # Re-raise to prevent startup if dir fails

# Call initialization when the module loads
_initialize_sessions_dir()

# --- Removed global _SESSIONS dictionary ---

# --- File I/O Helper Functions ---

def _get_session_path(user_uuid: str, session_id: str) -> Path | None:
    """Constructs the session file path and performs basic validation."""
    if not user_uuid or not session_id:
        app_logger.error("Attempted to get session path with missing user_uuid or session_id.")
        return None
    # Basic sanitization (replace potentially harmful chars - adjust as needed)
    safe_user_uuid = "".join(c for c in user_uuid if c.isalnum() or c in ['-', '_'])
    safe_session_id = "".join(c for c in session_id if c.isalnum() or c in ['-', '_'])
    if safe_user_uuid != user_uuid or safe_session_id != session_id:
        app_logger.warning(f"Sanitized UUID/SessionID for path. Original: '{user_uuid}/{session_id}', Safe: '{safe_user_uuid}/{safe_session_id}'")

    return SESSIONS_DIR / safe_user_uuid / f"{safe_session_id}.json"

def _load_session(user_uuid: str, session_id: str) -> dict | None:
    """Loads session data from a file."""
    session_path = _get_session_path(user_uuid, session_id)
    if not session_path:
        return None
    app_logger.debug(f"Attempting to load session from: {session_path}")
    try:
        if session_path.is_file():
            with open(session_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                app_logger.debug(f"Successfully loaded session '{session_id}' for user '{user_uuid}'.")
                return data
        else:
            app_logger.warning(f"Session file not found at: {session_path}")
            return None
    except (json.JSONDecodeError, OSError) as e:
        app_logger.error(f"Error loading session file '{session_path}': {e}", exc_info=True)
        return None # Return None on error

def _save_session(user_uuid: str, session_id: str, session_data: dict):
    """Saves session data to a file, creating directories if needed."""
    session_data['last_updated'] = datetime.now().isoformat()
    session_path = _get_session_path(user_uuid, session_id)
    if not session_path:
        app_logger.error(f"Cannot save session '{session_id}' for user '{user_uuid}': Invalid path.")
        return False # Indicate failure
    app_logger.debug(f"Attempting to save session to: {session_path}")
    try:
        # Ensure the user's directory exists
        session_path.parent.mkdir(parents=True, exist_ok=True)
        if not session_path.parent.exists():
             app_logger.warning(f"User session directory was just created (or failed silently): {session_path.parent}")

        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2) # Use indent for readability
        app_logger.debug(f"Successfully saved session '{session_id}' for user '{user_uuid}'.")

        # --- MODIFICATION START: Send session_model_update notification ---
        notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
        if notification_queues:
            notification_payload = {
                "session_id": session_id,
                "models_used": session_data.get("models_used", []),
                "last_updated": session_data.get("last_updated"),
                "provider": session_data.get("provider"),
                "model": session_data.get("model"),
                "name": session_data.get("name", "Unnamed Session"),
            }
            app_logger.debug(f"_save_session sending notification for session {session_id}: provider={notification_payload['provider']}, model={notification_payload['model']}")
            notification = {
                "type": "session_model_update",
                "payload": notification_payload
            }
            for queue in notification_queues:
                asyncio.create_task(queue.put(notification))
        # --- MODIFICATION END ---

        return True # Indicate success
    except OSError as e:
        app_logger.error(f"Error saving session file '{session_path}': {e}", exc_info=True)
        return False # Indicate failure


# --- Public Session Management Functions ---

def create_session(user_uuid: str, provider: str, llm_instance: any, charting_intensity: str, system_prompt_template: str | None = None) -> str:
    session_id = generate_session_id()
    app_logger.info(f"Attempting to create session '{session_id}' for user '{user_uuid}'.")

    # Note: chat_object cannot be directly serialized to JSON.
    # We will store history as a plain list.
    chat_history_for_file = []
    if provider == "Google":
        # Keep initial prompt for Google compatibility if needed later, but don't store the live object.
        initial_history_google = [
            {"role": "user", "parts": [{"text": "You are a helpful assistant."}]},
            {"role": "model", "parts": [{"text": "Understood."}]}
        ]
        # Store this initial history in the file version
        chat_history_for_file = [{'role': m['role'], 'content': m['parts'][0]['text']} for m in initial_history_google]

    session_data = {
        "id": session_id, # Store ID within the data itself
        "user_uuid": user_uuid, # Store user UUID for potential later use/verification
        "system_prompt_template": system_prompt_template,
        "charting_intensity": charting_intensity,
        "provider": provider, # --- Store the provider used for this session
        "model": APP_CONFIG.CURRENT_MODEL, # --- Store the model used for this session
        "models_used": [], # --- Initialize as empty for a new session
        "session_history": [], # UI history (messages added via add_message_to_histories)
        "chat_object": chat_history_for_file, # Store serializable history for LLM context
        "name": "New Chat",
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "input_tokens": 0,
        "output_tokens": 0,
        # --- MODIFICATION START: Ensure workflow_history list exists on creation ---
        "last_turn_data": {"workflow_history": []},
        # --- MODIFICATION END ---
        "full_context_sent": False,
        "license_info": APP_STATE.get("license_info") # Store license info at creation time
    }

    if _save_session(user_uuid, session_id, session_data):
        app_logger.info(f"Successfully created and saved session '{session_id}' for user '{user_uuid}'.")
        return session_id
    else:
        app_logger.error(f"Failed to save newly created session '{session_id}' for user '{user_uuid}'.")
        raise IOError(f"Failed to save session file for session {session_id}")


def get_session(user_uuid: str, session_id: str) -> dict | None:
    app_logger.debug(f"Getting session '{session_id}' for user '{user_uuid}'.")
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        history_modified = False
        # --- MODIFICATION START: Update backfill logic for turn numbers ---
        if "session_history" in session_data and session_data["session_history"]:
            if session_data["session_history"] and "turn_number" not in session_data["session_history"][0]:
                app_logger.info(f"Session {session_id} history is outdated. Adding turn numbers.")
                history_modified = True
                turn_counter = 0
                for msg in session_data["session_history"]:
                    if msg.get("role") == "user":
                        turn_counter += 1
                    msg["turn_number"] = turn_counter

        if "chat_object" in session_data and session_data["chat_object"]:
            if session_data["chat_object"] and "turn_number" not in session_data["chat_object"][0]:
                if not history_modified:
                    app_logger.info(f"Session {session_id} chat_object is outdated. Adding turn numbers.")
                history_modified = True
                turn_counter = 0
                # Skip the initial system message which doesn't have a turn
                for i, msg in enumerate(session_data["chat_object"]):
                    # The first two messages are the system prompt and should not be part of a turn
                    if i < 2:
                        msg["turn_number"] = 0
                        continue
                    if msg.get("role") == "user":
                        turn_counter += 1
                    msg["turn_number"] = turn_counter

        if history_modified:
            app_logger.info(f"Saving session {session_id} after migrating to include turn numbers.")
            _save_session(user_uuid, session_id, session_data)

    return session_data

def get_all_sessions(user_uuid: str) -> list[dict]:
    app_logger.debug(f"Getting all sessions for user '{user_uuid}'.")
    user_session_dir = SESSIONS_DIR / "".join(c for c in user_uuid if c.isalnum() or c in ['-', '_'])
    app_logger.debug(f"Scanning directory: {user_session_dir}")
    session_summaries = []
    if not user_session_dir.is_dir():
        app_logger.warning(f"User session directory not found: {user_session_dir}. Returning empty list.")
        return [] # Return empty list if user directory doesn't exist

    for session_file in user_session_dir.glob("*.json"):
        app_logger.debug(f"Found potential session file: {session_file.name}")
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                # Load only necessary fields for summary to improve performance
                data = json.load(f)
                summary = {
                    "id": data.get("id", session_file.stem),
                    "name": data.get("name", "Unnamed Session"),
                    "created_at": data.get("created_at", "Unknown"),
                    "models_used": data.get("models_used", []),
                    "last_updated": data.get("last_updated", data.get("created_at", "Unknown"))
                }
                app_logger.debug(f"Loaded summary for {session_file.name}: models_used={summary['models_used']}")
                session_summaries.append(summary)
                app_logger.debug(f"Successfully loaded summary for {session_file.name}.")
        except (json.JSONDecodeError, OSError, KeyError) as e:
            app_logger.error(f"Error loading summary from session file '{session_file}': {e}", exc_info=False) # Keep log concise
            # Optionally add a placeholder or skip corrupted files
            session_summaries.append({
                 "id": session_file.stem,
                 "name": f"Error Loading ({session_file.stem})",
                 "created_at": "Unknown"
            })


    def sort_key(session):
        created_at = session.get("created_at", "")
        if created_at == "Unknown" or not created_at:
            return datetime.min.isoformat()
        return created_at

    session_summaries.sort(key=sort_key, reverse=True)
    app_logger.debug(f"Returning {len(session_summaries)} session summaries for user '{user_uuid}'.")
    return session_summaries

def delete_session(user_uuid: str, session_id: str) -> bool:
    """Deletes a session file from the filesystem."""
    session_path = _get_session_path(user_uuid, session_id)
    if not session_path:
        app_logger.error(f"Cannot delete session '{session_id}' for user '{user_uuid}': Invalid path generated.")
        return False # Indicate failure due to invalid path

    app_logger.info(f"Attempting to delete session file: {session_path}")
    try:
        if session_path.is_file():
            session_path.unlink()
            app_logger.info(f"Successfully deleted session file: {session_path}")
            return True # Indicate success
        else:
            app_logger.warning(f"Session file not found for deletion: {session_path}. Treating as success (already gone).")
            return True # Indicate success (idempotent delete)
    except OSError as e:
        app_logger.error(f"Error deleting session file '{session_path}': {e}", exc_info=True)
        return False # Indicate failure due to OS error

# --- MODIFICATION START: Rename and refactor add_to_history ---
def add_message_to_histories(user_uuid: str, session_id: str, role: str, content: str, html_content: str | None = None, source: str | None = None):
    """
    Adds a message to the appropriate histories, decoupling UI from LLM context.
    - `content` (plain text) is *always* added to the LLM's chat_object.
    - `html_content` (if provided) is added to the UI's session_history.
    - If `html_content` is not provided, `content` is used for the UI.
    """
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        # --- 1. Add to UI History (session_history) ---
        # Use the rich HTML content if provided, otherwise fall back to plain text.
        ui_content = html_content if html_content is not None else content
        
        # --- MODIFICATION START: Explicitly manage turn_number ---
        session_history = session_data.setdefault('session_history', [])
        
        # Determine the next turn number
        next_turn_number = 1
        if session_history:
            last_message = session_history[-1]
            last_turn_number = last_message.get('turn_number', 0) # Default to 0 if not found
            # Increment turn number only when a new user message is added
            if role == 'user':
                next_turn_number = last_turn_number + 1
            else: # Assistant's turn
                next_turn_number = last_turn_number
        
        message_to_append = {
            'role': role,
            'content': ui_content,
            'isValid': True,
            'turn_number': next_turn_number,
        }

        if source:
             message_to_append['source'] = source
        
        session_history.append(message_to_append)
        # --- MODIFICATION END ---

        # --- 2. Add to LLM History (chat_object) ---
        # Determine the correct role for the LLM provider
        provider_in_session = session_data.get("license_info", {}).get("provider")
        current_provider = APP_CONFIG.CURRENT_PROVIDER
        provider = provider_in_session or current_provider
        if not provider:
             app_logger.warning(f"Could not determine LLM provider for role conversion in session {session_id}. Defaulting role.")
             provider = "Unknown" # Avoid error if APP_CONFIG isn't set somehow

        llm_role = 'model' if role == 'assistant' and provider == 'Google' else role
        
        # --- MODIFICATION START: Explicitly manage turn_number for chat_object ---
        chat_object_history = session_data.setdefault('chat_object', [])

        # Determine the next turn number for the LLM history
        llm_turn_number = 1
        if chat_object_history:
            last_llm_message = chat_object_history[-1]
            last_llm_turn = last_llm_message.get('turn_number', 0) # Default to 0
            # Increment only on the user's turn for the next cycle
            if llm_role == 'user':
                llm_turn_number = last_llm_turn + 1
            else: # Model's turn
                llm_turn_number = last_llm_turn

        # *Always* add the clean, plain text `content` to the LLM's history.
        chat_object_history.append({
            'role': llm_role,
            'content': content,
            'isValid': True,
            'turn_number': llm_turn_number
        })
        # --- MODIFICATION END ---
        # --- MODIFICATION END ---

        if not _save_session(user_uuid, session_id, session_data):
             app_logger.error(f"Failed to save session after adding history for {session_id}")
    else:
        app_logger.warning(f"Could not add history: Session {session_id} not found for user {user_uuid}.")

def update_session_name(user_uuid: str, session_id: str, new_name: str):
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        session_data['name'] = new_name
        if not _save_session(user_uuid, session_id, session_data):
             app_logger.error(f"Failed to save session after updating name for {session_id}")
        else:
            # --- MODIFICATION START: Send session_name_update notification ---
            notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
            if notification_queues:
                notification_payload = {
                    "session_id": session_id,
                    "newName": new_name,
                }
                app_logger.debug(f"update_session_name sending notification for session {session_id}: newName={new_name}")
                notification = {
                    "type": "session_name_update",
                    "payload": notification_payload
                }
                for queue in notification_queues:
                    asyncio.create_task(queue.put(notification))
            # --- MODIFICATION END ---
    else:
         app_logger.warning(f"Could not update name: Session {session_id} not found for user {user_uuid}.")


def update_token_count(user_uuid: str, session_id: str, input_tokens: int, output_tokens: int):
    """Updates the token counts for a given session."""
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        session_data['input_tokens'] = session_data.get('input_tokens', 0) + input_tokens
        session_data['output_tokens'] = session_data.get('output_tokens', 0) + output_tokens
        if not _save_session(user_uuid, session_id, session_data):
            app_logger.error(f"Failed to save session after updating tokens for {session_id}")
    else:
        app_logger.warning(f"Could not update tokens: Session {session_id} not found for user {user_uuid}.")


def update_models_used(user_uuid: str, session_id: str, provider: str, model: str):
    """Adds the current model to the list of models used in the session."""
    app_logger.debug(f"update_models_used called for session {session_id} with provider={provider}, model={model}")
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        models_used = session_data.get('models_used', [])
        model_string = f"{provider}/{model}"
        if model_string not in models_used:
            models_used.append(model_string)
            session_data['models_used'] = models_used

        # --- MODIFICATION START: Update top-level provider and model ---
        app_logger.debug(f"Updating session_data provider from {session_data.get('provider')} to {provider}")
        app_logger.debug(f"Updating session_data model from {session_data.get('model')} to {model}")
        session_data['provider'] = provider
        session_data['model'] = model
        # --- MODIFICATION END ---

        if not _save_session(user_uuid, session_id, session_data):
            app_logger.error(f"Failed to save session after updating models used for {session_id}")
    else:
        app_logger.warning(f"Could not update models used: Session {session_id} not found for user {user_uuid}.")


def update_last_turn_data(user_uuid: str, session_id: str, turn_data: dict):
    """Saves the most recent turn's action history and plans to the session file."""
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        # Ensure the structure exists (already done on creation, but good for robustness)
        if "last_turn_data" not in session_data:
            session_data["last_turn_data"] = {}
        if "workflow_history" not in session_data["last_turn_data"] or not isinstance(session_data["last_turn_data"]["workflow_history"], list):
            session_data["last_turn_data"]["workflow_history"] = []
        
        # --- MODIFICATION START: Add isValid=True for new turns ---
        # By default, all new turns are valid.
        if isinstance(turn_data, dict):
            turn_data["isValid"] = True
        # --- MODIFICATION END ---

        # Append the new turn data (contains original_plan and user_query now)
        session_data["last_turn_data"]["workflow_history"].append(turn_data)

        if not _save_session(user_uuid, session_id, session_data):
            app_logger.error(f"Failed to save session after updating last turn data for {session_id}")
    else:
        app_logger.warning(f"Could not update last turn data: Session {session_id} not found for user {user_uuid}.")

# --- MODIFICATION START: Add function to purge only the agent's memory ---
def purge_session_memory(user_uuid: str, session_id: str) -> bool:
    """
    Resets the agent's LLM context memory (`chat_object`) for a session,
    but leaves the UI history (`session_history`) and plan/trace history
    (`last_turn_data`) intact.
    """
    app_logger.info(f"Attempting to purge agent memory (chat_object) for session '{session_id}', user '{user_uuid}'.")
    session_data = _load_session(user_uuid, session_id)
    if not session_data:
        app_logger.warning(f"Could not purge memory: Session {session_id} not found for user {user_uuid}.")
        return False # Session not found

    try:
        # --- MODIFICATION START: Mark all existing history as invalid ---
        # This makes the "purge" a persistent archival event.

        # 1. Mark UI history (session_history) as invalid
        session_history = session_data.get('session_history', [])
        history_count = 0
        if isinstance(session_history, list):
            for msg in session_history:
                if isinstance(msg, dict):
                    msg["isValid"] = False
                    history_count += 1
        
        # 2. Mark backend turn data (workflow_history) as invalid
        workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])
        turn_count = 0
        if isinstance(workflow_history, list):
            for turn in workflow_history:
                if isinstance(turn, dict):
                    turn["isValid"] = False
                    turn_count += 1
        
        app_logger.info(f"Marked {history_count} UI messages and {turn_count} turns as invalid for session '{session_id}'.")
        # --- MODIFICATION END ---

        # Determine the correct initial state for chat_object
        # This mirrors the logic in create_session
        chat_history_for_file = []
        provider_in_session = session_data.get("license_info", {}).get("provider")
        current_provider = APP_CONFIG.CURRENT_PROVIDER
        provider = provider_in_session or current_provider or "Google" # Default to Google logic if unknown

        if provider == "Google":
            initial_history_google = [
                {"role": "user", "parts": [{"text": "You are a helpful assistant."}]},
                {"role": "model", "parts": [{"text": "Understood."}]}
            ]
            chat_history_for_file = [{'role': m['role'], 'content': m['parts'][0]['text']} for m in initial_history_google]
        
        # Reset *only* the chat_object
        session_data['chat_object'] = chat_history_for_file
        
        # Also reset the full_context_sent flag so the agent sends the full system prompt next time
        session_data['full_context_sent'] = False

        app_logger.info(f"Successfully reset chat_object for session '{session_id}'. Invalidated existing history.")

        if not _save_session(user_uuid, session_id, session_data):
            app_logger.error(f"Failed to save session after purging memory for {session_id}")
            return False # Save failed
        
        return True # Success

    except Exception as e:
        app_logger.error(f"An unexpected error occurred during memory purge for session '{session_id}': {e}", exc_info=True)
# --- MODIFICATION END ---

# --- MODIFICATION START: Add function to toggle turn validity ---
def toggle_turn_validity(user_uuid: str, session_id: str, turn_id: int) -> bool:
    """
    Toggles the 'isValid' status of a specific turn and its corresponding
    UI messages in the session history.
    """
    app_logger.info(f"Toggling validity for turn {turn_id} in session '{session_id}' for user '{user_uuid}'.")
    session_data = _load_session(user_uuid, session_id)
    if not session_data:
        app_logger.warning(f"Could not toggle validity: Session {session_id} not found.")
        return False

    try:
        # 1. Toggle validity in workflow_history
        workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])
        turn_found = False
        new_status = None
        if isinstance(workflow_history, list):
            for turn in workflow_history:
                if isinstance(turn, dict) and turn.get("turn") == turn_id:
                    current_status = turn.get("isValid", True)
                    new_status = not current_status
                    turn["isValid"] = new_status
                    turn_found = True
                    app_logger.info(f"Found turn {turn_id} in workflow_history. Set isValid to {new_status}.")
                    break
        
        if not turn_found:
            app_logger.warning(f"Turn {turn_id} not found in workflow_history for session {session_id}.")
            return False # If the planner's source of truth can't be updated, fail fast

        # 2. Toggle validity in session_history (for the UI)
        session_history = session_data.get('session_history', [])
        if isinstance(session_history, list):
            assistant_message_count = 0
            for i, msg in enumerate(session_history):
                if isinstance(msg, dict) and msg.get('role') == 'assistant':
                    assistant_message_count += 1
                    if assistant_message_count == turn_id:
                        msg['isValid'] = new_status
                        if i > 0 and session_history[i-1].get('role') == 'user':
                            session_history[i-1]['isValid'] = new_status
                        app_logger.info(f"Updated messages in session_history for turn {turn_id} to isValid={new_status}.")
                        break

        if not _save_session(user_uuid, session_id, session_data):
            app_logger.error(f"Failed to save session after toggling validity for turn {turn_id}")
            return False

        return True

    except Exception as e:
        app_logger.error(f"An unexpected error occurred during validity toggle for turn {turn_id}: {e}", exc_info=True)
        return False
# --- MODIFICATION END ---

# --- MODIFICATION START: Add function to update turn feedback ---
def update_turn_feedback(user_uuid: str, session_id: str, turn_id: int, vote: str | None) -> bool:
    """
    Updates the feedback (upvote/downvote) for a specific turn in the workflow_history.
    
    Args:
        user_uuid: The user's UUID
        session_id: The session ID
        turn_id: The turn number to update
        vote: 'up', 'down', or None to clear the vote
    
    Returns:
        True if successful, False otherwise
    """
    try:
        session_data = _load_session(user_uuid, session_id)
        if not session_data:
            app_logger.warning(f"Could not update feedback: Session {session_id} not found for user {user_uuid}.")
            return False

        # Get workflow_history from last_turn_data
        workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])
        
        # Find the turn with matching turn number
        turn_found = False
        for turn in workflow_history:
            if turn.get("turn") == turn_id:
                # Update or remove feedback field
                if vote is None:
                    turn.pop("feedback", None)
                else:
                    turn["feedback"] = vote
                turn_found = True
                app_logger.info(f"Updated feedback for turn {turn_id} in session {session_id}: {vote}")
                break
        
        if not turn_found:
            app_logger.warning(f"Turn {turn_id} not found in workflow_history for session {session_id}")
            return False

        # Save the updated session data
        if not _save_session(user_uuid, session_id, session_data):
            app_logger.error(f"Failed to save session after updating feedback for turn {turn_id}")
            return False

        return True

    except Exception as e:
        app_logger.error(f"Error updating feedback for turn {turn_id}: {e}", exc_info=True)
        return False
# --- MODIFICATION END ---
