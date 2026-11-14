"""
TP-B4 — Quote Templates (A25) — Test Endpoints

Coverage (one happy-path test per new /test endpoint minimum):
  1. GET  /api/v1/quote-templates/test                           → list_quote_templates_test
  2. POST /api/v1/quote-templates/test                           → create_quote_template_test
  3. POST /api/v1/quote-templates/{id}/fork/test                 → fork_quote_template_test
  4. POST /api/v1/quote-templates/{id}/disable/test              → disable_quote_template_test
  5. POST /api/v1/quote-templates/from-template/{template_id}/test → create_quote_from_template_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 404 for unknown template / customer / site IDs
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import status
from sqlmodel import select

from app.models.crm import Customer, Site
from app.models.quoting import (
    QcoLineType,
    QuoteTemplate,
)
from core.config import settings

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

BASE = "/api/v1/quote-templates"


# ==================== FIXTURES ====================


@pytest.fixture
def b4_qco_line_type(db_session, test_tenant):
    """Get or create a QcoLineType for the test tenant."""
    existing = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.tenant_id == test_tenant.id,
            QcoLineType.code == "material",
        )
    ).first()
    if existing:
        return existing
    lt = QcoLineType(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="material",
        name="Material",
        is_default=True,
        is_active=True,
    )
    db_session.add(lt)
    db_session.commit()
    db_session.refresh(lt)
    return lt


@pytest.fixture
def b4_tenant_template(db_session, test_tenant):
    """A tenant-owned template (not system) for disable/list tests."""
    t = QuoteTemplate(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name=f"TP-B4 Tenant Template {uuid.uuid4().hex[:6]}",
        style="component",
        is_system_template=False,
        is_active=True,
        current_version=1,
        created_by=TEST_USER_ID,
        updated_by=TEST_USER_ID,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def b4_system_template(db_session):
    """A system-level template (tenant_id=NULL) for fork tests."""
    t = QuoteTemplate(
        id=uuid.uuid4(),
        tenant_id=None,
        name=f"TP-B4 System Template {uuid.uuid4().hex[:6]}",
        style="deliverable",
        is_system_template=True,
        is_active=True,
        current_version=1,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def b4_customer(db_session, test_tenant):
    c = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type="person",
        display_name=f"TP-B4 Customer {uuid.uuid4().hex[:6]}",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def b4_site(db_session, test_tenant, b4_customer):
    s = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=b4_customer.id,
        address_line_1="100 Template Blvd",
        city="Templatetown",
        state="TX",
        postal_code="75004",
        country="US",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


# ==================== SECURITY GUARD TESTS ====================


class TestTpB4SecurityGuards:
    def test_list_blocked_when_disabled(self, client):
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_create_blocked_in_production(self, client):
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(
                    f"{BASE}/test",
                    json={"name": "blocked", "style": "component"},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== LIST /test ====================


class TestTpB4ListQuoteTemplates:
    def test_list_returns_200(self, client, b4_tenant_template):
        """GET /quote-templates/test returns 200 with a list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/test")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_list_includes_tenant_template(self, client, b4_tenant_template):
        """List includes the tenant-owned template."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/test")
        ids = [t["id"] for t in response.json()]
        assert str(b4_tenant_template.id) in ids

    def test_list_includes_system_template(self, client, b4_system_template):
        """List includes system templates (tenant_id=NULL)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{BASE}/test")
        ids = [t["id"] for t in response.json()]
        assert str(b4_system_template.id) in ids


# ==================== CREATE /test ====================


class TestTpB4CreateQuoteTemplate:
    def test_create_template_returns_201(self, client):
        """POST /quote-templates/test creates a new template."""
        name = f"TP-B4 New Template {uuid.uuid4().hex[:6]}"
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/test",
                    json={"name": name, "style": "component", "lines": []},
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == name
        assert data["style"] == "component"
        assert data["is_system_template"] is False

    def test_create_invalid_style_returns_422(self, client):
        """Returns 422 for invalid style value."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/test",
                    json={"name": "Bad Style", "style": "invalid_style"},
                )
        assert response.status_code == 422

    def test_create_duplicate_name_returns_422(self, client, b4_tenant_template):
        """Returns 422 when name already exists for this tenant."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/test",
                    json={"name": b4_tenant_template.name, "style": "component"},
                )
        assert response.status_code == 422


# ==================== FORK /test ====================


class TestTpB4ForkQuoteTemplate:
    def test_fork_system_template_returns_201(self, client, b4_system_template):
        """POST /{id}/fork/test creates a tenant copy of a system template."""
        fork_name = f"My Fork {uuid.uuid4().hex[:6]}"
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/{b4_system_template.id}/fork/test",
                    json={"name": fork_name},
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == fork_name
        assert data["is_system_template"] is False
        assert data["system_template_id"] == str(b4_system_template.id)

    def test_fork_non_system_returns_422(self, client, b4_tenant_template):
        """Returns 422 when forking a non-system template."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/{b4_tenant_template.id}/fork/test",
                    json={},
                )
        assert response.status_code == 422

    def test_fork_404_for_unknown_template(self, client):
        """Returns 404 for unknown template."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/{uuid.uuid4()}/fork/test",
                    json={},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== DISABLE /test ====================


class TestTpB4DisableQuoteTemplate:
    def test_disable_template_sets_inactive(self, client, b4_tenant_template):
        """POST /{id}/disable/test soft-disables the template."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{BASE}/{b4_tenant_template.id}/disable/test")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    def test_disable_404_for_unknown_template(self, client):
        """Returns 404 for unknown template."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{BASE}/{uuid.uuid4()}/disable/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_disable_no_longer_in_tenant_only_list(self, client, b4_tenant_template):
        """After disabling, template no longer appears in tenant_only list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                client.post(f"{BASE}/{b4_tenant_template.id}/disable/test")
                list_resp = client.get(f"{BASE}/test?tenant_only=true")
        assert list_resp.status_code == status.HTTP_200_OK
        ids = [t["id"] for t in list_resp.json()]
        assert str(b4_tenant_template.id) not in ids


# ==================== CREATE FROM TEMPLATE /test ====================


class TestTpB4CreateQuoteFromTemplate:
    def test_create_from_tenant_template(
        self, client, b4_tenant_template, b4_customer, b4_site
    ):
        """POST /from-template/{template_id}/test creates a quote from a template."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/from-template/{b4_tenant_template.id}/test",
                    json={
                        "customer_id": str(b4_customer.id),
                        "site_id": str(b4_site.id),
                        "variable_overrides": {},
                    },
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "quote_id" in data
        assert data["status"] == "draft"
        assert data["template_id"] == str(b4_tenant_template.id)

    def test_create_from_template_404_unknown_template(
        self, client, b4_customer, b4_site
    ):
        """Returns 404 for unknown template."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/from-template/{uuid.uuid4()}/test",
                    json={
                        "customer_id": str(b4_customer.id),
                        "site_id": str(b4_site.id),
                    },
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_from_template_404_unknown_customer(
        self, client, b4_tenant_template, b4_site
    ):
        """Returns 404 when customer not found."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/from-template/{b4_tenant_template.id}/test",
                    json={
                        "customer_id": str(uuid.uuid4()),
                        "site_id": str(b4_site.id),
                    },
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND
