"""
Pydantic v2 schemas for team invite API endpoints.

Related:
- API Routes: backend/api/routes/team_invites.py
- Service: backend/services/team_invite_service.py
- Model: backend/app/models/auth.py (TenantUserInvite)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TeamInviteCreateRequest(BaseModel):
    """Request to create a new team invite."""

    email: EmailStr = Field(..., description="Email address of the invitee")
    role_code: str = Field(
        ...,
        description="Role code to assign (owner, technician, office_staff, accountant)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "newguy@example.com", "role_code": "technician"}
        }
    )


class TeamInviteResponse(BaseModel):
    """Response after creating or resending an invite. Never includes the raw token."""

    id: uuid.UUID = Field(..., description="Invite ID")
    email: str = Field(..., description="Invitee email address")
    role_code: str | None = Field(None, description="Role code assigned at invite time")
    expires_at: datetime = Field(..., description="When the invite expires")
    created_at: datetime = Field(..., description="When the invite was created")

    model_config = ConfigDict(from_attributes=True)


class TeamInviteListItem(BaseModel):
    """List item for the invites endpoint, with computed status."""

    id: uuid.UUID = Field(..., description="Invite ID")
    email: str = Field(..., description="Invitee email address")
    role_code: str | None = Field(None, description="Role code assigned at invite time")
    invited_by: uuid.UUID | None = Field(None, description="User who sent the invite")
    created_at: datetime = Field(..., description="When the invite was created")
    expires_at: datetime = Field(..., description="When the invite expires")
    accepted_at: datetime | None = Field(
        None, description="When the invite was accepted"
    )
    is_active: bool = Field(..., description="Whether the invite is still active")
    status: str = Field(
        ..., description="Computed status: accepted, revoked, expired, or pending"
    )

    model_config = ConfigDict(from_attributes=True)


class TeamInviteResendResponse(BaseModel):
    """Response after resending an invite."""

    id: uuid.UUID = Field(..., description="Invite ID")
    email: str = Field(..., description="Invitee email address")
    expires_at: datetime = Field(..., description="New expiry time after resend")

    model_config = ConfigDict(from_attributes=True)


class TeamInviteRevokeResponse(BaseModel):
    """Response after revoking an invite."""

    id: uuid.UUID = Field(..., description="Invite ID")
    is_active: bool = Field(..., description="Always false after revoke")

    model_config = ConfigDict(from_attributes=True)


class TeamInvitePublicResponse(BaseModel):
    """Public response for the invite landing page (no auth required)."""

    tenant_name: str = Field(..., description="Name of the inviting tenant")
    email: str = Field(..., description="Invitee email address")
    role_code: str | None = Field(None, description="Role code assigned at invite time")
    expires_at: datetime = Field(..., description="When the invite expires")

    model_config = ConfigDict(from_attributes=True)
