"""
seed_scenario_mobile_sync.py — Group D: Mobile Sync scenario data.

Purpose: Seeds mobile_sync_session + mobile_sync_event rows for the test tenant
to support E2E tests in cp9_mobile_sync (W-11).

NEVER run in production.

Schema verified via MCP 2026-07-12:
  mobile_sync_session: id, tenant_id, user_id, device_id, triggered_by,
                       started_at, completed_at, outcome, items_attempted,
                       items_committed, items_deferred, items_failed,
                       failure_reason, created_at
  mobile_sync_event: id, tenant_id, user_id, device_id, operation_type,
                     operation_payload_summary, status, conflict_severity,
                     client_capture_at, synced_at, error_detail,
                     idempotency_uuid, created_at, created_by, resolution_action

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

TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
TECH_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

# Synthetic device IDs — stable UUIDs for idempotency
SEED_DEVICE_ID = UUID("00000000-0000-0000-0001-000000000001")
# SD-5: Second device for partial failure session
SEED_DEVICE_ID_2 = UUID("00000000-0000-0000-0002-000000000001")

ANCHOR = datetime(2026, 7, 1, tzinfo=UTC)

# SD-6: The open escalation is linked to the conflict event for Session 2 (device ...0002).
# That event has deterministic idempotency_uuid = 00000000-0002-0002-0002-000000000001.
# Do NOT hardcode the event's row UUID — it changes on every reset+reseed (gen_random_uuid()).
# _seed_owner_escalations() looks up the conflict_id at runtime using this idempotency_uuid.
CONFLICT_EVENT_IDEM_UUID = UUID("00000000-0002-0002-0002-000000000001")
# SD-6: idempotency UUID for resolved escalation's fabricated sync event
RESOLVED_CONFLICT_IDEM_UUID = UUID("00000000-0002-0002-0002-000000000099")

# Session anchor times: started 2 hours ago, completed 1h59m ago
SESSION_STARTED_AT = ANCHOR - timedelta(hours=2)
SESSION_COMPLETED_AT = ANCHOR - timedelta(hours=1, minutes=59)


def seed(db_url: str | None = None) -> None:
    """Idempotent seed — insert mobile sync session + event rows for test tenant."""
    print("=== seed_scenario_mobile_sync: seed mode ===")
    print(f"    Tenant ID: {TEST_TENANT_ID}\n")

    tid = str(TEST_TENANT_ID)
    uid = str(TECH_USER_ID)
    device_id = str(SEED_DEVICE_ID)

    with get_db_session() as db:
        # ── Session ────────────────────────────────────────────────────────────
        existing_session = db.execute(
            text("""
                SELECT id FROM public.mobile_sync_session
                WHERE tenant_id = :tid
                AND device_id = :device_id
                AND triggered_by = 'silent_push'
                AND outcome = 'success'
                LIMIT 1
            """),
            {"tid": tid, "device_id": device_id},
        ).first()

        if existing_session:
            print(
                "  ℹ️  [mobile_sync_session] Silent push success session already exists"
            )
            session_id = str(existing_session.id)
        else:
            session_result = db.execute(
                text("""
                    INSERT INTO public.mobile_sync_session
                    (id, tenant_id, user_id, device_id, triggered_by,
                     outcome, items_attempted, items_committed,
                     items_deferred, items_failed,
                     started_at, completed_at, created_at)
                    VALUES
                    (gen_random_uuid(), :tid, :uid, :device_id, 'silent_push',
                     'success', 3, 3,
                     0, 0,
                     :started_at, :completed_at, NOW())
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "uid": uid,
                    "device_id": device_id,
                    "started_at": SESSION_STARTED_AT,
                    "completed_at": SESSION_COMPLETED_AT,
                },
            )
            session_id = str(session_result.first().id)
            print(
                f"  ✅ [mobile_sync_session] Created silent_push success session ({session_id})"
            )

        # ── Events ─────────────────────────────────────────────────────────────
        events = [
            {
                "operation_type": "create_time_entry",
                "status": "succeeded",
                "idempotency_uuid": str(UUID("00000000-0001-0001-0001-000000000001")),
            },
            {
                "operation_type": "create_expense",
                "status": "succeeded",
                "idempotency_uuid": str(UUID("00000000-0001-0001-0001-000000000002")),
            },
        ]

        for ev in events:
            existing_ev = db.execute(
                text("""
                    SELECT id FROM public.mobile_sync_event
                    WHERE tenant_id = :tid
                    AND idempotency_uuid = :idem_uuid
                    LIMIT 1
                """),
                {"tid": tid, "idem_uuid": ev["idempotency_uuid"]},
            ).first()

            if existing_ev:
                print(f"  ℹ️  [mobile_sync_event] {ev['operation_type']} already exists")
                continue

            db.execute(
                text("""
                    INSERT INTO public.mobile_sync_event
                    (id, tenant_id, user_id, device_id, operation_type,
                     status, idempotency_uuid, client_capture_at, created_at)
                    VALUES
                    (gen_random_uuid(), :tid, :uid, :device_id, :operation_type,
                     :status, CAST(:idem_uuid AS uuid), :client_capture_at, NOW())
                """),
                {
                    "tid": tid,
                    "uid": uid,
                    "device_id": device_id,
                    "operation_type": ev["operation_type"],
                    "status": ev["status"],
                    "idem_uuid": ev["idempotency_uuid"],
                    "client_capture_at": SESSION_COMPLETED_AT,
                },
            )
            print(f"  ✅ [mobile_sync_event] Created {ev['operation_type']} event")

        # ── Session 2: Partial failure (SD-5) ─────────────────────────────────
        sess2_started = ANCHOR - timedelta(hours=5)
        sess2_completed = ANCHOR - timedelta(hours=4, minutes=55)

        existing_session2 = db.execute(
            text("""
                SELECT id FROM public.mobile_sync_session
                WHERE tenant_id = :tid
                AND device_id = :device_id
                AND triggered_by = 'foreground'
                AND outcome = 'partial'
                LIMIT 1
            """),
            {"tid": tid, "device_id": str(SEED_DEVICE_ID_2)},
        ).first()

        if existing_session2:
            print(
                "  ℹ️  [mobile_sync_session] Foreground partial session already exists"
            )
            session2_id = str(existing_session2.id)
        else:
            session2_result = db.execute(
                text("""
                    INSERT INTO public.mobile_sync_session
                    (id, tenant_id, user_id, device_id, triggered_by,
                     outcome, items_attempted, items_committed,
                     items_deferred, items_failed,
                     started_at, completed_at, created_at)
                    VALUES
                    (gen_random_uuid(), :tid, :uid, :device_id, 'foreground',
                     'partial', 4, 2,
                     0, 2,
                     :started_at, :completed_at, NOW())
                    RETURNING id
                """),
                {
                    "tid": tid,
                    "uid": uid,
                    "device_id": str(SEED_DEVICE_ID_2),
                    "started_at": sess2_started,
                    "completed_at": sess2_completed,
                },
            )
            session2_id = str(session2_result.first().id)
            print(
                f"  ✅ [mobile_sync_session] Created foreground partial session ({session2_id})"
            )

        # Session 2 events: 2 succeeded + 1 conflict + 1 failed
        events2 = [
            {
                "operation_type": "update_job_status",
                "status": "conflict",
                "idempotency_uuid": str(UUID("00000000-0002-0002-0002-000000000001")),
                "conflict_severity": "owner_escalation",
                "error_detail": "Concurrent edit detected on job status",
            },
            {
                "operation_type": "upload_photo",
                "status": "failed",
                "idempotency_uuid": str(UUID("00000000-0002-0002-0002-000000000002")),
                "conflict_severity": None,
                "error_detail": "Network timeout uploading attachment",
            },
        ]

        for ev in events2:
            existing_ev2 = db.execute(
                text("""
                    SELECT id FROM public.mobile_sync_event
                    WHERE tenant_id = :tid
                    AND idempotency_uuid = :idem_uuid
                    LIMIT 1
                """),
                {"tid": tid, "idem_uuid": ev["idempotency_uuid"]},
            ).first()

            if existing_ev2:
                print(
                    f"  ℹ️  [mobile_sync_event] {ev['operation_type']} (session 2) already exists"
                )
                continue

            db.execute(
                text("""
                    INSERT INTO public.mobile_sync_event
                    (id, tenant_id, user_id, device_id, operation_type,
                     status, conflict_severity, idempotency_uuid,
                     client_capture_at, error_detail, created_at)
                    VALUES
                    (gen_random_uuid(), :tid, :uid, :device_id, :operation_type,
                     :status, :conflict_severity, CAST(:idem_uuid AS uuid),
                     :client_capture_at, CAST(:error_detail AS jsonb), NOW())
                """),
                {
                    "tid": tid,
                    "uid": uid,
                    "device_id": str(SEED_DEVICE_ID_2),
                    "operation_type": ev["operation_type"],
                    "status": ev["status"],
                    "conflict_severity": ev["conflict_severity"],
                    "idem_uuid": ev["idempotency_uuid"],
                    "client_capture_at": sess2_completed,
                    "error_detail": f'{{"message": "{ev["error_detail"]}"}}'
                    if ev["error_detail"]
                    else None,
                },
            )
            print(
                f"  ✅ [mobile_sync_event] Created {ev['operation_type']} event (status={ev['status']})"
            )

        # SD-6: Seed owner escalations
        _seed_owner_escalations(db, tid)

        # SD-7 Batch 2: mobile_sync_event_audit + mobile_push_permission_state
        _seed_sd7_batch2_mobile(db, tid)

        db.commit()

    print(
        f"\n🎉 seed_scenario_mobile_sync complete — data present for {TEST_TENANT_ID}"
    )


