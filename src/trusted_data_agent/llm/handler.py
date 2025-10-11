# src/trusted_data_agent/llm/handler.py
import asyncio
import json
import logging
import httpx
import re
import random
import time
import copy
from typing import Tuple, List

import google.generativeai as genai
from anthropic import APIError, AsyncAnthropic, InternalServerError, RateLimitError
from openai import AsyncOpenAI, APIError as OpenAI_APIError, AsyncAzureOpenAI
from pydantic import ValidationError, BaseModel
import boto3

from trusted_data_agent.core.config import APP_CONFIG
from trusted_data_agent.core.session_manager import get_session, update_token_count
from trusted_data_agent.agent.prompts import CHARTING_INSTRUCTIONS, PROVIDER_SYSTEM_PROMPTS
from trusted_data_agent.core.config import (
    CERTIFIED_GOOGLE_MODELS, CERTIFIED_ANTHROPIC_MODELS,
    CERTIFIED_AMAZON_MODELS, CERTIFIED_AMAZON_PROFILES,
    CERTIFIED_OLLAMA_MODELS, CERTIFIED_OPENAI_MODELS,
    CERTIFIED_AZURE_MODELS, CERTIFIED_FRIENDLI_MODELS
)

llm_logger = logging.getLogger("llm_conversation")
llm_history_logger = logging.getLogger("llm_conversation_history")
app_logger = logging.getLogger("quart.app")

class OllamaClient:
    """A simple async client for interacting with the Ollama API."""
    def __init__(self, host: str):
        if not host.startswith("http://") and not host.startswith("https://"):
            self.host = f"http://{host}"
            app_logger.info(f"Ollama host missing protocol. Automatically prepending 'http://'. New host: {self.host}")
        else:
            self.host = host
        self.client = httpx.AsyncClient(base_url=self.host, timeout=120.0)

    async def list_models(self):
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except httpx.RequestError as e:
            app_logger.error(f"Ollama API request error: {e}")
            raise RuntimeError("Could not connect to Ollama server.") from e

    async def chat(self, model: str, messages: list, system_prompt: str):
        try:
            payload = {
                "model": model,
                "messages": messages,
                "system": system_prompt,
                "stream": False
            }
            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            app_logger.error(f"Ollama API request error: {e}")
            raise RuntimeError("Error during chat completion with Ollama.") from e

def parse_and_coerce_llm_response(response_text: str, target_model: BaseModel) -> Tuple[BaseModel, List[str]]:
    """
    A resilient parser for LLM responses that attempts to correct common
    schema deviations and reports on the corrections made.

    Args:
        response_text: The raw string output from the LLM.
        target_model: The Pydantic model class to validate against.

    Returns:
        A tuple containing the validated model instance and a list of
        strings describing any corrections that were applied.

    Raises:
        json.JSONDecodeError: If no valid JSON can be extracted.
        ValidationError: If the JSON is valid but cannot be coerced into the target model.
    """
    app_logger.debug(f"Attempting to parse and coerce response into {target_model.__name__}.")
    correction_descriptions = []

    # 1. Robustly extract JSON from the raw text
    json_match = re.search(r'```json\s*\n(.*?)\n\s*```|(\{.*\}|\[.*\])', response_text, re.DOTALL)
    if not json_match:
        raise json.JSONDecodeError("No valid JSON object or list found in the LLM response.", response_text, 0)
    
    json_str = next(g for g in json_match.groups() if g is not None)
    if not json_str:
        raise json.JSONDecodeError("Extracted JSON string is empty.", response_text, 0)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        app_logger.error(f"Initial JSON parsing failed even after extraction. Error: {e}")
        raise

    # 2. First validation attempt
    try:
        validated_data = target_model.model_validate(data)
        app_logger.debug("Initial validation successful. No coercion needed.")
        return validated_data, []
    except ValidationError as e:
        app_logger.warning(f"Initial validation against {target_model.__name__} failed. Attempting proactive correction.")
        
        # 3. On failure, diagnose and apply corrections
        corrected_data = copy.deepcopy(data)
        errors = e.errors()

        for error in errors:
            field_name = error['loc'][0] if error['loc'] else None
            
            # Correction rule: List of strings to list of objects with a 'text' key
            if 'model_type' in error['type'] and isinstance(error['input'], list) and all(isinstance(i, str) for i in error['input']):
                if field_name and field_name in corrected_data:
                    correction_msg = f"Corrected field '{field_name}': LLM provided a list of strings instead of a list of objects; the system automatically wrapped each string in the required format."
                    app_logger.info(correction_msg)
                    correction_descriptions.append(correction_msg)
                    corrected_data[field_name] = [{"text": item} for item in error['input']]

            # Correction rule: Coerce numbers to strings for specific fields
            if 'string_type' in error['type'] and isinstance(error['input'], (int, float)):
                field_loc = error.get('loc', [])
                if len(field_loc) > 1 and field_loc[0] == 'key_metric' and field_loc[1] == 'value':
                     correction_msg = "Corrected field 'key_metric.value': LLM provided a number instead of a string; the system automatically converted it."
                     app_logger.info(correction_msg)
                     correction_descriptions.append(correction_msg)
                     if 'key_metric' in corrected_data and isinstance(corrected_data['key_metric'], dict):
                         corrected_data['key_metric']['value'] = str(error['input'])

        # 4. Final validation attempt after corrections
        try:
            validated_data = target_model.model_validate(corrected_data)
            app_logger.info(f"Proactive correction successful. Data is now valid for {target_model.__name__}.")
            return validated_data, correction_descriptions
        except ValidationError:
            app_logger.error(f"Correction failed. Re-raising original validation error.")
            raise e

