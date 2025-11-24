#!/usr/bin/env python3
"""
Migration script: Update profiles with classification_mode='none' to 'light'
Since 'none' mode is no longer supported, all profiles must use 'light' or 'full'.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from trusted_data_agent.core.config_manager import ConfigManager

def migrate_none_to_light():
    """Update all profiles with classification_mode='none' to 'light'"""
    config_manager = ConfigManager()
    
    # Get all profiles (no user filtering for migration)
    profiles = config_manager.get_all_profiles()
    
    updated_count = 0
    
    print(f"\nFound {len(profiles)} total profiles")
    print("Checking for profiles with classification_mode='none'...\n")
    
    for profile in profiles:
        profile_id = profile.get('id')
        current_mode = profile.get('classification_mode')
        
        if current_mode == 'none':
            print(f"  Updating profile '{profile.get('name')}' ({profile_id})")
            print(f"    Current mode: {current_mode} → New mode: light")
            
            # Update the profile
            profile['classification_mode'] = 'light'
            
            # Save the update
            success = config_manager.update_profile(profile_id, profile)
            
            if success:
                print(f"    ✓ Successfully updated")
                updated_count += 1
            else:
                print(f"    ✗ Failed to update")
    
    print(f"\n{'='*60}")
    print(f"Migration complete: Updated {updated_count} profile(s)")
    print(f"{'='*60}\n")
    
    return updated_count

if __name__ == "__main__":
    migrate_none_to_light()
