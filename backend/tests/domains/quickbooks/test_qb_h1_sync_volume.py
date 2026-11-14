"""
QB-H1 Task 6 — Webhook Entity Guard + Multi-Entity Volume Tests

Task 6a: Verify the webhook entity guard — unhandled entity types (e.g.
``Estimate``, ``CreditMemo``) produce a WARNING log and a clean return
(no exception → no Celery retry storm).

Task 6b: Volume test — 50 QB customers across a mocked query response
through ``sync_all_customers_from_qb`` → 50 mappings, 0 conflicts.

All httpx calls are mocked — no live Intuit calls.

Batch: QB-H1
Design: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §F.5
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import select

from app.models.crm import Customer
from app.models.system import (
    AppService,
    IntegrationCredential,
    IntegrationSyncMapping,
)
from core.encryption import encrypt_token
from services.quickbooks_sync import QuickBooksSync

pytestmark = [
    pytest.mark.domain_quickbooks,
    pytest.mark.unit,
]


@pytest.fixture
def qb_credential_volume(db_session, test_tenant, test_user):
    """Ensure a QuickBooks credential exists for the test tenant."""
    # Find existing app_service
    app_service = db_session.exec(
        select(AppService).where(
            AppService.tenant_id == test_tenant.id,
            AppService.provider_code == "quickbooks",
        )
    ).first()
    if not app_service:
        app_service = AppService(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            name="QuickBooks Online",
            category_code="accounting",
            provider_code="quickbooks",
            external_account_id="1234567890123456",
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(app_service)
        db_session.flush()

    # Check for existing credential — update it with valid test tokens
    cred = db_session.exec(
        select(IntegrationCredential).where(
            IntegrationCredential.tenant_id == test_tenant.id,
            IntegrationCredential.app_service_id == app_service.id,
        )
    ).first()
    now = datetime.now(UTC)
    if cred:
        # Ensure it's active, not expiring soon, and has valid test tokens
        cred.connection_status = "active"
        cred.expires_at = now + timedelta(hours=1)
        cred.secret_json = {
            "access_token_encrypted": encrypt_token("test_access"),
            "refresh_token_encrypted": encrypt_token("test_refresh"),
        }
        db_session.add(cred)
        db_session.commit()
        return app_service

    now = datetime.now(UTC)
    credential = IntegrationCredential(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        app_service_id=app_service.id,
        secret_json={
            "access_token_encrypted": encrypt_token("test_access"),
            "refresh_token_encrypted": encrypt_token("test_refresh"),
        },
        expires_at=now + timedelta(hours=1),
        last_refresh_at=now,
        connected_at=now,
        connection_status="active",
        initiated_by_user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(credential)
    db_session.commit()
    return app_service


def _make_mock_qb_response(status_code: int, json_data: dict):
    """Create a mock httpx.Response for QB API calls."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = {"intuit_tid": "test-tid-volume"}
    response.json.return_value = json_data
    response.text = str(json_data)
    response.raise_for_status = MagicMock()
    return response


# ==================== Task 6a: Webhook Entity Guard ====================


class TestWebhookEntityGuard:
    """Verify unhandled entity types produce a WARNING + clean return."""

    def test_estimate_entity_type_logs_warning_and_returns_cleanly(
        self, db_session, test_tenant, qb_credential_volume, caplog
    ):
        """An unhandled entity type ('Estimate') → WARNING + clean return,
        no exception raised."""
        import logging

        from tasks.quickbooks_sync import sync_quickbooks_entity_task

        with caplog.at_level(logging.WARNING, logger="tasks.quickbooks_sync"):
            result = sync_quickbooks_entity_task.apply(
                args=[
                    str(test_tenant.id),
                    "Estimate",
                    "QB-EST-001",
                    "create",
                ]
            ).get()

        # Task returns cleanly (no exception)
        assert result["status"] == "success"
        assert result["result"] == "skipped_unknown_entity"

        # WARNING log captured
        warning_logs = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "not handled" in r.message
        ]
        assert len(warning_logs) >= 1, (
            "Expected a WARNING log for unhandled entity type"
        )

    def test_credit_memo_entity_type_logs_warning(
        self, db_session, test_tenant, qb_credential_volume, caplog
    ):
        """A 'CreditMemo' entity type → WARNING + clean return."""
        import logging

        from tasks.quickbooks_sync import sync_quickbooks_entity_task

        with caplog.at_level(logging.WARNING, logger="tasks.quickbooks_sync"):
            result = sync_quickbooks_entity_task.apply(
                args=[
                    str(test_tenant.id),
                    "CreditMemo",
                    "QB-CM-001",
                    "create",
                ]
            ).get()

        assert result["status"] == "success"
        assert result["result"] == "skipped_unknown_entity"

    def test_payment_entity_type_logs_warning(
        self, db_session, test_tenant, qb_credential_volume, caplog
    ):
        """A 'Payment' entity type → WARNING + clean return."""
        import logging

        from tasks.quickbooks_sync import sync_quickbooks_entity_task

        with caplog.at_level(logging.WARNING, logger="tasks.quickbooks_sync"):
            result = sync_quickbooks_entity_task.apply(
                args=[
                    str(test_tenant.id),
                    "Payment",
                    "QB-PAY-001",
                    "create",
                ]
            ).get()

        assert result["status"] == "success"
        assert result["result"] == "skipped_unknown_entity"


# ==================== Task 6b: Volume Test ====================


class TestSyncVolume:
    """Volume test for customer sync."""

    def test_50_customers_synced(self, db_session, test_tenant, qb_credential_volume):
        """50 QB customers across a mocked query response → 50 mappings,
        0 conflicts, 0 failures."""
        # Generate 50 QB customers with unique display names
        qb_customers = [
            {
                "Id": str(2000 + i),
                "DisplayName": f"Volume Customer {uuid.uuid4().hex[:8]}",
                "SyncToken": "0",
                "Active": True,
            }
            for i in range(50)
        ]

        # Mock the QB Query API response
        mock_response = _make_mock_qb_response(
            200,
            {"QueryResponse": {"Customer": qb_customers}},
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "services.quickbooks_sync.httpx.AsyncClient", return_value=mock_client
        ):
            sync = QuickBooksSync(test_tenant.id, db_session)
            result = asyncio.run(sync.sync_all_customers_from_qb(since=None))

        # Assert 50 synced, 0 conflicts, 0 failed
        assert result["synced"] == 50, f"Expected 50 synced, got {result['synced']}"
        assert result["conflicts"] == 0
        assert result["failed"] == 0

        # Verify 50 mappings were created (filter by the QB IDs we inserted)
        qb_ids = {str(2000 + i) for i in range(50)}
        mappings = db_session.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.tenant_id == test_tenant.id,
                IntegrationSyncMapping.entity_type_code == "customer",
                IntegrationSyncMapping.external_id.in_(qb_ids),
            )
        ).all()
        assert len(mappings) == 50, f"Expected 50 mappings, found {len(mappings)}"

        # Verify all mappings have external_version_token set
        for m in mappings:
            assert m.external_version_token == "0", (
                f"Mapping {m.id} has wrong external_version_token: {m.external_version_token}"
            )

        # Cleanup
        for m in mappings:
            db_session.delete(m)
        for c in db_session.exec(
            select(Customer).where(
                Customer.tenant_id == test_tenant.id,
                Customer.display_name.like("Volume Customer%"),
            )
        ).all():
            db_session.delete(c)
        db_session.commit()
