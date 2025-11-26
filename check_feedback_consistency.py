#!/usr/bin/env python3
"""
Check feedback consistency between ChromaDB and case files for default collection.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add project to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / 'src'))

import chromadb
from trusted_data_agent.core.config import APP_CONFIG

def check_consistency():
    """Check feedback consistency between ChromaDB and filesystem."""
    
    print("\n" + "="*80)
    print("FEEDBACK CONSISTENCY CHECK - DEFAULT COLLECTION")
    print("="*80 + "\n")
    
    # ChromaDB path
    persist_dir = project_root / '.chromadb_rag_cache'
    cases_dir = project_root / 'rag' / 'tda_rag_cases' / 'collection_0'
    
    print(f"ChromaDB path: {persist_dir}")
    print(f"Cases path: {cases_dir}\n")
    
    if not persist_dir.exists():
        print("❌ ChromaDB directory does not exist")
        return
    
    if not cases_dir.exists():
        print("❌ Cases directory does not exist")
        return
    
    # Load ChromaDB
    try:
        client = chromadb.PersistentClient(path=str(persist_dir))
        # Try different possible collection names
        collection_names = ["default_collection", "tda_rag_coll_0_default"]
        collection = None
        used_name = None
        for name in collection_names:
            try:
                collection = client.get_collection(name=name)
                used_name = name
                break
            except:
                pass
        
        if not collection:
            # List available collections
            available = client.list_collections()
            print(f"Available collections: {[col.name for col in available]}")
            raise Exception("Could not find default collection")
        
        print(f"✅ Loaded ChromaDB collection: {used_name}")
    except Exception as e:
        print(f"❌ Failed to load ChromaDB: {e}")
        return
    
    # Get all case files from filesystem
    case_files = list(cases_dir.glob('case_*.json'))
    print(f"✅ Found {len(case_files)} case files in filesystem\n")
    
    # Statistics
    stats = {
        'total': len(case_files),
        'filesystem_feedback': defaultdict(int),
        'chroma_feedback': defaultdict(int),
        'mismatches': [],
        'missing_in_chroma': [],
        'consistent': 0,
    }
    
    # Check each case
    for case_file in sorted(case_files)[:50]:  # Check first 50
        try:
            with open(case_file, 'r') as f:
                case_data = json.load(f)
            
            case_id = case_data.get('case_id', case_file.stem.replace('case_', ''))
            fs_feedback = case_data.get('metadata', {}).get('user_feedback_score', 0)
            
            # Look up in ChromaDB
            try:
                result = collection.get(ids=[case_id], include=['metadatas'])
                if result and result['ids']:
                    chroma_feedback = result['metadatas'][0].get('user_feedback_score', 0)
                else:
                    chroma_feedback = None
                    stats['missing_in_chroma'].append(case_id)
            except Exception as e:
                chroma_feedback = None
                stats['missing_in_chroma'].append(case_id)
            
            # Track statistics
            stats['filesystem_feedback'][fs_feedback] += 1
            if chroma_feedback is not None:
                stats['chroma_feedback'][chroma_feedback] += 1
            
            # Check for mismatch
            if chroma_feedback is not None and fs_feedback != chroma_feedback:
                stats['mismatches'].append({
                    'case_id': case_id[:8] + '...',
                    'filesystem': fs_feedback,
                    'chromadb': chroma_feedback,
                })
                print(f"⚠️  MISMATCH: {case_id[:8]}... | FS: {fs_feedback:2} | Chroma: {chroma_feedback:2}")
            else:
                stats['consistent'] += 1
        
        except Exception as e:
            print(f"❌ Error checking {case_file.name}: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nCases checked: {stats['total']}")
    print(f"Consistent: {stats['consistent']}")
    print(f"Mismatches: {len(stats['mismatches'])}")
    print(f"Missing in ChromaDB: {len(stats['missing_in_chroma'])}")
    
    print(f"\nFilesystem feedback distribution:")
    for score, count in sorted(stats['filesystem_feedback'].items()):
        labels = {-1: "downvote", 0: "neutral", 1: "upvote"}
        print(f"  {labels.get(score, score):10s}: {count:3d}")
    
    print(f"\nChromaDB feedback distribution:")
    for score, count in sorted(stats['chroma_feedback'].items()):
        labels = {-1: "downvote", 0: "neutral", 1: "upvote"}
        print(f"  {labels.get(score, score):10s}: {count:3d}")
    
    if stats['mismatches']:
        print(f"\n⚠️  INCONSISTENCIES FOUND:")
        for mismatch in stats['mismatches'][:10]:
            print(f"  {mismatch['case_id']} | FS: {mismatch['filesystem']:2} | Chroma: {mismatch['chromadb']:2}")
        if len(stats['mismatches']) > 10:
            print(f"  ... and {len(stats['mismatches']) - 10} more")
    else:
        print(f"\n✅ NO INCONSISTENCIES FOUND - All feedback is consistent!")
    
    if stats['missing_in_chroma']:
        print(f"\n⚠️  CASES MISSING IN CHROMADB:")
        for case_id in stats['missing_in_chroma'][:5]:
            print(f"  {case_id[:8]}...")
        if len(stats['missing_in_chroma']) > 5:
            print(f"  ... and {len(stats['missing_in_chroma']) - 5} more")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    check_consistency()