def _sanitize_llm_output(text: str) -> str:
    """
    Strips invalid characters from LLM output.
    """
    sanitized_text = text.replace('\ufeff', '')
    sanitized_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized_text)
    return sanitized_text.strip()

def _extract_final_answer_from_json(text: str) -> str:
    """
    Detects if the LLM hallucinated and wrapped a FINAL_ANSWER inside a JSON object.
    If so, it extracts the FINAL_ANSWER string and returns it.
    This makes the agent more robust to common LLM formatting errors.
    """
    try:
        json_match = re.search(r"```json\s*\n(.*?)\n\s*```|(\{.*?\})", text, re.DOTALL)
        if not json_match:
            return text

        json_str = json_match.group(1) or json_match.group(2)
        if not json_str:
            return text
            
        data = json.loads(json_str.strip())

        def find_answer_in_values(d):
            if isinstance(d, dict):
                for value in d.values():
                    found = find_answer_in_values(value)
                    if found:
                        return found
            elif isinstance(d, list):
                for item in d:
                    found = find_answer_in_values(item)
                    if found:
                        return found
            elif isinstance(d, str) and "FINAL_ANSWER:" in d:
                return d
            return None

        final_answer_value = find_answer_in_values(data)

        if final_answer_value:
            app_logger.warning(f"LLM hallucination detected and corrected. Extracted FINAL_ANSWER from JSON.")
            return final_answer_value

    except (json.JSONDecodeError, AttributeError):
        return text
    
    return text

