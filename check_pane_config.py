#!/usr/bin/env python3
"""
Quick diagnostic script to check pane visibility configuration in database.
"""
import sys
sys.path.insert(0, 'src')

from trusted_data_agent.auth.models import User, PaneVisibility
from trusted_data_agent.auth.database import get_db_session

def check_panes():
    print("=== Checking Pane Visibility Configuration ===\n")
    
    with get_db_session() as session:
        # Check admin user
        admin_user = session.query(User).filter_by(username='admin').first()
        if admin_user:
            print(f"Admin User Found:")
            print(f"  Username: {admin_user.username}")
            print(f"  Profile Tier: {admin_user.profile_tier}")
            print(f"  Is Admin: {admin_user.is_admin}")
            print()
        else:
            print("WARNING: Admin user not found!\n")
        
        # Check pane visibility configurations
        panes = session.query(PaneVisibility).order_by(PaneVisibility.display_order).all()
        
        if not panes:
            print("WARNING: No pane visibility configurations found!")
            print("The system should initialize defaults on first request.\n")
        else:
            print(f"Found {len(panes)} pane configurations:\n")
            print(f"{'Pane ID':<20} {'User':<8} {'Developer':<12} {'Admin':<8} {'Order':<6}")
            print("-" * 60)
            
            for pane in panes:
                print(f"{pane.pane_id:<20} "
                      f"{'✓' if pane.visible_to_user else '✗':<8} "
                      f"{'✓' if pane.visible_to_developer else '✗':<12} "
                      f"{'✓' if pane.visible_to_admin else '✗':<8} "
                      f"{pane.display_order:<6}")
            
            print()
            
            # Count how many should be visible to admin
            admin_visible = sum(1 for p in panes if p.visible_to_admin)
            developer_visible = sum(1 for p in panes if p.visible_to_developer)
            user_visible = sum(1 for p in panes if p.visible_to_user)
            
            print(f"Panes visible to:")
            print(f"  User tier: {user_visible}")
            print(f"  Developer tier: {developer_visible}")
            print(f"  Admin tier: {admin_visible}")
            print()
            
            if admin_visible < 6:
                print(f"WARNING: Admin should see 6 panes, but only {admin_visible} are configured!")
                print("This might be the cause of the issue.\n")

if __name__ == '__main__':
    check_panes()
