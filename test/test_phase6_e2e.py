#!/usr/bin/env python3
"""
Phase 6: End-to-End Testing with Actual MCP Services
Tests classification behavior across all three modes with real MCP server connections.
"""

import requests
import json
import time
from typing import Dict, List, Any

BASE_URL = "http://127.0.0.1:5000/api"

# Sample MCP server configurations for testing
SAMPLE_MCP_SERVERS = [
    {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "env": {}
    },
    {
        "name": "brave-search",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "env": {"BRAVE_API_KEY": "test-key"}
    },
    {
        "name": "memory",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {}
    }
]


def create_test_profile(mode: str, mcp_servers: List[Dict] = None) -> str:
    """Create a test profile with specified classification mode"""
    
    profile_data = {
        "name": f"E2E Test - {mode.title()} Mode",
        "tag": f"E2E{mode[:2].upper()}",
        "description": f"End-to-end testing with {mode} classification mode",
        "classification_mode": mode,
        "llm_provider": "Google",
        "llm_model": "gemini-1.5-flash",
        "mcp_servers": mcp_servers or SAMPLE_MCP_SERVERS
    }
    
    response = requests.post(f"{BASE_URL}/v1/profiles", json=profile_data)
    
    if response.status_code in [200, 201]:
        profile = response.json().get("profile", {})
        profile_id = profile.get("id")
        print(f"  ✓ Created profile '{profile_data['name']}': {profile_id}")
        return profile_id
    else:
        print(f"  ✗ Failed to create profile: HTTP {response.status_code}")
        print(f"    Response: {response.text[:200]}")
        return None


def activate_profile(profile_id: str) -> bool:
    """Activate a profile and wait for classification"""
    
    response = requests.post(f"{BASE_URL}/v1/profiles/{profile_id}/activate")
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ Profile activated: {result.get('message')}")
        time.sleep(2)  # Give classification time to complete
        return True
    else:
        print(f"  ✗ Activation failed: HTTP {response.status_code}")
        return False


def get_classification(profile_id: str) -> Dict[str, Any]:
    """Get classification results for a profile"""
    
    response = requests.get(f"{BASE_URL}/v1/profiles/{profile_id}/classification")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"  ✗ Could not get classification: HTTP {response.status_code}")
        return {}


def analyze_classification_structure(classification: Dict, expected_mode: str) -> bool:
    """Analyze classification structure and verify it matches expected mode"""
    
    tools = classification.get("tools", {})
    prompts = classification.get("prompts", {})
    resources = classification.get("resources", {})
    
    mode = classification.get("mode", "unknown")
    
    print(f"\n  Classification Mode: {mode}")
    print(f"  Expected Mode: {expected_mode}")
    
    if mode != expected_mode:
        print(f"  ✗ FAIL - Mode mismatch")
        return False
    
    # Analyze structure based on mode
    if expected_mode == "none":
        # Should be flat - tools/prompts/resources at top level, no categories
        if isinstance(tools, dict) and not any(isinstance(v, dict) for v in tools.values()):
            print(f"  ✓ PASS - Flat structure (no categories)")
            print(f"    Tools: {len(tools)} items")
            print(f"    Prompts: {len(prompts)} items")
            print(f"    Resources: {len(resources)} items")
            return True
        else:
            print(f"  ✗ FAIL - Expected flat structure, found nested")
            return False
    
    elif expected_mode == "light":
        # Should have generic categories: Tools, Prompts, Resources
        if isinstance(tools, dict):
            categories = list(tools.keys())
            print(f"  Tool categories: {categories}")
            
            # Light mode should have simple categorization
            if len(categories) > 0:
                print(f"  ✓ PASS - Light categorization present")
                for cat in categories:
                    items = tools[cat]
                    if isinstance(items, dict):
                        print(f"    - {cat}: {len(items)} tools")
                return True
            else:
                print(f"  ⚠ WARNING - No categories found (might be flat)")
                return False
        else:
            print(f"  ✗ FAIL - Unexpected structure")
            return False
    
    elif expected_mode == "full":
        # Should have semantic LLM-powered categories
        if isinstance(tools, dict):
            categories = list(tools.keys())
            print(f"  Tool categories: {categories}")
            
            # Full mode should have descriptive categories
            if len(categories) > 1:
                print(f"  ✓ PASS - Semantic categorization present")
                for cat in categories[:5]:  # Show first 5
                    items = tools[cat]
                    if isinstance(items, dict):
                        print(f"    - {cat}: {len(items)} tools")
                
                # Check if categories look semantic (longer than simple words)
                avg_len = sum(len(c) for c in categories) / len(categories)
                if avg_len > 10:
                    print(f"  ✓ Categories appear semantic (avg length: {avg_len:.1f})")
                else:
                    print(f"  ⚠ Categories might be too simple (avg length: {avg_len:.1f})")
                
                return True
            else:
                print(f"  ⚠ WARNING - Only {len(categories)} category found")
                return False
        else:
            print(f"  ✗ FAIL - Unexpected structure")
            return False
    
    return False


