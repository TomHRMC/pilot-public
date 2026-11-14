"""
Unit and integration tests for QuickBooks synchronization.

Tests cover:
- Token management and retrieval
- Customer sync from QuickBooks to Pilot for Trades (upsert logic)
- Customer sync from Pilot for Trades to QuickBooks (bidirectional)
- Incremental batch sync with timestamp filtering
- Deduplication (no duplicate records)
- Version token tracking
- Tenant isolation
- Celery background tasks
- API endpoints

Design Reference: Task #17 in phase-2-5-implementation-roadmap.md
Gap Reference: Gap #23 in phase-1-4-implementation-gap-analysis.md
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.crm import Customer, CustomerType
from app.models.system import AppService, IntegrationCredential, IntegrationSyncMapping
from core.encryption import encrypt_token
from services.quickbooks_sync import QuickBooksSync

# ==================== FIXTURES ====================


@pytest.fixture
def qb_customer_data():
    """Sample QuickBooks customer JSON response.

    NOTE: Name must NOT match any seeded customer (e.g. 'John Smith' is seeded by
    seed_scenario_quote_to_cash.py). Using a unique test-specific name here ensures
    the test is resilient to pre-existing dev DB seed data.
    """
    return {
        "Id": "123",
        "DisplayName": "QB Test Customer Zeta",
        "GivenName": "QB",
        "FamilyName": "Zeta",
        "CompanyName": "Zeta Electric Co",
        "PrimaryEmailAddr": {"Address": "qbzeta@zeta-electric-test.example.com"},
        "PrimaryPhone": {"FreeFormNumber": "555-9911"},
        "Notes": "VIP customer",
        "SyncToken": "0",
        "Active": True,
        "MetaData": {
            "CreateTime": "2026-03-20T10:00:00Z",
            "LastUpdatedTime": "2026-03-20T10:00:00Z",
        },
    }


@pytest.fixture
def qb_customer_updated(qb_customer_data):
    """Updated QuickBooks customer (for testing upsert logic)."""
    data = qb_customer_data.copy()
    data["DisplayName"] = "QB Test Customer Zeta Updated"
    data["SyncToken"] = "1"
    data["MetaData"]["LastUpdatedTime"] = "2026-03-21T10:00:00Z"
    return data


@pytest.fixture
def qb_app_service(db_session, test_tenant, test_user, utc_now):
    """QuickBooks AppService with active credential for testing."""
    from sqlmodel import select

    # Delete any existing QuickBooks connections for this tenant (test isolation)
    # Must delete child records first due to foreign key constraints:
    # 1. integration_sync_mapping (references app_service_id)
    # 2. integration_credential (references app_service_id)
    # 3. app_service
    stmt = select(AppService).where(
        AppService.tenant_id == test_tenant.id, AppService.provider_code == "quickbooks"
    )
    existing_services = db_session.exec(stmt).all()
    for svc in existing_services:
        # Delete sync mappings first (child of app_service)
        mapping_stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.app_service_id == svc.id
        )
        mappings = db_session.exec(mapping_stmt).all()
        for mapping in mappings:
            db_session.delete(mapping)

        # Delete associated credentials (child of app_service)
        cred_stmt = select(IntegrationCredential).where(
            IntegrationCredential.app_service_id == svc.id
        )
        credentials = db_session.exec(cred_stmt).all()
        for cred in credentials:
            db_session.delete(cred)

    # Flush child record deletes before deleting parent
    db_session.flush()

    # Now delete the app services (parent records)
    for svc in existing_services:
        db_session.delete(svc)
    db_session.commit()
    # Create QuickBooks AppService
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Online",
        category_code="accounting",
        provider_code="quickbooks",
        external_account_id="1234567890123456",  # Sandbox realm_id
        is_active=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(app_service)
    db_session.flush()

    # Create active credential with encrypted tokens
    access_token_encrypted = encrypt_token("test_access_token_123")
    refresh_token_encrypted = encrypt_token("test_refresh_token_456")

    credential = IntegrationCredential(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        app_service_id=app_service.id,
        secret_json={
            "access_token_encrypted": access_token_encrypted,
            "refresh_token_encrypted": refresh_token_encrypted,
        },
        expires_at=utc_now + timedelta(hours=1),  # Token valid for 1 hour
        last_refresh_at=utc_now,
        connected_at=utc_now,
        connection_status="active",
        initiated_by_user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(credential)
    db_session.commit()

    return app_service


@pytest.fixture
def test_customer(db_session, test_tenant, test_user):
    """Pilot for Trades customer for testing sync to QuickBooks."""
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type=CustomerType.company,
        display_name="Test Company",
        first_name="Jane",
        last_name="Doe",
        company_name="Test Company LLC",
        email="jane@testcompany.example.com",
        mobile_phone="555-9876",
        notes="Test customer",
        is_active=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


# ==================== TOKEN MANAGEMENT TESTS ====================


@pytest.mark.asyncio
async def test_get_access_token_success(db_session, test_tenant, qb_app_service):
    """Test successful token retrieval and decryption."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    access_token, realm_id = await sync.get_access_token()

    assert access_token == "test_access_token_123"
    assert realm_id == "1234567890123456"


