"""C-B15 — Tenant impersonation service.

Platform-level (not tenant-scoped) functions for the operator tenant
impersonation feature:

    - list_operator_tenants()      — all tenants for the selector dropdown
    - log_impersonation_event()    — INSERT one audit.event row
    - start_impersonation()        — validate tenant + log 'start' event
    - end_impersonation()          — log 'end' event (always 200)
"""

import logging
import uuid
from typing import Any, Literal

from sqlmodel import Session, select

from app.models.billing import Subscription, SubscriptionStatus
from app.models.core import Tenant
from app.models.subscription import SubscriptionTier
from app.models.system import AuditEvent
from core.datetime_utils import safe_now_utc

logger = logging.getLogger(__name__)


def list_operator_tenants(db: Session) -> list[dict[str, Any]]:
    """Return all tenants for the operator selector, active first then name ASC.

    LEFT JOIN current active subscription → subscription_status.code.
    LEFT JOIN subscription_tier on tenant.current_subscription_tier_id → tier_name.
    Both joins are nullable (tenant may have no subscription row).

    This is a sanctioned cross-tenant platform read (same class as
    cohort_dashboard.get_cohort_overview()) — the ONLY query in this batch
    without a tenant_id filter.

    Returns:
        list of dicts with keys: tenant_id, name, is_active, tier_name,
        subscription_status, created_at.
    """
    tenants = db.exec(
        select(Tenant).order_by(Tenant.is_active.desc(), Tenant.name.asc())
    ).all()

    results: list[dict[str, Any]] = []
    for tenant in tenants:
        # Active subscription row → status code
        sub_row = db.exec(
            select(Subscription)
            .where(Subscription.tenant_id == tenant.id)
            .where(Subscription.is_active == True)
        ).first()

        subscription_status: str | None = None
        if sub_row:
            status_row = db.exec(
                select(SubscriptionStatus).where(
                    SubscriptionStatus.id == sub_row.status_id
                )
            ).first()
            subscription_status = status_row.code if status_row else None

        # Tier name from tenant.current_subscription_tier_id
        tier_name: str | None = None
        if tenant.current_subscription_tier_id:
            tier = db.exec(
                select(SubscriptionTier).where(
                    SubscriptionTier.tier_id == tenant.current_subscription_tier_id
                )
            ).first()
            tier_name = tier.tier_name if tier else None

        results.append(
            {
                "tenant_id": tenant.id,
                "name": tenant.name,
                "is_active": tenant.is_active,
                "tier_name": tier_name,
                "subscription_status": subscription_status,
                "created_at": tenant.created_at,
            }
        )

    return results


def log_impersonation_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    impersonator_user_id: uuid.UUID,
    action: Literal["start", "end", "request"],
    context: dict[str, Any] | None = None,
    user_role: str | None = None,
) -> None:
    """INSERT one audit.event row for an impersonation lifecycle event.

    Uses actor_type='platform' (allowed by audit_event_actor_type_chk).
    entity_name='impersonation', entity_id=str(tenant_id).

    Calls db.add() + db.flush() only — the caller is responsible for commit.
    """
    event = AuditEvent(
        occurred_at=safe_now_utc(),
        tenant_id=tenant_id,
        user_id=impersonator_user_id,
        actor_type="platform",
        user_role=user_role,
        entity_name="impersonation",
        entity_id=str(tenant_id),
        action=action,
        contextdata=context,
    )
    db.add(event)
    db.flush()


def start_impersonation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    impersonator_user_id: uuid.UUID,
    user_role: str | None = None,
) -> dict[str, Any]:
    """Validate tenant exists + is active, log 'start' event, return session payload.

    Raises:
        ValueError: tenant not found or inactive (caller maps to 404/409).
    """
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    if not tenant.is_active:
        raise ValueError(f"Tenant {tenant_id} is not active")

    started_at = safe_now_utc()
    log_impersonation_event(
        db,
        tenant_id=tenant_id,
        impersonator_user_id=impersonator_user_id,
        action="start",
        user_role=user_role,
    )
    db.commit()

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "impersonator_user_id": impersonator_user_id,
        "role_code": "owner",
        "started_at": started_at,
    }


def end_impersonation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    impersonator_user_id: uuid.UUID,
    user_role: str | None = None,
) -> dict[str, Any]:
    """Log 'end' event for an impersonation session. Always succeeds (200).

    Never 404s on a missing prior start row (design §D.3) — the client state
    may have been cleared independently.
    """
    log_impersonation_event(
        db,
        tenant_id=tenant_id,
        impersonator_user_id=impersonator_user_id,
        action="end",
        user_role=user_role,
    )
    db.commit()
    return {"ended": True}
