"""
reset_dev_db.py — Group D central control panel.

Purpose: Wipes Group D (scenario) data and offers interactive or CLI-driven
re-seed selection. Does NOT touch Group A/B/C data (lookup tables, platform
config, test tenant infrastructure).

Modes:
  (no args)          Interactive menu
  --wipe-only        Wipe ALL Group D, exit (no prompt)
  --scenarios X,Y    Wipe named scenario(s), then prompt to re-seed
  --mode inspect     Show current Group D row counts, no changes

Usage:
  python migrations/scripts/reset_dev_db.py
  python migrations/scripts/reset_dev_db.py --wipe-only
  python migrations/scripts/reset_dev_db.py --scenarios quote_to_cash
  python migrations/scripts/reset_dev_db.py --scenarios quote_to_cash,dispatch
  python migrations/scripts/reset_dev_db.py --mode inspect
"""

import argparse
import importlib
import os
import sys
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

# ── SCENARIO REGISTRY ────────────────────────────────────────────────────────
# Add new Group D scenarios here. Each entry maps a short key to the seed
# script module path. The interactive menu and --scenarios flag both use this.
SCENARIOS = {
    "quote_to_cash": "migrations.scripts.seed_scenario_quote_to_cash",
    "dispatch": "migrations.scripts.seed_scenario_dispatch",
    "customer_comms": "migrations.scripts.seed_scenario_customer_comms",
    "reporting": "migrations.scripts.seed_scenario_reporting",
    "supplier_catalog": "migrations.scripts.seed_scenario_supplier_catalog",  # SD-09
    "nec": "migrations.scripts.seed_scenario_nec",  # E2E-B1: W-07 NEC calculation
    "mobile_sync": "migrations.scripts.seed_scenario_mobile_sync",  # E2E-B1: W-11 Mobile sync
    "notifications": "migrations.scripts.seed_scenario_notifications",  # SD-6: in_app_notification
    "voice_ai": "migrations.scripts.seed_scenario_voice_ai",  # SD-9: Voice AI history surfaces
}
# ─────────────────────────────────────────────────────────────────────────────

