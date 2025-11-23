# Phase 3 Security - Manual Testing Guide

This guide provides step-by-step instructions for manually testing Phase 3 security features.

---

## Prerequisites

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   # Generate a secure encryption key
   export TDA_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   
   # Enable security features
   export TDA_AUTH_ENABLED=true
   export TDA_RATE_LIMIT_ENABLED=true
   export TDA_AUDIT_LOGGING_ENABLED=true
   
   # JWT secret (if not already set)
   export TDA_JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

3. **Initialize database**:
   ```bash
   cd /Users/rainergeissendoerfer/my_private_code/trusted-data-agent
   python -c "from trusted_data_agent.auth.database import init_db; init_db()"
   ```

---

## Test 1: Credential Encryption

### 1.1 Test Encryption/Decryption

Open Python REPL:
```bash
python
```

```python
import os
os.environ['TDA_ENCRYPTION_KEY'] = 'test-key-for-manual-testing'

from trusted_data_agent.auth import encryption

# Test data
user_id = "user-123"
provider = "Amazon"
credentials = {
    "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "region": "us-west-2"
}

# Encrypt
result = encryption.encrypt_credentials(user_id, provider, credentials)
print(f"Encryption result: {result}")  # Should be True

# Decrypt
decrypted = encryption.decrypt_credentials(user_id, provider)
print(f"Decrypted: {decrypted}")  # Should match original

# Verify user isolation
other_user = encryption.decrypt_credentials("other-user", provider)
print(f"Other user access: {other_user}")  # Should be None

# List providers
providers = encryption.list_user_providers(user_id)
print(f"User providers: {providers}")  # Should contain "Amazon"
```

**Expected Results**:
- ✅ Encryption returns `True`
- ✅ Decrypted credentials match original
- ✅ Other users cannot access credentials
- ✅ Provider list shows "Amazon"

### 1.2 Test Database Storage

```python
from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import UserCredential

with get_db_session() as session:
    creds = session.query(UserCredential).filter_by(
        user_id=user_id, 
        provider=provider
    ).first()
    
    print(f"Stored credential ID: {creds.id}")
    print(f"Encrypted data (first 50 chars): {creds.credentials_encrypted[:50]}...")
    print(f"Created at: {creds.created_at}")
```

**Expected Results**:
- ✅ Credential found in database
- ✅ Data is encrypted (gibberish string)
- ✅ Timestamps present

---

## Test 2: Rate Limiting

### 2.1 Test Basic Rate Limit

```python
from trusted_data_agent.auth import rate_limiter

identifier = "test-user"
limit = 5
window = 10  # seconds

# Make 5 requests (should all be allowed)
for i in range(5):
    allowed, retry = rate_limiter.check_rate_limit(identifier, limit, window)
    print(f"Request {i+1}: Allowed={allowed}, Retry={retry}")

# 6th request (should be blocked)
allowed, retry = rate_limiter.check_rate_limit(identifier, limit, window)
print(f"Request 6: Allowed={allowed}, Retry after {retry}s")
```

**Expected Results**:
- ✅ First 5 requests allowed
- ✅ 6th request blocked
- ✅ Retry-after time provided

### 2.2 Test Token Refill

```python
import time

# Wait for tokens to refill
print("Waiting 3 seconds for token refill...")
time.sleep(3)

# Should be allowed now
allowed, retry = rate_limiter.check_rate_limit(identifier, limit, window)
print(f"After wait: Allowed={allowed}")
```

**Expected Results**:
- ✅ Request allowed after waiting

### 2.3 Test User Quotas

```python
# Test prompt quota
allowed, msg = rate_limiter.check_user_prompt_quota("user-123")
print(f"Prompt quota: Allowed={allowed}, Message={msg}")

# Test config quota
allowed, msg = rate_limiter.check_user_config_quota("user-123")
print(f"Config quota: Allowed={allowed}, Message={msg}")
```

**Expected Results**:
- ✅ Both quotas initially allowed
- ✅ Empty message when allowed

### 2.4 Test IP Rate Limits

