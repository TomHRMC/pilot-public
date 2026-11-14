"""
Tests for QuickBooks webhook handler (Task #19 - Gap #27).

Tests webhook receiver endpoint with Cloud Events format:
- HMAC-SHA256 signature verification
- Cloud Events payload parsing
- Tenant lookup from realm_id
- Background task triggering
- Webhook event logging
- Error handling

Design Reference: Task #19 in phase-2-5-implementation-roadmap.md
"""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models.system import AppService, WebhookEvent
from core.quickbooks_webhook import verify_quickbooks_signature

# ============================================================================
# HMAC Signature Verification Tests
# ============================================================================


@pytest.mark.asyncio
async def test_verify_signature_valid(mock_cognito_jwt_verify):
    """Test webhook signature verification with valid signature."""
    from core.config import settings

    # Mock settings
    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    # Create test payload
    payload = b'{"test": "data"}'

    # Calculate expected signature (Base64-encoded HMAC)
    expected_signature = base64.b64encode(
        hmac.new(
            settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN.encode(),
            payload,
            hashlib.sha256,
        ).digest()
    ).decode()

    # Mock request with valid signature
    mock_request = MagicMock()
    mock_request.headers.get.return_value = expected_signature

    # Should not raise exception
    result = await verify_quickbooks_signature(mock_request, payload)
    assert result is True


@pytest.mark.asyncio
async def test_verify_signature_invalid(mock_cognito_jwt_verify):
    """Test webhook signature verification with invalid signature."""
    from core.config import settings

    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    payload = b'{"test": "data"}'

    # Mock request with invalid signature
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "invalid_signature_here"

    # Should raise HTTPException 401
    with pytest.raises(HTTPException) as exc_info:
        await verify_quickbooks_signature(mock_request, payload)

    assert exc_info.value.status_code == 401
    assert "Invalid signature" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_signature_missing(mock_cognito_jwt_verify):
    """Test webhook signature verification with missing signature header."""
    payload = b'{"test": "data"}'

    # Mock request with no signature header
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    # Should raise HTTPException 401
    with pytest.raises(HTTPException) as exc_info:
        await verify_quickbooks_signature(mock_request, payload)

    assert exc_info.value.status_code == 401
    assert "Missing signature" in str(exc_info.value.detail)


# ============================================================================
# Webhook Endpoint Tests
# ============================================================================


def test_quickbooks_webhook_customer_create(client, db_session, test_tenant):
    """Test webhook for customer.create event."""
    from core.config import settings

    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    # Create AppService with realm_id
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Sandbox",
        category_code="accounting",
        provider_code="quickbooks",
        is_active=True,
        external_account_id="123456789",  # realm_id
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(app_service)
    db_session.commit()

    # Create Cloud Events payload
    payload = {
        "specversion": "1.0",
        "type": "com.intuit.quickbooks.customer.create",
        "source": "//quickbooks.api.intuit.com/company/123456789",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "realmId": "123456789",
            "entityName": "Customer",
            "entityId": "67",
            "lastUpdated": datetime.now(UTC).isoformat(),
        },
    }

    payload_bytes = json.dumps(payload).encode("utf-8")

    # Calculate signature (Base64-encoded HMAC)
    signature = base64.b64encode(
        hmac.new(
            settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN.encode(),
            payload_bytes,
            hashlib.sha256,
        ).digest()
    ).decode()

    # Mock Celery task (patch where it's imported in trigger_sync_task)
    with patch("tasks.quickbooks_sync.sync_quickbooks_entity_task") as mock_task:
        mock_task.delay = MagicMock()

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/quickbooks",
            content=payload_bytes,
            headers={"intuit-signature": signature, "Content-Type": "application/json"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["events_processed"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["event_id"] == payload["id"]
    assert data["events"][0]["status"] == "queued"

    # Verify webhook event was logged
    stmt = select(WebhookEvent).where(WebhookEvent.event_id == payload["id"])
    webhook_event = db_session.exec(stmt).first()
    assert webhook_event is not None
    assert webhook_event.source_app == "quickbooks"
    assert webhook_event.event_type == "com.intuit.quickbooks.customer.create"
    assert webhook_event.signature_valid is True
    assert webhook_event.tenant_id == test_tenant.id


def test_quickbooks_webhook_customer_update(client, db_session, test_tenant):
    """Test webhook for customer.update event."""
    from core.config import settings

    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    # Create AppService with realm_id
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Sandbox",
        category_code="accounting",
        provider_code="quickbooks",
        is_active=True,
        external_account_id="123456789",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(app_service)
    db_session.commit()

    # Create Cloud Events payload
    payload = {
        "specversion": "1.0",
        "type": "com.intuit.quickbooks.customer.update",
        "source": "//quickbooks.api.intuit.com/company/123456789",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "realmId": "123456789",
            "entityName": "Customer",
            "entityId": "67",
            "lastUpdated": datetime.now(UTC).isoformat(),
        },
    }

    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = base64.b64encode(
        hmac.new(
            settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN.encode(),
            payload_bytes,
            hashlib.sha256,
        ).digest()
    ).decode()

    with patch("tasks.quickbooks_sync.sync_quickbooks_entity_task") as mock_task:
        mock_task.delay = MagicMock()

        response = client.post(
            "/api/v1/webhooks/quickbooks",
            content=payload_bytes,
            headers={"intuit-signature": signature, "Content-Type": "application/json"},
        )

    assert response.status_code == 200


def test_quickbooks_webhook_customer_delete(client, db_session, test_tenant):
    """Test webhook for customer.delete event."""
    from core.config import settings

    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    # Create AppService
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Sandbox",
        category_code="accounting",
        provider_code="quickbooks",
        is_active=True,
        external_account_id="123456789",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(app_service)
    db_session.commit()

    payload = {
        "specversion": "1.0",
        "type": "com.intuit.quickbooks.customer.delete",
        "source": "//quickbooks.api.intuit.com/company/123456789",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "realmId": "123456789",
            "entityName": "Customer",
            "entityId": "67",
            "lastUpdated": datetime.now(UTC).isoformat(),
        },
    }

    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = base64.b64encode(
        hmac.new(
            settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN.encode(),
            payload_bytes,
            hashlib.sha256,
        ).digest()
    ).decode()

    with patch("tasks.quickbooks_sync.sync_quickbooks_entity_task") as mock_task:
        mock_task.delay = MagicMock()

        response = client.post(
            "/api/v1/webhooks/quickbooks",
            content=payload_bytes,
            headers={"intuit-signature": signature, "Content-Type": "application/json"},
        )

    assert response.status_code == 200


