import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserRole
from app.models.core import PlatformRole, Tenant, User
from core.config import settings
from core.db import get_db

security = HTTPBearer()

# C-B15 — Tenant impersonation header (platform users only).
IMPERSONATE_TENANT_HEADER = "x-impersonate-tenant"

# MFA-WIRE-1 — Cognito user-scoped MFA APIs need the user's ACCESS token.
COGNITO_ACCESS_TOKEN_HEADER = "x-cognito-access-token"
# Sentinel used by /test twins (they run on the mock client — no real token).
TEST_ACCESS_TOKEN_SENTINEL = "test-mock-access-token"


def get_cognito_access_token(request: Request) -> str:
    """Extract the ``X-Cognito-Access-Token`` header required by user-scoped
    Cognito MFA APIs. Raises 400 ``mfa_access_token_required`` (RFC 7807) if
    absent or empty.

    SECURITY: this value is use-in-memory-only — never log it, never persist
    it, never return it in any response (design §E).
    """
    token = request.headers.get(COGNITO_ACCESS_TOKEN_HEADER, "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/mfa-access-token-required",
                "title": "Cognito access token required",
                "status": 400,
                "detail": (
                    "The X-Cognito-Access-Token header is required for MFA "
                    "enrollment operations."
                ),
                "code": "mfa_access_token_required",
            },
        )
    return token


# JWKS cache with 1-hour TTL — prevents stale keys after Cognito key rotation.
# Reset to None in tests to force re-fetch: import core.auth; core.auth._jwks_cache = None
_jwks_cache = None
_jwks_cache_expires_at: datetime | None = None
_JWKS_TTL = timedelta(hours=1)


def get_jwks():
    global _jwks_cache, _jwks_cache_expires_at
    now = datetime.now(UTC)
    if _jwks_cache is None or (
        _jwks_cache_expires_at is not None and now >= _jwks_cache_expires_at
    ):
        # Construct the JWKS URL
        # e.g. https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/jwks.json
        region = settings.COGNITO_REGION
        user_pool_id = settings.COGNITO_USER_POOL_ID
        if not region or not user_pool_id:
            raise ValueError("Cognito configuration is missing")

        jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"

        with httpx.Client() as client:
            response = client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_expires_at = now + _JWKS_TTL
    return _jwks_cache


def verify_cognito_jwt(token: str) -> dict:
    # 1. Get unverified header to get the key ID (kid)
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No kid found in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Find the matching key in JWKS
    jwks = get_jwks()
    rsa_key = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = {
                "kty": key.get("kty"),
                "kid": key.get("kid"),
                "use": key.get("use"),
                "n": key.get("n"),
                "e": key.get("e"),
            }
            break

    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Public key not found in JWKS",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Construct public key and decode token
    try:
        public_key = RSAAlgorithm.from_jwk(rsa_key)
        # Cognito tokens require client_id or app_client_id if verifying audience.
        # We'll just verify signature and expiration for now,
        # or we could specify audience if we had COGNITO_APP_CLIENT_ID.
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Set to True if we add APP_CLIENT_ID check
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthenticatedUser(BaseModel):
    """
    Authenticated user with tenant context and RBAC permissions.

    This object is created by get_current_user() dependency after validating
    the JWT token and retrieving the user's role and permissions.

    Attributes:
        user: The User model instance
        tenant_id: The tenant the user is accessing
        role_code: The user's role code (e.g., "owner", "technician")
        permissions: List of permissions from the role (cached for performance)
        impersonator_user_id: Set when this context was built via tenant
            impersonation (C-B15). ``None`` for normal tenant users.

    Performance:
        - Permissions are cached here to avoid repeated DB queries
        - has_permission() is an in-memory check (< 1ms)

    Security:
        - Tenant isolation enforced at creation time
        - Permissions are read-only (cannot be modified after creation)
    """

    model_config = {"arbitrary_types_allowed": True}
    user: User
    tenant_id: uuid.UUID
    role_code: str
    permissions: list[str]
    impersonator_user_id: uuid.UUID | None = None

    @property
    def is_impersonated(self) -> bool:
        """Whether this context was built via tenant impersonation (C-B15)."""
        return self.impersonator_user_id is not None

    @property
    def id(self) -> uuid.UUID:
        """User ID (convenience property)"""
        return self.user.id

    @property
    def user_id(self) -> uuid.UUID:
        """Alias for id to match TestUserContext interface"""
        return self.user.id

    def has_permission(self, required_permission: str) -> bool:
        """
        Check if user has a specific permission.

        Convenience method that wraps the core permission checking logic.
        For route-level enforcement, use @require_permission() decorator instead.

        Args:
            required_permission: Permission to check (e.g., "quotes.create")

        Returns:
            True if user has permission, False otherwise

        Example:
            if current_user.has_permission("quotes.update"):
                # Show edit button
                ...
        """
        from core.permissions import has_permission

        return has_permission(self.permissions, required_permission)


