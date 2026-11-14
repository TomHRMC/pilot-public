"""
seed_scenario_nec.py — Group D: NEC Calculation scenario data.

Purpose: Seeds nec_calculation_log rows for the test tenant to support
E2E tests in cp8_nec (W-07).

NEVER run in production.

Schema verified via MCP 2026-07-12:
  nec_calculation_log: id, tenant_id, user_id, job_id, calc_type, nec_guide_version,
                       inputs_json, result_json, is_offline_calc, idempotency_key,
                       client_capture_at, created_at, updated_at, created_by, updated_by

Modes:
  seed()         — idempotent insert
  mode_reset()   — wipe this scenario's data
  mode_inspect() — show current state
"""

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text  # noqa: E402

from migrations.scripts._db_utils import get_db_session  # noqa: E402
from migrations.scripts._env_profiles import (  # noqa: E402
    add_env_args,
    assert_group_allowed,
    assert_target_compatible,
    print_seed_banner,
    resolve_profile_from_args,
)

# ── SEED DATA CONFIG ─────────────────────────────────────────────────────────

TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

ANCHOR = datetime(2026, 7, 1, tzinfo=UTC)


def _seed_impl(db_url: str | None = None) -> None:
    """Insert 3 nec_calculation_log rows idempotently."""
    tid = str(TEST_TENANT_ID)
    uid = str(OWNER_USER_ID)

    # Idempotency: check if seed rows already present (by calc_type + is_offline_calc combo)
    rows = [
        {
            "calc_type": "voltage_drop",
            "nec_guide_version": "2023",
            "inputs_json": '{"amperage": 20, "distance_feet": 50, "wire_gauge": "12", "voltage": 120, "phase": 1}',
            "result_json": '{"calc_type": "voltage_drop", "result_value": 0.3947, "is_compliant": true, "nec_article": "NEC 210.19(A)(1)", "nec_citation": "NEC 210.19(A)(1) Informational Note 4 — Voltage drop <= 3% recommended", "voltage_drop": 0.3947, "voltage_drop_pct": 0.3289, "is_compliant": true}',
            "is_offline_calc": False,
            "client_capture_at": None,
            "inputs_prefix": '%"amperage": 20%',
        },
        {
            "calc_type": "voltage_drop",
            "nec_guide_version": "2023",
            "inputs_json": '{"amperage": 15, "distance_feet": 100, "wire_gauge": "14", "voltage": 120, "phase": 1}',
            "result_json": '{"calc_type": "voltage_drop", "result_value": 0.9401, "is_compliant": true, "nec_article": "NEC 210.19(A)(1)", "nec_citation": "NEC 210.19(A)(1) Informational Note 4 — Voltage drop <= 3% recommended", "voltage_drop": 0.9401, "voltage_drop_pct": 0.7834, "is_compliant": true}',
            "is_offline_calc": True,
            "client_capture_at": ANCHOR - timedelta(days=3),
            "inputs_prefix": '%"amperage": 15%',
        },
        # SD-5: conduit_fill calc type (DB constraint allows: voltage_drop, conduit_fill, ampacity)
        {
            "calc_type": "conduit_fill",
            "nec_guide_version": "2023",
            "inputs_json": '{"conduit_type": "EMT", "conduit_size_inches": 0.75, "conductors": [{"awg": "12", "count": 4, "type": "THHN"}, {"awg": "14", "count": 2, "type": "THHN"}]}',
            "result_json": '{"calc_type": "conduit_fill", "result_value": 35.2, "is_compliant": true, "nec_article": "NEC 358.22", "nec_citation": "NEC 358.22 — Conduit fill 35.2% (max 40% per NEC 310)", "fill_percentage": 35.2, "available_area_sq_in": 0.213, "used_area_sq_in": 0.075}',
            "is_offline_calc": False,
            "client_capture_at": None,
            "inputs_prefix": '%"conduit_type"%',
        },
    ]

    with get_db_session() as db:
        inserted = 0
        for row in rows:
            # Idempotency: check by tenant + calc_type + is_offline_calc + inputs_json prefix
            existing = db.execute(
                text("""
                    SELECT id FROM public.nec_calculation_log
                    WHERE tenant_id = :tid
                    AND calc_type = :calc_type
                    AND is_offline_calc = :offline
                    AND inputs_json::text LIKE :inputs_prefix
                    LIMIT 1
                """),
                {
                    "tid": tid,
                    "calc_type": row["calc_type"],
                    "offline": row["is_offline_calc"],
                    "inputs_prefix": row["inputs_prefix"],
                },
            ).first()

            if existing:
                print(
                    f"  ℹ️  [nec_calculation_log] row already exists (offline={row['is_offline_calc']})"
                )
                continue

            params = {
                "tid": tid,
                "uid": uid,
                "calc_type": row["calc_type"],
                "nec_guide_version": row["nec_guide_version"],
                "inputs_json": row["inputs_json"],
                "result_json": row["result_json"],
                "is_offline_calc": row["is_offline_calc"],
            }
            if row["client_capture_at"]:
                db.execute(
                    text("""
                        INSERT INTO public.nec_calculation_log
                        (id, tenant_id, user_id, calc_type, nec_guide_version,
                         inputs_json, result_json, is_offline_calc,
                         client_capture_at, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :uid, :calc_type, :nec_guide_version,
                         CAST(:inputs_json AS jsonb), CAST(:result_json AS jsonb), :is_offline_calc,
                         :client_capture_at, NOW(), NOW())
                    """),
                    {**params, "client_capture_at": row["client_capture_at"]},
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.nec_calculation_log
                        (id, tenant_id, user_id, calc_type, nec_guide_version,
                         inputs_json, result_json, is_offline_calc,
                         created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :uid, :calc_type, :nec_guide_version,
                         CAST(:inputs_json AS jsonb), CAST(:result_json AS jsonb), :is_offline_calc,
                         NOW(), NOW())
                    """),
                    params,
                )
            print(
                f"  ✅ [nec_calculation_log] Inserted {row['calc_type']} (offline={row['is_offline_calc']})"
            )
            inserted += 1

        db.commit()

    print(f"\n🎉 seed_scenario_nec complete — {inserted} new row(s) inserted")


def seed(db_url: str | None = None) -> None:
    """Idempotent seed — insert NEC calculation log rows for test tenant."""
    print("=== seed_scenario_nec: seed mode ===")
    print(f"    Tenant ID: {TEST_TENANT_ID}\n")
    _seed_impl(db_url)


def mode_reset(db_url: str | None = None) -> None:
    """Wipe NEC scenario data for test tenant."""
    print("=== seed_scenario_nec: reset mode ===")
    tid = str(TEST_TENANT_ID)
    with get_db_session() as db:
        result = db.execute(
            text("DELETE FROM public.nec_calculation_log WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        db.commit()
        print(f"  🗑  [nec_calculation_log] Deleted {result.rowcount} row(s)")
    print("\n✅ NEC scenario data wiped.")


def mode_inspect(db_url: str | None = None) -> None:
    """Show current state of NEC scenario data."""
    print("=== seed_scenario_nec: inspect mode ===")
    tid = str(TEST_TENANT_ID)
    with get_db_session() as db:
        rows = db.execute(
            text("""
                SELECT id, calc_type, nec_guide_version, is_offline_calc,
                       client_capture_at, created_at
                FROM public.nec_calculation_log
                WHERE tenant_id = :tid
                ORDER BY created_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [nec_calculation_log]  {len(rows)} row(s)")
        for r in rows:
            print(
                f"    • {r.id}  calc_type={r.calc_type}"
                f"  offline={r.is_offline_calc}"
                f"  created={r.created_at}"
            )


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_nec.py — Group D NEC calculation seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_nec.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(args, "reset", False):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_nec.py")
    if args.reset:
        mode_reset()
    elif args.mode == "seed":
        seed()
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        print("=== seed_scenario_nec: show mode ===")
        print(f"  Tenant: {TEST_TENANT_ID}")
        print("  3 rows: voltage_drop(online), voltage_drop(offline), box_fill(online)")
