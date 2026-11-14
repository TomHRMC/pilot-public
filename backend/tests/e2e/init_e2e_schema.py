"""
init_e2e_schema.py — Apply dev DB schema dump to pilot_e2e_db and stamp alembic.

**DB-MGMT-1**: This script is now a thin wrapper that delegates to
``migrations/scripts/provision_schema.py --env e2e``. The existing CLI
signature (positional dump path + ``--schema-dump`` flag) is preserved so
all existing docs and muscle-memory commands continue to work.

Step 1 of E2E DB setup. Run ONCE after wiping the E2E DB volume, or whenever
the schema changes (new migrations have been applied to pilot_dev).

Usage:
    # Generate schema dump from dev DB first:
    pg_dump -h localhost -p 5432 -U pilot -d pilot_dev --schema-only \\
        -f /tmp/pilot_dev_schema.sql

    # Apply to E2E DB (requires E2E container to be running):
    cd <repo>/backend
    source .venv/bin/activate
    DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5434/pilot_e2e_db \\
    python tests/e2e/init_e2e_schema.py /tmp/pilot_dev_schema.sql

    # Or using --schema-dump flag:
    python tests/e2e/init_e2e_schema.py --schema-dump /tmp/pilot_dev_schema.sql

SAFETY: Refuses to run against pilot_dev or pilot (dev DB).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Resolve backend root
BACKEND_DIR = Path(__file__).parent.parent.parent

# ── Guard: never run against the dev database ─────────────────────────────────
_db_url = os.environ.get("DATABASE_URL", "")
_forbidden = ["pilot_dev", "/pilot", "pilot_user"]
if any(f in _db_url for f in _forbidden) and "pilot_e2e_db" not in _db_url:
    print(
        "ERROR: DATABASE_URL appears to point at the dev database.\n"
        f"       DATABASE_URL={_db_url}\n"
        "       Refusing to apply schema. Set DATABASE_URL to pilot_e2e_db (port 5434).",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="init_e2e_schema.py — Apply dev DB schema dump to pilot_e2e_db and stamp alembic."
    )
    parser.add_argument(
        "schema_dump",
        nargs="?",
        default=None,
        help="Path to schema dump SQL file (default: /tmp/pilot_dev_schema.sql)",
    )
    parser.add_argument(
        "--schema-dump",
        dest="schema_dump_flag",
        default=None,
        help="Path to schema dump SQL file (alternate flag form)",
    )
    args = parser.parse_args()

    # Resolve schema dump path (positional or flag, with fallback default)
    schema_path = (
        args.schema_dump or args.schema_dump_flag or "/tmp/pilot_dev_schema.sql"
    )

    # Delegate to provision_schema.py --env e2e
    provision_script = BACKEND_DIR / "migrations" / "scripts" / "provision_schema.py"
    cmd = [
        "python",
        str(provision_script),
        "--env",
        "e2e",
        "--schema-dump",
        str(schema_path),
    ]

    print("=" * 60)
    print("=== init_e2e_schema: delegating to provision_schema.py --env e2e ===")
    print(f"    Dump: {schema_path}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=str(BACKEND_DIR))
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
