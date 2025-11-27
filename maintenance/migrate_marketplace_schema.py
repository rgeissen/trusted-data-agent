#!/usr/bin/env python3
"""
Database migration script for marketplace feature.

Adds:
1. collection_subscriptions table
2. collection_ratings table
3. Ownership metadata to RAG collections in tda_config.json

Usage:
    python maintenance/migrate_marketplace_schema.py [--dry-run]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from trusted_data_agent.auth.database import get_db_session, engine
from trusted_data_agent.auth.models import Base, CollectionSubscription, CollectionRating
from trusted_data_agent.core.config_manager import get_config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate_database_tables(dry_run: bool = False):
    """Create new marketplace tables if they don't exist."""
    logger.info("=" * 80)
    logger.info("PHASE 1: DATABASE TABLES MIGRATION")
    logger.info("=" * 80)
    
    # Check which tables need to be created
    tables_to_create = []
    
    if not check_table_exists('collection_subscriptions'):
        tables_to_create.append('collection_subscriptions')
        logger.info("✓ Table 'collection_subscriptions' needs to be created")
    else:
        logger.info("✓ Table 'collection_subscriptions' already exists")
    
    if not check_table_exists('collection_ratings'):
        tables_to_create.append('collection_ratings')
        logger.info("✓ Table 'collection_ratings' needs to be created")
    else:
        logger.info("✓ Table 'collection_ratings' already exists")
    
    if not tables_to_create:
        logger.info("✓ All marketplace tables already exist. No database migration needed.")
        return True
    
    if dry_run:
        logger.info(f"\n[DRY RUN] Would create tables: {', '.join(tables_to_create)}")
        return True
    
    # Create tables
    try:
        logger.info(f"\nCreating tables: {', '.join(tables_to_create)}...")
        
        # Create only the marketplace tables
        Base.metadata.create_all(
            engine, 
            tables=[
                CollectionSubscription.__table__,
                CollectionRating.__table__
            ]
        )
        
        logger.info("✓ Successfully created marketplace tables")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}", exc_info=True)
        return False


def migrate_collection_metadata(dry_run: bool = False):
    """Add ownership and marketplace metadata to RAG collections."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: COLLECTION METADATA MIGRATION")
    logger.info("=" * 80)
    
    config_manager = get_config_manager()
    collections = config_manager.get_rag_collections()
    
    if not collections:
        logger.info("✓ No collections found. Nothing to migrate.")
        return True
    
    logger.info(f"Found {len(collections)} collection(s) to check")
    
    updated_collections = []
    changes_made = False
    
    for collection in collections:
        collection_copy = collection.copy()
        needs_update = False
        
        # Add owner_user_id if missing (default to None = admin-owned)
        if "owner_user_id" not in collection:
            collection_copy["owner_user_id"] = None
            needs_update = True
            logger.info(f"  Collection '{collection['name']}' (ID: {collection['id']}): Adding owner_user_id=None (admin-owned)")
        
        # Add visibility if missing (default to private)
        if "visibility" not in collection:
            collection_copy["visibility"] = "private"
            needs_update = True
            logger.info(f"  Collection '{collection['name']}' (ID: {collection['id']}): Adding visibility='private'")
        
        # Add is_marketplace_listed if missing (default to False)
        if "is_marketplace_listed" not in collection:
            collection_copy["is_marketplace_listed"] = False
            needs_update = True
            logger.info(f"  Collection '{collection['name']}' (ID: {collection['id']}): Adding is_marketplace_listed=False")
        
        # Add subscriber_count if missing (default to 0)
        if "subscriber_count" not in collection:
            collection_copy["subscriber_count"] = 0
            needs_update = True
            logger.info(f"  Collection '{collection['name']}' (ID: {collection['id']}): Adding subscriber_count=0")
        
        # Add marketplace_metadata if missing (for future use)
        if "marketplace_metadata" not in collection:
            collection_copy["marketplace_metadata"] = {}
            needs_update = True
            logger.info(f"  Collection '{collection['name']}' (ID: {collection['id']}): Adding empty marketplace_metadata")
        
        if needs_update:
            changes_made = True
        
        updated_collections.append(collection_copy)
    
    if not changes_made:
        logger.info("✓ All collections already have marketplace metadata. No migration needed.")
        return True
    
    if dry_run:
        logger.info("\n[DRY RUN] Would update tda_config.json with new metadata")
        logger.info(f"[DRY RUN] Collections with changes: {sum(1 for c in updated_collections if c != collections[updated_collections.index(c)])}")
        return True
    
    # Save updated collections
    try:
        logger.info("\nSaving updated collections to tda_config.json...")
        success = config_manager.save_rag_collections(updated_collections)
        
        if success:
            logger.info("✓ Successfully updated collection metadata")
            return True
        else:
            logger.error("✗ Failed to save updated collections")
            return False
            
    except Exception as e:
        logger.error(f"✗ Failed to update collection metadata: {e}", exc_info=True)
        return False


def verify_migration():
    """Verify that migration was successful."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3: VERIFICATION")
    logger.info("=" * 80)
    
    all_good = True
    
    # Check tables
    if check_table_exists('collection_subscriptions'):
        logger.info("✓ Table 'collection_subscriptions' exists")
    else:
        logger.error("✗ Table 'collection_subscriptions' does not exist")
        all_good = False
    
    if check_table_exists('collection_ratings'):
        logger.info("✓ Table 'collection_ratings' exists")
    else:
        logger.error("✗ Table 'collection_ratings' does not exist")
        all_good = False
    
    # Check collection metadata
    config_manager = get_config_manager()
    collections = config_manager.get_rag_collections()
    
    required_fields = ["owner_user_id", "visibility", "is_marketplace_listed", "subscriber_count", "marketplace_metadata"]
    missing_fields = []
    
    for collection in collections:
        for field in required_fields:
            if field not in collection:
                missing_fields.append(f"Collection {collection['id']}: missing '{field}'")
    
    if missing_fields:
        logger.error(f"✗ Some collections missing required fields:")
        for msg in missing_fields:
            logger.error(f"  - {msg}")
        all_good = False
    else:
        logger.info(f"✓ All {len(collections)} collection(s) have required marketplace metadata")
    
    return all_good


def main():
    parser = argparse.ArgumentParser(description='Migrate database schema for marketplace feature')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--skip-verification', action='store_true', help='Skip verification step')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("MARKETPLACE SCHEMA MIGRATION")
    logger.info("=" * 80)
    
    if args.dry_run:
        logger.info("\n*** DRY RUN MODE - No changes will be made ***\n")
    
    # Phase 1: Database tables
    success_db = migrate_database_tables(dry_run=args.dry_run)
    
    if not success_db:
        logger.error("\n✗ Database migration failed. Aborting.")
        sys.exit(1)
    
    # Phase 2: Collection metadata
    success_config = migrate_collection_metadata(dry_run=args.dry_run)
    
    if not success_config:
        logger.error("\n✗ Collection metadata migration failed. Aborting.")
        sys.exit(1)
    
    # Phase 3: Verification (skip in dry-run)
    if not args.dry_run and not args.skip_verification:
        success_verify = verify_migration()
        
        if not success_verify:
            logger.error("\n✗ Verification failed. Please check the errors above.")
            sys.exit(1)
    
    logger.info("\n" + "=" * 80)
    if args.dry_run:
        logger.info("DRY RUN COMPLETE - No changes were made")
    else:
        logger.info("✓ MIGRATION COMPLETE - Marketplace schema is ready!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