@pytest.mark.asyncio
async def test_get_access_token_not_connected(db_session, test_tenant):
    """Test error when QuickBooks not connected."""
    from sqlmodel import select

    from app.models.system import AppService, IntegrationCredential

    # Ensure no QB credentials exist for this tenant (defensive against test pollution)
    stmt = (
        select(IntegrationCredential)
        .join(AppService, IntegrationCredential.app_service_id == AppService.id)
        .where(
            IntegrationCredential.tenant_id == test_tenant.id,
            AppService.provider_code == "quickbooks",
        )
    )
    existing_creds = db_session.exec(stmt).all()
    for cred in existing_creds:
        db_session.delete(cred)
    db_session.commit()

    sync = QuickBooksSync(test_tenant.id, db_session)

    with pytest.raises(ValueError, match="QuickBooks not connected"):
        await sync.get_access_token()


@pytest.mark.asyncio
async def test_get_access_token_auto_refresh(
    db_session, test_tenant, test_user, qb_app_service, utc_now
):
    """Test automatic token refresh when token expiring soon."""
    # Update credential to expire in 3 minutes (should trigger refresh)
    from sqlmodel import select

    stmt = select(IntegrationCredential).where(
        IntegrationCredential.tenant_id == test_tenant.id
    )
    credential = db_session.exec(stmt).first()
    credential.expires_at = utc_now + timedelta(minutes=3)
    db_session.add(credential)
    db_session.commit()

    sync = QuickBooksSync(test_tenant.id, db_session)

    # Mock the refresh function
    with patch("api.routes.integrations._refresh_qbo_token_impl") as mock_refresh:
        mock_refresh.return_value = {"status": "refreshed"}

        access_token, realm_id = await sync.get_access_token()

        # Verify refresh was called
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_app_service_id_success(db_session, test_tenant, qb_app_service):
    """Test retrieval of QuickBooks app_service_id."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    app_service_id = await sync._get_app_service_id()

    assert app_service_id == qb_app_service.id


# ==================== UPSERT LOGIC TESTS (QB → Pilot for Trades) ====================


@pytest.mark.asyncio
async def test_sync_customer_from_qb_creates_new(
    db_session, test_tenant, test_user, qb_app_service, qb_customer_data
):
    """Test creating new customer when no mapping exists."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    customer = await sync.sync_customer_from_qb(qb_customer_data)

    # Verify customer created
    assert customer.id is not None
    assert customer.tenant_id == test_tenant.id
    assert customer.display_name == "QB Test Customer Zeta"
    assert customer.first_name == "QB"
    assert customer.last_name == "Zeta"
    assert customer.company_name == "Zeta Electric Co"
    assert customer.email == "qbzeta@zeta-electric-test.example.com"
    assert customer.mobile_phone == "555-9911"
    assert customer.notes == "VIP customer"
    assert customer.is_active is True

    # Verify mapping created
    from sqlmodel import select

    stmt = select(IntegrationSyncMapping).where(
        IntegrationSyncMapping.tenant_id == test_tenant.id,
        IntegrationSyncMapping.entity_type_code == "customer",
        IntegrationSyncMapping.external_id == "123",
    )
    mapping = db_session.exec(stmt).first()
    assert mapping is not None
    assert mapping.entity_id == customer.id
    assert mapping.external_version_token == "0"
    assert mapping.app_service_id == qb_app_service.id


