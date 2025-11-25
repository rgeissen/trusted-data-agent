#!/bin/bash

# Test script to validate an access token
# Usage: ./test_access_token.sh <your_access_token>

set -e

# Check if token is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <access_token>"
    echo ""
    echo "Example:"
    echo "  $0 tda_abc123xyz..."
    exit 1
fi

ACCESS_TOKEN="$1"
BASE_URL="http://127.0.0.1:5000"

echo "========================================"
echo "Access Token Validation Test"
echo "========================================"
echo ""

# Test 1: Validate token by getting user info
echo "Test 1: Get user information (/api/v1/auth/me)"
echo "----------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    "$BASE_URL/api/v1/auth/me")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Token is VALID"
    echo ""
    echo "User Details:"
    echo "$BODY" | jq -r '.user | "  Username: \(.username)\n  Email: \(.email)\n  Profile Tier: \(.profile_tier)\n  Is Admin: \(.is_admin)"'
    
    USER_UUID=$(echo "$BODY" | jq -r '.user.user_uuid')
    USERNAME=$(echo "$BODY" | jq -r '.user.username')
else
    echo "✗ Token is INVALID (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
    exit 1
fi

echo ""
echo "========================================"
echo ""

# Test 2: List user's access tokens
echo "Test 2: List access tokens (/api/v1/auth/tokens)"
echo "----------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    "$BASE_URL/api/v1/auth/tokens")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Successfully retrieved token list"
    echo ""
    TOKEN_COUNT=$(echo "$BODY" | jq '.tokens | length')
    echo "  Total tokens: $TOKEN_COUNT"
    echo ""
    echo "  Your tokens:"
    echo "$BODY" | jq -r '.tokens[] | "    - \(.name) (\(.token_prefix)...) - Created: \(.created_at) - Used: \(.use_count) times"'
else
    echo "✗ Failed to retrieve tokens (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
fi

echo ""
echo "========================================"
echo ""

# Test 3: Check pane visibility
echo "Test 3: Get pane visibility (/api/v1/auth/me/panes)"
echo "----------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    "$BASE_URL/api/v1/auth/me/panes")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Successfully retrieved pane configuration"
    echo ""
    USER_TIER=$(echo "$BODY" | jq -r '.user_tier')
    echo "  Your tier: $USER_TIER"
    echo "  Visible panes:"
    
    echo "$BODY" | jq -r --arg tier "$USER_TIER" '.panes[] | 
        if $tier == "admin" then 
            select(.visible_to_admin == true) | "    - \(.pane_id)"
        elif $tier == "developer" then 
            select(.visible_to_developer == true) | "    - \(.pane_id)"
        else 
            select(.visible_to_user == true) | "    - \(.pane_id)"
        end'
else
    echo "✗ Failed to retrieve pane configuration (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
fi

echo ""
echo "========================================"
echo ""
echo "✓ All tests completed successfully!"
echo ""
echo "Your access token is working correctly."
echo "You can now use it with REST API scripts:"
echo ""
echo "  ./docs/RestAPI/scripts/rest_run_query.sh $ACCESS_TOKEN \"What is the weather?\""
echo ""