def test_quickbooks_webhook_tenant_not_found(client, db_session):
    """Test webhook when tenant not found for realm_id."""
    from core.config import settings

    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    # No AppService created - tenant won't be found

    payload = {
        "specversion": "1.0",
        "type": "com.intuit.quickbooks.customer.create",
        "source": "//quickbooks.api.intuit.com/company/999999999",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "realmId": "999999999",  # Unknown realm_id
            "entityName": "Customer",
            "entityId": "67",
            "lastUpdated": datetime.now(UTC).isoformat(),
        },
    }

    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = base64.b64encode(
        hmac.new(
            settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN.encode(),
            payload_bytes,
            hashlib.sha256,
        ).digest()
    ).decode()

    response = client.post(
        "/api/v1/webhooks/quickbooks",
        content=payload_bytes,
        headers={"intuit-signature": signature, "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["events_processed"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["status"] == "tenant_not_found"

    # Verify webhook event was logged with no tenant_id
    stmt = select(WebhookEvent).where(WebhookEvent.event_id == payload["id"])
    webhook_event = db_session.exec(stmt).first()
    assert webhook_event is not None
    assert webhook_event.tenant_id is None
    assert webhook_event.error_message is not None
    assert "Tenant not found" in webhook_event.error_message


def test_quickbooks_webhook_invalid_json(client):
    """Test webhook with invalid JSON payload."""
    from core.config import settings

    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    # Invalid JSON
    payload_bytes = b"{ invalid json here"
    signature = base64.b64encode(
        hmac.new(
            settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN.encode(),
            payload_bytes,
            hashlib.sha256,
        ).digest()
    ).decode()

    response = client.post(
        "/api/v1/webhooks/quickbooks",
        content=payload_bytes,
        headers={"intuit-signature": signature, "Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]


def test_quickbooks_webhook_invalid_signature_rejected(client):
    """Test webhook with invalid signature is rejected."""
    from core.config import settings

    settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token_12345"

    payload = {
        "specversion": "1.0",
        "type": "com.intuit.quickbooks.customer.create",
        "source": "//quickbooks.api.intuit.com/company/123456789",
        "id": str(uuid.uuid4()),
        "data": {"realmId": "123456789", "entityName": "Customer", "entityId": "67"},
    }

    payload_bytes = json.dumps(payload).encode("utf-8")

    # Use wrong signature
    wrong_signature = "wrong_signature_here"

    response = client.post(
        "/api/v1/webhooks/quickbooks",
        content=payload_bytes,
        headers={
            "intuit-signature": wrong_signature,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"]


def test_quickbooks_webhook_missing_signature_rejected(client):
    """Test webhook without signature header is rejected."""
    payload = {"test": "data"}
    payload_bytes = json.dumps(payload).encode("utf-8")

    # No signature header
    response = client.post(
        "/api/v1/webhooks/quickbooks",
        content=payload_bytes,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401
    assert "Missing signature" in response.json()["detail"]


# ============================================================================
# Tenant Lookup Tests
# ============================================================================


def test_get_tenant_by_realm_id_success(db_session, test_tenant):
    """Test successful tenant lookup by realm_id."""
    from api.routes.webhooks import get_tenant_by_realm_id

    # Create AppService with realm_id
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Sandbox",
        category_code="accounting",
        provider_code="quickbooks",
        is_active=True,
        external_account_id="test_realm_123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(app_service)
    db_session.commit()

    # Lookup tenant
    import asyncio

    tenant_id = asyncio.run(get_tenant_by_realm_id("test_realm_123", db_session))

    assert tenant_id == test_tenant.id


def test_get_tenant_by_realm_id_not_found(db_session):
    """Test tenant lookup with unknown realm_id."""
    import asyncio

    from api.routes.webhooks import get_tenant_by_realm_id

    tenant_id = asyncio.run(get_tenant_by_realm_id("unknown_realm", db_session))

    assert tenant_id is None


def test_get_tenant_by_realm_id_inactive_service(db_session, test_tenant):
    """Test tenant lookup ignores inactive app services."""
    from api.routes.webhooks import get_tenant_by_realm_id

    # Create inactive AppService
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Sandbox",
        category_code="accounting",
        provider_code="quickbooks",
        is_active=False,  # Inactive
        external_account_id="inactive_realm_123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(app_service)
    db_session.commit()

    import asyncio

    tenant_id = asyncio.run(get_tenant_by_realm_id("inactive_realm_123", db_session))

    # Should not find inactive service
    assert tenant_id is None
