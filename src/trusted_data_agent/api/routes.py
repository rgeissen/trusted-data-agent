# src/trusted_data_agent/api/routes.py
import json
import os
import logging
import asyncio
import sys
import copy
import hashlib
import httpx

from quart import Blueprint, request, jsonify, render_template, Response, abort
from langchain_mcp_adapters.prompts import load_mcp_prompt

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.core import session_manager
from trusted_data_agent.agent.prompts import PROVIDER_SYSTEM_PROMPTS
from trusted_data_agent.agent.executor import PlanExecutor
from trusted_data_agent.llm import handler as llm_handler
from trusted_data_agent.agent import execution_service
from trusted_data_agent.core import configuration_service
from trusted_data_agent.core.utils import (
    get_tts_client,
    synthesize_speech,
    unwrap_exception,
    _get_prompt_info,
    _regenerate_contexts
)


api_bp = Blueprint('api', __name__)
app_logger = logging.getLogger("quart.app")

def _get_user_uuid_from_request():
    """Extracts User UUID from request header or aborts."""
    user_uuid = request.headers.get("X-TDA-User-UUID")
    if not user_uuid:
        app_logger.error("Missing X-TDA-User-UUID header in request.")
        abort(400, description="X-TDA-User-UUID header is required.")
    return user_uuid


@api_bp.route("/")
async def index():
    """Serves the main HTML page."""
    return await render_template("index.html")

@api_bp.route("/api/status")
async def get_application_status():
    """
    Returns the current configuration status of the application.
    This is used by the front end on startup to synchronize its state.
    It now respects the CONFIGURATION_PERSISTENCE flag.
    """
    if not APP_CONFIG.CONFIGURATION_PERSISTENCE:
        app_logger.info("Configuration persistence is disabled by environment setting. Forcing re-configuration.")
        return jsonify({"isConfigured": False})

    is_configured = APP_CONFIG.SERVICES_CONFIGURED
    app_logger.debug(f"API endpoint /api/status checked. Current configured status: {is_configured}")

    if is_configured:
        status_payload = {
            "isConfigured": True,
            "provider": APP_CONFIG.ACTIVE_PROVIDER,
            "model": APP_CONFIG.ACTIVE_MODEL,
            "mcp_server": { "name": APP_CONFIG.ACTIVE_MCP_SERVER_NAME }
        }
        app_logger.debug(f"/api/status responding with configured state: {status_payload}")
        return jsonify(status_payload)
    else:
        status_payload = {"isConfigured": False}
        app_logger.debug(f"/api/status responding with unconfigured state.")
        return jsonify(status_payload)

@api_bp.route("/simple_chat", methods=["POST"])
async def simple_chat():
    """
    Handles direct, tool-less chat with the configured LLM.
    This is used by the 'Chat' modal in the UI.
    """
    if not APP_STATE.get('llm'):
        return jsonify({"error": "LLM not configured."}), 400

    data = await request.get_json()
    message = data.get("message")
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "No message provided."}), 400

    try:
        response_text, _, _ = await llm_handler.call_llm_api(
            llm_instance=APP_STATE.get('llm'),
            prompt=message,
            chat_history=history,
            system_prompt_override="You are a helpful assistant.",
            dependencies={'STATE': APP_STATE},
            reason="Simple, tool-less chat."
        )

        final_response = response_text.replace("FINAL_ANSWER:", "").strip()

        return jsonify({"response": final_response})

    except Exception as e:
        app_logger.error(f"Error in simple_chat: {e}", exc_info=True)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@api_bp.route("/app-config")
async def get_app_config():
    """Returns the startup configuration flags and license info."""
    return jsonify({
        "all_models_unlocked": APP_CONFIG.ALL_MODELS_UNLOCKED,
        "charting_enabled": APP_CONFIG.CHARTING_ENABLED,
        "allow_synthesis_from_history": APP_CONFIG.ALLOW_SYNTHESIS_FROM_HISTORY,
        "default_charting_intensity": APP_CONFIG.DEFAULT_CHARTING_INTENSITY,
        "voice_conversation_enabled": APP_CONFIG.VOICE_CONVERSATION_ENABLED,
        "license_info": APP_STATE.get("license_info")
    })

