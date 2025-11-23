"""
Simple test for credential storage (no async, matches Phase3 structure).
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables before imports
os.environ['TDA_ENCRYPTION_KEY'] = 'test-encryption-key-simple'
os.environ['TDA_AUTH_DB_URL'] = 'sqlite:///./test_simple.db'
os.environ['TDA_AUTH_ENABLED'] = 'true'

from trusted_data_agent.auth.database import init_database, get_db_session
from trusted_data_agent.auth.models import User
from trusted_data_agent.auth.security import hash_password
from trusted_data_agent.auth import encryption  # This triggers the database engine creation!


def setup_test_db():
    """Initialize test database."""
    print("\n🔧 Setting up test database...")
    if os.path.exists('test_simple.db'):
        os.remove('test_simple.db')
    init_database()
    print("✅ Test database initialized")


def cleanup_test_db():
    """Clean up test database."""
    print("\n🧹 Cleaning up test database...")
    if os.path.exists('test_simple.db'):
        os.remove('test_simple.db')
    print("✅ Test database cleaned up")


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


def test_credential_storage():
    """Test basic credential storage."""
    print("\n" + "="*70)
    print("TEST: Credential Storage")
    print("="*70)
    
    user_id = "test-user-simple"
    
    # Create test user first
    print("\n📝 Creating test user...")
    create_test_user(user_id, "testuser")
    print("✅ Test user created")
    
    provider = "Google"
    credentials = {
        "apiKey": "test-google-api-key-12345"
    }
    
    # Test 1: Store credentials
    print("\n📝 Test 1: Storing credentials...")
    result = encryption.store_encrypted_credentials(user_id, provider, credentials)
    print(f"✅ Credentials stored: {result}")
    
    # Test 2: Retrieve credentials
    print("\n📝 Test 2: Retrieving credentials...")
    retrieved = encryption.retrieve_encrypted_credentials(user_id, provider)
    print(f"✅ Credentials retrieved")
    print(f"   Original apiKey: {credentials['apiKey'][:20]}...")
    print(f"   Retrieved apiKey: {retrieved['apiKey'][:20]}...")
    assert retrieved['apiKey'] == credentials['apiKey'], "Credentials don't match!"
    
    # Test 3: List providers
    print("\n📝 Test 3: Listing providers...")
    providers = encryption.list_user_credentials(user_id)
    print(f"✅ User has credentials for providers: {providers}")
    assert provider in providers, f"{provider} not in provider list!"
    
    # Test 4: Delete credentials
    print("\n📝 Test 4: Deleting credentials...")
    result = encryption.delete_encrypted_credentials(user_id, provider)
    print(f"✅ Credentials deleted: {result}")
    
    # Verify deletion
    providers = encryption.list_user_credentials(user_id)
    assert provider not in providers, f"{provider} still in provider list after deletion!"
    print(f"✅ Verified deletion - provider list: {providers}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 CREDENTIAL STORAGE - SIMPLE TEST")
    print("="*70)
    
    try:
        setup_test_db()
        test_credential_storage()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_db()
