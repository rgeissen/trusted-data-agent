#!/usr/bin/env python3
"""
Test script for tda_config.json persistence functionality.

This script tests the ConfigManager to ensure RAG collections
are properly persisted and loaded.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from trusted_data_agent.core.config_manager import ConfigManager
from datetime import datetime, timezone


def test_config_manager():
    """Test the ConfigManager functionality."""
    
    print("=" * 60)
    print("Testing TDA Config Manager")
    print("=" * 60)
    
    # Create a test config manager with a custom path
    test_config_path = project_root / "test_tda_config.json"
    
    # Clean up any existing test file
    if test_config_path.exists():
        test_config_path.unlink()
        print(f"✓ Cleaned up existing test config")
    
    # Test 1: Initialize ConfigManager
    print("\n1. Testing ConfigManager initialization...")
    config_manager = ConfigManager(config_path=test_config_path)
    print(f"✓ ConfigManager created with path: {test_config_path}")
    
    # Test 2: Load default config (should create file)
    print("\n2. Testing default config creation...")
    config = config_manager.load_config()
    print(f"✓ Config loaded. Schema version: {config['schema_version']}")
    print(f"✓ Number of collections: {len(config['rag_collections'])}")
    
    # Verify file was created
    if test_config_path.exists():
        print(f"✓ Config file created at: {test_config_path}")
    else:
        print(f"✗ ERROR: Config file not created!")
        return False
    
    # Test 3: Get RAG collections
    print("\n3. Testing get_rag_collections()...")
    collections = config_manager.get_rag_collections()
    print(f"✓ Retrieved {len(collections)} collection(s)")
    if collections:
        default_collection = collections[0]
        print(f"  - Default collection ID: {default_collection['id']}")
        print(f"  - Default collection name: {default_collection['name']}")
    
    # Test 4: Add a new collection
    print("\n4. Testing add_rag_collection()...")
    new_collection = {
        "id": 1,
        "name": "Test Collection",
        "collection_name": "test_collection_abc123",
        "mcp_server_id": "test_server",
        "enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "Test collection for validation"
    }
    success = config_manager.add_rag_collection(new_collection)
    if success:
        print(f"✓ Added new collection: {new_collection['name']}")
    else:
        print(f"✗ ERROR: Failed to add collection")
        return False
    
    # Verify the collection was added
    collections = config_manager.get_rag_collections()
    print(f"✓ Total collections now: {len(collections)}")
    
    # Test 5: Update a collection
    print("\n5. Testing update_rag_collection()...")
    updates = {
        "name": "Updated Test Collection",
        "description": "Updated description"
    }
    success = config_manager.update_rag_collection(1, updates)
    if success:
        print(f"✓ Updated collection ID 1")
        
        # Verify the update
        collections = config_manager.get_rag_collections()
        updated = next((c for c in collections if c["id"] == 1), None)
        if updated and updated["name"] == "Updated Test Collection":
            print(f"✓ Verified update: {updated['name']}")
        else:
            print(f"✗ ERROR: Update not reflected")
            return False
    else:
        print(f"✗ ERROR: Failed to update collection")
        return False
    
    # Test 6: Remove a collection
    print("\n6. Testing remove_rag_collection()...")
    success = config_manager.remove_rag_collection(1)
    if success:
        print(f"✓ Removed collection ID 1")
        
        # Verify removal
        collections = config_manager.get_rag_collections()
        print(f"✓ Total collections now: {len(collections)}")
    else:
        print(f"✗ ERROR: Failed to remove collection")
        return False
    
    # Test 7: Try to remove default collection (should fail)
    print("\n7. Testing protection of default collection...")
    success = config_manager.remove_rag_collection(0)
    if not success:
        print(f"✓ Default collection (ID 0) protected from removal")
    else:
        print(f"✗ ERROR: Default collection should not be removable!")
        return False
    
    # Test 8: Reload config from file
    print("\n8. Testing config reload from file...")
    new_manager = ConfigManager(config_path=test_config_path)
    reloaded_config = new_manager.load_config()
    print(f"✓ Config reloaded from file")
    print(f"✓ Schema version: {reloaded_config['schema_version']}")
    print(f"✓ Collections: {len(reloaded_config['rag_collections'])}")
    
    # Cleanup
    print("\n9. Cleaning up test file...")
    if test_config_path.exists():
        test_config_path.unlink()
        print(f"✓ Removed test config file")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_config_manager()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
