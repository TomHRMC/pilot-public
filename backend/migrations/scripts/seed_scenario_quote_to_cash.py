"""
seed_scenario_quote_to_cash.py — Group D: Quote-to-Cash scenario data.

Purpose: Seeds realistic scenario data for the full quote-to-cash UI test flow.
8 customers, 7 sites, 6 pricebook items, 10 quotes covering all statuses,
plus the full quote→job→invoice→payment chain for Q-CONV-001.
NEVER run in production.

Schema verified against live DB 2026-07-15:
  customer: id, tenant_id, type, display_name, first_name, last_name, company_name,
            email, mobile_phone, is_active, lifecycle_status_id,
            preferred_contact_channel, sms_opted_out, sms_opt_in_consent,
            created_at, updated_at
  site: id, tenant_id, customer_id, name, is_active, lifecycle_status_id,
        created_at, updated_at
  address: id, tenant_id, line1, city, state, postal_code, country, is_active,
           created_at, updated_at
  entity_address: id, tenant_id, entity_type_code, entity_id, address_id,
                  address_type_code, is_primary, is_active, created_at, updated_at
  pricebook_item: id, tenant_id, sku, name, description, uom_id, taxability_code,
                  is_active, created_at, updated_at
  pricebook_item_version: tenant_id, pricebook_item_id, default_unit_price_cents,
                           valid_period, recorded_at  (AppendOnly — no updated_at)
  quote: id, tenant_id, customer_id, site_id, status_id, subtotal_cents, tax_cents,
         total_cents, currency, quote_number, title, expires_at, submitted_at,
         approved_at, customer_accepted_at, customer_declined_at,
         customer_acceptance_comment, customer_email_at_action,
         customer_decline_comment, customer_decline_reason,
         is_active, created_at, updated_at
  quote_line: id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
              description, quantity, unit_price_cents, subtotal_cents, total_cents,
              is_active, customer_visible, display_order, is_section_header,
              created_at, updated_at

Modes:
  --mode seed     (default) idempotent
  --mode inspect  show current state with values
  --mode show     print definitions, no DB
  --reset         wipe this scenario's data only, then exit
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

# Fixed reference date — same anchor as reporting script
ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=UTC)

# NOTE: pricebook_item IDs use gen_random_uuid() and change on every reset+reseed.
# Do NOT hardcode pricebook_item UUIDs. Instead, use the pricebook_item_ids dict
# built during seeding (keyed by SKU) and pass it into helper functions.

# SD-6: qco_line_type codes — resolved to UUIDs at runtime via qco_line_type_ids
# dict (built from SELECT id, code FROM qco_line_type WHERE tenant_id IS NULL).
# DB-MGMT-1 Task 4: do NOT hardcode UUIDs — seed_core.py uses gen_random_uuid(),
# so UUIDs differ per DB. Look up by code instead.
QCO_LABOR = "labor"
QCO_MATERIAL = "material"
QCO_MISC = "misc"
QCO_NOTE = "note"

# SD-6: tax_rate_version.id for US-DEFAULT (bigint, MCP-verified)
TAX_RATE_VERSION_ID = 1
TAX_RATE_PCT = "6.00"
TENANT_ID_STR = "00000000-0000-0000-0000-000000000001"

CUSTOMERS = [
    {
        "display_name": "John Smith",
        "first_name": "John",
        "last_name": "Smith",
        "company_name": None,
        "type": "person",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "Mary Johnson",
        "first_name": "Mary",
        "last_name": "Johnson",
        "company_name": None,
        "type": "person",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "Apex Commercial LLC",
        "first_name": None,
        "last_name": None,
        "company_name": "Apex Commercial LLC",
        "type": "company",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "Bob Davis",
        "first_name": "Bob",
        "last_name": "Davis",
        "company_name": None,
        "type": "person",
        "lifecycle": "prospect",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "Inactive Customer",
        "first_name": "Inactive",
        "last_name": "Customer",
        "company_name": None,
        "type": "person",
        "lifecycle": "dormant",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    # SD-5 additions (indices 5, 6, 7)
    {
        "display_name": "Rachel Kim",
        "first_name": "Rachel",
        "last_name": "Kim",
        "company_name": None,
        "type": "person",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "Metro Properties LLC",
        "first_name": None,
        "last_name": None,
        "company_name": "Metro Properties LLC",
        "type": "company",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "James Torres",
        "first_name": "James",
        "last_name": "Torres",
        "company_name": None,
        "type": "person",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
]

# Sites indexed by customer_idx
CUSTOMER_SITES = [
    {
        "customer_idx": 0,
        "site_name": "Smith Residence",
        "line1": "123 Main St",
        "city": "Brooklyn",
        "state": "NY",
        "postal_code": "11201",
        "country": "US",
    },
    {
        "customer_idx": 1,
        "site_name": "Johnson Home",
        "line1": "456 Oak Ave",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "US",
    },
    {
        "customer_idx": 2,
        "site_name": "Apex HQ",
        "line1": "789 Commerce Blvd",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "country": "US",
    },
    # SD-5 additions
    # Bob Davis (idx 3) — needed for Q-REJT-001 (quote.site_id NOT NULL)
    {
        "customer_idx": 3,
        "site_name": "Davis Property",
        "line1": "42 Prospect Lane",
        "city": "Denver",
        "state": "CO",
        "postal_code": "80201",
        "country": "US",
    },
    # Rachel Kim (idx 5)
    {
        "customer_idx": 5,
        "site_name": "Kim Residence",
        "line1": "321 Pine St",
        "city": "Seattle",
        "state": "WA",
        "postal_code": "98101",
        "country": "US",
    },
    # Metro Properties LLC (idx 6)
    {
        "customer_idx": 6,
        "site_name": "Metro Office Park",
        "line1": "555 Business Ave",
        "city": "Dallas",
        "state": "TX",
        "postal_code": "75201",
        "country": "US",
    },
    # James Torres (idx 7)
    {
        "customer_idx": 7,
        "site_name": "Torres Home",
        "line1": "888 Palm Dr",
        "city": "Miami",
        "state": "FL",
        "postal_code": "33101",
        "country": "US",
    },
]

PRICEBOOK_ITEMS = [
    {
        "sku": "OUTLET-STD-01",
        "name": "Standard Outlet Installation",
        "description": "Install standard 15A/125V duplex outlet",
        "category": "labor",
        "uom_code": "each",
        "unit_price_cents": 15000,
        "taxability_code": "taxable",
    },
    {
        "sku": "PANEL-200A-01",
        "name": "200A Panel Upgrade",
        "description": "Upgrade to 200-amp main service panel",
        "category": "labor",
        "uom_code": "each",
        "unit_price_cents": 180000,
        "taxability_code": "taxable",
    },
    {
        "sku": "BRKR-15A-01",
        "name": "15A Circuit Breaker",
        "description": "Single-pole 15A circuit breaker",
        "category": "material",
        "uom_code": "each",
        "unit_price_cents": 1800,
        "taxability_code": "taxable",
    },
    {
        "sku": "COND-EMT-01",
        "name": "EMT Conduit",
        "description": "Electrical metallic tubing conduit",
        "category": "material",
        "uom_code": "foot",
        "unit_price_cents": 350,
        "taxability_code": "taxable",
    },
    {
        "sku": "PERMIT-RES-01",
        "name": "Residential Permit Fee",
        "description": "Local building permit for residential electrical",
        "category": "misc",
        "uom_code": "each",
        "unit_price_cents": 25000,
        "taxability_code": "exempt",
    },
    # SD-5 addition
    {
        "sku": "WNUT-BAG-01",
        "name": "Wire Nuts (bag of 50)",
        "description": "Assorted wire nuts for electrical connections",
        "category": "material",
        "uom_code": "bag",
        "unit_price_cents": 500,
        "taxability_code": "taxable",
    },
]

# SD-5: 9 new quotes covering all non-draft statuses
# site_customer_idx matches the customer_idx in CUSTOMER_SITES to look up site_id
# SD-5: quote numbers use canonical QUO-9XXXXX format (high range avoids collision
# with test-generated sequential QUO-000001 etc.)
QUOTES = [
    {
        "quote_number": "QUO-900001",
        "title": "200A Panel Upgrade — Johnson Residence",
        "status_code": "pending_approval",
        "customer_idx": 1,  # Mary Johnson
        "site_customer_idx": 1,  # Johnson Home
        "subtotal_cents": 190000,
        "tax_cents": 15200,
        "total_cents": 205200,
        "submitted_at_offset_days": -2,
        "expires_at_offset_days": 30,
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
            ("BRKR-15A-01", "material", 10, 18000),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "QUO-900002",
        "title": "Commercial Panel Assessment — Metro Properties LLC",
        "status_code": "pending",
        "customer_idx": 2,  # Apex Commercial LLC
        "site_customer_idx": 2,  # Apex HQ
        "subtotal_cents": 320000,
        "tax_cents": 25600,
        "total_cents": 345600,
        "submitted_at_offset_days": -1,
        "expires_at_offset_days": 14,
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
            ("COND-EMT-01", "material", 100, 35000),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "QUO-900003",
        "title": "GFCI Outlet Installation — Master Bath",
        "status_code": "approved",
        "customer_idx": 5,  # Rachel Kim
        "site_customer_idx": 5,  # Kim Residence
        "subtotal_cents": 45000,
        "tax_cents": 3600,
        "total_cents": 48600,
        "approved_at_offset_days": -1,
        "expires_at_offset_days": 21,
        "line_items": [
            ("OUTLET-STD-01", "labor", 3, 45000),
        ],
    },
    {
        "quote_number": "QUO-900004",
        "title": "Electrical Service Inspection — Fairview Ave Property",
        "status_code": "sent",
        "customer_idx": 6,  # Metro Properties LLC
        "site_customer_idx": 6,  # Metro Office Park
        "subtotal_cents": 85000,
        "tax_cents": 6800,
        "total_cents": 91800,
        "expires_at_offset_days": 14,
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 60000),
            ("BRKR-15A-01", "material", 5, 9000),
        ],
    },
    {
        "quote_number": "QUO-900005",
        "title": "Full Home Rewire — Smith Renovation",
        "status_code": "accepted",
        "customer_idx": 7,  # James Torres
        "site_customer_idx": 7,  # Torres Home
        "subtotal_cents": 230000,
        "tax_cents": 18400,
        "total_cents": 248400,
        "expires_at_offset_days": 30,
        "customer_accepted_at_offset_days": -3,
        "customer_acceptance_comment": "Looks good, please proceed.",
        "customer_email_at_action": "james.torres@example.com",
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
            ("COND-EMT-01", "material", 50, 17500),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "QUO-900006",
        "title": "LED Lighting Upgrade — Office Suite 200",
        "status_code": "converted",
        "customer_idx": 0,  # John Smith
        "site_customer_idx": 0,  # Smith Residence
        "subtotal_cents": 95000,
        "tax_cents": 7600,
        "total_cents": 102600,
        "expires_at_offset_days": 30,
        "create_job_and_invoice": True,
        "line_items": [
            ("OUTLET-STD-01", "labor", 3, 45000),
            ("BRKR-15A-01", "material", 5, 9000),
            ("PERMIT-RES-01", "misc", 1, 25000),
        ],
    },
    {
        "quote_number": "QUO-900007",
        "title": "Solar Panel Tie-In Wiring — Rooftop Array",
        "status_code": "rejected",
        "customer_idx": 3,  # Bob Davis (prospect)
        "site_customer_idx": 3,  # Davis Property
        "subtotal_cents": 450000,
        "tax_cents": 36000,
        "total_cents": 486000,
        "expires_at_offset_days": 14,
        "customer_declined_at_offset_days": -5,
        "customer_decline_comment": "Too expensive for now.",
        "customer_decline_reason": "pricing",
        "line_items": [
            ("PANEL-200A-01", "labor", 2, 360000),
            ("COND-EMT-01", "material", 100, 35000),
        ],
    },
    {
        "quote_number": "QUO-900008",
        "title": "Standby Generator Installation — Backup System",
        "status_code": "expired",
        "customer_idx": 1,  # Mary Johnson
        "site_customer_idx": 1,  # Johnson Home
        "subtotal_cents": 180000,
        "tax_cents": 14400,
        "total_cents": 194400,
        "expires_at_offset_days": -30,  # expired 30d before ANCHOR
        "line_items": [
            ("PANEL-200A-01", "labor", 1, 180000),
        ],
    },
    {
        "quote_number": "QUO-900009",
        "title": "EV Charger Rough-In — Garage 240V Circuit",
        "status_code": "void",
        "customer_idx": 5,  # Rachel Kim
        "site_customer_idx": 5,  # Kim Residence
        "subtotal_cents": 65000,
        "tax_cents": 5200,
        "total_cents": 70200,
        "expires_at_offset_days": 14,
        "line_items": [
            ("OUTLET-STD-01", "labor", 2, 30000),
            ("COND-EMT-01", "material", 50, 17500),
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_quote_to_cash.py — Group D quote-to-cash seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


def _get_tenant_id() -> UUID:
    return UUID(settings.TEST_TENANT_ID)


def mode_reset(tenant_id: UUID):
    """Wipe quote-to-cash scenario data (child-first ordering)."""
    tid = str(tenant_id)
    with get_db_session() as db:
        # SD-7 B1: Delete new child tables before their parents
        for table in [
            "change_order_line_tax_component",  # ← before change_order_line
            "quote_acceptance",  # ← before quote_version
            "quote_line_tax_component",  # ← before quote_line
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

        # SD-6: Delete invoice_line_tax_component before invoice_line (FK)
        for table in ["invoice_line_tax_component", "invoice_line"]:
            try:
                result = db.execute(
                    text(f"DELETE FROM public.{table} WHERE tenant_id = :tid"),
                    {"tid": tid},
                )
                if result.rowcount:
                    print(f"  🗑  [{table}] Deleted {result.rowcount} row(s)")
            except Exception:
                pass

        # SD-6: Reset invoice totals back to 0 for INV-900001
        try:
            db.execute(
                text("""
                    UPDATE public.invoice
                    SET subtotal_cents=0, tax_cents=0, total_cents=0, balance_due_cents=0
                    WHERE tenant_id = :tid AND invoice_number = 'INV-900001'
                """),
                {"tid": tid},
            )
        except Exception:
            pass

        tables = [
            "job_tech_assignment",
            "job_time_entry",
            "job_expense",
            "job_notes",
            "job_attachment",
            "change_order_line",
            "change_order",
            "tech_availability",
            "quote_line",
            "quote_version",
            "quote",
            "payment",
            "invoice",
            "job",
            # BILLING-B1: payment_schedule_line before payment_schedule (CASCADE FK)
            "payment_schedule_line",
            "payment_schedule",
            "pricebook_item_version",
            "pricebook_item",
            "entity_address",
            "entity_contact",
            "contact",
            "site",
            "customer",
        ]
        for table in tables:
            try:
                result = db.execute(
                    text(f"DELETE FROM public.{table} WHERE tenant_id = :tid"),
                    {"tid": tid},
                )
                if result.rowcount:
                    print(f"  🗑  [{table}] Deleted {result.rowcount} row(s)")
            except Exception:
                pass

        # address has tenant_id too
        try:
            result = db.execute(
                text("DELETE FROM public.address WHERE tenant_id = :tid"), {"tid": tid}
            )
            if result.rowcount:
                print(f"  🗑  [address] Deleted {result.rowcount} row(s)")
        except Exception:
            pass

        db.commit()

    print("\n✅ Quote-to-Cash scenario data wiped.")
    print("   Run: python migrations/scripts/seed_scenario_quote_to_cash.py")
    print("   to re-seed.")


def _seed_payment_schedule(db, tid: str):
    """BILLING-B1: Seed one active progress payment schedule on QUO-900002.

    Attaches to the Apex Commercial LLC / Apex HQ quote (total $3,456.00 =
    345600 cents). Three draws that reconcile exactly to the contract total:
      - Draw 1 (Deposit):  fixed_amount $500.00  (50000 cents)
      - Draw 2 (Rough-in): percent 50% of remainder (345600 - 50000 = 295600;
        50% = 147800 cents)
      - Draw 3 (Final):    percent 50% of remainder (147800 cents)
      Sum = 50000 + 147800 + 147800 = 345600 ✓ (residual = 0)

    Draw 1 is pre-linked to a generated ``progress`` invoice so the FE has a
    "partially invoiced schedule" to render. Idempotent — looks up by business
    key (quote_number + label), never hardcodes scenario UUIDs (README §7).
    """
    # Look up the quote, customer, and site by business key.
    quote_row = db.execute(
        text("""
            SELECT q.id, q.customer_id, q.site_id, q.total_cents
            FROM public.quote q
            WHERE q.tenant_id = :tid AND q.quote_number = 'QUO-900002'
            LIMIT 1
        """),
        {"tid": tid},
    ).first()

    if not quote_row:
        print("  ⚠️  [payment_schedule] QUO-900002 not found — skipping")
        return

    quote_id = str(quote_row.id)
    customer_id = str(quote_row.customer_id)
    site_id = str(quote_row.site_id)
    contract_total_cents = int(quote_row.total_cents)

    # Idempotency: check if the schedule already exists (by quote_id + tenant).
    existing_schedule = db.execute(
        text("""
            SELECT id FROM public.payment_schedule
            WHERE tenant_id = :tid AND quote_id = :qid
            LIMIT 1
        """),
        {"tid": tid, "qid": quote_id},
    ).first()

    if existing_schedule:
        print("  ℹ️  [payment_schedule] QUO-900002 schedule already exists")
        return

    # Create the schedule (status='active' — pre-reconciled, no activation step).
    schedule_row = db.execute(
        text("""
            INSERT INTO public.payment_schedule
                (id, tenant_id, quote_id, job_id, customer_id, site_id,
                 contract_total_cents, status, basis_default, is_active,
                 created_at, updated_at, created_by, updated_by)
            VALUES
                (gen_random_uuid(), :tid, :qid, NULL, :cid, :sid,
                 :total, 'active', 'percent', true,
                 :created_at, :created_at, NULL, NULL)
            RETURNING id
        """),
        {
            "tid": tid,
            "qid": quote_id,
            "cid": customer_id,
            "sid": site_id,
            "total": contract_total_cents,
            "created_at": ANCHOR_DATE,
        },
    ).first()

    if not schedule_row:
        print("  ⚠️  [payment_schedule] INSERT returned no row — skipping")
        return

    schedule_id = str(schedule_row.id)
    print(
        f"  ✅ [payment_schedule] Created active schedule for QUO-900002 ({schedule_id})"
    )

    # Compute draw amounts (must reconcile to contract_total_cents).
    deposit_cents = 50000  # $500.00 fixed deposit
    remainder = contract_total_cents - deposit_cents  # 295600
    rough_in_cents = round(remainder * 50 / 100)  # 147800
    final_cents = remainder - rough_in_cents  # 147800 (exact remainder)

    draws = [
        {
            "sequence": 1,
            "label": "Deposit",
            "basis": "fixed_amount",
            "percent": None,
            "amount_cents": deposit_cents,
            "trigger_type": "manual",
            "trigger_date": None,
            "milestone_label": None,
        },
        {
            "sequence": 2,
            "label": "Rough-in",
            "basis": "percent",
            "percent": "50.00",
            "amount_cents": None,
            "trigger_type": "milestone",
            "trigger_date": None,
            "milestone_label": "Rough-in inspection complete",
        },
        {
            "sequence": 3,
            "label": "Final",
            "basis": "percent",
            "percent": "50.00",
            "amount_cents": None,
            "trigger_type": "milestone",
            "trigger_date": None,
            "milestone_label": "Final inspection + punch list",
        },
    ]

    line_ids = []
    for draw in draws:
        line_row = db.execute(
            text("""
                INSERT INTO public.payment_schedule_line
                    (id, tenant_id, payment_schedule_id, sequence, label, basis,
                     percent, amount_cents, trigger_type, trigger_date,
                     milestone_label, invoice_id, status, is_active,
                     created_at, updated_at, created_by, updated_by)
                VALUES
                    (gen_random_uuid(), :tid, :sid, :seq, :label, :basis,
                     :percent, :amount, :trigger_type, :trigger_date,
                     :milestone, NULL, 'pending', true,
                     :created_at, :created_at, NULL, NULL)
                RETURNING id
            """),
            {
                "tid": tid,
                "sid": schedule_id,
                "seq": draw["sequence"],
                "label": draw["label"],
                "basis": draw["basis"],
                "percent": draw["percent"],
                "amount": draw["amount_cents"],
                "trigger_type": draw["trigger_type"],
                "trigger_date": draw["trigger_date"],
                "milestone": draw["milestone_label"],
                "created_at": ANCHOR_DATE,
            },
        ).first()
        line_ids.append((draw, str(line_row.id)))
        print(
            f"  ✅ [payment_schedule_line] Draw {draw['sequence']} "
            f"'{draw['label']}' ({draw['basis']}) created"
        )

    # Pre-link draw 1 (Deposit) to a generated progress invoice so the FE has a
    # "partially invoiced schedule" to render. Two-step write (circular FK):
    #   1. Create the invoice with payment_schedule_line_id set.
    #   2. Back-fill the line's invoice_id + status='invoiced'.
    deposit_draw, deposit_line_id = line_ids[0]

    # Idempotency: if the deposit invoice already exists (prior partial run), reuse it.
    # NOTE: INV-900020 is a reserved number for the deposit draw invoice — it does
    # not collide with the QTC chain invoices (INV-900001, INV-900002, etc.).
    existing_inv = db.execute(
        text("""
            SELECT id FROM public.invoice
            WHERE tenant_id = :tid AND invoice_number = 'INV-900020'
            LIMIT 1
        """),
        {"tid": tid},
    ).first()

    if existing_inv:
        invoice_id = str(existing_inv.id)
        print(f"  ℹ️  [invoice] INV-900020 already exists — reusing ({invoice_id})")
    else:
        # Look up the draft invoice status (tenant-scoped, fallback global).
        draft_status_row = db.execute(
            text("""
                SELECT id FROM public.invoice_status
                WHERE code = 'draft'
                  AND (tenant_id = :tid OR tenant_id IS NULL)
                ORDER BY tenant_id IS NULL
                LIMIT 1
            """),
            {"tid": tid},
        ).first()

        if not draft_status_row:
            print(
                "  ⚠️  [payment_schedule] draft invoice_status not found — skipping invoice link"
            )
            return

        # Create the deposit draw invoice (billing_mode='progress').
        inv_row = db.execute(
            text("""
                INSERT INTO public.invoice
                    (id, tenant_id, invoice_number, quote_id, job_id, customer_id, site_id,
                     status_id, subtotal_cents, tax_cents, total_cents, balance_due_cents,
                     currency, billing_mode, progress_pct, payment_schedule_line_id,
                     is_active, issued_at, reminder_count, created_at, updated_at,
                     created_by, updated_by)
                VALUES
                    (gen_random_uuid(), :tid, :inv_num, :qid, NULL, :cid, :sid,
                     :status_id, :amount, 0, :amount, :amount,
                     'USD', 'progress', :progress_pct, :psl_id,
                     true, :issued_at, 0, :created_at, :created_at, NULL, NULL)
                RETURNING id
            """),
            {
                "tid": tid,
                "inv_num": "INV-900020",
                "qid": quote_id,
                "cid": customer_id,
                "sid": site_id,
                "status_id": str(draft_status_row.id),
                "amount": deposit_cents,
                "progress_pct": f"{round(deposit_cents / contract_total_cents * 100, 2):.2f}",
                "psl_id": deposit_line_id,
                "issued_at": ANCHOR_DATE,
                "created_at": ANCHOR_DATE,
            },
        ).first()

        if not inv_row:
            print(
                "  ⚠️  [payment_schedule] deposit invoice INSERT failed — skipping link"
            )
            return

        invoice_id = str(inv_row.id)
        print(
            f"  ✅ [invoice] Created INV-900020 progress invoice for Deposit draw "
            f"(${deposit_cents / 100:.2f}, {round(deposit_cents / contract_total_cents * 100, 2):.2f}% of contract)"
        )

    # Step 2: back-fill the line's invoice_id + status='invoiced'.
    db.execute(
        text("""
            UPDATE public.payment_schedule_line
            SET invoice_id = :inv_id, status = 'invoiced', updated_at = NOW()
            WHERE id = :line_id AND tenant_id = :tid
        """),
        {"inv_id": invoice_id, "line_id": deposit_line_id, "tid": tid},
    )

    print(
        "  ✅ [payment_schedule_line] Draw 1 'Deposit' linked to INV-900020 (status='invoiced')"
    )


def mode_seed(tenant_id: UUID):
    """Seed quote-to-cash scenario data."""
    print("=== seed_scenario_quote_to_cash: seed mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        # Look up required FK values
        cust_lifecycle = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.customer_lifecycle_status WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }
        site_lifecycle = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.site_lifecycle_status WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }
        uom_ids = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.supplier_item_uom WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }
        qco_line_type_ids = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.qco_line_type WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }
        quote_status_ids = {
            row.code: str(row.id)
            for row in db.execute(
                text("SELECT id, code FROM public.quote_status WHERE tenant_id IS NULL")
            ).fetchall()
        }

        # ── 1. Customers ─────────────────────────────────────────────────────
        customer_ids = []
        for cust in CUSTOMERS:
            existing = db.execute(
                text(
                    "SELECT id FROM public.customer WHERE tenant_id = :tid AND display_name = :name"
                ),
                {"tid": tid, "name": cust["display_name"]},
            ).first()
            if existing:
                print(f"  ℹ️  [customer] '{cust['display_name']}' already exists")
                customer_ids.append(str(existing.id))
                continue

            lifecycle_id = cust_lifecycle.get(cust["lifecycle"])
            result = db.execute(
                text("""
                    INSERT INTO public.customer
                    (id, tenant_id, type, display_name, first_name, last_name, company_name,
                     email, mobile_phone, is_active, lifecycle_status_id,
                     preferred_contact_channel, sms_opted_out, sms_opt_in_consent,
                     created_at, updated_at)
                    VALUES
                    (gen_random_uuid(), :tid, :type, :display_name, :first_name, :last_name, :company_name,
                     :email, :mobile_phone, true, :lifecycle_id,
                     'email', false, false,
                     NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "type": cust["type"],
                    "display_name": cust["display_name"],
                    "first_name": cust["first_name"],
                    "last_name": cust["last_name"],
                    "company_name": cust["company_name"],
                    "email": cust["email"],
                    "mobile_phone": cust["mobile_phone"],
                    "lifecycle_id": lifecycle_id,
                },
            )
            row = result.first()
            cust_id = str(row.id) if row else None
            customer_ids.append(cust_id)
            print(f"  ✅ [customer] Created '{cust['display_name']}' ({cust_id})")

        # ── 2. Sites + Addresses ──────────────────────────────────────────────
        site_ids = {}
        for site_def in CUSTOMER_SITES:
            cust_idx = site_def["customer_idx"]
            cust_id = customer_ids[cust_idx] if cust_idx < len(customer_ids) else None
            if not cust_id:
                continue

            existing = db.execute(
                text(
                    "SELECT id FROM public.site WHERE tenant_id = :tid AND customer_id = :cid AND name = :name"
                ),
                {"tid": tid, "cid": cust_id, "name": site_def["site_name"]},
            ).first()
            if existing:
                print(f"  ℹ️  [site] '{site_def['site_name']}' already exists")
                site_ids[cust_idx] = str(existing.id)
                continue

            active_site_status = site_lifecycle.get("active")
            site_result = db.execute(
                text("""
                    INSERT INTO public.site
                    (id, tenant_id, customer_id, name, is_active, lifecycle_status_id,
                     created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :cid, :name, true, :lifecycle_id, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "name": site_def["site_name"],
                    "lifecycle_id": active_site_status,
                },
            )
            site_row = site_result.first()
            site_id = str(site_row.id) if site_row else None
            site_ids[cust_idx] = site_id
            print(f"  ✅ [site] Created '{site_def['site_name']}' ({site_id})")

            # Create address record
            addr_result = db.execute(
                text("""
                    INSERT INTO public.address
                    (id, tenant_id, line1, city, state, postal_code, country, is_active,
                     created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :line1, :city, :state, :postal_code, :country, true, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "line1": site_def["line1"],
                    "city": site_def["city"],
                    "state": site_def["state"],
                    "postal_code": site_def["postal_code"],
                    "country": site_def["country"],
                },
            )
            addr_row = addr_result.first()
            if addr_row:
                addr_id = str(addr_row.id)
                db.execute(
                    text("""
                        INSERT INTO public.entity_address
                        (id, tenant_id, entity_type_code, entity_id, address_id,
                         address_type_code, is_primary, is_active, created_at, updated_at)
                        VALUES (gen_random_uuid(), :tid, 'site', :site_id, :addr_id,
                                'service_location', true, true, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {"tid": tid, "site_id": site_id, "addr_id": addr_id},
                )
                print(
                    f"  ✅ [entity_address] Linked {site_def['line1']}, {site_def['city']}"
                )

        # ── 3. Pricebook Items + Versions ─────────────────────────────────────
        pricebook_item_ids = {}
        for item in PRICEBOOK_ITEMS:
            existing = db.execute(
                text(
                    "SELECT id FROM public.pricebook_item WHERE tenant_id = :tid AND sku = :sku"
                ),
                {"tid": tid, "sku": item["sku"]},
            ).first()
            if existing:
                print(f"  ℹ️  [pricebook_item] '{item['name']}' already exists")
                pricebook_item_ids[item["sku"]] = str(existing.id)
                continue

            uom_id = uom_ids.get(item["uom_code"])
            pb_result = db.execute(
                text("""
                    INSERT INTO public.pricebook_item
                    (id, tenant_id, sku, name, description, uom_id, taxability_code, is_active,
                     created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :sku, :name, :description, :uom_id, :taxability_code, true,
                            NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "sku": item["sku"],
                    "name": item["name"],
                    "description": item["description"],
                    "uom_id": uom_id,
                    "taxability_code": item["taxability_code"],
                },
            )
            pb_row = pb_result.first()
            pb_id = str(pb_row.id) if pb_row else None
            pricebook_item_ids[item["sku"]] = pb_id
            print(f"  ✅ [pricebook_item] Created '{item['name']}' ({pb_id})")

            # pricebook_item_version: AppendOnly — created_at NOT NULL, no server default
            db.execute(
                text("""
                    INSERT INTO public.pricebook_item_version
                    (tenant_id, pricebook_item_id, default_unit_price_cents,
                     valid_period, recorded_at, created_at)
                    VALUES (:tid, :item_id, :unit_price, tstzrange(now(), NULL), NOW(), NOW())
                """),
                {"tid": tid, "item_id": pb_id, "unit_price": item["unit_price_cents"]},
            )
            print(
                f"  ✅ [pricebook_item_version] ${item['unit_price_cents'] / 100:.2f} for '{item['name']}'"
            )

        # ── 4. Draft Quote (QTC-001) ──────────────────────────────────────────
        cust_0_id = customer_ids[0] if customer_ids else None
        site_0_id = site_ids.get(0)
        draft_status_id = quote_status_ids.get("draft")

        if not cust_0_id or not site_0_id or not draft_status_id:
            print(
                "  ⚠️  [quote] Cannot create draft quote — missing customer/site/status"
            )
            quote_id = None
        else:
            existing = db.execute(
                text("""
                    SELECT id FROM public.quote
                    WHERE tenant_id = :tid AND quote_number = 'QTC-001' LIMIT 1
                """),
                {"tid": tid},
            ).first()

            if existing:
                print("  ℹ️  [quote] Draft quote QTC-001 for John Smith already exists")
                quote_id = str(existing.id)
            else:
                subtotal = 15000 + (1800 * 5)  # outlet + 5 breakers
                quote_result = db.execute(
                    text("""
                        INSERT INTO public.quote
                        (id, tenant_id, customer_id, site_id, status_id,
                         quote_number, title, subtotal_cents, tax_cents, total_cents, currency, is_active,
                         created_at, updated_at)
                        VALUES (gen_random_uuid(), :tid, :cid, :site_id, :status_id,
                                'QTC-001', 'Service Call — Outlet Troubleshooting',
                                :subtotal, 0, :subtotal, 'USD', true,
                                NOW(), NOW())
                        ON CONFLICT DO NOTHING
                        RETURNING id
                    """),
                    {
                        "tid": tid,
                        "cid": cust_0_id,
                        "site_id": site_0_id,
                        "status_id": draft_status_id,
                        "subtotal": subtotal,
                    },
                )
                quote_row = quote_result.first()
                quote_id = str(quote_row.id) if quote_row else None
                print(
                    f"  ✅ [quote] Created draft quote QTC-001 for John Smith ({quote_id})"
                )

        if quote_id:
            # ── Draft quote lines 1–8 ────────────────────────────────────────

            # Line 1: Standard Outlet Installation
            existing_line1 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 1"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line1:
                outlet_pb_id = pricebook_item_ids.get("OUTLET-STD-01")
                labor_type_id = qco_line_type_ids.get("labor")
                if outlet_pb_id and labor_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 1, :type_id, :pb_id,
                                    'Standard Outlet Installation', 1, 15000, 15000, 15000,
                                    true, true, 1, false, NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "qid": quote_id,
                            "type_id": labor_type_id,
                            "pb_id": outlet_pb_id,
                        },
                    )
                    print(
                        "  ✅ [quote_line] Line 1: Standard Outlet Installation × 1 = $150.00"
                    )

            # Line 2: 15A Circuit Breaker × 5
            existing_line2 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 2"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line2:
                breaker_pb_id = pricebook_item_ids.get("BRKR-15A-01")
                material_type_id = qco_line_type_ids.get("material")
                if breaker_pb_id and material_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 2, :type_id, :pb_id,
                                    '15A Circuit Breaker', 5, 1800, 9000, 9000,
                                    true, true, 2, false, NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "qid": quote_id,
                            "type_id": material_type_id,
                            "pb_id": breaker_pb_id,
                        },
                    )
                    print("  ✅ [quote_line] Line 2: 15A Circuit Breaker × 5 = $90.00")

            # Line 3: labor — 200A Panel Upgrade × 1
            existing_line3 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 3"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line3:
                panel_pb_id = pricebook_item_ids.get("PANEL-200A-01")
                labor_type_id = qco_line_type_ids.get("labor")
                if panel_pb_id and labor_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 3, :type_id, :pb_id,
                                    '200A Panel Upgrade', 1, 180000, 180000, 180000,
                                    true, true, 3, false, NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "qid": quote_id,
                            "type_id": labor_type_id,
                            "pb_id": panel_pb_id,
                        },
                    )
                    print("  ✅ [quote_line] Line 3: 200A Panel Upgrade × 1 = $1800.00")

            # Line 4: material — EMT Conduit × 50 ft @ 350¢/ft = 17500¢
            existing_line4 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 4"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line4:
                cond_pb_id = pricebook_item_ids.get("COND-EMT-01")
                material_type_id = qco_line_type_ids.get("material")
                if cond_pb_id and material_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 4, :type_id, :pb_id,
                                    'EMT Conduit', 50, 350, 17500, 17500,
                                    true, true, 4, false, NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "qid": quote_id,
                            "type_id": material_type_id,
                            "pb_id": cond_pb_id,
                        },
                    )
                    print("  ✅ [quote_line] Line 4: EMT Conduit × 50 ft = $175.00")

            # Line 5: misc — Residential Permit Fee × 1 = 25000¢
            existing_line5 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 5"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line5:
                permit_pb_id = pricebook_item_ids.get("PERMIT-RES-01")
                misc_type_id = qco_line_type_ids.get("misc")
                if permit_pb_id and misc_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 5, :type_id, :pb_id,
                                    'Residential Permit Fee', 1, 25000, 25000, 25000,
                                    true, true, 5, false, NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "qid": quote_id,
                            "type_id": misc_type_id,
                            "pb_id": permit_pb_id,
                        },
                    )
                    print(
                        "  ✅ [quote_line] Line 5: Residential Permit Fee × 1 = $250.00"
                    )

            # Line 6: note — display text only, no price
            existing_line6 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 6"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line6:
                note_type_id = qco_line_type_ids.get("note")
                if note_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 6, :type_id, NULL,
                                    'All electrical work performed per NEC 2023 standards.',
                                    1, 0, 0, 0,
                                    true, true, 6, false, NOW(), NOW())
                        """),
                        {"tid": tid, "qid": quote_id, "type_id": note_type_id},
                    )
                    print("  ✅ [quote_line] Line 6: Note (NEC compliance note)")

            # Line 7: discount — unit_price_cents=-10000 (−$100 off)
            existing_line7 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 7"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line7:
                discount_type_id = qco_line_type_ids.get("discount")
                if discount_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 7, :type_id, NULL,
                                    'New customer discount', 1, -10000, -10000, -10000,
                                    true, true, 7, false, NOW(), NOW())
                        """),
                        {"tid": tid, "qid": quote_id, "type_id": discount_type_id},
                    )
                    print("  ✅ [quote_line] Line 7: New customer discount = −$100.00")

            # Line 8: material — Wire Nuts (WNUT-BAG-01) × 50 bags = 500¢ × 50 = 25000¢
            existing_line8 = db.execute(
                text(
                    "SELECT id FROM public.quote_line WHERE quote_id = :qid AND position = 8"
                ),
                {"qid": quote_id},
            ).first()
            if not existing_line8:
                wnut_pb_id = pricebook_item_ids.get("WNUT-BAG-01")
                material_type_id = qco_line_type_ids.get("material")
                if wnut_pb_id and material_type_id:
                    db.execute(
                        text("""
                            INSERT INTO public.quote_line
                            (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                             description, quantity, unit_price_cents, subtotal_cents, total_cents,
                             is_active, customer_visible, display_order, is_section_header,
                             created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, :qid, 8, :type_id, :pb_id,
                                    'Wire Nuts (bag of 50)', 50, 500, 25000, 25000,
                                    true, true, 8, false, NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "qid": quote_id,
                            "type_id": material_type_id,
                            "pb_id": wnut_pb_id,
                        },
                    )
                    print("  ✅ [quote_line] Line 8: Wire Nuts × 50 bags = $250.00")

            # ── quote_version (required by /detail endpoint) ──────────────────
            existing_version = db.execute(
                text(
                    "SELECT id FROM public.quote_version WHERE quote_id = :qid AND is_active = true LIMIT 1"
                ),
                {"qid": quote_id},
            ).first()
            if existing_version:
                print("  ℹ️  [quote_version] Version already exists for draft quote")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.quote_version
                        (id, tenant_id, quote_id, version_no, snapshot,
                         is_active, presentation_style, created_at)
                        VALUES (gen_random_uuid(), :tid, :qid, 1,
                                CAST(:snapshot AS jsonb), true, 'clean', NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tid": tid,
                        "qid": quote_id,
                        "snapshot": f'{{"quote_id": "{quote_id}", "version_no": 1, "total_cents": 24000}}',
                    },
                )
                print("  ✅ [quote_version] Created version 1 for draft quote")

        # ── 5. Additional Quotes (all non-draft statuses) ─────────────────────
        print("\n  -- Seeding additional quotes (all statuses) --")

        # Look up payment objects for Q-CONV-001 chain
        job_status_ids = {
            row.code: str(row.id)
            for row in db.execute(
                text("SELECT id, code FROM public.job_status WHERE tenant_id IS NULL")
            ).fetchall()
        }
        inv_status_ids = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.invoice_status WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }
        pmt_status_row = db.execute(
            text(
                "SELECT id FROM public.payment_status WHERE code = 'succeeded' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()
        pmt_succeeded_id = str(pmt_status_row.id) if pmt_status_row else None

        pmt_type_row = db.execute(
            text(
                "SELECT id FROM public.payment_type WHERE code = 'manual_check' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()
        pmt_type_id = str(pmt_type_row.id) if pmt_type_row else None

        # Get or create seed payment_method
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
                    VALUES (gen_random_uuid(), :tid, :pmt_type_id, 'seed', 'seed-manual-check',
                            'Manual Check', true, NOW(), NOW())
                    RETURNING id
                """),
                {"tid": tid, "pmt_type_id": pmt_type_id},
            )
            seed_pm_id = str(seed_pm_result.first().id)
            print(
                f"  ✅ [payment_method] Created seed manual_check method ({seed_pm_id})"
            )

        for quote_def in QUOTES:
            # Idempotency: check by tenant + quote_number
            existing_quote = db.execute(
                text(
                    "SELECT id FROM public.quote WHERE tenant_id = :tid AND quote_number = :qnum LIMIT 1"
                ),
                {"tid": tid, "qnum": quote_def["quote_number"]},
            ).first()
            if existing_quote:
                print(f"  ℹ️  [quote] '{quote_def['quote_number']}' already exists")
                # For Q-CONV-001, still check/create the chain
                if quote_def.get("create_job_and_invoice"):
                    _seed_conv_chain(
                        db,
                        tid,
                        str(existing_quote.id),
                        customer_ids[quote_def["customer_idx"]],
                        site_ids.get(quote_def["site_customer_idx"]),
                        job_status_ids,
                        inv_status_ids,
                        pmt_succeeded_id,
                        seed_pm_id,
                        pricebook_item_ids,
                        qco_line_type_ids,
                    )
                continue

            cust_id = (
                customer_ids[quote_def["customer_idx"]]
                if quote_def["customer_idx"] < len(customer_ids)
                else None
            )
            site_id = site_ids.get(quote_def["site_customer_idx"])
            status_id = quote_status_ids.get(quote_def["status_code"])

            if not cust_id or not site_id or not status_id:
                print(
                    f"  ⚠️  [quote] Cannot create '{quote_def['quote_number']}' — missing cust/site/status"
                )
                continue

            expires_at = ANCHOR_DATE + timedelta(
                days=quote_def.get("expires_at_offset_days", 30)
            )
            submitted_at = None
            approved_at = None
            customer_accepted_at = None
            customer_declined_at = None

            if "submitted_at_offset_days" in quote_def:
                submitted_at = ANCHOR_DATE + timedelta(
                    days=quote_def["submitted_at_offset_days"]
                )
            if "approved_at_offset_days" in quote_def:
                approved_at = ANCHOR_DATE + timedelta(
                    days=quote_def["approved_at_offset_days"]
                )
            if "customer_accepted_at_offset_days" in quote_def:
                customer_accepted_at = ANCHOR_DATE + timedelta(
                    days=quote_def["customer_accepted_at_offset_days"]
                )
            if "customer_declined_at_offset_days" in quote_def:
                customer_declined_at = ANCHOR_DATE + timedelta(
                    days=quote_def["customer_declined_at_offset_days"]
                )

            new_quote_result = db.execute(
                text("""
                    INSERT INTO public.quote
                    (id, tenant_id, customer_id, site_id, status_id,
                     quote_number, title, subtotal_cents, tax_cents, total_cents,
                     currency, expires_at, submitted_at, approved_at,
                     customer_accepted_at, customer_acceptance_comment, customer_email_at_action,
                     customer_declined_at, customer_decline_comment, customer_decline_reason,
                     is_active, created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :cid, :site_id, :status_id,
                            :quote_number, :title, :subtotal, :tax, :total,
                            'USD', :expires_at, :submitted_at, :approved_at,
                            :customer_accepted_at, :acceptance_comment, :email_at_action,
                            :customer_declined_at, :decline_comment, :decline_reason,
                            true, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "site_id": site_id,
                    "status_id": status_id,
                    "quote_number": quote_def["quote_number"],
                    "title": quote_def["title"],
                    "subtotal": quote_def["subtotal_cents"],
                    "tax": quote_def["tax_cents"],
                    "total": quote_def["total_cents"],
                    "expires_at": expires_at,
                    "submitted_at": submitted_at,
                    "approved_at": approved_at,
                    "customer_accepted_at": customer_accepted_at,
                    "acceptance_comment": quote_def.get("customer_acceptance_comment"),
                    "email_at_action": quote_def.get("customer_email_at_action"),
                    "customer_declined_at": customer_declined_at,
                    "decline_comment": quote_def.get("customer_decline_comment"),
                    "decline_reason": quote_def.get("customer_decline_reason"),
                },
            )
            new_quote_row = new_quote_result.first()
            new_quote_id = str(new_quote_row.id) if new_quote_row else None
            if not new_quote_id:
                print(
                    f"  ⚠️  [quote] INSERT returned no row for '{quote_def['quote_number']}'"
                )
                continue
            print(
                f"  ✅ [quote] Created '{quote_def['quote_number']}' status={quote_def['status_code']} ({new_quote_id})"
            )

            # Add 2–3 quote lines
            # Build SKU→name lookup so descriptions show human-readable product names
            pb_name_by_sku = {item["sku"]: item["name"] for item in PRICEBOOK_ITEMS}
            for line_pos, (sku, line_type_code, qty, subtotal) in enumerate(
                quote_def["line_items"], start=1
            ):
                pb_id = pricebook_item_ids.get(sku)
                line_type_id = qco_line_type_ids.get(line_type_code)
                if not pb_id or not line_type_id:
                    continue
                unit_price = subtotal // qty if qty else subtotal
                db.execute(
                    text("""
                        INSERT INTO public.quote_line
                        (id, tenant_id, quote_id, position, qco_line_type_id, pricebook_item_id,
                         description, quantity, unit_price_cents, subtotal_cents, total_cents,
                         is_active, customer_visible, display_order, is_section_header,
                         created_at, updated_at)
                        VALUES (gen_random_uuid(), :tid, :qid, :pos, :type_id, :pb_id,
                                :desc, :qty, :unit_price, :subtotal, :subtotal,
                                true, true, :pos, false, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tid": tid,
                        "qid": new_quote_id,
                        "pos": line_pos,
                        "type_id": line_type_id,
                        "pb_id": pb_id,
                        "desc": pb_name_by_sku.get(sku, sku),
                        "qty": qty,
                        "unit_price": unit_price,
                        "subtotal": subtotal,
                    },
                )

            # Add quote_version
            db.execute(
                text("""
                    INSERT INTO public.quote_version
                    (id, tenant_id, quote_id, version_no, snapshot,
                     is_active, presentation_style, created_at)
                    VALUES (gen_random_uuid(), :tid, :qid, 1,
                            CAST(:snapshot AS jsonb), true, 'clean', NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "qid": new_quote_id,
                    "snapshot": f'{{"quote_id": "{new_quote_id}", "version_no": 1, "total_cents": {quote_def["total_cents"]}}}',
                },
            )

            # Create job+invoice+payment chain for Q-CONV-001
            if quote_def.get("create_job_and_invoice"):
                _seed_conv_chain(
                    db,
                    tid,
                    new_quote_id,
                    cust_id,
                    site_id,
                    job_status_ids,
                    inv_status_ids,
                    pmt_succeeded_id,
                    seed_pm_id,
                    pricebook_item_ids,
                    qco_line_type_ids,
                )

        # SD-6: Seed change orders for JOB-900001 (Tasks 4)
        _seed_change_orders(db, tid, pricebook_item_ids, qco_line_type_ids)

        # SD-7 Batch 1: populate optional fields on all existing rows
        _seed_sd7_batch1_fields(db, tid, pricebook_item_ids, qco_line_type_ids)

        # SD-7 Batch 3: job estimated_duration, quote_version_id, invoice issued_at/terms
        _seed_sd7_batch3_fields(db, tid)

        db.commit()

        # ── CLASS-B1: Set site_type on 7 QTC sites ────────────────────────
        print("\n  -- CLASS-B1: site_type on QTC sites --")
        # Apex HQ + Metro Office Park → commercial; all homes → residential
        site_type_map = {
            "Apex HQ": "commercial",
            "Metro Office Park": "commercial",
            "Smith Residence": "residential",
            "Johnson Home": "residential",
            "Kim Residence": "residential",
            "Torres Home": "residential",
            "Davis Property": "residential",
        }
        for site_name, site_type_val in site_type_map.items():
            site_row = db.execute(
                text("""
                    SELECT id, site_type FROM public.site
                    WHERE tenant_id = :tid AND name = :name
                    LIMIT 1
                """),
                {"tid": tid, "name": site_name},
            ).first()
            if not site_row:
                print(f"  ⚠️  [site_type] Site '{site_name}' not found — skipping")
                continue
            if site_row.site_type == site_type_val:
                print(f"  ℹ️  [site_type] '{site_name}' already={site_type_val}")
                continue
            db.execute(
                text("""
                    UPDATE public.site SET site_type = :st, updated_at = NOW()
                    WHERE id = :sid AND tenant_id = :tid
                """),
                {"st": site_type_val, "sid": str(site_row.id), "tid": tid},
            )
            print(f"  ✅ [site_type] '{site_name}' → {site_type_val}")
        db.commit()

    print(
        f"\n🎉 seed_scenario_quote_to_cash complete — Group D data present for {tenant_id}"
    )


def _seed_conv_chain(
    db,
    tid: str,
    quote_id: str,
    cust_id: str,
    site_id: str,
    job_status_ids: dict,
    inv_status_ids: dict,
    pmt_succeeded_id: str,
    seed_pm_id: str,
    pricebook_item_ids: dict,
    qco_line_type_ids: dict,
):
    """Create job JOB-900001 + invoice INV-900001 + invoice_line + payment for QUO-900006 (converted)."""

    anchor = ANCHOR_DATE

    # ── Step 1: Job ────────────────────────────────────────────────────────────
    existing_job = db.execute(
        text(
            "SELECT id FROM public.job WHERE tenant_id = :tid AND job_number = 'JOB-900001' LIMIT 1"
        ),
        {"tid": tid},
    ).first()

    if existing_job:
        print("  ℹ️  [job] JOB-900001 already exists")
        job_id = str(existing_job.id)
    else:
        completed_status_id = job_status_ids.get("completed")
        if not completed_status_id:
            print("  ⚠️  [job] 'completed' status not found — skipping chain")
            return

        job_start = (anchor - timedelta(days=7)).replace(hour=9, minute=0, second=0)
        job_end = (anchor - timedelta(days=7)).replace(hour=17, minute=0, second=0)

        # JOB-UI-B1: Pull the quote title to use as the job title default
        qtitle_row = db.execute(
            text("SELECT title FROM public.quote WHERE id = :qid LIMIT 1"),
            {"qid": quote_id},
        ).first()
        job_title = (
            qtitle_row.title
            if qtitle_row and qtitle_row.title
            else "Panel Upgrade — Smith Residence"
        )

        job_result = db.execute(
            text("""
                INSERT INTO public.job
                (id, tenant_id, customer_id, site_id, status_id, job_number, quote_id,
                 scheduled_start_at, scheduled_end_at,
                 actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents,
                 title,
                 is_active, version, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :cid, :sid, :status_id, 'JOB-900001', :quote_id,
                        :job_start, :job_end,
                        48000, 22000, 25000,
                        :title,
                        true, 1, NOW(), NOW())
                RETURNING id
            """),
            {
                "tid": tid,
                "cid": cust_id,
                "sid": site_id,
                "status_id": completed_status_id,
                "quote_id": quote_id,
                "job_start": job_start,
                "job_end": job_end,
                "title": job_title,
            },
        )
        job_id = str(job_result.first().id)
        print(f"  ✅ [job] Created JOB-900001 title='{job_title}' ({job_id})")

    # ── Step 2: Invoice ────────────────────────────────────────────────────────
    existing_inv = db.execute(
        text(
            "SELECT id FROM public.invoice WHERE tenant_id = :tid AND invoice_number = 'INV-900001' LIMIT 1"
        ),
        {"tid": tid},
    ).first()

    if existing_inv:
        print("  ℹ️  [invoice] INV-900001 already exists")
        inv_id = str(existing_inv.id)
    else:
        paid_inv_status_id = inv_status_ids.get("paid")
        if not paid_inv_status_id:
            print("  ⚠️  [invoice] 'paid' status not found — skipping invoice")
            return

        anchor_minus_5d = anchor - timedelta(days=5)
        anchor_plus_25d = anchor + timedelta(days=25)

        inv_result = db.execute(
            text("""
                INSERT INTO public.invoice
                (id, tenant_id, invoice_number, quote_id, job_id, customer_id, site_id, status_id,
                 subtotal_cents, tax_cents, total_cents, balance_due_cents,
                 currency, billing_mode, is_active, issued_at, due_at, reminder_count,
                 created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'INV-900001', :quote_id, :job_id, :cid, :sid, :status_id,
                        91600, 3996, 95596, 0,
                        'USD', 'line_item', true, :issued_at, :due_at, 0,
                        NOW(), NOW())
                RETURNING id
            """),
            {
                "tid": tid,
                "quote_id": quote_id,
                "job_id": job_id,
                "cid": cust_id,
                "sid": site_id,
                "status_id": paid_inv_status_id,
                "issued_at": anchor_minus_5d,
                "due_at": anchor_plus_25d,
            },
        )
        inv_id = str(inv_result.first().id)
        print(f"  ✅ [invoice] Created INV-900001 ({inv_id})")

    # ── Step 3: Invoice Lines (SD-6) ──────────────────────────────────────────
    existing_lines = db.execute(
        text(
            "SELECT COUNT(*) FROM public.invoice_line WHERE invoice_id = :inv_id AND tenant_id = :tid"
        ),
        {"inv_id": inv_id, "tid": tid},
    ).scalar()

    if existing_lines:
        print(
            f"  ℹ️  [invoice_line] {existing_lines} line(s) already exist for INV-900001"
        )
    else:
        # INV-900001 lines: 3 lines per design doc §D.3
        # Line 1: labor — Standard Outlet Installation × 3 = 45000¢, taxable
        # Line 2: material — 15A Circuit Breaker × 12 = 21600¢, taxable
        # Line 3: misc — Residential Permit Fee × 1 = 25000¢, exempt
        line_defs = [
            {
                "position": 1,
                "qco_line_type_id": qco_line_type_ids.get(QCO_LABOR),
                "pricebook_item_id": pricebook_item_ids.get("OUTLET-STD-01"),
                "description": "Standard Outlet Installation",
                "quantity": 3,
                "unit": "hr",
                "unit_price_cents": 15000,
                "subtotal_cents": 45000,
                "taxability_code": "taxable",
            },
            {
                "position": 2,
                "qco_line_type_id": qco_line_type_ids.get(QCO_MATERIAL),
                "pricebook_item_id": pricebook_item_ids.get("BRKR-15A-01"),
                "description": "15A Circuit Breaker",
                "quantity": 12,
                "unit": "ea",
                "unit_price_cents": 1800,
                "subtotal_cents": 21600,
                "taxability_code": "taxable",
            },
            {
                "position": 3,
                "qco_line_type_id": qco_line_type_ids.get(QCO_MISC),
                "pricebook_item_id": pricebook_item_ids.get("PERMIT-RES-01"),
                "description": "Residential Permit Fee",
                "quantity": 1,
                "unit": "ea",
                "unit_price_cents": 25000,
                "subtotal_cents": 25000,
                "taxability_code": "exempt",
            },
        ]

        for line in line_defs:
            is_taxable = line["taxability_code"] == "taxable"
            tax_amount = round(line["subtotal_cents"] * 0.06) if is_taxable else 0
            total_cents = line["subtotal_cents"] + tax_amount

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
                        gen_random_uuid(), :inv_id, 'ad_hoc', NULL, :position,
                        :qco_line_type_id, :pricebook_item_id, :description,
                        :quantity, :unit, :unit_price_cents, :taxability_code,
                        :subtotal_cents, :total_cents,
                        :tax_rate_pct, :tax_basis_cents, :tax_amount_cents,
                        :tax_jurisdiction_code, NOW(), :tax_source,
                        true, :tid, NOW(), NULL
                    )
                    RETURNING id
                """),
                {
                    "inv_id": inv_id,
                    "position": line["position"],
                    "qco_line_type_id": line["qco_line_type_id"],
                    "pricebook_item_id": line["pricebook_item_id"],
                    "description": line["description"],
                    "quantity": line["quantity"],
                    "unit": line["unit"],
                    "unit_price_cents": line["unit_price_cents"],
                    "taxability_code": line["taxability_code"],
                    "subtotal_cents": line["subtotal_cents"],
                    "total_cents": total_cents,
                    "tax_rate_pct": TAX_RATE_PCT if is_taxable else None,
                    "tax_basis_cents": line["subtotal_cents"] if is_taxable else None,
                    "tax_amount_cents": tax_amount if is_taxable else None,
                    "tax_jurisdiction_code": "US-DEFAULT" if is_taxable else None,
                    "tax_source": "manual_rate" if is_taxable else None,
                    "tid": tid,
                },
            )
            line_id = str(line_result.first().id)
            print(
                f"  ✅ [invoice_line] pos={line['position']} {line['description']} "
                f"×{line['quantity']} = ${line['subtotal_cents'] / 100:.2f}"
                f"{'  (taxable)' if is_taxable else '  (exempt)'}"
            )

            # Insert tax component for taxable lines
            if is_taxable:
                db.execute(
                    text("""
                        INSERT INTO public.invoice_line_tax_component
                        (id, invoice_line_id, tax_rate_version_id, component_code,
                         rate_pct, amount_cents, is_active, tenant_id, created_at, created_by)
                        VALUES (
                            gen_random_uuid(), :line_id, :trv_id, 'US-DEFAULT',
                            6.00, :amount_cents, true, :tid, NOW(), NULL
                        )
                    """),
                    {
                        "line_id": line_id,
                        "trv_id": TAX_RATE_VERSION_ID,
                        "amount_cents": tax_amount,
                        "tid": tid,
                    },
                )
                print(
                    f"    ✅ [invoice_line_tax_component] tax={tax_amount}¢ (6% US-DEFAULT)"
                )

        print("  ✅ [invoice_line] 3 lines seeded for INV-900001")

    # ── Step 4: UPDATE invoice totals (always — covers re-runs + new inserts) ──
    # subtotal=91600, tax=3996, total=95596, balance_due=0 (paid)
    db.execute(
        text("""
            UPDATE public.invoice
            SET subtotal_cents = 91600,
                tax_cents      = 3996,
                total_cents    = 95596,
                balance_due_cents = 0
            WHERE id = :inv_id AND tenant_id = :tid
        """),
        {"inv_id": inv_id, "tid": tid},
    )
    print(
        "  ✅ [invoice] Updated INV-900001 totals: subtotal=916.00, tax=39.96, total=955.96"
    )

    # ── Step 5: Payment ────────────────────────────────────────────────────────
    existing_pmt = db.execute(
        text(
            "SELECT id FROM public.payment WHERE tenant_id = :tid AND invoice_id = :inv_id AND amount_cents > 0 LIMIT 1"
        ),
        {"tid": tid, "inv_id": inv_id},
    ).first()

    if existing_pmt:
        # Always UPDATE to match new total_cents=95596
        db.execute(
            text("""
                UPDATE public.payment SET amount_cents = 95596
                WHERE id = :pmt_id AND tenant_id = :tid
            """),
            {"pmt_id": str(existing_pmt.id), "tid": tid},
        )
        print("  ✅ [payment] Updated INV-900001 payment → 95596¢ ($955.96)")
    else:
        if not pmt_succeeded_id or not seed_pm_id:
            print(
                "  ⚠️  [payment] Missing succeeded status or payment_method — skipping payment"
            )
            return

        paid_at = ANCHOR_DATE - timedelta(days=2)
        db.execute(
            text("""
                INSERT INTO public.payment
                (id, tenant_id, invoice_id, payment_method_id, status_id,
                 amount_cents, paid_via, paid_at, is_active, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :inv_id, :pm_id, :status_id,
                        95596, 'check', :paid_at, true, NOW(), NOW())
            """),
            {
                "tid": tid,
                "inv_id": inv_id,
                "pm_id": seed_pm_id,
                "status_id": pmt_succeeded_id,
                "paid_at": paid_at,
            },
        )
        print("  ✅ [payment] Created $955.96 payment for INV-900001")


def _seed_change_orders(
    db, tid: str, pricebook_item_ids: dict, qco_line_type_ids: dict
):
    """Seed change_order + change_order_line for JOB-900001 (SD-6 Task 4)."""
    print("\n  -- Seeding change orders for JOB-900001 --")

    # Verify JOB-900001 exists
    job_row = db.execute(
        text(
            "SELECT id FROM public.job WHERE tenant_id = :tid AND job_number = 'JOB-900001' LIMIT 1"
        ),
        {"tid": tid},
    ).first()
    if not job_row:
        print("  ⚠️  [change_order] JOB-900001 not found — skipping change orders")
        return
    job_id = str(job_row.id)

    # ── CO-001: Additional panel breakers — pending owner approval ────────────
    existing_co1 = db.execute(
        text("""
            SELECT id FROM public.change_order
            WHERE tenant_id = :tid AND job_id = :jid
            AND description LIKE 'Additional 20A breakers%'
            LIMIT 1
        """),
        {"tid": tid, "jid": job_id},
    ).first()

    if existing_co1:
        print("  ℹ️  [change_order] CO-001 already exists")
        co1_id = str(existing_co1.id)
    else:
        co1_result = db.execute(
            text("""
                INSERT INTO public.change_order
                (id, job_id, tenant_id, description,
                 subtotal_cents, tax_cents, total_cents,
                 is_active, created_at, updated_at, created_by, updated_by)
                VALUES (gen_random_uuid(), :job_id, :tid,
                        'Additional 20A breakers requested by customer after panel inspection — awaiting owner approval',
                        29400, 1764, 31164,
                        true, :created_at, :created_at, NULL, NULL)
                RETURNING id
            """),
            {
                "tid": tid,
                "job_id": job_id,
                "created_at": ANCHOR_DATE - timedelta(days=2),
            },
        )
        co1_id = str(co1_result.first().id)
        print(f"  ✅ [change_order] CO-001 created ({co1_id})")

    # CO-001 lines: 2 lines
    existing_co1_lines = db.execute(
        text(
            "SELECT COUNT(*) FROM public.change_order_line WHERE change_order_id = :coid AND tenant_id = :tid"
        ),
        {"coid": co1_id, "tid": tid},
    ).scalar()

    if not existing_co1_lines:
        co1_lines = [
            {
                "position": 1,
                "qco_line_type_id": qco_line_type_ids.get(QCO_MATERIAL),
                "pricebook_item_id": pricebook_item_ids.get("BRKR-15A-01"),
                "description": "15A Circuit Breaker",
                "quantity": 8,
                "unit": "ea",
                "unit_price_cents": 1800,
                "subtotal_cents": 14400,
                "total_cents": 15264,  # 14400 + round(14400*0.06)=864
                "taxability_code": "taxable",
                "tax_rate_pct": "6.00",
                "tax_basis_cents": 14400,
                "tax_amount_cents": 864,
                "tax_jurisdiction_code": "US-DEFAULT",
                "tax_source": "manual_rate",
            },
            {
                "position": 2,
                "qco_line_type_id": qco_line_type_ids.get(QCO_LABOR),
                "pricebook_item_id": pricebook_item_ids.get("OUTLET-STD-01"),
                "description": "Standard Outlet Installation",
                "quantity": 1,
                "unit": "ea",
                "unit_price_cents": 15000,
                "subtotal_cents": 15000,
                "total_cents": 15900,  # 15000 + round(15000*0.06)=900
                "taxability_code": "taxable",
                "tax_rate_pct": "6.00",
                "tax_basis_cents": 15000,
                "tax_amount_cents": 900,
                "tax_jurisdiction_code": "US-DEFAULT",
                "tax_source": "manual_rate",
            },
        ]
        for line in co1_lines:
            db.execute(
                text("""
                    INSERT INTO public.change_order_line
                    (id, change_order_id, position, qco_line_type_id, pricebook_item_id,
                     description, quantity, unit, unit_price_cents,
                     taxability_code, tax_rate_pct, tax_basis_cents, tax_amount_cents,
                     tax_jurisdiction_code, tax_as_of, tax_source,
                     subtotal_cents, total_cents,
                     is_active, tenant_id, created_at, updated_at, created_by, updated_by)
                    VALUES (
                        gen_random_uuid(), :co_id, :position, :qco_line_type_id, :pricebook_item_id,
                        :description, :quantity, :unit, :unit_price_cents,
                        :taxability_code, :tax_rate_pct, :tax_basis_cents, :tax_amount_cents,
                        :tax_jurisdiction_code, NOW(), :tax_source,
                        :subtotal_cents, :total_cents,
                        true, :tid, :created_at, :created_at, NULL, NULL
                    )
                """),
                {
                    "co_id": co1_id,
                    "tid": tid,
                    "created_at": ANCHOR_DATE - timedelta(days=2),
                    **{
                        k: line[k]
                        for k in [
                            "position",
                            "qco_line_type_id",
                            "pricebook_item_id",
                            "description",
                            "quantity",
                            "unit",
                            "unit_price_cents",
                            "taxability_code",
                            "tax_rate_pct",
                            "tax_basis_cents",
                            "tax_amount_cents",
                            "tax_jurisdiction_code",
                            "tax_source",
                            "subtotal_cents",
                            "total_cents",
                        ]
                    },
                },
            )
            print(
                f"  ✅ [change_order_line] CO-001 line {line['position']}: {line['description']} ×{line['quantity']}"
            )

    # ── CO-002: Conduit extension — approved ──────────────────────────────────
    existing_co2 = db.execute(
        text("""
            SELECT id FROM public.change_order
            WHERE tenant_id = :tid AND job_id = :jid
            AND description LIKE 'Extension of EMT conduit%'
            LIMIT 1
        """),
        {"tid": tid, "jid": job_id},
    ).first()

    if existing_co2:
        print("  ℹ️  [change_order] CO-002 already exists")
        co2_id = str(existing_co2.id)
    else:
        co2_result = db.execute(
            text("""
                INSERT INTO public.change_order
                (id, job_id, tenant_id, description,
                 subtotal_cents, tax_cents, total_cents,
                 is_active, created_at, updated_at, created_by, updated_by)
                VALUES (gen_random_uuid(), :job_id, :tid,
                        'Extension of EMT conduit run to secondary panel location — approved by owner 2026-07-10',
                        44000, 2640, 46640,
                        true, :created_at, :created_at, NULL, NULL)
                RETURNING id
            """),
            {
                "tid": tid,
                "job_id": job_id,
                "created_at": ANCHOR_DATE + timedelta(days=9),
            },
        )
        co2_id = str(co2_result.first().id)
        print(f"  ✅ [change_order] CO-002 created ({co2_id})")

    # CO-002 lines: 3 lines (labor + material + note)
    existing_co2_lines = db.execute(
        text(
            "SELECT COUNT(*) FROM public.change_order_line WHERE change_order_id = :coid AND tenant_id = :tid"
        ),
        {"coid": co2_id, "tid": tid},
    ).scalar()

    if not existing_co2_lines:
        co2_lines = [
            {
                "position": 1,
                "qco_line_type_id": qco_line_type_ids.get(QCO_LABOR),
                "pricebook_item_id": pricebook_item_ids.get("OUTLET-STD-01"),
                "description": "Standard Outlet Installation",
                "quantity": 2,
                "unit": "ea",
                "unit_price_cents": 15000,
                "subtotal_cents": 30000,
                "total_cents": 31800,  # 30000 + round(30000*0.06)=1800
                "taxability_code": "taxable",
                "tax_rate_pct": "6.00",
                "tax_basis_cents": 30000,
                "tax_amount_cents": 1800,
                "tax_jurisdiction_code": "US-DEFAULT",
                "tax_source": "manual_rate",
            },
            {
                "position": 2,
                "qco_line_type_id": qco_line_type_ids.get(QCO_MATERIAL),
                "pricebook_item_id": pricebook_item_ids.get("COND-EMT-01"),
                "description": "EMT Conduit",
                "quantity": 40,
                "unit": "ft",
                "unit_price_cents": 350,
                "subtotal_cents": 14000,
                "total_cents": 14840,  # 14000 + round(14000*0.06)=840
                "taxability_code": "taxable",
                "tax_rate_pct": "6.00",
                "tax_basis_cents": 14000,
                "tax_amount_cents": 840,
                "tax_jurisdiction_code": "US-DEFAULT",
                "tax_source": "manual_rate",
            },
            {
                "position": 3,
                "qco_line_type_id": qco_line_type_ids.get(QCO_NOTE),
                "pricebook_item_id": None,
                "description": "Conduit run extended per field measurement — no additional materials required beyond listed items",
                "quantity": 1,
                "unit": None,
                "unit_price_cents": 0,
                "subtotal_cents": 0,
                "total_cents": 0,
                "taxability_code": None,
                "tax_rate_pct": None,
                "tax_basis_cents": None,
                "tax_amount_cents": None,
                "tax_jurisdiction_code": None,
                "tax_source": None,
            },
        ]
        for line in co2_lines:
            db.execute(
                text("""
                    INSERT INTO public.change_order_line
                    (id, change_order_id, position, qco_line_type_id, pricebook_item_id,
                     description, quantity, unit, unit_price_cents,
                     taxability_code, tax_rate_pct, tax_basis_cents, tax_amount_cents,
                     tax_jurisdiction_code, tax_as_of, tax_source,
                     subtotal_cents, total_cents,
                     is_active, tenant_id, created_at, updated_at, created_by, updated_by)
                    VALUES (
                        gen_random_uuid(), :co_id, :position, :qco_line_type_id, :pricebook_item_id,
                        :description, :quantity, :unit, :unit_price_cents,
                        :taxability_code, :tax_rate_pct, :tax_basis_cents, :tax_amount_cents,
                        :tax_jurisdiction_code,
                        CASE WHEN :taxability_code IS NOT NULL THEN NOW() ELSE NULL END,
                        :tax_source,
                        :subtotal_cents, :total_cents,
                        true, :tid, :created_at, :created_at, NULL, NULL
                    )
                """),
                {
                    "co_id": co2_id,
                    "tid": tid,
                    "created_at": ANCHOR_DATE + timedelta(days=9),
                    **{
                        k: line[k]
                        for k in [
                            "position",
                            "qco_line_type_id",
                            "pricebook_item_id",
                            "description",
                            "quantity",
                            "unit",
                            "unit_price_cents",
                            "taxability_code",
                            "tax_rate_pct",
                            "tax_basis_cents",
                            "tax_amount_cents",
                            "tax_jurisdiction_code",
                            "tax_source",
                            "subtotal_cents",
                            "total_cents",
                        ]
                    },
                },
            )
            print(
                f"  ✅ [change_order_line] CO-002 line {line['position']}: {line['description'][:50]}"
            )

    print("  ✅ [change_order] 2 change orders + 5 lines seeded for JOB-900001")


# ── SD-7 Batch 1 constants ──────────────────────────────────────────────────
OWNER_USER_ID = "00000000-0000-0000-0000-000000000002"
TECH_USER_ID_STR = "00000000-0000-0000-0000-000000000003"

# tax_rate_version IDs (bigint PKs — MCP-verified 2026-07-23)
TAX_RATE_VERSION_ID_US_DEFAULT = 1  # 6.00%
TAX_RATE_VERSION_ID_TX_HARRIS = 2  # 8.25%


def _seed_sd7_batch1_fields(
    db, tid: str, pricebook_item_ids: dict, qco_line_type_ids: dict
):
    """SD-7 Batch 1: populate optional fields on existing rows.

    Covers:
    - quote_line tax fields (taxability_code, tax_rate_pct, tax_basis_cents,
      tax_amount_cents, tax_jurisdiction_code) for all 28+ quote lines
    - quote_line_tax_component rows for taxable quote lines
    - change_order_line_tax_component rows for taxable CO lines (SD-6 added fields)
    - quote_acceptance for QUO-900005 (internal owner-recorded)
    - quote_approval_comment for QUO-900001 (kickback)
    - quote_message for QUO-900004 (tenant_user action)
    - customer optional fields: dba_name (company types), notes, taxability_code,
      last_assigned_tech_id, locale, timezone
    - site optional fields: notes, hazard_notes, jurisdiction_code, gate_code,
      access_instructions
    - invoice optional fields: payment_terms, customer_notes for INV-900001
    """
    print("\n  -- SD-7 Batch 1: populating optional fields --")

    # ── 1. Quote lines — tax fields ───────────────────────────────────────────
    # Determine each quote's site address state so we can assign correct tax jurisdiction.
    # TX sites → US-TX-HARRIS (8.25%); all others → US-DEFAULT (6%).
    quote_site_states = db.execute(
        text("""
            SELECT q.id AS quote_id, q.quote_number, a.state
            FROM public.quote q
            JOIN public.site s ON s.id = q.site_id
            LEFT JOIN public.entity_address ea
                ON ea.entity_id = s.id AND ea.entity_type_code = 'site' AND ea.is_primary = true
            LEFT JOIN public.address a ON a.id = ea.address_id
            WHERE q.tenant_id = :tid
        """),
        {"tid": tid},
    ).fetchall()

    for qrow in quote_site_states:
        quote_id = str(qrow.quote_id)
        state = qrow.state or "NY"
        # TX sites → US-TX-HARRIS; all others → US-DEFAULT
        if state == "TX":
            tax_rate_pct = "8.25"
            jurisdiction_code = "US-TX-HARRIS"
            tax_rate_version_id = TAX_RATE_VERSION_ID_TX_HARRIS
        else:
            tax_rate_pct = "6.00"
            jurisdiction_code = "US-DEFAULT"
            tax_rate_version_id = TAX_RATE_VERSION_ID_US_DEFAULT

        # Fetch quote lines that don't yet have taxability_code set
        lines = db.execute(
            text("""
                SELECT ql.id, ql.qco_line_type_id, ql.subtotal_cents,
                       pi.taxability_code AS pb_taxability
                FROM public.quote_line ql
                LEFT JOIN public.pricebook_item pi ON pi.id = ql.pricebook_item_id
                WHERE ql.quote_id = :qid AND ql.tenant_id = :tid
                  AND ql.taxability_code IS NULL
            """),
            {"qid": quote_id, "tid": tid},
        ).fetchall()

        for line in lines:
            line_id = str(line.id)
            # Use pricebook item taxability if available; default to "taxable" for labor
            is_exempt = line.pb_taxability == "exempt"
            is_non_taxable_type = (
                str(line.qco_line_type_id) == qco_line_type_ids.get(QCO_NOTE)
                or line.subtotal_cents == 0
            )

            if is_non_taxable_type:
                # note lines and zero-price lines get no tax
                db.execute(
                    text("""
                        UPDATE public.quote_line
                        SET taxability_code = 'exempt',
                            tax_rate_pct = NULL,
                            tax_basis_cents = 0,
                            tax_amount_cents = 0,
                            tax_jurisdiction_code = NULL,
                            updated_at = NOW()
                        WHERE id = :id AND tenant_id = :tid
                    """),
                    {"id": line_id, "tid": tid},
                )
                continue

            if is_exempt:
                db.execute(
                    text("""
                        UPDATE public.quote_line
                        SET taxability_code = 'exempt',
                            tax_rate_pct = NULL,
                            tax_basis_cents = :basis,
                            tax_amount_cents = 0,
                            tax_jurisdiction_code = NULL,
                            updated_at = NOW()
                        WHERE id = :id AND tenant_id = :tid
                    """),
                    {"id": line_id, "tid": tid, "basis": line.subtotal_cents},
                )
                continue

            # Taxable line
            tax_basis = line.subtotal_cents
            rate = float(tax_rate_pct)
            tax_amount = round(tax_basis * rate / 100)
            db.execute(
                text("""
                    UPDATE public.quote_line
                    SET taxability_code = 'taxable',
                        tax_rate_pct = :rate_pct,
                        tax_basis_cents = :basis,
                        tax_amount_cents = :tax_amount,
                        tax_jurisdiction_code = :jurisdiction,
                        tax_as_of = NOW(),
                        tax_source = 'manual_rate',
                        updated_at = NOW()
                    WHERE id = :id AND tenant_id = :tid
                """),
                {
                    "id": line_id,
                    "tid": tid,
                    "rate_pct": tax_rate_pct,
                    "basis": tax_basis,
                    "tax_amount": tax_amount,
                    "jurisdiction": jurisdiction_code,
                },
            )

            # Insert quote_line_tax_component if not already present
            existing_comp = db.execute(
                text("""
                    SELECT 1 FROM public.quote_line_tax_component
                    WHERE quote_line_id = :lid AND tenant_id = :tid
                """),
                {"lid": line_id, "tid": tid},
            ).first()
            if not existing_comp:
                db.execute(
                    text("""
                        INSERT INTO public.quote_line_tax_component
                        (id, quote_line_id, tax_rate_version_id, component_code,
                         rate_pct, amount_cents, is_active, tenant_id, created_at, created_by)
                        VALUES (
                            gen_random_uuid(), :lid, :trv_id, :comp_code,
                            :rate_pct, :amount_cents, true, :tid, NOW(), NULL
                        )
                    """),
                    {
                        "lid": line_id,
                        "trv_id": tax_rate_version_id,
                        "comp_code": jurisdiction_code,
                        "rate_pct": tax_rate_pct,
                        "amount_cents": tax_amount,
                        "tid": tid,
                    },
                )

    # Count results for logging
    updated_lines = db.execute(
        text("""
            SELECT COUNT(*) FROM public.quote_line
            WHERE tenant_id = :tid AND taxability_code IS NOT NULL
        """),
        {"tid": tid},
    ).scalar()
    tax_components = db.execute(
        text("""
            SELECT COUNT(*) FROM public.quote_line_tax_component
            WHERE tenant_id = :tid
        """),
        {"tid": tid},
    ).scalar()
    print(
        f"  ✅ [quote_line] tax fields set on {updated_lines} lines — "
        f"{tax_components} tax component(s) inserted"
    )

    # ── 2. change_order_line_tax_component — for taxable CO lines ─────────────
    # CO lines already have tax fields from SD-6. We just need to add the component rows.
    co_taxable_lines = db.execute(
        text("""
            SELECT col.id AS line_id, col.tax_rate_pct, col.tax_amount_cents,
                   col.tax_jurisdiction_code
            FROM public.change_order_line col
            WHERE col.tenant_id = :tid
              AND col.taxability_code = 'taxable'
              AND col.tax_amount_cents IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM public.change_order_line_tax_component cotc
                  WHERE cotc.change_order_line_id = col.id AND cotc.tenant_id = :tid
              )
        """),
        {"tid": tid},
    ).fetchall()

    for co_line in co_taxable_lines:
        jur = co_line.tax_jurisdiction_code or "US-DEFAULT"
        trv_id = (
            TAX_RATE_VERSION_ID_TX_HARRIS
            if jur == "US-TX-HARRIS"
            else TAX_RATE_VERSION_ID_US_DEFAULT
        )
        db.execute(
            text("""
                INSERT INTO public.change_order_line_tax_component
                (id, change_order_line_id, tax_rate_version_id, component_code,
                 rate_pct, amount_cents, tenant_id, created_at, created_by)
                VALUES (
                    gen_random_uuid(), :lid, :trv_id, :comp_code,
                    :rate_pct, :amount_cents, :tid, NOW(), NULL
                )
            """),
            {
                "lid": str(co_line.line_id),
                "trv_id": trv_id,
                "comp_code": jur,
                "rate_pct": str(co_line.tax_rate_pct),
                "amount_cents": co_line.tax_amount_cents,
                "tid": tid,
            },
        )

    co_components_count = db.execute(
        text(
            "SELECT COUNT(*) FROM public.change_order_line_tax_component WHERE tenant_id = :tid"
        ),
        {"tid": tid},
    ).scalar()
    print(
        f"  ✅ [change_order_line_tax_component] {co_components_count} component(s) present"
    )

    # ── 3. quote_acceptance for QUO-900005 (accepted) — internal owner-recorded ──
    # quote_acceptance.uq_quote_acceptance_version_contact = UNIQUE(quote_version_id, contact_id)
    # contact_id = NULL (internal acceptance — not via public link); this unique constraint
    # only applies when both are non-null. We check by quote_version_id.
    quo_900005 = db.execute(
        text("""
            SELECT q.id AS quote_id, qv.id AS version_id
            FROM public.quote q
            JOIN public.quote_version qv ON qv.quote_id = q.id
            WHERE q.tenant_id = :tid AND q.quote_number = 'QUO-900005'
            LIMIT 1
        """),
        {"tid": tid},
    ).first()

    if quo_900005:
        existing_acceptance = db.execute(
            text("""
                SELECT 1 FROM public.quote_acceptance
                WHERE quote_version_id = :vid AND tenant_id = :tid
            """),
            {"vid": str(quo_900005.version_id), "tid": tid},
        ).first()
        if existing_acceptance:
            print("  ℹ️  [quote_acceptance] QUO-900005 acceptance already exists")
        else:
            accepted_at = ANCHOR_DATE - timedelta(days=3)
            db.execute(
                text("""
                    INSERT INTO public.quote_acceptance
                    (id, quote_version_id, contact_id, approved_at, approved_ip,
                     terms_acknowledged, accepted_by_name, accepted_by_email,
                     accepted_by_user_id, acceptance_notes,
                     quote_public_link_id, tenant_id, created_at, created_by)
                    VALUES (
                        gen_random_uuid(),
                        :version_id,
                        NULL,
                        :approved_at,
                        NULL,
                        true,
                        'Dev Owner',
                        'dev@pilot.local',
                        CAST(:owner_id AS uuid),
                        'Customer verbally confirmed acceptance by phone. Owner recorded in system.',
                        NULL,
                        :tid,
                        :approved_at,
                        NULL
                    )
                """),
                {
                    "version_id": str(quo_900005.version_id),
                    "approved_at": accepted_at,
                    "owner_id": OWNER_USER_ID,
                    "tid": tid,
                },
            )
            print(
                "  ✅ [quote_acceptance] Created for QUO-900005 "
                "(internal owner-recorded, quote_public_link_id=NULL)"
            )
    else:
        print("  ⚠️  [quote_acceptance] QUO-900005 not found — skipping")

    # ── 4. quote_approval_comment for QUO-900001 (pending_approval) ──────────
    # comment_type: 'kickback' (reviewer requesting changes)
    quo_900001 = db.execute(
        text("""
            SELECT q.id AS quote_id, qv.id AS version_id
            FROM public.quote q
            JOIN public.quote_version qv ON qv.quote_id = q.id
            WHERE q.tenant_id = :tid AND q.quote_number = 'QUO-900001'
            LIMIT 1
        """),
        {"tid": tid},
    ).first()

    if quo_900001:
        existing_comment = db.execute(
            text("""
                SELECT 1 FROM public.quote_approval_comment
                WHERE quote_id = :qid AND tenant_id = :tid
            """),
            {"qid": str(quo_900001.quote_id), "tid": tid},
        ).first()
        if existing_comment:
            print("  ℹ️  [quote_approval_comment] QUO-900001 comment already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.quote_approval_comment
                    (id, tenant_id, quote_id, quote_version_id, target_line_id,
                     author_user_id, comment_type, content, created_at, created_by)
                    VALUES (
                        gen_random_uuid(),
                        :tid,
                        :quote_id,
                        :version_id,
                        NULL,
                        CAST(:author_id AS uuid),
                        'kickback',
                        'Please verify the permit fee is included. Also confirm the breaker count — customer asked about adding 2 more AFCI breakers.',
                        :created_at,
                        NULL
                    )
                """),
                {
                    "tid": tid,
                    "quote_id": str(quo_900001.quote_id),
                    "version_id": str(quo_900001.version_id),
                    "author_id": OWNER_USER_ID,
                    "created_at": ANCHOR_DATE - timedelta(days=1),
                },
            )
            print(
                "  ✅ [quote_approval_comment] Created kickback comment for QUO-900001"
            )
    else:
        print("  ⚠️  [quote_approval_comment] QUO-900001 not found — skipping")

    # ── 5. quote_message for QUO-900004 (sent) ───────────────────────────────
    # action_type: 'tenant_user' (owner sending a message on a sent quote)
    quo_900004 = db.execute(
        text("""
            SELECT id FROM public.quote
            WHERE tenant_id = :tid AND quote_number = 'QUO-900004'
            LIMIT 1
        """),
        {"tid": tid},
    ).first()

    if quo_900004:
        existing_msg = db.execute(
            text("""
                SELECT 1 FROM public.quote_message
                WHERE quote_id = :qid AND tenant_id = :tid
            """),
            {"qid": str(quo_900004.id), "tid": tid},
        ).first()
        if existing_msg:
            print("  ℹ️  [quote_message] QUO-900004 message already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.quote_message
                    (id, tenant_id, quote_id, contact_id, action_type, message,
                     created_at, updated_at, created_by, updated_by)
                    VALUES (
                        gen_random_uuid(),
                        :tid,
                        :quote_id,
                        NULL,
                        'tenant_user',
                        'Hi, just following up on the electrical inspection quote we sent over. Let us know if you have any questions or would like to schedule the work!',
                        :created_at,
                        :created_at,
                        NULL,
                        NULL
                    )
                """),
                {
                    "tid": tid,
                    "quote_id": str(quo_900004.id),
                    "created_at": ANCHOR_DATE,
                },
            )
            print("  ✅ [quote_message] Created follow-up message for QUO-900004")
    else:
        print("  ⚠️  [quote_message] QUO-900004 not found — skipping")

    # ── 6. Customer optional fields ───────────────────────────────────────────
    # dba_name: company types only (Apex Commercial LLC → "Apex Electric Services",
    #           Metro Properties LLC → "Metro Commercial Properties")
    # notes: 2–3 customers
    # taxability_code: "exempt" on Apex Commercial LLC (commercial tax-exempt)
    # last_assigned_tech_id: tech user on active customers
    # locale: "en-US" on 2 customers
    # timezone: NY customers → America/New_York, TX customers → America/Chicago
    customer_updates = [
        {
            "display_name": "Apex Commercial LLC",
            "dba_name": "Apex Electric Services",
            "notes": "Commercial account — requires certificate of insurance before work begins.",
            "taxability_code": "exempt",
            "last_assigned_tech_id": TECH_USER_ID_STR,
            "locale": "en-US",
            "timezone": "America/Chicago",
        },
        {
            "display_name": "Metro Properties LLC",
            "dba_name": "Metro Commercial Properties",
            "notes": "Multi-unit property manager. Contact facilities director for access.",
            "taxability_code": None,
            "last_assigned_tech_id": TECH_USER_ID_STR,
            "locale": "en-US",
            "timezone": "America/Chicago",
        },
        {
            "display_name": "John Smith",
            "dba_name": None,
            "notes": "Prefers morning appointments. Has a dog — call ahead.",
            "taxability_code": None,
            "last_assigned_tech_id": TECH_USER_ID_STR,
            "locale": "en-US",
            "timezone": "America/New_York",
        },
    ]
    for cu in customer_updates:
        db.execute(
            text("""
                UPDATE public.customer
                SET dba_name = COALESCE(dba_name, :dba_name),
                    notes = COALESCE(notes, :notes),
                    taxability_code = COALESCE(taxability_code, :taxability_code),
                    last_assigned_tech_id = COALESCE(last_assigned_tech_id,
                        CAST(:tech_id AS uuid)),
                    locale = COALESCE(locale, :locale),
                    timezone = COALESCE(timezone, :timezone),
                    updated_at = NOW()
                WHERE tenant_id = :tid AND display_name = :display_name
            """),
            {
                "tid": tid,
                "display_name": cu["display_name"],
                "dba_name": cu["dba_name"],
                "notes": cu["notes"],
                "taxability_code": cu["taxability_code"],
                "tech_id": cu["last_assigned_tech_id"],
                "locale": cu["locale"],
                "timezone": cu["timezone"],
            },
        )
    print(
        f"  ✅ [customer] dba_name/notes/taxability_code/locale/timezone set on "
        f"{len(customer_updates)} customers"
    )

    # ── 7. Site optional fields ───────────────────────────────────────────────
    site_updates = [
        {
            "site_name": "Smith Residence",
            "notes": "Panel is in the basement. Bring 200A fuses.",
            "hazard_notes": None,
            "jurisdiction_code": "US-DEFAULT",
            "gate_code": None,
            "access_instructions": None,
        },
        {
            "site_name": "Johnson Home",
            "notes": "Ring doorbell on arrival.",
            "hazard_notes": None,
            "jurisdiction_code": "US-TX-HARRIS",
            "gate_code": None,
            "access_instructions": None,
        },
        {
            "site_name": "Apex HQ",
            "notes": None,
            "hazard_notes": "Asbestos confirmed in east wall — PPE required before panel work.",
            "jurisdiction_code": "US-DEFAULT",
            "gate_code": None,
            "access_instructions": None,
        },
        {
            "site_name": "Metro Office Park",
            "notes": None,
            "hazard_notes": None,
            "jurisdiction_code": "US-TX-HARRIS",
            "gate_code": "#5588",
            "access_instructions": "Park on the east side. Unit B is second door from the stairwell.",
        },
    ]
    for su in site_updates:
        db.execute(
            text("""
                UPDATE public.site
                SET notes = COALESCE(notes, :notes),
                    hazard_notes = COALESCE(hazard_notes, :hazard_notes),
                    jurisdiction_code = COALESCE(jurisdiction_code, :jurisdiction_code),
                    gate_code = COALESCE(gate_code, :gate_code),
                    access_instructions = COALESCE(access_instructions, :access_instructions),
                    updated_at = NOW()
                WHERE tenant_id = :tid AND name = :site_name
            """),
            {
                "tid": tid,
                "site_name": su["site_name"],
                "notes": su["notes"],
                "hazard_notes": su["hazard_notes"],
                "jurisdiction_code": su["jurisdiction_code"],
                "gate_code": su["gate_code"],
                "access_instructions": su["access_instructions"],
            },
        )
    print(
        f"  ✅ [site] notes/hazard_notes/jurisdiction_code/gate_code/access_instructions "
        f"set on {len(site_updates)} sites"
    )

    # ── 8. Invoice optional fields ────────────────────────────────────────────
    # issued_at is already set on INV-900001 (from _seed_conv_chain).
    # We add: payment_terms, customer_notes.
    db.execute(
        text("""
            UPDATE public.invoice
            SET payment_terms = COALESCE(payment_terms, 'net_30'),
                customer_notes = COALESCE(customer_notes,
                    'Thank you for your business! Payment due within 30 days.'),
                updated_at = NOW()
            WHERE tenant_id = :tid AND invoice_number = 'INV-900001'
        """),
        {"tid": tid},
    )
    print("  ✅ [invoice] payment_terms + customer_notes set on INV-900001")

    # ── 9. BILLING-B1: Progress payment schedule on QUO-900002 (Apex HQ) ──────
    # One active schedule with 3 draws (deposit + rough-in + final) that
    # reconcile exactly to the quote total (345600 cents = $3,456.00).
    # Draw 1 (deposit) is pre-linked to a generated progress invoice so the FE
    # has a "partially invoiced schedule" to render.
    # Business-key lookup (never hardcode scenario UUIDs — README §7).
    _seed_payment_schedule(db, tid)

    print("  ✅ SD-7 Batch 1 optional fields complete")


