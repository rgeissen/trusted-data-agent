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
from google.api_core import exceptions as google_exceptions
from anthropic import APIError, AsyncAnthropic
from openai import AsyncOpenAI, APIError as OpenAI_APIError
from botocore.exceptions import ClientError
import google.generativeai as genai
import boto3
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.prompts import load_mcp_prompt
from mcp.shared.exceptions import McpError

try:
    from google.cloud import texttospeech
    from google.oauth2 import service_account
except ImportError:
    texttospeech = None
    service_account = None

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.core import session_manager
from trusted_data_agent.agent.prompts import PROVIDER_SYSTEM_PROMPTS, CHARTING_INSTRUCTIONS
from trusted_data_agent.agent.executor import PlanExecutor
from trusted_data_agent.llm import handler as llm_handler
from trusted_data_agent.mcp import adapter as mcp_adapter
from trusted_data_agent.agent.formatter import OutputFormatter
from trusted_data_agent.agent import execution_service


api_bp = Blueprint('api', __name__)
app_logger = logging.getLogger("quart.app")

def get_tts_client():
    """
    Initializes and returns a Google Cloud TextToSpeechClient.
    It prioritizes credentials provided via the UI, falling back to environment variables.
    """
    app_logger.info("AUDIO DEBUG: Attempting to get TTS client.")
    if texttospeech is None:
        app_logger.error("AUDIO DEBUG: The 'google-cloud-texttospeech' library is not installed.")
        app_logger.error("AUDIO DEBUG: Please install it to use the voice feature: pip install google-cloud-texttospeech")
        return None

    tts_creds_json_str = APP_STATE.get("tts_credentials_json")

    if tts_creds_json_str:
        app_logger.info("AUDIO DEBUG: Attempting to initialize TTS client from UI-provided JSON credentials.")
        try:
            credentials_info = json.loads(tts_creds_json_str)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            client = texttospeech.TextToSpeechClient(credentials=credentials)
            app_logger.info("AUDIO DEBUG: Successfully initialized Google Cloud TTS client using UI credentials.")
            return client
        except json.JSONDecodeError:
            app_logger.error("AUDIO DEBUG: Failed to parse TTS credentials JSON provided from the UI. It appears to be invalid JSON.")
            return None
        except Exception as e:
            app_logger.error(f"AUDIO DEBUG: Failed to initialize TTS client with UI credentials: {e}", exc_info=True)
            return None
    
    app_logger.info("AUDIO DEBUG: No UI credentials found. Falling back to environment variable for TTS client.")
    try:
        client = texttospeech.TextToSpeechClient()
        app_logger.info("AUDIO DEBUG: Successfully initialized Google Cloud TTS client using environment variables.")
        return client
    except Exception as e:
        app_logger.error(f"AUDIO DEBUG: Failed to initialize Google Cloud TTS client with environment variables: {e}", exc_info=True)
        app_logger.error("AUDIO DEBUG: Please ensure the 'GOOGLE_APPLICATION_CREDENTIALS' environment variable is set correctly or provide credentials in the UI.")
        return None

def synthesize_speech(client, text: str) -> bytes | None:
    """
    Synthesizes speech from the provided text using the given TTS client.
    """
    if not client:
        app_logger.error("AUDIO DEBUG: TTS client is not available. Cannot synthesize speech.")
        return None

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Studio-O",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.1
    )

    try:
        app_logger.info(f"AUDIO DEBUG: Requesting speech synthesis for text: '{text[:80]}...'")
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        app_logger.info("AUDIO DEBUG: Speech synthesis successful.")
        return response.audio_content
    except Exception as e:
        app_logger.error(f"AUDIO DEBUG: Google Cloud TTS API call failed: {e}", exc_info=True)
        return None

def unwrap_exception(e: BaseException) -> BaseException:
    """Recursively unwraps ExceptionGroups to find the root cause."""
    if isinstance(e, ExceptionGroup) and e.exceptions:
        return unwrap_exception(e.exceptions[0])
    return e

def _get_prompt_info(prompt_name: str) -> dict | None:
    """Helper to find prompt details from the structured prompts in the global state."""
    structured_prompts = APP_STATE.get('structured_prompts', {})
    for category_prompts in structured_prompts.values():
        for prompt in category_prompts:
            if prompt.get("name") == prompt_name:
                return prompt
    return None

