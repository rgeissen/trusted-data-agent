"""
Database Migration: Add Repository Type Support

Adds support for distinguishing between Planner and Knowledge repositories:
1. Adds repository_type column to collections table
2. Creates document_chunks table for Knowledge repository document storage
3. Adds chunking configuration fields

Run this script to migrate existing database:
    python maintenance/migrate_repository_types.py
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "tda_auth.db"


def migrate_repository_types():
    """Add repository type support to database schema."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Step 1: Check if repository_type column exists
        cursor.execute("PRAGMA table_info(collections)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'repository_type' not in columns:
            logger.info("Adding repository_type column to collections table...")
            cursor.execute("""
                ALTER TABLE collections
                ADD COLUMN repository_type TEXT DEFAULT 'planner'
            """)
            logger.info("✓ Added repository_type column")
        else:
            logger.info("repository_type column already exists")
        
        # Step 2: Add chunking configuration columns
        if 'chunking_strategy' not in columns:
            logger.info("Adding chunking configuration columns...")
            cursor.execute("""
                ALTER TABLE collections
                ADD COLUMN chunking_strategy TEXT DEFAULT 'none'
            """)
            cursor.execute("""
                ALTER TABLE collections
                ADD COLUMN chunk_size INTEGER DEFAULT 1000
            """)
            cursor.execute("""
                ALTER TABLE collections
                ADD COLUMN chunk_overlap INTEGER DEFAULT 200
            """)
            logger.info("✓ Added chunking configuration columns")
        else:
            logger.info("Chunking configuration columns already exist")
        
        # Step 3: Create document_chunks table for Knowledge repositories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                document_id TEXT NOT NULL,
                chunk_id TEXT UNIQUE NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,  -- JSON
                embedding_model TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE
            )
        """)
        logger.info("✓ Created document_chunks table")
        
        # Step 4: Create index for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_collection
            ON document_chunks(collection_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_document
            ON document_chunks(document_id)
        """)
        logger.info("✓ Created indexes on document_chunks table")
        
        # Step 5: Create documents table for tracking original documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                document_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                document_type TEXT,  -- pdf, txt, docx, etc.
                title TEXT,
                author TEXT,
                source TEXT,  -- upload, api, etc.
                category TEXT,
                tags TEXT,  -- JSON array
                file_size INTEGER,
                page_count INTEGER,
                content_hash TEXT,  -- SHA256 of content
                created_at TEXT NOT NULL,
                updated_at TEXT,
                metadata TEXT,  -- JSON for additional fields
                FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE
            )
        """)
        logger.info("✓ Created knowledge_documents table")
        
        # Step 6: Create index for documents
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_docs_collection
            ON knowledge_documents(collection_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_docs_category
            ON knowledge_documents(category)
        """)
        logger.info("✓ Created indexes on knowledge_documents table")
        
        # Step 7: Update existing collections to have repository_type = 'planner'
        cursor.execute("""
            UPDATE collections
            SET repository_type = 'planner'
            WHERE repository_type IS NULL OR repository_type = ''
        """)
        updated = cursor.rowcount
        if updated > 0:
            logger.info(f"✓ Updated {updated} existing collection(s) to repository_type='planner'")
        
        conn.commit()
        logger.info("\n✅ Migration completed successfully!")
        
        # Verify migration
        cursor.execute("PRAGMA table_info(collections)")
        columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"\nCollections table columns: {', '.join(columns)}")
        
        cursor.execute("SELECT COUNT(*) FROM collections")
        count = cursor.fetchone()[0]
        logger.info(f"Total collections: {count}")
        
        cursor.execute("SELECT COUNT(*) FROM collections WHERE repository_type = 'planner'")
        planner_count = cursor.fetchone()[0]
        logger.info(f"Planner repositories: {planner_count}")
        
        cursor.execute("SELECT COUNT(*) FROM collections WHERE repository_type = 'knowledge'")
        knowledge_count = cursor.fetchone()[0]
        logger.info(f"Knowledge repositories: {knowledge_count}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Repository Type Migration")
    logger.info("=" * 60)
    logger.info("")
    
    # Check if database exists
    if not Path(DB_PATH).exists():
        logger.error(f"❌ Database not found: {DB_PATH}")
        logger.error("Please run the application first to create the database.")
        exit(1)
    
    try:
        migrate_repository_types()
        logger.info("\n" + "=" * 60)
        logger.info("Migration completed! The database now supports:")
        logger.info("  • Planner Repositories (execution patterns)")
        logger.info("  • Knowledge Repositories (reference documents)")
        logger.info("  • Document chunking with configurable strategies")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error("Migration failed! Please check the error above.")
        logger.error("=" * 60)
        exit(1)
