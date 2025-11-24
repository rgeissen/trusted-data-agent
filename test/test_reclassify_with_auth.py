#!/usr/bin/env python3
"""
Test the reclassify endpoint with authentication.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

def login(username="admin", password="admin"):
    """Login and get auth token"""
    print(f"\n[1] Logging in as {username}...")
    response = requests.post(
        f"{BASE_URL}/v1/auth/login",
        json={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('token')
        print(f"  ✓ Login successful")
        print(f"  Token: {token[:20]}...")
        return token
    else:
        print(f"  ✗ Login failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return None


def get_profiles(token):
    """Get all profiles"""
    print("\n[2] Getting profiles...")
    response = requests.get(
        f"{BASE_URL}/v1/profiles",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        profiles = response.json().get("profiles", [])
        print(f"  ✓ Found {len(profiles)} profile(s)")
        for p in profiles:
            print(f"    - {p['name']} (ID: {p['id']})")
        return profiles
    else:
        print(f"  ✗ Failed: {response.status_code}")
        return []


def get_active_profiles(token):
    """Get active profiles"""
    print("\n[3] Getting active profiles...")
    response = requests.get(
        f"{BASE_URL}/v1/profiles",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        active_ids = data.get("active_for_consumption_profile_ids", [])
        print(f"  ✓ Active profile IDs: {active_ids}")
        return active_ids
    else:
        print(f"  ✗ Failed: {response.status_code}")
        return []


def activate_profile(token, profile_id):
    """Activate a profile"""
    print(f"\n[4] Activating profile {profile_id}...")
    response = requests.post(
        f"{BASE_URL}/v1/profiles/set_active_for_consumption",
        headers={"Authorization": f"Bearer {token}"},
        json={"profile_ids": [profile_id]}
    )
    
    if response.status_code == 200:
        print(f"  ✓ Profile activated successfully")
        return True
    else:
        print(f"  ✗ Failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False


def reclassify_profile(token, profile_id):
    """Reclassify a profile"""
    print(f"\n[5] Reclassifying profile {profile_id}...")
    response = requests.post(
        f"{BASE_URL}/v1/profiles/{profile_id}/reclassify",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    print(f"  Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ SUCCESS!")
        print(f"  Message: {result.get('message')}")
        
        classification = result.get('classification_results', {})
        if classification:
            mode = classification.get('mode', 'unknown')
            tools = classification.get('tools', {})
            prompts = classification.get('prompts', {})
            
            print(f"\n  Classification Results:")
            print(f"    Mode: {mode}")
            print(f"    Tools: {len(tools)} categories")
            print(f"    Prompts: {len(prompts)} categories")
            
            if tools:
                print(f"\n  Tool Categories:")
                for cat, items in list(tools.items())[:5]:
                    print(f"    - {cat}: {len(items)} tools")
        
        return True
    else:
        print(f"  ✗ FAILED")
        try:
            error = response.json()
            print(f"  Error: {error.get('message', 'Unknown error')}")
        except:
            print(f"  Response: {response.text[:500]}")
        return False


def main():
    print("="*80)
    print("TESTING RECLASSIFY ENDPOINT WITH AUTHENTICATION")
    print("="*80)
    
    # Step 1: Login
    token = login()
    if not token:
        print("\n✗ Cannot proceed without authentication")
        return 1
    
    # Step 2: Get profiles
    profiles = get_profiles(token)
    if not profiles:
        print("\n✗ No profiles found")
        return 1
    
    # Use the first profile
    test_profile = profiles[0]
    profile_id = test_profile['id']
    profile_name = test_profile['name']
    
    print(f"\n→ Using profile: {profile_name}")
    
    # Step 3: Check if active
    active_ids = get_active_profiles(token)
    is_active = profile_id in active_ids
    
    if not is_active:
        print(f"\n→ Profile is not active, activating...")
        if not activate_profile(token, profile_id):
            print("\n✗ Failed to activate profile")
            return 1
    else:
        print(f"\n→ Profile is already active")
    
    # Step 4: Reclassify
    success = reclassify_profile(token, profile_id)
    
    print("\n" + "="*80)
    if success:
        print("✓ TEST PASSED - Reclassify endpoint works!")
        return 0
    else:
        print("✗ TEST FAILED - See errors above")
        return 1


if __name__ == "__main__":
    exit(main())
