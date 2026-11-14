"""
seed_scenario_reporting.py — Group D: Profitability/Reporting scenario data.

Purpose: Seeds historical completed jobs with time entries and expenses to enable
meaningful data in the profitability and reporting surfaces.
NEVER run in production.

Schema verified against live DB 2026-07-06:
  job: id, tenant_id, customer_id, site_id, status_id, scheduled_start_at,
       scheduled_end_at, actual_labor_cost_cents, actual_material_cost_cents,
       actual_profit_cents, is_active, version, created_at, updated_at
  job_time_entry: id, tenant_id, job_id, user_id, started_at, ended_at, hours,
                  hourly_rate_cents, total_cost_cents, created_at, updated_at
  job_expense: id, tenant_id, job_id, job_expense_category_code, description,
               cost_cents, markup_pct, billable_cents, is_billable, user_id,
               incurred_at, created_at, updated_at
  job_tech_assignment: id, tenant_id, job_id, user_id, assigned_by_user_id,
                       role, ordinal, assigned_at, is_active, version,
                       created_at, updated_at

Uses:
  - Existing customers from seed_scenario_quote_to_cash.py (no new customers)
  - Fixed past dates (not NOW()) for consistent reporting data across re-seeds
  - Labor rates from seed_test_tenant.py (queried by skill_level_code)

Modes:
  --mode seed     (default) idempotent
  --mode inspect  show current state with values
  --mode show     print definitions, no DB
  --reset         wipe only this scenario's data, then exit
"""

import argparse
import base64
import os
import sys
import uuid
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

TECH_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
TENANT_ID_STR = "00000000-0000-0000-0000-000000000001"

# Fixed reference date — all job dates computed from this anchor
# Use a fixed past date so re-seeding produces the same relative dates
ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=UTC)  # anchored to July 1, 2026

# NOTE: pricebook_item IDs use gen_random_uuid() and change on every reset+reseed.
# Do NOT hardcode pricebook_item UUIDs. The pricebook_item_ids dict is built by
# querying the live DB at runtime (keyed by SKU) inside mode_seed().

# SD-6: qco_line_type codes — resolved to UUIDs at runtime via qco_line_type_ids
# dict (built from SELECT id, code FROM qco_line_type WHERE tenant_id IS NULL).
# DB-MGMT-1 Task 4: do NOT hardcode UUIDs — seed_core.py uses gen_random_uuid(),
# so UUIDs differ per DB. Look up by code instead.
QCO_LABOR = "labor"
QCO_MATERIAL = "material"
QCO_MISC = "misc"

# SD-6: tax_rate_version.id for US-DEFAULT (bigint, MCP-verified)
TAX_RATE_VERSION_ID = 1

# SD-6: Invoice line specs per invoice letter (design doc §D.3)
# Each entry: (qco_type_id, item_sku, description, qty, unit, unit_price_cents, taxability_code)
# NOTE: item_sku is a SKU string, NOT a UUID. It is resolved to a live pricebook_item_id
# inside mode_seed() using the pricebook_item_ids dict keyed by SKU. This ensures the
# correct ID is used even after a reset+reseed (UUIDs change on every gen_random_uuid() insert).
INVOICE_LINE_SPECS = {
    "A": {
        "invoice_number": "INV-900002",
        "lines": [
            (
                QCO_LABOR,
                "PANEL-200A-01",
                "200A Panel Upgrade",
                1,
                "ea",
                180000,
                "taxable",
            ),
            (QCO_MATERIAL, "COND-EMT-01", "EMT Conduit", 25, "ft", 350, "taxable"),
            (
                QCO_MATERIAL,
                "WNUT-BAG-01",
                "Wire Nuts (bag of 50)",
                2,
                "ea",
                500,
                "taxable",
            ),
            (
                QCO_MISC,
                "PERMIT-RES-01",
                "Residential Permit Fee",
                1,
                "ea",
                25000,
                "exempt",
            ),
        ],
        "subtotal_cents": 214750,
        "tax_cents": 11385,  # round(189750 * 0.06)
        "total_cents": 226135,
        "balance_due_cents": 0,  # paid
        "update_payment": True,
        "new_payment_amount": 226135,
    },
    "B": {
        "invoice_number": "INV-900003",
        "lines": [
            (
                QCO_LABOR,
                "OUTLET-STD-01",
                "Standard Outlet Installation",
                2,
                "ea",
                15000,
                "taxable",
            ),
            (
                QCO_MATERIAL,
                "BRKR-15A-01",
                "15A Circuit Breaker",
                6,
                "ea",
                1800,
                "taxable",
            ),
            (
                QCO_MATERIAL,
                "WNUT-BAG-01",
                "Wire Nuts (bag of 50)",
                1,
                "ea",
                500,
                "taxable",
            ),
        ],
        "subtotal_cents": 41300,
        "tax_cents": 2478,  # round(41300 * 0.06)
        "total_cents": 43778,
        "balance_due_cents": 0,  # paid
        "update_payment": True,
        "new_payment_amount": 43778,
    },
    "C": {
        "invoice_number": "INV-900004",
        "lines": [
            (
                QCO_LABOR,
                "OUTLET-STD-01",
                "Standard Outlet Installation",
                5,
                "ea",
                15000,
                "taxable",
            ),
            (QCO_MATERIAL, "COND-EMT-01", "EMT Conduit", 30, "ft", 350, "taxable"),
            (
                QCO_MISC,
                "PERMIT-RES-01",
                "Residential Permit Fee",
                1,
                "ea",
                25000,
                "exempt",
            ),
        ],
        "subtotal_cents": 110500,
        "tax_cents": 5130,  # round(85500 * 0.06)
        "total_cents": 115630,
        "balance_due_cents": 115630,
        "update_payment": False,
    },
    "D": {
        "invoice_number": "INV-900005",
        "lines": [
            (
                QCO_LABOR,
                "OUTLET-STD-01",
                "Standard Outlet Installation",
                1,
                "ea",
                15000,
                "taxable",
            ),
            (
                QCO_MATERIAL,
                "WNUT-BAG-01",
                "Wire Nuts (bag of 50)",
                2,
                "ea",
                500,
                "taxable",
            ),
        ],
        "subtotal_cents": 16000,
        "tax_cents": 960,  # round(16000 * 0.06)
        "total_cents": 16960,
        "balance_due_cents": 16960,
        "update_payment": False,
    },
    "E": {
        "invoice_number": "INV-900006",
        "lines": [
            (
                QCO_LABOR,
                "PANEL-200A-01",
                "200A Panel Upgrade",
                1,
                "ea",
                180000,
                "taxable",
            ),
            (
                QCO_MISC,
                "PERMIT-RES-01",
                "Residential Permit Fee",
                1,
                "ea",
                25000,
                "exempt",
            ),
        ],
        "subtotal_cents": 205000,
        "tax_cents": 10800,  # round(180000 * 0.06)
        "total_cents": 215800,
        "balance_due_cents": 135800,  # 215800 - 80000 partial payment
        "update_payment": True,
        "new_payment_amount": 80000,  # partial payment
    },
    "F": {
        "invoice_number": "INV-900007",
        "lines": [
            (
                QCO_LABOR,
                "PANEL-200A-01",
                "200A Panel Upgrade",
                1,
                "ea",
                180000,
                "taxable",
            ),
            (QCO_MATERIAL, "COND-EMT-01", "EMT Conduit", 50, "ft", 350, "taxable"),
            (
                QCO_MISC,
                "PERMIT-RES-01",
                "Residential Permit Fee",
                1,
                "ea",
                25000,
                "exempt",
            ),
        ],
        "subtotal_cents": 222500,
        "tax_cents": 11850,  # round(197500 * 0.06)
        "total_cents": 234350,
        "balance_due_cents": 234350,
        "update_payment": False,
    },
    "G": {
        "invoice_number": "INV-900008",
        "lines": [
            (
                QCO_LABOR,
                "PANEL-200A-01",
                "200A Panel Upgrade",
                2,
                "ea",
                180000,
                "taxable",
            ),
            (QCO_MATERIAL, "COND-EMT-01", "EMT Conduit", 100, "ft", 350, "taxable"),
            (
                QCO_MATERIAL,
                "BRKR-15A-01",
                "15A Circuit Breaker",
                20,
                "ea",
                1800,
                "taxable",
            ),
            (
                QCO_MISC,
                "PERMIT-RES-01",
                "Residential Permit Fee",
                2,
                "ea",
                25000,
                "exempt",
            ),
        ],
        "subtotal_cents": 481000,
        "tax_cents": 25860,  # round(431000 * 0.06)
        "total_cents": 506860,
        "balance_due_cents": 506860,
        "update_payment": False,
    },
}

