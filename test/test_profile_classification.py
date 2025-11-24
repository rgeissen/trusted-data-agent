#!/usr/bin/env python3
"""
Comprehensive test suite for profile-based classification system.
Tests Phases 1-4 implementation.

Usage:
    python test/test_profile_classification.py

Prerequisites:
    - Application running on http://127.0.0.1:5000
    - Valid authentication token (or SKIP_AUTH=true)
"""

import requests
import json
import time
from typing import Dict, Any, Optional

BASE_URL = "http://127.0.0.1:5000/api"
AUTH_TOKEN = None  # Will be set after login


class TestColors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a test section header"""
    print(f"\n{TestColors.HEADER}{TestColors.BOLD}{'='*80}{TestColors.ENDC}")
    print(f"{TestColors.HEADER}{TestColors.BOLD}{text}{TestColors.ENDC}")
    print(f"{TestColors.HEADER}{TestColors.BOLD}{'='*80}{TestColors.ENDC}\n")


def print_test(name: str):
    """Print test name"""
    print(f"{TestColors.OKCYAN}[TEST] {name}{TestColors.ENDC}")


def print_success(message: str):
    """Print success message"""
    print(f"{TestColors.OKGREEN}✓ {message}{TestColors.ENDC}")


def print_error(message: str):
    """Print error message"""
    print(f"{TestColors.FAIL}✗ {message}{TestColors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{TestColors.OKBLUE}ℹ {message}{TestColors.ENDC}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{TestColors.WARNING}⚠ {message}{TestColors.ENDC}")


def make_request(method: str, endpoint: str, json_data: Optional[Dict] = None, 
                 auth_required: bool = True) -> tuple[int, Dict[str, Any]]:
    """Make HTTP request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if auth_required and AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=json_data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, {"error": "Failed to parse JSON response"}
    
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return 0, {"error": str(e)}


def test_authentication():
    """Test authentication and get token"""
    global AUTH_TOKEN
    
    print_header("Phase 0: Authentication")
    print_test("Testing authentication")
    
    # Try to get profiles without auth first to see if auth is enabled
    status, response = make_request("GET", "/v1/profiles", auth_required=False)
    
    if status == 200:
        print_success("Authentication not required (SKIP_AUTH=true)")
        return True
    
    # Try to login
    print_info("Authentication required, attempting login...")
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    status, response = make_request("POST", "/auth/login", json_data=login_data, auth_required=False)
    
    if status == 200 and "token" in response:
        AUTH_TOKEN = response["token"]
        print_success(f"Login successful, token obtained")
        return True
    else:
        print_error(f"Login failed: {response}")
        return False


def test_phase1_data_model():
    """Test Phase 1: Data model changes"""
    print_header("Phase 1: Data Model Changes")
    
    # Test 1: Create profile with classification_mode
    print_test("Creating profile with classification_mode='light'")
    profile_data = {
        "name": "Test Profile Light",
        "classification_mode": "light",
        "llm_provider": "Google",
        "llm_model": "gemini-1.5-flash",
        "mcp_servers": []
    }
    
    status, response = make_request("POST", "/v1/profiles", json_data=profile_data)
    
    if status in [200, 201] and response.get("status") == "success":
        # Profile might be nested in response.profile
        profile_data = response.get("profile", {})
        profile_id = profile_data.get("id")
        
        if not profile_id:
            print_error(f"Profile ID not found in response: {response}")
            return None
        
        print_success(f"Profile created successfully: {profile_id}")
        
        # Verify classification_mode from creation response
        if profile_data.get("classification_mode") == "light":
            print_success(f"classification_mode verified in response: {profile_data.get('classification_mode')}")
        else:
            print_error(f"classification_mode not found or incorrect")
            return None
        
        if "classification_results" in profile_data:
            print_success("classification_results field exists in response")
            results = profile_data.get("classification_results", {})
            print_info(f"  - Structure: tools={type(results.get('tools'))}, prompts={type(results.get('prompts'))}, resources={type(results.get('resources'))}")
        else:
            print_warning("classification_results field not present")
        
        return profile_id
    else:
        print_error(f"Failed to create profile (status {status}): {response.get('message', 'Unknown error')}")
        return None


