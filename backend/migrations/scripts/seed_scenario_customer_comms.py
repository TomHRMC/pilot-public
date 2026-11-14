"""
seed_scenario_customer_comms.py — Group D: Customer communications scenario data.

Purpose: Seeds customers with valid E.164 mobile phone numbers, SMS communication
threads, and messages to enable end-to-end testing of the customer comms surface.
NEVER run in production.

Schema verified against live DB 2026-07-06:
  tenant_phone_number: id, tenant_id, phone_number, area_code, carrier, status,
                        created_at, updated_at
  customer: id, tenant_id, type, display_name, first_name, last_name, company_name,
            email, mobile_phone, is_active, lifecycle_status_id,
            preferred_contact_channel, sms_opted_out, sms_opt_in_consent,
            created_at, updated_at
  contact: id, tenant_id, customer_id, first_name, last_name, mobile_phone,
           is_active, created_at, updated_at
  entity_contact: id, tenant_id, entity_type_code, entity_id, contact_id,
                  contact_type_code, is_primary, created_at, updated_at
  customer_communication_thread: id, tenant_id, customer_id, tech_id,
                                  tenant_phone_number_id, status, first_message_at,
                                  last_message_at, message_count, created_at, updated_at
  customer_communication_message: id, thread_id, direction, channel, body,
                                   segment_count, status, sent_at, received_at,
                                   audit_user_id, created_at, updated_at

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

# Seed tenant phone number for this scenario
TENANT_PHONE_NUMBER = "+15125559001"
TENANT_AREA_CODE = "512"

# 3 customers with valid E.164 US mobile numbers — distinct from quote-to-cash (0001/0002)
COMMS_CUSTOMERS = [
    {
        "display_name": "Carlos Rivera",
        "first_name": "Carlos",
        "last_name": "Rivera",
        "type": "person",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "Linda Park",
        "first_name": "Linda",
        "last_name": "Park",
        "type": "person",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
    {
        "display_name": "Sunrise Electric LLC",
        "first_name": None,
        "last_name": None,
        "company_name": "Sunrise Electric LLC",
        "type": "company",
        "lifecycle": "active",
        "mobile_phone": "+14105550123",
        "email": "info@pilotfortrades.com",
    },
]

# Thread messages per customer: (direction, body, offset_minutes, is_unread_inbound)
# direction: 'inbound' or 'outbound'
# is_unread_inbound: True means received_at is set but no delivery confirmation (simulates unread)
THREAD_MESSAGES = [
    # Carlos Rivera — 4 messages
    [
        {
            "direction": "outbound",
            "body": "Hi Carlos, this is Pilot Electric. Your panel inspection is scheduled for tomorrow at 9am. Does that still work for you?",
            "offset_minutes": -120,
            "status": "delivered",
            "is_unread_inbound": False,
        },
        {
            "direction": "inbound",
            "body": "Yes, that works. See you then!",
            "offset_minutes": -100,
            "status": "received",
            "is_unread_inbound": False,
        },
        {
            "direction": "outbound",
            "body": "Great! Our tech will arrive between 9-10am. Reply STOP to opt out.",
            "offset_minutes": -98,
            "status": "delivered",
            "is_unread_inbound": False,
        },
        {
            "direction": "inbound",
            "body": "Actually, can you move it to 10am?",
            "offset_minutes": -30,
            "status": "received",
            "is_unread_inbound": True,  # ← unread — no sent_at on response yet
        },
    ],
    # Linda Park — 3 messages
    [
        {
            "direction": "outbound",
            "body": "Hi Linda! Your invoice #1042 for the outlet installation is ready. View and pay at: https://app.pilotfortrades.com/i/EXAMPLE_TOKEN_abc123. Reply STOP to opt out.",
            "offset_minutes": -240,
            "status": "delivered",
            "is_unread_inbound": False,
        },
        {
            "direction": "inbound",
            "body": "Paid! Thank you, great service.",
            "offset_minutes": -200,
            "status": "received",
            "is_unread_inbound": False,
        },
        {
            "direction": "inbound",
            "body": "Also — do you do HVAC work?",
            "offset_minutes": -15,
            "status": "received",
            "is_unread_inbound": True,  # ← unread
        },
    ],
    # Sunrise Electric LLC — 2 messages
    [
        {
            "direction": "outbound",
            "body": "Hi Sunrise Electric, this is Pilot Electric confirming your commercial panel inspection for Thursday 2pm at 789 Oak Blvd. Reply STOP to opt out.",
            "offset_minutes": -1440,  # yesterday
            "status": "delivered",
            "is_unread_inbound": False,
        },
        {
            "direction": "inbound",
            "body": "Confirmed. Please ask the tech to check in at the front desk.",
            "offset_minutes": -1380,
            "status": "received",
            "is_unread_inbound": False,
        },
    ],
]

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_customer_comms.py — Group D customer comms seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


def _get_tenant_id() -> UUID:
    return UUID(settings.TEST_TENANT_ID)


def mode_reset(tenant_id: UUID):
    """Wipe customer comms scenario data only (child-first ordering)."""
    tid = str(tenant_id)
    with get_db_session() as db:
        # Delete comms messages first (references threads)
        try:
            result = db.execute(
                text("""
                    DELETE FROM public.customer_communication_message
                    WHERE thread_id IN (
                        SELECT id FROM public.customer_communication_thread
                        WHERE tenant_id = :tid
                    )
                """),
                {"tid": tid},
            )
            if result.rowcount:
                print(
                    f"  🗑  [customer_communication_message] Deleted {result.rowcount} row(s)"
                )
        except Exception as e:
            print(f"  ⚠️  [customer_communication_message] {e}")

        # Delete threads
        try:
            result = db.execute(
                text(
                    "DELETE FROM public.customer_communication_thread WHERE tenant_id = :tid"
                ),
                {"tid": tid},
            )
            if result.rowcount:
                print(
                    f"  🗑  [customer_communication_thread] Deleted {result.rowcount} row(s)"
                )
        except Exception as e:
            print(f"  ⚠️  [customer_communication_thread] {e}")

        # Delete entity_contact for customers we own
        for cust in COMMS_CUSTOMERS:
            try:
                cust_row = db.execute(
                    text(
                        "SELECT id FROM public.customer WHERE tenant_id = :tid AND display_name = :name"
                    ),
                    {"tid": tid, "name": cust["display_name"]},
                ).first()
                if cust_row:
                    result = db.execute(
                        text(
                            "DELETE FROM public.entity_contact WHERE tenant_id = :tid AND entity_id = :eid"
                        ),
                        {"tid": tid, "eid": str(cust_row.id)},
                    )
                    if result.rowcount:
                        print(
                            f"  🗑  [entity_contact] Deleted {result.rowcount} row(s) for {cust['display_name']}"
                        )
            except Exception:
                pass

        # Delete contacts for our customers
        for cust in COMMS_CUSTOMERS:
            try:
                cust_row = db.execute(
                    text(
                        "SELECT id FROM public.customer WHERE tenant_id = :tid AND display_name = :name"
                    ),
                    {"tid": tid, "name": cust["display_name"]},
                ).first()
                if cust_row:
                    result = db.execute(
                        text(
                            "DELETE FROM public.contact WHERE tenant_id = :tid AND customer_id = :cid"
                        ),
                        {"tid": tid, "cid": str(cust_row.id)},
                    )
                    if result.rowcount:
                        print(
                            f"  🗑  [contact] Deleted {result.rowcount} row(s) for {cust['display_name']}"
                        )
            except Exception:
                pass

        # Delete customers
        for cust in COMMS_CUSTOMERS:
            try:
                result = db.execute(
                    text(
                        "DELETE FROM public.customer WHERE tenant_id = :tid AND display_name = :name"
                    ),
                    {"tid": tid, "name": cust["display_name"]},
                )
                if result.rowcount:
                    print(f"  🗑  [customer] Deleted '{cust['display_name']}'")
            except Exception:
                pass

        # Delete the seed tenant phone number
        try:
            result = db.execute(
                text(
                    "DELETE FROM public.tenant_phone_number WHERE tenant_id = :tid AND phone_number = :num"
                ),
                {"tid": tid, "num": TENANT_PHONE_NUMBER},
            )
            if result.rowcount:
                print(f"  🗑  [tenant_phone_number] Deleted {TENANT_PHONE_NUMBER}")
        except Exception as e:
            print(f"  ⚠️  [tenant_phone_number] {e}")

        db.commit()

    print("\n✅ Customer comms scenario data wiped.")
    print("   Run: python migrations/scripts/seed_scenario_customer_comms.py")
    print("   to re-seed.")


def mode_seed(tenant_id: UUID):
    """Seed customer comms scenario data."""
    print("=== seed_scenario_customer_comms: seed mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)
    now = datetime.now(UTC)

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

        # Look up customer lifecycle status IDs
        cust_lifecycle = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.customer_lifecycle_status WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }
        # Verify primary contact_type exists (code PK, no id column)
        contact_type_exists = db.execute(
            text(
                "SELECT 1 FROM public.contact_type WHERE code = 'primary' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()
        if not contact_type_exists:
            print("  ⚠️  [contact_type] 'primary' not found — run seed_core.py first")
            return

        # ── 0. Cleanup: remove any empty-phone_number orphan rows ─────────────
        # These accumulate when a seed run fails before the INSERT returns the
        # phone_number value. Safe to delete: only rows with phone_number = ''.
        orphan_result = db.execute(
            text(
                "DELETE FROM public.tenant_phone_number "
                "WHERE tenant_id = :tid AND phone_number = ''"
            ),
            {"tid": tid},
        )
        if orphan_result.rowcount:
            print(
                f"  🗑  [tenant_phone_number] Cleaned up {orphan_result.rowcount} empty-phone_number orphan row(s)"
            )

        # ── 1. Tenant Phone Number ────────────────────────────────────────────
        existing_phone = db.execute(
            text(
                "SELECT id FROM public.tenant_phone_number WHERE tenant_id = :tid AND phone_number = :num"
            ),
            {"tid": tid, "num": TENANT_PHONE_NUMBER},
        ).first()
        if existing_phone:
            tenant_phone_id = str(existing_phone.id)
            print(f"  ℹ️  [tenant_phone_number] {TENANT_PHONE_NUMBER} already exists")
        else:
            phone_result = db.execute(
                text("""
                    INSERT INTO public.tenant_phone_number
                    (id, tenant_id, phone_number, area_code, carrier, status)
                    VALUES (gen_random_uuid(), :tid, :num, :area, 'telnyx', 'provisioning_failed')
                    RETURNING id
                """),
                {"tid": tid, "num": TENANT_PHONE_NUMBER, "area": TENANT_AREA_CODE},
            )
            phone_row = phone_result.first()
            tenant_phone_id = str(phone_row.id)
            print(
                f"  ✅ [tenant_phone_number] Created {TENANT_PHONE_NUMBER} ({tenant_phone_id})"
            )

        # ── 2. Customers + Contacts + Entity Contacts ─────────────────────────
        customer_ids = []
        for cust_def in COMMS_CUSTOMERS:
            existing = db.execute(
                text(
                    "SELECT id FROM public.customer WHERE tenant_id = :tid AND display_name = :name"
                ),
                {"tid": tid, "name": cust_def["display_name"]},
            ).first()
            if existing:
                print(f"  ℹ️  [customer] '{cust_def['display_name']}' already exists")
                customer_ids.append(str(existing.id))
                continue

            lifecycle_id = cust_lifecycle.get(cust_def["lifecycle"])
            company_name = cust_def.get("company_name")
            cust_result = db.execute(
                text("""
                    INSERT INTO public.customer
                    (id, tenant_id, type, display_name, first_name, last_name, company_name,
                     email, mobile_phone, is_active, lifecycle_status_id,
                     preferred_contact_channel, sms_opted_out, sms_opt_in_consent,
                     created_at, updated_at)
                    VALUES
                    (gen_random_uuid(), :tid, :type, :display_name, :first_name, :last_name, :company_name,
                     :email, :mobile_phone, true, :lifecycle_id,
                     'sms', false, true,
                     NOW(), NOW())
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "type": cust_def["type"],
                    "display_name": cust_def["display_name"],
                    "first_name": cust_def.get("first_name"),
                    "last_name": cust_def.get("last_name"),
                    "company_name": company_name,
                    "email": cust_def.get("email"),
                    "mobile_phone": cust_def["mobile_phone"],
                    "lifecycle_id": lifecycle_id,
                },
            )
            cust_row = cust_result.first()
            cust_id = str(cust_row.id)
            customer_ids.append(cust_id)
            print(f"  ✅ [customer] Created '{cust_def['display_name']}' ({cust_id})")

            # Create contact with mobile_phone
            contact_result = db.execute(
                text("""
                    INSERT INTO public.contact
                    (id, tenant_id, customer_id, first_name, last_name, mobile_phone, is_active,
                     created_at, updated_at)
                    VALUES
                    (gen_random_uuid(), :tid, :cid, :first_name, :last_name, :mobile_phone, true,
                     NOW(), NOW())
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "first_name": cust_def.get("first_name"),
                    "last_name": cust_def.get("last_name"),
                    "mobile_phone": cust_def["mobile_phone"],
                },
            )
            contact_row = contact_result.first()
            contact_id = str(contact_row.id)
            print(
                f"  ✅ [contact] Created contact for '{cust_def['display_name']}' ({contact_id})"
            )

            # Create entity_contact linking customer → contact
            db.execute(
                text("""
                    INSERT INTO public.entity_contact
                    (id, tenant_id, entity_type_code, entity_id, contact_id, contact_type_code, is_primary,
                     created_at, updated_at)
                    VALUES
                    (gen_random_uuid(), :tid, 'customer', :entity_id, :contact_id, 'primary', true,
                     NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"tid": tid, "entity_id": cust_id, "contact_id": contact_id},
            )
            print(
                f"  ✅ [entity_contact] Linked contact to customer '{cust_def['display_name']}'"
            )

        # ── 3. Communication Threads + Messages ───────────────────────────────
        for idx, (cust_def, messages) in enumerate(
            zip(COMMS_CUSTOMERS, THREAD_MESSAGES)
        ):
            if idx >= len(customer_ids):
                continue
            cust_id = customer_ids[idx]
            if not cust_id:
                continue

            # Check for existing thread
            existing_thread = db.execute(
                text("""
                    SELECT id FROM public.customer_communication_thread
                    WHERE tenant_id = :tid AND customer_id = :cid LIMIT 1
                """),
                {"tid": tid, "cid": cust_id},
            ).first()
            if existing_thread:
                print(
                    f"  ℹ️  [customer_communication_thread] Thread for '{cust_def['display_name']}' already exists"
                )
                continue

            # Compute timestamps
            first_offset = min(m["offset_minutes"] for m in messages)
            last_offset = max(m["offset_minutes"] for m in messages)
            first_msg_at = now + timedelta(minutes=first_offset)
            last_msg_at = now + timedelta(minutes=last_offset)

            thread_result = db.execute(
                text("""
                    INSERT INTO public.customer_communication_thread
                    (id, tenant_id, customer_id, tech_id, tenant_phone_number_id,
                     status, first_message_at, last_message_at, message_count)
                    VALUES
                    (gen_random_uuid(), :tid, :cid, :tech_id, :phone_id,
                     'active', :first_at, :last_at, :msg_count)
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "cid": cust_id,
                    "tech_id": str(TECH_USER_ID),
                    "phone_id": tenant_phone_id,
                    "first_at": first_msg_at,
                    "last_at": last_msg_at,
                    "msg_count": len(messages),
                },
            )
            thread_row = thread_result.first()
            thread_id = str(thread_row.id)
            print(
                f"  ✅ [customer_communication_thread] Created thread for '{cust_def['display_name']}' ({thread_id})"
            )

            # Create messages
            for msg in messages:
                msg_at = now + timedelta(minutes=msg["offset_minutes"])
                # For inbound: received_at = msg_at; sent_at = NULL
                # For outbound: sent_at = msg_at; received_at = NULL
                is_inbound = msg["direction"] == "inbound"
                sent_at = None if is_inbound else msg_at
                received_at = msg_at if is_inbound else None
                # "unread" inbound = received_at is NULL (not yet confirmed received)
                if is_inbound and msg.get("is_unread_inbound"):
                    received_at = None  # simulates pending/unread state

                db.execute(
                    text("""
                        INSERT INTO public.customer_communication_message
                        (id, thread_id, direction, channel, body, segment_count, status,
                         sent_at, received_at, audit_user_id)
                        VALUES
                        (gen_random_uuid(), :thread_id, :direction, 'sms', :body, 1, :status,
                         :sent_at, :received_at, :audit_user_id)
                    """),
                    {
                        "thread_id": thread_id,
                        "direction": msg["direction"],
                        "body": msg["body"],
                        "status": msg["status"],
                        "sent_at": sent_at,
                        "received_at": received_at,
                        "audit_user_id": str(OWNER_USER_ID),
                    },
                )
                unread_flag = " [UNREAD]" if msg.get("is_unread_inbound") else ""
                print(
                    f"  ✅ [customer_communication_message] {msg['direction'].upper()}{unread_flag}: "
                    f"'{msg['body'][:50]}...'"
                )

        # SD-5: D10 — Close Sunrise Electric LLC thread
        db.execute(
            text("""
                UPDATE public.customer_communication_thread
                SET status = 'archived', updated_at = NOW()
                WHERE tenant_id = :tid
                AND customer_id = (
                    SELECT id FROM public.customer
                    WHERE tenant_id = :tid AND display_name = 'Sunrise Electric LLC'
                    LIMIT 1
                )
                AND status != 'archived'
            """),
            {"tid": tid},
        )
        print(
            "  ✅ [customer_communication_thread] Sunrise Electric LLC thread → status=archived"
        )

        # ── SD-7 Batch 3: contact_endpoint rows ──────────────────────────────────
        # ⚠️  SKIPPED: contact_endpoint_channel_chk constraint only allows 'email' | 'sms'.
        # 'phone' is not a valid channel value in the current schema.
        # 'sms' is on hold (§8.2) until Telnyx 10DLC campaign approved.
        # Therefore: no contact_endpoint rows can be seeded in this batch.
        print("\n  -- SD-7 B3: contact_endpoint --")
        print(
            "  ℹ️  [contact_endpoint] SKIPPED — constraint allows only 'email'|'sms'; "
            "'sms' is on hold (§8.2); 'phone' is not a valid channel."
        )

        # ── SD-7 Batch 3: customer_communication_message_read_state for already-read msgs ──
        print("\n  -- SD-7 B3: customer_communication_message_read_state --")
        # Read messages = outbound (always "read" by the tech) + inbound where is_unread_inbound=False
        # We mark the OWNER user as having read all non-unread messages
        read_state_messages = db.execute(
            text("""
                SELECT m.id AS message_id
                FROM public.customer_communication_message m
                JOIN public.customer_communication_thread t ON t.id = m.thread_id
                WHERE t.tenant_id = :tid
                  AND (
                      m.direction = 'outbound'
                      OR (m.direction = 'inbound' AND m.received_at IS NOT NULL)
                  )
            """),
            {"tid": tid},
        ).fetchall()

        for msg_row in read_state_messages:
            msg_id = str(msg_row.message_id)
            existing_rs = db.execute(
                text("""
                    SELECT 1 FROM public.customer_communication_message_read_state
                    WHERE message_id = :mid AND user_id = :uid
                    LIMIT 1
                """),
                {"mid": msg_id, "uid": str(OWNER_USER_ID)},
            ).first()
            if existing_rs:
                continue
            db.execute(
                text("""
                    INSERT INTO public.customer_communication_message_read_state
                    (message_id, user_id, read_at, created_at)
                    VALUES (:mid, :uid, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"mid": msg_id, "uid": str(OWNER_USER_ID)},
            )
        read_count = len(read_state_messages)
        print(
            f"  ✅ [customer_communication_message_read_state] {read_count} read_state rows inserted for owner user"
        )

        # ── SD-7 Batch 3: customer_communication_unrouted (1 parked row) ─────────
        print("\n  -- SD-7 B3: customer_communication_unrouted (parked) --")
        existing_unrouted = db.execute(
            text("""
                SELECT id FROM public.customer_communication_unrouted
                WHERE tenant_id = :tid AND status = 'parked'
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if existing_unrouted:
            print("  ℹ️  [customer_communication_unrouted] Parked row already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.customer_communication_unrouted
                    (id, tenant_id, from_number, to_number, body,
                     received_at, parked_at, status,
                     created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :from_num, :to_num, :body,
                            NOW() - INTERVAL '5 minutes', NOW() - INTERVAL '5 minutes',
                            'parked', NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "from_num": "+14085559123",
                    "to_num": TENANT_PHONE_NUMBER,
                    "body": "Hello, is this the electrician?",
                },
            )
            print(
                f"  ✅ [customer_communication_unrouted] parked: from=+14085559123 to={TENANT_PHONE_NUMBER}  body='Hello, is this the electrician?'"
            )

        db.commit()

    print(
        f"\n🎉 seed_scenario_customer_comms complete — Group D comms data present for {tenant_id}"
    )


def mode_inspect(tenant_id: UUID):
    """Show current state of customer comms scenario data."""
    print("=== seed_scenario_customer_comms: inspect mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        # Tenant phone number
        phones = db.execute(
            text("""
                SELECT id, phone_number, area_code, status
                FROM public.tenant_phone_number
                WHERE tenant_id = :tid
                ORDER BY phone_number
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [tenant_phone_number]  {len(phones)} row(s)")
        for p in phones:
            print(f"    • {p.phone_number}  area={p.area_code}  status={p.status}")
        print()

        # Customers in this scenario
        comms_names = [c["display_name"] for c in COMMS_CUSTOMERS]
        custs = db.execute(
            text("""
                SELECT c.id, c.display_name, c.mobile_phone, cls.code AS lifecycle
                FROM public.customer c
                LEFT JOIN public.customer_lifecycle_status cls ON cls.id = c.lifecycle_status_id
                WHERE c.tenant_id = :tid AND c.display_name = ANY(:names)
                ORDER BY c.display_name
            """),
            {"tid": tid, "names": comms_names},
        ).fetchall()
        print(f"  [customer (comms scenario)]  {len(custs)} row(s)")
        for c in custs:
            print(
                f"    • {c.id}  '{c.display_name}'  phone={c.mobile_phone}  lifecycle={c.lifecycle}"
            )
        print()

        # Threads
        threads = db.execute(
            text("""
                SELECT t.id, c.display_name, t.status, t.message_count,
                       t.first_message_at, t.last_message_at
                FROM public.customer_communication_thread t
                JOIN public.customer c ON c.id = t.customer_id
                WHERE t.tenant_id = :tid
                ORDER BY t.last_message_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [customer_communication_thread]  {len(threads)} row(s)")
        for t in threads:
            print(
                f"    • {t.id}  customer='{t.display_name}'  "
                f"status={t.status}  msg_count={t.message_count}"
            )
            print(f"          first={t.first_message_at}  last={t.last_message_at}")
        print()

        # Messages
        messages = db.execute(
            text("""
                SELECT m.id, m.thread_id, m.direction, m.status,
                       m.sent_at, m.received_at,
                       LEFT(m.body, 60) AS body_preview
                FROM public.customer_communication_message m
                JOIN public.customer_communication_thread t ON t.id = m.thread_id
                WHERE t.tenant_id = :tid
                ORDER BY t.id, m.sent_at NULLS LAST, m.received_at NULLS LAST
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [customer_communication_message]  {len(messages)} row(s)")
        unread_count = 0
        for m in messages:
            unread = (
                "(UNREAD)" if m.direction == "inbound" and not m.received_at else ""
            )
            if unread:
                unread_count += 1
            print(
                f"    • {m.direction.upper():<9} {m.status:<12} {unread}  '{m.body_preview}'"
            )
        print(f"\n    Unread messages: {unread_count}")
        print()

        # SD-7 Batch 3: contact_endpoint
        ep_rows = db.execute(
            text("""
                SELECT ce.id, ce.contact_id, ce.channel, ce.value,
                       ce.verification_status, ce.consent_status, ce.is_active
                FROM public.contact_endpoint ce
                WHERE ce.tenant_id = :tid
                ORDER BY ce.channel, ce.value
            """),
            {"tid": tid},
        ).fetchall()
        # contact_endpoint: channel chk allows only email|sms; phone invalid; sms on hold (§8.2)
        print(
            f"  [contact_endpoint]  {len(ep_rows)} row(s)  (SKIPPED in seed — channel chk: email|sms only; sms on hold §8.2)"
        )
        print()

        # SD-7 Batch 3: customer_communication_message_read_state
        rs_count = db.execute(
            text("""
                SELECT COUNT(*) FROM public.customer_communication_message_read_state rs
                WHERE rs.message_id IN (
                    SELECT m.id FROM public.customer_communication_message m
                    JOIN public.customer_communication_thread t ON t.id = m.thread_id
                    WHERE t.tenant_id = :tid
                )
            """),
            {"tid": tid},
        ).scalar()
        print(f"  [customer_communication_message_read_state]  {rs_count} row(s)")
        print()

        # SD-7 Batch 3: customer_communication_unrouted
        unrouted_rows = db.execute(
            text("""
                SELECT id, from_number, to_number, status, received_at, parked_at,
                       LEFT(body, 60) AS body_preview
                FROM public.customer_communication_unrouted
                WHERE tenant_id = :tid
                ORDER BY received_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [customer_communication_unrouted]  {len(unrouted_rows)} row(s)")
        for ur in unrouted_rows:
            print(
                f"    • id={ur.id}  from={ur.from_number}  to={ur.to_number}"
                f"  status={ur.status}  received={ur.received_at}"
                f"  body='{ur.body_preview}'"
            )


def mode_show():
    """Print what would be seeded without touching the DB."""
    print("=== seed_scenario_customer_comms: show mode ===\n")
    print(f"Tenant phone number: {TENANT_PHONE_NUMBER}  area={TENANT_AREA_CODE}\n")
    print(f"Technician UUID: {TECH_USER_ID}\n")
    print(f"Customers ({len(COMMS_CUSTOMERS)}):")
    for c in COMMS_CUSTOMERS:
        print(f"  • {c['display_name']}  type={c['type']}  phone={c['mobile_phone']}")
    print("\nCommunication threads (1 per customer):")
    for cust, msgs in zip(COMMS_CUSTOMERS, THREAD_MESSAGES):
        unread = sum(1 for m in msgs if m.get("is_unread_inbound"))
        inbound = sum(1 for m in msgs if m["direction"] == "inbound")
        outbound = sum(1 for m in msgs if m["direction"] == "outbound")
        print(
            f"  • {cust['display_name']}: {len(msgs)} messages  "
            f"({inbound} inbound, {outbound} outbound, {unread} unread)"
        )


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_customer_comms.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(args, "reset", False):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_customer_comms.py")
    tenant_id = _get_tenant_id()

    if args.reset:
        mode_reset(tenant_id)
    elif args.mode == "seed":
        mode_seed(tenant_id)
    elif args.mode == "inspect":
        mode_inspect(tenant_id)
    elif args.mode == "show":
        mode_show()