def _indent_multiline_description(description: str, indent_level: int = 2) -> str:
    """Indents all but the first line of a multi-line string."""
    if not description or '\n' not in description:
        return description
    
    lines = description.split('\n')
    first_line = lines[0]
    rest_lines = lines[1:]
    
    indentation = ' ' * indent_level
    indented_rest = [f"{indentation}{line}" for line in rest_lines]
    
    return '\n'.join([first_line] + indented_rest)

def _regenerate_contexts():
    """
    Updates all capability contexts ('tools_context', 'prompts_context', etc.)
    in the global STATE based on the current disabled lists and prints the
    current status to the console for debugging.
    """
    print("\n--- Regenerating Agent Capability Contexts ---")
    
    disabled_tools_list = APP_STATE.get("disabled_tools", [])
    disabled_prompts_list = APP_STATE.get("disabled_prompts", [])
    
    if APP_STATE.get('mcp_tools') and APP_STATE.get('structured_tools'):
        for category, tool_list in APP_STATE['structured_tools'].items():
            for tool_info in tool_list:
                tool_info['disabled'] = tool_info['name'] in disabled_tools_list
        
        enabled_count = sum(1 for category in APP_STATE['structured_tools'].values() for t in category if not t['disabled'])
        
        print(f"\n[ Tools Status ]")
        print(f"  - Active: {enabled_count}")
        print(f"  - Inactive: {len(disabled_tools_list)}")

        tool_context_parts = ["--- Available Tools ---"]
        for category, tools in sorted(APP_STATE['structured_tools'].items()):
            enabled_tools_in_category = [t for t in tools if not t['disabled']]
            if not enabled_tools_in_category:
                continue
                
            tool_context_parts.append(f"--- Category: {category} ---")
            for tool_info in enabled_tools_in_category:
                tool_description = tool_info.get("description", "No description available.")
                indented_description = _indent_multiline_description(tool_description, indent_level=2)
                tool_str = f"- `{tool_info['name']}` (tool): {indented_description}"
                
                processed_args = tool_info.get('arguments', [])
                if processed_args:
                    tool_str += "\n  - Arguments:"
                    for arg_details in processed_args:
                        arg_name = arg_details.get('name', 'unknown')
                        arg_type = arg_details.get('type', 'any')
                        is_required = arg_details.get('required', False)
                        req_str = "required" if is_required else "optional"
                        arg_desc = arg_details.get('description', 'No description.')
                        tool_str += f"\n    - `{arg_name}` ({arg_type}, {req_str}): {arg_desc}"
                tool_context_parts.append(tool_str)
        
        if len(tool_context_parts) > 1:
            APP_STATE['tools_context'] = "\n".join(tool_context_parts)
        else:
            APP_STATE['tools_context'] = "--- No Tools Available ---"
        app_logger.info(f"Regenerated LLM tool context. {enabled_count} tools are active.")

    if APP_STATE.get('mcp_prompts') and APP_STATE.get('structured_prompts'):
        for category, prompt_list in APP_STATE['structured_prompts'].items():
            for prompt_info in prompt_list:
                prompt_info['disabled'] = prompt_info['name'] in disabled_prompts_list

        enabled_count = sum(1 for category in APP_STATE['structured_prompts'].values() for p in category if not p['disabled'])
        
        print(f"\n[ Prompts Status ]")
        print(f"  - Active: {enabled_count}")
        print(f"  - Inactive: {len(disabled_prompts_list)}")
        
        prompt_context_parts = ["--- Available Prompts ---"]
        for category, prompts in sorted(APP_STATE['structured_prompts'].items()):
            enabled_prompts_in_category = [p for p in prompts if not p['disabled']]
            if not enabled_prompts_in_category:
                continue

            prompt_context_parts.append(f"--- Category: {category} ---")
            for prompt_info in enabled_prompts_in_category:
                prompt_description = prompt_info.get("description", "No description available.")
                indented_description = _indent_multiline_description(prompt_description, indent_level=2)
                prompt_str = f"- `{prompt_info['name']}` (prompt): {indented_description}"
                
                processed_args = prompt_info.get('arguments', [])
                if processed_args:
                    prompt_str += "\n  - Arguments:"
                    for arg_details in processed_args:
                        arg_name = arg_details.get('name', 'unknown')
                        arg_type = arg_details.get('type', 'any')
                        is_required = arg_details.get('required', False)
                        req_str = "required" if is_required else "optional"
                        arg_desc = arg_details.get('description', 'No description.')
                        prompt_str += f"\n    - `{arg_name}` ({arg_type}, {req_str}): {arg_desc}"
                prompt_context_parts.append(prompt_str)

        if len(prompt_context_parts) > 1:
            APP_STATE['prompts_context'] = "\n".join(prompt_context_parts)
        else:
            APP_STATE['prompts_context'] = "--- No Prompts Available ---"
        app_logger.info(f"Regenerated LLM prompt context. {enabled_count} prompts are active.")

    if disabled_tools_list or disabled_prompts_list:
        constraints_list = []
        if disabled_tools_list:
            constraints_list.extend([f"- `{name}` (tool)" for name in disabled_tools_list])
        if disabled_prompts_list:
            constraints_list.extend([f"- `{name}` (prompt)" for name in disabled_prompts_list])
        
        APP_STATE['constraints_context'] = (
            "\n--- CONSTRAINTS ---\n"
            "You are explicitly forbidden from using the following capabilities in your plan under any circumstances:\n"
            + "\n".join(constraints_list) + "\n"
        )
        app_logger.info(f"Regenerated LLM constraints context. {len(constraints_list)} capabilities are forbidden.")
    else:
        APP_STATE['constraints_context'] = "" 
        app_logger.info("Regenerated LLM constraints context. No capabilities are currently forbidden.")
    
    print("\n" + "-"*44)

