#!/usr/bin/env python3
import argparse
import json
import os
import sys

DEFAULT_SCHEMA_PATH = "../dev-docs/db-design/pilot-db-schema-v2.6h.json"


def load_schema(filepath):
    if not os.path.exists(filepath):
        print(f"Error: Schema file not found at '{filepath}'")
        sys.exit(1)
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def save_schema(filepath, schema_data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(schema_data, f, indent=2)
    print(f"Success: Schema changes saved to '{filepath}'.")


def get_value(payload_path, direct_value):
    """Loads JSON from a file, or parses a direct string value."""
    if direct_value is not None:
        try:
            return json.loads(direct_value)
        except json.JSONDecodeError:
            return direct_value

    if not payload_path:
        print(
            "Error: Must provide either --payload (file path) or --value (raw value)."
        )
        sys.exit(1)

    if not os.path.exists(payload_path):
        print(f"Error: Payload file not found at '{payload_path}'")
        sys.exit(1)

    with open(payload_path, encoding="utf-8") as f:
        return json.load(f)


def navigate_path(data, path_str, create_missing=False):
    """
    Traverses a dot-separated path (e.g., 'tables.user.columns.email').
    Returns the parent dictionary/list and the final key/index to target.
    """
    if not path_str:
        return None, None

    keys = path_str.split(".")
    current = data

    for i, key in enumerate(keys[:-1]):
        if key not in current:
            if create_missing:
                current[key] = {}
            else:
                print(f"Error: Path '{'.'.join(keys[: i + 1])}' not found.")
                sys.exit(1)

        current = current[key]
        if not isinstance(current, dict):
            print(f"Error: '{key}' is not a dictionary, cannot traverse further.")
            sys.exit(1)

    return current, keys[-1]


# --- COMMANDS ---


def cmd_get(args):
    schema = load_schema(args.file)
    if not args.path:
        print(json.dumps(schema, indent=2))
        return

    parent, key = navigate_path(schema, args.path)
    if key not in parent:
        print(f"Error: Key '{key}' not found at path '{args.path}'.")
        sys.exit(1)

    target = parent[key]
    print(json.dumps(target, indent=2))


def cmd_set(args):
    schema = load_schema(args.file)
    val = get_value(args.payload, args.value)

    if not args.path:
        print("Error: --path is required for set.")
        sys.exit(1)

    parent, key = navigate_path(schema, args.path, create_missing=True)
    parent[key] = val
    save_schema(args.file, schema)
    print(f"Set '{args.path}' successfully.")


def cmd_delete(args):
    schema = load_schema(args.file)
    parent, key = navigate_path(schema, args.path)

    if key in parent:
        del parent[key]
        save_schema(args.file, schema)
        print(f"Deleted '{args.path}' successfully.")
    else:
        print(f"Error: Key '{key}' not found.")
        sys.exit(1)


def cmd_array_append(args):
    schema = load_schema(args.file)
    val = get_value(args.payload, args.value)
    parent, key = navigate_path(schema, args.path, create_missing=True)

    if key not in parent:
        parent[key] = []

    if not isinstance(parent[key], list):
        print(f"Error: Target '{args.path}' is not an array.")
        sys.exit(1)

    parent[key].append(val)
    save_schema(args.file, schema)
    print(f"Appended item to '{args.path}'. Total items: {len(parent[key])}")


def cmd_array_remove(args):
    schema = load_schema(args.file)
    parent, key = navigate_path(schema, args.path)

    if key not in parent or not isinstance(parent[key], list):
        print(f"Error: Target array '{args.path}' not found or is not a list.")
        sys.exit(1)

    arr = parent[key]
    initial_len = len(arr)

    parent[key] = [
        item
        for item in arr
        if not (
            isinstance(item, dict)
            and str(item.get(args.match_key)) == str(args.match_value)
        )
    ]

    if len(parent[key]) == initial_len:
        print(
            f"Warning: No item found in '{args.path}' where {args.match_key} == '{args.match_value}'."
        )
    else:
        save_schema(args.file, schema)
        print(
            f"Removed item(s) from '{args.path}'. Remaining items: {len(parent[key])}"
        )


def cmd_array_update(args):
    schema = load_schema(args.file)
    val = get_value(args.payload, args.value)
    parent, key = navigate_path(schema, args.path)

    if key not in parent or not isinstance(parent[key], list):
        print(f"Error: Target array '{args.path}' not found or is not a list.")
        sys.exit(1)

    arr = parent[key]
    updated = False

    for i, item in enumerate(arr):
        if isinstance(item, dict) and str(item.get(args.match_key)) == str(
            args.match_value
        ):
            arr[i] = val
            updated = True
            print(f"Updated item at index {i} in '{args.path}'.")

    if not updated:
        print(
            f"Warning: No item found in '{args.path}' where {args.match_key} == '{args.match_value}'."
        )
    else:
        save_schema(args.file, schema)


def main():
    help_epilog = """
EXAMPLES:

  1. Get/View Data:
     python schema_manager.py get --path tables.user.columns.email
     python schema_manager.py get --path schemas.audit.tables.event
  
  2. Set/Update a Value (Dictionaries & Strings):
     python schema_manager.py set --path version --value "v2.7a"
     python schema_manager.py set --path tables.user.columns.email --payload updated_col.json
  
  3. Update a Foreign Key or Global Function in-place (Arrays):
     python schema_manager.py array-update --path tables.user.foreign_keys --match-key name --match-value fk_user_role --payload new_fk.json
     python schema_manager.py array-update --path functions --match-key name --match-value log_changes --payload updated_func.json

  4. Add items to an Array:
     python schema_manager.py array-append --path functions --payload new_func.json
     python schema_manager.py array-append --path tables.user.indexes --payload new_index.json
    """

    parser = argparse.ArgumentParser(
        description="Universal Schema JSON Manager",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=help_epilog,
    )

    parser.add_argument(
        "--file", default=DEFAULT_SCHEMA_PATH, help="Path to schema JSON."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # GET
    p_get = subparsers.add_parser("get", help="Print an object at a specific path.")
    p_get.add_argument("--path", help="Dot-separated path (e.g., tables.user.columns)")

    # SET
    p_set = subparsers.add_parser(
        "set", help="Create or overwrite an object at a path."
    )
    p_set.add_argument(
        "--path", required=True, help="Path to set (e.g., tables.user.columns.email)"
    )
    p_set.add_argument("--payload", help="JSON file containing the new object.")
    p_set.add_argument("--value", help="Direct string/number value.")

    # DELETE
    p_del = subparsers.add_parser("delete", help="Remove a dictionary key.")
    p_del.add_argument("--path", required=True, help="Path to remove.")

    # ARRAY APPEND
    p_arr_app = subparsers.add_parser("array-append", help="Add an item to an array.")
    p_arr_app.add_argument(
        "--path", required=True, help="Path to the array (e.g., functions)."
    )
    p_arr_app.add_argument("--payload", help="JSON file containing the new array item.")
    p_arr_app.add_argument("--value", help="Direct string/number value.")

    # ARRAY REMOVE
    p_arr_rm = subparsers.add_parser(
        "array-remove", help="Remove an item from an array."
    )
    p_arr_rm.add_argument("--path", required=True)
    p_arr_rm.add_argument(
        "--match-key", required=True, help="Key to match (e.g., name)."
    )
    p_arr_rm.add_argument(
        "--match-value", required=True, help="Value to match (e.g., log_changes)."
    )

    # ARRAY UPDATE (In-Place)
    p_arr_up = subparsers.add_parser(
        "array-update", help="Update an item in an array in-place."
    )
    p_arr_up.add_argument("--path", required=True)
    p_arr_up.add_argument("--match-key", required=True)
    p_arr_up.add_argument("--match-value", required=True)
    p_arr_up.add_argument(
        "--payload", help="JSON file containing the replacement item."
    )
    p_arr_up.add_argument("--value", help="Direct string/number replacement value.")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # Routing
    commands = {
        "get": cmd_get,
        "set": cmd_set,
        "delete": cmd_delete,
        "array-append": cmd_array_append,
        "array-remove": cmd_array_remove,
        "array-update": cmd_array_update,
    }

    if args.command in commands:
        commands[args.command](args)


if __name__ == "__main__":
    main()
