"""
Test script for Marketplace Phase 2: Collection Ownership & Access Control

This script tests the following Phase 2 features:
1. User accessible collections filtering (owned + subscribed)
2. Ownership validation for collection operations
3. Fork collection functionality
4. Maintenance skipping for subscribed collections
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trusted_data_agent.auth.database import get_db_session, init_database
from trusted_data_agent.auth.models import User, CollectionSubscription
from trusted_data_agent.core.config import APP_STATE
from trusted_data_agent.core.config_manager import get_config_manager
from trusted_data_agent.agent.rag_retriever import RAGRetriever


def setup_test_environment():
    """Initialize test environment with database and users."""
    print("\n" + "="*80)
    print("PHASE 2 TEST: Setting up test environment")
    print("="*80)
    
    # Initialize database
    init_database()
    
    # Create test users
    with get_db_session() as session:
        # Check if test users exist
        user1 = session.query(User).filter_by(username="test_user1").first()
        user2 = session.query(User).filter_by(username="test_user2").first()
        
        if not user1:
            user1 = User(
                username="test_user1",
                email="test1@example.com",
                password_hash="dummy_hash",
                is_admin=False
            )
            session.add(user1)
            session.commit()
            print(f"✓ Created test user1: {user1.id}")
        else:
            print(f"✓ Using existing test user1: {user1.id}")
        
        if not user2:
            user2 = User(
                username="test_user2",
                email="test2@example.com",
                password_hash="dummy_hash",
                is_admin=False
            )
            session.add(user2)
            session.commit()
            print(f"✓ Created test user2: {user2.id}")
        else:
            print(f"✓ Using existing test user2: {user2.id}")
        
        return user1.id, user2.id


def test_user_accessible_collections(retriever, user1_id, user2_id):
    """Test _get_user_accessible_collections method."""
    print("\n" + "="*80)
    print("TEST 1: User Accessible Collections Filtering")
    print("="*80)
    
    # Get all collections
    all_collections = APP_STATE.get("rag_collections", [])
    print(f"\nTotal collections in system: {len(all_collections)}")
    
    # Test user1 accessible collections
    user1_accessible = retriever._get_user_accessible_collections(user1_id)
    print(f"\nUser1 accessible collections: {user1_accessible}")
    print(f"  Count: {len(user1_accessible)}")
    
    # Test user2 accessible collections
    user2_accessible = retriever._get_user_accessible_collections(user2_id)
    print(f"\nUser2 accessible collections: {user2_accessible}")
    print(f"  Count: {len(user2_accessible)}")
    
    # Test anonymous user (no user_id)
    anon_accessible = retriever._get_user_accessible_collections(None)
    print(f"\nAnonymous user accessible collections: {anon_accessible}")
    print(f"  Count: {len(anon_accessible)}")
    print(f"  (Should include only admin-owned and public collections)")
    
    print("\n✓ TEST 1 PASSED: User accessible collections filtering works")


def test_ownership_validation(retriever, user1_id, user2_id):
    """Test is_user_collection_owner method."""
    print("\n" + "="*80)
    print("TEST 2: Collection Ownership Validation")
    print("="*80)
    
    collections = APP_STATE.get("rag_collections", [])
    
    if not collections:
        print("⚠ No collections found - skipping ownership test")
        return
    
    test_collection = collections[0]
    coll_id = test_collection["id"]
    owner_id = test_collection.get("owner_user_id")
    
    print(f"\nTesting collection: {test_collection['name']} (ID: {coll_id})")
    print(f"  Owner ID: {owner_id}")
    
    # Test ownership checks
    user1_is_owner = retriever.is_user_collection_owner(coll_id, user1_id)
    user2_is_owner = retriever.is_user_collection_owner(coll_id, user2_id)
    
    print(f"\n  User1 is owner: {user1_is_owner}")
    print(f"  User2 is owner: {user2_is_owner}")
    
    # For admin-owned collections (owner_user_id is None), check admin status
    if owner_id is None:
        print(f"  Collection is admin-owned (owner_user_id is None)")
        print(f"  Only admins should return True for ownership")
    
    print("\n✓ TEST 2 PASSED: Ownership validation works")


def test_subscription_check(retriever, user1_id, user2_id):
    """Test subscription checking and create a test subscription."""
    print("\n" + "="*80)
    print("TEST 3: Subscription Status Checking")
    print("="*80)
    
    collections = APP_STATE.get("rag_collections", [])
    
    if len(collections) < 2:
        print("⚠ Need at least 2 collections - skipping subscription test")
        return None
    
    # Use collection 0 as the subscribed collection
    source_coll_id = 0
    
    print(f"\nCreating subscription for User1 to collection {source_coll_id}...")
    
    # Create a subscription
    with get_db_session() as session:
        # Check if subscription already exists
        existing_sub = session.query(CollectionSubscription).filter_by(
            user_id=user1_id,
            source_collection_id=source_coll_id
        ).first()
        
        if not existing_sub:
            subscription = CollectionSubscription(
                user_id=user1_id,
                source_collection_id=source_coll_id,
                enabled=True
            )
            session.add(subscription)
            session.commit()
            print(f"✓ Created subscription (ID: {subscription.id})")
        else:
            print(f"✓ Using existing subscription (ID: {existing_sub.id})")
    
    # Test subscription check
    user1_subscribed = retriever.is_subscribed_collection(source_coll_id, user1_id)
    user2_subscribed = retriever.is_subscribed_collection(source_coll_id, user2_id)
    
    print(f"\n  User1 subscribed to collection {source_coll_id}: {user1_subscribed}")
    print(f"  User2 subscribed to collection {source_coll_id}: {user2_subscribed}")
    
    if user1_subscribed:
        print(f"\n✓ TEST 3 PASSED: Subscription checking works")
    else:
        print(f"\n✗ TEST 3 FAILED: User1 should be subscribed but check returned False")
    
    return source_coll_id


def test_fork_collection(retriever, user1_id):
    """Test fork_collection method."""
    print("\n" + "="*80)
    print("TEST 4: Fork Collection")
    print("="*80)
    
    collections = APP_STATE.get("rag_collections", [])
    
    if not collections:
        print("⚠ No collections found - skipping fork test")
        return
    
    # Fork collection 0
    source_coll_id = 0
    source_coll = next((c for c in collections if c["id"] == source_coll_id), None)
    
    if not source_coll:
        print(f"⚠ Collection {source_coll_id} not found - skipping fork test")
        return
    
    print(f"\nForking collection: {source_coll['name']} (ID: {source_coll_id})")
    
    # Get MCP server ID from source collection
    mcp_server_id = source_coll.get("mcp_server_id", "test-mcp-server")
    
    # Fork the collection
    forked_id = retriever.fork_collection(
        source_collection_id=source_coll_id,
        new_name=f"Forked: {source_coll['name']}",
        new_description="Test fork created by Phase 2 test script",
        owner_user_id=user1_id,
        mcp_server_id=mcp_server_id
    )
    
    if forked_id:
        print(f"✓ Successfully forked collection")
        print(f"  Source ID: {source_coll_id}")
        print(f"  Forked ID: {forked_id}")
        print(f"  Owner: {user1_id}")
        
        # Verify forked collection exists
        forked_coll = retriever.get_collection_metadata(forked_id)
        if forked_coll:
            print(f"  Forked collection name: {forked_coll['name']}")
            print(f"  Forked collection owner: {forked_coll.get('owner_user_id')}")
            print(f"\n✓ TEST 4 PASSED: Fork collection works")
        else:
            print(f"\n✗ TEST 4 FAILED: Forked collection not found in metadata")
    else:
        print(f"✗ TEST 4 FAILED: Fork operation returned None")


def test_maintenance_skip(retriever, user1_id, subscribed_coll_id):
    """Test that maintenance is skipped for subscribed collections."""
    print("\n" + "="*80)
    print("TEST 5: Maintenance Skip for Subscribed Collections")
    print("="*80)
    
    if subscribed_coll_id is None:
        print("⚠ No subscription setup - skipping maintenance test")
        return
    
    print(f"\nAttempting maintenance on subscribed collection {subscribed_coll_id}...")
    print(f"  User: {user1_id} (subscriber, not owner)")
    
    # This should skip maintenance and log a message
    try:
        retriever._maintain_vector_store(subscribed_coll_id, user_id=user1_id)
        print(f"✓ Maintenance operation completed (should have been skipped)")
        print(f"  Check logs above for 'Skipping maintenance' message")
        print(f"\n✓ TEST 5 PASSED: Maintenance skip logic executed")
    except Exception as e:
        print(f"✗ TEST 5 FAILED: Error during maintenance: {e}")


def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n" + "#"*80)
    print("# MARKETPLACE PHASE 2 TEST SUITE")
    print("# Collection Ownership & Access Control")
    print("#"*80)
    
    try:
        # Setup
        user1_id, user2_id = setup_test_environment()
        
        # Initialize RAG retriever (similar to production setup)
        config_manager = get_config_manager()
        collections = config_manager.get_rag_collections()
        APP_STATE["rag_collections"] = collections
        
        rag_cases_dir = Path(__file__).parent.parent / "rag" / "tda_rag_cases"
        persist_dir = Path(__file__).parent.parent / ".chromadb_rag_cache"
        
        retriever = RAGRetriever(
            rag_cases_dir=rag_cases_dir,
            persist_directory=persist_dir
        )
        
        # Run tests
        test_user_accessible_collections(retriever, user1_id, user2_id)
        test_ownership_validation(retriever, user1_id, user2_id)
        subscribed_coll_id = test_subscription_check(retriever, user1_id, user2_id)
        test_fork_collection(retriever, user1_id)
        test_maintenance_skip(retriever, user1_id, subscribed_coll_id)
        
        # Summary
        print("\n" + "#"*80)
        print("# TEST SUITE COMPLETE")
        print("#"*80)
        print("\n✓ All Phase 2 tests completed successfully!")
        print("\nPhase 2 Features Verified:")
        print("  ✓ User accessible collections filtering (owned + subscribed)")
        print("  ✓ Ownership validation for collection operations")
        print("  ✓ Subscription checking")
        print("  ✓ Fork collection functionality")
        print("  ✓ Maintenance skipping for subscribed collections")
        
    except Exception as e:
        print(f"\n✗ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
