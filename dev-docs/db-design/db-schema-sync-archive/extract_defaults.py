import json
import sys
from pathlib import Path


def extract_schema_defaults(json_filename):
    file_path = Path(json_filename)

    if not file_path.exists():
        print(f"Error: Could not find '{json_filename}' in the current directory.")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    print(f"Scanning {json_filename} for default values...\n")

    print(f"| {'Table Name':<30} | {'Column Name':<30} | {'Expected Default':<25} |")
    print(f"|{'-' * 32}|{'-' * 32}|{'-' * 27}|")

    total_defaults = 0

    # FIX: Step into the "tables" dictionary
    tables = schema.get("tables", {})

    for table_name, table_data in tables.items():
        if isinstance(table_data, dict) and "columns" in table_data:
            columns = table_data["columns"]

            for col_name, col_attrs in columns.items():
                # Skip the standard timestamps so we only see business logic defaults
                if col_name in ("created_at", "updated_at"):
                    continue

                if "default" in col_attrs:
                    default_value = str(col_attrs["default"])
                    print(
                        f"| {table_name:<30} | {col_name:<30} | {default_value:<25} |"
                    )
                    total_defaults += 1

    print(f"\nTotal business fields requiring a physical DB default: {total_defaults}")


if __name__ == "__main__":
    target_json_file = "pilot-db-schema-v2.6h.json"
    extract_schema_defaults(target_json_file)
