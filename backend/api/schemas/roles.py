"""
Pydantic schemas for RBAC role management API.

These schemas define request/response models for role-related endpoints.

Related:
- API Routes: backend/api/routes/roles.py
- Permission Module: backend/core/permissions.py
- Role Model: backend/app/models/auth.py:14 (TenantUserRole)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleResponse(BaseModel):
    """
    Role definition with permissions.

    Used for listing available roles to users.
    """

    code: str = Field(..., description="Unique role code (e.g., 'owner', 'technician')")
    name: str = Field(..., description="Human-readable role name")
    description: str | None = Field(None, description="Role description")
    permissions: list[str] = Field(
        ..., description="List of permissions granted by this role"
    )
    is_default: bool = Field(..., description="Whether this is a default role")
    is_active: bool = Field(..., description="Whether this role is active")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "code": "office_staff",
                "name": "Office Staff",
                "description": "Manages customers, quotes, and administrative tasks",
                "permissions": ["customers.*", "quotes.*", "sites.*", "invoices.view"],
                "is_default": False,
                "is_active": True,
            }
        },
    )


class UserPermissionsResponse(BaseModel):
    """
    Current user's permissions (self-service endpoint).

    Returns the authenticated user's role and permissions.
    """

    user_id: uuid.UUID = Field(..., description="User's unique identifier")
    tenant_id: uuid.UUID = Field(..., description="User's active tenant")
    role_code: str = Field(..., description="User's current role code")
    role_name: str = Field(..., description="User's current role name")
    permissions: list[str] = Field(..., description="User's effective permissions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
                "role_code": "owner",
                "role_name": "Owner",
                "permissions": [
                    "*",
                    "users.manage",
                    "users.view",
                    "integrations.manage",
                ],
            }
        }
    )


class RoleAssignmentRequest(BaseModel):
    """
    Request to assign a role to a user.

    Used by owners to change user roles within their tenant.
    """

    role_code: str = Field(
        ..., description="Role code to assign (must be valid role)", pattern="^[a-z_]+$"
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"role_code": "technician"}}
    )


class TenantUserWithRoleResponse(BaseModel):
    """
    Tenant user with role information.

    Used for listing all users in a tenant with their roles.
    """

    user_id: uuid.UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    role_code: str = Field(..., description="User's assigned role code")
    role_name: str = Field(..., description="User's role name")
    permissions: list[str] = Field(..., description="User's effective permissions")
    joined_at: datetime | None = Field(None, description="When user joined the tenant")
    is_active: bool = Field(..., description="Whether user is active in tenant")
    first_name: str | None = Field(None, description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    display_color: str | None = Field(
        None, description="User's avatar display color (hex or named)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "tech@example.com",
                "role_code": "technician",
                "role_name": "Field Technician",
                "permissions": ["jobs.view", "jobs.update", "time_entries.create"],
                "joined_at": "2026-01-15T10:30:00Z",
                "is_active": True,
                "first_name": "John",
                "last_name": "Smith",
                "display_color": "#4F86C6",
            }
        }
    )


class RoleAssignmentResponse(BaseModel):
    """
    Response after assigning a role to a user.

    Confirms the role assignment operation.
    """

    user_id: uuid.UUID = Field(..., description="User who received the role")
    tenant_id: uuid.UUID = Field(..., description="Tenant context")
    role_code: str = Field(..., description="Role that was assigned")
    role_name: str = Field(..., description="Role name")
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
                "role_code": "technician",
                "role_name": "Field Technician",
                "message": "Role successfully assigned to user",
            }
        }
    )


class PermissionCheckRequest(BaseModel):
    """
    Request to check if user has a specific permission.

    Used for UI conditional rendering (e.g., show/hide buttons).
    """

    permission: str = Field(
        ...,
        description="Permission to check (e.g., 'quotes.create')",
        pattern="^[a-z_]+\\.[a-z_]+$|^\\*$|^[a-z_]+\\.\\*$|^\\*\\.[a-z_]+$",
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"permission": "quotes.create"}}
    )


class PermissionCheckResponse(BaseModel):
    """
    Response indicating whether user has a permission.
    """

    permission: str = Field(..., description="Permission that was checked")
    has_permission: bool = Field(..., description="Whether user has this permission")
    user_role: str = Field(..., description="User's current role")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "permission": "quotes.create",
                "has_permission": True,
                "user_role": "office_staff",
            }
        }
    )
