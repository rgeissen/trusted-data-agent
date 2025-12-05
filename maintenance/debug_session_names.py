#!/usr/bin/env python3
"""Debug script to check session names in consumption_turns table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import ConsumptionTurn
from sqlalchemy import func

def debug_session_names():
    with get_db_session() as db_session:
        # Get all distinct sessions
        sessions = db_session.query(
            ConsumptionTurn.session_id,
            ConsumptionTurn.session_name,
            func.sum(ConsumptionTurn.total_tokens).label('total_tokens')
        ).group_by(
            ConsumptionTurn.session_id,
            ConsumptionTurn.session_name
        ).order_by(
            func.sum(ConsumptionTurn.total_tokens).desc()
        ).limit(10).all()
        
        print("="*80)
        print("Top 10 Sessions by Token Count:")
        print("="*80)
        
        for session_id, session_name, tokens in sessions:
            print(f"\nSession ID: {session_id}")
            print(f"Session Name: {repr(session_name)}")
            print(f"Total Tokens: {tokens}")
            
            # Get sample turns for this session
            turns = db_session.query(ConsumptionTurn).filter(
                ConsumptionTurn.session_id == session_id
            ).limit(2).all()
            
            print(f"Sample turns ({len(turns)}):")
            for turn in turns:
                print(f"  - Turn {turn.turn_number}: name={repr(turn.session_name)}, query={repr(turn.user_query[:50] if turn.user_query else None)}")
        
        print("\n" + "="*80)
        
        # Check if any turns have session_name
        total_turns = db_session.query(func.count(ConsumptionTurn.id)).scalar()
        turns_with_name = db_session.query(func.count(ConsumptionTurn.id)).filter(
            ConsumptionTurn.session_name != None,
            ConsumptionTurn.session_name != ''
        ).scalar()
        
        print(f"\nTotal turns in database: {total_turns}")
        print(f"Turns with session_name: {turns_with_name}")
        print(f"Turns without session_name: {total_turns - turns_with_name}")
        print("="*80)

if __name__ == "__main__":
    debug_session_names()
