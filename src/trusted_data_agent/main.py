# src/trusted_data_agent/main.py
import asyncio
import os
import sys
import logging
import shutil
import argparse

# --- MODIFICATION START: Import Response from Quart ---
# Required if you add test routes later, good practice to have it
from quart import Quart, Response
# --- MODIFICATION END ---
from quart_cors import cors
import hypercorn.asyncio
from hypercorn.config import Config

os.environ["LANGCHAIN_TRACING_V2"] = "false"

# --- Logging Setup (from your original file) ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
LOG_DIR = os.path.join(project_root, "logs")

if os.path.exists(LOG_DIR): shutil.rmtree(LOG_DIR)
os.makedirs(LOG_DIR)

class SseConnectionFilter(logging.Filter):
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
# --- MODIFICATION START: Set Root Logger Level to INFO ---
root_logger.setLevel(logging.INFO)
# root_logger.setLevel(logging.DEBUG)
# --- MODIFICATION END ---


app_logger = logging.getLogger("quart.app")
# --- MODIFICATION START: Set Quart App Logger Level to INFO ---
app_logger.setLevel(logging.INFO) # Ensures quart.app messages (like ours) are shown
# app_logger.setLevel(logging.DEBUG)
# --- MODIFICATION END ---
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
# --- End Logging Setup ---

try:
    from trusted_data_agent.agent import prompts
except RuntimeError as e:
    app_logger.critical(f"Application startup failed during initial import: {e}")
    sys.exit(1)

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.api.routes import get_tts_client # Assuming get_tts_client is still relevant


# --- MODIFICATION START: Add RAG Processing Worker ---
async def rag_processing_worker():
    """
    A single, persistent background worker that processes turns from the
    RAG queue one by one, ensuring no race conditions.
    """
    app_logger.info("RAG processing worker started and waiting for queue items.")
    while True:
        try:
            # 1. Wait for a turn_summary to arrive in the queue
            turn_summary = await APP_STATE['rag_processing_queue'].get()

            # 2. Get the RAG retriever instance
            retriever = APP_STATE.get('rag_retriever_instance')
            
            # 3. Process the turn if RAG is enabled and the instance exists
            if retriever and turn_summary and APP_CONFIG.RAG_ENABLED:
                app_logger.info(f"RAG worker: Processing turn {turn_summary.get('turn')} from session {turn_summary.get('session_id')}.")
                
                # We create a new task for the actual processing.
                # This allows the worker to be immediately ready for the next
                # item, though the processing itself is still serialized
                # by the nature of the retriever's logic.
                # For true atomicity, we await the processing here.
                await retriever.process_turn_for_rag(turn_summary)
                
            # 4. Mark the queue item as processed
            APP_STATE['rag_processing_queue'].task_done()

        except Exception as e:
            # Log errors but don't crash the worker
            app_logger.error(f"Error in RAG processing worker: {e}", exc_info=True)
            # Ensure task_done() is called even on error to prevent queue blockage
            if 'turn_summary' in locals() and turn_summary:
                APP_STATE['rag_processing_queue'].task_done()
# --- MODIFICATION END ---


