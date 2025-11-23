#!/usr/bin/env python3
"""
Database migration script to add profile_tier column to users table.

This script:
1. Adds profile_tier column with default value 'user'
2. Migrates existing is_admin=True users to 'admin' tier
3. Creates index on profile_tier column

Run this script once to upgrade the database schema.
"""

import sqlite3
import sys
from pathlib import Path

def migrate_profile_tier(db_path: str = "tda_auth.db"):
    """
    Add profile_tier column to users table.
    
    Args:
        db_path: Path to SQLite database file
    """
    print(f"Migrating database: {db_path}")
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'profile_tier' in columns:
            print("✅ profile_tier column already exists")
            return
        
        print("Adding profile_tier column...")
        
        # Add profile_tier column with default 'user'
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN profile_tier TEXT NOT NULL DEFAULT 'user'
        """)
        
        # Migrate existing admin users to 'admin' tier
        cursor.execute("""
            UPDATE users 
            SET profile_tier = 'admin' 
            WHERE is_admin = 1
        """)
        
        admin_count = cursor.rowcount
        
        # Create index on profile_tier
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_profile_tier 
            ON users(profile_tier)
        """)
        
        conn.commit()
        
        print(f"✅ Migration successful!")
        print(f"   - Added profile_tier column")
        print(f"   - Migrated {admin_count} admin user(s) to 'admin' tier")
        print(f"   - Created index on profile_tier")
        
        # Show tier distribution
        cursor.execute("""
            SELECT profile_tier, COUNT(*) 
            FROM users 
            GROUP BY profile_tier
        """)
        
        print("\nCurrent tier distribution:")
        for tier, count in cursor.fetchall():
            print(f"   - {tier}: {count} user(s)")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    migrate_profile_tier()
    
    print("\n✅ Database migration complete!")
    print("\nProfile Tier System:")
    print("   - USER: Basic access (default for new users)")
    print("   - DEVELOPER: Advanced features (RAG, templates, testing)")
    print("   - ADMIN: Full system access (user management, config)")
    print("\nUse admin API endpoints to promote users between tiers.")
