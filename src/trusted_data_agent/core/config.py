# src/trusted_data_agent/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class AppConfig:
    ALL_MODELS_UNLOCKED = False
    CHARTING_ENABLED = True
    DEFAULT_CHARTING_INTENSITY = "medium" # Options: "none", "medium", "heavy"
    MCP_SERVER_CONNECTED = False
    CHART_MCP_CONNECTED = False
    CURRENT_PROVIDER = None
    CURRENT_MODEL = None
    CURRENT_MCP_SERVER_NAME = None

    MCP_SYSTEM_NAME = "Teradata database system" # Derives System Specifics behaviour for Master Prompts

    CURRENT_AWS_REGION = None
    CURRENT_MODEL_PROVIDER_IN_PROFILE = None
    LLM_API_MAX_RETRIES = 5
    LLM_API_BASE_DELAY = 2 # The base delay in seconds for exponential backoff
    ALLOW_SYNTHESIS_FROM_HISTORY = False

    VOICE_CONVERSATION_ENABLED = True # Set to True to enable the voice conversation UI

    CONTEXT_DISTILLATION_MAX_ROWS = 500
    CONTEXT_DISTILLATION_MAX_CHARS = 10000
    
    # Heuristic for the PlanExecutor to distinguish between a generic vs. detailed task description.
    # Descriptions shorter than this are considered generic and can be overridden by a standard summary prompt.
    DETAILED_DESCRIPTION_THRESHOLD = 200

    #INITIALLY_DISABLED_PROMPTS = ["base_query","cust_promptExample","qlty_databaseQuality","dba_tableArchive","dba_databaseLineage", "dba_tableDropImpact", "dba_databaseHealthAssessment", "dba_userActivityAnalysis", "dba_systemVoice", "base_databaseBusinessDesc", "sales_prompt", "test_evsTools", "test_secTools", "test_dbaTools", "test_ragTools", "test_qltyTools", "test_fsTools", "test_baseTools", "rag_guidelines" ]
    INITIALLY_DISABLED_PROMPTS = []
    INITIALLY_DISABLED_TOOLS = ["sales_top_customers"]

    # Defines the hierarchy for inferring a tool's operational scope based on its
    # required arguments. The list is ordered from most specific to least specific,
    # and it uses canonical names defined in the ARGUMENT_SYNONYM_MAP below.
    TOOL_SCOPE_HIERARCHY = [
        ('column', {'database_name', 'object_name', 'column_name'}),
        ('table', {'database_name', 'object_name'}),
        ('database', {'database_name'}),
    ]

    # Defines a central map for all argument synonyms. This allows the application
    # to correctly map different argument names (e.g., 'obj_name', 'view_name')
    # to a single canonical concept (e.g., 'object_name').
    ARGUMENT_SYNONYM_MAP = {
        # Canonical Name : { Set of all synonyms }
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
    "llm": None, "mcp_client": None, "server_configs": {},
    "mcp_tools": {}, "mcp_prompts": {}, "mcp_charts": {},
    "structured_tools": {}, "structured_prompts": {}, "structured_resources": {}, "structured_charts": {},
    "tool_scopes": {},
    "tools_context": "--- No Tools Available ---", "prompts_context": "--- No Prompts Available ---", "charts_context": "--- No Charts Available ---",
    "disabled_prompts": list(APP_CONFIG.INITIALLY_DISABLED_PROMPTS),
    "disabled_tools": list(APP_CONFIG.INITIALLY_DISABLED_TOOLS),
    "license_info": None
}

CERTIFIED_GOOGLE_MODELS = ["*gemini-2.0-flash"]
CERTIFIED_ANTHROPIC_MODELS = ["*claude-3-7-sonnet*"]
CERTIFIED_AMAZON_MODELS = ["*amazon.nova-pro-v1*"]
CERTIFIED_AMAZON_PROFILES = ["*amazon.nova-pro-v1*"]
CERTIFIED_OLLAMA_MODELS = ["llama2"]
CERTIFIED_OPENAI_MODELS = ["*gpt-4.1-mini-2025*"]