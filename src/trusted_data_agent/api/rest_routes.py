# src/trusted_data_agent/api/rest_routes.py
import asyncio
import json
import logging
from datetime import datetime, timezone
import re
import uuid # Import uuid
import copy # --- MODIFICATION START: Import copy ---

# --- MODIFICATION START: Import generate_task_id ---
from quart import Blueprint, current_app, jsonify, request, abort
from trusted_data_agent.core.utils import generate_task_id, _get_prompt_info
# --- MODIFICATION END ---

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.core import session_manager
from trusted_data_agent.agent import execution_service
from trusted_data_agent.core import configuration_service

from trusted_data_agent.agent.executor import PlanExecutor
from langchain_mcp_adapters.prompts import load_mcp_prompt
from trusted_data_agent.llm import handler as llm_handler

rest_api_bp = Blueprint('rest_api', __name__)
app_logger = logging.getLogger("quart.app") # Use quart logger

# --- MODIFICATION START: Helper to get User UUID (copied from routes.py) ---
def _get_user_uuid_from_request():
    """Extracts the User UUID from the request header."""
    user_uuid = request.headers.get('X-TDA-User-UUID')
    if not user_uuid:
        app_logger.warning("REST API: Missing X-TDA-User-UUID header in request.")
        abort(400, "Missing required X-TDA-User-UUID header.")
    return user_uuid
# --- MODIFICATION END ---

def _sanitize_for_json(obj):
    """
    Recursively sanitizes an object to make it JSON-serializable by removing
    non-printable characters from strings.
    """
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(elem) for elem in obj]
    elif isinstance(obj, str):
        # Remove ASCII control characters (0x00-0x1F), except for newline,
        # carriage return, and tab, which are valid in JSON strings.
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', obj)
    else:
        return obj


@rest_api_bp.route("/v1/prompts/<prompt_name>/execute", methods=["POST"])
async def execute_prompt(prompt_name: str):
    """
    Execute an MCP prompt with the LLM and return the response.
    
    Request body:
    {
        "arguments": {"database": "mydb", ...}  // Optional prompt arguments
    }
    
    Returns:
    {
        "status": "success",
        "prompt_text": "<rendered prompt>",
        "response": "<LLM response>",
        "input_tokens": 123,
        "output_tokens": 456
    }
    """
    try:
        mcp_client = APP_STATE.get("mcp_client")
        if not mcp_client:
            return jsonify({
                "status": "error",
                "message": "MCP client not configured"
            }), 400

        server_name = APP_CONFIG.CURRENT_MCP_SERVER_NAME
        if not server_name:
            return jsonify({
                "status": "error",
                "message": "MCP server not configured"
            }), 400
            
        llm_instance = APP_STATE.get('llm')
        if not llm_instance:
            return jsonify({
                "status": "error",
                "message": "LLM not configured"
            }), 400

        # Get arguments from request body
        data = await request.get_json() or {}
        user_arguments = data.get('arguments', {})
        
        # Get prompt definition to know all expected arguments
        prompt_info = _get_prompt_info(prompt_name)
        prompt_arguments = {}
        
        if prompt_info and prompt_info.get("arguments"):
            # Build complete argument set - MCP server may require all arguments
            for arg in prompt_info["arguments"]:
                arg_name = arg.get("name")
                if arg_name:
                    if arg_name in user_arguments:
                        # Use user-provided value
                        prompt_arguments[arg_name] = user_arguments[arg_name]
                    elif arg.get("required"):
                        # Required argument missing
                        return jsonify({
                            "status": "error",
                            "message": f"Required argument '{arg_name}' is missing"
                        }), 400
                    else:
                        # Optional argument - use placeholder or empty string
                        prompt_arguments[arg_name] = ""
        else:
            # No argument definition found, use what user provided
            prompt_arguments = user_arguments
        
        # Load the prompt with arguments
        app_logger.info(f"Executing prompt '{prompt_name}' with server '{server_name}' and arguments: {prompt_arguments}")
        
        try:
            async with mcp_client.session(server_name) as temp_session:
                if prompt_arguments:
                    prompt_obj = await load_mcp_prompt(
                        temp_session, name=prompt_name, arguments=prompt_arguments
                    )
                else:
                    prompt_obj = await temp_session.get_prompt(name=prompt_name)
        except Exception as e:
            app_logger.error(f"Failed to load prompt '{prompt_name}' from MCP server: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Failed to load prompt from MCP server: {str(e)}"
            }), 500
        
        if not prompt_obj:
            return jsonify({
                "status": "error",
                "message": f"Prompt '{prompt_name}' not found"
            }), 404
        
        # Extract prompt text (reuse existing logic from planner.py)
        prompt_text = ""
        if isinstance(prompt_obj, str):
            prompt_text = prompt_obj
        elif (isinstance(prompt_obj, list) and len(prompt_obj) > 0 and 
              hasattr(prompt_obj[0], 'content')):
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
            
        if not prompt_text:
            return jsonify({
                "status": "error",
                "message": "Could not extract text from prompt"
            }), 500
        
        # Log the rendered prompt for debugging
        app_logger.info(f"Rendered prompt text (first 200 chars):\n{prompt_text[:200]}")
        app_logger.info(f"Arguments passed: {prompt_arguments}")
        
        # Create a temporary session and use the agent execution service
        # This ensures tools are properly registered and execution is autonomous
        temp_user_uuid = "api-prompt-executor"
        llm_instance = APP_STATE.get("llm")
        
        temp_session_id = session_manager.create_session(
            user_uuid=temp_user_uuid,
            provider=APP_CONFIG.CURRENT_PROVIDER,
            llm_instance=llm_instance,
            charting_intensity="medium"
        )
        
        app_logger.info(f"Executing MCP prompt '{prompt_name}' via agent execution service with temp session: {temp_session_id}")
        
        # Create a dummy event handler for API calls (no SSE needed)
        async def dummy_event_handler(data, event_type):
            app_logger.debug(f"Prompt execution event: {event_type}")
        
        # Execute using the agent execution service which handles tool registration properly
        result_payload = await execution_service.run_agent_execution(
            user_uuid=temp_user_uuid,
            session_id=temp_session_id,
            user_input=prompt_text,
            event_handler=dummy_event_handler,  # Provide dummy handler instead of None
            source='prompt_library'  # Indicates this is a prompt execution
        )
        
        # Extract response and tokens from result
        response_html = result_payload.get('final_answer', '')
        response_text = result_payload.get('final_answer_text', '')  # Clean text without HTML
        input_tokens = result_payload.get('total_input_tokens', 0)
        output_tokens = result_payload.get('total_output_tokens', 0)
        actual_provider = APP_CONFIG.CURRENT_PROVIDER
        actual_model = APP_CONFIG.CURRENT_MODEL
        
        # Clean up the temporary session
        try:
            session_manager.delete_session(temp_user_uuid, temp_session_id)
            app_logger.debug(f"Deleted temp session {temp_session_id}")
        except Exception as e:
            app_logger.warning(f"Failed to delete temp session {temp_session_id}: {e}")
        
        app_logger.info(f"Prompt '{prompt_name}' executed successfully. Tokens: in={input_tokens}, out={output_tokens}")
        
        return jsonify({
            "status": "success",
            "prompt_text": prompt_text,
            "response": response_html,  # HTML formatted response for display
            "response_text": response_text,  # Clean text for LLM consumption
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "provider": actual_provider,
            "model": actual_model
        })
        
    except Exception as e:
        app_logger.error(f"Error executing prompt '{prompt_name}': {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@rest_api_bp.route("/v1/prompts/<prompt_name>/execute-raw", methods=["POST"])
async def execute_prompt_raw(prompt_name: str):
    """
    Execute an MCP prompt and return raw, structured execution data.
    
    This endpoint is designed for programmatic consumption (e.g., auto-generating RAG cases)
    where clean, structured data is needed rather than HTML-formatted responses.
    
    Request body:
    {
        "arguments": {"database": "mydb", ...}  // Optional prompt arguments
    }
    
    Returns:
    {
        "status": "success",
        "prompt_text": "<rendered prompt>",
        "execution_trace": [...],
        "collected_data": {...},
        "final_answer_text": "<clean LLM summary>",
        "token_usage": {"input": 123, "output": 456, "total": 579}
    }
    """
    try:
        mcp_client = APP_STATE.get("mcp_client")
        if not mcp_client:
            return jsonify({"status": "error", "message": "MCP client not configured"}), 400

        server_name = APP_CONFIG.CURRENT_MCP_SERVER_NAME
        if not server_name:
            return jsonify({"status": "error", "message": "MCP server not configured"}), 400
            
        llm_instance = APP_STATE.get('llm')
        if not llm_instance:
            return jsonify({"status": "error", "message": "LLM not configured"}), 400

        # Get arguments from request body
        data = await request.get_json() or {}
        user_arguments = data.get('arguments', {})
        
        # Get prompt definition to know all expected arguments
        prompt_info = _get_prompt_info(prompt_name)
        prompt_arguments = {}
        
        if prompt_info and prompt_info.get("arguments"):
            for arg in prompt_info["arguments"]:
                arg_name = arg.get("name")
                if arg_name:
                    if arg_name in user_arguments:
                        prompt_arguments[arg_name] = user_arguments[arg_name]
                    elif arg.get("required"):
                        return jsonify({
                            "status": "error",
                            "message": f"Required argument '{arg_name}' is missing"
                        }), 400
                    else:
                        prompt_arguments[arg_name] = ""
        else:
            prompt_arguments = user_arguments
        
        # Load the prompt with arguments
        app_logger.info(f"Executing prompt '{prompt_name}' (raw mode) with server '{server_name}'")
        
        try:
            async with mcp_client.session(server_name) as temp_session:
                if prompt_arguments:
                    prompt_obj = await load_mcp_prompt(
                        temp_session, name=prompt_name, arguments=prompt_arguments
                    )
                else:
                    prompt_obj = await temp_session.get_prompt(name=prompt_name)
        except Exception as e:
            app_logger.error(f"Failed to load prompt '{prompt_name}': {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Failed to load prompt: {str(e)}"
            }), 500
        
        if not prompt_obj:
            return jsonify({"status": "error", "message": f"Prompt '{prompt_name}' not found"}), 404
        
        # Extract prompt text (reuse existing logic)
        prompt_text = ""
        if isinstance(prompt_obj, str):
            prompt_text = prompt_obj
        elif (isinstance(prompt_obj, list) and len(prompt_obj) > 0 and 
              hasattr(prompt_obj[0], 'content')):
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
            
        if not prompt_text:
            return jsonify({"status": "error", "message": "Could not extract text from prompt"}), 500
        
        # Create temporary session
        temp_user_uuid = "api-prompt-executor-raw"
        temp_session_id = session_manager.create_session(
            user_uuid=temp_user_uuid,
            provider=APP_CONFIG.CURRENT_PROVIDER,
            llm_instance=llm_instance,
            charting_intensity="medium"
        )
        
        app_logger.info(f"Executing prompt '{prompt_name}' (raw) with temp session: {temp_session_id}")
        
        # Dummy event handler
        async def dummy_event_handler(data, event_type):
            app_logger.debug(f"Event: {event_type}")
        
        # Execute via agent execution service
        result_payload = await execution_service.run_agent_execution(
            user_uuid=temp_user_uuid,
            session_id=temp_session_id,
            user_input=prompt_text,
            event_handler=dummy_event_handler,
            source='prompt_library_raw'
        )
        
        # Clean up temp session
        try:
            session_manager.delete_session(temp_user_uuid, temp_session_id)
        except Exception as e:
            app_logger.warning(f"Failed to delete temp session: {e}")
        
        # Extract data from result
        execution_trace = result_payload.get('execution_trace', [])
        collected_data = result_payload.get('collected_data', {})
        final_answer_text = result_payload.get('final_answer_text', '')
        input_tokens = result_payload.get('turn_input_tokens', 0)
        output_tokens = result_payload.get('turn_output_tokens', 0)
        
        app_logger.info(f"Prompt '{prompt_name}' (raw) done. Tokens: in={input_tokens}, out={output_tokens}")
        
        return jsonify({
            "status": "success",
            "prompt_text": prompt_text,
            "execution_trace": execution_trace,
            "collected_data": collected_data,
            "final_answer_text": final_answer_text,
            "token_usage": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            },
            "provider": APP_CONFIG.CURRENT_PROVIDER,
            "model": APP_CONFIG.CURRENT_MODEL
        })
        
    except Exception as e:
        app_logger.error(f"Error executing prompt '{prompt_name}' (raw): {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/generate-questions", methods=["POST"])
