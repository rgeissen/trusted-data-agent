#!/usr/bin/env python3
"""
Migration script to add classification_mode and classification_results to existing profiles.
Run this once to migrate from global classification to profile-based classification.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import shutil

def migrate_profiles():
    """Migrate existing profiles to include classification_mode and classification_results."""
    
    config_file = Path("tda_config.json")
    
    if not config_file.exists():
        print("❌ tda_config.json not found")
        return False
    
    # Create backup
    backup_file = config_file.with_suffix(f'.json.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    shutil.copy2(config_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    profiles = config.get("profiles", [])
    
    if not profiles:
        print("ℹ️  No profiles found to migrate")
        return True
    
    print(f"\n📋 Found {len(profiles)} profiles to migrate")
    
    migrated_count = 0
    skipped_count = 0
    
    for profile in profiles:
        profile_id = profile.get("id", "unknown")
        profile_name = profile.get("name", profile.get("tag", "unnamed"))
        
        # Check if already migrated
        if "classification_mode" in profile and "classification_results" in profile:
            print(f"  ⏭️  Skipped: {profile_name} ({profile_id}) - already migrated")
            skipped_count += 1
            continue
        
        # Add classification_mode (default to 'full' for existing profiles)
        if "classification_mode" not in profile:
            profile["classification_mode"] = "full"
        
        # Add empty classification_results structure
        if "classification_results" not in profile:
            profile["classification_results"] = {
                "tools": {},
                "prompts": {},
                "resources": {},
                "last_classified": None,
                "classified_with_mode": None
            }
        
        print(f"  ✅ Migrated: {profile_name} ({profile_id}) - mode: {profile['classification_mode']}")
        migrated_count += 1
    
    # Save updated config
    config["last_modified"] = datetime.now(timezone.utc).isoformat()
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Migration complete!")
    print(f"   - Migrated: {migrated_count} profiles")
    print(f"   - Skipped: {skipped_count} profiles")
    print(f"   - Backup saved to: {backup_file}")
    print(f"\n💡 Note: Profiles will be reclassified on first use with their new classification mode")
    
    return True

def main():
    """Main entry point."""
    print("=" * 70)
    print("Profile Classification Migration")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Add 'classification_mode' field to all profiles (default: 'full')")
    print("  2. Add 'classification_results' structure to all profiles")
    print("  3. Create a backup of tda_config.json")
    print("\n⚠️  Make sure the application is stopped before running this migration")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Migration cancelled")
        return 1
    
    print("\n🚀 Starting migration...\n")
    
    success = migrate_profiles()
    
    if success:
        print("\n✨ Migration successful!")
        print("\nNext steps:")
        print("  1. Review the migrated profiles in tda_config.json")
        print("  2. Start the application")
        print("  3. Profiles will reclassify automatically on first connection")
        return 0
    else:
        print("\n❌ Migration failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
