"""
Test suite for Phase 3 Security Hardening features.

Tests credential encryption, rate limiting, and audit logging.
"""

import os
import sys
import time
import json
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables before imports
os.environ['TDA_ENCRYPTION_KEY'] = 'test-encryption-key-do-not-use-in-production'
os.environ['TDA_RATE_LIMIT_ENABLED'] = 'true'
os.environ['TDA_AUDIT_LOGGING_ENABLED'] = 'true'
os.environ['TDA_AUTH_DB_URL'] = 'sqlite:///./test_auth.db'

from trusted_data_agent.auth import encryption, rate_limiter, audit
from trusted_data_agent.auth.database import init_database, get_db_session
from trusted_data_agent.auth.models import User, AuditLog, UserCredential
from trusted_data_agent.auth.security import hash_password


def create_test_user(user_id: str, username: str):
    """Create a test user in the database."""
    with get_db_session() as session:
        # Check if user already exists
        existing = session.query(User).filter_by(id=user_id).first()
        if not existing:
            user = User(
                id=user_id,
                username=username,
                email=f"{username}@test.com",
                password_hash=hash_password("test_password"),
                user_uuid=user_id,  # Use same UUID
                is_active=True
            )
            session.add(user)


def setup_test_db():
    """Initialize test database."""
    print("\n🔧 Setting up test database...")
    if os.path.exists('test_auth.db'):
        os.remove('test_auth.db')
    init_database()
    print("✅ Test database initialized")


def cleanup_test_db():
    """Clean up test database."""
    print("\n🧹 Cleaning up test database...")
    if os.path.exists('test_auth.db'):
        os.remove('test_auth.db')
    print("✅ Test database cleaned up")