def _condense_and_clean_history(history: list) -> list:
    """
    Sanitizes conversation history to save tokens by being abstract and provider-agnostic.
    1. Normalizes history from different provider formats by checking for object attributes.
    2. Aggressively removes ALL old capability definitions from the history.
    3. Replaces duplicate tool outputs with a placeholder.
    4. Denormalizes the history back to the original provider's format.
    """
    if not history:
        return []

    def _normalize_history(provider_history: list) -> list:
        """Converts provider-specific history to a generic internal format using type-aware checks."""
        normalized = []
        for msg in provider_history:
            role, content = "", ""
            if hasattr(msg, 'parts') and hasattr(msg, 'role'):
                role = msg.role
                if msg.parts and hasattr(msg.parts[0], 'text'):
                    content = msg.parts[0].text
            elif isinstance(msg, dict):
                role = msg.get('role', '')
                content = msg.get('content', '')
            normalized.append({'role': role, 'content': content})
        return normalized

    def _denormalize_history(generic_history: list, provider: str) -> list:
        """Converts the generic internal history back to a provider-specific format."""
        if provider == "Google":
            denormalized = []
            for msg in generic_history:
                role = 'model' if msg['role'] == 'assistant' else msg['role']
                denormalized.append({
                    'role': role,
                    'parts': [{'text': msg['content']}]
                })
            return denormalized
        return generic_history

    normalized_history = _normalize_history(history)
    
    cleaned_history = []
    seen_tool_outputs = set()
    capabilities_pattern = re.compile(r'# Capabilities\n--- Available Tools ---.*', re.DOTALL)
    
    system_prompt_wrapper_pattern = re.compile(r"SYSTEM PROMPT:.*USER PROMPT:\n", re.DOTALL)

    for msg in normalized_history:
        msg_copy = copy.deepcopy(msg)
        content = msg_copy.get('content', '')

        if msg_copy.get('role') == 'user' and system_prompt_wrapper_pattern.match(content):
            app_logger.debug("History Condensation: Removing system prompt wrapper from user message.")
            content = system_prompt_wrapper_pattern.sub("", content)
        
        if capabilities_pattern.search(content):
            app_logger.debug("History Condensation: Removing obsolete capability definitions.")
            content = capabilities_pattern.sub("# Capabilities\n[... Omitted for Brevity ...]", content)

        if msg_copy.get('role') in ['assistant', 'model']:
            try:
                json_content = json.loads(content)
                normalized_content = json.dumps(json_content, sort_keys=True)
                
                if normalized_content in seen_tool_outputs:
                    app_logger.debug("History Condensation: Replacing duplicate tool output.")
                    content = json.dumps({"status": "success", "comment": "Duplicate output omitted for brevity."})
                else:
                    seen_tool_outputs.add(normalized_content)
            except (json.JSONDecodeError, TypeError):
                pass
        
        msg_copy['content'] = content
        cleaned_history.append(msg_copy)

    return _denormalize_history(cleaned_history, APP_CONFIG.CURRENT_PROVIDER)


