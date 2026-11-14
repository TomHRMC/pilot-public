"""
seed_scenario_notifications.py — Group D: Notification pipeline scenario data.

Purpose: Seeds the full notification delivery chain for the owner user:
  - in_app_notification (5 rows) — SD-6
  - notification_event (3 events: quote_accepted, dunning_reminder, job_assigned) — SD-7 Batch 2
  - notification_outbox (email + in_app + push, 3 channels × 3 events = 9 rows) — SD-7 Batch 2
  - notification_delivery_attempt (1 per outbox row, status=delivered) — SD-7 Batch 2

Schema verified via MCP 2026-07-23:
  notification_event: id, tenant_id, notification_type_code, entity_type_code, entity_id,
                      occurred_at, payload, created_at, created_by
  notification_outbox: id, notification_event_id, tenant_id, recipient_user_id, channel,
                       user_endpoint_id, to_address, subject, body, status, attempt_count,
                       priority, category_id, contextdata, created_at, updated_at, created_by, updated_by
  notification_delivery_attempt: id (bigint serial), notification_outbox_id, tenant_id,
                                 attempt_no, status, provider, details, attempted_at,
                                 completed_at, retryable, created_at, created_by

Hard constraints: NEVER seed channel='sms' in notification_outbox (hold until Telnyx 10DLC live).

Modes:
  --mode seed     (default) idempotent insert
  --mode inspect  show current state
  --mode show     print definitions, no DB
  --reset         wipe this scenario's data
"""

import argparse
import json
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

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
TECH_USER_ID = UUID("00000000-0000-0000-0000-000000000003")

# Fixed reference date — consistent with all other Group D scripts
ANCHOR_DATE = datetime(2026, 7, 1, tzinfo=UTC)

# 5 notifications for owner user covering all categories and read/unread states (SD-6)
NOTIFICATIONS = [
    {
        "category_id": "job_activity",
        "body": "Tech assigned to Panel Upgrade job (JOB-SEED-A). Scheduled for tomorrow at 8:00 AM.",
        "deep_link_target": "/jobs/JOB-SEED-A",
        "priority": "standard",
        "read_at": None,  # unread
        "created_at": ANCHOR_DATE - timedelta(days=2),
    },
    {
        "category_id": "sync_conflicts",
        "body": "QuickBooks sync conflict on invoice INV-900003: customer name mismatch. Review required before next sync.",
        "deep_link_target": "/settings/quickbooks/conflicts",
        "priority": "critical",
        "read_at": None,  # unread
        "created_at": ANCHOR_DATE - timedelta(days=1),
    },
    {
        "category_id": "billing",
        "body": "Invoice INV-900004 is overdue by 14 days. Second dunning reminder sent to customer.",
        "deep_link_target": "/invoices/INV-900004",
        "priority": "standard",
        "read_at": ANCHOR_DATE - timedelta(days=3),  # read
        "created_at": ANCHOR_DATE - timedelta(days=3),
    },
    {
        "category_id": "customer_activity",
        "body": 'SMS sent to Carlos Rivera: "On my way to your location. ETA 15 minutes." Delivered successfully.',
        "deep_link_target": "/communications",
        "priority": "standard",
        "read_at": ANCHOR_DATE - timedelta(days=5),  # read
        "created_at": ANCHOR_DATE - timedelta(days=5),
    },
    {
        "category_id": "field_issues",
        "body": "GPS variance alert: tech location differs from job site by more than 0.5 miles on DISP-002. Review if unexpected.",
        "deep_link_target": "/dispatch",
        "priority": "standard",
        "read_at": ANCHOR_DATE - timedelta(days=7),  # read
        "created_at": ANCHOR_DATE - timedelta(days=7),
    },
]

