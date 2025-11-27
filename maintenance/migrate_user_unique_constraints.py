#!/usr/bin/env python3
"""
Migration script to update user table unique constraints.

This script:
1. Drops the old unique constraints on username and email
2. Creates partial unique indexes that only apply to active users
3. This allows reusing usernames/emails from soft-deleted (inactive) users

Run this script once to migrate your database.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from trusted_data_agent.auth.database import engine, get_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_user_constraints():
    """Remove unique constraints from username/email to allow reusing from inactive users."""
    
    logger.info("Starting migration to remove unique constraints...")
    logger.info("After this migration:")
    logger.info("  - id (UUID) remains the primary key")
    logger.info("  - username/email can be reused from inactive users")
    logger.info("  - Application checks for duplicates only among active users")
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                # Step 1: Rename old table
                logger.info("Step 1: Renaming old users table...")
                conn.execute(text("ALTER TABLE users RENAME TO users_old"))
                
                # Step 2: Create new table WITHOUT unique constraints on username/email
                logger.info("Step 2: Creating new users table (no unique constraints)...")
                conn.execute(text("""
                    CREATE TABLE users (
                        id VARCHAR(36) NOT NULL PRIMARY KEY,
                        username VARCHAR(30) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        display_name VARCHAR(100),
                        full_name VARCHAR(255),
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        last_login_at TIMESTAMP,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        is_admin BOOLEAN NOT NULL DEFAULT 0,
                        profile_tier VARCHAR(20) NOT NULL DEFAULT 'user',
                        failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                        locked_until TIMESTAMP
                    )
                """))
                
                # Step 3: Copy all data
                logger.info("Step 3: Copying data...")
                conn.execute(text("INSERT INTO users SELECT * FROM users_old"))
                
                # Step 4: Create regular indexes for performance (NOT unique)
                logger.info("Step 4: Creating indexes...")
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_is_active ON users(is_active)"))
                
                # Step 5: Drop old table
                logger.info("Step 5: Dropping old table...")
                conn.execute(text("DROP TABLE users_old"))
                
                trans.commit()
                logger.info("✅ Migration completed successfully!")
                logger.info("You can now delete users and reuse their usernames/emails")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed, rolled back: {e}", exc_info=True)
                return False
                
    except Exception as e:
        logger.error(f"Could not connect to database: {e}", exc_info=True)
        return False


def check_migration_needed():
    """Check if migration is needed."""
    try:
        with engine.connect() as conn:
            # Check if partial unique indexes exist
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='ix_users_username_active'
            """))
            
            if result.fetchone():
                logger.info("Partial unique indexes already exist - migration not needed")
                return False
            else:
                logger.info("Partial unique indexes not found - migration needed")
                return True
    except Exception as e:
        logger.error(f"Could not check migration status: {e}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("User Unique Constraint Migration Script")
    logger.info("=" * 60)
    
    if not check_migration_needed():
        logger.info("Migration not needed or already applied")
        sys.exit(0)
    
    logger.info("\nThis will modify the users table indexes.")
    response = input("Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        logger.info("Migration cancelled")
        sys.exit(0)
    
    success = migrate_user_constraints()
    
    if success:
        logger.info("\n✅ Migration completed successfully!")
        logger.info("You can now delete users and reuse their usernames/emails")
        sys.exit(0)
    else:
        logger.error("\n❌ Migration failed!")
        sys.exit(1)
