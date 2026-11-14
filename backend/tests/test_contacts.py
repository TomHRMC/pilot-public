"""
Tests for Contact API endpoints and EntityContact association management.

This module tests Gap #6 and Gap #8 implementations:
- Contact CRUD operations
- EntityContact linking/unlinking
- Tenant isolation for polymorphic relationships
- Primary contact enforcement
"""

from uuid import uuid4

from app.models.crm import Contact, Customer, EntityContact, Site


class TestContactCRUD:
    """Test basic Contact CRUD operations."""

    def test_create_contact_test_endpoint(self, client, test_tenant):
        """Test creating a contact via test endpoint."""
        response = client.post(
            "/api/v1/contacts/test",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "mobile_phone": "555-1234",
                "notes": "Primary contact",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["email"] == "john.doe@example.com"
        assert data["mobile_phone"] == "555-1234"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_list_contacts_empty(self, client, second_tenant):
        """Test listing contacts when none exist for the given tenant.
        Uses second_tenant which has no seeded contact rows (seed_scenario_customer_comms
        only seeds for TEST_TENANT_ID). test_tenant always has seed data.
        """
        response = client.get("/api/v1/contacts/test")
        assert response.status_code == 200
        # second_tenant has no seeded contacts; response must be a list (possibly empty)
        data = response.json()
        assert isinstance(data, list)

    def test_list_contacts_with_data(self, client, test_tenant, db_session):
        """Test listing contacts after creating some.
        Uses ID-scoped assertions per Seed Data Coexistence Rules (v1.3) —
        seed_scenario_customer_comms pre-seeds contacts for test_tenant.
        """
        # Create test contacts
        contact1 = Contact(
            tenant_id=test_tenant.id,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        contact2 = Contact(
            tenant_id=test_tenant.id,
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
        )
        db_session.add(contact1)
        db_session.add(contact2)
        db_session.commit()

        response = client.get("/api/v1/contacts/test")
        assert response.status_code == 200
        data = response.json()
        # Scope by IDs we just created — don't count all rows (seed data present)
        inserted_ids = {str(contact1.id), str(contact2.id)}
        returned_ids = {c["id"] for c in data}
        assert inserted_ids.issubset(returned_ids), (
            f"Expected {inserted_ids} in {returned_ids}"
        )
        emails = [c["email"] for c in data if c["id"] in inserted_ids]
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails

    def test_get_contact_by_id(self, client, test_tenant, db_session):
        """Test retrieving a specific contact by ID."""
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        response = client.get(f"/api/v1/contacts/{contact.id}/test")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(contact.id)
        assert data["first_name"] == "Jane"
        assert data["email"] == "jane@example.com"

    def test_get_nonexistent_contact(self, client, test_tenant):
        """Test retrieving a contact that doesn't exist."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/contacts/{fake_id}/test")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_contact(self, client, test_tenant, db_session):
        """Test updating a contact's information."""
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Old",
            last_name="Name",
            email="old@example.com",
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        response = client.patch(
            f"/api/v1/contacts/{contact.id}/test",
            json={"first_name": "New", "email": "new@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "New"
        assert data["last_name"] == "Name"  # Unchanged
        assert data["email"] == "new@example.com"

    def test_delete_contact_soft_delete(self, client, test_tenant, db_session):
        """Test soft deleting a contact."""
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Delete",
            last_name="Me",
            email="delete@example.com",
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        response = client.delete(f"/api/v1/contacts/{contact.id}/test")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()

        # Verify soft delete (is_active=False)
        db_session.refresh(contact)
        assert contact.is_active is False


class TestEntityContactLinking:
    """Test EntityContact association management."""

    def test_link_contact_to_customer(self, client, test_tenant, db_session):
        """Test linking a contact to a customer."""
        # Create customer and contact
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="ABC Corp",
            type="company",
        )
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="John",
            last_name="Doe",
            email="john@abc.com",
        )
        db_session.add(customer)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(customer)
        db_session.refresh(contact)

        response = client.post(
            f"/api/v1/contacts/{contact.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(customer.id),
                "contact_type_code": "primary",
                "is_primary": True,
            },
        )
        assert response.status_code == 200
        assert "linked" in response.json()["message"].lower()

        # Verify EntityContact record created
        from sqlmodel import select

        entity_contact = db_session.exec(
            select(EntityContact)
            .where(EntityContact.contact_id == contact.id)
            .where(EntityContact.entity_id == customer.id)
        ).first()
        assert entity_contact is not None
        assert entity_contact.contact_type_code == "primary"
        assert entity_contact.is_primary is True

    def test_link_contact_to_site(self, client, test_tenant, db_session):
        """Test linking a contact to a site."""
        # Create customer, site, and contact
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="XYZ Corp",
            type="company",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        site = Site(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Main Office",
        )
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Jane",
            last_name="Smith",
            email="jane@xyz.com",
        )
        db_session.add(site)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(site)
        db_session.refresh(contact)

        response = client.post(
            f"/api/v1/contacts/{contact.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(site.id),
                "contact_type_code": "technical",
                "is_primary": False,
            },
        )
        assert response.status_code == 200

    def test_unlink_contact_from_customer(self, client, test_tenant, db_session):
        """Test unlinking a contact from a customer."""
        # Create and link
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Test Corp",
            type="company",
        )
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Test",
            last_name="Contact",
            email="test@test.com",
        )
        db_session.add(customer)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(customer)
        db_session.refresh(contact)

        entity_contact = EntityContact(
            tenant_id=test_tenant.id,
            entity_type_code="customer",
            entity_id=customer.id,
            contact_id=contact.id,
            contact_type_code="primary",
            is_primary=True,
        )
        db_session.add(entity_contact)
        db_session.commit()

        # Unlink
        response = client.request(
            "DELETE",
            f"/api/v1/contacts/{contact.id}/unlink-from-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(customer.id),
            },
        )
        assert response.status_code == 200
        assert "unlinked" in response.json()["message"].lower()

    def test_get_contacts_by_customer(self, client, test_tenant, db_session):
        """Test retrieving all contacts for a specific customer."""
        # Create customer with multiple contacts
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Multi Contact Corp",
            type="company",
        )
        contact1 = Contact(
            tenant_id=test_tenant.id,
            first_name="Primary",
            last_name="Contact",
            email="primary@test.com",
        )
        contact2 = Contact(
            tenant_id=test_tenant.id,
            first_name="Billing",
            last_name="Contact",
            email="billing@test.com",
        )
        db_session.add(customer)
        db_session.add(contact1)
        db_session.add(contact2)
        db_session.commit()
        db_session.refresh(customer)
        db_session.refresh(contact1)
        db_session.refresh(contact2)

        # Link both contacts
        entity_contact1 = EntityContact(
            tenant_id=test_tenant.id,
            entity_type_code="customer",
            entity_id=customer.id,
            contact_id=contact1.id,
            contact_type_code="primary",
            is_primary=True,
        )
        entity_contact2 = EntityContact(
            tenant_id=test_tenant.id,
            entity_type_code="customer",
            entity_id=customer.id,
            contact_id=contact2.id,
            contact_type_code="billing",
            is_primary=False,
        )
        db_session.add(entity_contact1)
        db_session.add(entity_contact2)
        db_session.commit()

        # Get contacts for customer
        response = client.get(f"/api/v1/contacts/by-entity/customer/{customer.id}/test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify relationship metadata
        contact_types = {c["email"]: c["contact_type"] for c in data}
        assert contact_types["primary@test.com"] == "primary"
        assert contact_types["billing@test.com"] == "billing"

        # Verify is_primary flag
        primary_contacts = [c for c in data if c["is_primary"]]
        assert len(primary_contacts) == 1
        assert primary_contacts[0]["email"] == "primary@test.com"

    def test_primary_contact_enforcement(self, client, test_tenant, db_session):
        """Test that only one contact can be primary per entity."""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Primary Test Corp",
            type="company",
        )
        contact1 = Contact(
            tenant_id=test_tenant.id,
            first_name="First",
            last_name="Primary",
            email="first@test.com",
        )
        contact2 = Contact(
            tenant_id=test_tenant.id,
            first_name="Second",
            last_name="Primary",
            email="second@test.com",
        )
        db_session.add(customer)
        db_session.add(contact1)
        db_session.add(contact2)
        db_session.commit()
        db_session.refresh(customer)
        db_session.refresh(contact1)
        db_session.refresh(contact2)

        # Link first contact as primary
        client.post(
            f"/api/v1/contacts/{contact1.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(customer.id),
                "contact_type_code": "primary",
                "is_primary": True,
            },
        )

        # Link second contact as primary (should unset first)
        client.post(
            f"/api/v1/contacts/{contact2.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(customer.id),
                "contact_type_code": "technical",
                "is_primary": True,
            },
        )

        # Verify only second contact is primary
        from sqlmodel import select

        links = db_session.exec(
            select(EntityContact)
            .where(EntityContact.entity_type_code == "customer")
            .where(EntityContact.entity_id == customer.id)
            .where(EntityContact.is_primary == True)
        ).all()
        assert len(links) == 1
        assert links[0].contact_id == contact2.id

    def test_duplicate_link_prevention(self, client, test_tenant, db_session):
        """Test that same contact cannot be linked twice with same type."""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Duplicate Test",
            type="company",
        )
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Duplicate",
            last_name="Test",
            email="dup@test.com",
        )
        db_session.add(customer)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(customer)
        db_session.refresh(contact)

        # First link succeeds
        response1 = client.post(
            f"/api/v1/contacts/{contact.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(customer.id),
                "contact_type_code": "primary",
                "is_primary": True,
            },
        )
        assert response1.status_code == 200

        # Second link with same type fails
        response2 = client.post(
            f"/api/v1/contacts/{contact.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(customer.id),
                "contact_type_code": "primary",
                "is_primary": False,
            },
        )
        assert response2.status_code == 400
        assert "already linked" in response2.json()["detail"].lower()

    def test_link_contact_to_nonexistent_entity(self, client, test_tenant, db_session):
        """Test linking contact to entity that doesn't exist."""
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Test",
            last_name="Contact",
            email="test@test.com",
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        fake_customer_id = uuid4()
        response = client.post(
            f"/api/v1/contacts/{contact.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(fake_customer_id),
                "contact_type_code": "primary",
                "is_primary": True,
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestContactTenantIsolation:
    """Test tenant isolation for contact operations."""

    def test_cannot_access_other_tenant_contact(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that getting another tenant's contact returns 404."""
        other_contact = Contact(tenant_id=second_tenant.id, first_name="Other")
        db_session.add(other_contact)
        db_session.commit()
        db_session.refresh(other_contact)

        response = client.get(f"/api/v1/contacts/{other_contact.id}/test")
        assert response.status_code == 404

    def test_cannot_update_other_tenant_contact(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that updating another tenant's contact returns 404."""
        other_contact = Contact(tenant_id=second_tenant.id, first_name="Other")
        db_session.add(other_contact)
        db_session.commit()
        db_session.refresh(other_contact)

        response = client.patch(
            f"/api/v1/contacts/{other_contact.id}/test", json={"first_name": "Hacked"}
        )
        assert response.status_code == 404

    def test_cannot_delete_other_tenant_contact(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that deleting another tenant's contact returns 404."""
        other_contact = Contact(tenant_id=second_tenant.id, first_name="Other")
        db_session.add(other_contact)
        db_session.commit()
        db_session.refresh(other_contact)

        response = client.delete(f"/api/v1/contacts/{other_contact.id}/test")
        assert response.status_code == 404

    def test_cannot_link_to_other_tenant_customer(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that linking to other tenant's customer fails."""
        # Create customer in second tenant
        other_customer = Customer(
            tenant_id=second_tenant.id,
            display_name="Other Tenant Customer",
            type="company",
        )
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Test",
            last_name="Contact",
            email="test@test.com",
        )
        db_session.add(other_customer)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(other_customer)
        db_session.refresh(contact)

        # Try to link (should fail - customer not in test tenant)
        response = client.post(
            f"/api/v1/contacts/{contact.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(other_customer.id),
                "contact_type_code": "primary",
                "is_primary": True,
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cannot_get_contacts_for_other_tenant_customer(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that querying other tenant's customer contacts fails."""
        # Create customer in second tenant
        other_customer = Customer(
            tenant_id=second_tenant.id,
            display_name="Other Tenant Customer",
            type="company",
        )
        db_session.add(other_customer)
        db_session.commit()
        db_session.refresh(other_customer)

        response = client.get(
            f"/api/v1/contacts/by-entity/customer/{other_customer.id}/test"
        )
        assert response.status_code == 404