# 7 completed jobs. Days before anchor = how far in the past.
# Each specifies start/end hours for the work day.
REPORTING_JOBS = [
    {
        "title": "Panel Upgrade — Completed Job A",
        "days_ago": 30,
        "start_hour": 8,
        "end_hour": 17,
        "customer_idx": 0,  # John Smith (first customer from quote-to-cash)
        "time_entries": [
            {
                "skill": "master",
                "start_offset_h": 0,
                "duration_h": 4.0,
                "notes": "Panel removal and wiring",
            },
            {
                "skill": "journeyman",
                "start_offset_h": 4,
                "duration_h": 3.5,
                "notes": "Circuit breaker installation",
            },
        ],
        "expenses": [
            {
                "category": "materials",
                "description": "200A Main Panel + Breakers",
                "cost_cents": 45000,
                "markup_pct": 20.0,
            },
        ],
    },
    {
        "title": "Service Call — Completed Job B",
        "days_ago": 45,
        "start_hour": 9,
        "end_hour": 13,
        "customer_idx": 1,  # Mary Johnson
        "time_entries": [
            {
                "skill": "journeyman",
                "start_offset_h": 0,
                "duration_h": 2.0,
                "notes": "Diagnostic and GFCI replacement",
            },
            {
                "skill": "journeyman",
                "start_offset_h": 2,
                "duration_h": 1.5,
                "notes": "Circuit testing",
            },
        ],
        "expenses": [
            {
                "category": "materials",
                "description": "GFCI Outlets (qty 4)",
                "cost_cents": 8000,
                "markup_pct": 20.0,
            },
        ],
    },
    {
        "title": "Commercial Inspection — Completed Job C",
        "days_ago": 60,
        "start_hour": 10,
        "end_hour": 16,
        "customer_idx": 2,  # Apex Commercial LLC
        "time_entries": [
            {
                "skill": "master",
                "start_offset_h": 0,
                "duration_h": 3.0,
                "notes": "Full commercial panel inspection",
            },
            {
                "skill": "journeyman",
                "start_offset_h": 2,
                "duration_h": 4.0,
                "notes": "Wiring audit and load calculation",
            },
        ],
        "expenses": [
            {
                "category": "materials",
                "description": "Conduit fittings and hardware",
                "cost_cents": 12500,
                "markup_pct": 20.0,
            },
            {
                "category": "permits",
                "description": "Commercial electrical permit",
                "cost_cents": 35000,
                "markup_pct": 0.0,
            },
        ],
    },
    {
        "title": "Outlet Installation — Completed Job D",
        "days_ago": 15,
        "start_hour": 9,
        "end_hour": 12,
        "customer_idx": 0,  # John Smith (repeat customer)
        "time_entries": [
            {
                "skill": "journeyman",
                "start_offset_h": 0,
                "duration_h": 2.5,
                "notes": "Install 6 duplex outlets",
            },
        ],
        "expenses": [
            {
                "category": "materials",
                "description": "Duplex outlets and wall plates (qty 6)",
                "cost_cents": 4200,
                "markup_pct": 20.0,
            },
        ],
    },
    # SD-5 additions: Jobs E/F/G
    {
        "title": "HVAC Coordination — Completed Job E",
        "days_ago": 20,
        "start_hour": 10,
        "end_hour": 15,
        "customer_idx": 0,  # John Smith
        "time_entries": [
            {
                "skill": "journeyman",
                "start_offset_h": 0,
                "duration_h": 3.0,
                "notes": "Coordination with HVAC contractor",
            },
        ],
        "expenses": [
            {
                "category": "materials",
                "description": "Electrical supplies",
                "cost_cents": 8500,
                "markup_pct": 20.0,
            },
        ],
    },
    {
        "title": "Generator Hookup — Completed Job F",
        "days_ago": 35,
        "start_hour": 8,
        "end_hour": 14,
        "customer_idx": 1,  # Mary Johnson
        "time_entries": [
            {
                "skill": "master",
                "start_offset_h": 0,
                "duration_h": 4.0,
                "notes": "Generator transfer switch installation",
            },
        ],
        "expenses": [
            {
                "category": "materials",
                "description": "Transfer switch hardware",
                "cost_cents": 32000,
                "markup_pct": 20.0,
            },
        ],
    },
    {
        "title": "Commercial Rewire — Completed Job G",
        "days_ago": 75,
        "start_hour": 7,
        "end_hour": 16,
        "customer_idx": 2,  # Apex Commercial LLC
        "time_entries": [
            {
                "skill": "master",
                "start_offset_h": 0,
                "duration_h": 5.0,
                "notes": "Full commercial rewire",
            },
            {
                "skill": "journeyman",
                "start_offset_h": 3,
                "duration_h": 6.0,
                "notes": "Panel sub-feed installation",
            },
        ],
        "expenses": [
            {
                "category": "materials",
                "description": "Commercial wiring materials",
                "cost_cents": 65000,
                "markup_pct": 20.0,
            },
            {
                "category": "permits",
                "description": "Commercial electrical permit",
                "cost_cents": 45000,
                "markup_pct": 0.0,
            },
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_reporting.py — Group D reporting seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


def _get_tenant_id() -> UUID:
    return UUID(settings.TEST_TENANT_ID)


def _job_date(days_ago: int, hour: int) -> datetime:
    """Compute a fixed past UTC datetime."""
    return (ANCHOR_DATE - timedelta(days=days_ago)).replace(
        hour=hour, minute=0, second=0
    )


def mode_reset(tenant_id: UUID):
    """Wipe reporting scenario data only (child-first ordering)."""
    tid = str(tenant_id)
    # Identify jobs by title prefix to scope deletion
    job_titles = [j["title"] for j in REPORTING_JOBS]

    with get_db_session() as db:
        # CE-1: Delete invoice_signoff rows for this tenant first (FK to invoice)
        try:
            result = db.execute(
                text("DELETE FROM public.invoice_signoff WHERE tenant_id = :tid"),
                {"tid": tid},
            )
            if result.rowcount:
                print(f"  🗑  [invoice_signoff] Deleted {result.rowcount} row(s)")
        except Exception as e:
            print(f"  ⚠️  [invoice_signoff] {e}")

        # SD-7 Batch 2: Delete usage_ledger rows for this tenant first (no FKs to jobs)
        try:
            result = db.execute(
                text("DELETE FROM public.usage_ledger WHERE tenant_id = :tid"),
                {"tid": tid},
            )
            if result.rowcount:
                print(f"  🗑  [usage_ledger] Deleted {result.rowcount} row(s)")
        except Exception as e:
            print(f"  ⚠️  [usage_ledger] {e}")

        # SD-6: Delete loto_confirmation for this tenant first
        try:
            result = db.execute(
                text("DELETE FROM public.loto_confirmation WHERE tenant_id = :tid"),
                {"tid": tid},
            )
            if result.rowcount:
                print(f"  🗑  [loto_confirmation] Deleted {result.rowcount} row(s)")
        except Exception as e:
            print(f"  ⚠️  [loto_confirmation] {e}")

        # Find job IDs for our specific reporting jobs
        placeholders = ", ".join(f":t{i}" for i in range(len(job_titles)))
        params = {f"t{i}": title for i, title in enumerate(job_titles)}
        params["tid"] = tid

        job_rows = db.execute(
            text("""
                SELECT j.id FROM public.job j
                JOIN public.job_status js ON js.id = j.status_id
                WHERE j.tenant_id = :tid
                AND j.scheduled_start_at IS NOT NULL
                AND j.scheduled_start_at < NOW() - INTERVAL '10 days'
                AND j.status_id IN (
                    SELECT id FROM public.job_status WHERE code = 'completed' AND tenant_id IS NULL
                )
            """),
            {"tid": tid},
        ).fetchall()

        # Only delete if we actually seeded these (check via presence of time entries)
        job_ids_with_entries = []
        for jr in job_rows:
            has_entry = db.execute(
                text(
                    "SELECT 1 FROM public.job_time_entry WHERE job_id = :jid AND tenant_id = :tid LIMIT 1"
                ),
                {"jid": str(jr.id), "tid": tid},
            ).first()
            if has_entry:
                job_ids_with_entries.append(str(jr.id))

        if not job_ids_with_entries:
            print("  ℹ️  No reporting scenario jobs found to wipe")
        else:
            for job_id in job_ids_with_entries:
                # B19: Delete payments/lines then invoices before job deletion (FK order)
                invoice_ids = db.execute(
                    text(
                        "SELECT id FROM public.invoice WHERE tenant_id = :tid AND job_id = :jid"
                    ),
                    {"tid": tid, "jid": job_id},
                ).fetchall()
                for inv_row in invoice_ids:
                    # SD-6: Delete invoice_line_tax_component then invoice_line
                    try:
                        result = db.execute(
                            text(
                                "DELETE FROM public.invoice_line_tax_component WHERE tenant_id = :tid AND invoice_line_id IN (SELECT id FROM public.invoice_line WHERE invoice_id = :inv_id)"
                            ),
                            {"tid": tid, "inv_id": str(inv_row.id)},
                        )
                        if result.rowcount:
                            print(
                                f"  🗑  [invoice_line_tax_component] Deleted {result.rowcount} row(s)"
                            )
                    except Exception as e:
                        print(f"  ⚠️  [invoice_line_tax_component] {e}")
                    try:
                        result = db.execute(
                            text(
                                "DELETE FROM public.invoice_line WHERE tenant_id = :tid AND invoice_id = :inv_id"
                            ),
                            {"tid": tid, "inv_id": str(inv_row.id)},
                        )
                        if result.rowcount:
                            print(
                                f"  🗑  [invoice_line] Deleted {result.rowcount} row(s)"
                            )
                    except Exception as e:
                        print(f"  ⚠️  [invoice_line] {e}")
                    try:
                        result = db.execute(
                            text(
                                "DELETE FROM public.payment WHERE tenant_id = :tid AND invoice_id = :inv_id"
                            ),
                            {"tid": tid, "inv_id": str(inv_row.id)},
                        )
                        if result.rowcount:
                            print(
                                f"  🗑  [payment] Deleted {result.rowcount} row(s) for invoice {inv_row.id}"
                            )
                    except Exception as e:
                        print(f"  ⚠️  [payment] {e}")
                try:
                    result = db.execute(
                        text(
                            "DELETE FROM public.invoice WHERE tenant_id = :tid AND job_id = :jid"
                        ),
                        {"tid": tid, "jid": job_id},
                    )
                    if result.rowcount:
                        print(
                            f"  🗑  [invoice] Deleted {result.rowcount} invoice(s) for job {job_id}"
                        )
                except Exception as e:
                    print(f"  ⚠️  [invoice] {e}")

                for table in ["job_time_entry", "job_expense", "job_tech_assignment"]:
                    try:
                        result = db.execute(
                            text(
                                f"DELETE FROM public.{table} WHERE tenant_id = :tid AND job_id = :jid"
                            ),
                            {"tid": tid, "jid": job_id},
                        )
                        if result.rowcount:
                            print(
                                f"  🗑  [{table}] Deleted {result.rowcount} row(s) for job {job_id}"
                            )
                    except Exception as e:
                        print(f"  ⚠️  [{table}] {e}")

                # Delete the job itself
                try:
                    result = db.execute(
                        text(
                            "DELETE FROM public.job WHERE id = :jid AND tenant_id = :tid"
                        ),
                        {"jid": job_id, "tid": tid},
                    )
                    if result.rowcount:
                        print(f"  🗑  [job] Deleted job {job_id}")
                except Exception as e:
                    print(f"  ⚠️  [job] {e}")

        db.commit()

    print("\n✅ Reporting scenario data wiped.")
    print("   Run: python migrations/scripts/seed_scenario_reporting.py")
    print("   to re-seed.")


def mode_seed(tenant_id: UUID):
    """Seed reporting scenario jobs with time entries and expenses."""
    print("=== seed_scenario_reporting: seed mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        # Verify tech user exists
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
        completed_status_id = job_status_ids.get("completed")
        if not completed_status_id:
            print("  ❌ 'completed' job_status not found — run seed_core.py first")
            return

        # Look up labor rate hourly_rate_cents by skill_level_code for this tenant
        labor_rates = {
            row.skill_level_code: row.hourly_rate_cents
            for row in db.execute(
                text("""
                    SELECT skill_level_code, hourly_rate_cents
                    FROM public.labor_rate_version
                    WHERE tenant_id = :tid
                    ORDER BY skill_level_code
                """),
                {"tid": tid},
            ).fetchall()
        }
        if not labor_rates:
            print("  ❌ No labor_rate_version rows found for tenant.")
            print("     Run seed_test_tenant.py first, then retry.")
            return
        print(f"  ℹ️  Labor rates found: {labor_rates}")

        # Look up pricebook item IDs by SKU (IDs are gen_random_uuid() — change on every reseed)
        pricebook_item_ids = {
            row.sku: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, sku FROM public.pricebook_item WHERE tenant_id = :tid AND is_active = true"
                ),
                {"tid": tid},
            ).fetchall()
        }
        if not pricebook_item_ids:
            print("  ❌ No pricebook_item rows found for tenant.")
            print("     Run seed_scenario_quote_to_cash.py first, then retry.")
            return
        print(f"  ℹ️  Pricebook items found: {list(pricebook_item_ids.keys())}")

        # DB-MGMT-1 Task 4: Look up qco_line_type IDs by code (not hardcoded UUIDs)
        qco_line_type_ids = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.qco_line_type WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }

        # Get existing customers from quote-to-cash scenario
        customers = db.execute(
            text("""
                SELECT id FROM public.customer
                WHERE tenant_id = :tid AND is_active = true
                ORDER BY created_at
                LIMIT 5
            """),
            {"tid": tid},
        ).fetchall()
        if not customers:
            print("  ⚠️  No customers found. Run seed_scenario_quote_to_cash.py first.")
            return
        customer_ids = [str(c.id) for c in customers]
        print(f"  ℹ️  Found {len(customer_ids)} existing customer(s)")

        # Get a site for the first customer
        first_cust_id = customer_ids[0]
        site_row = db.execute(
            text(
                "SELECT id FROM public.site WHERE tenant_id = :tid AND customer_id = :cid LIMIT 1"
            ),
            {"tid": tid, "cid": first_cust_id},
        ).first()
        site_id = str(site_row.id) if site_row else None

        # ── Seed Jobs ─────────────────────────────────────────────────────────
        seeded_jobs = []

        for job_def in REPORTING_JOBS:
            cust_idx = min(job_def["customer_idx"], len(customer_ids) - 1)
            cust_id = customer_ids[cust_idx]

            scheduled_start = _job_date(job_def["days_ago"], job_def["start_hour"])
            scheduled_end = _job_date(job_def["days_ago"], job_def["end_hour"])

            # Idempotency: check by scheduled_start + status + customer
            existing = db.execute(
                text("""
                    SELECT j.id FROM public.job j
                    WHERE j.tenant_id = :tid
                    AND j.customer_id = :cid
                    AND j.status_id = :sid
                    AND j.scheduled_start_at = :sched_start
                    LIMIT 1
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "sid": completed_status_id,
                    "sched_start": scheduled_start,
                },
            ).first()

            if existing:
                print(f"  ℹ️  [job] '{job_def['title']}' already exists")
                seeded_jobs.append(
                    (str(existing.id), job_def, scheduled_start, scheduled_end)
                )
                continue

            # Compute labor cost from time entries
            total_labor_cost = 0
            for te in job_def["time_entries"]:
                rate = labor_rates.get(te["skill"], 8500)  # fallback to journeyman
                total_labor_cost += int(te["duration_h"] * rate)

            # Compute material cost from expenses
            total_material_cost = sum(
                e["cost_cents"]
                for e in job_def["expenses"]
                if e["category"] == "materials"
            )

            job_number = f"RPT-{len(seeded_jobs) + 1:03d}"
            job_result = db.execute(
                text("""
                    INSERT INTO public.job
                    (id, tenant_id, customer_id, site_id, status_id,
                     job_number, scheduled_start_at, scheduled_end_at,
                     actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents,
                     title,
                     is_active, version, created_at, updated_at)
                    VALUES
                    (gen_random_uuid(), :tid, :cid, :site_id, :status_id,
                     :job_number, :sched_start, :sched_end,
                     :labor_cost, :material_cost, 0,
                     :title,
                     true, 1, NOW(), NOW())
                    ON CONFLICT (tenant_id, job_number) DO NOTHING
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "site_id": site_id,
                    "status_id": completed_status_id,
                    "job_number": job_number,
                    "sched_start": scheduled_start,
                    "sched_end": scheduled_end,
                    "labor_cost": total_labor_cost,
                    "material_cost": total_material_cost,
                    "title": job_def.get("title"),
                },
            )
            job_row = job_result.first()
            if job_row is None:
                # Conflict: job_number already exists — look up existing row and UPDATE title
                existing_job = db.execute(
                    text("""
                        SELECT id FROM public.job
                        WHERE tenant_id = :tid AND job_number = :num
                        LIMIT 1
                    """),
                    {"tid": tid, "num": job_number},
                ).first()
                job_id = str(existing_job.id)
                # JOB-UI-B1: Idempotent UPDATE — set title on existing row
                db.execute(
                    text("""
                        UPDATE public.job SET title = :title, updated_at = NOW()
                        WHERE id = :jid AND tenant_id = :tid
                    """),
                    {"title": job_def.get("title"), "jid": job_id, "tid": tid},
                )
                print(
                    f"  ℹ️  [job] '{job_def['title']}' ({job_number}) already exists ({job_id})"
                )
            else:
                job_id = str(job_row.id)
                print(f"  ✅ [job] Created '{job_def['title']}' ({job_id})")
            seeded_jobs.append((job_id, job_def, scheduled_start, scheduled_end))

        # ── Seed Time Entries, Expenses, Assignments ─────────────────────────
        for job_id, job_def, job_start, job_end in seeded_jobs:
            # Time entries
            for te_def in job_def["time_entries"]:
                te_start = job_start + timedelta(hours=te_def["start_offset_h"])
                te_end = te_start + timedelta(hours=te_def["duration_h"])
                rate = labor_rates.get(te_def["skill"], 8500)
                total_cost = int(te_def["duration_h"] * rate)

                # Idempotency: check by job_id + user_id + started_at
                existing_te = db.execute(
                    text("""
                        SELECT id FROM public.job_time_entry
                        WHERE tenant_id = :tid AND job_id = :jid
                        AND user_id = :uid AND started_at = :started
                        LIMIT 1
                    """),
                    {
                        "tid": tid,
                        "jid": job_id,
                        "uid": str(TECH_USER_ID),
                        "started": te_start,
                    },
                ).first()
                if existing_te:
                    print(
                        f"  ℹ️  [job_time_entry] {te_def['skill']} entry already exists for job {job_id}"
                    )
                    continue

                db.execute(
                    text("""
                        INSERT INTO public.job_time_entry
                        (id, tenant_id, job_id, user_id, started_at, ended_at,
                         hours, hourly_rate_cents, total_cost_cents, notes,
                         created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :jid, :uid, :started, :ended,
                         :hours, :rate, :total, :notes,
                         NOW(), NOW())
                    """),
                    {
                        "tid": tid,
                        "jid": job_id,
                        "uid": str(TECH_USER_ID),
                        "started": te_start,
                        "ended": te_end,
                        "hours": te_def["duration_h"],
                        "rate": rate,
                        "total": total_cost,
                        "notes": te_def["notes"],
                    },
                )
                print(
                    f"  ✅ [job_time_entry] {te_def['skill'].upper()} "
                    f"{te_def['duration_h']}h @ {rate}¢/hr = ${total_cost / 100:.2f}"
                )

            # Expenses
            for exp_def in job_def["expenses"]:
                markup_pct = exp_def["markup_pct"]
                markup_amt = int(exp_def["cost_cents"] * markup_pct / 100)
                billable_cents = exp_def["cost_cents"] + markup_amt

                existing_exp = db.execute(
                    text("""
                        SELECT id FROM public.job_expense
                        WHERE tenant_id = :tid AND job_id = :jid
                        AND description = :desc
                        LIMIT 1
                    """),
                    {"tid": tid, "jid": job_id, "desc": exp_def["description"]},
                ).first()
                if existing_exp:
                    print(
                        f"  ℹ️  [job_expense] '{exp_def['description']}' already exists"
                    )
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
                        "jid": job_id,
                        "category": exp_def["category"],
                        "description": exp_def["description"],
                        "cost_cents": exp_def["cost_cents"],
                        "markup_pct": markup_pct,
                        "markup_amt": markup_amt,
                        "billable": billable_cents,
                        "uid": str(TECH_USER_ID),
                        "incurred_at": job_start,
                    },
                )
                print(
                    f"  ✅ [job_expense] {exp_def['category']}: '{exp_def['description']}' "
                    f"cost=${exp_def['cost_cents'] / 100:.2f} markup={markup_pct}%"
                )

            # Tech assignment
            existing_assign = db.execute(
                text("""
                    SELECT id FROM public.job_tech_assignment
                    WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid
                    LIMIT 1
                """),
                {"tid": tid, "jid": job_id, "uid": str(TECH_USER_ID)},
            ).first()
            if existing_assign:
                print(f"  ℹ️  [job_tech_assignment] Already assigned to job {job_id}")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.job_tech_assignment
                        (id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal,
                         assigned_at, is_active, version, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :jid, :uid, :assigned_by, 'primary', 1,
                         :assigned_at, true, 1, NOW(), NOW())
                    """),
                    {
                        "tid": tid,
                        "jid": job_id,
                        "uid": str(TECH_USER_ID),
                        "assigned_by": str(OWNER_USER_ID),
                        "assigned_at": job_start - timedelta(days=1),
                    },
                )
                print(f"  ✅ [job_tech_assignment] Assigned tech to job {job_id}")

        # ── Seed Invoices + Payments (B19) ──────────────────────────────────
        # Look up invoice_status IDs
        inv_status_rows = db.execute(
            text("SELECT id, code FROM public.invoice_status WHERE tenant_id IS NULL")
        ).fetchall()
        inv_status_map = {row.code: str(row.id) for row in inv_status_rows}
        paid_inv_status_id = inv_status_map.get("paid")
        issued_inv_status_id = inv_status_map.get("issued")
        draft_inv_status_id = inv_status_map.get("draft")
        partial_inv_status_id = inv_status_map.get("partial")
        void_inv_status_id = inv_status_map.get("void")
        writeoff_inv_status_id = inv_status_map.get("writeoff")

        if not all([paid_inv_status_id, issued_inv_status_id, draft_inv_status_id]):
            print("  ⚠️  Missing invoice_status codes — skipping invoice seeding")
        else:
            # Look up payment_status IDs
            pmt_status_row = db.execute(
                text(
                    "SELECT id FROM public.payment_status WHERE code = 'succeeded' AND tenant_id IS NULL LIMIT 1"
                )
            ).first()
            pmt_status_id = str(pmt_status_row.id) if pmt_status_row else None

            pmt_refunded_row = db.execute(
                text(
                    "SELECT id FROM public.payment_status WHERE code = 'refunded' AND tenant_id IS NULL LIMIT 1"
                )
            ).first()
            pmt_refunded_status_id = (
                str(pmt_refunded_row.id) if pmt_refunded_row else None
            )

            # Look up or create a manual_check payment_type
            pmt_type_row = db.execute(
                text(
                    "SELECT id FROM public.payment_type WHERE code = 'manual_check' AND tenant_id IS NULL LIMIT 1"
                )
            ).first()
            pmt_type_id = str(pmt_type_row.id) if pmt_type_row else None

            # Get or create a seed payment_method for this tenant
            pm_row = db.execute(
                text(
                    "SELECT id FROM public.payment_method WHERE tenant_id = :tid AND psp_provider = 'seed' LIMIT 1"
                ),
                {"tid": tid},
            ).first()
            if pm_row:
                seed_pm_id = str(pm_row.id)
            else:
                seed_pm_result = db.execute(
                    text("""
                        INSERT INTO public.payment_method
                        (id, tenant_id, payment_type_id, psp_provider, psp_payment_method_id,
                         brand, is_active, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :pmt_type_id, 'seed', 'seed-manual-check',
                         'Manual Check', true, NOW(), NOW())
                        RETURNING id
                    """),
                    {"tid": tid, "pmt_type_id": pmt_type_id},
                )
                seed_pm_id = str(seed_pm_result.first().id)
                print(
                    f"  ✅ [payment_method] Created seed manual_check method ({seed_pm_id})"
                )

            # Invoice spec per job (indices match seeded_jobs order: a=0..g=6)
            invoice_specs = [
                {
                    "letter": "a",
                    "subtotal_cents": 122700,
                    "tax_cents": 9816,
                    "total_cents": 132516,
                    "balance_due_cents": 0,
                    "issued_at_offset": -28,
                    "due_at_offset": -14,
                    "status_id": paid_inv_status_id,
                    "create_payment": True,
                },
                {
                    "letter": "b",
                    "subtotal_cents": 25000,
                    "tax_cents": 2000,
                    "total_cents": 27000,
                    "balance_due_cents": 0,
                    "issued_at_offset": -43,
                    "due_at_offset": -29,
                    "status_id": paid_inv_status_id,
                    "create_payment": True,
                },
                {
                    "letter": "c",
                    "subtotal_cents": 81818,
                    "tax_cents": 6545,
                    "total_cents": 88363,
                    "balance_due_cents": 88363,
                    "issued_at_offset": -55,
                    "due_at_offset": -25,
                    "status_id": issued_inv_status_id,
                    "create_payment": False,
                },
                {
                    "letter": "d",
                    "subtotal_cents": 21818,
                    "tax_cents": 1745,
                    "total_cents": 23563,
                    "balance_due_cents": 23563,
                    "issued_at_offset": -10,
                    "due_at_offset": 20,
                    "status_id": draft_inv_status_id,
                    "create_payment": False,
                },
                # SD-5: Jobs E/F/G — partial, void, writeoff
                {
                    "letter": "e",
                    "subtotal_cents": 41700,
                    "tax_cents": 3336,
                    "total_cents": 45036,
                    "balance_due_cents": 25036,
                    "issued_at_offset": -18,
                    "due_at_offset": -4,
                    "status_id": partial_inv_status_id,
                    "create_payment": True,
                    "payment_amount_override": 20000,
                },
                {
                    "letter": "f",
                    "subtotal_cents": 68400,
                    "tax_cents": 5472,
                    "total_cents": 73872,
                    "balance_due_cents": 73872,
                    "issued_at_offset": -33,
                    "due_at_offset": -19,
                    "status_id": void_inv_status_id,
                    "create_payment": False,
                },
                {
                    "letter": "g",
                    "subtotal_cents": 202000,
                    "tax_cents": 16160,
                    "total_cents": 218160,
                    "balance_due_cents": 218160,
                    "issued_at_offset": -72,
                    "due_at_offset": -42,
                    "status_id": writeoff_inv_status_id,
                    "create_payment": False,
                },
            ]

            for idx, (job_id, job_def, job_start, job_end) in enumerate(seeded_jobs):
                if idx >= len(invoice_specs):
                    break
                spec = invoice_specs[idx]

                # Skip if no status_id (status code may not be in DB)
                if not spec.get("status_id"):
                    print(
                        f"  ⚠️  [invoice] status_id missing for job_{spec['letter']} — skipping"
                    )
                    continue

                # Idempotency: skip if invoice already exists for this job
                existing_inv = db.execute(
                    text(
                        "SELECT id FROM public.invoice WHERE tenant_id = :tid AND job_id = :jid LIMIT 1"
                    ),
                    {"tid": tid, "jid": job_id},
                ).first()
                if existing_inv:
                    print(f"  ℹ️  [invoice] Already exists for job {job_id}")
                    continue

                issued_at = ANCHOR_DATE + timedelta(days=spec["issued_at_offset"])
                due_at = ANCHOR_DATE + timedelta(days=spec["due_at_offset"])
                # Map letter to INV-900XXX number (FIX-011)
                _letter_to_inv_num = {
                    "a": "INV-900002",
                    "b": "INV-900003",
                    "c": "INV-900004",
                    "d": "INV-900005",
                    "e": "INV-900006",
                    "f": "INV-900007",
                    "g": "INV-900008",
                }
                invoice_number = _letter_to_inv_num.get(
                    spec["letter"].lower(), f"INV-900-{spec['letter'].upper()}"
                )

                inv_result = db.execute(
                    text("""
                        INSERT INTO public.invoice
                        (id, tenant_id, invoice_number, customer_id, site_id, job_id, status_id,
                         subtotal_cents, tax_cents, total_cents, balance_due_cents,
                         currency, billing_mode, is_active, issued_at, due_at,
                         reminder_count, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :inv_num, :cid, :site_id, :jid, :status_id,
                         :subtotal, :tax, :total, :balance,
                         'USD', 'line_item', true, :issued_at, :due_at,
                         0, NOW(), NOW())
                        RETURNING id
                    """),
                    {
                        "tid": tid,
                        "inv_num": invoice_number,
                        "cid": customer_ids[min(idx, len(customer_ids) - 1)],
                        "site_id": site_id,
                        "jid": job_id,
                        "status_id": spec["status_id"],
                        "subtotal": spec["subtotal_cents"],
                        "tax": spec["tax_cents"],
                        "total": spec["total_cents"],
                        "balance": spec["balance_due_cents"],
                        "issued_at": issued_at,
                        "due_at": due_at,
                    },
                )
                inv_id = str(inv_result.first().id)
                print(
                    f"  ✅ [invoice] {invoice_number} (job_{spec['letter']}) "
                    f"total=${spec['total_cents'] / 100:.2f} status={inv_status_map.get(spec['letter'], '')}"
                )

                # Create payment for invoices that need one
                if spec["create_payment"] and pmt_status_id and seed_pm_id:
                    paid_at = ANCHOR_DATE + timedelta(days=spec["due_at_offset"])
                    payment_amount = spec.get(
                        "payment_amount_override", spec["total_cents"]
                    )
                    db.execute(
                        text("""
                            INSERT INTO public.payment
                            (id, tenant_id, invoice_id, payment_method_id, status_id,
                             amount_cents, paid_via, paid_at, is_active,
                             created_at, updated_at)
                            VALUES
                            (gen_random_uuid(), :tid, :inv_id, :pm_id, :status_id,
                             :amount, 'check', :paid_at, true,
                             NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "inv_id": inv_id,
                            "pm_id": seed_pm_id,
                            "status_id": pmt_status_id,
                            "amount": payment_amount,
                            "paid_at": paid_at,
                        },
                    )
                    print(
                        f"  ✅ [payment] ${payment_amount / 100:.2f} for invoice {invoice_number}"
                    )

            # ── D5: Refunded payment for Invoice B (SD-2 negative-amount model) ──────
            inv_b_row = db.execute(
                text(
                    "SELECT id FROM public.invoice WHERE tenant_id = :tid AND invoice_number = 'INV-900003' LIMIT 1"
                ),
                {"tid": tid},
            ).first()
            if inv_b_row and pmt_refunded_status_id and seed_pm_id:
                existing_refund = db.execute(
                    text(
                        "SELECT id FROM public.payment WHERE tenant_id = :tid AND invoice_id = :inv_id AND amount_cents = -3200 LIMIT 1"
                    ),
                    {"tid": tid, "inv_id": str(inv_b_row.id)},
                ).first()
                if existing_refund:
                    print("  ℹ️  [payment] Refund row for INV-900003 already exists")
                else:
                    anchor_minus_27d = ANCHOR_DATE - timedelta(days=27)
                    db.execute(
                        text("""
                            INSERT INTO public.payment
                            (id, tenant_id, invoice_id, payment_method_id, status_id,
                             amount_cents, paid_via, paid_at, is_active,
                             created_at, updated_at)
                            VALUES
                            (gen_random_uuid(), :tid, :inv_id, :pm_id, :status_id,
                             -3200, 'check', :paid_at, true,
                             NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "inv_id": str(inv_b_row.id),
                            "pm_id": seed_pm_id,
                            "status_id": pmt_refunded_status_id,
                            "paid_at": anchor_minus_27d,
                        },
                    )
                    print(
                        "  ✅ [payment] Refund row for INV-900003: amount_cents=-3200 (SD-2 negative-amount refund model)"
                    )
            elif not inv_b_row:
                print(
                    "  ℹ️  [payment] INV-900003 not found yet — refund will be created on next run"
                )

        # ── SD-6: Seed invoice_line + invoice_line_tax_component for all 7 reporting invoices ──
        print("\n  -- Seeding invoice lines for reporting invoices (SD-6) --")
        for letter, spec in INVOICE_LINE_SPECS.items():
            inv_row = db.execute(
                text(
                    "SELECT id FROM public.invoice WHERE tenant_id = :tid AND invoice_number = :inv_num LIMIT 1"
                ),
                {"tid": tid, "inv_num": spec["invoice_number"]},
            ).first()
            if not inv_row:
                print(
                    f"  ℹ️  [invoice_line] {spec['invoice_number']} not found — will be created on next run"
                )
                continue
            inv_id = str(inv_row.id)

            # Idempotency: skip if lines already exist
            existing_lines = db.execute(
                text(
                    "SELECT COUNT(*) FROM public.invoice_line WHERE invoice_id = :inv_id AND tenant_id = :tid"
                ),
                {"inv_id": inv_id, "tid": tid},
            ).scalar()
            if existing_lines:
                print(
                    f"  ℹ️  [invoice_line] {spec['invoice_number']} already has {existing_lines} line(s)"
                )
            else:
                for pos, (
                    qco_type_id,
                    item_sku,
                    description,
                    qty,
                    unit,
                    unit_price,
                    taxability,
                ) in enumerate(spec["lines"], start=1):
                    # Resolve SKU → live UUID (pricebook_item IDs change on every reseed)
                    pb_item_id = pricebook_item_ids.get(item_sku) if item_sku else None
                    # DB-MGMT-1 Task 4: resolve qco_line_type code → live UUID
                    qco_type_id = qco_line_type_ids.get(qco_type_id)
                    subtotal = unit_price * qty
                    is_taxable = taxability == "taxable"
                    tax_amount = round(subtotal * 0.06) if is_taxable else 0
                    total_cents = subtotal + tax_amount

                    line_result = db.execute(
                        text("""
                            INSERT INTO public.invoice_line
                            (id, invoice_id, source_type, source_id, position,
                             qco_line_type_id, pricebook_item_id, description,
                             quantity, unit, unit_price_cents, taxability_code,
                             subtotal_cents, total_cents,
                             tax_rate_pct, tax_basis_cents, tax_amount_cents,
                             tax_jurisdiction_code, tax_as_of, tax_source,
                             is_active, tenant_id, created_at, created_by)
                            VALUES (
                                gen_random_uuid(), :inv_id, 'ad_hoc', NULL, :pos,
                                :qco_type_id, :pb_item_id, :description,
                                :qty, :unit, :unit_price, :taxability,
                                :subtotal, :total_cents,
                                :tax_rate_pct, :tax_basis, :tax_amount,
                                :tax_jur_code, NOW(), :tax_source,
                                true, :tid, NOW(), NULL
                            )
                            RETURNING id
                        """),
                        {
                            "inv_id": inv_id,
                            "pos": pos,
                            "qco_type_id": qco_type_id,
                            "pb_item_id": pb_item_id,
                            "description": description,
                            "qty": qty,
                            "unit": unit,
                            "unit_price": unit_price,
                            "taxability": taxability,
                            "subtotal": subtotal,
                            "total_cents": total_cents,
                            "tax_rate_pct": "6.00" if is_taxable else None,
                            "tax_basis": subtotal if is_taxable else None,
                            "tax_amount": tax_amount if is_taxable else None,
                            "tax_jur_code": "US-DEFAULT" if is_taxable else None,
                            "tax_source": "manual_rate" if is_taxable else None,
                            "tid": tid,
                        },
                    )
                    line_id = str(line_result.first().id)
                    print(
                        f"    ✅ [invoice_line] {spec['invoice_number']} pos={pos} '{description}' ×{qty} = ${subtotal / 100:.2f}"
                    )

                    if is_taxable:
                        db.execute(
                            text("""
                                INSERT INTO public.invoice_line_tax_component
                                (id, invoice_line_id, tax_rate_version_id, component_code,
                                 rate_pct, amount_cents, is_active, tenant_id, created_at, created_by)
                                VALUES (gen_random_uuid(), :line_id, :trv_id, 'US-DEFAULT',
                                        6.00, :amount_cents, true, :tid, NOW(), NULL)
                            """),
                            {
                                "line_id": line_id,
                                "trv_id": TAX_RATE_VERSION_ID,
                                "amount_cents": tax_amount,
                                "tid": tid,
                            },
                        )

            # Always UPDATE invoice totals to match computed line math
            db.execute(
                text("""
                    UPDATE public.invoice
                    SET subtotal_cents = :subtotal,
                        tax_cents      = :tax,
                        total_cents    = :total,
                        balance_due_cents = :balance
                    WHERE id = :inv_id AND tenant_id = :tid
                """),
                {
                    "subtotal": spec["subtotal_cents"],
                    "tax": spec["tax_cents"],
                    "total": spec["total_cents"],
                    "balance": spec["balance_due_cents"],
                    "inv_id": inv_id,
                    "tid": tid,
                },
            )
            print(
                f"  ✅ [invoice] {spec['invoice_number']} totals updated: total={spec['total_cents']}¢  balance={spec['balance_due_cents']}¢"
            )

            # UPDATE payment amount_cents for paid/partial invoices
            if spec.get("update_payment"):
                new_pmt_amount = spec["new_payment_amount"]
                pmt_row = db.execute(
                    text(
                        "SELECT id FROM public.payment WHERE tenant_id = :tid AND invoice_id = :inv_id AND amount_cents > 0 LIMIT 1"
                    ),
                    {"tid": tid, "inv_id": inv_id},
                ).first()
                if pmt_row:
                    db.execute(
                        text(
                            "UPDATE public.payment SET amount_cents = :amt WHERE id = :pmt_id AND tenant_id = :tid"
                        ),
                        {"amt": new_pmt_amount, "pmt_id": str(pmt_row.id), "tid": tid},
                    )
                    print(
                        f"  ✅ [payment] {spec['invoice_number']} payment updated → {new_pmt_amount}¢"
                    )

        # ── SD-6: Seed loto_confirmation rows (Task 3) ────────────────────────
        print("\n  -- Seeding loto_confirmation rows (SD-6) --")
        loto_specs = [
            {
                "invoice_number": "INV-900002",
                "days_offset": -30,
                "hour_offset": 9,
                "minute_offset": 15,
                "server_offset_seconds": 2,
            },
            {
                "invoice_number": "INV-900008",
                "days_offset": -75,
                "hour_offset": 8,
                "minute_offset": 0,
                "server_offset_seconds": 5,
            },
        ]
        for loto_spec in loto_specs:
            # Look up job_id via invoice_number
            inv_for_loto = db.execute(
                text(
                    "SELECT job_id FROM public.invoice WHERE tenant_id = :tid AND invoice_number = :inv_num LIMIT 1"
                ),
                {"tid": tid, "inv_num": loto_spec["invoice_number"]},
            ).first()
            if not inv_for_loto or not inv_for_loto.job_id:
                print(
                    f"  ℹ️  [loto_confirmation] {loto_spec['invoice_number']} job not found — skipping"
                )
                continue
            loto_job_id = str(inv_for_loto.job_id)

            # Idempotency: skip if already exists for this job
            existing_loto = db.execute(
                text(
                    "SELECT id FROM public.loto_confirmation WHERE tenant_id = :tid AND job_id = :jid LIMIT 1"
                ),
                {"tid": tid, "jid": loto_job_id},
            ).first()
            if existing_loto:
                print(
                    f"  ℹ️  [loto_confirmation] Already exists for {loto_spec['invoice_number']} job"
                )
                continue

            confirmed_at = (
                ANCHOR_DATE + timedelta(days=loto_spec["days_offset"])
            ).replace(
                hour=loto_spec["hour_offset"],
                minute=loto_spec["minute_offset"],
                second=0,
                microsecond=0,
            )
            server_received_at = confirmed_at + timedelta(
                seconds=loto_spec["server_offset_seconds"]
            )

            db.execute(
                text("""
                    INSERT INTO public.loto_confirmation
                    (id, tenant_id, job_id, user_id,
                     confirmed_at, client_capture_at, server_received_at,
                     is_active, created_at, created_by)
                    VALUES (
                        gen_random_uuid(), :tid, :job_id, :user_id,
                        :confirmed_at, :confirmed_at, :server_received_at,
                        true, :confirmed_at, NULL
                    )
                """),
                {
                    "tid": tid,
                    "job_id": loto_job_id,
                    "user_id": str(TECH_USER_ID),
                    "confirmed_at": confirmed_at,
                    "server_received_at": server_received_at,
                },
            )
            print(
                f"  ✅ [loto_confirmation] Created for {loto_spec['invoice_number']} job at {confirmed_at.date()}"
            )

        # ── FIX-007: AR Aging Invoices (INV-900009 through INV-900014) ──────────
        print("\n  -- FIX-007: Seeding AR aging invoices --")

        # Get first customer and site for AR aging invoices
        aging_cust_row = db.execute(
            text(
                "SELECT id FROM public.customer WHERE tenant_id = :tid AND is_active = true ORDER BY created_at LIMIT 1"
            ),
            {"tid": tid},
        ).first()
        aging_site_row = db.execute(
            text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tid},
        ).first()

        if aging_cust_row and aging_site_row:
            aging_cust_id = str(aging_cust_row.id)
            aging_site_id = str(aging_site_row.id)

            # AR aging invoice specs — using NOW() relative dates so buckets stay accurate
            ar_aging_specs = [
                {
                    "invoice_number": "INV-900009",
                    "status_code": "issued",
                    "issued_days_ago": 5,
                    "due_days_from_now": 10,
                    "balance_due_cents": 85000,
                    "total_cents": 85000,
                    "subtotal_cents": 80189,
                    "tax_cents": 4811,
                    "create_payment": False,
                    "note": "Current (not yet overdue)",
                },
                {
                    "invoice_number": "INV-900010",
                    "status_code": "issued",
                    "issued_days_ago": 20,
                    "due_days_from_now": 5,
                    "balance_due_cents": 145000,
                    "total_cents": 145000,
                    "subtotal_cents": 136792,
                    "tax_cents": 8208,
                    "create_payment": False,
                    "note": "Current (due soon)",
                },
                {
                    "invoice_number": "INV-900011",
                    "status_code": "issued",
                    "issued_days_ago": 35,
                    "due_days_ago": 5,
                    "balance_due_cents": 62500,
                    "total_cents": 62500,
                    "subtotal_cents": 58962,
                    "tax_cents": 3538,
                    "create_payment": False,
                    "note": "30+ days bucket",
                },
                {
                    "invoice_number": "INV-900012",
                    "status_code": "issued",
                    "issued_days_ago": 55,
                    "due_days_ago": 25,
                    "balance_due_cents": 189000,
                    "total_cents": 189000,
                    "subtotal_cents": 178302,
                    "tax_cents": 10698,
                    "create_payment": False,
                    "note": "60+ days bucket",
                },
                {
                    "invoice_number": "INV-900013",
                    "status_code": "issued",
                    "issued_days_ago": 95,
                    "due_days_ago": 65,
                    "balance_due_cents": 340000,
                    "total_cents": 340000,
                    "subtotal_cents": 320755,
                    "tax_cents": 19245,
                    "create_payment": False,
                    "note": "90+ days bucket",
                },
                {
                    "invoice_number": "INV-900014",
                    "status_code": "partial",
                    "issued_days_ago": 45,
                    "due_days_ago": 15,
                    "balance_due_cents": 52000,
                    "total_cents": 102000,
                    "subtotal_cents": 96226,
                    "tax_cents": 5774,
                    "create_payment": True,
                    "payment_amount": 50000,
                    "payment_days_ago": 30,
                    "note": "Partial — has a payment recorded",
                },
            ]

            today_utc = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            for ar_spec in ar_aging_specs:
                # Idempotency: skip if already exists
                existing_ar = db.execute(
                    text(
                        "SELECT id FROM public.invoice WHERE tenant_id = :tid AND invoice_number = :inv_num LIMIT 1"
                    ),
                    {"tid": tid, "inv_num": ar_spec["invoice_number"]},
                ).first()
                if existing_ar:
                    print(f"  ℹ️  [invoice] {ar_spec['invoice_number']} already exists")
                    continue

                ar_status_id = inv_status_map.get(ar_spec["status_code"])
                if not ar_status_id:
                    print(
                        f"  ⚠️  [invoice] status '{ar_spec['status_code']}' not found — skipping {ar_spec['invoice_number']}"
                    )
                    continue

                issued_at = today_utc - timedelta(days=ar_spec["issued_days_ago"])
                if "due_days_from_now" in ar_spec:
                    due_at = today_utc + timedelta(days=ar_spec["due_days_from_now"])
                else:
                    due_at = today_utc - timedelta(days=ar_spec["due_days_ago"])

                ar_inv_result = db.execute(
                    text("""
                        INSERT INTO public.invoice
                        (id, tenant_id, invoice_number, customer_id, site_id, status_id,
                         subtotal_cents, tax_cents, total_cents, balance_due_cents,
                         currency, billing_mode, is_active, issued_at, due_at,
                         reminder_count, created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tid, :inv_num, :cid, :site_id, :status_id,
                         :subtotal, :tax, :total, :balance,
                         'USD', 'line_item', true, :issued_at, :due_at,
                         0, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                        RETURNING id
                    """),
                    {
                        "tid": tid,
                        "inv_num": ar_spec["invoice_number"],
                        "cid": aging_cust_id,
                        "site_id": aging_site_id,
                        "status_id": ar_status_id,
                        "subtotal": ar_spec["subtotal_cents"],
                        "tax": ar_spec["tax_cents"],
                        "total": ar_spec["total_cents"],
                        "balance": ar_spec["balance_due_cents"],
                        "issued_at": issued_at,
                        "due_at": due_at,
                    },
                )
                ar_inv_row = ar_inv_result.first()
                if not ar_inv_row:
                    print(
                        f"  ℹ️  [invoice] {ar_spec['invoice_number']} insert returned no row (conflict?)"
                    )
                    continue

                ar_inv_id = str(ar_inv_row.id)
                print(
                    f"  ✅ [invoice] {ar_spec['invoice_number']} — {ar_spec['note']} (balance=${ar_spec['balance_due_cents'] / 100:.2f})"
                )

                # Create payment for INV-900014 (partial)
                if ar_spec["create_payment"] and pmt_status_id and seed_pm_id:
                    payment_date = today_utc - timedelta(
                        days=ar_spec["payment_days_ago"]
                    )
                    db.execute(
                        text("""
                            INSERT INTO public.payment
                            (id, tenant_id, invoice_id, payment_method_id, status_id,
                             amount_cents, paid_via, paid_at, is_active,
                             created_at, updated_at)
                            VALUES
                            (gen_random_uuid(), :tid, :inv_id, :pm_id, :status_id,
                             :amount, 'check', :paid_at, true,
                             NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "inv_id": ar_inv_id,
                            "pm_id": seed_pm_id,
                            "status_id": pmt_status_id,
                            "amount": ar_spec["payment_amount"],
                            "paid_at": payment_date,
                        },
                    )
                    print(
                        f"  ✅ [payment] ${ar_spec['payment_amount'] / 100:.2f} partial payment for {ar_spec['invoice_number']}"
                    )
        else:
            print(
                "  ⚠️  [invoice] No customer/site found for AR aging invoices — run seed_scenario_quote_to_cash.py first"
            )

        # ── SD-7 Batch 2: usage_ledger rows (voice AI + outbound SMS) ───────────
        # Schema: id (bigint serial), tenant_id, subscription_id (nullable),
        #   product_feature_code, occurred_at, quantity (numeric, default 1),
        #   entity_type_code (nullable), entity_id (nullable),
        #   idempotency_key (varchar, NOT NULL), is_reported (bool, default false),
        #   reported_at (nullable), contextdata (jsonb, nullable),
        #   created_at (NOT NULL), created_by (nullable)
        #
        # Seed current-period voice AI minutes + outbound SMS segment entries.
        print("\n  -- SD-7 Batch 2: usage_ledger rows --")

        # Get subscription_id for test tenant
        sub_row_ul = db.execute(
            text("SELECT id FROM public.subscription WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tid},
        ).first()
        sub_id_ul = str(sub_row_ul.id) if sub_row_ul else None

        # Current billing period anchor
        period_anchor = ANCHOR_DATE

        usage_ledger_rows = [
            # voice_ai_minutes — 8 entries (spread over billing period)
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 5,
                "occurred_offset_days": 28,
                "idempotency_key": "ul-voice-ai-2026-07-03-001",
                "context": {
                    "session_duration_seconds": 300,
                    "model": "whisper-large-v3",
                },
            },
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 8,
                "occurred_offset_days": 25,
                "idempotency_key": "ul-voice-ai-2026-07-06-001",
                "context": {
                    "session_duration_seconds": 480,
                    "model": "whisper-large-v3",
                },
            },
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 6,
                "occurred_offset_days": 21,
                "idempotency_key": "ul-voice-ai-2026-07-10-001",
                "context": {
                    "session_duration_seconds": 360,
                    "model": "whisper-large-v3",
                },
            },
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 7,
                "occurred_offset_days": 18,
                "idempotency_key": "ul-voice-ai-2026-07-13-001",
                "context": {
                    "session_duration_seconds": 420,
                    "model": "whisper-large-v3",
                },
            },
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 4,
                "occurred_offset_days": 14,
                "idempotency_key": "ul-voice-ai-2026-07-17-001",
                "context": {
                    "session_duration_seconds": 240,
                    "model": "whisper-large-v3",
                },
            },
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 5,
                "occurred_offset_days": 11,
                "idempotency_key": "ul-voice-ai-2026-07-20-001",
                "context": {
                    "session_duration_seconds": 300,
                    "model": "whisper-large-v3",
                },
            },
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 4,
                "occurred_offset_days": 7,
                "idempotency_key": "ul-voice-ai-2026-07-24-001",
                "context": {
                    "session_duration_seconds": 240,
                    "model": "whisper-large-v3",
                },
            },
            {
                "feature_code": "voice_ai_minutes",
                "quantity": 3,
                "occurred_offset_days": 3,
                "idempotency_key": "ul-voice-ai-2026-07-28-001",
                "context": {
                    "session_duration_seconds": 180,
                    "model": "whisper-large-v3",
                },
            },
            # outbound_sms_segments — 5 entries (SMS reminder batches)
            {
                "feature_code": "outbound_sms_segments",
                "quantity": 3,
                "occurred_offset_days": 26,
                "idempotency_key": "ul-sms-2026-07-05-001",
                "context": {"template": "on_my_way", "recipient_count": 3},
            },
            {
                "feature_code": "outbound_sms_segments",
                "quantity": 4,
                "occurred_offset_days": 22,
                "idempotency_key": "ul-sms-2026-07-09-001",
                "context": {"template": "invoice_sent", "recipient_count": 4},
            },
            {
                "feature_code": "outbound_sms_segments",
                "quantity": 4,
                "occurred_offset_days": 17,
                "idempotency_key": "ul-sms-2026-07-14-001",
                "context": {"template": "dunning_reminder", "recipient_count": 4},
            },
            {
                "feature_code": "outbound_sms_segments",
                "quantity": 3,
                "occurred_offset_days": 12,
                "idempotency_key": "ul-sms-2026-07-19-001",
                "context": {"template": "appointment_reminder", "recipient_count": 3},
            },
            {
                "feature_code": "outbound_sms_segments",
                "quantity": 4,
                "occurred_offset_days": 5,
                "idempotency_key": "ul-sms-2026-07-26-001",
                "context": {"template": "on_my_way", "recipient_count": 4},
            },
        ]

        import json as _json_ul

        for ul_row in usage_ledger_rows:
            # Idempotency: check by idempotency_key (unique per tenant)
            existing_ul = db.execute(
                text("""
                    SELECT id FROM public.usage_ledger
                    WHERE tenant_id = :tid AND idempotency_key = :idem_key
                    LIMIT 1
                """),
                {"tid": tid, "idem_key": ul_row["idempotency_key"]},
            ).first()
            if existing_ul:
                print(
                    f"  ℹ️  [usage_ledger] '{ul_row['idempotency_key']}' already exists"
                )
                continue

            occurred = period_anchor - timedelta(days=ul_row["occurred_offset_days"])
            db.execute(
                text("""
                    INSERT INTO public.usage_ledger
                    (tenant_id, subscription_id, product_feature_code,
                     occurred_at, quantity, idempotency_key,
                     is_reported, contextdata, created_at, created_by)
                    VALUES (
                        :tid, :sub_id, :feat_code,
                        :occurred_at, :quantity, :idem_key,
                        false, CAST(:context AS jsonb), :occurred_at, NULL
                    )
                """),
                {
                    "tid": tid,
                    "sub_id": sub_id_ul,
                    "feat_code": ul_row["feature_code"],
                    "occurred_at": occurred,
                    "quantity": ul_row["quantity"],
                    "idem_key": ul_row["idempotency_key"],
                    "context": _json_ul.dumps(ul_row["context"]),
                },
            )
            print(
                f"  ✅ [usage_ledger] {ul_row['feature_code']}  qty={ul_row['quantity']}  "
                f"key={ul_row['idempotency_key']}"
            )

        # ── SD-7 Batch 3: Update job_time_entry with GPS, ETC, mobile capture fields ──
        print("\n  -- SD-7 B3: Updating job_time_entry GPS/ETC/capture fields --")

        # Apply hours_remaining_estimate, client_capture_at, server_received_at to ALL entries
        # Apply check_in_lat/lng to entries for NY/TX jobs; gps_variance=450 on 1 entry
        # Strategy: get all time entries for this tenant, then update in batches

        te_rows = db.execute(
            text("""
                SELECT jte.id, jte.started_at, ROW_NUMBER() OVER (ORDER BY jte.started_at) AS rn
                FROM public.job_time_entry jte
                WHERE jte.tenant_id = :tid
                ORDER BY jte.started_at
            """),
            {"tid": tid},
        ).fetchall()

        # NY coords: 40.6892, -74.0445  TX coords: 30.2672, -97.7431
        # Apply NY to first 4 entries, TX to next 3, remaining get NY as default
        ny_lat, ny_lng = "40.6892", "-74.0445"
        tx_lat, tx_lng = "30.2672", "-97.7431"

        for te in te_rows:
            te_id = str(te.id)
            started_at = te.started_at
            rn = te.rn

            # Assign coords: first 4 rows → NY, rows 5-7 → TX, rest → NY
            if rn <= 4 or rn > 7:
                lat, lng = ny_lat, ny_lng
            else:
                lat, lng = tx_lat, tx_lng

            # gps_variance_meters=450 on first entry only (near 500m threshold)
            gps_variance = 450 if rn == 1 else None

            # hours_remaining — estimate decreasing per entry
            # Use 4.0 minus (rn-1)*0.5, clamp to 0.5 min
            hrs_remaining = max(0.5, 4.0 - (rn - 1) * 0.3)

            db.execute(
                text("""
                    UPDATE public.job_time_entry
                    SET check_in_lat = :lat,
                        check_in_lng = :lng,
                        gps_variance_meters = :gps_variance,
                        hours_remaining_estimate = :hrs_remaining,
                        client_capture_at = :started_at - INTERVAL '2 seconds',
                        server_received_at = :started_at + INTERVAL '3 seconds',
                        updated_at = NOW()
                    WHERE id = :te_id AND tenant_id = :tid
                """),
                {
                    "lat": lat,
                    "lng": lng,
                    "gps_variance": gps_variance,
                    "hrs_remaining": hrs_remaining,
                    "started_at": started_at,
                    "te_id": te_id,
                    "tid": tid,
                },
            )

        print(
            f"  ✅ [job_time_entry] Updated {len(te_rows)} entries with GPS coords, ETC, mobile capture timestamps"
        )
        if te_rows:
            print(
                "      Row 1 gps_variance=450 (threshold test)  |  NY coords (40.6892, -74.0445)  |  TX (30.2672, -97.7431) on rows 5-7"
            )

        # ── SD-7 Batch 3: Update job_expense with vendor_name and capture timestamps ──
        print(
            "\n  -- SD-7 B3: Updating job_expense vendor_name and capture timestamps --"
        )

        exp_rows = db.execute(
            text("""
                SELECT id, job_expense_category_code, incurred_at
                FROM public.job_expense
                WHERE tenant_id = :tid
                ORDER BY incurred_at
            """),
            {"tid": tid},
        ).fetchall()

        for exp in exp_rows:
            exp_id = str(exp.id)
            cat = exp.job_expense_category_code
            incurred_at = exp.incurred_at

            # Assign vendor_name based on category
            if cat == "materials":
                vendor_name = "Home Depot"
            elif cat == "permits":
                vendor_name = "City Permit Office"
            else:
                vendor_name = "Home Depot"  # fallback for equipment

            db.execute(
                text("""
                    UPDATE public.job_expense
                    SET vendor_name = :vendor_name,
                        client_capture_at = :incurred_at - INTERVAL '1 second',
                        server_received_at = :incurred_at + INTERVAL '5 seconds',
                        updated_at = NOW()
                    WHERE id = :exp_id AND tenant_id = :tid
                """),
                {
                    "vendor_name": vendor_name,
                    "incurred_at": incurred_at,
                    "exp_id": exp_id,
                    "tid": tid,
                },
            )

        print(
            f"  ✅ [job_expense] Updated {len(exp_rows)} expenses with vendor_name and mobile capture timestamps"
        )

        db.commit()

        # ── CLASS-B1: Assign job_type_id to 7 reporting scenario jobs ──────
        print("\n  -- CLASS-B1: job_type_id on reporting jobs --")
        job_type_map = {
            row.code: str(row.id)
            for row in db.execute(
                text("SELECT id, code FROM public.job_type WHERE tenant_id IS NULL")
            ).fetchall()
        }
        if not job_type_map:
            print("  ⚠️  [job_type] No platform defaults found — run seed_core.py first")
        else:
            # Map invoice_number → job_type_code (per design §F.2)
            # Panel Upgrade A→panel_upgrade, Service Call B→service_call,
            # Commercial Inspection C→inspection, Outlet Install D→service_call,
            # HVAC Coord E→other, Generator Hookup F→generator_install,
            # Commercial Rewire G→rewire
            inv_to_type = {
                "INV-SEED-A": "panel_upgrade",
                "INV-SEED-B": "service_call",
                "INV-SEED-C": "inspection",
                "INV-SEED-D": "service_call",
                "INV-SEED-E": "other",
                "INV-SEED-F": "generator_install",
                "INV-SEED-G": "rewire",
            }
            for inv_num, type_code in inv_to_type.items():
                jt_id = job_type_map.get(type_code)
                if not jt_id:
                    print(
                        f"  ⚠️  [job_type] '{type_code}' not found — skipping {inv_num}"
                    )
                    continue
                job_row = db.execute(
                    text("""
                        SELECT j.id FROM public.invoice inv
                        JOIN public.job j ON j.id = inv.job_id
                        WHERE inv.invoice_number = :inv_num
                          AND inv.tenant_id = :tid
                    """),
                    {"inv_num": inv_num, "tid": tid},
                ).first()
                if not job_row:
                    print(f"  ⚠️  [job_type] Invoice {inv_num} not found — skipping")
                    continue
                existing = db.execute(
                    text("SELECT job_type_id FROM public.job WHERE id = :jid"),
                    {"jid": str(job_row.id)},
                ).first()
                if existing and existing.job_type_id:
                    print(f"  ℹ️  [job_type] {inv_num} already has job_type_id")
                    continue
                db.execute(
                    text("""
                        UPDATE public.job
                        SET job_type_id = CAST(:jt_id AS uuid), priority = 'standard',
                            updated_at = NOW()
                        WHERE id = :jid AND tenant_id = :tid
                    """),
                    {"jt_id": jt_id, "jid": str(job_row.id), "tid": tid},
                )
                print(f"  ✅ [job_type] {inv_num} → type={type_code}")
            db.commit()

        # ── CE-1: Overpayment variance + invoice signoff seed data ────────────
        print("\n  -- CE-1: Seeding overpayment variance + invoice signoff --")

        # 1. Overpaid payment with amount_variance_cents = 1500, unresolved
        #    Use INV-900002 (job_a, paid invoice) — add variance to existing payment
        inv_a_row = db.execute(
            text(
                "SELECT id FROM public.invoice WHERE tenant_id = :tid AND invoice_number = 'INV-900002' LIMIT 1"
            ),
            {"tid": tid},
        ).first()
        if inv_a_row:
            inv_a_id = str(inv_a_row.id)
            # Find the existing succeeded payment for this invoice
            pmt_a_row = db.execute(
                text("""
                    SELECT id FROM public.payment
                    WHERE tenant_id = :tid AND invoice_id = :inv_id
                      AND amount_cents > 0 AND is_active = true
                    LIMIT 1
                """),
                {"tid": tid, "inv_id": inv_a_id},
            ).first()
            if pmt_a_row:
                # Idempotency: only set variance if not already set
                existing_variance = db.execute(
                    text("""
                        SELECT amount_variance_cents FROM public.payment
                        WHERE id = :pmt_id AND tenant_id = :tid
                    """),
                    {"pmt_id": str(pmt_a_row.id), "tid": tid},
                ).first()
                if existing_variance and existing_variance.amount_variance_cents:
                    print(
                        f"  ℹ️  [payment] INV-900002 already has variance_cents={existing_variance.amount_variance_cents}"
                    )
                else:
                    db.execute(
                        text("""
                            UPDATE public.payment
                            SET amount_variance_cents = 1500,
                                updated_at = NOW()
                            WHERE id = :pmt_id AND tenant_id = :tid
                        """),
                        {"pmt_id": str(pmt_a_row.id), "tid": tid},
                    )
                    print(
                        "  ✅ [payment] INV-900002 payment variance_cents=1500 (unresolved — populates web review banner)"
                    )
            else:
                print(
                    "  ℹ️  [payment] INV-900002 has no succeeded payment — skipping variance"
                )
        else:
            print(
                "  ℹ️  [invoice] INV-900002 not found — variance seed will retry on next run"
            )

        # 2. Invoice signoff row on INV-900002 (completed-job invoice)
        #    Look up FKs by business key at runtime — never hardcode scenario UUIDs
        if inv_a_row:
            # Check if signoff already exists for this invoice
            existing_signoff = db.execute(
                text("""
                    SELECT id FROM public.invoice_signoff
                    WHERE tenant_id = :tid AND invoice_id = :inv_id
                      AND superseded_at IS NULL
                    LIMIT 1
                """),
                {"tid": tid, "inv_id": inv_a_id},
            ).first()
            if existing_signoff:
                print("  ℹ️  [invoice_signoff] INV-900002 already has an active signoff")
            else:
                # Generate a deterministic signoff_id for the S3 key
                signoff_id = str(uuid.uuid4())
                # Build S3 object key per build_signature_object_key() shape
                object_key = f"signatures/{tid}/{inv_a_id}/{signoff_id}.png"

                # Minimal valid 1x1 PNG (67 bytes)
                _minimal_png_b64 = (
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk"
                    "YPj/HwAEAQH/D6i1TAAAAABJRU5ErkJggg=="
                )
                png_bytes = base64.b64decode(_minimal_png_b64)

                # Attempt S3 upload — on failure, log + skip the object but keep the row
                s3_uploaded = False
                try:
                    from services.s3_service import put_signature_object

                    put_signature_object(object_key, png_bytes)
                    s3_uploaded = True
                    print(f"  ✅ [s3] Signature uploaded to {object_key}")
                except Exception as e:
                    print(
                        f"  ⚠️  [s3] Signature upload failed ({e}) — keeping row with object_key only"
                    )

                signed_at = ANCHOR_DATE + timedelta(days=-14)
                db.execute(
                    text("""
                        INSERT INTO public.invoice_signoff
                        (id, tenant_id, invoice_id, signed_by_name,
                         signature_object_key, terms_acknowledged,
                         signed_at, client_capture_at, captured_by_user_id,
                         superseded_at, idempotency_key,
                         created_at, updated_at, created_by, updated_by)
                        VALUES (
                            :id, :tid, :inv_id, 'John Customer',
                            :object_key, true,
                            :signed_at, :signed_at, :captured_by,
                            NULL, 'seed-ce1-signoff-inv900002',
                            NOW(), NOW(), NULL, NULL
                        )
                    """),
                    {
                        "id": signoff_id,
                        "tid": tid,
                        "inv_id": inv_a_id,
                        "object_key": object_key,
                        "signed_at": signed_at,
                        "captured_by": str(TECH_USER_ID),
                    },
                )
                print(
                    f"  ✅ [invoice_signoff] Created for INV-900002 "
                    f"(signed_by='John Customer', s3_uploaded={s3_uploaded})"
                )

        db.commit()

    print(
        f"\n🎉 seed_scenario_reporting complete — Group D reporting data present for {tenant_id}"
    )


