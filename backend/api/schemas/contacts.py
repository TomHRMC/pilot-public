"""
Contact API schemas for polymorphic relationship management.

This module defines Pydantic schemas for Contact CRUD operations and
EntityContact association management (Gap #6, #8).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class ContactCreate(BaseModel):
    """
    Schema for creating a new contact.

    Contacts are independent entities that can be linked to multiple
    customers, sites, or jobs via EntityContact associations.
    """

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    mobile_phone: str | None = None
    locale: str | None = None
    timezone: str | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    """
    Schema for updating an existing contact.

    All fields are optional - only provided fields will be updated.
    """

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    mobile_phone: str | None = None
    locale: str | None = None
    timezone: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ContactResponse(BaseModel):
    """
    Schema for contact response data.

    Used in API responses for contact retrieval and list operations.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None
    last_name: str | None
    email: str | None
    mobile_phone: str | None
    locale: str | None
    timezone: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EntityContactLink(BaseModel):
    """
    Schema for linking a contact to an entity (customer, site, job).

    Creates an EntityContact association record with role and primary flag.

    Validation Rules:
        - entity_type_code must exist in entity_type table
        - contact_type_code must exist in contact_type table
        - Only one contact can be is_primary=True per entity
        - Cannot link same contact twice with same contact_type to same entity
    """

    entity_type_code: str  # "customer" | "site" | "job"
    entity_id: UUID
    contact_type_code: str  # "primary" | "billing" | "technical" | "decision_maker"
    is_primary: bool = False


class EntityContactUnlink(BaseModel):
    """
    Schema for unlinking a contact from an entity.

    Removes the EntityContact association between contact and entity.
    """

    entity_type_code: str
    entity_id: UUID


class ContactWithRelations(ContactResponse):
    """
    Contact response with its entity associations.

    Includes list of all entities this contact is linked to, with
    relationship metadata (entity type, contact type, primary flag).
    """

    linked_entities: list[dict]
    # Example: [{"entity_type": "customer", "entity_id": "...", "contact_type": "primary", "is_primary": True}]
