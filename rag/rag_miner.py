import os
import json
import glob
import logging
import argparse
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone
import uuid
from collections import defaultdict

# Configure a dedicated logger for the miner
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("rag_miner")

class SessionMiner:
    def __init__(self, sessions_dir: str | Path, output_dir: str | Path, force_reprocess: bool = False):
        self.sessions_dir = Path(sessions_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.force_reprocess = force_reprocess
        
        if not self.sessions_dir.exists():
             logger.error(f"Sessions directory not found at: {self.sessions_dir}")
             
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        """
        Main entry point to scan and process all sessions. It holds all data in
        memory until processing is complete, then writes the final, correct
        data to disk to ensure atomicity.
        """
        logger.info("Starting mining process.")
        logger.info(f"Input (Sessions): {self.sessions_dir}")
        logger.info(f"Output (Cases):   {self.output_dir}")

        if self.force_reprocess:
            logger.info("Force reprocess is enabled. Clearing output directory...")
            for old_case in self.output_dir.glob("case_*.json"):
                old_case.unlink()
            
            project_root = self.output_dir.parent.parent
            chroma_cache_dir = project_root / ".chromadb_rag_cache"
            if chroma_cache_dir.exists():
                logger.info(f"Flushing ChromaDB cache at {chroma_cache_dir}...")
                shutil.rmtree(chroma_cache_dir)

        session_files = list(self.sessions_dir.rglob("*.json"))
        logger.info(f"Found {len(session_files)} potential session files.")

        all_cases = []
        successful_cases_by_query = defaultdict(list)
        total_turns = 0

        # --- Pass 1: Collect all cases from all sessions into memory ---
        logger.info("--- Pass 1: Collecting all cases into memory ---")
        for session_file in session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                if "id" not in session_data or "last_turn_data" not in session_data:
                    continue

                session_id = session_data["id"]
                workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])

                for turn in workflow_history:
                    total_turns += 1
                    if not turn.get("isValid", True) or turn.get("turn") is None:
                        continue
                    
                    turn_id = turn.get("turn")
                    case_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{session_id}_{turn_id}"))
                    
                    case_study = self._extract_case_study(session_data, turn, case_id)
                    if not case_study:
                        continue
                    
                    all_cases.append(case_study)
                    if "successful_strategy" in case_study:
                        query = case_study["intent"]["user_query"]
                        successful_cases_by_query[query].append(case_study)

            except Exception as e:
                logger.error(f"Failed to process session file {session_file.name} during collection: {e}", exc_info=True)
        
        logger.info(f"Collection complete. Found {len(all_cases)} total cases to process.")

        # --- Pass 2: Mark the most efficient successful cases in memory ---
        logger.info("--- Pass 2: Marking most efficient successful cases ---")
        for query, cases in successful_cases_by_query.items():
            if not cases:
                continue

            for c in cases:
                c["metadata"]["is_most_efficient"] = False

            best_case = min(cases, key=lambda c: c["metadata"]["llm_config"]["output_tokens"])
            best_case["metadata"]["is_most_efficient"] = True
            logger.debug(f"Marked case {best_case['case_id']} as most efficient for query '{query[:50]}...'.")

        # --- Pass 3: Save all cases to disk ---
        logger.info("--- Pass 3: Saving all cases to disk ---")
        saved_count = 0
        for case_study in all_cases:
            case_id = case_study["case_id"]
            output_path = self.output_dir / f"case_{case_id}.json"
            self._save_case_study(case_study, output_path)
            saved_count += 1
        
        logger.info(f"Mining complete. Total turns scanned: {total_turns}. Cases saved to disk: {saved_count}.")

    def _save_case_study(self, case_data: dict, output_path: Path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2)

    def _extract_case_study(self, session: dict, turn: dict, case_id: str) -> dict | None:
        """
        Core logic to transform a raw turn log into a clean Case Study.
        """
        try:
            trace = turn.get("execution_trace", [])

            # Check if any action in the trace is TDA_ContextReport
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
                        
                        # --- MODIFICATION START: Build a compliant phase object ---
                        # Find the corresponding phase from the original plan to get all metadata
                        original_phase = None
                        if turn.get("original_plan"):
                            for p in turn["original_plan"]:
                                if isinstance(p, dict) and p.get("phase") == phase_num:
                                    original_phase = p
                                    break
                        
                        if original_phase:
                            # Build a new, compliant phase structure
                            compliant_phase = {
                                "phase": phase_num,
                                "goal": original_phase.get("goal", "Execute tool."),
                                # Fix #2 and #3: Use 'relevant_tools' as a list and copy loop structure
                                "relevant_tools": [tool_name]
                            }
                            if "type" in original_phase:
                                compliant_phase["type"] = original_phase["type"]
                            if "loop_over" in original_phase:
                                compliant_phase["loop_over"] = original_phase["loop_over"]
                            
                            # Fix #1: Use 'arguments' key
                            compliant_phase["arguments"] = action.get("arguments", {})
                            
                            successful_actions_map[phase_num] = compliant_phase
                        else:
                            # Fallback for safety (should not happen if plan exists)
                            successful_actions_map[phase_num] = {
                                "phase": phase_num, 
                                "goal": "Goal not found in original plan.",
                                "relevant_tools": [tool_name], 
                                "arguments": action.get("arguments", {})
                            }
                        # --- MODIFICATION END ---
            
            case_study = {
                "case_id": case_id,
                "metadata": {
                    "session_id": session.get("id"), "turn_id": turn.get("turn"), "is_success": is_success,
                    "had_plan_improvements": had_plan_improvements, "had_tactical_improvements": had_tactical_improvements,
                    "timestamp": turn.get("timestamp", session.get("last_updated")),
                    "llm_config": {
                        "provider": turn.get("provider", session.get("provider")), "model": turn.get("model", session.get("model")),
                        "input_tokens": turn.get("turn_input_tokens", 0), "output_tokens": turn.get("turn_output_tokens", 0)
                    },
                },
                "intent": {"user_query": turn.get("user_query")}
            }

            if not case_study["intent"]["user_query"]:
                logger.warning(f"  -> Skipping turn {turn.get('turn')}: 'user_query' is missing or empty.")
                return None

            if successful_actions_map:
                case_study["metadata"]["is_most_efficient"] = False # Default, will be updated in marking pass
                case_study["successful_strategy"] = {"phases": []}
                for phase_num in sorted(successful_actions_map.keys()):
                    action_info = successful_actions_map[phase_num]
                    # --- MODIFICATION START: Append the new compliant phase object directly ---
                    case_study["successful_strategy"]["phases"].append(action_info)
                    # --- MODIFICATION END ---
                
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
            logger.error(f"  -> CRITICAL: An unexpected error occurred during extraction for turn {turn.get('turn')}: {e}", exc_info=True)
            return None

if __name__ == '__main__':
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent
    DEFAULT_SESSIONS_DIR = PROJECT_ROOT / "tda_sessions"
    DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "tda_rag_cases"

    parser = argparse.ArgumentParser(description="Extract RAG case studies from TDA session logs.")
    parser.add_argument("--sessions_dir", type=str, default=str(DEFAULT_SESSIONS_DIR), 
                        help=f"Path to input sessions directory (default: {DEFAULT_SESSIONS_DIR})")
    parser.add_argument("--output_dir", type=str, default=str(DEFAULT_OUTPUT_DIR), 
                        help=f"Path to output case studies directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--force", action="store_true", help="Force reprocessing of all turns.")

    args = parser.parse_args()

    miner = SessionMiner(args.sessions_dir, args.output_dir, force_reprocess=args.force)
    miner.run()