def mode_inspect(tenant_id: UUID):
    """Show current state of reporting scenario data."""
    print("=== seed_scenario_reporting: inspect mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        # Completed jobs with time entries
        jobs = db.execute(
            text("""
                SELECT j.id, js.code AS status, j.scheduled_start_at, j.scheduled_end_at,
                       j.actual_labor_cost_cents, j.actual_material_cost_cents
                FROM public.job j
                JOIN public.job_status js ON js.id = j.status_id
                WHERE j.tenant_id = :tid AND js.code = 'completed'
                ORDER BY j.scheduled_start_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job (completed)]  {len(jobs)} row(s)")
        for j in jobs:
            print(
                f"    • {j.id}  {j.scheduled_start_at} → {j.scheduled_end_at}"
                f"  labor=${j.actual_labor_cost_cents / 100:.2f}"
                f"  materials=${j.actual_material_cost_cents / 100:.2f}"
            )
        print()

        # Time entries — SD-7 Batch 3: GPS coords, ETC, capture timestamps
        entries = db.execute(
            text("""
                SELECT jte.id, jte.job_id, jte.hours, jte.hourly_rate_cents,
                       jte.total_cost_cents, jte.notes,
                       jte.check_in_lat, jte.check_in_lng, jte.gps_variance_meters,
                       jte.hours_remaining_estimate, jte.client_capture_at, jte.server_received_at
                FROM public.job_time_entry jte
                WHERE jte.tenant_id = :tid
                ORDER BY jte.started_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job_time_entry]  {len(entries)} row(s)")
        for e in entries:
            gps_str = (
                f"  gps=({e.check_in_lat},{e.check_in_lng})" if e.check_in_lat else ""
            )
            variance_str = (
                f"  variance={e.gps_variance_meters}m" if e.gps_variance_meters else ""
            )
            etc_str = (
                f"  hrs_remaining={e.hours_remaining_estimate}"
                if e.hours_remaining_estimate
                else ""
            )
            print(
                f"    • job={e.job_id}  {e.hours}h @ {e.hourly_rate_cents}¢/hr "
                f"= ${e.total_cost_cents / 100:.2f}{gps_str}{variance_str}{etc_str}"
            )
        print()

        # Expenses — SD-7 Batch 3: vendor_name and capture timestamps
        expenses = db.execute(
            text("""
                SELECT je.id, je.job_id, je.job_expense_category_code, je.description,
                       je.cost_cents, je.markup_pct, je.billable_cents,
                       je.vendor_name, je.client_capture_at, je.server_received_at
                FROM public.job_expense je
                WHERE je.tenant_id = :tid
                ORDER BY je.incurred_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job_expense]  {len(expenses)} row(s)")
        for e in expenses:
            vendor_str = f"  vendor='{e.vendor_name}'" if e.vendor_name else ""
            print(
                f"    • {e.job_expense_category_code}: '{e.description}' "
                f"cost=${e.cost_cents / 100:.2f} markup={e.markup_pct}%"
                f"{vendor_str}"
            )
        print()

        # Assignments for completed jobs
        assignments = db.execute(
            text("""
                SELECT jta.job_id, jta.user_id, jta.role
                FROM public.job_tech_assignment jta
                JOIN public.job j ON j.id = jta.job_id
                JOIN public.job_status js ON js.id = j.status_id
                WHERE jta.tenant_id = :tid AND js.code = 'completed'
                ORDER BY jta.job_id
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job_tech_assignment (completed jobs)]  {len(assignments)} row(s)")
        for a in assignments:
            print(f"    • job={a.job_id}  user={a.user_id}  role={a.role}")

        # B19: Invoice counts for seeded jobs
        completed_job_ids = [str(j.id) for j in jobs]
        if completed_job_ids:
            placeholders = ", ".join(f"'{jid}'" for jid in completed_job_ids)
            invoice_rows = db.execute(
                text(f"""
                    SELECT i.id, i.invoice_number, i.job_id, is2.code AS status_code, i.total_cents, i.balance_due_cents
                    FROM public.invoice i
                    JOIN public.invoice_status is2 ON is2.id = i.status_id
                    WHERE i.tenant_id = :tid AND i.job_id IN ({placeholders})
                    ORDER BY i.invoice_number
                """),
                {"tid": tid},
            ).fetchall()
            print(f"\n  [invoice (seeded jobs)]  {len(invoice_rows)} row(s)")
            for inv in invoice_rows:
                print(
                    f"    • {inv.invoice_number}  status={inv.status_code}  "
                    f"total=${inv.total_cents / 100:.2f}  balance=${inv.balance_due_cents / 100:.2f}"
                )

        # SD-6: invoice_line counts
        il_rows = db.execute(
            text("""
                SELECT i.invoice_number, COUNT(il.id) AS cnt
                FROM public.invoice_line il
                JOIN public.invoice i ON i.id = il.invoice_id
                WHERE il.tenant_id = :tid
                GROUP BY i.invoice_number
                ORDER BY i.invoice_number
            """),
            {"tid": tid},
        ).fetchall()
        print(
            f"\n  [invoice_line]  {sum(r.cnt for r in il_rows)} row(s) across {len(il_rows)} invoice(s)"
        )
        for r in il_rows:
            print(f"    • {r.invoice_number}: {r.cnt} line(s)")

        # SD-6: loto_confirmation
        loto_rows = db.execute(
            text("""
                SELECT lc.id, lc.job_id, lc.confirmed_at
                FROM public.loto_confirmation lc
                WHERE lc.tenant_id = :tid
                ORDER BY lc.confirmed_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [loto_confirmation]  {len(loto_rows)} row(s)")
        for r in loto_rows:
            print(f"    • job={r.job_id}  confirmed_at={r.confirmed_at}")

        # SD-7 Batch 2: usage_ledger
        ul_rows = db.execute(
            text("""
                SELECT product_feature_code, quantity, occurred_at, idempotency_key
                FROM public.usage_ledger
                WHERE tenant_id = :tid
                ORDER BY product_feature_code, occurred_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [usage_ledger]  {len(ul_rows)} row(s)")
        by_feature = {}
        for r in ul_rows:
            by_feature.setdefault(r.product_feature_code, []).append(r)
        for feat, rows in sorted(by_feature.items()):
            total_qty = sum(float(r.quantity) for r in rows)
            print(f"    feature={feat}  entries={len(rows)}  total_qty={total_qty:.0f}")
            for r in rows:
                print(
                    f"      • qty={r.quantity}  occurred={r.occurred_at.date()}  key={r.idempotency_key}"
                )

        # CE-1: Overpayment variance payments
        variance_rows = db.execute(
            text("""
                SELECT p.id, p.invoice_id, i.invoice_number, p.amount_cents,
                       p.amount_variance_cents, p.variance_resolution
                FROM public.payment p
                JOIN public.invoice i ON i.id = p.invoice_id
                WHERE p.tenant_id = :tid AND p.amount_variance_cents IS NOT NULL
                  AND p.amount_variance_cents > 0
                ORDER BY p.paid_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [payment (variance)]  {len(variance_rows)} row(s)")
        for r in variance_rows:
            resolved = (
                f"resolved={r.variance_resolution}"
                if r.variance_resolution
                else "UNRESOLVED"
            )
            print(
                f"    • {r.invoice_number}  amount={r.amount_cents}¢  "
                f"variance={r.amount_variance_cents}¢  {resolved}"
            )

        # CE-1: invoice_signoff
        signoff_rows = db.execute(
            text("""
                SELECT s.id, s.invoice_id, i.invoice_number, s.signed_by_name,
                       s.signature_object_key, s.signed_at, s.superseded_at
                FROM public.invoice_signoff s
                JOIN public.invoice i ON i.id = s.invoice_id
                WHERE s.tenant_id = :tid
                ORDER BY s.signed_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [invoice_signoff]  {len(signoff_rows)} row(s)")
        for r in signoff_rows:
            status = "SUPERSEDED" if r.superseded_at else "ACTIVE"
            print(
                f"    • {r.invoice_number}  signed_by='{r.signed_by_name}'  "
                f"status={status}  signed_at={r.signed_at}"
            )


def mode_show():
    """Print what would be seeded without touching the DB."""
    print("=== seed_scenario_reporting: show mode ===\n")
    print(f"Anchor date: {ANCHOR_DATE.date()} (all jobs relative to this)\n")
    print(f"Technician UUID: {TECH_USER_ID}\n")
    print(f"Jobs ({len(REPORTING_JOBS)}):")
    for job in REPORTING_JOBS:
        job_date = (ANCHOR_DATE - timedelta(days=job["days_ago"])).date()
        total_hours = sum(te["duration_h"] for te in job["time_entries"])
        n_expenses = len(job["expenses"])
        print(
            f"  • '{job['title']}'"
            f"  date={job_date}"
            f"  {len(job['time_entries'])} time entries ({total_hours}h total)"
            f"  {n_expenses} expense(s)"
        )
        for te in job["time_entries"]:
            print(f"      - {te['skill']} {te['duration_h']}h: {te['notes']}")
        for exp in job["expenses"]:
            print(
                f"      - {exp['category']}: {exp['description']}  ${exp['cost_cents'] / 100:.2f}  markup={exp['markup_pct']}%"
            )


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_reporting.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(
        args, "reset", False
    ):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_reporting.py")
    tenant_id = _get_tenant_id()

    if args.reset:
        mode_reset(tenant_id)
    elif args.mode == "seed":
        mode_seed(tenant_id)
    elif args.mode == "inspect":
        mode_inspect(tenant_id)
    elif args.mode == "show":
        mode_show()