async def generate_rag_questions():
    """
    Generate question/SQL pairs for RAG collection population.
    
    Request body:
    {
        "subject": "sales analysis",
        "count": 5,
        "database_context": "...",  // Output from Phase 2 (database context)
        "database_name": "fitness_db"
    }
    
    Returns:
    {
        "status": "success",
        "questions": [
            {"question": "What are...", "sql": "SELECT..."},
            ...
        ],
        "count": 5
    }
    """
    try:
        # Get configuration
        mcp_client = APP_STATE.get("mcp_client")
        if not mcp_client:
            return jsonify({
                "status": "error",
                "message": "MCP client not configured"
            }), 400

        llm_instance = APP_STATE.get('llm')
        if not llm_instance:
            return jsonify({
                "status": "error",
                "message": "LLM not configured"
            }), 400

        # Get parameters from request
        data = await request.get_json() or {}
        subject = data.get('subject', '').strip()
        count = int(data.get('count', 5))
        database_context = data.get('database_context', '').strip()
        database_name = data.get('database_name', '').strip()
        target_database = data.get('target_database', 'Teradata').strip()
        
        if not subject:
            return jsonify({
                "status": "error",
                "message": "Subject is required"
            }), 400
            
        if not database_context:
            return jsonify({
                "status": "error",
                "message": "Database context is required (run Phase 2 first)"
            }), 400
            
        if not database_name:
            return jsonify({
                "status": "error",
                "message": "Database name is required"
            }), 400
        
        # Construct the prompt for generating questions
        prompt_text = f"""You are a SQL expert helping to generate test questions and queries for a RAG system.

Based on the following database context, generate {count} diverse, interesting business questions about "{subject}" along with the SQL queries that would answer them.

Database Context:
{database_context}

Requirements:
1. Generate EXACTLY {count} question/SQL pairs
2. Questions should be natural language business questions about {subject}
3. SQL queries must be valid {target_database} syntax for the database schema shown above
4. Use {target_database}-specific SQL syntax, functions, and conventions
5. Questions should vary in complexity (simple to advanced)
6. Use the database name "{database_name}" in your queries
7. Return your response as a valid JSON array with this exact structure:
[
  {{
    "question": "What is the total revenue by product category?",
    "sql": "SELECT ProductType, SUM(Price * StockQuantity) as TotalValue FROM {database_name}.Products GROUP BY ProductType;"
  }},
  {{
    "question": "Which customer has the highest order value?",
    "sql": "SELECT CustomerID, CustomerName, MAX(OrderTotal) as MaxOrder FROM {database_name}.Orders GROUP BY CustomerID, CustomerName ORDER BY MaxOrder DESC LIMIT 1;"
  }}
]

IMPORTANT: 
- Write COMPLETE SQL queries - do NOT truncate them with "..." or similar
- Your entire response must be ONLY the JSON array, with no other text before or after
- Include all {count} question/SQL pairs requested

        app_logger.info(f"Generating {count} RAG questions for subject '{subject}' in database '{database_name}'")
        
        # Call LLM directly using the handler to avoid agent execution framework and TDA_FinalReport validation
        from trusted_data_agent.llm import handler as llm_handler
        
        try:
            # Direct LLM invocation using the existing handler
            response_text, input_tokens, output_tokens, provider, model = await llm_handler.call_llm_api(
                llm_instance=llm_instance,
                prompt=prompt_text,
                user_uuid="api-question-generator",
                session_id=None,
                dependencies={'STATE': APP_STATE, 'CONFIG': APP_CONFIG},
                reason="Generating RAG questions",
                disabled_history=True,  # Don't store this in chat history
                source='rag_question_generator'
            )
            
            app_logger.info(f"LLM generated response with {input_tokens} input tokens, {output_tokens} output tokens")
            
        except Exception as e:
            app_logger.error(f"Failed to generate questions with LLM: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"LLM invocation failed: {str(e)}"
            }), 500
        
        # Parse the JSON response
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            json_text = response_text.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]  # Remove ```json
            elif json_text.startswith('```'):
                json_text = json_text[3:]  # Remove ```
            if json_text.endswith('```'):
                json_text = json_text[:-3]  # Remove trailing ```
            json_text = json_text.strip()
            
            questions = json.loads(json_text)
            
            if not isinstance(questions, list):
                raise ValueError("Response is not a JSON array")
            
            # Validate structure
            for q in questions:
                if not isinstance(q, dict) or 'question' not in q or 'sql' not in q:
                    raise ValueError("Invalid question structure")
            
            app_logger.info(f"Successfully generated {len(questions)} question/SQL pairs")
            
            return jsonify({
                "status": "success",
                "questions": questions,
                "count": len(questions),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            })
            
        except json.JSONDecodeError as e:
            app_logger.error(f"Failed to parse LLM response as JSON: {e}")
            app_logger.error(f"Response was: {response_text[:500]}")
            return jsonify({
                "status": "error",
                "message": "LLM did not return valid JSON",
                "raw_response": response_text[:1000]
            }), 500
        except ValueError as e:
            app_logger.error(f"Invalid question structure: {e}")
            return jsonify({
                "status": "error",
                "message": str(e),
                "raw_response": response_text[:1000]
            }), 500
        
    except Exception as e:
        app_logger.error(f"Error generating RAG questions: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@rest_api_bp.route("/v1/configure", methods=["POST"])
async def configure_services_rest():
    """
    Configures and validates the core LLM and MCP services via the REST API.
    This is a protected, atomic operation that uses the centralized
    configuration service.
    """
    # Configuration is global, no user UUID needed.
    config_data = await request.get_json()
    if not config_data:
        return jsonify({"status": "error", "message": "Request body must be a valid JSON."}), 400

    result = await configuration_service.setup_and_categorize_services(config_data)

    if result.get("status") == "success":
        # --- MODIFICATION START: Broadcast reconfiguration notification ---
        # Create a copy of the config to sanitize it for notification
        safe_config = config_data.copy()
        if "credentials" in safe_config:
            safe_config["credentials"] = {k: v for k, v in safe_config["credentials"].items() if "key" not in k.lower() and "token" not in k.lower()}
        if "tts_credentials_json" in safe_config:
            del safe_config["tts_credentials_json"]

        notification = {
            "type": "reconfiguration",
            "payload": {
                "message": "Application has been reconfigured via REST API. A refresh is required.",
                "config": safe_config
            }
        }

        # Broadcast to all active notification queues
        all_queues = [q for user_queues in APP_STATE.get("notification_queues", {}).values() for q in user_queues]
        app_logger.info(f"Found {len(all_queues)} active notification queues.")
        if all_queues:
            app_logger.info(f"Broadcasting reconfiguration notification to {len(all_queues)} client(s).")
            for queue in all_queues:
                asyncio.create_task(queue.put(notification))
        # --- MODIFICATION END ---
        return jsonify(result), 200
    else:
        # Configuration errors are client-side problems (bad keys, wrong host, etc.)
        # so a 400-level error is more appropriate than a 500.
        return jsonify(result), 400

@rest_api_bp.route("/v1/sessions", methods=["POST"])
async def create_session():
    """Creates a new conversation session *for the requesting user*."""
    # --- MODIFICATION START: Get User UUID ---
    user_uuid = _get_user_uuid_from_request()
    # --- MODIFICATION END ---

    if not APP_CONFIG.MCP_SERVER_CONNECTED:
        return jsonify({
            "error": "Application is not configured. Please connect to LLM and MCP services first."
        }), 503

    try:
        llm_instance = APP_STATE.get("llm")

        # --- MODIFICATION START: Pass User UUID ---
        session_id = session_manager.create_session(
            user_uuid=user_uuid, # Pass the UUID
            provider=APP_CONFIG.CURRENT_PROVIDER,
            llm_instance=llm_instance,
            charting_intensity=APP_CONFIG.DEFAULT_CHARTING_INTENSITY
            # system_prompt_template is not typically passed via REST API for creation
        )
        app_logger.info(f"REST API: Created new session: {session_id} for user {user_uuid}")

        # Retrieve the newly created session's full data
        new_session_data = session_manager.get_session(user_uuid=user_uuid, session_id=session_id)
        if new_session_data:
            # Prepare notification payload
            notification_payload = {
                "id": new_session_data["id"],
                "name": new_session_data.get("name", "New Chat"), # Default name if not present
                "models_used": new_session_data.get("models_used", []),
                "last_updated": new_session_data.get("last_updated", datetime.now(timezone.utc).isoformat())
            }

            # Broadcast to all active notification queues for this user
            notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
            if notification_queues:
                app_logger.info(f"Broadcasting new_session_created notification to {len(notification_queues)} client(s) for user {user_uuid}.")
                notification = {
                    "type": "new_session_created",
                    "payload": notification_payload
                }
                for queue in notification_queues:
                    asyncio.create_task(queue.put(notification))
        else:
            app_logger.warning(f"REST API: Could not retrieve full session data for new session {session_id} for user {user_uuid}.")

        return jsonify({"session_id": session_id}), 201
    except Exception as e:
        app_logger.error(f"Failed to create REST session for user {user_uuid}: {e}", exc_info=True)
        return jsonify({"error": "Failed to create session."}), 500

@rest_api_bp.route("/v1/sessions/<session_id>/query", methods=["POST"])
async def execute_query(session_id: str):
    """Submits a query to a session and starts a background task *for the requesting user*."""
    # --- MODIFICATION START: Get User UUID ---
    user_uuid = _get_user_uuid_from_request()
    # --- MODIFICATION END ---

    data = await request.get_json()
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "The 'prompt' field is required."}), 400

    # --- MODIFICATION START: Validate session for this user ---
    if not session_manager.get_session(user_uuid, session_id):
        app_logger.warning(f"REST API: Session '{session_id}' not found for user '{user_uuid}'.")
        return jsonify({"error": f"Session '{session_id}' not found."}), 404
    # --- MODIFICATION END ---

    task_id = generate_task_id()

    # Initialize the task state
    APP_STATE.setdefault("background_tasks", {})[task_id] = {
        "task_id": task_id,
        "user_uuid": user_uuid, # Store the user UUID with the task
        "session_id": session_id, # Store session ID for reference
        "status": "pending",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "events": [],
        "intermediate_data": [],
        "result": None
    }

    async def event_handler(event_data, event_type):
        """This handler is called by the execution service for each event."""
        task_status_dict = APP_STATE["background_tasks"].get(task_id)
        sanitized_event_data = _sanitize_for_json(event_data)

        # 1. Update the persistent task state (for polling clients)
        if task_status_dict:
            task_status_dict["events"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_data": sanitized_event_data,
                "event_type": event_type
            })
            if event_type == "tool_result" and isinstance(sanitized_event_data, dict):
                details = sanitized_event_data.get("details", {})
                if isinstance(details, dict) and details.get("status") == "success" and "results" in details:
                    task_status_dict["intermediate_data"].append({
                        "tool_name": details.get("metadata", {}).get("tool_name", "unknown_tool"),
                        "data": details["results"]
                    })
            task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

        # 2. Create and send a canonical event to the UI notification stream
        notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
        if notification_queues:
            try:
                # --- MODIFICATION START: Build canonical_event directly ---
                # No need to format/re-parse. Just build the dict.
                canonical_event = copy.deepcopy(sanitized_event_data)
                # Ensure 'type' key exists, merging the event_type string
                canonical_event['type'] = event_type
                # --- MODIFICATION END ---
                    
                # --- MODIFICATION START: Handle session_name_update as a top-level event ---
                # --- MODIFICATION START: Handle status_indicator_update directly ---
                if event_type == "status_indicator_update":
                    notification = {
                        "type": "status_indicator_update",
                        "payload": canonical_event # canonical_event already contains target and state
                    }
                    app_logger.debug(f"REST API: Emitting status_indicator_update for task {task_id}: {notification}")
                # --- MODIFICATION END ---
                elif event_type == "session_name_update":
                    notification = {
                        "type": "session_name_update",
                        "payload": canonical_event # Payload already contains session_id and newName
                    }
                else:
                    notification = {
                        "type": "rest_task_update",
                        "payload": {
                            "task_id": task_id,
                            "session_id": session_id,
                            "event": canonical_event
                        }
                    }
                # --- MODIFICATION END ---
                for queue in notification_queues:
                    asyncio.create_task(queue.put(notification))

            except Exception as e:
                app_logger.error(f"Failed to format or send canonical event for REST task {task_id}: {e}", exc_info=True)

    async def background_wrapper():
        """Wraps the execution to handle context, final state updates, and notifications."""
        task_status_dict = APP_STATE["background_tasks"].get(task_id)
        final_result_payload = None
        try:
            if task_status_dict: task_status_dict["status"] = "processing"

            final_result_payload = await execution_service.run_agent_execution(
                user_uuid=user_uuid,
                session_id=session_id,
                user_input=prompt,
                event_handler=event_handler,
                source='rest', # Identify source as REST
                task_id=task_id # Pass the task_id here
            )

            if task_status_dict:
                task_status_dict["status"] = "complete"
                task_status_dict["result"] = _sanitize_for_json(final_result_payload)
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

        except asyncio.CancelledError:
            app_logger.info(f"REST background task {task_id} (user {user_uuid}) was cancelled.")
            if task_status_dict:
                task_status_dict["status"] = "cancelled"
                task_status_dict["result"] = {"message": "Task cancelled by user."}
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            app_logger.error(f"Background task {task_id} (user {user_uuid}) failed: {e}", exc_info=True)
            if task_status_dict:
                task_status_dict["status"] = "error"
                task_status_dict["result"] = {"error": str(e)}
                task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
        finally:
            # Remove from ACTIVE tasks registry
            if task_id in APP_STATE.get("active_tasks", {}):
                del APP_STATE["active_tasks"][task_id]

            # Send final notification to UI clients on success
            if final_result_payload and task_status_dict and task_status_dict.get("status") == "complete":
                notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())
                if notification_queues:
                    completion_notification = {
                        "type": "rest_task_complete",
                        "payload": {
                            "task_id": task_id,
                            "session_id": session_id,
                            "turn_id": final_result_payload.get("turn_id"),
                            "user_input": prompt,
                            "final_answer": final_result_payload.get("final_answer")
                        }
                    }
                    app_logger.info(f"Sending rest_task_complete notification for user {user_uuid}")
                    for queue in notification_queues:
                        asyncio.create_task(queue.put(completion_notification))

            app_logger.info(f"Background task {task_id} (user {user_uuid}) finished with status: {task_status_dict.get('status', 'unknown') if task_status_dict else 'unknown'}")

    # Start the agent execution in the background
    task_object = asyncio.create_task(background_wrapper())
    # Store the actual task object for potential cancellation (uses task_id)
    APP_STATE.setdefault("active_tasks", {})[task_id] = task_object

    status_url = f"/api/v1/tasks/{task_id}"

    return jsonify({"task_id": task_id, "status_url": status_url}), 202

@rest_api_bp.route("/v1/tasks/<task_id>", methods=["GET"])
async def get_task_status(task_id: str):
    """Gets the status and results of a background task."""
    # --- MODIFICATION START: Get User UUID and optionally check ownership ---
    user_uuid = _get_user_uuid_from_request()
    task = APP_STATE["background_tasks"].get(task_id)

    if not task:
        app_logger.warning(f"REST API: Task '{task_id}' not found for user '{user_uuid}'.")
        return jsonify({"error": f"Task '{task_id}' not found."}), 404

    # Optional: Check if the requesting user owns this task
    if task.get("user_uuid") != user_uuid:
        app_logger.error(f"REST API: User '{user_uuid}' attempted to access task '{task_id}' owned by user '{task.get('user_uuid')}'.")
        return jsonify({"error": "Access denied to this task."}), 403
    # --- MODIFICATION END ---

    # Exclude user_uuid from the response payload if desired
    # response_task = task.copy()
    # response_task.pop("user_uuid", None)
    # return jsonify(response_task)
    return jsonify(task)


@rest_api_bp.route("/v1/tasks/<task_id>/cancel", methods=["POST"])
async def cancel_task(task_id: str):
    """Cancels an active background task initiated via the REST API *by the requesting user*."""
    # --- MODIFICATION START: Get User UUID and check task ownership ---
    user_uuid = _get_user_uuid_from_request()
    task_status_dict = APP_STATE["background_tasks"].get(task_id)

    if not task_status_dict:
        app_logger.warning(f"REST API: Cancel failed. Task '{task_id}' not found for user '{user_uuid}'.")
        return jsonify({"error": f"Task '{task_id}' not found."}), 404

    if task_status_dict.get("user_uuid") != user_uuid:
        app_logger.error(f"REST API: User '{user_uuid}' attempted to cancel task '{task_id}' owned by user '{task_status_dict.get('user_uuid')}'. Denying.")
        return jsonify({"error": "Access denied: You cannot cancel a task you did not start."}), 403
    # --- MODIFICATION END ---

    active_tasks = APP_STATE.get("active_tasks", {})
    task_object = active_tasks.get(task_id) # Get the asyncio.Task object

    if task_object and not task_object.done():
        app_logger.info(f"Received REST request from user {user_uuid} to cancel task {task_id}.")
        task_object.cancel()
        # Remove immediately from active tasks dict
        if task_id in active_tasks:
             del active_tasks[task_id]
        # Update the status in the background_tasks dict as well
        task_status_dict["status"] = "cancelling" # Or "cancelled" immediately
        task_status_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

        return jsonify({"status": "success", "message": "Cancellation request sent."}), 200
    elif task_object and task_object.done():
        app_logger.info(f"REST cancellation request for task {task_id} (user {user_uuid}) ignored: task already completed.")
        if task_id in active_tasks:
             del active_tasks[task_id]
        # Ensure final status reflects completion if missed
        if task_status_dict.get("status") not in ["complete", "error", "cancelled"]:
             task_status_dict["status"] = "complete" # Or infer from result if possible
        return jsonify({"status": "success", "message": "Task already completed."}), 200
    else:
        # Task might exist in background_tasks but not in active_tasks if already finished/cancelled
        current_status = task_status_dict.get("status", "unknown")
        if current_status in ["complete", "error", "cancelled"]:
             app_logger.info(f"REST cancellation request for task {task_id} (user {user_uuid}) ignored: task already finished with status '{current_status}'.")
             return jsonify({"status": "success", "message": f"Task already finished ({current_status})."}), 200
        else:
            app_logger.warning(f"REST cancellation request for task {task_id} (user {user_uuid}) failed: No active asyncio task found, status is '{current_status}'.")
            return jsonify({"status": "error", "message": "No active running task found for this task ID."}), 404


# --- RAG Collection Management Endpoints ---

@rest_api_bp.route("/v1/rag/collections", methods=["GET"])
async def get_rag_collections():
    """Get all RAG collections with their active status and document counts."""
    try:
        collections = APP_STATE.get("rag_collections", [])
        retriever = APP_STATE.get("rag_retriever_instance")
        
        # Add 'is_active' field and 'count' to indicate if collection is actually loaded and how many docs it has
        enhanced_collections = []
        for coll in collections:
            coll_copy = coll.copy()
            # A collection is active if it's loaded in the retriever's collections dict
            is_active = retriever and coll["id"] in retriever.collections if retriever else False
            coll_copy["is_active"] = is_active
            
            # Get document count if collection is active
            if is_active and retriever:
                try:
                    chromadb_collection = retriever.collections.get(coll["id"])
                    if chromadb_collection:
                        coll_copy["count"] = chromadb_collection.count()
                    else:
                        coll_copy["count"] = 0
                except Exception as count_err:
                    app_logger.warning(f"Failed to get count for collection {coll['id']}: {count_err}")
                    coll_copy["count"] = 0
            else:
                coll_copy["count"] = 0
            
            enhanced_collections.append(coll_copy)
        
        return jsonify({"status": "success", "collections": enhanced_collections}), 200
    except Exception as e:
        app_logger.error(f"Error getting RAG collections: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/collections", methods=["POST"])
async def create_rag_collection():
    """Create a new RAG collection."""
    try:
        data = await request.get_json()
        
        # Validate required fields
        if not data.get("name"):
            return jsonify({"status": "error", "message": "Collection name is required"}), 400
        
        # ENFORCEMENT: mcp_server_id is now required for all new collections
        if not data.get("mcp_server_id"):
            return jsonify({"status": "error", "message": "mcp_server_id is required. Collections must be associated with an MCP server."}), 400
        
        name = data["name"]
        mcp_server_id = data["mcp_server_id"]
        description = data.get("description", "")
        
        # Add collection via RAG retriever
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"status": "error", "message": "RAG retriever not initialized"}), 500
        
        collection_id = retriever.add_collection(name, description, mcp_server_id)
        
        if collection_id is not None:
            app_logger.info(f"Created RAG collection with ID: {collection_id}, MCP server: {mcp_server_id}")
            return jsonify({
                "status": "success", 
                "message": "Collection created successfully", 
                "collection_id": collection_id,
                "mcp_server_id": mcp_server_id
            }), 201
        else:
            return jsonify({"status": "error", "message": "Failed to create collection"}), 500
            
    except Exception as e:
        app_logger.error(f"Error creating RAG collection: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/collections/<int:collection_id>", methods=["PUT"])
async def update_rag_collection(collection_id: int):
    """Update a RAG collection's metadata (name, MCP server, description)."""
    try:
        from trusted_data_agent.core.config_manager import get_config_manager
        
        data = await request.get_json()
        
        # Find the collection in APP_STATE
        # Note: We allow updating metadata even if RAG retriever is not initialized
        # This enables users to assign MCP servers before full configuration
        collections_list = APP_STATE.get("rag_collections", [])
        coll_meta = next((c for c in collections_list if c["id"] == collection_id), None)
        
        if not coll_meta:
            return jsonify({"status": "error", "message": f"Collection with ID {collection_id} not found"}), 404
        
        # ENFORCEMENT: Prevent removing mcp_server_id from ANY collection
        if "mcp_server_id" in data:
            new_mcp_server_id = data["mcp_server_id"]
            if not new_mcp_server_id:
                return jsonify({
                    "status": "error", 
                    "message": "Cannot remove mcp_server_id. All collections must be associated with an MCP server."
                }), 400
            coll_meta["mcp_server_id"] = new_mcp_server_id
        
        # Update other fields
        if "name" in data:
            coll_meta["name"] = data["name"]
        if "description" in data:
            coll_meta["description"] = data["description"]
        
        # Save the updated collections list to APP_STATE
        APP_STATE["rag_collections"] = collections_list
        
        # Persist to config file
        config_manager = get_config_manager()
        config_manager.save_rag_collections(collections_list)
        
        app_logger.info(f"Updated RAG collection {collection_id}: {coll_meta['name']} (MCP: {coll_meta.get('mcp_server_id')})")
        return jsonify({
            "status": "success", 
            "message": "Collection updated successfully",
            "collection": coll_meta
        }), 200
            
    except Exception as e:
        app_logger.error(f"Error updating RAG collection: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/collections/<int:collection_id>", methods=["DELETE"])