@api_bp.route("/api/prompts-version")
async def get_prompts_version():
    """
    Returns a SHA-256 hash of the master system prompts.
    """
    try:
        prompts_str = json.dumps(PROVIDER_SYSTEM_PROMPTS, sort_keys=True)
        prompt_hash = hashlib.sha256(prompts_str.encode('utf-8')).hexdigest()
        return jsonify({"version": prompt_hash})
    except Exception as e:
        app_logger.error(f"Failed to generate prompts version hash: {e}", exc_info=True)
        return jsonify({"error": "Could not generate prompts version"}), 500

@api_bp.route("/api_key/<provider>")
async def get_api_key(provider):
    """Retrieves API keys from environment variables for pre-population."""
    key = None
    provider_lower = provider.lower()

    if provider_lower == 'google':
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        return jsonify({"apiKey": key or ""})
    elif provider_lower == 'anthropic':
        key = os.environ.get("ANTHROPIC_API_KEY")
        return jsonify({"apiKey": key or ""})
    elif provider_lower == 'openai':
        key = os.environ.get("OPENAI_API_KEY")
        return jsonify({"apiKey": key or ""})
    elif provider_lower == 'azure':
        keys = {
            "azure_api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
            "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
            "azure_deployment_name": os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
            "azure_api_version": os.environ.get("AZURE_OPENAI_API_VERSION")
        }
        return jsonify(keys)
    elif provider_lower == 'friendli':
        keys = {
            "friendli_token": os.environ.get("FRIENDLI_TOKEN"),
            "friendli_endpoint_url": os.environ.get("FRIENDLI_ENDPOINT_URL")
        }
        return jsonify(keys)
    elif provider_lower == 'amazon':
        keys = {
            "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
            "aws_region": os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        }
        return jsonify(keys)
    elif provider_lower == 'ollama':
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        return jsonify({"host": host})

    return jsonify({"error": "Unknown provider"}), 404

@api_bp.route("/api/synthesize-speech", methods=["POST"])
async def text_to_speech():
    """
    Converts text to speech using Google Cloud TTS.
    """
    app_logger.debug("/api/synthesize-speech endpoint hit.")
    if not APP_CONFIG.VOICE_CONVERSATION_ENABLED:
        app_logger.warning("Voice conversation feature is disabled by config. Aborting text-to-speech request.")
        return jsonify({"error": "Voice conversation feature is disabled."}), 403

    data = await request.get_json()
    text = data.get("text")
    if not text:
        app_logger.warning("No text provided in request body for speech synthesis.")
        return jsonify({"error": "No text provided for synthesis."}), 400

    if "tts_client" not in APP_STATE or APP_STATE["tts_client"] is None:
        app_logger.info("TTS client not in STATE, attempting to initialize.")
        APP_STATE["tts_client"] = get_tts_client()

    tts_client = APP_STATE.get("tts_client")
    if not tts_client:
        app_logger.error("TTS client is still not available after initialization attempt.")
        return jsonify({"error": "TTS client could not be initialized. Check server logs."}), 500

    audio_content = synthesize_speech(tts_client, text)

    if audio_content:
        app_logger.debug(f"Returning synthesized audio content ({len(audio_content)} bytes).")
        return Response(audio_content, mimetype="audio/mpeg")
    else:
        app_logger.error("synthesize_speech returned None. Sending error response.")
        return jsonify({"error": "Failed to synthesize speech."}), 500

@api_bp.route("/tools")
async def get_tools():
    """Returns the categorized list of MCP tools."""
    if not APP_STATE.get("mcp_client"): return jsonify({"error": "Not configured"}), 400
    return jsonify(APP_STATE.get("structured_tools", {}))

@api_bp.route("/prompts")
async def get_prompts():
    """
    Returns the categorized list of MCP prompts with metadata only.
    """
    if not APP_STATE.get("mcp_client"):
        return jsonify({"error": "Not configured"}), 400
    return jsonify(APP_STATE.get("structured_prompts", {}))

