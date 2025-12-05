#!/usr/bin/env python3
"""
Bootstrap consumption tracking from existing session files.

This migration script:
1. Creates the new consumption tracking tables
2. Scans all existing session files
3. Calculates aggregate metrics per user
4. Populates user_consumption table
5. Validates accuracy

Usage:
    python maintenance/migrate_consumption_tracking.py [--dry-run] [--validate-only]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from trusted_data_agent.auth.models import Base, UserConsumption, User, ConsumptionProfile
from trusted_data_agent.auth.consumption_manager import ConsumptionManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConsumptionMigrator:
    """Migrates consumption data from files to database."""
    
    def __init__(self, db_path: str, sessions_dir: str):
        """
        Initialize migrator.
        
        Args:
            db_path: Path to SQLite database
            sessions_dir: Path to tda_sessions directory
        """
        self.db_path = db_path
        self.sessions_dir = Path(sessions_dir)
        
        # Setup database
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.engine = engine
        Session = sessionmaker(bind=engine)
        self.session = Session()
        
        # Create tables if they don't exist
        inspector = inspect(engine)
        if 'user_consumption' not in inspector.get_table_names():
            logger.info("Creating consumption tracking tables...")
            Base.metadata.create_all(engine)
        
        self.manager = ConsumptionManager(self.session)
    
    def scan_session_files(self) -> Dict[str, Dict]:
        """
        Scan all session files and aggregate metrics per user.
        
        Returns:
            Dictionary mapping user_id to aggregated metrics
        """
        logger.info(f"Scanning session files in {self.sessions_dir}...")
        
        user_metrics = defaultdict(lambda: {
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_tokens': 0,
            'successful_turns': 0,
            'failed_turns': 0,
            'total_turns': 0,
            'rag_guided_turns': 0,
            'rag_output_tokens_saved': 0,
            'champion_cases_created': 0,
            'estimated_cost_cents': 0,
            'rag_cost_saved_cents': 0,
            'total_sessions': 0,
            'active_sessions': 0,
            'models_used': defaultdict(int),
            'providers_used': defaultdict(int),
            'collection_ids': set(),
            'first_usage_at': None,
            'last_usage_at': None
        })
        
        total_sessions = 0
        total_users = 0
        errors = []
        
        # Iterate through user directories
        if not self.sessions_dir.exists():
            logger.error(f"Sessions directory not found: {self.sessions_dir}")
            return {}
        
        for user_dir in self.sessions_dir.iterdir():
            if not user_dir.is_dir():
                continue
            
            user_id = user_dir.name
            total_users += 1
            
            # Iterate through session files
            for session_file in user_dir.glob('*.json'):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    total_sessions += 1
                    metrics = user_metrics[user_id]
                    metrics['total_sessions'] += 1
                    
                    # Check if session is active (has recent activity)
                    last_activity = session_data.get('updated_at')
                    if last_activity:
                        try:
                            last_dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                            # Consider active if updated in last 24 hours
                            if (datetime.now(timezone.utc) - last_dt).total_seconds() < 86400:
                                metrics['active_sessions'] += 1
                        except:
                            pass
                    
                    # Process workflow history
                    workflow_history = session_data.get('workflow_history', [])
                    for turn in workflow_history:
                        metrics['total_turns'] += 1
                        
                        # Token counts
                        input_tokens = turn.get('input_tokens', 0)
                        output_tokens = turn.get('output_tokens', 0)
                        metrics['total_input_tokens'] += input_tokens
                        metrics['total_output_tokens'] += output_tokens
                        metrics['total_tokens'] += (input_tokens + output_tokens)
                        
                        # Status
                        status = turn.get('status', 'success')
                        if status == 'success':
                            metrics['successful_turns'] += 1
                        elif status in ['failure', 'error']:
                            metrics['failed_turns'] += 1
                        
                        # RAG metrics
                        rag_used = turn.get('rag_used', False) or turn.get('using_rag', False)
                        if rag_used:
                            metrics['rag_guided_turns'] += 1
                            tokens_saved = turn.get('rag_tokens_saved', 0) or turn.get('rag_efficiency_gain', 0)
                            metrics['rag_output_tokens_saved'] += tokens_saved
                        
                        # Cost tracking
                        cost_cents = turn.get('cost_usd_cents', 0)
                        if cost_cents:
                            metrics['estimated_cost_cents'] += cost_cents
                        
                        # Model tracking
                        model = turn.get('model')
                        provider = turn.get('provider')
                        if model:
                            metrics['models_used'][model] += 1
                        if provider:
                            metrics['providers_used'][provider] += 1
                        
                        # Timestamp tracking
                        turn_ts = turn.get('timestamp') or turn.get('created_at')
                        if turn_ts:
                            try:
                                turn_dt = datetime.fromisoformat(turn_ts.replace('Z', '+00:00'))
                                if metrics['first_usage_at'] is None or turn_dt < metrics['first_usage_at']:
                                    metrics['first_usage_at'] = turn_dt
                                if metrics['last_usage_at'] is None or turn_dt > metrics['last_usage_at']:
                                    metrics['last_usage_at'] = turn_dt
                            except:
                                pass
                    
                    # Track RAG champion cases (if session has rag_cases metadata)
                    rag_cases = session_data.get('rag_cases', [])
                    if rag_cases:
                        metrics['champion_cases_created'] += len(rag_cases)
                    
                    # Track collection subscriptions
                    collections = session_data.get('collections_subscribed', [])
                    if collections:
                        metrics['collection_ids'].update(collections)
                
                except Exception as e:
                    error_msg = f"Error processing {session_file}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        logger.info(f"Scanned {total_sessions} sessions from {total_users} users")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during scan")
        
        return dict(user_metrics)
    
    def populate_consumption_table(self, user_metrics: Dict[str, Dict], dry_run: bool = False) -> int:
        """
        Populate user_consumption table with aggregated metrics.
        
        Args:
            user_metrics: Dictionary of user metrics from scan
            dry_run: If True, don't commit changes
            
        Returns:
            Number of records created
        """
        logger.info(f"Populating consumption table for {len(user_metrics)} users...")
        
        created_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc)
        current_period = now.strftime("%Y-%m")
        
        for user_id, metrics in user_metrics.items():
            # Verify user exists
            user = self.session.query(User).filter_by(id=user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found in database, skipping")
                continue
            
            # Get or create consumption record
            consumption = self.session.query(UserConsumption).filter_by(user_id=user_id).first()
            
            if consumption:
                # Update existing record
                logger.info(f"Updating existing consumption for user {user_id}")
                updated_count += 1
            else:
                # Create new record
                logger.info(f"Creating consumption record for user {user_id}")
                
                # Get user's consumption profile for limits
                profile = user.consumption_profile
                if not profile:
                    profile = self.session.query(ConsumptionProfile).filter_by(is_default=True).first()
                
                consumption = UserConsumption(
                    user_id=user_id,
                    current_period=current_period,
                    period_started_at=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                    hour_reset_at=now.replace(minute=0, second=0, microsecond=0),
                    day_reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0),
                    input_tokens_limit=profile.input_tokens_per_month if profile else None,
                    output_tokens_limit=profile.output_tokens_per_month if profile else None,
                    prompts_per_hour_limit=profile.prompts_per_hour if profile else 100,
                    prompts_per_day_limit=profile.prompts_per_day if profile else 1000
                )
                self.session.add(consumption)
                created_count += 1
            
            # Update all metrics
            consumption.total_input_tokens = metrics['total_input_tokens']
            consumption.total_output_tokens = metrics['total_output_tokens']
            consumption.total_tokens = metrics['total_tokens']
            consumption.successful_turns = metrics['successful_turns']
            consumption.failed_turns = metrics['failed_turns']
            consumption.total_turns = metrics['total_turns']
            consumption.rag_guided_turns = metrics['rag_guided_turns']
            consumption.rag_output_tokens_saved = metrics['rag_output_tokens_saved']
            consumption.champion_cases_created = metrics['champion_cases_created']
            consumption.estimated_cost_usd = metrics['estimated_cost_cents']
            consumption.rag_cost_saved_usd = metrics['rag_cost_saved_cents']
            consumption.total_sessions = metrics['total_sessions']
            consumption.active_sessions = metrics['active_sessions']
            
            # Convert model/provider dicts to JSON
            consumption.models_used = json.dumps(dict(metrics['models_used']))
            consumption.providers_used = json.dumps(dict(metrics['providers_used']))
            
            # Convert collection set to JSON list
            consumption.collections_subscribed = json.dumps(list(metrics['collection_ids']))
            
            # Set timestamps
            if metrics['first_usage_at']:
                consumption.first_usage_at = metrics['first_usage_at']
            if metrics['last_usage_at']:
                consumption.last_usage_at = metrics['last_usage_at']
            consumption.last_updated_at = now
        
        if not dry_run:
            self.session.commit()
            logger.info(f"Created {created_count} records, updated {updated_count} records")
        else:
            self.session.rollback()
            logger.info(f"DRY RUN: Would create {created_count} records, update {updated_count} records")
        
        return created_count + updated_count
    
    def validate_migration(self, user_metrics: Dict[str, Dict]) -> Tuple[bool, List[str]]:
        """
        Validate migrated data against source metrics.
        
        Args:
            user_metrics: Original metrics from file scan
            
        Returns:
            Tuple of (success: bool, errors: List[str])
        """
        logger.info("Validating migration accuracy...")
        
        errors = []
        validated_count = 0
        
        for user_id, expected in user_metrics.items():
            consumption = self.session.query(UserConsumption).filter_by(user_id=user_id).first()
            
            if not consumption:
                errors.append(f"User {user_id}: No consumption record found")
                continue
            
            # Validate critical fields
            if consumption.total_tokens != expected['total_tokens']:
                errors.append(
                    f"User {user_id}: Token mismatch - "
                    f"expected {expected['total_tokens']}, got {consumption.total_tokens}"
                )
            
            if consumption.total_sessions != expected['total_sessions']:
                errors.append(
                    f"User {user_id}: Session count mismatch - "
                    f"expected {expected['total_sessions']}, got {consumption.total_sessions}"
                )
            
            if consumption.total_turns != expected['total_turns']:
                errors.append(
                    f"User {user_id}: Turn count mismatch - "
                    f"expected {expected['total_turns']}, got {consumption.total_turns}"
                )
            
            validated_count += 1
        
        success = len(errors) == 0
        logger.info(f"Validated {validated_count} users - {'SUCCESS' if success else f'{len(errors)} ERRORS'}")
        
        return success, errors
    
    def print_summary(self, user_metrics: Dict[str, Dict]) -> None:
        """Print migration summary statistics."""
        total_users = len(user_metrics)
        total_sessions = sum(m['total_sessions'] for m in user_metrics.values())
        total_tokens = sum(m['total_tokens'] for m in user_metrics.values())
        total_turns = sum(m['total_turns'] for m in user_metrics.values())
        total_rag_turns = sum(m['rag_guided_turns'] for m in user_metrics.values())
        
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"Total Users:        {total_users:,}")
        print(f"Total Sessions:     {total_sessions:,}")
        print(f"Total Turns:        {total_turns:,}")
        print(f"Total Tokens:       {total_tokens:,}")
        print(f"RAG-Guided Turns:   {total_rag_turns:,}")
        if total_turns > 0:
            print(f"RAG Activation:     {(total_rag_turns/total_turns*100):.1f}%")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Migrate consumption tracking to database')
    parser.add_argument('--db-path', default='tda_auth.db', help='Path to SQLite database')
    parser.add_argument('--sessions-dir', default='tda_sessions', help='Path to sessions directory')
    parser.add_argument('--dry-run', action='store_true', help='Scan and validate without writing')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing data')
    
    args = parser.parse_args()
    
    try:
        migrator = ConsumptionMigrator(args.db_path, args.sessions_dir)
        
        # Scan session files
        user_metrics = migrator.scan_session_files()
        
        if not user_metrics:
            logger.error("No session data found to migrate")
            return 1
        
        # Print summary
        migrator.print_summary(user_metrics)
        
        if args.validate_only:
            # Only validate
            success, errors = migrator.validate_migration(user_metrics)
            if not success:
                print("\nValidation Errors:")
                for error in errors[:10]:  # Show first 10 errors
                    print(f"  - {error}")
                if len(errors) > 10:
                    print(f"  ... and {len(errors) - 10} more errors")
                return 1
        else:
            # Populate database
            count = migrator.populate_consumption_table(user_metrics, dry_run=args.dry_run)
            
            if not args.dry_run:
                # Validate migration
                success, errors = migrator.validate_migration(user_metrics)
                if not success:
                    print("\nValidation Errors:")
                    for error in errors[:10]:
                        print(f"  - {error}")
                    if len(errors) > 10:
                        print(f"  ... and {len(errors) - 10} more errors")
                    return 1
        
        logger.info("Migration completed successfully!")
        return 0
    
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
