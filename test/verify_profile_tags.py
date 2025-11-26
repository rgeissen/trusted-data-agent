#!/usr/bin/env python3
"""
Simple verification test that profile tags are stored per-message in sessions.
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"
API_V1_BASE = f"{BASE_URL}/api/v1"
AUTH_BASE = f"{BASE_URL}/api/v1/auth"

# Login
response = requests.post(
    f"{AUTH_BASE}/login",
    json={"username": "admin", "password": "admin"}
)
jwt_token = response.json()['token']
user_uuid = response.json()['user']['user_uuid']

# Get sessions to find one with multiple profile tags
response = requests.get(
    f"{API_V1_BASE}/sessions",
    headers={"Authorization": f"Bearer {jwt_token}"}
)

sessions = response.json().get('sessions', [])

# Find a session with profile overrides (multiple profile_tags_used)
session_with_override = None
for session in sessions:
    profile_tags = session.get('profile_tags_used', [])
    if len(profile_tags) > 1:
        session_with_override = session
        break

if not session_with_override:
    print("❌ Could not find a session with profile overrides")
    print("   Please run test_profile_override_per_message.py first to create one")
    exit(1)

print("=" * 70)
print("Profile Tags Per-Message Verification")
print("=" * 70)
print()

session_id = session_with_override.get('id')
print(f"Found session with profile overrides: {session_id}")
print(f"  Name: {session_with_override.get('name')}")
print(f"  Profile tags used: {session_with_override.get('profile_tags_used')}")
print()

# Load the session file directly
session_file = Path(f"/Users/rainer.geissendoerfer/my_private_code/trusted-data-agent/tda_sessions/{user_uuid}/{session_id}.json")

if not session_file.exists():
    print(f"❌ Session file not found: {session_file}")
    exit(1)

with open(session_file) as f:
    session_data = json.load(f)

session_history = session_data.get('session_history', [])

print(f"Session history: {len(session_history)} messages")
print()

user_messages = []
for i, msg in enumerate(session_history):
    if msg.get('role') == 'user':
        profile_tag = msg.get('profile_tag')
        content = msg.get('content', '')[:50]
        user_messages.append({
            'index': i,
            'content': content,
            'profile_tag': profile_tag
        })
        print(f"User Message {len(user_messages)}:")
        print(f"  profile_tag: {profile_tag}")
        print(f"  content: {content}...")
        print()

print("=" * 70)
if len(user_messages) > 1 and any(m['profile_tag'] for m in user_messages):
    print("✅ SUCCESS!")
    print()
    print("Profile tags are being stored per-message!")
    print()
    print("NEXT: Load the session in the UI to see the profile badges")
    print("Each message will show its own profile badge with the appropriate color")
else:
    print("⚠️  Could not verify per-message profile tags")
print()