def create_app():
    template_folder = os.path.join(project_root, 'templates')
    static_folder = os.path.join(project_root, 'static')

    app = Quart(__name__, template_folder=template_folder, static_folder=static_folder)
    app = cors(app, allow_origin="*")

    # --- MODIFICATION START: Increase Quart's RESPONSE_TIMEOUT ---
    # This prevents Quart from closing long SSE streams prematurely (default is 60s)
    app.config['RESPONSE_TIMEOUT'] = 1800 # Set to 30 minutes (adjust as needed, or use None for unlimited)
    # You might also want to set REQUEST_TIMEOUT if needed, though less relevant here
    app.config['REQUEST_TIMEOUT'] = None
    # --- MODIFICATION END ---

    from trusted_data_agent.api.routes import api_bp
    from trusted_data_agent.api.rest_routes import rest_api_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(rest_api_bp, url_prefix="/api")

    @app.after_request
    async def add_security_headers(response):
        # Allow connections to unpkg for G2Plot if needed, adjust connect-src
        csp_policy = [
            "default-src 'self'",
            "script-src 'self' https://cdn.tailwindcss.com https://unpkg.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com", # Allow inline styles for G2Plot tooltips etc.
            "font-src 'self' https://fonts.gstatic.com",
            "connect-src 'self' *.googleapis.com https://*.withgoogle.com https://unpkg.com", # Added unpkg
            "worker-src 'self' blob:",
            "img-src 'self' data:",
            "media-src 'self' blob:" # Allow media from blobs for TTS audio
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_policy)
        return response

    # --- MODIFICATION START: Add startup task hook ---
    @app.before_serving
    async def startup():
        """
        Runs once before the server starts serving requests.
        Used to start background tasks like our RAG worker.
        """
        app_logger.info("Application starting up... Launching background tasks.")
        
        # Load RAG collections from persistent config into APP_STATE early
        # This allows the UI to display collections even before full configuration
        try:
            from trusted_data_agent.core.config_manager import get_config_manager
            config_manager = get_config_manager()
            collections_list = config_manager.get_rag_collections()
            APP_STATE["rag_collections"] = collections_list
            app_logger.info(f"Pre-loaded {len(collections_list)} RAG collections from persistent config")
        except Exception as e:
            app_logger.error(f"Failed to pre-load RAG collections: {e}", exc_info=True)
            APP_STATE["rag_collections"] = []
        
        # Start the single RAG worker as a background task
        asyncio.create_task(rag_processing_worker())
    # --- MODIFICATION END ---

    return app

app = create_app()

async def main(args): # MODIFIED: Accept args
    print("\n--- Starting Hypercorn Server for Quart App ---")
    host = args.host
    port = args.port
    print(f"Web client initialized and ready. Navigate to http://{host}:{port}")
    config = Config()
    config.bind = [f"{host}:{port}"] # MODIFIED: Use dynamic host and port
    config.accesslog = None
    config.errorlog = None
    # --- MODIFICATION START: Add longer Hypercorn timeouts (Good Practice) ---
    # While Quart's RESPONSE_TIMEOUT was the main fix, setting these high
    # ensures Hypercorn doesn't impose its own shorter limits.
    config.worker_timeout = 600 # e.g., 10 minutes
    config.read_timeout = 600  # e.g., 10 minutes
    app_logger.info(f"Hypercorn worker timeout set to {config.worker_timeout} seconds.")
    app_logger.info(f"Hypercorn read timeout set to {config.read_timeout} seconds.")
    # --- MODIFICATION END ---
    await hypercorn.asyncio.serve(app, config)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Trusted Data Agent web client.")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind the server to. Use '0.0.0.0' for Docker."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind the server to."
    )
    parser.add_argument("--all-models", action="store_true", help="Allow selection of all available models.")
    args = parser.parse_args()

    if args.all_models:
        APP_CONFIG.ALL_MODELS_UNLOCKED = True
        print("\n--- DEV MODE: All models will be selectable. ---\n")

    print("\n--- CHARTING ENABLED: Charting configuration is active. ---\n")

    if APP_CONFIG.VOICE_CONVERSATION_ENABLED:
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            print("\n--- ⚠️ VOICE FEATURE WARNING ---\n")
            print("The 'GOOGLE_APPLICATION_CREDENTIALS' environment variable is not set.")
            print("The voice conversation feature will require credentials to be provided in the config UI.")
        else:
            print("\n--- VOICE FEATURE ENABLED: Credentials found in environment. ---\n")

    try:
        asyncio.run(main(args)) # MODIFIED: Pass args to main
    except KeyboardInterrupt:
        print("\nServer shut down.")