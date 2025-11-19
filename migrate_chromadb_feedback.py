#!/usr/bin/env python3
"""
Migration script to rebuild ChromaDB with user_feedback_score field.

This script:
1. Backs up the existing ChromaDB directory
2. Deletes the corrupted ChromaDB
3. Rebuilds from the JSON case files in rag/tda_rag_cases/
4. All cases will have user_feedback_score=0 (neutral) by default

Usage:
    python migrate_chromadb_feedback.py
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from trusted_data_agent.core.config import APP_CONFIG
from trusted_data_agent.agent.rag_retriever import RAGRetriever

def main():
    chromadb_path = project_root / ".chromadb_rag_cache"
    backup_path = project_root / f".chromadb_rag_cache_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("=" * 70)
    print("ChromaDB Migration: Adding user_feedback_score support")
    print("=" * 70)
    print()
    
    # Check if ChromaDB exists
    if not chromadb_path.exists():
        print(f"❌ ChromaDB directory not found: {chromadb_path}")
        print("Nothing to migrate.")
        return
    
    print(f"📁 Current ChromaDB location: {chromadb_path}")
    print(f"💾 Will create backup at: {backup_path}")
    print()
    
    # Confirm with user
    response = input("⚠️  This will rebuild ChromaDB from scratch. Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Migration cancelled.")
        return
    
    print()
    print("Step 1: Creating backup...")
    try:
        shutil.copytree(chromadb_path, backup_path)
        print(f"✅ Backup created at: {backup_path}")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        print("Migration aborted for safety.")
        return
    
    print()
    print("Step 2: Removing old ChromaDB directory...")
    try:
        shutil.rmtree(chromadb_path)
        print(f"✅ Removed: {chromadb_path}")
    except Exception as e:
        print(f"❌ Failed to remove ChromaDB: {e}")
        print("You may need to manually delete it.")
        return
    
    print()
    print("Step 3: Rebuilding ChromaDB from JSON case files...")
    try:
        rag_cases_dir = project_root / "rag" / "tda_rag_cases"
        
        # Initialize RAGRetriever (will create new ChromaDB)
        retriever = RAGRetriever(
            rag_cases_dir=rag_cases_dir,
            persist_directory=chromadb_path
        )
        
        print(f"✅ New ChromaDB initialized")
        print(f"📊 Active collections: {len(retriever.collections)}")
        
        # Refresh all collections to rebuild from disk
        print()
        print("Step 4: Syncing case files to ChromaDB...")
        for coll_id in retriever.collections:
            print(f"   Syncing collection {coll_id}...")
            retriever._maintain_vector_store(coll_id)
        
        print()
        print("✅ Migration complete!")
        print()
        print("📝 Summary:")
        print(f"   - Backup saved: {backup_path}")
        print(f"   - New ChromaDB: {chromadb_path}")
        print(f"   - All cases have user_feedback_score=0 (neutral)")
        print()
        print("💡 You can now:")
        print("   1. Start the application normally")
        print("   2. User feedback will be tracked going forward")
        print("   3. If issues occur, restore from backup")
        print()
        
    except Exception as e:
        print(f"❌ Failed to rebuild ChromaDB: {e}")
        print()
        print("To restore from backup:")
        print(f"   rm -rf {chromadb_path}")
        print(f"   cp -r {backup_path} {chromadb_path}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main()
