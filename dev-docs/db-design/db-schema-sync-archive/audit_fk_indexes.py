import json
import re

json_file = "pilot-db-schema-v2.6h.json"
output_file = "audit_fk_missing_indexes.json"

with open(json_file, "r", encoding="utf-8") as f:
    schema = json.load(f)


def get_index_columns(def_str):
    """Extracts column names from a CREATE INDEX statement."""
    match = re.search(r"\(([^)]+)\)", def_str)
    if not match:
        return []

    cols_str = match.group(1)
    cols = []
    for c in cols_str.split(","):
        # Clean up quotes and get just the column name (ignore ASC/DESC)
        c_clean = c.strip().replace('"', "").replace("'", "")
        first_word = c_clean.split()[0]
        cols.append(first_word)
    return cols


missing_indexes = {}
total_fks = 0
indexed_fks = 0

tables = schema.get("tables", {})

for table_name, table_data in tables.items():
    fks = table_data.get("foreign_keys", [])
    if not fks:
        continue

    # 1. Collect all explicit indexes
    table_indexes = []
    for idx in table_data.get("indexes", []):
        cols = get_index_columns(idx.get("definition", ""))
        if cols:
            table_indexes.append(cols)

    # 2. Primary Keys implicitly create indexes
    pk_cols = table_data.get("primary_key", [])
    if pk_cols:
        table_indexes.append(pk_cols)

    # 3. Unique Constraints implicitly create indexes
    for uq in table_data.get("unique", []):
        table_indexes.append(uq)

    missing_for_table = []

    # Check each Foreign Key against all available indexes
    for fk in fks:
        total_fks += 1
        fk_cols = fk.get("columns", [])

        # An index covers an FK if it STARTS WITH the exact FK columns in the exact order
        is_covered = False
        for idx_cols in table_indexes:
            if len(idx_cols) >= len(fk_cols) and idx_cols[: len(fk_cols)] == fk_cols:
                is_covered = True
                break

        if is_covered:
            indexed_fks += 1
        else:
            missing_for_table.append(
                {
                    "fk_name": fk.get("name", "unknown"),
                    "columns": fk_cols,
                    "references": fk.get("ref_table"),
                }
            )

    if missing_for_table:
        missing_indexes[table_name] = missing_for_table

# Prepare JSON Output
output_data = {
    "summary": {
        "total_foreign_keys": total_fks,
        "indexed_foreign_keys": indexed_fks,
        "missing_indexes": total_fks - indexed_fks,
        "tables_needing_indexes": len(missing_indexes),
    },
    "tables": missing_indexes,
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print(f"📊 Scanned {total_fks} Foreign Keys across the schema.")
print(f"✅ {indexed_fks} FKs are safely covered by indexes.")
print(
    f"⚠️ {total_fks - indexed_fks} FKs are MISSING indexes across {len(missing_indexes)} tables."
)
print(f"📁 Full audit results saved to '{output_file}'")
