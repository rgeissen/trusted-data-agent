#!/usr/bin/env python3
"""
Load bootstrap cost entries from tda_config.json into the database.
Safe to run multiple times - will not overwrite existing entries.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trusted_data_agent.auth.database import get_db_session
from src.trusted_data_agent.auth.models import LLMModelCost
from sqlalchemy import select

CONFIG_PATH = "tda_config.json"


def load_bootstrap_costs():
    """Load default costs from tda_config.json."""
    print("=" * 60)
    print("Loading Bootstrap Costs from tda_config.json")
    print("=" * 60 + "\n")
    
    config_path = Path(__file__).parent.parent / CONFIG_PATH
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}\n")
        return
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        default_costs = config.get('default_model_costs', [])
        
        if not default_costs:
            print("❌ No default_model_costs found in config\n")
            return
        
        print(f"📋 Found {len(default_costs)} default costs in config\n")
        
        with get_db_session() as db:
            added_count = 0
            skipped_count = 0
            
            for cost_entry in default_costs:
                provider = cost_entry.get('provider')
                model = cost_entry.get('model')
                input_cost = cost_entry.get('input_cost_per_million')
                output_cost = cost_entry.get('output_cost_per_million')
                notes = cost_entry.get('notes', '')
                
                if not all([provider, model, input_cost is not None, output_cost is not None]):
                    print(f"⚠️  Skipping invalid entry: {cost_entry}")
                    continue
                
                # Check if entry already exists
                stmt = select(LLMModelCost).where(
                    LLMModelCost.provider == provider,
                    LLMModelCost.model == model
                )
                existing = db.execute(stmt).scalar_one_or_none()
                
                if existing:
                    print(f"⏭️  Skipped: {provider}/{model} (already exists)")
                    skipped_count += 1
                    continue
                
                # Insert config default
                new_cost = LLMModelCost(
                    id=str(uuid.uuid4()),
                    provider=provider,
                    model=model,
                    input_cost_per_million=input_cost,
                    output_cost_per_million=output_cost,
                    is_manual_entry=False,
                    is_fallback=False,
                    source='config_default',
                    last_updated=datetime.now(timezone.utc),
                    notes=notes
                )
                db.add(new_cost)
                print(f"✅ Added: {provider}/{model}")
                added_count += 1
            
            db.commit()
            
            print("\n" + "=" * 60)
            print(f"✅ Loaded {added_count} bootstrap costs")
            if skipped_count > 0:
                print(f"ℹ️  Skipped {skipped_count} existing entries")
            print("=" * 60 + "\n")
            
    except Exception as e:
        print(f"\n❌ Failed to load bootstrap costs: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    load_bootstrap_costs()
