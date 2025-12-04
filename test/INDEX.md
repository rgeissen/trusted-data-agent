# REST API Session Creation & Authentication - Complete Resource

This directory and the updated documentation contain everything you need to understand and test session creation with both JWT and Access Token authentication methods.

## 🎯 Quick Navigation

### I Want To...

**Run the tests immediately**
- Python: `python test/test_session_creation_methods.py`
- Bash: `bash test/test_session_creation_methods.sh`

**Understand the differences**
- Read: `test/JWT_VS_ACCESS_TOKEN_GUIDE.md`

**Implement in my code**
- See: `test/JWT_VS_ACCESS_TOKEN_GUIDE.md` → Implementation Examples section
- Python examples start at line ~400
- Bash examples start at line ~450

**Debug issues**
- See: `test/TEST_SESSION_CREATION_README.md` → Troubleshooting section
- Or: `docs/RestAPI/restAPI.md` → Section 9 (Migration Notes)

**Reference the API**
- See: `docs/RestAPI/restAPI.md`
- Session Management: Section 3.4
- Query Execution: Section 3.5
- Authentication: Section 2

---

## 📚 Documentation Files

### Test & Implementation Guides

| File | Purpose | Audience |
|------|---------|----------|
| `test/TEST_SESSION_CREATION_README.md` | Quick start, running tests, troubleshooting | Anyone getting started |
| `test/JWT_VS_ACCESS_TOKEN_GUIDE.md` | Detailed comparison, flows, implementation | Developers, DevOps |
| `test/test_session_creation_methods.py` | Python test script | Python developers |
| `test/test_session_creation_methods.sh` | Bash test script | Shell scripting, CI/CD |

### API Documentation

| File | Changes |
|------|---------|
| `docs/RestAPI/restAPI.md` | Updated (v2.1.0) - Removed outdated headers, added quick start, added migration guide |

---

## 🔍 What's Been Improved

### Documentation Updates

✅ **Removed Outdated References**
- Removed 3 instances of `X-TDA-User-UUID` header from session endpoints
- These headers are no longer needed; user identity is extracted from authentication token

✅ **Added Clarity**
- New "User-Scoped Sessions" warning section explaining automatic user association
- Sessions are automatically associated with the authenticated user
- No manual UUID specification needed

✅ **Added Quick Reference**
- New "Quick Start Workflow" section with 4-step guide
- Shows complete bash example from auth to query execution
- Includes both JWT and access token examples

✅ **Added Migration Guide**
- Section 9: "API Updates & Migration Notes"
- Documents what changed and how to migrate
- Shows before/after examples
- Explains why changes were made

✅ **Standardized Paths**
- All RAG endpoints now use consistent `/api/v1/` prefix
- All authentication requirements clearly marked

### Test Scripts Created

✅ **Python Test (`test_session_creation_methods.py`)**
- 16 KB, fully commented
- Interactive prompts for credentials
- Tests JWT approach (login → session → query → status)
- Tests Access Token approach (login → token creation → session → query → status)
- Colored output for readability
- No external dependencies beyond `requests`

✅ **Bash Test (`test_session_creation_methods.sh`)**
- 11 KB, fully commented
- Uses standard tools: curl, jq
- Same test flow as Python version
- Executable permissions set
- Can be integrated into CI/CD pipelines

---

## 🚀 Getting Started

### Prerequisites

```bash
# For Python test
python3 --version  # Python 3.6+
# requests library usually pre-installed

# For Bash test
curl --version
jq --version  # Install: brew install jq (macOS) or apt-get install jq (Linux)
```

### Run a Test

```bash
# Python (recommended)
cd /Users/rainer.geissendoerfer/my_private_code/uderia
python test/test_session_creation_methods.py

# You'll be prompted for credentials, then it will:
# 1. Test JWT approach (login → session creation → query submission)
# 2. Test Access Token approach (same flow with 90-day token)
# 3. Show side-by-side comparison
```

```bash
# Bash
cd /Users/rainer.geissendoerfer/my_private_code/uderia
bash test/test_session_creation_methods.sh

# Same flow as Python, but using curl and jq
```

---

## 📋 Test Coverage

Both test scripts validate:

✅ **JWT Token Workflow**
- User login with credentials
- JWT token generation
- Session creation with JWT
- Query submission to session
- Task status checking

✅ **Access Token Workflow**
- User login with credentials (to get temporary JWT)
- Long-lived access token creation
- Session creation with access token
- Query submission to session
- Task status checking

✅ **User Scoping**
- Each user sees only their own sessions
- Sessions cannot be accessed by other users
- No custom headers needed

---

## 💡 Key Findings

### Both Methods Work Identically

