# Implementation Prompt: DLC-B5 — SMS Delivery-Status Reconciliation

**Mode**: Pilot Python Engineer
**Batch**: DLC-B5
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 — DLC-B5 card
**Design doc**: none — the launch-plan card + this prompt are self-contained (MCP-verified schema, no migration)
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: None

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §16 (Standard Task Workflow). **No §13/Alembic — this batch has NO migration.**
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, and fixture rules.

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. `customer_communication_message` is tenant-scoped **transitively via `thread_id → customer_communication_thread.tenant_id`** — it has **no direct `tenant_id` column** (MCP-confirmed). The webhook is a public, tenant-agnostic endpoint; the lookup key is `carrier_message_id` (globally unique per Telnyx). Scope by `carrier_message_id`, not `tenant_id`, in the delivery-status path — this is the one legitimate exception, because the carrier does not know the tenant. Document this in your Completion Summary.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never INSERT/UPDATE/DELETE through it.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. No "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.

> **This batch adds NO endpoint and NO migration.** It adds one background-task function inside the existing webhook route file, extends the event-type routing, and adds tests. `export_openapi_json.py` is **not** required (no schema/endpoint change). `generate_db_model_map.py` is **not** required (no model change). Do not run them.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y skipped`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom that it is a known accepted failure, OR (b) fix it before touching any batch files. You may NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never INSERT/UPDATE/DELETE. If a query fails → STOP and ask Tom.

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Confirm the target table columns (this is the row you will UPDATE).
--    EXPECTED: status TEXT NOT NULL, carrier_message_id TEXT NULL,
--              sent_at TIMESTAMPTZ NULL, delivered_at TIMESTAMPTZ NULL.
--    There is NO tenant_id column and NO delivery_error_code column.
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer_communication_message'
ORDER BY ordinal_position;

-- 2. Confirm there is NO CHECK constraint that forbids status='delivered'/'failed'
--    (status is free TEXT — 'received'/'sent'/'delivered'/'failed' all valid).
SELECT conname, pg_get_constraintdef(oid) AS def
FROM pg_constraint
WHERE conrelid = 'public.customer_communication_message'::regclass
  AND contype = 'c';

-- 3. Confirm carrier_message_id is queryable and see what real values look like
--    (Telnyx message IDs are UUIDs-as-text; mock carrier uses 'mock-msg-N').
SELECT status, carrier_message_id, sent_at, delivered_at
FROM public.customer_communication_message
WHERE direction = 'outbound'
ORDER BY created_at DESC
LIMIT 10;

-- 4. Confirm the tenant-scoping path (transitive via thread).
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer_communication_thread'
  AND column_name IN ('id', 'tenant_id')
ORDER BY column_name;
```

