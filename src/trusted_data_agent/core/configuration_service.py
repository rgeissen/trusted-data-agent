# src/trusted_data_agent/core/configuration_service.py
import logging
import httpx

from google.api_core import exceptions as google_exceptions
from anthropic import APIError, AsyncAnthropic
from openai import AsyncOpenAI, APIError as OpenAI_APIError, AsyncAzureOpenAI
from botocore.exceptions import ClientError
import google.generativeai as genai
import boto3
from langchain_mcp_adapters.client import MultiServerMCPClient

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.llm import handler as llm_handler
from trusted_data_agent.mcp import adapter as mcp_adapter
from trusted_data_agent.core.utils import unwrap_exception, _regenerate_contexts

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

        is_already_configured = (
            APP_CONFIG.SERVICES_CONFIGURED and
            provider == APP_CONFIG.ACTIVE_PROVIDER and
            model == APP_CONFIG.ACTIVE_MODEL and
            server_name == APP_CONFIG.ACTIVE_MCP_SERVER_NAME
        )

        if is_already_configured:
            app_logger.info("Bypassing configuration: The requested configuration is already active.")
            return {"status": "success", "message": f"Services are already configured with the requested settings."}

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

            elif provider in ["OpenAI", "Azure", "Friendli"]:
                if provider == "OpenAI":
                    temp_llm_instance = AsyncOpenAI(api_key=credentials.get("apiKey"))
                    await temp_llm_instance.models.list()

                elif provider == "Azure":
                    temp_llm_instance = AsyncAzureOpenAI(
                        api_key=credentials.get("azure_api_key"),
                        azure_endpoint=credentials.get("azure_endpoint"),
                        api_version=credentials.get("azure_api_version")
                    )
                    await temp_llm_instance.chat.completions.create(model=model, messages=[{"role": "user", "content": "test"}], max_tokens=1)
                
                elif provider == "Friendli":
                    friendli_token = credentials.get("friendli_token")
                    endpoint_url = credentials.get("friendli_endpoint_url")
                    
                    if endpoint_url: # Dedicated Endpoint: Validate by listing models
                        app_logger.info("Validating Friendli.ai Dedicated Endpoint by listing models.")
                        validation_url = f"{endpoint_url.rstrip('/')}/v1/models"
                        headers = {"Authorization": f"Bearer {friendli_token}"}
                        async with httpx.AsyncClient() as client:
                            response = await client.get(validation_url, headers=headers)
                            response.raise_for_status()
                        temp_llm_instance = AsyncOpenAI(api_key=friendli_token, base_url=endpoint_url)
                        app_logger.info("Friendli.ai Dedicated Endpoint connection validated successfully.")
                    else: # Serverless Endpoint: Validate with a test completion call
                        app_logger.info(f"Validating Friendli.ai Serverless Endpoint with model '{model}'.")
                        if not model:
                            raise ValueError("A Model ID is required for Friendli.ai Serverless Endpoint configuration.")
                        
                        # --- MODIFICATION START: Correct the base_url for serverless endpoints ---
                        temp_llm_instance = AsyncOpenAI(api_key=friendli_token, base_url="https://api.friendli.ai/serverless/v1")
                        # --- MODIFICATION END ---
                        await temp_llm_instance.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": "test"}],
                            max_tokens=1
                        )
                        app_logger.info("Friendli.ai Serverless Endpoint token and model ID validated successfully.")

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
            if provider == "Azure":
                APP_CONFIG.CURRENT_AZURE_DEPLOYMENT_DETAILS = {
                    "endpoint": credentials.get("azure_endpoint"),
                    "deployment_name": credentials.get("azure_deployment_name"),
                    "api_version": credentials.get("azure_api_version")
                }
            if provider == "Friendli":
                is_dedicated = bool(credentials.get("friendli_endpoint_url"))
                APP_CONFIG.CURRENT_FRIENDLI_DETAILS = {
                    "token": credentials.get("friendli_token"),
                    "endpoint_url": credentials.get("friendli_endpoint_url"),
                    "models_path": "/v1/models" if is_dedicated else None # No path for serverless
                }
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
                from trusted_data_agent.core.utils import get_tts_client
                app_logger.info("AUDIO DEBUG: Configuration updated. Re-initializing TTS client.")
                APP_STATE['tts_client'] = get_tts_client()

            # --- 5. Finalize Contexts ---
            _regenerate_contexts()

            APP_CONFIG.SERVICES_CONFIGURED = True
            APP_CONFIG.ACTIVE_PROVIDER = provider
            APP_CONFIG.ACTIVE_MODEL = model
            APP_CONFIG.ACTIVE_MCP_SERVER_NAME = server_name

            return {"status": "success", "message": f"MCP Server '{server_name}' and LLM configured successfully."}

        except (APIError, OpenAI_APIError, google_exceptions.PermissionDenied, ClientError, RuntimeError, Exception) as e:
            app_logger.error(f"Configuration failed during validation: {e}", exc_info=True)
            # --- Rollback state on failure ---
            APP_STATE['llm'] = None
            APP_STATE['mcp_client'] = None
            APP_CONFIG.MCP_SERVER_CONNECTED = False
            APP_CONFIG.CHART_MCP_CONNECTED = False
            
            APP_CONFIG.SERVICES_CONFIGURED = False
            APP_CONFIG.ACTIVE_PROVIDER = None
            APP_CONFIG.ACTIVE_MODEL = None
            APP_CONFIG.ACTIVE_MCP_SERVER_NAME = None
            
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

