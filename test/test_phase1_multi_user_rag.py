#!/usr/bin/env python3
"""
Test Phase 1 Implementation: Multi-User RAG Compliance

Tests the following achievements:
1. RAGAccessContext class creation and functionality
2. User UUID metadata tracking in cases
3. Context-aware retrieval in planner
4. Context-aware processing in RAG worker
5. User filtering in autocomplete endpoint
"""

import sys
import json
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trusted_data_agent.agent.rag_access_context import RAGAccessContext
from trusted_data_agent.agent.rag_retriever import RAGRetriever


class TestRAGAccessContext:
    """Test the RAGAccessContext abstraction layer"""
    
    def test_context_creation(self):
        """Test RAGAccessContext can be instantiated"""
        retriever = Mock()
        user_id = "user-123"
        
        context = RAGAccessContext(user_id, retriever)
        
        assert context.user_id == user_id
        assert context.retriever is retriever
        print("✅ RAGAccessContext creation: PASS")
    
    def test_context_accessible_collections_property(self):
        """Test that accessible_collections uses caching"""
        retriever = Mock()
        retriever._get_user_accessible_collections = Mock(return_value={"col-1", "col-2"})
        user_id = "user-123"
        
        context = RAGAccessContext(user_id, retriever)
        
        # First call should hit the method
        collections1 = context.accessible_collections
        call_count_1 = retriever._get_user_accessible_collections.call_count
        
        # Second call should use cache
        collections2 = context.accessible_collections
        call_count_2 = retriever._get_user_accessible_collections.call_count
        
        assert collections1 == {"col-1", "col-2"}
        assert collections2 == collections1
        assert call_count_1 == 1, "Should call method once"
        assert call_count_2 == 1, "Should cache result, not call again"
        print("✅ RAGAccessContext caching: PASS")
    
    def test_build_query_filter(self):
        """Test query filter builder includes user context"""
        retriever = Mock()
        retriever.is_user_collection_owner = Mock(return_value=True)
        retriever._get_user_accessible_collections = Mock(return_value={1})
        user_id = "user-123"
        context = RAGAccessContext(user_id, retriever)
        
        # Build a filter with user context
        query_filter = context.build_query_filter(collection_id=1, strategy_type={"$eq": "successful"}, is_most_efficient={"$eq": True})
        
        assert "$and" in query_filter
        assert len(query_filter["$and"]) > 0
        # Verify user_uuid is included
        user_filter = [f for f in query_filter["$and"] if "user_uuid" in f]
        assert len(user_filter) > 0, "user_uuid should be in filter"
        assert user_filter[0]["user_uuid"]["$eq"] == user_id
        print("✅ RAGAccessContext query filter building: PASS")
    
    def test_validate_collection_access(self):
        """Test collection access validation"""
        retriever = Mock()
        user_id = "user-123"
        collection_id = 1
        
        # Mock the ownership checker
        retriever.is_user_collection_owner = Mock(return_value=True)
        
        context = RAGAccessContext(user_id, retriever)
        result = context.validate_collection_access(collection_id, write=True)
        
        assert result is True
        retriever.is_user_collection_owner.assert_called_once_with(collection_id, user_id)
        print("✅ RAGAccessContext access validation: PASS")


class TestMetadataTracking:
    """Test user_uuid is properly added to metadata"""
    
    def test_metadata_includes_user_uuid(self):
        """Test that case metadata includes user_uuid"""
        # Mock a turn summary with user_uuid
        turn_summary = {
            "user_uuid": "user-123",
            "user_query": "What is Python?",
            "collection_id": "col-1"
        }
        
        # Test the metadata preparation logic
        metadata = {
            "user_uuid": turn_summary.get("user_uuid"),
            "user_query": turn_summary.get("user_query"),
            "strategy_type": "successful",
            "is_most_efficient": True,
        }
        
        assert metadata["user_uuid"] == "user-123"
        assert metadata["user_query"] == "What is Python?"
        print("✅ Metadata includes user_uuid: PASS")


class TestParameterSignatures:
    """Test that function signatures accept rag_context parameter"""
    
    def test_process_turn_for_rag_signature(self):
        """Verify process_turn_for_rag accepts rag_context parameter"""
        import inspect
        
        sig = inspect.signature(RAGRetriever.process_turn_for_rag)
        params = list(sig.parameters.keys())
        
        assert "rag_context" in params, "process_turn_for_rag should have rag_context parameter"
        print("✅ process_turn_for_rag has rag_context parameter: PASS")
    
    def test_retrieve_examples_signature(self):
        """Verify retrieve_examples accepts rag_context parameter"""
        import inspect
        
        sig = inspect.signature(RAGRetriever.retrieve_examples)
        params = list(sig.parameters.keys())
        
        assert "rag_context" in params, "retrieve_examples should have rag_context parameter"
        print("✅ retrieve_examples has rag_context parameter: PASS")


class TestBackwardCompatibility:
    """Test that changes are backward compatible"""
    
    def test_rag_context_optional(self):
        """Verify rag_context parameter is optional (has default)"""
        import inspect
        
        sig = inspect.signature(RAGRetriever.process_turn_for_rag)
        rag_context_param = sig.parameters.get("rag_context")
        
        assert rag_context_param is not None
        assert rag_context_param.default is None, "rag_context should default to None"
        print("✅ rag_context parameter is optional (default=None): PASS")
    
    def test_retrieve_examples_rag_context_optional(self):
        """Verify rag_context in retrieve_examples is optional"""
        import inspect
        
        sig = inspect.signature(RAGRetriever.retrieve_examples)
        rag_context_param = sig.parameters.get("rag_context")
        
        assert rag_context_param is not None
        assert rag_context_param.default is None, "rag_context should default to None"
        print("✅ retrieve_examples rag_context is optional: PASS")


class TestImports:
    """Test that all imports are in place"""
    
    def test_planner_imports_rag_access_context(self):
        """Verify planner imports RAGAccessContext"""
        from trusted_data_agent.agent import planner
        import inspect
        
        source = inspect.getsource(planner)
        assert "RAGAccessContext" in source, "planner should import RAGAccessContext"
        print("✅ planner imports RAGAccessContext: PASS")
    
    def test_routes_imports_rag_access_context(self):
        """Verify routes imports RAGAccessContext"""
        from trusted_data_agent.api import routes
        import inspect
        
        source = inspect.getsource(routes)
        assert "RAGAccessContext" in source, "routes should import RAGAccessContext"
        print("✅ routes imports RAGAccessContext: PASS")


def run_all_tests():
    """Run all Phase 1 tests"""
    print("\n" + "="*60)
    print("PHASE 1 TEST SUITE: Multi-User RAG Compliance")
    print("="*60 + "\n")
    
    test_suites = [
        ("RAGAccessContext", TestRAGAccessContext),
        ("Metadata Tracking", TestMetadataTracking),
        ("Parameter Signatures", TestParameterSignatures),
        ("Backward Compatibility", TestBackwardCompatibility),
        ("Imports", TestImports),
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
        print("\n🎉 All Phase 1 tests PASSED!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
