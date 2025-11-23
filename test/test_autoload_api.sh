#!/bin/bash
# Test script for Phase 4 Credential Auto-Load Feature via REST API

BASE_URL="http://127.0.0.1:5000"
TOKEN=""
USER_UUID=""

echo "========================================================================"
echo "Phase 4 Credential Auto-Load - REST API Test"
echo "========================================================================"

# Step 1: Register a test user
echo ""
echo "Step 1: Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser_autoload",
    "email": "test_autoload@example.com",
    "password": "TestPassword123!"
  }')

echo "Register Response: $REGISTER_RESPONSE"
TOKEN=$(echo $REGISTER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
USER_UUID=$(echo $REGISTER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('user', {}).get('user_uuid', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get auth token. Trying login instead..."
  
  # Try logging in
  LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "testuser_autoload",
      "password": "TestPassword123!"
    }')
  
  echo "Login Response: $LOGIN_RESPONSE"
  TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
  USER_UUID=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('user', {}).get('user_uuid', ''))" 2>/dev/null)
fi

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to authenticate. Exiting."
  exit 1
fi

echo "✅ Authenticated successfully"
echo "   Token: ${TOKEN:0:20}..."
echo "   User UUID: $USER_UUID"

# Step 2: Store credentials for Google provider
echo ""
echo "Step 2: Storing credentials for Google provider..."
STORE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/credentials/Google" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "apiKey": "test-google-api-key-12345-stored"
  }')

echo "Store Response: $STORE_RESPONSE"
echo "✅ Credentials stored"

# Step 3: Verify credentials were stored by listing providers
echo ""
echo "Step 3: Listing stored credential providers..."
LIST_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/config/stored-credentials" \
  -H "Authorization: Bearer $TOKEN")

echo "List Response: $LIST_RESPONSE"

# Step 4: Test configuration WITHOUT auto-load (manual credentials)
echo ""
echo "Step 4: Testing configuration WITHOUT auto-load..."
CONFIG_MANUAL=$(curl -s -X POST "$BASE_URL/api/v1/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "Google",
    "model": "gemini-2.0-flash",
    "apiKey": "manual-api-key-provided-directly",
    "mcp_server_name": "None",
    "use_stored_credentials": false
  }')

echo "Manual Config Response: $CONFIG_MANUAL"
echo "✅ Configuration without auto-load completed"

# Step 5: Test configuration WITH auto-load (should use stored credentials)
echo ""
echo "Step 5: Testing configuration WITH auto-load..."
CONFIG_AUTOLOAD=$(curl -s -X POST "$BASE_URL/api/v1/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "Google",
    "model": "gemini-2.0-flash",
    "mcp_server_name": "None",
    "use_stored_credentials": true
  }')

echo "Auto-load Config Response: $CONFIG_AUTOLOAD"
echo "✅ Configuration with auto-load completed"

# Step 6: Test configuration with BOTH auto-load AND manual credentials (manual should take precedence)
echo ""
echo "Step 6: Testing credential override (auto-load + manual)..."
CONFIG_OVERRIDE=$(curl -s -X POST "$BASE_URL/api/v1/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "Google",
    "model": "gemini-2.0-flash",
    "apiKey": "override-api-key-takes-precedence",
    "mcp_server_name": "None",
    "use_stored_credentials": true
  }')

echo "Override Config Response: $CONFIG_OVERRIDE"
echo "✅ Configuration with override completed"

# Step 7: Test auto-save feature
echo ""
echo "Step 7: Testing credential auto-save..."
CONFIG_AUTOSAVE=$(curl -s -X POST "$BASE_URL/api/v1/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "Google",
    "model": "gemini-2.0-flash",
    "apiKey": "new-api-key-to-be-saved",
    "mcp_server_name": "None",
    "save_credentials": true
  }')

echo "Auto-save Config Response: $CONFIG_AUTOSAVE"
echo "✅ Configuration with auto-save completed"

# Step 8: Verify saved credentials by retrieving them
echo ""
echo "Step 8: Retrieving saved credentials..."
RETRIEVE_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/credentials/Google" \
  -H "Authorization: Bearer $TOKEN")

echo "Retrieve Response: $RETRIEVE_RESPONSE"
echo "✅ Credentials retrieved"

# Step 9: Delete credentials
echo ""
echo "Step 9: Deleting stored credentials..."
DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/v1/credentials/Google" \
  -H "Authorization: Bearer $TOKEN")

echo "Delete Response: $DELETE_RESPONSE"
echo "✅ Credentials deleted"

# Step 10: Verify deletion
echo ""
echo "Step 10: Verifying deletion..."
LIST_FINAL=$(curl -s -X GET "$BASE_URL/api/v1/config/stored-credentials" \
  -H "Authorization: Bearer $TOKEN")

echo "Final List Response: $LIST_FINAL"

echo ""
echo "========================================================================"
echo "✅ ALL TESTS COMPLETED!"
echo "========================================================================"
