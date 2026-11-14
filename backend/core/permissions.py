"""
RBAC Permission System for Pilot for Trades

This module implements Role-Based Access Control (RBAC) permission checking
with wildcard support for flexible authorization.

Permission Format: resource.action
  - resource: Entity type (customers, quotes, jobs, etc.)
  - action: Operation (create, view, update, delete)

Wildcard Support:
  - "*" = All permissions (owner role)
  - "customers.*" = All actions on customers
  - "*.view" = View action on all resources
  - "quotes.create" = Specific action on specific resource

Example Usage:
    from core.permissions import require_permission

    @router.post("/quotes")
    @require_permission("quotes.create")
    def create_quote(
        current_user: AuthenticatedUser = Depends(get_current_user)
    ):
        # Only users with quotes.create permission can access this
        ...

Security Model:
  - Permissions are cached in AuthenticatedUser object (no DB queries per request)
  - Permission checks are in-memory list comparisons (< 1ms)
  - Tenant isolation enforced at authentication layer
  - Fail-safe: Missing role = deny access

Related:
  - TenantUserRole model: backend/app/models/auth.py:14
  - AuthenticatedUser: backend/core/auth.py:112
  - Role definitions: Migration 2026_03_28_seed_default_roles.py
"""

from collections.abc import Callable
from functools import wraps

# Type stub for AuthenticatedUser to avoid circular import
# Actual type is defined in core.auth
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status

if TYPE_CHECKING:
    from core.auth import AuthenticatedUser


def has_permission(user_permissions: list[str], required_permission: str) -> bool:
    """
    Check if user has the required permission with wildcard support.

    Matching precedence:
    1. Exact match ("quotes.create")
    2. Full wildcard ("*")
    3. Resource wildcard ("quotes.*")
    4. Action wildcard ("*.create")

    Args:
        user_permissions: List of permissions from user's role (e.g., ["jobs.view", "jobs.update"])
        required_permission: Permission to check (e.g., "quotes.create")

    Returns:
        True if user has permission, False otherwise

    Examples:
        >>> has_permission(["quotes.create"], "quotes.create")
        True

        >>> has_permission(["*"], "anything.action")
        True

        >>> has_permission(["quotes.*"], "quotes.create")
        True

        >>> has_permission(["*.view"], "quotes.view")
        True

        >>> has_permission(["jobs.view"], "quotes.create")
        False

    Performance:
        - In-memory list comparison (< 1ms)
        - No database queries
        - Permissions cached in AuthenticatedUser object
    """
    # 1. Check for exact match
    if required_permission in user_permissions:
        return True

    # 2. Check for full wildcard (owner role)
    if "*" in user_permissions:
        return True

    # 3. Parse required permission for wildcard matching
    # Handle edge case: permission without dot separator
    if "." not in required_permission:
        return False

    resource, action = required_permission.split(".", 1)

    # 4. Check for resource wildcard (e.g., "quotes.*")
    if f"{resource}.*" in user_permissions:
        return True

    # 5. Check for action wildcard (e.g., "*.view")
    if f"*.{action}" in user_permissions:
        return True

    # No match found
    return False


def get_permission_hint(required_permission: str) -> str:
    """
    Generate a helpful hint for users who lack a permission.

    Args:
        required_permission: The permission that was required

    Returns:
        User-friendly hint about which role to request

    Examples:
        >>> get_permission_hint("quotes.create")
        "Contact your administrator to request the 'office_staff' or 'owner' role"

        >>> get_permission_hint("time_entries.create")
        "Contact your administrator to request the 'technician' or 'owner' role"
    """
    # Map common permissions to roles that have them
    permission_to_roles = {
        "quotes": ["office_staff", "owner"],
        "customers": ["office_staff", "owner"],
        "sites": ["office_staff", "owner"],
        "invoices": ["office_staff", "owner"],
        "jobs": ["technician", "office_staff", "owner"],
        "time_entries": ["technician", "owner"],
        "expenses": ["technician", "owner"],
        "voice": ["technician", "owner"],
        "audit": ["accountant", "owner"],
        "users": ["owner"],
        "integrations": ["owner"],
    }

    # Extract resource from permission (e.g., "quotes" from "quotes.create")
    resource = (
        required_permission.split(".")[0]
        if "." in required_permission
        else required_permission
    )

    # Get roles that typically have this permission
    suggested_roles = permission_to_roles.get(resource, ["owner"])

    if len(suggested_roles) == 1:
        return f"Contact your administrator to request the '{suggested_roles[0]}' role"
    else:
        roles_str = "', '".join(suggested_roles[:-1]) + f"' or '{suggested_roles[-1]}"
        return f"Contact your administrator to request the '{roles_str}' role"


