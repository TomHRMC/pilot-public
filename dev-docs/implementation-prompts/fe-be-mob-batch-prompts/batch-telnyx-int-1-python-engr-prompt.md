# Implementation Prompt: TELNYX-INT-1 — Telnyx Mock/Live Toggle + Real-API Integration Tests

**Mode**: Pilot Python Engineer
**Batch**: TELNYX-INT-1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 (row 9) — Order-0 "finish Telnyx completely" directive
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-telnyx-int-1-design.md` — read every section (A–G)
**Spike findings**: `dev-docs/integrations/telnyx/telnyx-spike-1-findings.md`
**Estimated session**: 3–4 hours
**Platform**: Backend only — no FE companion, no endpoint changes, no DB migrations, no seed changes
**Cost guardrails**: Mock Telnyx objects are $0. **No live SMS sends, no live number orders, no live brand/campaign submissions in this batch** — those are Tom's Step 3.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, fixtures
- **`batch-telnyx-int-1-design.md`** — the work order

**Critical rules for this batch:**

- **Rule 11**: If ANY test fails during your work — even pre-existing — fix it before declaring done. Unidentifiable root cause → STOP and ask Tom.
- **Rule 12 (sync routes)**: N/A to routes here, but the sync-by-design rule applies to any service code you touch — no `async def` conversions.
- **Rule 14 (Ruff)**: Run `ruff check --fix` + `ruff format` on **only the files you changed**; fix all errors in those files, including pre-existing ones.
- **Rule 16 (verify, don't assume)**: The live DB is authoritative. MCP verification queries below are mandatory even though this batch has no migrations.
- **Adapter discipline (mvp-arch)**: All Telnyx interaction stays inside `services/telnyx_sms_carrier.py`. Never import `telnyx` in routes, other services, or tests (tests instantiate the carrier or patch `get_sms_carrier()`).
- **Secrets hygiene**: Never commit API keys. `.env.example` gets variable **names only**. If you find a real key in any file you touch → STOP and tell Tom immediately.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Pre-existing failures → confirm with Tom or fix before starting.

## Pre-Work: Run MCP Verification Queries

Run **all** via `postgres-local` MCP before writing code. Unexpected results → STOP and ask Tom.

```sql
-- 1. Verify tenant_messaging_registration columns (integration tests exercise the C-B9
--    state machine against these via the service layer)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;
-- Expected (verified 2026-08-08): id, tenant_id, entity_type, status, telnyx_brand_id,
-- telnyx_campaign_id, telnyx_phone_number, quoted_setup_cents, quoted_monthly_cents,
-- stripe_checkout_id, stripe_payment_intent, otp_requested_at, otp_verified_at,
-- failure_reason, stripe_recurring_item_id, recurring_item_created_at, created_at,
-- updated_at, created_by, updated_by

-- 2. Verify tenant_phone_number columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_phone_number'
ORDER BY ordinal_position;
-- Expected: id, tenant_id, phone_number, area_code, carrier, carrier_provisioning_id,
-- monthly_fee_cents, status, provisioned_at, released_at, created_at, updated_at,
-- created_by, updated_by

