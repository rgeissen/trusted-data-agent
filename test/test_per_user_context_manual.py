#!/usr/bin/env python3
"""
Manual test script for per-user runtime context with live REST API.

This script simulates two users configuring different providers simultaneously
and executing prompts to verify isolation.

Prerequisites:
    1. Start the TDA server with multi-user mode:
       export TDA_CONFIGURATION_PERSISTENCE=false
       export TDA_SESSIONS_FILTER_BY_USER=true
       python -m trusted_data_agent.main

    2. Run this test script:
       python test/test_per_user_context_manual.py
"""

import asyncio
import httpx
import json
from datetime import datetime


BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api/v1"


async def test_two_users_different_configs():
    """Test two users with different provider configurations."""
    
    print("\n" + "="*80)
    print("  MANUAL TEST: Two Users with Different Configurations")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # ===== USER 1: Configure Amazon Bedrock =====
        print("👤 USER 1: Configuring Amazon Bedrock...")
        user1_uuid = "test-user-amazon"
        user1_config = {
            "provider": "Amazon",
            "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "credentials": {
                "aws_access_key_id": "YOUR_AWS_KEY",  # Replace with actual
                "aws_secret_access_key": "YOUR_AWS_SECRET",  # Replace with actual
                "aws_region": "us-west-2"
            },
            "mcp_server": {
                "name": "sqlite-mcp",
                "id": "sqlite-server-id",
                "host": "localhost",
                "port": 3000,
                "path": "/sse"
            }
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/configure",
                json=user1_config,
                headers={"X-TDA-User-UUID": user1_uuid}
            )
            if response.status_code == 200:
                print(f"   ✅ User 1 configured: Amazon Bedrock / Claude")
            else:
                print(f"   ❌ User 1 config failed: {response.text}")
                return
        except Exception as e:
            print(f"   ❌ User 1 config error: {e}")
            return
        
        # Small delay
        await asyncio.sleep(0.5)
        
        # ===== USER 2: Configure Google Gemini =====
        print("\n👤 USER 2: Configuring Google Gemini...")
        user2_uuid = "test-user-google"
        user2_config = {
            "provider": "Google",
            "model": "gemini-1.5-pro",
            "credentials": {
                "apiKey": "YOUR_GOOGLE_API_KEY"  # Replace with actual
            },
            "mcp_server": {
                "name": "postgres-mcp",
                "id": "postgres-server-id",
                "host": "localhost",
                "port": 3001,
                "path": "/sse"
            }
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/configure",
                json=user2_config,
                headers={"X-TDA-User-UUID": user2_uuid}
            )
            if response.status_code == 200:
                print(f"   ✅ User 2 configured: Google / Gemini")
            else:
                print(f"   ❌ User 2 config failed: {response.text}")
                return
        except Exception as e:
            print(f"   ❌ User 2 config error: {e}")
            return
        
        # ===== VERIFY: Execute prompts for both users =====
        print("\n" + "="*80)
        print("  VERIFICATION: Executing prompts to check isolation")
        print("="*80 + "\n")
        
        # User 1 executes prompt
        print("👤 USER 1: Executing prompt...")
        user1_prompt = {
            "prompt": "What provider and model are you using? Just state the provider and model name.",
            "active_prompt_name": None
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/prompt-executor",
                json=user1_prompt,
                headers={"X-TDA-User-UUID": user1_uuid}
            )
            if response.status_code == 200:
                result = response.json()
                # Look for the response in the result
                final_response = result.get('final_response', result.get('response', 'No response'))
                print(f"   Response: {final_response[:200]}")
                
                # Check if response mentions Amazon/Claude
                has_amazon = "amazon" in final_response.lower() or "bedrock" in final_response.lower()
                has_claude = "claude" in final_response.lower()
                
                if has_amazon or has_claude:
                    print(f"   ✅ User 1 correctly using Amazon/Claude")
                else:
                    print(f"   ⚠️  User 1 response doesn't clearly indicate Amazon/Claude")
            else:
                print(f"   ❌ User 1 prompt failed: {response.text}")
        except Exception as e:
            print(f"   ❌ User 1 prompt error: {e}")
        
        await asyncio.sleep(0.5)
        
        # User 2 executes prompt
        print("\n👤 USER 2: Executing prompt...")
        user2_prompt = {
            "prompt": "What provider and model are you using? Just state the provider and model name.",
            "active_prompt_name": None
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/prompt-executor",
                json=user2_prompt,
                headers={"X-TDA-User-UUID": user2_uuid}
            )
            if response.status_code == 200:
                result = response.json()
                final_response = result.get('final_response', result.get('response', 'No response'))
                print(f"   Response: {final_response[:200]}")
                
                # Check if response mentions Google/Gemini
                has_google = "google" in final_response.lower()
                has_gemini = "gemini" in final_response.lower()
                
                if has_google or has_gemini:
                    print(f"   ✅ User 2 correctly using Google/Gemini")
                else:
                    print(f"   ⚠️  User 2 response doesn't clearly indicate Google/Gemini")
            else:
                print(f"   ❌ User 2 prompt failed: {response.text}")
        except Exception as e:
            print(f"   ❌ User 2 prompt error: {e}")
        
        print("\n" + "="*80)
        print("  TEST COMPLETE")
        print("="*80)
        print("\n💡 If both users got responses indicating their respective")
        print("   providers/models, per-user isolation is working correctly!")
        print("\n")


async def test_check_server_status():
    """Quick test to check if server is running and in multi-user mode."""
    
    print("\n" + "="*80)
    print("  SERVER STATUS CHECK")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Try to access the main page
            response = await client.get(BASE_URL)
            if response.status_code == 200:
                print("✅ Server is running at", BASE_URL)
            else:
                print(f"⚠️  Server responded with status {response.status_code}")
                return False
        except httpx.ConnectError:
            print(f"❌ Cannot connect to server at {BASE_URL}")
            print("\n   Please start the server with:")
            print("   export TDA_CONFIGURATION_PERSISTENCE=false")
            print("   export TDA_SESSIONS_FILTER_BY_USER=true")
            print("   python -m trusted_data_agent.main")
            return False
        except Exception as e:
            print(f"❌ Error checking server: {e}")
            return False
    
    return True


async def main():
    """Run the manual test."""
    
    print("\n🧪 Per-User Runtime Context - Manual Test")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if server is running
    if not await test_check_server_status():
        return
    
    print("\n⚠️  IMPORTANT: Update the credentials in this script before running!")
    print("   - Line 34-36: AWS credentials for User 1")
    print("   - Line 63: Google API key for User 2")
    
    response = input("\n   Continue with test? (y/n): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        return
    
    # Run the test
    await test_two_users_different_configs()


if __name__ == "__main__":
    asyncio.run(main())
