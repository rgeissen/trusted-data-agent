#!/usr/bin/env python3
"""Quick debug script to check profile configuration"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

# Get profiles
response = requests.get(f"{BASE_URL}/v1/profiles")
profiles = response.json().get("profiles", [])

if profiles:
    profile = profiles[0]
    print(f"\nProfile: {profile['name']}")
    print(f"ID: {profile['id']}")
    print(f"\nLLM Config ID: {profile.get('llmConfigurationId')}")
    print(f"MCP Server ID: {profile.get('mcpServerId')}")
    
    # Get LLM configurations
    response = requests.get(f"{BASE_URL}/v1/llm_configurations")
    llm_configs = response.json().get("llm_configurations", [])
    
    llm_config_id = profile.get('llmConfigurationId')
    llm_config = next((c for c in llm_configs if c.get("id") == llm_config_id), None)
    
    if llm_config:
        print(f"\nLLM Configuration:")
        print(f"  Provider: {llm_config.get('provider')}")
        print(f"  Model: {llm_config.get('model')}")
        print(f"  Has credentials: {'credentials' in llm_config}")
        if 'credentials' in llm_config:
            creds = llm_config.get('credentials', {})
            print(f"  Credential keys: {list(creds.keys())}")
    else:
        print(f"\n✗ LLM configuration '{llm_config_id}' not found")
    
    # Get MCP servers
    response = requests.get(f"{BASE_URL}/v1/mcp_servers")
    mcp_servers = response.json().get("mcp_servers", [])
    
    mcp_server_id = profile.get('mcpServerId')
    mcp_server = next((s for s in mcp_servers if s.get("id") == mcp_server_id), None)
    
    if mcp_server:
        print(f"\nMCP Server:")
        print(f"  Name: {mcp_server.get('name')}")
        print(f"  Has config: {'config' in mcp_server}")
    else:
        print(f"\n✗ MCP server '{mcp_server_id}' not found")
