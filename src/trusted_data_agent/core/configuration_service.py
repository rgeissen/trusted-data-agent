# src/trusted_data_agent/core/configuration_service.py
import logging
import httpx

from google.api_core import exceptions as google_exceptions
from anthropic import APIError, AsyncAnthropic
from openai import AsyncOpenAI, APIError as OpenAI_APIError
from botocore.exceptions import ClientError
import google.generativeai as genai
import boto3
from langchain_mcp_adapters.client import MultiServerMCPClient

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.llm import handler as llm_handler
from trusted_data_agent.mcp import adapter as mcp_adapter
# --- MODIFICATION START: Import utilities from the new central location ---
from trusted_data_agent.core.utils import unwrap_exception, _regenerate_contexts
# --- MODIFICATION END ---

app_logger = logging.getLogger("quart.app")

async def setup_and_categorize_services(config_data: dict) -> dict:
    """
    A centralized, atomic, and lock-protected service to configure the entire
    application. It validates connections, sets up clients, and runs the
    automatic, LLM-based capability classification.
    """
    # --- Use the global lock to prevent race conditions ---
    async with APP_STATE["configuration_lock"]:
        app_logger.info("Configuration lock acquired. Starting service setup...")
        
        provider = config_data.get("provider")
        model = config_data.get("model")
        server_name = config_data.get("mcp_server", {}).get("name")
        tts_credentials_json = config_data.get("tts_credentials_json")

        if not server_name:
            return {"status": "error", "message": "Configuration failed: 'mcp_server.name' is a required field."}

        temp_llm_instance = None
        temp_mcp_client = None
        
        try:
            app_logger.info(f"Validating credentials for provider: {provider}")
            
            # --- 1. LLM Client Validation ---
            credentials = config_data.get("credentials", {})
            if provider == "Google":
                genai.configure(api_key=credentials.get("apiKey"))
                temp_llm_instance = genai.GenerativeModel(model)
                await temp_llm_instance.generate_content_async("test", generation_config={"max_output_tokens": 1})
            
            elif provider == "Anthropic":
                temp_llm_instance = AsyncAnthropic(api_key=credentials.get("apiKey"))
                await temp_llm_instance.models.list()

            elif provider == "OpenAI":
                temp_llm_instance = AsyncOpenAI(api_key=credentials.get("apiKey"))
                await temp_llm_instance.models.list()

            elif provider == "Amazon":
                aws_region = credentials.get("aws_region")
                temp_llm_instance = boto3.client(
                    service_name='bedrock-runtime',
                    aws_access_key_id=credentials.get("aws_access_key_id"),
                    aws_secret_access_key=credentials.get("aws_secret_access_key"),
                    region_name=aws_region
                )
                app_logger.info("Boto3 client for Bedrock created. Skipping pre-flight model invocation.")

            elif provider == "Ollama":
                host = credentials.get("ollama_host")
                if not host:
                    raise ValueError("Ollama host is required.")
                temp_llm_instance = llm_handler.OllamaClient(host=host)
                await temp_llm_instance.list_models()
            else:
                raise NotImplementedError(f"Provider '{provider}' is not yet supported.")
            app_logger.info("LLM credentials/connection validated successfully.")

            # --- 2. MCP Client Validation ---
            mcp_server_config = config_data.get("mcp_server", {})
            mcp_server_url = f"http://{mcp_server_config.get('host')}:{mcp_server_config.get('port')}{mcp_server_config.get('path')}"
            temp_server_configs = {server_name: {"url": mcp_server_url, "transport": "streamable_http"}}
            temp_mcp_client = MultiServerMCPClient(temp_server_configs)
            async with temp_mcp_client.session(server_name) as temp_session:
                await temp_session.list_tools()
            app_logger.info("MCP server connection validated successfully.")

            app_logger.info("All validations passed. Committing configuration to application state.")
            
            # --- 3. Commit to Global State ---
            APP_CONFIG.CURRENT_PROVIDER = provider
            APP_CONFIG.CURRENT_MODEL = model
            APP_CONFIG.CURRENT_AWS_REGION = credentials.get("aws_region") if provider == "Amazon" else None
            APP_CONFIG.CURRENT_MODEL_PROVIDER_IN_PROFILE = None
            APP_CONFIG.CURRENT_MCP_SERVER_NAME = server_name
            
            APP_STATE['llm'] = temp_llm_instance
            APP_STATE['mcp_client'] = temp_mcp_client
            APP_STATE['server_configs'] = temp_server_configs

            if provider == "Amazon" and model.startswith("arn:aws:bedrock:"):
                profile_part = model.split('/')[-1]
                APP_CONFIG.CURRENT_MODEL_PROVIDER_IN_PROFILE = profile_part.split('.')[1]
            
            # --- 4. Load and Classify Capabilities (The Automatic Step) ---
            await mcp_adapter.load_and_categorize_mcp_resources(APP_STATE)
            APP_CONFIG.MCP_SERVER_CONNECTED = True
            
            APP_CONFIG.CHART_MCP_CONNECTED = True

            APP_STATE['tts_credentials_json'] = tts_credentials_json
            if APP_CONFIG.VOICE_CONVERSATION_ENABLED:
                # We need to import get_tts_client here to avoid a circular dependency at the top level
                from trusted_data_agent.core.utils import get_tts_client
                app_logger.info("AUDIO DEBUG: Configuration updated. Re-initializing TTS client.")
                APP_STATE['tts_client'] = get_tts_client()

            # --- 5. Finalize Contexts ---
            _regenerate_contexts()

            return {"status": "success", "message": f"MCP Server '{server_name}' and LLM configured successfully."}

        except (APIError, OpenAI_APIError, google_exceptions.PermissionDenied, ClientError, RuntimeError, Exception) as e:
            app_logger.error(f"Configuration failed during validation: {e}", exc_info=True)
            # --- Rollback state on failure ---
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

            return {"status": "error", "message": f"Configuration failed: {error_message}"}
        finally:
            app_logger.info("Configuration lock released.")

