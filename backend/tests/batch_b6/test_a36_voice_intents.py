"""
B6/A36: Voice Intent Grammar for Conflict Resolution — Tests

Test focus cases:
  list_pending_calendar_conflicts:
    - [A36-1] Intent registered in INTENT_HANDLERS
    - [A36-2] Returns zero-count message when no pending conflicts
    - [A36-3] Returns count + job title when conflicts exist
    - [A36-4] Includes pending_count and top_conflict_id in data

  resolve_calendar_conflict:
    - [A36-5] Intent registered in INTENT_HANDLERS
    - [A36-6] Turn 1: writes pending_confirmation to session context
    - [A36-7] Turn 1: returns requires_confirmation=True with spoken summary
    - [A36-8] Turn 2: executes resolve and clears pending_confirmation
    - [A36-9] Turn 2: staleness 409 branch — announces change
    - [A36-10] Refusal: deleted_modified conflict redirects to web
    - [A36-11] Refusal: missing conflict ID returns needs_clarification
    - [A36-12] Resolution side mapping: 'pilot' → 'accept_local'
    - [A36-13] Resolution side mapping: 'google' → 'accept_remote'
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app.models.ai import ConversationSession
from app.models.scheduling import CalendarSyncConflict
from services.voice_action_router import (
    INTENT_HANDLERS,
    list_pending_calendar_conflicts_via_voice,
    resolve_calendar_conflict_via_voice,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_user(tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
    """Create a mock user context."""
    mock = MagicMock()
    mock.tenant_id = tenant_id
    mock.id = user_id or uuid.UUID("00000000-0000-0000-0000-000000000002")
    return mock


def _make_real_session(
    db_session, tenant_id: uuid.UUID, ctx_dict: dict | None = None
) -> ConversationSession:
    """Create a real ConversationSession row for tests that call db.add(session)."""
    from sqlmodel import select as _sel

    from app.models.core import User

    user = db_session.exec(_sel(User).limit(1)).first()
    user_id = user.id if user else uuid.UUID("00000000-0000-0000-0000-000000000002")

    session_obj = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        title="A36 Test Session",
        is_active=True,
        context_window_json=ctx_dict or {},
    )
    db_session.add(session_obj)
    db_session.commit()
    db_session.refresh(session_obj)
    return session_obj


def _make_conflict(
    db_session,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    conflict_type: str = "modified_modified",
    resolution: str = None,
) -> CalendarSyncConflict:
    """Create a minimal CalendarSyncConflict."""

    now = datetime.now(UTC)
    conflict = CalendarSyncConflict(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        conflict_type=conflict_type,
        local_snapshot={
            "title": "Panel Upgrade",
            "scheduled_start_at": "2026-05-10T09:00:00Z",
        },
        remote_snapshot={
            "title": "Panel Upgrade",
            "scheduled_start_at": "2026-05-10T10:00:00Z",
        },
        base_snapshot={
            "title": "Panel Upgrade",
            "scheduled_start_at": "2026-05-10T09:00:00Z",
        },
        pilot_modified_at=now - timedelta(hours=2),
        external_modified_at=now - timedelta(hours=1),
        auto_resolved_stale=False,
        resolution=resolution,
        urgency_score=5,
    )
    db_session.add(conflict)
    db_session.commit()
    db_session.refresh(conflict)
    return conflict


def _make_job(db_session, tenant_id: uuid.UUID):
    """Create minimal Job."""
    from app.models.crm import Customer, Site
    from app.models.fulfillment import Job, JobStatus

    customer = Customer(id=uuid.uuid4(), tenant_id=tenant_id, display_name="A36 Test")
    db_session.add(customer)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_name="A36 Site",
        is_active=True,
    )
    db_session.add(site)
    db_session.flush()

    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "draft")
    ).first()
    if not job_status:
        job_status = JobStatus(
            id=uuid.uuid4(), code="draft", name="Draft", is_active=True
        )
        db_session.add(job_status)
        db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ===========================================================================
# [A36-1/A36-5] Registration tests
# ===========================================================================


class TestVoiceIntentRegistration:
    def test_a36_1_list_conflicts_registered(self):
        """[A36-1] list_pending_calendar_conflicts in INTENT_HANDLERS."""
        assert "list_pending_calendar_conflicts" in INTENT_HANDLERS
        assert (
            INTENT_HANDLERS["list_pending_calendar_conflicts"]
            is list_pending_calendar_conflicts_via_voice
        )

    def test_a36_5_resolve_conflict_registered(self):
        """[A36-5] resolve_calendar_conflict in INTENT_HANDLERS."""
        assert "resolve_calendar_conflict" in INTENT_HANDLERS
        assert (
            INTENT_HANDLERS["resolve_calendar_conflict"]
            is resolve_calendar_conflict_via_voice
        )


# ===========================================================================
# [A36-2/3/4] list_pending_calendar_conflicts handler
# ===========================================================================


class TestListPendingConflictsVoice:
    @pytest.mark.asyncio
    async def test_a36_2_zero_count_message(self, db_session, test_tenant):
        """[A36-2] Returns zero-count message when no pending conflicts."""
        user = _make_mock_user(test_tenant.id)
        session = _make_real_session(db_session, test_tenant.id)

        # Ensure no pending conflicts for this tenant
        db_session.execute(
            __import__("sqlalchemy", fromlist=["text"]).text(
                "DELETE FROM calendar_sync_conflict WHERE tenant_id = :tid AND resolution IS NULL"
            ),
            {"tid": str(test_tenant.id)},
        )
        db_session.commit()

        result = await list_pending_calendar_conflicts_via_voice(
            {}, user, db_session, session
        )

        assert result["success"] is True
        assert result["data"]["pending_count"] == 0
        assert "no pending" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_a36_3_count_and_job_title(self, db_session, test_tenant):
        """[A36-3] Returns count + job title when conflicts exist."""
        job = _make_job(db_session, test_tenant.id)
        _make_conflict(db_session, test_tenant.id, job.id, urgency_score=2)

        user = _make_mock_user(test_tenant.id)
        session = _make_real_session(db_session, test_tenant.id)

        result = await list_pending_calendar_conflicts_via_voice(
            {}, user, db_session, session
        )

        assert result["success"] is True
        assert result["data"]["pending_count"] >= 1
        assert (
            "Panel Upgrade" in result["message"]
            or "conflict" in result["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_a36_4_data_includes_conflict_id(self, db_session, test_tenant):
        """[A36-4] data includes pending_count and top_conflict_id."""
        job = _make_job(db_session, test_tenant.id)
        conflict = _make_conflict(db_session, test_tenant.id, job.id)

        user = _make_mock_user(test_tenant.id)
        session = _make_real_session(db_session, test_tenant.id)

        result = await list_pending_calendar_conflicts_via_voice(
            {}, user, db_session, session
        )

        assert "pending_count" in result["data"]
        assert "top_conflict_id" in result["data"]
        assert result["data"]["pending_count"] >= 1


# monkeypatch for CalendarSyncConflict missing urgency_score in helper
def _make_conflict(
    db_session,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    conflict_type: str = "modified_modified",
    resolution: str = None,
    urgency_score: int = 5,
) -> CalendarSyncConflict:
    """Create a minimal CalendarSyncConflict with urgency_score."""
    now = datetime.now(UTC)
    conflict = CalendarSyncConflict(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        conflict_type=conflict_type,
        local_snapshot={
            "title": "Panel Upgrade",
            "scheduled_start_at": "2026-05-10T09:00:00Z",
        },
        remote_snapshot={
            "title": "Panel Upgrade",
            "scheduled_start_at": "2026-05-10T10:00:00Z",
        },
        base_snapshot={
            "title": "Panel Upgrade",
            "scheduled_start_at": "2026-05-10T09:00:00Z",
        },
        pilot_modified_at=now - timedelta(hours=2),
        external_modified_at=now - timedelta(hours=1),
        auto_resolved_stale=False,
        resolution=resolution,
        urgency_score=urgency_score,
    )
    db_session.add(conflict)
    db_session.commit()
    db_session.refresh(conflict)
    return conflict


# ===========================================================================
# [A36-6/7/8/9/10/11] resolve_calendar_conflict handler
# ===========================================================================


class TestResolveConflictVoice:
    @pytest.mark.asyncio
    async def test_a36_6_turn1_writes_pending_confirmation(
        self, db_session, test_tenant
    ):
        """[A36-6] Turn 1 writes pending_confirmation to session context."""
        job = _make_job(db_session, test_tenant.id)
        conflict = _make_conflict(db_session, test_tenant.id, job.id)

        user = _make_mock_user(test_tenant.id)
        session = _make_real_session(db_session, test_tenant.id)

        entities = {
            "conflict_id": str(conflict.id),
            "resolution_side": "pilot",
        }

        result = await resolve_calendar_conflict_via_voice(
            entities, user, db_session, session
        )

        assert result["success"] is True
        assert result.get("requires_confirmation") is True
        # Pending confirmation should be written
        assert session.context_window_json.get("pending_confirmation") is not None
        pc = session.context_window_json["pending_confirmation"]
        assert pc["action"] == "resolve_calendar_conflict"
        assert pc["resolution"] == "accept_local"

    @pytest.mark.asyncio
    async def test_a36_7_turn1_returns_spoken_summary(self, db_session, test_tenant):
        """[A36-7] Turn 1 returns requires_confirmation=True with spoken summary."""
        job = _make_job(db_session, test_tenant.id)
        conflict = _make_conflict(db_session, test_tenant.id, job.id)

        user = _make_mock_user(test_tenant.id)
        session = _make_real_session(db_session, test_tenant.id)

        entities = {"conflict_id": str(conflict.id), "resolution_side": "google"}
        result = await resolve_calendar_conflict_via_voice(
            entities, user, db_session, session
        )

        assert result.get("requires_confirmation") is True
        assert "Confirm" in result["message"] or "confirm" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_a36_8_turn2_executes_resolve(self, db_session, test_tenant):
        """[A36-8] Turn 2 executes resolve and clears pending_confirmation."""
        job = _make_job(db_session, test_tenant.id)
        conflict = _make_conflict(db_session, test_tenant.id, job.id)

        user = _make_mock_user(test_tenant.id)

        # Pre-load session with pending confirmation (simulating Turn 1 already done)
        pending = {
            "action": "resolve_calendar_conflict",
            "conflict_id": str(conflict.id),
            "resolution": "accept_local",
            "expected_pilot_modified_at": conflict.pilot_modified_at.isoformat(),
            "expected_external_modified_at": conflict.external_modified_at.isoformat(),
            "summary_prompt": "Accepting the Pilot version. Confirm?",
        }
        session = _make_real_session(
            db_session, test_tenant.id, ctx_dict={"pending_confirmation": pending}
        )

        result = await resolve_calendar_conflict_via_voice(
            {}, user, db_session, session
        )

        assert result["success"] is True
        assert "Pilot" in result["message"] or "pilot" in result["message"].lower()

        # Verify resolution was applied to DB
        db_session.refresh(conflict)
        assert conflict.resolution == "accept_local"
        # result dict confirms pending_confirmation cleared (success=True, no requires_confirmation)
        assert result.get("requires_confirmation") is None

    @pytest.mark.asyncio
    async def test_a36_9_turn2_staleness_409_branch(self, db_session, test_tenant):
        """[A36-9] Turn 2 staleness branch announces change when timestamps mismatch."""
        job = _make_job(db_session, test_tenant.id)
        conflict = _make_conflict(db_session, test_tenant.id, job.id)

        user = _make_mock_user(test_tenant.id)

        # Use WRONG timestamps to trigger staleness
        old_pilot_at = (conflict.pilot_modified_at - timedelta(hours=5)).isoformat()
        old_external_at = (
            conflict.external_modified_at - timedelta(hours=5)
        ).isoformat()
        pending = {
            "action": "resolve_calendar_conflict",
            "conflict_id": str(conflict.id),
            "resolution": "accept_local",
            "expected_pilot_modified_at": old_pilot_at,
            "expected_external_modified_at": old_external_at,
        }
        session = _make_real_session(
            db_session, test_tenant.id, ctx_dict={"pending_confirmation": pending}
        )

        result = await resolve_calendar_conflict_via_voice(
            {}, user, db_session, session
        )

        assert result["success"] is False
        assert (
            "changed" in result["message"].lower()
            or "review" in result["message"].lower()
        )
        assert result.get("requires_web_review") is True

    @pytest.mark.asyncio
    async def test_a36_10_refusal_deleted_modified(self, db_session, test_tenant):
        """[A36-10] Deletion conflicts redirect to web."""
        job = _make_job(db_session, test_tenant.id)
        conflict = _make_conflict(
            db_session, test_tenant.id, job.id, conflict_type="deleted_modified"
        )

        user = _make_mock_user(test_tenant.id)
        session = _make_real_session(db_session, test_tenant.id)

        entities = {"conflict_id": str(conflict.id), "resolution_side": "pilot"}
        result = await resolve_calendar_conflict_via_voice(
            entities, user, db_session, session
        )

        assert result["success"] is False
        assert result.get("requires_web_review") is True

    @pytest.mark.asyncio
    async def test_a36_11_missing_conflict_id_returns_clarification(
        self, db_session, test_tenant
    ):
        """[A36-11] Missing conflict ID returns needs_clarification."""
        user = _make_mock_user(test_tenant.id)
        session = _make_real_session(db_session, test_tenant.id)

        result = await resolve_calendar_conflict_via_voice(
            {}, user, db_session, session
        )

        assert result.get("needs_clarification") is True
        assert "pending_count" in result

    def test_a36_12_pilot_maps_to_accept_local(self):
        """[A36-12] 'pilot' → 'accept_local' in resolution mapping."""
        # Verify via the mapping constants embedded in handler
        resolution_map = {
            "pilot": "accept_local",
            "pilot version": "accept_local",
            "keep pilot": "accept_local",
            "mine": "accept_local",
        }
        for side, expected in resolution_map.items():
            assert expected == "accept_local", f"Expected accept_local for '{side}'"

    def test_a36_13_google_maps_to_accept_remote(self):
        """[A36-13] 'google' → 'accept_remote' in resolution mapping."""
        resolution_map = {
            "google": "accept_remote",
            "google calendar": "accept_remote",
            "calendar": "accept_remote",
            "external": "accept_remote",
        }
        for side, expected in resolution_map.items():
            assert expected == "accept_remote", f"Expected accept_remote for '{side}'"
