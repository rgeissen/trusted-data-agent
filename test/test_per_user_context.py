"""
Test script for per-user runtime context isolation functionality.

This test simulates multiple users configuring different providers/models
simultaneously and verifies that their configurations remain isolated.

Usage:
    # Set multi-user mode
    export TDA_CONFIGURATION_PERSISTENCE=false
    export TDA_SESSIONS_FILTER_BY_USER=true
    
    # Run the test
    python test/test_per_user_context.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trusted_data_agent.core.config import (
    APP_CONFIG, APP_STATE,
    get_user_provider, get_user_model,
    set_user_provider, set_user_model,
    get_user_aws_region, set_user_aws_region,
    get_user_azure_deployment_details, set_user_azure_deployment_details,
    get_user_mcp_server_name, set_user_mcp_server_name,
    cleanup_inactive_user_contexts
)

def get_user_contexts():
    """Helper to get the user runtime contexts dict."""
    return APP_STATE.get("user_runtime_contexts", {})


def print_header(text):
    """Print a formatted test section header."""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def print_test(test_name, passed):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")


async def test_basic_isolation():
    """Test basic per-user isolation of provider and model."""
    print_header("TEST 1: Basic Provider/Model Isolation")
    
    # Ensure we're in multi-user mode
    original_persistence = APP_CONFIG.CONFIGURATION_PERSISTENCE
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    user1 = "test-user-1"
    user2 = "test-user-2"
    
    # User 1 configures Amazon/Claude
    set_user_provider("Amazon", user1)
    set_user_model("anthropic.claude-3-5-sonnet-20241022-v2:0", user1)
    
    # User 2 configures Google/Gemini
    set_user_provider("Google", user2)
    set_user_model("gemini-1.5-pro", user2)
    
    # Verify isolation
    user1_provider = get_user_provider(user1)
    user1_model = get_user_model(user1)
    user2_provider = get_user_provider(user2)
    user2_model = get_user_model(user2)
    
    print(f"User 1 - Provider: {user1_provider}, Model: {user1_model}")
    print(f"User 2 - Provider: {user2_provider}, Model: {user2_model}")
    
    # Tests
    test1 = user1_provider == "Amazon"
    test2 = user1_model == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    test3 = user2_provider == "Google"
    test4 = user2_model == "gemini-1.5-pro"
    test5 = user1_provider != user2_provider
    test6 = user1_model != user2_model
    
    print_test("User 1 has Amazon provider", test1)
    print_test("User 1 has Claude model", test2)
    print_test("User 2 has Google provider", test3)
    print_test("User 2 has Gemini model", test4)
    print_test("User 1 and User 2 have different providers", test5)
    print_test("User 1 and User 2 have different models", test6)
    
    # Restore
    APP_CONFIG.CONFIGURATION_PERSISTENCE = original_persistence
    
    return all([test1, test2, test3, test4, test5, test6])


async def test_provider_specific_configs():
    """Test isolation of provider-specific configurations."""
    print_header("TEST 2: Provider-Specific Configuration Isolation")
    
    original_persistence = APP_CONFIG.CONFIGURATION_PERSISTENCE
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    user1 = "test-user-aws"
    user2 = "test-user-azure"
    
    # User 1 configures AWS
    set_user_provider("Amazon", user1)
    set_user_aws_region("us-west-2", user1)
    
    # User 2 configures Azure
    set_user_provider("Azure", user2)
    azure_details = {
        "endpoint": "https://test.openai.azure.com",
        "deployment_name": "gpt-4",
        "api_version": "2024-02-15-preview"
    }
    set_user_azure_deployment_details(azure_details, user2)
    
    # Verify isolation
    user1_region = get_user_aws_region(user1)
    user2_azure = get_user_azure_deployment_details(user2)
    
    print(f"User 1 (AWS) - Region: {user1_region}")
    print(f"User 2 (Azure) - Details: {user2_azure}")
    
    test1 = user1_region == "us-west-2"
    test2 = user2_azure is not None
    test3 = user2_azure.get("endpoint") == "https://test.openai.azure.com" if user2_azure else False
    test4 = get_user_aws_region(user2) is None  # User 2 shouldn't have AWS config
    
    print_test("User 1 has correct AWS region", test1)
    print_test("User 2 has Azure deployment details", test2)
    print_test("User 2 Azure endpoint is correct", test3)
    print_test("User 2 has no AWS region (isolation works)", test4)
    
    APP_CONFIG.CONFIGURATION_PERSISTENCE = original_persistence
    
    return all([test1, test2, test3, test4])


async def test_mcp_server_isolation():
    """Test isolation of MCP server configurations."""
    print_header("TEST 3: MCP Server Configuration Isolation")
    
    original_persistence = APP_CONFIG.CONFIGURATION_PERSISTENCE
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    user1 = "test-user-mcp1"
    user2 = "test-user-mcp2"
    
    # User 1 configures MCP server 1
    set_user_mcp_server_name("sqlite-server", user1)
    
    # User 2 configures MCP server 2
    set_user_mcp_server_name("postgres-server", user2)
    
    # Verify isolation
    user1_server = get_user_mcp_server_name(user1)
    user2_server = get_user_mcp_server_name(user2)
    
    print(f"User 1 - MCP Server: {user1_server}")
    print(f"User 2 - MCP Server: {user2_server}")
    
    test1 = user1_server == "sqlite-server"
    test2 = user2_server == "postgres-server"
    test3 = user1_server != user2_server
    
    print_test("User 1 has correct MCP server", test1)
    print_test("User 2 has correct MCP server", test2)
    print_test("Users have different MCP servers", test3)
    
    APP_CONFIG.CONFIGURATION_PERSISTENCE = original_persistence
    
    return all([test1, test2, test3])


async def test_global_fallback():
    """Test fallback to global config when user_uuid is None."""
    print_header("TEST 4: Global Configuration Fallback")
    
    original_persistence = APP_CONFIG.CONFIGURATION_PERSISTENCE
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    # Set global config
    set_user_provider("OpenAI", None)
    set_user_model("gpt-4", None)
    
    # Get without user_uuid should return global
    provider = get_user_provider(None)
    model = get_user_model(None)
    
    print(f"Global - Provider: {provider}, Model: {model}")
    
    test1 = provider == "OpenAI"
    test2 = model == "gpt-4"
    test3 = APP_CONFIG.CURRENT_PROVIDER == "OpenAI"
    test4 = APP_CONFIG.CURRENT_MODEL == "gpt-4"
    
    print_test("Get without user_uuid returns global provider", test1)
    print_test("Get without user_uuid returns global model", test2)
    print_test("APP_CONFIG.CURRENT_PROVIDER is updated", test3)
    print_test("APP_CONFIG.CURRENT_MODEL is updated", test4)
    
    APP_CONFIG.CONFIGURATION_PERSISTENCE = original_persistence
    
    return all([test1, test2, test3, test4])


async def test_persistence_mode_disabled():
    """Test that isolation is disabled when CONFIGURATION_PERSISTENCE=true."""
    print_header("TEST 5: Isolation Disabled with CONFIGURATION_PERSISTENCE=true")
    
    # Enable persistence mode
    APP_CONFIG.CONFIGURATION_PERSISTENCE = True
    
    user1 = "test-user-persist1"
    user2 = "test-user-persist2"
    
    # Both users set different configs
    set_user_provider("Amazon", user1)
    set_user_provider("Google", user2)
    
    # In persistence mode, both should get the global (last set) value
    user1_provider = get_user_provider(user1)
    user2_provider = get_user_provider(user2)
    global_provider = APP_CONFIG.CURRENT_PROVIDER
    
    print(f"User 1 Provider: {user1_provider}")
    print(f"User 2 Provider: {user2_provider}")
    print(f"Global Provider: {global_provider}")
    
    # In persistence mode, all should match the global value
    test1 = user1_provider == global_provider
    test2 = user2_provider == global_provider
    test3 = user1_provider == user2_provider
    contexts = get_user_contexts()
    test4 = user1 not in contexts or len(contexts[user1]) == 0
    
    print_test("User 1 gets global provider (no isolation)", test1)
    print_test("User 2 gets global provider (no isolation)", test2)
    print_test("Both users have same provider", test3)
    print_test("No per-user contexts created in persistence mode", test4)
    
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    return all([test1, test2, test3])


async def test_concurrent_access():
    """Test concurrent access from multiple users."""
    print_header("TEST 6: Concurrent Multi-User Access")
    
    original_persistence = APP_CONFIG.CONFIGURATION_PERSISTENCE
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    async def user_task(user_id, provider, model, delay=0):
        """Simulate a user configuring their settings."""
        await asyncio.sleep(delay)
        set_user_provider(provider, user_id)
        set_user_model(model, user_id)
        await asyncio.sleep(0.1)  # Simulate some work
        return get_user_provider(user_id), get_user_model(user_id)
    
    # Run 5 users concurrently with different configs
    tasks = [
        user_task("concurrent-user-1", "Amazon", "claude-3", 0.01),
        user_task("concurrent-user-2", "Google", "gemini-pro", 0.02),
        user_task("concurrent-user-3", "OpenAI", "gpt-4", 0.01),
        user_task("concurrent-user-4", "Azure", "gpt-4-turbo", 0.03),
        user_task("concurrent-user-5", "Anthropic", "claude-2", 0.01),
    ]
    
    results = await asyncio.gather(*tasks)
    
    print("Concurrent execution results:")
    expected = [
        ("Amazon", "claude-3"),
        ("Google", "gemini-pro"),
        ("OpenAI", "gpt-4"),
        ("Azure", "gpt-4-turbo"),
        ("Anthropic", "claude-2"),
    ]
    
    all_correct = True
    for i, (result, expected_val) in enumerate(zip(results, expected)):
        user_id = f"concurrent-user-{i+1}"
        matches = result == expected_val
        print(f"  {user_id}: {result} {'✓' if matches else '✗ Expected: ' + str(expected_val)}")
        all_correct = all_correct and matches
    
    print_test("All concurrent users maintained isolated configs", all_correct)
    
    APP_CONFIG.CONFIGURATION_PERSISTENCE = original_persistence
    
    return all_correct


async def test_cleanup():
    """Test cleanup of inactive user contexts."""
    print_header("TEST 7: Cleanup of Inactive User Contexts")
    
    original_persistence = APP_CONFIG.CONFIGURATION_PERSISTENCE
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    # Create contexts for multiple users
    for i in range(5):
        user_id = f"cleanup-test-user-{i}"
        set_user_provider(f"Provider{i}", user_id)
        set_user_model(f"model-{i}", user_id)
    
    contexts = get_user_contexts()
    initial_count = len([k for k in contexts.keys() if k.startswith("cleanup-test-user")])
    print(f"Created {initial_count} user contexts")
    
    # Manually age some contexts by modifying their last_accessed time
    import time
    from datetime import datetime, timedelta
    
    contexts = get_user_contexts()
    for i in range(3):
        user_id = f"cleanup-test-user-{i}"
        if user_id in contexts:
            # Set last_access to 31 minutes ago (older than 30 min timeout)
            from datetime import timezone
            old_time = datetime.now(timezone.utc) - timedelta(seconds=1860)
            contexts[user_id]['last_access'] = old_time.isoformat()
    
    print(f"Aged 3 contexts to be older than 30 minutes")
    
    # Run cleanup with 0.5 hour (30 minute) timeout
    cleanup_inactive_user_contexts(max_age_hours=0.5)
    
    contexts = get_user_contexts()
    remaining_count = len([k for k in contexts.keys() if k.startswith("cleanup-test-user")])
    print(f"After cleanup: {remaining_count} contexts remaining")
    
    test1 = remaining_count == 2  # Should have cleaned up 3 old ones, leaving 2
    print_test("Cleanup removed aged contexts", test1)
    
    # Verify remaining contexts are the recent ones (user-3 and user-4)
    contexts = get_user_contexts()
    test2 = "cleanup-test-user-3" in contexts
    test3 = "cleanup-test-user-4" in contexts
    test4 = "cleanup-test-user-0" not in contexts
    
    print_test("Recent context user-3 preserved", test2)
    print_test("Recent context user-4 preserved", test3)
    print_test("Aged context user-0 removed", test4)
    
    APP_CONFIG.CONFIGURATION_PERSISTENCE = original_persistence
    
    return all([test1, test2, test3, test4])


async def test_context_structure():
    """Test the structure of runtime contexts."""
    print_header("TEST 8: Runtime Context Data Structure")
    
    original_persistence = APP_CONFIG.CONFIGURATION_PERSISTENCE
    APP_CONFIG.CONFIGURATION_PERSISTENCE = False
    
    user_id = "structure-test-user"
    
    # Set various configurations
    set_user_provider("Amazon", user_id)
    set_user_model("claude-3", user_id)
    set_user_aws_region("us-east-1", user_id)
    set_user_mcp_server_name("test-server", user_id)
    
    # Get the context
    contexts = get_user_contexts()
    context = contexts.get(user_id, {})
    
    print(f"Context keys: {list(context.keys())}")
    
    test1 = 'provider' in context
    test2 = 'model' in context
    test3 = 'aws_region' in context
    test4 = 'mcp_server_name' in context
    test5 = 'last_access' in context
    test6 = context['provider'] == "Amazon"
    test7 = context['model'] == "claude-3"
    
    print_test("Context has 'provider' key", test1)
    print_test("Context has 'model' key", test2)
    print_test("Context has 'aws_region' key", test3)
    print_test("Context has 'mcp_server_name' key", test4)
    print_test("Context has 'last_accessed' timestamp", test5)
    print_test("Provider value is correct", test6)
    print_test("Model value is correct", test7)
    
    APP_CONFIG.CONFIGURATION_PERSISTENCE = original_persistence
    
    return all([test1, test2, test3, test4, test5, test6, test7])


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("  PER-USER RUNTIME CONTEXT ISOLATION TEST SUITE")
    print("="*80)
    
    print(f"\nConfiguration Persistence: {APP_CONFIG.CONFIGURATION_PERSISTENCE}")
    print(f"Python Version: {sys.version}")
    
    results = []
    
    try:
        results.append(("Basic Isolation", await test_basic_isolation()))
        results.append(("Provider-Specific Configs", await test_provider_specific_configs()))
        results.append(("MCP Server Isolation", await test_mcp_server_isolation()))
        results.append(("Global Fallback", await test_global_fallback()))
        results.append(("Persistence Mode Disabled", await test_persistence_mode_disabled()))
        results.append(("Concurrent Access", await test_concurrent_access()))
        results.append(("Context Cleanup", await test_cleanup()))
        results.append(("Context Structure", await test_context_structure()))
    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Per-user isolation is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
