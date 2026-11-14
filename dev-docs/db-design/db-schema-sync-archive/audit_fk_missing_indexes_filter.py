import json

input_file = "audit_fk_missing_indexes.json"  # Make sure this matches your filename!
output_file = "audit_fk_missing_indexes_filter_output.json"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

tables = data.get("tables", {})
filtered_tables = {}
ignored_columns = {"created_by", "updated_by"}

structural_missing_count = 0

for table_name, fks in tables.items():
    filtered_fks = []
    for fk in fks:
        # Check if the columns in this FK are purely audit columns
        cols = set(fk.get("columns", []))
        if not cols.issubset(ignored_columns):
            filtered_fks.append(fk)
            structural_missing_count += 1

    if filtered_fks:
        filtered_tables[table_name] = filtered_fks

# Update summary stats
original_missing = data["summary"]["missing_indexes"]
audit_indexes_ignored = original_missing - structural_missing_count

output_data = {
    "summary": {
        "total_foreign_keys_in_db": data["summary"]["total_foreign_keys"],
        "properly_indexed_fks": data["summary"]["indexed_foreign_keys"],
        "audit_fks_ignored": audit_indexes_ignored,
        "CRITICAL_missing_structural_indexes": structural_missing_count,
        "tables_needing_indexes": len(filtered_tables),
    },
    "tables": filtered_tables,
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print(f"🧹 Filtered out {audit_indexes_ignored} audit-only Foreign Keys.")
print(
    f"🎯 Found {structural_missing_count} critical structural Foreign Keys missing indexes across {len(filtered_tables)} tables."
)
print(f"📁 Filtered results saved to '{output_file}'")
