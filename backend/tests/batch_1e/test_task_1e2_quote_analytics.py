"""
Task 1-E-2: Quote View Analytics / Read Receipts API Tests

Verifies endpoints under /api/v1/quotes/{id}/analytics:

  A. 200 OK — returns sorted timeline, action names, contact names populated.
  B. IDOR Guard — querying another tenant's quote returns 404 (not 403 / data leak).
  C. Empty State — a quote with no view events returns an empty list.

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-E-2
Batch 1-E Verification:
  - Events returned newest-first (occurred_at DESC).
  - tenant_id filter enforced: cross-tenant quote → 404.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.models.crm import Contact, Customer, CustomerType, Site
from app.models.quoting import (
    QplContactActionType,
    Quote,
    QuotePublicLinkContactAction,
    QuoteStatus,
)

# ============================================================
# Helpers
# ============================================================


def _get_or_create_quote_status(
    db_session, tenant_id, code: str = "draft"
) -> QuoteStatus:
    qs = db_session.exec(
        select(QuoteStatus).where(
            QuoteStatus.code == code,
            QuoteStatus.tenant_id == tenant_id,
        )
    ).first()
    if not qs:
        qs = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            code=code,
            name=code.capitalize(),
            is_default=(code == "draft"),
            is_active=True,
        )
        db_session.add(qs)
        db_session.flush()
    return qs


def _get_or_create_action_type(
    db_session, code: str, name: str
) -> QplContactActionType:
    at = db_session.exec(
        select(QplContactActionType).where(
            QplContactActionType.code == code,
            QplContactActionType.tenant_id.is_(None),
        )
    ).first()
    if not at:
        at = QplContactActionType(
            id=uuid.uuid4(),
            tenant_id=None,
            code=code,
            name=name,
            is_active=True,
        )
        db_session.add(at)
        db_session.flush()
    return at


def _create_contact(
    db_session, tenant_id, customer_id, first_name: str, last_name: str
) -> Contact:
    contact = Contact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        first_name=first_name,
        last_name=last_name,
        email=f"{first_name.lower()}.{last_name.lower()}-{uuid.uuid4().hex[:6]}@example.com",
        is_active=True,
    )
    db_session.add(contact)
    db_session.flush()
    return contact


def _create_quote(db_session, tenant_id, customer_id, site_id, status_id) -> Quote:
    quote = Quote(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=status_id,
        currency="USD",
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
        is_active=True,
    )
    db_session.add(quote)
    db_session.flush()
    return quote


def _create_action(
    db_session,
    tenant_id,
    quote_id,
    contact_id,
    action_type_id,
    occurred_at: datetime,
    user_agent: str = None,
    ip: str = None,
) -> QuotePublicLinkContactAction:
    action = QuotePublicLinkContactAction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quote_id=quote_id,
        contact_id=contact_id,
        qpl_contact_action_type_id=action_type_id,
        occurred_at=occurred_at,
        user_agent=user_agent,
        ip=ip,
    )
    db_session.add(action)
    db_session.flush()
    return action


# ============================================================
# Seed helper — builds a complete quote + contact + action events
# ============================================================


def _seed_analytics_data(db_session, test_tenant, test_customer, test_site):
    """
    Returns (quote, contact, [view_type, accept_type], [older_action, newer_action])
    """
    qs = _get_or_create_quote_status(db_session, test_tenant.id)
    quote = _create_quote(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        qs.id,
    )

    contact = _create_contact(
        db_session, test_tenant.id, test_customer.id, "Alice", "Smith"
    )

    view_type = _get_or_create_action_type(db_session, "view", "Viewed Quote")
    accept_type = _get_or_create_action_type(db_session, "accept", "Accepted Quote")

    now = datetime.now(UTC)
    older = _create_action(
        db_session,
        test_tenant.id,
        quote.id,
        contact.id,
        view_type.id,
        occurred_at=now - timedelta(hours=2),
        user_agent="Mozilla/5.0 (iPhone)",
        ip="192.168.1.1",
    )
    newer = _create_action(
        db_session,
        test_tenant.id,
        quote.id,
        contact.id,
        accept_type.id,
        occurred_at=now - timedelta(minutes=5),
        user_agent="Mozilla/5.0 (Macintosh)",
        ip="192.168.1.2",
    )

    db_session.commit()
    return quote, contact, (view_type, accept_type), (older, newer)


# ============================================================
# Test A — Successful timeline, correct sort, field population
# ============================================================


class TestQuoteAnalyticsSuccess:
    """Test A: Returns 200 with correctly sorted and populated events."""

    def test_analytics_returns_200_and_events(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        GET /api/v1/quotes/{id}/analytics/test returns 200 and the correct
        list of events sorted newest-first.
        """
        quote, contact, (view_type, accept_type), (older, newer) = _seed_analytics_data(
            db_session, test_tenant, test_customer, test_site
        )

        resp = client.get(f"/api/v1/quotes/{quote.id}/analytics/test")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert "events" in body
        events = body["events"]
        assert len(events) == 2

    def test_events_sorted_newest_first(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Events must be ordered by occurred_at DESC (newest at index 0)."""
        quote, contact, (view_type, accept_type), (older, newer) = _seed_analytics_data(
            db_session, test_tenant, test_customer, test_site
        )

        resp = client.get(f"/api/v1/quotes/{quote.id}/analytics/test")
        assert resp.status_code == 200, resp.text
        events = resp.json()["events"]

        # Newest (accept) should be first
        assert events[0]["action_name"] == accept_type.name
        assert events[1]["action_name"] == view_type.name

        # Timestamps descending
        from datetime import datetime as dt

        t0 = dt.fromisoformat(events[0]["occurred_at"])
        t1 = dt.fromisoformat(events[1]["occurred_at"])
        assert t0 > t1

    def test_action_name_and_contact_name_populated(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """action_name and contact_name must be human-readable strings."""
        quote, contact, (view_type, accept_type), _ = _seed_analytics_data(
            db_session, test_tenant, test_customer, test_site
        )

        resp = client.get(f"/api/v1/quotes/{quote.id}/analytics/test")
        assert resp.status_code == 200, resp.text
        events = resp.json()["events"]

        action_names = {e["action_name"] for e in events}
        assert accept_type.name in action_names
        assert view_type.name in action_names

        # Contact name should be "Alice Smith"
        contact_names = {e["contact_name"] for e in events}
        assert "Alice Smith" in contact_names

    def test_ip_and_user_agent_populated(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """ip_address and user_agent are returned when present in the action row."""
        quote, contact, (view_type, _), _ = _seed_analytics_data(
            db_session, test_tenant, test_customer, test_site
        )

        resp = client.get(f"/api/v1/quotes/{quote.id}/analytics/test")
        assert resp.status_code == 200, resp.text
        events = resp.json()["events"]

        # Find the view event (older, has ip 192.168.1.1)
        view_event = next(e for e in events if e["action_name"] == view_type.name)
        assert view_event["ip_address"] == "192.168.1.1"
        assert "Mozilla" in view_event["user_agent"]


# ============================================================
# Test B — IDOR guard: cross-tenant quote returns 404
# ============================================================


class TestQuoteAnalyticsIDOR:
    """Test B: Accessing analytics for another tenant's quote returns 404."""

    def test_cross_tenant_quote_returns_404(
        self, client, db_session, test_tenant, test_customer, test_site, tenant_b
    ):
        """
        A quote belonging to tenant_b is invisible to the test context (test_tenant).
        The endpoint must return 404 — not 403 or a data payload.
        """
        # Build minimal data under tenant_b
        cust_b = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            display_name="Tenant B Customer",
            type=CustomerType.person,
            is_active=True,
        )
        db_session.add(cust_b)
        db_session.flush()

        site_b = Site(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            customer_id=cust_b.id,
            is_active=True,
        )
        db_session.add(site_b)
        db_session.flush()

        qs_b = _get_or_create_quote_status(db_session, tenant_b.id)
        quote_b = _create_quote(db_session, tenant_b.id, cust_b.id, site_b.id, qs_b.id)
        db_session.commit()

        # Test context authenticates as test_tenant (NOT tenant_b)
        resp = client.get(f"/api/v1/quotes/{quote_b.id}/analytics/test")
        assert resp.status_code == 404, resp.text

    def test_nonexistent_quote_returns_404(self, client, db_session, test_tenant):
        """A completely random UUID that doesn't exist returns 404."""
        resp = client.get(f"/api/v1/quotes/{uuid.uuid4()}/analytics/test")
        assert resp.status_code == 404, resp.text


# ============================================================
# Test C — Empty state: quote with no events returns []
# ============================================================


class TestQuoteAnalyticsEmptyState:
    """Test C: A quote with no view events returns an empty events list."""

    def test_quote_with_no_events_returns_empty_list(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        GET /api/v1/quotes/{id}/analytics/test on a quote that has never been
        viewed should return 200 with events: [].
        """
        qs = _get_or_create_quote_status(db_session, test_tenant.id)
        quote = _create_quote(
            db_session,
            test_tenant.id,
            test_customer.id,
            test_site.id,
            qs.id,
        )
        db_session.commit()

        resp = client.get(f"/api/v1/quotes/{quote.id}/analytics/test")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body == {"events": []}

    def test_empty_state_does_not_return_404(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """An unviewed quote must return 200 with an empty list, never a 404."""
        qs = _get_or_create_quote_status(db_session, test_tenant.id)
        quote = _create_quote(
            db_session,
            test_tenant.id,
            test_customer.id,
            test_site.id,
            qs.id,
        )
        db_session.commit()

        resp = client.get(f"/api/v1/quotes/{quote.id}/analytics/test")
        assert resp.status_code == 200
        assert isinstance(resp.json()["events"], list)
        assert len(resp.json()["events"]) == 0
