> **♻️ RESTORED 2026-08-20.** Restored from `dev-docs/db-design/aevofab-db-backup-md-files/aevofab-db-process-v2.6h.md` per Tom's decision — the pilot-named copy was missing while registry §4, `mvp-arch.md` §(schema reference), `pilot-operations.md`, root `README.md`, and architect mode instructions all referenced it. Rebranded (AevoFab → Pilot for Trades; `aevofab_master` → `pilot_master` per migration `5089dc9fc2e5`).
>
> **⚠️ CURRENCY NOTE**: This text describes the **v2.6h-era** database. It is the design-history companion to [`pilot-db-schema-v2.6h.json`](pilot-db-schema-v2.6h.json) — principles (snapshotting, outbox pattern, idempotency, sync conflict model) still hold, but it predates every post-v2.6h change (Charter program columns, `tenant_site`, `invoice_signoff`, CE-1 payment columns, DB-MGMT-1 env-aware seeds, etc.). **Batch DB-RECON-1 (launch plan §2.3, NEXT UP) will fully reconcile the dev DB against the master JSON and rewrite this document to match the current schema.** Until then, treat table/column specifics as historical and verify against the live DB via `postgres-local` MCP.

---

# Pilot for Trades — PROCESS (v2.6h Detailed Playbook)

> **Purpose.** This is the end-to-end operational playbook for the Pilot for Trades v2.6h database and API. It defines the state machine transitions, background worker responsibilities, external sync logic (QuickBooks/SSO), AI Voice telemetry, and data integrity guardrails required for development.
> **Schema Baseline.** Matches `pilot-db-schema-v2.6h.json` (PostgreSQL 17 with `vector`, `citext`, `btree_gist`).

---

## 1. Identity, Access, & SSO

### 1.1 Tenant Signup & User Identity

**Data Touches:** `tenant`, `user`, `user_endpoint`, `user_sso_identity`, `auth_password_history`.

* **Flow:** When a tenant signs up, the system creates the `tenant`, the initial `user`, and a `user_endpoint` for their email.
* **Sync Trigger:** The `sync_user_email_from_endpoint` trigger automatically updates `user.email` whenever a `user_endpoint` (where `channel='email'` and `is_primary=true`) is inserted, updated, or deleted.
* **SSO Flow:** Users can bypass passwords using `sso_provider` (Google, Microsoft). The callback maps the provider's unique ID to `user_sso_identity.provider_user_id` to establish the session without relying solely on email matching.

### 1.2 MFA & Password Policies

* **Enforcement:** Evaluated at login. If `tenant.mfa_enforced` is true, the system checks `user.preferred_mfa_channel` ('email', 'sms', or 'totp') and generates an `auth_mfa_otp` record.
* **Password Guard:** `auth_password_history` prevents password reuse based on the `password_policy.history_depth` setting.

---

## 2. Integrations & Sync Engine (QuickBooks / External ERPs)

This section manages bi-directional data flow between Pilot for Trades and external systems, ensuring data consistency without duplicates.

### 2.1 Entity Mapping & Sync Preferences

**Data Touches:** `integration_sync_mapping`, `integration_credential`.

