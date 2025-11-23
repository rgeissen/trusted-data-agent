# Testing Per-User Runtime Context Isolation

## Quick Start

### 1. Unit Tests (No Server Required)

Test the core helper functions directly:

```bash
# Run unit tests
python test/test_per_user_context.py
```

**What it tests:**
- ✅ Basic provider/model isolation between users
- ✅ Provider-specific configurations (AWS, Azure, Friendli)
- ✅ MCP server isolation
- ✅ Global configuration fallback
- ✅ Persistence mode behavior
- ✅ Concurrent multi-user access
- ✅ Context cleanup
- ✅ Runtime context data structure

**Expected output:**
```
================================================================================
  PER-USER RUNTIME CONTEXT ISOLATION TEST SUITE
================================================================================

✅ PASS: User 1 has Amazon provider
✅ PASS: User 1 has Claude model
✅ PASS: User 2 has Google provider
...

Total: 8/8 tests passed
🎉 ALL TESTS PASSED! Per-user isolation is working correctly.
```

### 2. Integration Tests (Server Required)

Test with the live REST API:

```bash
# Terminal 1: Start server in multi-user mode
export TDA_CONFIGURATION_PERSISTENCE=false
export TDA_SESSIONS_FILTER_BY_USER=true
python -m trusted_data_agent.main

# Terminal 2: Run integration test
python test/test_per_user_context_manual.py
```

**Before running**, update credentials in `test_per_user_context_manual.py`:
- Line 34-36: AWS credentials
- Line 63: Google API key

### 3. Manual Testing with curl

Test configuration isolation with curl commands:

```bash
# User 1: Configure Amazon Bedrock
curl -X POST http://localhost:5000/api/v1/configure \
  -H "Content-Type: application/json" \
  -H "X-TDA-User-UUID: user-1" \
  -d '{
    "provider": "Amazon",
    "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "credentials": {
      "aws_access_key_id": "YOUR_KEY",
      "aws_secret_access_key": "YOUR_SECRET",
      "aws_region": "us-west-2"
    },
    "mcp_server": {
      "name": "test-server",
      "id": "test-id",
      "host": "localhost",
      "port": 3000,
      "path": "/sse"
    }
  }'

# User 2: Configure Google Gemini (simultaneously)
curl -X POST http://localhost:5000/api/v1/configure \
  -H "Content-Type: application/json" \
  -H "X-TDA-User-UUID: user-2" \
  -d '{
    "provider": "Google",
    "model": "gemini-1.5-pro",
    "credentials": {
      "apiKey": "YOUR_GOOGLE_KEY"
    },
    "mcp_server": {
      "name": "test-server",
      "id": "test-id",
      "host": "localhost",
      "port": 3000,
      "path": "/sse"
    }
  }'

# Verify: User 1 executes with Amazon
curl -X POST http://localhost:5000/api/prompt-executor \
  -H "Content-Type: application/json" \
  -H "X-TDA-User-UUID: user-1" \
  -d '{
    "prompt": "What is 2+2? (Also mention which provider you are)",
    "active_prompt_name": null
  }'

# Verify: User 2 executes with Google
curl -X POST http://localhost:5000/api/prompt-executor \
  -H "Content-Type: application/json" \
  -H "X-TDA-User-UUID: user-2" \
  -d '{
    "prompt": "What is 2+2? (Also mention which provider you are)",
    "active_prompt_name": null
  }'
```

### 4. Test with the UI

1. **Start server in multi-user mode:**
   ```bash
   export TDA_CONFIGURATION_PERSISTENCE=false
   export TDA_SESSIONS_FILTER_BY_USER=true
   python -m trusted_data_agent.main
   ```

2. **Open two browser windows:**
   - Window 1: `http://localhost:5000` (User A)
   - Window 2: `http://localhost:5000?user_uuid=user-b` (User B)

3. **Configure different providers in each window:**
   - Window 1: Configure Amazon Bedrock
   - Window 2: Configure Google Gemini

4. **Execute prompts in both windows simultaneously:**
   - Both should use their respective configurations
   - Check browser console for `X-TDA-User-UUID` header

## Verification Checklist

### ✅ Isolation Working
- [ ] User A configures Amazon, User B configures Google
- [ ] Both configurations persist simultaneously
- [ ] User A's prompts execute with Amazon
- [ ] User B's prompts execute with Google
- [ ] No cross-contamination between users

### ✅ Session Management
- [ ] User A's sessions are isolated from User B's
- [ ] `/api/sessions` endpoint filters by user_uuid
- [ ] Session files stored in `tda_sessions/{user_uuid}/`

### ✅ Backward Compatibility
- [ ] Works with `TDA_CONFIGURATION_PERSISTENCE=true`
- [ ] Works without `X-TDA-User-UUID` header (uses global config)
- [ ] Existing functionality not broken

## Environment Variables

```bash
# Enable multi-user isolation
export TDA_CONFIGURATION_PERSISTENCE=false

# Enable session filtering by user
export TDA_SESSIONS_FILTER_BY_USER=true

# Optional: Configure cleanup (coming in Phase 4)
export TDA_USER_CONFIG_CLEANUP_INTERVAL=300    # seconds (5 min)
export TDA_USER_CONFIG_CLEANUP_TIMEOUT=1800    # seconds (30 min)
```

## Common Issues

### Issue: Both users see same configuration
**Cause:** `TDA_CONFIGURATION_PERSISTENCE=true` (persistence mode enabled)  
**Solution:** Set `TDA_CONFIGURATION_PERSISTENCE=false`

### Issue: User gets wrong provider/model
**Cause:** Missing `X-TDA-User-UUID` header in request  
**Solution:** Ensure all API calls include the header

### Issue: Contexts not cleaning up
**Cause:** Cleanup task not implemented yet (Phase 4)  
**Solution:** Manually call `cleanup_inactive_user_contexts(1800)` in Python

## Debug Commands

Check runtime contexts in Python:

```python
from trusted_data_agent.core.config import USER_RUNTIME_CONTEXTS
print(USER_RUNTIME_CONTEXTS)
```

Check current configuration:

```python
from trusted_data_agent.core.config import get_user_provider, get_user_model

user_uuid = "test-user"
print(f"Provider: {get_user_provider(user_uuid)}")
print(f"Model: {get_user_model(user_uuid)}")
```

## Performance Testing

Test with many concurrent users:

```bash
# Generate load with 10 users
for i in {1..10}; do
  curl -X POST http://localhost:5000/api/v1/configure \
    -H "X-TDA-User-UUID: load-test-user-$i" \
    -H "Content-Type: application/json" \
    -d '{"provider": "Google", "model": "gemini-pro", "credentials": {"apiKey": "test"}}' &
done
wait
```

## Next Steps

After successful testing:

1. **Phase 4**: Implement cleanup task and remaining updates
2. **Production**: Monitor `USER_RUNTIME_CONTEXTS` memory usage
3. **Optimization**: Consider Redis for distributed deployments
4. **Documentation**: Update user guide with multi-user examples

## Support

If tests fail:
1. Check server logs for errors
2. Verify environment variables are set
3. Confirm Python version >= 3.9
4. Review implementation summary: `docs/PER_USER_RUNTIME_CONTEXT_IMPLEMENTATION.md`
