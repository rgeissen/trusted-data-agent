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
# --- MODIFICATION START: Import the new configuration service ---
from trusted_data_agent.core import configuration_service
# --- MODIFICATION END ---

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

# --- MODIFICATION START: Add the new /configure endpoint ---
@rest_api_bp.route("/v1/configure", methods=["POST"])
async def configure_services_rest():
    """
    Configures and validates the core LLM and MCP services via the REST API.
    This is a protected, atomic operation that uses the centralized
    configuration service.
    """
    config_data = await request.get_json()
    if not config_data:
        return jsonify({"status": "error", "message": "Request body must be a valid JSON."}), 400

    result = await configuration_service.setup_and_categorize_services(config_data)

    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        # Configuration errors are client-side problems (bad keys, wrong host, etc.)
        # so a 400-level error is more appropriate than a 500.
        return jsonify(result), 400
# --- MODIFICATION END ---

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
        task_status_dict = APP_STATE["background_tasks"].get(task_id) # Renamed to avoid confusion with the asyncio task object
        # --- MODIFICATION END ---
        if task_status_dict:
            sanitized_event = _sanitize_for_json(event_data)

            task_status_dict["events"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_data": sanitized_event,
                "event_type": event_type
            })

            if event_type == "tool_result" and isinstance(sanitized_event, dict):
                details = sanitized_event.get("details", {})
                if isinstance(details, dict) and details.get("status") == "success" and "results" in details:
                    task_status_dict["intermediate_data"].append({
                        "tool_name": details.get("metadata", {}).get("tool_name", "unknown_tool"),
                        "data": details["results"]
                    })

            task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

    async def background_wrapper():
        """Wraps the execution to handle context and final state updates."""
        # --- MODIFICATION START: Use the direct APP_STATE import ---
        task_status_dict = APP_STATE["background_tasks"].get(task_id) # Renamed
        # --- MODIFICATION END ---
        try:
            async with current_app.app_context():
                task_status_dict["status"] = "processing"
                final_result_payload = await execution_service.run_agent_execution(
                    session_id=session_id,
                    user_input=prompt,
                    event_handler=event_handler
                )
                if task_status_dict:
                    task_status_dict["status"] = "complete"
                    task_status_dict["result"] = _sanitize_for_json(final_result_payload)
                    task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

        except asyncio.CancelledError:
            # --- MODIFICATION START: Handle cancellation in REST task ---
            app_logger.info(f"REST background task {task_id} was cancelled.")
            if task_status_dict:
                task_status_dict["status"] = "cancelled"
                task_status_dict["result"] = {"message": "Task cancelled by user."}
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
            # --- MODIFICATION END ---
        except Exception as e:
            app_logger.error(f"Background task {task_id} failed: {e}", exc_info=True)
            if task_status_dict:
                task_status_dict["status"] = "error"
                task_status_dict["result"] = {"error": str(e)}
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
        finally:
             # --- MODIFICATION START: Ensure task is removed from ACTIVE tasks registry ---
             if task_id in APP_STATE.get("active_tasks", {}):
                 del APP_STATE["active_tasks"][task_id]
             # --- MODIFICATION END ---

    # --- MODIFICATION START: Store the asyncio.Task object ---
    # Start the agent execution in the background
    task_object = asyncio.create_task(background_wrapper())
    # Store the actual task object for potential cancellation
    APP_STATE.setdefault("active_tasks", {})[task_id] = task_object
    # --- MODIFICATION END ---

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

# --- MODIFICATION START: Add new cancellation endpoint ---
@rest_api_bp.route("/v1/tasks/<task_id>/cancel", methods=["POST"])
async def cancel_task(task_id: str):
    """Cancels an active background task initiated via the REST API."""
    active_tasks = APP_STATE.get("active_tasks", {})
    task_object = active_tasks.get(task_id) # Get the asyncio.Task object

    if task_object and not task_object.done():
        app_logger.info(f"Received REST request to cancel task {task_id}.")
        task_object.cancel()
        # Remove immediately from active tasks dict
        if task_id in active_tasks:
             del active_tasks[task_id]
        # Update the status in the background_tasks dict as well
        if task_id in APP_STATE["background_tasks"]:
            APP_STATE["background_tasks"][task_id]["status"] = "cancelling" # Or "cancelled" immediately
            APP_STATE["background_tasks"][task_id]["last_updated"] = datetime.now(timezone.utc).isoformat()

        return jsonify({"status": "success", "message": "Cancellation request sent."}), 200
    elif task_object and task_object.done():
        app_logger.info(f"REST cancellation request for task {task_id} ignored: task already completed.")
        # Clean up if the finally block somehow missed it
        if task_id in active_tasks:
             del active_tasks[task_id]
        return jsonify({"status": "info", "message": "Task already completed."}), 200
    else:
        app_logger.warning(f"REST cancellation request for task {task_id} failed: No active task found.")
        return jsonify({"status": "error", "message": "No active task found for this task ID."}), 404
# --- MODIFICATION END ---
