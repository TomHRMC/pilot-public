# 🛡️ Sync & Idempotency: QuickBooks Reliability Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "Zero Duplicate" Mandate

The core success metric for all integrations is **zero duplicate data entries**. The Integrations Lead must ensure that any network retry or concurrent request does not result in redundant financial records.

## 2. Idempotency Key Implementation

All non-idempotent HTTP methods (**POST**, **PATCH**) targeting QuickBooks-related resources must implement a mandatory idempotency header:

* **Header Name**: `X-Idempotency-Key`.
* **Format**: Version 4 UUID.
* **Scope**: Unique per user/request attempt.

### Server-Side Enforcement (FastAPI)

1. **Persistence**: Store keys in the high-availability **Redis cache**.
2. **Expiration**: Keys must expire after **24 hours** to allow for long-duration retries while preventing database bloat.
3. **Conflict Handling**:
* **Identical Retry**: Return the original cached `200 OK` or `201 Created` response.
* **Payload Mismatch**: Return `422 Unprocessable Entity` if the same key is used with a different request body.
* **Race Condition**: Return `409 Conflict` if a request with the same key is already being processed.



## 3. Bi-Directional Sync Constraints

When performing a sync, the agent must adhere to the **Sync Direction Rules**:

| Entity | Master System | Logic Constraint |
| --- | --- | --- |
| **Customers** | User Choice | Check for modified versions in both systems before overwriting. |
| **Quotes** | Pilot for Trades | Sync as "Estimates" in QuickBooks. |
| **Invoices** | QuickBooks | Treat QuickBooks as the source of truth for final billing. |
| **Payments** | QuickBooks | Pilot for Trades should be read-only for payment status. |

## 4. Error Handling (RFC 7807)

Integration failures must never be silent. The agent must return structured error responses including:

* **type**: A link to specific documentation (e.g., `.../errors/sync-conflict`).
* **instance**: A unique request ID for log correlation (e.g., `req_abc123`).
* **errors**: A dictionary of validation failures for easy debugging.

## 5. Security & Token Rotation

* **Encryption**: All QuickBooks tokens must be **encrypted at rest** using AWS KMS.
* **Rotation**: Implement a background task to refresh tokens automatically; do not wait for a user to trigger a sync to check for expiration.
