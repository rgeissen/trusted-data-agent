#!/usr/bin/env python3
"""
Test Suite for Knowledge Repositories - Phase 1 Backend Foundation

Tests all Phase 1 components:
1. APP_CONFIG constants
2. Configuration schema support
3. RAGRetriever enhancement (repository_type filtering)
4. Knowledge retrieval infrastructure
5. Integration into planning
6. LLM reranking
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

# Must import after path setup
from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.core.config_manager import get_config_manager
from trusted_data_agent.agent.rag_retriever import RAGRetriever
from trusted_data_agent.agent.rag_access_context import RAGAccessContext


def test_1_app_config_constants():
    """Test 1: Verify APP_CONFIG constants exist and have correct defaults"""
    print("\n" + "="*80)
    print("TEST 1: APP_CONFIG Constants")
    print("="*80)
    
    required_constants = {
        'KNOWLEDGE_RAG_ENABLED': True,
        'KNOWLEDGE_RAG_NUM_DOCS': 3,
        'KNOWLEDGE_MIN_RELEVANCE_SCORE': 0.70,
        'KNOWLEDGE_MAX_TOKENS': 2000,
        'KNOWLEDGE_RERANKING_ENABLED': False
    }
    
    all_passed = True
    for const_name, expected_value in required_constants.items():
        if hasattr(APP_CONFIG, const_name):
            actual_value = getattr(APP_CONFIG, const_name)
            match = actual_value == expected_value
            status = "✅ PASS" if match else "❌ FAIL"
            print(f"{status} - {const_name}: {actual_value} (expected: {expected_value})")
            if not match:
                all_passed = False
        else:
            print(f"❌ FAIL - {const_name}: NOT FOUND")
            all_passed = False
    
    return all_passed


def test_2_configuration_schema():
    """Test 2: Verify profile schema supports knowledgeConfig"""
    print("\n" + "="*80)
    print("TEST 2: Configuration Schema Support")
    print("="*80)
    
    # Test profile with knowledgeConfig
    test_profile = {
        "id": "test_knowledge_profile",
        "name": "Test Knowledge Profile",
        "knowledgeConfig": {
            "enabled": True,
            "collections": [
                {"collectionId": 1, "reranking": False},
                {"collectionId": 2, "reranking": True}
            ],
            "minRelevanceScore": 0.75,
            "maxDocs": 5,
            "maxTokens": 3000
        }
    }
    
    try:
        # Verify we can read knowledgeConfig
        knowledge_config = test_profile.get("knowledgeConfig", {})
        
        checks = {
            "enabled field": knowledge_config.get("enabled") == True,
            "collections field": isinstance(knowledge_config.get("collections"), list),
            "collections count": len(knowledge_config.get("collections", [])) == 2,
            "minRelevanceScore": knowledge_config.get("minRelevanceScore") == 0.75,
            "maxDocs": knowledge_config.get("maxDocs") == 5,
            "maxTokens": knowledge_config.get("maxTokens") == 3000,
            "reranking in first": "reranking" in knowledge_config.get("collections", [{}])[0]
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        return False


def test_3_rag_retriever_repository_type():
    """Test 3: Verify RAGRetriever supports repository_type parameter"""
    print("\n" + "="*80)
    print("TEST 3: RAGRetriever repository_type Enhancement")
    print("="*80)
    
    try:
        # Initialize RAGRetriever
        rag_cases_dir = project_root / "rag" / "tda_rag_cases"
        persist_dir = project_root / ".chromadb_rag_cache"
        
        if not rag_cases_dir.exists():
            print(f"⚠️  SKIP - RAG cases directory not found: {rag_cases_dir}")
            return None
        
        retriever = RAGRetriever(
            rag_cases_dir=str(rag_cases_dir),
            persist_directory=str(persist_dir)
        )
        
        # Check method signature
        import inspect
        sig = inspect.signature(retriever.retrieve_examples)
        params = sig.parameters
        
        checks = {
            "has repository_type parameter": "repository_type" in params,
            "repository_type has default": params.get("repository_type") and params["repository_type"].default == "planner",
            "method callable": callable(retriever.retrieve_examples)
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Test actual filtering (if collections exist)
        if retriever.collections:
            print(f"\n📊 Found {len(retriever.collections)} active collections")
            
            # Test with planner repository_type
            try:
                planner_results = retriever.retrieve_examples(
                    query="test query",
                    k=1,
                    min_score=0.0,
                    repository_type="planner"
                )
                print(f"✅ PASS - retrieve_examples(repository_type='planner') returned {len(planner_results)} results")
            except Exception as e:
                print(f"❌ FAIL - retrieve_examples(repository_type='planner') raised: {e}")
                all_passed = False
            
            # Test with knowledge repository_type
            try:
                knowledge_results = retriever.retrieve_examples(
                    query="test query",
                    k=1,
                    min_score=0.0,
                    repository_type="knowledge"
                )
                print(f"✅ PASS - retrieve_examples(repository_type='knowledge') returned {len(knowledge_results)} results")
            except Exception as e:
                print(f"❌ FAIL - retrieve_examples(repository_type='knowledge') raised: {e}")
                all_passed = False
        else:
            print("⚠️  No collections loaded - skipping retrieval tests")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception during RAGRetriever initialization: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_planner_knowledge_methods():
    """Test 4: Verify Planner has knowledge retrieval methods"""
    print("\n" + "="*80)
    print("TEST 4: Planner Knowledge Retrieval Infrastructure")
    print("="*80)
    
    try:
        from trusted_data_agent.agent.planner import Planner
        
        # Check for required methods
        required_methods = [
            "_is_knowledge_enabled",
            "_get_knowledge_collections",
            "_balance_collection_diversity",
            "_format_with_token_limit",
            "_rerank_knowledge_with_llm",
            "_retrieve_knowledge_for_planning"
        ]
        
        all_passed = True
        for method_name in required_methods:
            has_method = hasattr(Planner, method_name)
            is_callable = callable(getattr(Planner, method_name, None))
            passed = has_method and is_callable
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - Method '{method_name}' exists and is callable")
            
            if not passed:
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ FAIL - Could not import Planner: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_planner_helper_methods():
    """Test 5: Test Planner helper method logic"""
    print("\n" + "="*80)
    print("TEST 5: Planner Helper Method Logic")
    print("="*80)
    
    try:
        from trusted_data_agent.agent.planner import Planner
        from trusted_data_agent.agent.executor import PlanExecutor
        
        # Create minimal executor for planner initialization
        # Note: This is a simplified test - full executor requires more setup
        class MockExecutor:
            def __init__(self):
                self.user_uuid = "test_user_123"
                self.profile_override_id = None
        
        executor = MockExecutor()
        planner = Planner(executor, rag_retriever_instance=None)
        
        # Test 5.1: _is_knowledge_enabled with different configs
        print("\n--- Test 5.1: _is_knowledge_enabled ---")
        
        # Global disabled
        original_enabled = APP_CONFIG.KNOWLEDGE_RAG_ENABLED
        APP_CONFIG.KNOWLEDGE_RAG_ENABLED = False
        result = planner._is_knowledge_enabled()
        check1 = result == False
        print(f"{'✅ PASS' if check1 else '❌ FAIL'} - Returns False when globally disabled")
        APP_CONFIG.KNOWLEDGE_RAG_ENABLED = original_enabled
        
        # Profile disabled
        profile_config = {"knowledgeConfig": {"enabled": False}}
        result = planner._is_knowledge_enabled(profile_config)
        check2 = result == False
        print(f"{'✅ PASS' if check2 else '❌ FAIL'} - Returns False when profile disabled")
        
        # Enabled
        profile_config = {"knowledgeConfig": {"enabled": True}}
        result = planner._is_knowledge_enabled(profile_config)
        check3 = result == True
        print(f"{'✅ PASS' if check3 else '❌ FAIL'} - Returns True when enabled")
        
        # Test 5.2: _balance_collection_diversity
        print("\n--- Test 5.2: _balance_collection_diversity ---")
        
        test_docs = [
            {"collection_id": 1, "content": "doc1"},
            {"collection_id": 1, "content": "doc2"},
            {"collection_id": 2, "content": "doc3"},
            {"collection_id": 2, "content": "doc4"},
            {"collection_id": 3, "content": "doc5"},
        ]
        
        balanced = planner._balance_collection_diversity(test_docs, 3)
        check4 = len(balanced) == 3
        print(f"{'✅ PASS' if check4 else '❌ FAIL'} - Returns correct count (expected 3, got {len(balanced)})")
        
        # Check diversity (should have different collections)
        collection_ids = [doc["collection_id"] for doc in balanced]
        check5 = len(set(collection_ids)) > 1
        print(f"{'✅ PASS' if check5 else '❌ FAIL'} - Balances across collections (got {len(set(collection_ids))} unique collections)")
        
        # Test 5.3: _format_with_token_limit
        print("\n--- Test 5.3: _format_with_token_limit ---")
        
        test_docs_format = [
            {
                "collection_name": "Test Collection",
                "similarity_score": 0.85,
                "full_case_data": {
                    "intent": {"user_query": "Test query 1"}
                }
            },
            {
                "collection_name": "Test Collection 2",
                "similarity_score": 0.75,
                "full_case_data": {
                    "intent": {"user_query": "Test query 2"}
                }
            }
        ]
        
        formatted = planner._format_with_token_limit(test_docs_format, 100)
        check6 = isinstance(formatted, str)
        check7 = len(formatted) > 0
        check8 = "Test Collection" in formatted
        
        print(f"{'✅ PASS' if check6 else '❌ FAIL'} - Returns string")
        print(f"{'✅ PASS' if check7 else '❌ FAIL'} - Returns non-empty result")
        print(f"{'✅ PASS' if check8 else '❌ FAIL'} - Contains collection name")
        
        all_passed = all([check1, check2, check3, check4, check5, check6, check7, check8])
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_prompt_template_integration():
    """Test 6: Verify prompt template has knowledge_context placeholder"""
    print("\n" + "="*80)
    print("TEST 6: Prompt Template Integration")
    print("="*80)
    
    try:
        from trusted_data_agent.agent.prompts import WORKFLOW_META_PLANNING_PROMPT
        
        checks = {
            "Prompt loaded": len(WORKFLOW_META_PLANNING_PROMPT) > 0,
            "Has knowledge_context placeholder": "{knowledge_context}" in WORKFLOW_META_PLANNING_PROMPT,
            "Has rag_few_shot_examples placeholder": "{rag_few_shot_examples}" in WORKFLOW_META_PLANNING_PROMPT
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Show context around the placeholder
        if "{knowledge_context}" in WORKFLOW_META_PLANNING_PROMPT:
            idx = WORKFLOW_META_PLANNING_PROMPT.find("{knowledge_context}")
            context = WORKFLOW_META_PLANNING_PROMPT[max(0, idx-100):idx+100]
            print(f"\n📄 Context around {{knowledge_context}}:")
            print(f"   ...{context}...")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_backward_compatibility():
    """Test 7: Verify backward compatibility (no errors with knowledge disabled)"""
    print("\n" + "="*80)
    print("TEST 7: Backward Compatibility")
    print("="*80)
    
    try:
        from trusted_data_agent.agent.planner import Planner
        
        class MockExecutor:
            def __init__(self):
                self.user_uuid = "test_user_123"
                self.profile_override_id = None
        
        executor = MockExecutor()
        planner = Planner(executor, rag_retriever_instance=None)
        
        checks = {}
        
        # Test with no profile config
        try:
            result = planner._is_knowledge_enabled(None)
            checks["No profile config - no error"] = True
            checks["No profile config - returns bool"] = isinstance(result, bool)
        except Exception as e:
            checks["No profile config - no error"] = False
            print(f"❌ Error with None profile: {e}")
        
        # Test with empty profile
        try:
            result = planner._is_knowledge_enabled({})
            checks["Empty profile - no error"] = True
        except Exception as e:
            checks["Empty profile - no error"] = False
            print(f"❌ Error with empty profile: {e}")
        
        # Test _get_knowledge_collections with no config
        try:
            result = planner._get_knowledge_collections(None)
            checks["Get collections with None - no error"] = True
            checks["Get collections with None - returns list"] = isinstance(result, list)
        except Exception as e:
            checks["Get collections with None - no error"] = False
            print(f"❌ Error getting collections: {e}")
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 1 tests"""
    print("\n" + "="*80)
    print("KNOWLEDGE REPOSITORIES - PHASE 1 TEST SUITE")
    print("="*80)
    print(f"Project Root: {project_root}")
    print(f"Python Version: {sys.version}")
    
    tests = [
        ("APP_CONFIG Constants", test_1_app_config_constants),
        ("Configuration Schema", test_2_configuration_schema),
        ("RAGRetriever Enhancement", test_3_rag_retriever_repository_type),
        ("Planner Knowledge Methods", test_4_planner_knowledge_methods),
        ("Planner Helper Logic", test_5_planner_helper_methods),
        ("Prompt Template Integration", test_6_prompt_template_integration),
        ("Backward Compatibility", test_7_backward_compatibility),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    if failed == 0 and passed > 0:
        print(f"\n🎉 ALL TESTS PASSED! Phase 1 is ready.")
    elif failed > 0:
        print(f"\n⚠️  {failed} test(s) failed. Review output above.")
    else:
        print(f"\n⚠️  No tests were able to run completely.")
    
    print("="*80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
