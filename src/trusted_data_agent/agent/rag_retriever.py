import os
import json
import glob
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
# --- MODIFICATION START: Import uuid and copy ---
import uuid
import copy
# --- MODIFICATION END ---

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
                
                # --- MODIFICATION START: Use new metadata helper ---
                metadata = self._prepare_chroma_metadata(case_data)
                # --- MODIFICATION END ---

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
                # --- MODIFICATION START: Handle relevant_tools list ---
                tool = (phase.get("relevant_tools") or ["No tool specified."])[0]
                # --- MODIFICATION END ---
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
        
        # --- MODIFICATION START: Fix ChromaDB $and syntax ---
        query_results = self.collection.query(
            query_texts=[query],
            n_results=k * 10, # Retrieve more candidates to filter
            where={"$and": [
                {"strategy_type": {"$eq": "successful"}},
                {"is_most_efficient": {"$eq": True}}
            ]}, # Only retrieve successful and most efficient cases
            include=["metadatas", "distances"]
        )
        # --- MODIFICATION END ---

        all_candidate_cases = []
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
                
                all_candidate_cases.append({
                    "case_id": case_id,
                    "user_query": metadata["user_query"],
                    "strategy_type": metadata.get("strategy_type", "unknown"),
                    "full_case_data": full_case_data,
                    "similarity_score": similarity_score,
                    "is_most_efficient": metadata.get("is_most_efficient"),
                    "had_plan_improvements": full_case_data.get("metadata", {}).get("had_plan_improvements", False),
                    "had_tactical_improvements": full_case_data.get("metadata", {}).get("had_tactical_improvements", False)
                })
        
        # Sort all candidates by similarity score first
        all_candidate_cases.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Apply hierarchical filtering
        no_improvements = []
        no_tactical_improvements = []
        other_successful_cases = []

        for case in all_candidate_cases:
            if not case["had_plan_improvements"] and not case["had_tactical_improvements"]:
                no_improvements.append(case)
            elif not case["had_tactical_improvements"]:
                no_tactical_improvements.append(case)
            else:
                other_successful_cases.append(case)
        
        final_candidates = []
        if no_improvements:
            final_candidates = no_improvements
            logger.debug(f"Prioritizing {len(no_improvements)} cases with no plan or tactical improvements.")
        elif no_tactical_improvements:
            final_candidates = no_tactical_improvements
            logger.debug(f"Prioritizing {len(no_tactical_improvements)} cases with no tactical improvements.")
        else:
            final_candidates = other_successful_cases
            logger.debug(f"No specific improvement categories found, returning {len(other_successful_cases)} other successful cases.")

        return final_candidates[:k]

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

    # --- MODIFICATION START: Add real-time processing methods ---
    
    def _extract_case_from_turn_summary(self, turn_summary: dict) -> dict | None:
        """
        Core logic to transform a raw turn_summary log into a clean Case Study.
        Adapted from rag_miner.py's _extract_case_study.
        """
        try:
            turn = turn_summary
            # Note: We rely on PlanExecutor to add session_id to the turn_summary
            session_id = turn.get("session_id")
            turn_id = turn.get("turn")

            if not session_id:
                logger.error(f"  -> Skipping turn {turn_id}: 'session_id' is missing from turn_summary.")
                return None
            if not turn_id:
                logger.error(f"  -> Skipping turn: 'turn' number is missing from turn_summary.")
                return None

            case_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{session_id}_{turn_id}"))
            trace = turn.get("execution_trace", [])

            for entry in trace:
                if not isinstance(entry, dict):
                    continue
                action = entry.get("action", {})
                if isinstance(action, dict) and action.get("tool_name") == "TDA_ContextReport":
                    logger.debug(f"  -> Skipping turn {turn.get('turn')} due to TDA_ContextReport usage.")
                    return None
            
            is_success = True
            had_plan_improvements = False
            had_tactical_improvements = False
            successful_actions_map = {}
            first_error_action = None

            for entry in trace:
                if not isinstance(entry, dict): continue
                action = entry.get("action", {})
                result = entry.get("result", {})
                action_is_dict = isinstance(action, dict)
                result_is_dict = isinstance(result, dict)

                if action_is_dict:
                    action_args = action.get("arguments", {})
                    action_meta = action.get("metadata", {})
                    tool_name = action.get("tool_name", "")
                    if isinstance(action_args, dict) and action_args.get("message") == "Unrecoverable Error": is_success = False
                    if isinstance(action_meta, dict) and action_meta.get("type") == "workaround": had_tactical_improvements = True
                    if tool_name == "TDA_SystemLog" and isinstance(action_args, dict) and action_args.get("message") == "System Correction":
                        if "Planner" in action_args.get("details", {}).get("summary", ""): had_plan_improvements = True
                
                if result_is_dict and result.get("status") == "error" and not first_error_action: first_error_action = action
                
                if result_is_dict and result.get("status") == "success" and action_is_dict:
                    tool_name = action.get("tool_name")
                    if tool_name and tool_name != "TDA_SystemLog":
                        phase_num = action.get("metadata", {}).get("phase_number", 0)
                        
                        original_phase = None
                        if turn.get("original_plan"):
                            for p in turn["original_plan"]:
                                if isinstance(p, dict) and p.get("phase") == phase_num:
                                    original_phase = p
                                    break
                        
                        if original_phase:
                            compliant_phase = {
                                "phase": phase_num,
                                "goal": original_phase.get("goal", "Execute tool."),
                                "relevant_tools": [tool_name]
                            }
                            if "type" in original_phase:
                                compliant_phase["type"] = original_phase["type"]
                            if "loop_over" in original_phase:
                                compliant_phase["loop_over"] = original_phase["loop_over"]
                            
                            # --- MODIFICATION START: Get arguments from the original plan, not the resolved action ---
                            # This saves the strategic placeholders (e.g., {"source": "result_of_phase_1"})
                            # instead of the raw data.
                            compliant_phase["arguments"] = original_phase.get("arguments", {})
                            # --- MODIFICATION END ---
                            
                            successful_actions_map[phase_num] = compliant_phase
                        else:
                            successful_actions_map[phase_num] = {
                                "phase": phase_num, 
                                "goal": "Goal not found in original plan.",
                                "relevant_tools": [tool_name], 
                                "arguments": action.get("arguments", {})
                            }
            
            case_study = {
                "case_id": case_id,
                "metadata": {
                    "session_id": session_id, "turn_id": turn.get("turn"), "is_success": is_success,
                    "had_plan_improvements": had_plan_improvements, "had_tactical_improvements": had_tactical_improvements,
                    "timestamp": turn.get("timestamp"),
                    "llm_config": {
                        "provider": turn.get("provider"), "model": turn.get("model"),
                        "input_tokens": turn.get("turn_input_tokens", 0), "output_tokens": turn.get("turn_output_tokens", 0)
                    },
                },
                "intent": {"user_query": turn.get("user_query")}
            }

            if not case_study["intent"]["user_query"]:
                logger.warning(f"  -> Skipping turn {turn.get('turn')}: 'user_query' is missing or empty.")
                return None

            if successful_actions_map:
                case_study["metadata"]["is_most_efficient"] = False # Default
                case_study["successful_strategy"] = {"phases": []}
                for phase_num in sorted(successful_actions_map.keys()):
                    action_info = successful_actions_map[phase_num]
                    case_study["successful_strategy"]["phases"].append(action_info)
                
                steps_per_phase = {}
                total_steps = 0
                for entry in trace:
                    if not isinstance(entry, dict): continue
                    action = entry.get("action", {})
                    if not isinstance(action, dict): continue
                    if action.get("tool_name") and action.get("tool_name") != "TDA_SystemLog":
                        phase_num = str(action.get("metadata", {}).get("phase_number", "N/A"))
                        steps_per_phase[phase_num] = steps_per_phase.get(phase_num, 0) + 1
                        total_steps += 1
                case_study["metadata"]["strategy_metrics"] = {"phase_count": len(turn.get("original_plan", [])), "steps_per_phase": steps_per_phase, "total_steps": total_steps}
            elif not is_success:
                case_study["failed_strategy"] = {"original_plan": turn.get("original_plan"), "error_summary": turn.get("final_summary", ""), "failed_action": first_error_action}
            else:
                case_study["conversational_response"] = { "summary": turn.get("final_summary", "") }

            return case_study
        except Exception as e:
            logger.error(f"  -> CRITICAL: An unexpected error occurred during case extraction for turn {turn.get('turn')}: {e}", exc_info=True)
            return None

    def _prepare_chroma_metadata(self, case_study: dict) -> dict:
        """Prepares the metadata dictionary for upserting into ChromaDB."""
        # Metadata for ChromaDB *must* be flat (str, int, float, bool).
        
        strategy_type = "unknown"
        if "successful_strategy" in case_study:
            strategy_type = "successful"
        elif "failed_strategy" in case_study:
            strategy_type = "failed"
        elif "conversational_response" in case_study:
            strategy_type = "conversational"

        metadata = {
            "case_id": case_study["case_id"],
            "user_query": case_study["intent"]["user_query"],
            "strategy_type": strategy_type,
            "timestamp": case_study["metadata"]["timestamp"],
            "is_most_efficient": case_study["metadata"].get("is_most_efficient", False),
            "had_plan_improvements": case_study["metadata"].get("had_plan_improvements", False),
            "had_tactical_improvements": case_study["metadata"].get("had_tactical_improvements", False),
            "output_tokens": case_study["metadata"].get("llm_config", {}).get("output_tokens", 0),
            # Store the full case data as a JSON string
            "full_case_data": json.dumps(case_study)
        }
        return metadata

    async def process_turn_for_rag(self, turn_summary: dict):
        """
        The main "consumer" method. It processes a single turn summary,
        determines its efficiency, and transactionally updates the vector store.
        """
        try:
            # 1. Extract & Filter
            case_study = self._extract_case_from_turn_summary(turn_summary)
            
            if not case_study or "successful_strategy" not in case_study:
                logger.debug("Skipping RAG processing: Turn was not a successful strategy.")
                return

            # 2. Get new case data
            new_case_id = case_study["case_id"]
            new_query = case_study["intent"]["user_query"]
            new_tokens = case_study["metadata"].get("llm_config", {}).get("output_tokens", 0)
            new_document = new_query # The document we embed is the user query
            
            logger.info(f"Processing RAG case {new_case_id} for query: '{new_query[:50]}...' (Tokens: {new_tokens})")

            # 3. Query ChromaDB for existing "most efficient"
            # --- MODIFICATION START: Fix ChromaDB $and syntax ---
            existing_cases = self.collection.get(
                where={"$and": [
                    {"user_query": {"$eq": new_query}},
                    {"is_most_efficient": {"$eq": True}}
                ]},
                include=["metadatas"]
            )
            # --- MODIFICATION END ---

            old_best_case_id = None
            old_best_case_tokens = float('inf')

            if existing_cases and existing_cases["ids"]:
                old_best_case_id = existing_cases["ids"][0]
                old_best_case_tokens = existing_cases["metadatas"][0].get("output_tokens", float('inf'))

            # 4. Compare & Decide
            id_to_demote = None
            if new_tokens < old_best_case_tokens:
                logger.info(f"New case {new_case_id} is MORE efficient ({new_tokens} tokens) than old case {old_best_case_id} ({old_best_case_tokens} tokens).")
                case_study["metadata"]["is_most_efficient"] = True
                id_to_demote = old_best_case_id
            else:
                logger.info(f"New case {new_case_id} ({new_tokens} tokens) is NOT more efficient than old case {old_best_case_id} ({old_best_case_tokens} tokens).")
                case_study["metadata"]["is_most_efficient"] = False
            
            new_metadata = self._prepare_chroma_metadata(case_study)

            # 5. Transact with ChromaDB
            # Step 5a: Upsert the new case
            self.collection.upsert(
                ids=[new_case_id],
                documents=[new_document],
                metadatas=[new_metadata]
            )
            logger.debug(f"Upserted new case {new_case_id} with is_most_efficient={new_metadata['is_most_efficient']}.")

            # Step 5b: Demote the old case if necessary
            if id_to_demote:
                logger.info(f"Demoting old best case: {id_to_demote}")
                # We must fetch the *full metadata* for the old case to update it
                old_case_meta_result = self.collection.get(ids=[id_to_demote], include=["metadatas"])
                if old_case_meta_result["metadatas"]:
                    meta_to_update = old_case_meta_result["metadatas"][0]
                    meta_to_update["is_most_efficient"] = False
                    self.collection.update(
                        ids=[id_to_demote],
                        metadatas=[meta_to_update]
                    )
                    logger.info(f"Successfully demoted old case {id_to_demote}.")
                else:
                    logger.warning(f"Could not find old case {id_to_demote} to demote it.")
            
            # 6. Save the case study JSON to disk
            output_path = self.rag_cases_dir / f"case_{new_case_id}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(case_study, f, indent=2)
            logger.debug(f"Saved case study JSON to disk: {output_path.name}")

        except Exception as e:
            logger.error(f"Error during real-time RAG processing: {e}", exc_info=True)
    
    # --- MODIFICATION END ---


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
            print(f"\n--- Retrieved Few-Shot Examples for '{test_query}' ---\n")
            for example in few_shot_examples:
                print(retriever._format_few_shot_example(example))
        else:
            print(f"\nNo RAG examples found for '{test_query}'.")

        test_query_2 = "what is the quality of table 'online' in database 'DEMO_Customer360_db'?"
        few_shot_examples_2 = retriever.retrieve_examples(test_query_2, k=1)

        if few_shot_examples_2:
            print(f"\n--- Retrieved Few-Shot Examples for '{test_query_2}' ---\n")
            for example in few_shot_examples_2:
                print(retriever._format_few_shot_example(example))
        else:
            print(f"\nNo RAG examples found for '{test_query_2}'.")

    except Exception as e:
        logger.error(f"An error occurred during RAGRetriever example usage: {e}", exc_info=True)