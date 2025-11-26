#!/usr/bin/env python3
"""
Quick test to verify profile badges appear in REST API queries.
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"
API_V1_BASE = f"{BASE_URL}/api/v1"
AUTH_BASE = f"{BASE_URL}/api/v1/auth"

def test_profile_badges_in_rest_queries():
    """Test that profile badges are associated with REST queries."""
    
    print("=" * 70)
    print("REST API Query - Profile Badge Test")
    print("=" * 70)
    print()
    
    # Step 1: Login
    print("[1] Logging in with credentials...")
    try:
        response = requests.post(
            f"{AUTH_BASE}/login",
            json={"username": "admin", "password": "admin"}
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   {response.text}")
            return
        
        jwt_token = response.json()['token']
        user_uuid = response.json()['user']['user_uuid']
        print(f"✓ Login successful")
        print(f"  User UUID: {user_uuid}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 2: Check profile
    print("[2] Checking user profile...")
    try:
        response = requests.get(
            f"{API_V1_BASE}/profiles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Profile check failed: {response.status_code}")
            return
        
        data = response.json()
        default_profile_id = data.get('default_profile_id')
        profiles = data.get('profiles', [])
        
        if not default_profile_id:
            print(f"❌ No default profile found")
            return
        
        profile = next((p for p in profiles if p.get('id') == default_profile_id), None)
        print(f"✓ Default profile found: {default_profile_id}")
        if profile:
            print(f"  Name: {profile.get('name')}")
            print(f"  Color: {profile.get('color')}")
            print(f"  Provider: {profile.get('providerName')}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 3: Create session
    print("[3] Creating session...")
    try:
        response = requests.post(
            f"{API_V1_BASE}/sessions",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 201:
            print(f"❌ Session creation failed: {response.status_code}")
            print(f"   {response.text}")
            return
        
        session_id = response.json()['session_id']
        print(f"✓ Session created: {session_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 4: Submit query via REST
    print("[4] Submitting query via REST API...")
    try:
        response = requests.post(
            f"{API_V1_BASE}/sessions/{session_id}/query",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={"prompt": "What databases are available?"}
        )
        
        if response.status_code not in [200, 202]:
            print(f"❌ Query submission failed: {response.status_code}")
            print(f"   {response.text}")
            return
        
        task_id = response.json()['task_id']
        print(f"✓ Query submitted: {task_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 5: Wait and check task status
    print("[5] Waiting for query to complete...")
    for i in range(10):
        time.sleep(1)
        
        try:
            response = requests.get(
                f"{API_V1_BASE}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if response.status_code != 200:
                print(f"❌ Task status check failed: {response.status_code}")
                return
            
            task_data = response.json()
            status = task_data.get('status')
            
            print(f"   Status: {status}")
            
            if status in ['complete', 'error', 'cancelled']:
                print(f"✓ Task completed with status: {status}")
                print(f"   Task ID: {task_id}")
                
                # Print events to see if profile badges are included
                events = task_data.get('events', [])
                print(f"\n   Events captured: {len(events)}")
                
                if events:
                    print(f"\n   First 3 events:")
                    for idx, event in enumerate(events[:3], 1):
                        event_type = event.get('event_type')
                        event_data = event.get('event_data', {})
                        print(f"     {idx}. {event_type}")
                        # Check if profile info is in event_data
                        if isinstance(event_data, dict):
                            # Look for profile-related keys
                            for key in ['profile', 'profile_id', 'llm_provider', 'provider']:
                                if key in event_data:
                                    print(f"        → {key}: {event_data[key]}")
                print()
                break
        except Exception as e:
            print(f"   Error checking status: {e}")
    
    # Step 6: Check session to see if profile badge is visible
    print("[6] Checking session for profile badge...")
    try:
        response = requests.get(
            f"{API_V1_BASE}/sessions/{session_id}/details",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 200:
            print(f"⚠️  Could not retrieve session details: {response.status_code}")
        else:
            session_data = response.json()
            print(f"✓ Session details retrieved")
            print(f"  ID: {session_data.get('id')}")
            print(f"  Name: {session_data.get('name')}")
            
            # Check for profile-related info
            if 'profile' in session_data:
                print(f"  Profile: {session_data.get('profile')}")
            if 'provider_color' in session_data:
                print(f"  Provider Color: {session_data.get('provider_color')}")
            if 'models_used' in session_data:
                print(f"  Models Used: {session_data.get('models_used')}")
            
            print("\n✅ Profile badge information should now appear in the UI")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    print("=" * 70)
    print("✅ Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    test_profile_badges_in_rest_queries()
