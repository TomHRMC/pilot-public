"""PLP-FIX-2: GET /api/v1/qco-line-types — list active QCO line types (platform defaults + tenant overrides).

Tenant rows override platform rows on matching code.
Read-only lookup — no create/edit endpoints in this batch.
Created so the frontend never hardcodes per-environment seed UUIDs again (Issue 5).
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from api.schemas.quotes import QcoLineTypeResponse
from app.models.quoting import QcoLineType
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


def _list_qco_line_types_impl(
    db: Session,
    tenant_id,
) -> list[QcoLineTypeResponse]:
    """Shared logic — called by both authenticated and test endpoints.

    Resolution rule (identical to job_types):
    1. Fetch ALL active platform rows (tenant_id IS NULL).
    2. Fetch ALL active tenant-specific rows for this tenant.
    3. Build a dict keyed by code — tenant row wins on conflict.
    4. Return sorted by name (no sort_order column on this table).
    """
    platform_rows = db.exec(
        select(QcoLineType)
        .where(QcoLineType.tenant_id == None)
        .where(QcoLineType.is_active == True)
    ).all()

    tenant_rows = db.exec(
        select(QcoLineType)
        .where(QcoLineType.tenant_id == tenant_id)
        .where(QcoLineType.is_active == True)
    ).all()

    merged: dict[str, tuple[QcoLineType, bool]] = {}
    for row in platform_rows:
        merged[row.code] = (row, False)
    for row in tenant_rows:
        merged[row.code] = (row, True)

    sorted_entries = sorted(merged.values(), key=lambda x: x[0].name)

    return [
        QcoLineTypeResponse(
            id=row.id,
            code=row.code,
            name=row.name,
            is_default=row.is_default,
            is_active=row.is_active,
            is_tenant_override=is_override,
        )
        for row, is_override in sorted_entries
    ]


@router.get("", response_model=list[QcoLineTypeResponse])
def list_qco_line_types(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
) -> list[QcoLineTypeResponse]:
    """List active QCO line types (platform defaults + tenant overrides, tenant wins on code)."""
    return _list_qco_line_types_impl(db, current_user.tenant_id)


@router.get("/test", response_model=list[QcoLineTypeResponse])
def list_qco_line_types_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> list[QcoLineTypeResponse]:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _list_qco_line_types_impl(db, ctx.tenant_id)
