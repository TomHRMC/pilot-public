import json
import re

json_file = "pilot-db-schema-v2.6h.json"
sql_file = "pilot-db-schema-dump-master.sql"

# 1. Load the JSON Blueprint
with open(json_file, "r", encoding="utf-8") as f:
    schema_json = json.load(f)

# 2. Extract the functions from the SQL dump
with open(sql_file, "r", encoding="utf-8") as f:
    sql_dump = f.read()

# Regex to find our specific cascade functions
func_pattern = re.compile(
    r"(CREATE FUNCTION public\.(cascade_soft_delete_to_[a-zA-Z_]+)\(\).*?\$\$;)",
    re.DOTALL,
)

found_functions = func_pattern.findall(sql_dump)

if "functions" not in schema_json:
    schema_json["functions"] = []

# Keep track of existing function names to avoid duplicates
existing_funcs = {f.get("name") for f in schema_json["functions"]}

added_count = 0
for full_def, func_name in found_functions:
    if func_name not in existing_funcs:
        new_func = {
            "name": func_name,
            "schema": "public",
            "language": "plpgsql",
            "returns": "trigger",
            "definition": full_def,
        }
        schema_json["functions"].append(new_func)
        print(f"✅ Added function: {func_name}")
        added_count += 1

# 3. Save back to JSON
with open(json_file, "w", encoding="utf-8") as f:
    # json.dump automatically handles escaping the \n line breaks for the SQL definitions
    json.dump(schema_json, f, indent=2)

print(
    f"\n🎉 Successfully added {added_count} functions to the JSON! Run `python schema_diff.py` to verify."
)
