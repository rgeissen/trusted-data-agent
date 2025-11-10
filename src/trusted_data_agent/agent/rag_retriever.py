import os
import json
import glob
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

from trusted_data_agent.core.config import APP_CONFIG

# Configure a dedicated logger for the RAG retriever
logger = logging.getLogger("rag_retriever")

class RAGRetriever:
    def __init__(self, rag_cases_dir: str | Path, embedding_model_name: str = "all-MiniLM-L6-v2", persist_directory: Optional[str | Path] = None):
        self.rag_cases_dir = Path(rag_cases_dir).resolve()
        self.embedding_model_name = embedding_model_name
        self.persist_directory = Path(persist_directory).resolve() if persist_directory else None

        if not self.rag_cases_dir.exists():
            logger.error(f"RAG cases directory not found at: {self.rag_cases_dir}")
            raise FileNotFoundError(f"RAG cases directory not found: {self.rag_cases_dir}")

        # Initialize ChromaDB client
        if self.persist_directory:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.persist_directory))
            logger.info(f"ChromaDB initialized with persistence at: {self.persist_directory}")
        else:
            self.client = chromadb.Client()
            logger.info("ChromaDB initialized in in-memory mode.")

        # Initialize embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model_name
        )
        logger.info(f"Embedding model loaded: {self.embedding_model_name}")

        self.collection_name = "tda_rag_cases_collection"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"} # Use cosine similarity for retrieval
        )
        logger.info(f"ChromaDB collection '{self.collection_name}' ready.")

        if APP_CONFIG.RAG_REFRESH_ON_STARTUP:
            logger.info("RAG_REFRESH_ON_STARTUP is True. Refreshing vector store...")
            self._load_and_process_cases()
        else:
            logger.info("RAG_REFRESH_ON_STARTUP is False. Using cached vector store.")

    def refresh_vector_store(self):
        """
        Manually triggers the loading and processing of RAG cases into ChromaDB.
        """
        logger.info("Manual refresh of vector store triggered.")
        self._load_and_process_cases()

    def _load_and_process_cases(self):
        """
        Loads RAG cases from JSON files, extracts relevant information,
        and adds them to the ChromaDB collection if not already present.
        """
        logger.info(f"Loading and processing RAG cases from {self.rag_cases_dir}...")
        
        existing_ids = set(self.collection.get(limit=999999)["ids"])
        
        case_files = list(self.rag_cases_dir.glob("case_*.json"))
        new_cases_count = 0

        for case_file in case_files:
            case_id = case_file.stem # e.g., "case_fcbd78d5-ba63-5f51-8ace-29e391a76f76"
            if case_id in existing_ids:
                logger.debug(f"Case {case_id} already in ChromaDB. Skipping.")
                continue

            try:
                with open(case_file, 'r', encoding='utf-8') as f:
                    case_data = json.load(f)
                
                # Extract user query and strategy summary
                user_query = case_data.get("intent", {}).get("user_query", "")
                
                strategy_summary = ""
                if case_data.get("successful_strategy"):
                    strategy_summary = self._summarize_strategy(case_data["successful_strategy"])
                elif case_data.get("failed_strategy"):
                    strategy_summary = self._summarize_strategy(case_data["failed_strategy"])
                elif case_data.get("conversational_response"):
                    strategy_summary = case_data["conversational_response"].get("summary", "")

                if not user_query or not strategy_summary:
                    logger.warning(f"Skipping case {case_id}: Missing user_query or strategy_summary.")
                    continue

                # Combine for embedding
                document_content = f"User Query: {user_query}\nAgent Strategy: {strategy_summary}"
                
                # Store full case data as metadata
                metadata = {
                    "case_id": case_id,
                    "user_query": user_query,
                    "strategy_type": "successful" if case_data.get("successful_strategy") else "failed" if case_data.get("failed_strategy") else "conversational",
                    "timestamp": case_data.get("metadata", {}).get("timestamp"),
                    "full_case_data": json.dumps(case_data) # Store full JSON for later retrieval
                }

                self.collection.add(
                    documents=[document_content],
                    metadatas=[metadata],
                    ids=[case_id]
                )
                new_cases_count += 1
                logger.debug(f"Added case {case_id} to ChromaDB.")

            except Exception as e:
                logger.error(f"Failed to process RAG case file {case_file.name}: {e}", exc_info=True)
        
        logger.info(f"Finished loading RAG cases. Added {new_cases_count} new cases.")

    def _summarize_strategy(self, strategy: Dict[str, Any]) -> str:
        """
        Creates a concise string summary of a strategy (successful or failed).
        """
        if "phases" in strategy and isinstance(strategy["phases"], list):
            phase_summaries = []
            for phase in strategy["phases"]:
                goal = phase.get("goal", "No goal specified.")
                tool = phase.get("tool", "No tool specified.")
                phase_summaries.append(f"Phase {phase.get('phase', 'N/A')}: Goal '{goal}', Tool '{tool}'")
            return " -> ".join(phase_summaries)
        elif "error_summary" in strategy:
            return f"Failed with error: {strategy['error_summary']}"
        return "Strategy details unavailable."

    def retrieve_examples(self, query: str, k: int = 3, filter_successful: bool = True, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most relevant RAG cases based on the query.
        Applies selection strategy (e.g., prioritizing successful cases and minimum score).
        """
        logger.info(f"Retrieving top {k} RAG examples for query: '{query}' (min_score: {min_score})")
        
        # Retrieve a larger set of results to allow for post-filtering and scoring
        # We retrieve more than k to ensure we have enough candidates after filtering
        query_results = self.collection.query(
            query_texts=[query],
            n_results=k * 10, # Retrieve more candidates
            include=["metadatas", "distances"] # Include distances for scoring
        )

        candidate_cases = []
        if query_results and query_results["ids"] and query_results["ids"][0]:
            for i in range(len(query_results["ids"][0])):
                case_id = query_results["ids"][0][i]
                metadata = query_results["metadatas"][0][i]
                distance = query_results["distances"][0][i]
                
                # Convert distance to similarity score (cosine distance is 1 - cosine similarity)
                similarity_score = 1 - distance 

                if similarity_score < min_score:
                    logger.debug(f"Skipping case {case_id} due to low similarity score: {similarity_score:.2f}")
                    continue

                # Apply filter_successful logic
                if filter_successful and metadata.get("strategy_type") != "successful":
                    logger.debug(f"Skipping case {case_id} due to non-successful strategy type.")
                    continue
                
                full_case_data = json.loads(metadata["full_case_data"])
                
                candidate_cases.append({
                    "case_id": case_id,
                    "user_query": metadata["user_query"],
                    "strategy_type": metadata.get("strategy_type", "unknown"),
                    "full_case_data": full_case_data,
                    "similarity_score": similarity_score
                })
        
        # Sort by similarity score (highest first) and return top k
        candidate_cases.sort(key=lambda x: x["similarity_score"], reverse=True)
        return candidate_cases[:k]

    def _format_few_shot_example(self, case: Dict[str, Any]) -> str:
        """
        Formats a retrieved RAG case into a string suitable for the prompt.
        """
        user_query = case["user_query"]
        case_id = case["case_id"]
        
        strategy_type = case.get("strategy_type", "unknown")
        plan_content = ""
        thought_process_summary = ""

        if strategy_type == "successful":
            plan_json = "[]"
            if case["full_case_data"].get("successful_strategy", {}).get("phases"):
                plan_json = json.dumps(case["full_case_data"]["successful_strategy"]["phases"], indent=2)
            plan_content = f"- **Correct Plan**:\n```json\n{plan_json}\n```"
            thought_process_summary = f"Retrieved RAG case `{case_id}` demonstrates a successful strategy for this type of query."
        elif strategy_type == "failed":
            error_summary = case["full_case_data"].get("failed_strategy", {}).get("error_summary", "an unspecified error.")
            plan_content = f"- **Failed Action**: {json.dumps(case['full_case_data'].get('failed_strategy', {}).get('failed_action', {}), indent=2)}"
            thought_process_summary = f"Retrieved RAG case `{case_id}` shows a past failure with error: {error_summary}. This helps in avoiding similar pitfalls."
        elif strategy_type == "conversational":
            conversation_summary = case["full_case_data"].get("conversational_response", {}).get("summary", "a conversational response.")
            plan_content = f"- **Conversational Response**: {conversation_summary}"
            thought_process_summary = f"Retrieved RAG case `{case_id}` indicates a conversational interaction: {conversation_summary}."
        else:
            thought_process_summary = f"Retrieved RAG case `{case_id}` with unknown strategy type."

        formatted_example = f"""### RAG Example (Case ID: {case_id})
- **User Goal**: "{user_query}"
- **Thought Process**:
  1. The user's request is similar to a past interaction.
  2. {thought_process_summary}
{plan_content}"""
        return formatted_example

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Assuming tda_rag_cases is in the parent directory of this script
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent # trusted-data-agent
    rag_cases_dir = project_root / "rag" / "tda_rag_cases"
    persist_dir = project_root / ".chromadb_rag_cache" # Persistent storage for ChromaDB

    # Configure logging for main execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.DEBUG) # Set RAG retriever logger to DEBUG for detailed output

    try:
        retriever = RAGRetriever(rag_cases_dir=rag_cases_dir, persist_directory=persist_dir)
        
        test_query = "educate yourself on the ddls of the fitness_db database"
        few_shot_examples = retriever.retrieve_examples(test_query, k=1)

        if few_shot_examples:
            print(f"\n--- Retrieved Few-Shot Examples for '{test_query}' ---")
            for example in few_shot_examples:
                print(retriever._format_few_shot_example(example))
        else:
            print(f"\nNo RAG examples found for '{test_query}'.")

        test_query_2 = "what is the quality of table 'online' in database 'DEMO_Customer360_db'?"
        few_shot_examples_2 = retriever.retrieve_examples(test_query_2, k=1)

        if few_shot_examples_2:
            print(f"\n--- Retrieved Few-Shot Examples for '{test_query_2}' ---")
            for example in few_shot_examples_2:
                print(retriever._format_few_shot_example(example))
        else:
            print(f"\nNo RAG examples found for '{test_query_2}'.")

    except Exception as e:
        logger.error(f"An error occurred during RAGRetriever example usage: {e}", exc_info=True)
