#!/usr/bin/env python3
"""
Migration script to add llm_model_costs table for tracking LLM pricing.
This script is safe to run multiple times and loads default costs from tda_config.json.
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = "tda_auth.db"
CONFIG_PATH = "tda_config.json"


def migrate_llm_model_costs_table():
    """Add llm_model_costs table if it doesn't exist."""
    print("=" * 60)
    print("LLM Model Costs Table Migration")
    print("=" * 60 + "\n")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='llm_model_costs'
        """)
        
        if cursor.fetchone():
            print("✅ llm_model_costs table already exists - no migration needed\n")
            conn.close()
            return
        
        print("📋 Creating llm_model_costs table...")
        
        # Create llm_model_costs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_model_costs (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                input_cost_per_million REAL NOT NULL,
                output_cost_per_million REAL NOT NULL,
                is_manual_entry BOOLEAN NOT NULL DEFAULT 0,
                is_fallback BOOLEAN NOT NULL DEFAULT 0,
                source TEXT NOT NULL,
                last_updated DATETIME NOT NULL,
                notes TEXT,
                UNIQUE(provider, model)
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_costs_provider ON llm_model_costs(provider)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_costs_model ON llm_model_costs(model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_costs_provider_model ON llm_model_costs(provider, model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_costs_fallback ON llm_model_costs(is_fallback)")
        
        conn.commit()
        
        print("   ✅ Table created successfully")
        print("   ✅ Indexes created successfully")
        
        # Insert default fallback entry
        print("\n📋 Adding default fallback cost entry...")
        cursor.execute("""
            INSERT INTO llm_model_costs 
            (id, provider, model, input_cost_per_million, output_cost_per_million, 
             is_manual_entry, is_fallback, source, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'fallback-default',
            'fallback',
            'default',
            10.0,  # $10 per 1M input tokens
            30.0,  # $30 per 1M output tokens
            1,
            1,
            'system_default',
            datetime.utcnow().isoformat(),
            'Default fallback pricing for models not found in LiteLLM or manual entries'
        ))
        
        conn.commit()
        print("   ✅ Default fallback entry added")
        
        # Load default costs from tda_config.json if available
        print("\n📋 Loading default costs from tda_config.json...")
        config_path = Path(__file__).parent.parent / CONFIG_PATH
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                default_costs = config.get('default_model_costs', [])
                
                if default_costs:
                    added_count = 0
                    skipped_count = 0
                    
                    for cost_entry in default_costs:
                        provider = cost_entry.get('provider')
                        model = cost_entry.get('model')
                        input_cost = cost_entry.get('input_cost_per_million')
                        output_cost = cost_entry.get('output_cost_per_million')
                        notes = cost_entry.get('notes', '')
                        
                        if not all([provider, model, input_cost is not None, output_cost is not None]):
                            print(f"   ⚠️  Skipping invalid entry: {cost_entry}")
                            continue
                        
                        # Check if entry already exists (respect manual entries)
                        cursor.execute("""
                            SELECT id FROM llm_model_costs 
                            WHERE provider = ? AND model = ?
                        """, (provider, model))
                        
                        if cursor.fetchone():
                            skipped_count += 1
                            continue
                        
                        # Insert config default
                        cursor.execute("""
                            INSERT INTO llm_model_costs 
                            (id, provider, model, input_cost_per_million, output_cost_per_million,
                             is_manual_entry, is_fallback, source, last_updated, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(uuid.uuid4()),
                            provider,
                            model,
                            input_cost,
                            output_cost,
                            0,  # Not a manual entry
                            0,  # Not fallback
                            'config_default',
                            datetime.utcnow().isoformat(),
                            notes
                        ))
                        added_count += 1
                    
                    conn.commit()
                    print(f"   ✅ Loaded {added_count} default costs from config")
                    if skipped_count > 0:
                        print(f"   ℹ️  Skipped {skipped_count} existing entries")
                else:
                    print("   ℹ️  No default_model_costs found in config")
                    
            except Exception as e:
                print(f"   ⚠️  Error loading config defaults: {e}")
        else:
            print("   ℹ️  tda_config.json not found - skipping config defaults")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(llm_model_costs)")
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
    migrate_llm_model_costs_table()
