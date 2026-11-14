import datetime
import uuid

from fastapi.testclient import TestClient
from psycopg2.extras import DateTimeTZRange
from sqlmodel import Session, select

from app.models.auth import TenantUser
from app.models.catalog import TenantMarkupVersion
from app.models.core import Tenant, User
from app.models.crm import Customer, CustomerType, EntityAddress, Site
from app.models.fulfillment import Job, JobExpenseCategory, JobStatus


def create_mock_user_and_tenant(db_session: Session):
    # Create Tenant
    tenant = Tenant(name=f"Test Tenant {uuid.uuid4()}")
    db_session.add(tenant)
    db_session.flush()

    # Create User matching the mocked JWT email "test@example.com"
    user = User(
        email="test@example.com", first_name="Test", last_name="User", is_active=True
    )
    db_session.add(user)
    db_session.flush()

    # Create TenantUser
    tenant_user = TenantUser(
        tenant_id=tenant.id,
        user_id=user.id,
        role_code="owner",  # Assumes 'owner' exists or doesn't strictly fk check in sqlite tests, but we are using PG so we might need it
        status_id=uuid.uuid4(),  # Mocked
        is_active=True,
    )
    # We need to bypass FK checks or ensure they exist. Let's just create them if needed.
    # Actually, the auth test shows they might exist or we can just create a real signup!
    db_session.rollback()
    return None


def setup_test_user(client: TestClient, db_session: Session):
    # Use the seeded test user and tenant
    # Email from mock: test@pilot.local
    # User ID: 00000000-0000-0000-0000-000000000002
    # Tenant ID: 00000000-0000-0000-0000-000000000001

    headers = {"Authorization": "Bearer dummy_test_token_12345"}
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    return headers, user_id, tenant_id


