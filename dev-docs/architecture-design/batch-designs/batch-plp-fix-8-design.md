# PLP-FIX-8 — Design: New-Device SMS Alert Recipient Resolution (INV-BUG-4)

**Batch**: PLP-FIX-8 (launch plan Ord 29, card §3.29) · **Type**: Backend-only (Python)
**Date**: 2026-09-04 · **Author**: Pilot Architect · **Status**: v1.0 — for Tom approval
**Findings source**: `tom-ui-issues-tracking.md` INV-BUG-4 + `team-invite-1-prod-test-plan.md` Tests 3/4 side-observation · **Estimate**: ~2 h
**Sequencing (Tom, 2026-09-04)**: executes **after** PLP-FIX-7 closes + deploys. Owner-visible "team member signed in" variant is **deferred — out of scope**.

---

## A. Input Read Summary

| Input | What it contributed | Read |
|---|---|---|
| `tom-ui-issues-tracking.md` INV-BUG-4 | Defect statement + Tom's expected behavior (alert the authenticating user, only after they add + verify a phone) | ✅ 2026-09-04 |
| `backend/lambda/post_authentication/handler.py` | Gate (`newDeviceUsed`), user resolution (email → `user.id` — currently discarded), per-tenant enqueue kwargs | ✅ |
| `backend/tasks/sms_platform_notifications.py` | Task signature (`tenant_id`, `type_code`, `template_context`), owner fan-out impl, retry/never-crash posture | ✅ (via call-site + test reads) |
| `backend/services/notification_endpoints.py` | `get_verified_owner_sms_endpoints(db, …)` — the consent/verification filter to reuse | ✅ (signature located; engineer reads body at pre-work) |
| `aws-cognito-prod-setup.md` §PLATFORM-SMS-B2 | Original design context (Sample 3, owner fan-out was single-user-era correct) + the 2026-09-04 device-tracking restore | ✅ |
| Other task callers | Backward-compat surface: `scripts/broadcast_maintenance_sms.py`, `services/stripe_subscriptions.py` | ✅ (grep census — 2 callers, neither passes user scoping) |

---

## B. Migration & Seed Plan

**None.** No schema change, no seed-data change (Seed Data Rollout explicitly N/A — this batch adds/modifies no DB data). MCP pre-work is verification-only:

```sql
-- 1. user_endpoint columns (verify the endpoint model the helper queries)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_endpoint' ORDER BY ordinal_position;
-- 2. Confirm user_endpoint scoping (tenant-scoped vs user-scoped rows) — informs the helper's WHERE clause
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_endpoint' AND column_name IN ('tenant_id','user_id','channel','verification_status','consent_status','is_primary');
-- 3. Current alembic head (record only — no migration)
SELECT version_num FROM public.alembic_version;
```

---

## C. Root Cause

`handler.py` resolves the authenticated `User` (it has `user.id` in hand) but enqueues only `tenant_id` + `type_code`. The task impl then resolves recipients as **all verified+opted-in OWNER SMS endpoints of the tenant** (`get_verified_owner_sms_endpoints`) — correct in the single-user era (owner == account), wrong since TEAM-INVITE-1: an employee's new-device sign-in texts the owner "New sign-in to **your** account". Wrong recipient, misleading copy for that case. The authenticated user never gets alerted — even after adding and verifying their own phone.

---

## D. New/Changed API Endpoints

None (no HTTP surface). Changed contracts:

1. **Celery task** `send_platform_account_notification_sms` — new **optional** kwarg `recipient_user_id: str | None = None`. Present → recipients = that user's verified+opted-in SMS endpoints (scoped per the existing helper's filters). Absent → legacy owner fan-out (unchanged behavior for the 2 existing callers). Additive-kwarg is safe for in-flight messages enqueued by the old Lambda (they lack the kwarg → default).
2. **Post-Authentication Lambda** — kwargs gain `"recipient_user_id": str(user.id)` (the already-resolved user). No other behavior change: same gate, same per-tenant fan-out, same never-raise invariant.

---

## E. Pattern Reuse Decisions

