"""
seed_e2e_db.py — Seed pilot_e2e_db with reference + test data (Step 2 of E2E setup).

Runs all seed scripts (Groups A → B → C → D) against pilot_e2e_db.
The schema must already be applied before running this script (Step 1).

Two-step E2E DB setup:
  Step 1: Apply schema + stamp alembic
    python tests/e2e/init_e2e_schema.py /tmp/pilot_dev_schema.sql

  Step 2: Seed all data (this script)
    DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db \\
    SMS_CARRIER=mock ENVIRONMENT=e2e \\
    python tests/e2e/seed_e2e_db.py

Why not alembic upgrade head:
  The migration chain was built against a dev DB that already had reference data
  when migrations ran. Running from a blank DB fails because migrations embed
  data INSERTs that reference lookup rows not yet seeded. The schema-dump approach
  avoids this by restoring the current schema state directly.

SAFETY RULE: This script ONLY writes to the database specified in DATABASE_URL.
It will refuse to run if DATABASE_URL points to pilot_dev or pilot (the dev DB).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Guard: never run against the dev database
_db_url = os.environ.get("DATABASE_URL", "")
_forbidden = ["pilot_dev", "/pilot", "pilot_user"]
if any(f in _db_url for f in _forbidden) and "pilot_e2e_db" not in _db_url:
    print(
        "ERROR: DATABASE_URL appears to point at the dev database.\n"
        f"       DATABASE_URL={_db_url}\n"
        "       Refusing to seed. Set DATABASE_URL to pilot_e2e_db (port 5433).",
        file=sys.stderr,
    )
    sys.exit(1)

# Resolve backend root (this script lives at backend/tests/e2e/seed_e2e_db.py)
BACKEND_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = BACKEND_DIR / "migrations" / "scripts"

E2E_ENV_OVERRIDE = {
    "DATABASE_URL": _db_url
    or "postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db",
    "SMS_CARRIER": "mock",
    # Note: ENVIRONMENT must be a valid pydantic-settings literal.
    # 'e2e' is not a valid value — use 'dev' so settings validates correctly.
    "ENVIRONMENT": "dev",
}


def _env() -> dict:
    """Merge the current environment with E2E overrides."""
    return {**os.environ, **E2E_ENV_OVERRIDE}


def run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command, raising on non-zero exit."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, env=_env(), cwd=str(cwd or BACKEND_DIR))
    if result.returncode != 0:
        print(
            f"ERROR: Command failed with exit code {result.returncode}", file=sys.stderr
        )
        sys.exit(result.returncode)


def main() -> None:
    print("=" * 60)
    print("=== SD-10: Seeding pilot_e2e_db ===")
    print(f"    DB: {E2E_ENV_OVERRIDE['DATABASE_URL']}")
    print("=" * 60)
    print("\n  NOTE: Schema must already be applied via init_e2e_schema.py")
    print("  Skipping alembic — running data seeds only.\n")

    # Step A: Group A — core lookup data (safe ON CONFLICT DO NOTHING)
    print("\n[1/7] Seeding Group A — core lookups (seed_core.py)...")
    run(["python", str(SCRIPTS_DIR / "seed_core.py")])

    # Step B: Group B — platform configuration
    print("\n[2/7] Seeding Group B — platform config (seed_platform.py)...")
    run(["python", str(SCRIPTS_DIR / "seed_platform.py")])

    # Step C: Group C — test tenant infrastructure
    print("\n[3/7] Seeding Group C — test tenant (seed_test_tenant.py)...")
    run(["python", str(SCRIPTS_DIR / "seed_test_tenant.py")])

    # Step D1: Group D — quote_to_cash scenario data
    print("\n[4/7] Seeding Group D — quote_to_cash scenario...")
    run(["python", str(SCRIPTS_DIR / "seed_scenario_quote_to_cash.py")])

    # Step D2: Group D — dispatch scenario data
    print("\n[5/7] Seeding Group D — dispatch scenario...")
    run(["python", str(SCRIPTS_DIR / "seed_scenario_dispatch.py")])

    # Step D3: Group D — customer_comms scenario data
    print("\n[6/7] Seeding Group D — customer_comms scenario...")
    run(["python", str(SCRIPTS_DIR / "seed_scenario_customer_comms.py")])

    # Step D4: Group D — NEC calculation scenario data (E2E-B1: W-07)
    print("\n[7/7a] Seeding Group D — NEC scenario...")
    run(["python", str(SCRIPTS_DIR / "seed_scenario_nec.py")])

    # Step D5: Group D — mobile sync scenario data (E2E-B1: W-11)
    print("\n[7/7b] Seeding Group D — mobile sync scenario...")
    run(["python", str(SCRIPTS_DIR / "seed_scenario_mobile_sync.py")])

    print("\n" + "=" * 60)
    print("=== pilot_e2e_db Seed Complete ===")
    print("=" * 60)
    print("\nReady to run E2E tests:")
    print("  python -m pytest tests/e2e/ --e2e --tb=short -q")


if __name__ == "__main__":
    main()
