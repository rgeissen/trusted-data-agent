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
        """Main entry point to scan and process all sessions."""
        logger.info(f"Starting mining process.")
        logger.info(f"Input (Sessions): {self.sessions_dir}")
        logger.info(f"Output (Cases):   {self.output_dir}")
        
        session_files = list(self.sessions_dir.rglob("*.json"))
        logger.info(f"Found {len(session_files)} potential session files.")

        total_turns = 0
        processed_turns = 0
        skipped_turns = 0

        for session_file in session_files:
            try:
                logger.info(f"Processing session file: {session_file.name}")
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                if "id" not in session_data or "last_turn_data" not in session_data:
                    logger.warning(f"Skipping malformed session file: {session_file.name}")
                    continue

                session_id = session_data["id"]
                workflow_history = session_data.get("last_turn_data", {}).get("workflow_history", [])

                for turn in workflow_history:
                    total_turns += 1
                    turn_id = turn.get("turn")
                    logger.info(f"Analyzing turn {turn_id} in session {session_id}...")

                    if not turn.get("isValid", True):
                        logger.warning(f"  -> Skipping turn {turn_id}: Marked as invalid.")
                        continue

                    if turn_id is None:
                         logger.warning(f"  -> Skipping turn: Missing 'turn' ID.")
                         continue

                    case_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{session_id}_{turn_id}"))
                    output_filename = f"case_{case_id}.json"
                    output_path = self.output_dir / output_filename

                    if output_path.exists() and not self.force_reprocess:
                        skipped_turns += 1
                        logger.info(f"  -> Skipping turn {turn_id}: Case study {output_filename} already exists.")
                        continue

                    case_study = self._extract_case_study(session_data, turn, case_id)
                    if case_study:
                        self._save_case_study(case_study, output_path)
                        processed_turns += 1
                        logger.info(f"  -> SUCCESS: Generated case study {output_filename}")
                    else:
                        # This case should ideally not be reached with the new logic, but is kept for safety.
                        logger.error(f"  -> CRITICAL: Failed to extract or categorize turn {turn_id}. Bypassing.")

            except Exception as e:
                logger.error(f"Failed to process session file {session_file.name}: {e}", exc_info=True) # Changed to True for better debugging

        logger.info(f"Mining complete. Total turns scanned: {total_turns}. New cases processed: {processed_turns}. Skipped (already existed): {skipped_turns}.")

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
