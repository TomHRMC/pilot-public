import hashlib
import logging
import uuid as _uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, or_, select

from api.schemas.schemas import (
    CustomerCreate,
    CustomerResponse,
    PaginatedCustomerResponse,
    PaymentMethodCreate,
    PaymentMethodResponse,
    SoftDeleteResponse,
)
from app.models.billing import PaymentMethod
from app.models.crm import Customer, CustomerSmsConsentAudit, CustomerType
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.onboarding_service import mark_first_customer

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _create_customer_impl(
    customer_in: CustomerCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Customer:
    """
    Shared customer creation logic used by both authenticated and test endpoints.

    Args:
        customer_in: Customer data to create
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Created Customer instance

    Raises:
        HTTPException: If validation fails or customer already exists

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
    """
    try:
        ctype = CustomerType(customer_in.type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid customer type: {customer_in.type}",
        )

    # Check if email already exists in tenant
    if customer_in.email:
        existing = db.exec(
            select(Customer)
            .where(Customer.tenant_id == user_context.tenant_id)
            .where(Customer.email == customer_in.email)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this email already exists in this tenant",
            )

    customer = Customer(
        tenant_id=user_context.tenant_id,
        type=ctype,
        display_name=customer_in.display_name,
        first_name=customer_in.first_name,
        last_name=customer_in.last_name,
        company_name=customer_in.company_name,
        email=customer_in.email,
        mobile_phone=customer_in.mobile_phone,
        # FIND-107 (B18): customer-level taxability override
        taxability_code=getattr(customer_in, "taxability_code", None),
        # B20: card-on-file requirement
        card_required=getattr(customer_in, "card_required", False),
    )

    # DLC-1: Offline consent attestation — only when checkbox is explicitly checked
    sms_attestation_checked = getattr(customer_in, "sms_attestation_checked", False)
    if customer_in.mobile_phone and sms_attestation_checked:
        now = datetime.now(UTC)
        customer.sms_opt_in_source = "explicit_checkbox"
        customer.sms_consent_attested_by = user_context.id
        customer.sms_consent_attested_at = now
        customer.sms_consent_ip_address = (
            getattr(customer_in, "sms_consent_ip_address", None) or "unknown"
        )
        customer.sms_verification_status = "pending_verification"

        # Commit customer first so audit FK resolves
        db.add(customer)
        db.commit()
        db.refresh(customer)

        # Write consent audit row
        consent_text = (
            "I confirm that I have received explicit, documented consent from this customer "
            "to send them SMS notifications regarding their service."
        )
        audit_row = CustomerSmsConsentAudit(
            id=_uuid.uuid4(),
            created_at=now,
            tenant_id=customer.tenant_id,
            customer_id=customer.id,
            attested_by=user_context.id,
            ip_address=customer.sms_consent_ip_address,
            attested_at=now,
            consent_text_hash=hashlib.sha256(consent_text.encode()).hexdigest(),
            action="attested",
        )
        db.add(audit_row)
        db.commit()

        # Enqueue double opt-in SMS (background)
        from tasks.sms_compliance import send_double_optin_sms

        send_double_optin_sms.delay(
            customer_id=str(customer.id),
            tenant_id=str(customer.tenant_id),
        )

        # FIX4-BE-01 (PLP-FIX-6): advance onboarding checklist — never fail the create
        try:
            mark_first_customer(db, user_context.tenant_id)
        except Exception:
            logger.warning(
                "mark_first_customer failed for tenant %s",
                user_context.tenant_id,
                exc_info=True,
            )

        return customer

    db.add(customer)
    db.commit()
    db.refresh(customer)

    # FIX4-BE-01 (PLP-FIX-6): advance onboarding checklist — never fail the create
    try:
        mark_first_customer(db, user_context.tenant_id)
    except Exception:
        logger.warning(
            "mark_first_customer failed for tenant %s",
            user_context.tenant_id,
            exc_info=True,
        )

    return customer


def _list_customers_impl(
    skip: int,
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    search: str | None = None,
    status: str | None = None,
    offset: int = 0,
) -> PaginatedCustomerResponse:
    """
    Shared customer listing logic used by both authenticated and test endpoints.

    UI-FIX-1C: Returns PaginatedCustomerResponse with total count.
    BETA-B3 companion task BE-1: optional ?search= param for case-insensitive
    match across display_name, first_name, last_name, company_name, and email.

    Args:
        skip: Deprecated — use offset instead (backward compat alias)
        limit: Maximum number of records to return
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)
        search: Optional case-insensitive search string
        status: Optional 'active' | 'inactive' filter
        offset: Canonical pagination offset (supersedes skip when > 0)

    Returns:
        PaginatedCustomerResponse with items, total, limit, offset

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
    """
    effective_offset = offset if offset > 0 else skip

    # Build base filter predicate
    base_where = [Customer.tenant_id == user_context.tenant_id]

    # BE-1: case-insensitive search across name and email fields
    if search:
        q = f"%{search}%"
        base_where.append(
            or_(
                Customer.display_name.ilike(q),
                Customer.first_name.ilike(q),
                Customer.last_name.ilike(q),
                Customer.company_name.ilike(q),
                Customer.email.ilike(q),
            )
        )

    # UI-FIX-1C: optional active/inactive filter
    if status == "active":
        base_where.append(Customer.is_active == True)
    elif status == "inactive":
        base_where.append(Customer.is_active == False)

    count_stmt = select(func.count(Customer.id)).where(*base_where)
    total = db.exec(count_stmt).one()

    statement = (
        select(Customer).where(*base_where).offset(effective_offset).limit(limit)
    )
    customers = db.exec(statement).all()

    return PaginatedCustomerResponse(
        items=customers,
        total=total,
        limit=limit,
        offset=effective_offset,
    )


def _get_customer_impl(
    customer_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Customer:
    """
    Shared customer retrieval logic used by both authenticated and test endpoints.

    Args:
        customer_id: UUID of customer to retrieve
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Customer instance

    Raises:
        HTTPException: If customer not found

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
    """
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer


def _update_customer_impl(
    customer_id: UUID,
    customer_in: CustomerCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Customer:
    """
    Shared customer update logic used by both authenticated and test endpoints.

    Args:
        customer_id: UUID of customer to update
        customer_in: Updated customer data
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Updated Customer instance

    Raises:
        HTTPException: If customer not found or validation fails

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
    """
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    try:
        ctype = CustomerType(customer_in.type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid customer type: {customer_in.type}",
        )

    # Check if email already exists (excluding current customer)
    if customer_in.email and customer_in.email != customer.email:
        existing = db.exec(
            select(Customer)
            .where(Customer.tenant_id == user_context.tenant_id)
            .where(Customer.email == customer_in.email)
            .where(Customer.id != customer_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this email already exists in this tenant",
            )

    # Update fields
    customer.type = ctype
    customer.display_name = customer_in.display_name
    customer.first_name = customer_in.first_name
    customer.last_name = customer_in.last_name
    customer.company_name = customer_in.company_name
    customer.email = customer_in.email
    customer.mobile_phone = customer_in.mobile_phone
    # FIND-107 (B18): persist customer-level taxability override
    customer.taxability_code = getattr(customer_in, "taxability_code", None)

    # DLC-1: Offline consent attestation — only when checkbox is explicitly checked
    sms_attestation_checked = getattr(customer_in, "sms_attestation_checked", False)
    if customer_in.mobile_phone and sms_attestation_checked:
        now = datetime.now(UTC)
        customer.sms_opt_in_source = "explicit_checkbox"
        customer.sms_consent_attested_by = user_context.id
        customer.sms_consent_attested_at = now
        customer.sms_consent_ip_address = (
            getattr(customer_in, "sms_consent_ip_address", None) or "unknown"
        )
        customer.sms_verification_status = "pending_verification"

        # Commit customer first so audit FK resolves
        db.add(customer)
        db.commit()
        db.refresh(customer)

        # Write consent audit row
        consent_text = (
            "I confirm that I have received explicit, documented consent from this customer "
            "to send them SMS notifications regarding their service."
        )
        audit_row = CustomerSmsConsentAudit(
            id=_uuid.uuid4(),
            created_at=now,
            tenant_id=customer.tenant_id,
            customer_id=customer.id,
            attested_by=user_context.id,
            ip_address=customer.sms_consent_ip_address,
            attested_at=now,
            consent_text_hash=hashlib.sha256(consent_text.encode()).hexdigest(),
            action="attested",
        )
        db.add(audit_row)
        db.commit()

        # Enqueue double opt-in SMS (background)
        from tasks.sms_compliance import send_double_optin_sms

        send_double_optin_sms.delay(
            customer_id=str(customer.id),
            tenant_id=str(customer.tenant_id),
        )

        return customer

    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def _delete_customer_impl(
    customer_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Shared customer deletion logic used by both authenticated and test endpoints.

    Args:
        customer_id: UUID of customer to delete
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Success message dict

    Raises:
        HTTPException: If customer not found

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
        Performs soft delete by setting is_active=False.
    """
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Soft delete
    customer.is_active = False
    db.add(customer)
    db.commit()

    return {"message": "Customer deleted successfully", "id": str(customer_id)}


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================
# NOTE: Test endpoints MUST be registered BEFORE authenticated endpoints
# to avoid route matching conflicts (/{id} would match /test)


@router.post(
    "/test", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED
)
def create_customer_test(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new customer (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/customers/test \\
          -H "Content-Type: application/json" \\
          -d '{"display_name": "John Doe", "type": "person", "email": "john@example.com"}'

    Returns:
        CustomerResponse with created customer data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_customer_impl(customer_in, db, test_context)


@router.get("/test", response_model=PaginatedCustomerResponse)
def list_customers_test(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """
    List customers (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns customers from test tenant only: 00000000-0000-0000-0000-000000000001

    Params:
        search: Optional case-insensitive search across display_name, first_name,
                last_name, company_name, email — BETA-B3 BE-1
        status: Optional 'active' | 'inactive' filter — UI-FIX-1C
        offset: Pagination offset (supersedes deprecated skip)

    Usage:
        curl http://localhost:8000/api/v1/customers/test
        curl "http://localhost:8000/api/v1/customers/test?search=smith"

    Returns:
        PaginatedCustomerResponse from test tenant (UI-FIX-1C)
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _list_customers_impl(
        skip, limit, db, test_context, search=search, status=status, offset=offset
    )


@router.get("/{customer_id}/test", response_model=CustomerResponse)
def get_customer_test(
    customer_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific customer (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns customer from test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/customers/{customer_id}/test

    Returns:
        CustomerResponse with customer data
    """
    test_context = get_test_context()
    return _get_customer_impl(customer_id, db, test_context)


@router.patch("/{customer_id}/test", response_model=CustomerResponse)
def update_customer_test(
    customer_id: UUID,
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
):
    """
    Update a customer (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Updates customer in test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl -X PATCH http://localhost:8000/api/v1/customers/{customer_id}/test \\
          -H "Content-Type: application/json" \\
          -d '{"display_name": "Updated Name", "type": "person", "email": "updated@example.com"}'

    Returns:
        CustomerResponse with updated customer data
    """
    test_context = get_test_context()
    return _update_customer_impl(customer_id, customer_in, db, test_context)


# FIND-151: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete("/{customer_id}/test", response_model=SoftDeleteResponse)
def delete_customer_test(
    customer_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a customer (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Deletes customer in test tenant: 00000000-0000-0000-0000-000000000001
        - Performs soft delete (sets is_active=False)

    Usage:
        curl -X DELETE http://localhost:8000/api/v1/customers/{customer_id}/test

    Returns:
        Success message
    """
    test_context = get_test_context()
    return _delete_customer_impl(customer_id, db, test_context)


# ==================== PAYMENT METHODS (FIND-058) ====================


def _list_payment_methods_impl(
    customer_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[PaymentMethod]:
    """
    List active payment methods for a customer (tenant-scoped).

    Args:
        customer_id: Customer ID
        db: Database session
        user_context: AuthenticatedUser or TestUserContext

    Returns:
        List of active PaymentMethod instances for the customer

    Raises:
        HTTPException 404: Customer not found or belongs to different tenant
    """
    # Verify customer exists and belongs to tenant (IDOR check)
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # List active payment methods for this customer
    payment_methods = db.exec(
        select(PaymentMethod)
        .where(PaymentMethod.customer_id == customer_id)
        .where(PaymentMethod.tenant_id == user_context.tenant_id)
        .where(PaymentMethod.is_active == True)
    ).all()

    return payment_methods


def _create_payment_method_impl(
    customer_id: UUID,
    pm_in: PaymentMethodCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PaymentMethod:
    """
    Vault a new Stripe PaymentMethod for a customer.

    Args:
        customer_id: Customer ID
        pm_in: PaymentMethodCreate with psp_payment_method_id from Stripe Elements
        db: Database session
        user_context: AuthenticatedUser or TestUserContext

    Returns:
        Created PaymentMethod instance

    Raises:
        HTTPException 404: Customer not found
        HTTPException 400: Payment method already vaulted for this customer
    """
    # Verify customer exists and belongs to tenant (IDOR check)
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check if this PSP payment method is already vaulted
    existing = db.exec(
        select(PaymentMethod)
        .where(PaymentMethod.tenant_id == user_context.tenant_id)
        .where(PaymentMethod.psp_payment_method_id == pm_in.psp_payment_method_id)
        .where(PaymentMethod.is_active == True)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method already vaulted for this tenant",
        )

    # Create new payment method
    pm = PaymentMethod(
        tenant_id=user_context.tenant_id,
        customer_id=customer_id,
        payment_type_id=pm_in.payment_type_id,
        psp_provider="stripe",  # Hardcoded for MVP
        psp_payment_method_id=pm_in.psp_payment_method_id,
    )

    db.add(pm)
    db.commit()
    db.refresh(pm)
    return pm


def _delete_payment_method_impl(
    customer_id: UUID,
    pm_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> SoftDeleteResponse:
    """
    Soft-delete a payment method for a customer.

    Args:
        customer_id: Customer ID
        pm_id: Payment method ID
        db: Database session
        user_context: AuthenticatedUser or TestUserContext

    Returns:
        SoftDeleteResponse with success message

    Raises:
        HTTPException 404: Customer or payment method not found
    """
    # Verify customer exists and belongs to tenant (IDOR check)
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get payment method (tenant-scoped, must belong to specified customer)
    pm = db.exec(
        select(PaymentMethod)
        .where(PaymentMethod.id == pm_id)
        .where(PaymentMethod.customer_id == customer_id)
        .where(PaymentMethod.tenant_id == user_context.tenant_id)
    ).first()

    if not pm:
        raise HTTPException(status_code=404, detail="Payment method not found")

    # Soft-delete
    pm.is_active = False
    db.add(pm)
    db.commit()

    return SoftDeleteResponse(
        message="Payment method deleted successfully",
        id=pm_id,
    )


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.create")),
):
    """
    Create a new customer (requires JWT authentication and customers.create permission).

    Security:
        - Requires valid JWT token
        - Requires customers.create permission
        - Customer created in authenticated user's tenant

    Returns:
        CustomerResponse with created customer data
    """
    return _create_customer_impl(customer_in, db, current_user)


@router.get("/", response_model=PaginatedCustomerResponse)
def list_customers(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.view")),
):
    """
    List customers (requires JWT authentication and customers.view permission).

    UI-FIX-1C: Returns PaginatedCustomerResponse with total, limit, offset.
    BETA-B3 addition (BE-1): optional ?search= param for case-insensitive
    search across display_name, first_name, last_name, company_name, and email.

    Security:
        - Requires valid JWT token
        - Requires customers.view permission
        - Returns only customers in authenticated user's tenant

    Params:
        status: Optional 'active' | 'inactive' filter
        offset: Pagination offset (supersedes deprecated skip)

    Returns:
        PaginatedCustomerResponse with total count
    """
    return _list_customers_impl(
        skip, limit, db, current_user, search=search, status=status, offset=offset
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.view")),
):
    """
    Get a specific customer (requires JWT authentication and customers.view permission).

    Security:
        - Requires valid JWT token
        - Requires customers.view permission
        - Returns only customer in authenticated user's tenant

    Returns:
        CustomerResponse with customer data
    """
    return _get_customer_impl(customer_id, db, current_user)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.update")),
):
    """
    Update a customer (requires JWT authentication and customers.update permission).

    Security:
        - Requires valid JWT token
        - Requires customers.update permission
        - Updates only customer in authenticated user's tenant

    Returns:
        CustomerResponse with updated customer data
    """
    return _update_customer_impl(customer_id, customer_in, db, current_user)


# FIND-151: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete("/{customer_id}", response_model=SoftDeleteResponse)
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.delete")),
):
    """
    Delete a customer (requires JWT authentication and customers.delete permission).

    Security:
        - Requires valid JWT token
        - Requires customers.delete permission
        - Deletes only customer in authenticated user's tenant
        - Performs soft delete (sets is_active=False)

    Returns:
        Success message
    """
    return _delete_customer_impl(customer_id, db, current_user)


# ==================== PAYMENT METHODS ENDPOINTS ====================


# ---- TEST endpoints (must be registered BEFORE authenticated counterparts) ----


@router.get(
    "/{customer_id}/payment-methods/test",
    response_model=list[PaymentMethodResponse],
)
def list_payment_methods_test(
    customer_id: UUID,
    db: Session = Depends(get_db),
):
    """List active payment methods for a customer (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _list_payment_methods_impl(customer_id, db, test_context)


@router.post(
    "/{customer_id}/payment-methods/test",
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_method_test(
    customer_id: UUID,
    pm_in: PaymentMethodCreate,
    db: Session = Depends(get_db),
):
    """Vault a new Stripe PaymentMethod for a customer (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _create_payment_method_impl(customer_id, pm_in, db, test_context)


@router.delete(
    "/{customer_id}/payment-methods/{pm_id}/test",
    response_model=SoftDeleteResponse,
)
def delete_payment_method_test(
    customer_id: UUID,
    pm_id: UUID,
    db: Session = Depends(get_db),
):
    """Soft-delete a payment method for a customer (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _delete_payment_method_impl(customer_id, pm_id, db, test_context)


# ---- Authenticated endpoints ----


@router.get(
    "/{customer_id}/payment-methods",
    response_model=list[PaymentMethodResponse],
)
def list_payment_methods(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.manage")),
):
    """
    List active payment methods for a customer (FIND-058).

    Security:
        - Requires valid JWT token
        - Requires customers.manage permission
        - Returns only customer in authenticated user's tenant

    Returns:
        List of PaymentMethodResponse objects
    """
    return _list_payment_methods_impl(customer_id, db, current_user)


@router.post(
    "/{customer_id}/payment-methods",
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_method(
    customer_id: UUID,
    pm_in: PaymentMethodCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.manage")),
):
    """
    Vault a new Stripe PaymentMethod for a customer (FIND-058).

    Security:
        - Requires valid JWT token
        - Requires customers.manage permission
        - Vaults only for customer in authenticated user's tenant

    Returns:
        PaymentMethodResponse with created payment method data
    """
    return _create_payment_method_impl(customer_id, pm_in, db, current_user)


@router.delete(
    "/{customer_id}/payment-methods/{pm_id}",
    response_model=SoftDeleteResponse,
)
def delete_payment_method(
    customer_id: UUID,
    pm_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.manage")),
):
    """
    Soft-delete a payment method for a customer (FIND-058).

    Security:
        - Requires valid JWT token
        - Requires customers.manage permission
        - Deletes only payment method in authenticated user's tenant

    Returns:
        Success message
    """
    return _delete_payment_method_impl(customer_id, pm_id, db, current_user)