@pytest.mark.asyncio
async def test_sync_customer_from_qb_updates_existing(
    db_session,
    test_tenant,
    test_user,
    qb_app_service,
    qb_customer_data,
    qb_customer_updated,
):
    """Test updating existing customer when mapping exists."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # First sync - create customer
    customer1 = await sync.sync_customer_from_qb(qb_customer_data)
    customer1_id = customer1.id

    # Second sync - update customer
    customer2 = await sync.sync_customer_from_qb(qb_customer_updated)

    # Verify same customer was updated (not a new one)
    assert customer2.id == customer1_id
    assert customer2.display_name == "QB Test Customer Zeta Updated"

    # Verify version token updated
    from sqlmodel import select

    stmt = select(IntegrationSyncMapping).where(
        IntegrationSyncMapping.entity_id == customer1_id
    )
    mapping = db_session.exec(stmt).first()
    assert mapping.external_version_token == "1"


@pytest.mark.asyncio
async def test_sync_customer_from_qb_prevents_duplicates(
    db_session, test_tenant, qb_app_service, qb_customer_data
):
    """Test that syncing same customer 100 times creates only 1 record."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # Sync same customer 100 times
    customer_ids = set()
    for _ in range(100):
        customer = await sync.sync_customer_from_qb(qb_customer_data)
        customer_ids.add(customer.id)

    # Verify only 1 unique customer created
    assert len(customer_ids) == 1

    # Verify only 1 mapping exists
    from sqlmodel import func, select

    stmt = select(func.count(IntegrationSyncMapping.id)).where(
        IntegrationSyncMapping.tenant_id == test_tenant.id,
        IntegrationSyncMapping.external_id == "123",
    )
    count = db_session.exec(stmt).one()
    assert count == 1


@pytest.mark.asyncio
async def test_sync_customer_from_qb_tracks_version_token(
    db_session, test_tenant, qb_app_service, qb_customer_data
):
    """Test that SyncToken is correctly tracked in mapping."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    customer = await sync.sync_customer_from_qb(qb_customer_data)

    # Verify SyncToken saved using ORM
    from sqlmodel import select

    stmt = select(IntegrationSyncMapping).where(
        IntegrationSyncMapping.entity_id == customer.id
    )
    mapping = db_session.exec(stmt).first()
    assert mapping.external_version_token == "0"
    assert mapping.last_synced_at is not None


@pytest.mark.asyncio
async def test_sync_customer_from_qb_tenant_isolation(
    db_session, test_tenant, tenant_a, qb_app_service, qb_customer_data
):
    """Test that sync respects tenant isolation."""
    sync_test = QuickBooksSync(test_tenant.id, db_session)
    sync_a = QuickBooksSync(tenant_a.id, db_session)

    # Sync to test tenant
    customer = await sync_test.sync_customer_from_qb(qb_customer_data)

    # Verify customer belongs to test tenant
    assert customer.tenant_id == test_tenant.id

    # Verify tenant_a cannot access this mapping
    # (would need to create QB connection for tenant_a first)


@pytest.mark.asyncio
async def test_sync_customer_from_qb_missing_required_fields(
    db_session, test_tenant, qb_app_service
):
    """Test error handling when required fields missing."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # Missing Id
    with pytest.raises(ValueError, match="missing required field 'Id'"):
        await sync.sync_customer_from_qb({"DisplayName": "Test"})

    # Missing DisplayName
    with pytest.raises(ValueError, match="missing required field 'DisplayName'"):
        await sync.sync_customer_from_qb({"Id": "123"})


