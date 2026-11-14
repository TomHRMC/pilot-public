"""CLASS-B1: GET /api/v1/job-types — list active job types (platform defaults ∪ tenant overrides).

Tenant rows override platform rows on matching code.
No create/edit endpoints for job_type in this batch — read-only for now.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from api.schemas.schemas import JobTypeResponse
from app.models.fulfillment import JobType
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


def _list_job_types_impl(
    db: Session,
    tenant_id,
) -> list[JobTypeResponse]:
    """Shared logic — called by both authenticated and test endpoints.

    Resolution rule:
    1. Fetch ALL active platform rows (tenant_id IS NULL).
    2. Fetch ALL active tenant-specific rows for this tenant.
    3. Build a dict keyed by code — tenant row wins on conflict.
    4. Return sorted by (sort_order, label).
    """
    # Fetch platform defaults
    platform_rows = db.exec(
        select(JobType)
        .where(JobType.tenant_id == None)
        .where(JobType.is_active == True)
    ).all()

    # Fetch tenant overrides
    tenant_rows = db.exec(
        select(JobType)
        .where(JobType.tenant_id == tenant_id)
        .where(JobType.is_active == True)
    ).all()

    # Merge — tenant row wins on code collision
    merged: dict[str, tuple[JobType, bool]] = {}
    for row in platform_rows:
        merged[row.code] = (row, False)  # is_tenant_override=False
    for row in tenant_rows:
        merged[row.code] = (row, True)  # is_tenant_override=True

    # Sort by sort_order, then label
    sorted_entries = sorted(
        merged.values(), key=lambda x: (x[0].sort_order, x[0].label)
    )

    return [
        JobTypeResponse(
            id=row.id,
            code=row.code,
            label=row.label,
            sort_order=row.sort_order,
            is_active=row.is_active,
            is_tenant_override=is_override,
        )
        for row, is_override in sorted_entries
    ]


@router.get("", response_model=list[JobTypeResponse])
def list_job_types(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
) -> list[JobTypeResponse]:
    """List active job types (platform defaults + tenant overrides, tenant wins on code)."""
    return _list_job_types_impl(db, current_user.tenant_id)


@router.get("/test", response_model=list[JobTypeResponse])
def list_job_types_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> list[JobTypeResponse]:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _list_job_types_impl(db, ctx.tenant_id)