async def delete_rag_collection(collection_id: int):
    """Delete a RAG collection."""
    try:
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"status": "error", "message": "RAG retriever not initialized"}), 500
        
        success = retriever.remove_collection(collection_id)
        
        if success:
            app_logger.info(f"Deleted RAG collection: {collection_id}")
            return jsonify({"status": "success", "message": "Collection deleted successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to delete collection or collection not found"}), 404
            
    except Exception as e:
        app_logger.error(f"Error deleting RAG collection: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/collections/<int:collection_id>/toggle", methods=["POST"])
async def toggle_rag_collection(collection_id: int):
    """Enable or disable a RAG collection."""
    try:
        data = await request.get_json()
        enabled = data.get("enabled")
        
        if enabled is None:
            return jsonify({"status": "error", "message": "Field 'enabled' is required"}), 400
        
        # Check if attempting to enable a collection without MCP server assignment FIRST
        # This validation should happen even if RAG retriever is not initialized
        if enabled:
            collections_list = APP_STATE.get("rag_collections", [])
            coll_meta = next((c for c in collections_list if c["id"] == collection_id), None)
            if coll_meta and not coll_meta.get("mcp_server_id"):
                return jsonify({
                    "status": "error", 
                    "message": "Cannot enable collection: MCP server must be assigned first"
                }), 400
        
        # Now check if RAG retriever is initialized
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"status": "error", "message": "RAG retriever not initialized. Please configure and connect the application first."}), 500
        
        success = retriever.toggle_collection(collection_id, enabled)
        
        if success:
            action = "enabled" if enabled else "disabled"
            app_logger.info(f"{action.capitalize()} RAG collection: {collection_id}")
            return jsonify({
                "status": "success", 
                "message": f"Collection {action} successfully",
                "enabled": enabled
            }), 200
        else:
            return jsonify({"status": "error", "message": "Failed to toggle collection or collection not found"}), 404
            
    except Exception as e:
        app_logger.error(f"Error toggling RAG collection: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/collections/<int:collection_id>/refresh", methods=["POST"])
