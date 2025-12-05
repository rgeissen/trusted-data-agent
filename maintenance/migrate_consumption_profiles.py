#!/usr/bin/env python3
"""
Database migration: Add consumption profiles and token usage tracking.

This migration:
1. Creates consumption_profiles table
2. Creates user_token_usage table
3. Adds consumption_profile_id to users table
4. Creates default consumption profiles

Usage:
    python maintenance/migrate_consumption_profiles.py
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text, inspect
from trusted_data_agent.auth.database import get_db_session, engine
from trusted_data_agent.auth.models import Base, ConsumptionProfile

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    if not table_exists(table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def create_consumption_profiles_table():
    """Create consumption_profiles table."""
    logger.info("Creating consumption_profiles table...")
    
    with get_db_session() as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS consumption_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                prompts_per_hour INTEGER NOT NULL DEFAULT 100,
                prompts_per_day INTEGER NOT NULL DEFAULT 1000,
                config_changes_per_hour INTEGER NOT NULL DEFAULT 10,
                input_tokens_per_month INTEGER,
                output_tokens_per_month INTEGER,
                is_default BOOLEAN NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create index on name
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_consumption_profiles_name 
            ON consumption_profiles(name)
        """))
        
        # Create index on is_default
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_consumption_profiles_is_default 
            ON consumption_profiles(is_default)
        """))
        
        session.commit()
    
    logger.info("✓ consumption_profiles table created")


def create_user_token_usage_table():
    """Create user_token_usage table."""
    logger.info("Creating user_token_usage table...")
    
    with get_db_session() as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(36) NOT NULL,
                period VARCHAR(7) NOT NULL,
                input_tokens_used INTEGER NOT NULL DEFAULT 0,
                output_tokens_used INTEGER NOT NULL DEFAULT 0,
                total_tokens_used INTEGER NOT NULL DEFAULT 0,
                first_usage_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_usage_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        
        # Create index on user_id
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_token_usage_user_id 
            ON user_token_usage(user_id)
        """))
        
        # Create index on period
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_token_usage_period 
            ON user_token_usage(period)
        """))
        
        # Create unique index on user_id + period
        session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_user_token_usage_user_period 
            ON user_token_usage(user_id, period)
        """))
        
        session.commit()
    
    logger.info("✓ user_token_usage table created")


def add_consumption_profile_id_to_users():
    """Add consumption_profile_id column to users table."""
    logger.info("Adding consumption_profile_id to users table...")
    
    if column_exists('users', 'consumption_profile_id'):
        logger.info("✓ consumption_profile_id column already exists")
        return
    
    with get_db_session() as session:
        session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN consumption_profile_id INTEGER
        """))
        
        # Create index
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_consumption_profile_id 
            ON users(consumption_profile_id)
        """))
        
        session.commit()
    
    logger.info("✓ consumption_profile_id column added to users")


def load_config():
    """Load configuration to get default consumption profile."""
    config_path = Path(__file__).parent.parent / "tda_config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('default_consumption_profile', 'Unlimited')
    except Exception as e:
        logger.warning(f"Could not load config, using 'Unlimited' as default: {e}")
        return 'Unlimited'


def create_default_profiles():
    """Create default consumption profiles."""
    logger.info("Creating default consumption profiles...")
    
    # Load config to determine which profile should be default
    default_profile_name = load_config()
    logger.info(f"Default consumption profile from config: {default_profile_name}")
    
    default_profiles = [
        {
            'name': 'Free',
            'description': 'Free tier with basic limits',
            'prompts_per_hour': 50,
            'prompts_per_day': 500,
            'config_changes_per_hour': 5,
            'input_tokens_per_month': 100000,
            'output_tokens_per_month': 50000,
            'is_default': (default_profile_name == 'Free'),
            'is_active': True
        },
        {
            'name': 'Pro',
            'description': 'Professional tier with higher limits',
            'prompts_per_hour': 200,
            'prompts_per_day': 2000,
            'config_changes_per_hour': 20,
            'input_tokens_per_month': 500000,
            'output_tokens_per_month': 250000,
            'is_default': (default_profile_name == 'Pro'),
            'is_active': True
        },
        {
            'name': 'Enterprise',
            'description': 'Enterprise tier with high limits',
            'prompts_per_hour': 500,
            'prompts_per_day': 5000,
            'config_changes_per_hour': 50,
            'input_tokens_per_month': 2000000,
            'output_tokens_per_month': 1000000,
            'is_default': (default_profile_name == 'Enterprise'),
            'is_active': True
        },
        {
            'name': 'Unlimited',
            'description': 'Unlimited tier with no token limits',
            'prompts_per_hour': 1000,
            'prompts_per_day': 10000,
            'config_changes_per_hour': 100,
            'input_tokens_per_month': None,  # Unlimited
            'output_tokens_per_month': None,  # Unlimited
            'is_default': (default_profile_name == 'Unlimited'),
            'is_active': True
        }
    ]
    
    with get_db_session() as session:
        for profile_data in default_profiles:
            # Check if profile already exists
            existing = session.query(ConsumptionProfile).filter_by(
                name=profile_data['name']
            ).first()
            
            if existing:
                logger.info(f"  Profile '{profile_data['name']}' already exists, skipping")
                continue
            
            profile = ConsumptionProfile(**profile_data)
            session.add(profile)
            logger.info(f"  Created profile: {profile_data['name']}")
        
        session.commit()
    
    logger.info("✓ Default consumption profiles created")


def run_migration():
    """Run the complete migration."""
    logger.info("=" * 70)
    logger.info("Starting consumption profiles migration")
    logger.info("=" * 70)
    
    try:
        # Create tables
        if not table_exists('consumption_profiles'):
            create_consumption_profiles_table()
        else:
            logger.info("✓ consumption_profiles table already exists")
        
        if not table_exists('user_token_usage'):
            create_user_token_usage_table()
        else:
            logger.info("✓ user_token_usage table already exists")
        
        # Add column to users table
        add_consumption_profile_id_to_users()
        
        # Create default profiles
        create_default_profiles()
        
        logger.info("=" * 70)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("1. Restart the application to load new models")
        logger.info("2. Access Admin Panel > Consumption Profiles")
        logger.info("3. Assign profiles to users")
        logger.info("4. Enable rate limiting if not already enabled")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
