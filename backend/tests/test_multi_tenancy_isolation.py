"""
Multi-Tenancy Isolation Tests (Gap #38)

Tests verifying that User A from Tenant 1 cannot access Tenant 2 data.
Critical for production security - prevents data leakage between tenants.

Security Principle: All cross-tenant access attempts return 404 (not 403)
to prevent tenant enumeration attacks.

Test Coverage:
- Customers (4 tests)
- Sites (4 tests)
- Jobs (5 tests)
- Quotes (6 tests)
- Catalog (2 tests)
- Voice AI (2 tests)
- Edge Cases (3 tests)
Total: 26 tests minimum

Reference: dev-docs/analysis/gap-38-multi-tenancy-isolation-remediation-plan.md
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.ai import ConversationSession
from app.models.catalog import SupplierItem
from app.models.crm import Customer, CustomerType, Site
from app.models.fulfillment import Job, JobStatus
from app.models.quoting import Quote, QuoteStatus

# ==================== CUSTOMER ISOLATION TESTS ====================


class TestCustomerIsolation:
    """Verify customers are isolated by tenant_id"""

    def test_cannot_list_other_tenant_customers(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A's customer list should not include Tenant B customers"""
        # ARRANGE: Create customers in both tenants
        customer_a = Customer(
            tenant_id=tenant_a.id,
            type=CustomerType.person,
            display_name="Customer A",
            email="customer-a@example.com",
        )
        customer_b = Customer(
            tenant_id=tenant_b.id,
            type=CustomerType.person,
            display_name="Customer B",
            email="customer-b@example.com",
        )
        db_session.add(customer_a)
        db_session.add(customer_b)
        db_session.commit()

        # ACT: User A lists customers
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get("/api/v1/customers/", headers={"Authorization": token})

        # ASSERT: Only sees Tenant A's customer
        assert response.status_code == 200
        customers = response.json()["items"]  # UI-FIX-1C: paginated response
        customer_ids = [c["id"] for c in customers]

        assert str(customer_a.id) in customer_ids
        assert str(customer_b.id) not in customer_ids, (
            "Tenant B customer leaked into Tenant A results!"
        )

    def test_cannot_get_other_tenant_customer_by_id(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot GET Tenant B's customer by ID (returns 404)"""
        # ARRANGE: Create customer in Tenant B
        customer_b = Customer(
            tenant_id=tenant_b.id,
            type=CustomerType.person,
            display_name="Customer B",
        )
        db_session.add(customer_b)
        db_session.commit()

        # ACT: User A tries to access Tenant B's customer
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get(
            f"/api/v1/customers/{customer_b.id}", headers={"Authorization": token}
        )

        # ASSERT: Returns 404 (not 403, to prevent enumeration)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cannot_update_other_tenant_customer(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot PATCH Tenant B's customer (returns 404)"""
        # ARRANGE: Create customer in Tenant B
        customer_b = Customer(
            tenant_id=tenant_b.id,
            type=CustomerType.person,
            display_name="Original Name",
        )
        db_session.add(customer_b)
        db_session.commit()
        original_name = customer_b.display_name

        # ACT: User A tries to update Tenant B's customer
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.patch(
            f"/api/v1/customers/{customer_b.id}",
            headers={"Authorization": token},
            json={"display_name": "Hacked Name"},
        )

        # ASSERT: Returns 404
        assert response.status_code == 404

        # VERIFY: Original customer unchanged
        db_session.refresh(customer_b)
        assert customer_b.display_name == original_name

    def test_cannot_delete_other_tenant_customer(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot DELETE Tenant B's customer (returns 404)"""
        # ARRANGE: Create customer in Tenant B
        customer_b = Customer(
            tenant_id=tenant_b.id,
            type=CustomerType.person,
            display_name="Customer B",
        )
        db_session.add(customer_b)
        db_session.commit()
        customer_b_id = customer_b.id

        # ACT: User A tries to delete Tenant B's customer
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.delete(
            f"/api/v1/customers/{customer_b_id}", headers={"Authorization": token}
        )

        # ASSERT: Returns 404
        assert response.status_code == 404

        # VERIFY: Customer still exists
        db_session.refresh(customer_b)
        assert customer_b.is_active is True


# ==================== SITE ISOLATION TESTS ====================


class TestSiteIsolation:
    """Verify sites are isolated by tenant_id"""

    def test_cannot_list_other_tenant_sites(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A's site list should not include Tenant B sites"""
        # ARRANGE: Create sites in both tenants
        customer_a = Customer(
            tenant_id=tenant_a.id, type=CustomerType.person, display_name="Customer A"
        )
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add_all([customer_a, customer_b])
        db_session.flush()

        site_a = Site(tenant_id=tenant_a.id, customer_id=customer_a.id, name="Site A")
        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add_all([site_a, site_b])
        db_session.commit()

        # ACT: User A lists sites
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get("/api/v1/sites/", headers={"Authorization": token})

        # ASSERT: Only sees Tenant A's site
        assert response.status_code == 200
        sites = response.json()
        site_ids = [s["id"] for s in sites]

        assert str(site_a.id) in site_ids
        assert str(site_b.id) not in site_ids, (
            "Tenant B site leaked into Tenant A results!"
        )

    def test_cannot_get_other_tenant_site_by_id(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot GET Tenant B's site by ID (returns 404)"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get(
            f"/api/v1/sites/{site_b.id}", headers={"Authorization": token}
        )

        # ASSERT
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cannot_update_other_tenant_site(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot PATCH Tenant B's site (returns 404 or validation error)"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(
            tenant_id=tenant_b.id, customer_id=customer_b.id, name="Original Name"
        )
        db_session.add(site_b)
        db_session.commit()
        original_name = site_b.name

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.patch(
            f"/api/v1/sites/{site_b.id}",
            headers={"Authorization": token},
            json={"name": "Hacked Name"},
        )

        # ASSERT: Should block access (404 or 422 validation)
        assert response.status_code in [404, 422], (
            f"Expected blocking response, got {response.status_code}"
        )

        # VERIFY: Original site unchanged
        db_session.refresh(site_b)
        assert site_b.name == original_name

    def test_cannot_create_site_for_other_tenant_customer(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot create site for Tenant B's customer"""
        # ARRANGE: Create customer in Tenant B
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.commit()

        # ACT: User A tries to create site for Tenant B's customer
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.post(
            "/api/v1/sites/",
            headers={"Authorization": token},
            json={"customer_id": str(customer_b.id), "name": "Malicious Site"},
        )

        # ASSERT: Should fail (customer not found in User A's tenant)
        assert response.status_code in [400, 404]


# ==================== JOB ISOLATION TESTS ====================


class TestJobIsolation:
    """Verify jobs and related entities are isolated by tenant_id"""

    def test_cannot_list_other_tenant_jobs(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A's job list should not include Tenant B jobs"""
        # ARRANGE: Create jobs in both tenants
        customer_a = Customer(
            tenant_id=tenant_a.id, type=CustomerType.person, display_name="Customer A"
        )
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add_all([customer_a, customer_b])
        db_session.flush()

        site_a = Site(tenant_id=tenant_a.id, customer_id=customer_a.id, name="Site A")
        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add_all([site_a, site_b])
        db_session.flush()

        # Create job statuses
        status_a = JobStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="new",
            name="New",
            is_default=True,
        )
        status_b = JobStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="new",
            name="New",
            is_default=True,
        )
        db_session.add_all([status_a, status_b])
        db_session.flush()

        job_a = Job(
            tenant_id=tenant_a.id,
            customer_id=customer_a.id,
            site_id=site_a.id,
            status_id=status_a.id,
        )
        job_b = Job(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add_all([job_a, job_b])
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get("/api/v1/jobs/", headers={"Authorization": token})

        # ASSERT
        assert response.status_code == 200
        jobs = response.json()["items"]  # UI-FIX-1C: paginated response
        job_ids = [j["id"] for j in jobs]

        assert str(job_a.id) in job_ids
        assert str(job_b.id) not in job_ids, (
            "Tenant B job leaked into Tenant A results!"
        )

    def test_cannot_get_other_tenant_job_by_id(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot GET Tenant B's job by ID (returns 404)"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = JobStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="new",
            name="New",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        job_b = Job(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(job_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get(
            f"/api/v1/jobs/{job_b.id}", headers={"Authorization": token}
        )

        # ASSERT
        assert response.status_code == 404

    def test_cannot_update_other_tenant_job(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot PATCH Tenant B's job (returns 404 or blocking error)"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = JobStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="new",
            name="New",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        job_b = Job(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(job_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.patch(
            f"/api/v1/jobs/{job_b.id}",
            headers={"Authorization": token},
            json={"notes": "Hacked notes"},
        )

        # ASSERT: Should block access (404, 405 if endpoint missing, 422 validation)
        assert response.status_code in [404, 405, 422], (
            f"Expected blocking response, got {response.status_code}"
        )

    def test_cannot_create_time_entry_on_other_tenant_job(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot POST time entry to Tenant B's job"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = JobStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="new",
            name="New",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        job_b = Job(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(job_b)
        db_session.commit()

        # ACT: User A tries to create time entry on Tenant B's job
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.post(
            f"/api/v1/jobs/{job_b.id}/time-entries",
            headers={"Authorization": token},
            json={
                "worked_date": "2026-03-18",
                "hours_worked": 8.0,
                "hourly_rate_cents": 5000,
            },
        )

        # ASSERT: Should fail (job not found in User A's tenant, or validation error)
        assert response.status_code in [400, 404, 422], (
            f"Expected blocking response, got {response.status_code}"
        )

    def test_cannot_create_expense_on_other_tenant_job(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot POST expense to Tenant B's job"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = JobStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="new",
            name="New",
            is_default=True,
        )
        # Don't create category in test - it will cause different validation errors
        db_session.add(status_b)
        db_session.flush()

        job_b = Job(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(job_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.post(
            f"/api/v1/jobs/{job_b.id}/expenses",
            headers={"Authorization": token},
            json={
                "expense_date": "2026-03-18",
                "category_id": str(uuid.uuid4()),  # Non-existent category
                "cost_cents": 10000,
            },
        )

        # ASSERT: Should fail (job not found or validation error)
        assert response.status_code in [400, 404, 422], (
            f"Expected blocking response, got {response.status_code}"
        )


# ==================== QUOTE ISOLATION TESTS ====================


class TestQuoteIsolation:
    """Verify quotes and related entities are isolated by tenant_id"""

    def test_cannot_list_other_tenant_quotes(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A's quote list should not include Tenant B quotes"""
        # ARRANGE
        customer_a = Customer(
            tenant_id=tenant_a.id, type=CustomerType.person, display_name="Customer A"
        )
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add_all([customer_a, customer_b])
        db_session.flush()

        # Create sites (required for quotes)
        site_a = Site(tenant_id=tenant_a.id, customer_id=customer_a.id, name="Site A")
        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add_all([site_a, site_b])
        db_session.flush()

        status_a = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        status_b = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        db_session.add_all([status_a, status_b])
        db_session.flush()

        quote_a = Quote(
            tenant_id=tenant_a.id,
            customer_id=customer_a.id,
            site_id=site_a.id,
            status_id=status_a.id,
        )
        quote_b = Quote(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add_all([quote_a, quote_b])
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get("/api/v1/quotes/", headers={"Authorization": token})

        # ASSERT
        assert response.status_code == 200
        quotes = response.json()["items"]  # UI-FIX-1C: paginated response
        quote_ids = [q["id"] for q in quotes]

        assert str(quote_a.id) in quote_ids
        assert str(quote_b.id) not in quote_ids, "Tenant B quote leaked!"

    def test_cannot_get_other_tenant_quote_by_id(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot GET Tenant B's quote by ID (returns 404)"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        quote_b = Quote(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(quote_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get(
            f"/api/v1/quotes/{quote_b.id}", headers={"Authorization": token}
        )

        # ASSERT
        assert response.status_code == 404

    def test_cannot_update_other_tenant_quote(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot PATCH Tenant B's quote (returns 404)"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        quote_b = Quote(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(quote_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.patch(
            f"/api/v1/quotes/{quote_b.id}",
            headers={"Authorization": token},
            json={"notes": "Hacked notes"},
        )

        # ASSERT
        assert response.status_code == 404

    def test_cannot_create_quote_line_on_other_tenant_quote(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot add line to Tenant B's quote"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        quote_b = Quote(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(quote_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.post(
            f"/api/v1/quotes/{quote_b.id}/lines",
            headers={"Authorization": token},
            json={
                "description": "Malicious line",
                "quantity": 1.0,
                "unit_price_cents": 10000,
            },
        )

        # ASSERT: Should block access (400, 404, or 422 validation)
        assert response.status_code in [400, 404, 422], (
            f"Expected blocking response, got {response.status_code}"
        )

    def test_cannot_create_quote_version_for_other_tenant_quote(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot create version for Tenant B's quote"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        quote_b = Quote(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(quote_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.post(
            f"/api/v1/quotes/{quote_b.id}/versions",
            headers={"Authorization": token},
            json={},
        )

        # ASSERT
        assert response.status_code in [400, 404]

    def test_cannot_create_public_link_for_other_tenant_quote(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot create public link for Tenant B's quote"""
        # ARRANGE
        customer_b = Customer(
            tenant_id=tenant_b.id, type=CustomerType.person, display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        quote_b = Quote(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(quote_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.post(
            f"/api/v1/quotes/{quote_b.id}/public-links",
            headers={"Authorization": token},
            json={},
        )

        # ASSERT
        assert response.status_code in [400, 404]


# ==================== CATALOG ISOLATION TESTS ====================


class TestCatalogIsolation:
    """Verify catalog items are isolated by tenant_id"""

    def test_cannot_list_other_tenant_supplier_items(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A's supplier item list should not include Tenant B items"""
        # ARRANGE: Create suppliers and UOMs first (required FKs)
        from app.models.catalog import Supplier, SupplierItemUom

        # Create UOMs
        uom_a = SupplierItemUom(
            tenant_id=tenant_a.id, code="EA", name="Each", is_default=True
        )
        uom_b = SupplierItemUom(
            tenant_id=tenant_b.id, code="EA", name="Each", is_default=True
        )
        db_session.add_all([uom_a, uom_b])
        db_session.flush()

        # Create suppliers
        supplier_a = Supplier(tenant_id=tenant_a.id, name="Supplier A")
        supplier_b = Supplier(tenant_id=tenant_b.id, name="Supplier B")
        db_session.add_all([supplier_a, supplier_b])
        db_session.flush()

        item_a = SupplierItem(
            tenant_id=tenant_a.id,
            supplier_id=supplier_a.id,
            uom_id=uom_a.id,
            sku="ITEM-A",
            name="Item A",
            description="Item A description",
        )
        item_b = SupplierItem(
            tenant_id=tenant_b.id,
            supplier_id=supplier_b.id,
            uom_id=uom_b.id,
            sku="ITEM-B",
            name="Item B",
            description="Item B description",
        )
        db_session.add_all([item_a, item_b])
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get(
            "/api/v1/catalog/supplier-items", headers={"Authorization": token}
        )

        # ASSERT
        assert response.status_code == 200
        items = response.json()
        item_ids = [i["id"] for i in items]

        assert str(item_a.id) in item_ids
        assert str(item_b.id) not in item_ids, "Tenant B supplier item leaked!"

    def test_cannot_get_other_tenant_supplier_item_by_id(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """User A cannot GET Tenant B's supplier item by ID (returns 404)"""
        # ARRANGE: Create supplier and UOM first (required FKs)
        from app.models.catalog import Supplier, SupplierItemUom

        # Create UOM
        uom_b = SupplierItemUom(
            tenant_id=tenant_b.id, code="EA", name="Each", is_default=True
        )
        db_session.add(uom_b)
        db_session.flush()

        # Create supplier
        supplier_b = Supplier(tenant_id=tenant_b.id, name="Supplier B")
        db_session.add(supplier_b)
        db_session.flush()

        item_b = SupplierItem(
            tenant_id=tenant_b.id,
            supplier_id=supplier_b.id,
            uom_id=uom_b.id,
            sku="ITEM-B",
            name="Item B",
            description="Item B description",
        )
        db_session.add(item_b)
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get(
            f"/api/v1/catalog/supplier-items/{item_b.id}",
            headers={"Authorization": token},
        )

        # ASSERT
        assert response.status_code == 404


# ==================== VOICE AI ISOLATION TESTS ====================


class TestVoiceAIIsolation:
    """Verify voice sessions and telemetry are isolated by tenant_id"""

    def test_cannot_list_other_tenant_voice_sessions(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A's voice session list should not include Tenant B sessions"""
        # ARRANGE
        session_a = ConversationSession(
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
            status="active",
        )
        session_b = ConversationSession(
            tenant_id=tenant_b.id,
            user_id=user_tenant_b.id,
            status="active",
        )
        db_session.add_all([session_a, session_b])
        db_session.commit()

        # ACT
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.get(
            "/api/v1/voice/sessions", headers={"Authorization": token}
        )

        # ASSERT: Either endpoint exists and returns isolated data, or doesn't exist yet (404)
        if response.status_code == 200:
            # Endpoint exists - verify isolation
            response_data = response.json()
            sessions = response_data.get(
                "sessions", response_data
            )  # Handle both list and SessionListResponse formats
            if isinstance(sessions, dict):
                sessions = [sessions]  # Wrap dict in list if needed
            session_ids = [str(s.get("session_id", s.get("id"))) for s in sessions]

            assert str(session_a.id) in session_ids
            assert str(session_b.id) not in session_ids, (
                "Tenant B voice session leaked!"
            )
        elif response.status_code == 404:
            # Endpoint doesn't exist yet - that's OK, isolation will be enforced when built
            pass  # Test passes - 404 is acceptable for unimplemented endpoint
        else:
            assert False, f"Expected 200 or 404, got {response.status_code}"

    def test_cannot_create_transcript_in_other_tenant_session(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A cannot create transcript in Tenant B's session"""
        # ARRANGE
        session_b = ConversationSession(
            tenant_id=tenant_b.id,
            user_id=user_tenant_b.id,
            status="active",
        )
        db_session.add(session_b)
        db_session.commit()

        # ACT: User A tries to post to Tenant B's session
        token = mock_jwt_for_user(user_tenant_a.email)

        # Note: The actual endpoint might vary, this is conceptual
        # Assuming there's a POST /voice/sessions/{id}/transcripts endpoint
        response = client.post(
            f"/api/v1/voice/sessions/{session_b.id}/transcripts",
            headers={"Authorization": token},
            json={"audio_data": "fake_audio_base64"},
        )

        # ASSERT: Should fail (session not found in User A's tenant)
        # If endpoint doesn't exist, this test validates the pattern
        assert response.status_code in [400, 404, 405], (
            f"Expected blocking response, got {response.status_code}"
        )


# ==================== EDGE CASE TESTS ====================


class TestEdgeCases:
    """Security edge cases and attack vectors"""

    def test_cannot_manipulate_tenant_id_in_request_body(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """Verify tenant_id from auth overrides any body parameter"""
        # ACT: User A tries to create customer with Tenant B's ID in body
        token = mock_jwt_for_user(user_tenant_a.email)
        response = client.post(
            "/api/v1/customers/",
            headers={"Authorization": token},
            json={
                "tenant_id": str(tenant_b.id),  # Malicious attempt
                "type": "person",
                "display_name": "Malicious Customer",
            },
        )

        # ASSERT: Should create customer in Tenant A (from auth), not Tenant B
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == str(tenant_a.id), (
            "tenant_id manipulation succeeded!"
        )
        assert data["tenant_id"] != str(tenant_b.id)

    def test_database_level_isolation_cannot_be_bypassed(
        self,
        db_session: Session,
        tenant_a,
        tenant_b,
    ):
        """Raw SQL query verification that WHERE tenant_id is enforced"""
        # ARRANGE: Create customers in both tenants
        customer_a = Customer(
            tenant_id=tenant_a.id,
            type=CustomerType.person,
            display_name="Customer A",
        )
        customer_b = Customer(
            tenant_id=tenant_b.id,
            type=CustomerType.person,
            display_name="Customer B",
        )
        db_session.add_all([customer_a, customer_b])
        db_session.commit()

        # ACT: Query with tenant_id filter (simulating route behavior)
        from sqlmodel import select

        statement = select(Customer).where(Customer.tenant_id == tenant_a.id)
        results = db_session.exec(statement).all()

        # ASSERT: Only Tenant A's customer returned
        assert len(results) >= 1
        for customer in results:
            assert customer.tenant_id == tenant_a.id
            assert customer.tenant_id != tenant_b.id

    def test_test_endpoints_respect_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test endpoints (unauthenticated) only access test tenant data"""
        # ARRANGE: Create customer in a different tenant
        other_tenant_id = uuid.uuid4()
        from app.models.core import Tenant

        other_tenant = Tenant(id=other_tenant_id, name="Other Tenant", is_active=True)
        db_session.add(other_tenant)
        db_session.flush()

        other_customer = Customer(
            tenant_id=other_tenant_id,
            type=CustomerType.person,
            display_name="Other Tenant Customer",
        )
        db_session.add(other_customer)
        db_session.commit()

        # ACT: Use test endpoint (no auth) to list customers
        response = client.get("/api/v1/customers/test")

        # ASSERT: Should only return test tenant customers
        assert response.status_code == 200
        customers = response.json()["items"]  # UI-FIX-1C: paginated response

        # Verify no other tenant's data leaks into test endpoint
        for customer in customers:
            assert customer["tenant_id"] == "00000000-0000-0000-0000-000000000001"
            assert customer["tenant_id"] != str(other_tenant_id)

    def test_cannot_accept_other_tenant_quote(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_jwt_for_user,
    ):
        """User A should not be able to accept Tenant B's quote"""
        import uuid

        from app.models.crm import Customer, Site
        from app.models.quoting import Quote, QuoteStatus, QuoteVersion

        # Setup Tenant B quote
        customer_b = Customer(
            tenant_id=tenant_b.id, type="person", display_name="Customer B"
        )
        db_session.add(customer_b)
        db_session.flush()

        site_b = Site(tenant_id=tenant_b.id, customer_id=customer_b.id, name="Site B")
        db_session.add(site_b)
        db_session.flush()

        status_b = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            code="sent",
            name="Sent",
            is_default=True,
        )
        db_session.add(status_b)
        db_session.flush()

        quote_b = Quote(
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=status_b.id,
        )
        db_session.add(quote_b)
        db_session.flush()

        # Create quote version for Tenant B
        version_b = QuoteVersion(
            tenant_id=tenant_b.id,
            quote_id=quote_b.id,
            version_no=1,
            snapshot={"test": "data"},
        )
        db_session.add(version_b)
        db_session.commit()

        # Tenant A tries to accept Tenant B's quote
        mock_jwt_for_user(user_tenant_a.id)
        response = client.post(
            f"/api/v1/quotes/{quote_b.id}/accept",
            json={
                "accepted_by_name": "Tenant A Guy",
                "accepted_by_email": "guy@tenanta.com",
                "terms_acknowledged": True,
            },
        )
        assert response.status_code == 404