# All Group D tables in strict child-first FK order (derived from pg_constraint audit).
# Some tables lack tenant_id and require a custom subquery DELETE — see GROUP_D_DELETES below.
GROUP_D_TABLES = [
    # ── Deepest children first ────────────────────────────────────────────────
    "loto_confirmation",
    "calendar_sync_conflict",
    "job_tech_assignment",
    "job_time_entry",
    "job_expense",
    "job_notes",
    "job_attachment",
    "change_order_line_tax_component",  # ← SD-7 B1: child of change_order_line
    "change_order_line",
    "change_order",
    "tech_availability",
    # ── Quote children (before quote) ─────────────────────────────────────────
    "quote_acceptance",  # ← SD-7 B1: child of quote_version (before quote_version)
    "quote_line_tax_component",  # ← SD-7 B1: child of quote_line (before quote_line)
    "quote_line",
    # NOTE: quote_version is intentionally NOT here — SD-7 B3 added job.quote_version_id FK,
    # so quote_version must be deleted AFTER job. See below.
    "quote_public_link_contact_action",  # ← child of quote_public_link
    "quote_public_link",  # ← child of quote
    "quote_message",  # ← child of quote
    "quote_pending_edit",  # ← child of quote
    "quote_approval_comment",  # ← child of quote
    # ── Invoice children (before invoice) ─────────────────────────────────────
    "invoice_line_tax_component",  # ← SD-6: child of invoice_line
    "invoice_line",  # ← SD-6: child of invoice
    "invoice_public_link",  # ← child of invoice
    "payment",  # ← child of invoice
    # ── Notification pipeline (SD-7 B2 — child-first) ─────────────────────────
    "notification_delivery_attempt",  # ← SD-7 B2: child of notification_outbox
    "notification_outbox",  # ← SD-7 B2: child of notification_event
    "notification_event",  # ← SD-7 B2
    # ── Mobile sync (SD-7 B2 additions before their parents) ──────────────────
    "mobile_sync_event_audit",  # ← SD-7 B2: child of mobile_sync_owner_escalation
    "mobile_push_permission_state",  # ← SD-7 B2: standalone (device/user refs only)
    # ── Usage tracking (SD-7 B2) ──────────────────────────────────────────────
    "usage_ledger",  # ← SD-7 B2: standalone (no job FK)
    # ── Other children ────────────────────────────────────────────────────────
    "mobile_sync_owner_escalation",  # ← SD-6: W-12 escalations
    "in_app_notification",  # ← SD-6: notifications scenario
    # ── Parent tables ─────────────────────────────────────────────────────────
    "invoice",
    "customer_communication",  # ← child of job + customer (before both)
    "job_recurrence_rule",  # ← child of site + customer
    "job",
    "quote_version",  # ← MOVED: SD-7 B3 set job.quote_version_id FK; must delete after job
    "quote",  # ← before site (site_id FK)
    "pricebook_item_version",
    "pricebook_item",
    "entity_address",
    "entity_contact",
    # contact_endpoint: NOT seeded — channel check constraint allows only email|sms;
    # sms is on hold (§8.2). Wipe is a no-op but safe to include for future use.
    "contact",
    "address",  # ← after entity_address
    "site",
    # ── Customer children (before customer) ───────────────────────────────────
    "customer_sms_consent_audit",  # ← child of customer
    "psp_customer",  # ← child of customer
    "payment_method",  # ← child of customer
    # customer_communication_message_read_state has no tenant_id — handled via subquery in _wipe_all_group_d
    # customer_communication_message has no tenant_id — handled via subquery in _wipe_all_group_d
    "customer_communication_unrouted",  # ← SD-7 B3: parked inbound SMS (has tenant_id)
    "customer_communication_thread",  # ← child of customer + tenant_phone_number
    "customer",
    "tenant_phone_number",  # ← SD-02: customer_comms scenario
    # ── Supplier catalog ──────────────────────────────────────────────────────
    "supplier_item_price",  # ← SD-09 (price → item → supplier)
    "supplier_item",
    "supplier",
    # ── Mobile sync + NEC ─────────────────────────────────────────────────────
    "mobile_sync_event",  # ← E2E-B1 (event → session)
    "mobile_sync_session",
    "nec_calculation_log",  # ← E2E-B1
    # ── Voice AI (SD-9) ───────────────────────────────────────────────────────
    "voice_feedback",  # SD-9: FK → voice_command_log (SET NULL; deleted first)
    "voice_command_entity_link",  # SD-9: FK → voice_command_log (RESTRICT)
    "voice_command_log",  # SD-9: FK → conversation_message
    "conversation_message",  # SD-9: FK → conversation_session
    "conversation_session",  # SD-9
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="reset_dev_db.py — Group D wipe/reseed control panel"
    )
    parser.add_argument(
        "--mode",
        choices=["inspect"],
        default=None,
        help="inspect: show current Group D row counts; no changes",
    )
    parser.add_argument(
        "--wipe-only",
        action="store_true",
        help="Wipe ALL Group D data and exit without prompting to re-seed",
    )
    parser.add_argument(
        "--scenarios",
        default=None,
        help="Comma-separated scenario keys to wipe (e.g. quote_to_cash,dispatch)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        help="Force interactive menu (also triggered by no args)",
    )
    add_env_args(parser)
    return parser.parse_args()


def _get_tenant_id() -> UUID:
    return UUID(settings.TEST_TENANT_ID)


# ── Core wipe logic ──────────────────────────────────────────────────────────