@api_bp.route("/tool/toggle_status", methods=["POST"])
async def toggle_tool_status():
    """
    Enables or disables a tool.
    """
    data = await request.get_json()
    tool_name = data.get("name")
    is_disabled = data.get("disabled")

    if not tool_name or is_disabled is None:
        return jsonify({"status": "error", "message": "Missing 'name' or 'disabled' field."}), 400

    disabled_tools_set = set(APP_STATE.get("disabled_tools", []))

    if is_disabled:
        disabled_tools_set.add(tool_name)
        app_logger.info(f"Disabling tool '{tool_name}' for agent use.")
    else:
        disabled_tools_set.discard(tool_name)
        app_logger.info(f"Enabling tool '{tool_name}' for agent use.")

    APP_STATE["disabled_tools"] = list(disabled_tools_set)

    _regenerate_contexts()

    return jsonify({"status": "success", "message": f"Tool '{tool_name}' status updated."})

@api_bp.route("/prompt/toggle_status", methods=["POST"])
async def toggle_prompt_status():
    """
    Enables or disables a prompt.
    """
    data = await request.get_json()
    prompt_name = data.get("name")
    is_disabled = data.get("disabled")

    if not prompt_name or is_disabled is None:
        return jsonify({"status": "error", "message": "Missing 'name' or 'disabled' field."}), 400

    disabled_prompts_set = set(APP_STATE.get("disabled_prompts", []))

    if is_disabled:
        disabled_prompts_set.add(prompt_name)
        app_logger.info(f"Disabling prompt '{prompt_name}' for agent use.")
    else:
        disabled_prompts_set.discard(prompt_name)
        app_logger.info(f"Enabling prompt '{prompt_name}' for agent use.")

    APP_STATE["disabled_prompts"] = list(disabled_prompts_set)

    _regenerate_contexts()

    return jsonify({"status": "success", "message": f"Prompt '{prompt_name}' status updated."})

@api_bp.route("/prompt/<prompt_name>", methods=["GET"])
async def get_prompt_content(prompt_name):
    """
    Retrieves the content of a specific MCP prompt. For dynamic prompts
    with arguments, it renders them with placeholder values for preview.
    """
    mcp_client = APP_STATE.get("mcp_client")
    if not mcp_client:
        return jsonify({"error": "MCP client not configured."}), 400

    server_name = APP_CONFIG.CURRENT_MCP_SERVER_NAME
    if not server_name:
         return jsonify({"error": "MCP server name not configured."}), 400

    try:
        prompt_info = _get_prompt_info(prompt_name)
        placeholder_args = {}

        if prompt_info and prompt_info.get("arguments"):
            app_logger.info(f"'{prompt_name}' is a dynamic prompt. Building placeholder arguments for preview.")
            for arg in prompt_info["arguments"]:
                arg_name = arg.get("name")
                if arg_name:
                    placeholder_args[arg_name] = f"<{arg_name}>"

        async with mcp_client.session(server_name) as temp_session:
            if placeholder_args:
                prompt_obj = await load_mcp_prompt(
                    temp_session, name=prompt_name, arguments=placeholder_args
                )
            else:
                prompt_obj = await temp_session.get_prompt(name=prompt_name)

        if not prompt_obj:
            return jsonify({"error": f"Prompt '{prompt_name}' not found."}), 404

        prompt_text = "Prompt content is not available."
        if isinstance(prompt_obj, str):
            prompt_text = prompt_obj
        elif (isinstance(prompt_obj, list) and len(prompt_obj) > 0 and hasattr(prompt_obj[0], 'content')):
             if isinstance(prompt_obj[0].content, str):
                 prompt_text = prompt_obj[0].content
             elif hasattr(prompt_obj[0].content, 'text'):
                 prompt_text = prompt_obj[0].content.text
        elif (hasattr(prompt_obj, 'messages') and
            isinstance(prompt_obj.messages, list) and
            len(prompt_obj.messages) > 0 and
            hasattr(prompt_obj.messages[0], 'content') and
            hasattr(prompt_obj.messages[0].content, 'text')):
            prompt_text = prompt_obj.messages[0].content.text
        elif hasattr(prompt_obj, 'text') and isinstance(prompt_obj.text, str):
            prompt_text = prompt_obj.text

        return jsonify({"name": prompt_name, "content": prompt_text})

    except Exception as e:
        root_exception = unwrap_exception(e)
        app_logger.error(f"Error fetching prompt content for '{prompt_name}': {root_exception}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred while fetching the prompt."}), 500

