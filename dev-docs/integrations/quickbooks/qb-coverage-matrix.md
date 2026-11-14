# QuickBooks Coverage Matrix — QB ↔ P4T Entity Mapping

**Published**: 2026-08-28 (QB-H1)
**Verifier**: PPE (Pilot Python Engineer)
**Source**: `batch-qb-h1-design.md` Appendix 1, verified against code
**Status**: Verified 2026-08-28 / PPE

---

## 1. Object Matrix

Each row verified against the actual codebase (`services/quickbooks_sync.py`, `tasks/quickbooks_sync.py`, `api/routes/integrations.py`, `api/routes/webhooks.py`).

| QB object | P4T entity | Synced? | Direction | Mechanism (file) | Fields mapped | Known gaps | Verified |
|---|---|---|---|---|---|---|---|
| Customer | `customer` | ✅ | Bi-directional | `services/quickbooks_sync.py` (`sync_customer_from_qb` / `to_qb`, `sync_all_customers_from_qb`); webhook → `sync_quickbooks_entity_task` | DisplayName↔display_name, GivenName↔first_name, FamilyName↔last_name, CompanyName↔company_name, PrimaryEmailAddr.Address↔email, PrimaryPhone↔mobile_phone, Notes↔notes, Active↔is_active, SyncToken↔external_version_token, MetaData→conflict snapshots | No BillAddr/ShipAddr; duplicate-DisplayName crash → **fixed QB-H1 Task 5** (dedup suffix + conflict row); no delete/deactivate propagation beyond `Active`; QB→P4T paged sync only via Beat (30-min) + webhook | ✅ 2026-08-28 / PPE |
| Invoice + lines | `invoice` + `invoice_line` | ✅ push | P4T→QB only | `services/quickbooks_sync.py` (`sync_invoice_to_qb`); task: `tasks/quickbooks_sync.py::sync_invoice_to_qb_task` | CustomerRef (via mapping), Line[].Amount/Description/ItemRef (via `qco_line_type.qb_item_name_hint`, **fallback item `"1"`**), Qty, UnitPrice (cents→dollars), CustomerMemo↔customer_notes, DocNumber↔invoice_number, TxnDate↔issued_at, DueDate↔due_at | No QB→P4T pull; no update-after-push audit; TxnTaxDetail unverified (not mapped — tax is computed P4T-side); DocNumber uses P4T invoice_number (QB may renumber) | ✅ 2026-08-28 / PPE |
| Payment | `payment` | ✅ push | P4T→QB only | `services/quickbooks_sync.py` (`sync_payment_to_qb`); task: `tasks/quickbooks_sync.py::sync_payment_to_qb_task` | CustomerRef (via invoice mapping — **note**: `CustomerRef.value` is set to `payment.invoice_id` not the customer's QB ID — potential bug), TotalAmt (cents→dollars), Line[].LinkedTxn (TxnId=invoice QB ID, TxnType="Invoice") | SD-2 refund (negative payment) → QB CreditMemo/RefundReceipt **unmapped**; QB-side payments never pulled; `CustomerRef.value` set to `invoice_id` not `customer_id` — follow-on fix candidate | ✅ 2026-08-28 / PPE |
| Estimate | `quote` | ❌ | — | none | — | PRD §3.9 names "Estimate/Invoice"; quote→estimate sync absent → **follow-on (QB-H2)** | ✅ 2026-08-28 / PPE |
| Credit Memo / Refund | `payment` (negative) | ❌ | — | none | — | **Follow-on (QB-H2)** — pairs with SD-2 refund model | ✅ 2026-08-28 / PPE |
| Item (Products & Services) | `qco_line_type` (+ pricebook) | ⚠️ partial | mapping-only | `services/quickbooks_sync.py` (`_resolve_qco_line_type_to_qb_item`) | `qb_item_name_hint` → QB Item lookup; fallback `"1"` | No item catalog sync; hint-based resolution fragile → **follow-on (QB-H2)** | ✅ 2026-08-28 / PPE |
| Tax Agency / Rate | `tax_rate_version.external_tax_agency_id` | ⚠️ field-only | mapping field exists | (batch 1c migration) | `external_tax_agency_id` holds QB agency id | Invoice-push tax detail (TxnTaxDetail) not mapped → **follow-on audit (QB-H2)** | ✅ 2026-08-28 / PPE |
| Attachment | `job_attachment` / invoice docs | ❌ | — | none | — | Accepted gap (S3-only) — document rationale | ✅ 2026-08-28 / PPE |
| Class / Department | — | ❌ | — | none | — | No P4T concept; likely N/A for electrical-contractor target — document | ✅ 2026-08-28 / PPE |
| Webhook events | all entities | ⚠️ customer-only | QB→P4T | `api/routes/webhooks.py` intake (entity-agnostic) → `sync_quickbooks_entity_task` (customer only) | realm→tenant via `app_service.external_account_id` | Non-customer entities silently dropped → **guard fixed QB-H1 Task 6** (WARNING log + clean return); prod realm lookup broken until QB-H1 Task 1 lands | ✅ 2026-08-28 / PPE |
| Sync telemetry | `integration_sync_log` / `_conflict` / `webhook_event` | ✅ | — | tasks + routes | records_processed/failed, conflict snapshots, auto-expiry | `intuit_tid` gaps in OAuth paths → **fixed QB-H1 Task 3** | ✅ 2026-08-28 / PPE |
| Connection health | `integration_credential` | ⚠️ | — | `tasks/quickbooks_token_refresh.py` + `api/routes/integrations.py` (`_refresh_qbo_token_impl`) | tokens (encrypted), expires_at, last_refresh_at, connection_status | Transient blips killed connection; no owner notification → **fixed QB-H1 Task 2** (transient/permanent classification + `qb_connection_expired` notification) | ✅ 2026-08-28 / PPE |

---

## 2. Triage Table — Tom's QB-H2 Approval Gate

### In-Batch Fixes ✅ (QB-H1)

| Fix | Task | Scope note |
|---|---|---|
| `display_name` dedup | Task 5 | Pre-check collision → suffix `(QB <Id>)` + `display_name_dedup` conflict row |
| Webhook unhandled-entity guard | Task 6a | WARNING log + clean return for non-customer entity types |
| `app_service*` registry restoration | Task 1 | Migration + seed ownership; prod recovery path; `intuit`→`quickbooks` canonization |
| OAuth refresh classification | Task 2 | Transient (5xx/network) vs permanent (invalid_grant/400/401); owner notification on permanent |
| `intuit_tid` CloudWatch extension | Task 3 | Arg-style logging on all QB HTTP paths (token refresh, OAuth callback, API calls) |
| Conflict email to owner proof | Task 4 | Verified `queue_conflict` resolves to tenant owner's email (existing behavior confirmed) |

### Follow-On Candidates (QB-H2 — each ≥ half a batch)

| Candidate | Scope note |
|---|---|
| Quote→Estimate sync | PRD §3.9 names "Estimate/Invoice"; quote→estimate push absent. Needs `sync_estimate_to_qb` service + task + mapping. |
| Refund/CreditMemo mapping | SD-2 negative-payment model → QB CreditMemo/RefundReceipt. Pairs with SD-2 refund architecture. |
| QB→P4T invoice/payment pull | Currently push-only. Webhook already routes Invoice/Payment events but handler returns `skipped_invoice_not_implemented`. Needs pull logic + conflict detection. |
| Item sync vs `qco_line_type` hints | `_resolve_qco_line_type_to_qb_item` uses fallback `"1"` — fragile. Needs Item catalog sync or robust lookup. |
| `TxnTaxDetail` audit | Invoice push doesn't map tax detail. Tax is computed P4T-side; QB-side tax agency/rate mapping via `external_tax_agency_id` exists but is unverified in push. |
| `payment` `entity_type` row | MCP confirmed: `entity_type` table has `customer`, `invoice`, `quote` — **no `payment` row**. Payment sync mappings use `entity_type_code="payment"` which may FK-fail if no `payment` entity_type exists. Verify impact. |
| Class/Department tracking | No P4T concept. Likely N/A for electrical-contractor target (Mike persona). Document and close. |
| Attachment sync | Accepted gap (S3-only). Document rationale and close. |
| `CustomerRef.value` bug in payment push | `sync_payment_to_qb` sets `CustomerRef.value = payment.invoice_id` (should be the customer's QB ID). Low-priority fix — QB may resolve via LinkedTxn. |

---

## 3. Connection Health / Telemetry Summary (QB-H1 Tasks 2–3)

### Task 2 — OAuth Refresh Robustness

**Before**: Any exception during token refresh marked the connection `expired` — a transient Intuit 5xx or network blip killed a healthy connection with no owner notification.

**After**: Error classification in both the Celery beat task (`refresh_quickbooks_tokens_task`) and the async route (`_refresh_qbo_token_impl`):
- **Transient** (5xx / `httpx.TransportError` / timeout): log WARNING, leave `connection_status="active"`, count `transient_failed`. The next beat cycle (30 min) retries.
- **Permanent** (`invalid_grant` / 400 / 401): mark `expired` + enqueue `qb_connection_expired` notification (email) to the tenant owner via `NotificationEvent` + `NotificationOutbox`.

**Dead code removed**: The sync `_refresh_qbo_token_impl` stub (lines 396–449, raised `NotImplementedError`) was deleted. Exactly 1 `_refresh_qbo_token_impl` remains (the async twin).

**`print()` → `logger`**: All `print()` calls in `refresh_quickbooks_tokens_task` replaced with structured `logger` calls.

### Task 3 — `intuit_tid` CloudWatch Extension

**Before**: `intuit_tid` was logged only in `services/quickbooks_sync.py` (5 call sites: customer CRUD, query, fetch, invoice push, payment push). The OAuth token paths (refresh + callback exchange) lacked it.

**After**: `intuit_tid` is now logged (arg-style `%s` interpolation, never f-strings) on every QB HTTP path:
- `tasks/quickbooks_token_refresh.py::_refresh_access_token` — token refresh call
- `api/routes/integrations.py::_exchange_code_for_tokens` — OAuth callback token exchange
- `api/routes/integrations.py::_refresh_access_token` — route-level token refresh call
- `services/quickbooks_sync.py` — 5 existing call sites (unchanged)

**Total `intuit_tid` log sites**: 8 (5 existing + 3 new).

---

## 4. `entity_type` Vocabulary (MCP-verified)

The `entity_type` table contains: `customer`, `customer_communication`, `invoice`, `job`, `quote`, `site`, `tenant`.

**Notably absent**: `payment`. The `sync_payment_to_qb` method creates mappings with `entity_type_code="payment"`, which may FK-fail if no `payment` entity_type row exists. This is a follow-on candidate for QB-H2.

---

## 5. Canonical `provider_code` Decision

**Canonical `provider_code` is `quickbooks`** (not `intuit`).

Evidence: ~30 application call sites query `provider_code == "quickbooks"` (sync service, routes, tasks, webhook realm lookup). `intuit` appears only in the 2026-05-31 migration file. Canonizing `intuit` would require a 30-site refactor with zero product value and high regression risk.

The QB-H1 migration re-points the one dev global row from `intuit` to `quickbooks` and retires the orphan `intuit` provider row. This is a deliberate, evidence-based deviation from the launch-plan card's parenthetical — flagged for Tom's visibility.