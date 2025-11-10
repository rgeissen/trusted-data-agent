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
            self._maintain_vector_store()
        else:
            logger.info("RAG_REFRESH_ON_STARTUP is False. Using cached vector store.")

    def refresh_vector_store(self):
        """
        Manually triggers the maintenance of the vector store.
        """
        logger.info("Manual refresh of vector store triggered.")
        self._maintain_vector_store()

    def _maintain_vector_store(self):
        """
        Maintains the ChromaDB vector store by synchronizing it with the
        JSON case files on disk. It adds new cases, removes deleted ones,
        and updates existing ones if their metadata has changed.
        """
        logger.info(f"Starting vector store maintenance for {self.rag_cases_dir}...")
        
        # 1. Get current state from disk and DB
        disk_case_ids = {p.stem for p in self.rag_cases_dir.glob("case_*.json")}
        db_results = self.collection.get(include=["metadatas"])
        db_case_ids = set(db_results["ids"])
        db_metadatas = {db_results["ids"][i]: meta for i, meta in enumerate(db_results["metadatas"])}

        # 2. Identify cases to delete from DB
        ids_to_delete = list(db_case_ids - disk_case_ids)
        if ids_to_delete:
            logger.info(f"Found {len(ids_to_delete)} stale cases to remove from DB.")
            self.collection.delete(ids=ids_to_delete)

        # 3. Iterate through disk cases to add or update
        added_count = 0
        updated_count = 0
        for case_id_stem in disk_case_ids:
            case_file = self.rag_cases_dir / f"{case_id_stem}.json"
            try:
                with open(case_file, 'r', encoding='utf-8') as f:
                    case_data = json.load(f)
                
                # Prepare document and metadata for ChromaDB
                user_query = case_data.get("intent", {}).get("user_query", "")
                strategy_summary = self._summarize_strategy(case_data)
                
                if not user_query or not strategy_summary:
                    logger.warning(f"Skipping case {case_id_stem}: Missing user_query or strategy_summary.")
                    continue

                document_content = user_query
                
                metadata = {
                    "case_id": case_data["case_id"],
                    "user_query": user_query,
                    "strategy_type": "successful" if "successful_strategy" in case_data else "failed" if "failed_strategy" in case_data else "conversational",
                    "timestamp": case_data.get("metadata", {}).get("timestamp"),
                    "is_most_efficient": case_data.get("metadata", {}).get("is_most_efficient", False),
                    "full_case_data": json.dumps(case_data)
                }

                # Decide whether to add or update
                if case_id_stem not in db_case_ids:
                    # Add new case
                    self.collection.add(documents=[document_content], metadatas=[metadata], ids=[case_id_stem])
                    added_count += 1
                    logger.debug(f"Added new case {case_id_stem} to DB.")
                else:
                    # Check if update is needed by comparing the full content
                    existing_meta = db_metadatas.get(case_id_stem, {})
                    try:
                        existing_case_data = json.loads(existing_meta.get("full_case_data", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        existing_case_data = {}

                    # If the file on disk is different from what's in the DB, update.
                    if case_data != existing_case_data:
                        self.collection.update(
                            ids=[case_id_stem],
                            metadatas=[metadata],
                            documents=[document_content] # Ensure embedding is updated too
                        )
                        updated_count += 1
                        logger.info(f"Updated case {case_id_stem} in DB because content has changed.")

            except Exception as e:
                logger.error(f"Failed to process RAG case file {case_file.name}: {e}", exc_info=True)
        
        logger.info(f"Vector store maintenance complete. Added: {added_count}, Updated: {updated_count}, Removed: {len(ids_to_delete)}.")

    def _summarize_strategy(self, case_data: Dict[str, Any]) -> str:
        """
        Creates a concise string summary of a strategy from the case data.
        """
        if "successful_strategy" in case_data:
            strategy = case_data["successful_strategy"]
            phase_summaries = []
            for phase in strategy.get("phases", []):
                goal = phase.get("goal", "No goal specified.")
                tool = phase.get("tool", "No tool specified.")
                phase_summaries.append(f"Phase {phase.get('phase', 'N/A')}: Goal '{goal}', Tool '{tool}'")
            return " -> ".join(phase_summaries)
        elif "failed_strategy" in case_data:
            return f"Failed with error: {case_data['failed_strategy'].get('error_summary', 'details unavailable.')}"
        elif "conversational_response" in case_data:
            return case_data["conversational_response"].get("summary", "Conversational response.")
        return "Strategy details unavailable."

    def retrieve_examples(self, query: str, k: int = 3, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most relevant and efficient RAG cases based on the query.
        """
        logger.info(f"Retrieving top {k} RAG examples for query: '{query}' (min_score: {min_score})")
        
        query_results = self.collection.query(
            query_texts=[query],
            n_results=k * 10, # Retrieve more candidates to filter
            where={"strategy_type": "successful", "is_most_efficient": True}, # Only retrieve successful and most efficient cases
            include=["metadatas", "distances"]
        )

        candidate_cases = []
        if query_results and query_results["ids"] and query_results["ids"][0]:
            for i in range(len(query_results["ids"][0])):
                case_id = query_results["ids"][0][i]
                metadata = query_results["metadatas"][0][i]
                distance = query_results["distances"][0][i]
                
                similarity_score = 1 - distance 

                if similarity_score < min_score:
                    logger.debug(f"Skipping case {case_id} due to low similarity score: {similarity_score:.2f}")
                    continue
                
                full_case_data = json.loads(metadata["full_case_data"])
                
                candidate_cases.append({
                    "case_id": case_id,
                    "user_query": metadata["user_query"],
                    "strategy_type": metadata.get("strategy_type", "unknown"),
                    "full_case_data": full_case_data,
                    "similarity_score": similarity_score,
                    "is_most_efficient": metadata.get("is_most_efficient")
                })
        
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
