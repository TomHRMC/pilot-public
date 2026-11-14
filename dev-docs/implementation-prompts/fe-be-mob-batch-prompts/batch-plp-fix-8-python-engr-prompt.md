# Implementation Prompt: PLP-FIX-8 — New-Device SMS Alert Recipient Resolution

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-8 (launch plan Ord 29, card §3.29)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.29
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-8-design.md` — read fully (A–G)
**Estimated session**: ~2 hours
**Platform**: Backend only (`backend/`) — worker task + Lambda handler source (no infra work)
**Sequencing**: executes **after** PLP-FIX-7 closes + deploys (Tom, 2026-09-04). Confirm with Tom that the PLP-FIX-7 deploy has landed before starting.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: `postgres-local` MCP is read-only verification. All data changes go through application code.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. No exceptions without Tom's written confirmation.
- **Rule 12 (sync routes)**: every DB-touching function is a plain `def` — the task impl and the Lambda handler are sync by design; keep them that way.
- **Rule 14 (Ruff)**: run ruff **only against changed files** — fix ALL errors in those files, including pre-existing ones.
- **Rule 16 (verify, don't assume)**: query `information_schema.columns` for `user_endpoint` before writing the new helper's SQL.

---

## Context: What This Batch Does

**INV-BUG-4**: on every new-device sign-in, the tenant **owner's** phone gets *"Pilot for Trades: New sign-in to your account from a new device…"* — even when the person who signed in was an employee. Root cause (design §C): the Post-Authentication Lambda resolves the authenticated user but enqueues only `tenant_id` + `type_code`; the task then fans out to **all verified+opted-in owner SMS endpoints** — a single-user-era design that predates team invites.

The fix (design §D/§F — an additive contract change, three files):

1. `backend/services/notification_endpoints.py` — new sibling `get_verified_user_sms_endpoints(db, *, tenant_id, user_id)` mirroring `get_verified_owner_sms_endpoints`' filter semantics (channel `sms` + `verification_status='verified'` + `consent_status='opted_in'`) scoped to ONE user.
2. `backend/tasks/sms_platform_notifications.py` — `_send_platform_account_notification_sms_impl` + the Celery task gain optional `recipient_user_id: str | None = None`. Present → user-scoped resolution; absent → legacy owner fan-out (the 2 other callers — `scripts/broadcast_maintenance_sms.py`, `services/stripe_subscriptions.py` — are untouched and must see zero behavior change).
3. `backend/lambda/post_authentication/handler.py` — pass `"recipient_user_id": str(user.id)` (the already-resolved user) in the per-tenant kwargs. The never-raise invariant is absolute here: an unhandled raise fails the user's sign-in.

**Out of scope** (design §G): the owner-visible "team member signed in" variant (deferred per Tom); any copy change; any device-tracking change; Lambda packaging/deploy mechanics (Tom/DevOps rides the existing `build-post-authentication-lambda.sh` path at deploy).

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Any pre-existing failure → confirm with Tom or fix first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** via `postgres-local` MCP before writing any code. Unexpected results → **STOP and ask Tom**.

```sql
-- 1. user_endpoint columns (the endpoint model the new helper queries)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_endpoint'
ORDER BY ordinal_position;

-- 2. Scoping fields the WHERE clause needs (channel / verification / consent / tenant)
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_endpoint'
  AND column_name IN ('tenant_id','user_id','channel','verification_status','consent_status','is_primary','value');

-- 3. Sanity: tenant_user_role exists and office_staff/technician rows are present (context only)
SELECT code FROM public.tenant_user_role ORDER BY code;

-- 4. Current alembic head (record only — no migration in this batch)
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Mandatory File Reads

1. `backend/services/notification_endpoints.py` — the full `get_verified_owner_sms_endpoints` function (you mirror its filters)
2. `backend/tasks/sms_platform_notifications.py` — the impl + task wrapper + retry posture
3. `backend/lambda/post_authentication/handler.py` — `_enqueue_new_device_alerts` + the never-raise entry point
4. `backend/tests/domains/notifications_comms/test_platform_sms_b1_payment_failed_sender.py` — the existing impl test patterns (mixed consent states)
5. `backend/tests/domains/identity_access/test_post_authentication_handler.py` — the existing Lambda kwargs assertion you extend
6. `backend/tests/domains/notifications_comms/test_platform_sms_b2_template_context.py` — the `template_context` extension pattern (your `recipient_user_id` follows the same shape)

---

## Tasks

### Task 1 — `get_verified_user_sms_endpoints` (design §F)

