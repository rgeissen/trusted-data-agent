#!/usr/bin/env python3
"""
Test to verify profile badges appear in REST API sessions after server restart.
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"
API_V1_BASE = f"{BASE_URL}/api/v1"
AUTH_BASE = f"{BASE_URL}/api/v1/auth"

def test_profile_badges_after_restart():
    """Test that profile badges appear in sessions with fresh server."""
    
    print("=" * 70)
    print("Profile Badges Test - After Server Restart")
    print("=" * 70)
    print()
    
    try:
        # Step 1: Login
        print("[1] Logging in...")
        response = requests.post(
            f"{AUTH_BASE}/login",
            json={"username": "admin", "password": "admin"}
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return
        
        jwt_token = response.json()['token']
        user_uuid = response.json()['user']['user_uuid']
        print(f"✓ Login successful")
        print(f"  User UUID: {user_uuid}")
        print()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Is the server running? python -m trusted_data_agent.main")
        return
    
    try:
        # Step 2: Get profile info
        print("[2] Getting profile information...")
        response = requests.get(
            f"{API_V1_BASE}/profiles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get profiles: {response.status_code}")
            return
        
        profiles_data = response.json()
        default_profile_id = profiles_data.get('default_profile_id')
        profiles = profiles_data.get('profiles', [])
        
        if not default_profile_id:
            print(f"❌ No default profile found")
            return
        
        profile = next((p for p in profiles if p.get('id') == default_profile_id), None)
        print(f"✓ Default profile found: {default_profile_id}")
        if profile:
            print(f"  Name: {profile.get('name')}")
            print(f"  Provider: {profile.get('providerName')}")
            print(f"  Color: {profile.get('color')}")
        print()
        
    except Exception as e:
        print(f"❌ Error getting profiles: {e}")
        return
    
    try:
        # Step 3: Create session via REST
        print("[3] Creating session via REST API...")
        response = requests.post(
            f"{API_V1_BASE}/sessions",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 201:
            print(f"❌ Session creation failed: {response.status_code}")
            print(f"   {response.json()}")
            return
        
        session_id = response.json()['session_id']
        print(f"✓ Session created: {session_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return
    
    try:
        # Step 4: Inspect session JSON file
        print("[4] Checking session file...")
        session_file = Path(f"/Users/rainer.geissendoerfer/my_private_code/trusted-data-agent/tda_sessions/{user_uuid}/{session_id}.json")
        
        if not session_file.exists():
            print(f"❌ Session file not found: {session_file}")
            return
        
        with open(session_file) as f:
            session_data = json.load(f)
        
        print(f"✓ Session file loaded")
        print()
        
        # Check for profile information
        print("[5] Profile information in session:")
        profile_id = session_data.get('profile_id')
        profile_tag = session_data.get('profile_tag')
        provider = session_data.get('provider')
        
        print(f"  profile_id: {profile_id}")
        print(f"  profile_tag: {profile_tag}")
        print(f"  provider: {provider}")
        print()
        
        # Verification
        print("[6] Verification:")
        if profile_id and profile_id == default_profile_id:
            print(f"✅ profile_id IS STORED and CORRECT!")
            print(f"   Session knows it was created with profile: {profile_id}")
        else:
            print(f"⚠️  profile_id NOT stored correctly")
            print(f"   Expected: {default_profile_id}")
            print(f"   Got: {profile_id}")
        
        if profile_tag:
            print(f"✅ profile_tag is stored: {profile_tag}")
        else:
            print(f"⚠️  profile_tag is not stored")
        
        print()
        
    except Exception as e:
        print(f"❌ Error checking session file: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Step 5: Submit a query
        print("[7] Submitting query...")
        response = requests.post(
            f"{API_V1_BASE}/sessions/{session_id}/query",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={"prompt": "What databases are available?"}
        )
        
        if response.status_code not in [200, 202]:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   {response.json()}")
            return
        
        task_id = response.json()['task_id']
        print(f"✓ Query submitted: {task_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error submitting query: {e}")
        return
    
    try:
        # Step 6: Check session details
        print("[8] Checking session details...")
        response = requests.get(
            f"{API_V1_BASE}/sessions/{session_id}/details",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code == 200:
            details = response.json()
            print(f"✓ Session details retrieved")
            print(f"  Name: {details.get('name')}")
            print(f"  Provider: {details.get('provider')}")
            print(f"  Models used: {details.get('models_used', [])}")
            
            # Check for profile info in details
            if 'profile_id' in details:
                print(f"  profile_id: {details.get('profile_id')}")
            
        else:
            print(f"⚠️  Could not get session details: {response.status_code}")
        
        print()
        
    except Exception as e:
        print(f"⚠️  Error getting session details: {e}")
    
    # Final summary
    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    print()
    print("NEXT STEPS:")
    print("1. Check the UI at http://localhost:5000")
    print("2. Look for the session in the left sidebar")
    print("3. The profile badge should appear with:")
    print(f"   • Provider color from profile: {profile.get('color') if profile else 'N/A'}")
    print(f"   • Provider name: {profile.get('providerName') if profile else 'N/A'}")
    print("4. If badges don't appear, check browser console for errors")
    print()

if __name__ == "__main__":
    test_profile_badges_after_restart()
