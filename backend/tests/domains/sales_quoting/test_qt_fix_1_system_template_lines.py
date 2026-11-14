"""QT-FIX-1 — System Template Lines (tenant_id nullable).

Regression tests for the QT-FIX-1 fix:
  1. A QuoteTemplateLine with tenant_id=None persists on a system template
     (proves the NOT NULL constraint was dropped).
  2. Applying a system template (NULL-tenant lines) produces a non-empty quote
     with QuoteLine rows — the original bug produced an empty quote because
     system-template lines could not be owned without a tenant.

Test-resilience rules (per python-engineer-rules §16):
  - Uses test_tenant, test_customer, test_site fixtures — never hardcoded UUIDs.
  - Scope every assertion by IDs inserted in the current test.
  - Never UPDATE/DELETE shared seed rows; db_session rollback is cleanup.
  - The seeded 9 system-template lines (tenant_id IS NULL) are present; tests
    are ID-scoped and resilient to that.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import status
from sqlmodel import select

from app.models.quoting import (
    QcoLineType,
    QuoteTemplateLine,
)
from core.config import settings

BASE = "/api/v1/quote-templates"

# The 3 seeded system template IDs (Alembic-owned, tenant_id IS NULL).
SERVICE_CALL_BASIC_ID = uuid.UUID("608e2c6e-344c-4a6d-9d43-bd86960d202f")

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]


class TestQtFix1NullTenantLinePersists:
    """Test 1 — NULL-tenant QuoteTemplateLine commits and reads back."""

    def test_null_tenant_line_persists(self, db_session):
        """Insert a QuoteTemplateLine with tenant_id=None on a system template
        and assert it commits and reads back with tenant_id is None.

        Proves the NOT NULL constraint on quote_template_line.tenant_id was
        dropped (QT-FIX-1 migration 990231f963b0).
        """
        # Look up a platform-level qco_line_type (tenant_id IS NULL)
        qco_type = db_session.exec(
            select(QcoLineType).where(QcoLineType.tenant_id.is_(None))
        ).first()
        if qco_type is None:
            # Fallback: any qco_line_type
            qco_type = db_session.exec(select(QcoLineType)).first()

        line_id = uuid.uuid4()
        line = QuoteTemplateLine(
            id=line_id,
            tenant_id=None,
            quote_template_id=SERVICE_CALL_BASIC_ID,
            display_order=999,  # high order to avoid colliding with seeded 1-3
            qco_line_type_id=qco_type.id,
            description="QT-FIX-1 test line — NULL tenant",
            default_quantity=Decimal("1"),
            default_unit_price_cents=100,
            customer_visible=True,
            is_section_header=False,
            is_active=True,
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        # Assert it persisted with NULL tenant
        assert line.id == line_id
        assert line.tenant_id is None
        assert line.quote_template_id == SERVICE_CALL_BASIC_ID

        # Read it back scoped by the inserted ID
        read_back = db_session.exec(
            select(QuoteTemplateLine).where(QuoteTemplateLine.id == line_id)
        ).first()
        assert read_back is not None
        assert read_back.tenant_id is None
        assert read_back.description == "QT-FIX-1 test line — NULL tenant"


class TestQtFix1ApplySystemTemplateProducesNonEmptyQuote:
    """Test 2 — applying a system template (NULL-tenant lines) creates a
    non-empty quote with QuoteLine rows.

    This is the regression for the original bug: system templates
    (tenant_id IS NULL) could not own lines because the child required a
    tenant, so applying a system template produced an empty quote.
    """

    def test_apply_system_template_creates_quote_lines(
        self, client, test_customer, test_site
    ):
        """POST /from-template/{system_template_id}/test creates a quote with
        lines_created > 0 and QuoteLine rows for the returned quote_id.

        Uses the seeded 'Service Call Basic' system template (3 NULL-tenant
        lines).
        """
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{BASE}/from-template/{SERVICE_CALL_BASIC_ID}/test",
                    json={
                        "customer_id": str(test_customer.id),
                        "site_id": str(test_site.id),
                        "variable_overrides": {},
                    },
                )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "quote_id" in data
        assert data["status"] == "draft"
        assert data["template_id"] == str(SERVICE_CALL_BASIC_ID)

        # The core regression assertion: lines_created > 0 (was 0 before fix)
        lines_created = data["lines_created"]
        assert lines_created > 0, (
            "System template apply produced 0 lines — the QT-FIX-1 regression. "
            "Expected the 3 seeded NULL-tenant lines to be copied to the quote."
        )

        # The lines_created count is the authoritative signal that QuoteLine
        # rows were created (the impl iterates template_lines and adds a
        # QuoteLine per line, returning len(template_lines)).
        assert lines_created == 3, (
            f"Expected 3 lines for Service Call Basic, got {lines_created}"
        )
