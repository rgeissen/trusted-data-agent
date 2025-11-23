#!/usr/bin/env python3
"""
Add user_uuid extraction to endpoints that use config_manager but don't have it
"""

import re

file_path = '/Users/rainergeissendoerfer/my_private_code/trusted-data-agent/src/trusted_data_agent/api/rest_routes.py'

# Read the file
with open(file_path, 'r') as f:
    content = f.read()

# Find all functions that use config_manager but don't extract user_uuid
pattern = r'(@rest_api_bp\.route\([^)]+\).*?\n)(async def (\w+)\([^)]*\):.*?\n)(    """[^"]*""".*?\n)?(    try:\n)'

def add_user_uuid_if_needed(match):
    route_decorator = match.group(1)
    func_def = match.group(2)
    docstring = match.group(3) or ''
    try_line = match.group(4)
    func_name = match.group(3)
    
    # Get a larger chunk to check if config_manager is used
    start_pos = match.start()
    end_pos = min(match.end() + 3000, len(content))
    func_body_sample = content[start_pos:end_pos]
    
    # Check if this function uses config_manager
    if 'config_manager.' not in func_body_sample:
        return match.group(0)
    
    # Check if user_uuid extraction already exists
    if 'user_uuid = _get_user_uuid_from_request()' in func_body_sample[:500]:
        return match.group(0)
    
    # Add user_uuid extraction right after "try:"
    user_uuid_line = '        user_uuid = _get_user_uuid_from_request()\n'
    return route_decorator + func_def + docstring + try_line + user_uuid_line

new_content = re.sub(pattern, add_user_uuid_if_needed, content)

# Count changes
changes = len([1 for old, new in zip(content.split('\n'), new_content.split('\n')) if old != new])

print(f"Adding user_uuid extraction to {changes} lines")

# Write the file
with open(file_path, 'w') as f:
    f.write(new_content)

print(f"✅ Updated {file_path}")
