# src/trusted_data_agent/core/config.py
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

class AppConfig:
    """
    Holds static configuration settings for the application.
    These values are typically set at startup and rarely change during runtime.
    """
    # --- Feature Flags & Behavior ---
    CONFIGURATION_PERSISTENCE = os.environ.get('TDA_CONFIGURATION_PERSISTENCE', 'true').lower() != 'false'
    ALL_MODELS_UNLOCKED = False # If True, bypasses model certification checks, allowing all models from a provider to be used.
    CHARTING_ENABLED = True # Master switch to enable or disable the agent's ability to generate charts.
    DEFAULT_CHARTING_INTENSITY = "medium" # Controls how proactively the agent suggests charts. Options: "none", "medium", "heavy".
    ALLOW_SYNTHESIS_FROM_HISTORY = True # If True, allows the planner to generate an answer directly from conversation history without using tools.
    VOICE_CONVERSATION_ENABLED = True # Master switch for the Text-to-Speech (TTS) feature.
    SUB_PROMPT_FORCE_SUMMARY = False # If True, forces sub-executors for prompts to generate their own final summary. Default is False.
    ENABLE_SQL_CONSOLIDATION_REWRITE = False # If True, enables an LLM-based plan rewrite rule to consolidate sequential SQL queries.
    GRANTED_PROMPTS_FOR_EFFICIENCY_REPLANNING = ["base_teradataQuery"] # A list of complex prompts that are exempt from the "Re-planning for Efficiency" optimization.
    CONDENSE_SYSTEMPROMPT_HISTORY = True # If True, sends a condensed list of tools/prompts in the system prompt for subsequent turns in a conversation to save tokens.
    ENABLE_MCP_CLASSIFICATION = True # If True, uses LLM to classify MCP tools/prompts into categories. If False, uses single categories ('All Tools', 'All Prompts', 'All Resources') for faster configuration.


    # --- Connection & Model State ---
    SERVICES_CONFIGURED = False # Master flag indicating if the core services (LLM, MCP) have been successfully configured.
    ACTIVE_PROVIDER = None
    ACTIVE_MODEL = None
    ACTIVE_MCP_SERVER_NAME = None
    MCP_SERVER_CONNECTED = False # Runtime flag indicating if a connection to the MCP server is active.
    CHART_MCP_CONNECTED = False # Runtime flag indicating if a connection to the Charting server is active.
    CURRENT_PROVIDER = None # Stores the name of the currently configured LLM provider (e.g., "Google").
    CURRENT_MODEL = None # Stores the name of the currently configured LLM model (e.g., "gemini-1.5-flash").
    CURRENT_MCP_SERVER_NAME = None # Stores the name of the active MCP server configuration.
    CURRENT_MCP_SERVER_ID = None # Stores the unique ID of the active MCP server (decoupled from name).
    CURRENT_AWS_REGION = None # Stores the AWS region, used specifically for the "Amazon" provider.
    CURRENT_AZURE_DEPLOYMENT_DETAILS = None # Stores Azure-specific details {endpoint, deployment_name, api_version}.
    CURRENT_FRIENDLI_DETAILS = None # Stores Friendli.ai specific details {token, endpoint_url}.
    CURRENT_MODEL_PROVIDER_IN_PROFILE = None # For Amazon Bedrock, stores the model provider if using an inference profile ARN.

    # --- LLM & Agent Configuration ---
    MCP_SYSTEM_NAME = "Teradata database system" # Describes the target system to the LLM in master prompts to provide context.
    LLM_API_MAX_RETRIES = 5 # The maximum number of times to retry a failed LLM API call.
    LLM_API_BASE_DELAY = 2 # The base delay in seconds for exponential backoff on API retries.
    CONTEXT_DISTILLATION_MAX_ROWS = 500 # The maximum number of rows from a tool's result to include in the LLM context.
    CONTEXT_DISTILLATION_MAX_CHARS = 10000 # The maximum number of characters from a tool's result to include in the LLM context.
    DETAILED_DESCRIPTION_THRESHOLD = 200 # A heuristic character count for the PlanExecutor to distinguish between a generic vs. a detailed task description from the planner.
    SQL_OPTIMIZATION_PROMPTS = []
    SQL_OPTIMIZATION_TOOLS = ["base_readQuery"]

    # RAG Configuration
    RAG_ENABLED = True
    RAG_REFRESH_ON_STARTUP = True # If True, vector store is refreshed on startup. If False, it uses cache until manually refreshed.
    RAG_CASES_DIR = "rag/tda_rag_cases"
    RAG_PERSIST_DIR = ".chromadb_rag_cache"
    RAG_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    RAG_NUM_EXAMPLES = 3 # Total number of few-shot examples to retrieve across all active collections
    RAG_DEFAULT_COLLECTION_NAME = "default_collection" # ChromaDB collection name for default collection (ID 0)
    
    # Session & Analytics Configuration
    SESSIONS_FILTER_BY_USER = os.environ.get('TDA_SESSIONS_FILTER_BY_USER', 'true').lower() == 'false' # If True, execution dashboard shows only current user's sessions. If False, shows all sessions.


    # --- Initial State Configuration ---
    INITIALLY_DISABLED_PROMPTS = [
        "base_query",
        "qlty_databaseQuality",
        "dba_databaseLineage",
        "base_tableBusinessDesc",
        "base_databaseBusinessDesc",
        "dba_databaseHealthAssessment",
        "dba_userActivityAnalysis",
        "dba_systemVoice",
        "dba_tableArchive",
        "dba_tableDropImpact",
        "_testMyServer"
    ]
    INITIALLY_DISABLED_TOOLS = ["sales_top_customers", "plot_line_chart","plot_pie_chart", "plot_polar_chart", "plot_radar_chart", "sql_Analyze_Cluster_Stats", "rag_Execute_Workflow","sql_Execute_Full_Pipeline", "sql_Retrieve_Cluster_Queries"] # A list of tool names to be disabled by default on application startup.

    # --- Tool & Argument Parsing Logic ---
    TOOL_SCOPE_HIERARCHY = [
        ('column', {'database_name', 'object_name', 'column_name'}),
        ('table', {'database_name', 'object_name'}),
        ('database', {'database_name'}),
    ]
    ARGUMENT_SYNONYM_MAP = {
        'database_name': {
            'database_name', 'db_name', 'DatabaseName'
        },
        'object_name':   {
            'table_name', 'tablename', 'TableName',
            'object_name', 'obj_name', 'ObjectName', 'objectname',
            'view_name', 'viewname', 'ViewName'
        },
        'column_name':   {
            'column_name', 'col_name', 'ColumnName'
        },
    }

