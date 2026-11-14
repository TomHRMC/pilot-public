"""
tests/batch_b7b/test_a45_tech_conflict_endpoints.py

Tests for B7b/A45 — Tech-Resolvable Conflict UI Endpoints.

Test focus cases (per design doc):
  1. resolution_action column exists on mobile_sync_event with correct properties
  2. CHECK constraint enforces valid resolution_action values
  3. NULL resolution_action is allowed (pre-B7b rows / non-resolution rows)
  4. _get_conflict_detail_impl returns ConflictDetailResponse for a conflict event
  5. _resolve_conflict_impl inserts resolved event with correct resolution_action
  6. _resolve_conflict_impl creates MobileSyncOwnerEscalation for escalate_to_owner
  7. _resolve_conflict_impl raises ValueError/404 for unknown conflict_id
  8. mobile_sync.resolve and mobile_sync.view permissions exist in platform_role
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.sync import MobileSyncEvent
from app.models.system import MobileSyncOwnerEscalation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conflict_event(
    db_session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> MobileSyncEvent:
    """Create a MobileSyncEvent with status='conflict' for A45 testing."""
    event = MobileSyncEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        device_id="test-device",
        operation_type="time_entry",
        operation_payload_summary={"job_id": str(uuid.uuid4()), "hours": 3.5},
        status="conflict",
        conflict_severity="tech_resolvable",
        client_capture_at=datetime.now(UTC),
        idempotency_uuid=uuid.uuid4(),
        error_detail={"trigger_condition": "job_reassigned"},
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


# ---------------------------------------------------------------------------
# ORM column verification
# ---------------------------------------------------------------------------


class TestResolutionActionColumn:
    def test_resolution_action_column_exists(self, db_session):
        """resolution_action column exists on mobile_sync_event, text, nullable."""
        row = db_session.execute(
            text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'mobile_sync_event'
            AND column_name = 'resolution_action'
        """)
        ).fetchone()
        assert row is not None, "resolution_action column must exist"
        assert row[1] == "text"
        assert row[2] == "YES"

    def test_resolution_action_null_allowed(self, db_session, test_user, test_tenant):
        """NULL resolution_action is allowed (non-resolution rows)."""
        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        assert event.resolution_action is None

    def test_resolution_action_can_be_set(self, db_session, test_user, test_tenant):
        """resolution_action = 'use_local' is stored correctly."""
        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        # Use raw insert of a new row with resolution_action set
        resolution_event = MobileSyncEvent(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            device_id="test-device",
            operation_type="time_entry",
            operation_payload_summary={"job_id": str(uuid.uuid4())},
            status="succeeded",
            conflict_severity="tech_resolvable",
            client_capture_at=datetime.now(UTC),
            idempotency_uuid=uuid.uuid4(),
            resolution_action="use_local",
        )
        db_session.add(resolution_event)
        db_session.commit()
        db_session.refresh(resolution_event)
        assert resolution_event.resolution_action == "use_local"

    def test_check_constraint_enforces_valid_values(
        self, db_session, test_user, test_tenant
    ):
        """CHECK constraint rejects invalid resolution_action values."""
        from sqlalchemy.exc import IntegrityError

        bad_event = MobileSyncEvent(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            device_id="test-device",
            operation_type="time_entry",
            operation_payload_summary={},
            status="succeeded",
            client_capture_at=datetime.now(UTC),
            idempotency_uuid=uuid.uuid4(),
            resolution_action="invalid_resolution_value",
        )
        db_session.add(bad_event)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


# ---------------------------------------------------------------------------
# _get_conflict_detail_impl
# ---------------------------------------------------------------------------


class TestGetConflictDetailImpl:
    def test_returns_conflict_detail(self, db_session, test_user, test_tenant):
        """_get_conflict_detail_impl returns ConflictDetailResponse."""
        from api.routes.mobile_sync import _get_conflict_detail_impl
        from core.test_context import get_test_context

        # test_tenant.id / test_user.id match get_test_context() seeded UUIDs
        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        test_context = get_test_context()

        result = _get_conflict_detail_impl(event.id, db_session, test_context)

        assert result.conflict_id == event.id
        assert result.operation_type == "time_entry"
        assert result.status == "conflict"

    def test_raises_404_for_unknown_conflict(self, db_session, test_tenant):
        """_get_conflict_detail_impl raises 404 for unknown conflict_id."""
        from fastapi import HTTPException

        from api.routes.mobile_sync import _get_conflict_detail_impl
        from core.test_context import get_test_context

        test_context = get_test_context()

        with pytest.raises(HTTPException) as exc_info:
            _get_conflict_detail_impl(uuid.uuid4(), db_session, test_context)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# _resolve_conflict_impl
# ---------------------------------------------------------------------------


class TestResolveConflictImpl:
    def test_use_local_inserts_succeeded_event(
        self, db_session, test_user, test_tenant
    ):
        """use_local resolution inserts a new row with status='succeeded'."""
        from api.routes.mobile_sync import (
            ConflictResolveRequest,
            _resolve_conflict_impl,
        )
        from core.test_context import get_test_context

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        test_context = get_test_context()

        request = ConflictResolveRequest(resolution="use_local")
        result = _resolve_conflict_impl(event.id, request, db_session, test_context)

        assert result.resolution == "use_local"
        assert result.resolved_at is not None
        assert result.escalation_id is None

        # Verify new row was inserted
        resolved = db_session.exec(
            select(MobileSyncEvent)
            .where(MobileSyncEvent.resolution_action == "use_local")
            .where(MobileSyncEvent.tenant_id == test_tenant.id)
        ).first()
        assert resolved is not None
        assert resolved.status == "succeeded"

    def test_escalate_to_owner_creates_escalation(
        self, db_session, test_user, test_tenant
    ):
        """escalate_to_owner resolution creates a MobileSyncOwnerEscalation row."""
        from api.routes.mobile_sync import (
            ConflictResolveRequest,
            _resolve_conflict_impl,
        )
        from core.test_context import get_test_context

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        test_context = get_test_context()

        request = ConflictResolveRequest(resolution="escalate_to_owner")
        result = _resolve_conflict_impl(event.id, request, db_session, test_context)

        assert result.escalation_id is not None

        escalation = db_session.exec(
            select(MobileSyncOwnerEscalation).where(
                MobileSyncOwnerEscalation.conflict_id == event.id
            )
        ).first()
        assert escalation is not None
        assert escalation.status == "pending"
        assert escalation.escalation_reason == "tech_chose"

    def test_raises_404_for_unknown_conflict(self, db_session):
        """_resolve_conflict_impl raises 404 for unknown conflict_id."""
        from fastapi import HTTPException

        from api.routes.mobile_sync import (
            ConflictResolveRequest,
            _resolve_conflict_impl,
        )
        from core.test_context import get_test_context

        test_context = get_test_context()

        request = ConflictResolveRequest(resolution="use_local")
        with pytest.raises(HTTPException) as exc_info:
            _resolve_conflict_impl(uuid.uuid4(), request, db_session, test_context)
        assert exc_info.value.status_code == 404
