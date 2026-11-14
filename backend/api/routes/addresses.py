"""
Address API routes for polymorphic relationship management.

This module implements Address CRUD operations and EntityAddress association
management (Gap #6, #7).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, update

from api.schemas.addresses import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
    EntityAddressLink,
    EntityAddressUnlink,
)
from api.schemas.schemas import SoftDeleteResponse
from app.models.crm import Address, Customer, EntityAddress, Site
from app.models.fulfillment import Job
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _create_address_impl(
    address_in: AddressCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Address:
    """
    Shared address creation logic used by both authenticated and test endpoints.

    Args:
        address_in: Address data to create
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Created Address instance

    Note:
        Tenant-scoped: the new row carries the caller's tenant_id.
        Tenant isolation is enforced when linking via EntityAddress.
    """
    address = Address(
        tenant_id=user_context.tenant_id,
        line1=address_in.line1,
        line2=address_in.line2,
        line3=address_in.line3,
        city=address_in.city,
        state=address_in.state,
        postal_code=address_in.postal_code,
        country=address_in.country,
        latitude=address_in.latitude,
        longitude=address_in.longitude,
    )

    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def _list_addresses_impl(
    skip: int,
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[Address]:
    """
    Shared address listing logic used by both authenticated and test endpoints.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        List of Address instances

    Note:
        Tenant-scoped: filters on the caller's tenant_id. To see the addresses for one entity,
        use /addresses/by-entity/{entity_type}/{entity_id} endpoints.
    """
    statement = (
        select(Address)
        .where(Address.is_active == True)
        .where(Address.tenant_id == user_context.tenant_id)
        .offset(skip)
        .limit(limit)
    )
    addresses = db.exec(statement).all()
    return addresses


def _get_address_impl(
    address_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Address:
    """
    Shared address retrieval logic used by both authenticated and test endpoints.

    Args:
        address_id: UUID of address to retrieve
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Address instance

    Raises:
        HTTPException: If address not found
    """
    address = db.exec(
        select(Address).where(
            Address.id == address_id, Address.tenant_id == user_context.tenant_id
        )
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    return address


def _update_address_impl(
    address_id: UUID,
    address_in: AddressUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Address:
    """
    Shared address update logic used by both authenticated and test endpoints.

    Args:
        address_id: UUID of address to update
        address_in: Updated address data
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Updated Address instance

    Raises:
        HTTPException: If address not found
    """
    address = db.exec(
        select(Address).where(
            Address.id == address_id, Address.tenant_id == user_context.tenant_id
        )
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    # Update only provided fields
    update_data = address_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(address, field, value)

    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def _delete_address_impl(
    address_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Shared address deletion logic used by both authenticated and test endpoints.

    Args:
        address_id: UUID of address to delete
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Success message dict

    Raises:
        HTTPException: If address not found

    Note:
        Performs soft delete by setting is_active=False.
    """
    address = db.exec(
        select(Address).where(
            Address.id == address_id, Address.tenant_id == user_context.tenant_id
        )
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    # Soft delete
    address.is_active = False
    db.add(address)
    db.commit()

    return {"message": "Address deleted successfully", "id": str(address_id)}


def _link_address_to_entity_impl(
    address_id: UUID,
    link_data: EntityAddressLink,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Link an address to an entity (customer, site, job).

    Args:
        address_id: UUID of address to link
        link_data: Entity link data (entity_type, entity_id, address_type, is_primary)
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Success message dict

    Raises:
        HTTPException: If address/entity not found, entity not in tenant, or duplicate link

    Validation:
        - Address must exist
        - Entity must exist and belong to user's tenant
        - Cannot duplicate link (same address + entity + address_type)
        - Only one is_primary=True per entity per address_type (auto-unsets others if is_primary=True)
    """
    # 1. Verify address exists
    address = db.exec(
        select(Address).where(
            Address.id == address_id, Address.tenant_id == user_context.tenant_id
        )
    ).first()
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    # 2. Verify entity exists and belongs to user's tenant
    entity = None
    if link_data.entity_type_code == "customer":
        entity = db.exec(
            select(Customer)
            .where(Customer.id == link_data.entity_id)
            .where(Customer.tenant_id == user_context.tenant_id)
        ).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found in this tenant",
            )
    elif link_data.entity_type_code == "site":
        entity = db.exec(
            select(Site)
            .where(Site.id == link_data.entity_id)
            .where(Site.tenant_id == user_context.tenant_id)
        ).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found in this tenant",
            )
    elif link_data.entity_type_code == "job":
        entity = db.exec(
            select(Job)
            .where(Job.id == link_data.entity_id)
            .where(Job.tenant_id == user_context.tenant_id)
        ).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found in this tenant",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity_type_code: {link_data.entity_type_code}",
        )

    # 3. Check for duplicate link
    existing = db.exec(
        select(EntityAddress)
        .where(EntityAddress.entity_type_code == link_data.entity_type_code)
        .where(EntityAddress.entity_id == link_data.entity_id)
        .where(EntityAddress.address_id == address_id)
        .where(EntityAddress.address_type_code == link_data.address_type_code)
        .where(EntityAddress.tenant_id == user_context.tenant_id)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address already linked to this entity with this address type",
        )

    # 4. If is_primary=True, unset other primary addresses for this entity+address_type
    if link_data.is_primary:
        db.exec(
            update(EntityAddress)
            .where(EntityAddress.entity_type_code == link_data.entity_type_code)
            .where(EntityAddress.entity_id == link_data.entity_id)
            .where(EntityAddress.address_type_code == link_data.address_type_code)
            .where(EntityAddress.tenant_id == user_context.tenant_id)
            .values(is_primary=False)
        )
        db.flush()

    # 5. Create the link
    entity_address = EntityAddress(
        tenant_id=user_context.tenant_id,
        entity_type_code=link_data.entity_type_code,
        entity_id=link_data.entity_id,
        address_id=address_id,
        address_type_code=link_data.address_type_code,
        is_primary=link_data.is_primary,
        is_active=True,
    )
    db.add(entity_address)
    db.commit()

    return {"message": "Address linked to entity successfully"}


def _unlink_address_from_entity_impl(
    address_id: UUID,
    unlink_data: EntityAddressUnlink,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Unlink an address from an entity.

    Args:
        address_id: UUID of address to unlink
        unlink_data: Entity unlink data (entity_type, entity_id)
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Success message dict

    Raises:
        HTTPException: If link not found

    Note:
        Removes all EntityAddress links for this address+entity combination
        (regardless of address_type).
    """
    # Find and delete the link(s)
    links = db.exec(
        select(EntityAddress)
        .where(EntityAddress.entity_type_code == unlink_data.entity_type_code)
        .where(EntityAddress.entity_id == unlink_data.entity_id)
        .where(EntityAddress.address_id == address_id)
        .where(EntityAddress.tenant_id == user_context.tenant_id)
    ).all()

    if not links:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address is not linked to this entity",
        )

    for link in links:
        db.delete(link)

    db.commit()

    return {
        "message": f"Address unlinked from entity successfully ({len(links)} link(s) removed)"
    }


def _get_addresses_by_entity_impl(
    entity_type: str,
    entity_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[dict]:
    """
    Get all addresses linked to a specific entity.

    Args:
        entity_type: Entity type code ("customer", "site", "job")
        entity_id: UUID of entity
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        List of address dicts with relationship metadata

    Raises:
        HTTPException: If entity not found or not in tenant
    """
    # 1. Verify entity belongs to user's tenant
    if entity_type == "customer":
        entity = db.exec(
            select(Customer)
            .where(Customer.id == entity_id)
            .where(Customer.tenant_id == user_context.tenant_id)
        ).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found in this tenant",
            )
    elif entity_type == "site":
        entity = db.exec(
            select(Site)
            .where(Site.id == entity_id)
            .where(Site.tenant_id == user_context.tenant_id)
        ).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found in this tenant",
            )
    elif entity_type == "job":
        entity = db.exec(
            select(Job)
            .where(Job.id == entity_id)
            .where(Job.tenant_id == user_context.tenant_id)
        ).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found in this tenant",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity_type: {entity_type}",
        )

    # 2. Query addresses via EntityAddress
    results = db.exec(
        select(Address, EntityAddress)
        .join(EntityAddress, EntityAddress.address_id == Address.id)
        .where(EntityAddress.entity_type_code == entity_type)
        .where(EntityAddress.entity_id == entity_id)
        .where(EntityAddress.is_active == True)
    ).all()

    # 3. Build response with relationship metadata
    addresses = []
    for address, entity_address in results:
        address_dict = {
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
            "address_type": entity_address.address_type_code,
            "is_primary": entity_address.is_primary,
        }
        addresses.append(address_dict)

    return addresses


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================
# NOTE: Test endpoints MUST be registered BEFORE authenticated endpoints
# to avoid route matching conflicts (/{id} would match /test)