async def refresh_rag_collection(collection_id: int):
    """Refresh the vector store for a specific RAG collection."""
    try:
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"status": "error", "message": "RAG retriever not initialized"}), 500
        
        # Check if the collection is actually loaded
        if collection_id not in retriever.collections:
            # Get collection info for better error message
            collections_list = APP_STATE.get("rag_collections", [])
            coll_meta = next((c for c in collections_list if c["id"] == collection_id), None)
            
            if not coll_meta:
                return jsonify({"status": "error", "message": f"Collection {collection_id} not found in configuration"}), 404
            
            # Collection exists but isn't loaded - explain why
            current_mcp = APP_CONFIG.CURRENT_MCP_SERVER_ID
            coll_mcp = coll_meta.get("mcp_server_id")
            error_msg = f"Collection '{coll_meta['name']}' (ID: {collection_id}) is not loaded. "
            
            if coll_mcp != current_mcp:
                error_msg += f"It's associated with MCP server '{coll_mcp}' but current server is '{current_mcp}'. "
            elif not coll_meta.get("enabled", False):
                error_msg += "It's disabled. Please enable it first."
            else:
                error_msg += "Reason unknown. Check server logs."
            
            app_logger.warning(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 400
        
        # Run refresh in background to avoid timeout
        asyncio.create_task(asyncio.to_thread(retriever.refresh_vector_store, collection_id))
        
        app_logger.info(f"Started refresh for RAG collection: {collection_id}")
        return jsonify({"status": "success", "message": "Collection refresh started"}), 202
            
    except Exception as e:
        app_logger.error(f"Error refreshing RAG collection: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/collections/<int:collection_id>/rows", methods=["GET"])
async def get_rag_collection_rows(collection_id: int):
    """Get rows (cases) from a specific RAG collection.
    
    Query Parameters:
      limit (int): number of rows to return (default 25, max 10000)
      q (str): optional search query; if provided runs a similarity query
      light (bool): if true, omits full_case_data from response for lighter payload
    """
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 25))
        limit = min(limit, 10000)  # Cap at 10000 for performance
        query_text = request.args.get('q', '').strip()
        light = request.args.get('light', 'false').lower() == 'true'
        
        # Get retriever
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"error": "RAG retriever not initialized"}), 500
        
        # Check if collection is loaded
        if collection_id not in retriever.collections:
            return jsonify({"error": f"Collection {collection_id} is not loaded"}), 404
        
        # Get the ChromaDB collection
        collection = retriever.collections[collection_id]
        
        # Get collection metadata
        collections_list = APP_STATE.get("rag_collections", [])
        collection_meta = next((c for c in collections_list if c["id"] == collection_id), None)
        
        if not collection_meta:
            return jsonify({"error": f"Collection {collection_id} metadata not found"}), 404
        
        rows = []
        total = 0
        
        if query_text and len(query_text) >= 3:
            # Similarity search
            try:
                query_results = collection.query(
                    query_texts=[query_text], n_results=limit, include=["metadatas", "distances"]
                )
                if query_results and query_results.get("ids"):
                    total = len(query_results["ids"][0])
                    for i in range(total):
                        row_id = query_results["ids"][0][i]
                        meta = query_results["metadatas"][0][i]
                        distance = query_results["distances"][0][i]
                        similarity = 1 - distance
                        full_case_data = None
                        if not light:
                            try:
                                full_case_data = json.loads(meta.get("full_case_data", "{}"))
                            except json.JSONDecodeError:
                                full_case_data = None
                        rows.append({
                            "id": row_id,
                            "user_query": meta.get("user_query"),
                            "strategy_type": meta.get("strategy_type"),
                            "is_most_efficient": meta.get("is_most_efficient"),
                            "user_feedback_score": meta.get("user_feedback_score", 0),
                            "output_tokens": meta.get("output_tokens"),
                            "timestamp": meta.get("timestamp"),
                            "similarity_score": similarity,
                            "full_case_data": full_case_data,
                        })
            except Exception as qe:
                app_logger.warning(f"Query failed for collection {collection_id}: {qe}")
        else:
            # Get all or sample
            try:
                all_results = collection.get(include=["metadatas"])
                ids = all_results.get("ids", [])
                metas = all_results.get("metadatas", [])
                total = len(ids)
                sample_count = min(limit, total)
                for i in range(sample_count):
                    meta = metas[i]
                    full_case_data = None
                    if not light:
                        try:
                            full_case_data = json.loads(meta.get("full_case_data", "{}"))
                        except json.JSONDecodeError:
                            full_case_data = None
                    rows.append({
                        "id": ids[i],
                        "user_query": meta.get("user_query"),
                        "strategy_type": meta.get("strategy_type"),
                        "is_most_efficient": meta.get("is_most_efficient"),
                        "user_feedback_score": meta.get("user_feedback_score", 0),
                        "output_tokens": meta.get("output_tokens"),
                        "timestamp": meta.get("timestamp"),
                        "full_case_data": full_case_data,
                    })
            except Exception as ge:
                app_logger.error(f"Failed to get rows for collection {collection_id}: {ge}", exc_info=True)
        
        return jsonify({
            "rows": rows,
            "total": total,
            "query": query_text,
            "collection_id": collection_id,
            "collection_name": collection_meta["name"]
        }), 200
            
    except Exception as e:
        app_logger.error(f"Error getting collection rows: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@rest_api_bp.route("/v1/rag/cases/<case_id>/feedback", methods=["POST"])
async def submit_rag_case_feedback(case_id: str):
    """Submit user feedback (upvote/downvote) for a RAG case."""
    try:
        data = await request.get_json()
        feedback_score = data.get("feedback_score")
        
        # Validate feedback_score
        if feedback_score not in [-1, 0, 1]:
            return jsonify({
                "status": "error", 
                "message": "Invalid feedback_score. Must be -1 (downvote), 0 (neutral), or 1 (upvote)"
            }), 400
        
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"status": "error", "message": "RAG retriever not initialized"}), 500
        
        # Update the case feedback
        success = await retriever.update_case_feedback(case_id, feedback_score)
        
        if success:
            action = "upvoted" if feedback_score == 1 else "downvoted" if feedback_score == -1 else "reset"
            app_logger.info(f"Case {case_id} {action} by user")
            return jsonify({
                "status": "success", 
                "message": f"Feedback submitted successfully",
                "case_id": case_id,
                "feedback_score": feedback_score
            }), 200
        else:
            return jsonify({"status": "error", "message": "Failed to update feedback. Case not found."}), 404
            
    except Exception as e:
        app_logger.error(f"Error submitting RAG case feedback: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/collections/<int:collection_id>/populate", methods=["POST"])
