#!/usr/bin/env python3
"""
Test Suite for Knowledge Repositories - Phase 4 Profile Configuration UI

Tests Phase 4 components:
1. Knowledge Configuration section in profile modal HTML
2. Advanced settings fields (minRelevanceScore, maxDocs, maxTokens)
3. Per-collection reranking toggle elements
4. JavaScript save/load logic for knowledgeConfig
"""

import sys
import os
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def test_1_knowledge_config_section_html():
    """Test 1: Verify Knowledge Configuration section exists in profile modal"""
    print("\n" + "="*80)
    print("TEST 1: Knowledge Configuration Section in Profile Modal")
    print("="*80)
    
    try:
        index_html_path = project_root / "templates" / "index.html"
        content = index_html_path.read_text()
        
        checks = {
            "Knowledge Configuration section exists": 'Knowledge Repository Configuration' in content,
            "Enable Knowledge toggle exists": 'profile-modal-knowledge-enabled' in content,
            "Knowledge config settings container exists": 'knowledge-config-settings' in content,
            "Section has purple/indigo gradient": 'from-purple-900/10 to-indigo-900/10' in content or 'purple-900' in content,
            "Knowledge icon in section": 'text-purple-400' in content and 'Knowledge Repository Configuration' in content
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


def test_2_advanced_settings_fields():
    """Test 2: Verify advanced settings input fields exist"""
    print("\n" + "="*80)
    print("TEST 2: Advanced Settings Input Fields")
    print("="*80)
    
    try:
        index_html_path = project_root / "templates" / "index.html"
        content = index_html_path.read_text()
        
        checks = {
            "Min Relevance Score input exists": 'profile-modal-knowledge-min-relevance' in content,
            "Min Relevance default value 0.70": 'value="0.70"' in content,
            "Min Relevance range (0-1)": 'min="0" max="1"' in content and 'profile-modal-knowledge-min-relevance' in content,
            "Max Documents input exists": 'profile-modal-knowledge-max-docs' in content,
            "Max Docs default value 3": re.search(r'profile-modal-knowledge-max-docs[^>]*value="3"', content) is not None,
            "Max Docs range (1-10)": 'min="1" max="10"' in content and 'profile-modal-knowledge-max-docs' in content,
            "Max Tokens input exists": 'profile-modal-knowledge-max-tokens' in content,
            "Max Tokens default value 2000": 'value="2000"' in content,
            "Max Tokens range (500-5000)": 'min="500" max="5000"' in content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Verify field labels
        print("\n--- Field Labels ---")
        labels = {
            "Min Relevance Score label": 'Min Relevance Score' in content,
            "Max Documents label": 'Max Documents' in content,
            "Max Tokens label": 'Max Tokens' in content
        }
        
        for label_name, passed in labels.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {label_name}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_reranking_toggles_container():
    """Test 3: Verify per-collection reranking toggles container exists"""
    print("\n" + "="*80)
    print("TEST 3: Per-Collection Reranking Toggles Container")
    print("="*80)
    
    try:
        index_html_path = project_root / "templates" / "index.html"
        content = index_html_path.read_text()
        
        checks = {
            "Reranking list container exists": 'profile-modal-knowledge-reranking-list' in content,
            "Reranking section label exists": 'LLM Reranking (Per-Collection)' in content,
            "Reranking description exists": 'Enable LLM-powered reranking' in content or 'reranking for specific collections' in content,
            "Reranking cost warning": 'incurs additional LLM costs' in content or 'additional LLM costs' in content
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


def test_4_javascript_load_logic():
    """Test 4: Verify JavaScript loads knowledgeConfig from profile"""
    print("\n" + "="*80)
    print("TEST 4: JavaScript Load Logic for knowledgeConfig")
    print("="*80)
    
    try:
        config_handler_path = project_root / "static" / "js" / "handlers" / "configurationHandler.js"
        content = config_handler_path.read_text()
        
        checks = {
            "Checks for profile.knowledgeConfig": 'profile?.knowledgeConfig' in content or 'profile.knowledgeConfig' in content,
            "Loads enabled setting": 'knowledgeConfig.enabled' in content,
            "Loads minRelevanceScore": 'knowledgeConfig.minRelevanceScore' in content,
            "Loads maxDocs": 'knowledgeConfig.maxDocs' in content,
            "Loads maxTokens": 'knowledgeConfig.maxTokens' in content,
            "Loads collections with reranking": 'knowledgeConfig.collections' in content or 'knowledgeConfig?.collections' in content,
            "Sets default values": '0.70' in content and (content.count('0.70') >= 2 or 'minRelevanceInput.value = 0.70' in content)
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Check for updateRerankingList function
        print("\n--- Reranking List Management ---")
        has_update_function = 'updateRerankingList' in content
        print(f"{'✅ PASS' if has_update_function else '❌ FAIL'} - updateRerankingList function exists")
        all_passed = all_passed and has_update_function
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_javascript_save_logic():
    """Test 5: Verify JavaScript saves knowledgeConfig to profile"""
    print("\n" + "="*80)
    print("TEST 5: JavaScript Save Logic for knowledgeConfig")
    print("="*80)
    
    try:
        config_handler_path = project_root / "static" / "js" / "handlers" / "configurationHandler.js"
        content = config_handler_path.read_text()
        
        checks = {
            "Reads knowledge enabled toggle": 'profile-modal-knowledge-enabled' in content and '.checked' in content,
            "Reads minRelevance input": 'profile-modal-knowledge-min-relevance' in content and '.value' in content,
            "Reads maxDocs input": 'profile-modal-knowledge-max-docs' in content and '.value' in content,
            "Reads maxTokens input": 'profile-modal-knowledge-max-tokens' in content and '.value' in content,
            "Creates knowledgeConfig object": 'knowledgeConfig' in content and '{' in content and 'enabled:' in content,
            "Includes collections array": 'collections:' in content or 'collections =' in content,
            "Includes reranking settings": 'reranking:' in content or 'data-reranking' in content,
            "Assigns to profileData": 'profileData' in content and 'knowledgeConfig:' in content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Verify knowledgeConfig structure
        print("\n--- knowledgeConfig Structure ---")
        structure_checks = {
            "enabled field": 'enabled:' in content and 'knowledgeEnabled' in content,
            "collections field": 'collections:' in content and 'collectionsWithReranking' in content,
            "minRelevanceScore field": 'minRelevanceScore:' in content,
            "maxDocs field": 'maxDocs:' in content,
            "maxTokens field": 'maxTokens:' in content
        }
        
        for check_name, passed in structure_checks.items():
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


def test_6_integration_with_existing_modal():
    """Test 6: Verify integration with existing profile modal structure"""
    print("\n" + "="*80)
    print("TEST 6: Integration with Existing Profile Modal")
    print("="*80)
    
    try:
        index_html_path = project_root / "templates" / "index.html"
        content = index_html_path.read_text()
        
        checks = {
            "Modal container exists": 'id="profile-modal"' in content,
            "Knowledge section after Intelligence Collections": True,  # Will verify order
            "Modal save button exists": 'profile-modal-save' in content,
            "Modal cancel button exists": 'profile-modal-cancel' in content,
            "Knowledge config in modal body": 'knowledge-config-settings' in content
        }
        
        # Check ordering
        intelligence_pos = content.find('Intelligence Collections')
        knowledge_config_pos = content.find('Knowledge Repository Configuration')
        checks["Knowledge section after Intelligence Collections"] = intelligence_pos > 0 and knowledge_config_pos > intelligence_pos
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check_name}")
            if not passed:
                all_passed = False
        
        # Verify existing sections still present
        print("\n--- Existing Sections Intact ---")
        existing_sections = {
            "Basic Info section": 'Profile Name' in content and 'Profile Tag' in content,
            "Provider Configuration": 'Provider Configuration' in content,
            "Classification Mode": 'Classification' in content,
            "MCP Resources": 'MCP Resources' in content,
            "Intelligence Collections": 'Intelligence Collections' in content
        }
        
        for section_name, passed in existing_sections.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {section_name}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_toggle_visibility_logic():
    """Test 7: Verify knowledge config visibility toggle logic"""
    print("\n" + "="*80)
    print("TEST 7: Knowledge Config Visibility Toggle")
    print("="*80)
    
    try:
        config_handler_path = project_root / "static" / "js" / "handlers" / "configurationHandler.js"
        content = config_handler_path.read_text()
        
        checks = {
            "updateKnowledgeConfigVisibility function exists": 'updateKnowledgeConfigVisibility' in content,
            "Checks toggle state": 'knowledgeEnabledToggle.checked' in content,
            "Shows/hides settings": 'classList.remove' in content and 'hidden' in content,
            "Event listener on toggle": 'addEventListener' in content and 'change' in content,
            "Initial visibility update": 'updateKnowledgeConfigVisibility()' in content
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


def run_all_tests():
    """Run all Phase 4 tests"""
    print("\n" + "="*80)
    print("KNOWLEDGE REPOSITORIES - PHASE 4 TEST SUITE")
    print("Profile Configuration UI")
    print("="*80)
    print(f"Project Root: {project_root}")
    print(f"Python Version: {sys.version}")
    
    tests = [
        ("Knowledge Config Section HTML", test_1_knowledge_config_section_html),
        ("Advanced Settings Fields", test_2_advanced_settings_fields),
        ("Reranking Toggles Container", test_3_reranking_toggles_container),
        ("JavaScript Load Logic", test_4_javascript_load_logic),
        ("JavaScript Save Logic", test_5_javascript_save_logic),
        ("Integration with Existing Modal", test_6_integration_with_existing_modal),
        ("Toggle Visibility Logic", test_7_toggle_visibility_logic),
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
        print(f"\n🎉 ALL TESTS PASSED! Phase 4 is ready.")
        print(f"\n📋 Manual Testing Steps:")
        print(f"   1. Start TDA and navigate to Configuration > Profiles")
        print(f"   2. Click 'Add Profile' or 'Edit' on existing profile")
        print(f"   3. Scroll to 'Knowledge Repository Configuration' section")
        print(f"   4. Verify Enable Knowledge toggle works")
        print(f"   5. Select knowledge collections in Intelligence Collections")
        print(f"   6. Verify reranking toggles appear for selected collections")
        print(f"   7. Set advanced settings (min relevance, max docs, max tokens)")
        print(f"   8. Save profile and reload - verify settings persist")
        print(f"   9. Check browser console for knowledgeConfig object in saved profile")
    elif failed > 0:
        print(f"\n⚠️  {failed} test(s) failed. Review output above.")
    
    print("="*80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
