#!/usr/bin/env python3
"""
Migration script: Add needs_reclassification field to existing profiles
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from trusted_data_agent.core.config_manager import ConfigManager

def add_needs_reclassification_field():
    """Add needs_reclassification field to all profiles that don't have it"""
    config_manager = ConfigManager()
    
    # Get all profiles (use None for user_uuid to get all)
    profiles = config_manager.get_profiles(user_uuid=None)
    
    updated_count = 0
    
    print(f"\nFound {len(profiles)} total profiles")
    print("Adding needs_reclassification field to profiles...\n")
    
    for profile in profiles:
        profile_id = profile.get('id')
        
        if 'needs_reclassification' not in profile:
            print(f"  Updating profile '{profile.get('name')}' ({profile_id})")
            
            # Add the field - set to False for existing profiles (assume they're already working)
            # User can manually reclassify if needed
            profile['needs_reclassification'] = False
            
            # Save the update
            success = config_manager.update_profile(profile_id, profile)
            
            if success:
                print(f"    ✓ Added needs_reclassification=False")
                updated_count += 1
            else:
                print(f"    ✗ Failed to update")
    
    print(f"\n{'='*60}")
    print(f"Migration complete: Updated {updated_count} profile(s)")
    print(f"{'='*60}\n")
    
    return updated_count

if __name__ == "__main__":
    add_needs_reclassification_field()
