#!/usr/bin/env python3
"""
Test switch_profile_context() function to verify proper LLM and MCP client initialization.
This test validates that when switching to a profile, both clients are properly initialized
and validated before being committed to APP_STATE.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trusted_data_agent.core.config_manager import ConfigManager
from src.trusted_data_agent.core.configuration_service import (
    switch_profile_context, retrieve_credentials_for_provider, ENCRYPTION_AVAILABLE
)
from src.trusted_data_agent.core.config import (
    APP_STATE, APP_CONFIG,
    get_user_provider, get_user_model, get_user_llm_instance,
    get_user_mcp_client, get_user_mcp_server_name
)


def print_header(text: str):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")


def print_status(passed: bool, message: str):
    """Print test status"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} - {message}")


async def test_profile_exists(config_manager: ConfigManager, user_uuid: str = None):
    """Test 1: Verify default profile exists"""
    print_header("TEST 1: Verify Default Profile Exists")
    
    default_profile_id = config_manager.get_default_profile_id(user_uuid)
    
    if not default_profile_id:
        print_status(False, "No default profile found")
        print("  → Please create and set a default profile before running this test")
        return None
    
    profile = config_manager.get_profile(default_profile_id, user_uuid)
    
    if not profile:
        print_status(False, f"Profile {default_profile_id} not found")
        return None
    
    print_status(True, f"Default profile found: {profile.get('name', 'Unknown')}")
    print(f"  Profile ID: {default_profile_id}")
    print(f"  Tag: {profile.get('tag', 'N/A')}")
    print(f"  LLM Config ID: {profile.get('llmConfigurationId', 'N/A')}")
    print(f"  MCP Server ID: {profile.get('mcpServerId', 'N/A')}")
    
    return default_profile_id


async def test_llm_configuration_exists(config_manager: ConfigManager, profile_id: str, user_uuid: str = None):
    """Test 2: Verify LLM configuration exists"""
    print_header("TEST 2: Verify LLM Configuration")
    
    profile = config_manager.get_profile(profile_id, user_uuid)
    llm_config_id = profile.get('llmConfigurationId')
    
    if not llm_config_id:
        print_status(False, "Profile has no LLM configuration ID")
        return False
    
    llm_configs = config_manager.get_llm_configurations(user_uuid)
    llm_config = next((c for c in llm_configs if c.get('id') == llm_config_id), None)
    
    if not llm_config:
        print_status(False, f"LLM configuration {llm_config_id} not found")
        return False
    
    provider = llm_config.get('provider')
    model = llm_config.get('model')
    credentials = llm_config.get('credentials', {})
    
    # Try to load stored credentials
    try:
        if user_uuid and ENCRYPTION_AVAILABLE:
            stored_result = await retrieve_credentials_for_provider(user_uuid, provider)
            if stored_result.get("credentials"):
                credentials = {**stored_result["credentials"], **credentials}
                print(f"  ℹ Loaded stored credentials for {provider}")
    except Exception as e:
        print(f"  ⚠ Could not load stored credentials: {e}")
    
    print_status(True, f"LLM configuration found")
    print(f"  Provider: {provider}")
    print(f"  Model: {model}")
    print(f"  Has credentials: {bool(credentials)}")
    
    if not provider or not model:
        print_status(False, "Incomplete LLM configuration (missing provider or model)")
        return False
    
    print_status(True, "LLM configuration is structurally complete")
    print("  ℹ Note: Actual credentials will be validated during switch_profile_context()")
    return True


async def test_mcp_configuration_exists(config_manager: ConfigManager, profile_id: str, user_uuid: str = None):
    """Test 3: Verify MCP server configuration exists"""
    print_header("TEST 3: Verify MCP Server Configuration")
    
    profile = config_manager.get_profile(profile_id, user_uuid)
    mcp_server_id = profile.get('mcpServerId')
    
    if not mcp_server_id:
        print_status(False, "Profile has no MCP server ID")
        return False
    
    mcp_servers = config_manager.get_mcp_servers(user_uuid)
    mcp_server = next((s for s in mcp_servers if s.get('id') == mcp_server_id), None)
    
    if not mcp_server:
        print_status(False, f"MCP server {mcp_server_id} not found")
        return False
    
    server_name = mcp_server.get('name')
    host = mcp_server.get('host')
    port = mcp_server.get('port')
    path = mcp_server.get('path')
    
    print_status(True, f"MCP server configuration found")
    print(f"  Server Name: {server_name}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Path: {path}")
    
    if not all([server_name, host, port, path]):
        print_status(False, "Incomplete MCP server configuration")
        return False
    
    print_status(True, "MCP server configuration appears complete")
    return True


