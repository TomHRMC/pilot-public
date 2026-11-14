"""
TP-B2 — Quote Approval Workflow & State Transitions — Test Endpoints

Coverage (one happy-path test per new /test endpoint minimum):
  1. POST /api/v1/quotes/{id}/submit-for-approval/test  → submit_quote_for_approval_test
  2. POST /api/v1/quotes/{id}/approve/test              → approve_quote_test
  3. POST /api/v1/quotes/{id}/reject/test               → reject_quote_test
  4. POST /api/v1/quotes/{id}/save-as-template/test     → save_quote_as_template_test
  5. POST /api/v1/quotes/{id}/apply-discount/test       → apply_quote_discount_test
  6. GET  /api/v1/quotes/{id}/comments/test             → get_quote_comments_test
  7. POST /api/v1/quotes/{id}/kickback/test             → kickback_quote_test
  8. POST /api/v1/quotes/{quote_id}/public-link/revoke/test → revoke_quote_public_link_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false for key endpoints
  - 404 for unknown quote IDs
  - State transition validation (422 for wrong status)
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import status
from sqlmodel import select

from app.models.crm import Customer, Site
from app.models.quoting import Quote, QuoteStatus, QuoteVersion
from core.config import settings

# ==================== CONSTANTS ====================

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


# ==================== HELPERS ====================


def _get_or_create_quote_status(
    db_session, tenant_id, code: str, is_default: bool = False
):
    """Get or create a QuoteStatus row for the given tenant and code."""
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


def _make_quote(db_session, tenant_id, customer_id, site_id, status_id):
    """Create a bare-minimum Quote row and return it."""
    q = Quote(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=status_id,
        currency="USD",
        subtotal_cents=10000,
        tax_cents=0,
        total_cents=10000,
        is_active=True,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def _make_version(db_session, tenant_id, quote_id, version_no=1):
    """Create a QuoteVersion snapshot for a quote."""
    v = QuoteVersion(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quote_id=quote_id,
        version_no=version_no,
        snapshot={},
        subtotal_cents=10000,
        tax_cents=0,
        total_cents=10000,
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


# ==================== FIXTURES ====================


@pytest.fixture
def quote_statuses(db_session, test_tenant):
    """Ensure all required quote statuses exist for the test tenant."""
    return {
        "draft": _get_or_create_quote_status(
            db_session, test_tenant.id, "draft", is_default=True
        ),
        "pending_approval": _get_or_create_quote_status(
            db_session, test_tenant.id, "pending_approval"
        ),
        "approved": _get_or_create_quote_status(db_session, test_tenant.id, "approved"),
        "rejected": _get_or_create_quote_status(db_session, test_tenant.id, "rejected"),
    }


@pytest.fixture
def test_customer_b2(db_session, test_tenant):
    """Create a test Customer."""
    c = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type="person",
        display_name=f"TP-B2 Customer {uuid.uuid4().hex[:6]}",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def test_site_b2(db_session, test_tenant, test_customer_b2):
    """Create a test Site."""
    s = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer_b2.id,
        address_line_1="456 Approval Ave",
        city="Approvetown",
        state="TX",
        postal_code="75002",
        country="US",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def draft_quote(
    db_session, test_tenant, test_customer_b2, test_site_b2, quote_statuses
):
    """A quote in 'draft' status with a version."""
    q = _make_quote(
        db_session,
        test_tenant.id,
        test_customer_b2.id,
        test_site_b2.id,
        quote_statuses["draft"].id,
    )
    _make_version(db_session, test_tenant.id, q.id)
    db_session.refresh(q)
    return q


@pytest.fixture
def pending_approval_quote(
    db_session, test_tenant, test_customer_b2, test_site_b2, quote_statuses
):
    """A quote already in 'pending_approval' status with a version."""
    q = _make_quote(
        db_session,
        test_tenant.id,
        test_customer_b2.id,
        test_site_b2.id,
        quote_statuses["pending_approval"].id,
    )
    q.submitted_by_user_id = TEST_USER_ID
    q.submitted_at = datetime.now(UTC)
    db_session.add(q)
    db_session.commit()
    _make_version(db_session, test_tenant.id, q.id)
    db_session.refresh(q)
    return q


# ==================== SECURITY GUARD TESTS ====================


class TestTpB2SecurityGuards:
    """Verify /test endpoints are blocked when disabled."""

    def test_submit_blocked_when_disabled(self, client, draft_quote):
        """POST submit-for-approval/test returns 403 when TEST_ENDPOINT_ENABLED=false."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{draft_quote.id}/submit-for-approval/test"
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_approve_blocked_in_production(self, client, pending_approval_quote):
        """POST approve/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(
                    f"/api/v1/quotes/{pending_approval_quote.id}/approve/test",
                    json={"expected_quote_version_id": None},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_comments_blocked_when_disabled(self, client, draft_quote):
        """GET comments/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"/api/v1/quotes/{draft_quote.id}/comments/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== SUBMIT FOR APPROVAL /test ====================


