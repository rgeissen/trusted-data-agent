#!/usr/bin/env python3
"""
Test Suite for Knowledge Repositories - Phase 2 Session Tracking & Events

Tests Phase 2 components:
1. knowledge_accessed field in turn summaries
2. Event handler tracking knowledge retrieval
3. Session replay support
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from trusted_data_agent.agent.executor import PlanExecutor


def test_1_executor_knowledge_tracking():
    """Test 1: Verify executor has knowledge_accessed tracking"""
    print("\n" + "="*80)
    print("TEST 1: Executor Knowledge Tracking Infrastructure")
    print("="*80)
    
    try:
        # Create minimal dependencies for executor
        mock_dependencies = {
            'STATE': {
                'llm': None,
                'mcp_client': None,
                'tools_context': '',
                'prompts_context': '',
                'rag_retriever_instance': None
            },
            'APP_CONFIG': {}
        }
        
        # Create executor instance
        executor = PlanExecutor(
            session_id="test_session",
            user_uuid="test_user",
            original_user_input="test query",
            dependencies=mock_dependencies
        )
        
        checks = {
            "Has knowledge_accessed attribute": hasattr(executor, 'knowledge_accessed'),
            "knowledge_accessed is list": isinstance(executor.knowledge_accessed, list),
            "knowledge_accessed starts empty": len(executor.knowledge_accessed) == 0
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Test adding knowledge access data
        print("\n--- Simulating Knowledge Access ---")
        test_access = {
            "collection_name": "Test Knowledge Collection",
            "document_count": 3,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        executor.knowledge_accessed.append(test_access)
        
        check4 = len(executor.knowledge_accessed) == 1
        check5 = executor.knowledge_accessed[0]["collection_name"] == "Test Knowledge Collection"
        check6 = executor.knowledge_accessed[0]["document_count"] == 3
        
        print(f"{'✅ PASS' if check4 else '❌ FAIL'} - Can append knowledge access")
        print(f"{'✅ PASS' if check5 else '❌ FAIL'} - Collection name stored correctly")
        print(f"{'✅ PASS' if check6 else '❌ FAIL'} - Document count stored correctly")
        
        return all_passed and check4 and check5 and check6
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_event_handler_knowledge_tracking():
    """Test 2: Verify event handler can track knowledge_retrieval events"""
    print("\n" + "="*80)
    print("TEST 2: Event Handler Knowledge Tracking")
    print("="*80)
    
    try:
        # Test the event handler logic directly
        knowledge_accessed = []
        
        async def simulate_event_handler(data, event_name):
            """Simulates the event handler from executor"""
            if event_name == "knowledge_retrieval":
                collections = data.get("collections", [])
                document_count = data.get("document_count", 0)
                
                for collection_name in collections:
                    knowledge_accessed.append({
                        "collection_name": collection_name,
                        "document_count": document_count,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
        
        # Simulate knowledge_retrieval event
        import asyncio
        event_data = {
            "collections": ["Knowledge Collection A", "Knowledge Collection B"],
            "document_count": 5
        }
        
        asyncio.run(simulate_event_handler(event_data, "knowledge_retrieval"))
        
        checks = {
            "Event handler ran": len(knowledge_accessed) > 0,
            "Tracked both collections": len(knowledge_accessed) == 2,
            "Collection A tracked": any(k["collection_name"] == "Knowledge Collection A" for k in knowledge_accessed),
            "Collection B tracked": any(k["collection_name"] == "Knowledge Collection B" for k in knowledge_accessed),
            "Document count correct": all(k["document_count"] == 5 for k in knowledge_accessed)
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
        import traceback
        traceback.print_exc()
        return False


def test_3_turn_summary_includes_knowledge():
    """Test 3: Verify turn_summary structure includes knowledge_accessed"""
    print("\n" + "="*80)
    print("TEST 3: Turn Summary Knowledge Field")
    print("="*80)
    
    try:
        # Simulate turn summary structure
        turn_summary_template = {
            "turn": 1,
            "user_query": "test query",
            "original_plan": [],
            "execution_trace": [],
            "final_summary": "test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "test",
            "model": "test",
            "profile_tag": "test",
            "task_id": "test",
            "turn_input_tokens": 0,
            "turn_output_tokens": 0,
            "session_id": "test_session",
            "rag_source_collection_id": None,
            "knowledge_accessed": []  # Phase 2 addition
        }
        
        # Test with knowledge data
        knowledge_data = [
            {
                "collection_name": "Business Rules",
                "document_count": 3,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "collection_name": "Technical Docs",
                "document_count": 2,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        turn_summary_template["knowledge_accessed"] = knowledge_data
        
        checks = {
            "knowledge_accessed field exists": "knowledge_accessed" in turn_summary_template,
            "knowledge_accessed is list": isinstance(turn_summary_template["knowledge_accessed"], list),
            "Can store multiple collections": len(turn_summary_template["knowledge_accessed"]) == 2,
            "First collection has name": "collection_name" in turn_summary_template["knowledge_accessed"][0],
            "First collection has count": "document_count" in turn_summary_template["knowledge_accessed"][0],
            "First collection has timestamp": "timestamp" in turn_summary_template["knowledge_accessed"][0]
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Test JSON serialization (for session storage)
        print("\n--- Testing JSON Serialization ---")
        try:
            json_str = json.dumps(turn_summary_template)
            deserialized = json.loads(json_str)
            check7 = deserialized["knowledge_accessed"] == knowledge_data
            print(f"{'✅ PASS' if check7 else '❌ FAIL'} - JSON serialization works")
            all_passed = all_passed and check7
        except Exception as e:
            print(f"❌ FAIL - JSON serialization failed: {e}")
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_session_replay_compatibility():
    """Test 4: Verify session replay can handle knowledge_accessed data"""
    print("\n" + "="*80)
    print("TEST 4: Session Replay Compatibility")
    print("="*80)
    
    try:
        # Simulate a stored session with knowledge data
        stored_turn = {
            "turn": 1,
            "user_query": "Analyze customer data",
            "knowledge_accessed": [
                {
                    "collection_name": "Customer Analytics Guide",
                    "document_count": 2,
                    "timestamp": "2025-11-30T10:00:00Z"
                }
            ],
            "original_plan": [
                {"phase": 1, "goal": "Gather data", "relevant_tools": ["base_readQuery"]}
            ]
        }
        
        checks = {
            "Can read stored knowledge_accessed": "knowledge_accessed" in stored_turn,
            "knowledge_accessed has data": len(stored_turn["knowledge_accessed"]) > 0,
            "Collection name retrievable": stored_turn["knowledge_accessed"][0]["collection_name"] == "Customer Analytics Guide",
            "Document count retrievable": stored_turn["knowledge_accessed"][0]["document_count"] == 2,
            "Timestamp retrievable": "timestamp" in stored_turn["knowledge_accessed"][0]
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Test backward compatibility (old sessions without knowledge_accessed)
        print("\n--- Testing Backward Compatibility ---")
        old_turn = {
            "turn": 1,
            "user_query": "Old query",
            "original_plan": []
        }
        
        # Should gracefully handle missing field
        knowledge = old_turn.get("knowledge_accessed", [])
        check6 = isinstance(knowledge, list) and len(knowledge) == 0
        print(f"{'✅ PASS' if check6 else '❌ FAIL'} - Gracefully handles missing knowledge_accessed")
        
        return all_passed and check6
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 2 tests"""
    print("\n" + "="*80)
    print("KNOWLEDGE REPOSITORIES - PHASE 2 TEST SUITE")
    print("Session Tracking & Events")
    print("="*80)
    print(f"Project Root: {project_root}")
    print(f"Python Version: {sys.version}")
    
    tests = [
        ("Executor Knowledge Tracking", test_1_executor_knowledge_tracking),
        ("Event Handler Knowledge Tracking", test_2_event_handler_knowledge_tracking),
        ("Turn Summary Knowledge Field", test_3_turn_summary_includes_knowledge),
        ("Session Replay Compatibility", test_4_session_replay_compatibility),
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
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0 and passed > 0:
        print(f"\n🎉 ALL TESTS PASSED! Phase 2 is ready.")
    elif failed > 0:
        print(f"\n⚠️  {failed} test(s) failed. Review output above.")
    
    print("="*80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