def mode_inspect(tenant_id: UUID):
    """Show current state of quote-to-cash scenario data with actual values."""
    print("=== seed_scenario_quote_to_cash: inspect mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        # Customers
        customers = db.execute(
            text("""
                SELECT c.id, c.display_name, c.type, cls.code AS lifecycle
                FROM public.customer c
                LEFT JOIN public.customer_lifecycle_status cls ON cls.id = c.lifecycle_status_id
                WHERE c.tenant_id = :tid ORDER BY c.display_name
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [customer]  {len(customers)} row(s)")
        for c in customers:
            print(
                f"    • {c.id}  '{c.display_name}'  type={c.type}  lifecycle={c.lifecycle}"
            )
        print()

        # Sites
        sites = db.execute(
            text(
                "SELECT id, name, customer_id FROM public.site WHERE tenant_id = :tid ORDER BY name"
            ),
            {"tid": tid},
        ).fetchall()
        print(f"  [site]  {len(sites)} row(s)")
        for s in sites:
            print(f"    • {s.id}  '{s.name}'  customer={s.customer_id}")
        print()

        # Pricebook items
        items = db.execute(
            text("""
                SELECT pi.id, pi.sku, pi.name, pi.taxability_code, piv.default_unit_price_cents
                FROM public.pricebook_item pi
                LEFT JOIN public.pricebook_item_version piv ON piv.pricebook_item_id = pi.id
                WHERE pi.tenant_id = :tid ORDER BY pi.sku
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [pricebook_item + version]  {len(items)} row(s)")
        for i in items:
            price = (
                f"${i.default_unit_price_cents / 100:.2f}"
                if i.default_unit_price_cents
                else "no version"
            )
            print(f"    • {i.sku}  '{i.name}'  {price}  taxability={i.taxability_code}")
        print()

        # Quotes
        quotes = db.execute(
            text("""
                SELECT q.id, q.quote_number, qs.code AS status, q.subtotal_cents, q.total_cents, q.currency
                FROM public.quote q
                JOIN public.quote_status qs ON qs.id = q.status_id
                WHERE q.tenant_id = :tid ORDER BY qs.code, q.quote_number
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [quote]  {len(quotes)} row(s)")
        for q in quotes:
            print(
                f"    • {q.quote_number}  status={q.status}  subtotal=${q.subtotal_cents / 100:.2f}  total=${q.total_cents / 100:.2f}"
            )
        print()

        # Quote lines
        lines = db.execute(
            text("""
                SELECT ql.quote_id, ql.position, ql.description, ql.quantity, ql.unit_price_cents, ql.subtotal_cents
                FROM public.quote_line ql
                WHERE ql.tenant_id = :tid ORDER BY ql.quote_id, ql.position
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [quote_line]  {len(lines)} row(s)")
        for ln in lines:
            print(
                f"    • quote={ln.quote_id}  pos={ln.position}  '{ln.description}'  qty={ln.quantity}  unit=${ln.unit_price_cents / 100:.2f}  subtotal=${ln.subtotal_cents / 100:.2f}"
            )
        print()

        # Jobs
        jobs = db.execute(
            text("""
                SELECT j.id, j.job_number, js.code AS status,
                       j.estimated_duration_minutes, j.quote_version_id
                FROM public.job j
                JOIN public.job_status js ON js.id = j.status_id
                WHERE j.tenant_id = :tid ORDER BY j.job_number
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [job]  {len(jobs)} row(s)")
        for j in jobs:
            dur_str = (
                f"  est_duration={j.estimated_duration_minutes}min"
                if j.estimated_duration_minutes
                else ""
            )
            qv_str = (
                f"  quote_version_id={j.quote_version_id}" if j.quote_version_id else ""
            )
            print(
                f"    • {j.job_number}  status={j.status}  id={j.id}{dur_str}{qv_str}"
            )
        print()

        # Invoices — SD-7 Batch 3: issued_at, payment_terms, customer_notes
        invoices = db.execute(
            text("""
                SELECT i.id, i.invoice_number, ist.code AS status,
                       i.total_cents, i.balance_due_cents,
                       i.issued_at, i.payment_terms, i.customer_notes
                FROM public.invoice i
                JOIN public.invoice_status ist ON ist.id = i.status_id
                WHERE i.tenant_id = :tid ORDER BY i.invoice_number
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [invoice]  {len(invoices)} row(s)")
        for inv in invoices:
            notes_str = "  customer_notes=set" if inv.customer_notes else ""
            terms_str = f"  terms={inv.payment_terms}" if inv.payment_terms else ""
            issued_str = f"  issued_at={inv.issued_at}" if inv.issued_at else ""
            print(
                f"    • {inv.invoice_number}  status={inv.status}  total=${inv.total_cents / 100:.2f}"
                f"  balance=${inv.balance_due_cents / 100:.2f}{issued_str}{terms_str}{notes_str}"
            )
        print()

        # SD-6: Invoice lines
        inv_lines = db.execute(
            text("""
                SELECT il.invoice_id, COUNT(*) as cnt, SUM(il.subtotal_cents) as subtotal, SUM(il.total_cents) as total
                FROM public.invoice_line il
                WHERE il.tenant_id = :tid
                GROUP BY il.invoice_id
            """),
            {"tid": tid},
        ).fetchall()
        print(
            f"\n  [invoice_line]  {sum(r.cnt for r in inv_lines)} row(s) across {len(inv_lines)} invoice(s)"
        )
        for r in inv_lines:
            print(
                f"    • invoice={r.invoice_id}  lines={r.cnt}  subtotal=${r.subtotal / 100:.2f}  total=${r.total / 100:.2f}"
            )
        print()

        # SD-6: Change orders
        cos = db.execute(
            text("""
                SELECT co.id, co.description, co.subtotal_cents, co.total_cents,
                       COUNT(col.id) AS line_count
                FROM public.change_order co
                LEFT JOIN public.change_order_line col ON col.change_order_id = co.id
                WHERE co.tenant_id = :tid
                GROUP BY co.id, co.description, co.subtotal_cents, co.total_cents
                ORDER BY co.created_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [change_order]  {len(cos)} row(s)")
        for co in cos:
            print(
                f"    • {co.id}  lines={co.line_count}  subtotal=${co.subtotal_cents / 100:.2f}  total=${co.total_cents / 100:.2f}"
            )
            print(f"      '{co.description[:80]}'")
        print()

        # Payments
        payments = db.execute(
            text("""
                SELECT p.id, p.invoice_id, ps.code AS status, p.amount_cents, p.paid_via
                FROM public.payment p
                JOIN public.payment_status ps ON ps.id = p.status_id
                WHERE p.tenant_id = :tid ORDER BY p.paid_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [payment]  {len(payments)} row(s)")
        for pmt in payments:
            print(
                f"    • invoice={pmt.invoice_id}  status={pmt.status}  amount=${pmt.amount_cents / 100:.2f}  via={pmt.paid_via}"
            )
        print()

        # SD-7 Batch 1: quote_line_tax_component
        qltc_rows = db.execute(
            text("""
                SELECT COUNT(*) AS cnt, component_code, rate_pct
                FROM public.quote_line_tax_component
                WHERE tenant_id = :tid
                GROUP BY component_code, rate_pct
                ORDER BY component_code
            """),
            {"tid": tid},
        ).fetchall()
        total_qltc = sum(r.cnt for r in qltc_rows)
        print(f"  [quote_line_tax_component]  {total_qltc} row(s)")
        for r in qltc_rows:
            print(
                f"    • component={r.component_code}  rate={r.rate_pct}%  count={r.cnt}"
            )
        print()

        # SD-7 Batch 1: change_order_line_tax_component
        coltc_rows = db.execute(
            text("""
                SELECT COUNT(*) AS cnt, component_code, rate_pct
                FROM public.change_order_line_tax_component
                WHERE tenant_id = :tid
                GROUP BY component_code, rate_pct
                ORDER BY component_code
            """),
            {"tid": tid},
        ).fetchall()
        total_coltc = sum(r.cnt for r in coltc_rows)
        print(f"  [change_order_line_tax_component]  {total_coltc} row(s)")
        for r in coltc_rows:
            print(
                f"    • component={r.component_code}  rate={r.rate_pct}%  count={r.cnt}"
            )
        print()

        # SD-7 Batch 1: quote_acceptance
        qa_rows = db.execute(
            text("""
                SELECT qa.id, qa.quote_version_id, qa.accepted_by_user_id,
                       qa.quote_public_link_id, qa.created_at
                FROM public.quote_acceptance qa
                WHERE qa.tenant_id = :tid
                ORDER BY qa.created_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [quote_acceptance]  {len(qa_rows)} row(s)")
        for r in qa_rows:
            print(
                f"    • {r.id}  quote_version={r.quote_version_id}  accepted_by={r.accepted_by_user_id}"
                f"  public_link={'set' if r.quote_public_link_id else 'NULL (internal)'}"
            )
        print()

        # SD-7 Batch 1: quote_approval_comment
        # MCP-verified columns: id, tenant_id, quote_id, quote_version_id,
        #   target_line_id, author_user_id, comment_type, content, created_at
        qac_rows = db.execute(
            text("""
                SELECT id, quote_id, comment_type, content
                FROM public.quote_approval_comment
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [quote_approval_comment]  {len(qac_rows)} row(s)")
        for r in qac_rows:
            print(
                f"    • {r.id}  quote={r.quote_id}  type={r.comment_type}"
                f"  content={r.content[:60] if r.content else ''}..."
            )
        print()

        # SD-7 Batch 1: quote_message
        # MCP-verified columns: id, tenant_id, quote_id, contact_id,
        #   action_type, message, attachments
        qm_rows = db.execute(
            text("""
                SELECT id, quote_id, action_type, message
                FROM public.quote_message
                WHERE tenant_id = :tid
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [quote_message]  {len(qm_rows)} row(s)")
        for r in qm_rows:
            print(
                f"    • {r.id}  quote={r.quote_id}  action_type={r.action_type}"
                f"  message={r.message[:60] if r.message else ''}..."
            )
        print()


def _call_seed_change_orders_from_mode_seed(
    db, tid, pricebook_item_ids, qco_line_type_ids
):
    """Wrapper called from mode_seed after all quotes are processed."""
    _seed_change_orders(db, tid, pricebook_item_ids, qco_line_type_ids)


def mode_show():
    """Print what would be seeded without touching the DB."""
    print("=== seed_scenario_quote_to_cash: show mode ===\n")
    print(f"Customers ({len(CUSTOMERS)}):")
    for c in CUSTOMERS:
        print(f"  • {c['display_name']}  type={c['type']}  lifecycle={c['lifecycle']}")
    print(f"\nSites ({len(CUSTOMER_SITES)}):")
    for s in CUSTOMER_SITES:
        print(
            f"  • {s['site_name']}  {s['line1']}, {s['city']}, {s['state']}  (customer_idx={s['customer_idx']})"
        )
    print(f"\nPricebook Items ({len(PRICEBOOK_ITEMS)}):")
    for p in PRICEBOOK_ITEMS:
        print(
            f"  • {p['name']}  sku={p['sku']}  ${p['unit_price_cents'] / 100:.2f}  taxability={p['taxability_code']}"
        )
    print("\nDraft Quote (QTC-001):")
    print("  • Draft quote for John Smith @ 123 Main St, Brooklyn NY")
    print("  • Lines 1–8 covering all qco_line_type codes")
    print(f"\nAdditional Quotes ({len(QUOTES)}):")
    for q in QUOTES:
        print(
            f"  • {q['quote_number']}  status={q['status_code']}  total=${q['total_cents'] / 100:.2f}"
        )


def _seed_sd7_batch3_fields(db, tid: str):
    """SD-7 Batch 3: job.estimated_duration_minutes, job.quote_version_id on JOB-900001;
    invoice.issued_at, invoice.payment_terms, invoice.customer_notes on issued/paid/partial invoices.
    """
    print("\n  -- SD-7 Batch 3: job/invoice optional fields --")

    # ── Job: estimated_duration_minutes = 480 on JOB-900001 ──────────────────
    job_row = db.execute(
        text(
            "SELECT id FROM public.job WHERE tenant_id = :tid AND job_number = 'JOB-900001' LIMIT 1"
        ),
        {"tid": tid},
    ).first()
    if job_row:
        # Look up quote_version_id for QUO-900006 (converted quote)
        qv_row = db.execute(
            text("""
                SELECT qv.id AS qv_id
                FROM public.quote_version qv
                JOIN public.quote q ON q.id = qv.quote_id
                WHERE q.tenant_id = :tid AND q.quote_number = 'QUO-900006'
                ORDER BY qv.created_at DESC
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        quote_version_id = str(qv_row.qv_id) if qv_row else None

        # JOB-UI-B1: Also set title from linked quote (idempotent — sets it if not already set or updates)
        qtitle_row = db.execute(
            text("""
                SELECT q.title FROM public.quote q
                JOIN public.job j ON j.quote_id = q.id
                WHERE j.id = :jid AND j.tenant_id = :tid
                LIMIT 1
            """),
            {"jid": str(job_row.id), "tid": tid},
        ).first()
        job_title = qtitle_row.title if qtitle_row and qtitle_row.title else None

        db.execute(
            text("""
                UPDATE public.job
                SET estimated_duration_minutes = 480,
                    quote_version_id = :qv_id,
                    title = COALESCE(title, :title),
                    updated_at = NOW()
                WHERE id = :jid AND tenant_id = :tid
            """),
            {
                "jid": str(job_row.id),
                "qv_id": quote_version_id,
                "tid": tid,
                "title": job_title,
            },
        )
        print(
            f"  ✅ [job] JOB-900001 estimated_duration_minutes=480  quote_version_id={quote_version_id}  title={job_title}"
        )
    else:
        print("  ℹ️  [job] JOB-900001 not found — skipping")

    # ── Invoices: issued_at, payment_terms, customer_notes ───────────────────
    # issued/paid/partial invoices get issued_at set; INV-900001 gets notes
    inv_rows = db.execute(
        text("""
            SELECT i.id, i.invoice_number, is2.code AS status_code, i.created_at
            FROM public.invoice i
            JOIN public.invoice_status is2 ON is2.id = i.status_id
            WHERE i.tenant_id = :tid
              AND is2.code IN ('issued', 'paid', 'partial')
            ORDER BY i.invoice_number
        """),
        {"tid": tid},
    ).fetchall()

    for inv in inv_rows:
        inv_id = str(inv.id)
        # issued_at = created_at + 1 day (simulates same-day issue)
        issued_at_expr = "created_at + INTERVAL '1 day'"

        # payment_terms and customer_notes per invoice
        if inv.invoice_number == "INV-900001":
            payment_terms = "net_30"
            customer_notes = "Thank you for your business! Payment due within 30 days."
        else:
            payment_terms = "net_30"
            customer_notes = None

        db.execute(
            text("""
                UPDATE public.invoice
                SET issued_at = COALESCE(issued_at, created_at + INTERVAL '1 day'),
                    payment_terms = COALESCE(payment_terms, :payment_terms),
                    customer_notes = COALESCE(customer_notes, :customer_notes),
                    updated_at = NOW()
                WHERE id = :inv_id AND tenant_id = :tid
            """),
            {
                "payment_terms": payment_terms,
                "customer_notes": customer_notes,
                "inv_id": inv_id,
                "tid": tid,
            },
        )
        print(
            f"  ✅ [invoice] {inv.invoice_number} issued_at=set  payment_terms={payment_terms}"
            + ("  customer_notes=set" if customer_notes else "")
        )


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_quote_to_cash.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(
        args, "reset", False
    ):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_quote_to_cash.py")
    tenant_id = _get_tenant_id()

    if args.reset:
        mode_reset(tenant_id)
    elif args.mode == "seed":
        mode_seed(tenant_id)
    elif args.mode == "inspect":
        mode_inspect(tenant_id)
    elif args.mode == "show":
        mode_show()