def _get_full_system_prompt(session_data: dict, dependencies: dict, system_prompt_override: str = None, active_prompt_name_for_filter: str = None, source: str = "text") -> str:
    """
    Constructs the final system prompt based on the user's license tier.
    """
    if system_prompt_override:
        return system_prompt_override

    if not session_data or not dependencies or 'STATE' not in dependencies:
        return "You are a helpful assistant."

    base_prompt_text = ""
    license_info = session_data.get("license_info", {})
    user_tier = license_info.get("tier")
    privileged_tiers = ["Prompt Engineer", "Enterprise"]

    if user_tier in privileged_tiers and session_data.get("system_prompt_template"):
        app_logger.info(f"Using custom system prompt for privileged user (Tier: {user_tier}).")
        base_prompt_text = session_data["system_prompt_template"]
    else:
        app_logger.info(f"Using server-side default system prompt for user (Tier: {user_tier or 'Standard'}).")
        base_prompt_text = PROVIDER_SYSTEM_PROMPTS.get(APP_CONFIG.CURRENT_PROVIDER, PROVIDER_SYSTEM_PROMPTS["Google"])

    STATE = dependencies['STATE']

    charting_instructions_section = ""
    if APP_CONFIG.CHARTING_ENABLED:
        charting_intensity = session_data.get("charting_intensity", "medium")
        chart_instructions_detail = CHARTING_INSTRUCTIONS.get(charting_intensity, "")
        if chart_instructions_detail:
            charting_instructions_section = f"- **Charting Guidelines:** {chart_instructions_detail}"

    tools_context = ""
    use_condensed_context = False
    if APP_CONFIG.CONDENSE_SYSTEMPROMPT_HISTORY and session_data and session_data.get("full_context_sent"):
        use_condensed_context = True

    tool_to_exclude = 'TDA_FinalReport' if source == 'prompt_library' else 'TDA_ComplexPromptReport'
    structured_tools = STATE.get('structured_tools', {})
    mcp_tools = STATE.get('mcp_tools', {})

    if use_condensed_context:
        app_logger.info("Session context: Using condensed (names-only) capability list for subsequent turn.")
        condensed_tools_parts = ["--- Available Tools (Names Only) ---"]
        for category, tools in sorted(structured_tools.items()):
            enabled_tools = [f"`{t['name']}`" for t in tools if not t.get('disabled') and t['name'] != tool_to_exclude]
            if enabled_tools:
                condensed_tools_parts.append(f"- **{category}**: {', '.join(enabled_tools)}")
        tools_context = "\n".join(condensed_tools_parts) if len(condensed_tools_parts) > 1 else "--- No Tools Available ---"
    else:
        app_logger.info("Session context: Sending full, detailed capability list for the first turn.")
        tool_context_parts = ["--- Available Tools ---"]
        for category, tools in sorted(structured_tools.items()):
            enabled_tools_in_category = [t for t in tools if not t['disabled'] and t['name'] != tool_to_exclude]
            if enabled_tools_in_category:
                tool_context_parts.append(f"--- Category: {category} ---")
                for tool_info in enabled_tools_in_category:
                    tool_obj = mcp_tools.get(tool_info['name'])
                    if not tool_obj: continue
                    
                    tool_str = f"- `{tool_obj.name}` (tool): {tool_obj.description}"
                    args_dict = tool_obj.args if isinstance(tool_obj.args, dict) else {}

                    if args_dict:
                        tool_str += "\n  - Arguments:"
                        for arg_name, arg_details in args_dict.items():
                            arg_type = arg_details.get('type', 'any')
                            is_required = arg_details.get('required', False)
                            req_str = "required" if is_required else "optional"
                            arg_desc = arg_details.get('description', 'No description.')
                            tool_str += f"\n    - `{arg_name}` ({arg_type}, {req_str}): {arg_desc}"
                    tool_context_parts.append(tool_str)
        tools_context = "\n".join(tool_context_parts) if len(tool_context_parts) > 1 else "--- No Tools Available ---"
    
    prompts_context = STATE.get('prompts_context', '')
    if active_prompt_name_for_filter:
        app_logger.info(f"Recursion prevention: Filtering active prompt '{active_prompt_name_for_filter}' from planner context.")
        
        filtered_prompts_context_parts = []
        current_prompt_block = []
        is_in_target_prompt = False

        for line in prompts_context.split('\n'):
            is_new_prompt_start = line.strip().startswith('- `') and ' (prompt):' in line

            if is_new_prompt_start:
                if current_prompt_block and not is_in_target_prompt:
                    filtered_prompts_context_parts.extend(current_prompt_block)
                
                current_prompt_block = [line]
                is_in_target_prompt = f"`{active_prompt_name_for_filter}`" in line
            else:
                current_prompt_block.append(line)
        
        if current_prompt_block and not is_in_target_prompt:
            filtered_prompts_context_parts.extend(current_prompt_block)

        prompts_context = "\n".join(filtered_prompts_context_parts)

    if use_condensed_context:
        condensed_prompts_parts = ["--- Available Prompts (Names Only) ---"]
        structured_prompts = STATE.get('structured_prompts', {})
        for category, prompts in sorted(structured_prompts.items()):
            enabled_prompts = [f"`{p['name']}`" for p in prompts if not p.get('disabled') and p['name'] != active_prompt_name_for_filter]
            if enabled_prompts:
                condensed_prompts_parts.append(f"- **{category}**: {', '.join(enabled_prompts)}")
        prompts_context = "\n".join(condensed_prompts_parts) if len(condensed_prompts_parts) > 1 else "--- No Prompts Available ---"
    
    if not use_condensed_context and session_data:
        session_data["full_context_sent"] = True

    final_system_prompt = base_prompt_text.replace(
        '{charting_instructions_section}', charting_instructions_section
    ).replace(
        '{tools_context}', tools_context
    ).replace(
        '{prompts_context}', prompts_context
    ).replace(
        '{mcp_system_name}', APP_CONFIG.MCP_SYSTEM_NAME
    )
    
    return final_system_prompt

def _normalize_bedrock_model_id(model_id: str) -> str:
    """
    Normalizes a standard Bedrock model ID by removing versioning suffixes,
    but leaves Inference Profile ARNs untouched.
    """
    if model_id.startswith("arn:aws:bedrock:"):
        return model_id
    # Safely split by the version delimiter ':' and take the base model ID
    return model_id.split(':')[0]

