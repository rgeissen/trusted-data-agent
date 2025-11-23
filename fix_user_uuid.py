#!/usr/bin/env python3
"""
Script to add user_uuid parameter to all config_manager calls in rest_routes.py
"""

import re

# Read the file
with open('src/trusted_data_agent/api/rest_routes.py', 'r') as f:
    content = f.read()

# Pattern to find config_manager method calls without user_uuid parameter
# This matches calls like: config_manager.get_xxx() or config_manager.get_xxx(some_param)
# but NOT config_manager.get_xxx(user_uuid) or config_manager.get_xxx(param, user_uuid)

patterns_to_fix = [
    # Methods with no parameters
    (r'config_manager\.(get_\w+|add_\w+|update_\w+|remove_\w+|set_\w+|save_\w+)\(\)', 
     r'config_manager.\1(user_uuid)'),
    
    # Methods with one parameter that's not user_uuid
    (r'config_manager\.(get_\w+|add_\w+|update_\w+|remove_\w+|set_\w+|save_\w+)\(([^)]+?)\)(?!\s*#.*user_uuid)',
     lambda m: f'config_manager.{m.group(1)}({m.group(2)}, user_uuid)' if 'user_uuid' not in m.group(2) else m.group(0)),
]

changes = 0
for pattern, replacement in patterns_to_fix:
    if callable(replacement):
        new_content = re.sub(pattern, replacement, content)
    else:
        new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        changes += re.subn(pattern, replacement, content)[1]
        content = new_content

print(f"Made {changes} replacements")

# Save if user confirms
response = input(f"Apply {changes} changes to rest_routes.py? (y/n): ")
if response.lower() == 'y':
    with open('src/trusted_data_agent/api/rest_routes.py', 'w') as f:
        f.write(content)
    print("Changes applied!")
else:
    print("Changes NOT applied")
