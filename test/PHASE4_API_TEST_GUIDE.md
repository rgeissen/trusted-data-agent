# Phase 4 Credential Auto-Load - Manual Test Guide

Server is running at: http://127.0.0.1:5000

## Test Sequence

### 1. Register/Login
```bash
# Register a new user
curl -X POST "http://127.0.0.1:5000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser_phase4",
    "email": "phase4@test.com",
    "password": "TestPass123!"
  }'

# Save the token from response
export TOKEN="<your-token-here>"
```

### 2. Store Credentials
```bash
# Store Google credentials
curl -X POST "http://127.0.0.1:5000/api/v1/credentials/Google" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "apiKey": "stored-test-api-key-12345"
  }'
```

### 3. List Stored Credentials (Metadata Only)
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/config/stored-credentials" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Test Auto-Load (use_stored_credentials=true)
```bash
# Configure WITHOUT providing credentials - should auto-load from storage
curl -X POST "http://127.0.0.1:5000/api/v1/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "Google",
    "model": "gemini-2.0-flash",
    "mcp_server_name": "None",
    "use_stored_credentials": true
  }'
```

### 5. Test Credential Override
```bash
# Provide manual credentials WITH auto-load - manual should take precedence
curl -X POST "http://127.0.0.1:5000/api/v1/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "Google",
    "model": "gemini-2.0-flash",
    "apiKey": "manual-override-key-99999",
    "mcp_server_name": "None",
    "use_stored_credentials": true
  }'
```

### 6. Test Auto-Save
```bash
# Save new credentials during configuration
curl -X POST "http://127.0.0.1:5000/api/v1/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "Google",
    "model": "gemini-2.0-flash",
    "apiKey": "new-api-key-to-save",
    "mcp_server_name": "None",
    "save_credentials": true
  }'
```

### 7. Retrieve Stored Credentials
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/credentials/Google" \
  -H "Authorization: Bearer $TOKEN"
```

### 8. Delete Credentials
```bash
curl -X DELETE "http://127.0.0.1:5000/api/v1/credentials/Google" \
  -H "Authorization: Bearer $TOKEN"
```

### 9. Verify Deletion
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/config/stored-credentials" \
  -H "Authorization: Bearer $TOKEN"
```

## Expected Results

**Step 2:** Should return `{"success": true, "message": "Credentials stored successfully"}`

**Step 3:** Should return `{"providers": ["Google"], "credentials": {"Google": ["apiKey"]}}`

**Step 4:** Configuration should succeed using stored credentials (check server logs for "Retrieved stored credentials")

**Step 5:** Configuration should use manual "manual-override-key-99999" instead of stored credentials

**Step 6:** Configuration should succeed AND save the new credentials

**Step 7:** Should return the decrypted credentials: `{"credentials": {"apiKey": "new-api-key-to-save"}}`

**Step 8:** Should return `{"success": true, "message": "Credentials deleted successfully"}`

**Step 9:** Should return empty providers list: `{"providers": [], "credentials": {}}`

## Success Criteria

✅ Credentials stored and encrypted in database
✅ Auto-load retrieves stored credentials during configuration
✅ Manual credentials override stored credentials (precedence)
✅ Auto-save stores credentials during configuration
✅ Metadata endpoint returns provider list without exposing credential values
✅ Delete operation removes stored credentials
✅ User isolation works (each user has separate credential storage)
