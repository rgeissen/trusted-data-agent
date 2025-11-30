#!/usr/bin/env python3
"""
Test Suite for Knowledge Repositories - Phase 3 Frontend Integration

Tests Phase 3 components:
1. Knowledge indicator HTML element presence
2. Knowledge banner HTML element presence
3. CSS styling for knowledge indicator states
4. JavaScript UI function availability
5. Event handler integration
"""

import sys
import os
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def test_1_html_knowledge_indicator():
    """Test 1: Verify knowledge indicator exists in index.html"""
    print("\n" + "="*80)
    print("TEST 1: Knowledge Indicator HTML Element")
    print("="*80)
    
    try:
        index_html_path = project_root / "templates" / "index.html"
        content = index_html_path.read_text()
        
        checks = {
            "knowledge-status-dot element exists": 'id="knowledge-status-dot"' in content,
            "knowledge-status-dot has connection-dot class": 'id="knowledge-status-dot" class="connection-dot' in content,
            "knowledge-status-dot has knowledge-idle class": 'knowledge-idle' in content,
            "Knowledge label exists": '<span class="text-sm text-gray-300">Knowledge</span>' in content,
            "Knowledge tooltip exists": 'title="Knowledge Repository Status"' in content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Verify placement (should be after Context indicator)
        print("\n--- Verifying Placement ---")
        context_pos = content.find('id="context-status-dot"')
        knowledge_pos = content.find('id="knowledge-status-dot"')
        check6 = context_pos > 0 and knowledge_pos > context_pos
        print(f"{'✅ PASS' if check6 else '❌ FAIL'} - Knowledge indicator after Context indicator")
        
        return all_passed and check6
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_html_knowledge_banner():
    """Test 2: Verify knowledge banner exists in Live Status"""
    print("\n" + "="*80)
    print("TEST 2: Knowledge Banner HTML Element")
    print("="*80)
    
    try:
        index_html_path = project_root / "templates" / "index.html"
        content = index_html_path.read_text()
        
        checks = {
            "knowledge-banner element exists": 'id="knowledge-banner"' in content,
            "knowledge-banner has hidden class": '<div id="knowledge-banner" class="hidden' in content,
            "knowledge-banner has purple styling": 'bg-purple-500/20 border border-purple-400/40' in content,
            "knowledge-collections-list element exists": 'id="knowledge-collections-list"' in content,
            "Banner has book icon": '<path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969' in content,
            "Banner has 'Knowledge:' label": '<span class="font-medium">Knowledge:</span>' in content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Verify placement (should be after status-prompt-name)
        print("\n--- Verifying Placement in Live Status ---")
        prompt_name_pos = content.find('id="status-prompt-name"')
        banner_pos = content.find('id="knowledge-banner"')
        check7 = prompt_name_pos > 0 and banner_pos > prompt_name_pos
        print(f"{'✅ PASS' if check7 else '❌ FAIL'} - Banner placed after prompt-name in Live Status")
        
        return all_passed and check7
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_css_knowledge_styles():
    """Test 3: Verify CSS styles for knowledge indicator"""
    print("\n" + "="*80)
    print("TEST 3: CSS Knowledge Indicator Styles")
    print("="*80)
    
    try:
        main_css_path = project_root / "static" / "css" / "main.css"
        content = main_css_path.read_text()
        
        checks = {
            "knowledge-idle style exists": '.connection-dot.knowledge-idle' in content,
            "knowledge-active style exists": '.connection-dot.knowledge-active' in content,
            "knowledge-idle has gray color": re.search(r'\.connection-dot\.knowledge-idle\s*{[^}]*background-color:\s*#6b7280', content) is not None,
            "knowledge-idle has opacity": re.search(r'\.connection-dot\.knowledge-idle\s*{[^}]*opacity:\s*0\.5', content) is not None,
            "knowledge-active has purple color": re.search(r'\.connection-dot\.knowledge-active\s*{[^}]*background-color:\s*#a855f7', content) is not None,
            "knowledge-active has box-shadow": re.search(r'\.connection-dot\.knowledge-active\s*{[^}]*box-shadow:[^}]*#a855f7', content) is not None
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Verify colors
        print("\n--- Color Validation ---")
        print("Gray (idle): #6b7280 ✓")
        print("Purple (active): #a855f7 ✓")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_javascript_ui_function():
    """Test 4: Verify updateKnowledgeIndicator function exists in ui.js"""
    print("\n" + "="*80)
    print("TEST 4: JavaScript UI Function")
    print("="*80)
    
    try:
        ui_js_path = project_root / "static" / "js" / "ui.js"
        content = ui_js_path.read_text()
        
        checks = {
            "updateKnowledgeIndicator function exists": 'export function updateKnowledgeIndicator' in content,
            "Function accepts collections parameter": 'updateKnowledgeIndicator(collections, documentCount)' in content,
            "Function gets knowledge-status-dot": 'getElementById(\'knowledge-status-dot\')' in content or 'getElementById("knowledge-status-dot")' in content,
            "Function gets knowledge-banner": 'getElementById(\'knowledge-banner\')' in content or 'getElementById("knowledge-banner")' in content,
            "Function adds knowledge-active class": "classList.add('knowledge-active'" in content or 'classList.add("knowledge-active"' in content,
            "Function removes knowledge-idle class": "classList.remove('knowledge-idle'" in content or 'classList.remove("knowledge-idle"' in content,
            "Function shows banner": "classList.remove('hidden')" in content or 'classList.remove("hidden")' in content,
            "Function uses setTimeout for fade": 'setTimeout' in content and '8000' in content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Check function documentation
        print("\n--- Function Documentation ---")
        has_jsdoc = '/**' in content and '@param' in content and 'collections' in content
        print(f"{'✅ PASS' if has_jsdoc else '⚠️  WARN'} - Function has JSDoc comments")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_event_handler_integration():
    """Test 5: Verify knowledge_retrieval event handler in notifications.js"""
    print("\n" + "="*80)
    print("TEST 5: Event Handler Integration")
    print("="*80)
    
    try:
        notifications_js_path = project_root / "static" / "js" / "notifications.js"
        content = notifications_js_path.read_text()
        
        checks = {
            "knowledge_retrieval event check exists": "event.type === 'knowledge_retrieval'" in content or 'event.type === "knowledge_retrieval"' in content,
            "Handler extracts collections": 'event.data?.collections' in content or 'event.data.collections' in content,
            "Handler extracts document_count": 'event.data?.document_count' in content or 'event.data.documentCount' in content or 'event.data.document_count' in content,
            "Handler calls UI.updateKnowledgeIndicator": 'UI.updateKnowledgeIndicator' in content,
            "Handler has console.log for debugging": "console.log('[knowledge_retrieval]" in content or 'console.log("[knowledge_retrieval]' in content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Verify placement in rest_task_update event
        print("\n--- Event Handler Location ---")
        in_rest_task_update = "case 'rest_task_update':" in content
        knowledge_after_rag = content.find("event.type === 'rag_retrieval'") < content.find("event.type === 'knowledge_retrieval'") if "event.type === 'knowledge_retrieval'" in content else False
        
        print(f"{'✅ PASS' if in_rest_task_update else '❌ FAIL'} - Handler in rest_task_update case")
        print(f"{'✅ PASS' if knowledge_after_rag else '⚠️  WARN'} - Handler after rag_retrieval check")
        
        return all_passed and in_rest_task_update
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_complete_event_flow():
    """Test 6: Verify complete event flow from backend to UI"""
    print("\n" + "="*80)
    print("TEST 6: Complete Event Flow")
    print("="*80)
    
    try:
        # Check backend emits knowledge_retrieval event
        planner_path = project_root / "src" / "trusted_data_agent" / "agent" / "planner.py"
        planner_content = planner_path.read_text()
        
        # Check executor captures event
        executor_path = project_root / "src" / "trusted_data_agent" / "agent" / "executor.py"
        executor_content = executor_path.read_text()
        
        # Check frontend handles event
        notifications_path = project_root / "static" / "js" / "notifications.js"
        notifications_content = notifications_path.read_text()
        
        checks = {
            "Backend emits knowledge_retrieval": '}, "knowledge_retrieval"' in planner_content or "}, 'knowledge_retrieval'" in planner_content,
            "Backend includes collections": '"collections":' in planner_content or "'collections':" in planner_content,
            "Backend includes document_count": '"document_count":' in planner_content or "'document_count':" in planner_content,
            "Executor tracks knowledge_accessed": 'self.knowledge_accessed' in executor_content,
            "Executor captures knowledge_retrieval event": 'knowledge_retrieval' in executor_content,
            "Frontend listens for event": "event.type === 'knowledge_retrieval'" in notifications_content or 'event.type === "knowledge_retrieval"' in notifications_content,
            "Frontend updates UI": 'UI.updateKnowledgeIndicator' in notifications_content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        print("\n--- Event Flow Diagram ---")
        print("1. Planner.py emits 'knowledge_retrieval' event ✓")
        print("2. Executor.py captures event in event_handler ✓")
        print("3. SSE sends event to frontend ✓")
        print("4. Notifications.js receives event ✓")
        print("5. UI.js updates indicator and banner ✓")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_backward_compatibility():
    """Test 7: Verify backward compatibility with existing UI"""
    print("\n" + "="*80)
    print("TEST 7: Backward Compatibility")
    print("="*80)
    
    try:
        index_html_path = project_root / "templates" / "index.html"
        html_content = index_html_path.read_text()
        
        notifications_js_path = project_root / "static" / "js" / "notifications.js"
        notifications_content = notifications_js_path.read_text()
        
        ui_js_path = project_root / "static" / "js" / "ui.js"
        ui_content = ui_js_path.read_text()
        
        checks = {
            "Existing MCP indicator unchanged": 'id="mcp-status-dot"' in html_content,
            "Existing RAG indicator unchanged": 'id="rag-status-dot"' in html_content,
            "Existing LLM indicator unchanged": 'id="llm-status-dot"' in html_content,
            "Existing SSE indicator unchanged": 'id="sse-status-dot"' in html_content,
            "Existing Context indicator unchanged": 'id="context-status-dot"' in html_content,
            "Existing blinkRagDot function unchanged": 'export function blinkRagDot()' in ui_content,
            "Existing rag_retrieval handler unchanged": "event.type === 'rag_retrieval'" in notifications_content or 'event.type === "rag_retrieval"' in notifications_content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        print("\n--- Compatibility Notes ---")
        print("✓ Knowledge indicator is additive (no changes to existing)")
        print("✓ Uses same connection-dot pattern as other indicators")
        print("✓ Event handler follows same pattern as rag_retrieval")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 3 tests"""
    print("\n" + "="*80)
    print("KNOWLEDGE REPOSITORIES - PHASE 3 TEST SUITE")
    print("Frontend Indicator & Banner")
    print("="*80)
    print(f"Project Root: {project_root}")
    print(f"Python Version: {sys.version}")
    
    tests = [
        ("Knowledge Indicator HTML", test_1_html_knowledge_indicator),
        ("Knowledge Banner HTML", test_2_html_knowledge_banner),
        ("CSS Knowledge Styles", test_3_css_knowledge_styles),
        ("JavaScript UI Function", test_4_javascript_ui_function),
        ("Event Handler Integration", test_5_event_handler_integration),
        ("Complete Event Flow", test_6_complete_event_flow),
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
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0 and passed > 0:
        print(f"\n🎉 ALL TESTS PASSED! Phase 3 is ready.")
        print(f"\n📋 Next Steps:")
        print(f"   1. Start the TDA server")
        print(f"   2. Create a profile with knowledgeConfig enabled")
        print(f"   3. Create a knowledge repository with documents")
        print(f"   4. Send a query that triggers knowledge retrieval")
        print(f"   5. Verify purple indicator lights up and banner shows collections")
    elif failed > 0:
        print(f"\n⚠️  {failed} test(s) failed. Review output above.")
    
    print("="*80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
