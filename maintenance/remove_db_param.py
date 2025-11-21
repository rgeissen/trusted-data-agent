# maintenance/remove_db_param.py
import os
import json
import logging
from pathlib import Path
import sys

# Add project root to path to allow imports
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / 'src'))

from trusted_data_agent.agent.rag_retriever import RAGRetriever
from trusted_data_agent.core.config import APP_CONFIG, APP_STATE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("remove_db_param_script")

def remove_database_name_parameter():
    """
    Iterates through all case files in collection_1, removes the 'database_name'
    parameter from the arguments of the first phase, and then triggers a
    refresh of the vector store.
    """
    collection_id_to_modify = 1
    
    # Initialize the retriever to get access to its config and methods
    try:
        rag_cases_dir = project_root / APP_CONFIG.RAG_CASES_DIR
        persist_dir = project_root / APP_CONFIG.RAG_PERSIST_DIR
        
        # We need to initialize the retriever to get the collection loaded
        # and to use its refresh method.
        retriever = RAGRetriever(rag_cases_dir=rag_cases_dir, persist_directory=persist_dir)
        
        collection_dir = retriever._get_collection_dir(collection_id_to_modify)
        if not collection_dir.exists():
            logger.error(f"Collection directory not found: {collection_dir}")
            return

        logger.info(f"Scanning files in {collection_dir}...")
        
        modified_files = 0
        case_files = list(collection_dir.glob("case_*.json"))

        if not case_files:
            logger.warning(f"No case files found in {collection_dir}.")
            return

        for case_file in case_files:
            try:
                with open(case_file, 'r+', encoding='utf-8') as f:
                    case_data = json.load(f)
                    
                    # Navigate to the arguments
                    strategy = case_data.get("successful_strategy", {})
                    phases = strategy.get("phases", [])
                    
                    if phases and isinstance(phases, list) and len(phases) > 0:
                        arguments = phases[0].get("arguments", {})
                        if "database_name" in arguments:
                            logger.info(f"Found and removing 'database_name' from {case_file.name}")
                            del arguments["database_name"]
                            
                            # Go back to the beginning of the file to overwrite
                            f.seek(0)
                            json.dump(case_data, f, indent=2)
                            f.truncate()
                            modified_files += 1

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"Could not process file {case_file.name}: {e}")
                continue
        
        logger.info(f"Finished processing files. {modified_files} files were modified.")

        # After modifying files, refresh the vector store for the collection
        # The refresh is triggered by the _maintain_vector_store method which is called inside RAGRetriever
        # We can call the public method refresh_vector_store to trigger it.
        logger.info(f"Refreshing vector store for collection ID: {collection_id_to_modify}")
        retriever.refresh_vector_store(collection_id=collection_id_to_modify)
        logger.info("Vector store refresh complete.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    remove_database_name_parameter()
