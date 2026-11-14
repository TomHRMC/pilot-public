import json

json_filename = "pilot-db-schema-v2.6h.json"
design_file = "sync_design_functions_backup.json"
physical_file = "sync_physical_db_functions_export.json"

# 1. Load the designs and physical exports
with open(design_file, "r", encoding="utf-8") as f:
    designs = json.load(f)
with open(physical_file, "r", encoding="utf-8") as f:
    physical = json.load(f)

# Convert physical to a dictionary for easy lookup by name
# Note: Physical export just has "name" (which might include schema, e.g. "audit.log_changes")
physical_dict = {f["name"]: f["definition"] for f in physical}

# 2. Perform the Smart Merge
merged_functions = []
for func in designs:
    # Reconstruct the full name to match the physical export format
    full_name = f"{func.get('schema', 'public')}.{func['name']}"
    if func.get("schema") is None and "." in func["name"]:
        full_name = func[
            "name"
        ]  # Handle edge cases where schema is already in the name

    # Create the merged object, keeping all original metadata
    merged_func = func.copy()

    # Swap the definition for the exact database version if it exists
    if full_name in physical_dict:
        merged_func["definition"] = physical_dict[full_name]
    elif func["name"] in physical_dict:
        merged_func["definition"] = physical_dict[func["name"]]

    merged_functions.append(merged_func)

# 3. Inject back into the Master JSON
with open(json_filename, "r", encoding="utf-8") as f:
    master_json = json.load(f)

master_json["functions"] = merged_functions

with open(json_filename, "w", encoding="utf-8") as f:
    json.dump(master_json, f, indent=2)

print(
    "✅ Smart Merge complete! Your rich metadata is preserved, and the definitions are perfectly synced."
)
