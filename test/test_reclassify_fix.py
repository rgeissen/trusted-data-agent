#!/usr/bin/env python3
"""
Quick test to verify the reclassify endpoint fix.
Tests that reclassify can initialize temporary LLM and MCP clients.
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000/api"


def get_profiles():
    """Get all profiles"""
    response = requests.get(f"{BASE_URL}/v1/profiles")
    if response.status_code == 200:
        return response.json().get("profiles", [])
    return []


def get_active_profiles():
    """Get active profiles"""
    response = requests.get(f"{BASE_URL}/v1/profiles/active")
    if response.status_code == 200:
        data = response.json()
        return data.get("active_profile_ids", [])
    return []


def activate_profile(profile_id: str):
    """Activate a profile"""
    response = requests.post(
        f"{BASE_URL}/v1/profiles/set_active_for_consumption",
        json={"profile_ids": [profile_id]}
    )
    return response.status_code == 200, response


def test_profile_connections(profile_id: str):
    """Test a profile's connections"""
    response = requests.post(f"{BASE_URL}/v1/profiles/{profile_id}/test")
    return response.status_code == 200, response


def reclassify_profile(profile_id: str):
    """Trigger reclassification"""
    response = requests.post(f"{BASE_URL}/v1/profiles/{profile_id}/reclassify")
    return response.status_code == 200, response


def main():
    print("\n" + "="*80)
    print("TESTING RECLASSIFY ENDPOINT FIX")
    print("="*80)
    
    # Step 1: Get profiles
    print("\n[Step 1] Getting profiles...")
    profiles = get_profiles()
    
    if not profiles:
        print("  ✗ No profiles found. Please create a profile first.")
        return 1
    
    # Find a profile to test with
    first_profile = profiles[0]
    profile_id = first_profile['id']
    profile_name = first_profile['name']
    
    print(f"  ✓ Found {len(profiles)} profile(s)")
    print(f"  → Using profile: {profile_name} ({profile_id})")
    
    # Step 2: Check if profile is active
    print("\n[Step 2] Checking if profile is active...")
    active_ids = get_active_profiles()
    is_active = profile_id in active_ids
    
    if is_active:
        print(f"  ✓ Profile is already active")
    else:
        print(f"  → Profile is not active, activating...")
        
        # Test the profile first
        print("  → Testing profile connections...")
        success, response = test_profile_connections(profile_id)
        
        if not success:
            print(f"  ✗ Profile test failed: {response.status_code}")
            try:
                error = response.json()
                print(f"     {error.get('message', response.text)}")
            except:
                print(f"     {response.text[:200]}")
            print("\n  Note: Profile needs valid LLM and MCP configurations to test.")
            return 1
        
        print(f"  ✓ Profile tests passed")
        
        # Activate it
        print("  → Activating profile...")
        success, response = activate_profile(profile_id)
        
        if not success:
            print(f"  ✗ Activation failed: {response.status_code}")
            return 1
        
        print(f"  ✓ Profile activated")
        time.sleep(1)  # Give it a moment
    
    # Step 3: Test reclassify endpoint
    print("\n[Step 3] Testing reclassify endpoint...")
    print(f"  → POST /v1/profiles/{profile_id}/reclassify")
    
    success, response = reclassify_profile(profile_id)
    
    if success:
        result = response.json()
        print(f"  ✓ SUCCESS - Reclassify worked!")
        print(f"     Message: {result.get('message')}")
        
        # Show some classification results if available
        classification = result.get('classification_results', {})
        if classification:
            tools = classification.get('tools', {})
            prompts = classification.get('prompts', {})
            mode = classification.get('mode', 'unknown')
            
            print(f"\n  Classification Results:")
            print(f"     Mode: {mode}")
            print(f"     Tools: {len(tools)} items")
            print(f"     Prompts: {len(prompts)} items")
        
        return 0
    else:
        print(f"  ✗ FAILED - HTTP {response.status_code}")
        try:
            error = response.json()
            print(f"     Error: {error.get('message', 'Unknown error')}")
            print(f"\n     Full response: {json.dumps(error, indent=2)}")
        except:
            print(f"     Response: {response.text[:500]}")
        
        return 1


if __name__ == "__main__":
    exit(main())