def test_credential_encryption():
    """Test credential encryption and decryption."""
    print("\n" + "="*70)
    print("TEST 1: Credential Encryption")
    print("="*70)
    
    user_id = "test-user-123"
    
    # Create test user first
    print("\n📝 Creating test user...")
    create_test_user(user_id, "testuser123")
    print("✅ Test user created")
    
    provider = "Amazon"
    credentials = {
        "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "region": "us-west-2"
    }
    
    # Test encryption
    print("\n📝 Test 1.1: Encrypting credentials...")
    result = encryption.encrypt_credentials(user_id, provider, credentials)
    assert result, "❌ Encryption failed"
    print("✅ Credentials encrypted successfully")
    
    # Test decryption
    print("\n📝 Test 1.2: Decrypting credentials...")
    decrypted = encryption.decrypt_credentials(user_id, provider)
    assert decrypted is not None, "❌ Decryption failed"
    assert decrypted == credentials, "❌ Decrypted data doesn't match original"
    print(f"✅ Credentials decrypted successfully")
    print(f"   Original keys: {list(credentials.keys())}")
    print(f"   Decrypted keys: {list(decrypted.keys())}")
    
    # Test user isolation
    print("\n📝 Test 1.3: Testing user isolation...")
    other_user_id = "test-user-456"
    create_test_user(other_user_id, "testuser456")
    other_creds = encryption.decrypt_credentials(other_user_id, provider)
    assert other_creds is None, "❌ User isolation failed - got other user's credentials!"
    print("✅ User isolation working - users cannot access each other's credentials")
    
    # Test provider isolation
    print("\n📝 Test 1.4: Testing provider isolation...")
    other_provider = "Google"
    other_provider_creds = encryption.decrypt_credentials(user_id, other_provider)
    assert other_provider_creds is None, "❌ Provider isolation failed"
    print("✅ Provider isolation working")
    
    # Test update
    print("\n📝 Test 1.5: Updating credentials...")
    updated_credentials = {
        "aws_access_key_id": "AKIAIOSFODNN7UPDATED",
        "aws_secret_access_key": "NEW_SECRET_KEY",
        "region": "eu-west-1"
    }
    result = encryption.encrypt_credentials(user_id, provider, updated_credentials)
    assert result, "❌ Update failed"
    
    decrypted_updated = encryption.decrypt_credentials(user_id, provider)
    assert decrypted_updated == updated_credentials, "❌ Updated credentials don't match"
    print("✅ Credentials updated successfully")
    
    # Test list providers
    print("\n📝 Test 1.6: Listing user providers...")
    providers = encryption.list_user_providers(user_id)
    assert provider in providers, "❌ Provider not in list"
    print(f"✅ User has credentials for providers: {providers}")
    
    # Test deletion
    print("\n📝 Test 1.7: Deleting credentials...")
    result = encryption.delete_credentials(user_id, provider)
    assert result, "❌ Deletion failed"
    
    deleted_check = encryption.decrypt_credentials(user_id, provider)
    assert deleted_check is None, "❌ Credentials still exist after deletion"
    print("✅ Credentials deleted successfully")
    
    print("\n✅ ALL ENCRYPTION TESTS PASSED!")


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n" + "="*70)
    print("TEST 2: Rate Limiting")
    print("="*70)
    
    # Test basic rate limiting
    print("\n📝 Test 2.1: Basic rate limit check...")
    identifier = "test-user-rate"
    limit = 5
    window = 10  # 10 seconds
    
    # Should allow first 5 requests
    for i in range(limit):
        allowed, retry_after = rate_limiter.check_rate_limit(identifier, limit, window)
        assert allowed, f"❌ Request {i+1} should be allowed"
        print(f"✅ Request {i+1}/{limit} allowed")
    
    # 6th request should be blocked
    print("\n📝 Test 2.2: Blocking over-limit requests...")
    allowed, retry_after = rate_limiter.check_rate_limit(identifier, limit, window)
    assert not allowed, "❌ Request should be rate limited"
    print(f"✅ Request blocked - retry after {retry_after} seconds")
    
    # Test token refill
    print("\n📝 Test 2.3: Testing token refill...")
    print(f"   Waiting 3 seconds for token refill...")
    time.sleep(3)
    
    allowed, retry_after = rate_limiter.check_rate_limit(identifier, limit, window)
    assert allowed, "❌ Request should be allowed after token refill"
    print("✅ Token refill working - request allowed after wait")
    
    # Test reset
    print("\n📝 Test 2.4: Testing rate limit reset...")
    rate_limiter.reset_rate_limits(identifier)
    allowed, retry_after = rate_limiter.check_rate_limit(identifier, limit, window)
    assert allowed, "❌ Request should be allowed after reset"
    print("✅ Rate limit reset working")
    
    # Test different buckets
    print("\n📝 Test 2.5: Testing separate buckets...")
    allowed1, _ = rate_limiter.check_rate_limit(identifier, 3, 60, "bucket1")
    allowed2, _ = rate_limiter.check_rate_limit(identifier, 5, 60, "bucket2")
    assert allowed1 and allowed2, "❌ Different buckets should be independent"
    print("✅ Separate buckets working independently")
    
    # Test quota checks
    print("\n📝 Test 2.6: Testing user quota checks...")
    user_id = "test-user-quota"
    
    allowed, msg = rate_limiter.check_user_prompt_quota(user_id)
    assert allowed, f"❌ Prompt quota check failed: {msg}"
    print("✅ User prompt quota check passed")
    
    allowed, msg = rate_limiter.check_user_config_quota(user_id)
    assert allowed, f"❌ Config quota check failed: {msg}"
    print("✅ User config quota check passed")
    
    # Test IP limit checks
    print("\n📝 Test 2.7: Testing IP limit checks...")
    allowed, retry = rate_limiter.check_ip_login_limit("192.168.1.1")
    assert allowed, "❌ IP login limit check failed"
    print("✅ IP login limit check passed")
    
    allowed, retry = rate_limiter.check_ip_register_limit("192.168.1.1")
    assert allowed, "❌ IP register limit check failed"
    print("✅ IP register limit check passed")
    
    # Test status retrieval
    print("\n📝 Test 2.8: Testing rate limit status...")
    status = rate_limiter.get_rate_limit_status(identifier)
    assert isinstance(status, dict), "❌ Status should be a dictionary"
    print(f"✅ Rate limit status retrieved: {len(status)} buckets tracked")
    
    print("\n✅ ALL RATE LIMITING TESTS PASSED!")


