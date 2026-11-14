"""
RBAC Role Management API

Endpoints for managing user roles and permissions within a tenant.

Key Features:
- List available roles (all users)
- Get current user's permissions (self-service)
- Assign roles to users (owner only)
- List tenant users with roles (owner/office_staff)
- Check specific permissions (UI conditional rendering)

Security:
- All endpoints require authentication
- Role assignment requires "users.manage" permission (owner only)
- User listing requires "users.view" permission
- Tenant isolation enforced (users can only see their tenant's users)

Related:
- Permission Module: backend/core/permissions.py
- Schemas: backend/api/schemas/roles.py
- Auth: backend/core/auth.py
- Migration: backend/migrations/versions/2026_03_27_2350_seed_default_rbac_roles.py
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.schemas.roles import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    RoleResponse,
    TenantUserWithRoleResponse,
    UserPermissionsResponse,
)
from app.models.auth import TenantUser, TenantUserRole
from app.models.core import User
from core.auth import AuthenticatedUser, get_current_user
from core.db import get_db
from core.permissions import check_permission, require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter(prefix="/api/v1", tags=["roles"])


# ==================== SHARED _impl() FUNCTIONS ====================


def _list_roles_impl(db: Session) -> list[RoleResponse]:
    """Shared logic for listing all active roles (global — not tenant-scoped)."""
    statement = select(TenantUserRole).where(TenantUserRole.is_active == True)
    roles = db.exec(statement).all()
    return [
        RoleResponse(
            code=role.code,
            name=role.name,
            description=role.description,
            permissions=role.permissions if isinstance(role.permissions, list) else [],
            is_default=role.is_default,
            is_active=role.is_active,
        )
        for role in roles
    ]


def _get_my_permissions_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> UserPermissionsResponse:
    """Shared logic for getting the current user's permissions."""
    # TestUserContext has no role_code/permissions — return sensible defaults
    if isinstance(user_context, TestUserContext):
        return UserPermissionsResponse(
            user_id=user_context.id,
            tenant_id=user_context.tenant_id,
            role_code="test_user",
            role_name="Test User",
            permissions=[],
        )

    role = db.exec(
        select(TenantUserRole).where(TenantUserRole.code == user_context.role_code)
    ).first()
    role_name = role.name if role else user_context.role_code

    return UserPermissionsResponse(
        user_id=user_context.id,
        tenant_id=user_context.tenant_id,
        role_code=user_context.role_code,
        role_name=role_name,
        permissions=user_context.permissions,
    )


def _assign_role_impl(
    user_id: uuid.UUID,
    role_assignment: RoleAssignmentRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> RoleAssignmentResponse:
    """Shared logic for assigning a role to a user."""
    tenant_user = db.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == user_context.tenant_id)
        .where(TenantUser.user_id == user_id)
        .where(TenantUser.is_active == True)
    ).first()

    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your tenant or is inactive",
        )

    role = db.exec(
        select(TenantUserRole)
        .where(TenantUserRole.code == role_assignment.role_code)
        .where(TenantUserRole.is_active == True)
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_assignment.role_code}' not found or is inactive",
        )

    if tenant_user.role_code == "owner" and role_assignment.role_code != "owner":
        owner_count = db.exec(
            select(TenantUser)
            .where(TenantUser.tenant_id == user_context.tenant_id)
            .where(TenantUser.role_code == "owner")
            .where(TenantUser.is_active == True)
        ).all()
        if len(owner_count) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner from the tenant. Assign another owner first.",
            )

    tenant_user.role_code = role_assignment.role_code
    tenant_user.updated_at = datetime.now(UTC)
    db.add(tenant_user)
    db.commit()
    db.refresh(tenant_user)

    return RoleAssignmentResponse(
        user_id=user_id,
        tenant_id=user_context.tenant_id,
        role_code=role.code,
        role_name=role.name,
        message=f"Role '{role.name}' successfully assigned to user. User must re-authenticate to see new permissions.",
    )


