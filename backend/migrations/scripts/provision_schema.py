"""
provision_schema.py — Generalized schema-restore provisioning (DB-MGMT-1, ADR-0016).

Generalizes the proven E2E schema-restore flow (``tests/e2e/init_e2e_schema.py``)
into an env-parameterized tool that provisions any target database from a
schema-only dump of the dev DB at alembic head.

Steps (design §F.2):
  1. Guard: resolve env profile, assert target compatibility
  2. pg_dump --schema-only from local pilot_dev (or accept --schema-dump PATH)
  3. psql -f apply to DATABASE_URL target
  4. Patch gen_random_uuid() defaults on 24 lookup tables
  5. alembic stamp head
  6. Write a dated dump artifact to dev-docs/db-design/dbbackups/
  7. Print the next-step seed command

Usage:
  python migrations/scripts/provision_schema.py --env e2e [--schema-dump PATH]
  python migrations/scripts/provision_schema.py --env qa  [--schema-dump PATH]
  python migrations/scripts/provision_schema.py --env prod --i-understand-prod-rebuild

``tests/e2e/init_e2e_schema.py`` becomes a thin wrapper delegating to
``--env e2e`` (keeps existing CLI signature + docs valid).

SAFETY: prod mode is double-gated (``--i-understand-prod-rebuild`` + interactive
confirmation). Existing prod is converged in place — this tool is for a
hypothetical fresh rebuild only (design §G-3).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Resolve backend root
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from migrations.scripts._env_profiles import (  # noqa: E402
    SeedEnv,
    assert_target_compatible,
    get_profile,
    print_seed_banner,
    resolve_seed_env,
)

# ── 24 lookup tables that need gen_random_uuid() defaults after schema-restore ──
# Carried over verbatim from init_e2e_schema.py lines 148–174.
UUID_DEFAULT_TABLES = [
    "address_type",
    "contact_type",
    "customer_lifecycle_status",
    "customer_comm_template_type",
    "invoice_status",
    "job_status",
    "jwk_status",
    "notification_category",
    "notification_category_sub_trigger",
    "notification_default_policy",
    "notification_type",
    "payment_status",
    "payment_type",
    "qco_line_type",
    "qpl_contact_action_type",
    "quote_link_status",
    "quote_status",
    "site_lifecycle_status",
    "subscription_status",
    "supplier_item_category",
    "supplier_item_uom",
    "supplier_lifecycle_status",
    "sync_conflict_classification_matrix",
    "tenant_user_status",
    "webhook_event_type",
]

# Dev DB connection defaults (for pg_dump source)
DEV_DB_HOST = os.environ.get("DEV_DB_HOST", "localhost")
DEV_DB_PORT = os.environ.get("DEV_DB_PORT", "5432")
DEV_DB_USER = os.environ.get("DEV_DB_USER", "pilot_user")
DEV_DB_NAME = os.environ.get("DEV_DB_NAME", "pilot_dev")
DEV_DB_PASSWORD = os.environ.get("DEV_DB_PASSWORD", "CHANGE_ME_LOCAL_DB_PW")

# Dump artifact directory
DUMP_ARTIFACT_DIR = (
    Path(__file__).parent.parent.parent.parent / "dev-docs" / "db-design" / "dbbackups"
)


def _parse_connection_url(url: str) -> dict:
    """Parse postgresql://user:password@host:port/dbname into components."""
    url = url.replace("postgresql://", "").replace("postgres://", "")
    userpass, rest = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, dbname = rest.split("/", 1)
    if ":" in hostport:
        host, port = hostport.split(":", 1)
    else:
        host, port = hostport, "5432"
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname,
    }


