# src/trusted_data_agent/rag/logger.py
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Define the sets of problem and solution event types
PROBLEM_EVENTS = {"InefficientPlanDetected", "ExecutionError", "InvalidPlanGenerated", "UnhandledError", "SelfCorrectionFailed"}
SOLUTION_EVENTS = {"PlanOptimization", "SelfHealing", "SelfCorrectionAttempt", "SelfCorrectionLLMCall", "SelfCorrectionProposedAction", "SelfCorrectionFailedProposal", "SystemWorkaround"}

# Determine the project root relative to this file (up 4 levels from src/trusted_data_agent/rag/logger.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Define the log directory relative to the project root, allowing for environment variable override for flexibility
DEFAULT_LOG_DIR = _PROJECT_ROOT / "rag" / "rag_input"
LOG_DIRECTORY = os.environ.get("TDA_RAG_LOG_DIR", str(DEFAULT_LOG_DIR))

PROBLEMS_FILE = os.path.join(LOG_DIRECTORY, "problems.jsonl")
SOLUTIONS_FILE = os.path.join(LOG_DIRECTORY, "solutions.jsonl")

def log_rag_event(session_id: str, correlation_id: str, event_type: str, event_source: str, details: dict, task_id: str = None):
    """
    Logs a structured event for RAG to the appropriate file (problems.jsonl or solutions.jsonl).

    Args:
        session_id: The ID for the entire user session.
        correlation_id: The ID linking a problem to its solution.
        event_type: The name of the event.
        event_source: The module/component that generated the event.
        details: A dictionary containing event-specific information.
        task_id: Optional. The ID of the overall task or user request.
    """
    log_entry = {
        "log_id": str(uuid.uuid4()),
        "session_id": session_id,
    }
    if task_id:
        log_entry["task_id"] = task_id
    log_entry.update({
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "event_source": event_source,
        "details": details
    })

    # Determine the correct file to write to
    if event_type in PROBLEM_EVENTS:
        target_file = PROBLEMS_FILE
    elif event_type in SOLUTION_EVENTS:
        target_file = SOLUTIONS_FILE
    else:
        # As a fallback, if the event type is unknown, we can log it to a separate file
        # or raise an error. For now, we'll log to a generic file to avoid losing data.
        target_file = os.path.join(LOG_DIRECTORY, "unknown_events.jsonl")

    try:
        # Ensure the directory exists
        os.makedirs(LOG_DIRECTORY, exist_ok=True)
        
        # Append the JSON object as a new line
        with open(target_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    except IOError as e:
        # In a real application, you might have a fallback logging mechanism here
        print(f"Error writing to RAG log file: {e}")