def _seed_sd7_batch2_mobile(db, tid: str) -> None:
    """Seed SD-7 Batch 2 mobile tables: event_audit, push_permission_state, resolution_payload."""
    print(
        "\n  -- SD-7 Batch 2: mobile_sync_event_audit + mobile_push_permission_state --"
    )

    # ── mobile_sync_event_audit: 1 row for the resolved escalation ────────────
    # Schema (MCP verified): id (uuid), tenant_id, escalation_id, originator_user_id,
    #   resolver_user_id, resolution_action (text, NOT NULL), resolution_channel (text, default 'web'),
    #   tech_local_snapshot_at_commit (jsonb), server_state_snapshot_at_commit (jsonb),
    #   post_commit_state (jsonb), resolved_at (timestamptz, NOT NULL), created_at, created_by

    # Look up the resolved escalation by conflict event idempotency_uuid
    resolved_esc_row = db.execute(
        text("""
            SELECT e.id AS esc_id
            FROM public.mobile_sync_owner_escalation e
            JOIN public.mobile_sync_event ev ON ev.id = e.conflict_id
            WHERE e.tenant_id = :tid
              AND e.status = 'resolved'
              AND ev.idempotency_uuid = :idem_uuid
            LIMIT 1
        """),
        {"tid": tid, "idem_uuid": str(RESOLVED_CONFLICT_IDEM_UUID)},
    ).first()

    if not resolved_esc_row:
        print(
            "  ⚠️  [mobile_sync_event_audit] Resolved escalation not found — run seed first"
        )
    else:
        esc_id = str(resolved_esc_row.esc_id)
        existing_audit = db.execute(
            text("""
                SELECT id FROM public.mobile_sync_event_audit
                WHERE tenant_id = :tid AND escalation_id = :esc_id
                LIMIT 1
            """),
            {"tid": tid, "esc_id": esc_id},
        ).first()

        if existing_audit:
            print(
                "  ℹ️  [mobile_sync_event_audit] Already exists for resolved escalation"
            )
        else:
            import json as _json

            resolved_at = ANCHOR - timedelta(days=9)
            db.execute(
                text("""
                    INSERT INTO public.mobile_sync_event_audit
                    (id, tenant_id, escalation_id, originator_user_id, resolver_user_id,
                     resolution_action, resolution_channel,
                     tech_local_snapshot_at_commit, server_state_snapshot_at_commit,
                     post_commit_state, resolved_at, created_at, created_by)
                    VALUES (
                        gen_random_uuid(), :tid, :esc_id, :tech_id, :owner_id,
                        'use_tech', 'web',
                        CAST(:tech_snapshot AS jsonb),
                        CAST(:server_snapshot AS jsonb),
                        CAST(:post_commit AS jsonb),
                        :resolved_at, :resolved_at, NULL
                    )
                """),
                {
                    "tid": tid,
                    "esc_id": esc_id,
                    "tech_id": str(TECH_USER_ID),
                    "owner_id": str(OWNER_USER_ID),
                    "tech_snapshot": _json.dumps(
                        {
                            "expense_category": "materials",
                            "cost_cents": 32500,
                            "description": "Wire nuts batch",
                        }
                    ),
                    "server_snapshot": _json.dumps(
                        {
                            "expense_category": "equipment",
                            "cost_cents": 32500,
                            "description": "Wire nuts batch",
                        }
                    ),
                    "post_commit": _json.dumps(
                        {
                            "expense_category": "materials",
                            "cost_cents": 32500,
                            "resolution": "use_tech",
                        }
                    ),
                    "resolved_at": resolved_at,
                },
            )
            print(
                f"  ✅ [mobile_sync_event_audit] Created for resolved escalation ({esc_id})"
            )

        # ── UPDATE resolution_payload on the resolved escalation (4N gap) ────────
        db.execute(
            text("""
                UPDATE public.mobile_sync_owner_escalation
                SET resolution_payload = CAST(:payload AS jsonb),
                    updated_at = NOW()
                WHERE id = :esc_id AND tenant_id = :tid
                  AND resolution_payload IS NULL
            """),
            {
                "esc_id": esc_id,
                "tid": tid,
                "payload": json.dumps(
                    {
                        "server_value": {"expense_category": "equipment"},
                        "device_value": {"expense_category": "materials"},
                        "resolution": "use_tech",
                    }
                ),
            },
        )
        print(
            "  ✅ [mobile_sync_owner_escalation] resolution_payload updated on resolved row"
        )

    # ── mobile_push_permission_state: tech user, permission_state='granted' ────
    # Schema (MCP verified): tenant_id, user_id, device_id (composite PK),
    #   permission_state (text, default 'not_asked'), last_state_change_at (timestamptz, NOT NULL),
    #   dismissable_banner_dismissed_at (timestamptz, nullable),
    #   created_at, updated_at, created_by, updated_by
    existing_perm = db.execute(
        text("""
            SELECT tenant_id FROM public.mobile_push_permission_state
            WHERE tenant_id = :tid AND user_id = :uid AND device_id = :device_id
            LIMIT 1
        """),
        {"tid": tid, "uid": str(TECH_USER_ID), "device_id": str(SEED_DEVICE_ID)},
    ).first()

    if existing_perm:
        print("  ℹ️  [mobile_push_permission_state] Already exists for tech user")
    else:
        db.execute(
            text("""
                INSERT INTO public.mobile_push_permission_state
                (tenant_id, user_id, device_id, permission_state, last_state_change_at,
                 created_at, updated_at, created_by, updated_by)
                VALUES (
                    :tid, :uid, :device_id, 'granted', NOW() - INTERVAL '7 days',
                    NOW(), NOW(), NULL, NULL
                )
                ON CONFLICT DO NOTHING
            """),
            {"tid": tid, "uid": str(TECH_USER_ID), "device_id": str(SEED_DEVICE_ID)},
        )
        print(
            f"  ✅ [mobile_push_permission_state] tech@pilot.local  permission_state=granted  device={SEED_DEVICE_ID}"
        )