def _generate_schema_dump(output_path: Path) -> None:
    """Generate a schema-only dump from the local dev DB."""
    print(f"  Generating schema dump from dev DB → {output_path}")
    env = {**os.environ, "PGPASSWORD": DEV_DB_PASSWORD}
    result = subprocess.run(
        [
            "pg_dump",
            "-h",
            DEV_DB_HOST,
            "-p",
            DEV_DB_PORT,
            "-U",
            DEV_DB_USER,
            "-d",
            DEV_DB_NAME,
            "--schema-only",
            "-f",
            str(output_path),
        ],
        env=env,
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: pg_dump failed:", file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        sys.exit(result.returncode)
    print(f"  ✅ Schema dump generated ({output_path.stat().st_size} bytes)")


def _apply_schema_dump(schema_dump: Path, target_url: str) -> None:
    """Apply a schema-only SQL file to the target database."""
    if not schema_dump.exists():
        print(
            f"ERROR: Schema dump not found at {schema_dump}\n"
            "  Generate it with --schema-dump or let this script generate one.",
            file=sys.stderr,
        )
        sys.exit(1)

    conn = _parse_connection_url(target_url)
    print(
        f"  Applying schema from {schema_dump} → "
        f"{conn['host']}:{conn['port']}/{conn['dbname']}"
    )
    env = {**os.environ, "PGPASSWORD": conn["password"]}
    result = subprocess.run(
        [
            "psql",
            "-h",
            conn["host"],
            "-p",
            conn["port"],
            "-U",
            conn["user"],
            "-d",
            conn["dbname"],
            "-f",
            str(schema_dump),
            "--quiet",
        ],
        env=env,
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: psql schema restore failed:", file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        sys.exit(result.returncode)
    print("  ✅ Schema applied successfully")


def _add_uuid_defaults(target_url: str) -> None:
    """Add gen_random_uuid() defaults to 'id' columns on 24 lookup tables."""
    conn = _parse_connection_url(target_url)
    env = {**os.environ, "PGPASSWORD": conn["password"]}
    print(
        f"  Adding gen_random_uuid() defaults to {len(UUID_DEFAULT_TABLES)} lookup tables..."
    )
    patched = 0
    skipped = 0
    for table in UUID_DEFAULT_TABLES:
        sql = (
            f"ALTER TABLE public.{table} ALTER COLUMN id SET DEFAULT gen_random_uuid();"
        )
        result = subprocess.run(
            [
                "psql",
                "-h",
                conn["host"],
                "-p",
                conn["port"],
                "-U",
                conn["user"],
                "-d",
                conn["dbname"],
                "-c",
                sql,
                "--quiet",
            ],
            env=env,
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if "does not exist" in result.stderr:
                skipped += 1
                continue
            print(f"  ⚠️  [{table}] ALTER failed: {result.stderr.strip()[:120]}")
        else:
            patched += 1
    print(
        f"  ✅ UUID defaults set on {patched} tables ({skipped} skipped — not present)"
    )


def _stamp_alembic_head(target_url: str) -> None:
    """Stamp alembic_version in the target DB at the current head revision."""
    result = subprocess.run(
        ["alembic", "heads", "--resolve-dependencies"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": target_url},
    )
    if result.returncode != 0:
        print("ERROR: alembic heads failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    head = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            head = line.split()[0]
            break
    if not head:
        print("ERROR: Could not determine alembic head revision", file=sys.stderr)
        sys.exit(1)

    print(f"  Stamping alembic at head revision: {head}")
    result = subprocess.run(
        ["alembic", "stamp", head],
        cwd=str(BACKEND_DIR),
        env={**os.environ, "DATABASE_URL": target_url},
    )
    if result.returncode != 0:
        print("ERROR: alembic stamp failed:", file=sys.stderr)
        sys.exit(result.returncode)
    print(f"  ✅ alembic_version stamped at {head}")


def _write_dump_artifact(schema_dump: Path) -> Path:
    """Copy the schema dump to the dated artifact directory for audit."""
    DUMP_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    artifact = DUMP_ARTIFACT_DIR / f"schema_dump_{ts}.sql"
    shutil.copy2(schema_dump, artifact)
    print(f"  ✅ Dump artifact saved: {artifact}")
    return artifact


def _prod_rebuild_confirmation() -> None:
    """Double-gate for prod rebuild (design §G-3)."""
    print("\n" + "!" * 72)
    print("  ⚠️  PROD REBUILD — This will DROP and recreate the prod schema!")
    print("  Existing prod data will be LOST. This is NOT the converge path.")
    print("  Prod is normally converged in place via seed_prod_db.py (§G-3).")
    print("!" * 72)
    print("\n  Type PILOT-PROD-REBUILD to proceed, or anything else to abort:")
    response = input("  > ").strip()
    if response != "PILOT-PROD-REBUILD":
        print("  Aborted.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="provision_schema.py — generalized schema-restore provisioning (DB-MGMT-1)"
    )
    parser.add_argument(
        "--env",
        choices=["e2e", "qa", "prod"],
        default=None,
        help="Target environment (e2e, qa, or prod). Required.",
    )
    parser.add_argument(
        "--schema-dump",
        dest="schema_dump_flag",
        default=None,
        help="Path to an existing schema dump SQL file. If omitted, generates one from dev DB.",
    )
    parser.add_argument(
        "--i-understand-prod-rebuild",
        action="store_true",
        default=False,
        help="Required for --env prod: acknowledges this is a destructive rebuild.",
    )
    parser.add_argument(
        "--stripe-mode",
        choices=["test", "live"],
        default=None,
        help="Required with --env prod (profile resolution requires it). "
        "Ignored for e2e/qa.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        default=False,
        help="Skip the Stripe secrets-manager key-alignment preflight (prod).",
    )
    # --env is already defined above; don't call add_env_args (would conflict).
    args = parser.parse_args()

    # Resolve env (required for this tool — no default dev)
    env_raw = args.env or os.environ.get("SEED_ENV")
    if not env_raw:
        print(
            "ERROR: --env is required for provision_schema.py (one of: e2e, qa, prod).",
            file=sys.stderr,
        )
        sys.exit(1)
    env = resolve_seed_env(env_raw)
    if env is SeedEnv.DEV:
        print(
            "ERROR: --env dev is not valid for provision_schema.py — "
            "dev is provisioned via `alembic upgrade head` (design §H.1).",
            file=sys.stderr,
        )
        sys.exit(1)

    profile = get_profile(env, getattr(args, "stripe_mode", None))
    target_url = os.environ.get("DATABASE_URL", "")
    if not target_url:
        print(
            "ERROR: DATABASE_URL must be set to the target database.",
            file=sys.stderr,
        )
        sys.exit(1)
    assert_target_compatible(profile, target_url)
    print_seed_banner(profile, target_url, "provision_schema.py")

    # Prod double-gate
    if env is SeedEnv.PROD:
        if not args.i_understand_prod_rebuild:
            print(
                "ERROR: --env prod requires --i-understand-prod-rebuild "
                "(design §G-3: prod rebuild is double-gated).",
                file=sys.stderr,
            )
            sys.exit(1)
        _prod_rebuild_confirmation()

    # Resolve schema dump path
    schema_path = args.schema_dump_flag or "/tmp/pilot_dev_schema.sql"
    schema_dump = Path(schema_path)

    # Generate dump if it doesn't exist (or if --schema-dump not provided)
    if not schema_dump.exists():
        _generate_schema_dump(schema_dump)
    else:
        print(f"  Using existing schema dump: {schema_dump}")

    print("\n[1/4] Applying schema dump...")
    _apply_schema_dump(schema_dump, target_url)

    print("\n[2/4] Patching UUID defaults on lookup tables...")
    _add_uuid_defaults(target_url)

    print("\n[3/4] Stamping alembic at head...")
    _stamp_alembic_head(target_url)

    print("\n[4/4] Writing dump artifact...")
    _write_dump_artifact(schema_dump)

    # Print next-step seed command
    print("\n" + "=" * 72)
    print("  Schema provisioning complete.")
    print("=" * 72)
    if env is SeedEnv.E2E:
        print("\n  Next step: seed the E2E database:")
        print(
            f"  DATABASE_URL={target_url} \\\n"
            "  SMS_CARRIER=mock ENVIRONMENT=dev \\\n"
            "  python tests/e2e/seed_e2e_db.py"
        )
    elif env is SeedEnv.QA:
        print("\n  Next step: seed the QA database:")
        print(
            f"  DATABASE_URL={target_url} \\\n  python migrations/scripts/seed_qa_db.py"
        )
    else:  # prod
        print("\n  Next step: converge prod data (Groups A+B only):")
        print(
            f"  DATABASE_URL={target_url} \\\n"
            "  python migrations/scripts/seed_prod_db.py --stripe-mode <test|live>"
        )


if __name__ == "__main__":
    main()