def _list_tenant_users_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[TenantUserWithRoleResponse]:
    """Shared logic for listing all users in the current tenant with their roles."""
    statement = (
        select(TenantUser, User, TenantUserRole)
        .join(User, TenantUser.user_id == User.id)
        .join(TenantUserRole, TenantUser.role_code == TenantUserRole.code)
        .where(TenantUser.tenant_id == user_context.tenant_id)
        .where(TenantUser.is_active == True)
        .where(User.is_active == True)
    )
    results = db.exec(statement).all()
    return [
        TenantUserWithRoleResponse(
            user_id=tenant_user.user_id,
            email=user.email,
            role_code=role.code,
            role_name=role.name,
            permissions=role.permissions if isinstance(role.permissions, list) else [],
            joined_at=tenant_user.joined_at,
            is_active=tenant_user.is_active,
            first_name=user.first_name,
            last_name=user.last_name,
            display_color=user.display_color,
        )
        for tenant_user, user, role in results
    ]


def _check_user_permission_impl(
    permission_check: PermissionCheckRequest,
    user_context: AuthenticatedUser | TestUserContext,
) -> PermissionCheckResponse:
    """Shared logic for checking if the current user has a specific permission."""
    # TestUserContext has no permissions — always returns False for test context
    if isinstance(user_context, TestUserContext):
        return PermissionCheckResponse(
            permission=permission_check.permission,
            has_permission=False,
            user_role="test_user",
        )

    has_perm = check_permission(user_context, permission_check.permission)
    return PermissionCheckResponse(
        permission=permission_check.permission,
        has_permission=has_perm,
        user_role=user_context.role_code,
    )


# ==================== TEST ENDPOINTS (register BEFORE authenticated) ====================


@router.get("/roles/test", response_model=list[RoleResponse])
def list_roles_test(db: Session = Depends(get_db)) -> list[RoleResponse]:
    """List all available roles (TEST ENDPOINT — no auth required)."""
    get_test_context()  # Raises 403 if disabled
    return _list_roles_impl(db)


@router.get("/users/me/permissions/test", response_model=UserPermissionsResponse)
def get_my_permissions_test(db: Session = Depends(get_db)) -> UserPermissionsResponse:
    """Get current user's permissions (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _get_my_permissions_impl(test_context, db)


@router.get("/users/test", response_model=list[TenantUserWithRoleResponse])
def list_tenant_users_test(
    db: Session = Depends(get_db),
) -> list[TenantUserWithRoleResponse]:
    """List all users in the test tenant (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _list_tenant_users_impl(db, test_context)


@router.post("/users/{user_id}/role/test", response_model=RoleAssignmentResponse)
def assign_role_test(
    user_id: uuid.UUID,
    role_assignment: RoleAssignmentRequest,
    db: Session = Depends(get_db),
) -> RoleAssignmentResponse:
    """Assign a role to a user (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _assign_role_impl(user_id, role_assignment, db, test_context)


@router.post("/permissions/check/test", response_model=PermissionCheckResponse)
def check_user_permission_test(
    permission_check: PermissionCheckRequest,
) -> PermissionCheckResponse:
    """Check if test user has a specific permission (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _check_user_permission_impl(permission_check, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[RoleResponse]:
    """List all available roles. Any authenticated user can view."""
    return _list_roles_impl(db)


@router.get("/users/me/permissions", response_model=UserPermissionsResponse)
def get_my_permissions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPermissionsResponse:
    """Get current user's role and permissions (self-service)."""
    return _get_my_permissions_impl(current_user, db)


@router.post("/users/{user_id}/role", response_model=RoleAssignmentResponse)
def assign_role(
    user_id: uuid.UUID,
    role_assignment: RoleAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("users.manage")),
) -> RoleAssignmentResponse:
    """Assign a role to a user. RBAC: users.manage."""
    return _assign_role_impl(user_id, role_assignment, db, current_user)


@router.get("/users", response_model=list[TenantUserWithRoleResponse])
def list_tenant_users(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("users.view")),
) -> list[TenantUserWithRoleResponse]:
    """List all users in tenant with roles. RBAC: users.view."""
    return _list_tenant_users_impl(db, current_user)


@router.post("/permissions/check", response_model=PermissionCheckResponse)
def check_user_permission(
    permission_check: PermissionCheckRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PermissionCheckResponse:
    """Check if current user has a specific permission (in-memory check)."""
    return _check_user_permission_impl(permission_check, current_user)


# Export router
__all__ = ["router"]