@api_bp.route("/")
async def index():
    """Serves the main HTML page."""
    return await render_template("index.html")

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
    app_logger.info("AUDIO DEBUG: /api/synthesize-speech endpoint hit.")
    if not APP_CONFIG.VOICE_CONVERSATION_ENABLED:
        app_logger.warning("AUDIO DEBUG: Voice conversation feature is disabled by config. Aborting.")
        return jsonify({"error": "Voice conversation feature is disabled."}), 403

    data = await request.get_json()
    text = data.get("text")
    if not text:
        app_logger.warning("AUDIO DEBUG: No text provided in request body.")
        return jsonify({"error": "No text provided for synthesis."}), 400

    if "tts_client" not in APP_STATE or APP_STATE["tts_client"] is None:
        app_logger.info("AUDIO DEBUG: TTS client not in STATE, attempting to initialize.")
        APP_STATE["tts_client"] = get_tts_client()

    tts_client = APP_STATE.get("tts_client")
    if not tts_client:
        app_logger.error("AUDIO DEBUG: TTS client is still not available after initialization attempt.")
        return jsonify({"error": "TTS client could not be initialized. Check server logs."}), 500

    audio_content = synthesize_speech(tts_client, text)

    if audio_content:
        app_logger.info(f"AUDIO DEBUG: Returning synthesized audio content ({len(audio_content)} bytes).")
        return Response(audio_content, mimetype="audio/mpeg")
    else:
        app_logger.error("AUDIO DEBUG: synthesize_speech returned None. Sending error response.")
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
    Configures and validates the core LLM and MCP services.
    """
    data = await request.get_json()
    provider = data.get("provider")
    model = data.get("model")
    server_name = data.get("server_name")
    tts_credentials_json = data.get("tts_credentials_json")

    if not server_name:
        return jsonify({"status": "error", "message": "Configuration failed: 'MCP Server Name' is a required field."}), 400
    
    temp_llm_instance = None
    temp_mcp_client = None
    
    try:
        app_logger.info(f"Validating credentials for provider: {provider}")
        if provider == "Google":
            genai.configure(api_key=data.get("apiKey"))
            temp_llm_instance = genai.GenerativeModel(model)
            await temp_llm_instance.generate_content_async("test", generation_config={"max_output_tokens": 1})
        elif provider == "Anthropic":
            temp_llm_instance = AsyncAnthropic(api_key=data.get("apiKey"))
            await temp_llm_instance.models.list()
        elif provider == "OpenAI":
            temp_llm_instance = AsyncOpenAI(api_key=data.get("apiKey"))
            await temp_llm_instance.models.list()
        elif provider == "Amazon":
            aws_region = data.get("aws_region")
            temp_llm_instance = boto3.client(
                service_name='bedrock-runtime',
                aws_access_key_id=data.get("aws_access_key_id"),
                aws_secret_access_key=data.get("aws_secret_access_key"),
                region_name=aws_region
            )
            app_logger.info("Boto3 client for Bedrock created. Skipping pre-flight model invocation.")
        elif provider == "Ollama":
            host = data.get("ollama_host")
            if not host:
                raise ValueError("Ollama host is required.")
            temp_llm_instance = llm_handler.OllamaClient(host=host)
            await temp_llm_instance.list_models()
        else:
            raise NotImplementedError(f"Provider '{provider}' is not yet supported.")
        app_logger.info("LLM credentials/connection validated successfully.")

        mcp_server_url = f"http://{data.get('host')}:{data.get('port')}{data.get('path')}"
        temp_server_configs = {server_name: {"url": mcp_server_url, "transport": "streamable_http"}}
        temp_mcp_client = MultiServerMCPClient(temp_server_configs)
        async with temp_mcp_client.session(server_name) as temp_session:
            await temp_session.list_tools()
        app_logger.info("MCP server connection validated successfully.")

        app_logger.info("All validations passed. Committing configuration to application state.")
        
        APP_CONFIG.CURRENT_PROVIDER = provider
        APP_CONFIG.CURRENT_MODEL = model
        APP_CONFIG.CURRENT_AWS_REGION = data.get("aws_region") if provider == "Amazon" else None
        APP_CONFIG.CURRENT_MODEL_PROVIDER_IN_PROFILE = None
        APP_CONFIG.CURRENT_MCP_SERVER_NAME = server_name
        
        APP_STATE['llm'] = temp_llm_instance
        APP_STATE['mcp_client'] = temp_mcp_client
        APP_STATE['server_configs'] = temp_server_configs

        if provider == "Amazon" and model.startswith("arn:aws:bedrock:"):
            profile_part = model.split('/')[-1]
            APP_CONFIG.CURRENT_MODEL_PROVIDER_IN_PROFILE = profile_part.split('.')[1]
        
        await mcp_adapter.load_and_categorize_mcp_resources(APP_STATE)
        APP_CONFIG.MCP_SERVER_CONNECTED = True
        
        APP_CONFIG.CHART_MCP_CONNECTED = True

        APP_STATE['tts_credentials_json'] = tts_credentials_json
        if APP_CONFIG.VOICE_CONVERSATION_ENABLED:
            app_logger.info("AUDIO DEBUG: Configuration updated. Re-initializing TTS client.")
            APP_STATE['tts_client'] = get_tts_client()

        _regenerate_contexts()

        return jsonify({"status": "success", "message": f"MCP Server '{server_name}' and LLM configured successfully."})

    except (APIError, OpenAI_APIError, google_exceptions.PermissionDenied, ClientError, RuntimeError, Exception) as e:
        app_logger.error(f"Configuration failed during validation: {e}", exc_info=True)
        APP_STATE['llm'] = None
        APP_STATE['mcp_client'] = None
        APP_CONFIG.MCP_SERVER_CONNECTED = False
        APP_CONFIG.CHART_MCP_CONNECTED = False
        
        root_exception = unwrap_exception(e)
        error_message = ""
        
        if isinstance(root_exception, (httpx.ConnectTimeout, httpx.ConnectError)):
            error_message = "Connection to MCP server failed. Please check the Host and Port and ensure the server is running."
        elif isinstance(root_exception, (google_exceptions.PermissionDenied, ClientError)):
             if 'AccessDeniedException' in str(e):
                 error_message = "Access denied. Please check your AWS IAM permissions for the selected model."
             else:
                error_message = "Authentication failed. Please check your API keys or credentials."
        elif isinstance(root_exception, (APIError, OpenAI_APIError)) and "authentication_error" in str(e).lower():
             error_message = f"Authentication failed. Please check your {provider} API key."
        else:
            error_message = getattr(root_exception, 'message', str(root_exception))

        return jsonify({"status": "error", "message": f"Configuration failed: {error_message}"}), 500

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

