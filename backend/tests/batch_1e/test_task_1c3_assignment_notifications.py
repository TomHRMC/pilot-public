"""
Task 1-C-3: Assignment Notifications — Test Suite

Verifies that ``_assign_tech_impl`` inserts a ``notification_outbox`` record
whenever a technician is assigned to a job by someone other than themselves.

Transaction isolation strategy:
  The ``client`` fixture (from conftest.py) overrides ``get_db`` to inject the
  same ``db_session`` used by the test.  This means User rows inserted into
  ``db_session`` before the HTTP call ARE visible inside the route handler,
  because both live in the same postgres transaction (rolled back after each test).

Strategy for triggering "assigner ≠ tech":
  - Assigner = _TEST_USER_ID (the seeded test context user set by TestUserContext).
  - Tech      = a new User row inserted directly via ``db_session`` in each test.
    The two UUIDs differ → ``_emit_job_assigned_notification`` fires.

Coverage:
  1. Third-party assignment → exactly one ``in_app`` NotificationOutbox created
  2. Notification has correct channel, status, and recipient_user_id
  3. Notification body references the job_id
  4. Self-assignment (_TEST_USER_ID assigns themselves) → NO notification
  5. Re-assignment (upsert primary) → exactly one notification for the new tech
  6. Helper role assignment → notification still created
  7. NotificationEvent FK wired correctly to the outbox row
"""

import uuid

from sqlmodel import Session, select

from app.models.core import User
from app.models.system import NotificationEvent, NotificationOutbox

SCHED_BASE = "/api/v1/scheduling"
JOBS_BASE = "/api/v1/jobs"
CUST_BASE = "/api/v1/customers"
SITES_BASE = "/api/v1/sites"

_TEST_USER_ID = "00000000-0000-0000-0000-000000000002"
_TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# DB helpers (use db_session so they're visible to the HTTP call)
# ---------------------------------------------------------------------------


