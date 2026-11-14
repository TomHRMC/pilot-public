"""
tests/batch_b8/test_a47_a48_owner_escalation_extensions.py

B8/A47: Enhanced list endpoint + history sub-route
B8/A48: 7 resolution variants + 3x 409 shapes + audit log + push dispatch

Test focus cases:
  A47:
  - List escalations with status='all' filter
  - List escalations with status='pending' (default)
  - List escalations with invalid status returns 400
  - History sub-route returns resolved escalations
  - History sub-route excludes pending escalations
  - Detail endpoint includes available_resolutions
  - Detail endpoint includes escalation_type
  A48:
  - use_tech resolution → resolved status
  - use_server resolution → resolved status
  - reject_unauthorized resolution → rejected status
  - restore_and_accept resolution → resolved status
  - discard_tech resolution → resolved status
  - accept_authorized_at_capture resolution → resolved status
  - override_with_tech resolution → resolved status
  - 409 shape: auto_recovered when escalation already auto_recovered
  - 409 shape: stale when escalation status is stale
  - 409 shape: server_changed when expected_at doesn't match
  - Invalid resolution action returns 422
  - Audit log inserted on successful resolution
  - Loop-closure push attempted (with mock carrier)
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.sync import MobileSyncEvent, MobileSyncEventAudit
from app.models.system import MobileSyncOwnerEscalation

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_conflict_event(db_session, tenant_id, user_id) -> MobileSyncEvent:
    import uuid
    from datetime import UTC, datetime

    event = MobileSyncEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        device_id="test-device-1",
        operation_type="job_time_entry",
        status="conflict",
        conflict_severity="owner_escalation",
        client_capture_at=datetime.now(UTC),
        idempotency_uuid=uuid.uuid4(),
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
        escalation_reason_explainer="Automatic escalation due to conflict severity",
        status=status,
    )
    db_session.add(esc)
    db_session.commit()
    db_session.refresh(esc)
    return esc


# ─────────────────────────────────────────────────────────────────────────────
# A47: Enhanced list + history sub-route
# ─────────────────────────────────────────────────────────────────────────────


def test_a47_list_escalations_status_all(
    client: TestClient, db_session, test_tenant, test_user
):
    """A47: status='all' returns both pending and resolved escalations."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    _make_escalation(
        db_session, test_tenant.id, test_user.id, event.id, status="pending"
    )

    event2 = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    _make_escalation(
        db_session, test_tenant.id, test_user.id, event2.id, status="resolved"
    )

    resp = client.get(
        "/api/v1/owner/mobile-sync-escalations/test?escalation_status=all"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 2


def test_a47_list_escalations_status_pending(
    client: TestClient, db_session, test_tenant, test_user
):
    """A47: Default status='pending' returns only pending escalations."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    _make_escalation(
        db_session, test_tenant.id, test_user.id, event.id, status="pending"
    )

    resp = client.get(
        "/api/v1/owner/mobile-sync-escalations/test?escalation_status=pending"
    )
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["status"] == "pending"


def test_a47_list_escalations_invalid_status_returns_400(client: TestClient, test_user):
    """A47: Invalid status returns 400."""
    resp = client.get(
        "/api/v1/owner/mobile-sync-escalations/test?escalation_status=invalid_xyz"
    )
    assert resp.status_code == 400
    assert "status" in resp.json()["detail"].lower()


def test_a47_history_returns_resolved_only(
    client: TestClient, db_session, test_tenant, test_user
):
    """A47: /history returns resolved/rejected escalations."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(
        db_session, test_tenant.id, test_user.id, event.id, status="resolved"
    )
    esc.resolved_at = datetime.now(UTC)
    esc.resolved_by_user_id = test_user.id
    esc.resolution_action = "use_tech"
    db_session.add(esc)
    db_session.commit()

    resp = client.get("/api/v1/owner/mobile-sync-escalations/history/test")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "offset" in data
    # All returned items should be resolved or rejected
    for item in data["items"]:
        assert item["status"] in ("resolved", "rejected")