* **Flow:** When a Pilot entity (e.g., `customer` or `invoice`) is created or updated, the system checks `integration_sync_mapping` for an existing `external_id` (e.g., QuickBooks Customer ID 59).
* **Conflict Strategy:** Handled by `sync_preference` (`pilot_master`, `external_master`, or `bi_directional`). `external_version_token` (like QB's SyncToken) is used for optimistic concurrency.

### 2.2 Conflict Resolution & Run Logs

**Data Touches:** `integration_sync_conflict`, `integration_sync_log`.

* **Collisions:** If a bi-directional sync detects simultaneous changes, it creates an `integration_sync_conflict` row with `status='pending'`, storing `internal_payload` and `external_payload` snapshots. The tenant UI displays a "Requires Attention" widget to resolve it manually.
* **Observability:** Every background sync job writes to `integration_sync_log`, capturing `records_processed`, `records_failed`, and detailed execution metrics in `contextdata`.

---

## 3. Job Profitability & Expense Ledger

Pilot tracks exact profitability by comparing invoiced revenue against immutable snapshots of labor and material costs.

### 3.1 Job Costing & Markups

**Data Touches:** `job`, `job_expense`, `job_time_entry`, `tenant_markup_version`.

* **Labor Costs:** Technicians clocking in generate `job_time_entry` records. The `hourly_rate_cents` is snapshotted at that moment, calculating `total_cost_cents` permanently.
* **Material Expenses:** Out-of-pocket costs are recorded in `job_expense`. The system queries the `tenant_markup_version` active at `incurred_at` (using GiST exclusion constraints to ensure no overlap) to apply the correct `markup_pct` or `markup_amt_cents`, resulting in the final `billable_cents`.
* **Profitability Rollup:** Background workers periodically recalculate `job.actual_labor_cost_cents`, `job.actual_material_cost_cents`, and `job.actual_profit_cents` (Revenue minus Costs).

---

## 4. Notifications, Email Generation & Webhooks

### 4.1 Internal Notification Engine (Email/SMS)

**Data Touches:** `notification_event`, `notification_outbox`, `notification_template`, `notification_delivery_attempt`.

* **Event Trigger:** A business action (e.g., Quote Approved) creates a `notification_event`.
* **Template Rendering:** The system looks up `notification_template` matching the event, channel, and user locale, injecting `contextdata` variables.
* **Outbox Worker:** A queue worker polls `notification_outbox` where `status='pending'` and `next_attempt_at <= now()`. It records a `notification_delivery_attempt` capturing the provider's HTTP status and error message.
* **Backoff:** If an attempt fails but `retryable=true`, the worker sets `next_attempt_at` using exponential backoff.

### 4.2 Outbound Webhooks (Tenant APIs)

**Data Touches:** `webhook_endpoint`, `webhook_event`, `webhook_delivery_attempt`.

* **Flow:** Tenants can register URLs in `webhook_endpoint` with an `event_filter` (e.g., `["invoice.paid"]`).
* **Delivery:** Similar to emails, `webhook_event` payloads are queued. `webhook_delivery_attempt` logs the exact `request_header` (useful for HMAC signature debugging) and `response_body` from the tenant's server.

---

## 5. Quotes, Change Orders, & Snapshot Principle

### 5.1 Immutable Financial Snapshots

**Data Touches:** `quote_line`, `change_order_line`, `quote_version`.

* **The Snapshot Principle:** Financial records (`unit_price_cents`, `tax_rate_pct`, `tax_amount_cents`) are hardcoded directly onto the lines at the moment of creation. They do not dynamically update if pricebooks change later, preserving historical accuracy.
* **Trigger Math:** `recalc_quote_totals_tg` and `recalc_change_order_totals_tg` fire on any line insert/update/delete to keep the parent header totals perfectly aligned with the lines.

### 5.2 Public Links & Approvals

**Data Touches:** `quote_public_link`, `quote_public_link_contact_action`, `quote_acceptance`.

* **Flow:** When a quote is sent, a `quote_public_link` is generated containing a `token_hash` and `max_uses`.
* **Tracking:** Customer actions (viewing, messaging, approving) are logged in `quote_public_link_contact_action`. Approval generates an immutable `quote_acceptance` record mapping back to a specific `quote_version_id`.

---

## 6. AI Voice Engine & Vector Search

Pilot uses Ollama/Whisper pipelines for field technicians. The DB manages context windows and vector semantic search.

### 6.1 Session Management & Telemetry

**Data Touches:** `conversation_session`, `conversation_message`, `voice_command_log`.

* **Context Isolation:** AI sessions are isolated via `tenant_id` and `user_id`. `conversation_session` maintains a `context_summary` and `context_window_json` to resolve pronouns (e.g., knowing "this quote" means the active quote ID).
* **Embeddings:** Every `conversation_message` stores a `vector(1024)` embedding for RAG (Retrieval-Augmented Generation). Queried using pgvector's HNSW indexes.
* **Observability:** `voice_command_log` acts as the telemetry layer, tracking `whisper_latency_ms`, `ollama_latency_ms`, and the specific `intent_detected` to monitor SLA performance.

---

## 7. API Sketch & Idempotency Rules

* **Idempotency Keys (`idempotency_key`):** All state-mutating requests (POST/PATCH) MUST accept an `Idempotency-Key` header. The system locks the key `status='in_progress'`, executes the logic, stores the `response_body` and `response_hash`, and marks it `succeeded`. Duplicate requests within 24 hours return the cached response.
* **Monetary Math:** All currency fields are strictly integers representing cents (`unit_price_cents`, `total_cents`).

---

## 8. Background Jobs Catalog

| Job Name | Domain | Responsibility |
| --- | --- | --- |
| **Outbox Dispatcher** | Notifications | Polls `notification_outbox`; handles exponential backoff; updates `notification_delivery_attempt`. |
| **Webhook Delivery** | Integrations | Dispatches `webhook_event` payloads to `webhook_endpoint` URLs; signs with HMAC secrets. |
| **External Sync Worker** | Integrations | Runs bi-directional checks against QuickBooks/ERPs; logs to `integration_sync_log`; queues conflicts. |
| **Profitability Rollup** | Jobs | Sweeps `job_expense` (where `is_billable=true` and `invoice_line_id IS NULL`) and `job_time_entry` to recalculate job actuals. |
| **Price Spike Monitor** | Suppliers | Analyzes `supplier_item_price` updates against thresholds; enqueues `notification_event` alerts. |
| **AI Session Pruner** | AI / Voice | Sweeps `conversation_session` where `expires_at < now()`, generating final summaries and freeing active memory. |
