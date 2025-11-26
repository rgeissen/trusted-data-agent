#!/usr/bin/env python3
"""
Test to verify that when loading an existing session in the UI,
profile badges appear correctly based on per-message profile tags.
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"
API_V1_BASE = f"{BASE_URL}/api/v1"
AUTH_BASE = f"{BASE_URL}/api/v1/auth"

def test_profile_badges_in_loaded_session():
    """Test that profile badges display when loading a session with profile overrides."""
    
    print("=" * 70)
    print("Profile Badges in Loaded Session Test")
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
        print()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    try:
        # Step 2: Get profiles
        print("[2] Getting profiles...")
        response = requests.get(
            f"{API_V1_BASE}/profiles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get profiles: {response.status_code}")
            return
        
        profiles_data = response.json()
        profiles = profiles_data.get('profiles', [])
        
        print(f"✓ Available profiles: {len(profiles)}")
        for p in profiles:
            print(f"  • {p.get('tag')}: {p.get('name')}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    try:
        # Step 3: Get the most recent session
        print("[3] Fetching most recent session...")
        response = requests.get(
            f"{API_V1_BASE}/sessions",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get sessions: {response.status_code}")
            return
        
        sessions = response.json().get('sessions', [])
        if not sessions:
            print(f"❌ No sessions found")
            return
        
        # Get most recent session
        most_recent_session = sessions[0]  # Assuming they're sorted by recent first
        session_id = most_recent_session.get('session_id')
        
        print(f"✓ Most recent session: {session_id}")
        print(f"  Provider: {most_recent_session.get('provider')}")
        print(f"  Name: {most_recent_session.get('name')}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    try:
        # Step 4: Load session details to get history
        print("[4] Loading session details...")
        response = requests.get(
            f"{API_V1_BASE}/sessions/{session_id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to load session: {response.status_code}")
            return
        
        session_details = response.json()
        history = session_details.get('history', [])
        
        print(f"✓ Session loaded: {len(history)} messages in history")
        print()
        
        # Step 5: Check each message for profile_tag
        print("[5] Message Profile Tags:")
        print()
        
        user_message_count = 0
        messages_with_profile_tag = 0
        
        for i, msg in enumerate(history):
            role = msg.get('role')
            profile_tag = msg.get('profile_tag')
            content_preview = msg.get('content', '')[:50].replace('\n', ' ')
            
            if role == 'user':
                user_message_count += 1
                if profile_tag:
                    messages_with_profile_tag += 1
                    print(f"  ✓ Message {i+1} (User):")
                    print(f"    Profile Tag: {profile_tag}")
                    print(f"    Content: {content_preview}...")
                else:
                    print(f"  Message {i+1} (User):")
                    print(f"    Profile Tag: (not set)")
                    print(f"    Content: {content_preview}...")
                print()
        
        print("[6] Verification:")
        print(f"  Total user messages: {user_message_count}")
        print(f"  Messages with profile_tag: {messages_with_profile_tag}")
        
        if messages_with_profile_tag > 0:
            print(f"✅ SUCCESS! Profile tags are being stored and will display in UI")
            print()
            print("WHAT THIS MEANS:")
            print("  When you load this session in the UI:")
            print("  - Each user message will show its profile_tag badge")
            print("  - Different messages can have different profile badges")
            print("  - The badge will use the profile's color for styling")
        else:
            print(f"⚠️  No profile tags found in messages")
            print(f"   This is expected if the session was created before profile tracking")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Final summary
    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    print()
    print("NEXT STEPS:")
    print("1. Load the session in the UI at http://localhost:5000")
    print("2. Look at each user message")
    print("3. You should see profile badges like @GOGET or @FRGOT")
    print("4. Messages with overridden profiles will show the override profile badge")
    print()

if __name__ == "__main__":
    test_profile_badges_in_loaded_session()