def test_mode(mode: str) -> bool:
    """Test a specific classification mode end-to-end"""
    
    print("\n" + "="*80)
    print(f"TESTING MODE: {mode.upper()}")
    print("="*80)
    
    # Step 1: Create profile
    print("\n[Step 1] Creating profile...")
    profile_id = create_test_profile(mode)
    if not profile_id:
        return False
    
    # Step 2: Activate profile
    print("\n[Step 2] Activating profile...")
    if not activate_profile(profile_id):
        return False
    
    # Step 3: Get classification results
    print("\n[Step 3] Retrieving classification...")
    classification = get_classification(profile_id)
    
    if not classification:
        print("  ✗ No classification data returned")
        return False
    
    # Step 4: Analyze structure
    print("\n[Step 4] Analyzing classification structure...")
    passed = analyze_classification_structure(classification, mode)
    
    return passed


def test_mode_switching(profile_id: str) -> bool:
    """Test switching classification modes on existing profile"""
    
    print("\n" + "="*80)
    print("TESTING MODE SWITCHING")
    print("="*80)
    
    modes = ['none', 'light', 'full']
    
    for mode in modes:
        print(f"\n[TEST] Switching to mode '{mode}'...")
        
        # Update profile
        response = requests.put(
            f"{BASE_URL}/v1/profiles/{profile_id}",
            json={"classification_mode": mode}
        )
        
        if response.status_code != 200:
            print(f"  ✗ Failed to update: HTTP {response.status_code}")
            return False
        
        # Reactivate
        print("  → Reactivating profile...")
        if not activate_profile(profile_id):
            return False
        
        # Get classification
        classification = get_classification(profile_id)
        
        # Verify mode changed
        actual_mode = classification.get("mode")
        if actual_mode == mode:
            print(f"  ✓ Classification mode correctly changed to '{mode}'")
        else:
            print(f"  ✗ Mode mismatch: expected '{mode}', got '{actual_mode}'")
            return False
    
    print("\n  ✓ PASS - Mode switching works correctly")
    return True


def test_manual_reclassify(profile_id: str) -> bool:
    """Test manual reclassification via API"""
    
    print("\n" + "="*80)
    print("TESTING MANUAL RECLASSIFICATION")
    print("="*80)
    
    # Get initial classification
    print("\n[Step 1] Getting initial classification...")
    initial = get_classification(profile_id)
    initial_timestamp = initial.get("cached_at")
    print(f"  Initial cache timestamp: {initial_timestamp}")
    
    # Trigger reclassification
    print("\n[Step 2] Triggering manual reclassification...")
    response = requests.post(f"{BASE_URL}/v1/profiles/{profile_id}/reclassify")
    
    if response.status_code != 200:
        print(f"  ✗ Reclassify failed: HTTP {response.status_code}")
        return False
    
    result = response.json()
    print(f"  ✓ {result.get('message')}")
    
    # Reactivate to trigger new classification
    print("\n[Step 3] Reactivating to trigger classification...")
    if not activate_profile(profile_id):
        return False
    
    # Get new classification
    print("\n[Step 4] Getting new classification...")
    new = get_classification(profile_id)
    new_timestamp = new.get("cached_at")
    print(f"  New cache timestamp: {new_timestamp}")
    
    # Verify cache was cleared and reclassification occurred
    if new_timestamp != initial_timestamp:
        print(f"  ✓ PASS - Reclassification occurred (timestamp changed)")
        return True
    else:
        print(f"  ⚠ WARNING - Timestamps match (cache might not have cleared)")
        return False


def main():
    print("\n" + "="*80)
    print("PHASE 6: End-to-End Testing with MCP Services")
    print("="*80)
    
    results = {}
    
    # Test 1: None mode
    print("\n\n### TEST 1: NONE MODE ###")
    results['none'] = test_mode('none')
    
    # Test 2: Light mode
    print("\n\n### TEST 2: LIGHT MODE ###")
    results['light'] = test_mode('light')
    
    # Test 3: Full mode
    print("\n\n### TEST 3: FULL MODE ###")
    profile_id = create_test_profile('full')
    if profile_id:
        if activate_profile(profile_id):
            classification = get_classification(profile_id)
            results['full'] = analyze_classification_structure(classification, 'full')
            
            # Test 4: Mode switching (using full mode profile)
            print("\n\n### TEST 4: MODE SWITCHING ###")
            results['switching'] = test_mode_switching(profile_id)
            
            # Test 5: Manual reclassify
            print("\n\n### TEST 5: MANUAL RECLASSIFICATION ###")
            results['reclassify'] = test_manual_reclassify(profile_id)
    
    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ ALL PHASE 6 TESTS PASSED")
        print("\nThe classification system is fully functional!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        print("Review output above for details")
        return 1


if __name__ == "__main__":
    exit(main())