class TestTpB2SubmitForApproval:
    """Tests for POST /{id}/submit-for-approval/test."""

    def test_submit_draft_quote_transitions_to_pending(self, client, draft_quote):
        """Happy path: draft quote transitions to pending_approval."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{draft_quote.id}/submit-for-approval/test"
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quote_id"] == str(draft_quote.id)
        assert data["status"] == "pending_approval"
        assert data["submitted_by_user_id"] == str(TEST_USER_ID)
        assert "submitted_at" in data

    def test_submit_404_for_unknown_quote(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/submit-for-approval/test"
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_422_if_not_draft(self, client, pending_approval_quote):
        """Returns 422 if quote is not in draft status."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{pending_approval_quote.id}/submit-for-approval/test"
                )
        assert response.status_code == 422


# ==================== APPROVE /test ====================


class TestTpB2ApproveQuote:
    """Tests for POST /{id}/approve/test."""

    def test_approve_pending_quote(self, client, pending_approval_quote):
        """Happy path: pending_approval quote transitions to approved."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{pending_approval_quote.id}/approve/test",
                    json={},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quote_id"] == str(pending_approval_quote.id)
        assert data["status"] == "approved"
        assert data["approved_by_user_id"] == str(TEST_USER_ID)

    def test_approve_404_for_unknown_quote(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/approve/test", json={}
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_approve_422_if_not_pending(self, client, draft_quote):
        """Returns 422 if quote is not in pending_approval status."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{draft_quote.id}/approve/test", json={}
                )
        assert response.status_code == 422


# ==================== REJECT /test ====================


class TestTpB2RejectQuote:
    """Tests for POST /{id}/reject/test."""

    def test_reject_pending_quote(self, client, pending_approval_quote):
        """Happy path: pending_approval quote transitions to rejected."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{pending_approval_quote.id}/reject/test",
                    json={"overall_comment": "Prices are too high."},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quote_id"] == str(pending_approval_quote.id)
        assert data["status"] == "rejected"

    def test_reject_422_without_comment(self, client, pending_approval_quote):
        """Returns 422 if overall_comment is missing."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{pending_approval_quote.id}/reject/test",
                    json={},
                )
        assert response.status_code == 422

    def test_reject_404_for_unknown(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/reject/test",
                    json={"overall_comment": "nope"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== SAVE-AS-TEMPLATE /test ====================


class TestTpB2SaveAsTemplate:
    """Tests for POST /{id}/save-as-template/test."""

    def test_save_as_template_creates_template(self, client, draft_quote):
        """Happy path: saves quote as a reusable template."""
        template_name = f"TP-B2 Template {uuid.uuid4().hex[:6]}"
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{draft_quote.id}/save-as-template/test",
                    json={"name": template_name, "style": "component"},
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == template_name
        assert data["style"] == "component"
        assert "template_id" in data

    def test_save_as_template_404_for_unknown(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/save-as-template/test",
                    json={"name": "Won't Work", "style": "component"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== APPLY-DISCOUNT /test ====================


class TestTpB2ApplyDiscount:
    """Tests for POST /{id}/apply-discount/test."""

    def test_apply_discount_creates_version(self, client, draft_quote):
        """Happy path: applies discount and creates a new quote version."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{draft_quote.id}/apply-discount/test",
                    json={"discount_pct": "5.00"},
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["quote_id"] == str(draft_quote.id)
        assert "new_version_id" in data

    def test_apply_discount_404_for_unknown(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/apply-discount/test",
                    json={"discount_pct": "5.00"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== GET COMMENTS /test ====================


class TestTpB2GetComments:
    """Tests for GET /{id}/comments/test."""

    def test_get_comments_returns_empty_list(self, client, draft_quote):
        """Happy path: returns empty list for quote with no comments."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"/api/v1/quotes/{draft_quote.id}/comments/test")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_comments_404_for_unknown(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"/api/v1/quotes/{uuid.uuid4()}/comments/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== KICKBACK /test ====================


class TestTpB2KickbackQuote:
    """Tests for POST /{id}/kickback/test."""

    def test_kickback_pending_to_draft(self, client, pending_approval_quote):
        """Happy path: kicks quote back from pending_approval to draft."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{pending_approval_quote.id}/kickback/test",
                    json={"overall_comment": "Please revise line items."},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quote_id"] == str(pending_approval_quote.id)
        assert data["status"] == "draft"

    def test_kickback_422_no_comments(self, client, pending_approval_quote):
        """Returns 422 if neither overall_comment nor line_comments provided."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{pending_approval_quote.id}/kickback/test",
                    json={},
                )
        assert response.status_code == 422

    def test_kickback_404_for_unknown(self, client):
        """Returns 404 for unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/kickback/test",
                    json={"overall_comment": "nope"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== REVOKE PUBLIC LINK /test ====================


class TestTpB2RevokePublicLink:
    """Tests for POST /{quote_id}/public-link/revoke/test."""

    def test_revoke_404_no_active_link(self, client, draft_quote):
        """Returns 404 if no active public link exists for the quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{draft_quote.id}/public-link/revoke/test"
                )
        # No link exists — should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_404_for_unknown_quote(self, client):
        """Returns 404 for completely unknown quote."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{uuid.uuid4()}/public-link/revoke/test"
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_endpoint_reachable(self, client, draft_quote):
        """Verify endpoint is not blocked by auth or routing (not 403/405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/quotes/{draft_quote.id}/public-link/revoke/test"
                )
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
