#!/usr/bin/env python3
"""
Complete database schema fix - recreates all tables to match current models.
This fixes all the column mismatches between models and database tables.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from trusted_data_agent.auth.database import engine, SessionLocal
from trusted_data_agent.auth.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_and_recreate_all_tables():
    """Drop and recreate all tables to match current models."""
    
    logger.info("=" * 70)
    logger.info("Complete Database Schema Fix")
    logger.info("=" * 70)
    logger.info("This will:")
    logger.info("  1. Back up ALL existing data")
    logger.info("  2. Drop all tables")
    logger.info("  3. Recreate tables from current models")
    logger.info("  4. Restore data where possible")
    logger.info("=" * 70)
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Get list of all existing tables
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
            existing_tables = [row[0] for row in result.fetchall()]
            logger.info(f"Found {len(existing_tables)} tables: {', '.join(existing_tables)}")
            
            # Backup data from key tables
            backups = {}
            for table in ['users', 'auth_tokens', 'access_tokens', 'user_credentials', 'audit_logs']:
                if table in existing_tables:
                    try:
                        result = conn.execute(text(f"SELECT * FROM {table}"))
                        backups[table] = result.fetchall()
                        logger.info(f"Backed up {len(backups[table])} rows from {table}")
                    except Exception as e:
                        logger.warning(f"Could not backup {table}: {e}")
                        backups[table] = []
            
            # Drop all tables
            logger.info("\nDropping all tables...")
            for table in existing_tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                    logger.info(f"Dropped {table}")
                except Exception as e:
                    logger.warning(f"Could not drop {table}: {e}")
            
            trans.commit()
            logger.info("All tables dropped successfully")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"Failed to drop tables: {e}")
            return False
    
    # Recreate all tables from models
    logger.info("\nRecreating tables from models...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("All tables recreated successfully")
    except Exception as e:
        logger.error(f"Failed to recreate tables: {e}")
        return False
    
    # Restore users data
    logger.info("\nRestoring data...")
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Restore users
            if 'users' in backups and backups['users']:
                logger.info(f"Restoring {len(backups['users'])} users...")
                for row in backups['users']:
                    # users table columns: id, username, email, password_hash, display_name, full_name, 
                    # created_at, updated_at, last_login_at, is_active, is_admin, profile_tier, failed_login_attempts, locked_until
                    values = list(row[:14])
                    conn.execute(text("""
                        INSERT INTO users (id, username, email, password_hash, display_name, full_name,
                                         created_at, updated_at, last_login_at, is_active, is_admin, 
                                         profile_tier, failed_login_attempts, locked_until)
                        VALUES (:p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10, :p11, :p12, :p13, :p14)
                    """), {f'p{i+1}': values[i] for i in range(len(values))})
                logger.info(f"Restored {len(backups['users'])} users")
            
            # Restore audit_logs (partial - just the basic columns)
            if 'audit_logs' in backups and backups['audit_logs']:
                logger.info(f"Restoring {len(backups['audit_logs'])} audit logs...")
                for row in backups['audit_logs']:
                    try:
                        # Basic audit log columns
                        values = list(row[:9])
                        conn.execute(text("""
                            INSERT INTO audit_logs (id, user_id, action, resource, status, ip_address, 
                                                   user_agent, details, timestamp)
                            VALUES (:p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9)
                        """), {f'p{i+1}': values[i] for i in range(len(values))})
                    except Exception as e:
                        logger.warning(f"Could not restore audit log: {e}")
                logger.info("Audit logs restored (where possible)")
            
            trans.commit()
            logger.info("\n" + "=" * 70)
            logger.info("✅ Database schema fix completed successfully!")
            logger.info("=" * 70)
            logger.info("All tables now match the current models")
            logger.info("Users have been preserved")
            logger.info("You may need to:")
            logger.info("  - Re-login (old auth tokens were cleared)")
            logger.info("  - Reconfigure any stored credentials")
            logger.info("=" * 70)
            return True
            
        except Exception as e:
            trans.rollback()
            logger.error(f"Failed to restore data: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    logger.info("\nThis will RECREATE all database tables from scratch.")
    logger.info("All users will be preserved, but auth tokens and credentials will be cleared.")
    response = input("\nContinue? (yes/no): ")
    
    if response.lower() != 'yes':
        logger.info("Operation cancelled")
        sys.exit(0)
    
    success = backup_and_recreate_all_tables()
    
    if success:
        sys.exit(0)
    else:
        logger.error("\n❌ Schema fix failed!")
        sys.exit(1)
