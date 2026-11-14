import ast
import sys
from pathlib import Path


def get_model_imports_from_file(file_path):
    """Parse a Python file and return a set of individual model import statements."""
    try:
        with open(file_path, encoding="utf-8") as f:
            node = ast.parse(f.read(), filename=str(file_path))
    except Exception:
        return set()

    imports = set()

    # Common standard/third-party libraries to filter out
    ignore_modules = {
        "pytest",
        "unittest",
        "typing",
        "datetime",
        "sqlalchemy",
        "pydantic",
        "uuid",
        "enum",
        "mock",
        "factory",
    }

    for n in node.body:
        if isinstance(n, ast.ImportFrom):
            module = n.module if n.module else "LOCAL"

            # Skip if it's coming from a known non-app module
            base_module = module.split(".")[0]
            if base_module in ignore_modules:
                continue

            for alias in n.names:
                # Capture uppercase imports (standard Python convention for Classes/Models)
                if alias.name[0].isupper():
                    imports.add(f"from {module} import {alias.name}")

    return imports


def generate_consolidated_map(target_directory):
    target_path = Path(target_directory)

    if not target_path.is_dir():
        print(f"Error: Directory '{target_directory}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print("# Pilot for Trades Consolidated Model Imports\n")
    print(f"**Source Directory:** `{target_path.resolve()}`\n")
    print(
        "*Note: This is a deduplicated list of all application models imported across the test suite.*\n"
    )

    all_imports = set()
    py_files = sorted(target_path.rglob("*.py"))

    for file_path in py_files:
        # Scan test files, factories, and fixtures
        is_test_file = (
            file_path.name.startswith("test_")
            or file_path.name == "conftest.py"
            or "factory" in file_path.name.lower()
            or "fixture" in file_path.name.lower()
        )

        if is_test_file:
            all_imports.update(get_model_imports_from_file(file_path))

    # Print the clean, sorted, deduplicated list
    for imp in sorted(all_imports):
        print(f"- `{imp}`")


if __name__ == "__main__":
    # Default to the 'tests' directory if no argument is provided
    directory_to_scan = sys.argv[1] if len(sys.argv) > 1 else "tests"
    generate_consolidated_map(directory_to_scan)