```python
# Test login limit
allowed, retry = rate_limiter.check_ip_login_limit("192.168.1.1")
print(f"IP login limit: Allowed={allowed}")

# Test register limit
allowed, retry = rate_limiter.check_ip_register_limit("192.168.1.1")
print(f"IP register limit: Allowed={allowed}")
```

**Expected Results**:
- ✅ Both initially allowed

---

## Test 3: Audit Logging

### 3.1 Test Basic Logging

```python
from trusted_data_agent.auth import audit

# Log some events
audit.log_login_success("user-123", "testuser")
audit.log_configuration_change("user-123", "Amazon", "Updated credentials")
audit.log_prompt_execution("user-123", "session-456", "Test query")
audit.log_security_event("user-123", "test_event", "Test security event")

print("✅ Events logged")
```

### 3.2 Test Retrieving Logs

```python
# Get user logs
logs = audit.get_user_audit_logs("user-123", limit=10)
print(f"\nFound {len(logs)} audit log entries:")

for log in logs[:3]:  # Show first 3
    print(f"\n- Action: {log['action']}")
    print(f"  Status: {log['status']}")
    print(f"  Details: {log['details']}")
    print(f"  Timestamp: {log['timestamp']}")
```

**Expected Results**:
- ✅ Multiple logs retrieved
- ✅ Correct action types
- ✅ Proper timestamps

### 3.3 Test Database Storage

```python
from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import AuditLog

with get_db_session() as session:
    count = session.query(AuditLog).filter_by(user_id="user-123").count()
    print(f"Total audit logs for user: {count}")
    
    # Get latest log
    latest = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
    print(f"\nLatest log:")
    print(f"  Action: {latest.action}")
    print(f"  Details: {latest.details}")
    print(f"  IP: {latest.ip_address}")
```

**Expected Results**:
- ✅ Logs stored in database
- ✅ All fields populated correctly

---

## Test 4: API Integration

### 4.1 Test Registration with Rate Limiting

Start the server:
```bash
export TDA_RATE_LIMIT_ENABLED=true
python -m trusted_data_agent.main
```

In another terminal:
```bash
# First registration (should succeed)
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser1",
    "email": "test1@example.com",
    "password": "SecurePass123"
  }'

# Rapid registrations (should hit rate limit after 3)
for i in {2..5}; do
  curl -X POST http://localhost:5000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"testuser$i\",
      \"email\": \"test$i@example.com\",
      \"password\": \"SecurePass123\"
    }"
  sleep 0.5
done
```

**Expected Results**:
- ✅ First 3 registrations succeed
- ✅ 4th registration gets 429 error (rate limit exceeded)
- ✅ Response includes `retry_after` field

### 4.2 Test Login with Rate Limiting

```bash
# Rapid login attempts (should hit rate limit after 5)
for i in {1..7}; do
  curl -X POST http://localhost:5000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "username": "testuser1",
      "password": "WrongPassword"
    }'
  echo ""
  sleep 0.5
done
```

**Expected Results**:
- ✅ First 5 attempts get 401 (invalid credentials)
- ✅ 6th attempt gets 429 (rate limit exceeded)

### 4.3 Verify Audit Logs

After running API tests:
```python
from trusted_data_agent.auth import audit
from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import AuditLog

with get_db_session() as session:
    # Check for registration attempts
    reg_logs = session.query(AuditLog).filter(
        AuditLog.action.like('%registration%')
    ).all()
    print(f"Registration logs: {len(reg_logs)}")
    
    # Check for login attempts
    login_logs = session.query(AuditLog).filter(
        AuditLog.action.like('%login%')
    ).all()
    print(f"Login logs: {len(login_logs)}")
    
    # Check for rate limit violations
    rate_logs = session.query(AuditLog).filter(
        AuditLog.action == 'rate_limit_exceeded'
    ).all()
    print(f"Rate limit violations: {len(rate_logs)}")
```

**Expected Results**:
- ✅ All API attempts logged
- ✅ Rate limit violations recorded
- ✅ Proper timestamps and IP addresses