If any query returns unexpected results → **STOP and ask Tom**.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/routes/webhooks_sms.py                       ← the route file you extend (event-type routing at Step 3; _process_inbound_sms is the pattern for your new _process_delivery_status)
backend/services/sms_carrier.py                          ← SmsCarrier ABC + MockSmsCarrier + get_sms_carrier factory; note verify_webhook_signature(payload, headers: dict) signature (DLC-B4)
backend/services/telnyx_sms_carrier.py                   ← real Ed25519 verify + parse_inbound_webhook shape (data.payload.*); the delivery-status payload shape lives here conceptually
backend/app/models/sms.py                                ← CustomerCommunicationMessage model — confirm field names (status, carrier_message_id, sent_at, delivered_at)
backend/services/customer_communication_threading.py     ← how outbound/inbound rows are written (status='received'/'sent', carrier_message_id set from result) — your update target
backend/api/routes/communications_threads.py             ← outbound send path that sets status='sent' + carrier_message_id (lines ~380–412) — this is the row DLC-B5 later reconciles to 'delivered'/'failed'
backend/tests/conftest.py                                ← available fixtures (client, db_session, test_tenant, test_customer)
backend/tests/domains/notifications_comms/test_dlc_b4_sms_prefix.py  ← recent sibling test file — pattern for this domain
backend/tests/domains/notifications_comms/test_sms_tcpa_keyword_handlers.py  ← how webhook payloads are built in tests
```

Also run these to find related files and confirm current state:

```bash
grep -rn "message.received\|message.finalized\|message.sent\|event_type" backend/api/routes/webhooks_sms.py
grep -rn "DEBUG-DLC-B4" backend/  --include="*.py"     # expect ZERO hits — the temp block was already removed; confirm
grep -rn "verify_webhook_signature" backend/services backend/tests --include="*.py"
```

---

## Background / Context

**The gap** (discovered 2026-07-27 during DLC-B4 live-webhook verification): Telnyx fires `message.sent` and `message.finalized` delivery-status webhooks for every outbound SMS. The webhook endpoint `webhooks_sms.py` now **verifies + acknowledges** these events (returns 200), but **only `message.received` (inbound) is processed** — delivery-status events fall into the `else` branch and are dropped. As a result, every outbound row in `customer_communication_message` keeps `status = 'sent'` forever; `delivered_at` and a true `failed` state are never persisted. A contractor cannot tell whether a customer's appointment reminder actually landed or bounced (e.g. Verizon 40010 on an unregistered number).

**The schema already supports this** (MCP-verified — see Pre-Work query 1): `status TEXT NOT NULL`, `carrier_message_id TEXT NULL`, `sent_at`, `delivered_at`. **No migration needed.**

**Telnyx delivery-status webhook payload shape** (for reference — verify against your MCP query 3 real IDs and the `parse_inbound_webhook` shape in `telnyx_sms_carrier.py`):

```json
{
  "data": {
    "event_type": "message.finalized",
    "payload": {
      "id": "40017cd5-...-carrier-message-id",
      "to": [
        { "phone_number": "+1512...", "status": "delivered" }
      ],
      "errors": [
        { "code": "40010", "title": "Not 10DLC registered", "detail": "..." }
      ]
    }
  }
}
```

- `data.payload.id` = the `carrier_message_id` that was stored on the outbound row when it was sent.
- `data.payload.to[0].status` = Telnyx per-recipient status: `queued` / `sending` / `sent` / `delivery_unconfirmed` / `delivered` / `delivery_failed` / `sending_failed`.
- `data.payload.errors[]` present (non-empty) on failures — e.g. `40010`.

**Status mapping** (align with the existing `TelnyxSmsCarrier.get_delivery_status` mapping you read):

| Telnyx recipient status | our `status` | set `delivered_at`? |
|---|---|---|
| `delivered` | `delivered` | yes (event timestamp / now) |
| `sent`, `sending`, `queued`, `delivery_unconfirmed` | `sent` | no |
| `delivery_failed`, `sending_failed` (or non-empty `errors[]`) | `failed` | no |

**Idempotency invariant**: a repeat/late webhook must **never regress** a `delivered` row back to `sent`. Once `delivered`, stay `delivered`. `failed` may be set from `sent`. Never overwrite `delivered` with anything.

---

## Task 1 — Add `_process_delivery_status` background task

**File**: `backend/api/routes/webhooks_sms.py`

Add a module-level function mirroring the structure of the existing `_process_inbound_sms` (opens its own DB session from the injected factory, wraps in try/except/finally, closes the session). It must:

1. Parse the raw payload JSON → extract `data.payload.id` (carrier message id), `data.payload.to[0].status`, and `data.payload.errors` (may be absent/empty).
2. Look up the `customer_communication_message` row by `carrier_message_id` using a tenant-agnostic `select()` (see Rule 6 — this endpoint is carrier-driven and does not know the tenant; `carrier_message_id` is the globally-unique key). If **no row matches** → log at `info`/`debug` and return cleanly (no crash, no-op — Telnyx also sends status for numbers we didn't originate, and mock IDs won't match).
3. Map the Telnyx status → our status per the table above. Extract the mapping into a small pure helper (e.g. `_map_delivery_status(telnyx_status: str, has_errors: bool) -> str`) so it is unit-testable without a DB.
4. Apply the **idempotency invariant**: if the current row `status == "delivered"`, do nothing (return). Otherwise update `status`; when the mapped status is `delivered`, set `delivered_at` (use the event timestamp if present and parseable, else `datetime.now(UTC)`).
5. **Error capture (MVP decision — no schema change)**: when the event carries a non-empty `errors[]`, set `status='failed'` and **log** the error code + detail at `warning` level (structured — include `carrier_message_id`). Do NOT add a column. A future `delivery_error_code` column is a P2 nice-to-have — add a one-line `# TODO(P2/DLC): persist delivery_error_code — flagged to Tom` comment at the log site so it is discoverable.
6. `db.commit()` on the update; `db.rollback()` in the except; always `db.close()` in finally (mirror `_process_inbound_sms` exactly).

