# src/trusted_data_agent/api/rest_routes.py
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
import re

from quart import Blueprint, current_app, jsonify, request

# --- MODIFICATION START: Direct import of APP_CONFIG, APP_STATE and session_manager ---
from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.core import session_manager
# --- MODIFICATION END ---
from trusted_data_agent.agent import execution_service

rest_api_bp = Blueprint('rest_api', __name__)
app_logger = logging.getLogger("main")

def _sanitize_for_json(obj):
    """
    Recursively sanitizes an object to make it JSON-serializable by removing
    non-printable characters from strings.
    """
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(elem) for elem in obj]
    elif isinstance(obj, str):
        # Remove ASCII control characters (0x00-0x1F), except for newline,
        # carriage return, and tab, which are valid in JSON strings.
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', obj)
    else:
        return obj

@rest_api_bp.route("/v1/sessions", methods=["POST"])
async def create_session():
    """Creates a new conversation session."""
    if not APP_CONFIG.MCP_SERVER_CONNECTED:
        return jsonify({
            "error": "Application is not configured. Please connect to LLM and MCP services first."
        }), 503

    try:
        # --- MODIFICATION START: Access llm instance directly from APP_STATE ---
        llm_instance = APP_STATE.get("llm")
        # --- MODIFICATION END ---
        
        session_id = session_manager.create_session(
            provider=APP_CONFIG.CURRENT_PROVIDER,
            llm_instance=llm_instance,
            charting_intensity=APP_CONFIG.DEFAULT_CHARTING_INTENSITY
        )
        app_logger.info(f"REST API: Created new session: {session_id}")
        return jsonify({"session_id": session_id}), 201
    except Exception as e:
        app_logger.error(f"Failed to create REST session: {e}", exc_info=True)
        return jsonify({"error": "Failed to create session."}), 500

@rest_api_bp.route("/v1/sessions/<session_id>/query", methods=["POST"])
async def execute_query(session_id: str):
    """Submits a query to a session and starts a background task."""
    data = await request.get_json()
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "The 'prompt' field is required."}), 400

    if not session_manager.get_session(session_id):
        return jsonify({"error": f"Session '{session_id}' not found."}), 404

    task_id = f"task-{uuid.uuid4()}"
    
    # Initialize the task state
    # --- MODIFICATION START: Use the direct APP_STATE import ---
    APP_STATE["background_tasks"][task_id] = {
    # --- MODIFICATION END ---
        "task_id": task_id,
        "status": "pending",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "events": [],
        "intermediate_data": [],
        "result": None
    }

    async def event_handler(event_data, event_type):
        """This handler is called by the execution service for each event."""
        # --- MODIFICATION START: Use the direct APP_STATE import ---
        task = APP_STATE["background_tasks"].get(task_id)
        # --- MODIFICATION END ---
        if task:
            sanitized_event = _sanitize_for_json(event_data)
            
            task["events"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_data": sanitized_event,
                "event_type": event_type
            })

            if event_type == "tool_result" and isinstance(sanitized_event, dict):
                details = sanitized_event.get("details", {})
                if isinstance(details, dict) and details.get("status") == "success" and "results" in details:
                    task["intermediate_data"].append({
                        "tool_name": details.get("metadata", {}).get("tool_name", "unknown_tool"),
                        "data": details["results"]
                    })
            
            task["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    async def background_wrapper():
        """Wraps the execution to handle context and final state updates."""
        # --- MODIFICATION START: Use the direct APP_STATE import ---
        task = APP_STATE["background_tasks"].get(task_id)
        # --- MODIFICATION END ---
        try:
            async with current_app.app_context():
                task["status"] = "processing"
                final_result_payload = await execution_service.run_agent_execution(
                    session_id=session_id,
                    user_input=prompt,
                    event_handler=event_handler
                )
                if task:
                    task["status"] = "complete"
                    task["result"] = _sanitize_for_json(final_result_payload)
                    task["last_updated"] = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            app_logger.error(f"Background task {task_id} failed: {e}", exc_info=True)
            if task:
                task["status"] = "error"
                task["result"] = {"error": str(e)}
                task["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    # Start the agent execution in the background
    asyncio.create_task(background_wrapper())

    status_url = f"/api/v1/tasks/{task_id}"
    return jsonify({"task_id": task_id, "status_url": status_url}), 202

@rest_api_bp.route("/v1/tasks/<task_id>", methods=["GET"])
async def get_task_status(task_id: str):
    """Gets the status and results of a background task."""
    # --- MODIFICATION START: Use the direct APP_STATE import ---
    task = APP_STATE["background_tasks"].get(task_id)
    # --- MODIFICATION END ---

    if not task:
        return jsonify({"error": f"Task '{task_id}' not found."}), 404
    
    return jsonify(task)
