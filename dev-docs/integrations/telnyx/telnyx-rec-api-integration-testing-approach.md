# Telnyx Testing — Setup & Run Guide (Canonical)

**Version**: 2.0
**Date**: 2026-08-09
**Author**: Pilot Architect
**Status**: ACTIVE — the authoritative "how to set up and run Telnyx tests" guide
**Supersedes**: v1.0 generic research note (preserved as Appendix A)
**Sources**: TELNYX-SPIKE-1 findings (`archived/telnyx-spike-1-findings.md` — archived 2026-08-20) + TELNYX-INT-1 as-built implementation (closed 2026-08-09)

---

## 1. The three testing modes

All modes are selected by environment variables at the `get_sms_carrier()` factory seam (`backend/services/sms_carrier.py`). Nothing else changes code-path.

| Mode | Env vars | What happens | Cost | Use |
|---|---|---|---|---|
| **1. In-memory mock** (default) | `SMS_CARRIER=mock` | `MockSmsCarrier` — pure Python fake, zero network calls, deterministic IDs | $0 | Unit tests, E2E suite, CI, local dev default |
| **2. Telnyx-mock** | `SMS_CARRIER=telnyx` + `TELNYX_API_KEY=<dev key>` + `TELNYX_10DLC_MOCK=true` | Real Telnyx API calls; 10DLC brands/campaigns created as **mock objects** on Telnyx's servers | $0 (no TCR fees) | Real-API provisioning-flow + webhook integration tests |
| **3. Telnyx-live** | `SMS_CARRIER=telnyx` + live keys, `TELNYX_10DLC_MOCK` unset/false | Real brands, real SMS, real fees | Real | Production; Tom's Step 3 E2E SMS test; final pre-launch verification |

**Critical constraints:**
- `TELNYX_10DLC_MOCK` is only read when `SMS_CARRIER=telnyx`. With `SMS_CARRIER=mock` it is ignored entirely.
- Mock campaigns **cannot carry SMS traffic** (Telnyx platform constraint). There is no "mock brand + real SMS" combination — real SMS requires the live approved campaign (`CXXXXXX`).
- Campaigns under a mock brand are mock **by inheritance** — no `mock` flag is passed on campaign creation (verified against Telnyx Help Center: *"During creation of the brand set the 'mock' field to true. Once you've created your mock brand, create a 10DLC campaign as normal."*).
- When `TELNYX_10DLC_MOCK=true`, `TelnyxSmsCarrier.__init__` logs a loud WARNING — if you ever see that warning in prod logs, the environment is misconfigured.

---

## 2. One-time setup

### 2.1 API keys (Mission Control)