APP_CONFIG = AppConfig()

APP_STATE = {
    # Live client instances and server configurations
    "llm": None, 
    "mcp_client": None, 
    "server_configs": {},

    # Raw tool/prompt definitions loaded from the MCP server
    "mcp_tools": {}, 
    "mcp_prompts": {}, 
    "mcp_charts": {},

    # Processed and categorized structures for UI display
    "structured_tools": {}, 
    "structured_prompts": {}, 
    "structured_resources": {}, 
    "structured_charts": {},

    # Cache for inferred tool operational scopes (e.g., 'table', 'column')
    "tool_scopes": {},

    # Formatted context strings injected into LLM prompts
    "tools_context": "--- No Tools Available ---", 
    "prompts_context": "--- No Prompts Available ---", 
    "charts_context": "--- No Charts Available ---",
    "constraints_context": "",

    # Runtime lists of currently disabled capabilities
    "disabled_prompts": list(APP_CONFIG.INITIALLY_DISABLED_PROMPTS),
    "disabled_tools": list(APP_CONFIG.INITIALLY_DISABLED_TOOLS),

    # Validated license information
    "license_info": None,

    # Asynchronous task tracking for the REST API
    "background_tasks": {},
    
    # --- MODIFICATION START: Add RAG queue and instance placeholder ---
    # Asynchronous RAG processing queue and singleton instance
    "rag_processing_queue": asyncio.Queue(),
    "rag_retriever_instance": None,
    # RAG collections configuration: list of collection metadata
    # Each collection: {id, name, collection_name, mcp_server_id, enabled, created_at, description}
    "rag_collections": [],
    # --- MODIFICATION END ---

    # Concurrency lock for the configuration process
    "configuration_lock": asyncio.Lock(),
}

# Whitelists for models that are officially supported.
# The ALL_MODELS_UNLOCKED flag bypasses these checks.
CERTIFIED_GOOGLE_MODELS = ["gemini-2.0-flash"]
CERTIFIED_ANTHROPIC_MODELS = ["*claude-3-5-haiku-2024102*"]
CERTIFIED_AMAZON_MODELS = ["*titan-text-express-v1*"]
CERTIFIED_AMAZON_PROFILES = ["*nova-lite*"]
CERTIFIED_OLLAMA_MODELS = ["llama3.1:8b-instruct-q8_0"]
CERTIFIED_OPENAI_MODELS = ["*gpt-4o-mini"]
CERTIFIED_AZURE_MODELS = ["*gpt-4o*"]
CERTIFIED_FRIENDLI_MODELS = ["google/gemma-3-27b-it"]