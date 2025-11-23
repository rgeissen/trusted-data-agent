#!/usr/bin/env python3
"""
Test script for Phase 1: Database & Authentication Infrastructure

Tests:
1. Database initialization
2. User model creation
3. Password hashing and verification
4. JWT token generation and validation
5. Token revocation
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Enable authentication for testing
os.environ['TDA_AUTH_ENABLED'] = 'true'
os.environ['TDA_JWT_SECRET_KEY'] = 'test-secret-key-for-development-only'

from trusted_data_agent.auth.database import init_database, drop_all_tables, get_db_session
from trusted_data_agent.auth.models import User, AuthToken
from trusted_data_agent.auth.security import (
    hash_password,
    verify_password,
    generate_auth_token,
    verify_auth_token,
    revoke_token,
    validate_password_strength
)


def print_header(text):
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def test_database_initialization():
    """Test 1: Database initialization"""
    print_header("TEST 1: Database Initialization")
    
    try:
        # Drop existing tables for clean test
        if os.environ.get('TDA_ENV') != 'production':
            drop_all_tables()
        
        # Initialize database
        result = init_database()
        
        assert result == True, "Database initialization failed"
        print("✅ Database initialized successfully")
        
        # Verify tables exist
        from trusted_data_agent.auth.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['users', 'auth_tokens', 'user_credentials', 
                          'user_preferences', 'audit_logs', 'password_reset_tokens']
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
            print(f"✅ Table '{table}' exists")
        
        print("\n✅ All tables created successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_user_creation():
    """Test 2: User model creation and queries"""
    print_header("TEST 2: User Model Creation")
    
    try:
        with get_db_session() as session:
            # Create a test user
            password_hash = hash_password("TestPassword123")
            
            user = User(
                username="testuser",
                email="test@example.com",
                password_hash=password_hash,
                full_name="Test User"
            )
            
            session.add(user)
            session.flush()  # Get ID without committing
            
            print(f"✅ User created: {user}")
            print(f"   ID: {user.id}")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Created: {user.created_at}")
            
            # Query user back
            queried_user = session.query(User).filter_by(username="testuser").first()
            assert queried_user is not None, "Failed to query user"
            assert queried_user.username == "testuser"
            assert queried_user.email == "test@example.com"
            
            print("\n✅ User query successful")
            
            # Test to_dict method
            user_dict = user.to_dict()
            assert 'id' in user_dict
            assert 'username' in user_dict
            assert 'email' in user_dict
            assert 'password_hash' not in user_dict  # Should not expose password
            
            print("✅ User.to_dict() method works")
            
            return True
        
    except Exception as e:
        print(f"\n❌ User creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_password_hashing():
    """Test 3: Password hashing and verification"""
    print_header("TEST 3: Password Hashing & Verification")
    
    try:
        password = "MySecurePassword123!"
        
        # Hash password
        password_hash = hash_password(password)
        print(f"✅ Password hashed: {password_hash[:50]}...")
        
        # Verify correct password
        assert verify_password(password, password_hash) == True, "Failed to verify correct password"
        print("✅ Correct password verified")
        
        # Verify incorrect password
        assert verify_password("WrongPassword", password_hash) == False, "Incorrectly verified wrong password"
        print("✅ Incorrect password rejected")
        
        # Test password strength validation
        weak_password = "short"
        is_valid, errors = validate_password_strength(weak_password)
        assert is_valid == False, "Weak password should fail validation"
        assert len(errors) > 0, "Should have validation errors"
        print(f"✅ Weak password rejected: {errors}")
        
        strong_password = "StrongPassword123"
        is_valid, errors = validate_password_strength(strong_password)
        assert is_valid == True, "Strong password should pass validation"
        assert len(errors) == 0, "Should have no validation errors"
        print("✅ Strong password accepted")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Password hashing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jwt_tokens():
    """Test 4: JWT token generation and validation"""
    print_header("TEST 4: JWT Token Generation & Validation")
    
    try:
        # Create a test user first
        with get_db_session() as session:
            user = session.query(User).filter_by(username="testuser").first()
            user_id = user.id
            username = user.username
        
        # Generate token
        token, expiry = generate_auth_token(
            user_id=user_id,
            username=username,
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        print(f"✅ Token generated: {token[:50]}...")
        print(f"   Expires: {expiry}")
        
        # Verify token
        payload = verify_auth_token(token)
        assert payload is not None, "Failed to verify token"
        assert payload['user_id'] == user_id, "User ID mismatch"
        assert payload['username'] == username, "Username mismatch"
        
        print(f"✅ Token verified successfully")
        print(f"   User ID: {payload['user_id']}")
        print(f"   Username: {payload['username']}")
        
        # Test token revocation
        revoke_result = revoke_token(token)
        assert revoke_result == True, "Failed to revoke token"
        print("✅ Token revoked successfully")
        
        # Verify revoked token fails
        payload_after_revoke = verify_auth_token(token)
        assert payload_after_revoke is None, "Revoked token should not verify"
        print("✅ Revoked token correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"\n❌ JWT token test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_token_model():
    """Test 5: AuthToken model and queries"""
    print_header("TEST 5: AuthToken Model")
    
    try:
        with get_db_session() as session:
            # Get test user
            user = session.query(User).filter_by(username="testuser").first()
            
            # Query auth tokens
            tokens = session.query(AuthToken).filter_by(user_id=user.id).all()
            
            print(f"✅ Found {len(tokens)} auth tokens for user")
            
            for token in tokens:
                print(f"   Token ID: {token.id}")
                print(f"   Created: {token.created_at}")
                print(f"   Expires: {token.expires_at}")
                print(f"   Revoked: {token.revoked}")
                print(f"   Valid: {token.is_valid()}")
            
            return True
        
    except Exception as e:
        print(f"\n❌ AuthToken model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  PHASE 1 AUTHENTICATION INFRASTRUCTURE TESTS")
    print("="*80)
    
    results = []
    
    results.append(("Database Initialization", test_database_initialization()))
    results.append(("User Model Creation", test_user_creation()))
    results.append(("Password Hashing", test_password_hashing()))
    results.append(("JWT Tokens", test_jwt_tokens()))
    results.append(("AuthToken Model", test_auth_token_model()))
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase 1 infrastructure is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