def _try_impersonation(
    request: Request,
    db: Session,
    user: User,
) -> AuthenticatedUser | None:
    """Return an impersonated owner context, or ``None`` to fall through to 403.

    C-B15 — Tenant impersonation.  Activated only when *all* of the following
    are true:

    1. The ``X-Impersonate-Tenant`` header is present.
    2. ``user.is_platform_user`` is ``True`` and ``user.platform_role_code`` is set.
    3. The user's active ``platform_role.permissions.impersonate_tenant`` is ``True``.

    Security invariants (design §D.4):

    - Header is silently ignored for tenant users (``return None``).
    - Platform user without the header → ``return None`` (existing 403 preserved).
    - Platform user with header but ``impersonate_tenant=false`` → 403 RFC 7807.
    - Target tenant must exist (404) and be ``is_active=true`` (409).
    - Impersonated context is always ``role_code='owner'`` with the owner role's
      real permission list — never synthetic super-permissions.

    Raises:
        HTTPException 400: header value is not a valid UUID.
        HTTPException 403: role lacks ``impersonate_tenant``.
        HTTPException 404: target tenant not found.
        HTTPException 409: target tenant is inactive.
        HTTPException 500: owner role missing (system misconfiguration).
    """
    tenant_header = request.headers.get(IMPERSONATE_TENANT_HEADER)
    if not tenant_header or not user.is_platform_user or not user.platform_role_code:
        return None

    # Load the platform role to check the impersonate_tenant permission.
    platform_role = db.exec(
        select(PlatformRole)
        .where(PlatformRole.code == user.platform_role_code)
        .where(PlatformRole.is_active == True)
    ).first()
    if not platform_role:
        # Role missing/inactive — fall through to the existing 403.
        return None

    if platform_role.permissions.get("impersonate_tenant") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Impersonation not permitted",
                "status": 403,
                "detail": "Platform role does not have impersonate_tenant permission.",
            },
        )

    # Parse the target tenant UUID.
    try:
        target_tenant_id = uuid.UUID(tenant_header)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-uuid",
                "title": "Invalid tenant identifier",
                "status": 400,
                "detail": "X-Impersonate-Tenant header must be a valid UUID.",
            },
        )

    # Load the target tenant (select, not db.get — ADR-0005).
    tenant = db.exec(select(Tenant).where(Tenant.id == target_tenant_id)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Tenant not found",
                "status": 404,
                "detail": f"Tenant {target_tenant_id} does not exist.",
            },
        )
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://errors.pilotfortrades.com/conflict",
                "title": "Tenant inactive",
                "status": 409,
                "detail": f"Tenant {target_tenant_id} is not active.",
            },
        )

    # Load the owner role's permission list (never synthetic super-permissions).
    owner_role = db.exec(
        select(TenantUserRole)
        .where(TenantUserRole.code == "owner")
        .where(TenantUserRole.is_active == True)
    ).first()
    if not owner_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://errors.pilotfortrades.com/server-error",
                "title": "Owner role not found",
                "status": 500,
                "detail": "The 'owner' tenant_user_role is missing or inactive.",
            },
        )

    owner_permissions = (
        owner_role.permissions if isinstance(owner_role.permissions, list) else []
    )

    # Set request state so downstream middleware + audit context see the
    # impersonated tenant and the impersonator's identity.
    request.state.impersonator_user_id = user.id
    request.state.tenant_id = tenant.id
    request.state.user_id = user.id

    return AuthenticatedUser(
        user=user,
        tenant_id=tenant.id,
        role_code="owner",
        permissions=owner_permissions,
        impersonator_user_id=user.id,
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """
    FastAPI dependency that validates JWT and returns authenticated user with permissions.

    Authentication Flow:
    1. Validate JWT token from Authorization header
    2. Extract email from token
    3. Lookup user in database
    4. Fetch user's tenant membership and role
    5. Load permissions from role definition
    6. Return AuthenticatedUser with cached permissions

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token from Authorization header
        db: Database session

    Returns:
        AuthenticatedUser with user, tenant_id, role_code, and permissions

    Raises:
        HTTPException 400: Token missing email
        HTTPException 404: User not found
        HTTPException 403: User not in tenant or role not found

    Security:
        - JWT signature validated via Cognito JWKS
        - Tenant isolation enforced (user must belong to active tenant)
        - Fail-safe: Missing role = deny access (403)

    Performance:
        - Single database query to fetch user + tenant_user + role
        - Permissions cached in AuthenticatedUser (no repeated queries)
    """
    token = credentials.credentials
    payload = verify_cognito_jwt(token)

    # Extract email or sub (email preferred if available)
    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain email",
        )

    # Query database for user
    statement = select(User).where(User.email == email).where(User.is_active == True)
    user = db.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive",
        )

    # Attach tenant_id from TenantUser for the active tenant
    # For MVP, we assume a user belongs to one active tenant
    tenant_user = db.exec(
        select(TenantUser)
        .where(TenantUser.user_id == user.id)
        .where(TenantUser.is_active == True)
    ).first()

    if not tenant_user:
        # C-B15: Platform users with impersonate_tenant permission can act
        # as any tenant's owner via the X-Impersonate-Tenant header.
        impersonated = _try_impersonation(request, db, user)
        if impersonated is not None:
            return impersonated
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any active tenant",
        )

    # NEW: Fetch role and permissions
    # This is critical for RBAC - user must have a valid role
    role = db.exec(
        select(TenantUserRole)
        .where(TenantUserRole.code == tenant_user.role_code)
        .where(TenantUserRole.is_active == True)
    ).first()

    if not role:
        # Fail-safe: If role not found, deny access (security-first approach)
        # This could happen if:
        # - Default roles migration hasn't been run
        # - User has invalid role_code
        # - Role has been deactivated
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role '{tenant_user.role_code}' not found or inactive. Contact administrator.",
        )

    # Extract permissions from role's JSONB field
    # TenantUserRole.permissions is a JSONB field containing a list of permission strings
    # Example: ["*"] for owner, ["jobs.view", "jobs.update"] for technician
    permissions = role.permissions if isinstance(role.permissions, list) else []

    # Create AuthenticatedUser with permissions cached
    authenticated_user = AuthenticatedUser(
        user=user,
        tenant_id=tenant_user.tenant_id,
        role_code=role.code,
        permissions=permissions,
    )

    # Set request state for downstream middleware (e.g., idempotency, audit logging)
    request.state.tenant_id = authenticated_user.tenant_id
    request.state.user_id = authenticated_user.id

    return authenticated_user


