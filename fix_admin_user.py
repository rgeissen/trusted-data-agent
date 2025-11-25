#!/usr/bin/env python3
"""
Fix admin user's profile tier and is_admin flag.
"""
import sys
sys.path.insert(0, 'src')

from trusted_data_agent.auth.models import User
from trusted_data_agent.auth.database import get_db_session

def fix_admin_user():
    print("=== Fixing Admin User Configuration ===\n")
    
    with get_db_session() as session:
        # Find admin user
        admin_user = session.query(User).filter_by(username='admin').first()
        
        if not admin_user:
            print("ERROR: Admin user not found!")
            return
        
        print(f"Current admin user settings:")
        print(f"  Username: {admin_user.username}")
        print(f"  Profile Tier: {admin_user.profile_tier}")
        print(f"  Is Admin: {admin_user.is_admin}")
        print()
        
        # Fix the settings
        admin_user.profile_tier = 'admin'
        admin_user.is_admin = True
        
        session.commit()
        
        print(f"Updated admin user settings:")
        print(f"  Username: {admin_user.username}")
        print(f"  Profile Tier: {admin_user.profile_tier}")
        print(f"  Is Admin: {admin_user.is_admin}")
        print()
        print("✓ Admin user configuration fixed successfully!")

if __name__ == '__main__':
    fix_admin_user()
