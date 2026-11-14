"""
Tests for Address API endpoints and EntityAddress association management.

This module tests Gap #6 and Gap #7 implementations:
- Address CRUD operations
- EntityAddress linking/unlinking
- Tenant isolation for polymorphic relationships
- Primary address enforcement per address type
- Site address auto-creation
"""

from uuid import uuid4

from sqlalchemy import delete

from app.models.crm import Address, Customer, EntityAddress, Site


class TestAddressCRUD:
    """Test basic Address CRUD operations."""

    def test_create_address_test_endpoint(self, client, test_tenant):
        """Test creating an address via test endpoint."""
        response = client.post(
            "/api/v1/addresses/test",
            json={
                "line1": "123 Main St",
                "line2": "Suite 100",
                "city": "Houston",
                "state": "TX",
                "postal_code": "77001",
                "country": "US",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["line1"] == "123 Main St"
        assert data["city"] == "Houston"
        assert data["state"] == "TX"
        assert data["postal_code"] == "77001"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_list_addresses_empty(self, client, test_tenant, db_session):
        """Test listing addresses when none exist (scoped to this tenant)."""
        # Delete entity_address links first (child FK), then address rows (parent)
        db_session.exec(
            delete(EntityAddress).where(EntityAddress.tenant_id == test_tenant.id)
        )
        db_session.exec(delete(Address).where(Address.tenant_id == test_tenant.id))
        db_session.commit()

        response = client.get("/api/v1/addresses/test")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_addresses_with_data(self, client, test_tenant, db_session):
        """Test listing addresses after creating some."""
        # Delete entity_address links first (child FK), then address rows (parent)
        db_session.exec(
            delete(EntityAddress).where(EntityAddress.tenant_id == test_tenant.id)
        )
        db_session.exec(delete(Address).where(Address.tenant_id == test_tenant.id))
        db_session.commit()

        # Create test addresses
        address1 = Address(
            tenant_id=test_tenant.id,
            line1="100 First St",
            city="Dallas",
            state="TX",
            postal_code="75201",
        )
        address2 = Address(
            tenant_id=test_tenant.id,
            line1="200 Second Ave",
            city="Austin",
            state="TX",
            postal_code="78701",
        )
        db_session.add(address1)
        db_session.add(address2)
        db_session.commit()

        response = client.get("/api/v1/addresses/test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        cities = [a["city"] for a in data]
        assert "Dallas" in cities
        assert "Austin" in cities

    def test_get_address_by_id(self, client, test_tenant, db_session):
        """Test retrieving a specific address by ID."""
        address = Address(
            tenant_id=test_tenant.id,
            line1="300 Third Blvd",
            city="San Antonio",
            state="TX",
            postal_code="78201",
        )
        db_session.add(address)
        db_session.commit()
        db_session.refresh(address)

        response = client.get(f"/api/v1/addresses/{address.id}/test")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(address.id)
        assert data["line1"] == "300 Third Blvd"
        assert data["city"] == "San Antonio"

    def test_get_nonexistent_address(self, client, test_tenant):
        """Test retrieving an address that doesn't exist."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/addresses/{fake_id}/test")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_address(self, client, test_tenant, db_session):
        """Test updating an address's information."""
        address = Address(
            tenant_id=test_tenant.id,
            line1="Old Address",
            city="Old City",
            state="TX",
            postal_code="00000",
        )
        db_session.add(address)
        db_session.commit()
        db_session.refresh(address)

        response = client.patch(
            f"/api/v1/addresses/{address.id}/test",
            json={"line1": "New Address", "city": "New City"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["line1"] == "New Address"
        assert data["city"] == "New City"
        assert data["state"] == "TX"  # Unchanged

    def test_delete_address_soft_delete(self, client, test_tenant, db_session):
        """Test soft deleting an address."""
        address = Address(
            tenant_id=test_tenant.id,
            line1="Delete Me St",
            city="Deleteville",
            state="TX",
            postal_code="99999",
        )
        db_session.add(address)
        db_session.commit()
        db_session.refresh(address)

        response = client.delete(f"/api/v1/addresses/{address.id}/test")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()

        # Verify soft delete (is_active=False)
        db_session.refresh(address)
        assert address.is_active is False


class TestEntityAddressLinking:
    """Test EntityAddress association management."""

    def test_link_address_to_site(self, client, test_tenant, db_session):
        """Test linking an address to a site."""
        # Create customer, site, and address
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="ABC Corp",
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
        address = Address(
            tenant_id=test_tenant.id,
            line1="123 Business Pkwy",
            city="Houston",
            state="TX",
            postal_code="77001",
        )
        db_session.add(site)
        db_session.add(address)
        db_session.commit()
        db_session.refresh(site)
        db_session.refresh(address)

        response = client.post(
            f"/api/v1/addresses/{address.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(site.id),
                "address_type_code": "service_location",
                "is_primary": True,
            },
        )
        assert response.status_code == 200
        assert "linked" in response.json()["message"].lower()

        # Verify EntityAddress record created
        from sqlmodel import select

        entity_address = db_session.exec(
            select(EntityAddress)
            .where(EntityAddress.address_id == address.id)
            .where(EntityAddress.entity_id == site.id)
        ).first()
        assert entity_address is not None
        assert entity_address.address_type_code == "service_location"
        assert entity_address.is_primary is True

    def test_link_address_to_customer(self, client, test_tenant, db_session):
        """Test linking an address to a customer."""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="XYZ Corp",
            type="company",
        )
        address = Address(
            tenant_id=test_tenant.id,
            line1="456 Corporate Dr",
            city="Dallas",
            state="TX",
            postal_code="75201",
        )
        db_session.add(customer)
        db_session.add(address)
        db_session.commit()
        db_session.refresh(customer)
        db_session.refresh(address)

        response = client.post(
            f"/api/v1/addresses/{address.id}/link-to-entity/test",
            json={
                "entity_type_code": "customer",
                "entity_id": str(customer.id),
                "address_type_code": "billing",
                "is_primary": True,
            },
        )
        assert response.status_code == 200

    def test_unlink_address_from_site(self, client, test_tenant, db_session):
        """Test unlinking an address from a site."""
        # Create and link
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Test Corp",
            type="company",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        site = Site(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
        )
        address = Address(
            tenant_id=test_tenant.id,
            line1="789 Test Ave",
            city="Austin",
            state="TX",
            postal_code="78701",
        )
        db_session.add(site)
        db_session.add(address)
        db_session.commit()
        db_session.refresh(site)
        db_session.refresh(address)

        entity_address = EntityAddress(
            tenant_id=test_tenant.id,
            entity_type_code="site",
            entity_id=site.id,
            address_id=address.id,
            address_type_code="service_location",
            is_primary=True,
            is_active=True,
        )
        db_session.add(entity_address)
        db_session.commit()

        # Unlink
        response = client.request(
            "DELETE",
            f"/api/v1/addresses/{address.id}/unlink-from-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(site.id),
            },
        )
        assert response.status_code == 200
        assert "unlinked" in response.json()["message"].lower()

    def test_get_addresses_by_site(self, client, test_tenant, db_session):
        """Test retrieving all addresses for a specific site."""
        # Create site with multiple addresses
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Multi Address Corp",
            type="company",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        site = Site(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
        )
        address1 = Address(
            tenant_id=test_tenant.id,
            line1="100 Service Ln",
            city="Houston",
            state="TX",
            postal_code="77001",
        )
        address2 = Address(
            tenant_id=test_tenant.id,
            line1="200 Billing Blvd",
            city="Houston",
            state="TX",
            postal_code="77002",
        )
        db_session.add(site)
        db_session.add(address1)
        db_session.add(address2)
        db_session.commit()
        db_session.refresh(site)
        db_session.refresh(address1)
        db_session.refresh(address2)

        # Link both addresses
        entity_address1 = EntityAddress(
            tenant_id=test_tenant.id,
            entity_type_code="site",
            entity_id=site.id,
            address_id=address1.id,
            address_type_code="service_location",
            is_primary=True,
            is_active=True,
        )
        entity_address2 = EntityAddress(
            tenant_id=test_tenant.id,
            entity_type_code="site",
            entity_id=site.id,
            address_id=address2.id,
            address_type_code="billing",
            is_primary=True,
            is_active=True,
        )
        db_session.add(entity_address1)
        db_session.add(entity_address2)
        db_session.commit()

        # Get addresses for site
        response = client.get(f"/api/v1/addresses/by-entity/site/{site.id}/test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify relationship metadata
        address_types = {a["line1"]: a["address_type"] for a in data}
        assert address_types["100 Service Ln"] == "service_location"
        assert address_types["200 Billing Blvd"] == "billing"

        # Verify both are primary (different types)
        primary_addresses = [a for a in data if a["is_primary"]]
        assert len(primary_addresses) == 2

    def test_primary_address_enforcement_per_type(
        self, client, test_tenant, db_session
    ):
        """Test that only one address can be primary per entity per address_type."""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Primary Test Corp",
            type="company",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        site = Site(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
        )
        address1 = Address(
            tenant_id=test_tenant.id,
            line1="First Service Address",
            city="Houston",
            state="TX",
            postal_code="77001",
        )
        address2 = Address(
            tenant_id=test_tenant.id,
            line1="Second Service Address",
            city="Houston",
            state="TX",
            postal_code="77002",
        )
        db_session.add(site)
        db_session.add(address1)
        db_session.add(address2)
        db_session.commit()
        db_session.refresh(site)
        db_session.refresh(address1)
        db_session.refresh(address2)

        # Link first address as primary service_location
        client.post(
            f"/api/v1/addresses/{address1.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(site.id),
                "address_type_code": "service_location",
                "is_primary": True,
            },
        )

        # Link second address as primary service_location (should unset first)
        client.post(
            f"/api/v1/addresses/{address2.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(site.id),
                "address_type_code": "service_location",
                "is_primary": True,
            },
        )

        # Verify only second address is primary for service_location
        from sqlmodel import select

        links = db_session.exec(
            select(EntityAddress)
            .where(EntityAddress.entity_type_code == "site")
            .where(EntityAddress.entity_id == site.id)
            .where(EntityAddress.address_type_code == "service_location")
            .where(EntityAddress.is_primary == True)
        ).all()
        assert len(links) == 1
        assert links[0].address_id == address2.id

    def test_duplicate_link_prevention(self, client, test_tenant, db_session):
        """Test that same address cannot be linked twice with same type."""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Duplicate Test",
            type="company",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        site = Site(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
        )
        address = Address(
            tenant_id=test_tenant.id,
            line1="Duplicate Address",
            city="Houston",
            state="TX",
            postal_code="77001",
        )
        db_session.add(site)
        db_session.add(address)
        db_session.commit()
        db_session.refresh(site)
        db_session.refresh(address)

        # First link succeeds
        response1 = client.post(
            f"/api/v1/addresses/{address.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(site.id),
                "address_type_code": "service_location",
                "is_primary": True,
            },
        )
        assert response1.status_code == 200

        # Second link with same type fails
        response2 = client.post(
            f"/api/v1/addresses/{address.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(site.id),
                "address_type_code": "service_location",
                "is_primary": False,
            },
        )
        assert response2.status_code == 400
        assert "already linked" in response2.json()["detail"].lower()

    def test_link_address_to_nonexistent_entity(self, client, test_tenant, db_session):
        """Test linking address to entity that doesn't exist."""
        address = Address(
            tenant_id=test_tenant.id,
            line1="Test Address",
            city="Houston",
            state="TX",
            postal_code="77001",
        )
        db_session.add(address)
        db_session.commit()
        db_session.refresh(address)

        fake_site_id = uuid4()
        response = client.post(
            f"/api/v1/addresses/{address.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(fake_site_id),
                "address_type_code": "service_location",
                "is_primary": True,
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAddressTenantIsolation:
    """Test tenant isolation for address operations."""

    def test_cannot_access_other_tenant_address(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that getting another tenant's address returns 404."""
        other_address = Address(
            tenant_id=second_tenant.id, line1="Other St", city="Other City"
        )
        db_session.add(other_address)
        db_session.commit()
        db_session.refresh(other_address)

        response = client.get(f"/api/v1/addresss/{other_address.id}/test")
        assert response.status_code == 404

    def test_cannot_update_other_tenant_address(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that updating another tenant's address returns 404."""
        other_address = Address(
            tenant_id=second_tenant.id, line1="Other St", city="Other City"
        )
        db_session.add(other_address)
        db_session.commit()
        db_session.refresh(other_address)

        response = client.patch(
            f"/api/v1/addresss/{other_address.id}/test", json={"line1": "Hacked St"}
        )
        assert response.status_code == 404

    def test_cannot_delete_other_tenant_address(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that deleting another tenant's address returns 404."""
        other_address = Address(
            tenant_id=second_tenant.id, line1="Other St", city="Other City"
        )
        db_session.add(other_address)
        db_session.commit()
        db_session.refresh(other_address)

        response = client.delete(f"/api/v1/addresss/{other_address.id}/test")
        assert response.status_code == 404

    def test_cannot_link_to_other_tenant_site(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that linking to other tenant's site fails."""
        # Create customer and site in second tenant
        other_customer = Customer(
            tenant_id=second_tenant.id,
            display_name="Other Tenant Customer",
            type="company",
        )
        db_session.add(other_customer)
        db_session.commit()
        db_session.refresh(other_customer)

        other_site = Site(
            tenant_id=second_tenant.id,
            customer_id=other_customer.id,
            name="Other Site",
        )
        address = Address(
            tenant_id=test_tenant.id,
            line1="Test Address",
            city="Houston",
            state="TX",
            postal_code="77001",
        )
        db_session.add(other_site)
        db_session.add(address)
        db_session.commit()
        db_session.refresh(other_site)
        db_session.refresh(address)

        # Try to link (should fail - site not in test tenant)
        response = client.post(
            f"/api/v1/addresses/{address.id}/link-to-entity/test",
            json={
                "entity_type_code": "site",
                "entity_id": str(other_site.id),
                "address_type_code": "service_location",
                "is_primary": True,
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cannot_get_addresses_for_other_tenant_site(
        self, client, test_tenant, second_tenant, db_session
    ):
        """Test that querying other tenant's site addresses fails."""
        # Create customer and site in second tenant
        other_customer = Customer(
            tenant_id=second_tenant.id,
            display_name="Other Tenant Customer",
            type="company",
        )
        db_session.add(other_customer)
        db_session.commit()
        db_session.refresh(other_customer)

        other_site = Site(
            tenant_id=second_tenant.id,
            customer_id=other_customer.id,
            name="Other Site",
        )
        db_session.add(other_site)
        db_session.commit()
        db_session.refresh(other_site)

        response = client.get(f"/api/v1/addresses/by-entity/site/{other_site.id}/test")
        assert response.status_code == 404


class TestAddressWithLatLong:
    """Test address creation with latitude/longitude (geocoding support)."""

    def test_create_address_with_coordinates(self, client, test_tenant):
        """Test creating an address with lat/long coordinates."""
        response = client.post(
            "/api/v1/addresses/test",
            json={
                "line1": "1600 Pennsylvania Ave NW",
                "city": "Washington",
                "state": "DC",
                "postal_code": "20500",
                "country": "US",
                "latitude": 38.8977,
                "longitude": -77.0365,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["latitude"] == 38.8977
        assert data["longitude"] == -77.0365