class PermissionDeniedError(HTTPException):
    """
    Custom exception for permission denied errors.

    Follows RFC 7807 Problem Details format with additional context
    for debugging and user guidance.
    """

    def __init__(
        self,
        required_permission: str,
        user_permissions: list[str],
        user_role: str | None = None,
    ):
        """
        Initialize permission denied error with helpful context.

        Args:
            required_permission: The permission that was required
            user_permissions: The permissions the user actually has
            user_role: The user's current role code (e.g., "technician")
        """
        detail = {
            "type": "https://pilotfortrades.com/errors/forbidden",
            "title": "Insufficient Permissions",
            "status": 403,
            "detail": "You do not have permission to perform this action",
            "required_permission": required_permission,
            "user_permissions": user_permissions,
            "user_role": user_role,
            "hint": get_permission_hint(required_permission),
        }

        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_permission(
    required_permission: str,
    feature_code: str | None = None,
) -> Callable:
    """
    Dependency factory for FastAPI routes: enforces RBAC then (optionally)
    feature-entitlement checks.

    Step 1 — RBAC string check
        Validates ``current_user.permissions`` against ``required_permission``
        using wildcard matching.  Raises **403 Forbidden** on failure.

    Step 2 — Feature entitlement (optional)
        When ``feature_code`` is supplied, calls the Redis-backed entitlement
        service to confirm the tenant is within their plan limits.
        Raises **402 Payment Required** on failure with a structured payload
        that the React frontend can parse to show an "Upgrade Plan" modal.

    Args:
        required_permission : RBAC string, e.g. ``"quotes.create"``
        feature_code        : Optional product feature code to enforce, e.g.
                              ``"schedule_lanes"``

    Returns:
        FastAPI-compatible dependency callable

    Error Responses:
        403 Forbidden (RBAC failure)::

            {
                "type": "https://pilotfortrades.com/errors/forbidden",
                "title": "Insufficient Permissions",
                "status": 403,
                ...
            }

        402 Payment Required (entitlement failure)::

            {
                "error": "usage_limit_exceeded",
                "feature": "schedule_lanes",
                "limit": 5,
                "used": 5
            }

    Performance:
        - RBAC check : in-memory, < 1 ms
        - Entitlement : Redis HIT ~1 ms, DB MISS ~5 ms

    Security:
        - Runs after authentication (requires valid JWT)
        - Tenant isolation enforced at auth layer
        - Fail-safe: missing permissions = deny access
    """
    # Import here to avoid circular dependency
    from sqlmodel import Session

    from core.auth import get_current_user
    from core.db import get_db

    def permission_checker(
        current_user: "AuthenticatedUser" = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> "AuthenticatedUser":
        """
        FastAPI dependency: authenticate → RBAC → entitlement.

        Args:
            current_user : Injected by ``get_current_user``
            db           : Injected by ``get_db`` (only used when feature_code set)

        Returns:
            AuthenticatedUser if all checks pass

        Raises:
            PermissionDeniedError (403) : RBAC failure
            HTTPException (402)         : Plan / usage-limit exceeded
        """
        # ── Step 1: RBAC ────────────────────────────────────────────────────
        if not has_permission(current_user.permissions, required_permission):
            raise PermissionDeniedError(
                required_permission=required_permission,
                user_permissions=current_user.permissions,
                user_role=current_user.role_code,
            )

        # ── Step 2: Feature entitlement ─────────────────────────────────────
        if feature_code is not None:
            from services.entitlement_service import get_cached_entitlement

            result = get_cached_entitlement(
                tenant_id=current_user.tenant_id,
                feature_code=feature_code,
                db=db,
            )
            if not result.is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": result.reason,
                        "feature": feature_code,
                        "limit": result.limit,
                        "used": result.used,
                    },
                )

        return current_user

    return permission_checker


# Convenience decorator that combines authentication + permission check
def require_permission_decorator(required_permission: str):
    """
    Alternative decorator syntax for permission checks (syntactic sugar).

    This provides a more traditional decorator syntax as an alternative to
    using Depends(require_permission(...)) in the route signature.

    Args:
        required_permission: Permission to require (e.g., "quotes.create")

    Usage:
        @router.post("/quotes")
        @require_permission_decorator("quotes.create")
        def create_quote(
            current_user: AuthenticatedUser = Depends(get_current_user)
        ):
            # Only users with quotes.create can access
            ...

    Note:
        This is syntactic sugar. The recommended approach is to use
        the dependency-based @require_permission() with Depends() for
        better FastAPI integration and automatic OpenAPI documentation.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (injected by FastAPI)
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication dependency not properly configured",
                )

            # Check permission
            if not has_permission(current_user.permissions, required_permission):
                raise PermissionDeniedError(
                    required_permission=required_permission,
                    user_permissions=current_user.permissions,
                    user_role=getattr(current_user, "role_code", None),
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Helper function for manual permission checks in business logic
def check_permission(
    current_user: "AuthenticatedUser", required_permission: str
) -> bool:
    """
    Manual permission check for use in business logic (non-decorator).

    Use this when you need conditional logic based on permissions
    rather than hard enforcement at the route level.

    Args:
        current_user: Authenticated user with permissions
        required_permission: Permission to check

    Returns:
        True if user has permission, False otherwise

    Usage:
        def get_quote(quote_id: UUID, current_user: AuthenticatedUser):
            quote = db.get(Quote, quote_id)

            # Show full details only if user can edit
            if check_permission(current_user, "quotes.update"):
                return quote  # Full details
            else:
                return QuotePublicView(quote)  # Limited view
    """
    return has_permission(current_user.permissions, required_permission)


# Export public API
__all__ = [
    "PermissionDeniedError",
    "check_permission",
    "get_permission_hint",
    "has_permission",
    "require_permission",
    "require_permission_decorator",
]
