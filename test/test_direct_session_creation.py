#!/usr/bin/env python3
"""
Direct test of the session creation with profile_id.
"""

import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trusted_data_agent.core.session_manager import create_session

async def test():
    user_uuid = "832e9f55-adc5-4f6a-8988-d38e32469612"
    
    # Create a session with profile_id
    try:
        session_id = create_session(
            user_uuid=user_uuid,
            provider="Google",
            llm_instance=None,  # Not using LLM for this test
            charting_intensity="reduced",
            profile_tag="TEST_TAG",
            profile_id="profile-test-123"
        )
        
        print(f"✓ Session created: {session_id}")
        
        # Check the file
        session_file = Path(f"/Users/rainer.geissendoerfer/my_private_code/trusted-data-agent/tda_sessions/{user_uuid}/{session_id}.json")
        
        if session_file.exists():
            import json
            with open(session_file) as f:
                data = json.load(f)
            print(f"✓ Session file exists")
            print(f"  profile_id: {data.get('profile_id')}")
            print(f"  profile_tag: {data.get('profile_tag')}")
        else:
            print(f"❌ Session file not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