async def test_switch_profile_context(profile_id: str, user_uuid: str = None):
    """Test 4: Execute switch_profile_context and verify initialization"""
    print_header("TEST 4: Execute switch_profile_context()")
    
    print("Attempting to switch to profile...")
    print(f"  Profile ID: {profile_id}")
    print(f"  User UUID: {user_uuid or 'None (shared)'}")
    
    # Clear existing state
    if 'llm' in APP_STATE:
        del APP_STATE['llm']
    if 'mcp_client' in APP_STATE:
        del APP_STATE['mcp_client']
    APP_CONFIG.SERVICES_CONFIGURED = False
    APP_CONFIG.MCP_SERVER_CONNECTED = False
    
    print("\n  → Calling switch_profile_context()...")
    
    try:
        result = await switch_profile_context(profile_id, user_uuid=user_uuid)
        
        if result.get("status") == "error":
            print_status(False, f"switch_profile_context() failed: {result.get('message')}")
            return False
        
        print_status(True, "switch_profile_context() completed successfully")
        
    except Exception as e:
        print_status(False, f"Exception during switch_profile_context(): {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_llm_client_initialized(user_uuid: str = None):
    """Test 5: Verify LLM client was properly initialized"""
    print_header("TEST 5: Verify LLM Client Initialization")
    
    provider = get_user_provider(user_uuid)
    model = get_user_model(user_uuid)
    llm_instance = get_user_llm_instance(user_uuid)
    
    print(f"  Provider: {provider}")
    print(f"  Model: {model}")
    print(f"  LLM Instance: {type(llm_instance).__name__ if llm_instance else 'None'}")
    
    if not provider:
        print_status(False, "Provider not set in APP_STATE")
        return False
    
    if not model:
        print_status(False, "Model not set in APP_STATE")
        return False
    
    if not llm_instance:
        print_status(False, "LLM instance not initialized")
        return False
    
    # Check if it's a placeholder dict (old approach) vs real client
    if isinstance(llm_instance, dict) and llm_instance.get("placeholder"):
        print_status(False, "LLM instance is a placeholder dict, not a real client")
        return False
    
    if not APP_CONFIG.SERVICES_CONFIGURED:
        print_status(False, "APP_CONFIG.SERVICES_CONFIGURED is False")
        return False
    
    print_status(True, "LLM client properly initialized")
    print(f"  Provider: {APP_CONFIG.ACTIVE_PROVIDER}")
    print(f"  Model: {APP_CONFIG.ACTIVE_MODEL}")
    print(f"  Services Configured: {APP_CONFIG.SERVICES_CONFIGURED}")
    
    return True


async def test_mcp_client_initialized(user_uuid: str = None):
    """Test 6: Verify MCP client was properly initialized"""
    print_header("TEST 6: Verify MCP Client Initialization")
    
    mcp_client = get_user_mcp_client(user_uuid)
    server_name = get_user_mcp_server_name(user_uuid)
    
    print(f"  MCP Client: {type(mcp_client).__name__ if mcp_client else 'None'}")
    print(f"  Server Name: {server_name}")
    
    if not mcp_client:
        print_status(False, "MCP client not initialized")
        return False
    
    if not server_name:
        print_status(False, "MCP server name not set")
        return False
    
    if not APP_CONFIG.MCP_SERVER_CONNECTED:
        print_status(False, "APP_CONFIG.MCP_SERVER_CONNECTED is False")
        return False
    
    print_status(True, "MCP client properly initialized")
    print(f"  Server: {server_name}")
    print(f"  MCP Connected: {APP_CONFIG.MCP_SERVER_CONNECTED}")
    
    return True


async def test_mcp_connection(user_uuid: str = None):
    """Test 7: Verify MCP client can actually communicate with server"""
    print_header("TEST 7: Test MCP Client Connection")
    
    mcp_client = get_user_mcp_client(user_uuid)
    server_name = get_user_mcp_server_name(user_uuid)
    
    if not mcp_client or not server_name:
        print_status(False, "MCP client or server name not available")
        return False
    
    print(f"  Testing connection to '{server_name}'...")
    
    try:
        async with mcp_client.session(server_name) as session:
            tools = await session.list_tools()
            prompts = await session.list_prompts()
            resources = await session.list_resources()
            
            print_status(True, "MCP server connection successful")
            print(f"  Tools: {len(tools.tools if hasattr(tools, 'tools') else [])}")
            print(f"  Prompts: {len(prompts.prompts if hasattr(prompts, 'prompts') else [])}")
            print(f"  Resources: {len(resources.resources if hasattr(resources, 'resources') else [])}")
            
            return True
            
    except Exception as e:
        print_status(False, f"MCP connection failed: {e}")
        return False


async def test_session_creation_check(user_uuid: str = None):
    """Test 8: Verify state satisfies session creation requirements"""
    print_header("TEST 8: Verify Session Creation Requirements")
    
    # This simulates the check in /session endpoint:
    # if not APP_STATE.get('llm') or not APP_CONFIG.MCP_SERVER_CONNECTED
    
    llm = get_user_llm_instance(user_uuid)
    mcp_connected = APP_CONFIG.MCP_SERVER_CONNECTED
    
    print(f"  APP_STATE['llm'] exists: {llm is not None}")
    print(f"  APP_CONFIG.MCP_SERVER_CONNECTED: {mcp_connected}")
    
    can_create_session = bool(llm) and mcp_connected
    
    if can_create_session:
        print_status(True, "Session creation requirements satisfied")
        return True
    else:
        print_status(False, "Session creation requirements NOT satisfied")
        if not llm:
            print("  → Missing: APP_STATE['llm']")
        if not mcp_connected:
            print("  → Missing: APP_CONFIG.MCP_SERVER_CONNECTED")
        return False


async def main():
    """Main test execution"""
    print_header("Switch Profile Context - Comprehensive Test")
    print("This test validates that switch_profile_context() properly initializes")
    print("and validates both LLM and MCP clients before committing to APP_STATE.")
    
    config_manager = ConfigManager()
    user_uuid = None  # Test with shared config
    
    results = {}
    
    # Test 1: Verify profile exists
    profile_id = await test_profile_exists(config_manager, user_uuid)
    results['profile_exists'] = profile_id is not None
    
    if not profile_id:
        print("\n⚠ Cannot continue without a default profile")
        print("Please configure a profile with both LLM and MCP server settings")
        return 1
    
    # Test 2: Verify LLM configuration
    results['llm_config_exists'] = await test_llm_configuration_exists(config_manager, profile_id, user_uuid)
    
    if not results['llm_config_exists']:
        print("\n⚠ Cannot continue without valid LLM configuration")
        return 1
    
    # Test 3: Verify MCP configuration
    results['mcp_config_exists'] = await test_mcp_configuration_exists(config_manager, profile_id, user_uuid)
    
    if not results['mcp_config_exists']:
        print("\n⚠ Cannot continue without valid MCP configuration")
        return 1
    
    # Test 4: Execute switch_profile_context
    results['switch_successful'] = await test_switch_profile_context(profile_id, user_uuid)
    
    if not results['switch_successful']:
        print("\n⚠ switch_profile_context() failed")
        return 1
    
    # Test 5: Verify LLM client initialized
    results['llm_initialized'] = await test_llm_client_initialized(user_uuid)
    
    # Test 6: Verify MCP client initialized
    results['mcp_initialized'] = await test_mcp_client_initialized(user_uuid)
    
    # Test 7: Test MCP connection
    results['mcp_connection'] = await test_mcp_connection(user_uuid)
    
    # Test 8: Verify session creation requirements
    results['session_requirements'] = await test_session_creation_check(user_uuid)
    
    # Summary
    print_header("TEST SUMMARY")
    
    for test_name, passed in results.items():
        print_status(passed, test_name.replace('_', ' ').title())
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED")
        print("\nswitch_profile_context() is working correctly!")
        print("Both LLM and MCP clients are properly initialized and validated.")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        print("Review output above for details")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