async def call_llm_api(llm_instance: any, prompt: str, session_id: str = None, chat_history=None, raise_on_error: bool = False, system_prompt_override: str = None, dependencies: dict = None, reason: str = "No reason provided.", disabled_history: bool = False, active_prompt_name_for_filter: str = None, source: str = "text") -> tuple[str, int, int]:
    if not llm_instance:
        raise RuntimeError("LLM is not initialized.")
    
    response_text = ""
    input_tokens, output_tokens = 0, 0
    
    max_retries = APP_CONFIG.LLM_API_MAX_RETRIES
    base_delay = APP_CONFIG.LLM_API_BASE_DELAY
    
    session_data = get_session(session_id) if session_id else None
    system_prompt = _get_full_system_prompt(session_data, dependencies, system_prompt_override, active_prompt_name_for_filter, source)

    history_for_log_str = "No history available."
    if session_data: 
        history_source = []
        if not disabled_history:
             history_source = chat_history if chat_history is not None else session_data.get('chat_object', [])

        if APP_CONFIG.CURRENT_PROVIDER == "Google" and hasattr(session_data.get('chat_object'), 'history'):
             normalized_history = [
                 {'role': msg.role, 'content': msg.parts[0].text} for msg in session_data['chat_object'].history
             ]
             history_json_obj = {"chat_history": normalized_history}
        else:
             history_json_obj = {"chat_history": history_source}
        
        history_for_log_str = json.dumps(history_json_obj, indent=2)

    full_log_message = (
        f"--- FULL CONTEXT (Session: {session_id or 'one-off'}) ---\n"
        f"--- REASON FOR CALL ---\n{reason}\n\n"
        f"--- History (History Disabled for LLM Call: {disabled_history}) ---\n{history_for_log_str}\n\n"
        f"--- Current User Prompt (with System Prompt) ---\n"
        f"SYSTEM PROMPT:\n{system_prompt}\n\n"
        f"USER PROMPT:\n{prompt}\n"
    )
    llm_history_logger.info(full_log_message)


    for attempt in range(max_retries):
        try:
            if APP_CONFIG.CURRENT_PROVIDER == "Google":
                is_session_call = session_data is not None and 'chat_object' in session_data and not disabled_history
                
                if is_session_call:
                    chat_session = session_data['chat_object']
                    full_prompt_for_api = f"SYSTEM PROMPT:\n{system_prompt}\n\nUSER PROMPT:\n{prompt}"
                    
                    if APP_CONFIG.CONDENSE_SYSTEMPROMPT_HISTORY:
                        chat_session.history = _condense_and_clean_history(chat_session.history)
                    
                    response = await chat_session.send_message_async(full_prompt_for_api)
                else:
                    full_prompt_for_api = f"{system_prompt}\n\n{prompt}"
                    response = await llm_instance.generate_content_async(full_prompt_for_api)

                if not response or not hasattr(response, 'text'):
                    raise RuntimeError("Google LLM returned an empty or invalid response.")
                response_text = response.text.strip()
                
                if hasattr(response, 'usage_metadata'):
                    usage = response.usage_metadata
                    input_tokens = usage.prompt_token_count
                    output_tokens = usage.candidates_token_count
                
                break

            elif APP_CONFIG.CURRENT_PROVIDER in ["Anthropic", "OpenAI", "Azure", "Ollama", "Friendli"]:
                history_source = []
                if not disabled_history:
                    history_source = chat_history if chat_history is not None else (session_data.get('chat_object', []) if session_id else [])

                if APP_CONFIG.CONDENSE_SYSTEMPROMPT_HISTORY:
                    history_source = _condense_and_clean_history(history_source)

                messages_for_api = [{'role': 'assistant' if msg.get('role') == 'model' else msg.get('role'), 'content': msg.get('content')} for msg in history_source]
                messages_for_api.append({'role': 'user', 'content': prompt})
                
                if APP_CONFIG.CURRENT_PROVIDER == "Anthropic":
                    response = await llm_instance.messages.create(
                        model=APP_CONFIG.CURRENT_MODEL, system=system_prompt, messages=messages_for_api, max_tokens=4096, timeout=120.0
                    )
                    response_text = _sanitize_llm_output(response.content[0].text)
                    if hasattr(response, 'usage'):
                        input_tokens, output_tokens = response.usage.input_tokens, response.usage.output_tokens
                
                elif APP_CONFIG.CURRENT_PROVIDER in ["OpenAI", "Azure", "Friendli"]:
                    messages_for_api.insert(0, {'role': 'system', 'content': system_prompt})
                    response = await llm_instance.chat.completions.create(
                        model=APP_CONFIG.CURRENT_MODEL, messages=messages_for_api, max_tokens=4096, timeout=120.0
                    )
                    response_text = _sanitize_llm_output(response.choices[0].message.content)
                    if hasattr(response, 'usage'):
                        input_tokens, output_tokens = response.usage.prompt_tokens, response.usage.completion_tokens
                
                elif APP_CONFIG.CURRENT_PROVIDER == "Ollama":
                    response = await llm_instance.chat(
                        model=APP_CONFIG.CURRENT_MODEL, messages=messages_for_api, system_prompt=system_prompt
                    )
                    response_text = response["message"]["content"].strip()
                    input_tokens, output_tokens = response.get('prompt_eval_count', 0), response.get('eval_count', 0)
                
                break
            
            # --- MODIFICATION START: Final context-aware payload logic for AWS Bedrock ---
            elif APP_CONFIG.CURRENT_PROVIDER == "Amazon":
                history = []
                if not disabled_history:
                    history = (session_data.get('chat_object', []) if session_id else []) or (chat_history or [])

                if APP_CONFIG.CONDENSE_SYSTEMPROMPT_HISTORY:
                    history = _condense_and_clean_history(history)

                model_id_to_invoke = APP_CONFIG.CURRENT_MODEL
                is_inference_profile = model_id_to_invoke.startswith("arn:aws:bedrock:")
                
                bedrock_provider = ""
                if is_inference_profile:
                    profile_part = model_id_to_invoke.split('/')[-1]
                    provider_match = re.search(r'\.(.*?)\.', profile_part)
                    if provider_match:
                        bedrock_provider = provider_match.group(1)
                else:
                    bedrock_provider = model_id_to_invoke.split('.')[0]
                
                app_logger.info(f"Determined Bedrock provider for payload construction: '{bedrock_provider}'")

                body = ""
                if bedrock_provider == "anthropic":
                    messages = [{'role': 'assistant' if msg.get('role') == 'model' else msg.get('role'), 'content': msg.get('content')} for msg in history]
                    messages.append({'role': 'user', 'content': prompt})
                    body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31", 
                        "max_tokens": 4096, 
                        "system": system_prompt, 
                        "messages": messages
                    })
                elif bedrock_provider == "amazon":
                    # Use modern `messages` format for newer models/profiles, legacy `inputText` for direct legacy calls
                    if is_inference_profile or "titan-text-express" not in model_id_to_invoke:
                         messages = [{'role': 'assistant' if msg.get('role') == 'model' else 'user', 'content': [{'text': msg.get('content')}]} for msg in history]
                         messages.append({"role": "user", "content": [{"text": prompt}]})
                         body_dict = {"messages": messages, "inferenceConfig": {"maxTokens": 4096}}
                         if system_prompt:
                             body_dict["system"] = [{"text": system_prompt}]
                         body = json.dumps(body_dict)
                    else: # Legacy Titan direct invocation
                        text_prompt = f"{system_prompt}\n\n" + "".join([f"{msg['role']}: {msg['content']}\n\n" for msg in history]) + f"user: {prompt}\n\nassistant:"
                        body = json.dumps({"inputText": text_prompt, "textGenerationConfig": {"maxTokenCount": 4096}})

                elif bedrock_provider in ["cohere", "meta", "ai21", "mistral"]:
                    text_prompt = f"{system_prompt}\n\n" + "".join([f"{msg['role']}: {msg['content']}\n\n" for msg in history]) + f"user: {prompt}\n\nassistant:"
                    
                    if bedrock_provider == "cohere":
                        body_dict = {"prompt": text_prompt, "max_tokens": 4096}
                    elif bedrock_provider == "meta":
                        body_dict = {"prompt": text_prompt, "max_gen_len": 2048}
                    elif bedrock_provider == "mistral":
                        body_dict = {"prompt": text_prompt, "max_tokens": 4096}
                    else: # ai21
                        body_dict = {"prompt": text_prompt, "maxTokens": 4096}
                    body = json.dumps(body_dict)
                else:
                    app_logger.warning(f"Unknown Bedrock provider '{bedrock_provider}'. Defaulting to legacy 'inputText' format.")
                    text_prompt = f"{system_prompt}\n\n" + "".join([f"{msg['role']}: {msg['content']}\n\n" for msg in history]) + f"user: {prompt}\n\nassistant:"
                    body = json.dumps({
                        "inputText": text_prompt, 
                        "textGenerationConfig": {"maxTokenCount": 4096}
                    })

                final_model_id_for_api = _normalize_bedrock_model_id(model_id_to_invoke)
                
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, lambda: llm_instance.invoke_model(body=body, modelId=final_model_id_for_api))
                response_body = json.loads(response.get('body').read())
                
                if bedrock_provider == "anthropic":
                    response_text = response_body.get('content')[0].get('text')
                elif bedrock_provider == "amazon":
                    if is_inference_profile or "titan-text-express" not in model_id_to_invoke:
                        response_text = response_body.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
                    else:
                        response_text = response_body.get('results')[0].get('outputText')
                elif bedrock_provider == "cohere":
                    response_text = response_body.get('generations')[0].get('text')
                elif bedrock_provider == "meta":
                    response_text = response_body.get('generation')
                elif bedrock_provider == "mistral":
                    response_text = response_body.get('outputs')[0].get('text')
                elif bedrock_provider == "ai21":
                    response_text = response_body.get('completions')[0].get('data').get('text')
                else:
                    response_text = response_body.get('results')[0].get('outputText')
                
                break
            # --- MODIFICATION END ---
            else:
                raise NotImplementedError(f"Provider '{APP_CONFIG.CURRENT_PROVIDER}' is not yet supported.")
        
        except (InternalServerError, RateLimitError, OpenAI_APIError) as e:
            if attempt < max_retries - 1:
                delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                app_logger.warning(f"API overloaded or rate limited. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
                continue
            else:
                raise e
        except Exception as e:
            app_logger.error(f"Error calling LLM API for provider {APP_CONFIG.CURRENT_PROVIDER}: {e}", exc_info=True)
            llm_history_logger.error(f"--- ERROR in LLM call ---\n{e}\n" + "-"*50 + "\n")
            raise e

    if not response_text and raise_on_error:
        raise RuntimeError(f"LLM call failed after {max_retries} retries.")

    response_text = _extract_final_answer_from_json(response_text)

    llm_logger.info(f"--- REASON FOR CALL ---\n{reason}\n--- RESPONSE ---\n{response_text}\n" + "-"*50 + "\n")

    if session_id:
        update_token_count(session_id, input_tokens, output_tokens)

    return response_text, input_tokens, output_tokens

def _is_model_certified(model_name: str, certified_list: list[str]) -> bool:
    """
    Checks if a model is certified, a supporting wildcards.
    """
    if APP_CONFIG.ALL_MODELS_UNLOCKED:
        return True
    for pattern in certified_list:
        regex_pattern = re.escape(pattern).replace('\\*', '.*')
        if re.fullmatch(regex_pattern, model_name):
            return True
    return False

async def list_models(provider: str, credentials: dict) -> list[dict]:
    """
    Lists available models for a given provider and checks certification status.
    """
    certified_list = []
    model_names = []

    # --- MODIFICATION START: Implement resilient model listing for Google ---
    if provider == "Google":
        certified_list = CERTIFIED_GOOGLE_MODELS
        api_key = credentials.get("apiKey")
        if not api_key:
            raise ValueError("API key for Google is required.")

        # Use a direct, raw HTTP request to bypass the faulty SDK deserialization
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                models_data = response.json().get("models", [])
            
            # Manually parse the raw response, ignoring any unexpected fields
            model_names = [
                model['name'].split('/')[-1]
                for model in models_data
                if 'generateContent' in model.get('supportedGenerationMethods', [])
            ]
        except (httpx.RequestError, json.JSONDecodeError, KeyError) as e:
            app_logger.error(f"Failed to list Google models via direct API call: {e}", exc_info=True)
            # As a fallback, try the original SDK method, which might work if the SDK is updated
            try:
                app_logger.warning("Direct API failed. Falling back to SDK's genai.list_models().")
                genai.configure(api_key=api_key)
                sdk_models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_names = [model.name.split('/')[-1] for model in sdk_models]
            except Exception as sdk_e:
                app_logger.error(f"SDK fallback for listing Google models also failed: {sdk_e}", exc_info=True)
                raise RuntimeError("Could not retrieve model list from Google via API or SDK.") from sdk_e
    # --- MODIFICATION END ---

    elif provider == "Anthropic":
        certified_list = CERTIFIED_ANTHROPIC_MODELS
        client = AsyncAnthropic(api_key=credentials.get("apiKey"))
        models_page = await client.models.list()
        model_names = [model.id for model in models_page.data]

    elif provider == "OpenAI":
        certified_list = CERTIFIED_OPENAI_MODELS
        client = AsyncOpenAI(api_key=credentials.get("apiKey"))
        models_page = await client.models.list()
        model_names = [model.id for model in models_page.data if "gpt" in model.id]

    # --- MODIFICATION START: Implement bifurcated model listing for Friendli.ai ---
    elif provider == "Friendli":
        certified_list = CERTIFIED_FRIENDLI_MODELS
        friendli_token = credentials.get("friendli_token")
        endpoint_url = credentials.get("friendli_endpoint_url")
        
        if endpoint_url: # Dedicated Endpoint: Fetch models dynamically
            request_url = f"{endpoint_url.rstrip('/')}/v1/models"
            headers = {"Authorization": f"Bearer {friendli_token}"}
            async with httpx.AsyncClient() as client:
                app_logger.info(f"Fetching Friendli.ai models from: {request_url}")
                response = await client.get(request_url, headers=headers)
                response.raise_for_status()
                data = response.json()
            model_names = [model.get("id") for model in data if model.get("id")]
        else: # Serverless Endpoint: Use a hardcoded list, as per the new design
            app_logger.info("Friendli.ai Serverless mode: No model listing endpoint available. Returning certified list.")
            # Return the raw names from the certified list, removing wildcards
            model_names = [name.replace('*', '') for name in certified_list]
    # --- MODIFICATION END ---
            
    elif provider == "Amazon":
        bedrock_client = boto3.client(
            service_name='bedrock',
            aws_access_key_id=credentials.get("aws_access_key_id"),
            aws_secret_access_key=credentials.get("aws_secret_access_key"),
            region_name=credentials.get("aws_region")
        )
        loop = asyncio.get_running_loop()
        if credentials.get("listing_method") == "inference_profiles":
            certified_list = CERTIFIED_AMAZON_PROFILES
            response = await loop.run_in_executor(None, lambda: bedrock_client.list_inference_profiles())
            model_names = [p['inferenceProfileArn'] for p in response['inferenceProfileSummaries']]
        else:
            certified_list = CERTIFIED_AMAZON_MODELS
            response = await loop.run_in_executor(None, lambda: bedrock_client.list_foundation_models(byOutputModality='TEXT'))
            model_names = [m['modelId'] for m in response['modelSummaries']]
    
    elif provider == "Azure":
        certified_list = CERTIFIED_AZURE_MODELS
        deployment_name = credentials.get("azure_deployment_name")
        if deployment_name:
            model_names = [deployment_name]
    
    elif provider == "Ollama":
        certified_list = CERTIFIED_OLLAMA_MODELS
        client = OllamaClient(host=credentials.get("host"))
        models_data = await client.list_models()
        model_names = [m.get("name") for m in models_data]

    return [
        {
            "name": name,
            "certified": _is_model_certified(name, certified_list)
        }
        for name in model_names
    ]

