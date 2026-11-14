import ast
import sys
from pathlib import Path


def classify_classes(file_path):
    """Returns (table_classes, non_table_classes).

    table_classes: list of (class_name, tablename_str)
        - Only SQLModel classes with table=True keyword argument
        - tablename_str is the literal __tablename__ value, or "(inherited)"

    non_table_classes: list of class_name strings
        - All other class definitions (Enums, Schemas, Mixins, Helpers, etc.)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            node = ast.parse(f.read(), filename=str(file_path))
    except Exception:
        return [], []

    table_classes = []  # list of (class_name, tablename_str)
    other_classes = []  # list of class_name strings

    for n in node.body:
        if not isinstance(n, ast.ClassDef):
            continue

        # Check for table=True keyword in class definition
        is_table = any(
            kw.arg == "table"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
            for kw in n.keywords
        )

        if is_table:
            # Find __tablename__ assignment in class body
            tablename = "(inherited)"
            for stmt in n.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and any(
                        isinstance(t, ast.Name) and t.id == "__tablename__"
                        for t in stmt.targets
                    )
                    and isinstance(stmt.value, ast.Constant)
                ):
                    tablename = stmt.value.value
                    break
            table_classes.append((n.name, tablename))
        else:
            other_classes.append(n.name)

    return table_classes, other_classes


def generate_map(target_directory):
    target_path = Path(target_directory)

    if not target_path.is_dir():
        print(f"Error: Directory '{target_directory}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print("# Pilot for Trades Database Models Map\n")
    print(f"**Source Directory:** `{target_path.resolve()}`\n")
    print(
        "> **Key**: Only **DB Tables** entries are queryable via `select()`. "
        "Never use `db.get()` or `select()` against Enum/Schema classes — they are not database tables.\n"
    )

    # Find all Python files recursively
    py_files = sorted(target_path.rglob("*.py"))

    for file_path in py_files:
        # Skip common non-model directories to keep the map clean
        ignored_parts = {"__pycache__", "venv", ".venv", "alembic", "tests"}
        if any(part in file_path.parts for part in ignored_parts):
            continue

        # Skip standard init files unless they actually contain classes
        if file_path.name == "__init__.py":
            table_cls, other_cls = classify_classes(file_path)
            if not table_cls and not other_cls:
                continue

        table_classes, other_classes = classify_classes(file_path)

        if not table_classes and not other_classes:
            continue

        # Create a clean relative path for the markdown header
        rel_path = file_path.relative_to(target_path)
        print(f"### `{rel_path}`\n")

        if table_classes:
            print("**DB Tables** (SQLModel `table=True` — queryable via `select()`):")
            for cls_name, tablename in table_classes:
                print(f"- `{cls_name}` → table: `{tablename}`")
            if other_classes:
                print()

        if other_classes:
            print(
                "**Enums / Schemas / Helpers** "
                "(NOT DB tables — do not use in `select()` queries):"
            )
            for cls_name in other_classes:
                print(f"- {cls_name}")

        print("\n---")  # Visual separator between files


if __name__ == "__main__":
    # Default to the current directory if no argument is provided
    directory_to_scan = sys.argv[1] if len(sys.argv) > 1 else "."
    generate_map(directory_to_scan)
