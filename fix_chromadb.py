#!/usr/bin/env python3
"""Fix ChromaDB database schema for version 0.6+ compatibility"""

import sqlite3
import json
from pathlib import Path

# Path to ChromaDB
project_root = Path(__file__).resolve().parent
db_path = project_root / '.chromadb_rag_cache' / 'chroma.sqlite3'

print(f"Database path: {db_path}")
print(f"Database exists: {db_path.exists()}")

if not db_path.exists():
    print("ERROR: Database file not found!")
    exit(1)

# Default configuration for ChromaDB 0.6+
default_config = {
    "_type": "CollectionConfigurationInternal",
    "hnsw_configuration": {
        "_type": "HNSWConfigurationInternal",
        "space": "cosine",
        "ef_construction": 100,
        "ef_search": 10,
        "num_threads": 12,
        "M": 16,
        "resize_factor": 1.2,
        "batch_size": 100,
        "sync_threshold": 1000
    }
}

try:
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all collections with their configurations
    cursor.execute("""
        SELECT id, name, config_json_str 
        FROM collections
    """)
    
    collections = cursor.fetchall()
    print(f"\nFound {len(collections)} collection(s):")
    
    fixed_count = 0
    for coll_id, coll_name, config_str in collections:
        print(f"\n  Collection: {coll_name}")
        print(f"  ID: {coll_id}")
        print(f"  Current config: {config_str}")
        
        if not config_str or config_str.strip() in ('{}', ''):
            # Empty or minimal config - needs fixing
            print(f"  ⚠️  Fixing empty configuration...")
            
            # Update with default config
            new_config_str = json.dumps(default_config)
            cursor.execute("""
                UPDATE collections 
                SET config_json_str = ? 
                WHERE id = ?
            """, (new_config_str, coll_id))
            
            fixed_count += 1
            print(f"  ✓ Fixed!")
        else:
            # Check if it has _type field
            try:
                config = json.loads(config_str)
                if '_type' not in config:
                    print(f"  ⚠️  Missing _type field, fixing...")
                    config['_type'] = 'CollectionConfigurationInternal'
                    
                    if 'hnsw_configuration' in config and '_type' not in config['hnsw_configuration']:
                        config['hnsw_configuration']['_type'] = 'HNSWConfigurationInternal'
                    
                    new_config_str = json.dumps(config)
                    cursor.execute("""
                        UPDATE collections 
                        SET config_json_str = ? 
                        WHERE id = ?
                    """, (new_config_str, coll_id))
                    
                    fixed_count += 1
                    print(f"  ✓ Fixed!")
                else:
                    print(f"  ✓ Configuration OK")
            except json.JSONDecodeError:
                print(f"  ✗ Invalid JSON, fixing...")
                new_config_str = json.dumps(default_config)
                cursor.execute("""
                    UPDATE collections 
                    SET config_json_str = ? 
                    WHERE id = ?
                """, (new_config_str, coll_id))
                fixed_count += 1
                print(f"  ✓ Fixed!")
    
    # Commit changes
    conn.commit()
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} collection(s)")
    print(f"{'='*60}")
    
    # Verify fix
    print("\nVerifying fix...")
    cursor.execute("""
        SELECT id, name, config_json_str 
        FROM collections
    """)
    
    collections = cursor.fetchall()
    all_ok = True
    for coll_id, coll_name, config_str in collections:
        try:
            config = json.loads(config_str)
            if '_type' in config:
                print(f"  ✓ {coll_name}: OK")
            else:
                print(f"  ✗ {coll_name}: Still missing _type")
                all_ok = False
        except Exception as e:
            print(f"  ✗ {coll_name}: Error: {e}")
            all_ok = False
    
    if all_ok:
        print(f"\n✓ All collections are now compatible with ChromaDB 0.6+")
    else:
        print(f"\n✗ Some collections still have issues")
    
    conn.close()
    
except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