def _seed_owner_escalations(db, tid: str) -> None:
    """Seed mobile_sync_owner_escalation rows (SD-6 Task 2)."""
    print("\n  -- Seeding mobile_sync_owner_escalation rows (SD-6) --")

    # ── Look up the conflict event by its deterministic idempotency_uuid ─────────
    # CONFLICT_EVENT_ID was a stale hardcoded UUID — the row UUID changes on every
    # reset+reseed. Use the stable idempotency_uuid to find the live row ID instead.
    conflict_ev_row = db.execute(
        text("""
            SELECT id FROM public.mobile_sync_event
            WHERE tenant_id = :tid AND idempotency_uuid = :idem_uuid
            LIMIT 1
        """),
        {"tid": tid, "idem_uuid": str(CONFLICT_EVENT_IDEM_UUID)},
    ).first()
    if not conflict_ev_row:
        print(
            "  ⚠️  [mobile_sync_owner_escalation] Conflict event not found by idempotency_uuid "
            f"({CONFLICT_EVENT_IDEM_UUID}) — run seed_scenario_mobile_sync.py to seed Session 2 events first"
        )
        return
    conflict_event_id = str(conflict_ev_row.id)

    # ── Row 1: Open escalation (linked to existing conflict event) ─────────────
    existing_open = db.execute(
        text("""
            SELECT id FROM public.mobile_sync_owner_escalation
            WHERE tenant_id = :tid AND conflict_id = :conflict_id
            LIMIT 1
        """),
        {"tid": tid, "conflict_id": conflict_event_id},
    ).first()

    if existing_open:
        print("  ℹ️  [mobile_sync_owner_escalation] Open escalation already exists")
    else:
        db.execute(
            text("""
                INSERT INTO public.mobile_sync_owner_escalation
                (id, tenant_id, originating_user_id, conflict_id,
                 escalated_at, escalation_reason, escalation_reason_explainer,
                 status, resolved_by_user_id, resolved_at, resolution_action, resolution_payload,
                 created_at, updated_at, created_by, updated_by)
                VALUES (
                    gen_random_uuid(), :tid, :tech_id, :conflict_id,
                    :escalated_at,
                    'tech_chose',
                    'Technician attempted to mark job in_progress while owner had already changed status to scheduled. Requires owner review before proceeding.',
                    'pending', NULL, NULL, NULL, NULL,
                    :escalated_at, :escalated_at, NULL, NULL
                )
            """),
            {
                "tid": tid,
                "tech_id": str(TECH_USER_ID),
                "conflict_id": conflict_event_id,
                "escalated_at": ANCHOR,
            },
        )
        print(
            "  ✅ [mobile_sync_owner_escalation] Open escalation created (status=pending)"
        )

    # ── Row 2: Resolved escalation (fabricate new sync event first) ───────────
    resolved_conflict_at = ANCHOR - timedelta(days=10)

    # Ensure the fabricated sync event exists
    existing_ev = db.execute(
        text("""
            SELECT id FROM public.mobile_sync_event
            WHERE tenant_id = :tid AND idempotency_uuid = :idem_uuid
            LIMIT 1
        """),
        {"tid": tid, "idem_uuid": str(RESOLVED_CONFLICT_IDEM_UUID)},
    ).first()

    if existing_ev:
        resolved_event_id = str(existing_ev.id)
        print("  ℹ️  [mobile_sync_event] Resolved conflict event already exists")
    else:
        ev_result = db.execute(
            text("""
                INSERT INTO public.mobile_sync_event
                (id, tenant_id, user_id, device_id, operation_type,
                 status, conflict_severity, idempotency_uuid,
                 client_capture_at, created_at)
                VALUES (
                    gen_random_uuid(), :tid, :uid, :device_id, 'update_expense',
                    'conflict', 'owner_escalation', CAST(:idem_uuid AS uuid),
                    :client_capture_at, :created_at
                )
                RETURNING id
            """),
            {
                "tid": tid,
                "uid": str(TECH_USER_ID),
                "device_id": str(SEED_DEVICE_ID_2),
                "idem_uuid": str(RESOLVED_CONFLICT_IDEM_UUID),
                "client_capture_at": resolved_conflict_at,
                "created_at": resolved_conflict_at,
            },
        )
        resolved_event_id = str(ev_result.first().id)
        print(
            f"  ✅ [mobile_sync_event] Fabricated resolved conflict event ({resolved_event_id})"
        )

    # Now check if the resolved escalation exists
    existing_resolved = db.execute(
        text("""
            SELECT id FROM public.mobile_sync_owner_escalation
            WHERE tenant_id = :tid AND conflict_id = :conflict_id
            LIMIT 1
        """),
        {"tid": tid, "conflict_id": resolved_event_id},
    ).first()

    if existing_resolved:
        print("  ℹ️  [mobile_sync_owner_escalation] Resolved escalation already exists")
    else:
        resolution_payload = json.dumps(
            {
                "accepted_value": "materials",
                "note": "Technician expense confirmed correct",
            }
        )
        db.execute(
            text("""
                INSERT INTO public.mobile_sync_owner_escalation
                (id, tenant_id, originating_user_id, conflict_id,
                 escalated_at, escalation_reason, escalation_reason_explainer,
                 status, resolved_by_user_id, resolved_at, resolution_action,
                 resolution_payload,
                 created_at, updated_at, created_by, updated_by)
                VALUES (
                    gen_random_uuid(), :tid, :tech_id, :conflict_id,
                    :escalated_at,
                    'tech_chose',
                    'Technician submitted an expense update that conflicted with a recently approved purchase order. Owner reviewed and accepted the technician change.',
                    'resolved', :owner_id, :resolved_at, 'use_tech',
                    CAST(:resolution_payload AS jsonb),
                    :escalated_at, :resolved_at, NULL, NULL
                )
            """),
            {
                "tid": tid,
                "tech_id": str(TECH_USER_ID),
                "conflict_id": resolved_event_id,
                "escalated_at": resolved_conflict_at,
                "owner_id": str(OWNER_USER_ID),
                "resolved_at": ANCHOR - timedelta(days=9),
                "resolution_payload": resolution_payload,
            },
        )
        print(
            "  ✅ [mobile_sync_owner_escalation] Resolved escalation created (status=resolved)"
        )


