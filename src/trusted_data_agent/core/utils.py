# src/trusted_data_agent/core/utils.py
import json
import logging

try:
    from google.cloud import texttospeech
    from google.oauth2 import service_account
except ImportError:
    texttospeech = None
    service_account = None

from trusted_data_agent.core.config import APP_STATE

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