@api_bp.route("/sessions", methods=["GET"])
async def get_sessions():
    """Returns a list of all active chat sessions for the requesting user."""
    user_uuid = _get_user_uuid_from_request()
    app_logger.info(f"GET /sessions endpoint hit for user {user_uuid}")
    sessions = session_manager.get_all_sessions(user_uuid=user_uuid)
    return jsonify(sessions)

@api_bp.route("/session/<session_id>", methods=["GET"])
async def get_session_history(session_id):
    """Retrieves the chat history and token counts for a specific session."""
    user_uuid = _get_user_uuid_from_request()
    session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
    if session_data:
        response_data = {
            "history": session_data.get("session_history", []),
            "input_tokens": session_data.get("input_tokens", 0),
            "output_tokens": session_data.get("output_tokens", 0)
        }
        return jsonify(response_data)
    app_logger.warning(f"Session {session_id} not found for user {user_uuid}.")
    return jsonify({"error": "Session not found"}), 404

@api_bp.route("/api/session/<session_id>/rename", methods=["POST"])
async def rename_session(session_id: str):
    """Renames a specific session for the requesting user."""
    user_uuid = _get_user_uuid_from_request()
    data = await request.get_json()
    new_name = data.get("newName")

    if not new_name or not isinstance(new_name, str) or len(new_name.strip()) == 0:
        return jsonify({"status": "error", "message": "Invalid or empty 'newName' provided."}), 400

    session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
    if not session_data:
        app_logger.warning(f"Rename failed: Session {session_id} not found for user {user_uuid}.")
        return jsonify({"status": "error", "message": "Session not found or access denied."}), 404

    try:
        session_manager.update_session_name(user_uuid, session_id, new_name.strip())
        app_logger.info(f"User {user_uuid} renamed session {session_id} to '{new_name.strip()}'.")
        return jsonify({"status": "success", "message": "Session renamed successfully."}), 200
    except Exception as e:
        app_logger.error(f"Error renaming session {session_id} for user {user_uuid}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to update session name on the server."}), 500

@api_bp.route("/api/session/<session_id>", methods=["DELETE"])
async def delete_session_endpoint(session_id: str):
    """Deletes a specific session for the requesting user."""
    user_uuid = _get_user_uuid_from_request()
    app_logger.info(f"DELETE request received for session {session_id} from user {user_uuid}.")

    try:
        success = session_manager.delete_session(user_uuid, session_id)
        if success:
            app_logger.info(f"Successfully processed delete request for session {session_id} (user {user_uuid}).")
            return jsonify({"status": "success", "message": "Session deleted successfully."}), 200
        else:
            app_logger.error(f"session_manager.delete_session reported failure for session {session_id} (user {user_uuid}).")
            return jsonify({"status": "error", "message": "Failed to delete session file on the server."}), 500
    except Exception as e:
        app_logger.error(f"Unexpected error during DELETE /api/session/{session_id} for user {user_uuid}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected server error occurred during deletion."}), 500

# --- MODIFICATION START: Add new endpoint for purging session memory ---
@api_bp.route("/api/session/<session_id>/purge_memory", methods=["POST"])
async def purge_memory(session_id: str):
    """Purges the agent's LLM context memory (`chat_object`) for a session."""
    user_uuid = _get_user_uuid_from_request()
    app_logger.info(f"Purge memory request for session {session_id}, user {user_uuid}")

    success = session_manager.purge_session_memory(user_uuid, session_id)

    if success:
        app_logger.info(f"Agent memory purged successfully for session {session_id}, user {user_uuid}.")
        return jsonify({"status": "success", "message": "Agent memory purged."}), 200
    else:
        # This could be 404 (session not found) or 500 (save error), 404 is safer
        app_logger.warning(f"Failed to purge memory for session {session_id}, user {user_uuid}. Session may not exist or save failed.")
        return jsonify({"status": "error", "message": "Failed to purge session memory. Session not found or save error."}), 404
# --- MODIFICATION END ---

