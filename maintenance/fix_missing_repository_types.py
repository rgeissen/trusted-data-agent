#!/usr/bin/env python3
"""
Fix collections that are missing repository_type field.
Sets default collections and planner collections to 'planner' type.
"""

import sqlite3
from pathlib import Path

def fix_repository_types():
    """Add repository_type='planner' to collections missing this field."""
    
    # Database path
    db_path = Path(__file__).parent.parent / "tda_auth.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    print(f"📊 Checking collections in: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if repository_type column exists
    cursor.execute("PRAGMA table_info(collections)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'repository_type' not in columns:
        print("⚠️  repository_type column doesn't exist in collections table")
        print("   Run: python maintenance/migrate_repository_types.py")
        conn.close()
        return
    
    # Find collections with NULL or empty repository_type
    cursor.execute("""
        SELECT id, name, collection_name, repository_type, owner_user_id
        FROM collections
        WHERE repository_type IS NULL OR repository_type = ''
    """)
    
    missing_type = cursor.fetchall()
    
    if not missing_type:
        print("✅ All collections have repository_type set")
        
        # Show all collections for verification
        cursor.execute("""
            SELECT id, name, collection_name, repository_type, owner_user_id
            FROM collections
            ORDER BY id
        """)
        all_collections = cursor.fetchall()
        
        print(f"\n📋 Total collections: {len(all_collections)}")
        print("\nCollections:")
        for coll_id, name, coll_name, repo_type, owner in all_collections:
            print(f"  ID {coll_id}: {name} (collection_name: {coll_name})")
            print(f"    - repository_type: {repo_type}")
            print(f"    - owner: {owner}")
        
        conn.close()
        return
    
    print(f"\n⚠️  Found {len(missing_type)} collections without repository_type:")
    for coll_id, name, coll_name, repo_type, owner in missing_type:
        print(f"  ID {coll_id}: {name} (collection_name: {coll_name})")
        print(f"    - Current repository_type: {repo_type or 'NULL'}")
        print(f"    - owner: {owner}")
    
    # Fix: Set all missing repository_type to 'planner'
    # (Default collections and existing collections are planner type)
    print("\n🔧 Setting repository_type='planner' for these collections...")
    
    cursor.execute("""
        UPDATE collections
        SET repository_type = 'planner'
        WHERE repository_type IS NULL OR repository_type = ''
    """)
    
    updated = cursor.rowcount
    conn.commit()
    
    print(f"✅ Updated {updated} collection(s)")
    
    # Verify the fix
    cursor.execute("""
        SELECT id, name, collection_name, repository_type, owner_user_id
        FROM collections
        ORDER BY id
    """)
    all_collections = cursor.fetchall()
    
    print(f"\n📋 Total collections after fix: {len(all_collections)}")
    print("\nAll collections:")
    for coll_id, name, coll_name, repo_type, owner in all_collections:
        print(f"  ID {coll_id}: {name} (collection_name: {coll_name})")
        print(f"    - repository_type: {repo_type}")
        print(f"    - owner: {owner}")
    
    conn.close()
    print("\n✅ Done! Refresh your UI to see the collections appear.")

if __name__ == "__main__":
    fix_repository_types()
