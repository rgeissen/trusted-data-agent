#!/usr/bin/env python3
"""Test ChromaDB 0.6 collection listing"""

import chromadb
from pathlib import Path
from chromadb.utils import embedding_functions

project_root = Path(__file__).resolve().parent
persist_dir = project_root / '.chromadb_rag_cache'

print(f"Testing ChromaDB collection access...")
print(f"Directory: {persist_dir}")

# Test 1: Client without embedding function
print("\n=== Test 1: Client without embedding function ===")
try:
    client1 = chromadb.PersistentClient(path=str(persist_dir))
    collections1 = client1.list_collections()
    print(f"Collections found: {len(collections1)}")
    for col in collections1:
        print(f"  - {col}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Client with embedding function
print("\n=== Test 2: Client with embedding function ===")
try:
    client2 = chromadb.PersistentClient(path=str(persist_dir))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collections2 = client2.list_collections()
    print(f"Collections found: {len(collections2)}")
    for col_name in collections2:
        print(f"  - {col_name}")
        try:
            # Try to get collection with embedding function
            col = client2.get_collection(name=str(col_name), embedding_function=embedding_fn)
            print(f"    Count with embedding_fn: {col.count()}")
        except Exception as e:
            print(f"    Error with embedding_fn: {e}")
        try:
            # Try to get collection without embedding function
            col2 = client2.get_collection(name=str(col_name))
            print(f"    Count without embedding_fn: {col2.count()}")
        except Exception as e:
            print(f"    Error without embedding_fn: {e}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