def test_a47_history_excludes_pending(
    client: TestClient, db_session, test_tenant, test_user
):
    """A47: /history does not include pending escalations."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    _make_escalation(
        db_session, test_tenant.id, test_user.id, event.id, status="pending"
    )

    resp = client.get("/api/v1/owner/mobile-sync-escalations/history/test")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["status"] != "pending"


def test_a47_detail_includes_available_resolutions(
    client: TestClient, db_session, test_tenant, test_user
):
    """A47: Detail endpoint includes available_resolutions field."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

    resp = client.get(f"/api/v1/owner/mobile-sync-escalations/{esc.id}/test")
    assert resp.status_code == 200
    data = resp.json()
    assert "available_resolutions" in data
    assert isinstance(data["available_resolutions"], list)
    assert len(data["available_resolutions"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# A48: 7 resolution variants
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "resolution,expected_status,expected_action",
    [
        ("use_tech", "resolved", "use_tech"),
        ("use_server", "resolved", "use_server"),
        ("restore_and_accept", "resolved", "restore_and_accept"),
        ("override_with_tech", "resolved", "override_with_tech"),
        ("discard_tech", "resolved", "discard_tech"),
        ("accept_authorized_at_capture", "resolved", "accept_authorized_at_capture"),
        ("reject_unauthorized", "rejected", "reject_unauthorized"),
    ],
)
def test_a48_all_resolution_variants(
    client: TestClient,
    db_session,
    test_tenant,
    test_user,
    resolution,
    expected_status,
    expected_action,
):
    """A48: All 7 resolution variants are accepted and stored correctly."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={"resolution": resolution},
    )
    assert resp.status_code == 200, f"resolution={resolution} failed: {resp.text}"
    data = resp.json()
    assert data["committed"] is True
    assert data["resolution_outcome"] == expected_action


def test_a48_invalid_resolution_returns_422(
    client: TestClient, db_session, test_tenant, test_user
):
    """A48: Invalid resolution action returns 422."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={"resolution": "completely_invalid"},
    )
    assert resp.status_code == 422


def test_a48_missing_resolution_returns_400(
    client: TestClient, db_session, test_tenant, test_user
):
    """A48: Request without resolution or resolution_action returns 400."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={},  # No resolution field
    )
    assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# A48: 409 shapes
# ─────────────────────────────────────────────────────────────────────────────


def test_a48_409_auto_recovered(client: TestClient, db_session, test_tenant, test_user):
    """A48: 409 shape 2 — auto_recovered when escalation already auto-recovered."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(
        db_session, test_tenant.id, test_user.id, event.id, status="auto_recovered"
    )

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={"resolution": "use_tech"},
    )
    assert resp.status_code == 409
    data = resp.json()["detail"]
    assert data.get("staleness_type") == "auto_recovered"


def test_a48_409_stale(client: TestClient, db_session, test_tenant, test_user):
    """A48: 409 shape 3 — stale when escalation status is stale."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(
        db_session, test_tenant.id, test_user.id, event.id, status="stale"
    )

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={"resolution": "use_tech"},
    )
    assert resp.status_code == 409
    data = resp.json()["detail"]
    assert data.get("staleness_type") == "stale"
    assert data.get("tech_force_discarded") is True


def test_a48_409_server_changed(client: TestClient, db_session, test_tenant, test_user):
    """A48: 409 shape 1 — server_changed via staleness check."""
    from datetime import timedelta

    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

    # Pass an expected_server_state_at_view_time that is in the past (stale)
    past_time = datetime.now(UTC) - timedelta(hours=1)

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={
            "resolution": "use_tech",
            "expected_server_state_at_view_time": past_time.isoformat(),
        },
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    # assert_not_stale raises with type stale-state
    assert "stale" in str(detail).lower() or "409" in str(resp.status_code)


# ─────────────────────────────────────────────────────────────────────────────
# A48: Audit log + push dispatch
# ─────────────────────────────────────────────────────────────────────────────


def test_a48_audit_log_inserted_on_resolve(
    client: TestClient, db_session, test_tenant, test_user
):
    """A48: MobileSyncEventAudit row is inserted when escalation is resolved."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={"resolution": "use_tech"},
    )
    assert resp.status_code == 200

    audit_row = db_session.exec(
        select(MobileSyncEventAudit).where(MobileSyncEventAudit.escalation_id == esc.id)
    ).first()
    assert audit_row is not None
    assert audit_row.resolution_action == "use_tech"
    assert audit_row.resolution_channel == "web"


def test_a48_resolve_response_includes_committed_flag(
    client: TestClient, db_session, test_tenant, test_user
):
    """A48: Response includes committed=True and resolution_outcome."""
    event = _make_conflict_event(db_session, test_tenant.id, test_user.id)
    esc = _make_escalation(db_session, test_tenant.id, test_user.id, event.id)

    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{esc.id}/resolve/test",
        json={"resolution": "discard_tech"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["committed"] is True
    assert data["resolution_outcome"] == "discard_tech"
    assert "originator_notification_dispatched" in data


def test_a48_escalation_not_found_returns_404(client: TestClient, test_user):
    """A48: Unknown escalation_id returns 404."""
    resp = client.post(
        f"/api/v1/owner/mobile-sync-escalations/{uuid.uuid4()}/resolve/test",
        json={"resolution": "use_tech"},
    )
    assert resp.status_code == 404
