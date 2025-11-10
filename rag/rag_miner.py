import os
import json
import glob
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime, timezone
import uuid

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
        Main entry point to scan and process all sessions. It now deduplicates
        successful cases based on the user query, keeping only the one with the
        lowest total token count.
        """
        logger.info("Starting mining process.")
        logger.info(f"Input (Sessions): {self.sessions_dir}")
        logger.info(f"Output (Cases):   {self.output_dir}")

        session_files = list(self.sessions_dir.rglob("*.json"))
        logger.info(f"Found {len(session_files)} potential session files.")

        successful_cases = {}  # To hold the best successful case for each query
        total_turns = 0
        processed_turns = 0
        skipped_turns = 0
        other_cases_processed = 0

        # --- First Pass: Collect all cases and identify the best successful ones ---
        logger.info("--- Pass 1: Collecting and deduplicating successful cases ---")
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

                    case_study = self._extract_case_study(session_data, turn, "temp_id") # Use a temp ID for now
                    if not case_study:
                        continue

                    # Handle successful cases for deduplication
                    if "successful_strategy" in case_study:
                        query = case_study["intent"]["user_query"]
                        llm_config = case_study["metadata"]["llm_config"]
                        total_tokens = llm_config.get("input_tokens", 0) + llm_config.get("output_tokens", 0)

                        # If we haven't seen this query, or if the new one is better, store it
                        if query not in successful_cases or total_tokens < successful_cases[query]["tokens"]:
                            successful_cases[query] = {"case": case_study, "tokens": total_tokens}
                            logger.debug(f"Found new best successful case for query '{query[:50]}...' with {total_tokens} tokens.")

            except Exception as e:
                logger.error(f"Failed to process session file {session_file.name} during collection: {e}", exc_info=True)

        # --- Second Pass: Process and save the final set of cases ---
        logger.info("--- Pass 2: Saving final case studies ---")
        
        # Clear the output directory if force_reprocess is on
        if self.force_reprocess:
            logger.info("Force reprocess is enabled. Clearing output directory...")
            for old_case in self.output_dir.glob("case_*.json"):
                old_case.unlink()

        # Save the best successful cases
        for query, data in successful_cases.items():
            case_study = data["case"]
            # Generate a stable UUID based on the query itself for the final case ID
            case_id = str(uuid.uuid5(uuid.NAMESPACE_OID, query))
            case_study["case_id"] = case_id
            output_filename = f"case_{case_id}.json"
            output_path = self.output_dir / output_filename
            
            self._save_case_study(case_study, output_path)
            processed_turns += 1
            logger.info(f"  -> SUCCESS (Best): Saved case {output_filename} for query '{query[:50]}...'")

        # Save all other case types (failed, conversational) from a fresh loop
        for session_file in session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                if "id" not in session_data or "last_turn_data" not in session_data: continue
                session_id = session_data["id"]
                workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])

                for turn in workflow_history:
                    if not turn.get("isValid", True) or turn.get("turn") is None: continue
                    
                    case_study = self._extract_case_study(session_data, turn, "temp_id")
                    if not case_study or "successful_strategy" in case_study:
                        continue # Skip successful cases as they are already handled

                    # Generate a stable ID for these other cases
                    turn_id = turn.get("turn")
                    case_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{session_id}_{turn_id}"))
                    case_study["case_id"] = case_id
                    output_filename = f"case_{case_id}.json"
                    output_path = self.output_dir / output_filename

                    if output_path.exists() and not self.force_reprocess:
                        skipped_turns += 1
                        continue
                    
                    self._save_case_study(case_study, output_path)
                    other_cases_processed += 1
                    logger.info(f"  -> SUCCESS (Other): Saved case {output_filename}")

            except Exception as e:
                logger.error(f"Failed to process session file {session_file.name} during saving: {e}", exc_info=True)

        logger.info(f"Mining complete. Total turns scanned: {total_turns}. Best successful cases processed: {processed_turns}. Other cases processed: {other_cases_processed}. Skipped (already existed): {skipped_turns}.")

    def _save_case_study(self, case_data: dict, output_path: Path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2)

    def _extract_case_study(self, session: dict, turn: dict, case_id: str) -> dict | None:
        """
        Core logic to transform a raw turn log into a clean Case Study,
        categorizing it as Successful, Failed, or Conversational.
        This function is designed to be highly robust against malformed trace data.
        """
        try:
            trace = turn.get("execution_trace", [])
            
            # --- 1. First Pass: Calculate metadata flags and find key events ---
            is_success = True
            had_plan_improvements = False
            had_tactical_improvements = False
            successful_actions_map = {}
            first_error_action = None

            for entry in trace:
                if not isinstance(entry, dict):
                    logger.warning(f"  -> Bypassing malformed non-dict entry in trace: {entry}")
                    continue

                action = entry.get("action", {})
                result = entry.get("result", {})
                
                # Defensive check for action and result being dicts
                action_is_dict = isinstance(action, dict)
                result_is_dict = isinstance(result, dict)

                # --- Flag Calculation ---
                if action_is_dict:
                    action_args = action.get("arguments", {})
                    action_meta = action.get("metadata", {})
                    tool_name = action.get("tool_name", "")

                    if isinstance(action_args, dict) and action_args.get("message") == "Unrecoverable Error":
                        is_success = False

                    if isinstance(action_meta, dict) and action_meta.get("type") == "workaround":
                        had_tactical_improvements = True

                    if tool_name == "TDA_SystemLog" and isinstance(action_args, dict) and action_args.get("message") == "System Correction":
                        details_summary = action_args.get("details", {}).get("summary", "")
                        if "Planner" in details_summary:
                            had_plan_improvements = True
                
                # --- Event Finding ---
                if result_is_dict and result.get("status") == "error" and not first_error_action:
                    first_error_action = action
                
                if result_is_dict and result.get("status") == "success" and action_is_dict:
                    tool_name = action.get("tool_name")
                    if tool_name and tool_name != "TDA_SystemLog":
                        phase_num = action.get("metadata", {}).get("phase_number", 0)
                        successful_actions_map[phase_num] = {
                            "phase": phase_num,
                            "tool": tool_name,
                            "key_arguments": action.get("arguments", {})
                        }
            
            # --- 2. Build the base case study object ---
            case_study = {
                "case_id": case_id,
                "metadata": {
                    "session_id": session.get("id"),
                    "turn_id": turn.get("turn"),
                    "is_success": is_success,
                    "had_plan_improvements": had_plan_improvements,
                    "had_tactical_improvements": had_tactical_improvements,
                    "timestamp": turn.get("timestamp", session.get("last_updated")),
                    "llm_config": {
                        "provider": turn.get("provider", session.get("provider")),
                        "model": turn.get("model", session.get("model")),
                        "input_tokens": turn.get("turn_input_tokens", 0),
                        "output_tokens": turn.get("turn_output_tokens", 0)
                    },
                },
                "intent": {"user_query": turn.get("user_query")}
            }

            if not case_study["intent"]["user_query"]:
                logger.warning(f"  -> Skipping turn {turn.get('turn')}: 'user_query' is missing or empty.")
                return None

            # --- 3. Categorize and finalize the case study body ---
            if successful_actions_map:
                # SUCCESSFUL STRATEGY
                case_study["successful_strategy"] = {"phases": []}
                sorted_phases = sorted(successful_actions_map.keys())
                for phase_num in sorted_phases:
                    action_info = successful_actions_map[phase_num]
                    original_goal = "Execute tool."
                    if turn.get("original_plan"):
                        for p in turn["original_plan"]:
                            if isinstance(p, dict) and p.get("phase") == phase_num:
                                original_goal = p.get("goal")
                                break
                    case_study["successful_strategy"]["phases"].append({
                        "phase": phase_num, "goal": original_goal, "tool": action_info['tool'],
                        "key_arguments": action_info['key_arguments']
                    })
                
                # Add metrics for successful strategies
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
                
                case_study["metadata"]["strategy_metrics"] = {
                    "phase_count": len(turn.get("original_plan", [])),
                    "steps_per_phase": steps_per_phase,
                    "total_steps": total_steps
                }
            elif not is_success:
                # FAILED STRATEGY
                case_study["failed_strategy"] = {
                    "original_plan": turn.get("original_plan"),
                    "error_summary": turn.get("final_summary", ""),
                    "failed_action": first_error_action
                }
            else:
                # CONVERSATIONAL RESPONSE
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
