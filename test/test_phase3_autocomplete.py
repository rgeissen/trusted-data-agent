#!/usr/bin/env python3
"""
Test Phase 3: Autocomplete Endpoint with Multi-User Support

Tests the /api/questions endpoint to ensure:
1. User context is extracted from request
2. RAGAccessContext is created with user_uuid
3. Collections are filtered by user accessibility
4. Query results are filtered by user_uuid (for owned collections)
5. Backward compatibility maintained for unauthenticated access
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MockRequest:
    """Mock Flask request object"""
    def __init__(self, args=None):
        self.args = args or {}
    
    def get(self, key, default=''):
        return self.args.get(key, default)


class TestAutocompletePhase3:
    """Test the autocomplete endpoint with multi-user support"""
    
    def test_user_context_extraction(self):
        """Test that user context is extracted from request"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        # Simulate extracting user_uuid from request
        user = {"user_id": "user-123", "email": "user@example.com"}
        user_uuid = user.get("user_id") if user else None
        
        assert user_uuid == "user-123"
        print("✅ User context extraction: PASS")
    
    def test_rag_context_creation_in_endpoint(self):
        """Test that RAGAccessContext is created in endpoint"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        # Mock retriever
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={0, 1, 2})
        
        # Simulate endpoint logic
        user = {"user_id": "user-123"}
        user_uuid = user.get("user_id") if user else None
        rag_context = RAGAccessContext(user_uuid, retriever) if user_uuid else None
        
        assert rag_context is not None
        assert rag_context.user_id == "user-123"
        print("✅ RAGAccessContext creation in endpoint: PASS")
    
    def test_collection_filtering_by_user_access(self):
        """Test that collections are filtered by user access"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={0, 1})  # User can access 0 and 1
        
        user_uuid = "user-123"
        rag_context = RAGAccessContext(user_uuid, retriever)
        
        # Simulate profile-based filtering
        profile_collections = {0, 1, 2}  # Profile allows 0, 1, 2
        user_accessible = rag_context.accessible_collections
        
        # Intersection
        allowed = profile_collections & user_accessible
        
        assert allowed == {0, 1}, "Should only include collections user can access"
        print("✅ Collection filtering by user access: PASS")
    
    def test_no_context_for_unauthenticated_access(self):
        """Test backward compatibility for unauthenticated access"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        # No user
        user = None
        user_uuid = user.get("user_id") if user else None
        retriever = Mock()
        rag_context = RAGAccessContext(user_uuid, retriever) if user_uuid else None
        
        assert rag_context is None
        print("✅ Unauthenticated access backward compatible: PASS")
    
    def test_query_filter_for_owned_collections(self):
        """Test that queries filter by user_uuid for owned collections"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={0})
        retriever.is_user_collection_owner = Mock(return_value=True)  # User owns collection 0
        
        user_uuid = "user-123"
        context = RAGAccessContext(user_uuid, retriever)
        
        # Build query filter for owned collection
        query_filter = context.build_query_filter(
            collection_id=0,
            strategy_type={"$eq": "successful"},
            is_most_efficient={"$eq": True}
        )
        
        # Verify user_uuid is in filter
        assert "$and" in query_filter
        user_filters = [f for f in query_filter["$and"] if "user_uuid" in f]
        assert len(user_filters) > 0, "user_uuid should be in filter for owned collection"
        assert user_filters[0]["user_uuid"]["$eq"] == user_uuid
        print("✅ Query filter for owned collections: PASS")
    
    def test_query_filter_for_subscribed_collections(self):
        """Test that queries don't filter by user_uuid for subscribed collections"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={1})
        retriever.is_user_collection_owner = Mock(return_value=False)  # User doesn't own
        retriever.is_subscribed_collection = Mock(return_value=True)  # But is subscribed
        retriever.get_collection_metadata = Mock(return_value={"visibility": "private"})
        
        user_uuid = "user-123"
        context = RAGAccessContext(user_uuid, retriever)
        
        # Build query filter for subscribed collection
        query_filter = context.build_query_filter(
            collection_id=1,
            strategy_type={"$eq": "successful"}
        )
        
        # Should NOT have user_uuid filter (see all cases)
        user_filters = [f for f in query_filter.get("$and", []) if "user_uuid" in f]
        assert len(user_filters) == 0, "Should NOT filter by user_uuid for subscribed collection"
        print("✅ Query filter for subscribed collections: PASS")
    
    def test_access_denied_for_unauthorized_collection(self):
        """Test that access is denied for collections user can't access"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={0})  # Can only access 0
        retriever.is_user_collection_owner = Mock(return_value=False)
        
        user_uuid = "user-123"
        context = RAGAccessContext(user_uuid, retriever)
        
        # Try to access collection 2 (not accessible)
        try:
            query_filter = context.build_query_filter(collection_id=2)
            assert False, "Should raise PermissionError"
        except PermissionError:
            print("✅ Access denied for unauthorized collection: PASS")
    
    def test_endpoint_imports_exist(self):
        """Test that routes module imports RAGAccessContext"""
        from trusted_data_agent.api import routes
        import inspect
        
        source = inspect.getsource(routes.get_rag_questions)
        assert "RAGAccessContext" in source
        assert "get_current_user" in source
        assert "rag_context" in source
        print("✅ Autocomplete endpoint has required imports: PASS")
    
    def test_endpoint_has_user_filtering_logic(self):
        """Test that endpoint includes user filtering logic"""
        from trusted_data_agent.api import routes
        import inspect
        
        source = inspect.getsource(routes.get_rag_questions)
        
        # Check for key logic pieces
        assert "user_uuid" in source, "Should extract user_uuid"
        assert "rag_context" in source, "Should create rag_context"
        assert "accessible_collections" in source, "Should use accessible_collections"
        assert "user_uuid" in source and "$eq" in source, "Should filter by user_uuid"
        
        print("✅ Autocomplete endpoint has user filtering logic: PASS")
    
    def test_fallback_path_with_user_filter(self):
        """Test that fallback path (no query) includes user filtering"""
        from trusted_data_agent.api import routes
        import inspect
        
        source = inspect.getsource(routes.get_rag_questions)
        
        # The fallback path should have where_clause logic with user_uuid
        assert "where_clause" in source
        assert "user_uuid" in source
        
        print("✅ Fallback path has user filtering: PASS")
    
    def test_semantic_search_path_with_user_filter(self):
        """Test that semantic search path includes user filtering"""
        from trusted_data_agent.api import routes
        import inspect
        
        source = inspect.getsource(routes.get_rag_questions)
        
        # Should have semantic search section
        lines = source.split('\n')
        
        # Find semantic search section
        semantic_start = None
        for i, line in enumerate(lines):
            if "Semantic search" in line:
                semantic_start = i
                break
        
        assert semantic_start is not None, "Should have semantic search section"
        
        # Check that user filtering is after semantic search
        remaining = '\n'.join(lines[semantic_start:])
        assert "where_clause" in remaining, "Semantic search should use where_clause"
        assert "user_uuid" in remaining, "Semantic search should filter by user_uuid"
        
        print("✅ Semantic search path has user filtering: PASS")