In `notification_endpoints.py`: new sibling function with the exact design §F signature. Mirror the owner helper's WHERE semantics (same channel/verification/consent filters — verify against the live `user_endpoint` columns from MCP query 1–2) scoped to `user_id` (+ tenant scope per the model's scoping — if `user_endpoint` rows are tenant-scoped, filter `tenant_id` too; if user-scoped, scope by `user_id` only and note it in the Completion Summary). Return the same element shape as the owner helper so the task's send loop is untouched.

### Task 2 — Task impl + wrapper: `recipient_user_id` branch (design §D.1/§F)

- `_send_platform_account_notification_sms_impl(...)` gains `recipient_user_id: str | None = None`; recipient selection: `if recipient_user_id is not None → get_verified_user_sms_endpoints(db, tenant_id=tenant_id, user_id=recipient_user_id)` else the owner helper. Log lines name the mode (`recipient=user …` / `recipient=owners …`). The no-endpoints skip path, send loop, and retry posture are unchanged.
- The Celery task wrapper gains the same optional kwarg and forwards it (additive — in-flight messages without the kwarg deserialize with the default; do NOT bump task names or routing).
- Type hints modern (`str | None`); ruff clean in the changed files.

### Task 3 — Lambda kwargs (design §D.2)

In `handler.py` `_enqueue_new_device_alerts`: add `"recipient_user_id": str(user.id)` to the per-tenant kwargs dict. Nothing else changes — gate, tenant loop, never-raise, logging.

### Task 4 — Tests

Domain folders per `README-adding-tests.md`:

1. **`tests/domains/notifications_comms/`** — extend the impl test module (or a sibling per the README structure): (a) `recipient_user_id` present → only that user's verified+opted-in SMS endpoints receive (build a fixture set with: target user verified+opted-in, target user opted-out, target user unverified, OTHER tenant user verified+opted-in — assert ONLY the first is sent); (b) `recipient_user_id` absent → legacy owner fan-out unchanged (regression); (c) target user with no verified+opted-in endpoint → quiet skip, no send, no exception.
2. **`tests/domains/identity_access/test_post_authentication_handler.py`** — extend the existing enqueue assertion: kwargs now include `recipient_user_id` equal to the resolved user's id (per-tenant, multi-tenant case keeps one task per tenant each carrying the same user id); gate-absent and no-user paths still enqueue nothing.
3. Conventions: `pytestmark` domain marker + `pytest.mark.unit`; `test_tenant`/`test_user` fixtures (no hardcoded UUIDs); autouse fixture opt-outs per the README table; no module-level `TestClient` (n/a here, but the rule stands).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Vendor-suite inclusion call for THIS batch: NOT required — the SMS send path itself is
# not modified (recipient selection only); requires_telnyx covers the carrier adapter, untouched.

# Batch-specific spot checks
python -m pytest tests/domains/notifications_comms/ -k "platform_sms" -v 2>&1 | tail -20
python -m pytest tests/domains/identity_access/test_post_authentication_handler.py -v 2>&1 | tail -20

echo "=== PLP-FIX-8 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without Tom's written confirmation. Root cause unidentifiable → STOP and ask Tom.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [x] Pre-modification regression baseline captured (`4831 passed, 1 skipped`) using `pytest -m unit`
- [x] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [x] All MCP pre-work queries run — `user_endpoint` columns + scoping fields verified (rules §25)
- [x] All mandatory source files read before writing any code
- [x] Task 1: `get_verified_user_sms_endpoints` mirrors the owner helper's filters, scoped per the verified endpoint model; same element shape returned
- [x] Task 2: impl + Celery task accept `recipient_user_id` (additive, default None); branch selects user-scoped vs owner fan-out; log names the mode; other callers untouched
- [x] Task 3: Lambda kwargs carry `recipient_user_id: str(user.id)` per tenant; never-raise invariant intact
- [x] Task 4: (a) user-scoped send matrix test, (b) absent-kwarg legacy regression, (c) no-endpoints quiet-skip test, (d) Lambda kwargs assertions — all green
- [x] All new/modified functions are sync `def` (rules §21); Pydantic v2 idioms where applicable (rules §22)
- [x] `ruff check --fix && ruff format` on changed files only — zero remaining issues, no unjustified `# noqa` (rules §23)
- [x] **Phase 1**: All unit tests pass — zero failures including any pre-existing
- [x] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor inclusion call: NOT required (recorded in Completion Summary)
- [x] Final test count (before → after) documented (4831 → 4836, +5 new tests)
- [x] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [x] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan — if applicable (N/A — no separate spec doc)

---

## Completion Summary

