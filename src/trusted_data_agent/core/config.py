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
    ALL_MODELS_UNLOCKED = False # If True, bypasses model certification checks, allowing all models from a provider to be used.
    CHARTING_ENABLED = True # Master switch to enable or disable the agent's ability to generate charts.
    DEFAULT_CHARTING_INTENSITY = "medium" # Controls how proactively the agent suggests charts. Options: "none", "medium", "heavy".
    ALLOW_SYNTHESIS_FROM_HISTORY = True # If True, allows the planner to generate an answer directly from conversation history without using tools.
    VOICE_CONVERSATION_ENABLED = True # Master switch for the Text-to-Speech (TTS) feature.
    SUB_PROMPT_FORCE_SUMMARY = False # If True, forces sub-executors for prompts to generate their own final summary. Default is False.
    GRANTED_PROMPTS_FOR_EFFICIENCY_REPLANNING = ["base_teradataQuery"] # A list of complex prompts that are exempt from the "Re-planning for Efficiency" optimization.
    CONDENSE_SYSTEMPROMPT_HISTORY = True # If True, sends a condensed list of tools/prompts in the system prompt for subsequent turns in a conversation to save tokens.


    # --- Connection & Model State ---
    # --- MODIFICATION START: Add state-aware configuration flags ---
    SERVICES_CONFIGURED = False # Master flag indicating if the core services (LLM, MCP) have been successfully configured.
    # The following fields store the details of the *active* configuration to detect changes.
    ACTIVE_PROVIDER = None
    ACTIVE_MODEL = None
    ACTIVE_MCP_SERVER_NAME = None
    # --- MODIFICATION END ---
    MCP_SERVER_CONNECTED = False # Runtime flag indicating if a connection to the MCP server is active.
    CHART_MCP_CONNECTED = False # Runtime flag indicating if a connection to the Charting server is active.
    CURRENT_PROVIDER = None # Stores the name of the currently configured LLM provider (e.g., "Google").
    CURRENT_MODEL = None # Stores the name of the currently configured LLM model (e.g., "gemini-1.5-flash").
    CURRENT_MCP_SERVER_NAME = None # Stores the name of the active MCP server configuration.
    CURRENT_AWS_REGION = None # Stores the AWS region, used specifically for the "Amazon" provider.
    CURRENT_MODEL_PROVIDER_IN_PROFILE = None # For Amazon Bedrock, stores the model provider if using an inference profile ARN.

    # --- LLM & Agent Configuration ---
    MCP_SYSTEM_NAME = "Teradata database system" # Describes the target system to the LLM in master prompts to provide context.
    LLM_API_MAX_RETRIES = 5 # The maximum number of times to retry a failed LLM API call.
    LLM_API_BASE_DELAY = 2 # The base delay in seconds for exponential backoff on API retries.
    CONTEXT_DISTILLATION_MAX_ROWS = 500 # The maximum number of rows from a tool's result to include in the LLM context.
    CONTEXT_DISTILLATION_MAX_CHARS = 10000 # The maximum number of characters from a tool's result to include in the LLM context.
    DETAILED_DESCRIPTION_THRESHOLD = 200 # A heuristic character count for the PlanExecutor to distinguish between a generic vs. a detailed task description from the planner.
    SQL_OPTIMIZATION_PROMPTS = ["base_teradataQuery"] # A list of prompts that should be favored for SQL consolidation, if the rule is active.
    SQL_OPTIMIZATION_TOOLS = ["base_readQuery"] # A list of tools that should be favored for SQL consolidation, if the rule is active.

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
    INITIALLY_DISABLED_TOOLS = ["sales_top_customers"] # A list of tool names to be disabled by default on application startup.

    # --- Tool & Argument Parsing Logic ---
    # Defines the hierarchy for inferring a tool's operational scope (e.g., column-level, table-level) based on its required arguments.
    TOOL_SCOPE_HIERARCHY = [
        ('column', {'database_name', 'object_name', 'column_name'}),
        ('table', {'database_name', 'object_name'}),
        ('database', {'database_name'}),
    ]
    # A central map to normalize different argument names (e.g., 'table_name', 'object_name') to a single canonical concept.
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
    
    # Concurrency lock for the configuration process
    "configuration_lock": asyncio.Lock(),
}

# Whitelists for models that are officially supported.
# The ALL_MODELS_UNLOCKED flag bypasses these checks.
CERTIFIED_GOOGLE_MODELS = ["*gemini-1.5-flash*"]
CERTIFIED_ANTHROPIC_MODELS = ["*claude-3-sonnet*"]
CERTIFIED_AMAZON_MODELS = ["*amazon.titan-text-express-v1*"]
CERTIFIED_AMAZON_PROFILES = ["*amazon.titan-text-express-v1*"]
CERTIFIED_OLLAMA_MODELS = ["llama2"]
CERTIFIED_OPENAI_MODELS = ["*gpt-4-turbo*"]
