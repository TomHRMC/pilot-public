"""
A25: Quote Template Schema with Style and Versioning

Endpoints:
  GET  /api/v1/quote-templates                      — list templates (filterable)
  POST /api/v1/quote-templates                      — create tenant template
  POST /api/v1/quote-templates/{id}/fork            — fork a system template
  POST /api/v1/quote-templates/{id}/disable         — soft-disable a template
  POST /api/v1/quotes/from-template/{template_id}   — create quote from template

Note: POST /api/v1/quotes/{id}/save-as-template is implemented in A27 (quotes.py).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.crm import Customer, Site
from app.models.quoting import (
    QcoLineType,
    Quote,
    QuoteLine,
    QuoteStatus,
    QuoteTemplate,
    QuoteTemplateLine,
    QuoteTemplateVersion,
)
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────


class QuoteTemplateLineCreate(BaseModel):
    qco_line_type_id: UUID
    description: str
    default_quantity: Decimal = Decimal("1")
    default_unit_price_cents: int = 0
    customer_visible: bool = True
    is_section_header: bool = False
    display_order: int = 0
    parent_line_id: UUID | None = None


class QuoteTemplateCreate(BaseModel):
    name: str
    style: str  # component | deliverable | lump_sum
    category: str | None = None
    description: str | None = None
    lines: list[QuoteTemplateLineCreate] = []


class QuoteTemplateForkRequest(BaseModel):
    name: str | None = None  # Optional override name for the fork


class QuoteTemplateLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_template_id: UUID
    tenant_id: UUID | None
    qco_line_type_id: UUID
    description: str
    default_quantity: Decimal
    default_unit_price_cents: int
    customer_visible: bool
    is_section_header: bool
    display_order: int
    parent_line_id: UUID | None
    is_active: bool


class QuoteTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None
    name: str
    style: str
    category: str | None
    description: str | None
    is_system_template: bool
    current_version: int
    system_template_id: UUID | None
    forked_from_version: int | None
    is_active: bool
    lines: list[QuoteTemplateLineResponse] = []


class QuoteFromTemplateRequest(BaseModel):
    customer_id: UUID
    site_id: UUID
    variable_overrides: dict = {}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: substitute template variables
# ─────────────────────────────────────────────────────────────────────────────

_TEMPLATE_VAR_RE = re.compile(r"\{(\w+)\}")


def _substitute_variables(text: str, ctx: dict) -> str:
    """Replace {variable} placeholders with values from ctx dict."""

    def _replace(m: re.Match) -> str:
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))  # keep original if unknown

    return _TEMPLATE_VAR_RE.sub(_replace, text)


# ─────────────────────────────────────────────────────────────────────────────
# A25 Shared _impl() Functions
# ─────────────────────────────────────────────────────────────────────────────


def _list_quote_templates_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    style: str | None = None,
    category: str | None = None,
    system_only: bool = False,
    tenant_only: bool = False,
) -> list[QuoteTemplateResponse]:
    """Shared logic for listing quote templates."""
    stmt = select(QuoteTemplate).where(QuoteTemplate.is_active == True)

    if system_only:
        stmt = stmt.where(QuoteTemplate.tenant_id == None)
    elif tenant_only:
        stmt = stmt.where(QuoteTemplate.tenant_id == user_context.tenant_id)
    else:
        stmt = stmt.where(
            (QuoteTemplate.tenant_id == None)
            | (QuoteTemplate.tenant_id == user_context.tenant_id)
        )

    if style:
        stmt = stmt.where(QuoteTemplate.style == style)
    if category:
        stmt = stmt.where(QuoteTemplate.category == category)

    templates = db.exec(stmt).all()

    result = []
    for t in templates:
        lines = db.exec(
            select(QuoteTemplateLine)
            .where(QuoteTemplateLine.quote_template_id == t.id)
            .where(QuoteTemplateLine.is_active == True)
            .order_by(QuoteTemplateLine.display_order)
        ).all()
        resp = QuoteTemplateResponse.model_validate(t)
        resp.lines = [QuoteTemplateLineResponse.model_validate(line) for line in lines]
        result.append(resp)

    return result


def _create_quote_template_impl(
    payload: QuoteTemplateCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteTemplateResponse:
    """Shared logic for creating a tenant quote template."""
    valid_styles = {"component", "deliverable", "lump_sum"}
    if payload.style not in valid_styles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Invalid Style",
                "status": 422,
                "detail": f"style must be one of: {', '.join(valid_styles)}",
            },
        )

    existing = db.exec(
        select(QuoteTemplate).where(
            QuoteTemplate.tenant_id == user_context.tenant_id,
            QuoteTemplate.name == payload.name,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Duplicate Template Name",
                "status": 422,
                "detail": f"A template named '{payload.name}' already exists for this tenant.",
            },
        )

    template = QuoteTemplate(
        tenant_id=user_context.tenant_id,
        name=payload.name,
        style=payload.style,
        category=payload.category,
        description=payload.description,
        current_version=1,
        is_system_template=False,
        is_active=True,
        created_by=user_context.id,
        updated_by=user_context.id,
    )
    db.add(template)
    db.flush()

    lines = []
    for line_in in payload.lines:
        line = QuoteTemplateLine(
            tenant_id=user_context.tenant_id,
            quote_template_id=template.id,
            qco_line_type_id=line_in.qco_line_type_id,
            description=line_in.description,
            default_quantity=line_in.default_quantity,
            default_unit_price_cents=line_in.default_unit_price_cents,
            customer_visible=line_in.customer_visible,
            is_section_header=line_in.is_section_header,
            display_order=line_in.display_order,
            parent_line_id=line_in.parent_line_id,
            is_active=True,
            created_by=user_context.id,
            updated_by=user_context.id,
        )
        db.add(line)
        lines.append(line)

    content_json = [
        {
            "id": str(line.id),
            "qco_line_type_id": str(line.qco_line_type_id),
            "description": line.description,
            "default_unit_price_cents": line.default_unit_price_cents,
            "default_quantity": str(line.default_quantity)
            if line.default_quantity
            else None,
            "display_order": line.display_order,
            "customer_visible": line.customer_visible,
            "is_section_header": line.is_section_header,
            "is_active": line.is_active,
        }
        for line in lines
    ]
    template_version = QuoteTemplateVersion(
        template_id=template.id,
        version_no=1,
        content_json=content_json,
        changelog="Initial version",
        created_by=user_context.id,
    )
    db.add(template_version)
    db.commit()
    db.refresh(template)

    resp = QuoteTemplateResponse.model_validate(template)
    resp.lines = [QuoteTemplateLineResponse.model_validate(line) for line in lines]
    return resp


def _fork_quote_template_impl(
    id: UUID,
    payload: QuoteTemplateForkRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteTemplateResponse:
    """Shared logic for forking a system template."""
    source = db.exec(
        select(QuoteTemplate)
        .where(QuoteTemplate.id == id)
        .where(QuoteTemplate.is_active == True)
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Template not found")

    if not source.is_system_template:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Not a System Template",
                "status": 422,
                "detail": "Only system templates can be forked. Tenant templates can be duplicated directly.",
            },
        )

    fork_name = payload.name or f"{source.name} (Custom)"

    existing = db.exec(
        select(QuoteTemplate).where(
            QuoteTemplate.tenant_id == user_context.tenant_id,
            QuoteTemplate.name == fork_name,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Duplicate Template Name",
                "status": 422,
                "detail": f"A template named '{fork_name}' already exists for this tenant.",
            },
        )

    forked = QuoteTemplate(
        tenant_id=user_context.tenant_id,
        name=fork_name,
        style=source.style,
        category=source.category,
        description=source.description,
        system_template_id=source.id,
        forked_from_version=source.current_version,
        current_version=1,
        is_system_template=False,
        is_active=True,
        created_by=user_context.id,
        updated_by=user_context.id,
    )
    db.add(forked)
    db.flush()

    source_lines = db.exec(
        select(QuoteTemplateLine)
        .where(QuoteTemplateLine.quote_template_id == source.id)
        .where(QuoteTemplateLine.is_active == True)
        .order_by(QuoteTemplateLine.display_order)
    ).all()

    forked_lines = []
    for sl in source_lines:
        nl = QuoteTemplateLine(
            tenant_id=user_context.tenant_id,
            quote_template_id=forked.id,
            qco_line_type_id=sl.qco_line_type_id,
            description=sl.description,
            default_quantity=sl.default_quantity,
            default_unit_price_cents=sl.default_unit_price_cents,
            customer_visible=sl.customer_visible,
            is_section_header=sl.is_section_header,
            display_order=sl.display_order,
            parent_line_id=None,
            is_active=True,
            created_by=user_context.id,
            updated_by=user_context.id,
        )
        db.add(nl)
        forked_lines.append(nl)

    db.commit()
    db.refresh(forked)

    resp = QuoteTemplateResponse.model_validate(forked)
    resp.lines = [
        QuoteTemplateLineResponse.model_validate(line) for line in forked_lines
    ]
    return resp


def _disable_quote_template_impl(
    id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteTemplateResponse:
    """Shared logic for soft-disabling a quote template."""
    template = db.exec(
        select(QuoteTemplate)
        .where(QuoteTemplate.id == id)
        .where(QuoteTemplate.tenant_id == user_context.tenant_id)
        .where(QuoteTemplate.is_active == True)
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.is_active = False
    template.updated_by = user_context.id
    db.add(template)
    db.commit()
    db.refresh(template)

    resp = QuoteTemplateResponse.model_validate(template)
    resp.lines = []
    return resp


def _create_quote_from_template_impl(
    template_id: UUID,
    payload: QuoteFromTemplateRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Shared logic for creating a quote from a template."""
    template = db.exec(
        select(QuoteTemplate)
        .where(QuoteTemplate.id == template_id)
        .where(QuoteTemplate.is_active == True)
        .where(
            (QuoteTemplate.tenant_id == None)
            | (QuoteTemplate.tenant_id == user_context.tenant_id)
        )
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    customer = db.exec(
        select(Customer)
        .where(Customer.id == payload.customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    site = db.exec(
        select(Site)
        .where(Site.id == payload.site_id)
        .where(Site.tenant_id == user_context.tenant_id)
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    draft_status = db.exec(
        select(QuoteStatus).where(QuoteStatus.code == "draft")
    ).first()
    if not draft_status:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Draft status not found in quote_status table",
        )

    now = datetime.now(UTC)
    var_ctx = {
        "customer_name": customer.display_name or "",
        "customer_first_name": (customer.display_name or "").split(" ")[0],
        "site_address": getattr(site, "address_line_1", "") or "",
        "quote_date": now.strftime("%Y-%m-%d"),
        **payload.variable_overrides,
    }

    quote = Quote(
        tenant_id=user_context.tenant_id,
        customer_id=payload.customer_id,
        site_id=payload.site_id,
        status_id=draft_status.id,
        currency="USD",
        created_by=user_context.id,
        updated_by=user_context.id,
    )
    db.add(quote)
    db.flush()

    template_lines = db.exec(
        select(QuoteTemplateLine)
        .where(QuoteTemplateLine.quote_template_id == template.id)
        .where(QuoteTemplateLine.is_active == True)
        .order_by(QuoteTemplateLine.display_order)
    ).all()

    for pos, tl in enumerate(template_lines, start=1):
        qco = db.exec(
            select(QcoLineType).where(QcoLineType.id == tl.qco_line_type_id)
        ).first()
        if not qco:
            continue

        ql = QuoteLine(
            tenant_id=user_context.tenant_id,
            quote_id=quote.id,
            position=pos,
            display_order=tl.display_order,
            qco_line_type_id=tl.qco_line_type_id,
            description=_substitute_variables(tl.description, var_ctx),
            quantity=tl.default_quantity,
            unit_price_cents=tl.default_unit_price_cents,
            subtotal_cents=int(tl.default_quantity * tl.default_unit_price_cents),
            total_cents=int(tl.default_quantity * tl.default_unit_price_cents),
            customer_visible=tl.customer_visible,
            is_section_header=tl.is_section_header,
            is_active=True,
            created_by=user_context.id,
            updated_by=user_context.id,
        )
        db.add(ql)

    db.commit()
    db.refresh(quote)

    return {
        "quote_id": str(quote.id),
        "status": "draft",
        "customer_id": str(quote.customer_id),
        "site_id": str(quote.site_id),
        "template_id": str(template_id),
        "lines_created": len(template_lines),
    }


# ─────────────────────────────────────────────────────────────────────────────
# A25 TEST ENDPOINTS (register BEFORE authenticated endpoints)
# Route ordering: POST /test before POST /{id}/fork, POST /{id}/disable
#                 POST /from-template/{template_id}/test before POST /from-template/{template_id}
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/test",
    response_model=list[QuoteTemplateResponse],
    summary="List quote templates (TEST — no auth)",
    tags=["quote-templates"],
)
def list_quote_templates_test(
    style: str | None = Query(None),
    category: str | None = Query(None),
    system_only: bool = Query(False),
    tenant_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _list_quote_templates_impl(
        db,
        test_context,
        style=style,
        category=category,
        system_only=system_only,
        tenant_only=tenant_only,
    )


@router.post(
    "/test",
    response_model=QuoteTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant quote template (TEST — no auth)",
    tags=["quote-templates"],
)
def create_quote_template_test(
    payload: QuoteTemplateCreate,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_quote_template_impl(payload, db, test_context)


@router.post(
    "/from-template/{template_id}/test",
    summary="Create a quote from a template (TEST — no auth)",
    tags=["quote-templates"],
    status_code=status.HTTP_201_CREATED,
)
def create_quote_from_template_test(
    template_id: UUID,
    payload: QuoteFromTemplateRequest,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_quote_from_template_impl(template_id, payload, db, test_context)


@router.post(
    "/{id}/fork/test",
    response_model=QuoteTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fork a system template (TEST — no auth)",
    tags=["quote-templates"],
)
def fork_quote_template_test(
    id: UUID,
    payload: QuoteTemplateForkRequest,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _fork_quote_template_impl(id, payload, db, test_context)


@router.post(
    "/{id}/disable/test",
    response_model=QuoteTemplateResponse,
    summary="Soft-disable a quote template (TEST — no auth)",
    tags=["quote-templates"],
)
def disable_quote_template_test(
    id: UUID,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _disable_quote_template_impl(id, db, test_context)


# ─────────────────────────────────────────────────────────────────────────────
# A25 AUTHENTICATED ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[QuoteTemplateResponse],
    summary="List quote templates",
    tags=["quote-templates"],
)
def list_quote_templates(
    style: str | None = Query(None),
    category: str | None = Query(None),
    system_only: bool = Query(False),
    tenant_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
):
    """
    A25: List quote templates accessible to the current tenant.
    RBAC: quotes.view permission.
    """
    return _list_quote_templates_impl(
        db,
        current_user,
        style=style,
        category=category,
        system_only=system_only,
        tenant_only=tenant_only,
    )


@router.post(
    "",
    response_model=QuoteTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant quote template",
    tags=["quote-templates"],
)
def create_quote_template(
    payload: QuoteTemplateCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("quote_template.create")
    ),
):
    """A25: Create a new tenant-owned quote template. RBAC: quote_template.create."""
    return _create_quote_template_impl(payload, db, current_user)


@router.post(
    "/{id}/fork",
    response_model=QuoteTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fork a system template into a tenant copy",
    tags=["quote-templates"],
)
def fork_quote_template(
    id: UUID,
    payload: QuoteTemplateForkRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("quote_template.fork_system")
    ),
):
    """A25: Fork a system template into a tenant-owned copy. RBAC: quote_template.fork_system."""
    return _fork_quote_template_impl(id, payload, db, current_user)


@router.post(
    "/{id}/disable",
    response_model=QuoteTemplateResponse,
    summary="Soft-disable a quote template",
    tags=["quote-templates"],
)
def disable_quote_template(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("quote_template.edit")
    ),
):
    """A25: Soft-disable a tenant-owned quote template. RBAC: quote_template.edit."""
    return _disable_quote_template_impl(id, db, current_user)


@router.post(
    "/from-template/{template_id}",
    summary="Instantiate a new quote from a template",
    tags=["quote-templates"],
    status_code=status.HTTP_201_CREATED,
)
def create_quote_from_template(
    template_id: UUID,
    payload: QuoteFromTemplateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.create")),
):
    """A25: Create a new quote pre-populated with lines from a template. RBAC: quotes.create."""
    return _create_quote_from_template_impl(template_id, payload, db, current_user)
