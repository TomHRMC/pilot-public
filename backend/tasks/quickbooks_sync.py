"""
Celery background tasks for QuickBooks synchronization.

These tasks handle scheduled and on-demand sync operations between
Pilot for Trades and QuickBooks Online:
- sync_quickbooks_customers_task: Sync customers for a single tenant
- sync_all_tenants_customers_task: Iterate all tenants and sync customers

Design Reference: Task #17 in phase-2-5-implementation-roadmap.md
Gap Reference: Gap #23 in phase-1-4-implementation-gap-analysis.md

Celery Beat Schedule:
- sync_all_tenants_customers_task: Every 15 minutes

Usage:
    # Manual trigger (sync specific tenant)
    from tasks.quickbooks_sync import sync_quickbooks_customers_task
    sync_quickbooks_customers_task.delay(tenant_id_str)

    # Automatic trigger (Celery Beat)
    # Configured in core/celery_app.py beat_schedule
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.system import AppService, IntegrationCredential
from core.celery_app import celery_app
from services.quickbooks_sync import QuickBooksSync

logger = logging.getLogger(__name__)


@celery_app.task(name="sync_quickbooks_customers", bind=True, max_retries=3)
def sync_quickbooks_customers_task(self, tenant_id: str) -> dict:
    """
    Sync QuickBooks customers for a specific tenant.

    This task performs an incremental sync, fetching only customers
    modified since the last successful sync timestamp.

    Args:
        tenant_id: String representation of tenant UUID

    Returns:
        Dict with sync results:
            - status: "success" or "error"
            - tenant_id: Tenant ID that was synced
            - customers_synced: Number of customers synced
            - last_sync_at: Timestamp of previous sync
            - error: Error message (if status="error")

    Raises:
        Retry: If sync fails (max 3 retries with exponential backoff)
    """
    from core.db import engine as db_engine

    tenant_uuid = uuid.UUID(tenant_id)

    try:
        with Session(db_engine) as db:
            # Initialize sync service
            sync = QuickBooksSync(tenant_uuid, db)

            # Perform incremental sync (only fetch changed customers)
            # Note: sync methods are async, but Celery tasks are sync
            # We need to run them in a sync context
            import asyncio

            # Get last sync timestamp for incremental sync
            last_sync = asyncio.run(sync.get_last_sync_timestamp())

            result = asyncio.run(sync.sync_all_customers_from_qb(since=last_sync))

            return {
                "status": "success",
                "tenant_id": tenant_id,
                "customers_synced": result["synced"],
                "conflicts_detected": result["conflicts"],
                "sync_failures": result["failed"],
                "last_sync_at": last_sync.isoformat() if last_sync else None,
                "synced_at": datetime.now(UTC).isoformat(),
            }

    except ValueError as e:
        # QuickBooks not connected or other validation error
        # Don't retry - this requires user action
        return {
            "status": "error",
            "tenant_id": tenant_id,
            "error": str(e),
            "error_type": "validation_error",
        }

    except Exception as e:
        # Network error, QB API error, etc - retry
        # Exponential backoff: 60s, 180s, 540s
        retry_countdown = 60 * (3**self.request.retries)

        try:
            raise self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            # Max retries exceeded - log error and give up
            return {
                "status": "error",
                "tenant_id": tenant_id,
                "error": str(e),
                "error_type": "max_retries_exceeded",
                "retries": self.request.retries,
            }


@celery_app.task(name="sync_all_tenants_customers")
def sync_all_tenants_customers_task() -> dict:
    """
    Sync QuickBooks customers for all tenants with active QB connections.

    This task is triggered by Celery Beat every 15 minutes.
    It iterates through all tenants that have an active QuickBooks connection
    and triggers a sync task for each.

    Returns:
        Dict with summary:
            - status: "success"
            - tenants_found: Number of tenants with active QB connections
            - tasks_triggered: Number of sync tasks triggered
            - timestamp: When this task ran
    """
    from core.db import engine as db_engine

    try:
        with Session(db_engine) as db:
            # Find all tenants with active QuickBooks connections
            stmt = (
                select(IntegrationCredential.tenant_id)
                .join(AppService)
                .where(
                    AppService.provider_code == "quickbooks",
                    IntegrationCredential.connection_status == "active",
                )
                .distinct()
            )
            tenant_ids = db.exec(stmt).all()

            # Trigger sync task for each tenant
            tasks_triggered = 0
            for tenant_id in tenant_ids:
                try:
                    sync_quickbooks_customers_task.delay(str(tenant_id))
                    tasks_triggered += 1
                except Exception as e:
                    # Log error but continue with other tenants
                    print(f"Error triggering sync for tenant {tenant_id}: {e!s}")

            return {
                "status": "success",
                "tenants_found": len(tenant_ids),
                "tasks_triggered": tasks_triggered,
                "timestamp": datetime.now(UTC).isoformat(),
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


@celery_app.task(name="sync_customer_to_qb", bind=True, max_retries=3)
def sync_customer_to_qb_task(self, tenant_id: str, customer_id: str) -> dict:
    """
    Sync a single Pilot for Trades customer to QuickBooks (on-demand).

    This task is typically triggered when a customer is created or updated
    in Pilot for Trades and needs to be pushed to QuickBooks immediately.

    Args:
        tenant_id: String representation of tenant UUID
        customer_id: String representation of customer UUID

    Returns:
        Dict with sync results:
            - status: "success" or "error"
            - customer_id: Customer ID that was synced
            - qb_customer_id: QuickBooks customer ID
            - qb_sync_token: QuickBooks SyncToken

    Raises:
        Retry: If sync fails (max 3 retries with exponential backoff)
    """
    from core.db import engine as db_engine

    tenant_uuid = uuid.UUID(tenant_id)
    customer_uuid = uuid.UUID(customer_id)

    try:
        with Session(db_engine) as db:
            sync = QuickBooksSync(tenant_uuid, db)

            # Sync customer to QuickBooks
            import asyncio

            qb_customer = asyncio.run(sync.sync_customer_to_qb(customer_uuid))

            return {
                "status": "success",
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "qb_customer_id": qb_customer.get("Id"),
                "qb_sync_token": qb_customer.get("SyncToken"),
                "synced_at": datetime.now(UTC).isoformat(),
            }

    except ValueError as e:
        # Validation error - don't retry
        return {
            "status": "error",
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "error": str(e),
            "error_type": "validation_error",
        }

    except Exception as e:
        # Network error, QB API error, etc - retry
        retry_countdown = 60 * (3**self.request.retries)

        try:
            raise self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            return {
                "status": "error",
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "error": str(e),
                "error_type": "max_retries_exceeded",
                "retries": self.request.retries,
            }


@celery_app.task(name="sync_quickbooks_entity", bind=True, max_retries=3)
def sync_quickbooks_entity_task(
    self, tenant_id: str, entity_type: str, entity_id: str, operation: str
) -> dict:
    """
    Sync a single QuickBooks entity triggered by webhook.

    Faster than full sync (only fetches one record). Uses existing
    QuickBooksSync service for conflict detection and deduplication.

    Args:
        tenant_id: String representation of tenant UUID
        entity_type: Entity type (e.g., "Customer", "Invoice")
        entity_id: QuickBooks entity ID
        operation: Operation (e.g., "create", "update", "delete")

    Returns:
        Dict with sync results:
            - status: "success" or "error"
            - tenant_id: Tenant ID
            - entity_type: Entity type
            - entity_id: QuickBooks entity ID
            - operation: Operation performed
            - error: Error message (if status="error")
    """
    from datetime import UTC, datetime

    from sqlmodel import Session, select

    from app.models.crm import Customer
    from app.models.system import IntegrationSyncMapping
    from core.db import engine
    from services.quickbooks_sync import QuickBooksSync

    logger.info(
        f"Starting entity sync: {entity_type} {entity_id} ({operation}) - Tenant: {tenant_id}"
    )

    try:
        tenant_uuid = uuid.UUID(tenant_id)

        with Session(engine) as db:
            sync = QuickBooksSync(tenant_uuid, db)

            if entity_type == "Customer":
                if operation == "delete":
                    # Soft delete in Pilot for Trades (mark as inactive)
                    # Find customer via sync mapping
                    stmt = (
                        select(IntegrationSyncMapping)
                        .where(IntegrationSyncMapping.tenant_id == tenant_uuid)
                        .where(IntegrationSyncMapping.external_id == entity_id)
                        .where(IntegrationSyncMapping.entity_type == "Customer")
                    )
                    mapping = db.exec(stmt).first()

                    if not mapping:
                        logger.warning(f"No mapping found for QB customer {entity_id}")
                        return {
                            "status": "success",
                            "tenant_id": tenant_id,
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "operation": operation,
                            "result": "not_found",
                        }

                    # Mark customer as inactive
                    customer = db.get(Customer, mapping.aevofab_id)
                    if customer:
                        customer.is_active = False
                        customer.updated_at = datetime.now(UTC)
                        db.add(customer)
                        db.commit()

                        logger.info(
                            f"Soft deleted customer {customer.id} (QB ID: {entity_id})"
                        )
                        return {
                            "status": "success",
                            "tenant_id": tenant_id,
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "operation": operation,
                            "result": "deleted",
                        }
                else:
                    # Fetch customer from QuickBooks API and sync
                    import asyncio

                    qb_customer = asyncio.run(sync.fetch_customer_by_id(entity_id))
                    result = asyncio.run(sync.sync_customer_from_qb(qb_customer))
                    logger.info(f"Synced customer {entity_id} from QuickBooks")
                    return {
                        "status": "success",
                        "tenant_id": tenant_id,
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "operation": operation,
                        "result": result,
                    }

            elif entity_type == "Invoice":
                # One-way sync: QB → Pilot for Trades only (deferred to post-MVP)
                logger.info(
                    f"Invoice sync not yet implemented (entity_id: {entity_id})"
                )
                return {
                    "status": "success",
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "operation": operation,
                    "result": "skipped_invoice_not_implemented",
                }

            else:
                # QB-H1 Task 6: explicit guard for unhandled entity types.
                # Log a WARNING and return cleanly — no exception → no Celery
                # retry storm. The event is logged for observability; no sync
                # is queued.
                logger.warning(
                    "QB webhook entity type %r not handled — "
                    "event logged, no sync queued",
                    entity_type,
                )
                return {
                    "status": "success",
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "operation": operation,
                    "result": "skipped_unknown_entity",
                }

    except Exception as exc:
        logger.error(f"Error syncing {entity_type} {entity_id}: {exc}", exc_info=True)

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@celery_app.task(name="sync_invoice_to_qb", bind=True, max_retries=3)
def sync_invoice_to_qb_task(self, tenant_id: str, invoice_id: str) -> dict:
    """
    Sync a single Pilot for Trades invoice to QuickBooks (proactive push).

    Triggered when an invoice is created or finalized in Pilot for Trades.
    Pushes invoice + line items to QB, stores mapping for future syncs.

    Args:
        tenant_id: String representation of tenant UUID
        invoice_id: String representation of invoice UUID

    Returns:
        Dict with sync results:
            - status: "success" or "error"
            - invoice_id: Pilot invoice ID that was synced
            - qb_invoice_id: QuickBooks invoice ID
            - qb_sync_token: QuickBooks SyncToken

    Raises:
        Retry: If sync fails (max 3 retries with exponential backoff)
    """
    from core.db import engine as db_engine

    tenant_uuid = uuid.UUID(tenant_id)
    invoice_uuid = uuid.UUID(invoice_id)

    try:
        with Session(db_engine) as db:
            sync = QuickBooksSync(tenant_uuid, db)

            # Sync invoice to QuickBooks
            import asyncio

            qb_invoice = asyncio.run(sync.sync_invoice_to_qb(invoice_uuid))

            return {
                "status": "success",
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "qb_invoice_id": qb_invoice.get("Id"),
                "qb_sync_token": qb_invoice.get("SyncToken"),
                "synced_at": datetime.now(UTC).isoformat(),
            }

    except ValueError as e:
        # Validation error - don't retry
        return {
            "status": "error",
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "error": str(e),
            "error_type": "validation_error",
        }

    except Exception as e:
        # Network error, QB API error, etc - retry
        retry_countdown = 60 * (3**self.request.retries)

        try:
            raise self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            return {
                "status": "error",
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "error": str(e),
                "error_type": "max_retries_exceeded",
                "retries": self.request.retries,
            }


@celery_app.task(name="sync_payment_to_qb", bind=True, max_retries=3)
def sync_payment_to_qb_task(self, tenant_id: str, payment_id: str) -> dict:
    """
    Sync a single Pilot for Trades payment to QuickBooks (proactive push).

    Triggered when a payment is recorded in Pilot for Trades.
    Pushes payment + linked invoice reference to QB, stores mapping for future syncs.

    Args:
        tenant_id: String representation of tenant UUID
        payment_id: String representation of payment UUID

    Returns:
        Dict with sync results:
            - status: "success" or "error"
            - payment_id: Pilot payment ID that was synced
            - qb_payment_id: QuickBooks payment ID
            - qb_sync_token: QuickBooks SyncToken

    Raises:
        Retry: If sync fails (max 3 retries with exponential backoff)
    """
    from core.db import engine as db_engine

    tenant_uuid = uuid.UUID(tenant_id)
    payment_uuid = uuid.UUID(payment_id)

    try:
        with Session(db_engine) as db:
            sync = QuickBooksSync(tenant_uuid, db)

            # Sync payment to QuickBooks
            import asyncio

            qb_payment = asyncio.run(sync.sync_payment_to_qb(payment_uuid))

            return {
                "status": "success",
                "tenant_id": tenant_id,
                "payment_id": payment_id,
                "qb_payment_id": qb_payment.get("Id"),
                "qb_sync_token": qb_payment.get("SyncToken"),
                "synced_at": datetime.now(UTC).isoformat(),
            }

    except ValueError as e:
        # Validation error - don't retry
        return {
            "status": "error",
            "tenant_id": tenant_id,
            "payment_id": payment_id,
            "error": str(e),
            "error_type": "validation_error",
        }

    except Exception as e:
        # Network error, QB API error, etc - retry
        retry_countdown = 60 * (3**self.request.retries)

        try:
            raise self.retry(exc=e, countdown=retry_countdown)
        except self.MaxRetriesExceededError:
            return {
                "status": "error",
                "tenant_id": tenant_id,
                "payment_id": payment_id,
                "error": str(e),
                "error_type": "max_retries_exceeded",
                "retries": self.request.retries,
            }
