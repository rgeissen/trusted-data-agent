import os
import json
import glob
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
# --- MODIFICATION START: Import uuid, copy, and datetime ---
import uuid
import copy
from datetime import datetime, timezone
# --- MODIFICATION END ---

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

from trusted_data_agent.core.config import APP_CONFIG, APP_STATE
from trusted_data_agent.core.config_manager import get_config_manager

# Configure a dedicated logger for the RAG retriever
logger = logging.getLogger("rag_retriever")

class RAGRetriever:
    def __init__(self, rag_cases_dir: str | Path, embedding_model_name: str = "all-MiniLM-L6-v2", persist_directory: Optional[str | Path] = None):
        self.rag_cases_dir = Path(rag_cases_dir).resolve()
        self.embedding_model_name = embedding_model_name
        self.persist_directory = Path(persist_directory).resolve() if persist_directory else None

        # Create RAG cases directory if it doesn't exist
        if not self.rag_cases_dir.exists():
            logger.info(f"Creating RAG cases directory at: {self.rag_cases_dir}")
            self.rag_cases_dir.mkdir(parents=True, exist_ok=True)

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

        # --- MODIFICATION START: Support multiple collections ---
        # Store collections as a dict: {collection_id: chromadb_collection_object}
        self.collections = {}
        
        # Initialize default collection if not already in APP_STATE
        self._ensure_default_collection()
        
        # Load all active collections from APP_STATE
        self._load_active_collections()
        # --- MODIFICATION END ---

    def _ensure_default_collection(self):
        """Ensures the default collection exists in persistent config and APP_STATE."""
        config_manager = get_config_manager()
        
        # Load collections from persistent config
        collections_list = config_manager.get_rag_collections()
        
        # Check if default collection already exists (ID = 0)
        default_exists = any(c["id"] == 0 for c in collections_list)
        
        if not default_exists:
            # Create default collection with no MCP server assignment
            # User must explicitly assign MCP server before enabling
            default_collection = {
                "id": 0,  # Default collection always has ID 0
                "name": "Default Collection",
                "collection_name": APP_CONFIG.RAG_DEFAULT_COLLECTION_NAME,
                "mcp_server_id": "",  # No MCP server assigned initially
                "enabled": False,  # User must explicitly enable collections
                "created_at": datetime.now(timezone.utc).isoformat(),
                "description": "Default collection for RAG cases"
            }
            collections_list.append(default_collection)
            config_manager.save_rag_collections(collections_list)
            logger.info("Created default RAG collection with ID: 0 (no MCP server assigned)")
        
        # Sync to APP_STATE
        APP_STATE["rag_collections"] = collections_list
    
    def get_collection_metadata(self, collection_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific collection by ID."""
        collections_list = APP_STATE.get("rag_collections", [])
        return next((c for c in collections_list if c["id"] == collection_id), None)
    
    def _load_active_collections(self):
        """
        Loads and initializes enabled collections that match the current MCP server.
        Only collections associated with the active MCP server (by ID) are loaded.
        """
        collections_list = APP_STATE.get("rag_collections", [])
        current_mcp_server_id = APP_CONFIG.CURRENT_MCP_SERVER_ID
        
        logger.info(f"Loading RAG collections for MCP server ID: '{current_mcp_server_id}'")
        
        for coll_meta in collections_list:
            if not coll_meta.get("enabled", False):
                continue
            
            coll_id = coll_meta["id"]
            coll_name = coll_meta["collection_name"]
            coll_mcp_server_id = coll_meta.get("mcp_server_id")
            
            # Enforcement rule: Collection must match current MCP server ID
            if coll_mcp_server_id != current_mcp_server_id:
                logger.debug(f"Skipping collection '{coll_id}': associated with server ID '{coll_mcp_server_id}', current server ID is '{current_mcp_server_id}'")
                continue
            
            try:
                collection = self.client.get_or_create_collection(
                    name=coll_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                self.collections[coll_id] = collection
                logger.info(f"Loaded collection '{coll_id}' (ChromaDB: '{coll_name}', MCP Server ID: '{coll_mcp_server_id}')")
            except Exception as e:
                logger.error(f"Failed to load collection '{coll_id}': {e}", exc_info=True)
        
        if not self.collections:
            logger.warning(f"No active RAG collections loaded for MCP server ID '{current_mcp_server_id}'!")
        else:
            logger.info(f"Loaded {len(self.collections)} collection(s) for MCP server ID '{current_mcp_server_id}'")
        
        # Refresh vector stores for all collections if configured
        if APP_CONFIG.RAG_REFRESH_ON_STARTUP:
            logger.info("RAG_REFRESH_ON_STARTUP is True. Refreshing all vector stores...")
            for coll_id in self.collections:
                self._maintain_vector_store(coll_id)
        else:
            logger.info("RAG_REFRESH_ON_STARTUP is False. Using cached vector stores.")
    
    def add_collection(self, name: str, description: str = "", mcp_server_id: Optional[str] = None) -> Optional[int]:
        """
        Adds a new RAG collection and enables it.
        
        Args:
            name: Display name for the collection
            description: Collection description
            mcp_server_id: Associated MCP server ID (REQUIRED for non-default collections)
            
        Returns:
            The numeric collection ID if successful, None otherwise
        """
        config_manager = get_config_manager()
        
        # Enforcement: mcp_server_id is required for new collections
        if mcp_server_id is None:
            logger.error("Cannot add collection: mcp_server_id is required")
            return None
        
        # Generate unique numeric ID
        collections_list = APP_STATE.get("rag_collections", [])
        existing_ids = [c["id"] for c in collections_list if isinstance(c["id"], int)]
        collection_id = max(existing_ids) + 1 if existing_ids else 1
        
        # Generate unique ChromaDB collection name
        collection_name = f"tda_rag_coll_{collection_id}_{uuid.uuid4().hex[:6]}"
        
        new_collection = {
            "id": collection_id,
            "name": name,
            "collection_name": collection_name,
            "mcp_server_id": mcp_server_id,
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": description
        }
        
        # Add to APP_STATE
        collections_list.append(new_collection)
        APP_STATE["rag_collections"] = collections_list
        
        # Persist to config file
        config_manager.save_rag_collections(collections_list)
        
        # Create ChromaDB collection only if it matches the current MCP server ID
        current_mcp_server_id = APP_CONFIG.CURRENT_MCP_SERVER_ID
        if mcp_server_id == current_mcp_server_id:
            try:
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                self.collections[collection_id] = collection
                logger.info(f"Added and loaded new collection '{collection_id}' (ChromaDB: '{collection_name}', MCP Server ID: '{mcp_server_id}'")
            except Exception as e:
                logger.error(f"Failed to create collection '{collection_id}': {e}", exc_info=True)
                # Remove from APP_STATE if creation failed
                APP_STATE["rag_collections"] = [c for c in collections_list if c["id"] != collection_id]
                config_manager.save_rag_collections(APP_STATE["rag_collections"])
                return None
        else:
            logger.info(f"Added collection '{collection_id}' for MCP server ID '{mcp_server_id}' (not loaded - current server ID is '{current_mcp_server_id}')")
        
        return collection_id
    
    def remove_collection(self, collection_id: int):
        """Removes a RAG collection (except default)."""
        if collection_id == 0:  # Default collection is always ID 0
            logger.warning("Cannot remove default collection")
            return False
        
        config_manager = get_config_manager()
        collections_list = APP_STATE.get("rag_collections", [])
        coll_meta = next((c for c in collections_list if c["id"] == collection_id), None)
        
        if not coll_meta:
            logger.warning(f"Collection '{collection_id}' not found")
            return False
        
        try:
            # Delete from ChromaDB
            self.client.delete_collection(name=coll_meta["collection_name"])
            
            # Remove from runtime
            if collection_id in self.collections:
                del self.collections[collection_id]
            
            # Remove from APP_STATE
            APP_STATE["rag_collections"] = [c for c in collections_list if c["id"] != collection_id]
            
            # Persist to config file
            config_manager.save_rag_collections(APP_STATE["rag_collections"])
            
            logger.info(f"Removed collection '{collection_id}'")
            return True
        except Exception as e:
            logger.error(f"Failed to remove collection '{collection_id}': {e}", exc_info=True)
            return False
    
    def toggle_collection(self, collection_id: int, enabled: bool):
        """
        Enables or disables a RAG collection.
        Collections are only loaded into memory if they match the current MCP server.
        Collections cannot be enabled without an MCP server assignment.
        """
        config_manager = get_config_manager()
        collections_list = APP_STATE.get("rag_collections", [])
        coll_meta = next((c for c in collections_list if c["id"] == collection_id), None)
        
        if not coll_meta:
            logger.warning(f"Collection '{collection_id}' not found")
            return False
        
        # Validate: Cannot enable a collection without an MCP server assignment
        coll_mcp_server = coll_meta.get("mcp_server_id")
        if enabled and not coll_mcp_server:
            logger.warning(f"Cannot enable collection '{collection_id}': no MCP server assigned")
            return False
        
        coll_meta["enabled"] = enabled
        
        # Persist to config file
        config_manager.save_rag_collections(collections_list)
        
        # Check if collection matches current MCP server ID
        current_mcp_server_id = APP_CONFIG.CURRENT_MCP_SERVER_ID
        
        mcp_server_matches = (coll_mcp_server == current_mcp_server_id)
        
        if enabled and collection_id not in self.collections:
            if not mcp_server_matches:
                logger.info(f"Collection '{collection_id}' enabled but not loaded: associated with server ID '{coll_mcp_server}', current server ID is '{current_mcp_server_id}'")
                return True  # Config updated, but not loaded
            
            # Load the collection
            try:
                collection = self.client.get_or_create_collection(
                    name=coll_meta["collection_name"],
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                self.collections[collection_id] = collection
                logger.info(f"Enabled and loaded collection '{collection_id}'")
            except Exception as e:
                logger.error(f"Failed to enable collection '{collection_id}': {e}", exc_info=True)
                return False
        elif not enabled and collection_id in self.collections:
            # Unload the collection
            del self.collections[collection_id]
            logger.info(f"Disabled collection '{collection_id}'")
        
        return True

    def reload_collections_for_mcp_server(self):
        """
        Reloads collections to match the current MCP server.
        Unloads collections from previous MCP server and loads collections for current server.
        Should be called when the MCP server changes.
        """
        current_mcp_server_id = APP_CONFIG.CURRENT_MCP_SERVER_ID
        logger.info(f"Reloading RAG collections for MCP server ID: '{current_mcp_server_id}'")
        
        # Clear currently loaded collections
        self.collections.clear()
        
        # Ensure default collection exists (will create if MCP server is now set)
        self._ensure_default_collection()
        
        # Reload collections using the standard method
        self._load_active_collections()
        
        logger.info(f"Reload complete. {len(self.collections)} collection(s) now loaded for MCP server ID '{current_mcp_server_id}'")

    def refresh_vector_store(self, collection_id: Optional[str] = None):
        """
        Manually triggers the maintenance of the vector store.
        If collection_id is None, refreshes all collections.
        """
        if collection_id:
            logger.info(f"Manual refresh of vector store triggered for collection: {collection_id}")
            self._maintain_vector_store(collection_id)
        else:
            logger.info("Manual refresh of all vector stores triggered.")
            for coll_id in self.collections:
                self._maintain_vector_store(coll_id)

    async def update_case_feedback(self, case_id: str, feedback_score: int) -> bool:
        """
        Update user feedback for a RAG case.
        
        Args:
            case_id: The case ID to update
            feedback_score: -1 (downvote), 0 (neutral), 1 (upvote)
            
        Returns:
            True if successful, False if case not found
        """
        import json
        
        # Load case study from disk
        case_file = self.rag_cases_dir / f"case_{case_id}.json"
        if not case_file.exists():
            logger.warning(f"Case file not found: {case_file}")
            return False
        
        try:
            # Update case study JSON
            with open(case_file, 'r', encoding='utf-8') as f:
                case_study = json.load(f)
            
            old_feedback = case_study["metadata"].get("user_feedback_score", 0)
            case_study["metadata"]["user_feedback_score"] = feedback_score
            
            # Save updated case study
            with open(case_file, 'w', encoding='utf-8') as f:
                json.dump(case_study, f, indent=2)
            
            logger.info(f"Updated case {case_id} feedback: {old_feedback} -> {feedback_score}")
            
            # Update ChromaDB metadata in all collections that contain this case
            for collection_id, collection in self.collections.items():
                try:
                    # Check if this case exists in this collection
                    existing = collection.get(ids=[case_id], include=["metadatas"])
                    
                    if existing and existing["ids"]:
                        # Update the metadata
                        metadata = existing["metadatas"][0]
                        metadata["user_feedback_score"] = feedback_score
                        
                        # If downvoted, demote from champion status
                        if feedback_score < 0:
                            metadata["is_most_efficient"] = False
                            logger.info(f"Case {case_id} downvoted - demoted from champion in collection {collection_id}")
                            
                            # Trigger re-evaluation to find new champion
                            await self._reevaluate_champion_for_query(
                                collection_id, 
                                metadata["user_query"]
                            )
                        
                        # Update full_case_data with new feedback
                        metadata["full_case_data"] = json.dumps(case_study)
                        
                        collection.update(
                            ids=[case_id],
                            metadatas=[metadata]
                        )
                        logger.debug(f"Updated ChromaDB metadata for case {case_id} in collection {collection_id}")
                        
                except Exception as e:
                    logger.error(f"Error updating case {case_id} in collection {collection_id}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating case feedback: {e}", exc_info=True)
            return False

    async def _reevaluate_champion_for_query(self, collection_id: int, user_query: str):
        """
        Re-evaluates which case should be champion for a given query.
        Called when the current champion is downvoted.
        """
        if collection_id not in self.collections:
            return
        
        collection = self.collections[collection_id]
        
        try:
            # Get all cases for this query (excluding downvoted)
            all_cases = collection.get(
                where={"$and": [
                    {"user_query": {"$eq": user_query}},
                    {"user_feedback_score": {"$gte": 0}}  # Exclude downvoted
                ]},
                include=["metadatas"]
            )
            
            if not all_cases or not all_cases["ids"]:
                logger.info(f"No eligible cases remain for query '{user_query}' in collection {collection_id}")
                return
            
            # Find the best case using our priority logic
            best_case_id = None
            best_feedback = -999
            best_tokens = float('inf')
            
            for i, case_id in enumerate(all_cases["ids"]):
                meta = all_cases["metadatas"][i]
                feedback = meta.get("user_feedback_score", 0)
                tokens = meta.get("output_tokens", float('inf'))
                
                # Priority: feedback first, then tokens
                if feedback > best_feedback or (feedback == best_feedback and tokens < best_tokens):
                    best_case_id = case_id
                    best_feedback = feedback
                    best_tokens = tokens
            
            if best_case_id:
                # Demote all others, promote the best
                for i, case_id in enumerate(all_cases["ids"]):
                    meta = all_cases["metadatas"][i]
                    meta["is_most_efficient"] = (case_id == best_case_id)
                    collection.update(ids=[case_id], metadatas=[meta])
                
                logger.info(f"New champion for query '{user_query[:50]}...' in collection {collection_id}: {best_case_id} (feedback={best_feedback}, tokens={best_tokens})")
                
        except Exception as e:
            logger.error(f"Error re-evaluating champion: {e}", exc_info=True)

    def _maintain_vector_store(self, collection_id: str):
        """
        Maintains the ChromaDB vector store for a specific collection by synchronizing it with the
        JSON case files on disk. It adds new cases, removes deleted ones,
        and updates existing ones if their metadata has changed.
        """
        if collection_id not in self.collections:
            logger.warning(f"Cannot maintain vector store: collection '{collection_id}' not loaded")
            return
        
        collection = self.collections[collection_id]
        logger.info(f"Starting vector store maintenance for collection '{collection_id}' at {self.rag_cases_dir}...")
        
        # 1. Get current state from disk and DB
        disk_case_ids = {p.stem for p in self.rag_cases_dir.glob("case_*.json")}
        db_results = collection.get(include=["metadatas"])
        db_case_ids = set(db_results["ids"])
        db_metadatas = {db_results["ids"][i]: meta for i, meta in enumerate(db_results["metadatas"])}

        # 2. Identify cases to delete from DB
        ids_to_delete = list(db_case_ids - disk_case_ids)
        if ids_to_delete:
            logger.info(f"Found {len(ids_to_delete)} stale cases to remove from collection '{collection_id}'.")
            collection.delete(ids=ids_to_delete)

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
                    collection.add(documents=[document_content], metadatas=[metadata], ids=[case_id_stem])
                    added_count += 1
                    logger.debug(f"Added new case {case_id_stem} to collection '{collection_id}'.")
                else:
                    # Check if update is needed by comparing the full content
                    existing_meta = db_metadatas.get(case_id_stem, {})
                    try:
                        existing_case_data = json.loads(existing_meta.get("full_case_data", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        existing_case_data = {}

                    # If the file on disk is different from what's in the DB, update.
                    if case_data != existing_case_data:
                        collection.update(
                            ids=[case_id_stem],
                            metadatas=[metadata],
                            documents=[document_content] # Ensure embedding is updated too
                        )
                        updated_count += 1
                        logger.info(f"Updated case {case_id_stem} in collection '{collection_id}' because content has changed.")

            except Exception as e:
                logger.error(f"Failed to process RAG case file {case_file.name}: {e}", exc_info=True)
        
        logger.info(f"Vector store maintenance complete for '{collection_id}'. Added: {added_count}, Updated: {updated_count}, Removed: {len(ids_to_delete)}.")

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

    def retrieve_examples(self, query: str, k: int = 1, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most relevant and efficient RAG cases based on the query.
        Queries all active collections and aggregates results by similarity score.
        """
        logger.info(f"Retrieving top {k} RAG examples for query: '{query}' (min_score: {min_score})")
        
        if not self.collections:
            logger.warning("No active collections to retrieve examples from")
            return []
        
        # --- MODIFICATION START: Query all active collections ---
        all_candidate_cases = []
        
        for collection_id, collection in self.collections.items():
            try:
                query_results = collection.query(
                    query_texts=[query],
                    n_results=k * 10,  # Retrieve more candidates to filter
                    where={"$and": [
                        {"strategy_type": {"$eq": "successful"}},
                        {"is_most_efficient": {"$eq": True}},
                        {"user_feedback_score": {"$gte": 0}}  # Exclude downvoted cases
                    ]},  # Only retrieve successful, most efficient, non-downvoted cases
                    include=["metadatas", "distances"]
                )
                
                if query_results and query_results["ids"] and query_results["ids"][0]:
                    for i in range(len(query_results["ids"][0])):
                        case_id = query_results["ids"][0][i]
                        metadata = query_results["metadatas"][0][i]
                        distance = query_results["distances"][0][i]
                        
                        similarity_score = 1 - distance 

                        if similarity_score < min_score:
                            logger.debug(f"Skipping case {case_id} from collection '{collection_id}' due to low similarity score: {similarity_score:.2f}")
                            continue
                        
                        full_case_data = json.loads(metadata["full_case_data"])
                        
                        all_candidate_cases.append({
                            "case_id": case_id,
                            "collection_id": collection_id,  # Track which collection this came from
                            "user_query": metadata["user_query"],
                            "strategy_type": metadata.get("strategy_type", "unknown"),
                            "full_case_data": full_case_data,
                            "similarity_score": similarity_score,
                            "is_most_efficient": metadata.get("is_most_efficient"),
                            "had_plan_improvements": full_case_data.get("metadata", {}).get("had_plan_improvements", False),
                            "had_tactical_improvements": full_case_data.get("metadata", {}).get("had_tactical_improvements", False)
                        })
            except Exception as e:
                logger.error(f"Error querying collection '{collection_id}': {e}", exc_info=True)
        
        if not all_candidate_cases:
            logger.info("No candidate cases found across all collections")
            return []
        # --- MODIFICATION END ---
        
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

        # Enrich with collection metadata
        for case in final_candidates[:k]:
            coll_id = case.get("collection_id")
            if coll_id:
                coll_meta = self.get_collection_metadata(coll_id)
                if coll_meta:
                    case["collection_name"] = coll_meta.get("name")
                    case["collection_mcp_server_id"] = coll_meta.get("mcp_server_id")

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
    
    def _extract_case_from_turn_summary(self, turn_summary: dict, collection_id: Optional[int] = None) -> dict | None:
        """
        Core logic to transform a raw turn_summary log into a clean Case Study.
        Adapted from rag_miner.py's _extract_case_study.
        
        Args:
            turn_summary: The turn data to process
            collection_id: The collection this case will belong to (defaults to 0)
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
            
            # --- MODIFICATION START: Stricter success checking ---
            original_plan = turn.get("original_plan")
            if not original_plan or not isinstance(original_plan, list):
                logger.debug(f"  -> Skipping turn {turn.get('turn')}: 'original_plan' is missing or not a list.")
                return None

            required_phases = {p.get("phase") for p in original_plan if isinstance(p, dict) and p.get("phase") is not None}
            if not required_phases:
                logger.debug(f"  -> Skipping turn {turn.get('turn')}: 'original_plan' has no valid phases.")
                return None
            
            completed_phases = set()
            has_critical_error = False
            first_error_action = None
            successful_actions_map = {}
            had_plan_improvements = False
            had_tactical_improvements = False
            # --- MODIFICATION END ---

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
                    # --- MODIFICATION START: Check for unrecoverable errors ---
                    if (tool_name == "TDA_SystemLog" and 
                        isinstance(action_args, dict) and 
                        action_args.get("message") == "Unrecoverable Error"):
                        has_critical_error = True
                    # --- MODIFICATION END ---
                    if isinstance(action_meta, dict) and action_meta.get("type") == "workaround": had_tactical_improvements = True
                    if tool_name == "TDA_SystemLog" and isinstance(action_args, dict) and action_args.get("message") == "System Correction":
                        if "Planner" in action_args.get("details", {}).get("summary", ""): had_plan_improvements = True
                
                # --- MODIFICATION START: Stricter error tracking ---
                if result_is_dict and result.get("status") == "error":
                    has_critical_error = True
                    if not first_error_action:
                        first_error_action = action
                # --- MODIFICATION END ---
                
                if result_is_dict and result.get("status") == "success" and action_is_dict:
                    tool_name = action.get("tool_name")
                    if tool_name and tool_name != "TDA_SystemLog":
                        # --- MODIFICATION START: Use phase_number (can be None) ---
                        phase_num = action.get("metadata", {}).get("phase_number")
                        if phase_num is not None:
                            completed_phases.add(phase_num)
                        # --- MODIFICATION END ---
                            
                            original_phase = None
                            # --- MODIFICATION START: Use original_plan variable ---
                            if original_plan:
                                for p in original_plan:
                            # --- MODIFICATION END ---
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
            
            # --- MODIFICATION START: Apply new success criteria ---
            is_success = (not has_critical_error) and (required_phases == completed_phases)
            if not is_success:
                logger.debug(f"  -> Marking turn {turn.get('turn')} as NOT successful. "
                             f"HasError: {has_critical_error}, "
                             f"Required: {required_phases}, "
                             f"Completed: {completed_phases}")
            # --- MODIFICATION END ---

            case_study = {
                "case_id": case_id,
                "metadata": {
                    "session_id": session_id, "turn_id": turn.get("turn"), "is_success": is_success,
                    # --- MODIFICATION START: Add task_id and collection_id ---
                    "task_id": turn.get("task_id"),
                    "collection_id": collection_id if collection_id is not None else 0,
                    # --- MODIFICATION END ---
                    "had_plan_improvements": had_plan_improvements, "had_tactical_improvements": had_tactical_improvements,
                    "timestamp": turn.get("timestamp"),
                    "user_feedback_score": 0,  # Default: no feedback yet (-1=downvote, 0=neutral, 1=upvote)
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

            # --- MODIFICATION START: Use is_success flag to build strategy ---
            if is_success:
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
                return case_study  # Return successful strategy
            elif first_error_action:
                case_study["failed_strategy"] = {"original_plan": turn.get("original_plan"), "error_summary": turn.get("final_summary", ""), "failed_action": first_error_action}
                return case_study  # Return failed strategy for analysis
            else:
                # Conversational response - skip RAG processing
                logger.debug(f"  -> Skipping turn {turn.get('turn')}: Conversational response (no strategic value for RAG).")
                return None
            # --- MODIFICATION END ---
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
            # --- MODIFICATION START: Add task_id and collection_id ---
            "task_id": case_study["metadata"].get("task_id"),
            "collection_id": case_study["metadata"].get("collection_id", 0),
            # --- MODIFICATION END ---
            "is_most_efficient": case_study["metadata"].get("is_most_efficient", False),
            "had_plan_improvements": case_study["metadata"].get("had_plan_improvements", False),
            "had_tactical_improvements": case_study["metadata"].get("had_tactical_improvements", False),
            "output_tokens": case_study["metadata"].get("llm_config", {}).get("output_tokens", 0),
            # Store the full case data as a JSON string
            "full_case_data": json.dumps(case_study)
        }
        return metadata

    async def process_turn_for_rag(self, turn_summary: dict, collection_id: Optional[int] = None):
        """
        The main "consumer" method. It processes a single turn summary,
        determines its efficiency, and transactionally updates the vector store.
        If collection_id is not specified, uses the default collection (ID 0).
        """
        try:
            # 1. Determine which collection to use first
            if collection_id is None:
                collection_id = 0  # Default collection ID
            
            # 2. Extract & Filter (pass collection_id so it's stored in case metadata)
            case_study = self._extract_case_from_turn_summary(turn_summary, collection_id)
            
            if not case_study or "successful_strategy" not in case_study:
                logger.debug("Skipping RAG processing: Turn was not a successful strategy.")
                return

            # 3. Verify collection is active

            if collection_id not in self.collections:
                logger.warning(f"Collection '{collection_id}' not found or not active. Skipping RAG processing.")
                return
            
            collection = self.collections[collection_id]

            # 3. Get new case data
            new_case_id = case_study["case_id"]
            new_query = case_study["intent"]["user_query"]
            new_tokens = case_study["metadata"].get("llm_config", {}).get("output_tokens", 0)
            new_document = new_query # The document we embed is the user query
            
            logger.info(f"Processing RAG case {new_case_id} for collection '{collection_id}', query: '{new_query[:50]}...' (Tokens: {new_tokens})")

            # 4. Query ChromaDB for existing "most efficient" in this collection
            existing_cases = collection.get(
                where={"$and": [
                    {"user_query": {"$eq": new_query}},
                    {"is_most_efficient": {"$eq": True}}
                ]},
                include=["metadatas"]
            )

            old_best_case_id = None
            old_best_case_tokens = float('inf')
            old_best_case_feedback = 0
            new_feedback = case_study["metadata"].get("user_feedback_score", 0)

            if existing_cases and existing_cases["ids"]:
                old_best_case_id = existing_cases["ids"][0]
                old_best_case_tokens = existing_cases["metadatas"][0].get("output_tokens", float('inf'))
                old_best_case_feedback = existing_cases["metadatas"][0].get("user_feedback_score", 0)

            # 5. Compare & Decide (Feedback score takes priority over token efficiency)
            id_to_demote = None
            
            # Downvoted cases never become champion
            if new_feedback < 0:
                logger.info(f"New case {new_case_id} is downvoted (feedback={new_feedback}). Not eligible for champion.")
                case_study["metadata"]["is_most_efficient"] = False
            # Old champion is downvoted, new case wins by default (if not also downvoted)
            elif old_best_case_feedback < 0:
                logger.info(f"Old case {old_best_case_id} is downvoted. New case {new_case_id} becomes champion.")
                case_study["metadata"]["is_most_efficient"] = True
                id_to_demote = old_best_case_id
            # Compare feedback scores first
            elif new_feedback != old_best_case_feedback:
                if new_feedback > old_best_case_feedback:
                    logger.info(f"New case {new_case_id} has better feedback ({new_feedback}) than old case {old_best_case_id} ({old_best_case_feedback}). New case wins.")
                    case_study["metadata"]["is_most_efficient"] = True
                    id_to_demote = old_best_case_id
                else:
                    logger.info(f"Old case {old_best_case_id} has better feedback ({old_best_case_feedback}) than new case {new_case_id} ({new_feedback}). Old case wins.")
                    case_study["metadata"]["is_most_efficient"] = False
            # Same feedback level - use token efficiency as tiebreaker
            else:
                if new_tokens < old_best_case_tokens:
                    logger.info(f"New case {new_case_id} is MORE efficient ({new_tokens} tokens) than old case {old_best_case_id} ({old_best_case_tokens} tokens). Same feedback level ({new_feedback}).")
                    case_study["metadata"]["is_most_efficient"] = True
                    id_to_demote = old_best_case_id
                else:
                    logger.info(f"New case {new_case_id} ({new_tokens} tokens) is NOT more efficient than old case {old_best_case_id} ({old_best_case_tokens} tokens). Same feedback level ({new_feedback}).")
                    case_study["metadata"]["is_most_efficient"] = False
            
            new_metadata = self._prepare_chroma_metadata(case_study)

            # 6. Transact with ChromaDB
            # Step 6a: Upsert the new case
            collection.upsert(
                ids=[new_case_id],
                documents=[new_document],
                metadatas=[new_metadata]
            )
            logger.debug(f"Upserted new case {new_case_id} to collection '{collection_id}' with is_most_efficient={new_metadata['is_most_efficient']}.")

            # Step 6b: Demote the old case if necessary
            if id_to_demote:
                logger.info(f"Demoting old best case: {id_to_demote}")
                # We must fetch the *full metadata* for the old case to update it
                old_case_meta_result = collection.get(ids=[id_to_demote], include=["metadatas"])
                if old_case_meta_result["metadatas"]:
                    meta_to_update = old_case_meta_result["metadatas"][0]
                    meta_to_update["is_most_efficient"] = False
                    collection.update(
                        ids=[id_to_demote],
                        metadatas=[meta_to_update]
                    )
                    logger.info(f"Successfully demoted old case {id_to_demote}.")
                else:
                    logger.warning(f"Could not find old case {id_to_demote} to demote it.")
            
            # 7. Save the case study JSON to disk
            # Ensure the directory exists before writing
            self.rag_cases_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.rag_cases_dir / f"case_{new_case_id}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(case_study, f, indent=2)
            logger.debug(f"Saved case study JSON to disk: {output_path.name}")
            
            # Return the case_id so it can be stored in the session
            return new_case_id

        except Exception as e:
            logger.error(f"Error during real-time RAG processing: {e}", exc_info=True)
            return None


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