# ─────────────────────────────────────────────────────────────────────────────
# C-B11 — Platform-level auth (operator endpoints)
# ─────────────────────────────────────────────────────────────────────────────


class PlatformUser(BaseModel):
    """Platform-level authenticated user (no tenant context).

    Created by :func:`get_platform_user` after validating the JWT and checking
    ``is_platform_user=True``.  Carries the ``platform_role.permissions`` JSON
    for authorization checks.  Platform users have **no** ``tenant_id`` — they
    access operator-level endpoints (cohort dashboard, etc.).
    """

    model_config = {"arbitrary_types_allowed": True}
    user: User
    platform_role_code: str
    permissions: dict[str, Any]

    @property
    def id(self) -> uuid.UUID:
        """User ID (convenience property)."""
        return self.user.id

    @property
    def user_id(self) -> uuid.UUID:
        """Alias for id to match AuthenticatedUser interface."""
        return self.user.id

    def can_read_all(self) -> bool:
        """Whether the platform role grants global read access."""
        return bool(self.permissions.get("read_all", False))

    def can_write(self, resource: str) -> bool:
        """Whether the platform role grants write access to *resource*."""
        write_perms = self.permissions.get("write") or []
        return resource in write_perms


def get_platform_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> PlatformUser:
    """FastAPI dependency for platform-level operator endpoints.

    Flow:
    1. Validate the Cognito JWT (reuses :func:`verify_cognito_jwt`).
    2. Look up the user by email.
    3. Check ``is_platform_user=True`` and ``platform_role_code`` is set.
    4. Load the ``platform_role.permissions`` JSON.
    5. Return a :class:`PlatformUser` (no ``tenant_id``).

    Raises:
        HTTPException 401: invalid/expired token.
        HTTPException 404: user not found or inactive.
        HTTPException 403: user is not a platform user, or platform_role inactive.
    """
    token = credentials.credentials
    payload = verify_cognito_jwt(token)

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain email",
        )

    user = db.exec(
        select(User).where(User.email == email).where(User.is_active == True)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive",
        )

    if not user.is_platform_user or not user.platform_role_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Platform access required",
                "status": 403,
                "detail": "User is not a platform user. "
                "Operator endpoints require platform-level access.",
            },
        )

    platform_role = db.exec(
        select(PlatformRole)
        .where(PlatformRole.code == user.platform_role_code)
        .where(PlatformRole.is_active == True)
    ).first()
    if not platform_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Platform role inactive",
                "status": 403,
                "detail": f"Platform role '{user.platform_role_code}' "
                "not found or inactive.",
            },
        )

    # Set request state for downstream middleware (audit logging)
    request.state.user_id = user.id

    return PlatformUser(
        user=user,
        platform_role_code=user.platform_role_code,
        permissions=platform_role.permissions or {},
    )
