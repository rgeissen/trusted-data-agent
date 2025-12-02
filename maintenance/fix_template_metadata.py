#!/usr/bin/env python3
"""
Fix is_most_efficient metadata in ChromaDB for template-generated cases.

The issue: Template-generated cases have is_most_efficient=True in their JSON files,
but ChromaDB stores it as the string "None" due to incorrect metadata preparation.

This script:
1. Finds all documents with is_most_efficient="None"
2. Updates them to is_most_efficient=True (boolean)
3. Reports the changes made
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trusted_data_agent.agent.rag_retriever import RAGRetriever
from trusted_data_agent.core.config_manager import get_config_manager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_template_metadata():
    """Fix is_most_efficient metadata for template-generated cases."""
    try:
        # Initialize retriever
        logger.info("Initializing RAG retriever...")
        config_manager = get_config_manager()
        retriever = RAGRetriever()
        
        total_fixed = 0
        
        for coll_id, collection in retriever.collections.items():
            logger.info(f"\n=== Processing Collection {coll_id}: {collection.name} ===")
            
            # Get all documents with is_most_efficient="None" (stored as string)
            try:
                results = collection.get(
                    where={"is_most_efficient": "None"},
                    include=["metadatas"]
                )
                
                if not results or not results.get('ids'):
                    logger.info(f"  No documents with is_most_efficient='None' found")
                    continue
                
                ids_to_fix = results['ids']
                metadatas_to_fix = results['metadatas']
                
                logger.info(f"  Found {len(ids_to_fix)} documents to fix")
                
                # Update each document
                for doc_id, metadata in zip(ids_to_fix, metadatas_to_fix):
                    # Set is_most_efficient to True (boolean)
                    metadata['is_most_efficient'] = True
                    
                    # Also fix other boolean fields if they're strings
                    for field in ['is_success', 'had_plan_improvements', 'had_tactical_improvements', 'has_orchestration']:
                        if field in metadata:
                            val = metadata[field]
                            if val == "None" or val is None:
                                metadata[field] = False
                            elif val == "True" or val is True:
                                metadata[field] = True
                            elif val == "False" or val is False:
                                metadata[field] = False
                    
                    # Update in ChromaDB
                    collection.update(
                        ids=[doc_id],
                        metadatas=[metadata]
                    )
                    
                    total_fixed += 1
                    
                    if total_fixed % 10 == 0:
                        logger.info(f"  Fixed {total_fixed} documents so far...")
                
                logger.info(f"  ✓ Fixed {len(ids_to_fix)} documents in collection {coll_id}")
                
            except Exception as e:
                logger.error(f"  Error processing collection {coll_id}: {e}", exc_info=True)
        
        logger.info(f"\n=== Summary ===")
        logger.info(f"Total documents fixed: {total_fixed}")
        logger.info("Done!")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    fix_template_metadata()
