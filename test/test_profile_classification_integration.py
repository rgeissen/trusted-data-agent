#!/usr/bin/env python3
"""
Integration test for profile-based classification with a real configured profile.
This test requires an existing configured profile with LLM and MCP server set up.

Usage:
    python test/test_profile_classification_integration.py <profile_id>
    
Example:
    python test/test_profile_classification_integration.py profile-1763820446672-zy475d5rc
"""

import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:5000/api"

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{text}")
    print(f"{'='*80}\n")

def print_test(name):
    print(f"[TEST] {name}")

def print_success(message):
    print(f"✓ {message}")

def print_error(message):
    print(f"✗ {message}")

def print_info(message):
    print(f"ℹ {message}")

def make_request(method, endpoint, json_data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=json_data)
        
        return response.status_code, response.json()
    except Exception as e:
        return 0, {"error": str(e)}

def test_profile_classification_modes(profile_id):
    """Test all three classification modes with an existing profile"""
    
    print_header("Integration Test: Profile Classification Modes")
    print_info(f"Testing with profile: {profile_id}")
    
    # Test 1: Get current classification
    print_test("Getting current classification")
    status, response = make_request("GET", f"/v1/profiles/{profile_id}/classification")
    
    if status == 200:
        current_mode = response.get('classification_mode', 'unknown')
        print_success(f"Current mode: {current_mode}")
        results = response.get('classification_results', {})
        print_info(f"Cached results: {len(results.get('tools', {}))} tool categories, {len(results.get('prompts', {}))} prompt categories")
    else:
        print_error(f"Failed to get classification: {response}")
        return False
    
    # Test 2: Test each mode
    modes_to_test = ['none', 'light', 'full']
    original_mode = current_mode
    
    for test_mode in modes_to_test:
        print_test(f"Testing classification_mode='{test_mode}'")
        
        # Update profile to use this mode
        status, response = make_request("PUT", f"/v1/profiles/{profile_id}", 
                                       json_data={"classification_mode": test_mode})
        
        if status == 200:
            print_success(f"Updated profile to mode '{test_mode}'")
        else:
            print_error(f"Failed to update profile: {response}")
            continue
        
        # Get classification to see if it was cleared
        status, response = make_request("GET", f"/v1/profiles/{profile_id}/classification")
        if status == 200:
            results = response.get('classification_results', {})
            mode = response.get('classification_mode')
            print_info(f"Mode: {mode}, Results: {len(results.get('tools', {}))} categories")
        
        time.sleep(0.5)
    
    # Restore original mode
    print_test(f"Restoring original mode '{original_mode}'")
    make_request("PUT", f"/v1/profiles/{profile_id}", 
                json_data={"classification_mode": original_mode})
    
    return True

def test_reclassification(profile_id):
    """Test manual reclassification"""
    
    print_header("Integration Test: Manual Reclassification")
    
    print_test("Triggering reclassification")
    status, response = make_request("POST", f"/v1/profiles/{profile_id}/reclassify")
    
    if status == 200:
        print_success("Reclassification triggered successfully")
        print_info(f"Message: {response.get('message')}")
        return True
    else:
        print_error(f"Failed to reclassify: {response}")
        return False

def test_profile_comparison(profile_id):
    """Compare profile with different modes"""
    
    print_header("Integration Test: Mode Comparison")
    
    # Create two test profiles with different modes
    modes = ['light', 'full']
    test_profiles = {}
    
    for mode in modes:
        print_test(f"Creating test profile with mode='{mode}'")
        
        profile_data = {
            "name": f"Comparison Test {mode.title()}",
            "classification_mode": mode,
            "llm_provider": "Google",
            "llm_model": "gemini-1.5-flash",
            "mcp_servers": []
        }
        
        status, response = make_request("POST", "/v1/profiles", json_data=profile_data)
        
        if status in [200, 201]:
            pid = response.get("profile", {}).get("id")
            test_profiles[mode] = pid
            print_success(f"Created profile: {pid}")
            
            # Get classification
            status, class_resp = make_request("GET", f"/v1/profiles/{pid}/classification")
            if status == 200:
                results = class_resp.get('classification_results', {})
                print_info(f"  Mode '{mode}': {len(results.get('tools', {}))} tool categories")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_profile_classification_integration.py <profile_id>")
        print("\nExample existing profiles:")
        
        status, response = make_request("GET", "/v1/profiles")
        if status == 200:
            profiles = response.get('profiles', [])
            for p in profiles[:5]:  # Show first 5
                print(f"  - {p.get('name')} ({p.get('id')})")
        sys.exit(1)
    
    profile_id = sys.argv[1]
    
    print("\n🧪 Profile Classification Integration Tests")
    print(f"Target: {profile_id}")
    
    # Run tests
    success = True
    success = test_profile_classification_modes(profile_id) and success
    success = test_reclassification(profile_id) and success
    success = test_profile_comparison(profile_id) and success
    
    # Summary
    print_header("Test Summary")
    if success:
        print_success("All integration tests completed successfully!")
    else:
        print_error("Some tests failed - review output above")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
