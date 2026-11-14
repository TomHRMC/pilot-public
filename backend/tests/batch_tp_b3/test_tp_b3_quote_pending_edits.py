"""
TP-B3 — Quote Pending Edits — Test Endpoints

Coverage (one happy-path test per new /test endpoint minimum):
  1. GET    /api/v1/quotes/{id}/pending-edits/test             → list_pending_edits_test
  2. POST   /api/v1/quotes/{id}/pending-edits/test             → create_pending_edit_test
  3. PATCH  /api/v1/quotes/{id}/pending-edits/{edit_id}/test   → update_pending_edit_test
  4. DELETE /api/v1/quotes/{id}/pending-edits/test             → delete_all_pending_edits_test
  5. DELETE /api/v1/quotes/{id}/pending-edits/{edit_id}/test   → delete_pending_edit_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 404 for unknown quote or edit IDs
  - Route ordering: DELETE /test (all) is distinct from DELETE /{edit_id}/test (one)
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import status
from sqlmodel import select

from app.models.crm import Customer, Site
from app.models.quoting import Quote, QuotePendingEdit, QuoteStatus, QuoteVersion
from core.config import settings

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


# ==================== HELPERS ====================


def _get_or_create_quote_status(db_session, tenant_id, code, is_default=False):
    existing = db_session.exec(
        select(QuoteStatus).where(
            QuoteStatus.tenant_id == tenant_id,
            QuoteStatus.code == code,
        )
    ).first()
    if existing:
        return existing
    s = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=code.replace("_", " ").title(),
        is_default=is_default,
        is_active=True,
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


# ==================== FIXTURES ====================


@pytest.fixture
def b3_customer(db_session, test_tenant):
    c = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type="person",
        display_name=f"TP-B3 Customer {uuid.uuid4().hex[:6]}",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def b3_site(db_session, test_tenant, b3_customer):
    s = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=b3_customer.id,
        address_line_1="789 Edit St",
        city="Edittown",
        state="TX",
        postal_code="75003",
        country="US",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def b3_quote(db_session, test_tenant, b3_customer, b3_site):
    """A quote in pending_approval status with a version (required for creating pending edits)."""
    pending_status = _get_or_create_quote_status(
        db_session, test_tenant.id, "pending_approval"
    )
    q = Quote(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=b3_customer.id,
        site_id=b3_site.id,
        status_id=pending_status.id,
        currency="USD",
        subtotal_cents=10000,
        tax_cents=0,
        total_cents=10000,
        is_active=True,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)

    # Create a version (required for create_pending_edit)
    v = QuoteVersion(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=q.id,
        version_no=1,
        snapshot={},
        subtotal_cents=10000,
        tax_cents=0,
        total_cents=10000,
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(q)
    return q


@pytest.fixture
def b3_pending_edit(db_session, test_tenant, b3_quote):
    """A pre-existing pending edit for the test user on b3_quote."""
    # Fetch the version
    version = db_session.exec(
        select(QuoteVersion).where(QuoteVersion.quote_id == b3_quote.id)
    ).first()
    edit = QuotePendingEdit(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=b3_quote.id,
        quote_version_id=version.id,
        editor_user_id=TEST_USER_ID,
        edit_type="edit_notes",
        edit_payload={"note": "fix the description"},
        created_by=TEST_USER_ID,
        updated_by=TEST_USER_ID,
    )
    db_session.add(edit)
    db_session.commit()
    db_session.refresh(edit)
    return edit


# ==================== SECURITY GUARD TESTS ====================


class TestTpB3SecurityGuards:
    """Verify /test endpoints are blocked when disabled."""

    def test_list_pending_edits_blocked_when_disabled(self, client, b3_quote):
        """GET pending-edits/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_pending_edit_blocked_in_production(self, client, b3_quote):
        """POST pending-edits/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test",
                    json={"edit_type": "edit_notes", "edit_payload": {}},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== LIST PENDING EDITS /test ====================


class TestTpB3ListPendingEdits:
    """Tests for GET /{id}/pending-edits/test."""

    def test_list_returns_empty_for_new_quote(self, client, b3_quote):
        """Happy path: empty list for quote with no pending edits."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_returns_existing_edits(self, client, b3_quote, b3_pending_edit):
        """Happy path: returns existing pending edits for the test user."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
        assert response.status_code == status.HTTP_200_OK
        edits = response.json()
        assert len(edits) == 1
        assert edits[0]["id"] == str(b3_pending_edit.id)

    def test_list_404_for_unknown_quote(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/quotes/{uuid.uuid4()}/pending-edits/test"
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== CREATE PENDING EDIT /test ====================


class TestTpB3CreatePendingEdit:
    """Tests for POST /{id}/pending-edits/test."""

    def test_create_pending_edit_returns_201(self, client, b3_quote):
        """Happy path: creates a pending edit and returns 201."""
        payload = {
            "edit_type": "edit_notes",
            "edit_payload": {"note": "change material to aluminum"},
            "annotation": "Cost savings opportunity",
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test",
                    json=payload,
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["edit_type"] == "edit_notes"
        assert data["editor_user_id"] == str(TEST_USER_ID)
        assert "id" in data

    def test_create_invalid_edit_type_returns_422(self, client, b3_quote):
        """Returns 422 for invalid edit_type."""
        payload = {
            "edit_type": "invalid_type",
            "edit_payload": {},
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test",
                    json=payload,
                )
        assert response.status_code == 422

    def test_create_404_for_unknown_quote(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/pending-edits/test",
                    json={"edit_type": "edit_notes", "edit_payload": {}},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== UPDATE PENDING EDIT /test ====================


class TestTpB3UpdatePendingEdit:
    """Tests for PATCH /{id}/pending-edits/{edit_id}/test."""

    def test_update_pending_edit_returns_200(self, client, b3_quote, b3_pending_edit):
        """Happy path: updates annotation on a pending edit."""
        payload = {"annotation": "Updated annotation via test endpoint"}
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.patch(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/{b3_pending_edit.id}/test",
                    json=payload,
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["annotation"] == "Updated annotation via test endpoint"

    def test_update_404_for_unknown_edit(self, client, b3_quote):
        """Returns 404 for unknown edit ID."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.patch(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/{uuid.uuid4()}/test",
                    json={"annotation": "nope"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== DELETE ALL PENDING EDITS /test ====================


class TestTpB3DeleteAllPendingEdits:
    """Tests for DELETE /{id}/pending-edits/test (delete all)."""

    def test_delete_all_returns_count(self, client, b3_quote, b3_pending_edit):
        """Happy path: deletes all edits and returns count."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.delete(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deleted_count"] == 1

    def test_delete_all_returns_zero_when_empty(self, client, b3_quote):
        """Returns deleted_count=0 when no edits exist."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.delete(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["deleted_count"] == 0

    def test_delete_all_no_longer_listed(self, client, b3_quote, b3_pending_edit):
        """After delete-all, list returns empty."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                client.delete(f"/api/v1/quotes/{b3_quote.id}/pending-edits/test")
                list_resp = client.get(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.json() == []


# ==================== DELETE SINGLE PENDING EDIT /test ====================


class TestTpB3DeletePendingEdit:
    """Tests for DELETE /{id}/pending-edits/{edit_id}/test (delete one)."""

    def test_delete_single_edit_returns_deleted_true(
        self, client, b3_quote, b3_pending_edit
    ):
        """Happy path: deletes a single edit."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.delete(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/{b3_pending_edit.id}/test"
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["deleted"] is True

    def test_delete_single_no_longer_in_list(self, client, b3_quote, b3_pending_edit):
        """After deleting one edit, it no longer appears in the list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                client.delete(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/{b3_pending_edit.id}/test"
                )
                list_resp = client.get(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
        assert list_resp.status_code == status.HTTP_200_OK
        ids = [e["id"] for e in list_resp.json()]
        assert str(b3_pending_edit.id) not in ids

    def test_delete_single_404_for_unknown_edit(self, client, b3_quote):
        """Returns 404 for unknown edit ID."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.delete(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/{uuid.uuid4()}/test"
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_route_ordering_delete_all_vs_single(self, client, b3_quote):
        """Verify DELETE /pending-edits/test (all) and DELETE /pending-edits/{id}/test (one) are distinct."""
        fake_edit_id = uuid.uuid4()
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # delete-all endpoint (no edit_id)
                resp_all = client.delete(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/test"
                )
                # delete-one endpoint (with edit_id)
                resp_one = client.delete(
                    f"/api/v1/quotes/{b3_quote.id}/pending-edits/{fake_edit_id}/test"
                )
        # Both must be reachable
        assert resp_all.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
        assert resp_one.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
        # delete-all returns deleted_count; delete-one with unknown ID returns 404
        assert "deleted_count" in resp_all.json()
        assert resp_one.status_code == status.HTTP_404_NOT_FOUND