@router.post(
    "/test", response_model=AddressResponse, status_code=status.HTTP_201_CREATED
)
def create_address_test(
    address_in: AddressCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new address (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/addresses/test \\
          -H "Content-Type: application/json" \\
          -d '{"line1": "123 Main St", "city": "Houston", "state": "TX", "postal_code": "77001"}'

    Returns:
        AddressResponse with created address data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_address_impl(address_in, db, test_context)


@router.get("/test", response_model=list[AddressResponse])
def list_addresses_test(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List addresses (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Usage:
        curl http://localhost:8000/api/v1/addresses/test

    Returns:
        List of AddressResponse objects
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _list_addresses_impl(skip, limit, db, test_context)


@router.get("/{address_id}/test", response_model=AddressResponse)
def get_address_test(
    address_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific address (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl http://localhost:8000/api/v1/addresses/{address_id}/test

    Returns:
        AddressResponse with address data
    """
    test_context = get_test_context()
    return _get_address_impl(address_id, db, test_context)


@router.patch("/{address_id}/test", response_model=AddressResponse)
def update_address_test(
    address_id: UUID,
    address_in: AddressUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an address (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl -X PATCH http://localhost:8000/api/v1/addresses/{address_id}/test \\
          -H "Content-Type: application/json" \\
          -d '{"city": "Dallas"}'

    Returns:
        AddressResponse with updated address data
    """
    test_context = get_test_context()
    return _update_address_impl(address_id, address_in, db, test_context)


# FIND-152: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete("/{address_id}/test", response_model=SoftDeleteResponse)
def delete_address_test(
    address_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete an address (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Note:
        - Performs soft delete (sets is_active=False)

    Usage:
        curl -X DELETE http://localhost:8000/api/v1/addresses/{address_id}/test

    Returns:
        Success message
    """
    test_context = get_test_context()
    return _delete_address_impl(address_id, db, test_context)


@router.post("/{address_id}/link-to-entity/test")
def link_address_to_entity_test(
    address_id: UUID,
    link_data: EntityAddressLink,
    db: Session = Depends(get_db),
):
    """
    Link an address to an entity (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl -X POST http://localhost:8000/api/v1/addresses/{address_id}/link-to-entity/test \\
          -H "Content-Type: application/json" \\
          -d '{"entity_type_code": "site", "entity_id": "...", "address_type_code": "service_location", "is_primary": true}'

    Returns:
        Success message
    """
    test_context = get_test_context()
    return _link_address_to_entity_impl(address_id, link_data, db, test_context)


@router.delete("/{address_id}/unlink-from-entity/test")
def unlink_address_from_entity_test(
    address_id: UUID,
    unlink_data: EntityAddressUnlink,
    db: Session = Depends(get_db),
):
    """
    Unlink an address from an entity (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl -X DELETE http://localhost:8000/api/v1/addresses/{address_id}/unlink-from-entity/test \\
          -H "Content-Type: application/json" \\
          -d '{"entity_type_code": "site", "entity_id": "..."}'

    Returns:
        Success message
    """
    test_context = get_test_context()
    return _unlink_address_from_entity_impl(address_id, unlink_data, db, test_context)


@router.get("/by-entity/{entity_type}/{entity_id}/test", response_model=list[dict])
def get_addresses_by_entity_test(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get all addresses for a specific entity (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl http://localhost:8000/api/v1/addresses/by-entity/site/{site_id}/test

    Returns:
        List of addresses with relationship metadata (address_type, is_primary)
    """
    test_context = get_test_context()
    return _get_addresses_by_entity_impl(entity_type, entity_id, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post("/", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    address_in: AddressCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.create")),
):
    """
    Create a new address (requires JWT authentication and addresses.create permission).

    Security:
        - Requires valid JWT token
        - Requires addresses.create permission
        - Address created with the caller's tenant_id
        - Link to tenant entities via /link-to-entity endpoint

    Returns:
        AddressResponse with created address data
    """
    return _create_address_impl(address_in, db, current_user)


@router.get("/", response_model=list[AddressResponse])
def list_addresses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.view")),
):
    """
    List addresses (requires JWT authentication and addresses.view permission).

    Security:
        - Requires valid JWT token
        - Requires addresses.view permission
        - Returns the caller's tenant's active addresses
        - Use /by-entity endpoints to see tenant-specific addresses

    Returns:
        List of AddressResponse objects
    """
    return _list_addresses_impl(skip, limit, db, current_user)


@router.get("/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.view")),
):
    """
    Get a specific address (requires JWT authentication and addresses.view permission).

    Security:
        - Requires valid JWT token
        - Requires addresses.view permission

    Returns:
        AddressResponse with address data
    """
    return _get_address_impl(address_id, db, current_user)


@router.patch("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: UUID,
    address_in: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.update")),
):
    """
    Update an address (requires JWT authentication and addresses.update permission).

    Security:
        - Requires valid JWT token
        - Requires addresses.update permission

    Returns:
        AddressResponse with updated address data
    """
    return _update_address_impl(address_id, address_in, db, current_user)


# FIND-152: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete("/{address_id}", response_model=SoftDeleteResponse)
def delete_address(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.delete")),
):
    """
    Delete an address (requires JWT authentication and addresses.delete permission).

    Security:
        - Requires valid JWT token
        - Requires addresses.delete permission
        - Performs soft delete (sets is_active=False)

    Returns:
        Success message
    """
    return _delete_address_impl(address_id, db, current_user)


@router.post("/{address_id}/link-to-entity")
def link_address_to_entity(
    address_id: UUID,
    link_data: EntityAddressLink,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.update")),
):
    """
    Link an address to an entity (customer, site, job).

    Security:
        - Requires valid JWT token
        - Requires addresses.update permission
        - Entity must belong to authenticated user's tenant

    Validation:
        - Only one is_primary=True per entity per address_type
        - Cannot duplicate link (same address + entity + address_type)

    Returns:
        Success message
    """
    return _link_address_to_entity_impl(address_id, link_data, db, current_user)


@router.delete("/{address_id}/unlink-from-entity")
def unlink_address_from_entity(
    address_id: UUID,
    unlink_data: EntityAddressUnlink,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.update")),
):
    """
    Unlink an address from an entity.

    Security:
        - Requires valid JWT token
        - Requires addresses.update permission

    Returns:
        Success message
    """
    return _unlink_address_from_entity_impl(address_id, unlink_data, db, current_user)


@router.get("/by-entity/{entity_type}/{entity_id}", response_model=list[dict])
def get_addresses_by_entity(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("addresses.view")),
):
    """
    Get all addresses for a specific entity.

    Security:
        - Requires valid JWT token
        - Requires addresses.view permission
        - Entity must belong to authenticated user's tenant

    Returns:
        List of addresses with relationship metadata (address_type, is_primary)
    """
    return _get_addresses_by_entity_impl(entity_type, entity_id, db, current_user)
