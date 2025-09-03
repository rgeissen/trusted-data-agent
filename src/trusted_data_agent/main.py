# src/trusted_data_agent/main.py
import asyncio
import os
import sys
import logging
import shutil
import argparse

from quart import Quart
from quart_cors import cors
import hypercorn.asyncio
from hypercorn.config import Config

os.environ["LANGCHAIN_TRACING_V2"] = "false"

# --- MODIFICATION START: Configure logging with absolute paths ---
# This ensures logging is set up before any other application modules are imported.

# Determine the absolute path to the project's root directory.
# __file__ -> /path/to/teradata-trusted-data-agent/src/trusted_data_agent/main.py
# script_dir -> /path/to/teradata-trusted-data-agent/src/trusted_data_agent
# project_root -> /path/to/teradata-trusted-data-agent
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
LOG_DIR = os.path.join(project_root, "logs")

if os.path.exists(LOG_DIR): shutil.rmtree(LOG_DIR)
os.makedirs(LOG_DIR)

# --- Custom log filter to suppress benign SSE connection warnings ---
class SseConnectionFilter(logging.Filter):
    """
    Filters out benign validation warnings from the MCP client related to
    the initial SSE connection handshake message from the chart server.
    """
    def filter(self, record):
        is_validation_error = "Failed to validate notification" in record.getMessage()
        is_sse_connection_method = "sse/connection" in record.getMessage()
        return not (is_validation_error and is_sse_connection_method)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
handler.addFilter(SseConnectionFilter())

root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Configure the specific logger used throughout the application
app_logger = logging.getLogger("quart.app")
app_logger.setLevel(logging.INFO)
app_logger.addHandler(handler)
app_logger.propagate = False # Prevent duplicate messages in the root logger

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)
logging.getLogger("hypercorn.access").propagate = False
logging.getLogger("hypercorn.error").propagate = False

llm_log_handler = logging.FileHandler(os.path.join(LOG_DIR, "llm_conversation.log"))
llm_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
llm_logger = logging.getLogger("llm_conversation")
llm_logger.setLevel(logging.INFO)
llm_logger.addHandler(llm_log_handler)
llm_logger.propagate = False

llm_history_log_handler = logging.FileHandler(os.path.join(LOG_DIR, "llm_conversation_history.log"))
llm_history_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
llm_history_logger = logging.getLogger("llm_conversation_history")
llm_history_logger.setLevel(logging.INFO)
llm_history_logger.addHandler(llm_history_log_handler)
llm_history_logger.propagate = False
# --- MODIFICATION END ---

try:
    from trusted_data_agent.agent import prompts
except RuntimeError as e:
    # Use the now-configured logger for startup errors
    app_logger.critical(f"Application startup failed during initial import: {e}")
    sys.exit(1)

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.api.routes import get_tts_client


def create_app():
    # The project root is now calculated at the top level, so we can reuse it here.
    template_folder = os.path.join(project_root, 'templates')
    static_folder = os.path.join(project_root, 'static')
    
    app = Quart(__name__, template_folder=template_folder, static_folder=static_folder)
    app = cors(app, allow_origin="*")

    from trusted_data_agent.api.routes import api_bp
    app.register_blueprint(api_bp)

    @app.after_request
    async def add_security_headers(response):
        csp_policy = [
            "default-src 'self'",
            "script-src 'self' https://cdn.tailwindcss.com https://unpkg.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "connect-src 'self' *.googleapis.com https://*.withgoogle.com",
            "worker-src 'self' blob:",
            "img-src 'self' data:",
            "media-src 'self' blob:" # Allow media from blobs for TTS audio
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_policy)
        return response
    
    return app

app = create_app()

async def main():
    print("\n--- Starting Hypercorn Server for Quart App ---")
    print("Web client initialized and ready. Navigate to http://127.0.0.1:5000")
    config = Config()
    config.bind = ["127.0.0.1:5000"]
    config.accesslog = None
    config.errorlog = None 
    await hypercorn.asyncio.serve(app, config)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Trusted Data Agent web client.")
    parser.add_argument("--all-models", action="store_true", help="Allow selection of all available models.")
    args = parser.parse_args()

    if args.all_models:
        APP_CONFIG.ALL_MODELS_UNLOCKED = True
        print("\n--- DEV MODE: All models will be selectable. ---")
    
    print("\n--- CHARTING ENABLED: Charting configuration is active. ---")

if APP_CONFIG.VOICE_CONVERSATION_ENABLED:
    # First, check if the required environment variable is set.
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("\n--- ⚠️ VOICE FEATURE WARNING ---")
        print("The 'GOOGLE_APPLICATION_CREDENTIALS' environment variable is not set.")
        print("The voice conversation feature requires valid Google Cloud credentials for Text-to-Speech.")
        APP_CONFIG.VOICE_CONVERSATION_ENABLED = False
        print("Voice feature has been DISABLED.")
    else:
        # If the variable is set, proceed with initialization.
        print("\n--- VOICE FEATURE ENABLED: Checking Google TTS Credentials... ---")
        APP_STATE["tts_client"] = get_tts_client()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nServer shut down.")