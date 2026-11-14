import json
import re

json_filename = "pilot-db-schema-v2.6h.json"
sql_filename = "pilot-db-schema-dump-master.sql"
design_backup_filename = "sync_design_functions_backup.json"
sql_export_filename = "sync_physical_db_functions_export.json"

print("🔍 Starting PostgreSQL Function Extraction (Dry Run / Export Mode)...")

# ---------------------------------------------------------
# 1. Extract EXISTING functions from the master JSON file
# ---------------------------------------------------------
try:
    with open(json_filename, "r", encoding="utf-8") as f:
        schema_json = json.load(f)

    # Check if a "functions" array even exists in the JSON yet
    existing_functions = schema_json.get("functions", [])

    with open(design_backup_filename, "w", encoding="utf-8") as f:
        json.dump(existing_functions, f, indent=2)

    print(
        f"✅ Found {len(existing_functions)} functions in JSON blueprint. Saved to '{design_backup_filename}'."
    )

except FileNotFoundError:
    print(f"❌ Could not find {json_filename}!")

# ---------------------------------------------------------
# 2. Extract functions from the physical SQL dump
# ---------------------------------------------------------
try:
    with open(sql_filename, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Regex to capture: CREATE [OR REPLACE] FUNCTION name(args) ... $$ body $$ ... ;
    func_pattern = re.compile(
        r"(CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+((?:[a-zA-Z0-9_]+\.)?[a-zA-Z0-9_]+)\s*\([^)]*\).*?(?:\$[a-zA-Z0-9_]*\$).*?(?:\$[a-zA-Z0-9_]*\$)[^;]*;)",
        re.IGNORECASE | re.DOTALL,
    )

    extracted_functions = []
    for match in func_pattern.finditer(sql_content):
        full_def = match.group(1).strip()
        func_name = match.group(2).strip()

        extracted_functions.append({"name": func_name, "definition": full_def})

    with open(sql_export_filename, "w", encoding="utf-8") as f:
        json.dump(extracted_functions, f, indent=2)

    print(
        f"✅ Found {len(extracted_functions)} functions in SQL dump. Saved to '{sql_export_filename}'."
    )

except FileNotFoundError:
    print(f"❌ Could not find {sql_filename}!")

print("\n🛑 Extraction complete! The master JSON file was NOT modified.")