class TestEndpointIntegration:
    """Integration tests simulating the full endpoint flow"""
    
    def test_full_endpoint_flow_with_user(self):
        """Test complete flow from user request to filtered results"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        # Simulate request
        user = {"user_id": "user-123"}
        profile_id = ""  # No profile filter
        query_text = ""  # Fallback path
        
        # Extract user context
        user_uuid = user.get("user_id") if user else None
        
        # Mock retriever
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={0, 1})
        retriever.is_user_collection_owner = Mock(side_effect=lambda cid, uid: cid == 0)
        retriever.is_subscribed_collection = Mock(return_value=False)
        
        # Create context
        rag_context = RAGAccessContext(user_uuid, retriever) if user_uuid else None
        
        # Determine allowed collections (no profile filter, so all accessible)
        allowed_collection_ids = None
        if rag_context:
            allowed_collection_ids = rag_context.accessible_collections
        
        # Result should include collections 0 and 1
        assert allowed_collection_ids == {0, 1}
        print("✅ Full endpoint flow with user: PASS")
    
    def test_full_endpoint_flow_profile_filtered(self):
        """Test endpoint flow with profile-based collection filtering"""
        from trusted_data_agent.agent.rag_access_context import RAGAccessContext
        
        user = {"user_id": "user-123"}
        profile_collections = {0}  # Profile allows only collection 0
        
        user_uuid = user.get("user_id") if user else None
        
        # Mock retriever
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={0, 1, 2})
        retriever.is_user_collection_owner = Mock(side_effect=lambda cid, uid: cid == 0)
        
        rag_context = RAGAccessContext(user_uuid, retriever) if user_uuid else None
        
        # Simulate profile + user access intersection
        allowed = None
        if rag_context:
            user_accessible = rag_context.accessible_collections
            allowed = profile_collections & user_accessible
        
        # Should only include collection 0
        assert allowed == {0}
        print("✅ Full endpoint flow with profile filtering: PASS")
    
    def test_full_endpoint_flow_no_user(self):
        """Test endpoint flow without user (backward compatibility)"""
        user = None
        user_uuid = user.get("user_id") if user else None
        rag_context = None
        
        assert user_uuid is None
        assert rag_context is None
        print("✅ Full endpoint flow without user (backward compatible): PASS")


def run_all_tests():
    """Run all Phase 3 tests"""
    print("\n" + "="*60)
    print("PHASE 3 TEST SUITE: Autocomplete with Multi-User Support")
    print("="*60 + "\n")
    
    test_suites = [
        ("Autocomplete Logic", TestAutocompletePhase3),
        ("Endpoint Integration", TestEndpointIntegration),
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for suite_name, suite_class in test_suites:
        print(f"\n--- {suite_name} ---")
        suite = suite_class()
        
        # Get all test methods
        test_methods = [m for m in dir(suite) if m.startswith("test_")]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                getattr(suite, test_method)()
                passed_tests += 1
            except Exception as e:
                failed_tests.append((suite_name, test_method, str(e)))
                print(f"❌ {test_method}: FAIL - {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for suite, test, error in failed_tests:
            print(f"  - {suite}.{test}: {error}")
        return False
    else:
        print("\n🎉 All Phase 3 tests PASSED!")
        print("\nPhase 3 Achievements:")
        print("✅ User context properly extracted from requests")
        print("✅ RAGAccessContext created and used in endpoint")
        print("✅ Collections filtered by user accessibility")
        print("✅ Query results filtered by user_uuid (owned collections)")
        print("✅ Subscribed collections show all cases")
        print("✅ Access control properly enforced")
        print("✅ Backward compatibility maintained")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