async def populate_collection_from_template(collection_id: int):
    """
    Populate a RAG collection using a template and user-provided examples.
    
    Request body:
    {
        "template_type": "sql_query",
        "examples": [
            {
                "user_query": "Show me all users older than 25",
                "sql_statement": "SELECT * FROM users WHERE age > 25"
            },
            {
                "user_query": "Count completed orders",
                "sql_statement": "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
            }
        ],
        "database_name": "mydb",  // optional
        "mcp_tool_name": "base_executeRawSQLStatement"  // optional
    }
    """
    try:
        data = await request.get_json()
        app_logger.info(f"Populate collection {collection_id} - Received request with data keys: {list(data.keys())}")
        
        # Validate required fields
        template_type = data.get("template_type")
        examples_data = data.get("examples", [])
        app_logger.info(f"Template type: {template_type}, Examples count: {len(examples_data)}")
        
        if not template_type:
            return jsonify({"status": "error", "message": "template_type is required"}), 400
        
        if not examples_data or not isinstance(examples_data, list):
            return jsonify({"status": "error", "message": "examples must be a non-empty list"}), 400
        
        # Currently only SQL template is supported
        if template_type != "sql_query":
            return jsonify({"status": "error", "message": f"Unsupported template_type: {template_type}. Only 'sql_query' is supported."}), 400
        
        # Parse examples based on template type
        if template_type == "sql_query":
            examples = []
            for idx, ex in enumerate(examples_data):
                user_query = ex.get("user_query")
                sql_statement = ex.get("sql_statement")
                
                if not user_query or not sql_statement:
                    return jsonify({
                        "status": "error", 
                        "message": f"Example {idx+1} missing required fields (user_query, sql_statement)"
                    }), 400
                
                examples.append((user_query, sql_statement))
        
        # Get RAG retriever
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"status": "error", "message": "RAG retriever not initialized"}), 500
        
        # Import and create template generator
        from trusted_data_agent.agent.rag_template_generator import RAGTemplateGenerator
        generator = RAGTemplateGenerator(retriever)
        
        # Validate examples first
        validation_issues = generator.validate_sql_examples(examples)
        if validation_issues:
            return jsonify({
                "status": "error", 
                "message": "Validation failed for some examples",
                "validation_issues": validation_issues
            }), 400
        
        # Populate collection
        database_name = data.get("database_name")
        mcp_tool_name = data.get("mcp_tool_name", "base_executeRawSQLStatement")
        
        app_logger.info(f"Populating collection {collection_id} with {len(examples)} SQL template examples")
        app_logger.info(f"Database name: {database_name}, MCP tool: {mcp_tool_name}")
        app_logger.info(f"Examples preview: {examples[:2] if len(examples) >= 2 else examples}")
        
        results = generator.populate_collection_from_sql_examples(
            collection_id=collection_id,
            examples=examples,
            database_name=database_name,
            mcp_tool_name=mcp_tool_name
        )
        
        app_logger.info(f"Population complete - Successful: {results['successful']}, Failed: {results['failed']}")
        if results['errors']:
            app_logger.error(f"Population errors: {results['errors']}")
        
        return jsonify({
            "status": "success",
            "message": f"Successfully populated {results['successful']} cases",
            "results": results
        }), 200
        
    except ValueError as ve:
        # Collection validation error
        app_logger.error(f"Validation error: {ve}")
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        app_logger.error(f"Error populating collection from template: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/templates", methods=["GET"])
async def get_rag_templates():
    """Get information about available RAG templates."""
    try:
        retriever = APP_STATE.get("rag_retriever_instance")
        if not retriever:
            return jsonify({"status": "error", "message": "RAG retriever not initialized"}), 500
        
        from trusted_data_agent.agent.rag_template_generator import RAGTemplateGenerator
        generator = RAGTemplateGenerator(retriever)
        
        # Get info for all supported templates
        sql_template = generator.get_template_info("sql_query")
        
        return jsonify({
            "status": "success",
            "templates": {
                "sql_query": sql_template
            }
        }), 200
        
    except Exception as e:
        app_logger.error(f"Error getting RAG templates: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/templates/<template_id>/config", methods=["GET"])