> **Read `_process_inbound_sms` first and copy its session-handling skeleton.** Do not invent a new session pattern.

Intermediate check after this task:

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Route delivery-status events in the endpoint

**File**: `backend/api/routes/webhooks_sms.py` — the `telnyx_inbound_sms` handler, "Step 3" routing block (currently lines ~181–200).

Extend the event-type routing:

- `message.received` → `background_tasks.add_task(_process_inbound_sms, payload_bytes, _get_db)` (unchanged).
- `message.sent` **or** `message.finalized` → `background_tasks.add_task(_process_delivery_status, payload_bytes, _get_db)` (new).
- everything else (`10dlc.*`, unknown) → `logger.debug(...)` ack only (unchanged).

Keep the 200 `{"status": "received"}` return for all verified events (Telnyx retries on non-2xx). Do not change the signature-verification step. Keep the `_get_db` factory pattern already used for the inbound task.

> **Confirm the `DEBUG-DLC-B4` temp log block is already gone** (grep returned zero hits in Pre-Work). If — and only if — you find any leftover `DEBUG-DLC-B4` block, remove it as part of this task (it was flagged in the DLC-B5 card). Expected: nothing to remove.

Intermediate check:

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — Ed25519 verify regression test (fold-in from DLC-B4)

The DLC-B4 signature-verification rewrite (`verify_webhook_signature(payload, headers: dict)` doing direct Ed25519 against `TELNYX_PUBLIC_KEY`, signed payload = `timestamp + "|" + body`) currently has no unit test that exercises the real verify path with a known keypair — so a future refactor could silently regress it.

Add a unit test in the notifications_comms domain that:

1. Generates an Ed25519 keypair with `cryptography` (`Ed25519PrivateKey.generate()`).
2. Builds `signed_payload = timestamp + "|" + body`, signs it, base64-encodes the signature and the public key.
3. Instantiates `TelnyxSmsCarrier` with `TELNYX_PUBLIC_KEY` set to the base64 public key (monkeypatch `core.config.settings` / construct so `self._public_key` is the test key — read the `__init__` to see how it reads settings; use `monkeypatch.setattr` on the settings object).
4. Asserts `verify_webhook_signature(body_bytes, {"telnyx-signature-ed25519": sig_b64, "telnyx-timestamp": ts})` returns **True** for the correct signature and **False** for a tampered body / wrong signature / missing header.

> Telnyx is not installed in every env — this test constructs `TelnyxSmsCarrier` directly. If import of `telnyx` fails in the test env, guard with the existing integration-marker convention you see in `test_telnyx_sms_integration.py` (check whether it uses a skip marker) and keep the **pure** `_map_delivery_status` + verify-crypto assertions in a plain `unit` test that does not require the Telnyx SDK. Prefer keeping the crypto assertions unit-level (the `cryptography` calls in `verify_webhook_signature` do not need the `telnyx` package — only `__init__` does; if `__init__` forces the import, factor the test to call the verify logic without the SDK, or use the integration marker). **If you cannot make it a clean `unit` test without the SDK, put it under the integration marker and note why in the Completion Summary.**

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**New test file**: `backend/tests/domains/notifications_comms/test_dlc_b5_delivery_status.py`

```python
pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]
```

- Use the `client` fixture (never module-level `TestClient`).
- Use `test_tenant` / `test_customer` fixtures — never hardcoded UUIDs.
- **Scope every assertion by the `carrier_message_id` / row id you inserted** — never assert on total row counts (shared seed DB rule).
- For rows you need in a specific state, INSERT a new `customer_communication_message` (with its own `carrier_message_id`) — never mutate seed rows. It needs a valid `thread_id`; create a `customer_communication_thread` first (read how `test_customer_sms_threads.py` builds one), or reuse a thread you inserted in the test.

**Required coverage:**

