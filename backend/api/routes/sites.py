from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.schemas.schemas import SITE_TYPE_VALUES, SiteCreate, SiteResponse
from app.models.crm import Address, Customer, EntityAddress, Site
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _create_site_impl(
    site_in: SiteCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Shared site creation logic used by both authenticated and test endpoints.

    Args:
        site_in: Site data to create
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Site dict with optional nested address (Gap #7)

    Raises:
        HTTPException: If customer not found or validation fails

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
        If site_in.address is provided, creates Address and EntityAddress automatically.
    """
    # CLASS-B1: Validate site_type if explicitly provided
    if site_in.site_type is not None and site_in.site_type not in SITE_TYPE_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-site-type",
                "title": "Invalid site type",
                "status": 422,
                "detail": f"'{site_in.site_type}' is not a valid site_type. Must be one of: {sorted(SITE_TYPE_VALUES)}",
            },
        )

    # Verify the customer belongs to the current tenant
    customer = db.exec(
        select(Customer)
        .where(Customer.id == site_in.customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found in this tenant",
        )

    # CLASS-B1: Resolve site_type — explicit > customer-type-derived default
    if site_in.site_type is not None:
        site_type = site_in.site_type
    else:
        # company → commercial, person → residential (DB fallback is residential)
        site_type = "commercial" if customer.type == "company" else "residential"

    # Create site
    site = Site(
        tenant_id=user_context.tenant_id,
        customer_id=site_in.customer_id,
        name=site_in.name,
        notes=site_in.notes,
        jurisdiction_code=site_in.jurisdiction_code,
        site_type=site_type,
    )

    db.add(site)
    db.flush()  # Get site.id without committing yet

    # If address provided, create address and link via EntityAddress (Gap #7)
    address_data = None
    if site_in.address:
        # Create address
        address = Address(
            tenant_id=user_context.tenant_id,
            line1=site_in.address.line1,
            line2=site_in.address.line2,
            line3=site_in.address.line3,
            city=site_in.address.city,
            state=site_in.address.state,
            postal_code=site_in.address.postal_code,
            country=site_in.address.country,
            latitude=site_in.address.latitude,
            longitude=site_in.address.longitude,
        )
        db.add(address)
        db.flush()  # Get address.id

        # Create EntityAddress link with service_location type
        entity_address = EntityAddress(
            tenant_id=user_context.tenant_id,
            entity_type_code="site",
            entity_id=site.id,
            address_id=address.id,
            address_type_code="service_location",
            is_primary=True,
            is_active=True,
        )
        db.add(entity_address)

        # Prepare address data for response
        address_data = {
            "id": address.id,
            "line1": address.line1,
            "line2": address.line2,
            "line3": address.line3,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
            "latitude": address.latitude,
            "longitude": address.longitude,
            "is_active": address.is_active,
            "created_at": address.created_at,
            "updated_at": address.updated_at,
        }

    # Commit all together (transaction-safe)
    db.commit()
    db.refresh(site)

    # Build response with optional address
    site_dict = {
        "id": site.id,
        "tenant_id": site.tenant_id,
        "customer_id": site.customer_id,
        "name": site.name,
        "notes": site.notes,
        "jurisdiction_code": site.jurisdiction_code,
        "is_active": site.is_active,
        "address": address_data,
        # CLASS-B1: site_type classification
        "site_type": site.site_type,
    }

    return site_dict


def _list_sites_impl(
    customer_id: UUID | None,
    skip: int,
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[Site]:
    """
    Shared site listing logic used by both authenticated and test endpoints.

    Args:
        customer_id: Optional filter by customer ID
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        List of Site instances for the tenant

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
    """
    statement = select(Site).where(Site.tenant_id == user_context.tenant_id)
    if customer_id:
        statement = statement.where(Site.customer_id == customer_id)

    statement = statement.offset(skip).limit(limit)
    sites = db.exec(statement).all()
    return sites


def _get_site_impl(
    site_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Shared site retrieval logic used by both authenticated and test endpoints.

    Args:
        site_id: UUID of site to retrieve
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Site dict with optional primary address (Gap #7)

    Raises:
        HTTPException: If site not found

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
    """
    site = db.exec(
        select(Site)
        .where(Site.id == site_id)
        .where(Site.tenant_id == user_context.tenant_id)
    ).first()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Fetch primary address if exists (Gap #7)
    address_data = None
    entity_address_result = db.exec(
        select(Address, EntityAddress)
        .join(EntityAddress, EntityAddress.address_id == Address.id)
        .where(EntityAddress.entity_type_code == "site")
        .where(EntityAddress.tenant_id == user_context.tenant_id)
        .where(EntityAddress.entity_id == site_id)
        .where(EntityAddress.is_primary == True)
        .where(EntityAddress.is_active == True)
    ).first()

    if entity_address_result:
        address = entity_address_result[0]
        address_data = {
            "id": address.id,
            "line1": address.line1,
            "line2": address.line2,
            "line3": address.line3,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
            "latitude": address.latitude,
            "longitude": address.longitude,
            "is_active": address.is_active,
            "created_at": address.created_at,
            "updated_at": address.updated_at,
        }

    # Build response with optional address
    site_dict = {
        "id": site.id,
        "tenant_id": site.tenant_id,
        "customer_id": site.customer_id,
        "name": site.name,
        "notes": site.notes,
        "jurisdiction_code": site.jurisdiction_code,
        "is_active": site.is_active,
        "address": address_data,
        # CLASS-B1: site_type classification
        "site_type": site.site_type,
    }

    return site_dict


def _update_site_impl(
    site_id: UUID,
    site_in: SiteCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Site:
    """
    Shared site update logic used by both authenticated and test endpoints.

    Args:
        site_id: UUID of site to update
        site_in: Updated site data
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Updated Site instance

    Raises:
        HTTPException: If site or customer not found

    Note:
        Both AuthenticatedUser and TestUserContext provide tenant_id attribute.
    """
    site = db.exec(
        select(Site)
        .where(Site.id == site_id)
        .where(Site.tenant_id == user_context.tenant_id)
    ).first()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Verify the customer belongs to the current tenant
    customer = db.exec(
        select(Customer)
        .where(Customer.id == site_in.customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found in this tenant",
        )

    # Update fields
    site.customer_id = site_in.customer_id
    site.name = site_in.name
    site.notes = site_in.notes
    site.jurisdiction_code = site_in.jurisdiction_code

    db.add(site)
    db.commit()
    db.refresh(site)

    # Build response (without address for update - use GET to see address)
    site_dict = {
        "id": site.id,
        "tenant_id": site.tenant_id,
        "customer_id": site.customer_id,
        "name": site.name,
        "notes": site.notes,
        "jurisdiction_code": site.jurisdiction_code,
        "is_active": site.is_active,
        "address": None,  # Address not included in update response
    }

    return site_dict


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================
# NOTE: Test endpoints MUST be registered BEFORE authenticated endpoints
# to avoid route matching conflicts (/{id} would match /test)


@router.post("/test", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site_test(
    site_in: SiteCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new site (TEST ENDPOINT - no authentication required).
    
    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled
        
    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002
        
    Usage:
        curl -X POST http://localhost:8000/api/v1/sites/test \\
          -H "Content-Type: application/json" \\
          -d '{"customer_id": "...", "name": "Main Office", "notes": "Downtown location"}'
          
    Returns:
        SiteResponse with created site data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_site_impl(site_in, db, test_context)


@router.get("/test", response_model=list[SiteResponse])
def list_sites_test(
    customer_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List sites (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns sites from test tenant only: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/sites/test

    Returns:
        List of SiteResponse objects from test tenant
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _list_sites_impl(customer_id, skip, limit, db, test_context)


@router.get("/{site_id}/test", response_model=SiteResponse)
def get_site_test(
    site_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific site (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns site from test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/sites/{site_id}/test

    Returns:
        SiteResponse with site data
    """
    test_context = get_test_context()
    return _get_site_impl(site_id, db, test_context)


@router.patch("/{site_id}/test", response_model=SiteResponse)
def update_site_test(
    site_id: UUID,
    site_in: SiteCreate,
    db: Session = Depends(get_db),
):
    """
    Update a site (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Updates site in test tenant: 00000000-0000-0000-0000-000000000001
        - Validates customer belongs to test tenant

    Usage:
        curl -X PATCH http://localhost:8000/api/v1/sites/{site_id}/test \\
          -H "Content-Type: application/json" \\
          -d '{"customer_id": "...", "name": "Updated Site", "notes": "New notes"}'

    Returns:
        SiteResponse with updated site data
    """
    test_context = get_test_context()
    return _update_site_impl(site_id, site_in, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(
    site_in: SiteCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("sites.create")),
):
    """
    Create a new site (requires JWT authentication and sites.create permission).

    Security:
        - Requires valid JWT token
        - Requires sites.create permission
        - Site created in authenticated user's tenant
        - Validates customer belongs to same tenant

    Returns:
        SiteResponse with created site data
    """
    return _create_site_impl(site_in, db, current_user)


@router.get("/", response_model=list[SiteResponse])
def list_sites(
    customer_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("sites.view")),
):
    """
    List sites (requires JWT authentication and sites.view permission).

    Security:
        - Requires valid JWT token
        - Requires sites.view permission
        - Returns only sites in authenticated user's tenant

    Returns:
        List of SiteResponse objects
    """
    return _list_sites_impl(customer_id, skip, limit, db, current_user)


@router.get("/{site_id}", response_model=SiteResponse)
def get_site(
    site_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("sites.view")),
):
    """
    Get a specific site (requires JWT authentication and sites.view permission).

    Security:
        - Requires valid JWT token
        - Requires sites.view permission
        - Returns only site in authenticated user's tenant

    Returns:
        SiteResponse with site data
    """
    return _get_site_impl(site_id, db, current_user)


@router.patch("/{site_id}", response_model=SiteResponse)
def update_site(
    site_id: UUID,
    site_in: SiteCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("sites.update")),
):
    """
    Update a site (requires JWT authentication and sites.update permission).

    Security:
        - Requires valid JWT token
        - Requires sites.update permission
        - Updates only site in authenticated user's tenant
        - Validates customer belongs to same tenant

    Returns:
        SiteResponse with updated site data
    """
    return _update_site_impl(site_id, site_in, db, current_user)
