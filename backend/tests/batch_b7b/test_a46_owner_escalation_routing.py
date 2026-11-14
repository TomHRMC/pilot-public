"""
tests/batch_b7b/test_a46_owner_escalation_routing.py

Tests for B7b/A46 — Owner Escalation Routing & Notification.

Test focus cases (per design doc):
  1. mobile_sync_owner_escalation table exists with correct columns
  2. status CHECK constraint enforces valid values
  3. escalation_reason CHECK constraint enforces valid values
  4. resolution_action CHECK constraint enforces valid values
  5. _list_escalations_impl returns escalation rows filtered by status
  6. _get_escalation_detail_impl returns correct escalation detail
  7. _resolve_escalation_impl updates escalation to 'resolved' with resolution_action
  8. A45 deferred test: escalate_to_owner creates MobileSyncOwnerEscalation row
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


def _make_conflict_event(db_session, tenant_id, user_id) -> MobileSyncEvent:
    event = MobileSyncEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        device_id="test-device",
        operation_type="time_entry",
        operation_payload_summary={"job_id": str(uuid.uuid4())},
        status="conflict",
        conflict_severity="owner_escalation",
        client_capture_at=datetime.now(UTC),
        idempotency_uuid=uuid.uuid4(),
        error_detail={"trigger_condition": "job_deleted"},
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def _make_escalation(
    db_session, tenant_id, user_id, conflict_id, status="pending"
) -> MobileSyncOwnerEscalation:
    esc = MobileSyncOwnerEscalation(
        tenant_id=tenant_id,
        originating_user_id=user_id,
        conflict_id=conflict_id,
        escalation_reason="auto_severity",
        escalation_reason_explainer="Job deleted while tech was working it",
        status=status,
    )
    db_session.add(esc)
    db_session.commit()
    db_session.refresh(esc)
    return esc


# ---------------------------------------------------------------------------
# Table column / constraint verification
# ---------------------------------------------------------------------------


class TestMobileSyncOwnerEscalationSchema:
    def _column(self, db_session, col: str):
        return db_session.execute(
            text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'mobile_sync_owner_escalation'
            AND column_name = :col
        """),
            {"col": col},
        ).fetchone()

    def test_id_column_exists(self, db_session):
        row = self._column(db_session, "id")
        assert row is not None
        assert row[1] == "uuid"
        assert row[2] == "NO"

    def test_status_column_exists_not_null(self, db_session):
        row = self._column(db_session, "status")
        assert row is not None
        assert row[2] == "NO"

    def test_escalation_reason_column_exists(self, db_session):
        row = self._column(db_session, "escalation_reason")
        assert row is not None

    def test_conflict_id_column_exists(self, db_session):
        row = self._column(db_session, "conflict_id")
        assert row is not None
        assert row[1] == "uuid"

    def test_resolution_action_is_nullable(self, db_session):
        row = self._column(db_session, "resolution_action")
        assert row is not None
        assert row[2] == "YES"

    def test_status_check_constraint_rejects_invalid(
        self, db_session, test_user, test_tenant
    ):
        """CHECK constraint rejects invalid status."""
        from sqlalchemy.exc import IntegrityError

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        bad = MobileSyncOwnerEscalation(
            tenant_id=test_tenant.id,
            originating_user_id=test_user.id,
            conflict_id=event.id,
            escalation_reason="auto_severity",
            escalation_reason_explainer="test",
            status="invalid_status_value",
        )
        db_session.add(bad)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_valid_pending_status(self, db_session, test_user, test_tenant):
        """'pending' is a valid status."""
        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        esc = _make_escalation(
            db_session, test_tenant.id, test_user.id, event.id, "pending"
        )
        assert esc.status == "pending"


# ---------------------------------------------------------------------------
# _list_escalations_impl
# ---------------------------------------------------------------------------


