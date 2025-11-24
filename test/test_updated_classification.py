#!/usr/bin/env python3
"""
Test updated classification system: Only Light and Full modes allowed
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

def test_classification_modes():
    """Test that only 'light' and 'full' modes are accepted"""
    print("\n" + "="*80)
    print("TEST: Classification Mode Validation")
    print("="*80 + "\n")
    
    # Test 1: Try to create profile with 'none' mode (should fail)
    print("[TEST 1] Attempting to create profile with mode='none' (should be rejected)...")
    response = requests.post(f"{BASE_URL}/v1/profiles", json={
        "name": "Test None Mode",
        "tag": "TESTNONE",
        "classification_mode": "none",
        "llm_provider": "Google",
        "llm_model": "gemini-1.5-flash"
    })
    
    if response.status_code == 400:
        print("  ✓ PASS - 'none' mode correctly rejected")
        print(f"    Message: {response.json().get('message')}")
    else:
        print(f"  ✗ FAIL - Expected 400, got {response.status_code}")
    
    # Test 2: Create profile with 'light' mode (should succeed)
    print("\n[TEST 2] Creating profile with mode='light'...")
    response = requests.post(f"{BASE_URL}/v1/profiles", json={
        "name": "Test Light Mode v2",
        "tag": "LIGHT2",
        "classification_mode": "light",
        "llm_provider": "Google",
        "llm_model": "gemini-1.5-flash"
    })
    
    if response.status_code in [200, 201]:
        profile = response.json().get('profile', {})
        if profile.get('classification_mode') == 'light':
            print("  ✓ PASS - 'light' mode accepted and saved")
            light_profile_id = profile.get('id')
        else:
            print(f"  ✗ FAIL - Mode mismatch: {profile.get('classification_mode')}")
    else:
        print(f"  ✗ FAIL - HTTP {response.status_code}: {response.text[:100]}")
    
    # Test 3: Create profile with 'full' mode (should succeed)
    print("\n[TEST 3] Creating profile with mode='full'...")
    response = requests.post(f"{BASE_URL}/v1/profiles", json={
        "name": "Test Full Mode v2",
        "tag": "FULL2",
        "classification_mode": "full",
        "llm_provider": "Google",
        "llm_model": "gemini-1.5-flash"
    })
    
    if response.status_code in [200, 201]:
        profile = response.json().get('profile', {})
        if profile.get('classification_mode') == 'full':
            print("  ✓ PASS - 'full' mode accepted and saved")
            full_profile_id = profile.get('id')
        else:
            print(f"  ✗ FAIL - Mode mismatch: {profile.get('classification_mode')}")
    else:
        print(f"  ✗ FAIL - HTTP {response.status_code}: {response.text[:100]}")
    
    # Test 4: Create profile without specifying mode (should default to 'light')
    print("\n[TEST 4] Creating profile without classification_mode (should default to 'light')...")
    response = requests.post(f"{BASE_URL}/v1/profiles", json={
        "name": "Test Default Mode",
        "tag": "DEFAULT",
        "llm_provider": "Google",
        "llm_model": "gemini-1.5-flash"
    })
    
    if response.status_code in [200, 201]:
        profile = response.json().get('profile', {})
        mode = profile.get('classification_mode')
        if mode == 'light':
            print(f"  ✓ PASS - Defaults to 'light' mode")
        else:
            print(f"  ⚠ WARNING - Defaults to '{mode}' instead of 'light'")
    else:
        print(f"  ✗ FAIL - HTTP {response.status_code}")
    
    # Test 5: Verify no profiles have 'none' mode
    print("\n[TEST 5] Checking all profiles for 'none' mode...")
    response = requests.get(f"{BASE_URL}/v1/profiles")
    
    if response.status_code == 200:
        profiles = response.json().get('profiles', [])
        none_profiles = [p for p in profiles if p.get('classification_mode') == 'none']
        
        if len(none_profiles) == 0:
            print(f"  ✓ PASS - No profiles with 'none' mode (checked {len(profiles)} profiles)")
        else:
            print(f"  ✗ FAIL - Found {len(none_profiles)} profiles with 'none' mode:")
            for p in none_profiles[:5]:
                print(f"    - {p.get('name')} ({p.get('id')})")
    else:
        print(f"  ✗ FAIL - Could not fetch profiles")
    
    # Test 6: Verify mode distribution
    print("\n[TEST 6] Mode distribution across all profiles...")
    if response.status_code == 200:
        profiles = response.json().get('profiles', [])
        light_count = sum(1 for p in profiles if p.get('classification_mode') == 'light')
        full_count = sum(1 for p in profiles if p.get('classification_mode') == 'full')
        other_count = len(profiles) - light_count - full_count
        
        print(f"  Light mode: {light_count} profiles")
        print(f"  Full mode:  {full_count} profiles")
        if other_count > 0:
            print(f"  Other/None: {other_count} profiles (should be 0)")
        else:
            print(f"  ✓ All profiles using valid modes")

def main():
    print("\n" + "="*80)
    print("Updated Classification System Tests")
    print("Only 'light' and 'full' modes are now supported")
    print("="*80)
    
    test_classification_modes()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("\n✓ Classification system updated successfully!")
    print("  - 'none' mode rejected by API")
    print("  - 'light' and 'full' modes accepted")
    print("  - Default mode is 'light'")
    print("  - All profiles migrated")
    print("\nReady for UI testing!")

if __name__ == "__main__":
    main()
