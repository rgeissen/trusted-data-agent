#!/usr/bin/env python3
"""
Test REST API with JWT Authentication

This script tests the REST API endpoints using JWT token authentication.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_rest_api_with_jwt():
    """Test REST API endpoints with JWT authentication."""
    
    print("=" * 60)
    print("REST API JWT Authentication Test")
    print("=" * 60)
    print()
    
    # Step 1: Get credentials from user
    print("Please provide your credentials:")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    print()
    
    # Step 2: Login to get JWT token
    print("[1] Logging in to get JWT token...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        data = response.json()
        jwt_token = data.get('token')
        
        if not jwt_token:
            print("❌ No token in response")
            return False
        
        print(f"✓ Login successful")
        print(f"  Token: {jwt_token[:30]}...")
        print()
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Step 3: Test REST API status endpoint
    print("[2] Testing /api/status with JWT...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/status",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status endpoint works")
            print(f"  Configured: {data.get('isConfigured')}")
            print(f"  User authenticated: {data.get('authenticationRequired')}")
        else:
            print(f"❌ Status failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
        print()
        
    except Exception as e:
        print(f"❌ Status error: {e}")
    
    # Step 4: Test user profile endpoint
    print("[3] Testing /api/v1/auth/me with JWT...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            user = data.get('user', {})
            print(f"✓ Profile endpoint works")
            print(f"  Username: {user.get('username')}")
            print(f"  Email: {user.get('email')}")
            print(f"  User UUID: {user.get('user_uuid')}")
            print(f"  Profile Tier: {user.get('profile_tier')}")
            print(f"  Is Admin: {user.get('is_admin')}")
        else:
            print(f"❌ Profile failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
        print()
        
    except Exception as e:
        print(f"❌ Profile error: {e}")
    
    # Step 5: List MCP resources (if configured)
    print("[4] Testing /api/resources with JWT...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/resources",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            resources = data.get('resources', [])
            print(f"✓ Resources endpoint works")
            print(f"  Found {len(resources)} resource(s)")
            if resources:
                for i, res in enumerate(resources[:3], 1):
                    print(f"    {i}. {res.get('name')} ({res.get('mimeType', 'N/A')})")
        else:
            print(f"⚠️  Resources endpoint: {response.status_code}")
            print(f"   (This is normal if MCP is not configured)")
        print()
        
    except Exception as e:
        print(f"⚠️  Resources error: {e}")
        print(f"   (This is normal if MCP is not configured)")
        print()
    
    # Step 6: List prompts (if configured)
    print("[5] Testing /api/prompts with JWT...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/prompts",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            prompts = data.get('prompts', [])
            print(f"✓ Prompts endpoint works")
            print(f"  Found {len(prompts)} prompt(s)")
            if prompts:
                for i, prompt in enumerate(prompts[:3], 1):
                    print(f"    {i}. {prompt.get('name')}")
        else:
            print(f"⚠️  Prompts endpoint: {response.status_code}")
            print(f"   (This is normal if MCP is not configured)")
        print()
        
    except Exception as e:
        print(f"⚠️  Prompts error: {e}")
        print(f"   (This is normal if MCP is not configured)")
        print()
    
    print("=" * 60)
    print("✅ REST API JWT authentication test complete!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        test_rest_api_with_jwt()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
