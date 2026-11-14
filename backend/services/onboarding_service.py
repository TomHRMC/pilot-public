"""
B14/A77 — Onboarding checklist auto-completion service.
Called by domain event handlers in customer, catalog, QB, calendar, and team modules.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.onboarding import TenantOnboardingChecklist

logger = logging.getLogger(__name__)


def _get_or_create_checklist(db: Session, tenant_id: UUID) -> TenantOnboardingChecklist:
    """Get existing checklist row or create one with defaults."""
    checklist = db.exec(
        select(TenantOnboardingChecklist).where(
            TenantOnboardingChecklist.tenant_id == tenant_id
        )
    ).first()

    if not checklist:
        checklist = TenantOnboardingChecklist(tenant_id=tenant_id)
        db.add(checklist)
        db.commit()
        db.refresh(checklist)

    return checklist


def ensure_checklist_exists(db: Session, tenant_id: UUID) -> None:
    """
    Create tenant_onboarding_checklist row if it doesn't exist.
    Called during signup wizard completion (step5 → complete transition).
    Sets account_created = True, legal_accepted = True, tier_selected = True.
    """
    checklist = db.exec(
        select(TenantOnboardingChecklist).where(
            TenantOnboardingChecklist.tenant_id == tenant_id
        )
    ).first()

    if not checklist:
        checklist = TenantOnboardingChecklist(
            tenant_id=tenant_id,
            account_created=True,
            legal_accepted=True,
            tier_selected=True,
        )
        db.add(checklist)
        db.commit()
        logger.info(f"Onboarding checklist created for tenant {tenant_id}")
    else:
        # Update wizard completion flags if already exists
        updated = False
        if not checklist.account_created:
            checklist.account_created = True
            updated = True
        if not checklist.legal_accepted:
            checklist.legal_accepted = True
            updated = True
        if not checklist.tier_selected:
            checklist.tier_selected = True
            updated = True
        if updated:
            db.add(checklist)
            db.commit()


def mark_first_customer(db: Session, tenant_id: UUID) -> None:
    """
    Mark first_customer_added = True in tenant_onboarding_checklist.
    Idempotent — no-op if already marked.
    Called from customer create handler after successful commit.
    """
    checklist = _get_or_create_checklist(db, tenant_id)
    if not checklist.first_customer_added:
        checklist.first_customer_added = True
        checklist.first_customer_added_at = datetime.now(UTC)
        db.add(checklist)
        db.commit()
        logger.info(f"Onboarding: first customer marked for tenant {tenant_id}")


def mark_catalog_setup(db: Session, tenant_id: UUID) -> None:
    """Mark catalog_setup = True. Called from catalog item create handler."""
    checklist = _get_or_create_checklist(db, tenant_id)
    if not checklist.catalog_setup:
        checklist.catalog_setup = True
        checklist.catalog_setup_at = datetime.now(UTC)
        db.add(checklist)
        db.commit()
        logger.info(f"Onboarding: catalog setup marked for tenant {tenant_id}")


def mark_quickbooks_connected(db: Session, tenant_id: UUID) -> None:
    """Mark quickbooks_connected = True. Called from QB OAuth complete handler."""
    checklist = _get_or_create_checklist(db, tenant_id)
    if not checklist.quickbooks_connected:
        checklist.quickbooks_connected = True
        db.add(checklist)
        db.commit()
        logger.info(f"Onboarding: QuickBooks connected for tenant {tenant_id}")


def mark_calendar_connected(db: Session, tenant_id: UUID) -> None:
    """Mark calendar_connected = True. Called from Calendar OAuth complete handler."""
    checklist = _get_or_create_checklist(db, tenant_id)
    if not checklist.calendar_connected:
        checklist.calendar_connected = True
        db.add(checklist)
        db.commit()
        logger.info(f"Onboarding: Calendar connected for tenant {tenant_id}")


def mark_team_invited(db: Session, tenant_id: UUID) -> None:
    """Mark team_invited = True. Called from team invite send handler."""
    checklist = _get_or_create_checklist(db, tenant_id)
    if not checklist.team_invited:
        checklist.team_invited = True
        db.add(checklist)
        db.commit()
        logger.info(f"Onboarding: team invited for tenant {tenant_id}")


def skip_item(db: Session, tenant_id: UUID, item: str) -> TenantOnboardingChecklist:
    """
    Skip a skippable checklist item.
    item: quickbooks | calendar | team

    Returns updated checklist.
    """
    valid_items = {"quickbooks", "calendar", "team"}
    if item not in valid_items:
        raise ValueError(f"Invalid skip item: {item}. Must be one of {valid_items}")

    checklist = _get_or_create_checklist(db, tenant_id)

    if item == "quickbooks":
        checklist.quickbooks_skipped = True
    elif item == "calendar":
        checklist.calendar_skipped = True
    elif item == "team":
        checklist.team_skipped = True

    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    logger.info(f"Onboarding: {item} skipped for tenant {tenant_id}")
    return checklist


def hide_checklist(db: Session, tenant_id: UUID) -> TenantOnboardingChecklist:
    """Set checklist_hidden = True."""
    checklist = _get_or_create_checklist(db, tenant_id)
    checklist.checklist_hidden = True
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist


def unhide_checklist(db: Session, tenant_id: UUID) -> TenantOnboardingChecklist:
    """Set checklist_hidden = False (INV-BUG-14 — the unhide path that was missing)."""
    checklist = _get_or_create_checklist(db, tenant_id)
    checklist.checklist_hidden = False
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist


def dismiss_checklist_permanently(
    db: Session, tenant_id: UUID
) -> TenantOnboardingChecklist:
    """Set checklist_dismissed_permanently = True."""
    checklist = _get_or_create_checklist(db, tenant_id)
    checklist.checklist_dismissed_permanently = True
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist
