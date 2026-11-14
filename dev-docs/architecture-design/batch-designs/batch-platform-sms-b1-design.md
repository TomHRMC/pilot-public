# Batch Design: PLATFORM-SMS-B1 — Pathway C Platform SMS Templates (DB Single-Path) + Payment-Failed Sender

**Version**: 1.1
**Date**: 2026-08-10
**Author**: Pilot Architect
**Status**: ✅ **COMPLETE 2026-08-10**
**Architect decision (2026-08-10, closes §D open point)**: `SignupStateResponse.collected_data` **remains a generic `dict`** (`additionalProperties: true` in OpenAPI). `sms_consent_status` is carried at runtime inside `collected_data` without a named schema property — verified by the FU3 regression test and consumed by the FE via `collected_data.sms_consent_status`. Rationale: `collected_data` is an intentionally extensible wizard-data bag; typing it as a Pydantic model would couple the public response contract to wizard internals and force a schema change for every future wizard field. FE treats the key as an opaque runtime field (MSW-mocked). If a future batch needs strict typing of the whole bag, that is a deliberate contract change to design separately — not a retrofit. No ADR (reversible, single-endpoint scope).
**v1.1**: Scope addition — **SIGNUP-C-FU3** folded in (Tom decision 2026-08-10): add `sms_consent_status` to `GET /signup/{tenant_id}/state` `collected_data`. Discovered during the 10DLC Step 3 live test: the web phone page polls `collected_data.sms_consent_status === "opted_in"` (`page.tsx`) but `get_signup_state()` never includes the field → wizard hangs on "Check your phone" forever despite successful verification. §D updated: OpenAPI regeneration now required (additive response field).
**Mode**: Backend-only (Python Engineer)
**Estimate**: 3–4 hours
**Campaign**: Telnyx `CXXXXXX` (APPROVED 2026-08-07) — Pathway C, Mixed (Account Notifications + Customer Care)
**Canonical campaign doc**: `telnyx-10dlc-p4t-tenant-comms-campaign.md` §6 (samples) / §8 (auto-replies)
**Launch plan card**: `pilot-launch-plan.md` §2.3

---

## Purpose

Campaign `CXXXXXX` is approved with 5 registered sample messages + 4 registered auto-reply strings. Today only the double-opt-in flow works, and its strings live as **code constants** in two files. The `notification_template` table has **zero `sms`-channel rows** (MCP-verified 2026-08-09). This batch:

1. Moves **all** currently-live Pathway C SMS strings (double opt-in + STOP/START/HELP auto-replies) from code constants into system-default `notification_template` rows — **one content path for all Pilot→tenant SMS**.
2. Adds the **Sample 2 (failed payment)** template + sender, wired to the existing `invoice.payment_failed` Stripe webhook handler (the first real Account-Notifications traffic the campaign will carry — Charter billing).
2a. **(v1.1 — SIGNUP-C-FU3)** Fixes the `/state` ↔ phone-page contract bug: `collected_data` gains `sms_consent_status` (`"opted_in"` when the owner's SMS `user_endpoint.verification_status == "verified"`, else `"pending"`, else `null` when no SMS endpoint exists). Same domain (Pathway C consent), same engineer, 30-minute change.
3. Installs the **verbatim-match guardrail** (§6↔§8 code-match rule, error 806) as an automated test so no future edit silently drifts from the registered campaign strings.

**Explicitly out of scope** (documented follow-ons, not deferred ambiguity):

| Item | Owning batch |
|---|---|
| Sample 3 (new-device sign-in security alert) — needs a Cognito post-auth trigger | **PLATFORM-SMS-B2** (follow-on) |
| Sample 4 (scheduled maintenance broadcast) — needs an admin/ops broadcast trigger | **PLATFORM-SMS-B2** (follow-on) |
| Sample 5 (Customer Care support-ticket resolution, two-way) — needs the ticket system, `support`/`customer_care` categories, inbound threading | **SUPPORT-B1** (already queued, P2 — launch plan §2.4) |
| Per-tenant `notification_template` overrides of platform templates | Not planned — platform compliance strings are campaign-locked, not tenant-editable |

---

## A. Input Read Summary

| Input | Read? | Key facts taken |
|---|---|---|
| `telnyx-10dlc-p4t-tenant-comms-campaign.md` §6/§7/§8/§9 | ✅ | The 5 verbatim samples, 4 verbatim auto-replies, keyword sets, §6↔§8 code-match rule (error 806) |
| `telnyx-rec-api-integration-testing-approach.md` | ✅ | 3 carrier modes; real SMS only via live campaign `CXXXXXX` |
| `pilot-launch-plan.md` §1/§2.0/§2.3 | ✅ | Step 3 status (number assigned, ready to test); SUPPORT-B1 card; SIGNUP-C-FU open item |
| `postgres-local` MCP — `notification_template`, `notification_type`, `notification_category`, `notification_channel` schemas + rows | ✅ | Zero `sms` rows in `notification_template`; `sms` channel row exists in `notification_channel`; `notification_type` PK = `code`, CHECK audience ∈ ('tenant','customer'); template FK → `notification_type(code)`; full 4-column audit mixin on both tables |
| `backend/tasks/sms_compliance_platform.py` | ✅ | `_PLATFORM_DOUBLE_OPTIN_TEMPLATE` constant; `_impl` + `@celery_app.task` two-layer pattern; consent/verification skip gates; `PILOT_PLATFORM_SMS_NUMBER` FROM |
| `backend/api/routes/webhooks_sms.py` | ✅ | `_PLATFORM_OPTOUT_REPLY` / `_PLATFORM_OPTIN_REPLY` / `_PLATFORM_HELP_REPLY` constants (lines ~53–70); owner `user_endpoint` resolution (SIGNUP-C) |
| `backend/services/stripe_subscriptions.py` `handle_invoice_payment_failed` | ✅ | Existing paywall transition + **TODO (Phase 2): dispatch billing.payment_failed notification** — this batch's wiring point |
| `backend/tasks/notification_worker.py` `_send_via_channel` | ✅ | Outbox SMS path uses sandbox/tenant FROM fallback — **not** suitable for platform sends; platform sends stay on the direct-carrier pattern |
| `backend/services/template_renderer.py` | ✅ | `render_template(template_string, context)` — Jinja-style `{{var}}` rendering |
| `backend/migrations/scripts/seed_platform.py` (notification_template block, ~lines 491–707) | ✅ | Established update-or-insert seed pattern keyed on `(notification_type_code, channel)` with `tenant_id IS NULL` — this batch extends it |
| `backend/services/notification_endpoints.py` | ✅ | `get_owner_sms_endpoint()`, `hash_consent_text()` helpers reused as-is |

---

## B. Migration Plan

**One Alembic data migration** (blank revision, raw `op.execute`, `SET LOCAL session_replication_role = 'replica';` at top of `upgrade()`, full `downgrade()`). No DDL — inserts only. All statements idempotent (`ON CONFLICT DO NOTHING` / existence-guarded) so prod and fresh-env runs converge.

### B.1 — `notification_type` rows (system, `tenant_id NULL`, `audience='tenant'`)

| `code` | `name` | `description` | Campaign string |
|---|---|---|---|
| `platform_sms_double_optin` | Platform SMS — Double Opt-In Request | Pathway C first message (§6 Sample 1 / §8). Campaign-locked — do not edit without Telnyx resubmission. | §8 double opt-in |
| `platform_sms_optin_reply` | Platform SMS — Opt-In Reply (START/UNSTOP/YES) | §8 auto-reply. Campaign-locked. | §8 opt-in |
| `platform_sms_optout_reply` | Platform SMS — Opt-Out Reply (STOP) | §8 auto-reply. Campaign-locked. Carrier-mandatory. | §8 opt-out |
| `platform_sms_help_reply` | Platform SMS — Help Reply (HELP/INFO) | §8 auto-reply. Campaign-locked. Carrier-mandatory. | §8 help |
| `platform_payment_failed` | Platform SMS — Subscription Payment Failed | §6 Sample 2 (Account Notifications). Campaign-locked. Fires from `invoice.payment_failed`. | §6 Sample 2 |

### B.2 — `notification_template` rows (`tenant_id NULL`, `channel='sms'`, `locale='en'`, `subject=NULL`, `is_active=true`)

Bodies are **verbatim** — no variable placeholders in this batch (Sample 2 is static text; the login URL is the fixed bare domain per §6 embedded-link note):

| `notification_type_code` | `body` (verbatim) |
|---|---|
| `platform_sms_double_optin` | `Pilot for Trades: Reply YES to get important account, billing & security alerts by text. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.` |
| `platform_sms_optin_reply` | `Pilot for Trades: You're opted in to account, billing & security alerts. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.` |
| `platform_sms_optout_reply` | `You have been unsubscribed from Pilot for Trades account alerts. No further messages will be sent. Reply START to re-subscribe.` |
| `platform_sms_help_reply` | `Pilot for Trades account alerts. For help, visit pilotfortrades.com or email info@pilotfortrades.com. Msg & data rates may apply. Reply STOP to unsubscribe.` |
| `platform_payment_failed` | `Pilot for Trades: Your payment didn't go through. Please login to app.pilotfortrades.com and update your credit card to keep your account active. Reply STOP to opt out.` |

> **⚠️ Engineer verification duty**: before writing the migration, diff these five strings character-for-character against the live constants in `webhooks_sms.py` (lines ~53–70) and `sms_compliance_platform.py` (line ~40). The code constants were SIGNUP-C-verified against the portal submission — **if the table above and the code disagree, the code wins** and the discrepancy must be flagged in the Completion Summary.

### B.3 — MCP verification queries (run before authoring migration)

```sql
-- 1. Confirm zero pre-existing platform sms rows (expect 0 rows)
SELECT notification_type_code, channel FROM public.notification_template
WHERE channel = 'sms' AND tenant_id IS NULL;

-- 2. Confirm none of the 5 new type codes exist (expect 0 rows)
SELECT code FROM public.notification_type
WHERE code IN ('platform_sms_double_optin','platform_sms_optin_reply','platform_sms_optout_reply',
               'platform_sms_help_reply','platform_payment_failed');

-- 3. Column shapes (already verified by Architect 2026-08-09; engineer re-verifies)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name IN ('notification_type','notification_template')
ORDER BY table_name, ordinal_position;

-- 4. Current alembic head
SELECT version_num FROM public.alembic_version;
```

### B.4 — Pre-migration state

`notification_template` has 30 system rows (10 types × email/in_app/push), zero sms. `notification_type` has 10 system rows. No triggers block inserts (both tables have standard audit triggers only; replica-role setting handles them).

### B.5 — NOT NULL pattern

`notification_type.is_active` NOT NULL → explicit `true`. `notification_template.is_active` NOT NULL → explicit `true`; `locale` NOT NULL → `'en'`; `body` NOT NULL → verbatim string. `created_at`/`updated_at` default `now()` — set explicitly anyway per seed-platform precedent.

### B.6 — Seed Data Rollout (Rule 11.5 — mandatory)

Two layers, both required:

1. **Layer 1 — Core/Platform (prod + all envs)**: the Alembic data migration above (§B.1/§B.2) **plus** matching additions to `seed_platform.py`:
   - Extend the `notification_type` seed list with the 5 new codes.
   - Extend the `notification_template_copy` dict + insert loop with the 5 `(code, 'sms')` bodies (update-or-insert, matching the existing pattern at ~lines 648–707).
   - Extend the `mode_inspect` notification_template printout (it already selects all system rows — no change needed beyond confirming the new rows print).
2. **Layer 2 — Scenario**: N/A — system rows are not tenant-scoped; scenario seeds do not touch platform templates.
3. **Verification**: `python migrations/scripts/seed_platform.py --mode inspect` shows the 5 new rows; `pytest -m unit` green.
4. **README update**: `backend/README-seed-data.md` §4 (Current Seed State) — add the 5 `notification_type` + 5 `notification_template` rows to the table counts/listing.

---

## C. Execution Order

| # | Step | File(s) |
|---|---|---|
| 1 | MCP verification (§B.3) + regression baseline | — |
| 2 | Alembic data migration (5 type rows + 5 template rows) + `upgrade`/`downgrade` cycle test | `migrations/versions/<new>_platform_sms_b1_templates.py` |
| 3 | New service: `get_platform_sms_body()` template loader (fail-loud) | `services/platform_sms_templates.py` |
| 4 | Refactor double opt-in task to load body from DB; delete `_PLATFORM_DOUBLE_OPTIN_TEMPLATE` | `tasks/sms_compliance_platform.py` |
| 5 | Refactor webhook auto-replies to load bodies from DB; delete `_PLATFORM_OPTOUT_REPLY` / `_PLATFORM_OPTIN_REPLY` / `_PLATFORM_HELP_REPLY` | `api/routes/webhooks_sms.py` |
| 6 | New Celery task `send_platform_account_notification_sms` (payment-failed sender) | `tasks/sms_platform_notifications.py` |
| 7 | Wire `handle_invoice_payment_failed` TODO → enqueue task | `services/stripe_subscriptions.py` |
| 7a | **(v1.1 — FU3)** `get_signup_state()`: add `sms_consent_status` to `collected_data` (owner SMS endpoint lookup; `"opted_in"` if `verification_status=="verified"`, `"pending"` if endpoint exists unverified, `null` if none) | `services/tenant_signup.py` |
| 7b | **(v1.1 — FU3)** Response-shape regression test: real `/state` route response contains `collected_data.sms_consent_status` with correct values across the three endpoint states | `tests/domains/identity_access/test_signup_c_step3.py` (or new `test_signup_state_shape.py`) |
| 8 | Seed-platform additions + inspect verification | `migrations/scripts/seed_platform.py` |
| 9 | Verbatim-guardrail test + loader tests + refactor regression updates + wiring tests | `tests/domains/notifications_comms/test_platform_sms_b1_*.py`, updates to `test_signup_c_platform_sms.py` |
| 10 | README-seed-data §4 update + OpenAPI check (no endpoint changes expected — confirm) | `backend/README-seed-data.md` |

---

## D. New API Endpoints

**No new routes.** **(v1.1 update)** FU3 makes an **additive** change to the `GET /api/v1/signup/{tenant_id}/state` response (`collected_data.sms_consent_status: str | null`) — the `SignupStateResponse` schema must be updated and **`python export_openapi_json.py` is now required** on batch close, followed by `pnpm sync-api-types` so the FE type for the field the phone page already polls becomes real. Webhook route files are otherwise modified internally only; no other contract changes.

---

## E. Pattern Reuse Decisions

| Pattern (mvp-arch §16 / existing code) | Decision |
|---|---|
| Two-layer Celery task (`_impl` + wrapper) from `sms_compliance_platform.py` | **Reuse** for the new payment-failed task |
| Direct carrier send (bypass `notification_outbox`) | **Reuse** — platform compliance + account SMS send directly via `get_sms_carrier()` with `PILOT_PLATFORM_SMS_NUMBER` FROM. Rationale: the outbox worker's sms branch resolves a sandbox/tenant FROM and applies category preference gating; Pathway C messages are (a) from the platform number, (b) consent-gated by `user_endpoint` (a TCPA gate, not a preference gate), and (c) the compliance auto-replies must be unsuppressible. |
| `notification_template` as content store + `render_template()` | **Reuse** — new loader reads system rows; this batch's 5 bodies are static (no `{{vars}}`) |
| Seed-platform update-or-insert pattern | **Reuse** for Layer 1 seed parity |
| Tenant-overridable templates (system-default/tenant-override §16) | **Explicitly NOT applied** — platform campaign strings are campaign-locked; tenants must never override them. No tenant-scoped rows are created. |
| Hardcoded fallback if DB row missing | **Forbidden** — see §G-1 fail-loud decision |

---

## F. Shared Module Interfaces

```python
# services/platform_sms_templates.py  (NEW)

class PlatformSmsTemplateMissingError(RuntimeError):
    """Raised when a campaign-locked platform SMS template row is missing or inactive.
    Never swallow: a missing compliance template means the environment is mis-seeded
    or the row was edited — fail loud, send nothing."""

def get_platform_sms_body(db: Session, type_code: str) -> str:
    """
    Load the system-default (tenant_id IS NULL) sms-channel notification_template
    body for `type_code`. Direct lookup — NOT preference-gated, NOT tenant-scoped.

    Raises PlatformSmsTemplateMissingError if no active row exists.
    Callers: tasks/sms_compliance_platform.py, api/routes/webhooks_sms.py,
             tasks/sms_platform_notifications.py
    """


# tasks/sms_platform_notifications.py  (NEW)

def _send_platform_account_notification_sms_impl(
    tenant_id: str,
    type_code: str,          # e.g. 'platform_payment_failed'
) -> dict[str, Any]:
    """
    Send a Pathway C account-notification SMS to ALL owner endpoints of the tenant
    where consent_status='opted_in' AND verification_status='verified'.
    FROM = settings.PILOT_PLATFORM_SMS_NUMBER. Body = get_platform_sms_body(...).
    Skip conditions (status='skipped'): no verified endpoints, no FROM configured.
    Sends are logged (structured logger); carrier delivery receipts arrive via the
    existing Telnyx webhook. Returns {'status': 'sent'|'skipped'|'failed',
    'sent_count': int, ...}
    """

@celery_app.task(name="send_platform_account_notification_sms", bind=True,
                 max_retries=3, default_retry_delay=60)
def send_platform_account_notification_sms(self, tenant_id: str, type_code: str) -> dict[str, Any]:
    """Celery wrapper — str UUIDs only."""


# services/stripe_subscriptions.py  (MODIFIED — replaces the Phase-2 TODO)

def handle_invoice_payment_failed(db: Session, stripe_event: dict) -> None:
    # ... existing paywall transition unchanged ...
    # PLATFORM-SMS-B1: enqueue Pathway C payment-failed SMS (campaign Sample 2)
    send_platform_account_notification_sms.delay(
        tenant_id=str(tenant.id), type_code="platform_payment_failed"
    )
```

**Refactor contracts:**

- `tasks/sms_compliance_platform.py::_send_platform_double_optin_sms_impl` — step 3 becomes `body = get_platform_sms_body(db, "platform_sms_double_optin")`; `hash_consent_text(body)` unchanged; constant deleted.
- `api/routes/webhooks_sms.py` — the three send sites (opt-in ~line 166, opt-out ~line 228, help ~line 251) call `get_platform_sms_body(db, "platform_sms_optin_reply" | "platform_sms_optout_reply" | "platform_sms_help_reply")`; `hash_consent_text(...)` calls use the loaded body; constants deleted. The handler already has a `db` session in scope at all three sites.

**Test-time seeding note**: unit tests that exercise these paths must insert the required `notification_type` + `notification_template` rows via fixtures (the test DB is not guaranteed to carry seed_platform rows). A shared module-scoped fixture `platform_sms_templates` in `tests/domains/notifications_comms/conftest.py` (or local fixtures) inserts the 5 pairs.

---

## G. Open Questions Resolved

1. **Should code constants remain as a fallback if the DB row is missing?** → **No.** A silent fallback recreates the two-path problem and can mask an edited/deleted campaign-locked row until error 806 hits in prod. Fail loud (`PlatformSmsTemplateMissingError`), send nothing, alert via logs. The verbatim-guardrail test (below) makes drift a CI failure before deploy.
2. **How is verbatim-match enforced long-term?** → New test `test_platform_sms_b1_verbatim_guardrail.py`: holds the five campaign-doc strings as test constants and asserts (a) the seeded DB rows match them exactly, and (b) grep-level assertion that no `Pilot for Trades:` SMS string literals remain in `tasks/sms_compliance_platform.py` / `webhooks_sms.py` outside the loader. Any future copy change requires editing the test + Telnyx portal resubmission — a deliberate, visible act.
3. **Do these notifications go through `notification_preference` gating?** → No for compliance messages (double opt-in, STOP/START/HELP replies — carrier-mandatory, unsuppressible). For `platform_payment_failed`: consent-gated via `user_endpoint` (opted_in + verified) only — not category-preference-gated in this batch. Rationale: TCPA consent is the legal gate; an owner who completed double opt-in has requested account alerts. Preference-gated refinement (billing category, sms channel) is a B2 consideration.
4. **Why not route through `notification_outbox` + worker?** → The worker's sms branch uses a sandbox/tenant-number FROM and per-user preference resolution; retrofitting platform-FROM + owner-endpoint-fan-out into it is a larger change than the direct pattern already proven in SIGNUP-C. Revisit if Pathway C message types proliferate (B2+).
5. **Does the seed/migration ordering matter for prod?** → Prod already ran SIGNUP-C code with constants. Deploy order: migration + seeds land **with** the code deploy (same release); the loader fail-loud behavior means a deploy that runs code before data would error — standard alembic-before-task-restart ordering on ECS avoids this (migration runs in the deploy pipeline before new tasks start).
6. **Tenant-visible template management UI?** → None. These rows are invisible to tenant template editors by design (campaign-locked). Any admin surface that lists `notification_template` should filter `notification_type_code LIKE 'platform_%'` out of editable lists — flagged as a note for the future template-management batch, no work here.
7. **Sample 2 contains an embedded link — any carrier risk?** → Already accounted for in campaign attributes (§9: Embedded link = Yes, bare `app.pilotfortrades.com`). No deep paths allowed in future edits without portal update.
8. **(v1.1) Why `"opted_in"` as the field value when the backend state is `verified`?** → The frontend contract already polls for the literal `"opted_in"` (SIGNUP-C FE shipped against MSW mocks carrying that value); the backend derives it from `user_endpoint.verification_status == "verified"` (the YES-reply terminal state) — NOT from `consent_status` (which flips to `opted_in` at checkbox attestation, before confirmation). Returning `"opted_in"` only on `verified` preserves the double-opt-in semantics the UI intends. Changing the FE to poll `verification_status` directly was considered and rejected — one backend field is the smaller, contract-preserving fix.
9. **(v1.1) Why did unit/integration tests not catch the missing field?** → MSW mocks hand-rolled the `/state` JSON with `sms_consent_status` present while the real backend never emitted it — mock/reality divergence. Mitigations logged: the FU3 regression test asserts against the real route handler (not a mock), and "MSW response fixtures must be generated from or diffed against `openapi.json`" is added to CQ-GATE.

---

## Handoff

Python Engineer prompt: `batch-platform-sms-b1-python-engr-prompt.md`

On batch close: update `pilot-launch-plan.md` (§2.0 ✅, Appendix A row, Appendix C summary), `README-seed-data.md` §4, and the campaign playbook §11 checklist. No OpenAPI/FE handoff (no endpoint changes).