-- 3. Confirm no leftover mock-brand rows pollute local dev data (informational)
SELECT status, count(*) FROM public.tenant_messaging_registration GROUP BY status;
```

If any column name differs from the expectations above → use the MCP-returned name, note the discrepancy in your Completion Summary, proceed.

## Pre-Work: Read These Source Files

```
backend/services/sms_carrier.py                    ← ABC + MockSmsCarrier + get_sms_carrier() factory
backend/services/telnyx_sms_carrier.py             ← the file you'll modify (create_brand ~L269, __init__ ~L51)
backend/core/config.py                             ← settings pattern (add TELNYX_10DLC_MOCK)
backend/services/messaging_provisioning.py         ← C-B9 13-state machine that consumes the carrier
backend/tests/integration/test_telnyx_sms_integration.py  ← existing SDK-patched tests (do NOT modify; your new suite sits alongside)
backend/tests/batch_b11/test_a59_sms_carrier_adapter.py   ← factory/mock-carrier unit tests you'll extend
backend/.env.example                               ← add the 5 Telnyx/SMS vars
dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md  ← add §14 Testing Modes
```

---

## Tasks (execute in design-doc §C order)

### Task 1 — `TELNYX_10DLC_MOCK` setting
Add to `core/config.py` following the existing settings pattern: `TELNYX_10DLC_MOCK: bool = False`.

### Task 2 — Mock mode in `TelnyxSmsCarrier`
Per design §F.2: read the flag in `__init__`, log a loud WARNING when enabled, add `payload["mock"] = True` in `create_brand` when the flag is on. **Verify against current Telnyx API docs whether `create_campaign` under a mock brand needs its own explicit mock flag** — if yes, add it identically and note it in the Completion Summary; if no, leave `create_campaign` unchanged and cite the doc you confirmed against.

### Task 3 — Init guardrail
The WARNING log from Task 2 IS the guardrail (design §C.3). No DB-state guardrails — mock IDs persist identically by design.

### Task 4 — Documentation (spike gap G2)
- `backend/.env.example`: add `SMS_CARRIER=mock`, `TELNYX_API_KEY=`, `TELNYX_PUBLIC_KEY=`, `TELNYX_MESSAGING_PROFILE_ID=`, `TELNYX_10DLC_MOCK=false` — one-line comment each. Names only, never values. **Fix the existing hazard**: the current file ships `SMS_CARRIER=telnyx` (B21/FIND-173 leftover) — change the default to `mock` and comment the three modes.
- `dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md`: add **§14 — Testing Modes (mock vs live)** with the 3-mode table from the spike findings §5 (mock / telnyx+TELNYX_10DLC_MOCK / telnyx-live), plus instructions for capturing a real webhook payload into `tests/integration/fixtures/telnyx/real_webhook_capture.json` during Step 3.
- **Do NOT edit `telnyx-rec-api-integration-testing-approach.md`** — per Tom decision 2026-08-09, the Architect rewrites that doc into the canonical setup-and-run guide *after* your completion summary, so it matches what was actually built. Your job is to give the Architect accurate raw material: in your Completion Summary, include the exact final env-var names, the exact pytest commands you ran, and any deviations from the design's flag semantics.

### Task 5 — Real-API integration suite (spike gap G3)
New file `backend/tests/integration/test_telnyx_real_api.py` implementing design §F.3 exactly:
- Skip unless `TELNYX_API_KEY` is set; **hard-refuse** brand/campaign creation unless `TELNYX_10DLC_MOCK=true` (fixture-level guard — this is the anti-fee safety).
- Scenarios 1–6 from §F.3 (mock brand create/poll, mock campaign create/poll, verticals, number search, 4xx error mapping, Ed25519 fixture verification).
- **Excluded**: `send_message` live, `provision_number` (paid number order), `assign_number_to_campaign` on the live campaign.
- Markers per `tests/README-adding-tests.md` (integration marker; confirm the exact marker name from pytest.ini/`--strict-markers` before writing).

### Task 6 — Ed25519 capture verification (spike gap G4)
The fixture-driven test from §F.3 scenario 6: skip with a clear message when `fixtures/telnyx/real_webhook_capture.json` is absent (it gets captured during Tom's Step 3); verify `verify_webhook_signature()` returns True when present.

### Task 7 — Unit tests for the flag
Extend `tests/batch_b11/test_a59_sms_carrier_adapter.py` (or the correct domain file per README-adding-tests):
1. `TELNYX_10DLC_MOCK=true` → `create_brand` payload includes `mock=True` (patch the SDK client, assert kwargs)
2. Flag absent/false → payload has no `mock` key
3. Flag on → WARNING logged at init (caplog assertion)
4. `get_sms_carrier()` factory routing unchanged (regression — mock default still returns `MockSmsCarrier`)

### Task 8 — Execute the real suite once
With a dev Telnyx key + `TELNYX_10DLC_MOCK=true` (coordinate with Tom for the key): run `pytest tests/integration/test_telnyx_real_api.py -v`, record per-scenario pass/fail + any Telnyx-side surprises in the Completion Summary. If no key is available in your environment → mark this "BLOCKED — needs Tom's dev key" and ensure the suite is skip-clean in CI (zero failures when env vars absent).

---

## OpenAPI Regeneration

No endpoints change → `python export_openapi_json.py` should produce an empty diff. Run it anyway at close and confirm; if a diff appears, STOP and ask Tom (something unintended changed).

## Final Verification Gate

**Phase 1 — unit only:**
```bash
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

**Phase 2 — full suite (excluding live-key tests, which self-skip):**
```bash
python -m pytest --tb=short -q 2>&1 | tail -10
```
Plus: ruff clean on changed files; real-API suite result recorded (pass or BLOCKED-with-reason).

## Definition of Done

- [ ] `TELNYX_10DLC_MOCK` setting + carrier mock-flag behavior + init WARNING
- [ ] Campaign-mock question resolved against Telnyx docs (answer recorded)
- [ ] `.env.example` + playbook §14 documentation
- [ ] `tests/integration/test_telnyx_real_api.py` — 6 scenarios, fee-guard fixture, skip-clean without keys
- [ ] 4 new unit tests for the flag; existing carrier tests untouched and green
- [ ] Phase 1 unit suite: baseline count maintained or improved
- [ ] Phase 2 full suite green; ruff clean on changed files
- [ ] Real-API suite executed once (or explicitly BLOCKED on Tom's dev key)
- [ ] `openapi.json` diff confirmed empty
- [ ] No keys committed; no live SMS/orders/registrations performed

## Completion Summary

```
## TELNYX-INT-1 Completion Summary
- Tasks completed: N/8 (deviations + why)
- Campaign mock flag: [required / inherited from mock brand — doc cited]
- Files changed: [list]
- Test counts: baseline X → final Y (unit); new tests: N
- Real-API suite: [PASS per-scenario / BLOCKED reason]; Telnyx-side observations: [any]
- openapi.json diff: empty / [describe]
- MCP discrepancies: [none / describe]
- Deviations from design: [none / describe]
```
