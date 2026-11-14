# Batch Design: TELNYX-INT-1 — Telnyx Mock/Live Toggle + Real-API Integration Tests

**Version**: 1.0
**Date**: 2026-08-08
**Author**: Pilot Architect
**Status**: ✅ **COMPLETE 2026-08-10** — 10DLC Step 3 live E2E run passed; G4 closed with real webhook capture fixture (`tests/integration/fixtures/telnyx/real_webhook_capture.json`); scenario 6 auto-verifies. Recorded in launch plan Appendix A
**Batch code**: TELNYX-INT-1
**Owner**: Python Engineer
**Priority**: P1 — Pre-GA; part of the Order-0 "finish Charter/Stripe/Telnyx completely" directive
**Prerequisite**: TELNYX-SPIKE-1 ✅ (findings) · 10DLC Step 2 ✅ (campaign `CXXXXXX` approved 2026-08-07, number assigned)
**Platform**: Backend only — no FE, no OpenAPI-visible changes (no new/changed endpoints)

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `telnyx-spike-1-findings.md` | Spike output — mock brands/campaigns free + API-createable; webhook-testable; no SMS traffic over mock campaigns; gaps G1–G4 | 2026-08-08 |
| `telnyx-rec-api-integration-testing-approach.md` | Baseline: no sandbox; portal-first; separate API keys per env; cost guardrails | 2026-08-08 |
| `backend/services/sms_carrier.py` (full) | `SmsCarrier` ABC; `MockSmsCarrier` implements all C-B9 10DLC methods; `get_sms_carrier()` factory routes on `SMS_CARRIER` env (`mock` default / `telnyx`) | 2026-08-08 |
| `backend/services/telnyx_sms_carrier.py` (full) | v2 SDK client (`telnyx.Telnyx(api_key=…)`); `create_brand` payload map (~L269), `create_campaign` (~L335), `assign_number_to_campaign` (~L445); lazy SDK import; env vars `TELNYX_API_KEY`, `TELNYX_PUBLIC_KEY`, `TELNYX_MESSAGING_PROFILE_ID` | 2026-08-08 |
| `backend/tests/integration/test_telnyx_sms_integration.py` | Existing "integration" tests **patch the SDK** (`patch.object(carrier._client.messages, "send")`) — never hit the real API. This batch adds the real suite alongside it. | 2026-08-08 |
| Telnyx API docs (spike) | Campaign object `mock: true` field; mock campaigns cannot be shared upstream; mocks exist for webhook-flow testing | 2026-08-08 |
| DB schema | **No DB changes in this batch** — no MCP DDL verification needed. Integration tests read/write existing `tenant_messaging_registration` + `tenant_phone_number` via the service layer; prompt includes MCP column verification for both (engineer safety net). | 2026-08-08 |

## B. Migration Plan

**None.** No schema changes, no seed data changes (no Seed Data Rollout required — Rule 11.5 N/A, verified: this batch adds env config, carrier code, tests, and docs only).

## C. Execution Order

