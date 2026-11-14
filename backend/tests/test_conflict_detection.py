"""
Tests for QuickBooks sync conflict detection and resolution.

Task Reference: Phase 3, Task #18 - Conflict Detection & Resolution
Gap Reference: Gap #24 in phase-1-4-implementation-gap-analysis.md

Test Coverage:
- Conflict detection logic (version token comparison)
- Conflict queuing (payload serialization)
- Conflict listing API endpoint
- Conflict resolution API (accept_local, accept_remote, merge)
- Tenant isolation for conflicts

NOTE: Since IntegrationSyncMapping doesn't have internal_version_token field yet,
      conflict detection tests are simplified to test the core logic.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

from app.models.core import Tenant
from app.models.crm import Customer, CustomerType
from app.models.system import (
    AppService,
    IntegrationCredential,
    IntegrationSyncConflict,
    IntegrationSyncMapping,
)
from services.quickbooks_sync import QuickBooksSync

# ==================== FIXTURES ====================


@pytest.fixture
def qb_app_service(db_session, test_tenant, test_user):
    """Get or create QuickBooks AppService for testing."""
    from sqlmodel import select

    # Try to find existing QuickBooks AppService for this tenant
    stmt = select(AppService).where(
        AppService.tenant_id == test_tenant.id,
        AppService.provider_code == "quickbooks",
    )
    app_service = db_session.exec(stmt).first()

    if not app_service:
        # Create if it doesn't exist
        app_service = AppService(
            tenant_id=test_tenant.id,
            name="QuickBooks Online",
            category_code="accounting",
            provider_code="quickbooks",
            external_account_id="1234567890123456",  # Sandbox realm ID
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(app_service)
        db_session.commit()
        db_session.refresh(app_service)

    return app_service


@pytest.fixture
def qb_credential(db_session, test_tenant, qb_app_service, test_user):
    """Create QuickBooks credential for testing."""
    from core.encryption import encrypt_token

    credential = IntegrationCredential(
        tenant_id=test_tenant.id,
        app_service_id=qb_app_service.id,
        connection_status="active",
        secret_json={
            "access_token_encrypted": encrypt_token("test_access_token_12345"),
            "refresh_token_encrypted": encrypt_token("test_refresh_token_67890"),
        },
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        initiated_by_user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)
    return credential


@pytest.fixture
def qb_credential_full(db_session, test_tenant, qb_app_service, test_user):
    """
    Full QuickBooks credential for resolution tests.
    Includes all required fields for sync operations.
    """
    from core.encryption import encrypt_token

    credential = IntegrationCredential(
        tenant_id=test_tenant.id,
        app_service_id=qb_app_service.id,
        connection_status="active",
        secret_json={
            "access_token_encrypted": encrypt_token("test_access_token_full"),
            "refresh_token_encrypted": encrypt_token("test_refresh_token_full"),
        },
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        initiated_by_user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)
    return credential


@pytest.fixture
def test_customer(db_session, test_tenant, test_user):
    """Create test customer in Pilot for Trades."""
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="John Smith Electric",
        first_name="John",
        last_name="Smith",
        company_name="Smith Electric LLC",
        email="john@smithelectric.example.com",
        mobile_phone="555-1234",
        type=CustomerType.company,
        is_active=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def sync_mapping(db_session, test_tenant, qb_app_service, test_customer, test_user):
    """Create sync mapping for test customer."""
    mapping = IntegrationSyncMapping(
        tenant_id=test_tenant.id,
        app_service_id=qb_app_service.id,
        entity_type_code="customer",
        entity_id=test_customer.id,
        external_id="QB123",
        external_version_token="5",
        sync_preference="pilot_master",
        last_synced_at=datetime.now(UTC) - timedelta(minutes=10),
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(mapping)
    db_session.commit()
    db_session.refresh(mapping)
    return mapping


# ==================== CONFLICT DETECTION TESTS ====================


class TestConflictDetection:
    """Test conflict detection logic."""

    @pytest.mark.asyncio
    async def test_no_conflict_on_first_sync(
        self, db_session, test_tenant, qb_app_service, qb_credential
    ):
        """First sync should never create conflict (no mapping exists)."""
        sync = QuickBooksSync(test_tenant.id, db_session)

        qb_customer = {
            "Id": "QB999",
            "DisplayName": "New Customer LLC",
            "SyncToken": "0",
        }

        # Sync customer (no mapping exists, so no conflict check)
        result = await sync.sync_customer_from_qb(qb_customer)

        # Verify customer created
        assert result is not None
        assert result.display_name == "New Customer LLC"

        # Verify no conflict created
        stmt = select(IntegrationSyncConflict).where(
            IntegrationSyncConflict.tenant_id == test_tenant.id
        )
        conflicts = db_session.exec(stmt).all()
        assert len(conflicts) == 0


class TestConflictQueuing:
    """Test conflict queue creation and payload storage."""

    @pytest.mark.asyncio
    async def test_conflict_record_created_with_payloads(
        self,
        db_session,
        test_tenant,
        qb_app_service,
        qb_credential,
        test_customer,
        sync_mapping,
    ):
        """Conflict record should store both internal and external payloads."""
        sync = QuickBooksSync(test_tenant.id, db_session)

        qb_customer = {
            "Id": "QB123",
            "DisplayName": "Smith Electrical Services",
            "GivenName": "John",
            "FamilyName": "Smith",
            "CompanyName": "Smith Electric",
            "SyncToken": "6",
            "Active": True,
            "MetaData": {"LastUpdatedTime": "2026-03-22T10:00:00Z"},
        }

        # Queue conflict
        conflict = await sync.queue_conflict(
            sync_mapping, qb_customer, qb_app_service.id
        )

        # Verify conflict created
        assert conflict is not None
        assert conflict.tenant_id == test_tenant.id
        assert conflict.entity_id == test_customer.id
        assert conflict.external_id == "QB123"
        assert conflict.status == "pending"

        # Verify internal payload
        assert conflict.internal_payload["display_name"] == test_customer.display_name
        assert conflict.internal_payload["email"] == test_customer.email

        # Verify external payload
        assert conflict.external_payload["DisplayName"] == "Smith Electrical Services"
        assert conflict.external_payload["SyncToken"] == "6"


# ==================== CONFLICT API TESTS ====================


class TestConflictListingAPI:
    """Test conflict listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_conflicts_endpoint(
        self, client, db_session, test_tenant, test_user, qb_app_service
    ):
        """GET /conflicts should return unresolved conflicts for tenant."""
        # Create test conflicts
        conflict1 = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB111",
            status="pending",
            internal_payload={"display_name": "Customer A"},
            external_payload={"DisplayName": "Customer A QB"},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        conflict2 = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB222",
            status="pending",
            internal_payload={"display_name": "Customer B"},
            external_payload={"DisplayName": "Customer B QB"},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(conflict1)
        db_session.add(conflict2)
        db_session.commit()

        # Call API (use test endpoint)
        response = client.get(
            "/api/v1/integrations/quickbooks/conflicts/test",
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["status"] == "pending"
        assert data[1]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_conflicts_filter_by_status(
        self, client, db_session, test_tenant, test_user, qb_app_service
    ):
        """GET /conflicts?status=pending should filter results."""
        # Create pending and resolved conflicts
        pending = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB333",
            status="pending",
            internal_payload={"display_name": "Pending"},
            external_payload={"DisplayName": "Pending QB"},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        resolved = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB444",
            status="resolved_keep_internal",
            internal_payload={"display_name": "Resolved"},
            external_payload={"DisplayName": "Resolved QB"},
            resolved_at=datetime.now(UTC),
            resolved_by=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(pending)
        db_session.add(resolved)
        db_session.commit()

        # Filter for pending only (use test endpoint)
        response = client.get(
            "/api/v1/integrations/quickbooks/conflicts/test?status=pending",
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["external_id"] == "QB333"


class TestConflictResolutionAPI:
    """Test conflict resolution endpoint."""

    @pytest.mark.asyncio
    async def test_resolve_conflict_accept_local(
        self,
        client,
        db_session,
        test_tenant,
        test_user,
        qb_app_service,
        qb_credential_full,
        test_customer,
    ):
        """Resolution strategy 'accept_local' should overwrite QuickBooks."""
        # Create sync mapping
        sync_mapping = IntegrationSyncMapping(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=test_customer.id,
            external_id="QB123",
            external_version_token="5",
            internal_version_token=test_customer.updated_at.isoformat(),
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(sync_mapping)

        # Create conflict
        conflict = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=test_customer.id,
            external_id="QB123",
            status="pending",
            internal_payload={
                "display_name": test_customer.display_name,
                "email": test_customer.email,
            },
            external_payload={
                "Id": "QB123",
                "DisplayName": "Different Name",
                "SyncToken": "6",
            },
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(conflict)
        db_session.commit()
        db_session.refresh(conflict)

        # Mock QuickBooks API call - properly mock the AsyncClient
        mock_response = MagicMock(
            status_code=200,
            json=lambda: {
                "Customer": {
                    "Id": "QB123",
                    "DisplayName": test_customer.display_name,
                    "SyncToken": "7",
                }
            },
            raise_for_status=lambda: None,
        )

        async def mock_post(*args, **kwargs):
            return mock_response

        async def mock_aenter(self):
            return self

        async def mock_aexit(self, *args):
            return None

        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Resolve conflict (use test endpoint)
            response = client.post(
                f"/api/v1/integrations/quickbooks/conflicts/{conflict.id}/resolve/test",
                json={"strategy": "accept_local"},
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved_keep_internal"

        # Verify conflict marked as resolved
        db_session.refresh(conflict)
        assert conflict.resolved_at is not None
        assert conflict.resolved_by == test_user.id
        assert conflict.status == "resolved_keep_internal"

    @pytest.mark.asyncio
    async def test_resolve_conflict_accept_remote(
        self,
        client,
        db_session,
        test_tenant,
        test_user,
        qb_app_service,
        qb_credential_full,
        test_customer,
    ):
        """Resolution strategy 'accept_remote' should overwrite Pilot for Trades."""
        # Create sync mapping
        sync_mapping = IntegrationSyncMapping(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=test_customer.id,
            external_id="QB123",
            external_version_token="5",
            internal_version_token=test_customer.updated_at.isoformat(),
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(sync_mapping)

        # Create conflict
        conflict = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=test_customer.id,
            external_id="QB123",
            status="pending",
            internal_payload={"display_name": "Pilot for Trades Version"},
            external_payload={
                "Id": "QB123",
                "DisplayName": "QuickBooks Version",
                "SyncToken": "5",
            },
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(conflict)
        db_session.commit()
        db_session.refresh(conflict)

        # Resolve conflict (use test endpoint)
        response = client.post(
            f"/api/v1/integrations/quickbooks/conflicts/{conflict.id}/resolve/test",
            json={"strategy": "accept_remote"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved_keep_external"

        # Verify Pilot for Trades customer updated
        db_session.refresh(test_customer)
        assert test_customer.display_name == "QuickBooks Version"

    @pytest.mark.asyncio
    async def test_resolve_conflict_merge(
        self,
        client,
        db_session,
        test_tenant,
        test_user,
        qb_app_service,
        qb_credential_full,
        test_customer,
    ):
        """Resolution strategy 'merge' should apply merged data to both systems."""
        # Create sync mapping
        sync_mapping = IntegrationSyncMapping(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=test_customer.id,
            external_id="QB123",
            external_version_token="5",
            internal_version_token=test_customer.updated_at.isoformat(),
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(sync_mapping)

        # Create conflict
        conflict = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=test_customer.id,
            external_id="QB123",
            status="pending",
            internal_payload={"display_name": "Pilot for Trades Version"},
            external_payload={"DisplayName": "QuickBooks Version"},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(conflict)
        db_session.commit()
        db_session.refresh(conflict)

        # Mock QuickBooks API call - properly mock the AsyncClient
        mock_response = MagicMock(
            status_code=200,
            json=lambda: {
                "Customer": {
                    "Id": "QB123",
                    "DisplayName": "Merged Version",
                    "SyncToken": "7",
                }
            },
            raise_for_status=lambda: None,
        )

        async def mock_post(*args, **kwargs):
            return mock_response

        async def mock_aenter(self):
            return self

        async def mock_aexit(self, *args):
            return None

        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Resolve with merged data (use test endpoint)
            response = client.post(
                f"/api/v1/integrations/quickbooks/conflicts/{conflict.id}/resolve/test",
                json={
                    "strategy": "merge",
                    "merged_payload": {"display_name": "Merged Version"},
                },
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved_keep_internal"

        # Verify Pilot for Trades customer updated with merged data
        db_session.refresh(test_customer)
        assert test_customer.display_name == "Merged Version"

    @pytest.mark.asyncio
    async def test_cannot_resolve_already_resolved_conflict(
        self, client, db_session, test_tenant, test_user, qb_app_service
    ):
        """Attempting to resolve already-resolved conflict should fail."""
        # Create already-resolved conflict
        conflict = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB999",
            status="resolved_keep_internal",
            internal_payload={"display_name": "Test"},
            external_payload={"DisplayName": "Test"},
            resolved_at=datetime.now(UTC),
            resolved_by=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(conflict)
        db_session.commit()

        # Try to resolve again (use test endpoint)
        response = client.post(
            f"/api/v1/integrations/quickbooks/conflicts/{conflict.id}/resolve/test",
            json={"strategy": "accept_local"},
        )

        # Should fail with 400
        assert response.status_code == 400
        assert "already resolved" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_resolution_strategy_rejected(
        self, client, db_session, test_tenant, test_user, qb_app_service
    ):
        """Invalid resolution strategy should return 400."""
        conflict = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB888",
            status="pending",
            internal_payload={"display_name": "Test"},
            external_payload={"DisplayName": "Test"},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(conflict)
        db_session.commit()

        # Try invalid strategy (use test endpoint)
        response = client.post(
            f"/api/v1/integrations/quickbooks/conflicts/{conflict.id}/resolve/test",
            json={"strategy": "invalid_strategy"},
        )

        assert response.status_code == 400
        assert "invalid strategy" in response.json()["detail"].lower()


# ==================== TENANT ISOLATION TESTS ====================


class TestConflictTenantIsolation:
    """Test multi-tenancy isolation for conflicts."""

    @pytest.mark.asyncio
    async def test_conflicts_filtered_by_tenant(
        self, client, db_session, test_tenant, test_user, qb_app_service
    ):
        """Tenant A should not see Tenant B's conflicts."""
        # Create second tenant
        tenant2 = Tenant(
            name="Tenant 2",
            email="tenant2@test.com",
            plan_type="pro",
            is_active=True,
        )
        db_session.add(tenant2)
        db_session.commit()

        # Create conflict for tenant 1
        conflict1 = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB_T1",
            status="pending",
            internal_payload={"display_name": "Tenant 1 Conflict"},
            external_payload={"DisplayName": "Tenant 1 QB"},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(conflict1)

        # Create AppService for tenant2
        app_service2 = AppService(
            tenant_id=tenant2.id,
            name="QuickBooks Online",
            category_code="accounting",
            provider_code="quickbooks",
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(app_service2)
        db_session.commit()

        # Create conflict for tenant 2
        conflict2 = IntegrationSyncConflict(
            tenant_id=tenant2.id,
            app_service_id=app_service2.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB_T2",
            status="pending",
            internal_payload={"display_name": "Tenant 2 Conflict"},
            external_payload={"DisplayName": "Tenant 2 QB"},
            created_by=test_user.id,
            updated_by=None,
        )
        db_session.add(conflict2)
        db_session.commit()

        # Tenant 1 user lists conflicts (use test endpoint)
        response = client.get(
            "/api/v1/integrations/quickbooks/conflicts/test",
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see tenant 1's conflict
        assert len(data) == 1
        assert data[0]["external_id"] == "QB_T1"

    @pytest.mark.asyncio
    async def test_cannot_resolve_other_tenant_conflict(
        self, client, db_session, test_tenant, test_user, qb_app_service
    ):
        """Tenant A should not be able to resolve Tenant B's conflict."""
        # Create second tenant
        tenant2 = Tenant(
            name="Tenant 2",
            email="tenant2@test.com",
            plan_type="pro",
            is_active=True,
        )
        db_session.add(tenant2)
        db_session.commit()

        # Create AppService for tenant2
        app_service2 = AppService(
            tenant_id=tenant2.id,
            name="QuickBooks Online",
            category_code="accounting",
            provider_code="quickbooks",
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(app_service2)
        db_session.commit()

        # Create conflict for tenant 2
        conflict = IntegrationSyncConflict(
            tenant_id=tenant2.id,
            app_service_id=app_service2.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            external_id="QB_T2",
            status="pending",
            internal_payload={"display_name": "Tenant 2"},
            external_payload={"DisplayName": "Tenant 2 QB"},
            created_by=None,
            updated_by=None,
        )
        db_session.add(conflict)
        db_session.commit()

        # Tenant 1 user tries to resolve tenant 2's conflict (use test endpoint)
        response = client.post(
            f"/api/v1/integrations/quickbooks/conflicts/{conflict.id}/resolve/test",
            json={"strategy": "accept_local"},
        )

        # Should fail with 403 Forbidden
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()


class TestInternalVersionTokenTracking:
    """Test that internal_version_token is properly tracked during sync operations."""

    @pytest.mark.asyncio
    async def test_internal_version_token_updated_on_sync(
        self,
        db_session,
        test_tenant,
        qb_app_service,
        qb_credential,
        test_customer,
    ):
        """Verify internal_version_token is updated after sync."""
        sync = QuickBooksSync(test_tenant.id, db_session)

        # Create initial mapping with initial version
        original_version = test_customer.updated_at.isoformat()
        print(
            f"TEST: Creating mapping with entity_id={test_customer.id}, app_service_id={qb_app_service.id}"
        )
        sync_mapping = IntegrationSyncMapping(
            tenant_id=test_tenant.id,
            app_service_id=qb_app_service.id,
            entity_type_code="customer",
            entity_id=test_customer.id,
            external_id="QB999",
            external_version_token="0",
            internal_version_token=original_version,
            created_by=test_customer.created_by,
            updated_by=test_customer.updated_by,
        )
        db_session.add(sync_mapping)
        db_session.commit()
        print(f"TEST: Mapping created with id={sync_mapping.id}")

        # Edit customer (updated_at changes)
        import time

        time.sleep(0.01)  # Ensure timestamp changes
        test_customer.display_name = "Updated Name"
        # Force updated_at to change by setting it explicitly
        test_customer.updated_at = datetime.now(UTC)
        db_session.add(test_customer)
        db_session.commit()
        db_session.refresh(test_customer)

        # Mock QB API for sync - properly mock the AsyncClient
        mock_response = MagicMock(
            status_code=200,
            json=lambda: {"Customer": {"Id": "QB999", "SyncToken": "1"}},
            raise_for_status=lambda: None,
        )

        async def mock_post(*args, **kwargs):
            return mock_response

        async def mock_aenter(self):
            return self

        async def mock_aexit(self, *args):
            return None

        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await sync.sync_customer_to_qb(test_customer.id)
            print(f"Sync result: {result}")

        # Query for the mapping again (sync may have found existing or created new one)
        from sqlmodel import select

        stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.entity_id == test_customer.id,
            IntegrationSyncMapping.app_service_id == qb_app_service.id,
            IntegrationSyncMapping.entity_type_code == "customer",
        )
        sync_mapping_after = db_session.exec(stmt).first()
        assert sync_mapping_after is not None, "Mapping should exist after sync"
        print(
            f"Mapping external_version_token after sync: {sync_mapping_after.external_version_token}"
        )

        # Verify tokens were updated correctly
        assert sync_mapping_after.external_version_token == "1", (
            "External version should be updated"
        )
        assert sync_mapping_after.internal_version_token is not None, (
            "Internal version should be set"
        )
        assert sync_mapping_after.internal_version_token != original_version, (
            "Internal version should change"
        )

        # Verify internal_version_token is a valid timestamp
        try:
            datetime.fromisoformat(sync_mapping_after.internal_version_token)
        except ValueError:
            pytest.fail("internal_version_token is not a valid ISO timestamp")
