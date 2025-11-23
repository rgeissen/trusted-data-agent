#!/usr/bin/env python3
"""
Script to add user_uuid parameter to remaining config_manager calls in rest_routes.py
"""

import re

file_path = '/Users/rainergeissendoerfer/my_private_code/trusted-data-agent/src/trusted_data_agent/api/rest_routes.py'

# Read the file
with open(file_path, 'r') as f:
    lines = f.readlines()

changes_made = []
new_lines = []

for line_num, line in enumerate(lines, 1):
    original_line = line
    
    # Skip lines that already have user_uuid in the call
    if 'user_uuid)' in line or '# user_uuid' in line:
        new_lines.append(line)
        continue
    
    # Pattern 1: Methods with no parameters - e.g., config_manager.get_profiles()
    match = re.search(r'(config_manager\.(get_\w+|add_\w+|update_\w+|remove_\w+|set_\w+|save_\w+))\(\)', line)
    if match:
        line = line.replace(f'{match.group(1)}()', f'{match.group(1)}(user_uuid)')
        if line != original_line:
            changes_made.append((line_num, original_line.strip(), line.strip()))
    
    # Pattern 2: Methods with one parameter
    if line != original_line:  # Skip if already modified
        new_lines.append(line)
        continue
        
    match2 = re.search(r'(config_manager\.(get_\w+|add_\w+|update_\w+|remove_\w+|set_\w+|save_\w+))\(([^)]+)\)', line)
    if match2:
        method_call = match2.group(1)
        params = match2.group(3)
        # Only add user_uuid if it's not already there
        if 'user_uuid' not in params:
            line = line.replace(f'{method_call}({params})', f'{method_call}({params}, user_uuid)')
            if line != original_line:
                changes_made.append((line_num, original_line.strip(), line.strip()))
    
    new_lines.append(line)

# Show changes
print(f"Found {len(changes_made)} changes to make:\n")
for line_num, old, new in changes_made[:10]:  # Show first 10
    print(f"Line {line_num}:")
    print(f"  OLD: {old}")
    print(f"  NEW: {new}")
    print()

if len(changes_made) > 10:
    print(f"... and {len(changes_made) - 10} more changes\n")

# Apply changes
with open(file_path, 'w') as f:
    f.writelines(new_lines)

print(f"\n✅ Applied {len(changes_made)} changes to {file_path}")
