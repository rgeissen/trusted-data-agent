#!/usr/bin/env python3
"""
Backfill session names and user queries in consumption_turns table from session files.
Run this after adding user_query and session_name fields to ConsumptionTurn model.
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import ConsumptionTurn
from sqlalchemy import distinct

def load_session_file(user_uuid: str, session_id: str) -> dict:
    """Load session data from JSON file."""
    session_dir = Path(__file__).parent.parent / "tda_sessions" / user_uuid
    session_file = session_dir / f"{session_id}.json"
    
    if not session_file.exists():
        return None
    
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading session file {session_file}: {e}")
        return None

def backfill_session_data():
    """Backfill session names and user queries from session files."""
    
    with get_db_session() as db_session:
        # Get all unique user_id and session_id combinations
        sessions = db_session.query(
            distinct(ConsumptionTurn.user_id),
            distinct(ConsumptionTurn.session_id)
        ).filter(
            ConsumptionTurn.session_name == None  # Only update rows without session_name
        ).all()
        
        print(f"Found {len(sessions)} unique sessions to backfill")
        
        updated_count = 0
        error_count = 0
        
        for user_id, session_id in sessions:
            try:
                # Load session file
                session_data = load_session_file(user_id, session_id)
                if not session_data:
                    print(f"  ⚠️  Session file not found: {user_id}/{session_id}")
                    error_count += 1
                    continue
                
                session_name = session_data.get('name', 'Untitled Session')
                workflow_history = session_data.get('last_turn_data', {}).get('workflow_history', [])
                
                # Update all turns for this session
                turns = db_session.query(ConsumptionTurn).filter(
                    ConsumptionTurn.user_id == user_id,
                    ConsumptionTurn.session_id == session_id
                ).all()
                
                for turn in turns:
                    # Update session name
                    turn.session_name = session_name
                    
                    # Update user query if we can find it in workflow history
                    if turn.user_query is None and workflow_history:
                        # Find the matching turn in workflow history (1-indexed)
                        if 0 < turn.turn_number <= len(workflow_history):
                            turn_data = workflow_history[turn.turn_number - 1]
                            turn.user_query = turn_data.get('user_query', 'N/A')
                    
                    updated_count += 1
                
                db_session.commit()
                print(f"  ✅ Updated session: {session_name} ({len(turns)} turns)")
                
            except Exception as e:
                print(f"  ❌ Error updating session {session_id}: {e}")
                db_session.rollback()
                error_count += 1
                continue
        
        print(f"\n{'='*60}")
        print(f"Backfill complete!")
        print(f"  Updated: {updated_count} turns")
        print(f"  Errors:  {error_count} sessions")
        print(f"{'='*60}")

if __name__ == "__main__":
    print("Backfilling session names and user queries...")
    print("="*60)
    backfill_session_data()
