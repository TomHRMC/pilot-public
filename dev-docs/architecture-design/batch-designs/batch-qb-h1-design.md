# Batch Design: QB-H1 — QuickBooks Coverage Audit + Sync Hardening

**Version**: 1.0
**Date**: 2026-08-28
**Author**: Pilot Architect
**Batch**: QB-H1 (Phase 1 — launch plan §1.1 Ord 5; card §3.5; **§7 founder-gate item**)
**Owner**: Pilot Python Engineer (executing); Tom (prod verification after deploy; follow-on triage approval gate)
**Prompt**: `batch-qb-h1-python-engr-prompt.md`
**Source plan**: `pilot-launch-plan.md` §3.5 (Part 1 coverage audit + Part 2 hardening; out-of-scope: Tom-authored QB dev reference doc → 6b downtime list)
**Estimated session**: 5–6 hours (sequenced registry-first; Tasks 1–2 are the prod-critical path — see §G Q5 for the declared flex protocol)
**Cost impact**: **$0** — no new AWS resources, no new services, no new third-party APIs (infrastructure-constraints §1: no founder cost review required)

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `pilot-launch-plan.md` | §1.1 Ord 5 (QB-H1, deps: none); §3.5 full card (Parts 1–2, out-of-scope); §7 gate row "coverage matrix published; sync hardened"; §6b downtime list (receives the dev-ref doc); PLAT-DEBT ⤴ row (`customer.display_name` uniqueness — moved to QB-H1) | 2026-08-28 |
| `mvp-prd.md` | §3.9 QuickBooks Integration (8 feature rows: bi-directional customer sync, sync dashboard/queue visibility, bilateral conflict UI, invoice & payment push — *"as Estimate/Invoice and Payment records"*, tax agency mapping via `external_tax_agency_id`, conflict notification to owner, financial-delta callout, in-flight sync indicator) | 2026-08-28 |
| `pilot-architect-methods.md` | §2.1.1 complete DB-object verification; §3 Standard Architecture Design Workflow (A–G); §3.0.1 inclusions compliance | 2026-08-28 |
| `backend/python-engr-std-prompt-inclusions.md` | Full file (943 lines) — all REQUIRED/CONDITIONAL sections; §14 vendor-deselected Phase 2 gate; §20 Seed Data Rollout (**triggered** — new `notification_type` + templates + `app_service*` seed ownership) | 2026-08-28 |
| `backend/services/quickbooks_sync.py` | Full service surface: `get_access_token` (5-min refresh window via `_refresh_qbo_token_impl`), `_get_app_service_id`, `detect_conflict`, `queue_conflict` (sends `qb_sync_conflict` notification), `sync_customer_from_qb`/`to_qb`, `sync_all_customers`, `sync_invoice_to_qb`, `sync_payment_to_qb`, `_resolve_qco_line_type_to_qb_item` (fallback item `"1"`); `intuit_tid` logged at 5 call sites (lines 570, 659, 772, 887, 1014); **no estimate/credit-memo/refund sync exists** | 2026-08-28 |
| `backend/api/routes/integrations.py` | OAuth connect (creates tenant `app_service` row `provider_code="quickbooks"` — FK-fails when provider row absent → **prod connect broken**); **dead sync `_refresh_qbo_token_impl` stub (lines 396–449, raises `NotImplementedError`)** shadowed by the async twin (452–529); async refresh marks `connection_status="expired"` on ANY exception (transient-fragile); conflict queue endpoints (A49/A50) with `qb_conflict.view`/`resolve` RBAC | 2026-08-28 |
| `backend/tasks/quickbooks_token_refresh.py` | Beat task (30 min): refreshes tokens expiring <5 min; marks `expired` on ANY exception (a 5xx/network blip kills the connection); uses `print()` not `logger` (lines 141, 154); no `intuit_tid`; no owner notification on expiry | 2026-08-28 |
| `backend/tasks/quickbooks_sync.py` | Celery tasks: `sync_quickbooks_customers`, `sync_all_tenants_customers` (Beat), `sync_customer_to_qb`, `sync_quickbooks_entity` (**webhook entry — handles `customer` only**), `sync_invoice_to_qb`, `sync_payment_to_qb` | 2026-08-28 |
| `backend/api/routes/webhooks.py` | CloudEvents intake (entity-agnostic parse `qbo.<entity>.<op>.v1`); HMAC verify; `get_tenant_by_realm_id` = `AppService.external_account_id == realm_id AND provider_code == "quickbooks"` (**0 rows in prod → every webhook is `tenant_not_found`**); `trigger_sync_task` → `sync_quickbooks_entity_task` | 2026-08-28 |
| `backend/core/quickbooks_webhook.py` | HMAC signature verifier presence confirmed | 2026-08-28 |
| `backend/tasks/auto_expire_qb_conflicts.py` | Daily 03:30 UTC auto-expiry; `qb_auto_expire_days` via `get_effective_setting`; `qb_conflict_pre_warning` notification path | 2026-08-28 |
| `backend/migrations/versions/2026_05_31_2216-dd4ed7ed5f3b_seed_missing_lookup_tables_batch_1.py` | Lines 342–410: canonical trio INSERTs (`accounting` / `intuit` / global NULL-tenant `QuickBooks Online` row with `provider_code='intuit'`); `intuit` is referenced **nowhere in application code** (grep-verified — migration file only) | 2026-08-28 |
| `backend/migrations/scripts/seed_core.py` | Dict-driven Group A patterns (`CODE_TABLES`, `TENANT_NULLABLE_CODE_TABLES`); stale NOTEs at lines 118–120 + 2381–2382 ("rows already exist from Alembic migrations — NOT seeded here. Seeding them caused FK violations in test_quickbooks_sync.py"); `notification_type` dict owns `qb_sync_conflict` (line 511); inspect manifest lines 2995–2999; help text lines 3305–3306 (**stale**: "provider — 1 row: quickbooks_online") | 2026-08-28 |
| `backend/migrations/scripts/seed_platform.py` | Group B owns `notification_template` rows: template-copy dict + idempotent upsert loop keyed `(code, channel)` with `tenant_id IS NULL` (lines 610–950); SD-3 precedent: 6 types × 3 channels | 2026-08-28 |
| `backend/README-seed-data.md` | §8.1 exclusion row: "`app_service`, `app_service_provider` — Alembic-managed with FK references in `integration_sync_mapping`; seeding causes QB test teardown failures"; §7 DELETE-safety rule; §3 Group A–D ownership model; §4 current seed state | 2026-08-28 |
| `backend/tests/conftest.py` | `test_app_service` fixture (lines 1270–1288): creates tenant-scoped row `provider_code="quickbooks"` — FK-requires the provider row; `test_qco_line_type` fixture exists | 2026-08-28 |
| QB test files | `test_quickbooks_sync.py` (`qb_app_service` get-or-create fixture, mocked-httpx sync tests), `batch_b8/test_a49_a50_qb_conflict_endpoints.py`, `batch_1e/test_task_1e4_qb_sync_notifications.py`, `batch_b19/test_qb_invoice_push.py` — the collision cohort for the §8.1 teardown fix | 2026-08-28 |
| `postgres-local` MCP (9 queries) | ① Trio columns: all four audit cols present; `app_service` PK `id`, FKs `category_code→app_service_category(code)`, `provider_code→app_service_provider(code)`, `tenant_id→tenant(id)`; **no UNIQUE on the natural key** ② Dev rows: category `accounting`; providers `intuit` + `quickbooks`; `app_service` 2 rows (global `intuit` `ffa5ec40-…`; tenant-0001 `quickbooks` realm `1234567890123456`) ③ `uq_customer_tenant_display_name UNIQUE (tenant_id, display_name)` ④ `integration_credential`/`_mapping`/`_log`/`_conflict` columns (incl. `connection_status`, `secret_json`, `expires_at`, `last_refresh_at`, `external_version_token`, `conflict_subtype`) ⑤ alembic head `58c3ad26129f` ⑥ `entity_type` seeded: `customer`, `invoice`, `quote` only — **no `payment` row** ⑦ `notification_type`: only `qb_sync_conflict` + `qb_conflict_pre_warning` — **no connection-expiry type**; both have email/in_app/push system templates ⑧ `notification_type` PK = `code`; `notification_template` PK = `id` ⑨ `qco_line_type.qb_item_name_hint` + `tax_rate_version.external_tax_agency_id` confirmed | 2026-08-28 |
| `batch-test-uplift-1a-design.md` | Design-doc format exemplar (header block, A–G, ratchet/§G patterns) | 2026-08-28 |

