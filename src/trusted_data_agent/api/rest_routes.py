# src/trusted_data_agent/api/rest_routes.py
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
import re

# --- MODIFICATION START: Import abort ---
from quart import Blueprint, current_app, jsonify, request, abort
# --- MODIFICATION END ---

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.core import session_manager
from trusted_data_agent.agent import execution_service
from trusted_data_agent.core import configuration_service

from trusted_data_agent.agent.executor import PlanExecutor

rest_api_bp = Blueprint('rest_api', __name__)
app_logger = logging.getLogger("quart.app") # Use quart logger

# --- MODIFICATION START: Helper to get User UUID (copied from routes.py) ---
def _get_user_uuid_from_request():
    """Extracts the User UUID from the request header."""
    user_uuid = request.headers.get('X-TDA-User-UUID')
    if not user_uuid:
        app_logger.warning("REST API: Missing X-TDA-User-UUID header in request.")
        abort(400, "Missing required X-TDA-User-UUID header.")
    return user_uuid
# --- MODIFICATION END ---

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

@rest_api_bp.route("/v1/configure", methods=["POST"])
async def configure_services_rest():
    """
    Configures and validates the core LLM and MCP services via the REST API.
    This is a protected, atomic operation that uses the centralized
    configuration service.
    """
    # Configuration is global, no user UUID needed.
    config_data = await request.get_json()
    if not config_data:
        return jsonify({"status": "error", "message": "Request body must be a valid JSON."}), 400

    result = await configuration_service.setup_and_categorize_services(config_data)

    if result.get("status") == "success":
        # --- MODIFICATION START: Broadcast reconfiguration notification ---
        # Create a copy of the config to sanitize it for notification
        safe_config = config_data.copy()
        if "credentials" in safe_config:
            safe_config["credentials"] = {k: v for k, v in safe_config["credentials"].items() if "key" not in k.lower() and "token" not in k.lower()}
        if "tts_credentials_json" in safe_config:
            del safe_config["tts_credentials_json"]

        notification = {
            "type": "reconfiguration",
            "payload": {
                "message": "Application has been reconfigured via REST API. A refresh is required.",
                "config": safe_config
            }
        }

        # Broadcast to all active notification queues
        all_queues = [q for user_queues in APP_STATE.get("notification_queues", {}).values() for q in user_queues]
        app_logger.info(f"Found {len(all_queues)} active notification queues.")
        if all_queues:
            app_logger.info(f"Broadcasting reconfiguration notification to {len(all_queues)} client(s).")
            for queue in all_queues:
                asyncio.create_task(queue.put(notification))
        # --- MODIFICATION END ---
        return jsonify(result), 200
    else:
        # Configuration errors are client-side problems (bad keys, wrong host, etc.)
        # so a 400-level error is more appropriate than a 500.
        return jsonify(result), 400

@rest_api_bp.route("/v1/sessions", methods=["POST"])
async def create_session():
    """Creates a new conversation session *for the requesting user*."""
    # --- MODIFICATION START: Get User UUID ---
    user_uuid = _get_user_uuid_from_request()
    # --- MODIFICATION END ---

    if not APP_CONFIG.MCP_SERVER_CONNECTED:
        return jsonify({
            "error": "Application is not configured. Please connect to LLM and MCP services first."
        }), 503

    try:
        llm_instance = APP_STATE.get("llm")

        # --- MODIFICATION START: Pass User UUID ---
        session_id = session_manager.create_session(
            user_uuid=user_uuid, # Pass the UUID
            provider=APP_CONFIG.CURRENT_PROVIDER,
            llm_instance=llm_instance,
            charting_intensity=APP_CONFIG.DEFAULT_CHARTING_INTENSITY
            # system_prompt_template is not typically passed via REST API for creation
        )
        app_logger.info(f"REST API: Created new session: {session_id} for user {user_uuid}")

        # Retrieve the newly created session's full data
        new_session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
        if new_session_data:
            # Prepare notification payload
            notification_payload = {
                "id": new_session_data["id"],
                "name": new_session_data.get("name", "New Chat"), # Default name if not present
                "models_used": new_session_data.get("models_used", []),
                "last_updated": new_session_data.get("last_updated", datetime.now(timezone.utc).isoformat())
            }

            # Broadcast to all active notification queues for this user
            notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
            if notification_queues:
                app_logger.info(f"Broadcasting new_session_created notification to {len(notification_queues)} client(s) for user {user_uuid}.")
                notification = {
                    "type": "new_session_created",
                    "payload": notification_payload
                }
                for queue in notification_queues:
                    asyncio.create_task(queue.put(notification))
        else:
            app_logger.warning(f"REST API: Could not retrieve full session data for new session {session_id} for user {user_uuid}.")

        return jsonify({"session_id": session_id}), 201
    except Exception as e:
        app_logger.error(f"Failed to create REST session for user {user_uuid}: {e}", exc_info=True)
        return jsonify({"error": "Failed to create session."}), 500

