# trusted_data_agent/agent/prompts.py
import os
import json
import logging
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from trusted_data_agent.core.config import APP_STATE

# --- Prompt Loading Mechanism ---

# Initialize a logger for this module.
app_logger = logging.getLogger("quart.app")

# Global dictionary to hold the loaded prompt content.
_LOADED_PROMPTS = {}

def _verify_license_and_load_prompts():
    """
    Verifies the user's license, stores the info, decrypts the base prompts,
    and then checks for developer/enterprise-tier overrides.
    """
    global _LOADED_PROMPTS

    # --- 1. Define Paths ---
    from trusted_data_agent.core.utils import get_project_root
    project_root = str(get_project_root())
    keys_dir = os.path.join(project_root, "tda_keys")
    public_key_path = os.path.join(keys_dir, "public_key.pem")
    license_path = os.path.join(keys_dir, "license.key")
    encrypted_file_path = os.path.join(os.path.dirname(__file__), 'prompts.dat')

    # --- 2. Load Public Key and License ---
    if not os.path.exists(public_key_path):
        raise RuntimeError("Application is missing its public key; cannot verify license.")

    try:
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
    except Exception as e:
        raise RuntimeError("Application public key is invalid; cannot verify license.") from e

    if not os.path.exists(license_path):
        raise RuntimeError("A valid license.key file is required to run this application.")

    try:
        with open(license_path, 'r', encoding='utf-8') as f:
            license_content = json.load(f)
        
        payload = license_content['payload']
        signature = bytes.fromhex(license_content['signature'])
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')

        public_key.verify(
            signature, payload_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        
        expiration_date = datetime.fromisoformat(payload['expires_at'])
        if expiration_date < datetime.now(timezone.utc):
            raise RuntimeError("Your license key has expired.")
            
        app_logger.info(f"License successfully validated for: {payload['holder']} (Tier: {payload.get('tier', 'N/A')})")
        APP_STATE['license_info'] = payload

    except (InvalidSignature, json.JSONDecodeError, KeyError):
        raise RuntimeError("Invalid or corrupt license.key file.")
    except Exception as e:
        raise RuntimeError("License validation failed.") from e

    # --- 3. Decrypt and Load Base Prompts ---
    if not os.path.exists(encrypted_file_path):
        raise FileNotFoundError("Encrypted 'prompts.dat' not found.")

    try:
        prompt_key = payload['prompt_key'].encode('utf-8')
        cipher_suite = Fernet(prompt_key)

        with open(encrypted_file_path, 'rb') as f_in:
            encrypted_data = f_in.read()
            
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        _LOADED_PROMPTS.update(json.loads(decrypted_data.decode('utf-8')))
        app_logger.info("Successfully decrypted and loaded base prompts.")

    except Exception as e:
        raise RuntimeError("Could not load essential prompt configuration.") from e

    # --- 4. MODIFICATION: Check for Tiers with Override Privileges ---
    license_tier = payload.get("tier")
    privileged_tiers = ["Prompt Engineer", "Enterprise"]
    if license_tier in privileged_tiers:
        override_dir = os.path.join(project_root, 'prompt_overrides')
        if os.path.isdir(override_dir):
            app_logger.info(f"'{license_tier}' license detected. Checking for overrides in '{override_dir}'...")
            for filename in os.listdir(override_dir):
                if filename.endswith(".txt"):
                    prompt_name = os.path.splitext(filename)[0]
                    try:
                        with open(os.path.join(override_dir, filename), 'r', encoding='utf-8') as f:
                            _LOADED_PROMPTS[prompt_name] = f.read()
                            app_logger.info(f"  -> Overriding prompt: '{prompt_name}'")
                    except Exception as e:
                        app_logger.error(f"Failed to load override prompt '{filename}': {e}")

# --- Execute the loading process on module import ---
try:
    _verify_license_and_load_prompts()
except (RuntimeError, FileNotFoundError) as e:
    app_logger.critical(f"A critical error occurred during application startup: {e}")
    raise

# --- Prompt Definitions ---
MASTER_SYSTEM_PROMPT = _LOADED_PROMPTS.get("MASTER_SYSTEM_PROMPT", "")
GOOGLE_MASTER_SYSTEM_PROMPT = _LOADED_PROMPTS.get("GOOGLE_MASTER_SYSTEM_PROMPT", "")
OLLAMA_MASTER_SYSTEM_PROMPT = _LOADED_PROMPTS.get("OLLAMA_MASTER_SYSTEM_PROMPT", "")

PROVIDER_SYSTEM_PROMPTS = {
    "Google": GOOGLE_MASTER_SYSTEM_PROMPT,
    "Anthropic": MASTER_SYSTEM_PROMPT,
    "Amazon": MASTER_SYSTEM_PROMPT,
    "OpenAI": MASTER_SYSTEM_PROMPT,
    "Azure": MASTER_SYSTEM_PROMPT,
    "Friendli": MASTER_SYSTEM_PROMPT,
    "Ollama": OLLAMA_MASTER_SYSTEM_PROMPT
}

G2PLOT_GUIDELINES = _LOADED_PROMPTS.get("G2PLOT_GUIDELINES", "")
CHARTING_INSTRUCTIONS = _LOADED_PROMPTS.get("CHARTING_INSTRUCTIONS", {})

ERROR_RECOVERY_PROMPT = _LOADED_PROMPTS.get("ERROR_RECOVERY_PROMPT", "")
TACTICAL_SELF_CORRECTION_PROMPT = _LOADED_PROMPTS.get("TACTICAL_SELF_CORRECTION_PROMPT", "")
TACTICAL_SELF_CORRECTION_PROMPT_COLUMN_ERROR = _LOADED_PROMPTS.get("TACTICAL_SELF_CORRECTION_PROMPT_COLUMN_ERROR", "")
TACTICAL_SELF_CORRECTION_PROMPT_TABLE_ERROR = _LOADED_PROMPTS.get("TACTICAL_SELF_CORRECTION_PROMPT_TABLE_ERROR", "")
TASK_CLASSIFICATION_PROMPT = _LOADED_PROMPTS.get("TASK_CLASSIFICATION_PROMPT", "")
WORKFLOW_META_PLANNING_PROMPT = _LOADED_PROMPTS.get("WORKFLOW_META_PLANNING_PROMPT", "")
WORKFLOW_TACTICAL_PROMPT = _LOADED_PROMPTS.get("WORKFLOW_TACTICAL_PROMPT", "")
# --- MODIFICATION START: Add new SQL Consolidation Prompt ---
SQL_CONSOLIDATION_PROMPT = _LOADED_PROMPTS.get("SQL_CONSOLIDATION_PROMPT", "")
# --- MODIFICATION END ---
