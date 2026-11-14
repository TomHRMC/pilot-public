"""
api/routes/job_expense_categories.py — B17/A8

GET  /api/v1/job-expense-categories       — authenticated: list expense categories for tenant
GET  /api/v1/job-expense-categories/test  — test-only: no JWT required

Returns global rows (tenant_id IS NULL) plus tenant-specific overrides
(tenant_id = current_user.tenant_id). When the same code exists in both,
the tenant-specific row shadows the global row.

Permission: jobs.view
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlmodel import Session, or_, select

from app.models.fulfillment import JobExpenseCategory
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────


class JobExpenseCategoryItem(BaseModel):
    code: str
    name: str
    is_default: bool


class JobExpenseCategoriesResponse(BaseModel):
    categories: list[JobExpenseCategoryItem]


# ─────────────────────────────────────────────────────────────────────────────
# Shared business logic
# ─────────────────────────────────────────────────────────────────────────────


def _get_job_expense_categories_impl(
    db: Session,
    tenant_id: UUID,
) -> JobExpenseCategoriesResponse:
    """
    Return job expense categories for a tenant.

    Merges:
      - Global rows (tenant_id IS NULL) — system defaults
      - Tenant-specific rows (tenant_id = tenant_id) — override global rows of same code

    Tenant-specific rows shadow global rows of the same code.
    Result ordered by name ASC.
    """
    # Fetch both global and tenant-specific active rows in one query
    rows = db.exec(
        select(JobExpenseCategory)
        .where(
            JobExpenseCategory.is_active == True,
            or_(
                JobExpenseCategory.tenant_id == None,
                JobExpenseCategory.tenant_id == tenant_id,
            ),
        )
        .order_by(JobExpenseCategory.name)
    ).all()

    # Tenant-specific rows shadow global rows for the same code
    merged: dict[str, JobExpenseCategory] = {}
    for row in rows:
        code = row.code
        if code not in merged:
            merged[code] = row
        else:
            # Prefer tenant-specific over global
            if row.tenant_id is not None:
                merged[code] = row

    categories = [
        JobExpenseCategoryItem(
            code=row.code,
            name=row.name,
            is_default=row.is_default,
        )
        for row in sorted(merged.values(), key=lambda r: r.name)
    ]

    return JobExpenseCategoriesResponse(categories=categories)


# ─────────────────────────────────────────────────────────────────────────────
# Test endpoint (registered BEFORE authenticated endpoint)
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/test",
    response_model=JobExpenseCategoriesResponse,
    status_code=status.HTTP_200_OK,
    tags=["test-only"],
    summary="[TEST] List job expense categories (no JWT)",
)
def list_job_expense_categories_test(
    db: Session = Depends(get_db),
) -> JobExpenseCategoriesResponse:
    """Test-only endpoint — no auth required. Blocked in staging/production."""
    ctx: TestUserContext = get_test_context()
    return _get_job_expense_categories_impl(db, ctx.tenant_id)


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated endpoint
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=JobExpenseCategoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="List job expense categories for the tenant",
)
def list_job_expense_categories(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
) -> JobExpenseCategoriesResponse:
    """
    Return all active job expense categories available to the tenant.

    Merges global system categories (tenant_id IS NULL) with any
    tenant-specific overrides. Tenant rows shadow global rows of the same code.
    Ordered by name ASC.
    """
    return _get_job_expense_categories_impl(db, current_user.tenant_id)
