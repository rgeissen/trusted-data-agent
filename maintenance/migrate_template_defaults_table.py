#!/usr/bin/env python3
"""
Migration script to add template_defaults table to existing databases.
This script is safe to run multiple times.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = "tda_auth.db"


def migrate_template_defaults_table():
    """Add template_defaults table if it doesn't exist."""
    print("=" * 60)
    print("Template Defaults Table Migration")
    print("=" * 60 + "\n")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='template_defaults'
        """)
        
        if cursor.fetchone():
            print("✅ template_defaults table already exists - no migration needed\n")
            conn.close()
            return
        
        print("📋 Creating template_defaults table...")
        
        # Create template_defaults table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS template_defaults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id VARCHAR(100) NOT NULL,
                user_id VARCHAR(36),
                parameter_name VARCHAR(100) NOT NULL,
                parameter_value TEXT NOT NULL,
                parameter_type VARCHAR(20) NOT NULL,
                is_system_default BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                updated_by VARCHAR(36),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE(template_id, user_id, parameter_name)
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_template ON template_defaults(template_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_user ON template_defaults(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_system ON template_defaults(is_system_default)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_lookup ON template_defaults(template_id, user_id)")
        
        conn.commit()
        
        print("   ✅ Table created successfully")
        print("   ✅ Indexes created successfully")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(template_defaults)")
        columns = cursor.fetchall()
        print(f"\n📊 Table structure ({len(columns)} columns):")
        for col in columns:
            col_name, col_type = col[1], col[2]
            print(f"   • {col_name}: {col_type}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    migrate_template_defaults_table()
