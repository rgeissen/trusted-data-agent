#!/usr/bin/env python3
"""Test script to verify RAG collection access without full app configuration"""

import chromadb
from pathlib import Path

# Get the ChromaDB path
project_root = Path(__file__).resolve().parent
persist_dir = project_root / '.chromadb_rag_cache'

print(f"ChromaDB path: {persist_dir}")
print(f"Directory exists: {persist_dir.exists()}")

try:
    # Create client
    client = chromadb.PersistentClient(path=str(persist_dir))
    print(f"✓ Successfully created ChromaDB client")
    
    # List collections (in v0.6+ this returns collection names only)
    collection_names = client.list_collections()
    print(f"\n✓ Found {len(collection_names)} collection(s):")
    
    for col_name in collection_names:
        # Get the actual collection object
        # col_name is already a string in v0.6+
        col = client.get_collection(name=str(col_name))
        
        print(f"\n  Collection: {str(col_name)}")
        print(f"  ID: {col.id}")
        
        # Get count
        count = col.count()
        print(f"  Total documents: {count}")
        
        if count > 0:
            # Get first few documents
            result = col.get(limit=3, include=['documents', 'metadatas'])
            print(f"  Sample documents: {len(result['ids'])}")
            
            for i, doc_id in enumerate(result['ids']):
                print(f"\n    Document {i+1}:")
                print(f"      ID: {doc_id}")
                if result['documents'][i]:
                    print(f"      Content: {result['documents'][i][:100]}...")
                if result['metadatas'][i]:
                    print(f"      Metadata: {result['metadatas'][i]}")
        else:
            print(f"  ⚠️  Collection is empty")

except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
