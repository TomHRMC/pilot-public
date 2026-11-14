"""C-B15 — Operator tenant impersonation Pydantic schemas (request/response).

Separate from the SQLModel ORM classes in app/models/.  These schemas define
the API contract consumed by the React frontend (Part B).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OperatorTenantSummary(BaseModel):
    """A single tenant row in the operator tenant selector."""

    model_config = ConfigDict(from_attributes=True)
    tenant_id: UUID
    name: str
    is_active: bool
    tier_name: str | None
    subscription_status: str | None
    created_at: datetime


class OperatorTenantListResponse(BaseModel):
    """Response for GET /api/v1/operator/tenants — tenant selector source."""

    model_config = ConfigDict(from_attributes=True)
    tenants: list[OperatorTenantSummary]


class ImpersonationStartRequest(BaseModel):
    """Request body for POST /api/v1/operator/impersonation/start."""

    tenant_id: UUID


class ImpersonationEndRequest(BaseModel):
    """Request body for POST /api/v1/operator/impersonation/end."""

    tenant_id: UUID


class ImpersonationSessionResponse(BaseModel):
    """Response for POST /api/v1/operator/impersonation/start."""

    model_config = ConfigDict(from_attributes=True)
    tenant_id: UUID
    tenant_name: str
    impersonator_user_id: UUID
    role_code: str
    started_at: datetime


class ImpersonationEndResponse(BaseModel):
    """Response for POST /api/v1/operator/impersonation/end."""

    ended: bool = True
