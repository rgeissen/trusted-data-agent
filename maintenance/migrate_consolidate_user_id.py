#!/usr/bin/env python3
"""
Database Migration: Consolidate user_uuid into user.id

This migration removes the redundant user_uuid column and uses user.id
for both database relationships and application-level tracking.

Steps:
1. Backup existing database
2. For each user: if user_uuid differs from id, we keep id (primary key)
3. Drop user_uuid column
4. Update codebase references

Usage:
    python maintenance/migrate_consolidate_user_id.py
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from trusted_data_agent.auth.database import get_db_session, engine
from trusted_data_agent.auth.models import User
from sqlalchemy import text


def backup_database():
    """Create a backup of the database before migration."""
    db_path = Path(__file__).parent.parent / 'tda_auth.db'
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.with_suffix(f'.db.backup_{timestamp}')
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to backup database: {e}")
        return False


def check_migration_needed():
    """Check if user_uuid column exists."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result]
        return 'user_uuid' in columns


def perform_migration():
    """Execute the migration."""
    print("\n" + "="*70)
    print("User ID Consolidation Migration")
    print("="*70)
    print()
    
    # Check if migration is needed
    if not check_migration_needed():
        print("ℹ️  Migration not needed - user_uuid column doesn't exist")
        return True
    
    # Backup database
    print("Step 1: Backing up database...")
    if not backup_database():
        return False
    
    print("\nStep 2: Analyzing user records...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, user_uuid FROM users"))
        users = list(result)
        print(f"   Found {len(users)} user(s)")
        
        # Check if any user has different id vs user_uuid
        mismatches = [u for u in users if u[0] != u[1]]
        if mismatches:
            print(f"   ⚠️  {len(mismatches)} user(s) have id != user_uuid")
            print(f"   We'll keep the 'id' value (primary key)")
        else:
            print(f"   ✅ All users have matching id and user_uuid")
    
    print("\nStep 3: Dropping user_uuid column...")
    try:
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        with engine.begin() as conn:
            # Get existing data
            result = conn.execute(text("SELECT * FROM users"))
            users_data = [dict(row._mapping) for row in result]
            
            # Create new table without user_uuid
            conn.execute(text("""
                CREATE TABLE users_new (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    full_name TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    last_login_at TIMESTAMP,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    is_admin BOOLEAN NOT NULL DEFAULT 0,
                    profile_tier TEXT NOT NULL DEFAULT 'user',
                    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TIMESTAMP
                )
            """))
            
            # Copy data (excluding user_uuid)
            for user in users_data:
                user.pop('user_uuid', None)  # Remove user_uuid field
                columns = ', '.join(user.keys())
                placeholders = ', '.join([f':{k}' for k in user.keys()])
                conn.execute(
                    text(f"INSERT INTO users_new ({columns}) VALUES ({placeholders})"),
                    user
                )
            
            # Create indexes
            conn.execute(text("CREATE UNIQUE INDEX idx_users_username ON users_new(username)"))
            conn.execute(text("CREATE UNIQUE INDEX idx_users_email ON users_new(email)"))
            conn.execute(text("CREATE INDEX idx_users_profile_tier ON users_new(profile_tier)"))
            
            # Drop old table and rename new one
            conn.execute(text("DROP TABLE users"))
            conn.execute(text("ALTER TABLE users_new RENAME TO users"))
            
        print("   ✅ Column dropped successfully")
        
    except Exception as e:
        print(f"   ❌ Migration failed: {e}")
        print("\n   Your backup is safe. You can restore it if needed.")
        return False
    
    print("\n" + "="*70)
    print("✨ Migration completed successfully!")
    print("="*70)
    print()
    print("Next steps:")
    print("1. The codebase will be updated to use 'user.id' everywhere")
    print("2. Restart your application")
    print("3. Test login and credential loading")
    print()
    
    return True


if __name__ == '__main__':
    try:
        success = perform_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
