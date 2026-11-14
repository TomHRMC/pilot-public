"""
Address API schemas for polymorphic relationship management.

This module defines Pydantic schemas for Address CRUD operations and
EntityAddress association management (Gap #6, #7).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AddressCreate(BaseModel):
    """
    Schema for creating a new address.

    Addresses are independent entities that can be linked to multiple
    customers, sites, or jobs via EntityAddress associations.
    """

    line1: str | None = None
    line2: str | None = None
    line3: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"
    latitude: float | None = None
    longitude: float | None = None


class AddressUpdate(BaseModel):
    """
    Schema for updating an existing address.

    All fields are optional - only provided fields will be updated.
    """

    line1: str | None = None
    line2: str | None = None
    line3: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool | None = None


class AddressResponse(BaseModel):
    """
    Schema for address response data.

    Used in API responses for address retrieval and list operations.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line1: str | None
    line2: str | None
    line3: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str
    latitude: float | None
    longitude: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EntityAddressLink(BaseModel):
    """
    Schema for linking an address to an entity (customer, site, job).

    Creates an EntityAddress association record with type and primary flag.

    Validation Rules:
        - entity_type_code must exist in entity_type table
        - address_type_code must exist in address_type table
        - Only one address can be is_primary=True per entity per address_type
        - Cannot link same address twice with same address_type to same entity
    """

    entity_type_code: str  # "customer" | "site" | "job"
    entity_id: UUID
    address_type_code: str  # "billing" | "service_location" | "mailing" | "shipping"
    is_primary: bool = False


class EntityAddressUnlink(BaseModel):
    """
    Schema for unlinking an address from an entity.

    Removes the EntityAddress association between address and entity.
    """

    entity_type_code: str
    entity_id: UUID


class AddressWithRelations(AddressResponse):
    """
    Address response with its entity associations.

    Includes list of all entities this address is linked to, with
    relationship metadata (entity type, address type, primary flag).
    """

    linked_entities: list[dict]
    # Example: [{"entity_type": "site", "entity_id": "...", "address_type": "service_location", "is_primary": True}]
