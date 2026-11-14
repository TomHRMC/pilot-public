"""
Contact API routes for polymorphic relationship management.

This module implements Contact CRUD operations and EntityContact association
management (Gap #6, #8).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, update

from api.schemas.contacts import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    EntityContactLink,
    EntityContactUnlink,
)
from api.schemas.schemas import SoftDeleteResponse
from app.models.crm import Contact, Customer, EntityContact, Site
from app.models.fulfillment import Job
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _create_contact_impl(
    contact_in: ContactCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Contact:
    """
    Shared contact creation logic used by both authenticated and test endpoints.

    Args:
        contact_in: Contact data to create
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Created Contact instance

    Note:
        Tenant-scoped: the new row carries the caller's tenant_id.
        Tenant isolation is enforced when linking via EntityContact.
    """
    contact = Contact(
        tenant_id=user_context.tenant_id,
        first_name=contact_in.first_name,
        last_name=contact_in.last_name,
        email=contact_in.email,
        mobile_phone=contact_in.mobile_phone,
        locale=contact_in.locale,
        timezone=contact_in.timezone,
        notes=contact_in.notes,
    )

    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def _list_contacts_impl(
    skip: int,
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[Contact]:
    """
    Shared contact listing logic used by both authenticated and test endpoints.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        List of Contact instances

    Note:
        Tenant-scoped: filters on the caller's tenant_id. To see the contacts for one entity,
        use /contacts/by-entity/{entity_type}/{entity_id} endpoints.
    """
    statement = (
        select(Contact)
        .where(Contact.is_active == True)
        .where(Contact.tenant_id == user_context.tenant_id)
        .offset(skip)
        .limit(limit)
    )
    contacts = db.exec(statement).all()
    return contacts


def _get_contact_impl(
    contact_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Contact:
    """
    Shared contact retrieval logic used by both authenticated and test endpoints.

    Args:
        contact_id: UUID of contact to retrieve
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Contact instance

    Raises:
        HTTPException: If contact not found
    """
    contact = db.exec(
        select(Contact).where(
            Contact.id == contact_id, Contact.tenant_id == user_context.tenant_id
        )
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    return contact


def _update_contact_impl(
    contact_id: UUID,
    contact_in: ContactUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Contact:
    """
    Shared contact update logic used by both authenticated and test endpoints.

    Args:
        contact_id: UUID of contact to update
        contact_in: Updated contact data
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Updated Contact instance

    Raises:
        HTTPException: If contact not found
    """
    contact = db.exec(
        select(Contact).where(
            Contact.id == contact_id, Contact.tenant_id == user_context.tenant_id
        )
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # Update only provided fields
    update_data = contact_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def _delete_contact_impl(
    contact_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Shared contact deletion logic used by both authenticated and test endpoints.

    Args:
        contact_id: UUID of contact to delete
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Success message dict

    Raises:
        HTTPException: If contact not found

    Note:
        Performs soft delete by setting is_active=False.
    """
    contact = db.exec(
        select(Contact).where(
            Contact.id == contact_id, Contact.tenant_id == user_context.tenant_id
        )
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # Soft delete
    contact.is_active = False
    db.add(contact)
    db.commit()

    return {"message": "Contact deleted successfully", "id": str(contact_id)}


def _link_contact_to_entity_impl(
    contact_id: UUID,
    link_data: EntityContactLink,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Link a contact to an entity (customer, site, job).

    Args:
        contact_id: UUID of contact to link
        link_data: Entity link data (entity_type, entity_id, contact_type, is_primary)
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Success message dict

    Raises:
        HTTPException: If contact/entity not found, entity not in tenant, or duplicate link

    Validation:
        - Contact must exist
        - Entity must exist and belong to user's tenant
        - Cannot duplicate link (same contact + entity + contact_type)
        - Only one is_primary=True per entity (auto-unsets others if is_primary=True)
    """
    # 1. Verify contact exists
    contact = db.exec(
        select(Contact).where(
            Contact.id == contact_id, Contact.tenant_id == user_context.tenant_id
        )
    ).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
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
        select(EntityContact)
        .where(EntityContact.entity_type_code == link_data.entity_type_code)
        .where(EntityContact.entity_id == link_data.entity_id)
        .where(EntityContact.contact_id == contact_id)
        .where(EntityContact.contact_type_code == link_data.contact_type_code)
        .where(EntityContact.tenant_id == user_context.tenant_id)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact already linked to this entity with this contact type",
        )

    # 4. If is_primary=True, unset other primary contacts for this entity
    if link_data.is_primary:
        db.exec(
            update(EntityContact)
            .where(EntityContact.entity_type_code == link_data.entity_type_code)
            .where(EntityContact.entity_id == link_data.entity_id)
            .where(EntityContact.tenant_id == user_context.tenant_id)
            .values(is_primary=False)
        )
        db.flush()

    # 5. Create the link
    entity_contact = EntityContact(
        tenant_id=user_context.tenant_id,
        entity_type_code=link_data.entity_type_code,
        entity_id=link_data.entity_id,
        contact_id=contact_id,
        contact_type_code=link_data.contact_type_code,
        is_primary=link_data.is_primary,
    )
    db.add(entity_contact)
    db.commit()

    return {"message": "Contact linked to entity successfully"}


def _unlink_contact_from_entity_impl(
    contact_id: UUID,
    unlink_data: EntityContactUnlink,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """
    Unlink a contact from an entity.

    Args:
        contact_id: UUID of contact to unlink
        unlink_data: Entity unlink data (entity_type, entity_id)
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        Success message dict

    Raises:
        HTTPException: If link not found

    Note:
        Removes all EntityContact links for this contact+entity combination
        (regardless of contact_type).
    """
    # Find and delete the link(s)
    links = db.exec(
        select(EntityContact)
        .where(EntityContact.entity_type_code == unlink_data.entity_type_code)
        .where(EntityContact.entity_id == unlink_data.entity_id)
        .where(EntityContact.contact_id == contact_id)
        .where(EntityContact.tenant_id == user_context.tenant_id)
    ).all()

    if not links:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact is not linked to this entity",
        )

    for link in links:
        db.delete(link)

    db.commit()

    return {
        "message": f"Contact unlinked from entity successfully ({len(links)} link(s) removed)"
    }


def _get_contacts_by_entity_impl(
    entity_type: str,
    entity_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[dict]:
    """
    Get all contacts linked to a specific entity.

    Args:
        entity_type: Entity type code ("customer", "site", "job")
        entity_id: UUID of entity
        db: Database session
        user_context: AuthenticatedUser (authenticated) or TestUserContext (test mode)

    Returns:
        List of contact dicts with relationship metadata

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

    # 2. Query contacts via EntityContact
    results = db.exec(
        select(Contact, EntityContact)
        .join(EntityContact, EntityContact.contact_id == Contact.id)
        .where(EntityContact.entity_type_code == entity_type)
        .where(EntityContact.entity_id == entity_id)
        .where(EntityContact.tenant_id == user_context.tenant_id)
        .where(Contact.tenant_id == user_context.tenant_id)
    ).all()

    # 3. Build response with relationship metadata
    contacts = []
    for contact, entity_contact in results:
        contact_dict = {
            "id": contact.id,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "mobile_phone": contact.mobile_phone,
            "locale": contact.locale,
            "timezone": contact.timezone,
            "notes": contact.notes,
            "is_active": contact.is_active,
            "created_at": contact.created_at,
            "updated_at": contact.updated_at,
            "contact_type": entity_contact.contact_type_code,
            "is_primary": entity_contact.is_primary,
        }
        contacts.append(contact_dict)

    return contacts


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================
# NOTE: Test endpoints MUST be registered BEFORE authenticated endpoints
# to avoid route matching conflicts (/{id} would match /test)


@router.post(
    "/test", response_model=ContactResponse, status_code=status.HTTP_201_CREATED
)
def create_contact_test(
    contact_in: ContactCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new contact (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/contacts/test \\
          -H "Content-Type: application/json" \\
          -d '{"first_name": "John", "last_name": "Doe", "email": "john@example.com"}'

    Returns:
        ContactResponse with created contact data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_contact_impl(contact_in, db, test_context)


@router.get("/test", response_model=list[ContactResponse])
def list_contacts_test(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List contacts (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Usage:
        curl http://localhost:8000/api/v1/contacts/test

    Returns:
        List of ContactResponse objects
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _list_contacts_impl(skip, limit, db, test_context)


@router.get("/{contact_id}/test", response_model=ContactResponse)
def get_contact_test(
    contact_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific contact (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl http://localhost:8000/api/v1/contacts/{contact_id}/test

    Returns:
        ContactResponse with contact data
    """
    test_context = get_test_context()
    return _get_contact_impl(contact_id, db, test_context)


@router.patch("/{contact_id}/test", response_model=ContactResponse)
def update_contact_test(
    contact_id: UUID,
    contact_in: ContactUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a contact (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl -X PATCH http://localhost:8000/api/v1/contacts/{contact_id}/test \\
          -H "Content-Type: application/json" \\
          -d '{"email": "updated@example.com"}'

    Returns:
        ContactResponse with updated contact data
    """
    test_context = get_test_context()
    return _update_contact_impl(contact_id, contact_in, db, test_context)


# FIND-153: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete("/{contact_id}/test", response_model=SoftDeleteResponse)
def delete_contact_test(
    contact_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a contact (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Note:
        - Performs soft delete (sets is_active=False)

    Usage:
        curl -X DELETE http://localhost:8000/api/v1/contacts/{contact_id}/test

    Returns:
        Success message
    """
    test_context = get_test_context()
    return _delete_contact_impl(contact_id, db, test_context)


@router.post("/{contact_id}/link-to-entity/test")
def link_contact_to_entity_test(
    contact_id: UUID,
    link_data: EntityContactLink,
    db: Session = Depends(get_db),
):
    """
    Link a contact to an entity (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl -X POST http://localhost:8000/api/v1/contacts/{contact_id}/link-to-entity/test \\
          -H "Content-Type: application/json" \\
          -d '{"entity_type_code": "customer", "entity_id": "...", "contact_type_code": "primary", "is_primary": true}'

    Returns:
        Success message
    """
    test_context = get_test_context()
    return _link_contact_to_entity_impl(contact_id, link_data, db, test_context)


@router.delete("/{contact_id}/unlink-from-entity/test")
def unlink_contact_from_entity_test(
    contact_id: UUID,
    unlink_data: EntityContactUnlink,
    db: Session = Depends(get_db),
):
    """
    Unlink a contact from an entity (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl -X DELETE http://localhost:8000/api/v1/contacts/{contact_id}/unlink-from-entity/test \\
          -H "Content-Type: application/json" \\
          -d '{"entity_type_code": "customer", "entity_id": "..."}'

    Returns:
        Success message
    """
    test_context = get_test_context()
    return _unlink_contact_from_entity_impl(contact_id, unlink_data, db, test_context)


@router.get("/by-entity/{entity_type}/{entity_id}/test", response_model=list[dict])
def get_contacts_by_entity_test(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get all contacts for a specific entity (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Usage:
        curl http://localhost:8000/api/v1/contacts/by-entity/customer/{customer_id}/test

    Returns:
        List of contacts with relationship metadata (contact_type, is_primary)
    """
    test_context = get_test_context()
    return _get_contacts_by_entity_impl(entity_type, entity_id, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    contact_in: ContactCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.create")),
):
    """
    Create a new contact (requires JWT authentication and contacts.create permission).

    Security:
        - Requires valid JWT token
        - Requires contacts.create permission
        - Contact created with the caller's tenant_id
        - Link to tenant entities via /link-to-entity endpoint

    Returns:
        ContactResponse with created contact data
    """
    return _create_contact_impl(contact_in, db, current_user)


@router.get("/", response_model=list[ContactResponse])
def list_contacts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.view")),
):
    """
    List contacts (requires JWT authentication and contacts.view permission).

    Security:
        - Requires valid JWT token
        - Requires contacts.view permission
        - Returns the caller's tenant's active contacts
        - Use /by-entity endpoints to see tenant-specific contacts

    Returns:
        List of ContactResponse objects
    """
    return _list_contacts_impl(skip, limit, db, current_user)


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.view")),
):
    """
    Get a specific contact (requires JWT authentication and contacts.view permission).

    Security:
        - Requires valid JWT token
        - Requires contacts.view permission

    Returns:
        ContactResponse with contact data
    """
    return _get_contact_impl(contact_id, db, current_user)


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: UUID,
    contact_in: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.update")),
):
    """
    Update a contact (requires JWT authentication and contacts.update permission).

    Security:
        - Requires valid JWT token
        - Requires contacts.update permission

    Returns:
        ContactResponse with updated contact data
    """
    return _update_contact_impl(contact_id, contact_in, db, current_user)


# FIND-153: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete("/{contact_id}", response_model=SoftDeleteResponse)
def delete_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.delete")),
):
    """
    Delete a contact (requires JWT authentication and contacts.delete permission).

    Security:
        - Requires valid JWT token
        - Requires contacts.delete permission
        - Performs soft delete (sets is_active=False)

    Returns:
        Success message
    """
    return _delete_contact_impl(contact_id, db, current_user)


@router.post("/{contact_id}/link-to-entity")
def link_contact_to_entity(
    contact_id: UUID,
    link_data: EntityContactLink,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.update")),
):
    """
    Link a contact to an entity (customer, site, job).

    Security:
        - Requires valid JWT token
        - Requires contacts.update permission
        - Entity must belong to authenticated user's tenant

    Validation:
        - Only one is_primary=True per entity
        - Cannot duplicate link (same contact + entity + contact_type)

    Returns:
        Success message
    """
    return _link_contact_to_entity_impl(contact_id, link_data, db, current_user)


@router.delete("/{contact_id}/unlink-from-entity")
def unlink_contact_from_entity(
    contact_id: UUID,
    unlink_data: EntityContactUnlink,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.update")),
):
    """
    Unlink a contact from an entity.

    Security:
        - Requires valid JWT token
        - Requires contacts.update permission

    Returns:
        Success message
    """
    return _unlink_contact_from_entity_impl(contact_id, unlink_data, db, current_user)


@router.get("/by-entity/{entity_type}/{entity_id}", response_model=list[dict])
def get_contacts_by_entity(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("contacts.view")),
):
    """
    Get all contacts for a specific entity.

    Security:
        - Requires valid JWT token
        - Requires contacts.view permission
        - Entity must belong to authenticated user's tenant

    Returns:
        List of contacts with relationship metadata (contact_type, is_primary)
    """
    return _get_contacts_by_entity_impl(entity_type, entity_id, db, current_user)
