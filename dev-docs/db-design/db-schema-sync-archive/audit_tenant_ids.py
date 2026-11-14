import json

json_filename = "pilot-db-schema-v2.6h.json"
output_filename = "audit_tenant_ids.json"

with open(json_filename, "r", encoding="utf-8") as f:
    schema = json.load(f)

missing_tenant_id = []
has_tenant_id = []

# Scan public tables
for table_name, table_data in schema.get("tables", {}).items():
    if "tenant_id" in table_data.get("columns", {}):
        has_tenant_id.append(table_name)
    else:
        missing_tenant_id.append(table_name)

# Prepare the data payload
output_data = {
    "summary": {
        "has_tenant_id_count": len(has_tenant_id),
        "missing_tenant_id_count": len(missing_tenant_id),
    },
    "tables_with_tenant_id": sorted(has_tenant_id),
    "tables_missing_tenant_id": sorted(missing_tenant_id),
}

# Write to JSON file
with open(output_filename, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print(f"✅ Found {len(has_tenant_id)} tables WITH a tenant_id.")
print(f"⚠️ Found {len(missing_tenant_id)} tables MISSING a tenant_id.")
print(f"📁 Full audit results saved to '{output_filename}'")