| # | Task | Files |
|---|---|---|
| 1 | Add `TELNYX_10DLC_MOCK` setting | `core/config.py` |
| 2 | Mock-mode support in `TelnyxSmsCarrier` — read flag in `__init__`; pass `mock=True` on brand creation; campaign creation under a mock brand is automatically mock (carrier-side: pass through Telnyx's behavior, no extra param needed beyond brand) | `services/telnyx_sms_carrier.py` |
| 3 | Guardrail: mock flag + live keys sanity — log a loud warning at carrier init when `TELNYX_10DLC_MOCK=true` (so nobody accidentally runs prod in mock mode); mock-mode brand/campaign IDs are persisted identically (no schema change) | `services/telnyx_sms_carrier.py` |
| 4 | Env + runbook documentation (G2): `.env.example` entries (`SMS_CARRIER`, `TELNYX_API_KEY`, `TELNYX_PUBLIC_KEY`, `TELNYX_MESSAGING_PROFILE_ID`, `TELNYX_10DLC_MOCK`) + a "Mock vs Live testing modes" section in the 10DLC playbook doc (3-mode table from spike §5) | `backend/.env.example`, `dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md` |
| 5 | Real-API integration test suite (G3) — new file `tests/integration/test_telnyx_real_api.py`, marker-gated, skipped unless `TELNYX_API_KEY` present; covers: mock brand create→poll, mock campaign create→poll, verticals list, number search; **explicitly no live SMS send** (reserved for Step 3) | `tests/integration/test_telnyx_real_api.py` |
| 6 | Ed25519 live-verification prep (G4): a `--check-webhook` style utility or test that verifies a **captured real webhook payload** (from Tom's Step 3 test) against `TELNYX_PUBLIC_KEY` — delivered as a pytest that reads a captured fixture file, skipped until fixture exists | `tests/integration/test_telnyx_real_api.py` + fixture dir |
| 7 | Unit tests for the flag: mock-mode on/off payload assertions (`mock=True` present/absent), warning logged, factory unchanged | `tests/batch_b11/test_a59_sms_carrier_adapter.py` (extend) or new domain file per README-adding-tests |
| 8 | Full verification: unit suite green; real-API suite executed once against the dev Telnyx key with `TELNYX_10DLC_MOCK=true` and results recorded in the completion summary | — |

## D. New API Endpoints

None. (No `export_openapi_json.py` regeneration needed — verify at close; if `openapi.json` diff is empty, note it in the summary.)

## E. Pattern Reuse Decisions

- **`SmsCarrier` adapter layer** (mvp-arch §16 / infrastructure-constraints §3): all changes stay inside the adapter — no route/service code touches Telnyx directly. This batch *strengthens* the adapter seam rather than bypassing it.
- **Cost guardrails** (infrastructure-constraints §1, spike §5): mock-object tests are $0; no live brand/campaign re-submissions; no live SMS in the automated suite.

## F. Shared Module Interfaces

### F.1 — Config

```python
# core/config.py — new setting
TELNYX_10DLC_MOCK: bool = False  # when True, 10DLC brand/campaign creation uses Telnyx mock objects ($0)
```

### F.2 — Carrier changes (`services/telnyx_sms_carrier.py`)

```python
def __init__(self):
    ...
    self._mock_10dlc: bool = getattr(settings, "TELNYX_10DLC_MOCK", False)
    if self._mock_10dlc:
        logger.warning(
            "TelnyxSmsCarrier running with TELNYX_10DLC_MOCK=true — "
            "10DLC brands/campaigns will be created as MOCK objects (no TCR fees, no SMS traffic)"
        )

# create_brand(): payload gains exactly one conditional field
if self._mock_10dlc:
    payload["mock"] = True

# create_campaign(): NO code change expected — campaigns under a mock brand are mock by inheritance.
# Engineer MUST verify against Telnyx docs during implementation; if the API requires an explicit
# mock flag on campaign creation, add it the same way and note it in the Completion Summary.
```

### F.3 — Test suite (`tests/integration/test_telnyx_real_api.py`)

- Module-level skip: `pytestmark = [pytest.mark.integration, pytest.mark.skipif(not os.getenv("TELNYX_API_KEY"), reason="live Telnyx key required")]` — plus `TELNYX_10DLC_MOCK=true` required for the provisioning tests (assert the env flag at fixture setup; refuse to run brand/campaign creation without it → prevents accidental fee-bearing registrations).
- Scenarios (all against real API, mock objects):
  1. `create_brand` with mock → returns `brand_id`; `get_brand` polls to a terminal state; response `mock` field is true (if exposed)
  2. `create_campaign` under the mock brand → `campaign_id`; `get_campaign` poll
  3. `get_verticals` returns non-empty list (real enum values — compare shape with `MockSmsCarrier`'s fixed list)
  4. `list_available_numbers` for a real area code returns real numbers (read-only, no order placed)
  5. Error path: malformed brand payload → Telnyx 4xx mapped correctly by the adapter (raises with useful message)
  6. **Webhook Ed25519** (G4): `fixtures/telnyx/real_webhook_capture.json` — if present, `verify_webhook_signature()` must return True for the captured real payload; if absent, skip with a message pointing at Step 3 capture instructions.
- **Explicitly excluded**: `send_message` against live numbers, `provision_number` (places a paid number order), `assign_number_to_campaign` against the live campaign. These belong to Tom's Step 3 E2E run.

### F.4 — Documentation (G2)

- `backend/.env.example`: add `SMS_CARRIER=mock`, `TELNYX_API_KEY=`, `TELNYX_PUBLIC_KEY=`, `TELNYX_MESSAGING_PROFILE_ID=`, `TELNYX_10DLC_MOCK=false` with one-line comments each.
- `dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md`: new §14 "Testing Modes (mock vs live)" with the 3-mode table from the spike findings + instructions for capturing a real webhook payload into the fixture (for G4).

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does campaign creation need an explicit `mock` param? | Telnyx docs say campaigns under a mock brand are mock ("Campaign created from mock brand"). Engineer verifies at implementation; add flag if required (F.2). |
| New endpoints or schema? | Neither — adapter + tests + docs only. |
| Live SMS in automated tests? | **No** — reserved for Tom's Step 3 E2E run (cost + compliance). |
| Where do the real-API tests live? | `tests/integration/` alongside the existing (SDK-patched) Telnyx file; that file is left untouched. |
| Dev API key hygiene | Separate tagged dev key per baseline research; never commit keys; `.env.example` documents names only. |

## Handoff

Python Engineer prompt: `batch-telnyx-int-1-python-engr-prompt.md`. No FE companion. On close: update launch plan row 9 → record real-API test results; Tom proceeds with Step 3 (live number config + E2E SMS, which also delivers the G4 webhook capture fixture).

**Post-batch Architect task (Tom decision 2026-08-09)**: After the Python Engineer's completion summary, the **Architect** rewrites `telnyx-rec-api-integration-testing-approach.md` from a generic research note into the canonical **setup-and-run guide** for both testing modes — exact env vars, API-key setup (dev key creation in Mission Control: separate tagged key, expiration, never committed), the three modes (in-memory mock / Telnyx-mock / live), exact pytest invocations, fee guardrails, and the Step 3 live-SMS + webhook-capture procedure. The engineer does NOT edit that doc — the Architect finalizes it against what was actually built (flag semantics, fixture paths, final commands) so the doc matches reality, not the plan.