def mode_reset(db_url: str | None = None) -> None:
    """Wipe mobile sync scenario data for test tenant."""
    print("=== seed_scenario_mobile_sync: reset mode ===")
    tid = str(TEST_TENANT_ID)
    device_id = str(SEED_DEVICE_ID)

    with get_db_session() as db:
        # SD-7 Batch 2: Delete event_audit and push_permission_state first (child-first)
        result_audit = db.execute(
            text("DELETE FROM public.mobile_sync_event_audit WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        if result_audit.rowcount:
            print(
                f"  🗑  [mobile_sync_event_audit] Deleted {result_audit.rowcount} row(s)"
            )

        result_pps = db.execute(
            text(
                "DELETE FROM public.mobile_push_permission_state WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        )
        if result_pps.rowcount:
            print(
                f"  🗑  [mobile_push_permission_state] Deleted {result_pps.rowcount} row(s)"
            )

        # SD-6: Delete owner escalations
        result_esc = db.execute(
            text(
                "DELETE FROM public.mobile_sync_owner_escalation WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        )
        if result_esc.rowcount:
            print(
                f"  🗑  [mobile_sync_owner_escalation] Deleted {result_esc.rowcount} row(s)"
            )

        # SD-6: Also delete the fabricated resolved conflict event
        result_fab_ev = db.execute(
            text("""
                DELETE FROM public.mobile_sync_event
                WHERE tenant_id = :tid
                  AND idempotency_uuid = :idem_uuid
            """),
            {"tid": tid, "idem_uuid": str(RESOLVED_CONFLICT_IDEM_UUID)},
        )
        if result_fab_ev.rowcount:
            print("  🗑  [mobile_sync_event] Deleted fabricated resolved conflict event")

        result_ev = db.execute(
            text("""
                DELETE FROM public.mobile_sync_event
                WHERE tenant_id = :tid AND device_id = :device_id
            """),
            {"tid": tid, "device_id": device_id},
        )
        result_sess = db.execute(
            text("""
                DELETE FROM public.mobile_sync_session
                WHERE tenant_id = :tid AND device_id = :device_id
            """),
            {"tid": tid, "device_id": device_id},
        )
        db.commit()
        print(f"  🗑  [mobile_sync_event]   Deleted {result_ev.rowcount} row(s)")
        print(f"  🗑  [mobile_sync_session] Deleted {result_sess.rowcount} row(s)")

    print("\n✅ Mobile sync scenario data wiped.")


def mode_inspect(db_url: str | None = None) -> None:
    """Show current state of mobile sync scenario data."""
    print("=== seed_scenario_mobile_sync: inspect mode ===")
    tid = str(TEST_TENANT_ID)

    with get_db_session() as db:
        sessions = db.execute(
            text("""
                SELECT id, device_id, triggered_by, outcome,
                       items_attempted, items_committed, started_at, completed_at
                FROM public.mobile_sync_session
                WHERE tenant_id = :tid
                ORDER BY started_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [mobile_sync_session]  {len(sessions)} row(s)")
        for s in sessions:
            print(
                f"    • {s.id}  device={s.device_id}"
                f"  triggered_by={s.triggered_by}  outcome={s.outcome}"
                f"  items={s.items_attempted}/{s.items_committed}"
            )

        events = db.execute(
            text("""
                SELECT id, operation_type, status, idempotency_uuid, client_capture_at
                FROM public.mobile_sync_event
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [mobile_sync_event]  {len(events)} row(s)")
        for e in events:
            print(
                f"    • {e.id}  op={e.operation_type}  status={e.status}"
                f"  idem={e.idempotency_uuid}"
            )

        # SD-6: Owner escalations
        escalations = db.execute(
            text("""
                SELECT id, status, escalation_reason, escalated_at, resolved_at,
                       resolution_payload
                FROM public.mobile_sync_owner_escalation
                WHERE tenant_id = :tid
                ORDER BY escalated_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [mobile_sync_owner_escalation]  {len(escalations)} row(s)")
        for esc in escalations:
            has_payload = esc.resolution_payload is not None
            print(
                f"    • {esc.id}  status={esc.status}  reason={esc.escalation_reason}"
                f"  escalated_at={esc.escalated_at}  resolved_at={esc.resolved_at}"
                f"  resolution_payload={'set' if has_payload else 'NULL'}"
            )

        # SD-7 Batch 2: mobile_sync_event_audit
        audits = db.execute(
            text("""
                SELECT id, escalation_id, originator_user_id, resolver_user_id,
                       resolution_action, resolution_channel, resolved_at
                FROM public.mobile_sync_event_audit
                WHERE tenant_id = :tid
                ORDER BY resolved_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [mobile_sync_event_audit]  {len(audits)} row(s)")
        for a in audits:
            print(
                f"    • {a.id}  esc={a.escalation_id}  action={a.resolution_action}"
                f"  channel={a.resolution_channel}  resolved={a.resolved_at}"
            )

        # SD-7 Batch 2: mobile_push_permission_state
        perms = db.execute(
            text("""
                SELECT tenant_id, user_id, device_id, permission_state, last_state_change_at
                FROM public.mobile_push_permission_state
                WHERE tenant_id = :tid
                ORDER BY last_state_change_at DESC
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [mobile_push_permission_state]  {len(perms)} row(s)")
        for p in perms:
            print(
                f"    • user={p.user_id}  device={p.device_id}  "
                f"state={p.permission_state}  changed={p.last_state_change_at}"
            )


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_mobile_sync.py — Group D mobile sync seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_mobile_sync.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(args, "reset", False):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_mobile_sync.py")
    if args.reset:
        mode_reset()
    elif args.mode == "seed":
        seed()
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        print("=== seed_scenario_mobile_sync: show mode ===")
        print(
            f"  Session 1: device={SEED_DEVICE_ID}  triggered_by=silent_push  outcome=success"
        )
        print(
            f"  Session 2: device={SEED_DEVICE_ID_2}  triggered_by=user_initiated  outcome=partial"
        )
        print(
            "  Events: create_time_entry, create_expense (succeeded) + update_job_status (conflict) + upload_photo (failed)"
        )
