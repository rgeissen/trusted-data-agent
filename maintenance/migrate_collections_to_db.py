#!/usr/bin/env python3
"""
Migration script to create collections table in database.
This moves collection storage from tda_config.json to tda_auth.db.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = "tda_auth.db"


def create_collections_table():
    """Create the collections table in the database."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create collections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            collection_name VARCHAR(255) NOT NULL UNIQUE,
            mcp_server_id VARCHAR(100),
            enabled BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL,
            description TEXT,
            owner_user_id VARCHAR(36) NOT NULL,
            visibility VARCHAR(20) NOT NULL DEFAULT 'private',
            is_marketplace_listed BOOLEAN NOT NULL DEFAULT 0,
            subscriber_count INTEGER NOT NULL DEFAULT 0,
            marketplace_category VARCHAR(50),
            marketplace_tags TEXT,
            marketplace_long_description TEXT,
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_owner ON collections(owner_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_marketplace ON collections(is_marketplace_listed, visibility)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(collection_name)")
    
    conn.commit()
    conn.close()
    
    print("✅ Collections table created successfully")


def verify_table():
    """Verify the table was created correctly."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(collections)")
    columns = cursor.fetchall()
    
    print("\n📋 Collections table schema:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Count existing collections
    cursor.execute("SELECT COUNT(*) FROM collections")
    count = cursor.fetchone()[0]
    print(f"\n📊 Current collection count: {count}")
    
    conn.close()


if __name__ == "__main__":
    print("🚀 Creating collections table in database...")
    create_collections_table()
    verify_table()
    print("\n✅ Migration complete!")
