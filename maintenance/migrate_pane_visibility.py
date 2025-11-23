#!/usr/bin/env python3
"""
Migration script to add and initialize pane_visibility table.

This script:
1. Creates the pane_visibility table if it doesn't exist
2. Seeds default pane configuration
3. Can be run safely multiple times (idempotent)

Usage:
    python maintenance/migrate_pane_visibility.py
"""

import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from trusted_data_agent.auth.database import get_db_session, init_database
from trusted_data_agent.auth.models import PaneVisibility


def migrate_pane_visibility():
    """
    Create pane_visibility table and seed default configuration.
    """
    print("=" * 70)
    print("Pane Visibility Migration")
    print("=" * 70)
    
    # Initialize database (creates tables if they don't exist)
    print("\n[1/3] Initializing database...")
    if not init_database():
        print("❌ Failed to initialize database")
        return False
    print("✅ Database initialized")
    
    # Check if panes already exist
    print("\n[2/3] Checking for existing pane configuration...")
    with get_db_session() as session:
        existing_panes = session.query(PaneVisibility).count()
        
        if existing_panes > 0:
            print(f"ℹ️  Found {existing_panes} existing pane(s)")
            response = input("Do you want to reset to defaults? (y/N): ").strip().lower()
            if response != 'y':
                print("✅ Migration complete (no changes)")
                return True
            
            # Delete existing panes
            print("   Deleting existing panes...")
            session.query(PaneVisibility).delete()
            session.commit()
            print("   ✅ Existing panes deleted")
        else:
            print("✅ No existing panes found")
    
    # Seed default panes
    print("\n[3/3] Creating default pane configuration...")
    
    default_panes = [
        {
            'pane_id': 'conversation',
            'pane_name': 'Conversations',
            'description': 'Chat interface for conversations',
            'display_order': 1,
            'visible_to_user': True,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'executions',
            'pane_name': 'Executions',
            'description': 'Execution dashboard and history',
            'display_order': 2,
            'visible_to_user': False,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'rag-maintenance',
            'pane_name': 'RAG Maintenance',
            'description': 'Manage RAG collections and templates',
            'display_order': 3,
            'visible_to_user': False,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'marketplace',
            'pane_name': 'Marketplace',
            'description': 'Browse and install RAG templates',
            'display_order': 4,
            'visible_to_user': True,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'credentials',
            'pane_name': 'Credentials',
            'description': 'Configure LLM and MCP credentials',
            'display_order': 5,
            'visible_to_user': True,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'admin',
            'pane_name': 'Administration',
            'description': 'User and system administration',
            'display_order': 6,
            'visible_to_user': False,
            'visible_to_developer': False,
            'visible_to_admin': True
        }
    ]
    
    with get_db_session() as session:
        for pane_data in default_panes:
            pane = PaneVisibility(**pane_data)
            session.add(pane)
            print(f"   ✅ Created pane: {pane_data['pane_name']}")
        
        session.commit()
    
    print("\n" + "=" * 70)
    print("✅ Migration completed successfully!")
    print("=" * 70)
    print("\nDefault Pane Configuration:")
    print("  • Conversations:    User, Developer, Admin")
    print("  • Executions:       Developer, Admin")
    print("  • RAG Maintenance:  Developer, Admin")
    print("  • Marketplace:      User, Developer, Admin")
    print("  • Credentials:      User, Developer, Admin")
    print("  • Administration:   Admin only")
    print("\nYou can modify these settings in the Admin panel.")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        success = migrate_pane_visibility()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
