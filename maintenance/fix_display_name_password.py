#!/usr/bin/env python3
"""
Fix Display Name Password Issue
================================
This script fixes user accounts where the password was accidentally stored
in the display_name field, which causes it to be displayed in the UI.

The script:
1. Identifies users where display_name might contain a password
2. Resets display_name to username for affected users
3. Logs all changes made
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import User
from datetime import datetime, timezone

def fix_display_name_password_issue():
    """Fix users where display_name contains what appears to be a password."""
    print("=" * 70)
    print("Fixing Display Name Password Issue")
    print("=" * 70)
    print()
    
    fixed_count = 0
    
    try:
        with get_db_session() as session:
            # Get all users
            users = session.query(User).all()
            
            print(f"Checking {len(users)} users...\n")
            
            for user in users:
                # Check if display_name looks like it might be a password
                # Passwords typically have special chars, mixed case, etc.
                # Also check if display_name is very different from username
                should_reset = False
                reason = ""
                
                if user.display_name:
                    # Check for password-like characteristics:
                    # 1. Contains special characters like $, !, @, #, etc.
                    # 2. Contains digits
                    # 3. Mixed case
                    # 4. Is significantly different from username
                    
                    has_special = any(c in user.display_name for c in '$!@#%^&*()_+-=[]{}|;:,.<>?/')
                    has_digit = any(c.isdigit() for c in user.display_name)
                    has_upper = any(c.isupper() for c in user.display_name)
                    has_lower = any(c.islower() for c in user.display_name)
                    
                    # If it has special chars AND digits, it's likely a password
                    if has_special and has_digit:
                        should_reset = True
                        reason = "Contains special characters and digits (password-like)"
                    
                    # Or if it has all typical password characteristics
                    elif has_special and has_digit and has_upper and has_lower:
                        should_reset = True
                        reason = "Contains all password characteristics"
                
                if should_reset:
                    old_display_name = user.display_name
                    user.display_name = user.username
                    user.updated_at = datetime.now(timezone.utc)
                    
                    print(f"✓ Fixed user: {user.username}")
                    print(f"  Old display_name: {old_display_name}")
                    print(f"  New display_name: {user.display_name}")
                    print(f"  Reason: {reason}")
                    print()
                    
                    fixed_count += 1
            
            if fixed_count > 0:
                # Commit changes
                session.commit()
                print(f"\n{'=' * 70}")
                print(f"✓ Successfully fixed {fixed_count} user(s)")
                print(f"{'=' * 70}")
            else:
                print("✓ No issues found. All display names look correct.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = fix_display_name_password_issue()
    sys.exit(0 if success else 1)
