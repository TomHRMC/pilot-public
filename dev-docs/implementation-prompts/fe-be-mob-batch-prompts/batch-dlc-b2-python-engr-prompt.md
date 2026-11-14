# Implementation Prompt: DLC-B2 (Backend) — 10DLC Customer-Comms Campaign Compliance Fixes

**Mode**: Pilot Python Engineer
**Batch**: DLC-B2 (Python half — runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 (DLC-B2 card, §2.0 row #9)
**Design doc**: None — this is a copy/cleanup batch; the compliant strings are specified inline below and in the submission playbook.
**Submission playbook**: `dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md` — §7 (keywords) and §8 (auto-reply strings) are the source of truth for every string you set.
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: `batch-dlc-b2-react-engr-prompt.md` (customer-consent disclosure UI) — runs AFTER you finish and hand off.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow), §8 (Router Design). No Alembic or model changes in this batch, but follow the standard workflow.
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules.
- **`dev-docs/integrations/mfa-integration-approach.md`** — the 6-finding audit that defines this batch. Findings 1, 2, 3, 4, 5, 6 map directly to your tasks.
- **`dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md`** — §8 has the EXACT strings you must emit. Copy them character-for-character.

**Critical rules for this batch:**

- **Rule 1**: Never guess column/table names. Use `postgres-local` MCP to verify before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 5**: Never use module-level `TestClient`. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is banned on tenant-scoped models. Use tenant-scoped `select()` with explicit `WHERE tenant_id`.
- **Rule 7**: `postgres-local` MCP is **read-only verification only**. Never INSERT/UPDATE/DELETE through it.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. No "not my fault" exception. If you cannot find the root cause → STOP and ask Tom.

- **⚠️ String-exactness rule (batch-specific, highest risk)**: The auto-reply strings you set in code are submitted verbatim to Telnyx/TCR by Tom. If the code string and the submitted string differ by even one word, MNO review fails (rejection code 806 — this already happened once with the `CYYYYYY` campaign). Copy the strings from §8 of the submission playbook EXACTLY — including punctuation, capitalization, and word order. Do not "improve" them.

---

## Background / Context

Pilot has **two separate SMS pathways** (see `pilot-operations.md §13.12`):
- **Pathway A — MFA OTP** → AWS Cognito → AWS SNS. No Telnyx, no 10DLC campaign. Not touched by this batch.
- **Pathway B — Customer communications** → `TelnyxSmsCarrier`. **This is what the new "Mixed" 10DLC campaign covers.**

The first campaign (`CYYYYYY`) was mis-filed as "2FA" and deleted. Tom is submitting a fresh **Mixed** campaign for customer comms. For MNO review to pass, the STOP/START/HELP auto-replies and the double opt-in message that the code emits must exactly match the copy submitted to Telnyx, and undeclared keywords must be documented. Your job is to make the code emit the compliant strings and remove dead Twilio code.

**This is a copy + cleanup batch. No schema changes, no new endpoints, no migration.**

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: do NOT treat them as "pre-existing." Either (a) confirm with Tom it's a known accepted failure, or (b) fix it before touching batch files. You may NOT start while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` is **read-only verification only**. Never INSERT/UPDATE/DELETE. If a query errors → STOP and ask Tom.

Run these via `postgres-local` MCP before writing any code. This batch has no schema changes, but you must confirm the tables the touched code reads still have the columns the code references:

```sql
-- 1. Confirm customer_sms_consent_audit action constraint values (do NOT add a new action code)
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.customer_sms_consent_audit'::regclass AND contype = 'c';

-- 2. Confirm tenant_10dlc_profile columns the auto-reply code reads (legal_business_name, support_phone)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_10dlc_profile'
AND column_name IN ('legal_business_name', 'support_phone', 'support_email')
ORDER BY ordinal_position;

-- 3. Confirm tenant_phone_number resolution columns (phone_number, status)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_phone_number'
AND column_name IN ('phone_number', 'status', 'tenant_id')
ORDER BY ordinal_position;

-- 4. Confirm the live SMS templates (for cross-checking Tom's portal samples — read only, no change)
SELECT template_code, body_template
FROM public.communication_template
WHERE channel = 'sms'
ORDER BY template_code;
```

**Expected**: the `action` CHECK is `IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out')` — you are NOT adding a new action value. `legal_business_name` and `support_phone` exist on `tenant_10dlc_profile`. If anything differs → STOP and ask Tom.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/services/customer_communication_threading.py   ← the STOP/START/HELP handlers you are editing (lines ~283, ~374, ~431)
backend/tasks/sms_compliance.py                         ← the double opt-in template you are hardening (line ~26)
backend/api/routes/webhooks_sms.py                      ← keyword sets; add YES/ARRET declaration comment
backend/services/sms_service.py                         ← dead Twilio file to DELETE
backend/api/routes/webhooks.py                          ← confirms Twilio was replaced by Telnyx (context for deletion)
backend/services/telnyx_sms_carrier.py                  ← the real Pathway B carrier (context — do not change)
backend/tests/domains/notifications_comms/test_dlc1_sms_compliance.py  ← existing tests you will extend
backend/.env.example                                    ← remove Twilio vars
```

Also grep for any remaining Twilio references before deleting the file:

```bash
grep -rn "twilio\|TWILIO\|sms_service" backend/ --include="*.py" -l
```

> If `sms_service.send_sms` is imported anywhere other than its own tests, STOP and ask Tom — do not delete a file that has live callers.

---

## Task 1 — Fix the STOP auto-reply (Finding 1)

**File**: `backend/services/customer_communication_threading.py` (~line 283, inside the opt-out handler)

**Current** (non-compliant — missing brand + re-subscribe instruction):
```python
body="You have been unsubscribed. No more messages will be sent.",
```

**Change to** (exact string from playbook §8):
```python
body=(
    "You have been unsubscribed from Pilot for Trades messages. "
    "No further messages will be sent. Reply START to re-subscribe."
),
```

Run: `python -m pytest -m unit backend/tests/domains/notifications_comms/ --tb=short -q 2>&1 | tail -5`

---

## Task 2 — Fix the opt-in (START/UNSTOP/YES) auto-reply (Finding 2)

**File**: same file (~line 374, inside `handle_sms_opt_in`)

> **Important context**: this handler serves BOTH the double-opt-in YES confirmation AND a later re-opt-in via START. Keep it generic to customer comms — do NOT reintroduce MFA/"login verification" framing (that was the `CYYYYYY` mistake). Read the surrounding function first; note it currently interpolates `{business_name}` — the compliant string below drops that interpolation in favor of the fixed brand line, which is what Tom submits to Telnyx. Confirm removing `business_name` here does not leave an unused variable that breaks lint (remove the now-unused lookup if it is only used for this string).

**Current**:
```python
body=(
    f"Pilot for Trades: You've opted back in to updates from {business_name}. "
    "Reply HELP for help. Msg freq may vary. Msg & Data rates may apply. "
    "Reply STOP to cancel."
),
```

**Change to** (exact string from playbook §8):
```python
body=(
    "Pilot for Trades: You're opted in to receive service updates. "
    "Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
),
```

> If `business_name` (and its `Tenant10DlcProfile` lookup above it) becomes unused after this change, remove the now-dead lookup block to keep Ruff clean. Verify with `grep -n "business_name" ` in the function scope before removing.

Run unit tests for the domain again.

---

## Task 3 — Fix the HELP auto-reply (Finding 3)

**File**: same file (~line 431, inside `handle_sms_help`)

**Current** (non-compliant — missing website + email, wrong framing):
```python
body = (
    f"Pilot for Trades alerts for {business_name}. "
    f"Reply STOP to cancel. Msg&Data rates apply. "
    f"Contact {support_phone} for help."
)
```

**Change to** (exact string from playbook §8):
```python
body = (
    "Pilot for Trades service messages. "
    "For help, visit pilotfortrades.com or email info@pilotfortrades.com. "
    "Msg & data rates may apply. Reply STOP to unsubscribe."
)
```

> Same cleanup note: if `business_name` / `support_phone` and their `Tenant10DlcProfile` lookup become unused after this change, remove the dead lookup. Check with grep first — the lookup block spans several lines above (~line 425). Removing an unused DB query is preferred; leaving a now-unused variable will trip Ruff.

Run unit tests for the domain again.

---

## Task 4 — Harden the double opt-in message (the highest-scrutiny message)

**File**: `backend/tasks/sms_compliance.py` (~line 26, `_DOUBLE_OPTIN_TEMPLATE`)

This is the FIRST message a consumer ever receives — MNO reviewers scrutinize it most. It currently lacks two required disclosures ("Msg & data rates may apply" and "Reply HELP for help").

**Current**:
```python
_DOUBLE_OPTIN_TEMPLATE = (
    "Hi {first_name}, {business_name} uses Pilot for Trades for service updates. "
    "Reply YES to confirm you want to receive texts. Reply STOP to cancel."
)
```

**Change to** (exact string from playbook §8):
```python
_DOUBLE_OPTIN_TEMPLATE = (
    "Hi {first_name}, {business_name} uses Pilot for Trades for service updates. "
    "Reply YES to confirm you want to receive texts. "
    "Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)
```

> Keep the `{first_name}` and `{business_name}` placeholders — they are `.format()`ed at `sms_compliance.py`. Do not change the `.format()` call.

Run: `python -m pytest -m unit backend/tests/domains/notifications_comms/test_dlc1_sms_compliance.py --tb=short -q 2>&1 | tail -10`

> The existing test `test_send_double_optin_sms_impl_*` may assert on the old body substring. Update those assertions to match the new disclosures (assert the presence of "Reply YES", "Msg & data rates", "Reply HELP" — not the entire string, to stay resilient).

---

## Task 5 — Document YES + ARRET keywords (Findings 4 & 5)

**File**: `backend/api/routes/webhooks_sms.py`

The code already **handles** `yes` (line ~38, `_OPTIN_KEYWORDS`) and `arret` (line ~36, `_STOP_KEYWORDS`) — they just were not declared in the `CYYYYYY` submission. No behavior change needed. Add a comment block above the keyword frozensets so the code is self-documenting and matches what Tom declares in the portal (playbook §7):

```python
# TCPA keyword sets (case-insensitive, exact-match on stripped body).
# These MUST match the keywords declared in the Telnyx customer-comms campaign.
# See dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md §7.
#   Opt-out:  STOP, STOPALL, UNSUBSCRIBE, QUIT, CANCEL, END, ARRET (French STOP)
#   Opt-in:   START, UNSTOP, YES
#   Help:     HELP, INFO
```

No functional change — the frozensets already contain these values (verified). Do not alter the sets.

---

## Task 6 — Delete dead Twilio code (Finding 6)

Twilio was replaced by Telnyx in B11/A59 (confirmed in `webhooks.py` comment). `sms_service.py` imports `twilio` and is dead.

1. **Verify no live callers** (only its own tests should reference it):
   ```bash
   grep -rn "from services.sms_service\|import sms_service\|sms_service\." backend/ --include="*.py"
   ```
   If any non-test file imports it → STOP and ask Tom.

2. **Delete** `backend/services/sms_service.py`.

3. **Delete any test file** that exists solely to test `sms_service` (e.g. a `test_sms_service.py`). If Twilio assertions are embedded in a broader test file, remove only those tests. Confirm with grep first.

4. **Remove Twilio vars from** `backend/.env.example`:
   ```bash
   grep -n "TWILIO" backend/.env.example
   ```
   Remove `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` lines.

5. **Check `core/config.py`** for `TWILIO_*` settings fields — if present and unused after deletion, remove them. Grep first:
   ```bash
   grep -rn "TWILIO" backend/ --include="*.py"
   ```
   If removing them from `settings` breaks an import → fix that import. There must be zero `twilio` references left in `backend/` when done (except possibly in a requirements lock — leave `requirements.txt` alone unless Tom asks).

Run the full domain test group after deletion to confirm nothing imported the deleted module:
```bash
python -m pytest -m unit backend/tests/domains/notifications_comms/ --tb=short -q 2>&1 | tail -10
```

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

Extend `backend/tests/domains/notifications_comms/test_dlc1_sms_compliance.py` (do not create a new file — this is the canonical SMS-compliance test home).

**Add/adjust tests** (all with `pytestmark = [pytest.mark.domain_notifications_comms, pytest.mark.unit]`):

1. `test_opt_out_reply_is_compliant` — invoke `handle_sms_opt_out`, capture the `MockSmsCarrier` sent body, assert it contains `"Pilot for Trades"`, `"No further messages"`, and `"Reply START"`.
2. `test_opt_in_reply_is_compliant` — assert the START/YES reply contains `"opted in"`, `"Msg & data rates may apply"`, `"Reply HELP"`, and does NOT contain `"login"` or `"verification"` (guards against MFA-framing regression).
3. `test_help_reply_is_compliant` — assert HELP reply contains `"pilotfortrades.com"`, `"info@pilotfortrades.com"`, `"Msg & data rates may apply"`, `"Reply STOP"`.
4. `test_double_optin_message_has_required_disclosures` — assert `_DOUBLE_OPTIN_TEMPLATE` (or the rendered body) contains `"Reply YES"`, `"Msg & data rates may apply"`, and `"Reply HELP"`.
5. Update any existing assertion that checked the OLD body strings so the suite stays green.

**Test resilience**: use `MockSmsCarrier` (see existing `test_send_double_optin_sms_impl_*` tests for the pattern) — never hit a real carrier. Assert on substrings, not full-string equality, so minor punctuation tweaks don't force test churn. Use `test_tenant`/`test_customer` fixtures — no hardcoded UUIDs. Never assert total row counts.

Use the `MockSmsCarrier` via `patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier)` exactly as the existing tests do.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before Phase 2.

### Phase 2 — Full Suite (run once, at the end)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest backend/tests/domains/notifications_comms/test_dlc1_sms_compliance.py -v 2>&1 | tail -30

# Confirm zero Twilio references remain
grep -rn "twilio\|TWILIO" backend/ --include="*.py" || echo "NO TWILIO REFS — GOOD"

echo "=== DLC-B2 BACKEND FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before the batch is done. No "pre-existing failure" exception without Tom's written confirmation.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) via `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — action constraint + profile/phone columns confirmed
- [ ] All mandatory source files read before writing code
- [ ] **Task 1**: STOP reply string matches playbook §8 exactly
- [ ] **Task 2**: opt-in reply string matches playbook §8 exactly; no MFA/login framing; unused `business_name` lookup removed if orphaned
- [ ] **Task 3**: HELP reply string matches playbook §8 exactly; unused lookup removed if orphaned
- [ ] **Task 4**: double opt-in template hardened with freq + rates + HELP
- [ ] **Task 5**: keyword-declaration comment added to `webhooks_sms.py`; frozensets unchanged
- [ ] **Task 6**: `sms_service.py` deleted; Twilio `.env.example` vars removed; `core/config.py` Twilio settings removed; zero `twilio` refs in `backend/**/*.py`
- [ ] 5 compliance tests added/updated in `test_dlc1_sms_compliance.py`
- [ ] Ruff clean (`ruff check backend/ --fix && ruff format backend/`)
- [ ] **Phase 1**: all unit tests pass — zero failures
- [ ] **Phase 2**: full suite passes — zero failures including integration
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B
- [ ] **Handoff performed** (see below)

---

## Handoff Instructions (MANDATORY — this batch has a frontend companion)

This batch does **not** change any endpoint, so `openapi.json` is unaffected and `pnpm sync-api-types` is **not** required for the React half. However, you MUST still hand off:

1. Commit your work with a clear message: `DLC-B2 backend: compliant SMS auto-reply strings + double opt-in hardening + Twilio removal`.
2. Notify the React Engineer that the backend half is complete and they may start `batch-dlc-b2-react-engr-prompt.md` (the customer-consent disclosure UI).
3. In your Completion Summary, paste the FINAL compliant strings you set for STOP/START/HELP/double-opt-in so Tom can copy them into the Telnyx portal (they must match `telnyx-10dlc-customer-comms-campaign.md §8`). If you deviated from the playbook strings for any reason, flag it explicitly — Tom submits these verbatim to Telnyx.

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `pilot-launch-plan.md` Appendix B using the standard template. Include a **"Compliant strings as shipped"** subsection quoting the exact STOP/START/HELP/double-opt-in bodies, so the launch plan and the Telnyx submission playbook stay in sync.

```markdown
### DLC-B2 (Backend) — 10DLC Customer-Comms Compliance: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- Compliant STOP/START/HELP auto-reply strings (Findings 1–3)
- Double opt-in message hardened with freq + rates + HELP disclosures (Finding 0-adjacent)
- YES/ARRET keywords documented (Findings 4–5)
- Dead Twilio `sms_service.py` + env vars + config removed (Finding 6)

#### Compliant Strings As Shipped
- STOP: "..."
- START/YES: "..."
- HELP: "..."
- Double opt-in: "..."

#### Files Changed / Created
| File | Action |
|---|---|
| ... | ... |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/notifications_comms/test_dlc1_sms_compliance.py` | `notifications_comms` | 5 | ✅ |
```

---

## After This Task — Next Step

Hand off to the React Engineer for `batch-dlc-b2-react-engr-prompt.md`. Once both halves are merged and deployed to production, Tom takes the customer-consent screenshot and submits the Mixed campaign per `telnyx-10dlc-customer-comms-campaign.md`.
