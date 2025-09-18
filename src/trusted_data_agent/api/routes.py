# src/trusted_data_agent/api/routes.py
import json
import os
import logging
import asyncio
import sys
import copy
import hashlib
import httpx

from quart import Blueprint, request, jsonify, render_template, Response
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


@api_bp.route("/")
async def index():
    """Serves the main HTML page."""
    return await render_template("index.html")

# --- MODIFICATION START: Add the new /api/status endpoint with logging ---
@api_bp.route("/api/status")
async def get_application_status():
    """
    Returns the current configuration status of the application.
    This is used by the front end on startup to synchronize its state.
    """
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
# --- MODIFICATION END ---

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
    """Returns a list of all active chat sessions."""
    return jsonify(session_manager.get_all_sessions())

@api_bp.route("/session/<session_id>", methods=["GET"])
async def get_session_history(session_id):
    """Retrieves the chat history and token counts for a specific session."""
    session_data = session_manager.get_session(session_id)
    if session_data:
        response_data = {
            "history": session_data.get("session_history", []),
            "input_tokens": session_data.get("input_tokens", 0),
            "output_tokens": session_data.get("output_tokens", 0)
        }
        return jsonify(response_data)
    return jsonify({"error": "Session not found"}), 404

@api_bp.route("/session", methods=["POST"])
async def new_session():
    """Creates a new chat session."""
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
                    
                    with open(log_file_path, 'w'):
                        pass

                    new_handler = logging.FileHandler(log_file_path)
                    new_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
                    logger.addHandler(new_handler)
                    app_logger.info(f"Successfully purged and reset log file: {log_file_path}")
    except Exception as e:
        app_logger.error(f"Failed to purge log files for new session: {e}", exc_info=True)

    data = await request.get_json()
    charting_intensity = data.get("charting_intensity", APP_CONFIG.DEFAULT_CHARTING_INTENSITY) if APP_CONFIG.CHARTING_ENABLED else "none"
    system_prompt_template = data.get("system_prompt")

    try:
        session_id = session_manager.create_session(
            provider=APP_CONFIG.CURRENT_PROVIDER,
            llm_instance=APP_STATE.get('llm'),
            charting_intensity=charting_intensity,
            system_prompt_template=system_prompt_template
        )
        app_logger.info(f"Created new session: {session_id} for provider {APP_CONFIG.CURRENT_PROVIDER}.")
        return jsonify({"session_id": session_id, "name": "New Chat"})
    except Exception as e:
        app_logger.error(f"Failed to create new session: {e}", exc_info=True)
        return jsonify({"error": f"Failed to initialize a new chat session: {e}"}), 500

@api_bp.route("/models", methods=["POST"])
async def get_models():
    """Fetches the list of available models from the selected provider."""
    try:
        data = await request.get_json()
        provider = data.get("provider")
        credentials = { "listing_method": data.get("listing_method", "foundation_models") }
        if provider == 'Amazon':
            credentials.update({
                "aws_access_key_id": data.get("aws_access_key_id"),
                "aws_secret_access_key": data.get("aws_secret_access_key"),
                "aws_region": data.get("aws_region")
            })
        elif provider == 'Ollama':
            credentials["host"] = data.get("ollama_host")
        else:
            credentials["apiKey"] = data.get("apiKey")

        models = await llm_handler.list_models(provider, credentials)
        return jsonify({"status": "success", "models": models})
    except Exception as e:
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

    # --- MODIFICATION START: Adapter to reshape UI data for the service ---
    # This reshapes the flat structure from the UI into the nested structure
    # expected by the new, centralized configuration service.
    service_config_data = {
        "provider": data_from_ui.get("provider"),
        "model": data_from_ui.get("model"),
        "tts_credentials_json": data_from_ui.get("tts_credentials_json"),
        "credentials": {
            "apiKey": data_from_ui.get("apiKey"),
            "aws_access_key_id": data_from_ui.get("aws_access_key_id"),
            "aws_secret_access_key": data_from_ui.get("aws_secret_access_key"),
            "aws_region": data_from_ui.get("aws_region"),
            "ollama_host": data_from_ui.get("ollama_host"),
            "listing_method": data_from_ui.get("listing_method", "foundation_models")
        },
        "mcp_server": {
            "name": data_from_ui.get("server_name"),
            "host": data_from_ui.get("host"),
            "port": data_from_ui.get("port"),
            "path": data_from_ui.get("path")
        }
    }
    # Clean up None values to avoid sending empty keys
    service_config_data["credentials"] = {k: v for k, v in service_config_data["credentials"].items() if v is not None}
    # --- MODIFICATION END ---

    # Call the centralized, lock-protected service function
    result = await configuration_service.setup_and_categorize_services(service_config_data)
    
    # Return the result from the service directly to the UI
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@api_bp.route("/ask_stream", methods=["POST"])
async def ask_stream():
    """Handles the main chat conversation stream for ad-hoc user queries."""
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
    
    async def stream_generator():
        queue = asyncio.Queue()

        async def event_handler(event_data, event_type):
            sse_event = PlanExecutor._format_sse(event_data, event_type)
            await queue.put(sse_event)

        async def run_and_signal_completion():
            await execution_service.run_agent_execution(
                session_id=session_id,
                user_input=user_input,
                event_handler=event_handler,
                disabled_history=disabled_history,
                source=source
            )
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
    
    async def stream_generator():
        queue = asyncio.Queue()

        async def event_handler(event_data, event_type):
            sse_event = PlanExecutor._format_sse(event_data, event_type)
            await queue.put(sse_event)

        async def run_and_signal_completion():
            await execution_service.run_agent_execution(
                session_id=session_id,
                user_input="Executing prompt...",
                event_handler=event_handler,
                active_prompt_name=prompt_name,
                prompt_arguments=arguments,
                disabled_history=disabled_history,
                source=source
            )
            await queue.put(None)

        asyncio.create_task(run_and_signal_completion())
        
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return Response(stream_generator(), mimetype="text/event-stream")