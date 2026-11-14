"""
Integration tests for Golden Master Schema v2.6h synchronization.
Tests the 6 high-priority gaps identified in the reconciliation plan.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.auth import ContactPortalInvite
from app.models.core import UserEndpoint
from app.models.quoting import (
    Quote,
    QuoteAcceptance,
    QuoteLine,
    QuoteLineTaxComponent,
)
from app.models.system import AuditEvent, NotificationDeliveryAttempt

# ============================================================================
# GAP 1: contact_portal_invite Uniqueness on contact_id
# ============================================================================


def test_contact_portal_invite_unique_contact_id(
    db_session: Session, test_tenant, test_contact
):
    """
    Test Scenario: Workflow Uniqueness
    Expected: Only one active invitation per contact allowed
    """
    # First invitation - should succeed
    invite1 = ContactPortalInvite(
        tenant_id=test_tenant.id,
        contact_id=test_contact.id,
        email=test_contact.email,
        token_hash="hash1",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC),
    )
    db_session.add(invite1)
    db_session.commit()

    # Second invitation for same contact - should fail
    invite2 = ContactPortalInvite(
        tenant_id=test_tenant.id,
        contact_id=test_contact.id,  # Same contact
        email=test_contact.email,
        token_hash="hash2",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC),
    )
    db_session.add(invite2)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    assert "uq_contact_portal_invite_contact_id" in str(exc_info.value).lower()


# ============================================================================
# GAP 2: guard_user_endpoint_primary_email "Highlander Rule"
# ============================================================================


def test_user_endpoint_primary_demotion(db_session: Session, test_user):
    """
    Test Scenario: Primary Demotion
    Expected: Setting a new endpoint to is_primary=true must auto-demote the old primary

    The guard_user_endpoint_primary_email() trigger uses session variables to prevent
    race conditions:
    - Sets aevofab.skip_sync=true before auto-demotion to prevent premature sync
    - Clears the flag after auto-demotion
    - The sync happens when the new primary is promoted (INSERT operation)
    """
    from sqlmodel import select

    # Get the existing primary email endpoint from test_user fixture
    existing_primary = db_session.exec(
        select(UserEndpoint).where(
            UserEndpoint.user_id == test_user.id,
            UserEndpoint.channel == "email",
            UserEndpoint.is_primary == True,
        )
    ).first()

    assert existing_primary is not None, "Test user should have a primary email"
    old_primary_id = existing_primary.id

    # Create second endpoint as NON-primary first
    endpoint2 = UserEndpoint(
        user_id=test_user.id,
        channel="email",
        value="primary2@test.com",
        is_primary=False,  # Start as non-primary
        verification_status="verified",
        consent_status="opted_in",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(endpoint2)
    db_session.commit()
    db_session.refresh(endpoint2)

    # Now promote it to primary (triggers auto-demotion)
    endpoint2.is_primary = True
    db_session.commit()

    # Verify: Old primary was auto-demoted
    db_session.refresh(existing_primary)
    assert existing_primary.is_primary is False, "Old primary should be auto-demoted"
    assert endpoint2.is_primary is True, "New endpoint should be primary"

    # Verify only ONE primary email exists for this user
    primary_count = db_session.exec(
        select(UserEndpoint).where(
            UserEndpoint.user_id == test_user.id,
            UserEndpoint.channel == "email",
            UserEndpoint.is_primary == True,
        )
    ).all()
    assert len(primary_count) == 1, "Only one primary email should exist"
    assert primary_count[0].id == endpoint2.id, (
        "New endpoint should be the only primary"
    )


def test_user_endpoint_highlander_rule_delete(db_session: Session, test_user):
    """
    Test Scenario: The "Highlander" Rule (DELETE)
    Expected: Cannot delete the only primary email endpoint
    """
    from sqlmodel import select

    # Get the existing primary email endpoint from test_user fixture
    endpoint = db_session.exec(
        select(UserEndpoint).where(
            UserEndpoint.user_id == test_user.id,
            UserEndpoint.channel == "email",
            UserEndpoint.is_primary == True,
        )
    ).first()

    assert endpoint is not None, "Test user should have a primary email"

    # Attempt to delete - should raise exception
    db_session.delete(endpoint)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    assert "cannot delete the only primary email" in str(exc_info.value).lower()


def test_user_endpoint_highlander_rule_demote(db_session: Session, test_user):
    """
    Test Scenario: The "Highlander" Rule (UPDATE)
    Expected: Cannot manually demote the only primary email
    """
    from sqlmodel import select

    # Get the existing primary email endpoint from test_user fixture
    endpoint = db_session.exec(
        select(UserEndpoint).where(
            UserEndpoint.user_id == test_user.id,
            UserEndpoint.channel == "email",
            UserEndpoint.is_primary == True,
        )
    ).first()

    assert endpoint is not None, "Test user should have a primary email"

    # Attempt to demote - should raise exception
    endpoint.is_primary = False
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    assert "cannot demote the only primary email" in str(exc_info.value).lower()


# ============================================================================
# GAP 3: Componentized Tax Logic - Quote
# ============================================================================


def test_quote_multi_component_sum(
    db_session: Session,
    test_tenant,
    test_customer,
    test_site,
    test_quote_status,
    test_qco_line_type,
):
    """
    Test Scenario: Multi-Component Sum (Quote)
    Expected: Header tax_cents must equal sum of all tax_component.amount_cents for active lines
    """
    # Create quote
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)

    # Create line item
    line = QuoteLine(
        tenant_id=quote.tenant_id,
        quote_id=quote.id,
        position=1,
        qco_line_type_id=test_qco_line_type.id,  # Use fixture
        description="Test Item",
        quantity=Decimal("1.0"),
        unit_price_cents=10000,
        subtotal_cents=10000,
        total_cents=10000,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(line)

    # Create tax components
    tax_comp1 = QuoteLineTaxComponent(
        tenant_id=quote.tenant_id,
        quote_line_id=line.id,
        tax_rate_version_id=1,  # Assume seeded
        component_code="STATE",
        rate_pct=Decimal("6.25"),
        amount_cents=625,
        created_at=datetime.now(UTC),
    )
    tax_comp2 = QuoteLineTaxComponent(
        tenant_id=quote.tenant_id,
        quote_line_id=line.id,
        tax_rate_version_id=1,
        component_code="LOCAL",
        rate_pct=Decimal("2.00"),
        amount_cents=200,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([tax_comp1, tax_comp2])
    db_session.commit()

    # Verify: Header tax_cents = 625 + 200 = 825
    db_session.refresh(quote)
    assert quote.tax_cents == 825, f"Expected 825, got {quote.tax_cents}"
    assert quote.total_cents == 10825, f"Expected 10825, got {quote.total_cents}"


def test_quote_component_update(
    db_session: Session,
    test_tenant,
    test_customer,
    test_site,
    test_quote_status,
    test_qco_line_type,
):
    """
    Test Scenario: Component Update (Quote)
    Expected: Updating a tax component amount_cents must instantly update parent header total
    """
    # Setup quote with line and tax component
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(quote)
    db_session.commit()

    line = QuoteLine(
        tenant_id=quote.tenant_id,
        quote_id=quote.id,
        position=1,
        qco_line_type_id=test_qco_line_type.id,
        description="Test",
        subtotal_cents=10000,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(line)
    db_session.commit()

    tax_comp = QuoteLineTaxComponent(
        tenant_id=quote.tenant_id,
        quote_line_id=line.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("6.25"),
        amount_cents=625,
        created_at=datetime.now(UTC),
    )
    db_session.add(tax_comp)
    db_session.commit()

    # Verify initial state
    db_session.refresh(quote)
    assert quote.tax_cents == 625

    # Update component
    tax_comp.amount_cents = 700
    db_session.commit()

    # Verify header updated
    db_session.refresh(quote)
    assert quote.tax_cents == 700, "Header should reflect updated component"


def test_quote_component_deletion(
    db_session: Session,
    test_tenant,
    test_customer,
    test_site,
    test_quote_status,
    test_qco_line_type,
):
    """
    Test Scenario: Component Deletion (Quote)
    Expected: Deleting a tax component must reduce header tax_cents and total_cents
    """
    # Setup
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(quote)
    db_session.commit()

    line = QuoteLine(
        tenant_id=quote.tenant_id,
        quote_id=quote.id,
        position=1,
        qco_line_type_id=test_qco_line_type.id,
        description="Test",
        subtotal_cents=10000,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(line)
    db_session.commit()

    tax_comp = QuoteLineTaxComponent(
        tenant_id=quote.tenant_id,
        quote_line_id=line.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("6.25"),
        amount_cents=625,
        created_at=datetime.now(UTC),
    )
    db_session.add(tax_comp)
    db_session.commit()

    db_session.refresh(quote)
    assert quote.tax_cents == 625

    # Delete component
    db_session.delete(tax_comp)
    db_session.commit()

    # Verify header updated
    db_session.refresh(quote)
    assert quote.tax_cents == 0, "Header tax should be 0 after component deletion"


def test_quote_soft_delete_line_recalc(
    db_session: Session,
    test_tenant,
    test_customer,
    test_site,
    test_quote_status,
    test_qco_line_type,
):
    """
    Test Scenario: Soft-Delete (is_active) (Quote)
    Expected: Setting line to is_active=false must exclude its tax components from header
    """
    # Setup
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(quote)
    db_session.commit()

    line = QuoteLine(
        tenant_id=quote.tenant_id,
        quote_id=quote.id,
        position=1,
        qco_line_type_id=test_qco_line_type.id,
        description="Test",
        subtotal_cents=10000,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(line)
    db_session.commit()

    tax_comp = QuoteLineTaxComponent(
        tenant_id=quote.tenant_id,
        quote_line_id=line.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("6.25"),
        amount_cents=625,
        created_at=datetime.now(UTC),
    )
    db_session.add(tax_comp)
    db_session.commit()

    db_session.refresh(quote)
    assert quote.tax_cents == 625
    assert quote.subtotal_cents == 10000

    # Soft delete line
    line.is_active = False
    db_session.commit()

    # Verify header excludes inactive line
    db_session.refresh(quote)
    assert quote.tax_cents == 0, "Inactive line taxes should not be counted"
    assert quote.subtotal_cents == 0, "Inactive line subtotal should not be counted"


# ============================================================================
# GAP 4: NotificationDeliveryAttempt Lifecycle Fields
# ============================================================================


def test_notification_delivery_attempt_lifecycle(
    db_session: Session, test_tenant, test_notification_outbox
):
    """
    Test Scenario: Notification Lifecycle Tracking
    Expected: completed_at and next_attempt_after fields exist and are timezone-aware
    """
    now = datetime.now(UTC)
    next_attempt = now + timedelta(minutes=5)

    attempt = NotificationDeliveryAttempt(
        notification_outbox_id=test_notification_outbox.id,
        tenant_id=test_tenant.id,
        attempt_no=1,
        status="delivered",
        provider="sendgrid",
        attempted_at=now,
        completed_at=now,  # GAP 4 field
        next_attempt_after=next_attempt,  # GAP 4 field
        created_at=now,
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.refresh(attempt)

    # Verify fields exist and are timezone-aware
    assert attempt.completed_at is not None
    assert attempt.next_attempt_after is not None
    assert attempt.completed_at.tzinfo is not None, (
        "completed_at must be timezone-aware"
    )
    assert attempt.next_attempt_after.tzinfo is not None, (
        "next_attempt_after must be timezone-aware"
    )


# ============================================================================
# GAP 5: quote_acceptance.approved_at Timezone Awareness
# ============================================================================


def test_quote_acceptance_approved_at_timezone(
    db_session: Session, test_quote_version, test_contact
):
    """
    Test Scenario: Timezone Compliance Fix
    Expected: approved_at field is timezone-aware (TIMESTAMPTZ)
    """
    now = datetime.now(UTC)

    acceptance = QuoteAcceptance(
        tenant_id=test_contact.tenant_id,
        quote_version_id=test_quote_version.id,
        contact_id=test_contact.id,
        accepted_by_name="John Doe",
        accepted_by_email="john@test.com",
        approved_at=now,  # GAP 5 fix
        created_at=now,
    )
    db_session.add(acceptance)
    db_session.commit()
    db_session.refresh(acceptance)

    # Verify timezone awareness
    assert acceptance.approved_at.tzinfo is not None, (
        "approved_at must be timezone-aware"
    )


# ============================================================================
# GAP 6: audit.event.actor_type CHECK Constraint
# ============================================================================


def test_audit_event_actor_type_valid(db_session: Session):
    """
    Test Scenario: Audit Integrity Enforcement (Valid)
    Expected: Valid actor_type values accepted: system, user, platform, external_webhook
    """
    valid_types = ["system", "user", "platform", "external_webhook"]

    for actor_type in valid_types:
        event = AuditEvent(
            occurred_at=datetime.now(UTC),
            actor_type=actor_type,
            entity_name="test",
            entity_id="123",
            action="create",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        assert event.actor_type == actor_type


def test_audit_event_actor_type_invalid(db_session: Session):
    """
    Test Scenario: Audit Integrity Enforcement (Invalid)
    Expected: Invalid actor_type values rejected
    """
    event = AuditEvent(
        occurred_at=datetime.now(UTC),
        actor_type="invalid_type",  # Should be rejected
        entity_name="test",
        entity_id="123",
        action="create",
    )
    db_session.add(event)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    assert "audit_event_actor_type_chk" in str(exc_info.value).lower()