1. Log into [Mission Control](https://portal.telnyx.com) → **API Keys**.
2. **Dev key** (for Mode 2 testing): create a new key, tag it (e.g. `pilot-dev-testing`), set an expiration date. This isolates dev/testing from production credentials per Telnyx best practice.
3. **Prod key**: lives only in AWS Secrets Manager `pilot/prod/telnyx` (Step 3). Never copy it locally.
4. **Public key** (for webhook signature verification): Mission Control → **Account Settings → Keys & Credentials → Public Key** (Ed25519, base64). Same key signs all webhook deliveries, all modes.
5. **Never commit keys.** `backend/.env.example` documents variable names only.

### 2.2 Local `.env` (backend)

```bash
# Mode 1 (default — safe):
SMS_CARRIER=mock

# Mode 2 (real API, mock objects — for running the integration suite):
SMS_CARRIER=telnyx
TELNYX_API_KEY=KEY...            # the DEV key from §2.1
TELNYX_PUBLIC_KEY=...            # Ed25519 public key (base64)
TELNYX_MESSAGING_PROFILE_ID=...  # only needed for outbound send tests (Step 3)
TELNYX_10DLC_MOCK=true           # the fee guard — REQUIRED for brand/campaign tests
```

### 2.3 Production (ECS task definition)

`SMS_CARRIER=telnyx`, keys from Secrets Manager `pilot/prod/telnyx`, **`TELNYX_10DLC_MOCK` must be unset or `false`**. Verify this before the Step 3 live test — a prod task running in mock mode would register tenant brands as non-functional mock objects.

---

## 3. Running the tests

### 3.1 Unit tests (Mode 1 — default, CI-safe)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q | tail -5
```

Includes the `TELNYX_10DLC_MOCK` flag behavior tests in `tests/batch_b11/test_a59_sms_carrier_adapter.py` (mock=True payload assertion, init WARNING, factory routing regression). No keys needed.

### 3.2 Real-API integration suite (Mode 2 — $0)

File: `backend/tests/integration/test_telnyx_real_api.py` · markers: `integration`, `requires_telnyx`

```bash
cd <repo>/backend
source .venv/bin/activate
TELNYX_API_KEY=<dev key> TELNYX_PUBLIC_KEY=<pubkey> TELNYX_10DLC_MOCK=true \
    pytest tests/integration/test_telnyx_real_api.py -v
```

**Behavior without keys**: the entire module skips cleanly — zero failures in CI.

**Fee guard**: brand/campaign creation tests **hard-refuse to run** unless `TELNYX_10DLC_MOCK=true` — a developer with a live key cannot accidentally submit fee-bearing TCR registrations.

**Scenarios (6):**
1. Mock brand create → retrieve (verify `brand_id`, status, `_mock_10dlc` flag active)
2. Mock campaign create under mock brand → poll
3. `get_verticals()` returns the real enum list
4. `list_available_numbers()` — read-only number search, no order placed
5. Malformed brand payload → Telnyx 4xx surfaces correctly (not swallowed)
6. Ed25519 webhook signature verification against a captured real payload (skips until the fixture exists — see §4)

**Excluded by design** (reserved for Step 3, Mode 3): `send_message` (live SMS), `provision_number` (paid number order), `assign_number_to_campaign` on the live campaign.

### 3.3 Cleanup of test artifacts

Mock brands/campaigns accumulate on the Telnyx account. Clean them with:

```bash
cd <repo>/backend
source .venv/bin/activate
TELNYX_API_KEY=<dev key> python scripts/cleanup_telnyx_mocks.py
```

**Safety**: the script only touches objects where `mock=True` — real (non-mock) brands/campaigns like `CXXXXXX` are never deleted.

### 3.4 Legacy SDK-patched suite

`tests/integration/test_telnyx_sms_integration.py` (B21/FIND-173 era) patches the SDK and never hits the real API. Retained for error-path coverage; the real-API suite above is the authoritative live-behavior check.

---

## 4. Step 3 — live E2E SMS test (Mode 3) + Ed25519 capture

Precondition: `pilot/prod/telnyx` Secrets Manager configured with the assigned number + prod keys; ECS task def `SMS_CARRIER=telnyx`, `TELNYX_10DLC_MOCK` unset.

1. Follow the E2E test procedure in the 10DLC playbook §13 (`telnyx-10dlc-p4t-tenant-comms-campaign.md`) — send to **Pilot-owned devices only** (per-segment cost is pennies).
2. Verify delivery-receipt webhooks arrive at the ALB endpoint and `message.sent`/`message.finalized` statuses reconcile (DLC-B5 `_process_delivery_status` path).
3. **Capture one real webhook delivery** (raw HTTP body + `telnyx-signature-ed25519` + `telnyx-timestamp` headers) and save it to `backend/tests/integration/fixtures/telnyx/real_webhook_capture.json`:
   ```json
   {
     "payload": "<raw JSON body as a string>",
     "headers": {
       "telnyx-signature-ed25519": "<base64 signature>",
       "telnyx-timestamp": "<unix timestamp string>"
     }
   }
   ```
4. Re-run the Mode 2 suite — scenario 6 now verifies `verify_webhook_signature()` against a real Telnyx signature, closing spike gap G4.

---

## 5. Cost guardrails (hard rules)

- Never run brand/campaign creation without `TELNYX_10DLC_MOCK=true` outside production. (The suite enforces this; ad-hoc scripts must too.)
- Never re-submit the live brand/campaign without Tom's sign-off — TCR re-submission fees apply.
- Live SMS tests target Pilot-owned devices only.
- The cleanup script (`cleanup_telnyx_mocks.py`) is the only deletion tool for test artifacts; it is mock-scoped by design.
- Monitor spend: Mission Control → Billing during any live testing window.

---

## Appendix A — Original research note (v1.0, superseded)

Telnyx operates as a live production environment without a dedicated sandbox mode. Baseline strategies: portal-first familiarity, API-driven brand/campaign/number management, careful TCR-fee planning, separate API keys per environment with tags/expiration, optional dedicated test account, webhook-driven delivery validation, single test number + own-device messaging, and billing monitoring. Superseded by §§1–5 above, which reflect the implemented TELNYX-INT-1 architecture.