def test_audit_logging():
    """Test audit logging functionality."""
    print("\n" + "="*70)
    print("TEST 3: Audit Logging")
    print("="*70)
    
    user_id = "test-user-audit"
    username = "testuser"
    
    # Create test user
    create_test_user(user_id, username)
    
    # Test basic audit log
    print("\n📝 Test 3.1: Creating basic audit log...")
    result = audit.log_audit_event(
        user_id=user_id,
        action="test_action",
        details="This is a test audit log",
        success=True,
        resource="/api/test"
    )
    assert result, "❌ Audit log creation failed"
    print("✅ Audit log created successfully")
    
    # Test specialized logging functions
    print("\n📝 Test 3.2: Testing specialized logging functions...")
    
    audit.log_login_success(user_id, username)
    print("   ✓ Login success logged")
    
    audit.log_login_failure(username, "Invalid password")
    print("   ✓ Login failure logged")
    
    audit.log_logout(user_id, username)
    print("   ✓ Logout logged")
    
    audit.log_registration(user_id, username, True)
    print("   ✓ Registration logged")
    
    audit.log_password_change(user_id, username, True)
    print("   ✓ Password change logged")
    
    audit.log_configuration_change(user_id, "Amazon", "Updated AWS credentials")
    print("   ✓ Configuration change logged")
    
    audit.log_prompt_execution(user_id, "session-123", "Test prompt execution")
    print("   ✓ Prompt execution logged")
    
    audit.log_session_access(user_id, "session-123", "create")
    print("   ✓ Session access logged")
    
    audit.log_credential_change(user_id, "Amazon", "stored")
    print("   ✓ Credential change logged")
    
    audit.log_rate_limit_exceeded(f"user:{user_id}", "/api/test")
    print("   ✓ Rate limit violation logged")
    
    audit.log_security_event(user_id, "test_event", "Test security event", "warning")
    print("   ✓ Security event logged")
    
    print("✅ All specialized logging functions working")
    
    # Test retrieving logs
    print("\n📝 Test 3.3: Retrieving user audit logs...")
    logs = audit.get_user_audit_logs(user_id, limit=20)
    assert len(logs) > 0, "❌ No logs retrieved"
    print(f"✅ Retrieved {len(logs)} audit log entries for user")
    
    # Show sample log entry
    if logs:
        sample = logs[0]
        print(f"\n   Sample log entry:")
        print(f"   - Action: {sample['action']}")
        print(f"   - Status: {sample['status']}")
        print(f"   - Details: {sample['details']}")
        print(f"   - Timestamp: {sample['timestamp']}")
    
    # Test log filtering
    print("\n📝 Test 3.4: Testing log filtering...")
    filtered_logs = audit.get_user_audit_logs(user_id, limit=10, action_filter="test_action")
    assert len(filtered_logs) > 0, "❌ Filtered logs should exist"
    assert all(log['action'] == 'test_action' for log in filtered_logs), "❌ Filter not working"
    print(f"✅ Log filtering working - found {len(filtered_logs)} matching entries")
    
    # Test with metadata
    print("\n📝 Test 3.5: Testing audit log with metadata...")
    metadata = {
        "ip_address": "192.168.1.100",
        "user_agent": "Test Agent/1.0",
        "extra_data": {"key": "value"}
    }
    result = audit.log_audit_event(
        user_id=user_id,
        action="test_with_metadata",
        details="Test with metadata",
        metadata=metadata
    )
    assert result, "❌ Audit log with metadata failed"
    print("✅ Audit log with metadata created successfully")
    
    print("\n✅ ALL AUDIT LOGGING TESTS PASSED!")


def test_integration():
    """Test integration between components."""
    print("\n" + "="*70)
    print("TEST 4: Integration Tests")
    print("="*70)
    
    user_id = "test-user-integration"
    
    # Create test user
    create_test_user(user_id, "testintegration")
    
    # Test: Encrypt credentials, log it, check rate limit
    print("\n📝 Test 4.1: Full workflow test...")
    
    # 1. Store credentials with audit log
    provider = "Google"
    credentials = {"api_key": "test-google-key"}
    
    result = encryption.encrypt_credentials(user_id, provider, credentials)
    assert result, "❌ Credential encryption failed"
    
    audit.log_credential_change(user_id, provider, "stored")
    print("   ✓ Stored credentials and logged event")
    
    # 2. Check rate limit
    allowed, _ = rate_limiter.check_user_config_quota(user_id)
    assert allowed, "❌ Rate limit check failed"
    print("   ✓ Rate limit check passed")
    
    # 3. Retrieve credentials
    decrypted = encryption.decrypt_credentials(user_id, provider)
    assert decrypted == credentials, "❌ Decryption failed"
    print("   ✓ Retrieved encrypted credentials")
    
    # 4. Verify audit logs
    logs = audit.get_user_audit_logs(user_id)
    assert len(logs) > 0, "❌ No audit logs found"
    print(f"   ✓ Verified audit trail ({len(logs)} entries)")
    
    print("\n✅ INTEGRATION TEST PASSED!")


def run_all_tests():
    """Run all Phase 3 tests."""
    print("\n" + "="*70)
    print("🚀 PHASE 3 SECURITY HARDENING - TEST SUITE")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        setup_test_db()
        
        # Run test suites
        test_credential_encryption()
        test_rate_limiting()
        test_audit_logging()
        test_integration()
        
        # Summary
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED!")
        print("="*70)
        print("\n✅ Phase 3 Security Features:")
        print("   • Credential Encryption: WORKING")
        print("   • Rate Limiting: WORKING")
        print("   • Audit Logging: WORKING")
        print("   • Integration: WORKING")
        
        print("\n📊 Test Summary:")
        print("   • Total Test Suites: 4")
        print("   • Total Test Cases: 28+")
        print("   • Status: ALL PASSED ✅")
        
        print(f"\n⏱️  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_db()
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