def _wipe_all_group_d(tenant_id: UUID):
    """Delete all Group D tables scoped to test tenant. Child-first FK order.

    Uses SAVEPOINT per table so a missing table or FK violation on one table
    does not poison the entire transaction (bare except:pass causes InFailedSqlTransaction).
    """
    tid = str(tenant_id)
    total_deleted = 0

    with get_db_session() as db:
        # Special case: customer_communication_message_read_state has no tenant_id
        sp = "sp_ccmrs"
        db.execute(text(f"SAVEPOINT {sp}"))
        try:
            result = db.execute(
                text(
                    "DELETE FROM public.customer_communication_message_read_state "
                    "WHERE message_id IN ("
                    "  SELECT m.id FROM public.customer_communication_message m "
                    "  JOIN public.customer_communication_thread t ON t.id = m.thread_id "
                    "  WHERE t.tenant_id = :tid"
                    ")"
                ),
                {"tid": tid},
            )
            db.execute(text(f"RELEASE SAVEPOINT {sp}"))
            if result.rowcount:
                print(
                    f"  🗑  [{'cust_comm_msg_read_state':<30}] Deleted {result.rowcount} row(s)"
                )
                total_deleted += result.rowcount
        except Exception as exc:
            db.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
            print(
                f"  ⚠️  [{'cust_comm_msg_read_state':<30}] Skipped ({type(exc).__name__})"
            )

        # Special case: customer_communication_message has no tenant_id column
        sp = "sp_ccmsg"
        db.execute(text(f"SAVEPOINT {sp}"))
        try:
            result = db.execute(
                text(
                    "DELETE FROM public.customer_communication_message WHERE thread_id IN "
                    "(SELECT id FROM public.customer_communication_thread WHERE tenant_id = :tid)"
                ),
                {"tid": tid},
            )
            db.execute(text(f"RELEASE SAVEPOINT {sp}"))
            if result.rowcount:
                print(
                    f"  🗑  [{'customer_communication_message':<30}] Deleted {result.rowcount} row(s)"
                )
                total_deleted += result.rowcount
        except Exception as exc:
            db.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
            print(
                f"  ⚠️  [{'customer_communication_message':<30}] Skipped ({type(exc).__name__})"
            )

        for table in GROUP_D_TABLES:
            sp = f"sp_{table[:28]}"  # SAVEPOINT names max 63 chars
            db.execute(text(f"SAVEPOINT {sp}"))
            try:
                result = db.execute(
                    text(f"DELETE FROM public.{table} WHERE tenant_id = :tid"),
                    {"tid": tid},
                )
                db.execute(text(f"RELEASE SAVEPOINT {sp}"))
                if result.rowcount:
                    print(f"  🗑  [{table:<30}] Deleted {result.rowcount} row(s)")
                    total_deleted += result.rowcount
            except Exception as exc:
                db.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
                print(f"  ⚠️  [{table:<30}] Skipped ({type(exc).__name__})")

        db.commit()

    print(f"\n  Total rows deleted: {total_deleted}")


def _wipe_scenario(scenario_key: str, tenant_id: UUID):
    """Wipe a single scenario by importing its reset logic."""
    if scenario_key not in SCENARIOS:
        print(f"  ❌ Unknown scenario: '{scenario_key}'")
        print(f"     Available: {', '.join(SCENARIOS.keys())}")
        return

    module_path = SCENARIOS[scenario_key]
    mod = importlib.import_module(module_path)
    mod.mode_reset(tenant_id)


def _seed_scenario(scenario_key: str, tenant_id: UUID):
    """Run seed for a single scenario."""
    if scenario_key not in SCENARIOS:
        print(f"  ❌ Unknown scenario: '{scenario_key}'")
        return

    module_path = SCENARIOS[scenario_key]
    mod = importlib.import_module(module_path)
    mod.mode_seed(tenant_id)


# ── Inspect mode ─────────────────────────────────────────────────────────────