async def get_rag_template_config(template_id: str):
    """
    Get the editable configuration for a specific template.
    
    Returns the current configuration values that can be customized.
    """
    try:
        from trusted_data_agent.agent.rag_template_manager import get_template_manager
        
        template_manager = get_template_manager()
        
        # Get template
        template = template_manager.get_template(template_id)
        if not template:
            return jsonify({
                "status": "error",
                "message": f"Template {template_id} not found"
            }), 404
        
        # Get editable configuration
        config = template_manager.get_template_config(template_id)
        
        # Get template metadata
        metadata = {
            "template_id": template.get("template_id"),
            "template_name": template.get("template_name"),
            "template_type": template.get("template_type"),
            "description": template.get("description"),
            "version": template.get("template_version")
        }
        
        return jsonify({
            "status": "success",
            "template": metadata,
            "config": config
        }), 200
        
    except Exception as e:
        app_logger.error(f"Error getting template config: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/templates/<template_id>/config", methods=["PUT"])
async def update_rag_template_config(template_id: str):
    """
    Update the editable configuration for a specific template.
    
    Body:
    {
        "default_mcp_tool": "base_executeRawSQLStatement",
        "estimated_input_tokens": 150,
        "estimated_output_tokens": 180
    }
    """
    try:
        from trusted_data_agent.agent.rag_template_manager import get_template_manager
        
        data = await request.get_json()
        
        template_manager = get_template_manager()
        
        # Verify template exists
        template = template_manager.get_template(template_id)
        if not template:
            return jsonify({
                "status": "error",
                "message": f"Template {template_id} not found"
            }), 404
        
        # Update configuration
        template_manager.update_template_config(template_id, data)
        
        # Get updated config
        updated_config = template_manager.get_template_config(template_id)
        
        return jsonify({
            "status": "success",
            "message": f"Template {template_id} configuration updated",
            "config": updated_config
        }), 200
        
    except Exception as e:
        app_logger.error(f"Error updating template config: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/rag/templates/list", methods=["GET"])
