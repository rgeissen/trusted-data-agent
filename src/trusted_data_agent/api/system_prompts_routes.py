# src/trusted_data_agent/api/system_prompts_routes.py
import os
import logging
from quart import Blueprint, jsonify, request
from functools import wraps

from trusted_data_agent.core.config import APP_STATE
from trusted_data_agent.auth.middleware import require_auth

system_prompts_bp = Blueprint('system_prompts', __name__, url_prefix='/api/v1/system-prompts')
app_logger = logging.getLogger("quart.app")

# Define all available system prompts
AVAILABLE_PROMPTS = [
    "MASTER_SYSTEM_PROMPT",
    "GOOGLE_MASTER_SYSTEM_PROMPT",
    "OLLAMA_MASTER_SYSTEM_PROMPT",
    "G2PLOT_GUIDELINES",
    "ERROR_RECOVERY_PROMPT",
    "TACTICAL_SELF_CORRECTION_PROMPT",
    "TACTICAL_SELF_CORRECTION_PROMPT_COLUMN_ERROR",
    "TACTICAL_SELF_CORRECTION_PROMPT_TABLE_ERROR",
    "TASK_CLASSIFICATION_PROMPT",
    "WORKFLOW_META_PLANNING_PROMPT",
    "WORKFLOW_TACTICAL_PROMPT",
    "SQL_CONSOLIDATION_PROMPT"
]

def require_prompt_engineer_or_enterprise(f):
    """
    Decorator to require Prompt Engineer or Enterprise license tier.
    Must be used with @require_auth decorator.
    current_user is injected by @require_auth as the first parameter.
    """
    @wraps(f)
    async def decorated_function(current_user, *args, **kwargs):
        # Check license tier from APP_STATE
        license_info = APP_STATE.get('license_info') or {}
        license_tier = license_info.get('tier', 'Unknown')
        
        if license_tier not in ['Prompt Engineer', 'Enterprise']:
            return jsonify({
                "success": False,
                "message": f"System Prompt Editor requires 'Prompt Engineer' or 'Enterprise' license tier. Current tier: {license_tier}"
            }), 403
        
        return await f(current_user, *args, **kwargs)
    
    return decorated_function


@system_prompts_bp.route('/<prompt_name>', methods=['GET'])
@require_auth
@require_prompt_engineer_or_enterprise
async def get_system_prompt(current_user, prompt_name):
    """
    Get the current content of a system prompt.
    Checks for override in prompt_overrides/ directory first, then falls back to encrypted default.
    """
    try:
        if prompt_name not in AVAILABLE_PROMPTS:
            return jsonify({
                "success": False,
                "message": f"Invalid prompt name. Available prompts: {', '.join(AVAILABLE_PROMPTS)}"
            }), 400
        
        # Get project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        override_path = os.path.join(project_root, 'prompt_overrides', f'{prompt_name}.txt')
        
        # Check for override file
        if os.path.exists(override_path):
            try:
                with open(override_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    "success": True,
                    "prompt_name": prompt_name,
                    "content": content,
                    "is_override": True
                })
            except Exception as e:
                app_logger.error(f"Error reading override file for {prompt_name}: {e}")
        
        # Fall back to default from prompts.py (loaded from encrypted prompts.dat)
        from trusted_data_agent.agent.prompts import _LOADED_PROMPTS
        content = _LOADED_PROMPTS.get(prompt_name, "")
        
        return jsonify({
            "success": True,
            "prompt_name": prompt_name,
            "content": content,
            "is_override": False
        })
        
    except Exception as e:
        app_logger.error(f"Error getting system prompt {prompt_name}: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to load system prompt: {str(e)}"
        }), 500


@system_prompts_bp.route('/<prompt_name>', methods=['PUT'])
@require_auth
@require_prompt_engineer_or_enterprise
async def update_system_prompt(current_user, prompt_name):
    """
    Save a system prompt override to prompt_overrides/ directory.
    """
    try:
        if prompt_name not in AVAILABLE_PROMPTS:
            return jsonify({
                "success": False,
                "message": f"Invalid prompt name. Available prompts: {', '.join(AVAILABLE_PROMPTS)}"
            }), 400
        
        data = await request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({
                "success": False,
                "message": "Content is required"
            }), 400
        
        # Get project root and ensure prompt_overrides directory exists
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        override_dir = os.path.join(project_root, 'prompt_overrides')
        os.makedirs(override_dir, exist_ok=True)
        
        override_path = os.path.join(override_dir, f'{prompt_name}.txt')
        
        # Write the override file
        with open(override_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        app_logger.info(f"System prompt override saved: {prompt_name}")
        
        return jsonify({
            "success": True,
            "message": f"System prompt '{prompt_name}' saved successfully",
            "prompt_name": prompt_name
        })
        
    except Exception as e:
        app_logger.error(f"Error saving system prompt {prompt_name}: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to save system prompt: {str(e)}"
        }), 500


@system_prompts_bp.route('/<prompt_name>', methods=['DELETE'])
@require_auth
@require_prompt_engineer_or_enterprise
async def delete_system_prompt_override(current_user, prompt_name):
    """
    Delete a system prompt override, reverting to the encrypted default.
    """
    try:
        if prompt_name not in AVAILABLE_PROMPTS:
            return jsonify({
                "success": False,
                "message": f"Invalid prompt name. Available prompts: {', '.join(AVAILABLE_PROMPTS)}"
            }), 400
        
        # Get project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        override_path = os.path.join(project_root, 'prompt_overrides', f'{prompt_name}.txt')
        
        # Check if override exists
        if not os.path.exists(override_path):
            return jsonify({
                "success": True,
                "message": f"No override exists for '{prompt_name}', already using default"
            })
        
        # Delete the override file
        os.remove(override_path)
        app_logger.info(f"System prompt override deleted: {prompt_name}")
        
        return jsonify({
            "success": True,
            "message": f"System prompt override deleted, reverted to default for '{prompt_name}'"
        })
        
    except Exception as e:
        app_logger.error(f"Error deleting system prompt override {prompt_name}: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to delete system prompt override: {str(e)}"
        }), 500


@system_prompts_bp.route('/list', methods=['GET'])
@require_auth
@require_prompt_engineer_or_enterprise
async def list_system_prompts(current_user):
    """
    List all available system prompts with their override status.
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        override_dir = os.path.join(project_root, 'prompt_overrides')
        
        prompts = []
        for prompt_name in AVAILABLE_PROMPTS:
            override_path = os.path.join(override_dir, f'{prompt_name}.txt')
            has_override = os.path.exists(override_path)
            
            prompts.append({
                "name": prompt_name,
                "has_override": has_override
            })
        
        return jsonify({
            "success": True,
            "prompts": prompts
        })
        
    except Exception as e:
        app_logger.error(f"Error listing system prompts: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to list system prompts: {str(e)}"
        }), 500
