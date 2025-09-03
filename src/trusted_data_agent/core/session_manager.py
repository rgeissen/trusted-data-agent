# trusted_data_agent/core/session_manager.py
import uuid
from datetime import datetime

import google.generativeai as genai
from trusted_data_agent.agent.prompts import PROVIDER_SYSTEM_PROMPTS
from trusted_data_agent.core.config import APP_STATE

_SESSIONS = {}

def create_session(provider: str, llm_instance: any, charting_intensity: str, system_prompt_template: str | None = None) -> str:
    session_id = str(uuid.uuid4())
    
    # MODIFICATION: The system_prompt_template is now passed in.
    # For standard users, this will be None, and the LLM handler will use the server's default.
    # For privileged users, this will be their custom prompt from the client.
    
    chat_object = None
    if provider == "Google":
        initial_history = [
            {"role": "user", "parts": [{"text": "You are a helpful assistant."}]},
            {"role": "model", "parts": [{"text": "Understood."}]}
        ]
        if isinstance(llm_instance, genai.GenerativeModel):
             chat_object = llm_instance.start_chat(history=initial_history)
    else:
        chat_object = []

    _SESSIONS[session_id] = {
        "system_prompt_template": system_prompt_template,
        "charting_intensity": charting_intensity,
        "session_history": [],
        "chat_object": chat_object,
        "name": "New Chat",
        "created_at": datetime.now().isoformat(),
        "input_tokens": 0,
        "output_tokens": 0,
        "last_turn_data": [],
        # MODIFICATION: Store the user's license info in the session.
        "license_info": APP_STATE.get("license_info")
    }
    return session_id

def get_session(session_id: str) -> dict | None:
    return _SESSIONS.get(session_id)

def get_all_sessions() -> list[dict]:
    session_summaries = [
        {"id": sid, "name": s_data["name"], "created_at": s_data["created_at"]}
        for sid, s_data in _SESSIONS.items()
    ]
    session_summaries.sort(key=lambda x: x["created_at"], reverse=True)
    return session_summaries

def add_to_history(session_id: str, role: str, content: str):
    if session_id in _SESSIONS:
        _SESSIONS[session_id]['session_history'].append({'role': role, 'content': content})

def update_session_name(session_id: str, new_name: str):
    if session_id in _SESSIONS:
        _SESSIONS[session_id]['name'] = new_name

def get_session_history(session_id: str) -> list | None:
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]['session_history']
    return None

def update_token_count(session_id: str, input_tokens: int, output_tokens: int):
    """Updates the token counts for a given session."""
    if session_id in _SESSIONS:
        _SESSIONS[session_id]['input_tokens'] += input_tokens
        _SESSIONS[session_id]['output_tokens'] += output_tokens

def update_last_turn_data(session_id: str, turn_data: list):
    """Saves the most recent turn's action history to the session."""
    if session_id in _SESSIONS:
        _SESSIONS[session_id]['last_turn_data'] = turn_data