After all Definition of Done items are complete, fill in the appendix at the end of THIS prompt doc using the format below. Include the deploy note for Tom: **worker image first, then the Lambda redeploy** via `infrastructure/scripts/build-post-authentication-lambda.sh` + Terraform (design §G.6); no prod verification until both land.

```markdown
### PLP-FIX-8 — New-Device SMS Recipient Resolution: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [recipient_user_id additive contract + user-scoped resolution + Lambda kwargs]
- [user_endpoint scoping note (tenant-scoped vs user-scoped — from MCP)]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/services/notification_endpoints.py` | Updated — ... |
| `backend/tasks/sms_platform_notifications.py` | Updated — ... |
| `backend/lambda/post_authentication/handler.py` | Updated — ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/notifications_comms/...` | `notifications_comms` | N | ✅ |
```

---

## After This Task — Next Step

Tom deploys (worker image → Lambda redeploy) and runs the design §Verification checks (employee sign-in → no owner SMS; owner sign-in → owner SMS; `recipient=user` in worker logs). The owner-visible "team member signed in" variant stays deferred per Tom (2026-09-04) — do not build it.

---

## Appendix — Completion Summary

### PLP-FIX-8 — New-Device SMS Recipient Resolution: Completion Summary

**Completed**: 2026-09-05
**Mode**: Pilot Python Engineer
**Baseline**: 4831 passed, 1 skipped, 96 deselected
**Final**: 4836 passed, 1 skipped, 96 deselected (+5 new tests)

#### What Was Accomplished

- Added `get_verified_user_sms_endpoints(db, *, tenant_id, user_id)` sibling to `notification_endpoints.py` — mirrors the owner helper's filter semantics (channel `sms` + `is_active=True` + `consent_status='opted_in'` + `verification_status='verified'`), scoped to a single `user_id`.
- Extended `_send_platform_account_notification_sms_impl` + the Celery task wrapper with additive `recipient_user_id: str | None = None`. Present → user-scoped resolution; absent → legacy owner fan-out (the 2 existing callers — `broadcast_maintenance_sms`, `stripe_subscriptions` — see zero behavior change). Log lines name the mode (`recipient=user` / `recipient=owners`).
- Updated the Post-Authentication Lambda `_enqueue_new_device_alerts` to pass `"recipient_user_id": str(user.id)` in the per-tenant kwargs. Never-raise invariant intact.
- **user_endpoint scoping note (from MCP)**: `user_endpoint` has NO `tenant_id` column — rows are user-scoped. The `tenant_id` parameter on the new helper is accepted for signature symmetry with the owner helper but the WHERE clause filters by `user_id` only. In the MVP single-trade model a user belongs to at most one tenant, so user-scoping is equivalent to tenant+user scoping.

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/services/notification_endpoints.py` | Updated — added `get_verified_user_sms_endpoints` sibling function |
| `backend/tasks/sms_platform_notifications.py` | Updated — `recipient_user_id` kwarg on impl + Celery task; user-scoped vs owner fan-out branch; mode-named log lines |
| `backend/lambda/post_authentication/handler.py` | Updated — kwargs carry `recipient_user_id: str(user.id)` per tenant |
| `backend/tests/domains/notifications_comms/test_platform_sms_recipient_user_resolution.py` | Created — 5 tests: user-scoped matrix (target receives, other user excluded, opted-out skip, unverified skip), legacy owner fan-out regression, no-endpoints quiet skip |
| `backend/tests/domains/identity_access/test_post_authentication_handler.py` | Updated — extended `test_two_active_tenants_two_calls` to assert `recipient_user_id` present in kwargs and equal to the resolved user's id (same user id across both per-tenant tasks) |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/notifications_comms/test_platform_sms_recipient_user_resolution.py` | `notifications_comms` | 5 | ✅ |
| `tests/domains/identity_access/test_post_authentication_handler.py` (extended) | `identity_access` | +1 assertion block | ✅ |

#### Deploy Note for Tom

**Order: worker image first, then the Lambda redeploy.**
1. Deploy the worker image (carries the `recipient_user_id` kwarg + user-scoped resolution).
2. Redeploy the Post-Authentication Lambda via `infrastructure/scripts/build-post-authentication-lambda.sh` + Terraform (carries the `recipient_user_id` kwarg in the enqueued task message).
3. No prod verification until both land. Old Lambda messages (pre-redeploy) lack the kwarg → default None → owner fan-out — acceptable transition window.

#### Vendor-Suite Inclusion Call

NOT required — the SMS send path itself (carrier adapter) is not modified; recipient selection logic only. `requires_telnyx` covers the carrier adapter, which is untouched.