def _make_tech_user(db_session: Session) -> User:
    """Insert a User row in the shared transaction and return it."""
    user = User(
        id=uuid.uuid4(),
        email=f"tech-{uuid.uuid4().hex[:8]}@test.pilotfortrades.com",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_job(client) -> str:
    cust = client.post(
        f"{CUST_BASE}/test",
        json={
            "display_name": f"Notif Customer {uuid.uuid4().hex[:6]}",
            "type": "person",
        },
    )
    assert cust.status_code == 201, cust.text
    site = client.post(f"{SITES_BASE}/test", json={"customer_id": cust.json()["id"]})
    assert site.status_code == 201, site.text
    job = client.post(
        f"{JOBS_BASE}/test",
        json={"customer_id": cust.json()["id"], "site_id": site.json()["id"]},
    )
    assert job.status_code == 201, job.text
    return job.json()["id"]


def _assign(client, job_id: str, user_id: str, role: str = "primary") -> dict:
    """POST to the /test assignment endpoint.

    The TestUserContext sets ``assigned_by_user_id`` to _TEST_USER_ID when no
    explicit ``assigned_by_user_id`` is passed in the payload.
    """
    payload: dict = {"user_id": user_id, "role": role, "ordinal": 1}
    resp = client.post(f"{SCHED_BASE}/jobs/{job_id}/assignments/test", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _pending_inapp_outbox(db_session: Session, tech_user_id: uuid.UUID) -> list:
    stmt = (
        select(NotificationOutbox)
        .where(NotificationOutbox.tenant_id == uuid.UUID(_TEST_TENANT_ID))
        .where(NotificationOutbox.recipient_user_id == tech_user_id)
        .where(NotificationOutbox.channel == "in_app")
        .where(NotificationOutbox.status == "pending")
    )
    return db_session.exec(stmt).all()


# ---------------------------------------------------------------------------
# Tests: third-party assignment emits notification
# ---------------------------------------------------------------------------


class TestThirdPartyAssignment:
    def test_outbox_created_on_third_party_assignment(self, db_session, client):
        """Assigner (_TEST_USER_ID) ≠ tech → one in_app outbox row inserted."""
        tech = _make_tech_user(db_session)
        job_id = _create_job(client)

        before = _pending_inapp_outbox(db_session, tech.id)

        _assign(client, job_id, str(tech.id))

        after = _pending_inapp_outbox(db_session, tech.id)
        assert len(after) == len(before) + 1, (
            f"Expected +1 outbox row; before={len(before)}, after={len(after)}"
        )

    def test_outbox_channel_and_status(self, db_session, client):
        """Emitted outbox row must be in_app / pending."""
        tech = _make_tech_user(db_session)
        job_id = _create_job(client)

        _assign(client, job_id, str(tech.id))

        rows = _pending_inapp_outbox(db_session, tech.id)
        assert len(rows) >= 1
        latest = max(rows, key=lambda r: r.created_at)
        assert latest.channel == "in_app"
        assert latest.status == "pending"
        assert latest.recipient_user_id == tech.id

    def test_outbox_body_mentions_job(self, db_session, client):
        """Notification body must contain the job id."""
        tech = _make_tech_user(db_session)
        job_id = _create_job(client)

        _assign(client, job_id, str(tech.id))

        rows = _pending_inapp_outbox(db_session, tech.id)
        assert len(rows) >= 1
        latest = max(rows, key=lambda r: r.created_at)
        assert job_id in latest.body


# ---------------------------------------------------------------------------
# Tests: self-assignment → NO notification
# ---------------------------------------------------------------------------


class TestSelfAssignment:
    def test_self_assignment_no_outbox(self, db_session, client):
        """_TEST_USER_ID assigns themselves → assigner == tech → no notification."""
        job_id = _create_job(client)
        before = _pending_inapp_outbox(db_session, uuid.UUID(_TEST_USER_ID))

        _assign(client, job_id, _TEST_USER_ID)

        after = _pending_inapp_outbox(db_session, uuid.UUID(_TEST_USER_ID))
        assert len(after) == len(before), (
            "Self-assignment must NOT create a NotificationOutbox row"
        )


# ---------------------------------------------------------------------------
# Tests: re-assignment (upsert primary) emits exactly one new notification
# ---------------------------------------------------------------------------


class TestReassignment:
    def test_reassignment_emits_one_notification(self, db_session, client):
        """Upsert primary: old self-assignment replaced, new tech gets notification."""
        tech = _make_tech_user(db_session)
        job_id = _create_job(client)

        # First self-assign (no notification expected)
        _assign(client, job_id, _TEST_USER_ID)

        before = _pending_inapp_outbox(db_session, tech.id)

        # Assign the new tech (assigner = _TEST_USER_ID ≠ tech)
        _assign(client, job_id, str(tech.id))

        after = _pending_inapp_outbox(db_session, tech.id)
        assert len(after) == len(before) + 1


# ---------------------------------------------------------------------------
# Tests: helper role also triggers notification
# ---------------------------------------------------------------------------


class TestHelperRoleNotification:
    def test_helper_assignment_emits_notification(self, db_session, client):
        """Helper role from a different assigner also creates an outbox row."""
        tech = _make_tech_user(db_session)
        job_id = _create_job(client)

        before = _pending_inapp_outbox(db_session, tech.id)

        _assign(client, job_id, str(tech.id), role="helper")

        after = _pending_inapp_outbox(db_session, tech.id)
        assert len(after) == len(before) + 1


# ---------------------------------------------------------------------------
# Tests: NotificationEvent FK wired to NotificationOutbox
# ---------------------------------------------------------------------------


class TestNotificationEventWiring:
    def test_notification_event_linked_to_outbox(self, db_session, client):
        """Each outbox row must reference a NotificationEvent with correct fields."""
        tech = _make_tech_user(db_session)
        job_id = _create_job(client)

        _assign(client, job_id, str(tech.id))

        rows = _pending_inapp_outbox(db_session, tech.id)
        assert len(rows) >= 1

        latest = max(rows, key=lambda r: r.created_at)
        event = db_session.get(NotificationEvent, latest.notification_event_id)
        assert event is not None
        assert event.notification_type_code == "job_assigned"
        assert event.entity_type_code == "job"
        assert event.entity_id == job_id