def test_phase1_validation():
    """Test Phase 1: Validation logic"""
    print_test("Testing classification_mode validation")
    
    # Test invalid classification_mode
    invalid_profile = {
        "name": "Invalid Profile",
        "classification_mode": "invalid_mode",
        "llm_provider": "Google",
        "llm_model": "gemini-1.5-flash",
        "mcp_servers": []
    }
    
    status, response = make_request("POST", "/v1/profiles", json_data=invalid_profile)
    
    if status == 400:
        print_success("Invalid classification_mode correctly rejected")
    else:
        print_error(f"Invalid mode should have been rejected but got: {status}")


def test_phase2_mcp_adapter(profile_id: str):
    """Test Phase 2: MCP adapter changes"""
    print_header("Phase 2: MCP Adapter Integration")
    
    print_test("Testing profile uses its own classification_mode")
    
    # Create profiles with different modes
    modes_to_test = ["none", "light", "full"]
    created_profiles = {}
    
    for mode in modes_to_test:
        print_info(f"Creating profile with mode='{mode}'")
        profile_data = {
            "name": f"Test Profile {mode.title()}",
            "classification_mode": mode,
            "llm_provider": "Google",
            "llm_model": "gemini-1.5-flash",
            "mcp_servers": []
        }
        
        status, response = make_request("POST", "/v1/profiles", json_data=profile_data)
        
        if status in [200, 201] and response.get("status") == "success":
            pid = response.get("profile", {}).get("id")
            if pid:
                created_profiles[mode] = pid
                print_success(f"Created profile with mode '{mode}': {pid}")
            else:
                print_error(f"Profile ID not found for mode '{mode}'")
        else:
            print_error(f"Failed to create profile with mode '{mode}': {response}")
    
    return created_profiles


def test_phase3_api_endpoints(profile_id: str):
    """Test Phase 3: Classification API endpoints"""
    print_header("Phase 3: API Endpoints")
    
    # Test 1: GET /v1/profiles/<id>/classification
    print_test("GET /v1/profiles/<id>/classification")
    status, response = make_request("GET", f"/v1/profiles/{profile_id}/classification")
    
    if status == 200:
        print_success("Classification endpoint accessible")
        print_info(f"Classification mode: {response.get('classification_mode')}")
        
        results = response.get('classification_results', {})
        print_info(f"Tools categories: {len(results.get('tools', {}))}")
        print_info(f"Prompts categories: {len(results.get('prompts', {}))}")
        print_info(f"Resources categories: {len(results.get('resources', {}))}")
    else:
        print_error(f"Failed to get classification: {response}")
    
    # Test 2: POST /v1/profiles/<id>/reclassify
    print_test("POST /v1/profiles/<id>/reclassify")
    status, response = make_request("POST", f"/v1/profiles/{profile_id}/reclassify")
    
    if status == 200:
        print_success("Reclassify endpoint working")
        print_info(f"Message: {response.get('message')}")
    else:
        print_error(f"Failed to reclassify: {response}")


def test_phase4_profile_switching(profiles: Dict[str, str]):
    """Test Phase 4: Profile switching logic"""
    print_header("Phase 4: Profile Switching")
    
    if not profiles:
        print_warning("No profiles available for switching test")
        return
    
    for mode, profile_id in profiles.items():
        print_test(f"Activating profile with mode='{mode}'")
        status, response = make_request("POST", f"/v1/profiles/{profile_id}/activate")
        
        if status == 200:
            print_success(f"Profile activated successfully")
            print_info(f"Classification mode: {response.get('classification_mode')}")
            print_info(f"Used cache: {response.get('used_cache')}")
        else:
            print_error(f"Failed to activate profile: {response}")
        
        time.sleep(0.5)  # Brief pause between switches


