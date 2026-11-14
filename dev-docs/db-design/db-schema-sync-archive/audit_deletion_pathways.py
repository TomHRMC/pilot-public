import json

json_file = "pilot-db-schema-v2.6h.json"
output_file = "audit_deletion_pathways.json"

with open(json_file, "r", encoding="utf-8") as f:
    schema = json.load(f)

tables = schema.get("tables", {})

soft_delete_tables = []
hard_delete_tables = []
deletion_rules = {
    "CASCADE": [],
    "RESTRICT": [],
    "SET_NULL": [],
    "NO_ACTION_OR_DEFAULT": [],
}

# Tables that generally should NEVER be hard-deleted or cascaded
financial_audit_keywords = [
    "invoice",
    "payment",
    "ledger",
    "subscription",
    "usage",
    "audit",
    "quote",
]
risky_cascades = []

for table_name, table_data in tables.items():
    columns = table_data.get("columns", {})

    # 1. Determine Soft vs Hard Delete capability
    has_soft_delete = "is_active" in columns or "deleted_at" in columns
    if has_soft_delete:
        soft_delete_tables.append(table_name)
    else:
        hard_delete_tables.append(table_name)

    # 2. Analyze Foreign Key behaviors
    for fk in table_data.get("foreign_keys", []):
        # Handle variations in JSON naming ('on_delete' vs 'ondelete' vs 'definition')
        on_delete_rule = fk.get("on_delete") or fk.get("ondelete")

        # If it's not explicitly pulled out, try to find it in the raw definition string
        if not on_delete_rule and "definition" in fk:
            def_str = fk["definition"].upper()
            if "ON DELETE CASCADE" in def_str:
                on_delete_rule = "CASCADE"
            elif "ON DELETE RESTRICT" in def_str:
                on_delete_rule = "RESTRICT"
            elif "ON DELETE SET NULL" in def_str:
                on_delete_rule = "SET NULL"

        rule_category = (
            on_delete_rule.upper() if on_delete_rule else "NO_ACTION_OR_DEFAULT"
        )

        fk_info = {
            "table": table_name,
            "fk_name": fk.get("name"),
            "columns": fk.get("columns"),
            "references": fk.get("ref_table"),
        }

        if rule_category == "CASCADE":
            deletion_rules["CASCADE"].append(fk_info)
            # Check for risky cascades on financial/audit tables
            if any(
                keyword in table_name.lower() for keyword in financial_audit_keywords
            ):
                risky_cascades.append(fk_info)
        elif rule_category == "RESTRICT":
            deletion_rules["RESTRICT"].append(fk_info)
        elif rule_category in ["SET NULL", "SET_NULL"]:
            deletion_rules["SET_NULL"].append(fk_info)
        else:
            deletion_rules["NO_ACTION_OR_DEFAULT"].append(fk_info)

# Prepare Output
output_data = {
    "summary": {
        "total_tables": len(tables),
        "tables_with_soft_delete": len(soft_delete_tables),
        "tables_without_soft_delete": len(hard_delete_tables),
        "total_fks_analyzed": sum(
            len(v) for k, v in deletion_rules.items() if k != "risky_cascades"
        ),
        "fk_rules": {
            "CASCADE": len(deletion_rules["CASCADE"]),
            "RESTRICT": len(deletion_rules["RESTRICT"]),
            "SET_NULL": len(deletion_rules["SET_NULL"]),
            "NO_ACTION_OR_DEFAULT": len(deletion_rules["NO_ACTION_OR_DEFAULT"]),
        },
        "CRITICAL_risky_financial_cascades": len(risky_cascades),
    },
    "critical_risks": risky_cascades,
    "soft_delete_tables": sorted(soft_delete_tables),
    "hard_delete_tables": sorted(hard_delete_tables),
    "detailed_fk_rules": deletion_rules,
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print(f"📊 Scanned {len(tables)} tables for deletion pathways.")
print(f"🛡️ Found {len(soft_delete_tables)} tables with soft-delete capabilities.")
print(
    f"⚠️ Found {len(risky_cascades)} potentially dangerous CASCADE rules on financial/audit tables!"
)
print(f"📁 Full audit results saved to '{output_file}'")