@rest_api_bp.route("/v1/sessions/<session_id>/query", methods=["POST"])
async def execute_query(session_id: str):
    """Submits a query to a session and starts a background task *for the requesting user*."""
    # --- MODIFICATION START: Get User UUID ---
    user_uuid = _get_user_uuid_from_request()
    # --- MODIFICATION END ---

    data = await request.get_json()
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "The 'prompt' field is required."}), 400

    # --- MODIFICATION START: Validate session for this user ---
    if not session_manager.get_session(user_uuid, session_id):
        app_logger.warning(f"REST API: Session '{session_id}' not found for user '{user_uuid}'.")
        return jsonify({"error": f"Session '{session_id}' not found."}), 404
    # --- MODIFICATION END ---

    task_id = f"task-{uuid.uuid4()}"

    # Initialize the task state
    APP_STATE.setdefault("background_tasks", {})[task_id] = {
        "task_id": task_id,
        "user_uuid": user_uuid, # Store the user UUID with the task
        "session_id": session_id, # Store session ID for reference
        "status": "pending",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "events": [],
        "intermediate_data": [],
        "result": None
    }

    async def event_handler(event_data, event_type):
        """This handler is called by the execution service for each event."""
        task_status_dict = APP_STATE["background_tasks"].get(task_id)
        sanitized_event_data = _sanitize_for_json(event_data)

        # 1. Update the persistent task state (for polling clients)
        if task_status_dict:
            task_status_dict["events"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_data": sanitized_event_data,
                "event_type": event_type
            })
            if event_type == "tool_result" and isinstance(sanitized_event_data, dict):
                details = sanitized_event_data.get("details", {})
                if isinstance(details, dict) and details.get("status") == "success" and "results" in details:
                    task_status_dict["intermediate_data"].append({
                        "tool_name": details.get("metadata", {}).get("tool_name", "unknown_tool"),
                        "data": details["results"]
                    })
            task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

        # 2. Create and send a canonical event to the UI notification stream
        notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
        if notification_queues:
            try:
                # Use the application's own formatter to guarantee a canonical event object
                sse_message_str = PlanExecutor._format_sse(sanitized_event_data, event_type)
                
                # Extract the JSON part from the "data: ..." line
                json_payload_str = None
                for line in sse_message_str.strip().split('\n'):
                    if line.startswith('data:'):
                        json_payload_str = line[5:].strip()
                        break
                
                if json_payload_str:
                    # The extracted part is a JSON string, so we load it into a Python dict
                    canonical_event = json.loads(json_payload_str)
                    
                    # --- MODIFICATION START: Handle session_name_update as a top-level event ---
                    # --- MODIFICATION START: Handle status_indicator_update directly ---
                    if event_type == "status_indicator_update":
                        notification = {
                            "type": "status_indicator_update",
                            "payload": canonical_event # canonical_event already contains target and state
                        }
                        app_logger.debug(f"REST API: Emitting status_indicator_update for task {task_id}: {notification}")
                    # --- MODIFICATION END ---
                    elif event_type == "session_name_update":
                        notification = {
                            "type": "session_name_update",
                            "payload": canonical_event # Payload already contains session_id and newName
                        }
                    else:
                        notification = {
                            "type": "rest_task_update",
                            "payload": {
                                "task_id": task_id,
                                "session_id": session_id,
                                "event": canonical_event
                            }
                        }
                    # --- MODIFICATION END ---
                    for queue in notification_queues:
                        asyncio.create_task(queue.put(notification))
                else:
                    app_logger.warning(f"Could not extract JSON payload from SSE message for event type {event_type}")

            except Exception as e:
                app_logger.error(f"Failed to format or send canonical event for REST task {task_id}: {e}", exc_info=True)

    async def background_wrapper():
        """Wraps the execution to handle context, final state updates, and notifications."""
        task_status_dict = APP_STATE["background_tasks"].get(task_id)
        final_result_payload = None
        try:
            if task_status_dict: task_status_dict["status"] = "processing"

            final_result_payload = await execution_service.run_agent_execution(
                user_uuid=user_uuid,
                session_id=session_id,
                user_input=prompt,
                event_handler=event_handler,
                source='rest' # Identify source as REST
            )

            if task_status_dict:
                task_status_dict["status"] = "complete"
                task_status_dict["result"] = _sanitize_for_json(final_result_payload)
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

        except asyncio.CancelledError:
            app_logger.info(f"REST background task {task_id} (user {user_uuid}) was cancelled.")
            if task_status_dict:
                task_status_dict["status"] = "cancelled"
                task_status_dict["result"] = {"message": "Task cancelled by user."}
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            app_logger.error(f"Background task {task_id} (user {user_uuid}) failed: {e}", exc_info=True)
            if task_status_dict:
                task_status_dict["status"] = "error"
                task_status_dict["result"] = {"error": str(e)}
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
        finally:
            # Remove from ACTIVE tasks registry
            if task_id in APP_STATE.get("active_tasks", {}):
                del APP_STATE["active_tasks"][task_id]

            # Send final notification to UI clients on success
            if final_result_payload and task_status_dict and task_status_dict.get("status") == "complete":
                notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
                if notification_queues:
                    completion_notification = {
                        "type": "rest_task_complete",
                        "payload": {
                            "task_id": task_id,
                            "session_id": session_id,
                            "turn_id": final_result_payload.get("turn_id"),
                            "user_input": prompt,
                            "final_answer": final_result_payload.get("final_answer")
                        }
                    }
                    app_logger.info(f"Sending rest_task_complete notification for user {user_uuid}")
                    for queue in notification_queues:
                        asyncio.create_task(queue.put(completion_notification))

            app_logger.info(f"Background task {task_id} (user {user_uuid}) finished with status: {task_status_dict.get('status', 'unknown') if task_status_dict else 'unknown'}")

    # Start the agent execution in the background
    task_object = asyncio.create_task(background_wrapper())
    # Store the actual task object for potential cancellation (uses task_id)
    APP_STATE.setdefault("active_tasks", {})[task_id] = task_object

    status_url = f"/api/v1/tasks/{task_id}"

    return jsonify({"task_id": task_id, "status_url": status_url}), 202