---

## B. Migration Plan

One Alembic **data** migration (blank revision + raw `op.execute()`; no DDL, no new columns/tables). It is the **prod recovery path** for the `app_service*` registry (prod has 0 rows — schema-restore + `alembic stamp` never executed `dd4ed7ed5f3b`'s INSERTs) and the dev reconciliation of the `intuit`/`quickbooks` provider split.

### B.1 Pre-Migration Verification (MCP state at design time)

| Check | Result | Source |
|---|---|---|
| Dev alembic head | `58c3ad26129f` | `postgres-local` MCP 2026-08-28 |
| `app_service` constraints | PK `id`; FK `category_code→app_service_category(code)`; FK `provider_code→app_service_provider(code)`; FK `tenant_id→tenant(id)`; **no UNIQUE constraint** → idempotent INSERT needs `WHERE NOT EXISTS` | `postgres-local` MCP 2026-08-28 |
| `app_service_category` / `app_service_provider` | PK `code` → `ON CONFLICT DO NOTHING` safe | `postgres-local` MCP 2026-08-28 |
| Dev trio rows | category `accounting`; providers `intuit`, `quickbooks`; global row `ffa5ec40-3723-45f1-8b28-925ac45bd618` (`intuit`); tenant-0001 row (`quickbooks`, realm `1234567890123456`) | `postgres-local` MCP 2026-08-28 |
| Prod trio rows | **0 rows in all three tables** (2026-08-25 prod converge finding, per launch plan §3.5) | launch plan §3.5 |
| `notification_type` PK | `code` → `ON CONFLICT DO NOTHING` safe | `postgres-local` MCP 2026-08-28 |
| `notification_template` PK | `id`; idempotency guard = `WHERE NOT EXISTS (notification_type_code, channel, locale, tenant_id IS NULL)` | `postgres-local` MCP 2026-08-28 |

### B.2 Canonical provider_code decision — **`quickbooks`** (see §G Q1)

The card's parenthetical named `intuit` canonical (from the migration). Design-time evidence reverses that: **all ~30 application call sites query `provider_code == "quickbooks"`** (sync service, routes, tasks, webhook realm lookup); `intuit` appears nowhere in code. The migration in §B.3 therefore canonizes `quickbooks` and retires `intuit`. No application code changes.

### B.3 Migration `qb_h1_restore_app_service_registry` (blank revision)

`upgrade()` — all statements idempotent; begins with `SET LOCAL session_replication_role = 'replica';` (data-migration standard):

1. `INSERT INTO app_service_category (code, description, is_active, created_at, updated_at) VALUES ('accounting', 'Accounting & Bookkeeping integrations', true, now(), now()) ON CONFLICT DO NOTHING;`
2. `INSERT INTO app_service_provider (code, description, is_active, created_at, updated_at) VALUES ('quickbooks', 'QuickBooks Online (Intuit)', true, now(), now()) ON CONFLICT DO NOTHING;`
3. **Dev reconcile**: `UPDATE app_service SET provider_code = 'quickbooks', updated_at = now() WHERE tenant_id IS NULL AND provider_code = 'intuit';` (no-op in prod — 0 rows)
4. **Orphan retire**: `DELETE FROM app_service_provider WHERE code = 'intuit' AND NOT EXISTS (SELECT 1 FROM app_service WHERE provider_code = 'intuit');`
5. **Normalize the global row to the deterministic UUID** (seed parity — §B.4): `DELETE FROM app_service WHERE tenant_id IS NULL AND category_code = 'accounting' AND provider_code = 'quickbooks';` then `INSERT INTO app_service (id, tenant_id, name, category_code, provider_code, is_active, external_account_id, created_at, updated_at) VALUES ('00000000-0000-0000-0000-000000000aa5', NULL, 'QuickBooks Online', 'accounting', 'quickbooks', true, NULL, now(), now());` — the DELETE+INSERT pair is safe because the global row is a pure catalog entry: **nothing references it** (`integration_credential`/`integration_sync_mapping` reference tenant-scoped rows; engineer proves this in pre-work via MCP, §G Q2). The deterministic UUID `00000000-0000-0000-0000-000000000aa5` does not collide with the reserved `…0001`–`…0005` seed families (README-seed-data §reserved-UUIDs; engineer re-verifies).
6. `INSERT INTO notification_type (code, name, audience, is_active, created_at, updated_at) VALUES ('qb_connection_expired', 'QuickBooks Connection Expired', 'tenant', true, now(), now()) ON CONFLICT DO NOTHING;` (column set verified against the `qb_sync_conflict` seed row shape in `seed_core.py` line 511 — engineer confirms cols via MCP pre-work)
7. Three `notification_template` rows (`email` / `in_app` / `push`, `tenant_id NULL`, `locale` matching the existing `qb_sync_conflict` rows), each guarded by `WHERE NOT EXISTS (notification_type_code, channel, locale, tenant_id IS NULL)`. Subject/body copy = the strings specified in §F.3 (must be byte-identical between this migration and `seed_platform.py`).

`downgrade()` — exact reverse: delete the 3 templates (value-scoped on `notification_type_code = 'qb_connection_expired'` + `tenant_id IS NULL`); delete the `qb_connection_expired` type; delete the deterministic global row by PK; re-`INSERT` provider `intuit`; re-point nothing (the re-pointed global row is deleted in the step above — document that the pre-migration random-UUID dev row is not restorable, acceptable: it is re-created by the forward path).

### B.4 Seed Data Rollout (Rule 11.5 — REQUIRED this batch)

**Layer 1 — Core/Platform (Group A/B):**
- `seed_core.py`: add `app_service_category` + `app_service_provider` entries (rows exactly as §B.3.1–2); add a global-`app_service` seed block using the deterministic UUID `00000000-0000-0000-0000-000000000aa5` with `ON CONFLICT (id) DO NOTHING`; add `qb_connection_expired` to the `notification_type` dict; **delete both stale NOTEs** (lines 118–120, 2381–2382); fix help text (lines 3305–3306 — `quickbooks_online` is wrong); add `app_service` to the inspect manifest. Row content **byte-identical to the migration** (inclusions §20: `seed_core.py` is the post-schema-restore recovery path).
- `seed_platform.py`: add the 3 `qb_connection_expired` template-copy entries (idempotent `(code, channel)` upsert loop already exists — follow the `qb_sync_conflict` precedent at lines 682–694).
- **Mode-reset safety**: wherever the trio joins reset/wipe ordering, deletes must be child-first (`app_service` → provider/category) and `mode_seed` DELETEs value-scoped per Rule 11.1 (never channel/provider-scoped wipes).

**Layer 2 — Scenario data**: none — no entity columns added; tenant-scoped `app_service` connection rows remain OAuth-flow-created runtime data (never seeded).

**Verification**: `seed_core.py --mode inspect` shows all three tables; `pytest -m unit` green after seed changes (shared-DB rule); README §4 updated (trio ownership + row counts + deterministic UUID documented; new notification type/templates); **README §8.1 exclusion row for the trio removed** with a one-line pointer to this batch.

---

## C. Execution Order

| # | Task | Card scope item | Gate to proceed |
|---|---|---|---|
| 1 | **`app_service*` registry restoration** — §B.3 migration (full cycle test: upgrade → downgrade → upgrade → `alembic current`); `seed_core.py`/`seed_platform.py` §B.4 changes; stale NOTE/help/§8.1 removals; **teardown-collision proof**: `seed_core.py --mode reset && --mode seed` then run `test_quickbooks_sync.py` + `batch_b8` + `batch_1e` + `batch_b19` QB files green; new seed tests (trio rows present, idempotent re-run, deterministic UUID) | Part 2 — registry restoration | Migration cycle clean; QB test cohort green after a reset+seed cycle; `seed_core.py --mode inspect` shows trio |
| 2 | **OAuth refresh robustness** — error classification in `tasks/quickbooks_token_refresh.py` + `api/routes/integrations.py::_refresh_qbo_token_impl` (async): `invalid_grant`/400-401 → `expired` + enqueue `qb_connection_expired` owner notification; 5xx/`httpx.TransportError` → log WARNING, leave `active` (next beat retries); delete the dead sync stub (lines 396–449); `print()` → `logger`; unit tests for all four branches | Part 2 — OAuth refresh robustness | New tests pass; no route signature changes (no OpenAPI regen) |
| 3 | **`intuit_tid` → CloudWatch extension** — add the existing structured-log pattern (`services/quickbooks_sync.py` line 571 exemplar) to the token paths: `tasks/quickbooks_token_refresh.py::_refresh_access_token`, `integrations.py` refresh + OAuth callback exchange; confirm JSON-accessible fields for CloudWatch Insights (`intuit_tid=%s` arg, not f-string interpolation) | Part 2 — `intuit_tid` capture | Grep shows `intuit_tid` in every QB HTTP call path; tests assert log capture via `caplog` |
| 4 | **Conflict email to owner — verify + close** — tests proving `queue_conflict` enqueues a `qb_sync_conflict` notification that resolves to the **tenant owner's** `user_endpoint` on the `email` channel (PRD §3.9 row 6: "SMS or email notification to the tenant owner"); fix recipient resolution only if the test proves a gap | Part 2 — conflict email to owner | Test green (either confirming current behavior or the fix) |
| 5 | **`customer.display_name` uniqueness collision resolution** — in `sync_customer_from_qb`: catch `IntegrityError` on `uq_customer_tenant_display_name` → retry insert with deterministic suffix `"{DisplayName} (QB {Id})"` → write an `integration_sync_conflict` row (`conflict_subtype='display_name_dedup'`, both snapshots) so the owner sees the dedup in the conflict queue; tests: two QB customers same DisplayName → two P4T customers, second suffixed, conflict row queued | Part 2 — display_name investigation (PLAT-DEBT ⤴) | New tests green; existing `test_sync_customer_from_qb_*` unchanged-green |
| 6 | **Webhook entity guard + multi-entity volume test** — (a) `sync_quickbooks_entity_task`: explicit WARNING log + clean no-op for unhandled entity types (currently customer-only); (b) new mocked volume test: 50 QB customers paged through `sync_all_customers` (2 pages), assert 50 mappings + 0 conflicts; 25 invoice + 25 payment pushes (mocked) assert all mappings written; all `unit`-marked, httpx mocked | Part 2 — multi-entity sync volume test | Volume test green; guard test asserts the WARNING |
| 7 | **Coverage matrix publication** — verify every row of Appendix 1 against the code (checkbox protocol in the prompt), correct any drift, fill the field-level detail columns, then publish as `dev-docs/integrations/quickbooks/qb-coverage-matrix.md` (new directory) with the triage table (in-batch fixes ✅ vs follow-on candidates for Tom's QB-H2 approval gate) | Part 1 — coverage audit | Doc merged; matrix rows carry verification date + verifier initials |

### C.1 Explicit exclusions (do not build)

- **No Estimate / Credit Memo / Item / Class / Attachment sync implementation** — these are documented as matrix gaps and triaged to a Tom-approved follow-on (§G Q4). Only `display_name` dedup + the webhook guard are in-batch gap fixes (card: "gaps that make sync non-meaningful … fixed in-batch").
- **No QB dev reference doc** — card's explicit out-of-scope; rides the 6b downtime list.
- **No new API endpoints** → no OpenAPI regen, no FE handoff.
- **No changes to the QB OAuth connect flow's row-creation logic** beyond what Task 1 unbreaks (the connect flow's `INSERT` works as-is once the provider row exists).

---

## D. New API Endpoints

**None.** No route changes → **no `export_openapi_json.py` run, no `pnpm sync-api-types`, no FE companion**. (Task 2 deletes dead code and changes internals of existing handlers only; Task 6 changes a Celery task body. Stated explicitly because this deviates from the normal BE→FE handoff rhythm.)

---

## E. Pattern Reuse Decisions

| Pattern / rule | Application |
|---|---|
| **Bilateral Integration Conflict pattern** (PRD §3.9; §16 locked pattern) | Task 5 writes dedup events into the *existing* `integration_sync_conflict` queue with a new `conflict_subtype` — composing the locked pattern, never a parallel UX |
| **Two-Tier Configuration** (system default + tenant override) | No new settings; `qb_auto_expire_days` precedent cited only |
| **Seed ownership Group A/B split** (README-seed-data §3) | Trio + notification type → Group A (`seed_core.py`); templates → Group B (`seed_platform.py`); migration INSERTs byte-identical to seed rows (inclusions §20) |
| **DELETE-safety rule** (Rule 11.1; README §7) | All migration/seed DELETEs value-scoped (deterministic UUID, `code =`, `tenant_id IS NULL` + natural key) — never blanket/channel-scoped |
| **Audit mixin rule** (Rule 3 / Python Rule 15) | No new tables; all INSERT statements carry explicit `created_at, updated_at = now(), now()`; `created_by`/`updated_by` left NULL (system rows — matches existing seed precedent) |
| **RFC 7807** | No endpoint changes; existing QB routes untouched |
| **Sync-by-design** (rules §21) | QB service methods stay `async def` **only** where they exclusively await `httpx.AsyncClient` (existing pattern); Celery tasks + `_impl`s stay sync `def`; no new async-over-Session code |
| **Fail-closed + retry-friendly external calls** | Task 2's transient/permanent classification mirrors the `sync_quickbooks_customers_task` `max_retries=3` posture; permanent failure is the only state transition |
| **MCP read-only** (`.roo/rules/02-database-mcp-access.md`) | All verification via `postgres-local`; prod verification of Task 1 post-deploy is Tom's step via `postgres-prod` + SSH tunnel |

---

## F. Shared Module Interfaces & Celery Tasks

### F.1 `tasks/quickbooks_token_refresh.py` (modified)

```python
class TokenRefreshOutcome(str, Enum):
    REFRESHED = "refreshed"
    TRANSIENT_FAILURE = "transient_failure"   # 5xx / network — stays active, next beat retries
    PERMANENT_FAILURE = "permanent_failure"   # invalid_grant / 400 / 401 — expired + notify

def _classify_refresh_error(exc: Exception) -> TokenRefreshOutcome: ...

def _mark_connection_expired(db: Session, credential: IntegrationCredential) -> None:
    """Set connection_status='expired' and enqueue qb_connection_expired to the tenant owner."""
```

Beat schedule **unchanged** (`refresh-quickbooks-tokens` every 1800 s). Return dict gains `transient_failed: int`.

### F.2 `api/routes/integrations.py` (modified)

- Delete the dead sync `_refresh_qbo_token_impl` (lines 396–449).
- Async `_refresh_qbo_token_impl` gains the same classification; on permanent failure it still raises `HTTPException(500)` to its API caller (contract preserved) **after** marking expired + enqueueing the owner notification.

### F.3 New notification content (byte-identical: migration ↔ `seed_platform.py`)

| Channel | Subject | Body (summary) |
|---|---|---|
| `email` | `[QuickBooks] Connection expired — reconnect to resume sync` | Named tenant, what happened (refresh token rejected by Intuit), consequence (customer/invoice/payment sync paused; nothing lost — queued changes resume after reconnect), CTA: Settings → Integrations → QuickBooks → Reconnect |
| `in_app` | same subject | Short variant + deep link to the QB settings surface |
| `push` | subject only | Tap → QB settings surface |

Recipient resolution: tenant **owner** role only (matches PRD §3.9 "notification to the tenant owner" and the `qb_sync_conflict` precedent).

### F.4 `services/quickbooks_sync.py` (modified — Task 5)

```python
async def _insert_customer_with_dedup(
    self, customer_values: dict, qb_customer: dict, app_service_id: uuid.UUID
) -> Customer:
    """INSERT customer; on uq_customer_tenant_display_name collision retry once with
    f"{DisplayName} (QB {Id})" and queue a display_name_dedup conflict row."""
```

### F.5 `tasks/quickbooks_sync.py` (modified — Task 6)

`sync_quickbooks_entity_task` gains an explicit `else` branch: `logger.warning("QB webhook entity type %r not handled — event logged, no sync queued", entity_type)` and a clean return (no exception → no Celery retry storm).

---

## G. Open Questions Resolved

**Q1 — Canonical `provider_code`: `intuit` or `quickbooks`?** The card parenthetical said `intuit` (migration-era). Resolved to **`quickbooks`**: ~30 code call sites query `provider_code == "quickbooks"`; `intuit` is referenced only inside the 2026-05-31 migration itself. Canonizing `intuit` would mean a 30-site refactor with zero product value and high regression risk. The migration re-points the one dev global row and retires the orphan provider row; this is the "reconcile dev's extra `quickbooks` provider code" work the card asks for. **Deviation from the card's parenthetical is deliberate and evidence-based — flagged for Tom's visibility at close.**

**Q2 — Is deleting the dev global row safe (§B.3.5)?** Nothing references it: `integration_credential.app_service_id` and `integration_sync_mapping.app_service_id` point at **tenant-scoped** rows (the OAuth flow creates per-tenant rows); the global row is a catalog entry no query filters on (grep: zero `tenant_id IS NULL` consumers). Engineer still runs the `NOT EXISTS` reference check in pre-work as the safety net.

**Q3 — Why does the teardown collision (§8.1 exclusion) disappear now?** Historical mechanics: fixtures/tests create `provider_code="quickbooks"` rows (conftest `test_app_service`, `qb_app_service`, `_get_or_create_app_service`), which FK-require a `quickbooks` provider row that seeds never owned — so any seed/reset cycle touching the trio either FK-failed the tests or was forced to wipe rows tests depended on. With the trio canonically seeded (incl. `quickbooks` provider), fixtures get-or-create against stable rows and reset ordering deletes child-first. Task 1's proof protocol (reset+seed → QB test cohort green) is the regression net either way.

**Q4 — Which coverage gaps are in-batch vs follow-on?** In-batch (small + blocks "valid and meaningful" sync): `display_name` dedup (crash-class), webhook unhandled-entity guard (silent-drop class). Follow-on candidates for Tom's QB-H2 gate (each ≥ half a batch): Quote→Estimate sync (PRD §3.9 says "Estimate/Invoice"), refund/credit-memo handling for the SD-2 negative-payment model, QB→P4T invoice/payment pull, Item sync vs `qco_line_type` hints, `TxnTaxDetail` audit, `payment` `entity_type` row (MCP: absent while payments sync — verify impact in Task 7), class/department tracking (likely N/A for target customers), attachment sync (accepted S3-only). The matrix's triage table is the decision artifact Tom approves.

**Q5 — One batch or split (Rule 9.6)?** Designed as one 5–6 h batch, sequenced prod-critical first (Tasks 1–2). Declared flex: if context runs short after Task 5, the engineer stops cleanly after any task boundary (each task is independently committable with its own tests), reports in the Completion Summary, and the Architect scopes the remainder into QB-H2 with Tom. **Task 6 (volume test) is the first flex candidate, never Tasks 1–2** (prod-blocking).

**Q6 — Does the new notification type need web/mobile UI work?** No — it flows through the existing notification dispatch (email/in_app/push templates + preference matrix). The settings/notification-preference surfaces render `notification_type` rows generically (SD-2/SD-3 pattern). No FE batch.

**Q7 — `connection_status` vocabulary check.** Existing values in use: `active`, `expired` (refresh paths), and whatever the disconnect flow sets (engineer verifies — likely `disconnected`). Task 2 introduces **no new status values**; transient failures leave the row `active` untouched.

---

## Appendix 1 — Pre-Built Coverage Matrix (design-time evidence; engineer verifies in Task 7)

Verification protocol: each row gets `verified YYYY-MM-DD / <initials>` after re-confirming against code; corrections are expected and are the audit's value.

| QB object | P4T entity | Synced? | Direction | Mechanism (file) | Fields mapped | Known gaps |
|---|---|---|---|---|---|---|
| Customer | `customer` | ✅ | Bi-directional | `services/quickbooks_sync.py` (`sync_customer_from_qb` / `to_qb`, `sync_all_customers`); webhook → `sync_quickbooks_entity_task` | DisplayName↔display_name, GivenName↔first_name, FamilyName↔last_name, CompanyName↔company_name, PrimaryEmailAddr.Address↔email, PrimaryPhone↔mobile_phone, Notes↔notes, Active↔is_active, SyncToken↔external_version_token, MetaData→conflict snapshots | No BillAddr/ShipAddr; duplicate-DisplayName crash → **fixed Task 5**; no delete/deactivate propagation beyond `Active`; QB→P4T paged sync only via Beat (30-min) + webhook |
| Invoice + lines | `invoice` + `invoice_line` | ✅ push | P4T→QB only | `sync_invoice_to_qb` (task + service) | CustomerRef (via mapping), Line[].Amount/Description/ItemRef (via `qco_line_type.qb_item_name_hint`, **fallback item `"1"`**), Qty, UnitPrice (cents→dollars), CustomerMemo↔customer_notes, due date (verify) | No QB→P4T pull; no update-after-push audit; TxnTaxDetail unverified; DocNumber/numbering scheme unverified |
| Payment | `payment` | ✅ push | P4T→QB only | `sync_payment_to_qb` (task + service) | CustomerRef, TotalAmt (cents→dollars), invoice linkage (verify Line/LinkedTxn) | SD-2 refund (negative payment) → QB CreditMemo/RefundReceipt **unmapped**; QB-side payments never pulled |
| Estimate | `quote` | ❌ | — | none | — | PRD §3.9 names "Estimate/Invoice"; quote→estimate sync absent → follow-on |
| Credit Memo / Refund | `payment` (negative) | ❌ | — | none | — | Follow-on (pairs with SD-2 refund model) |
| Item (Products & Services) | `qco_line_type` (+ pricebook) | ⚠️ partial | mapping-only | `_resolve_qco_line_type_to_qb_item` | `qb_item_name_hint` → QB Item lookup; fallback `"1"` | No item catalog sync; hint-based resolution fragile → follow-on |
| Tax Agency / Rate | `tax_rate_version.external_tax_agency_id` | ⚠️ field-only | mapping field exists | (batch 1c) | `external_tax_agency_id` holds QB agency id | Invoice-push tax detail usage unverified → Task 7 audit row |
| Attachment | `job_attachment` / invoice docs | ❌ | — | none | — | Accepted gap (S3-only) — document rationale |
| Class / Department | — | ❌ | — | none | — | No P4T concept; likely N/A for electrical-contractor target — document |
| Webhook events | all entities | ⚠️ customer-only | QB→P4T | `webhooks.py` intake (entity-agnostic) → `sync_quickbooks_entity_task` (customer only) | realm→tenant via `app_service.external_account_id` | Non-customer entities silently dropped → **guard Task 6**; prod realm lookup broken until Task 1 lands |
| Sync telemetry | `integration_sync_log` / `_conflict` / `webhook_event` | ✅ | — | tasks + routes | records_processed/failed, conflict snapshots, auto-expiry | `intuit_tid` gaps in OAuth paths → **fixed Task 3** |
| Connection health | `integration_credential` | ⚠️ | — | `quickbooks_token_refresh.py` + `_refresh_qbo_token_impl` | tokens (encrypted), expires_at, last_refresh_at, connection_status | Transient blips kill connection; no owner notification → **fixed Task 2** |

**Triage table (for Tom's QB-H2 approval gate)** — populated by Task 7 from the verified matrix: in-batch fixes (Tasks 5, 6a) ✅ / follow-on candidates (Estimate, refunds, pulls, items, tax detail, `payment` entity_type, classes, attachments).
