"""
seed_scenario_voice_ai.py — Group D: Voice AI scenario data (SD-9).

Purpose: Seeds realistic, CHECK-constraint-valid, multi-user, multi-day voice
history for the primary test tenant AND tenant-B so the web Voice AI History /
Session Detail / Command Detail / feedback review / analytics surfaces render
real data instead of empty states.

Content manifest (design §F.2-§F.5):
  - 8 conversation_session rows (6 tenant-1 + 2 tenant-B)
  - ~24 conversation_message rows (alternating user/assistant + 1 system)
  - 16 voice_command_log rows (13 tenant-1 + 3 tenant-B)
  - 6 voice_command_entity_link rows (tenant-1 only — no tenant-B entities)
  - 2 voice_feedback rows (tenant-1 only)

NEVER run in production (Group D gating refuses prod).

Modes:
  --mode seed     (default) idempotent insert (zero DELETEs — existence-check-then-insert)
  --mode inspect  show per-tenant counts for all 5 voice tables
  --mode show     print definitions, no DB
  --reset         wipe the 5 voice tables for BOTH tenants (design §G-9)

Injectable inner functions (_seed_voice_ai / _reset_voice_ai) accept an open
connection so tests can call them against the rollback-wrapped db_session fixture
without committing to the shared dev DB (design §F.6).
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
from migrations.scripts.seed_second_tenant import (  # noqa: E402
    SECOND_TENANT_ID,
    TENANT_B_OWNER_ID,
    TENANT_B_TECH_ID,
)

# ── SEED DATA CONFIG ─────────────────────────────────────────────────────────

TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
TECH_USER_ID = UUID("00000000-0000-0000-0000-000000000003")

# ── Deterministic UUID families (design §B.3) ────────────────────────────────
# Sessions:    00000000-0000-0000-0010-0000000000NN (NN=01-08)
# Messages:    00000000-0000-0000-0011-0000000000NN (NN=01-24)
# Feedback:    00000000-0000-0000-0012-0000000000NN (NN=01-02)
# Offline-log idempotency UUIDs: 00000000-0000-0000-0013-0000000000NN (NN=01-02)
# Sync-log idempotency UUIDs:    00000000-0000-0000-0014-0000000000NN (NN=01-13)


def _sess_uuid(nn: int) -> str:
    return str(UUID(f"00000000-0000-0000-0010-{nn:012d}"))


def _msg_uuid(nn: int) -> str:
    return str(UUID(f"00000000-0000-0000-0011-{nn:012d}"))


def _fb_uuid(nn: int) -> str:
    return str(UUID(f"00000000-0000-0000-0012-{nn:012d}"))


def _offline_idem_uuid(nn: int) -> str:
    return str(UUID(f"00000000-0000-0000-0013-{nn:012d}"))


def _sync_idem_uuid(nn: int) -> str:
    return str(UUID(f"00000000-0000-0000-0014-{nn:012d}"))


# ── Session manifest (design §F.2) ───────────────────────────────────────────
# Rolling anchor: NOW() at run time with fixed negative offsets.
# Each session dict: key, user_id, offset, status, title, title_auto, context_json


def _build_sessions(now: datetime) -> list[dict]:
    """Build the 8-session manifest with rolling timestamps from NOW()."""
    today = now.replace(hour=9, minute=14, second=0, microsecond=0)
    return [
        # S1 — owner, today 09:14, active, auto title, rich context
        {
            "key": "S1",
            "id": _sess_uuid(1),
            "user_id": str(OWNER_USER_ID),
            "created_at": today,
            "status": "active",
            "title": "Johnson panel quote",
            "title_auto": True,
            "context_json": json.dumps(
                {
                    "active_quote_id": None,  # resolved at runtime
                    "active_customer_id": None,  # resolved at runtime
                    "last_action": "add_quote_line",
                    "pending_confirmation": None,
                    "safety_loto_verified": False,
                }
            ),
            "archived_at": None,
        },
        # S2 — owner, today 11:02, active, user-renamed title
        {
            "key": "S2",
            "id": _sess_uuid(2),
            "user_id": str(OWNER_USER_ID),
            "created_at": now.replace(hour=11, minute=2, second=0, microsecond=0),
            "status": "active",
            "title": "Davis 200A panel",
            "title_auto": False,
            "context_json": json.dumps(
                {
                    "active_job_id": None,  # resolved at runtime (DISP-002)
                    "last_action": "query_job_profit",
                }
            ),
            "archived_at": None,
        },
        # S3 — tech, today 07:45, ended
        {
            "key": "S3",
            "id": _sess_uuid(3),
            "user_id": str(TECH_USER_ID),
            "created_at": now.replace(hour=7, minute=45, second=0, microsecond=0),
            "status": "ended",
            "title": "Field ops — Smith residence",
            "title_auto": True,
            "context_json": json.dumps(
                {
                    "active_job_id": None,  # resolved at runtime (DISP-002)
                    "safety_loto_verified": True,
                }
            ),
            "archived_at": None,
        },
        # S4 — tech, yesterday 15:20, ended
        {
            "key": "S4",
            "id": _sess_uuid(4),
            "user_id": str(TECH_USER_ID),
            "created_at": (now - timedelta(days=1)).replace(
                hour=15, minute=20, second=0, microsecond=0
            ),
            "status": "ended",
            "title": "Time + expense logging",
            "title_auto": True,
            "context_json": json.dumps({"active_job_id": None}),  # JOB-900001
            "archived_at": None,
        },
        # S5 — owner, -2 days, archived (archived_at = updated_at)
        {
            "key": "S5",
            "id": _sess_uuid(5),
            "user_id": str(OWNER_USER_ID),
            "created_at": (now - timedelta(days=2)).replace(
                hour=10, minute=0, second=0, microsecond=0
            ),
            "status": "archived",
            "title": "Metro office rough-in",
            "title_auto": True,
            "context_json": "{}",
            "archived_at": (now - timedelta(days=2)).replace(
                hour=11, minute=30, second=0, microsecond=0
            ),
        },
        # S6 — tech, -3 days, abandoned, NULL title (exercises title fallback)
        {
            "key": "S6",
            "id": _sess_uuid(6),
            "user_id": str(TECH_USER_ID),
            "created_at": (now - timedelta(days=3)).replace(
                hour=14, minute=0, second=0, microsecond=0
            ),
            "status": "abandoned",
            "title": None,
            "title_auto": False,
            "context_json": "{}",
            "archived_at": None,
        },
        # SB1 — tenant-B owner, today 08:30, active
        {
            "key": "SB1",
            "id": _sess_uuid(7),
            "user_id": str(TENANT_B_OWNER_ID),
            "created_at": now.replace(hour=8, minute=30, second=0, microsecond=0),
            "status": "active",
            "title": "Apex storefront service call",
            "title_auto": True,
            "context_json": "{}",
            "archived_at": None,
        },
        # SB2 — tenant-B tech, yesterday 16:10, ended
        {
            "key": "SB2",
            "id": _sess_uuid(8),
            "user_id": str(TENANT_B_TECH_ID),
            "created_at": (now - timedelta(days=1)).replace(
                hour=16, minute=10, second=0, microsecond=0
            ),
            "status": "ended",
            "title": "Voltage drop questions",
            "title_auto": True,
            "context_json": "{}",
            "archived_at": None,
        },
    ]


# ── Message manifest (design §F.3) ───────────────────────────────────────────
# Each message: id, session_key, role, content_text, offset_minutes (from session created_at),
# structured_content_json (optional), created_by (None for assistant/system)


def _build_messages(sessions: list[dict]) -> list[dict]:
    """Build ~24 messages with chronological created_at within each session day."""
    sess_by_key = {s["key"]: s for s in sessions}
    msgs = []
    nn = 0

    def _add(session_key, role, text, offset_min, structured=None, created_by=None):
        nonlocal nn
        nn += 1
        s = sess_by_key[session_key]
        msg = {
            "id": _msg_uuid(nn),
            "session_id": s["id"],
            "created_at": s["created_at"] + timedelta(minutes=offset_min),
            "role": role,
            "content_text": text,
            "structured_content_json": structured,
            "created_by": created_by,
        }
        msgs.append(msg)

    # S1: 6 messages (system, user, assistant[snapshot], user, assistant, user)
    s1_user = str(OWNER_USER_ID)
    _add(
        "S1",
        "system",
        "Session initialized — voice pipeline ready.",
        0,
        created_by=None,
    )
    _add(
        "S1",
        "user",
        "Create a quote for Mary Johnson for a 200A service panel.",
        1,
        created_by=s1_user,
    )
    _add(
        "S1",
        "assistant",
        "I've created quote QUO-900003 for Mary Johnson. Here's the draft:",
        2,
        structured=None,  # filled at runtime with quote snapshot
        created_by=None,
    )
    _add("S1", "user", "Add a 200A service panel, quantity 1.", 4, created_by=s1_user)
    _add(
        "S1",
        "assistant",
        "Added 200A service panel (qty 1) to the quote. Anything else?",
        5,
        created_by=None,
    )
    _add("S1", "user", "That's all for now.", 7, created_by=s1_user)

    # S2: 4 messages (user, assistant, user[parse fail], assistant)
    _add(
        "S2",
        "user",
        "What's the profitability on the Davis job?",
        0,
        created_by=s1_user,
    )
    _add(
        "S2",
        "assistant",
        "The Davis 200A panel job is currently at 34% margin.",
        1,
        created_by=None,
    )
    _add("S2", "user", "Add the wire nuts to Tom's quote", 3, created_by=s1_user)
    _add(
        "S2",
        "assistant",
        "I couldn't parse that command. Could you rephrase?",
        4,
        created_by=None,
    )

    # S3: 5 messages (user, assistant[live], user, assistant, user)
    s3_user = str(TECH_USER_ID)
    _add("S3", "user", "Clock in to the Smith residence job.", 0, created_by=s3_user)
    _add(
        "S3",
        "assistant",
        "Clocked in. Here's the current job status:",
        1,
        structured=None,  # filled at runtime with live job_etc_status
        created_by=None,
    )
    _add("S3", "user", "Log 3 hours on this job.", 3, created_by=s3_user)
    _add(
        "S3",
        "assistant",
        "Logged 3 hours (journeyman rate). Added expense for breakers from Home Depot, $45.99.",
        4,
        created_by=None,
    )
    _add("S3", "user", "Thanks, clocking out now.", 6, created_by=s3_user)

    # S4: 6 messages (user, assistant, user, assistant, user[deferred], assistant)
    _add(
        "S4", "user", "Update the Davis job status to completed.", 0, created_by=s3_user
    )
    _add("S4", "assistant", "Job status updated to completed.", 1, created_by=None)
    _add("S4", "user", "Show me the active jobs.", 3, created_by=s3_user)
    _add(
        "S4",
        "assistant",
        "You have 3 active jobs: Davis panel, Smith residence, and Metro rough-in.",
        4,
        created_by=None,
    )
    _add("S4", "user", "Log 1.5 hours on the Johnson panel.", 6, created_by=s3_user)
    _add(
        "S4",
        "assistant",
        "Time entry received — processing offline capture.",
        7,
        created_by=None,
    )

    # S5: 3 messages (user, assistant, user)
    _add(
        "S5",
        "user",
        "Schedule the Metro rough-in for Thursday 10am.",
        0,
        created_by=s1_user,
    )
    _add(
        "S5",
        "assistant",
        "Scheduled Metro office rough-in for Thursday 10:00 AM.",
        1,
        created_by=None,
    )
    _add("S5", "user", "Great, archiving this session.", 3, created_by=s1_user)

    # S6: 4 messages (user, assistant, user[deferred-fail], assistant) — abandoned, NULL title
    _add("S6", "user", "What's my next job?", 0, created_by=s3_user)
    _add("S6", "assistant", "No upcoming jobs scheduled.", 1, created_by=None)
    _add("S6", "user", "Log my hours from yesterday.", 3, created_by=s3_user)
    _add(
        "S6",
        "assistant",
        "Unable to process — please try again later.",
        4,
        created_by=None,
    )

    # SB1: 3 messages (user, assistant, user)
    sb1_user = str(TENANT_B_OWNER_ID)
    _add(
        "SB1", "user", "Create a customer Apex Storefront LLC.", 0, created_by=sb1_user
    )
    _add(
        "SB1", "assistant", "Created customer Apex Storefront LLC.", 1, created_by=None
    )
    _add("SB1", "user", "Tell the customer I've arrived.", 3, created_by=sb1_user)

    # SB2: 3 messages (user, assistant, user)
    sb2_user = str(TENANT_B_TECH_ID)
    _add(
        "SB2",
        "user",
        "Calculate voltage drop for 200 feet of 10 AWG wire.",
        0,
        created_by=sb2_user,
    )
    _add(
        "SB2",
        "assistant",
        "Voltage drop for 200ft of 10 AWG at 20A is approximately 6.4V (2.7%).",
        1,
        created_by=None,
    )
    _add("SB2", "user", "Thanks, that's within the 3% limit.", 3, created_by=sb2_user)

    return msgs


# ── Command log manifest (design §F.4) ────────────────────────────────────────
# Each log: session_key, message_key_index (1-based into the session's user-turn messages),
# intent, entities_json, action, latencies (whisper, ollama, total) or None,
# is_successful, processing_status, idempotency_uuid, deferred timestamps


def _build_command_logs(sessions, messages) -> list[dict]:
    """Build 16 voice_command_log rows. message_id resolved at insert time."""
    sess_by_key = {s["key"]: s for s in sessions}
    # Map session_key → list of user-role message ids (in order)
    user_msgs_by_session: dict[str, list[str]] = {}
    for m in messages:
        if m["role"] == "user":
            user_msgs_by_session.setdefault(
                _find_session_key(m["session_id"], sessions), []
            ).append(m["id"])

    logs = []
    idem_nn = 0

    def _next_sync_idem():
        nonlocal idem_nn
        idem_nn += 1
        return _sync_idem_uuid(idem_nn)

    def _add(
        session_key,
        user_msg_idx,
        intent,
        entities,
        action,
        latencies,
        is_successful=True,
        processing_status=None,
        idempotency_uuid=None,
        deferred_ts=None,
    ):
        s = sess_by_key[session_key]
        msg_id = user_msgs_by_session[session_key][user_msg_idx]
        log = {
            "tenant_id": _tenant_for_session(session_key),
            "user_id": s["user_id"],
            "message_id": msg_id,
            "created_at": s["created_at"] + timedelta(minutes=user_msg_idx * 2 + 1),
            "intent_detected": intent,
            "entities_extracted": json.dumps(entities) if entities else None,
            "action_executed": action,
            "whisper_latency_ms": latencies[0] if latencies else None,
            "ollama_latency_ms": latencies[1] if latencies else None,
            "total_latency_ms": latencies[2] if latencies else None,
            "is_successful": is_successful,
            "processing_status": processing_status,
            "idempotency_uuid": idempotency_uuid or _next_sync_idem(),
            "audio_object_key": None,
            "captured_at": deferred_ts["captured_at"] if deferred_ts else None,
            "uploaded_at": deferred_ts["uploaded_at"] if deferred_ts else None,
            "transcribed_at": deferred_ts["transcribed_at"] if deferred_ts else None,
            "parsed_at": deferred_ts["parsed_at"] if deferred_ts else None,
        }
        logs.append(log)

    now = datetime.now(UTC)

    # V1 — S1, create_quote
    _add(
        "S1",
        0,
        "create_quote",
        {"customer_name": "Mary Johnson"},
        "create_quote_via_voice",
        (520, 280, 850),
    )
    # V2 — S1, add_quote_line (feedback F1 links here)
    _add(
        "S1",
        1,
        "add_quote_line",
        {"item_description": "200A service panel", "qty": 1},
        "add_line_via_voice",
        (480, 220, 740),
    )
    # V3 — S2, query_job_profit
    _add(
        "S2",
        0,
        "query_job_profit",
        {"job_reference": "Davis"},
        "get_job_profitability",
        (610, 350, 980),
    )
    # V4 — S3, clock_in
    _add(
        "S3",
        0,
        "clock_in",
        {"job_reference": "Smith residence"},
        "clock_in_via_voice",
        (450, 190, 670),
    )
    # V5 — S3, log_time_entry
    _add(
        "S3",
        1,
        "log_time_entry",
        {"hours": 3, "job_reference": "Smith residence"},
        "log_time_entry_via_voice",
        (520, 240, 790),
    )
    # V6 — S3, add_expense
    _add(
        "S3",
        2,
        "add_expense",
        {"amount": 45.99, "vendor": "Home Depot", "description": "breakers"},
        "add_expense_via_voice",
        (490, 210, 730),
    )
    # V7 — S4, update_job_status (NULL latencies)
    _add(
        "S4",
        0,
        "update_job_status",
        {"job_reference": "Davis", "status": "completed"},
        "update_job_status_via_voice",
        None,
    )
    # V8 — S4, navigate
    _add(
        "S4",
        1,
        "navigate",
        {"target": "active jobs"},
        "return_navigation_command",
        (380, 150, 560),
    )
    # V9 — S5, schedule_job
    _add(
        "S5",
        0,
        "schedule_job",
        {"job_reference": "Metro rough-in", "when": "Thursday 10am"},
        "schedule_job_via_voice",
        (550, 260, 840),
    )
    # V10 — S6, check_next_job (NULL latencies)
    _add("S6", 0, "check_next_job", {}, "check_next_job_via_voice", None)
    # V11 — S2, NULL intent (parse failure, is_successful=false, feedback F2 links here)
    _add("S2", 1, None, None, None, (600, 320, 950), is_successful=False)
    # V12 — S4, log_time_entry (DEFERRED: completed, full timestamp chain, ~3h gap)
    deferred_v12 = {
        "captured_at": now - timedelta(hours=3, minutes=30),
        "uploaded_at": now - timedelta(hours=3, minutes=15),
        "transcribed_at": now - timedelta(hours=3, minutes=5),
        "parsed_at": now - timedelta(hours=3),
    }
    _add(
        "S4",
        2,
        "log_time_entry",
        {"hours": 1.5, "job_reference": "Johnson panel"},
        "log_time_entry_via_voice",
        None,
        is_successful=True,
        processing_status="completed",
        idempotency_uuid=_offline_idem_uuid(1),
        deferred_ts=deferred_v12,
    )
    # V13 — S6, NULL (DEFERRED FAILED: captured/uploaded set, transcribed/parsed NULL)
    deferred_v13 = {
        "captured_at": now - timedelta(hours=5),
        "uploaded_at": now - timedelta(hours=4, minutes=45),
        "transcribed_at": None,
        "parsed_at": None,
    }
    _add(
        "S6",
        1,
        None,
        None,
        None,
        None,
        is_successful=False,
        processing_status="failed",
        idempotency_uuid=_offline_idem_uuid(2),
        deferred_ts=deferred_v13,
    )
    # VB1 — SB1, create_customer (tenant-B)
    _add(
        "SB1",
        0,
        "create_customer",
        {"customer_name": "Apex Storefront LLC"},
        "create_customer_via_voice",
        (510, 270, 810),
    )
    # VB2 — SB1, tell_customer_arrived (tenant-B)
    _add(
        "SB1",
        1,
        "tell_customer_arrived",
        {"customer_reference": "Apex"},
        "tell_customer_arrived_via_voice",
        (470, 200, 700),
    )
    # VB3 — SB2, calculate_voltage_drop (tenant-B, NULL latencies)
    _add(
        "SB2",
        0,
        "calculate_voltage_drop",
        {"length_ft": 200, "awg": "10"},
        "calculate_nec_voltage_drop",
        None,
    )

    return logs


def _tenant_for_session(session_key: str) -> str:
    """Return the tenant_id for a session key."""
    if session_key.startswith("SB"):
        return str(SECOND_TENANT_ID)
    return str(TEST_TENANT_ID)


def _find_session_key(session_id: str, sessions: list[dict]) -> str:
    for s in sessions:
        if s["id"] == session_id:
            return s["key"]
    return ""


# ── Entity link manifest (design §F.5) — tenant-1 only ───────────────────────
# Each link: log_index (0-based into logs list), entity_type, entity_lookup_fn, action


def _build_entity_link_specs() -> list[dict]:
    """Build 6 entity-link specs. Entity IDs resolved at runtime via business-key lookups."""
    return [
        {
            "log_idx": 3,
            "entity_type": "job",
            "lookup": "dispatch_inprogress",
            "action": "clock_in",
        },
        {
            "log_idx": 4,
            "entity_type": "job_time_entry",
            "lookup": "latest_time_entry_dispatch",
            "action": "logged",
        },
        {
            "log_idx": 5,
            "entity_type": "job_expense",
            "lookup": "latest_expense_dispatch",
            "action": "created",
        },
        {
            "log_idx": 6,
            "entity_type": "job",
            "lookup": "job_900001",
            "action": "status_changed",
        },
        {
            "log_idx": 8,
            "entity_type": "job",
            "lookup": "metro_job",
            "action": "rescheduled",
        },
        {
            "log_idx": 0,
            "entity_type": "quote",
            "lookup": "quo_900003",
            "action": "created",
        },
    ]


# ── Feedback manifest (design §F.5) ──────────────────────────────────────────


def _build_feedback_specs() -> list[dict]:
    """Build 2 feedback row specs. voice_command_log_id resolved at runtime."""
    return [
        {
            "id": _fb_uuid(1),
            "log_idx": 1,  # V2
            "original_transcription": "Add ten feet of twelve gauge wire",
            "corrected_text": "Add 10 feet of 12-gauge wire",
            "intent_misparsed": False,
            "corrected_intent": None,
            "feedback_notes": "Transcription normalization only",
        },
        {
            "id": _fb_uuid(2),
            "log_idx": 10,  # V11
            "original_transcription": "Add the wire nuts to Tom's quote",
            "corrected_text": None,
            "intent_misparsed": True,
            "corrected_intent": "add_quote_line",
            "feedback_notes": "Llama returned no intent — capture as retrain sample",
        },
    ]


# ── Runtime business-key lookups (design §F.4/§F.5) ──────────────────────────


def _resolve_runtime_lookups(db, sessions, messages, logs):
    """Resolve runtime business-key lookups and inject values into the manifests.

    - Session context_window_json: active_quote_id, active_customer_id, active_job_id
    - Message structured_content_json: S1 snapshot (quote), S3 live (job)
    - Entity-link targets: job/quote/time_entry/expense UUIDs
    """
    tid = str(TEST_TENANT_ID)

    # ── QUO-900003 (quote + customer + total + line count) ────────────────────
    quo_row = db.execute(
        text(
            "SELECT id, customer_id, total_cents FROM public.quote "
            "WHERE tenant_id = :tid AND quote_number = 'QUO-900003' LIMIT 1"
        ),
        {"tid": tid},
    ).first()
    quo_id = str(quo_row.id) if quo_row else None
    quo_customer_id = str(quo_row.customer_id) if quo_row else None
    quo_total = quo_row.total_cents if quo_row else 0

    quo_line_count = 0
    if quo_id:
        quo_line_count = (
            db.execute(
                text(
                    "SELECT COUNT(*) FROM public.quote_line "
                    "WHERE tenant_id = :tid AND quote_id = :qid"
                ),
                {"tid": tid, "qid": quo_id},
            ).scalar()
            or 0
        )

    # ── JOB-900001 ────────────────────────────────────────────────────────────
    job_900001_row = db.execute(
        text(
            "SELECT id FROM public.job "
            "WHERE tenant_id = :tid AND job_number = 'JOB-900001' LIMIT 1"
        ),
        {"tid": tid},
    ).first()
    job_900001_id = str(job_900001_row.id) if job_900001_row else None

    # ── DISP-002 (in-progress dispatch job) ───────────────────────────────────
    disp002_row = db.execute(
        text(
            "SELECT id FROM public.job "
            "WHERE tenant_id = :tid AND job_number = 'DISP-002' LIMIT 1"
        ),
        {"tid": tid},
    ).first()
    disp002_id = str(disp002_row.id) if disp002_row else None

    # ── Metro Properties job (title ILIKE) ────────────────────────────────────
    metro_row = db.execute(
        text(
            "SELECT id FROM public.job "
            "WHERE tenant_id = :tid AND title ILIKE '%Metro%' LIMIT 1"
        ),
        {"tid": tid},
    ).first()
    metro_job_id = str(metro_row.id) if metro_row else None

    # ── Latest time entry on DISP-002 ─────────────────────────────────────────
    latest_te_id = None
    if disp002_id:
        te_row = db.execute(
            text(
                "SELECT id FROM public.job_time_entry "
                "WHERE tenant_id = :tid AND job_id = :jid "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tid, "jid": disp002_id},
        ).first()
        latest_te_id = str(te_row.id) if te_row else None

    # ── Latest expense on DISP-002 ────────────────────────────────────────────
    latest_exp_id = None
    if disp002_id:
        exp_row = db.execute(
            text(
                "SELECT id FROM public.job_expense "
                "WHERE tenant_id = :tid AND job_id = :jid "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tid, "jid": disp002_id},
        ).first()
        latest_exp_id = str(exp_row.id) if exp_row else None

    # ── Inject into session context_window_json ───────────────────────────────
    for s in sessions:
        ctx = json.loads(s["context_json"])
        if s["key"] == "S1":
            ctx["active_quote_id"] = quo_id
            ctx["active_customer_id"] = quo_customer_id
        elif s["key"] in ("S2", "S3"):
            ctx["active_job_id"] = disp002_id
        elif s["key"] == "S4":
            ctx["active_job_id"] = job_900001_id
        s["context_json"] = json.dumps(ctx)

    # ── Inject structured_content_json into messages ──────────────────────────
    for m in messages:
        if m["role"] != "assistant":
            continue
        # S1 assistant (3rd message, index 2) — snapshot quote_draft
        if m["id"] == _msg_uuid(3):
            m["structured_content_json"] = json.dumps(
                {
                    "render_mode": "snapshot",
                    "content_type": "quote_draft",
                    "data": {
                        "quote_number": "QUO-900003",
                        "customer_name": "Mary Johnson",
                        "total_cents": quo_total,
                        "line_count": quo_line_count,
                    },
                    "captured_at": m["created_at"].isoformat(),
                }
            )
        # S3 assistant (2nd message, index 7 overall) — live job_etc_status
        elif m["id"] == _msg_uuid(8):
            m["structured_content_json"] = json.dumps(
                {
                    "render_mode": "live",
                    "content_type": "job_etc_status",
                    "data": {"job_id": disp002_id},
                    "captured_at": m["created_at"].isoformat(),
                }
            )

    # ── Build entity-link target resolution map ──────────────────────────────
    link_targets = {
        "dispatch_inprogress": disp002_id,
        "latest_time_entry_dispatch": latest_te_id,
        "latest_expense_dispatch": latest_exp_id,
        "job_900001": job_900001_id,
        "metro_job": metro_job_id,
        "quo_900003": quo_id,
    }

    return link_targets


# ── INJECTABLE INNER FUNCTIONS (test-isolation seam, design §F.6) ────────────


def _seed_voice_ai(db, tenant_id: UUID) -> dict[str, int]:
    """All inserts for the passed tenant AND tenant-B.

    B-side is skipped with a printed notice if tenant …-0006 does not exist
    (ordering: seed_second_tenant.py runs first; QA orchestrator runs
    second-tenant before scenarios). Tenant-B gets sessions/messages/logs only
    — no entity links (design §G-8).

    Returns per-table new-row counts (0 on idempotent re-run).
    """
    counts = {
        "conversation_session": 0,
        "conversation_message": 0,
        "voice_command_log": 0,
        "voice_command_entity_link": 0,
        "voice_feedback": 0,
    }
    now = datetime.now(UTC)

    # ── Check tenant-B exists ─────────────────────────────────────────────────
    tenant_b_exists = db.execute(
        text("SELECT 1 FROM public.tenant WHERE id = :tid"),
        {"tid": str(SECOND_TENANT_ID)},
    ).first()
    if not tenant_b_exists:
        print(
            f"  ⚠️  Tenant-B ({SECOND_TENANT_ID}) not found — "
            "B-side sessions skipped. Run seed_second_tenant.py first."
        )

    # ── Build manifests ───────────────────────────────────────────────────────
    sessions = _build_sessions(now)
    messages = _build_messages(sessions)
    logs = _build_command_logs(sessions, messages)
    link_specs = _build_entity_link_specs()
    feedback_specs = _build_feedback_specs()

    # ── Resolve runtime lookups (tenant-1 entities only) ──────────────────────
    link_targets = _resolve_runtime_lookups(db, sessions, messages, logs)

    # ── 1. Sessions (existence check by deterministic PK) ─────────────────────
    for s in sessions:
        # Skip tenant-B sessions if tenant-B doesn't exist
        if s["key"].startswith("SB") and not tenant_b_exists:
            continue
        existed = db.execute(
            text("SELECT 1 FROM public.conversation_session WHERE id = :id"),
            {"id": s["id"]},
        ).first()
        if existed:
            continue
        db.execute(
            text("""
                INSERT INTO public.conversation_session
                (id, tenant_id, user_id, status, context_summary, title,
                 title_auto_generated, context_window_json, expires_at, archived_at,
                 is_active, created_at, updated_at, created_by, updated_by)
                VALUES (:id, :tenant_id, :user_id, :status, NULL, :title,
                        :title_auto, CAST(:ctx AS jsonb), NULL, :archived_at,
                        true, :created_at, :created_at, :user_id, :user_id)
            """),
            {
                "id": s["id"],
                "tenant_id": _tenant_for_session(s["key"]),
                "user_id": s["user_id"],
                "status": s["status"],
                "title": s["title"],
                "title_auto": s["title_auto"],
                "ctx": s["context_json"],
                "archived_at": s["archived_at"],
                "created_at": s["created_at"],
            },
        )
        counts["conversation_session"] += 1
        print(
            f"  ✅ [conversation_session] {s['key']} ({s['id'][:12]}…) status={s['status']}"
        )

    # ── 2. Messages (existence check by deterministic PK) ────────────────────
    for m in messages:
        # Skip tenant-B messages if tenant-B doesn't exist
        s_key = _find_session_key(m["session_id"], sessions)
        if s_key.startswith("SB") and not tenant_b_exists:
            continue
        existed = db.execute(
            text("SELECT 1 FROM public.conversation_message WHERE id = :id"),
            {"id": m["id"]},
        ).first()
        if existed:
            continue
        db.execute(
            text("""
                INSERT INTO public.conversation_message
                (id, tenant_id, session_id, role, content_text, audio_object_key,
                 structured_content_json, embedding, created_by, created_at)
                VALUES (:id, :tenant_id, :session_id, :role, :content_text, NULL,
                        CAST(:structured AS jsonb), NULL, :created_by, :created_at)
            """),
            {
                "id": m["id"],
                "tenant_id": _tenant_for_session(s_key),
                "session_id": m["session_id"],
                "role": m["role"],
                "content_text": m["content_text"],
                "structured": m["structured_content_json"],
                "created_by": m["created_by"],
                "created_at": m["created_at"],
            },
        )
        counts["conversation_message"] += 1

    print(f"  ✅ [conversation_message] {counts['conversation_message']} new row(s)")

    # ── 3. Command logs (existence check by (tenant_id, idempotency_uuid)) ────
    # Capture RETURNING id for downstream entity links + feedback
    log_ids: list[int | None] = [None] * len(logs)
    for i, log in enumerate(logs):
        # Skip tenant-B logs if tenant-B doesn't exist
        s_key = _find_session_key_by_user_msg(log["message_id"], sessions, messages)
        if s_key and s_key.startswith("SB") and not tenant_b_exists:
            continue
        existed = db.execute(
            text(
                "SELECT id FROM public.voice_command_log "
                "WHERE tenant_id = :tid AND idempotency_uuid = :idem"
            ),
            {"tid": log["tenant_id"], "idem": log["idempotency_uuid"]},
        ).first()
        if existed:
            log_ids[i] = existed.id
            continue
        result = db.execute(
            text("""
                INSERT INTO public.voice_command_log
                (tenant_id, user_id, message_id, intent_detected, entities_extracted,
                 action_executed, whisper_latency_ms, ollama_latency_ms, total_latency_ms,
                 is_successful, audio_object_key, captured_at, uploaded_at, transcribed_at,
                 parsed_at, processing_status, idempotency_uuid, created_at)
                VALUES (:tenant_id, :user_id, :message_id, :intent, :entities,
                        :action, :whisper, :ollama, :total,
                        :is_successful, NULL, :captured_at, :uploaded_at, :transcribed_at,
                        :parsed_at, :processing_status, CAST(:idem AS uuid), :created_at)
                RETURNING id
            """),
            {
                "tenant_id": log["tenant_id"],
                "user_id": log["user_id"],
                "message_id": log["message_id"],
                "intent": log["intent_detected"],
                "entities": log["entities_extracted"],
                "action": log["action_executed"],
                "whisper": log["whisper_latency_ms"],
                "ollama": log["ollama_latency_ms"],
                "total": log["total_latency_ms"],
                "is_successful": log["is_successful"],
                "captured_at": log["captured_at"],
                "uploaded_at": log["uploaded_at"],
                "transcribed_at": log["transcribed_at"],
                "parsed_at": log["parsed_at"],
                "processing_status": log["processing_status"],
                "idem": log["idempotency_uuid"],
                "created_at": log["created_at"],
            },
        )
        log_ids[i] = result.first().id
        counts["voice_command_log"] += 1

    print(f"  ✅ [voice_command_log] {counts['voice_command_log']} new row(s)")

    # ── 4. Entity links (tenant-1 only — existence check on natural key) ──────
    for spec in link_specs:
        log_idx = spec["log_idx"]
        if log_idx >= len(logs) or log_ids[log_idx] is None:
            print(
                f"  ⚠️  [voice_command_entity_link] Log index {log_idx} not found — skipping"
            )
            continue
        target_id = link_targets.get(spec["lookup"])
        if not target_id:
            print(
                f"  ⚠️  [voice_command_entity_link] Target '{spec['lookup']}' not found — skipping"
            )
            continue
        log_id = log_ids[log_idx]
        existed = db.execute(
            text(
                "SELECT 1 FROM public.voice_command_entity_link "
                "WHERE voice_command_log_id = :log_id AND entity_type = :etype "
                "AND entity_id = :eid"
            ),
            {"log_id": log_id, "etype": spec["entity_type"], "eid": target_id},
        ).first()
        if existed:
            continue
        db.execute(
            text("""
                INSERT INTO public.voice_command_entity_link
                (tenant_id, voice_command_log_id, entity_type, entity_id, action,
                 created_at, created_by)
                VALUES (:tenant_id, :log_id, :etype, CAST(:eid AS uuid), :action,
                        NOW(), :created_by)
            """),
            {
                "tenant_id": str(TEST_TENANT_ID),
                "log_id": log_id,
                "etype": spec["entity_type"],
                "eid": target_id,
                "action": spec["action"],
                "created_by": str(OWNER_USER_ID),
            },
        )
        counts["voice_command_entity_link"] += 1
        print(
            f"  ✅ [voice_command_entity_link] {spec['entity_type']} → {spec['lookup']} ({spec['action']})"
        )

    # ── 5. Feedback (tenant-1 only — existence check by deterministic PK) ─────
    for fb in feedback_specs:
        log_idx = fb["log_idx"]
        if log_idx >= len(logs) or log_ids[log_idx] is None:
            print(f"  ⚠️  [voice_feedback] Log index {log_idx} not found — skipping")
            continue
        existed = db.execute(
            text("SELECT 1 FROM public.voice_feedback WHERE id = :id"),
            {"id": fb["id"]},
        ).first()
        if existed:
            continue
        db.execute(
            text("""
                INSERT INTO public.voice_feedback
                (id, tenant_id, user_id, voice_command_log_id, original_transcription,
                 corrected_text, intent_misparsed, corrected_intent, feedback_notes,
                 s3_export_key, exported_at, created_at, created_by)
                VALUES (:id, :tenant_id, :user_id, :log_id, :orig,
                        :corrected, :misparsed, :corrected_intent, :notes,
                        NULL, NULL, NOW(), :created_by)
            """),
            {
                "id": fb["id"],
                "tenant_id": str(TEST_TENANT_ID),
                "user_id": str(OWNER_USER_ID),
                "log_id": log_ids[log_idx],
                "orig": fb["original_transcription"],
                "corrected": fb["corrected_text"],
                "misparsed": fb["intent_misparsed"],
                "corrected_intent": fb["corrected_intent"],
                "notes": fb["feedback_notes"],
                "created_by": str(OWNER_USER_ID),
            },
        )
        counts["voice_feedback"] += 1
        print(f"  ✅ [voice_feedback] {fb['id'][:12]}… → log[{log_idx}]")

    return counts


def _find_session_key_by_user_msg(message_id: str, sessions, messages) -> str:
    """Find the session key for a given message_id."""
    for m in messages:
        if m["id"] == message_id:
            return _find_session_key(m["session_id"], sessions)
    return ""


def _reset_voice_ai(db, tenant_id: UUID) -> dict[str, int]:
    """Wipe the 5 voice tables for BOTH tenants (design §G-9).

    reset_dev_db.py only ever passes the primary tenant; without the tenant-B
    wipe, B-side rows would orphan across full resets. Child-first FK order:
    feedback → entity_link → log → message → session.
    """
    counts: dict[str, int] = {}
    tenants = [str(TEST_TENANT_ID), str(SECOND_TENANT_ID)]

    tables_child_first = [
        "voice_feedback",
        "voice_command_entity_link",
        "voice_command_log",
        "conversation_message",
        "conversation_session",
    ]

    for tid in tenants:
        for table in tables_child_first:
            result = db.execute(
                text(f"DELETE FROM public.{table} WHERE tenant_id = :tid"),
                {"tid": tid},
            )
            if result.rowcount:
                counts[table] = counts.get(table, 0) + result.rowcount
                print(
                    f"  🗑  [{table}] Deleted {result.rowcount} row(s) for tenant {tid[:12]}…"
                )

    return counts


# ── PUBLIC MODE WRAPPERS ─────────────────────────────────────────────────────


def mode_seed(tenant_id: UUID = TEST_TENANT_ID) -> None:
    """Idempotent seed — inserts voice AI history for both tenants."""
    print("=== seed_scenario_voice_ai: seed mode ===")
    print(f"    Primary Tenant ID: {tenant_id}\n")

    with get_db_session() as db:
        counts = _seed_voice_ai(db, tenant_id)
        db.commit()

    total_new = sum(counts.values())
    print(f"\n🎉 seed_scenario_voice_ai complete — {total_new} new row(s)")


def mode_reset(tenant_id: UUID = TEST_TENANT_ID) -> None:
    """Wipe the 5 voice tables for both tenants."""
    print("=== seed_scenario_voice_ai: reset mode ===")
    print(f"    Primary Tenant ID: {tenant_id}\n")

    with get_db_session() as db:
        counts = _reset_voice_ai(db, tenant_id)
        db.commit()

    total_del = sum(counts.values())
    print(f"\n✅ Voice AI scenario reset complete — {total_del} row(s) deleted.")


def mode_inspect() -> None:
    """Show per-tenant counts for all 5 voice tables."""
    print("=== seed_scenario_voice_ai: inspect mode ===\n")

    tenants = [
        ("Tenant-1 (…0001)", str(TEST_TENANT_ID)),
        ("Tenant-B (…0006)", str(SECOND_TENANT_ID)),
    ]

    with get_db_session() as db:
        for label, tid in tenants:
            print(f"  {label}:")
            for table in [
                "conversation_session",
                "conversation_message",
                "voice_command_log",
                "voice_command_entity_link",
                "voice_feedback",
            ]:
                count = db.execute(
                    text(f"SELECT COUNT(*) FROM public.{table} WHERE tenant_id = :tid"),
                    {"tid": tid},
                ).scalar()
                print(f"    {table:<35} {count} row(s)")
            print()

        # Show session details for tenant-1
        print("  Tenant-1 sessions:")
        sessions = db.execute(
            text("""
                SELECT id, user_id, status, title, title_auto_generated,
                       created_at, archived_at
                FROM public.conversation_session
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """),
            {"tid": str(TEST_TENANT_ID)},
        ).fetchall()
        for s in sessions:
            title_display = s.title or "(NULL — fallback to context_summary)"
            archived = f" archived_at={s.archived_at}" if s.archived_at else ""
            print(
                f"    • {s.id}  user={s.user_id}  status={s.status}  "
                f"title='{title_display}'  auto={s.title_auto_generated}  "
                f"created={s.created_at}{archived}"
            )


def mode_show() -> None:
    """Print what would be seeded without touching the DB."""
    print("=== seed_scenario_voice_ai: show mode ===\n")
    print("  Content manifest (design §F.2-§F.5):")
    print("    conversation_session:           8 rows (6 tenant-1 + 2 tenant-B)")
    print(
        "    conversation_message:          ~24 rows (alternating user/assistant + 1 system)"
    )
    print("    voice_command_log:              16 rows (13 tenant-1 + 3 tenant-B)")
    print("    voice_command_entity_link:       6 rows (tenant-1 only)")
    print("    voice_feedback:                  2 rows (tenant-1 only)")
    print()
    print("  Deterministic UUID families (design §B.3):")
    print("    Sessions:    00000000-0000-0000-0010-0000000000NN (NN=01-08)")
    print("    Messages:    00000000-0000-0000-0011-0000000000NN (NN=01-24)")
    print("    Feedback:    00000000-0000-0000-0012-0000000000NN (NN=01-02)")
    print("    Offline idem:00000000-0000-0000-0013-0000000000NN (NN=01-02)")
    print("    Sync idem:   00000000-0000-0000-0014-0000000000NN (NN=01-13)")
    print()
    print("  Sessions:")
    print("    S1  owner  today 09:14   active    'Johnson panel quote' (auto)")
    print("    S2  owner  today 11:02   active    'Davis 200A panel' (user-renamed)")
    print("    S3  tech   today 07:45   ended     'Field ops — Smith residence' (auto)")
    print("    S4  tech   yesterday     ended     'Time + expense logging' (auto)")
    print("    S5  owner  -2 days       archived  'Metro office rough-in' (auto)")
    print("    S6  tech   -3 days       abandoned NULL title (fallback exercise)")
    print("    SB1 tenant-B owner today 08:30  active 'Apex storefront service call'")
    print("    SB2 tenant-B tech  yesterday     ended  'Voltage drop questions'")


# ── CLI ──────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_voice_ai.py — Group D Voice AI scenario seeder (SD-9)"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_voice_ai.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(
        args, "reset", False
    ):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_voice_ai.py")

    if args.reset:
        mode_reset()
    elif args.mode == "seed":
        mode_seed()
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        mode_show()
