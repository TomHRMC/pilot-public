"""
seed_scenario_dispatch.py — Group D: Dispatch board scenario data.

Purpose: Seeds jobs with scheduling data and tech assignments for dispatch
board testing. Depends on seed_test_tenant.py having run first.

Schema verified against live DB 2026-06-01:
  job: id, tenant_id, customer_id, site_id, status_id, scheduled_start_at,
       scheduled_end_at, actual_labor_cost_cents, actual_material_cost_cents,
       actual_profit_cents, is_active, version, created_at, updated_at
  job_tech_assignment: id, tenant_id, job_id, user_id, assigned_by_user_id,
                        role, ordinal, assigned_at, is_active, version,
                        created_at, updated_at
  tech_availability: id, tenant_id, user_id, availability_type, starts_at,
                      ends_at, is_active, created_at, updated_at

Modes:
  --mode seed     (default) idempotent
  --mode inspect  show current state with values
  --mode show     print definitions, no DB
  --reset         wipe only this scenario's data, then exit
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

from core.config import settings  # noqa: E402
from migrations.scripts._db_utils import get_db_session  # noqa: E402
from migrations.scripts._env_profiles import (  # noqa: E402
    add_env_args,
    assert_group_allowed,
    assert_target_compatible,
    print_seed_banner,
    resolve_profile_from_args,
)

# ── SEED DATA CONFIG ─────────────────────────────────────────────────────────

# Technician UUID — must match seed_test_tenant.py
TECH_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

JOBS = [
    {
        "title": "Scheduled - Outlet Installation",
        "status_code": "scheduled",
        "offset_days": 1,  # tomorrow
        "start_hour": 9,
        "end_hour": 13,
        "assign_tech": True,
    },
    {
        "title": "In Progress - Panel Upgrade",
        "status_code": "in_progress",
        "offset_days": 0,  # today
        "start_hour": 8,
        "end_hour": 17,
        "assign_tech": True,
    },
    {
        "title": "Completed - Circuit Job",
        "status_code": "completed",
        "offset_days": -1,  # yesterday
        "start_hour": 10,
        "end_hour": 15,
        "assign_tech": True,
    },
    {
        "title": "Completed - Awaiting Invoice",
        "status_code": "completed",
        "offset_days": -3,  # 3 days ago
        "start_hour": 9,
        "end_hour": 12,
        "assign_tech": False,
    },
    {
        "title": "Draft - Estimate Only",
        "status_code": "draft",
        "offset_days": None,  # no scheduling
        "start_hour": None,
        "end_hour": None,
        "assign_tech": False,
    },
    # SD-5: Cancelled job
    {
        "title": "Cancelled - Customer Backed Out",
        "status_code": "cancelled",
        "offset_days": None,
        "start_hour": None,
        "end_hour": None,
        "assign_tech": False,
        "job_number_suffix": "006",
    },
]

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_dispatch.py — Group D dispatch seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


def _get_tenant_id() -> UUID:
    return UUID(settings.TEST_TENANT_ID)


def _compute_scheduled_start(job_def: dict):
    if job_def["offset_days"] is None:
        return None
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        today
        + timedelta(days=job_def["offset_days"])
        + timedelta(hours=job_def["start_hour"])
    )


def _compute_scheduled_end(job_def: dict):
    if job_def["offset_days"] is None:
        return None
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        today
        + timedelta(days=job_def["offset_days"])
        + timedelta(hours=job_def["end_hour"])
    )


def _next_friday_utc() -> datetime:
    today = datetime.now(UTC).date()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    friday = today + timedelta(days=days_until_friday)
    return datetime(friday.year, friday.month, friday.day, 8, 0, 0, tzinfo=UTC)


def mode_reset(tenant_id: UUID):
    """Wipe dispatch scenario data (child-first ordering)."""
    tid = str(tenant_id)
    with get_db_session() as db:
        for table in [
            "job_tech_assignment",
            "tech_availability",
            "job_time_entry",
            "job_expense",
            "job_notes",
            "job_attachment",
            "job",
        ]:
            try:
                result = db.execute(
                    text(f"DELETE FROM public.{table} WHERE tenant_id = :tid"),
                    {"tid": tid},
                )
                if result.rowcount:
                    print(f"  🗑  [{table}] Deleted {result.rowcount} row(s)")
            except Exception:
                pass
        db.commit()

    print("\n✅ Dispatch scenario data wiped.")
    print("   Run: python migrations/scripts/seed_scenario_dispatch.py")
    print("   to re-seed.")


def mode_seed(tenant_id: UUID):
    """Seed dispatch scenario jobs, assignments, and tech availability."""
    print("=== seed_scenario_dispatch: seed mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        # Verify technician user exists
        tech_exists = db.execute(
            text('SELECT id FROM public."user" WHERE id = :uid'),
            {"uid": str(TECH_USER_ID)},
        ).first()
        if not tech_exists:
            print(f"  ❌ Technician user {TECH_USER_ID} not found.")
            print("     Run seed_test_tenant.py first, then retry.")
            return

        # Look up job status IDs
        job_status_ids = {
            row.code: str(row.id)
            for row in db.execute(
                text("SELECT id, code FROM public.job_status WHERE tenant_id IS NULL")
            ).fetchall()
        }

        # Get or use existing customer/site
        cust_row = db.execute(
            text("SELECT id FROM public.customer WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tid},
        ).first()
        site_row = db.execute(
            text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tid},
        ).first()

        if not cust_row or not site_row:
            print(
                "  ⚠️  No customer/site found — creating minimal fallback customer/site"
            )
            cust_lifecycle = db.execute(
                text(
                    "SELECT id FROM public.customer_lifecycle_status WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
                )
            ).first()
            cust_result = db.execute(
                text("""
                    INSERT INTO public.customer
                    (id, tenant_id, type, display_name, first_name, last_name,
                     is_active, preferred_contact_channel, sms_opted_out, sms_opt_in_consent,
                     lifecycle_status_id, created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, 'person', 'Dispatch Test Customer',
                            'Dispatch', 'Customer', true, 'email', false, false, :lifecycle_id,
                            NOW(), NOW())
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "lifecycle_id": str(cust_lifecycle.id) if cust_lifecycle else None,
                },
            )
            cust_id = str(cust_result.first().id)
            print(f"  ✅ Created fallback customer ({cust_id})")

            site_lifecycle = db.execute(
                text(
                    "SELECT id FROM public.site_lifecycle_status WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
                )
            ).first()
            site_result = db.execute(
                text("""
                    INSERT INTO public.site
                    (id, tenant_id, customer_id, name, is_active, lifecycle_status_id,
                     created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :cid, 'Dispatch Test Site', true, :lifecycle_id,
                            NOW(), NOW())
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "lifecycle_id": str(site_lifecycle.id) if site_lifecycle else None,
                },
            )
            site_id = str(site_result.first().id)
            print(f"  ✅ Created fallback site ({site_id})")
        else:
            cust_id = str(cust_row.id)
            site_id = str(site_row.id)

        # ── 1. Jobs ──────────────────────────────────────────────────────────
        job_ids = []

        for job_idx, job_def in enumerate(JOBS, start=1):
            status_id = job_status_ids.get(job_def["status_code"])
            if not status_id:
                print(
                    f"  ⚠️  [job] Status '{job_def['status_code']}' not found — skipping"
                )
                job_ids.append((None, job_def))
                continue

            scheduled_start = _compute_scheduled_start(job_def)
            scheduled_end = _compute_scheduled_end(job_def)

            # Idempotency check: find by status + title (description via join)
            existing = db.execute(
                text("""
                    SELECT j.id FROM public.job j
                    JOIN public.job_status js ON js.id = j.status_id
                    WHERE j.tenant_id = :tid AND j.customer_id = :cid
                    AND j.site_id = :sid AND js.code = :status_code
                    AND (j.scheduled_start_at = :sched_start
                         OR (j.scheduled_start_at IS NULL AND :sched_start IS NULL))
                    LIMIT 1
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "sid": site_id,
                    "status_code": job_def["status_code"],
                    "sched_start": scheduled_start,
                },
            ).first()

            if existing:
                print(f"  ℹ️  [job] '{job_def['title']}' already exists")
                # JOB-UI-B1: Idempotent UPDATE — set title on existing row
                db.execute(
                    text("""
                        UPDATE public.job SET title = :title, updated_at = NOW()
                        WHERE id = :jid AND tenant_id = :tid
                    """),
                    {"title": job_def["title"], "jid": str(existing.id), "tid": tid},
                )
                job_ids.append((str(existing.id), job_def))
                continue

            # estimated_duration_minutes: 240 min (4 hrs) for scheduled/in_progress
            est_duration = (
                240 if job_def["status_code"] in ("scheduled", "in_progress") else None
            )
            job_result = db.execute(
                text("""
                    INSERT INTO public.job
                    (id, tenant_id, customer_id, site_id, status_id,
                     job_number, scheduled_start_at, scheduled_end_at,
                     actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents,
                     estimated_duration_minutes, title,
                     is_active, version, created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :cid, :sid, :status_id,
                            :job_number, :scheduled_start, :scheduled_end,
                            0, 0, 0, :est_duration, :title,
                            true, 1, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "sid": site_id,
                    "status_id": status_id,
                    "job_number": (
                        job_def.get("job_number_suffix")
                        and f"DISP-{job_def['job_number_suffix']}"
                    )
                    or f"DISP-{job_idx:03d}",
                    "scheduled_start": scheduled_start,
                    "scheduled_end": scheduled_end,
                    "est_duration": est_duration,
                    "title": job_def.get("title"),
                },
            )
            job_row = job_result.first()
            job_id = str(job_row.id) if job_row else None
            job_ids.append((job_id, job_def))
            print(f"  ✅ [job] Created '{job_def['title']}' ({job_id})")

        # ── 2. Job Tech Assignments ───────────────────────────────────────────
        owner_id = str(UUID(settings.TEST_USER_ID))  # owner is assigning tech

        for job_id, job_def in job_ids:
            if not job_id or not job_def["assign_tech"]:
                continue

            existing = db.execute(
                text("""
                    SELECT id FROM public.job_tech_assignment
                    WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid
                """),
                {"tid": tid, "jid": job_id, "uid": str(TECH_USER_ID)},
            ).first()

            if existing:
                print(f"  ℹ️  [job_tech_assignment] Tech already assigned to {job_id}")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.job_tech_assignment
                        (id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal,
                         assigned_at, is_active, version, created_at, updated_at)
                        VALUES (gen_random_uuid(), :tid, :jid, :uid, :assigned_by, 'primary', 1,
                                NOW(), true, 1, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tid": tid,
                        "jid": job_id,
                        "uid": str(TECH_USER_ID),
                        "assigned_by": owner_id,
                    },
                )
                print(
                    f"  ✅ [job_tech_assignment] Assigned tech to '{job_def['title']}'"
                )

        # ── 3. Secondary Tech (Owner) Assignments for Jobs 1 and 2 (0-indexed) ─────
        for job_list_idx in [0, 1]:
            if job_list_idx >= len(job_ids):
                continue
            sec_job_id, sec_job_def = job_ids[job_list_idx]
            if not sec_job_id:
                continue

            existing_secondary = db.execute(
                text("""
                    SELECT id FROM public.job_tech_assignment
                    WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid
                """),
                {"tid": tid, "jid": sec_job_id, "uid": str(OWNER_USER_ID)},
            ).first()

            if not existing_secondary:
                db.execute(
                    text("""
                        INSERT INTO public.job_tech_assignment
                        (id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal,
                         assigned_at, is_active, version, created_at, updated_at)
                        VALUES (gen_random_uuid(), :tid, :jid, :uid, :assigned_by, 'helper', 2,
                                NOW(), true, 1, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tid": tid,
                        "jid": sec_job_id,
                        "uid": str(OWNER_USER_ID),
                        "assigned_by": str(OWNER_USER_ID),
                    },
                )
                print(
                    f"  ✅ [job_tech_assignment] Owner assigned as secondary to job {sec_job_id}"
                )

        # ── 4. Tech Availability Block (PTO next Friday) ─────────────────────
        next_friday = _next_friday_utc()
        next_friday_eod = next_friday.replace(hour=17)

        existing_pto = db.execute(
            text("""
                SELECT id FROM public.tech_availability
                WHERE tenant_id = :tid AND user_id = :uid AND availability_type = 'pto'
                AND starts_at = :starts
            """),
            {"tid": tid, "uid": str(TECH_USER_ID), "starts": next_friday},
        ).first()

        if existing_pto:
            print("  ℹ️  [tech_availability] PTO block already exists for technician")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tech_availability
                    (id, tenant_id, user_id, availability_type, starts_at, ends_at, is_active,
                     created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :uid, 'pto', :starts, :ends, true, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "uid": str(TECH_USER_ID),
                    "starts": next_friday,
                    "ends": next_friday_eod,
                },
            )
            print(
                f"  ✅ [tech_availability] PTO block: {next_friday.date()} 8am–5pm (next Friday)"
            )

        # ── 5. Owner Sick Day (2 weeks after next Friday) ────────────────────
        sick_start_utc = (next_friday + timedelta(weeks=2)).replace(hour=8)
        sick_end_utc = sick_start_utc.replace(hour=17)

        existing_sick = db.execute(
            text("""
                SELECT id FROM public.tech_availability
                WHERE tenant_id = :tid AND user_id = :uid AND availability_type = 'unavailable'
                AND starts_at = :starts
            """),
            {"tid": tid, "uid": str(OWNER_USER_ID), "starts": sick_start_utc},
        ).first()

        if not existing_sick:
            db.execute(
                text("""
                    INSERT INTO public.tech_availability
                    (id, tenant_id, user_id, availability_type, starts_at, ends_at, is_active,
                     notes, created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :uid, 'unavailable', :starts, :ends, true,
                            'Owner sick day', NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "uid": str(OWNER_USER_ID),
                    "starts": sick_start_utc,
                    "ends": sick_end_utc,
                },
            )
            print(f"  ✅ [tech_availability] Owner sick day: {sick_start_utc.date()}")
        else:
            print("  ℹ️  [tech_availability] Owner sick day already exists")

        # ── FIX-005: Update scheduled_start_at for DISP scheduled/in_progress jobs ─────
        # Ensures dispatch board shows current dates on any re-seed date
        print("\n  -- FIX-005: Refreshing DISP scheduled/in_progress job dates --")
        for update_job_id, update_job_def in job_ids:
            if update_job_id is None:
                continue
            if update_job_def["status_code"] not in ("scheduled", "in_progress"):
                continue
            new_start = _compute_scheduled_start(update_job_def)
            new_end = _compute_scheduled_end(update_job_def)
            if new_start is None:
                continue
            db.execute(
                text("""
                    UPDATE public.job
                    SET scheduled_start_at = :new_start,
                        scheduled_end_at   = :new_end,
                        updated_at         = NOW()
                    WHERE id = :jid AND tenant_id = :tid
                """),
                {
                    "new_start": new_start,
                    "new_end": new_end,
                    "jid": update_job_id,
                    "tid": tid,
                },
            )
            print(
                f"  ✅ [job] Updated {update_job_def['title']} dates → {new_start.date()}"
            )

        # ── FIX-005B: Add job_tech_assignment rows for scheduled/in_progress DISP jobs ─
        print("\n  -- FIX-005B: Seeding job_tech_assignment rows for DISP jobs --")
        for assign_job_id, assign_job_def in job_ids:
            if assign_job_id is None:
                continue
            if assign_job_def["status_code"] not in ("scheduled", "in_progress"):
                continue
            if not assign_job_def.get("assign_tech", False):
                continue

            existing_ja = db.execute(
                text("""
                    SELECT id FROM public.job_tech_assignment
                    WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid
                """),
                {"tid": tid, "jid": assign_job_id, "uid": str(TECH_USER_ID)},
            ).first()

            if existing_ja:
                print(
                    f"  ℹ️  [job_tech_assignment] Already exists for {assign_job_def['title']}"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.job_tech_assignment
                          (id, tenant_id, job_id, user_id, assigned_by_user_id,
                           role, ordinal, assigned_at, is_active, version,
                           created_at, updated_at)
                        VALUES
                          (gen_random_uuid(), :tid, :jid, :uid, :uid,
                           'primary', 1, NOW(), true, 1,
                           NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {"tid": tid, "jid": assign_job_id, "uid": str(TECH_USER_ID)},
                )
                print(
                    f"  ✅ [job_tech_assignment] Added primary assignment for '{assign_job_def['title']}'"
                )

        # ── FIX-006: Add job_time_entry, job_expense, job_notes for DISP jobs ────────
        print(
            "\n  -- FIX-006: Seeding operational data for DISP in_progress/scheduled jobs --"
        )

        # Labor rates — fallback if not available
        labor_rate_row = db.execute(
            text("""
                SELECT hourly_rate_cents FROM public.labor_rate_version
                WHERE tenant_id = :tid
                ORDER BY valid_period DESC
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        hourly_rate_cents = labor_rate_row.hourly_rate_cents if labor_rate_row else 9500

        # job_expense_category_code options (use 'materials' which is standard)
        for op_job_id, op_job_def in job_ids:
            if op_job_id is None:
                continue
            if op_job_def["status_code"] not in ("scheduled", "in_progress"):
                continue

            op_start = _compute_scheduled_start(op_job_def)
            if op_start is None:
                continue

            # -- Time Entries (2 per job) --
            te_specs = [
                {
                    "offset_h": 0,
                    "duration_h": 2.0,
                    "notes": "Site prep and material staging",
                    "hours_remaining": 3.0,
                },
                {
                    "offset_h": 2,
                    "duration_h": 2.0,
                    "notes": "Panel rough-in complete",
                    "hours_remaining": 2.0,
                },
            ]
            for te in te_specs:
                te_start = op_start + timedelta(hours=te["offset_h"])
                te_end = te_start + timedelta(hours=te["duration_h"])
                total_cost = int(te["duration_h"] * hourly_rate_cents)

                existing_te = db.execute(
                    text("""
                        SELECT id FROM public.job_time_entry
                        WHERE tenant_id = :tid AND job_id = :jid
                        AND user_id = :uid AND started_at = :started
                        LIMIT 1
                    """),
                    {
                        "tid": tid,
                        "jid": op_job_id,
                        "uid": str(TECH_USER_ID),
                        "started": te_start,
                    },
                ).first()
                if existing_te:
                    print(f"  ℹ️  [job_time_entry] Already exists for job {op_job_id}")
                    continue

                db.execute(
                    text("""
                        INSERT INTO public.job_time_entry
                        (id, tenant_id, job_id, user_id, started_at, ended_at,
                         hours, hourly_rate_cents, total_cost_cents, notes,
                         hours_remaining_estimate, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :jid, :uid, :started, :ended,
                         :hours, :rate, :total, :notes,
                         :hours_remaining, NOW(), NOW())
                    """),
                    {
                        "tid": tid,
                        "jid": op_job_id,
                        "uid": str(TECH_USER_ID),
                        "started": te_start,
                        "ended": te_end,
                        "hours": te["duration_h"],
                        "rate": hourly_rate_cents,
                        "total": total_cost,
                        "notes": te["notes"],
                        "hours_remaining": te["hours_remaining"],
                    },
                )
                print(
                    f"  ✅ [job_time_entry] {te['duration_h']}h @ {hourly_rate_cents}¢/hr for job {op_job_id}"
                )

            # -- Expenses (2 per job; one material, one permit) --
            exp_specs = [
                {
                    "category": "materials",
                    "description": "Electrical supplies and wire",
                    "cost_cents": 18500,
                    "markup_pct": 20.0,
                },
                {
                    "category": "materials",
                    "description": "Circuit breakers and hardware",
                    "cost_cents": 9200,
                    "markup_pct": 20.0,
                },
            ]
            # At-risk scenario: for DISP-002 (in_progress), use high-cost materials
            if op_job_def["status_code"] == "in_progress":
                exp_specs[0]["cost_cents"] = (
                    85000  # high cost to trigger at-risk threshold
                )
                exp_specs[0]["description"] = (
                    "200A panel + materials (at-risk scenario)"
                )

            for exp in exp_specs:
                markup_amt = int(exp["cost_cents"] * exp["markup_pct"] / 100)
                billable_cents = exp["cost_cents"] + markup_amt

                existing_exp = db.execute(
                    text("""
                        SELECT id FROM public.job_expense
                        WHERE tenant_id = :tid AND job_id = :jid AND description = :desc
                        LIMIT 1
                    """),
                    {"tid": tid, "jid": op_job_id, "desc": exp["description"]},
                ).first()
                if existing_exp:
                    print(f"  ℹ️  [job_expense] '{exp['description']}' already exists")
                    continue

                db.execute(
                    text("""
                        INSERT INTO public.job_expense
                        (id, tenant_id, job_id, job_expense_category_code, description,
                         cost_cents, markup_pct, markup_amt_cents, billable_cents,
                         is_billable, user_id, incurred_at, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :jid, :category, :description,
                         :cost_cents, :markup_pct, :markup_amt, :billable,
                         true, :uid, :incurred_at, NOW(), NOW())
                    """),
                    {
                        "tid": tid,
                        "jid": op_job_id,
                        "category": exp["category"],
                        "description": exp["description"],
                        "cost_cents": exp["cost_cents"],
                        "markup_pct": exp["markup_pct"],
                        "markup_amt": markup_amt,
                        "billable": billable_cents,
                        "uid": str(TECH_USER_ID),
                        "incurred_at": op_start,
                    },
                )
                print(
                    f"  ✅ [job_expense] '{exp['description']}' cost=${exp['cost_cents'] / 100:.2f}"
                )

            # -- Job Notes (1 per job) --
            note_text = "Customer requested outlet moved to east wall — adjusted scope accordingly"
            existing_note = db.execute(
                text("""
                    SELECT id FROM public.job_notes
                    WHERE tenant_id = :tid AND job_id = :jid AND notes = :notes
                    LIMIT 1
                """),
                {"tid": tid, "jid": op_job_id, "notes": note_text},
            ).first()
            if existing_note:
                print(f"  ℹ️  [job_notes] Already exists for job {op_job_id}")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.job_notes
                        (id, tenant_id, job_id, notes, customer_visible, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :jid, :notes, false, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {"tid": tid, "jid": op_job_id, "notes": note_text},
                )
                print(f"  ✅ [job_notes] Added note for job {op_job_id}")

        # ── SD-7 Batch 3: customer_communication for DISP-002 (in_progress) ─────
        print("\n  -- SD-7 B3: customer_communication on-my-way for DISP-002 --")

        # Find the in_progress job (DISP-002)
        inprog_job_id = None
        inprog_cust_id = None
        for _jid, _jdef in job_ids:
            if _jid and _jdef["status_code"] == "in_progress":
                inprog_job_id = _jid
                inprog_cust_id = cust_id  # shared customer from dispatch scenario
                break

        if inprog_job_id:
            # Look up communication_template id for on_my_way (use sms channel)
            comm_tmpl_row = db.execute(
                text("""
                    SELECT id FROM public.communication_template
                    WHERE template_code = 'on_my_way' AND channel = 'sms'
                    LIMIT 1
                """)
            ).first()
            comm_tmpl_id = str(comm_tmpl_row.id) if comm_tmpl_row else None

            # Idempotency: skip if already exists
            existing_cc = db.execute(
                text("""
                    SELECT id FROM public.customer_communication
                    WHERE tenant_id = :tid AND job_id = :jid AND template_code = 'on_my_way'
                    LIMIT 1
                """),
                {"tid": tid, "jid": inprog_job_id},
            ).first()
            if existing_cc:
                print(
                    "  ℹ️  [customer_communication] on_my_way already exists for DISP-002"
                )
            else:
                now_utc = datetime.now(UTC)
                sent_ts = now_utc - timedelta(minutes=30)
                db.execute(
                    text("""
                        INSERT INTO public.customer_communication
                        (id, tenant_id, customer_id, job_id, sender_user_id,
                         template_code, template_id,
                         rendered_message, channel, actual_channel,
                         channel_override_flag, status, sent_at,
                         created_at, updated_at)
                        VALUES (gen_random_uuid(), :tid, :cid, :jid, :sender_id,
                                'on_my_way', :tmpl_id,
                                'I''m on my way to your location. ETA 15 minutes.',
                                'sms', 'sms',
                                false, 'sent', :sent_at,
                                NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tid": tid,
                        "cid": inprog_cust_id,
                        "jid": inprog_job_id,
                        "sender_id": str(TECH_USER_ID),
                        "tmpl_id": comm_tmpl_id,
                        "sent_at": sent_ts,
                    },
                )
                print(
                    f"  ✅ [customer_communication] on_my_way → DISP-002 (job={inprog_job_id}) sent={sent_ts}"
                )

        # ── SD-7 Batch 3: job_recurrence_rule (1 active weekly inspection) ───────
        print("\n  -- SD-7 B3: job_recurrence_rule (weekly inspection) --")
        now_date = datetime.now(UTC).date()
        existing_rr = db.execute(
            text("""
                SELECT id FROM public.job_recurrence_rule
                WHERE tenant_id = :tid AND pattern = 'weekly'
                AND is_active = true
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if existing_rr:
            print("  ℹ️  [job_recurrence_rule] Weekly rule already exists")
        else:
            starts_on = now_date
            next_job_at = datetime.now(UTC).replace(
                hour=9, minute=0, second=0, microsecond=0
            ) + timedelta(weeks=1)
            db.execute(
                text("""
                    INSERT INTO public.job_recurrence_rule
                    (id, tenant_id, customer_id, site_id, pattern, interval_count,
                     starts_on, ends_on, max_occurrences, occurrences_created,
                     next_job_at, estimated_duration_minutes,
                     default_tech_user_id, notes_template, is_active,
                     created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :cid, :sid, 'weekly', 1,
                            :starts_on, NULL, NULL, 0,
                            :next_job_at, 120,
                            :tech_id,
                            'Weekly electrical panel inspection — check breaker torque and connections.',
                            true,
                            NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "sid": site_id,
                    "starts_on": starts_on,
                    "next_job_at": next_job_at,
                    "tech_id": str(TECH_USER_ID),
                },
            )
            print(
                f"  ✅ [job_recurrence_rule] Weekly inspection rule created (starts={starts_on})"
            )

        db.commit()

        # ── CLASS-B1: Assign priority + job_type_id to dispatch scenario jobs ──
        print("\n  -- CLASS-B1: priority + job_type_id on dispatch jobs --")
        # Look up job_type IDs at runtime — never hardcode UUIDs (README §7)
        job_type_map = {
            row.code: str(row.id)
            for row in db.execute(
                text("SELECT id, code FROM public.job_type WHERE tenant_id IS NULL")
            ).fetchall()
        }
        if not job_type_map:
            print("  ⚠️  [job_type] No platform defaults found — run seed_core.py first")
        else:
            # Assignment: job_number → (priority, job_type_code)
            # Requirements: ≥1 emergency, ≥1 urgent, rest standard
            dispatch_assignments = {
                "JOB-900001": ("emergency", "service_call"),
                "JOB-900002": ("urgent", "panel_upgrade"),
                "JOB-900003": ("standard", "inspection"),
                "JOB-900004": ("standard", "lighting"),
                "JOB-900005": ("standard", "troubleshoot"),
                "JOB-900006": ("standard", "service_call"),
            }
            # Fallback: assign by ordinal position if DISP-series job_numbers differ
            tenant_jobs = db.execute(
                text("""
                    SELECT id, job_number FROM public.job
                    WHERE tenant_id = :tid
                    ORDER BY created_at
                """),
                {"tid": tid},
            ).fetchall()
            priority_cycle = [
                "emergency",
                "urgent",
                "standard",
                "standard",
                "standard",
                "standard",
            ]
            type_cycle = [
                "service_call",
                "panel_upgrade",
                "inspection",
                "lighting",
                "troubleshoot",
                "service_call",
            ]
            for idx, row in enumerate(tenant_jobs):
                priority_val = (
                    priority_cycle[idx] if idx < len(priority_cycle) else "standard"
                )
                type_code = type_cycle[idx] if idx < len(type_cycle) else "other"
                jt_id = job_type_map.get(type_code)
                existing = db.execute(
                    text(
                        "SELECT priority, job_type_id FROM public.job WHERE id = :jid"
                    ),
                    {"jid": str(row.id)},
                ).first()
                if existing and existing.priority != "standard":
                    print(
                        f"  ℹ️  [job priority] job {row.id} already has priority={existing.priority}"
                    )
                    continue
                db.execute(
                    text("""
                        UPDATE public.job
                        SET priority = :priority, job_type_id = CAST(:jt_id AS uuid),
                            updated_at = NOW()
                        WHERE id = :jid AND tenant_id = :tid
                    """),
                    {
                        "priority": priority_val,
                        "jt_id": jt_id,
                        "jid": str(row.id),
                        "tid": tid,
                    },
                )
                print(
                    f"  ✅ [job priority+type] job {str(row.id)[:8]}… priority={priority_val} type={type_code}"
                )
            db.commit()

    print(
        f"\n🎉 seed_scenario_dispatch complete — Group D dispatch data present for {tenant_id}"
    )


def mode_inspect(tenant_id: UUID):
    """Show current state of dispatch scenario data."""
    print("=== seed_scenario_dispatch: inspect mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        jobs = db.execute(
            text("""
                SELECT j.id, js.code as status_code, j.scheduled_start_at, j.scheduled_end_at,
                       j.estimated_duration_minutes
                FROM public.job j
                JOIN public.job_status js ON js.id = j.status_id
                WHERE j.tenant_id = :tid ORDER BY j.scheduled_start_at NULLS LAST
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job]  {len(jobs)} row(s)")
        for j in jobs:
            sched = str(j.scheduled_start_at) if j.scheduled_start_at else "no schedule"
            end = str(j.scheduled_end_at) if j.scheduled_end_at else "open"
            dur = (
                f"  est_duration={j.estimated_duration_minutes}min"
                if j.estimated_duration_minutes
                else ""
            )
            print(f"    • {j.id}  status={j.status_code}  {sched} → {end}{dur}")
        print()

        assignments = db.execute(
            text("""
                SELECT jta.id, jta.job_id, jta.user_id, jta.role, jta.ordinal, jta.assigned_at
                FROM public.job_tech_assignment jta
                WHERE jta.tenant_id = :tid ORDER BY jta.job_id
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job_tech_assignment]  {len(assignments)} row(s)")
        for a in assignments:
            print(
                f"    • job={a.job_id}  user={a.user_id}  role={a.role}  ordinal={a.ordinal}"
            )
        print()

        avail = db.execute(
            text("""
                SELECT user_id, availability_type, starts_at, ends_at
                FROM public.tech_availability
                WHERE tenant_id = :tid ORDER BY starts_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [tech_availability]  {len(avail)} row(s)")
        for av in avail:
            print(
                f"    • user={av.user_id}  type={av.availability_type}  {av.starts_at} → {av.ends_at}"
            )
        print()

        # SD-7 Batch 3: customer_communication
        comms = db.execute(
            text("""
                SELECT id, customer_id, job_id, template_code, actual_channel, status, sent_at
                FROM public.customer_communication
                WHERE tenant_id = :tid
                ORDER BY sent_at NULLS LAST
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [customer_communication]  {len(comms)} row(s)")
        for cc in comms:
            print(
                f"    • id={cc.id}  template={cc.template_code}  channel={cc.actual_channel}"
                f"  status={cc.status}  sent={cc.sent_at}  job={cc.job_id}"
            )
        print()

        # SD-7 Batch 3: job_recurrence_rule
        rr_rows = db.execute(
            text("""
                SELECT id, pattern, interval_count, starts_on, is_active,
                       estimated_duration_minutes, next_job_at
                FROM public.job_recurrence_rule
                WHERE tenant_id = :tid
                ORDER BY starts_on
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job_recurrence_rule]  {len(rr_rows)} row(s)")
        for rr in rr_rows:
            print(
                f"    • id={rr.id}  pattern={rr.pattern}  interval={rr.interval_count}"
                f"  is_active={rr.is_active}  duration={rr.estimated_duration_minutes}min"
                f"  next_job_at={rr.next_job_at}"
            )


def mode_show():
    """Print what would be seeded without touching the DB."""
    print("=== seed_scenario_dispatch: show mode ===\n")
    print(f"Technician UUID: {TECH_USER_ID}\n")
    print("Jobs (5):")
    for j in JOBS:
        sched = (
            f"  offset={j['offset_days']}d  {j['start_hour']}:00–{j['end_hour']}:00"
            if j["offset_days"] is not None
            else "  no schedule"
        )
        assign = "  assigned=tech" if j["assign_tech"] else "  no assignment"
        print(f"  • {j['title']}  status={j['status_code']}{sched}{assign}")
    print("\nTech Availability (1):")
    print(f"  • Next Friday 8am–5pm  type=pto  user={TECH_USER_ID}")


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_dispatch.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(args, "reset", False):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_dispatch.py")
    tenant_id = _get_tenant_id()

    if args.reset:
        mode_reset(tenant_id)
    elif args.mode == "seed":
        mode_seed(tenant_id)
    elif args.mode == "inspect":
        mode_inspect(tenant_id)
    elif args.mode == "show":
        mode_show()
