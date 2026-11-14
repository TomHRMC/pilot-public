"""
Notification Category Registry — B10/A56

GET /api/v1/notifications/categories  — list all categories with resolved defaults
GET /api/v1/notifications/sub-triggers — list sub-triggers (optional category_id filter)

Pattern: dual-endpoint architecture (§8.2 of pilot-python-engineer-methods.md).
Permission: notification_preference.user_override.edit (all authenticated roles).
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.models.system import (
    NotificationCategory,
    NotificationCategorySubTrigger,
    NotificationDefaultPolicy,
)
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== SHARED BUSINESS LOGIC ====================


def _list_categories_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict[str, Any]:
    """
    Return all 8 notification categories with effective channel defaults
    resolved at the TENANT level (not user level — this feeds the matrix header row).

    Resolution order per channel per category:
      1. Tenant-override row in notification_default_policy (tenant_id = requesting tenant)
      2. System-default row in notification_default_policy (tenant_id IS NULL)
      3. Fallback: False
    """
    tenant_id = user_context.tenant_id

    # Load all categories ordered by display_order
    categories = db.exec(
        select(NotificationCategory).order_by(NotificationCategory.display_order)
    ).all()

    # Load system defaults (tenant_id IS NULL) — keyed by (category_id, channel)
    system_defaults: dict[tuple, bool] = {}
    for row in db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == None
        )
    ).all():
        system_defaults[(row.category_id, row.channel)] = row.enabled

    # Load tenant overrides for this tenant — keyed by (category_id, channel)
    tenant_overrides: dict[tuple, bool] = {}
    for row in db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id
        )
    ).all():
        tenant_overrides[(row.category_id, row.channel)] = row.enabled

    channels = ["push", "email", "in_app"]
    result = []

    for cat in categories:
        channel_data: dict[str, dict[str, Any]] = {}
        for ch in channels:
            # FIND-169: cat.category_id → cat.code (PK renamed on NotificationCategory)
            sys_default = system_defaults.get((cat.code, ch), False)
            tenant_default_val = tenant_overrides.get((cat.code, ch))

            has_tenant_override = tenant_default_val is not None
            effective = tenant_default_val if has_tenant_override else sys_default

            channel_data[ch] = {
                "system_default": sys_default,
                "tenant_default": tenant_default_val
                if has_tenant_override
                else sys_default,
                "effective": effective,
            }

        result.append(
            {
                # FIND-169: cat.category_id → cat.code
                "category_id": cat.code,
                "display_label": cat.display_label,
                "description": cat.description,
                "display_order": cat.display_order,
                "channels": channel_data,
            }
        )

    return {"categories": result}


def _list_sub_triggers_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    category_id: str | None = None,
) -> dict[str, Any]:
    """Return sub-triggers, optionally filtered by category_id."""
    stmt = select(NotificationCategorySubTrigger)
    if category_id:
        stmt = stmt.where(NotificationCategorySubTrigger.category_id == category_id)

    sub_triggers = db.exec(stmt).all()

    return {
        "sub_triggers": [
            {
                # FIND-169: sub_trigger_id → code on NotificationCategorySubTrigger PK
                "sub_trigger_id": st.code,
                "category_id": st.category_id,
                "display_label": st.display_label,
                "forced_minimum_push_uniform": st.forced_minimum_push_uniform,
                "forced_minimum_push_recipient_only": st.forced_minimum_push_recipient_only,
            }
            for st in sub_triggers
        ]
    }


# ==================== TEST ENDPOINTS (register FIRST) ====================


@router.get("/test/categories")
def list_categories_test(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _list_categories_impl(db, test_context)


@router.get("/test/sub-triggers")
def list_sub_triggers_test(
    category_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Test endpoint — no auth required."""
    test_context = get_test_context()
    return _list_sub_triggers_impl(db, test_context, category_id)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """
    List all notification categories with resolved effective channel defaults.

    Returns 8 categories × 3 channels with system_default, tenant_default, and effective values.
    Used by the frontend notification preference matrix header row.
    """
    return _list_categories_impl(db, current_user)


@router.get("/sub-triggers")
def list_sub_triggers(
    category_id: str | None = Query(None, description="Filter by category_id"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """
    List notification sub-triggers with forced-minimum push metadata.

    Optional query param: category_id — filter to a specific category.
    """
    return _list_sub_triggers_impl(db, current_user, category_id)