# --- MODIFICATION START: Add endpoints for /plan and /details ---
@api_bp.route("/api/session/<session_id>/turn/<int:turn_id>/plan", methods=["GET"])
async def get_turn_plan(session_id: str, turn_id: int):
    """Retrieves the original plan for a specific turn in a session."""
    user_uuid = _get_user_uuid_from_request()
    app_logger.info(f"GET /plan request for session {session_id}, turn {turn_id}, user {user_uuid}")
    session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
    if not session_data:
        return jsonify({"error": "Session not found"}), 404

    workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])
    if not isinstance(workflow_history, list) or turn_id <= 0 or turn_id > len(workflow_history):
        return jsonify({"error": f"Turn {turn_id} not found in session history."}), 404

    # Turns are 1-based for the user, but list index is 0-based
    turn_data = workflow_history[turn_id - 1]
    original_plan = turn_data.get("original_plan")

    if original_plan:
        return jsonify({"plan": original_plan})
    else:
        return jsonify({"error": f"Original plan not found for turn {turn_id}."}), 404

@api_bp.route("/api/session/<session_id>/turn/<int:turn_id>/details", methods=["GET"])
async def get_turn_details(session_id: str, turn_id: int):
    """Retrieves the full details (plan and trace) for a specific turn."""
    user_uuid = _get_user_uuid_from_request()
    app_logger.info(f"GET /details request for session {session_id}, turn {turn_id}, user {user_uuid}")
    session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
    if not session_data:
        return jsonify({"error": "Session not found"}), 404

    workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])
    if not isinstance(workflow_history, list) or turn_id <= 0 or turn_id > len(workflow_history):
        return jsonify({"error": f"Turn {turn_id} not found in session history."}), 404

    # Return the entire turn data object
    turn_data = workflow_history[turn_id - 1]
    # Optionally filter/clean the data before sending if needed, but for now send all
    return jsonify(turn_data)
# --- MODIFICATION END ---


@api_bp.route("/api/session/<session_id>/turn/<int:turn_id>/query", methods=["GET"])
async def get_turn_query(session_id: str, turn_id: int):
    """Retrieves the original user query for a specific turn in a session."""
    user_uuid = _get_user_uuid_from_request()
    app_logger.info(f"GET /query request for session {session_id}, turn {turn_id}, user {user_uuid}")
    session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
    if not session_data:
        return jsonify({"error": "Session not found"}), 404

    workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])
    if not isinstance(workflow_history, list) or turn_id <= 0 or turn_id > len(workflow_history):
        return jsonify({"error": f"Turn {turn_id} not found in session history."}), 404

    # Turns are 1-based for the user, but list index is 0-based
    turn_data = workflow_history[turn_id - 1]
    original_query = turn_data.get("user_query")

    if original_query:
        return jsonify({"query": original_query})
    else:
        # Should ideally always be present, but handle gracefully
        return jsonify({"error": f"Original query not found for turn {turn_id}."}), 404

@api_bp.route("/session", methods=["POST"])
async def new_session():
    """Creates a new chat session for the requesting user."""
    user_uuid = _get_user_uuid_from_request()

    if not APP_STATE.get('llm') or not APP_CONFIG.MCP_SERVER_CONNECTED:
        return jsonify({"error": "Application not configured. Please set MCP and LLM details in Config."}), 400

    try:
        loggers_to_purge = ["llm_conversation", "llm_conversation_history"]
        for logger_name in loggers_to_purge:
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    log_file_path = handler.baseFilename
                    handler.close()
                    logger.removeHandler(handler)
                    try:
                        with open(log_file_path, 'w'):
                            pass
                        app_logger.info(f"Successfully purged log file: {log_file_path}")
                        logger.addHandler(handler)
                    except Exception as clear_e:
                        app_logger.error(f"Failed to clear log file {log_file_path}: {clear_e}. Attempting to re-add handler anyway.")
                        logger.addHandler(handler)
    except Exception as e:
        app_logger.error(f"Failed to purge log files for new session: {e}", exc_info=True)


    data = await request.get_json()
    charting_intensity = data.get("charting_intensity", APP_CONFIG.DEFAULT_CHARTING_INTENSITY) if APP_CONFIG.CHARTING_ENABLED else "none"
    system_prompt_template = data.get("system_prompt")

    try:
        session_id = session_manager.create_session(
            user_uuid=user_uuid,
            provider=APP_CONFIG.CURRENT_PROVIDER,
            llm_instance=APP_STATE.get('llm'),
            charting_intensity=charting_intensity,
            system_prompt_template=system_prompt_template
        )
        app_logger.info(f"Created new session: {session_id} for user {user_uuid} provider {APP_CONFIG.CURRENT_PROVIDER}.")
        return jsonify({"session_id": session_id, "name": "New Chat"})
    except Exception as e:
        app_logger.error(f"Failed to create new session for user {user_uuid}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to initialize a new chat session: {e}"}), 500

