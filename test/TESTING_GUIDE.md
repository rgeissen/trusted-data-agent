# How to Test Per-User Runtime Context Isolation

## ✅ Quick Test (Just Run This)

```bash
# No server needed - tests the core functions directly
python test/test_per_user_context.py
```

**Expected Result:**
```
🎉 ALL TESTS PASSED! Per-user isolation is working correctly.
Total: 8/8 tests passed
```

This validates:
- ✅ Different users can have different providers/models simultaneously
- ✅ AWS, Azure, Friendli configs are isolated per user
- ✅ MCP server configurations are isolated per user
- ✅ Global config fallback works correctly
- ✅ Persistence mode disables isolation when needed
- ✅ Concurrent access from 5+ users works without conflicts
- ✅ Old user contexts are cleaned up automatically
- ✅ Runtime context data structure is correct

---

## 🔧 Integration Test (With Running Server)

### 1. Start Server in Multi-User Mode

```bash
export TDA_CONFIGURATION_PERSISTENCE=false
export TDA_SESSIONS_FILTER_BY_USER=true
python -m trusted_data_agent.main
```

### 2. Run Integration Test

```bash
# Edit credentials first!
vim test/test_per_user_context_manual.py

# Then run
python test/test_per_user_context_manual.py
```

---

## 🎯 Quick Manual Test with curl

Test two users with different providers:

```bash
# Terminal 1: User 1 configures Amazon
curl -X POST http://localhost:5000/api/v1/configure \
  -H "Content-Type: application/json" \
  -H "X-TDA-User-UUID: alice" \
  -d '{
    "provider": "Amazon",
    "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "credentials": {"aws_access_key_id": "KEY", "aws_secret_access_key": "SECRET", "aws_region": "us-west-2"},
    "mcp_server": {"name": "test", "id": "1", "host": "localhost", "port": 3000, "path": "/sse"}
  }'

# Terminal 2: User 2 configures Google (at the same time!)
curl -X POST http://localhost:5000/api/v1/configure \
  -H "Content-Type: application/json" \
  -H "X-TDA-User-UUID: bob" \
  -d '{
    "provider": "Google",
    "model": "gemini-1.5-pro",
    "credentials": {"apiKey": "YOUR_KEY"},
    "mcp_server": {"name": "test", "id": "1", "host": "localhost", "port": 3000, "path": "/sse"}
  }'
```

Both configurations will coexist without conflicts! ✨

---

## 📋 Complete Test Documentation

See `test/TEST_PER_USER_CONTEXT.md` for:
- Detailed test procedures
- Environment variable configuration
- Debugging tips
- Performance testing
- Common issues and solutions

---

## 🚀 What's Working

- ✅ **Phases 1-3 Complete**: All core functionality implemented
- ✅ **Unit Tests Pass**: 8/8 tests passing
- ✅ **Zero Errors**: All modified files pass syntax checks
- ✅ **Backward Compatible**: Works with both persistence modes

## 📝 Next Steps

**Phase 4** (Optional enhancements):
- Add background cleanup task
- Additional low-priority file updates
- Environment variable configuration for cleanup intervals

**Production Deployment:**
- Monitor memory usage of runtime contexts
- Consider Redis for distributed deployments
- Add alerting for cleanup failures