# SD-7 Batch 2: notification_event definitions (3 events)
# Uses only notification_type codes verified in live DB (MCP 2026-07-23).
NOTIFICATION_EVENTS = [
    {
        "notification_type_code": "quote_accepted",
        "entity_type_code": "quote",
        "entity_id": "QUO-900005",
        "category_id": "quote_approvals",
        "occurred_at": ANCHOR_DATE - timedelta(days=5),
        "payload": {
            "quote_number": "QUO-900005",
            "accepted_by": "owner",
            "note": "Customer verbally accepted; owner recorded in system.",
        },
        "outbox_entries": [
            {
                "channel": "email",
                "to_address": "dev@pilot.local",
                "subject": "Quote QUO-900005 Accepted",
                "body": "Quote QUO-900005 has been accepted by the customer. Proceed to schedule the job.",
                "provider": "sendgrid",
            },
            {
                "channel": "in_app",
                "to_address": None,
                "subject": None,
                "body": "Quote QUO-900005 accepted. Customer confirmed via phone. Ready to convert to job.",
                "provider": "internal",
            },
            {
                "channel": "push",
                "to_address": None,
                "subject": None,
                "body": "Quote accepted: QUO-900005. Tap to view details.",
                "provider": "expo",
            },
        ],
    },
    {
        "notification_type_code": "dunning_reminder",
        "entity_type_code": "invoice",
        "entity_id": "INV-900004",
        "category_id": "billing",
        "occurred_at": ANCHOR_DATE - timedelta(days=3),
        "payload": {
            "invoice_number": "INV-900004",
            "days_overdue": 14,
            "reminder_sequence": 2,
            "balance_due_cents": 115630,
        },
        "outbox_entries": [
            {
                "channel": "email",
                "to_address": "dev@pilot.local",
                "subject": "Payment Reminder: INV-900004 is 14 Days Overdue",
                "body": "Invoice INV-900004 for $1,156.30 is now 14 days overdue. Second reminder sent to customer.",
                "provider": "sendgrid",
            },
            {
                "channel": "in_app",
                "to_address": None,
                "subject": None,
                "body": "INV-900004 is 14 days overdue. Second dunning reminder sent to customer automatically.",
                "provider": "internal",
            },
            {
                "channel": "push",
                "to_address": None,
                "subject": None,
                "body": "Overdue invoice: INV-900004 ($1,156.30). Tap to review.",
                "provider": "expo",
            },
        ],
    },
    {
        "notification_type_code": "job_assigned",
        "entity_type_code": "job",
        "entity_id": "JOB-SEED-A",
        "category_id": "job_activity",
        "occurred_at": ANCHOR_DATE - timedelta(days=2),
        "payload": {
            "job_number": "JOB-SEED-A",
            "assigned_to": "tech@pilot.local",
            "scheduled_start": str((ANCHOR_DATE - timedelta(days=29)).date()),
        },
        "outbox_entries": [
            {
                "channel": "email",
                "to_address": "dev@pilot.local",
                "subject": "Tech Assigned: Panel Upgrade Job",
                "body": "Technician has been assigned to the Panel Upgrade job. Scheduled for tomorrow at 8:00 AM.",
                "provider": "sendgrid",
            },
            {
                "channel": "in_app",
                "to_address": None,
                "subject": None,
                "body": "Panel Upgrade job assigned to tech. Scheduled start: 8:00 AM tomorrow.",
                "provider": "internal",
            },
            {
                "channel": "push",
                "to_address": None,
                "subject": None,
                "body": "Job assigned: Panel Upgrade. Tech confirmed for tomorrow 8AM.",
                "provider": "expo",
            },
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_notifications.py — Group D notifications seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


def mode_seed():
    """Seed in_app_notification, notification_event, outbox, and delivery_attempt rows."""
    print("=== seed_scenario_notifications: seed mode ===")
    print(f"    Tenant ID: {TENANT_ID}\n")

    tid = str(TENANT_ID)
    uid = str(OWNER_USER_ID)

    with get_db_session() as db:
        # ── SD-6: in_app_notification rows ────────────────────────────────────
        existing_count = db.execute(
            text("""
                SELECT COUNT(*) FROM public.in_app_notification
                WHERE tenant_id = :tid AND user_id = :uid
            """),
            {"tid": tid, "uid": uid},
        ).scalar()

        if existing_count >= len(NOTIFICATIONS):
            print(
                f"  ℹ️  [in_app_notification] {existing_count} notification(s) already exist for owner user"
            )
        else:
            for n in NOTIFICATIONS:
                db.execute(
                    text("""
                        INSERT INTO public.in_app_notification
                        (id, tenant_id, user_id, category_id, body,
                         deep_link_target, priority, read_at, created_at, created_by)
                        VALUES (
                            gen_random_uuid(), :tid, :uid, :category_id, :body,
                            :deep_link_target, :priority, :read_at, :created_at, NULL
                        )
                    """),
                    {
                        "tid": tid,
                        "uid": uid,
                        "category_id": n["category_id"],
                        "body": n["body"],
                        "deep_link_target": n["deep_link_target"],
                        "priority": n["priority"],
                        "read_at": n["read_at"],
                        "created_at": n["created_at"],
                    },
                )
                read_label = "unread" if n["read_at"] is None else "read"
                print(
                    f"  ✅ [in_app_notification] category={n['category_id']}  "
                    f"priority={n['priority']}  {read_label}"
                )
            print(
                f"\n  ✅ [in_app_notification] {len(NOTIFICATIONS)} notifications seeded for dev@pilot.local"
            )

        # ── SD-7 Batch 2: Lookup owner user endpoints for outbox ──────────────
        user_endpoints = db.execute(
            text("""
                SELECT id, channel, value FROM public.user_endpoint
                WHERE user_id = :uid AND channel IN ('email', 'in_app', 'push')
                  AND is_active = true
            """),
            {"uid": uid},
        ).fetchall()
        endpoint_map = {ep.channel: str(ep.id) for ep in user_endpoints}
        email_address = next(
            (ep.value for ep in user_endpoints if ep.channel == "email"),
            "dev@pilot.local",
        )

        # ── SD-7 Batch 2: notification_event + notification_outbox + delivery_attempt ──
        print("\n  -- SD-7 Batch 2: notification_event / outbox / delivery_attempt --")
        for ev_def in NOTIFICATION_EVENTS:
            # Idempotency: check by type_code + entity_id
            existing_ev = db.execute(
                text("""
                    SELECT id FROM public.notification_event
                    WHERE tenant_id = :tid
                      AND notification_type_code = :type_code
                      AND entity_id = :entity_id
                    LIMIT 1
                """),
                {
                    "tid": tid,
                    "type_code": ev_def["notification_type_code"],
                    "entity_id": ev_def["entity_id"],
                },
            ).first()

            if existing_ev:
                print(
                    f"  ℹ️  [notification_event] {ev_def['notification_type_code']} / {ev_def['entity_id']} already exists"
                )
                event_id = str(existing_ev.id)
            else:
                ev_result = db.execute(
                    text("""
                        INSERT INTO public.notification_event
                        (id, tenant_id, notification_type_code, entity_type_code,
                         entity_id, occurred_at, payload, created_at, created_by)
                        VALUES (
                            gen_random_uuid(), :tid, :type_code, :entity_type,
                            :entity_id, :occurred_at, CAST(:payload AS jsonb),
                            :occurred_at, NULL
                        )
                        RETURNING id
                    """),
                    {
                        "tid": tid,
                        "type_code": ev_def["notification_type_code"],
                        "entity_type": ev_def["entity_type_code"],
                        "entity_id": ev_def["entity_id"],
                        "occurred_at": ev_def["occurred_at"],
                        "payload": json.dumps(ev_def["payload"]),
                    },
                )
                event_id = str(ev_result.first().id)
                print(
                    f"  ✅ [notification_event] {ev_def['notification_type_code']} → entity={ev_def['entity_id']}"
                )

            # Outbox entries for this event — email + in_app + push only (no SMS)
            for ob_def in ev_def["outbox_entries"]:
                channel = ob_def["channel"]
                # Idempotency: check by event_id + channel
                existing_ob = db.execute(
                    text("""
                        SELECT id FROM public.notification_outbox
                        WHERE notification_event_id = :event_id AND channel = :channel
                        LIMIT 1
                    """),
                    {"event_id": event_id, "channel": channel},
                ).first()

                if existing_ob:
                    print(
                        f"  ℹ️  [notification_outbox] {channel} already exists for event"
                    )
                    outbox_id = str(existing_ob.id)
                else:
                    # to_address MUST be NULL when recipient_user_id is set.
                    # notification_outbox_recipient_exclusive_chk requires exactly ONE of
                    # (recipient_contact_id, recipient_user_id, to_address) to be non-null.
                    # The delivery service resolves the email from user_endpoint at send time.
                    to_addr = None
                    endpoint_id = endpoint_map.get(channel)
                    ob_result = db.execute(
                        text("""
                            INSERT INTO public.notification_outbox
                            (id, notification_event_id, tenant_id, recipient_user_id,
                             channel, user_endpoint_id, to_address, subject, body,
                             status, attempt_count, priority, category_id,
                             created_at, updated_at, created_by, updated_by)
                            VALUES (
                                gen_random_uuid(), :event_id, :tid, :uid,
                                :channel, :endpoint_id, :to_address, :subject, :body,
                                'sent', 1, 5, :category_id,
                                NOW(), NOW(), NULL, NULL
                            )
                            RETURNING id
                        """),
                        {
                            "event_id": event_id,
                            "tid": tid,
                            "uid": uid,
                            "channel": channel,
                            "endpoint_id": endpoint_id,
                            "to_address": to_addr,
                            "subject": ob_def.get("subject"),
                            "body": ob_def["body"],
                            "category_id": ev_def["category_id"],
                        },
                    )
                    outbox_id = str(ob_result.first().id)
                    print(
                        f"  ✅ [notification_outbox] channel={channel}  event={ev_def['notification_type_code']}"
                    )

                # Delivery attempt: 1 per outbox row, status=delivered
                existing_da = db.execute(
                    text("""
                        SELECT id FROM public.notification_delivery_attempt
                        WHERE notification_outbox_id = :outbox_id AND attempt_no = 1
                        LIMIT 1
                    """),
                    {"outbox_id": outbox_id},
                ).first()

                if existing_da:
                    print(
                        f"  ℹ️  [notification_delivery_attempt] already exists for outbox {outbox_id}"
                    )
                else:
                    attempted_at = ev_def["occurred_at"] + timedelta(seconds=5)
                    db.execute(
                        text("""
                            INSERT INTO public.notification_delivery_attempt
                            (notification_outbox_id, tenant_id, attempt_no, status,
                             provider, details, http_status, attempted_at, completed_at,
                             retryable, duration_ms, created_at, created_by)
                            VALUES (
                                :outbox_id, :tid, 1, 'delivered',
                                :provider, CAST(:details AS jsonb), 200,
                                :attempted_at, :completed_at,
                                false, :duration_ms, :attempted_at, NULL
                            )
                        """),
                        {
                            "outbox_id": outbox_id,
                            "tid": tid,
                            "provider": ob_def["provider"],
                            "details": json.dumps(
                                {"result": "delivered", "channel": channel}
                            ),
                            "attempted_at": attempted_at,
                            "completed_at": attempted_at + timedelta(milliseconds=250),
                            "duration_ms": 250,
                        },
                    )
                    print(
                        f"  ✅ [notification_delivery_attempt] channel={channel}  status=delivered"
                    )

        db.commit()

    print(f"\n🎉 seed_scenario_notifications complete — data present for {TENANT_ID}")


def mode_reset():
    """Wipe notification scenario data for the owner user (seeded data only)."""
    print("=== seed_scenario_notifications: reset mode ===")
    tid = str(TENANT_ID)
    uid = str(OWNER_USER_ID)

    with get_db_session() as db:
        # SD-7 Batch 2: delivery_attempts → outbox → events (child-first FK order)
        for ev_def in NOTIFICATION_EVENTS:
            ev_row = db.execute(
                text("""
                    SELECT id FROM public.notification_event
                    WHERE tenant_id = :tid
                      AND notification_type_code = :type_code
                      AND entity_id = :entity_id
                    LIMIT 1
                """),
                {
                    "tid": tid,
                    "type_code": ev_def["notification_type_code"],
                    "entity_id": ev_def["entity_id"],
                },
            ).first()
            if not ev_row:
                continue
            event_id = str(ev_row.id)

            # Delete delivery attempts for this event's outboxes
            db.execute(
                text("""
                    DELETE FROM public.notification_delivery_attempt
                    WHERE notification_outbox_id IN (
                        SELECT id FROM public.notification_outbox
                        WHERE notification_event_id = :event_id
                    )
                """),
                {"event_id": event_id},
            )
            # Delete outbox rows
            result_ob = db.execute(
                text(
                    "DELETE FROM public.notification_outbox WHERE notification_event_id = :event_id"
                ),
                {"event_id": event_id},
            )
            # Delete event
            db.execute(
                text("DELETE FROM public.notification_event WHERE id = :id"),
                {"id": event_id},
            )
            if result_ob.rowcount:
                print(
                    f"  🗑  [notification] Deleted event+outbox+attempts for {ev_def['notification_type_code']}"
                )

        # SD-6: in_app_notification
        result = db.execute(
            text("""
                DELETE FROM public.in_app_notification
                WHERE tenant_id = :tid AND user_id = :uid
            """),
            {"tid": tid, "uid": uid},
        )
        db.commit()
        print(
            f"  🗑  [in_app_notification] Deleted {result.rowcount} row(s) for owner user"
        )

    print("\n✅ Notifications scenario data wiped.")
    print("   Run: python migrations/scripts/seed_scenario_notifications.py")
    print("   to re-seed.")


def mode_inspect():
    """Show current state of notification data."""
    print("=== seed_scenario_notifications: inspect mode ===")
    tid = str(TENANT_ID)
    uid = str(OWNER_USER_ID)

    with get_db_session() as db:
        # SD-6: in_app_notification
        rows = db.execute(
            text("""
                SELECT id, category_id, priority, read_at, created_at
                FROM public.in_app_notification
                WHERE tenant_id = :tid AND user_id = :uid
                ORDER BY created_at DESC
            """),
            {"tid": tid, "uid": uid},
        ).fetchall()

        unread = sum(1 for r in rows if r.read_at is None)
        print(
            f"  [in_app_notification]  {len(rows)} row(s)  ({unread} unread)  user=dev@pilot.local"
        )
        for r in rows:
            read_label = (
                "unread" if r.read_at is None else f"read at {r.read_at.date()}"
            )
            print(
                f"    • {r.id}  category={r.category_id}  priority={r.priority}  {read_label}"
            )

        # SD-7 Batch 2: notification_event
        events = db.execute(
            text("""
                SELECT id, notification_type_code, entity_type_code, entity_id, occurred_at
                FROM public.notification_event
                WHERE tenant_id = :tid
                ORDER BY occurred_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [notification_event]  {len(events)} row(s)")
        for ev in events:
            print(
                f"    • {ev.id}  type={ev.notification_type_code}  "
                f"entity={ev.entity_type_code}/{ev.entity_id}  occurred={ev.occurred_at.date()}"
            )

        # SD-7 Batch 2: notification_outbox
        outboxes = db.execute(
            text("""
                SELECT id, channel, status, to_address, attempt_count, category_id
                FROM public.notification_outbox
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [notification_outbox]  {len(outboxes)} row(s)")
        for ob in outboxes:
            print(
                f"    • {ob.id}  channel={ob.channel}  status={ob.status}  "
                f"attempts={ob.attempt_count}  category={ob.category_id}"
            )

        # SD-7 Batch 2: notification_delivery_attempt
        attempts = db.execute(
            text("""
                SELECT nda.id, nda.attempt_no, nda.status, nda.provider, nda.duration_ms, nda.attempted_at
                FROM public.notification_delivery_attempt nda
                WHERE nda.tenant_id = :tid
                ORDER BY nda.attempted_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [notification_delivery_attempt]  {len(attempts)} row(s)")
        for a in attempts:
            print(
                f"    • {a.id}  attempt_no={a.attempt_no}  status={a.status}  "
                f"provider={a.provider}  duration={a.duration_ms}ms"
            )


def mode_show():
    """Print what would be seeded without touching the DB."""
    print("=== seed_scenario_notifications: show mode ===\n")
    print(f"Tenant ID:    {TENANT_ID}")
    print(f"Owner User:   {OWNER_USER_ID}  (dev@pilot.local)")
    print(f"Anchor Date:  {ANCHOR_DATE.date()}\n")
    print(f"in_app_notifications ({len(NOTIFICATIONS)}):")
    for n in NOTIFICATIONS:
        read_label = (
            "unread" if n["read_at"] is None else f"read ({n['read_at'].date()})"
        )
        print(
            f"  • category={n['category_id']}  priority={n['priority']}  {read_label}"
        )
        print(f"    body: {n['body'][:80]}...")

    print(f"\nnotification_events ({len(NOTIFICATION_EVENTS)}) — SD-7 Batch 2:")
    for ev in NOTIFICATION_EVENTS:
        print(
            f"  • type={ev['notification_type_code']}  entity={ev['entity_type_code']}/{ev['entity_id']}"
        )
        print(
            f"    channels: {', '.join(ob['channel'] for ob in ev['outbox_entries'])}"
        )

    total_outbox = sum(len(ev["outbox_entries"]) for ev in NOTIFICATION_EVENTS)
    print(
        f"\nnotification_outbox: {total_outbox} rows (email + in_app + push × 3 events)"
    )
    print(
        f"notification_delivery_attempt: {total_outbox} rows (1 per outbox, status=delivered)"
    )


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_notifications.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(args, "reset", False):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_notifications.py")
    if args.reset:
        mode_reset()
    elif args.mode == "seed":
        mode_seed()
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        mode_show()
