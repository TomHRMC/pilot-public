import json


def get_structure(data, depth=0, max_depth=4):
    """Recursively maps the structure of a JSON object."""
    if depth > max_depth:
        return "..."
    if isinstance(data, dict):
        return {k: get_structure(v, depth + 1, max_depth) for k, v in data.items()}
    elif isinstance(data, list):
        if len(data) > 0:
            # Only look at the first item in a list to get the structure pattern
            return [get_structure(data[0], depth + 1, max_depth)]
        return []
    else:
        return type(data).__name__


def main():
    json_file = "pilot-db-schema-v2.6h.json"  # <-- UPDATE THIS with your filename

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        structure = get_structure(data)
        print("--- JSON STRUCTURAL BLUEPRINT ---")
        print(json.dumps(structure, indent=2))

    except Exception as e:
        print(f"Error reading JSON: {e}")


if __name__ == "__main__":
    main()
