# src/trusted_data_agent/core/session_manager.py
import uuid
import os
import json
import logging
from datetime import datetime
from pathlib import Path # Use pathlib for better path handling
import shutil # For potential cleanup later if needed

import google.generativeai as genai
from trusted_data_agent.agent.prompts import PROVIDER_SYSTEM_PROMPTS
# --- MODIFICATION START: Import APP_CONFIG ---
from trusted_data_agent.core.config import APP_STATE, APP_CONFIG
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
        return True # Indicate success
    except OSError as e:
        app_logger.error(f"Error saving session file '{session_path}': {e}", exc_info=True)
        return False # Indicate failure


# --- Public Session Management Functions ---

def create_session(user_uuid: str, provider: str, llm_instance: any, charting_intensity: str, system_prompt_template: str | None = None) -> str:
    session_id = str(uuid.uuid4())
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
        "session_history": [], # UI history (messages added via add_to_history)
        "chat_object": chat_history_for_file, # Store serializable history for LLM context
        "name": "New Chat",
        "created_at": datetime.now().isoformat(),
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
    return _load_session(user_uuid, session_id)

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
                    "id": data.get("id", session_file.stem), # Use filename stem as fallback ID
                    "name": data.get("name", "Unnamed Session"),
                    "created_at": data.get("created_at", "Unknown")
                }
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


    session_summaries.sort(key=lambda x: x.get("created_at", ""), reverse=True)
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

def add_to_history(user_uuid: str, session_id: str, role: str, content: str):
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        session_data.setdefault('session_history', []).append({'role': role, 'content': content})
        provider_in_session = session_data.get("license_info", {}).get("provider")
        current_provider = APP_CONFIG.CURRENT_PROVIDER
        provider = provider_in_session or current_provider
        if not provider:
             app_logger.warning(f"Could not determine LLM provider for role conversion in session {session_id}. Defaulting role.")
             provider = "Unknown" # Avoid error if APP_CONFIG isn't set somehow

        llm_role = 'model' if role == 'assistant' and provider == 'Google' else role
        session_data.setdefault('chat_object', []).append({'role': llm_role, 'content': content})

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


def update_last_turn_data(user_uuid: str, session_id: str, turn_data: dict):
    """Saves the most recent turn's action history and plans to the session file."""
    session_data = _load_session(user_uuid, session_id)
    if session_data:
        # Ensure the structure exists (already done on creation, but good for robustness)
        if "last_turn_data" not in session_data:
            session_data["last_turn_data"] = {}
        if "workflow_history" not in session_data["last_turn_data"] or not isinstance(session_data["last_turn_data"]["workflow_history"], list):
            session_data["last_turn_data"]["workflow_history"] = []

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
        # Determine the correct initial state for chat_object based on the provider
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

        app_logger.info(f"Successfully reset chat_object for session '{session_id}'. Preserving session_history and last_turn_data.")

        if not _save_session(user_uuid, session_id, session_data):
            app_logger.error(f"Failed to save session after purging memory for {session_id}")
            return False # Save failed
        
        return True # Success

    except Exception as e:
        app_logger.error(f"An unexpected error occurred during memory purge for session '{session_id}': {e}", exc_info=True)
        return False
# --- MODIFICATION END ---