async def list_rag_templates():
    """
    List all available templates with their metadata.
    """
    try:
        from trusted_data_agent.agent.rag_template_manager import get_template_manager
        
        template_manager = get_template_manager()
        templates = template_manager.list_templates()
        
        return jsonify({
            "status": "success",
            "templates": templates
        }), 200
        
    except Exception as e:
        app_logger.error(f"Error listing templates: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================
# MCP SERVER CONFIGURATION ENDPOINTS
# ============================================================================

@rest_api_bp.route("/v1/mcp/servers", methods=["GET"])
async def get_mcp_servers():
    """Get all MCP server configurations."""
    try:
        from trusted_data_agent.core.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        servers = config_manager.get_mcp_servers()
        active_server_id = config_manager.get_active_mcp_server_id()
        
        return jsonify({
            "status": "success",
            "servers": servers,
            "active_server_id": active_server_id
        }), 200
    except Exception as e:
        app_logger.error(f"Error getting MCP servers: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/mcp/servers", methods=["POST"])
async def create_mcp_server():
    """Create a new MCP server configuration."""
    try:
        from trusted_data_agent.core.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        data = await request.get_json()
        
        # Validate required fields
        required_fields = ["id", "name", "host", "port"]
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"Field '{field}' is required"}), 400
        
        # Add server
        success = config_manager.add_mcp_server(data)
        
        if success:
            app_logger.info(f"Created MCP server: {data.get('name')} (ID: {data.get('id')})")
            return jsonify({
                "status": "success",
                "message": "MCP server created successfully",
                "server_id": data.get("id")
            }), 201
        else:
            return jsonify({"status": "error", "message": "Failed to create MCP server"}), 500
            
    except Exception as e:
        app_logger.error(f"Error creating MCP server: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/mcp/servers/<server_id>", methods=["PUT"])
async def update_mcp_server(server_id: str):
    """Update an existing MCP server configuration."""
    try:
        from trusted_data_agent.core.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        data = await request.get_json()
        
        # Don't allow changing the ID
        if "id" in data and data["id"] != server_id:
            return jsonify({"status": "error", "message": "Cannot change server ID"}), 400
        
        success = config_manager.update_mcp_server(server_id, data)
        
        if success:
            app_logger.info(f"Updated MCP server: {server_id}")
            return jsonify({
                "status": "success",
                "message": "MCP server updated successfully"
            }), 200
        else:
            return jsonify({"status": "error", "message": "MCP server not found"}), 404
            
    except Exception as e:
        app_logger.error(f"Error updating MCP server: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/mcp/servers/<server_id>", methods=["DELETE"])