---

## Test 5: Security Validation

### 5.1 Test User Isolation

```python
from trusted_data_agent.auth import encryption

# User A stores credentials
encryption.encrypt_credentials("user-a", "Amazon", {"key": "user-a-secret"})

# User B tries to access User A's credentials
result = encryption.decrypt_credentials("user-b", "Amazon")
print(f"User B accessing User A's creds: {result}")  # Should be None

# User B stores their own credentials
encryption.encrypt_credentials("user-b", "Amazon", {"key": "user-b-secret"})
result = encryption.decrypt_credentials("user-b", "Amazon")
print(f"User B accessing their own creds: {result}")  # Should work
```

**Expected Results**:
- ✅ User B cannot access User A's credentials
- ✅ Each user accesses only their own data

### 5.2 Test Key Security

```python
from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import UserCredential

with get_db_session() as session:
    cred = session.query(UserCredential).first()
    
    # Verify encrypted data is not readable
    print(f"Encrypted data: {cred.credentials_encrypted[:100]}...")
    
    # Should look like random base64 data
    assert not "secret" in cred.credentials_encrypted.lower()
    assert not "password" in cred.credentials_encrypted.lower()
    print("✅ Credentials properly encrypted in database")
```

---

## Test 6: Performance Tests

### 6.1 Test Encryption Performance

```python
import time
from trusted_data_agent.auth import encryption

credentials = {"key": "value" * 100}  # Medium-sized credential

start = time.time()
for i in range(100):
    encryption.encrypt_credentials(f"user-{i}", "TestProvider", credentials)
encrypt_time = time.time() - start

start = time.time()
for i in range(100):
    encryption.decrypt_credentials(f"user-{i}", "TestProvider")
decrypt_time = time.time() - start

print(f"Encryption: 100 operations in {encrypt_time:.2f}s ({encrypt_time*10:.2f}ms avg)")
print(f"Decryption: 100 operations in {decrypt_time:.2f}s ({decrypt_time*10:.2f}ms avg)")
```

**Expected Results**:
- ✅ Encryption < 50ms per operation
- ✅ Decryption < 50ms per operation

### 6.2 Test Rate Limiter Performance

```python
import time
from trusted_data_agent.auth import rate_limiter

start = time.time()
for i in range(1000):
    rate_limiter.check_rate_limit(f"user-{i % 100}", 100, 3600)
elapsed = time.time() - start

print(f"Rate limit checks: 1000 operations in {elapsed:.2f}s ({elapsed:.2f}ms avg)")
```

**Expected Results**:
- ✅ < 1ms per check
- ✅ Scales with concurrent users

---

## Cleanup

After testing:

```python
# Clean up test data
from trusted_data_agent.auth import encryption

# Delete test credentials
encryption.delete_all_user_credentials("user-123")

# Or delete database entirely
import os
if os.path.exists('tda_auth.db'):
    os.remove('tda_auth.db')
    print("✅ Test database deleted")
```

---

## Troubleshooting

### Issue: "No module named 'cryptography'"
**Solution**: 
```bash
pip install cryptography
```

### Issue: "ENCRYPTION_KEY not set" warning
**Solution**:
```bash
export TDA_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### Issue: Rate limiting not working
**Solution**:
```bash
export TDA_RATE_LIMIT_ENABLED=true
```

### Issue: Audit logs not created
**Solution**:
```bash
export TDA_AUDIT_LOGGING_ENABLED=true
# Restart application
```

---

## Success Criteria

Phase 3 is working correctly if:

- ✅ Credentials encrypted/decrypted successfully
- ✅ Users cannot access each other's credentials
- ✅ Rate limiting blocks excessive requests
- ✅ Token refill allows requests after waiting
- ✅ All API attempts logged in audit table
- ✅ Security events properly recorded
- ✅ Performance meets expectations
- ✅ No credentials visible in database

---

**Need Help?** Check logs in `logs/` directory or enable debug logging:
```bash
export TDA_LOG_LEVEL=DEBUG
python -m trusted_data_agent.main
```
