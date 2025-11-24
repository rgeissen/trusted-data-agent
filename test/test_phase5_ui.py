#!/usr/bin/env python3
"""
Test Phase 5: Frontend UI changes for profile-based classification.
Tests that classification_mode is properly saved and displayed.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

def test_create_profile_with_classification():
    """Test creating a profile with different classification modes"""
    print("\n" + "="*80)
    print("PHASE 5 UI TEST: Profile Creation with Classification Modes")
    print("="*80 + "\n")
    
    modes = ['none', 'light', 'full']
    created_profiles = []
    
    for mode in modes:
        print(f"[TEST] Creating profile with classification_mode='{mode}'")
        
        profile_data = {
            "name": f"UI Test {mode.title()} Mode",
            "tag": f"UI{mode[:2].upper()}",
            "description": f"Testing {mode} classification mode via UI",
            "classification_mode": mode,
            "llm_provider": "Google",
            "llm_model": "gemini-1.5-flash",
            "mcp_servers": []
        }
        
        response = requests.post(f"{BASE_URL}/v1/profiles", json=profile_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            profile = result.get("profile", {})
            profile_id = profile.get("id")
            saved_mode = profile.get("classification_mode")
            
            if saved_mode == mode:
                print(f"  ✓ PASS - Profile created with mode '{mode}': {profile_id}")
                created_profiles.append(profile_id)
            else:
                print(f"  ✗ FAIL - Mode mismatch: expected '{mode}', got '{saved_mode}'")
        else:
            print(f"  ✗ FAIL - HTTP {response.status_code}: {response.text[:100]}")
    
    return created_profiles


def test_update_classification_mode(profile_id):
    """Test updating a profile's classification mode"""
    print("\n[TEST] Updating classification mode")
    
    modes = ['none', 'light', 'full']
    
    for mode in modes:
        print(f"  → Changing to '{mode}'...")
        
        response = requests.put(
            f"{BASE_URL}/v1/profiles/{profile_id}",
            json={"classification_mode": mode}
        )
        
        if response.status_code == 200:
            # Verify the change
            get_response = requests.get(f"{BASE_URL}/v1/profiles")
            if get_response.status_code == 200:
                profiles = get_response.json().get("profiles", [])
                profile = next((p for p in profiles if p.get("id") == profile_id), None)
                
                if profile and profile.get("classification_mode") == mode:
                    print(f"    ✓ Successfully updated to '{mode}'")
                else:
                    print(f"    ✗ Update didn't persist correctly")
        else:
            print(f"    ✗ Update failed: HTTP {response.status_code}")


def test_profile_list_shows_modes():
    """Test that profile list includes classification_mode"""
    print("\n[TEST] Verifying classification modes in profile list")
    
    response = requests.get(f"{BASE_URL}/v1/profiles")
    
    if response.status_code == 200:
        profiles = response.json().get("profiles", [])
        
        profiles_with_mode = [p for p in profiles if "classification_mode" in p]
        
        print(f"  ✓ Found {len(profiles_with_mode)}/{len(profiles)} profiles with classification_mode")
        
        # Show some examples
        for profile in profiles[:5]:
            mode = profile.get("classification_mode", "NOT SET")
            name = profile.get("name", "Unnamed")
            print(f"    - {name}: {mode}")
        
        if len(profiles_with_mode) == len(profiles):
            print("  ✓ PASS - All profiles have classification_mode")
            return True
        else:
            print("  ⚠ WARNING - Some profiles missing classification_mode")
            return False
    else:
        print(f"  ✗ FAIL - Could not fetch profiles: HTTP {response.status_code}")
        return False


def test_reclassify_endpoint(profile_id):
    """Test the reclassify endpoint"""
    print("\n[TEST] Testing reclassify endpoint")
    
    response = requests.post(f"{BASE_URL}/v1/profiles/{profile_id}/reclassify")
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ PASS - Reclassify endpoint responded: {result.get('message')}")
        return True
    else:
        print(f"  ✗ FAIL - HTTP {response.status_code}: {response.text[:100]}")
        return False


def main():
    print("\n" + "="*80)
    print("PHASE 5: Frontend UI Implementation Tests")
    print("="*80)
    
    all_passed = True
    
    # Test 1: Create profiles with different modes
    created_profiles = test_create_profile_with_classification()
    if len(created_profiles) != 3:
        all_passed = False
    
    # Test 2: Update classification mode
    if created_profiles:
        test_update_classification_mode(created_profiles[0])
    
    # Test 3: List profiles shows modes
    if not test_profile_list_shows_modes():
        all_passed = False
    
    # Test 4: Reclassify endpoint
    if created_profiles:
        if not test_reclassify_endpoint(created_profiles[0]):
            all_passed = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if all_passed:
        print("\n✓ ALL PHASE 5 UI TESTS PASSED")
        print("\nThe UI is ready for end-to-end testing!")
        print("Next: Test with actual MCP server configuration")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        print("Review output above for details")
        return 1


if __name__ == "__main__":
    exit(main())