async def delete_mcp_server(server_id: str):
    """Delete an MCP server configuration."""
    try:
        from trusted_data_agent.core.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # Try to remove the server (will fail if collections are assigned)
        success, error_message = config_manager.remove_mcp_server(server_id)
        
        if not success:
            return jsonify({
                "status": "error", 
                "message": error_message or "Failed to delete MCP server"
            }), 400
        
        # Check if this was the active server and clear it
        active_server_id = config_manager.get_active_mcp_server_id()
        if active_server_id == server_id:
            config_manager.set_active_mcp_server_id(None)
        
        app_logger.info(f"Deleted MCP server: {server_id}")
        return jsonify({
            "status": "success",
            "message": "MCP server deleted successfully"
        }), 200
            
    except Exception as e:
        app_logger.error(f"Error deleting MCP server: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@rest_api_bp.route("/v1/mcp/servers/<server_id>/activate", methods=["POST"])
async def activate_mcp_server(server_id: str):
    """Set an MCP server as the active server."""
    try:
        from trusted_data_agent.core.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # Verify server exists
        servers = config_manager.get_mcp_servers()
        server = next((s for s in servers if s.get("id") == server_id), None)
        
        if not server:
            return jsonify({"status": "error", "message": "MCP server not found"}), 404
        
        success = config_manager.set_active_mcp_server_id(server_id)
        
        if success:
            app_logger.info(f"Activated MCP server: {server_id}")
            return jsonify({
                "status": "success",
                "message": "MCP server activated successfully"
            }), 200
        else:
            return jsonify({"status": "error", "message": "Failed to activate MCP server"}), 500
            
    except Exception as e:
        app_logger.error(f"Error activating MCP server: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================
# EXECUTION DASHBOARD API ENDPOINTS
# ============================================================================

@rest_api_bp.route('/v1/sessions/analytics', methods=['GET'])
async def get_sessions_analytics():
    """
    Get comprehensive analytics across all sessions for the execution dashboard.
    Returns: total sessions, tokens, success rate, cost, velocity, model distribution, top champions
    """
    try:
        user_uuid = _get_user_uuid_from_request()
        from pathlib import Path
        
        project_root = Path(__file__).resolve().parents[3]
        sessions_root = project_root / 'tda_sessions' / user_uuid
        rag_cases_dir = project_root / 'rag' / 'tda_rag_cases'
        
        if not sessions_root.exists():
            return jsonify({
                "total_sessions": 0,
                "total_tokens": {"input": 0, "output": 0, "total": 0},
                "success_rate": 0,
                "estimated_cost": 0,
                "model_distribution": {},
                "top_expensive_queries": [],
                "top_expensive_questions": [],
                "velocity_data": []
            }), 200
        
        # Initialize analytics
        total_sessions = 0
        total_input_tokens = 0
        total_output_tokens = 0
        successful_turns = 0
        total_turns = 0
        model_usage = {}
        sessions_by_hour = {}
        expensive_queries = []
        expensive_questions = []
        
        # Scan all session files
        for session_file in sessions_root.glob('*.json'):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                total_sessions += 1
                total_input_tokens += session_data.get('input_tokens', 0)
                total_output_tokens += session_data.get('output_tokens', 0)
                
                # Track model usage
                models_used = session_data.get('models_used', [])
                for model in models_used:
                    model_usage[model] = model_usage.get(model, 0) + 1
                
                # Analyze workflow history
                workflow_history = session_data.get('last_turn_data', {}).get('workflow_history', [])
                for turn in workflow_history:
                    if turn.get('isValid', True):
                        total_turns += 1
                        # Simple success heuristic: has final_summary and no critical errors
                        if turn.get('final_summary'):
                            successful_turns += 1
                        
                        # Track expensive individual questions
                        user_query = turn.get('user_query', '')
                        turn_tokens = (turn.get('turn_input_tokens', 0) + 
                                     turn.get('turn_output_tokens', 0))
                        
                        if turn_tokens > 0 and user_query:
                            expensive_questions.append({
                                "query": user_query[:60] + "..." if len(user_query) > 60 else user_query,
                                "tokens": turn_tokens,
                                "session_id": session_data.get('id', 'unknown')[:8]
                            })
                
                # Track expensive sessions (tokens are at session level, not turn level)
                session_tokens = session_data.get('input_tokens', 0) + session_data.get('output_tokens', 0)
                session_name = session_data.get('name', 'Unnamed Session')
                
                if session_tokens > 0:
                    expensive_queries.append({
                        "query": session_name[:60] + "..." if len(session_name) > 60 else session_name,
                        "tokens": session_tokens,
                        "session_id": session_data.get('id', 'unknown')[:8]
                    })
                
                # Track velocity (sessions per hour)
                created_at = session_data.get('created_at')
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        hour_key = dt.strftime('%Y-%m-%d %H:00')
                        sessions_by_hour[hour_key] = sessions_by_hour.get(hour_key, 0) + 1
                    except:
                        pass
                        
            except Exception as e:
                app_logger.warning(f"Error processing session file {session_file.name}: {e}")
                continue
        
        # Calculate metrics
        total_tokens_val = total_input_tokens + total_output_tokens
        success_rate = (successful_turns / total_turns * 100) if total_turns > 0 else 0
        
        # Rough cost estimate ($0.01 per 1K tokens as average)
        estimated_cost = total_tokens_val / 1000 * 0.01
        
        # Model distribution percentages
        total_model_count = sum(model_usage.values())
        model_distribution = {
            model: round(count / total_model_count * 100, 1)
            for model, count in model_usage.items()
        } if total_model_count > 0 else {}
        
        # Sort by token count (descending) and take top 5 most expensive sessions and questions
        expensive_queries.sort(key=lambda x: x['tokens'], reverse=True)
        top_expensive_queries = expensive_queries[:5]
        
        expensive_questions.sort(key=lambda x: x['tokens'], reverse=True)
        top_expensive_questions = expensive_questions[:5]
        
        # Velocity data (last 24 hours)
        velocity_data = []
        if sessions_by_hour:
            sorted_hours = sorted(sessions_by_hour.items())[-24:]  # Last 24 hours
            velocity_data = [{"hour": hour, "count": count} for hour, count in sorted_hours]
        
        return jsonify({
            "total_sessions": total_sessions,
            "total_tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_tokens_val
            },
            "success_rate": round(success_rate, 1),
            "estimated_cost": round(estimated_cost, 2),
            "model_distribution": model_distribution,
            "top_expensive_queries": top_expensive_queries,
            "top_expensive_questions": top_expensive_questions,
            "velocity_data": velocity_data
        }), 200
        
    except Exception as e:
        app_logger.error(f"Error getting session analytics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@rest_api_bp.route('/v1/sessions', methods=['GET'])
async def get_sessions_list():
    """
    Get list of all sessions with metadata for the execution dashboard.
    Query params: search, sort, filter_status, filter_model, limit, offset
    """
    try:
        user_uuid = _get_user_uuid_from_request()
        from pathlib import Path
        
        # Get query parameters
        search_query = request.args.get('search', '').lower()
        sort_by = request.args.get('sort', 'recent')  # recent, oldest, tokens, turns
        filter_status = request.args.get('filter_status', 'all')  # all, success, partial, failed
        filter_model = request.args.get('filter_model', 'all')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        project_root = Path(__file__).resolve().parents[3]
        sessions_root = project_root / 'tda_sessions' / user_uuid
        rag_cases_dir = project_root / 'rag' / 'tda_rag_cases'
        
        if not sessions_root.exists():
            return jsonify({"sessions": [], "total": 0}), 200
        
        sessions = []
        
        # Load all sessions
        for session_file in sessions_root.glob('*.json'):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                session_id = session_data.get('id')
                name = session_data.get('name', 'Unnamed Session')
                created_at = session_data.get('created_at', '')
                last_updated = session_data.get('last_updated', '')
                provider = session_data.get('provider', 'Unknown')
                model = session_data.get('model', 'Unknown')
                input_tokens = session_data.get('input_tokens', 0)
                output_tokens = session_data.get('output_tokens', 0)
                
                # Analyze workflow
                workflow_history = session_data.get('last_turn_data', {}).get('workflow_history', [])
                turn_count = len([t for t in workflow_history if t.get('isValid', True)])
                
                # Determine status
                has_errors = False
                all_successful = True
                for turn in workflow_history:
                    if not turn.get('isValid', True):
                        continue
                    if not turn.get('final_summary'):
                        all_successful = False
                    # Check for errors in execution trace
                    exec_trace = turn.get('execution_trace', [])
                    for entry in exec_trace:
                        if isinstance(entry, dict):
                            result = entry.get('result', {})
                            if isinstance(result, dict) and result.get('status') == 'error':
                                has_errors = True
                
                if all_successful and not has_errors and turn_count > 0:
                    status = 'success'
                elif turn_count > 0:
                    status = 'partial' if all_successful else 'failed'
                else:
                    status = 'empty'
                
                # Check for RAG enhancement
                has_rag = False
                if rag_cases_dir.exists():
                    for case_file in rag_cases_dir.glob(f'case_*-{session_id[:8]}*.json'):
                        has_rag = True
                        break
                
                # Apply filters (but not search - let client handle that for flexibility)
                if filter_status != 'all' and status != filter_status:
                    continue
                if filter_model != 'all' and filter_model not in f"{provider}/{model}":
                    continue
                
                sessions.append({
                    "id": session_id,
                    "name": name,
                    "created_at": created_at,
                    "last_updated": last_updated,
                    "provider": provider,
                    "model": model,
                    "turn_count": turn_count,
                    "total_tokens": input_tokens + output_tokens,
                    "status": status,
                    "has_rag": has_rag,
                    "has_errors": has_errors,
                    "last_turn_data": {
                        "workflow_history": workflow_history
                    }
                })
                
            except Exception as e:
                app_logger.warning(f"Error processing session {session_file.name}: {e}")
                continue
        
        # Sort sessions
        if sort_by == 'recent':
            sessions.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
        elif sort_by == 'oldest':
            sessions.sort(key=lambda x: x.get('created_at', ''))
        elif sort_by == 'tokens':
            sessions.sort(key=lambda x: x.get('total_tokens', 0), reverse=True)
        elif sort_by == 'turns':
            sessions.sort(key=lambda x: x.get('turn_count', 0), reverse=True)
        
        # Paginate
        total = len(sessions)
        sessions_page = sessions[offset:offset + limit]
        
        return jsonify({
            "sessions": sessions_page,
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        app_logger.error(f"Error getting sessions list: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@rest_api_bp.route('/v1/sessions/<session_id>/details', methods=['GET'])
async def get_session_details(session_id: str):
    """
    Get full session details for deep dive inspector.
    Returns: complete session data with timeline, execution traces, RAG associations
    """
    try:
        user_uuid = _get_user_uuid_from_request()
        from pathlib import Path
        
        project_root = Path(__file__).resolve().parents[3]
        sessions_root = project_root / 'tda_sessions' / user_uuid
        rag_cases_dir = project_root / 'rag' / 'tda_rag_cases'
        
        session_file = sessions_root / f"{session_id}.json"
        
        if not session_file.exists():
            return jsonify({"error": "Session not found"}), 404
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Find associated RAG cases
        rag_cases = []
        if rag_cases_dir.exists():
            for case_file in rag_cases_dir.glob('case_*.json'):
                try:
                    with open(case_file, 'r', encoding='utf-8') as cf:
                        case_data = json.load(cf)
                    
                    if case_data.get('metadata', {}).get('session_id') == session_id:
                        rag_cases.append({
                            "case_id": case_data.get('case_id'),
                            "turn_id": case_data.get('metadata', {}).get('turn_id'),
                            "is_most_efficient": case_data.get('metadata', {}).get('is_most_efficient', False),
                            "output_tokens": case_data.get('metadata', {}).get('llm_config', {}).get('output_tokens', 0),
                            "strategy_metrics": case_data.get('metadata', {}).get('strategy_metrics', {}),
                            "collection_id": case_data.get('metadata', {}).get('collection_id', 0)
                        })
                except:
                    continue
        
        session_data['rag_cases'] = rag_cases
        
        return jsonify(session_data), 200
        
    except Exception as e:
        app_logger.error(f"Error getting session details: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