@api_bp.route("/models", methods=["POST"])
async def get_models():
    """Fetches the list of available models from the selected provider."""
    try:
        data = await request.get_json()
        provider = data.get("provider")
        credentials = { "listing_method": data.get("listing_method", "foundation_models") }
        if provider == 'Azure':
            credentials["azure_deployment_name"] = data.get("azure_deployment_name")
        elif provider == 'Amazon':
            credentials.update({
                "aws_access_key_id": data.get("aws_access_key_id"),
                "aws_secret_access_key": data.get("aws_secret_access_key"),
                "aws_region": data.get("aws_region")
            })
        elif provider == 'Friendli':
            credentials.update({
                "friendli_token": data.get("friendli_token"),
                "friendli_endpoint_url": data.get("friendli_endpoint_url")
            })
        elif provider == 'Ollama':
            credentials["host"] = data.get("host")
        else:
            credentials["apiKey"] = data.get("apiKey")

        models = await llm_handler.list_models(provider, credentials)
        return jsonify({"status": "success", "models": models})
    except Exception as e:
        app_logger.error(f"Failed to list models for provider {provider}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400

@api_bp.route("/system_prompt/<provider>/<model_name>", methods=["GET"])
async def get_default_system_prompt(provider, model_name):
    """Gets the default system prompt for a given model."""
    base_prompt_template = PROVIDER_SYSTEM_PROMPTS.get(provider, PROVIDER_SYSTEM_PROMPTS["Google"])
    return jsonify({"status": "success", "system_prompt": base_prompt_template})

@api_bp.route("/configure", methods=["POST"])
async def configure_services():
    """
    Configures and validates the core LLM and MCP services from the UI.
    This is now a thin, protected wrapper around the centralized configuration service.
    """
    data_from_ui = await request.get_json()
    if not data_from_ui:
        return jsonify({"status": "error", "message": "Request body must be a valid JSON."}), 400

    host_keys = ["ollama_host", "ollamaHost", "host"]
    ollama_host_value = next((data_from_ui.get(key) for key in host_keys if data_from_ui.get(key) is not None), None)

    service_config_data = {
        "provider": data_from_ui.get("provider"),
        "model": data_from_ui.get("model"),
        "tts_credentials_json": data_from_ui.get("tts_credentials_json"),
        "credentials": {
            "apiKey": data_from_ui.get("apiKey"),
            "aws_access_key_id": data_from_ui.get("aws_access_key_id"),
            "aws_secret_access_key": data_from_ui.get("aws_secret_access_key"),
            "aws_region": data_from_ui.get("aws_region"),
            "ollama_host": ollama_host_value,
            "azure_api_key": data_from_ui.get("azure_api_key"),
            "azure_endpoint": data_from_ui.get("azure_endpoint"),
            "azure_deployment_name": data_from_ui.get("azure_deployment_name"),
            "azure_api_version": data_from_ui.get("azure_api_version"),
            "listing_method": data_from_ui.get("listing_method", "foundation_models"),
            "friendli_token": data_from_ui.get("friendli_token"),
            "friendli_endpoint_url": data_from_ui.get("friendli_endpoint_url")
        },
        "mcp_server": {
            "name": data_from_ui.get("server_name"),
            "host": data_from_ui.get("host"),
            "port": data_from_ui.get("port"),
            "path": data_from_ui.get("path")
        }
    }
    service_config_data["credentials"] = {k: v for k, v in service_config_data["credentials"].items() if v is not None}

    result = await configuration_service.setup_and_categorize_services(service_config_data)

    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@api_bp.route("/ask_stream", methods=["POST"])
async def ask_stream():
    """Handles the main chat conversation stream for ad-hoc user queries."""
    user_uuid = _get_user_uuid_from_request()

    if not APP_STATE.get('mcp_tools'):
        async def error_gen():
            yield PlanExecutor._format_sse({
                "error": "The agent is not fully configured. Please ensure the LLM and MCP server details are set correctly in the 'Config' tab before starting a chat."
            }, "error")
        return Response(error_gen(), mimetype="text/event-stream")

    data = await request.get_json()
    user_input = data.get("message")
    session_id = data.get("session_id")
    disabled_history = data.get("disabled_history", False)
    source = data.get("source", "text")
    # --- MODIFICATION START: Receive optional plan and replay flag ---
    plan_to_execute = data.get("plan_to_execute") # Plan object or null
    is_replay = data.get("is_replay", False) # Boolean flag
    # --- MODIFICATION END ---


    session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
    if not session_data:
        app_logger.error(f"ask_stream denied: Session {session_id} not found for user {user_uuid}.")
        async def error_gen():
            yield PlanExecutor._format_sse({"error": "Session not found or invalid."}, "error")
        return Response(error_gen(), mimetype="text/event-stream")


    active_tasks_key = f"{user_uuid}_{session_id}"
    active_tasks = APP_STATE.get("active_tasks", {})
    if active_tasks_key in active_tasks:
        existing_task = active_tasks.pop(active_tasks_key)
        if not existing_task.done():
            app_logger.warning(f"Cancelling previous active task for user {user_uuid}, session {session_id}.")
            existing_task.cancel()
            try:
                await asyncio.wait_for(existing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                app_logger.error(f"Error during cancellation cleanup: {e}")

    async def stream_generator():
        queue = asyncio.Queue()

        async def event_handler(event_data, event_type):
            sse_event = PlanExecutor._format_sse(event_data, event_type)
            await queue.put(sse_event)

        async def run_and_signal_completion():
            task = None
            try:
                # --- MODIFICATION START: Pass plan and replay flag to execution service ---
                task = asyncio.create_task(
                    execution_service.run_agent_execution(
                        user_uuid=user_uuid,
                        session_id=session_id,
                        user_input=user_input,
                        event_handler=event_handler,
                        disabled_history=disabled_history,
                        source=source,
                        plan_to_execute=plan_to_execute, # Pass the plan
                        is_replay=is_replay # Pass the flag
                    )
                )
                # --- MODIFICATION END ---
                APP_STATE.setdefault("active_tasks", {})[active_tasks_key] = task
                await task
            except asyncio.CancelledError:
                app_logger.info(f"Task for user {user_uuid}, session {session_id} was cancelled.")
                await event_handler({"message": "Execution stopped by user."}, "cancelled")
            except Exception as e:
                 app_logger.error(f"Error during task execution for user {user_uuid}, session {session_id}: {e}", exc_info=True)
                 await event_handler({"error": str(e)}, "error")
            finally:
                if active_tasks_key in APP_STATE.get("active_tasks", {}):
                    del APP_STATE["active_tasks"][active_tasks_key]
                await queue.put(None)

        asyncio.create_task(run_and_signal_completion())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return Response(stream_generator(), mimetype="text/event-stream")

@api_bp.route("/invoke_prompt_stream", methods=["POST"])
async def invoke_prompt_stream():
    """
    Handles the direct invocation of a prompt from the UI.
    """
    user_uuid = _get_user_uuid_from_request()

    if not APP_STATE.get('mcp_tools'):
        async def error_gen():
            yield PlanExecutor._format_sse({
                "error": "The agent is not fully configured. Please ensure the LLM and MCP server details are set correctly in the 'Config' tab before invoking a prompt."
            }, "error")
        return Response(error_gen(), mimetype="text/event-stream")

    data = await request.get_json()
    session_id = data.get("session_id")
    prompt_name = data.get("prompt_name")
    arguments = data.get("arguments", {})
    disabled_history = data.get("disabled_history", False)
    source = data.get("source", "prompt_library")

    session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
    if not session_data:
        app_logger.error(f"invoke_prompt_stream denied: Session {session_id} not found for user {user_uuid}.")
        async def error_gen():
            yield PlanExecutor._format_sse({"error": "Session not found or invalid."}, "error")
        return Response(error_gen(), mimetype="text/event-stream")

    active_tasks_key = f"{user_uuid}_{session_id}"
    active_tasks = APP_STATE.get("active_tasks", {})
    if active_tasks_key in active_tasks:
        existing_task = active_tasks.pop(active_tasks_key)
        if not existing_task.done():
            app_logger.warning(f"Cancelling previous active task for user {user_uuid}, session {session_id} during prompt invocation.")
            existing_task.cancel()
            try:
                await asyncio.wait_for(existing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                app_logger.error(f"Error during cancellation cleanup: {e}")

    async def stream_generator():
        queue = asyncio.Queue()

        async def event_handler(event_data, event_type):
            sse_event = PlanExecutor._format_sse(event_data, event_type)
            await queue.put(sse_event)

        async def run_and_signal_completion():
            task = None
            try:
                # Prompt invocation doesn't support replay currently
                task = asyncio.create_task(
                    execution_service.run_agent_execution(
                        user_uuid=user_uuid,
                        session_id=session_id,
                        user_input="Executing prompt...",
                        event_handler=event_handler,
                        active_prompt_name=prompt_name,
                        prompt_arguments=arguments,
                        disabled_history=disabled_history,
                        source=source
                        # plan_to_execute=None, is_replay=False
                    )
                )
                APP_STATE.setdefault("active_tasks", {})[active_tasks_key] = task
                await task
            except asyncio.CancelledError:
                app_logger.info(f"Prompt task for user {user_uuid}, session {session_id} was cancelled.")
                await event_handler({"message": "Execution stopped by user."}, "cancelled")
            except Exception as e:
                 app_logger.error(f"Error during prompt task execution for user {user_uuid}, session {session_id}: {e}", exc_info=True)
                 await event_handler({"error": str(e)}, "error")
            finally:
                if active_tasks_key in APP_STATE.get("active_tasks", {}):
                    del APP_STATE["active_tasks"][active_tasks_key]
                await queue.put(None)

        asyncio.create_task(run_and_signal_completion())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return Response(stream_generator(), mimetype="text/event-stream")

@api_bp.route("/api/session/<session_id>/cancel_stream", methods=["POST"])
async def cancel_stream(session_id: str):
    """Cancels the active execution task for a given session."""
    user_uuid = _get_user_uuid_from_request()
    active_tasks_key = f"{user_uuid}_{session_id}"
    active_tasks = APP_STATE.get("active_tasks", {})
    task = active_tasks.get(active_tasks_key)

    if task and not task.done():
        app_logger.info(f"Received request to cancel task for user {user_uuid}, session {session_id}.")
        task.cancel()
        if active_tasks_key in active_tasks:
             del active_tasks[active_tasks_key]
        return jsonify({"status": "success", "message": "Cancellation request sent."}), 200
    elif task and task.done():
        app_logger.info(f"Cancellation request for user {user_uuid}, session {session_id} ignored: task already completed.")
        if active_tasks_key in active_tasks:
             del active_tasks[active_tasks_key]
        return jsonify({"status": "info", "message": "Task already completed."}), 200
    else:
        app_logger.warning(f"Cancellation request for user {user_uuid}, session {session_id} failed: No active task found.")
        return jsonify({"status": "error", "message": "No active task found for this session."}), 404

# --- MODIFICATION START: Add endpoint to toggle turn validity ---
@api_bp.route("/api/session/<session_id>/turn/<int:turn_id>/toggle_validity", methods=["POST"])
async def toggle_turn_validity_route(session_id: str, turn_id: int):
    """Toggles the validity of a specific turn."""
    user_uuid = _get_user_uuid_from_request()
    app_logger.info(f"Toggle validity request for session {session_id}, turn {turn_id}, user {user_uuid}")

    success = session_manager.toggle_turn_validity(user_uuid, session_id, turn_id)

    if success:
        return jsonify({"status": "success", "message": f"Turn {turn_id} validity toggled."}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to toggle turn validity."}), 500
# --- MODIFICATION END ---