1. **Consent/verification filters reuse** — the new user-scoped resolution MUST reuse the exact filter semantics of `get_verified_owner_sms_endpoints` (channel `sms` + `verification_status='verified'` + `consent_status='opted_in'` — engineer mirrors the existing helper's WHERE clause; do not invent new filter logic). Implemented as a sibling function `get_verified_user_sms_endpoints(db, *, tenant_id, user_id)` in `notification_endpoints.py`, sharing any existing private query-builder if one exists.
2. **Never-raise invariant** — the Post-Authentication handler stays log-and-swallow; the task keeps its retry/max-retries posture. No change.
3. **Static Sample 3 copy unchanged** — "New sign-in to your account from a new device…" is now *correct by recipient* (the account holder receives it). No template work (owner-variant deferred per Tom).

---

## F. Shared Module Interfaces

```python
# services/notification_endpoints.py (new sibling — mirror the existing helper's filters)
def get_verified_user_sms_endpoints(
    db: Session, *, tenant_id: str, user_id: str
) -> list[...]:  # same element shape as get_verified_owner_sms_endpoints
    """Verified + opted-in SMS endpoints for ONE user within the tenant."""

# tasks/sms_platform_notifications.py — impl signature extension
def _send_platform_account_notification_sms_impl(
    tenant_id: str,
    type_code: str,
    template_context: dict | None = None,
    recipient_user_id: str | None = None,   # NEW — user-scoped resolution when set
) -> dict: ...

# tasks/sms_platform_notifications.py — Celery task (additive kwarg, default None)
def send_platform_account_notification_sms(
    self, tenant_id: str, type_code: str,
    template_context: dict | None = None,
    recipient_user_id: str | None = None,
) -> dict: ...

# lambda/post_authentication/handler.py — kwargs per tenant
producer.send_task(_TASK_NAME, kwargs={
    "tenant_id": str(tid),
    "type_code": _TYPE_CODE,
    "recipient_user_id": str(user.id),   # NEW
})
```

Recipient-selection rule in the impl: `if recipient_user_id is not None → get_verified_user_sms_endpoints(...)` else `get_verified_owner_sms_endpoints(...)`. Log line names the resolution mode (`recipient=user` vs `recipient=owners`). No-endpoints case stays a quiet skip (existing "no verified+opted-in … skipping" info log — correct: a tech with no verified phone gets no SMS).

---

## G. Open Questions Resolved

1. **New task vs. kwarg?** → Optional kwarg on the existing task. One delivery path, zero duplication, additive-compatible with in-flight messages.
2. **Where does user-scoping live?** → In the task impl (not the Lambda) — the Lambda stays a thin producer; resolution logic + tests live with the other recipient logic in the worker.
3. **Owner alert on employee sign-in?** → Deferred (Tom, 2026-09-04). No owner fan-out for `platform_security_new_device` after this batch — the owner is alerted only for their *own* new-device sign-ins (they're the authenticated user in that case).
4. **Multi-tenant users** → per-tenant fan-out preserved; each task resolves the user's endpoints **in that tenant** (engineer verifies `user_endpoint` scoping via MCP B.2 and scopes the helper's WHERE accordingly).
5. **Copy change?** → None — correct-by-recipient (§E.3).
6. **Deploy mechanics** → Task change rides the normal worker image deploy; the Lambda change rides the existing `build-post-authentication-lambda.sh` + Terraform path (noted for Tom/DevOps — the runbook §14.5 documents it; no new infra). **Order: worker first, then the Lambda** (old Lambda messages lack the kwarg → default → owner fan-out until the Lambda lands — acceptable transition; reverse order would be silent-loss-free too but worker-first is the natural image deploy).
7. **Seed Data Rollout** → N/A (no DB data change; stated per Rule 11.5 discipline).

## Verification (Tom, post-deploy)

1. office1 (no verified phone) signs in from a fresh browser → **no SMS to anyone**.
2. Owner signs in from a fresh browser → SMS to the **owner's** verified phone only (unchanged).
3. (Optional, if a test user has a verified phone) employee sign-in → SMS to the **employee's** phone only.
4. Worker logs show `recipient=user` for `platform_security_new_device`; broadcast/payment-failed paths show `recipient=owners`.