| # | Scenario | Expected |
|---|---|---|
| 1 | `message.finalized`, `to[0].status="delivered"` | row `status == "delivered"`, `delivered_at` set |
| 2 | `message.finalized` with `errors=[{code:"40010"}]` | row `status == "failed"`, `delivered_at` still NULL |
| 3 | Idempotency — deliver, then replay a `sent` event | row stays `delivered` (no regression), `delivered_at` unchanged |
| 4 | `message.sent`, `to[0].status="sent"` | row `status == "sent"` (unchanged from initial) |
| 5 | Unknown `carrier_message_id` | no row mutated, no exception (clean no-op) |
| 6 | `_map_delivery_status` pure-function table | each Telnyx status maps to the correct `status` string |
| 7 | Endpoint routing — POST a `message.finalized` payload to `/api/v1/webhooks/sms/telnyx-inbound` with mock carrier (signature True) | 200 `{"status":"received"}` and (via the background task run inline in TestClient) the row is reconciled |
| 8 | (Task 3) Ed25519 verify — good sig True, tampered body False | as described |

> **Autouse fixtures**: `mock_ai_services` and `mock_cognito_jwks` run automatically. This batch does not touch entitlements — no `skip_mock_entitlement_allowed` needed. The webhook endpoint is public (no JWT), so no `mock_cognito_jwt` needed for the POST.

> **Background-task execution note**: FastAPI's `TestClient` runs `BackgroundTasks` synchronously **after** the response is returned, within the same `with client:` context. Confirm your test reads the DB row *after* the request returns. If you find the task did not run, check whether the test uses the `client` fixture as a context manager (read how existing webhook tests assert post-request state).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving on. Fix any failure — including ones that appear pre-existing — before proceeding.

### Phase 2 — Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot check
python -m pytest tests/domains/notifications_comms/test_dlc_b5_delivery_status.py -v 2>&1 | tail -20

echo "=== DLC-B5 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without written confirmation from Tom. If you cannot identify a root cause → STOP and ask Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y skipped`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — schema confirmed (no migration needed; no `tenant_id`, no `delivery_error_code` column; `status` is free TEXT with no forbidding CHECK)
- [ ] All mandatory source files read before writing code
- [ ] **Task 1**: `_process_delivery_status` added to `webhooks_sms.py` — carrier_message_id lookup, status mapping, idempotency invariant (delivered never regresses), error logging with P2 TODO, own-session skeleton mirrors `_process_inbound_sms`
- [ ] **Task 1**: `_map_delivery_status` pure helper extracted (unit-testable without DB)
- [ ] **Task 2**: event-type routing extended — `message.sent`/`message.finalized` → `_process_delivery_status`; `message.received` unchanged; else → 200 ack
- [ ] `DEBUG-DLC-B4` block confirmed already absent (or removed if found)
- [ ] **Task 3**: Ed25519 verify regression test added (good sig True / tampered False)
- [ ] New test file uses `pytestmark` (domain + unit), `client` fixture, `test_tenant`/`test_customer` — no hardcoded UUIDs, no total-count assertions
- [ ] All 8 coverage scenarios implemented and passing
- [ ] **No** `export_openapi_json.py` run needed (no endpoint/schema change) — confirmed
- [ ] **No** Alembic migration created (schema already supports it) — confirmed
- [ ] **Phase 1**: all unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: full suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B + one-row entry to Appendix A
- [ ] DLC-B5 marked ✅ in launch-plan §2.0 (#9a) and §2.3 card; DLC-B4 card's "tracked as DLC-B5" note updated to point at the completion

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` Appendix B using the format below, and add a one-row entry to Appendix A (§A-2).
2. Update the §2.0 Master Status Table row #9a and the §2.3 DLC-B5 card to ✅.

```markdown
### DLC-B5 — SMS Delivery-Status Reconciliation: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y skipped
**Final**: X+N passed, Y skipped (+N new tests)

#### What Was Accomplished
- [background task, routing, idempotency invariant, error logging, Ed25519 test]
- [note the Rule 6 exception: carrier_message_id lookup is tenant-agnostic — carrier does not know tenant]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/api/routes/webhooks_sms.py` | Updated — `_process_delivery_status` + `_map_delivery_status` + event routing |
| `backend/tests/domains/notifications_comms/test_dlc_b5_delivery_status.py` | Created — N tests |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/notifications_comms/test_dlc_b5_delivery_status.py` | `notifications_comms` | N | ✅ |
```

---

## After This Task — Next Step

DLC-B5 clears the last non-approval-gated item in launch-plan Order 3. Once the 10DLC campaign is approved (Tom's operational item), delivery-status will populate live automatically. The next backend candidate is **SMS-2** (dedicated-number revenue add-on), which depends on DLC-B2 campaign approval.