class TestListEscalationsImpl:
    def test_lists_pending_escalations(self, db_session, test_user, test_tenant):
        """_list_escalations_impl returns pending escalations for the tenant."""
        from api.routes.owner_escalations import _list_escalations_impl
        from core.test_context import get_test_context

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        _make_escalation(db_session, test_tenant.id, test_user.id, event.id, "pending")

        test_context = get_test_context()
        result = _list_escalations_impl(
            db_session, test_context, escalation_status="pending"
        )

        assert isinstance(result.items, list)
        assert isinstance(result.total_pending, int)

    def test_resolved_escalations_excluded_from_pending_list(
        self, db_session, test_user, test_tenant
    ):
        """Resolved escalations do not appear in pending list."""
        from api.routes.owner_escalations import _list_escalations_impl
        from core.test_context import get_test_context

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        esc = _make_escalation(
            db_session, test_tenant.id, test_user.id, event.id, "resolved"
        )

        test_context = get_test_context()
        result = _list_escalations_impl(
            db_session, test_context, escalation_status="pending"
        )

        ids = [item.id for item in result.items]
        assert esc.id not in ids


# ---------------------------------------------------------------------------
# _get_escalation_detail_impl
# ---------------------------------------------------------------------------


class TestGetEscalationDetailImpl:
    def test_returns_escalation_detail(self, db_session, test_user, test_tenant):
        """_get_escalation_detail_impl returns escalation detail."""
        from api.routes.owner_escalations import _get_escalation_detail_impl
        from core.test_context import get_test_context

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

        test_context = get_test_context()
        result = _get_escalation_detail_impl(esc.id, db_session, test_context)

        assert result.id == esc.id
        assert result.escalation_reason == "auto_severity"
        assert result.status == "pending"

    def test_raises_404_for_unknown_escalation(self, db_session):
        """_get_escalation_detail_impl raises 404 for unknown escalation_id."""
        from fastapi import HTTPException

        from api.routes.owner_escalations import _get_escalation_detail_impl
        from core.test_context import get_test_context

        test_context = get_test_context()
        with pytest.raises(HTTPException) as exc_info:
            _get_escalation_detail_impl(uuid.uuid4(), db_session, test_context)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# _resolve_escalation_impl
# ---------------------------------------------------------------------------


class TestResolveEscalationImpl:
    def test_resolves_escalation_with_used_local(
        self, db_session, test_user, test_tenant
    ):
        """_resolve_escalation_impl marks escalation as 'resolved' with used_local."""
        from api.routes.owner_escalations import (
            EscalationResolveRequest,
            _resolve_escalation_impl,
        )
        from core.test_context import get_test_context

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

        test_context = get_test_context()
        # B8/F.6: used_local → use_tech (canonical A48 name)
        request = EscalationResolveRequest(resolution_action="used_local")
        result = _resolve_escalation_impl(esc.id, request, db_session, test_context)

        assert result.status == "resolved"
        # B8: used_local is mapped to canonical use_tech
        assert result.resolution_action == "use_tech"
        assert result.resolved_at is not None
        assert result.resolved_by_user_id is not None

    def test_rejected_resolution_sets_rejected_status(
        self, db_session, test_user, test_tenant
    ):
        """resolution_action='rejected' sets status='rejected'. B8: mapped to reject_unauthorized."""
        from api.routes.owner_escalations import (
            EscalationResolveRequest,
            _resolve_escalation_impl,
        )
        from core.test_context import get_test_context

        event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
        esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

        test_context = get_test_context()
        # B8/F.6: rejected → reject_unauthorized (canonical A48 name)
        request = EscalationResolveRequest(resolution_action="rejected")
        result = _resolve_escalation_impl(esc.id, request, db_session, test_context)

        assert result.status == "rejected"
        # B8: rejected is mapped to canonical reject_unauthorized
        assert result.resolution_action == "reject_unauthorized"


# ---------------------------------------------------------------------------
# A45 deferred test: escalate_to_owner creates escalation (now table exists)
# ---------------------------------------------------------------------------


class TestA45DeferredEscalateToOwner:
    def test_escalate_to_owner_creates_escalation_row(
        self, db_session, test_user, test_tenant
    ):
        """
        A45 deferred: _resolve_conflict_impl with escalate_to_owner creates
        a MobileSyncOwnerEscalation row (requires mobile_sync_owner_escalation table).
        """
        from api.routes.mobile_sync import (
            ConflictResolveRequest,
            _resolve_conflict_impl,
        )
        from core.test_context import get_test_context

        # Create conflict event using test_tenant/test_user (match test_context)
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
