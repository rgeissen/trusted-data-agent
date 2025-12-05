#!/usr/bin/env python3
"""Debug test to check session data structure."""

import requests
import json

BASE_URL = "http://127.0.0.1:5050"
API_V1_BASE = f"{BASE_URL}/api/v1"
AUTH_BASE = f"{BASE_URL}/api/v1/auth"

response = requests.post(
    f"{AUTH_BASE}/login",
    json={"username": "admin", "password": "admin"}
)

jwt_token = response.json()['token']

# Get sessions
response = requests.get(
    f"{API_V1_BASE}/sessions",
    headers={"Authorization": f"Bearer {jwt_token}"}
)

print("Sessions response:")
print(json.dumps(response.json(), indent=2))
