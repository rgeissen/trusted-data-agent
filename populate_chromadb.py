#!/usr/bin/env python3
"""
Manually populate ChromaDB from case files.
Run this after ChromaDB has been rebuilt to load all case studies.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.agent.rag_retriever import RAGRetriever
from trusted_data_agent.core.config_manager import get_config_manager

def main():
    print("=" * 70)
    print("Populating ChromaDB from case files")
    print("=" * 70)
    print()
    
    # Load configuration
    config_manager = get_config_manager()
    
    # Load RAG collections and MCP servers from config
    APP_STATE["rag_collections"] = config_manager.get_rag_collections()
    APP_CONFIG.CURRENT_MCP_SERVER_ID = config_manager.get_active_mcp_server_id()
    
    print(f"✅ Loaded configuration")
    print(f"   MCP Server ID: {APP_CONFIG.CURRENT_MCP_SERVER_ID}")
    print(f"   RAG Collections: {len(APP_STATE.get('rag_collections', []))}")
    print()
    
    # Initialize RAG retriever
    rag_cases_dir = project_root / "rag" / "tda_rag_cases"
    chromadb_path = project_root / ".chromadb_rag_cache"
    
    print(f"📁 RAG Cases Directory: {rag_cases_dir}")
    print(f"📁 ChromaDB Directory: {chromadb_path}")
    
    case_files = list(rag_cases_dir.glob("case_*.json"))
    print(f"📊 Found {len(case_files)} case files")
    print()
    
    if not case_files:
        print("⚠️  No case files found. Nothing to populate.")
        return
    
    try:
        retriever = RAGRetriever(
            rag_cases_dir=rag_cases_dir,
            persist_directory=chromadb_path
        )
        
        print(f"✅ RAGRetriever initialized")
        print(f"   Active collections: {len(retriever.collections)}")
        print()
        
        if not retriever.collections:
            print("⚠️  No active collections loaded.")
            print("   This usually means:")
            print("   1. No MCP server is configured")
            print("   2. Collections don't match current MCP server")
            print("   3. Collections are disabled")
            print()
            print("   Please configure the app via UI first, then run this script.")
            return
        
        # Refresh all collections
        print("🔄 Syncing case files to ChromaDB...")
        for coll_id in retriever.collections:
            coll_meta = retriever.get_collection_metadata(coll_id)
            if coll_meta:
                print(f"   Collection {coll_id}: {coll_meta['name']}")
            
            retriever._maintain_vector_store(coll_id)
            
            # Check count
            collection = retriever.collections[coll_id]
            count = collection.count()
            print(f"      → {count} documents loaded")
        
        print()
        print("✅ Population complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
