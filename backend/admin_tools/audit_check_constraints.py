#!/usr/bin/env python3
"""
Audit CHECK constraints from JSON schema vs database.
Identifies missing CHECK constraints that need to be implemented.
"""

import json
from pathlib import Path


def extract_check_constraints_from_json():
    """Parse JSON schema and extract all CHECK constraints."""
    json_path = (
        Path(__file__).parent.parent.parent
        / "dev-docs/db-design/pilot-db-schema-v2.6h.json"
    )

    with open(json_path) as f:
        schema = json.load(f)

    constraints = []

    for table_name, table_def in schema.get("tables", {}).items():
        check_constraints = table_def.get("check_constraints", [])

        for constraint in check_constraints:
            constraints.append(
                {
                    "table": table_name,
                    "name": constraint.get("name"),
                    "definition": constraint.get("definition"),
                    "description": constraint.get("description", ""),
                }
            )

    return constraints


def main():
    """Extract and display all CHECK constraints from JSON schema."""
    constraints = extract_check_constraints_from_json()

    print(f"Found {len(constraints)} CHECK constraints in JSON schema:\n")

    # Group by table
    by_table = {}
    for c in constraints:
        table = c["table"]
        if table not in by_table:
            by_table[table] = []
        by_table[table].append(c)

    for table in sorted(by_table.keys()):
        print(f"\n{'=' * 80}")
        print(f"Table: {table}")
        print("=" * 80)
        for c in by_table[table]:
            print(f"\nConstraint: {c['name']}")
            print(f"Definition: {c['definition']}")
            if c["description"]:
                print(f"Description: {c['description']}")

    # Summary by table
    print(f"\n\n{'=' * 80}")
    print("SUMMARY BY TABLE")
    print("=" * 80)
    for table in sorted(by_table.keys()):
        print(f"{table:40} {len(by_table[table])} constraints")

    print(
        f"\nTotal: {len(constraints)} CHECK constraints across {len(by_table)} tables"
    )


if __name__ == "__main__":
    main()