def test_customer_creation(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    payload = {
        "type": "person",
        "display_name": "John Doe",
        "email": "johndoe@example.com",
    }

    response = client.post("/api/v1/customers/", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["display_name"] == "John Doe"
    assert data["tenant_id"] == str(tenant_id)


def test_job_creation(client: TestClient, db_session: Session, mock_cognito_jwt_verify):
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # Create Customer
    customer = Customer(
        tenant_id=tenant_id, type=CustomerType.person, display_name="Job Customer"
    )
    db_session.add(customer)
    db_session.flush()

    # Create Site
    site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Main Site")
    db_session.add(site)
    db_session.flush()

    # Create Job Status
    job_status = JobStatus(
        id=uuid.uuid4(), tenant_id=tenant_id, code="new", name="New", is_default=True
    )
    db_session.add(job_status)
    db_session.commit()

    payload = {"customer_id": str(customer.id), "site_id": str(site.id)}

    response = client.post("/api/v1/jobs/", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == str(customer.id)
    assert data["site_id"] == str(site.id)
    assert data["status_id"] == str(job_status.id)


def test_job_expense_costing_logic(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # 1. Setup Customer, Site, Job Status
    customer = Customer(
        tenant_id=tenant_id, type=CustomerType.person, display_name="Expense Customer"
    )
    db_session.add(customer)
    db_session.flush()

    site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Expense Site")
    db_session.add(site)
    db_session.flush()

    job_status = JobStatus(
        id=uuid.uuid4(), tenant_id=tenant_id, code="open", name="Open", is_default=True
    )
    db_session.add(job_status)
    db_session.flush()

    job = Job(
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
    )
    db_session.add(job)
    db_session.flush()

    # 2. Setup JobExpenseCategory
    cat_code = "materials"
    cat = JobExpenseCategory(code=cat_code, tenant_id=tenant_id, name="Materials")
    # if it already exists, just use it
    existing_cat = db_session.exec(
        select(JobExpenseCategory).where(JobExpenseCategory.code == cat_code)
    ).first()
    if not existing_cat:
        db_session.add(cat)
        db_session.flush()

    # 3. Setup TenantMarkupVersion
    # 20% markup — use a past CLOSED range to avoid GiST conflict with the
    # seeded open-ended row [2026-06-01, NULL) for (TEST_TENANT_ID, materials).
    valid_from = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    valid_to = datetime.datetime(2020, 12, 31, 23, 59, 59, tzinfo=datetime.UTC)
    markup = TenantMarkupVersion(
        tenant_id=tenant_id,
        job_expense_category_code=cat_code,
        markup_pct=20.0,
        valid_period=DateTimeTZRange(lower=valid_from, upper=valid_to, bounds="[)"),
    )
    db_session.add(markup)
    db_session.commit()

    # 4. Create JobExpense
    payload = {
        "job_expense_category_code": cat_code,
        "description": "Wiring",
        "incurred_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "cost_cents": 10000,  # $100.00
        "is_billable": True,
    }

    response = client.post(
        f"/api/v1/jobs/{job.id}/expenses", json=payload, headers=headers
    )
    assert response.status_code == 201
    data = response.json()

    # 20% markup on 10000 cents -> 12000 cents
    assert data["cost_cents"] == 10000
    assert data["markup_pct"] == 20.0
    assert data["billable_cents"] == 12000


def test_site_creation_with_nested_address(client: TestClient, db_session: Session):
    """
    Test creating a site with nested address (Gap #7).

    Verifies that:
    1. Site is created successfully
    2. Address is created automatically
    3. EntityAddress link is created
    4. Address type is 'service_location'
    5. Address is marked as primary
    """
    # Create a customer first
    response = client.post(
        "/api/v1/customers/test",
        json={
            "display_name": "Site Address Test Corp",
            "type": "company",
        },
    )
    assert response.status_code == 201
    customer_id = response.json()["id"]

    # Create site with nested address
    response = client.post(
        "/api/v1/sites/test",
        json={
            "customer_id": customer_id,
            "name": "Main Office with Address",
            "address": {
                "line1": "123 Business Parkway",
                "line2": "Suite 200",
                "city": "Houston",
                "state": "TX",
                "postal_code": "77001",
                "country": "US",
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Main Office with Address"
    assert "address" in data
    assert data["address"] is not None
    assert data["address"]["line1"] == "123 Business Parkway"
    assert data["address"]["city"] == "Houston"

    # Verify EntityAddress was created
    site_id = uuid.UUID(data["id"])
    entity_address = db_session.exec(
        select(EntityAddress)
        .where(EntityAddress.entity_type_code == "site")
        .where(EntityAddress.entity_id == site_id)
    ).first()
    assert entity_address is not None
    assert entity_address.address_type_code == "service_location"
    assert entity_address.is_primary is True


def test_site_creation_without_address_still_works(
    client: TestClient, db_session: Session
):
    """
    Test that site creation without address still works (backward compatibility).

    Verifies that the nested address is optional and existing
    code continues to work.
    """
    # Create a customer first
    response = client.post(
        "/api/v1/customers/test",
        json={
            "display_name": "No Address Test Corp",
            "type": "company",
        },
    )
    assert response.status_code == 201
    customer_id = response.json()["id"]

    # Create site without address
    response = client.post(
        "/api/v1/sites/test",
        json={
            "customer_id": customer_id,
            "name": "Office Without Address",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Office Without Address"
    assert data["address"] is None

    # Verify no EntityAddress was created
    site_id = uuid.UUID(data["id"])
    entity_address = db_session.exec(
        select(EntityAddress)
        .where(EntityAddress.entity_type_code == "site")
        .where(EntityAddress.entity_id == site_id)
    ).first()
    assert entity_address is None


def test_get_site_includes_primary_address(client: TestClient, db_session: Session):
    """
    Test that retrieving a site includes its primary address (Gap #7).

    Verifies that the GET /sites/{id} endpoint includes
    the linked address in the response.
    """
    # Create customer
    response = client.post(
        "/api/v1/customers/test",
        json={
            "display_name": "Address Retrieval Test Corp",
            "type": "company",
        },
    )
    assert response.status_code == 201
    customer_id = response.json()["id"]

    # Create site with address
    response = client.post(
        "/api/v1/sites/test",
        json={
            "customer_id": customer_id,
            "name": "Test Site",
            "address": {
                "line1": "456 Test Avenue",
                "city": "Dallas",
                "state": "TX",
                "postal_code": "75201",
            },
        },
    )
    assert response.status_code == 201
    site_id = response.json()["id"]

    # Get the site
    response = client.get(f"/api/v1/sites/{site_id}/test")
    assert response.status_code == 200
    data = response.json()
    assert "address" in data
    assert data["address"] is not None
    assert data["address"]["line1"] == "456 Test Avenue"
    assert data["address"]["city"] == "Dallas"


def test_site_address_is_primary_service_location(
    client: TestClient, db_session: Session
):
    """
    Test that auto-created site address has correct type and flags (Gap #7).

    Verifies that when a site is created with nested address:
    - address_type_code is 'service_location'
    - is_primary is True
    - is_active is True
    """
    # Create customer
    response = client.post(
        "/api/v1/customers/test",
        json={
            "display_name": "Address Type Test Corp",
            "type": "company",
        },
    )
    assert response.status_code == 201
    customer_id = response.json()["id"]

    # Create site with address
    response = client.post(
        "/api/v1/sites/test",
        json={
            "customer_id": customer_id,
            "name": "Type Test Site",
            "address": {
                "line1": "789 Service Road",
                "city": "Austin",
                "state": "TX",
                "postal_code": "78701",
            },
        },
    )
    assert response.status_code == 201
    site_id = uuid.UUID(response.json()["id"])

    # Verify EntityAddress properties
    entity_address = db_session.exec(
        select(EntityAddress)
        .where(EntityAddress.entity_type_code == "site")
        .where(EntityAddress.entity_id == site_id)
    ).first()
    assert entity_address is not None
    assert entity_address.address_type_code == "service_location"
    assert entity_address.is_primary is True
    assert entity_address.is_active is True
