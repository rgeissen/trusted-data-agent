#!/bin/bash
#
# Reload collection 3 (Fitness DB) to fix metadata
#
# This will re-import all case JSON files and apply the corrected
# metadata preparation logic that properly handles is_most_efficient values

cd "$(dirname "$0")/.."

echo "Reloading collection 3 (Fitness DB) to fix template metadata..."
conda run -n tda python3 maintenance/reload_collection.py --collection_id 3

echo "Done! Collection 3 has been reloaded with corrected metadata."
echo "The autocomplete should now show results from Fitness DB when using @FMANA tag."
