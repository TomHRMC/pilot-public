import json
import re

json_filename = "pilot-db-schema-v2.6h.json"
sql_filename = "pilot-db-schema-dump-master.sql"
design_backup_filename = "sync_design_triggers_backup.json"
sql_export_filename = "sync_physical_db_triggers_export.json"

# 1. Load JSON
with open(json_filename, "r", encoding="utf-8") as f:
    schema_json = json.load(f)

# 2. Extract and Backup EXISTING JSON Triggers
existing_design_triggers = {}


def backup_triggers(table_dict, schema_name):
    for table_name, table_data in table_dict.items():
        full_name = f"{schema_name}.{table_name}"
        triggers = table_data.get("triggers", [])
        if triggers:
            existing_design_triggers[full_name] = triggers


backup_triggers(schema_json.get("tables", {}), "public")
for schema_name, schema_data in schema_json.get("schemas", {}).items():
    backup_triggers(schema_data.get("tables", {}), schema_name)

# Save the design backup
with open(design_backup_filename, "w", encoding="utf-8") as f:
    json.dump(existing_design_triggers, f, indent=2)
print(f"✅ Saved original JSON design triggers to '{design_backup_filename}'")

# 3. Extract Triggers from SQL Dump
sql_triggers = {}  # format: {"schema.table": [{"name": "x", "definition": "y"}]}
with open(sql_filename, "r", encoding="utf-8") as f:
    for line in f.read().split(";"):
        stmt = re.sub(r"\s+", " ", line).strip()
        trig_match = re.search(
            r'CREATE\s+TRIGGER\s+"?([a-zA-Z0-9_]+)"?\s+(.*?)\s+ON\s+(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s+(.*)',
            stmt,
            re.IGNORECASE | re.DOTALL,
        )
        if trig_match:
            trig_name = trig_match.group(1)
            schema = trig_match.group(3) or "public"
            table = trig_match.group(4)
            full_name = f"{schema}.{table}"

            if full_name not in sql_triggers:
                sql_triggers[full_name] = []

            sql_triggers[full_name].append({"name": trig_name, "definition": stmt})

# Save the physical database export
with open(sql_export_filename, "w", encoding="utf-8") as f:
    json.dump(sql_triggers, f, indent=2)
print(f"✅ Exported pure physical database triggers to '{sql_export_filename}'")


# 4. Inject Triggers into JSON tables
def inject_triggers(table_dict, schema_name):
    for table_name, table_data in table_dict.items():
        full_name = f"{schema_name}.{table_name}"
        if full_name in sql_triggers:
            # Overwrite any existing messy triggers with the ground-truth SQL triggers
            table_data["triggers"] = sql_triggers[full_name]
        else:
            # Ensure the key exists even if empty, and clear out the old bad ones
            table_data["triggers"] = []


inject_triggers(schema_json.get("tables", {}), "public")
for schema_name, schema_data in schema_json.get("schemas", {}).items():
    inject_triggers(schema_data.get("tables", {}), schema_name)

# 5. Save the Overwritten JSON
with open(json_filename, "w", encoding="utf-8") as f:
    json.dump(schema_json, f, indent=2)

print(
    f"✅ Successfully injected all physical database triggers into '{json_filename}'!"
)
