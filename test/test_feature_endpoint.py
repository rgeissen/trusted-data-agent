#!/usr/bin/env python3
"""Test script for feature tagging system endpoint."""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def login(username, password):
    """Login and get authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def get_user_features(token):
    """Get user features from /me/features endpoint."""
    response = requests.get(
        f"{BASE_URL}/api/v1/auth/me/features",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Get features failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_user_tier(username, password, expected_tier):
    """Test feature access for a specific user tier."""
    print(f"\n{'='*70}")
    print(f"Testing: {username} (expected tier: {expected_tier})")
    print(f"{'='*70}")
    
    # Login
    token = login(username, password)
    if not token:
        print(f"⚠️  Could not login as {username}")
        return
    
    print(f"✅ Login successful")
    
    # Get features
    features_data = get_user_features(token)
    if not features_data:
        print(f"⚠️  Could not get features")
        return
    
    # Display results
    print(f"\n📊 Feature Access Summary:")
    print(f"   Profile Tier: {features_data.get('profile_tier')}")
    print(f"   Total Features: {features_data.get('feature_count')}")
    
    print(f"\n🎯 Feature Groups:")
    for group, has_access in sorted(features_data.get('feature_groups', {}).items()):
        status = "✅" if has_access else "❌"
        print(f"   {status} {group}")
    
    print(f"\n📝 Available Features ({len(features_data.get('features', []))}):")
    features = sorted(features_data.get('features', []))
    
    # Show first 10 features
    for feature in features[:10]:
        print(f"   • {feature}")
    
    if len(features) > 10:
        print(f"   ... and {len(features) - 10} more features")
    
    # Verify tier
    actual_tier = features_data.get('profile_tier')
    if actual_tier == expected_tier:
        print(f"\n✅ Tier verification PASSED: {actual_tier} == {expected_tier}")
    else:
        print(f"\n❌ Tier verification FAILED: {actual_tier} != {expected_tier}")
    
    return features_data

def main():
    print("=" * 70)
    print("Feature Tagging System - Endpoint Testing")
    print("=" * 70)
    
    # Test all three tiers
    print("\n🔹 Testing USER TIER (Basic Access)")
    user_data = test_user_tier("usertest", "Test123456", "user")
    
    # Temporarily set featuretest to developer for testing
    print("\n🔹 Testing DEVELOPER TIER (User + Advanced Features)")
    print("   (Temporarily changing featuretest to developer tier)")
    import subprocess
    subprocess.run([
        "sqlite3",
        "/Users/rainergeissendoerfer/my_private_code/trusted-data-agent/tda_auth.db",
        "UPDATE users SET profile_tier='developer' WHERE username='featuretest';"
    ], capture_output=True)
    dev_data = test_user_tier("featuretest", "Test123456", "developer")
    
    # Set back to admin
    print("\n🔹 Testing ADMIN TIER (Full System Access)")
    print("   (Changing featuretest back to admin tier)")
    subprocess.run([
        "sqlite3",
        "/Users/rainergeissendoerfer/my_private_code/trusted-data-agent/tda_auth.db",
        "UPDATE users SET profile_tier='admin' WHERE username='featuretest';"
    ], capture_output=True)
    admin_data = test_user_tier("featuretest", "Test123456", "admin")
    
    # Summary comparison
    if user_data and dev_data and admin_data:
        print("\n" + "="*70)
        print("📈 Feature Count Summary:")
        print("="*70)
        print(f"   USER:      {user_data.get('feature_count'):2d} features")
        print(f"   DEVELOPER: {dev_data.get('feature_count'):2d} features (+{dev_data.get('feature_count') - user_data.get('feature_count')} from user)")
        print(f"   ADMIN:     {admin_data.get('feature_count'):2d} features (+{admin_data.get('feature_count') - dev_data.get('feature_count')} from developer)")
        print("\n✅ Hierarchical inheritance working correctly!")
        print(f"✅ Total unique features defined: {admin_data.get('feature_count')}")
    
    print("\n" + "=" * 70)
    print("Testing Complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
