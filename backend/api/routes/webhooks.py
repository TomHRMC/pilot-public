"""
Webhook receiver endpoints.

QuickBooks webhook:
  Security: HMAC-SHA256 signature verification prevents unauthorized requests.
  Payload Format: CloudEvents 1.0 specification.
  ngrok Endpoint: https://your-tunnel.ngrok-free.dev/api/v1/webhooks/quickbooks
  Design Reference: Task #19 in phase-2-5-implementation-roadmap.md
  Gap Reference: Gap #27 in phase-1-4-implementation-gap-analysis.md

Note: Twilio inbound SMS webhook was replaced by Telnyx in B11/A59.
  See webhooks_sms.py for POST /api/v1/webhooks/sms/telnyx-inbound
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.models.system import AppService, WebhookEvent
from core.db import get_db
from core.quickbooks_webhook import verify_quickbooks_signature

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/quickbooks")
async def quickbooks_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Receive webhook notifications from QuickBooks (Cloud Events format).

    This endpoint is publicly accessible via ngrok:
    https://your-tunnel.ngrok-free.dev/api/v1/webhooks/quickbooks

    Security: HMAC signature verification prevents unauthorized requests.

    Payload Format: CloudEvents 1.0 specification.
    Enable "Cloud event payload format" in Intuit Developer Portal.

    QuickBooks expects 200 OK response within 5 seconds.

    Returns:
        dict: Status and event ID
    """
    # Get raw body for signature verification
    payload_bytes = await request.body()

    # Verify HMAC signature (raises HTTPException if invalid)
    signature_valid = await verify_quickbooks_signature(request, payload_bytes)

    # Parse JSON payload (Cloud Events format)
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # QuickBooks can send single event or array of events
    events = payload if isinstance(payload, list) else [payload]

    logger.info(f"QuickBooks webhook received: {len(events)} event(s)")

    processed_events = []

    for event in events:
        # Extract Cloud Events fields
        # QuickBooks uses two formats:
        # 1. Old format: data.realmId, data.entityName, data.entityId
        # 2. New format (Cloud Events): intuitaccountid, intuitentityid at root
        event_type = event.get("type")  # e.g., "qbo.customer.created.v1"
        event_id = event.get("id")  # CloudEvents ID (for idempotency)

        # Try new format first (Cloud Events)
        realm_id = event.get("intuitaccountid")
        entity_id = event.get("intuitentityid")

        # Fall back to old format if new format not found
        if not realm_id:
            event_data = event.get("data", {})
            realm_id = event_data.get("realmId")
            entity_id = event_data.get("entityId")
            entity_name = event_data.get("entityName")
        else:
            # Parse entity name from event type (qbo.customer.created.v1 → Customer)
            # Event type format: qbo.<entity>.<operation>.v1
            parts = event_type.split(".")
            entity_name = parts[1].capitalize() if len(parts) > 1 else "Unknown"

        logger.info(f"Processing webhook: {event_type} - Event ID: {event_id}")
        logger.debug(
            f"Webhook data: realm_id={realm_id}, entity={entity_name}, id={entity_id}"
        )

        # Parse operation from event type
        # Old format: "com.intuit.quickbooks.customer.create" → "create"
        # New format: "qbo.customer.created.v1" → "created"
        parts = event_type.split(".") if event_type else []
        if len(parts) >= 3:
            operation = parts[-2] if parts[-1].startswith("v") else parts[-1]
        else:
            operation = "unknown"

        # Get tenant_id from realm_id
        tenant_id = await get_tenant_by_realm_id(realm_id, db)

        if not tenant_id:
            logger.warning(f"No tenant found for realm_id: {realm_id}")

            # Log webhook event with no tenant (for debugging)
            webhook_event = WebhookEvent(
                id=uuid.uuid4(),
                tenant_id=None,
                source_app="quickbooks",
                event_type=event_type,
                event_id=event_id,
                payload=event,
                signature_valid=signature_valid,
                error_message=f"Tenant not found for realm_id: {realm_id}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(webhook_event)
            db.commit()

            processed_events.append(
                {"event_id": event_id, "status": "tenant_not_found"}
            )
            continue

        # Log webhook event
        webhook_event = WebhookEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            source_app="quickbooks",
            event_type=event_type,
            event_id=event_id,
            payload=event,
            signature_valid=signature_valid,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(webhook_event)
        db.commit()

        # Trigger background sync task (non-blocking)
        background_tasks.add_task(
            trigger_sync_task,
            tenant_id=str(tenant_id),
            entity_type=entity_name,
            entity_id=entity_id,
            operation=operation,
        )

        logger.info(
            f"Queued sync for {entity_name} {entity_id} ({operation}) - Tenant: {tenant_id}"
        )

        processed_events.append({"event_id": event_id, "status": "queued"})

    # QuickBooks expects 200 OK response within 5 seconds
    return {
        "status": "received",
        "events_processed": len(processed_events),
        "events": processed_events,
    }


async def get_tenant_by_realm_id(realm_id: str, db: Session) -> uuid.UUID | None:
    """
    Look up tenant_id from QuickBooks realm_id.

    Uses indexed AppService.external_account_id for O(1) lookup.

    Args:
        realm_id: QuickBooks company ID (realm_id)
        db: Database session

    Returns:
        UUID of tenant or None if not found
    """
    stmt = (
        select(AppService)
        .where(AppService.external_account_id == realm_id)
        .where(AppService.provider_code == "quickbooks")
        .where(AppService.is_active == True)
    )
    result = db.exec(stmt).first()
    return result.tenant_id if result else None


def trigger_sync_task(tenant_id: str, entity_type: str, entity_id: str, operation: str):
    """
    Trigger Celery background task for entity sync.

    This function is called by FastAPI BackgroundTasks to ensure
    webhook responds within 5 seconds (QuickBooks requirement).

    Args:
        tenant_id: Tenant UUID string
        entity_type: Entity type (e.g., "Customer", "Invoice")
        entity_id: QuickBooks entity ID
        operation: Operation (e.g., "create", "update", "delete")
    """
    # Import here to avoid circular dependency
    from tasks.quickbooks_sync import sync_quickbooks_entity_task

    sync_quickbooks_entity_task.delay(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        operation=operation,
    )