@rest_api_bp.route("/v1/tasks/<task_id>", methods=["GET"])
async def get_task_status(task_id: str):
    """Gets the status and results of a background task."""
    # --- MODIFICATION START: Get User UUID and optionally check ownership ---
    user_uuid = _get_user_uuid_from_request()
    task = APP_STATE["background_tasks"].get(task_id)

    if not task:
        app_logger.warning(f"REST API: Task '{task_id}' not found for user '{user_uuid}'.")
        return jsonify({"error": f"Task '{task_id}' not found."}), 404

    # Optional: Check if the requesting user owns this task
    if task.get("user_uuid") != user_uuid:
        app_logger.error(f"REST API: User '{user_uuid}' attempted to access task '{task_id}' owned by user '{task.get('user_uuid')}'.")
        return jsonify({"error": "Access denied to this task."}), 403
    # --- MODIFICATION END ---

    # Exclude user_uuid from the response payload if desired
    # response_task = task.copy()
    # response_task.pop("user_uuid", None)
    # return jsonify(response_task)
    return jsonify(task)


@rest_api_bp.route("/v1/tasks/<task_id>/cancel", methods=["POST"])
async def cancel_task(task_id: str):
    """Cancels an active background task initiated via the REST API *by the requesting user*."""
    # --- MODIFICATION START: Get User UUID and check task ownership ---
    user_uuid = _get_user_uuid_from_request()
    task_status_dict = APP_STATE["background_tasks"].get(task_id)

    if not task_status_dict:
        app_logger.warning(f"REST API: Cancel failed. Task '{task_id}' not found for user '{user_uuid}'.")
        return jsonify({"error": f"Task '{task_id}' not found."}), 404

    if task_status_dict.get("user_uuid") != user_uuid:
        app_logger.error(f"REST API: User '{user_uuid}' attempted to cancel task '{task_id}' owned by user '{task_status_dict.get('user_uuid')}'. Denying.")
        return jsonify({"error": "Access denied: You cannot cancel a task you did not start."}), 403
    # --- MODIFICATION END ---

    active_tasks = APP_STATE.get("active_tasks", {})
    task_object = active_tasks.get(task_id) # Get the asyncio.Task object

    if task_object and not task_object.done():
        app_logger.info(f"Received REST request from user {user_uuid} to cancel task {task_id}.")
        task_object.cancel()
        # Remove immediately from active tasks dict
        if task_id in active_tasks:
             del active_tasks[task_id]
        # Update the status in the background_tasks dict as well
        task_status_dict["status"] = "cancelling" # Or "cancelled" immediately
        task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

        return jsonify({"status": "success", "message": "Cancellation request sent."}), 200
    elif task_object and task_object.done():
        app_logger.info(f"REST cancellation request for task {task_id} (user {user_uuid}) ignored: task already completed.")
        if task_id in active_tasks:
             del active_tasks[task_id]
        # Ensure final status reflects completion if missed
        if task_status_dict.get("status") not in ["complete", "error", "cancelled"]:
             task_status_dict["status"] = "complete" # Or infer from result if possible
        return jsonify({"status": "info", "message": "Task already completed."}), 200
    else:
        # Task might exist in background_tasks but not in active_tasks if already finished/cancelled
        current_status = task_status_dict.get("status", "unknown")
        if current_status in ["complete", "error", "cancelled"]:
             app_logger.info(f"REST cancellation request for task {task_id} (user {user_uuid}) ignored: task already finished with status '{current_status}'.")
             return jsonify({"status": "info", "message": f"Task already finished ({current_status})."}), 200
        else:
            app_logger.warning(f"REST cancellation request for task {task_id} (user {user_uuid}) failed: No active asyncio task found, status is '{current_status}'.")
            return jsonify({"status": "error", "message": "No active running task found for this task ID."}), 404