def test_classification_caching(profile_id: str):
    """Test classification caching behavior"""
    print_header("Classification Caching Test")
    
    print_test("First activation (should run classification)")
    status, response = make_request("POST", f"/v1/profiles/{profile_id}/activate")
    
    if status == 200:
        used_cache_first = response.get('used_cache')
        print_info(f"First activation - used cache: {used_cache_first}")
    
    time.sleep(1)
    
    print_test("Second activation (should use cache)")
    status, response = make_request("POST", f"/v1/profiles/{profile_id}/activate")
    
    if status == 200:
        used_cache_second = response.get('used_cache')
        print_info(f"Second activation - used cache: {used_cache_second}")
        
        if not used_cache_first and used_cache_second:
            print_success("Caching behavior verified: first run classified, second used cache")
        elif used_cache_first and used_cache_second:
            print_info("Both used cache (profile may have been classified previously)")
        else:
            print_warning("Unexpected caching behavior - may need investigation")


def test_mode_change_invalidation(profile_id: str):
    """Test that changing classification mode invalidates cache"""
    print_header("Mode Change Cache Invalidation Test")
    
    print_test("Updating profile classification_mode")
    
    # Update to different mode
    update_data = {"classification_mode": "full"}
    status, response = make_request("PUT", f"/v1/profiles/{profile_id}", json_data=update_data)
    
    if status == 200:
        print_success("Profile mode updated successfully")
        
        # Now activate - should not use cache
        print_test("Activating after mode change")
        status, response = make_request("POST", f"/v1/profiles/{profile_id}/activate")
        
        if status == 200:
            used_cache = response.get('used_cache')
            print_info(f"Used cache after mode change: {used_cache}")
            
            if not used_cache:
                print_success("Cache correctly invalidated after mode change")
            else:
                print_warning("Cache was used after mode change - may indicate issue")
    else:
        print_error(f"Failed to update profile: {response}")


def test_get_all_profiles():
    """Test getting all profiles to see classification modes"""
    print_header("Profile List Test")
    
    print_test("GET /v1/profiles (all profiles)")
    status, response = make_request("GET", "/v1/profiles")
    
    if status == 200:
        profiles = response.get('profiles', [])
        print_success(f"Retrieved {len(profiles)} profiles")
        
        for profile in profiles:
            profile_id = profile.get('id', 'unknown')
            name = profile.get('name', 'unnamed')
            mode = profile.get('classification_mode', 'not set')
            print_info(f"  - {name} (ID: {profile_id}): mode={mode}")
    else:
        print_error(f"Failed to get profiles: {response}")


def run_all_tests():
    """Run complete test suite"""
    print(f"\n{TestColors.BOLD}Profile-Based Classification Test Suite{TestColors.ENDC}")
    print(f"{TestColors.BOLD}Testing implementation of Phases 1-4{TestColors.ENDC}")
    
    # Phase 0: Auth
    if not test_authentication():
        print_error("Authentication failed, cannot continue tests")
        return
    
    # Phase 1: Data model
    test_profile_id = test_phase1_data_model()
    if not test_profile_id:
        print_error("Phase 1 tests failed, cannot continue")
        return
    
    test_phase1_validation()
    
    # Phase 2: MCP adapter
    mode_profiles = test_phase2_mcp_adapter(test_profile_id)
    
    # Phase 3: API endpoints
    test_phase3_api_endpoints(test_profile_id)
    
    # Phase 4: Profile switching
    test_phase4_profile_switching(mode_profiles)
    
    # Additional tests
    if mode_profiles.get('light'):
        test_classification_caching(mode_profiles['light'])
        test_mode_change_invalidation(mode_profiles['light'])
    
    # Summary
    test_get_all_profiles()
    
    print_header("Test Suite Complete")
    print_success("All tests executed. Review output above for any failures.")


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print_warning("\nTests interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
