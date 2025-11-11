import os
import json
import logging
from pathlib import Path
from trusted_data_agent.agent.rag_retriever import RAGRetriever
from trusted_data_agent.core.config import APP_CONFIG

# Configure logging for the test script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Mock APP_CONFIG for testing purposes if it's not properly initialized
# In a real scenario, ensure APP_CONFIG is loaded correctly.
# For this test, we'll assume RAG_REFRESH_ON_STARTUP is False to avoid long refresh times.
class MockAppConfig:
    RAG_REFRESH_ON_STARTUP = False

APP_CONFIG = MockAppConfig()


def run_test():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent # trusted-data-agent
    rag_cases_dir = project_root / "rag" / "tda_rag_cases"
    persist_dir = project_root / ".chromadb_rag_cache"

    logger.info(f"Using RAG cases directory: {rag_cases_dir}")
    logger.info(f"Using ChromaDB persistence directory: {persist_dir}")

    try:
        # Initialize RAGRetriever
        retriever = RAGRetriever(rag_cases_dir=rag_cases_dir, persist_directory=persist_dir)
        
        # Manually refresh the vector store to ensure it's up-to-date for the test
        # This is important if APP_CONFIG.RAG_REFRESH_ON_STARTUP is False
        logger.info("Manually refreshing vector store for test...")
        retriever.refresh_vector_store()
        logger.info("Vector store refresh complete.")

        # Test query 1: Should trigger the new filtering logic
        test_query_1 = "what are the top 5 products by revenue generated?"
        logger.info(f"\n--- Testing query: '{test_query_1}' ---")
        few_shot_examples_1 = retriever.retrieve_examples(test_query_1, k=3)

        if few_shot_examples_1:
            logger.info(f"Retrieved {len(few_shot_examples_1)} examples for '{test_query_1}':")
            for i, example in enumerate(few_shot_examples_1):
                logger.info(f"  Example {i+1}: Case ID: {example['case_id']}, Similarity: {example['similarity_score']:.2f}, "
                            f"Plan Improvements: {example['had_plan_improvements']}, Tactical Improvements: {example['had_tactical_improvements']}")
        else:
            logger.info(f"No RAG examples found for '{test_query_1}'.")

        # Test query 2: Another query to see if filtering works generally
        test_query_2 = "how to get the schema of the customer database?"
        logger.info(f"\n--- Testing query: '{test_query_2}' ---")
        few_shot_examples_2 = retriever.retrieve_examples(test_query_2, k=3)

        if few_shot_examples_2:
            logger.info(f"Retrieved {len(few_shot_examples_2)} examples for '{test_query_2}':")
            for i, example in enumerate(few_shot_examples_2):
                logger.info(f"  Example {i+1}: Case ID: {example['case_id']}, Similarity: {example['similarity_score']:.2f}, "
                            f"Plan Improvements: {example['had_plan_improvements']}, Tactical Improvements: {example['had_tactical_improvements']}")
        else:
            logger.info(f"No RAG examples found for '{test_query_2}'.")

    except Exception as e:
        logger.error(f"An error occurred during RAGRetriever test: {e}", exc_info=True)

if __name__ == "__main__":
    run_test()