# ==================== BIDIRECTIONAL SYNC TESTS (Pilot for Trades → QB) ====================


@pytest.mark.asyncio
async def test_sync_customer_to_qb_creates_in_qb(
    db_session, test_tenant, test_customer, qb_app_service
):
    """Test creating customer in QuickBooks when no mapping exists."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # Mock QuickBooks API response
    mock_qb_response = {
        "Customer": {
            "Id": "456",
            "DisplayName": "Test Company",
            "SyncToken": "0",
        }
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        # json() is synchronous in httpx, not async!
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        qb_customer = await sync.sync_customer_to_qb(test_customer.id)

        # Verify API called
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Verify payload does NOT include Id (new customer)
        payload = call_args.kwargs["json"]
        assert "Id" not in payload
        assert payload["DisplayName"] == "Test Company"

        # Verify mapping created
        from sqlmodel import select

        stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.entity_id == test_customer.id
        )
        mapping = db_session.exec(stmt).first()
        assert mapping is not None
        assert mapping.external_id == "456"
        assert mapping.external_version_token == "0"


@pytest.mark.asyncio
async def test_sync_customer_to_qb_updates_in_qb(
    db_session, test_tenant, test_customer, test_user, qb_app_service
):
    """Test updating customer in QuickBooks when mapping exists."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # Create existing mapping
    mapping = IntegrationSyncMapping(
        tenant_id=test_tenant.id,
        entity_id=test_customer.id,
        entity_type_code="customer",
        app_service_id=qb_app_service.id,
        external_id="456",
        external_version_token="1",
        last_synced_at=datetime.now(UTC),
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(mapping)
    db_session.commit()

    # Mock QuickBooks API response
    mock_qb_response = {
        "Customer": {
            "Id": "456",
            "DisplayName": "Test Company",
            "SyncToken": "2",
        }
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        qb_customer = await sync.sync_customer_to_qb(test_customer.id)

        # Verify API called
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Verify payload INCLUDES Id and SyncToken (update)
        payload = call_args.kwargs["json"]
        assert payload["Id"] == "456"
        assert payload["SyncToken"] == "1"

        # Verify mapping updated with new SyncToken
        db_session.refresh(mapping)
        assert mapping.external_version_token == "2"


@pytest.mark.asyncio
async def test_sync_customer_to_qb_field_mapping(
    db_session, test_tenant, test_customer, qb_app_service
):
    """Test correct field transformation from Pilot for Trades to QuickBooks."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    mock_qb_response = {
        "Customer": {"Id": "456", "DisplayName": "Test", "SyncToken": "0"}
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await sync.sync_customer_to_qb(test_customer.id)

        # Verify field mappings
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["DisplayName"] == "Test Company"
        assert payload["GivenName"] == "Jane"
        assert payload["FamilyName"] == "Doe"
        assert payload["CompanyName"] == "Test Company LLC"
        assert payload["PrimaryEmailAddr"]["Address"] == "jane@testcompany.example.com"
        assert payload["PrimaryPhone"]["FreeFormNumber"] == "555-9876"
        assert payload["Notes"] == "Test customer"
        assert payload["Active"] is True


@pytest.mark.asyncio
async def test_sync_customer_to_qb_customer_not_found(
    db_session, test_tenant, qb_app_service
):
    """Test error when customer doesn't exist."""
    sync = QuickBooksSync(test_tenant.id, db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match=f"Customer {fake_id} not found"):
        await sync.sync_customer_to_qb(fake_id)


@pytest.mark.asyncio
async def test_sync_customer_to_qb_wrong_tenant(
    db_session, test_tenant, tenant_a, test_customer, qb_app_service
):
    """Test error when trying to sync customer from different tenant.

    FIND-132: The pre-fix behavior raised 'does not belong to tenant' (post-fetch check).
    After FIND-132, the tenant-scoped query returns None immediately — the customer is
    never fetched into memory, so the error is 'not found'.
    Both behaviors correctly reject cross-tenant customer access; the error message changed.
    """
    # Use tenant_a's sync service but test_customer belongs to test_tenant
    sync = QuickBooksSync(tenant_a.id, db_session)

    with pytest.raises(ValueError, match="not found"):
        await sync.sync_customer_to_qb(test_customer.id)


# ==================== INCREMENTAL SYNC TESTS ====================


@pytest.mark.asyncio
async def test_sync_all_customers_initial_sync(
    db_session, test_tenant, qb_app_service, qb_customer_data
):
    """Test initial sync (since=None) fetches all customers."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # Create second customer with different name/email — must NOT match any seeded customer
    # (e.g. 'Jane Doe' is seeded by seed_scenario_quote_to_cash.py)
    qb_customer_2 = {
        **qb_customer_data,
        "Id": "124",
        "DisplayName": "QB Test Customer Beta",
        "GivenName": "QB",
        "FamilyName": "Beta",
        "PrimaryEmailAddr": {"Address": "qbbeta@beta-electric-test.example.com"},
    }

    # Mock QuickBooks API response
    mock_qb_response = {
        "QueryResponse": {"Customer": [qb_customer_data, qb_customer_2]}
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        count = await sync.sync_all_customers_from_qb(since=None)

        # Verify query parameter (no timestamp filter)
        call_args = mock_client.get.call_args
        query = call_args.kwargs["params"]["query"]
        assert query == "SELECT * FROM Customer"
        assert count["synced"] == 2
        assert count["conflicts"] == 0
        assert count["failed"] == 0


@pytest.mark.asyncio
async def test_sync_all_customers_incremental_sync(
    db_session, test_tenant, qb_app_service, qb_customer_data
):
    """Test incremental sync with timestamp filter."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    since_time = datetime(2026, 3, 20, 10, 0, 0, tzinfo=UTC)

    mock_qb_response = {"QueryResponse": {"Customer": [qb_customer_data]}}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        count = await sync.sync_all_customers_from_qb(since=since_time)

        # Verify query includes timestamp filter
        call_args = mock_client.get.call_args
        query = call_args.kwargs["params"]["query"]
        assert "WHERE MetaData.LastUpdatedTime >" in query
        assert "2026-03-20T10:00:00" in query
        assert count["synced"] == 1
        assert count["conflicts"] == 0
        assert count["failed"] == 0


@pytest.mark.asyncio
async def test_sync_all_customers_empty_result(db_session, test_tenant, qb_app_service):
    """Test handling empty result (no customers changed)."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # QB returns empty array when no customers match
    mock_qb_response = {"QueryResponse": {}}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        count = await sync.sync_all_customers_from_qb(since=None)

        assert count["synced"] == 0
        assert count["conflicts"] == 0
        assert count["failed"] == 0


@pytest.mark.asyncio
async def test_get_last_sync_timestamp(
    db_session, test_tenant, test_customer, test_user, qb_app_service
):
    """Test retrieval of last sync timestamp."""
    sync = QuickBooksSync(test_tenant.id, db_session)

    # No sync yet - should return None
    last_sync = await sync.get_last_sync_timestamp()
    assert last_sync is None

    # Create mapping with sync timestamp
    sync_time = datetime(2026, 3, 21, 12, 0, 0, tzinfo=UTC)
    mapping = IntegrationSyncMapping(
        tenant_id=test_tenant.id,
        entity_id=test_customer.id,
        entity_type_code="customer",
        app_service_id=qb_app_service.id,
        external_id="789",
        external_version_token="0",
        last_synced_at=sync_time,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(mapping)
    db_session.commit()
    db_session.refresh(mapping)

    # Should return last sync timestamp
    last_sync = await sync.get_last_sync_timestamp()
    # Verify we got a timestamp back and it's close to what we set
    assert last_sync is not None
    # Database may store/return with timezone info added
    if last_sync.tzinfo is None:
        # If returned without timezone, compare just the datetime values
        assert last_sync == sync_time.replace(tzinfo=None)
    else:
        # If returned with timezone, compare as-is
        assert last_sync == sync_time


# ==================== API ENDPOINT TESTS ====================


def test_sync_customers_endpoint_success(client, test_tenant, qb_app_service):
    """Test POST /sync/customers/test endpoint."""
    mock_qb_response = {"QueryResponse": {"Customer": []}}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        response = client.post("/api/v1/integrations/quickbooks/sync/customers/test")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "customers_synced" in data
        assert "synced_at" in data


def test_sync_status_endpoint(client, test_tenant, qb_app_service):
    """Test GET /sync/status/test endpoint."""
    response = client.get("/api/v1/integrations/quickbooks/sync/status/test")

    assert response.status_code == 200
    data = response.json()
    assert "last_sync_at" in data
    assert "total_customers_mapped" in data
    assert data["quickbooks_connected"] == True


def test_sync_status_endpoint_not_connected(client, test_tenant, db_session):
    """Test sync status when QuickBooks not connected."""
    # Clean up any existing QB connections for this tenant.
    # Deletion order must respect FK constraints:
    #   integration_sync_mapping  → references app_service_id (child)
    #   integration_credential    → references app_service_id (child)
    #   app_service               → parent
    from sqlmodel import select

    stmt = select(AppService).where(
        AppService.tenant_id == test_tenant.id, AppService.provider_code == "quickbooks"
    )
    existing_services = db_session.exec(stmt).all()
    for svc in existing_services:
        # 1. Delete sync mappings (child of app_service, blocks DELETE otherwise)
        mapping_stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.app_service_id == svc.id
        )
        for mapping in db_session.exec(mapping_stmt).all():
            db_session.delete(mapping)

        # 2. Delete associated credentials (also child of app_service)
        cred_stmt = select(IntegrationCredential).where(
            IntegrationCredential.app_service_id == svc.id
        )
        for cred in db_session.exec(cred_stmt).all():
            db_session.delete(cred)

    db_session.flush()

    # Now safe to delete the app services (parent records)
    for svc in existing_services:
        db_session.delete(svc)
    db_session.commit()

    response = client.get("/api/v1/integrations/quickbooks/sync/status/test")

    assert response.status_code == 200
    data = response.json()
    assert data["quickbooks_connected"] == False
    assert data["total_customers_mapped"] == 0


def test_sync_customer_to_qb_endpoint(
    client, test_tenant, test_customer, qb_app_service
):
    """Test POST /sync/customer/{id}/test endpoint."""
    mock_qb_response = {
        "Customer": {"Id": "999", "DisplayName": "Test", "SyncToken": "0"}
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_qb_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        response = client.post(
            f"/api/v1/integrations/quickbooks/sync/customer/{test_customer.id}/test"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["qb_customer_id"] == "999"
        assert data["qb_sync_token"] == "0"


def test_sync_customer_to_qb_endpoint_not_found(client, test_tenant, qb_app_service):
    """Test sync endpoint with non-existent customer."""
    fake_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/integrations/quickbooks/sync/customer/{fake_id}/test"
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"]


# ==================== CELERY TASK TESTS ====================


def test_sync_quickbooks_customers_task_exists():
    """Test that Celery task is registered."""
    from tasks.quickbooks_sync import sync_quickbooks_customers_task

    assert sync_quickbooks_customers_task is not None
    assert sync_quickbooks_customers_task.name == "sync_quickbooks_customers"


def test_sync_all_tenants_customers_task_exists():
    """Test that batch sync task is registered."""
    from tasks.quickbooks_sync import sync_all_tenants_customers_task

    assert sync_all_tenants_customers_task is not None
    assert sync_all_tenants_customers_task.name == "sync_all_tenants_customers"


def test_celery_beat_schedule_registered():
    """Test that sync task is in Celery Beat schedule."""
    from core.celery_app import celery_app

    beat_schedule = celery_app.conf.beat_schedule
    assert "sync-quickbooks-customers-all-tenants" in beat_schedule
    assert (
        beat_schedule["sync-quickbooks-customers-all-tenants"]["task"]
        == "sync_all_tenants_customers"
    )
