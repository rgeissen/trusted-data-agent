#!/usr/bin/env python3
"""
View classification results for a profile.
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5050/api"

def get_classification(profile_id):
    """Get classification results for a profile"""
    print(f"\nFetching classification for profile: {profile_id}")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/v1/profiles/{profile_id}/classification")
    
    if response.status_code == 200:
        classification = response.json()
        
        mode = classification.get('mode', 'unknown')
        cached_at = classification.get('cached_at', 'N/A')
        
        print(f"\nClassification Mode: {mode}")
        print(f"Cached At: {cached_at}")
        
        # Tools
        tools = classification.get('tools', {})
        print(f"\n{'='*80}")
        print(f"TOOLS ({len(tools)} categories)")
        print(f"{'='*80}")
        
        total_tools = 0
        for category, tool_list in sorted(tools.items()):
            if isinstance(tool_list, dict):
                count = len(tool_list)
                total_tools += count
                print(f"\n[{category}] - {count} tools")
                for tool_name, tool_info in list(tool_list.items())[:3]:  # Show first 3
                    desc = tool_info.get('description', '')[:60] if isinstance(tool_info, dict) else ''
                    print(f"  • {tool_name}")
                    if desc:
                        print(f"    {desc}...")
                if count > 3:
                    print(f"  ... and {count - 3} more")
            elif isinstance(tool_list, list):
                count = len(tool_list)
                total_tools += count
                print(f"\n[{category}] - {count} tools")
                for tool in tool_list[:3]:  # Show first 3
                    if isinstance(tool, dict):
                        name = tool.get('name', 'unknown')
                        desc = tool.get('description', '')[:60]
                        print(f"  • {name}")
                        if desc:
                            print(f"    {desc}...")
                    else:
                        print(f"  • {tool}")
                if count > 3:
                    print(f"  ... and {count - 3} more")
        
        print(f"\nTotal Tools: {total_tools}")
        
        # Prompts
        prompts = classification.get('prompts', {})
        print(f"\n{'='*80}")
        print(f"PROMPTS ({len(prompts)} categories)")
        print(f"{'='*80}")
        
        total_prompts = 0
        for category, prompt_list in sorted(prompts.items()):
            if isinstance(prompt_list, dict):
                count = len(prompt_list)
                total_prompts += count
                print(f"\n[{category}] - {count} prompts")
                for prompt_name in list(prompt_list.keys())[:5]:  # Show first 5
                    print(f"  • {prompt_name}")
                if count > 5:
                    print(f"  ... and {count - 5} more")
            elif isinstance(prompt_list, list):
                count = len(prompt_list)
                total_prompts += count
                print(f"\n[{category}] - {count} prompts")
                for prompt in prompt_list[:5]:  # Show first 5
                    if isinstance(prompt, dict):
                        name = prompt.get('name', 'unknown')
                        print(f"  • {name}")
                    else:
                        print(f"  • {prompt}")
                if count > 5:
                    print(f"  ... and {count - 5} more")
        
        print(f"\nTotal Prompts: {total_prompts}")
        
        # Resources (if any)
        resources = classification.get('resources', {})
        if resources:
            print(f"\n{'='*80}")
            print(f"RESOURCES ({len(resources)} categories)")
            print(f"{'='*80}")
            for category, resource_list in sorted(resources.items()):
                count = len(resource_list) if isinstance(resource_list, (list, dict)) else 0
                print(f"\n[{category}] - {count} resources")
        
        print(f"\n{'='*80}")
        
        return True
    else:
        print(f"✗ Failed to get classification: HTTP {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False


def list_profiles():
    """List all profiles"""
    response = requests.get(f"{BASE_URL}/v1/profiles")
    if response.status_code == 200:
        profiles = response.json().get("profiles", [])
        print("\nAvailable Profiles:")
        for p in profiles:
            print(f"  • {p['name']}")
            print(f"    ID: {p['id']}")
            print(f"    Classification Mode: {p.get('classification_mode', 'N/A')}")
        return profiles
    return []


if __name__ == "__main__":
    if len(sys.argv) > 1:
        profile_id = sys.argv[1]
        get_classification(profile_id)
    else:
        profiles = list_profiles()
        if profiles:
            print(f"\nUsage: python {sys.argv[0]} <profile_id>")
            print(f"\nExample:")
            print(f"  python {sys.argv[0]} {profiles[0]['id']}")
