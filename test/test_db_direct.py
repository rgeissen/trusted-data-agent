#!/usr/bin/env python3
"""Direct database test to isolate the issue."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from trusted_data_agent.core.collection_db import CollectionDatabase

collection_id = 7

try:
    db = CollectionDatabase()
    conn = db._get_connection()
    cursor = conn.cursor()
    
    # Test 1: Query collection
    print("Test 1: Query collection...")
    cursor.execute("""
        SELECT repository_type, owner_user_id FROM collections
        WHERE id = ?
    """, (collection_id,))
    
    result = cursor.fetchone()
    print(f"  Collection result: {dict(result) if result else None}")
    
    if result:
        # Test 2: Query documents
        print("\nTest 2: Query documents...")
        cursor.execute("""
            SELECT * FROM knowledge_documents
            WHERE collection_id = ?
            ORDER BY created_at DESC
        """, (collection_id,))
        
        rows = cursor.fetchall()
        print(f"  Found {len(rows)} documents")
        
        documents = []
        for row in rows:
            doc = dict(row)
            # Parse tags
            if doc.get('tags'):
                doc['tags'] = [t.strip() for t in doc['tags'].split(',')]
            else:
                doc['tags'] = []
            documents.append(doc)
        
        print(f"  Processed {len(documents)} documents")
        print("✓ Success!")
    
    conn.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
