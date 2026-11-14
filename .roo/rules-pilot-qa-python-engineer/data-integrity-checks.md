# 🕵️ Data Integrity: Sync Verification & Anti-Duplication Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "Zero-Duplicate" Mandate

The Test Engineer is responsible for verifying that no operation—regardless of network failure, user error, or system retry—results in duplicate records within the database or QuickBooks Online. This is a critical success metric for the MVP.

## 2. Mandatory Idempotency Tests

To validate the **`X-Idempotency-Key`** implementation, the following test cases must be automated in the **Pytest** suite:

* **Immediate Retry**: Send an identical `POST /v1/quotes` request with the same idempotency key within 50ms of the first request; verify a `409 Conflict` or the original `201 Created` response is returned.
* **Delayed Retry**: Send the same request after the first has completed; verify the server returns the **cached response body** and does not create a second record.
* **Payload Mismatch**: Send a second request with the same key but a different JSON body; verify the system returns a `422 Unprocessable Entity`.
* **Cache Expiration**: Verify that after **24 hours**, the idempotency key is purged from Redis and a new request with that key is treated as a fresh transaction.

## 3. QuickBooks Sync Integrity Checks

Integration tests must simulate the "Real World" of spotty job-site connectivity:

* **Interrupted Sync**: Simulate a network timeout during an `Invoice.Create` call to QuickBooks; verify the **Sync History** table accurately reflects the "Unknown" state and that subsequent sync attempts do not create a duplicate invoice.
* **Race Condition Test**: Trigger a manual sync while a background **Celery worker** is already syncing the same company; verify the **Distributed Lock** prevents concurrent writes to the same QuickBooks entity.
* **Mapping Validation**: Verify that every Pilot for Trades `quote_id` maps 1:1 with a QuickBooks `EstimateId` in the **Sync Mappings** table.

## 4. Database Consistency Checks

The Test Engineer must implement "Sanity Check" scripts that run daily in the **Staging/Production** environments:

* **Uniqueness Audit**: Query the `Quotes` and `Customers` tables for any records sharing identical external `quickbooks_id` values.
* **Orphaned Record Check**: Identify any **Quote Line Items** that do not have a valid parent `quote_id`.
* **Vector Index Integrity**: Verify that every record in `conversation_messages` has a corresponding embedding in **pgvector** to ensure the Voice AI context remains reliable.

## 5. Failure Recovery Tests

* **Dead Letter Queue (DLQ) Verification**: Purposefully fail a **QuickBooks Sync Task** (e.g., via invalid tokens) and verify the task is moved to the **SQS DLQ** for manual inspection rather than silently disappearing.
* **Alembic Rollback Test**: Execute a database migration and immediately perform a `downgrade -1`; verify that all table constraints and unique indexes are restored correctly.
