# src/trusted_data_agent/core/provider_colors.py
"""
Provider color mapping for visual identification throughout the UI.
Each provider gets a distinct color scheme that's auto-applied to profiles.
"""

# Provider color schemes: primary color and lighter variant for gradients
PROVIDER_COLORS = {
    "google": {
        "primary": "#4285f4",     # Google Blue
        "secondary": "#669df6",   # Lighter blue
        "name": "Google"
    },
    "anthropic": {
        "primary": "#8b5cf6",     # Purple
        "secondary": "#a78bfa",   # Lighter purple
        "name": "Anthropic"
    },
    "openai": {
        "primary": "#10a37f",     # OpenAI Green
        "secondary": "#1ec99b",   # Lighter green
        "name": "OpenAI"
    },
    "amazon_bedrock": {
        "primary": "#ff9900",     # AWS Orange
        "secondary": "#ffb84d",   # Lighter orange
        "name": "Amazon Bedrock"
    },
    "azure": {
        "primary": "#00bfff",     # Azure Cyan
        "secondary": "#4dd2ff",   # Lighter cyan
        "name": "Azure"
    },
    "friendli": {
        "primary": "#ec4899",     # Pink
        "secondary": "#f472b6",   # Lighter pink
        "name": "Friendli"
    },
    "ollama": {
        "primary": "#64748b",     # Slate gray
        "secondary": "#94a3b8",   # Lighter gray
        "name": "Ollama"
    }
}

def get_provider_color(provider: str) -> dict:
    """
    Get color scheme for a provider.
    
    Args:
        provider: Provider name (case-insensitive)
        
    Returns:
        Dictionary with 'primary', 'secondary', and 'name' keys
        Returns a default gray scheme if provider not found
    """
    provider_lower = provider.lower() if provider else ""
    
    return PROVIDER_COLORS.get(provider_lower, {
        "primary": "#6b7280",     # Default gray
        "secondary": "#9ca3af",   # Lighter gray
        "name": provider or "Unknown"
    })

def get_provider_from_llm_config(llm_config: dict) -> str:
    """
    Extract provider name from LLM configuration.
    
    Args:
        llm_config: LLM configuration dictionary
        
    Returns:
        Provider name in lowercase
    """
    return (llm_config.get("provider") or "").lower()