def mode_inspect(tenant_id: UUID):
    """Show current Group D state with actual data values."""
    print("=== reset_dev_db: Current Group D State ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)
    total = 0

    with get_db_session() as db:
        # Customers
        rows = db.execute(
            text("""
                SELECT c.id, c.display_name, c.type, cls.code AS lifecycle
                FROM public.customer c
                LEFT JOIN public.customer_lifecycle_status cls ON cls.id = c.lifecycle_status_id
                WHERE c.tenant_id = :tid ORDER BY c.display_name
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [customer]  {len(rows)} row(s)")
        for r in rows:
            print(f"    • '{r.display_name}'  type={r.type}  lifecycle={r.lifecycle}")
        total += len(rows)

        # Sites
        rows = db.execute(
            text(
                "SELECT id, name, customer_id FROM public.site WHERE tenant_id = :tid ORDER BY name"
            ),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [site]  {len(rows)} row(s)")
        for r in rows:
            print(f"    • '{r.name}'  customer={r.customer_id}")
        total += len(rows)

        # Jobs
        rows = db.execute(
            text("""
                SELECT j.id, js.code AS status, j.scheduled_start_at
                FROM public.job j
                JOIN public.job_status js ON js.id = j.status_id
                WHERE j.tenant_id = :tid
                ORDER BY j.scheduled_start_at NULLS LAST
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [job]  {len(rows)} row(s)")
        for r in rows:
            sched = str(r.scheduled_start_at) if r.scheduled_start_at else "no schedule"
            print(f"    • {r.id}  status={r.status}  start={sched}")
        total += len(rows)

        # Job assignments
        rows = db.execute(
            text("""
                SELECT jta.job_id, jta.user_id, jta.role, jta.ordinal
                FROM public.job_tech_assignment jta
                WHERE jta.tenant_id = :tid
                ORDER BY jta.job_id
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [job_tech_assignment]  {len(rows)} row(s)")
        for r in rows:
            print(
                f"    • job={r.job_id}  user={r.user_id}  role={r.role}  ordinal={r.ordinal}"
            )
        total += len(rows)

        # Tech availability
        rows = db.execute(
            text("""
                SELECT user_id, availability_type, starts_at, ends_at
                FROM public.tech_availability
                WHERE tenant_id = :tid
                ORDER BY starts_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [tech_availability]  {len(rows)} row(s)")
        for r in rows:
            print(
                f"    • user={r.user_id}  type={r.availability_type}  {r.starts_at} → {r.ends_at}"
            )
        total += len(rows)

        # Quotes
        rows = db.execute(
            text("""
                SELECT q.id, qs.code AS status, q.subtotal_cents, q.total_cents, q.currency
                FROM public.quote q
                JOIN public.quote_status qs ON qs.id = q.status_id
                WHERE q.tenant_id = :tid
                ORDER BY q.created_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [quote]  {len(rows)} row(s)")
        for r in rows:
            print(
                f"    • {r.id}  status={r.status}  subtotal=${r.subtotal_cents / 100:.2f}  total=${r.total_cents / 100:.2f}"
            )
        total += len(rows)

        # Quote lines
        rows = db.execute(
            text("""
                SELECT ql.quote_id, ql.position, ql.description, ql.quantity, ql.unit_price_cents
                FROM public.quote_line ql
                WHERE ql.tenant_id = :tid
                ORDER BY ql.quote_id, ql.position
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [quote_line]  {len(rows)} row(s)")
        for r in rows:
            print(
                f"    • quote={r.quote_id}  pos={r.position}  '{r.description}'  qty={r.quantity}  unit=${r.unit_price_cents / 100:.2f}"
            )
        total += len(rows)

        # Pricebook items
        rows = db.execute(
            text("""
                SELECT pi.sku, pi.name, piv.default_unit_price_cents
                FROM public.pricebook_item pi
                LEFT JOIN public.pricebook_item_version piv ON piv.pricebook_item_id = pi.id
                WHERE pi.tenant_id = :tid
                ORDER BY pi.sku
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [pricebook_item]  {len(rows)} row(s)")
        for r in rows:
            price = (
                f"${r.default_unit_price_cents / 100:.2f}"
                if r.default_unit_price_cents
                else "no version"
            )
            print(f"    • {r.sku}  '{r.name}'  {price}")
        total += len(rows)

        # Remaining tables — counts only (rarely have user-visible data)
        for table in [
            "loto_confirmation",
            "calendar_sync_conflict",
            "invoice",
            "invoice_line",
            "change_order",
            "change_order_line",
            "job_time_entry",
            "job_expense",
            "job_notes",
            "job_attachment",
            "quote_version",
            "entity_address",
            "entity_contact",
            "contact",
        ]:
            try:
                count = db.execute(
                    text(f"SELECT COUNT(*) FROM public.{table} WHERE tenant_id = :tid"),
                    {"tid": tid},
                ).scalar()
                if count:
                    print(f"\n  [{table}]  {count} row(s)")
                    total += count
            except Exception:
                pass

    print("\n  ─────────────────────────────────────")
    print(f"  Total Group D rows: {total}")


# ── Interactive menu ─────────────────────────────────────────────────────────


def _interactive_menu(tenant_id: UUID):
    """Launch the interactive numbered menu."""
    print("=" * 55)
    print("  === Pilot Dev DB Reset Manager ===")
    print("=" * 55)
    print("  Group A/B/C data (lookup tables, platform config,")
    print("  test tenant) is NEVER touched.\n")
    print("  What would you like to do?")
    print("    1. Wipe ALL Group D data (all scenarios)")
    print("    2. Wipe individual scenario(s)")
    print("    3. Inspect current Group D state (row counts)")
    print("    4. Exit")
    print()

    try:
        choice = input("  Choice: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Aborted.")
        return

    if choice == "1":
        _interactive_wipe_all(tenant_id)
    elif choice == "2":
        _interactive_wipe_select(tenant_id)
    elif choice == "3":
        mode_inspect(tenant_id)
    elif choice == "4":
        print("  Exiting.")
    else:
        print(f"  Invalid choice: '{choice}'. Exiting.")


def _interactive_wipe_all(tenant_id: UUID):
    """Wipe all scenarios, then prompt to re-seed."""
    print("\n  Wiping ALL Group D data...\n")
    _wipe_all_group_d(tenant_id)
    _prompt_reseed(list(SCENARIOS.keys()), tenant_id)


def _interactive_wipe_select(tenant_id: UUID):
    """Let user pick one or more scenarios to wipe."""
    scenario_list = list(SCENARIOS.keys())

    print("\n  Select scenarios to wipe (comma-separated numbers, or 'a' for all):")
    for i, key in enumerate(scenario_list, start=1):
        print(f"    {i}. {key}")
    print()

    try:
        sel = input("  Choice: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Aborted.")
        return

    if sel.lower() == "a":
        selected = scenario_list
    else:
        selected = []
        for part in sel.split(","):
            part = part.strip()
            try:
                idx = int(part) - 1
                if 0 <= idx < len(scenario_list):
                    selected.append(scenario_list[idx])
                else:
                    print(f"  ⚠️  Invalid number: {part}")
            except ValueError:
                print(f"  ⚠️  Non-numeric input ignored: '{part}'")

    if not selected:
        print("  No valid scenarios selected. Exiting.")
        return

    print(f"\n  Wiping: {', '.join(selected)}\n")
    for key in selected:
        _wipe_scenario(key, tenant_id)

    _prompt_reseed(selected, tenant_id)


def _prompt_reseed(scenario_keys: list, tenant_id: UUID):
    """After a wipe, ask whether to re-seed."""
    print()
    try:
        ans = input("  ✅ Wipe complete. Re-seed now? (y/N): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        ans = "n"

    if ans == "y":
        print()
        for key in scenario_keys:
            print(f"  → Re-seeding '{key}'...")
            _seed_scenario(key, tenant_id)
    else:
        print("\n  Exiting without re-seed. To re-seed manually:")
        for key in scenario_keys:
            module_path = SCENARIOS.get(key, "")
            script_name = module_path.replace(".", "/") + ".py" if module_path else key
            print(f"    python {script_name}")


# ── CLI non-interactive paths ─────────────────────────────────────────────────


def _cli_wipe_only(tenant_id: UUID):
    """--wipe-only: wipe ALL Group D, exit without prompting."""
    print("=== reset_dev_db: --wipe-only ===")
    print(f"    Tenant ID: {tenant_id}\n")
    print("  Wiping ALL Group D data...\n")
    _wipe_all_group_d(tenant_id)
    print("\n  ✅ All Group D data wiped. No re-seed performed.")
    print("  Run without --wipe-only to use the interactive menu.")


def _cli_scenarios(scenario_keys: list, tenant_id: UUID):
    """--scenarios X,Y: wipe specific scenarios, then prompt to re-seed."""
    print(f"=== reset_dev_db: --scenarios {','.join(scenario_keys)} ===")
    print(f"    Tenant ID: {tenant_id}\n")

    for key in scenario_keys:
        print(f"  Wiping '{key}'...")
        _wipe_scenario(key, tenant_id)
        print()

    _prompt_reseed(scenario_keys, tenant_id)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "reset_dev_db.py")
    # reset_dev_db.py is a wipe tool — design §B.4 requires it to refuse e2e
    # (docker volume wipe) and prod (forbidden wipe). Prod is already caught
    # by the Group D gate above; e2e needs a script-specific check.
    if profile.env.value == "e2e":
        print(
            "ERROR [seed-env]: reset_dev_db.py refuses --env e2e — "
            "E2E DB is wiped via docker volume, not this script (design §B.4).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(
        args, "reset", False
    ):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "reset_dev_db.py")
    tenant_id = _get_tenant_id()

    if args.mode == "inspect":
        mode_inspect(tenant_id)

    elif args.wipe_only:
        _cli_wipe_only(tenant_id)

    elif args.scenarios:
        keys = [k.strip() for k in args.scenarios.split(",") if k.strip()]
        _cli_scenarios(keys, tenant_id)

    else:
        # No args (or --interactive) → interactive menu
        _interactive_menu(tenant_id)
