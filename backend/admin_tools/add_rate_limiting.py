#!/usr/bin/env python3
"""
Script to add rate limiting decorators to API routes.

This script automatically adds:
1. Import statements for limiter and Request
2. @limiter.limit("1000/hour") decorator to POST/PATCH/PUT/DELETE routes
3. request: Request parameter to route functions

Usage:
    python admin_tools/add_rate_limiting.py
"""

import re
from pathlib import Path

# Route files to modify
ROUTE_FILES = [
    "backend/api/routes/quotes.py",
    "backend/api/routes/jobs.py",
    "backend/api/routes/contacts.py",
    "backend/api/routes/addresses.py",
    "backend/api/routes/integrations.py",
    "backend/api/routes/roles.py",
    "backend/api/routes/voice.py",
    "backend/api/routes/catalog.py",
]

# Routes to EXCLUDE from rate limiting (test endpoints, public endpoints, etc.)
EXCLUDE_PATTERNS = [
    r"/test\b",  # Test endpoints
    r"/public/",  # Public endpoints
    r"@router\.get\(",  # GET requests (read-only)
]


def should_add_rate_limit(route_decorator: str, function_def: str) -> bool:
    """Check if rate limiting should be added to this route."""
    # Skip if already has @limiter.limit
    if "@limiter.limit" in function_def:
        return False

    # Skip test endpoints
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, route_decorator):
            return False

    # Only add to POST, PATCH, PUT, DELETE
    if any(
        method in route_decorator
        for method in ["@router.post", "@router.patch", "@router.put", "@router.delete"]
    ):
        return True

    return False


def add_imports(content: str) -> str:
    """Add rate limiting imports if not already present."""
    lines = content.split("\n")

    # Check if imports already exist
    has_limiter = any("from core.rate_limit import limiter" in line for line in lines)
    has_request = any(
        "Request" in line and "from fastapi import" in line for line in lines
    )

    if has_limiter and has_request:
        return content  # Already has imports

    # Find the fastapi import line
    for i, line in enumerate(lines):
        if line.startswith("from fastapi import"):
            # Add Request if not present
            if not has_request and "Request" not in line:
                # Add Request to existing import
                lines[i] = (
                    line.rstrip(",") + ", Request"
                    if not line.endswith(",")
                    else line + " Request"
                )

            # Add rate_limit import after core imports
            if not has_limiter:
                # Find last core.* import
                core_import_idx = i
                for j in range(i, len(lines)):
                    if lines[j].startswith("from core."):
                        core_import_idx = j
                    elif lines[j].startswith("from api.") or lines[j].startswith(
                        "from fastapi"
                    ):
                        break

                # Insert rate_limit import
                lines.insert(core_import_idx + 1, "from core.rate_limit import limiter")

            break

    return "\n".join(lines)


def add_rate_limiting_to_route(content: str) -> tuple[str, int]:
    """Add rate limiting decorator and Request parameter to routes."""
    lines = content.split("\n")
    modified_count = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for @router.post/patch/put/delete decorators
        if line.strip().startswith("@router.") and any(
            method in line for method in [".post(", ".patch(", ".put(", ".delete("]
        ):
            # Get the full decorator and function definition
            decorator_start = i

            # Find function definition (may be multiple lines after decorator)
            func_def_idx = i + 1
            while func_def_idx < len(lines) and not lines[
                func_def_idx
            ].strip().startswith("def "):
                func_def_idx += 1

            if func_def_idx >= len(lines):
                i += 1
                continue

            # Get lines from decorator to function start
            route_section = "\n".join(lines[decorator_start : func_def_idx + 1])

            # Check if we should add rate limiting
            if should_add_rate_limit(lines[decorator_start], route_section):
                # Insert @limiter.limit decorator before function def
                lines.insert(func_def_idx, '@limiter.limit("1000/hour")')

                # Add request: Request parameter
                func_line = lines[func_def_idx + 1]
                if "def " in func_line and "(" in func_line:
                    # Add request parameter as first arg after opening paren
                    func_line = func_line.replace("(", "(request: Request, ", 1)
                    # Handle case where function has no params
                    func_line = func_line.replace(
                        "(request: Request, )", "(request: Request)"
                    )
                    lines[func_def_idx + 1] = func_line
                    modified_count += 1

                i = func_def_idx + 2  # Skip past the modified function
            else:
                i = func_def_idx + 1
        else:
            i += 1

    return "\n".join(lines), modified_count


def process_file(filepath: str) -> None:
    """Process a single route file."""
    path = Path(filepath)

    if not path.exists():
        print(f"⚠️  File not found: {filepath}")
        return

    print(f"\n📝 Processing {filepath}...")

    # Read file
    content = path.read_text()

    # Add imports
    content = add_imports(content)

    # Add rate limiting to routes
    content, count = add_rate_limiting_to_route(content)

    # Write back
    path.write_text(content)

    print(f"✅ Modified {count} routes in {filepath}")


def main():
    """Main execution."""
    print("🚀 Adding rate limiting to API routes...")
    print("=" * 60)

    total_modified = 0
    for filepath in ROUTE_FILES:
        try:
            process_file(filepath)
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")

    print("\n" + "=" * 60)
    print("✅ Rate limiting setup complete!")
    print("\nNext steps:")
    print("1. Review the changes in each file")
    print("2. Run: cd backend && python -m pytest tests/test_rate_limiting.py")
    print("3. Fix any import or syntax errors")


if __name__ == "__main__":
    main()
