import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserRole, TenantUserStatus
from app.models.core import Tenant, User, UserEndpoint
from core.auth import security, verify_cognito_jwt
from core.db import get_db
from core.test_context import get_test_context

router = APIRouter()


class SignupRequest(BaseModel):
    tenant_name: str
    first_name: str | None = None
    last_name: str | None = None


class SignupResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    message: str


# ==================== SHARED BUSINESS LOGIC ====================


def _signup_impl(
    request: SignupRequest,
    email: str,
    db: Session,
) -> SignupResponse:
    """
    DEV/TEST STAND-IN for the prod Post-Confirmation Lambda router (G6).

    This function mirrors the row-creation logic of
    ``backend/lambda/post_confirmation/handler.py`` (Path 3 — new-owner create)
    so the dev/test environment can provision a tenant + owner user without a
    real Cognito confirmation. The prod Lambda is the authoritative account-
    birth path; this stand-in exists only for local dev/test.

    ADR-0012: the ``Tenant.name`` uniqueness pre-check was REMOVED —
    ``tenant_name_key`` is dropped, so duplicate names are allowed. The email
    duplicate check is retained (email is the Cognito↔RDS join key).

    Args:
        request: Signup request with tenant and user details
        email: Email address for the new user
        db: Database session

    Returns:
        SignupResponse with created user and tenant IDs

    Raises:
        HTTPException: If user with this email already exists, or creation fails

    Note:
        This function creates:
        - New Tenant
        - New User
        - UserEndpoint (email)
        - TenantUser association with 'owner' role
    """
    # 1. Check if user already exists (email is the join key — still enforced)
    existing_user = db.exec(select(User).where(User.email == email)).first()
    if existing_user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    # ADR-0012: tenant.name uniqueness pre-check REMOVED — tenant_name_key
    # dropped; duplicate business names are now allowed.

    try:
        # Create Tenant
        tenant = Tenant(name=request.tenant_name)
        db.add(tenant)
        db.flush()  # flush to get tenant.id

        # Create User
        user = User(
            email=email,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        db.add(user)
        db.flush()  # flush to get user.id

        # Create UserEndpoint
        endpoint = UserEndpoint(
            user_id=user.id,
            channel="email",
            value=email,
            is_primary=True,
            verification_status="pending",
        )
        db.add(endpoint)

        # Get or create Role
        role_code = "owner"
        role = db.exec(
            select(TenantUserRole).where(TenantUserRole.code == role_code)
        ).first()
        if not role:
            role = TenantUserRole(code=role_code, name="Owner", is_default=True)
            db.add(role)
            db.flush()

        # Get or create Status
        status_code = "active"
        user_status = db.exec(
            select(TenantUserStatus).where(TenantUserStatus.code == status_code)
        ).first()
        if not user_status:
            user_status = TenantUserStatus(
                code=status_code, name="Active", is_default=True
            )
            db.add(user_status)
            db.flush()

        # Create TenantUser link
        tenant_user = TenantUser(
            tenant_id=tenant.id,
            user_id=user.id,
            role_code=role.code,
            status_id=user_status.id,
            joined_at=datetime.now(UTC),
        )
        db.add(tenant_user)

        db.commit()

        return SignupResponse(
            user_id=user.id, tenant_id=tenant.id, message="Signup successful"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED
)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Create new tenant and user account (requires JWT authentication).

    Security:
        - Requires valid Cognito JWT token
        - Email extracted from JWT token
        - Creates new tenant with user as owner

    Returns:
        SignupResponse with created user and tenant IDs
    """
    # Verify the token
    token = credentials.credentials
    payload = verify_cognito_jwt(token)

    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token does not contain email")

    return _signup_impl(request, email, db)


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================


@router.post(
    "/signup/test", response_model=SignupResponse, status_code=status.HTTP_201_CREATED
)
def signup_test(
    request: SignupRequest,
    email: str,
    db: Session = Depends(get_db),
):
    """
    Create new tenant and user account (TEST ENDPOINT - no authentication required).
    
    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled
        
    Test Context:
        - No JWT verification required
        - Email provided as query parameter instead of from token
        
    Usage:
        curl -X POST "http://localhost:8000/api/v1/auth/signup/test?email=test@example.com" \\
          -H "Content-Type: application/json" \\
          -d '{"tenant_name": "Test Company", "first_name": "Test", "last_name": "User"}'
          
    Returns:
        SignupResponse with created user and tenant IDs
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _signup_impl(request, email, db)