For session creation and query execution:
- Same endpoints: `POST /api/v1/sessions`, `POST /api/v1/sessions/{id}/query`
- Same response format
- Same error handling
- Same user-scoping behavior

### Differences Are Only in Lifecycle

| Aspect | JWT | Access Token |
|--------|-----|--------------|
| **Lifetime** | 24 hours | 30/90/180/365 days or never |
| **Created** | `POST /auth/login` | `POST /api/v1/auth/tokens` |
| **Storage** | Client localStorage | Database (hashed) |
| **Retrieval** | Anytime by login | Only once (at creation!) |
| **Best for** | Interactive use | Automation |

### No More X-TDA-User-UUID Header

- **Old way**: `curl -H "X-TDA-User-UUID: user-id" -H "Authorization: Bearer $TOKEN"`
- **New way**: `curl -H "Authorization: Bearer $TOKEN"`
- User identity is now automatically extracted from the token

---

## 🎯 Use Cases

### Choose JWT When:
- Interactive web UI sessions
- Browser-based applications  
- Short-lived API testing
- One-off queries

### Choose Access Token When:
- Scheduled automation / cron jobs
- CI/CD pipelines
- Microservice integration
- Unattended processes
- Multiple environments

---

## 🔐 Security Notes

**JWT Tokens:**
- Short-lived (24 hours) by default
- Stateless (no server storage)
- Can be revoked via blacklist if needed
- Suitable for interactive use

**Access Tokens:**
- Long-lived (30-365 days or never)
- Hashed storage in database
- Can be individually revoked anytime
- Trackable in audit logs
- Better for unattended automation

---

## 📖 Full Documentation Index

### If You Want To...

**Understand JWT token generation**
→ `docs/RestAPI/restAPI.md` section 2.1 or `test/JWT_VS_ACCESS_TOKEN_GUIDE.md` section "JWT Token Generation"

**Understand access token flow**
→ `docs/RestAPI/restAPI.md` section 2.1 or `test/JWT_VS_ACCESS_TOKEN_GUIDE.md` section "Access Token Flow"

**Learn about session management**
→ `docs/RestAPI/restAPI.md` section 3.4

**Execute queries through REST**
→ `docs/RestAPI/restAPI.md` section 3.5

**Implement in Python**
→ `test/JWT_VS_ACCESS_TOKEN_GUIDE.md` - Python Examples

**Implement in Bash**
→ `test/JWT_VS_ACCESS_TOKEN_GUIDE.md` - Bash Examples

**Migrate from old approach**
→ `docs/RestAPI/restAPI.md` section 9 - Migration Guide

**Troubleshoot issues**
→ `test/TEST_SESSION_CREATION_README.md` - Troubleshooting section

---

## ✅ Files Included

```
test/
├── test_session_creation_methods.py       (16 KB) - Python test script
├── test_session_creation_methods.sh       (11 KB) - Bash test script
├── TEST_SESSION_CREATION_README.md        Quick start & troubleshooting
├── JWT_VS_ACCESS_TOKEN_GUIDE.md           Comprehensive comparison
└── THIS_FILE                               (index/overview)

docs/RestAPI/
└── restAPI.md                              (Updated, v2.1.0)
```

---

## 🎓 Learning Path

1. **Start here**: `test/TEST_SESSION_CREATION_README.md`
2. **Run a test**: `python test/test_session_creation_methods.py`
3. **Understand differences**: `test/JWT_VS_ACCESS_TOKEN_GUIDE.md`
4. **See implementation**: Look at code examples in the guide
5. **Reference the API**: `docs/RestAPI/restAPI.md` sections 2, 3.4, 3.5

---

## 🆘 Troubleshooting

### Test fails with "Login failed: 401"
- Check username and password are correct
- Verify the user account exists and isn't locked

### "Cannot connect to server"
- Start the server: `python -m trusted_data_agent.main`
- Check the URL is correct (default: `http://localhost:5000`)

### "jq: command not found" (Bash test)
- Install: `brew install jq` (macOS) or `sudo apt-get install jq` (Ubuntu)

### "Session creation failed"
- Ensure authentication token is valid
- Check server logs for details

For more troubleshooting, see `test/TEST_SESSION_CREATION_README.md`

---

## 📞 Support

This testing and documentation package provides everything needed for:
- ✅ Understanding both authentication methods
- ✅ Testing them locally
- ✅ Implementing them in your code
- ✅ Migrating from old approaches
- ✅ Troubleshooting issues

All test scripts and guides are self-contained and include detailed comments and examples.

---

**Last Updated**: November 26, 2025  
**Documentation Version**: v2.1.0  
**Status**: Production-ready ✅
