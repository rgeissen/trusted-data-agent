#!/usr/bin/env python3
"""
Test script for document upload configuration database schema.

Tests:
1. Database initialization
2. Configuration retrieval
3. Configuration updates
4. Configuration reset
5. Effective config merging
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

def test_database_initialization():
    """Test that database initializes correctly."""
    print("\n" + "="*60)
    print("TEST 1: Database Initialization")
    print("="*60)
    
    from trusted_data_agent.auth.database import init_database
    
    result = init_database()
    print(f"✓ Database initialization: {'SUCCESS' if result else 'FAILED'}")
    return result


def test_get_all_configs():
    """Test retrieving all configurations."""
    print("\n" + "="*60)
    print("TEST 2: Get All Configurations")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    
    configs = DocumentUploadConfigManager.get_all_configs()
    print(f"✓ Found {len(configs)} provider configurations")
    
    for config in configs:
        print(f"  - {config.provider}: enabled={config.enabled}, native={config.use_native_upload}")
    
    return len(configs) > 0


def test_get_effective_config():
    """Test getting effective configuration with defaults."""
    print("\n" + "="*60)
    print("TEST 3: Get Effective Configuration")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    import json
    
    providers = ['Google', 'Anthropic', 'OpenAI']
    
    for provider in providers:
        effective = DocumentUploadConfigManager.get_effective_config(provider)
        print(f"\n{provider} Effective Config:")
        print(json.dumps(effective, indent=2))
    
    return True


def test_update_config():
    """Test updating configuration."""
    print("\n" + "="*60)
    print("TEST 4: Update Configuration")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    
    # Update Google config
    print("\nUpdating Google configuration...")
    updated = DocumentUploadConfigManager.update_config(
        provider='Google',
        max_file_size_mb=50,
        use_native_upload=False,
        notes='Test override - increased limit and disabled native'
    )
    
    if updated:
        print(f"✓ Updated Google config: {updated.to_dict()}")
    else:
        print("✗ Failed to update Google config")
        return False
    
    # Verify override is applied
    print("\nVerifying override in effective config...")
    effective = DocumentUploadConfigManager.get_effective_config('Google')
    
    success = (
        effective['max_file_size_mb'] == 50 and
        effective['use_native_upload'] == False and
        effective['has_overrides'] == True
    )
    
    if success:
        print("✓ Override correctly applied:")
        print(f"  - max_file_size_mb: {effective['max_file_size_mb']} (expected 50)")
        print(f"  - use_native_upload: {effective['use_native_upload']} (expected False)")
        print(f"  - has_overrides: {effective['has_overrides']} (expected True)")
    else:
        print("✗ Override not correctly applied")
    
    return success


def test_reset_config():
    """Test resetting configuration to defaults."""
    print("\n" + "="*60)
    print("TEST 5: Reset Configuration to Defaults")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    
    # Reset Google config
    print("\nResetting Google configuration to defaults...")
    reset = DocumentUploadConfigManager.reset_to_defaults('Google')
    
    if reset:
        print(f"✓ Reset Google config")
    else:
        print("✗ Failed to reset Google config")
        return False
    
    # Verify overrides are removed
    print("\nVerifying reset in effective config...")
    effective = DocumentUploadConfigManager.get_effective_config('Google')
    
    success = (
        effective['use_native_upload'] == True and
        effective['has_overrides'] == False
    )
    
    if success:
        print("✓ Reset correctly applied:")
        print(f"  - use_native_upload: {effective['use_native_upload']} (expected True)")
        print(f"  - has_overrides: {effective['has_overrides']} (expected False)")
    else:
        print("✗ Reset not correctly applied")
    
    return success


def test_supported_formats_override():
    """Test updating supported formats override."""
    print("\n" + "="*60)
    print("TEST 6: Update Supported Formats Override")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    import json
    
    # Update Anthropic with custom formats
    print("\nUpdating Anthropic with custom formats...")
    custom_formats = ['pdf', 'txt']
    updated = DocumentUploadConfigManager.update_config(
        provider='Anthropic',
        supported_formats_override=custom_formats,
        notes='Test - restricted to PDF and TXT only'
    )
    
    if updated:
        print(f"✓ Updated Anthropic config")
    else:
        print("✗ Failed to update Anthropic config")
        return False
    
    # Verify formats override
    print("\nVerifying formats override in effective config...")
    effective = DocumentUploadConfigManager.get_effective_config('Anthropic')
    
    success = (
        effective['supported_formats'] == custom_formats and
        effective['has_overrides'] == True
    )
    
    if success:
        print("✓ Formats override correctly applied:")
        print(f"  - supported_formats: {effective['supported_formats']}")
        print(f"  - has_overrides: {effective['has_overrides']}")
    else:
        print("✗ Formats override not correctly applied")
    
    # Reset for cleanup
    DocumentUploadConfigManager.reset_to_defaults('Anthropic')
    
    return success


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("DOCUMENT UPLOAD CONFIG DATABASE SCHEMA TESTS")
    print("="*60)
    
    tests = [
        ("Database Initialization", test_database_initialization),
        ("Get All Configs", test_get_all_configs),
        ("Get Effective Config", test_get_effective_config),
        ("Update Config", test_update_config),
        ("Reset Config", test_reset_config),
        ("Supported Formats Override", test_supported_formats_override)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            print(f"\n✗ TEST FAILED: {name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, str(e)))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"       Error: {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
