"""
seed_qa_db.py — QA database orchestrator (DB-MGMT-1, design §F.3).

Orchestrates Groups A→B→C→D with **all 8** scenario scripts against a QA
target database. QA = full relational density for Tom's beta testing
(E2E stays at the 5 cp-covered scenarios).

Propagates ``SEED_ENV=qa`` + ``DATABASE_URL`` to all child seed scripts.

Usage:
    DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilot_qa_scratch \\
    python migrations/scripts/seed_qa_db.py

Targets a local ``pilot_qa`` DB today; Phase 2 QA RDS via tunnel with zero
code change (URL-only). See design §G-4: "qa is a data profile, not a location."
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = BACKEND_DIR / "migrations" / "scripts"

# Guard: never run against the dev database
_db_url = os.environ.get("DATABASE_URL", "")
_forbidden = ["pilot_dev", "pilot_user"]
if any(f in _db_url for f in _forbidden) and "pilot_qa" not in _db_url:
    print(
        "ERROR: DATABASE_URL appears to point at the dev database.\n"
        f"       DATABASE_URL={_db_url}\n"
        "       Refusing to seed. Set DATABASE_URL to a pilot_qa* database.",
        file=sys.stderr,
    )
    sys.exit(1)

QA_ENV_OVERRIDE = {
    "DATABASE_URL": _db_url,
    "SEED_ENV": "qa",
    "SMS_CARRIER": "mock",
    # Note: ENVIRONMENT must be a valid pydantic-settings literal.
    # 'qa' is valid per core/config.py line 57.
    "ENVIRONMENT": "qa",
}


def _env() -> dict:
    """Merge the current environment with QA overrides."""
    return {**os.environ, **QA_ENV_OVERRIDE}


def _run(cmd: list[str], cwd: Path | None = None) -> None:
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
    print("=== DB-MGMT-1: Seeding QA database ===")
    print(f"    DB: {QA_ENV_OVERRIDE['DATABASE_URL']}")
    print(f"    SEED_ENV: {QA_ENV_OVERRIDE['SEED_ENV']}")
    print("=" * 60)
    print("\n  NOTE: Schema must already be applied via provision_schema.py --env qa")
    print("  Skipping alembic — running data seeds only.\n")

    # Step A: Group A — core lookup data
    print("\n[1/13] Seeding Group A — core lookups (seed_core.py)...")
    _run(["python", str(SCRIPTS_DIR / "seed_core.py"), "--env", "qa"])

    # Step B: Group B — platform configuration
    print("\n[2/13] Seeding Group B — platform config (seed_platform.py)...")
    _run(["python", str(SCRIPTS_DIR / "seed_platform.py"), "--env", "qa"])

    # Step C: Group C — test tenant infrastructure
    print("\n[3/13] Seeding Group C — test tenant (seed_test_tenant.py)...")
    _run(["python", str(SCRIPTS_DIR / "seed_test_tenant.py"), "--env", "qa"])

    # Step C2: Group C — second tenant (SD-9: tenant isolation validation)
    print("\n[4/13] Seeding Group C — second tenant (seed_second_tenant.py)...")
    _run(["python", str(SCRIPTS_DIR / "seed_second_tenant.py"), "--env", "qa"])

    # Step D: Group D — all 9 scenario scripts (8 universal + voice_ai)
    scenarios = [
        ("seed_scenario_quote_to_cash.py", "quote_to_cash"),
        ("seed_scenario_dispatch.py", "dispatch"),
        ("seed_scenario_customer_comms.py", "customer_comms"),
        ("seed_scenario_reporting.py", "reporting"),
        ("seed_scenario_supplier_catalog.py", "supplier_catalog"),
        ("seed_scenario_nec.py", "nec"),
        ("seed_scenario_mobile_sync.py", "mobile_sync"),
        ("seed_scenario_notifications.py", "notifications"),
        ("seed_scenario_voice_ai.py", "voice_ai"),
    ]
    for i, (script, label) in enumerate(scenarios, start=5):
        print(f"\n[{i}/13] Seeding Group D — {label} scenario...")
        _run(["python", str(SCRIPTS_DIR / script), "--env", "qa"])

    # Step E: tenant_site scenario (C-B16)
    print("\n[13/13] Seeding Group D — tenant_site scenario...")
    _run(["python", str(SCRIPTS_DIR / "seed_scenario_tenant_site.py"), "--env", "qa"])

    print("\n" + "=" * 60)
    print("=== QA Database Seed Complete ===")
    print("=" * 60)
    print("\nVerify with:")
    print("  python migrations/scripts/seed_core.py --env qa --mode inspect")
    print("  python migrations/scripts/seed_platform.py --env qa --mode inspect")


if __name__ == "__main__":
    main()
