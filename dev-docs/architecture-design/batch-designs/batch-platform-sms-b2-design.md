# Batch Design: PLATFORM-SMS-B2 — Pathway C Platform SMS: Security-Alert (New-Device) + Maintenance Broadcast Senders

| | |
|---|---|
| **Batch code** | PLATFORM-SMS-B2 |
| **Status** | ✅ APPROVED 2026-08-16 — both prompts authored, ready to run |
| **Date** | 2026-08-14 |
| **Architect** | Pilot Architect |
| **Engineer prompts** | ① `batch-platform-sms-b2-python-engr-prompt.md` (3–4h, runs FIRST) ✅ authored 2026-08-16 → ② `batch-platform-sms-b2-devops-prompt.md` (~1h, deploys what Part 1 authors) ✅ authored 2026-08-16 |
| **Launch plan card** | `pilot-launch-plan.md §2.4 PLATFORM-SMS-B2` (P2 Pre-GA) |
| **Prerequisite** | PLATFORM-SMS-B1 ✅ (loader, task, guardrail, seed substrate shipped) |
| **Governing ADRs** | ADR-0013 (three-pathway SMS model / Pathway C) |
| **Campaign source of truth** | `telnyx-10dlc-p4t-tenant-comms-campaign.md §6` — Samples 3 & 4 verbatim |
| **Design alignment** | Tom approved the full Q1–Q4 alignment package on 2026-08-14 (recorded in §G) |

---

## 0. Scope Reconciliation vs. Launch Plan Card (READ FIRST)

The launch-plan card says: *"Seed + wire the remaining two approved `CXXXXXX` Account-Notifications samples: Sample 3 (new-device sign-in security alert — needs a Cognito post-auth trigger point) and Sample 4 (scheduled maintenance broadcast — needs an ops/admin broadcast trigger, likely a Celery task invoked manually or via beat). Both reuse PLATFORM-SMS-B1's loader, verbatim-guardrail test, and `send_platform_account_notification_sms` task."*

This design matches the card exactly, with the two trigger points now resolved (Tom-approved 2026-08-14):

| Card anticipation | Resolution (this design) |
|---|---|
| "Cognito post-auth trigger point" for Sample 3 | Cognito **device tracking (Always remember)** + new **Post Authentication Lambda** (`backend/lambda/post_authentication/handler.py` — new) gating on `event.request.newDeviceUsed`; the Lambda enqueues the existing B1 task directly to the Redis broker (§F.3). |
| "ops/admin broadcast trigger, likely a Celery task invoked manually or via beat" for Sample 4 | **Operator-run CLI script** (`backend/scripts/broadcast_maintenance_sms.py` — new) with `--date` / `--window` / `--i-am-sure`; it enqueues the existing B1 task per eligible tenant with a template context (§F.2). **No beat schedule** (maintenance windows are ad-hoc) and **no operator endpoint** (RBAC/admin-surface scope creep for a twice-a-year action). |
| "reuse B1's loader / guardrail / task" | Reused unchanged except one **additive** optional `template_context` parameter on the B1 task (§F.1) to support Sample 4's date/window slots. Loader, consent gate, FROM number, carrier path all untouched. |

**Out of scope (explicit)**: Sample 5 (Customer Care, two-way) stays with **SUPPORT-B1** per the card family split. No new API endpoints, no frontend surface, no preference gating, no email parallel, no Cognito advanced security features.

---

## A. Input Read Summary

| Input | What was taken from it |
|---|---|
| `pilot-launch-plan.md §2.4 PLATFORM-SMS-B2 card` | Scope, prerequisite, "reuse B1 substrate" mandate (§0 above) |
| `batch-platform-sms-b1-design.md` (full) | Loader contract (`get_platform_sms_body`, fail-loud), task contract, seed update-or-insert pattern, verbatim-guardrail pattern, §G-3 consent-gate-only stance, §G-1 no-hardcoded-fallback rule |
| `telnyx-10dlc-p4t-tenant-comms-campaign.md §6` | Sample 3 & Sample 4 **verbatim strings** (quoted in §B.2); §6↔§8 code-match / error-806 rule; Sample 5 deferral note |
| `pilot-operations.md §7` | Notification template system flow (type → template → render) — Rule 10.1 mandatory read |
| `aws-cognito-prod-setup.md §11` | Post-Confirmation trigger is live and wired **manually via CLI**; `update-user-pool --lambda-config` overwrites the **entire** LambdaConfig block (must include all triggers); `lambda_config` sits in Terraform `ignore_changes` |
| `infrastructure/terraform/modules/security/main.tf` | `lambda_config { post_confirmation = ... }` declared but `ignore_changes`'d — manual CLI wiring posture confirmed in code; pool is ESSENTIALS tier (`user_pool_add_ons` ignored — advanced security unavailable, reinforcing the Q1 rejection) |
| `backend/lambda/post_confirmation/handler.py` | Lambda handler pattern to mirror: SQLModel-ORM-only imports (no FastAPI), module-level engine cache, `_resolve_db_url()` (env `DATABASE_URL` → `DB_SECRET_ARN` Secrets Manager JSON `url` field), **never-raise-to-Cognito** discipline |
| `backend/tasks/sms_platform_notifications.py` (as-built, 244 lines) | Exact impl + wrapper signatures (§F.1), `get_verified_owner_sms_endpoints()` eligibility function, skip-condition contract |
| `backend/services/template_renderer.py` | `render_template(template_string, context)` is **Jinja2 with `autoescape=True`** — drives the §G-5 value-allowlist constraint |
| `backend/core/celery_app.py` + `docker-compose.yml` + `compute/main.tf` | App name `pilot_worker`; broker = `settings.CELERY_BROKER_URL`; worker runs with **no `-Q` flag** → consumes the **default `celery` queue** → a Lambda-side `send_task` with no explicit queue is consumed (§F.3) |
| `aws-env-mgmt-ops-plan.md` secrets inventory | `pilot/prod/redis` secret supplies `CELERY_BROKER_URL` (DB 1) — the Lambda's broker env source |
| `backend/tests/domains/identity_access/test_post_confirmation_router.py` | Lambda unit-test precedent: `importlib.import_module("lambda.post_confirmation.handler")` — B2 mirrors for `lambda.post_authentication.handler` |
| **MCP `postgres-local` verification (2026-08-14)** | Full column lists for `notification_type` (10 cols), `notification_template` (13 cols), `user_endpoint`, `tenant_user`, `user` (**no `cognito_sub` column** → identity join is by `email`, §G-9); 5 existing `platform_%` template rows present + active; neither new code exists yet |
| ADR-0013 | Pathway C governance — this batch implements its remaining two samples; no new ADR required (§J) |

---

## B. Migration Plan

**Data-only migration — zero DDL.** Two `notification_type` rows + two `notification_template` rows, mirroring B1 §B.1/§B.2 exactly.

### B.0 — Pre-migration MCP verification (already executed 2026-08-14)

Executed this session against `postgres-local` (Rule §3 prompt-authoring gate — all SQL below uses only these returned columns):

- `notification_type`: `code` varchar PK, `tenant_id` uuid NULL, `audience` varchar NOT NULL, `name` varchar NOT NULL, `description` varchar NULL, `is_active` bool NOT NULL, + audit (`created_at`/`updated_at` NOT NULL, `created_by`/`updated_by` uuid NULL).
- `notification_template`: `id` uuid PK, `tenant_id` uuid NULL, `notification_type_code` varchar NOT NULL, `channel` varchar NOT NULL, `locale` varchar NOT NULL, `subject` varchar NULL, `body` varchar NOT NULL, `is_active` bool NOT NULL, + same 4 audit cols.
- Existing state: 5 `platform_%` sms template rows present + active (`platform_sms_double_optin`, `platform_sms_optin_reply`, `platform_sms_optout_reply`, `platform_sms_help_reply`, `platform_payment_failed`); **zero** rows with codes `platform_security_new_device` / `platform_maintenance_broadcast`.

The Python Engineer prompt will re-run these as its own Pre-Work MCP gate.

### B.1 — `notification_type` rows (system, `tenant_id NULL`, `audience='tenant'`)

```sql
INSERT INTO public.notification_type
    (code, tenant_id, audience, name, description, is_active,
     created_at, updated_at, created_by, updated_by)
SELECT v.code, NULL, 'tenant', v.name, v.description, true,
       now(), now(), NULL, NULL
FROM (VALUES
    ('platform_security_new_device',
     'Platform: New-Device Sign-In Alert',
     'Pathway C security alert to tenant owners when a successful sign-in occurs from a device Cognito has not remembered (Post-Authentication trigger, newDeviceUsed). Campaign CXXXXXX Sample 3.'),
    ('platform_maintenance_broadcast',
     'Platform: Scheduled Maintenance Broadcast',
     'Pathway C broadcast to all tenant owners announcing a scheduled platform maintenance window (operator-run CLI). Campaign CXXXXXX Sample 4.')
) AS v(code, name, description)
WHERE NOT EXISTS (
    SELECT 1 FROM public.notification_type t WHERE t.code = v.code
);
```

### B.2 — `notification_template` rows (`tenant_id NULL`, `channel='sms'`, `locale='en'`, `subject=NULL`, `is_active=true`)

**Sample 3 — stored fully static** (verbatim from playbook §6, error-806 rule):

```sql
INSERT INTO public.notification_template
    (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active,
     created_at, updated_at, created_by, updated_by)
SELECT gen_random_uuid(), NULL, 'platform_security_new_device', 'sms', 'en', NULL,
       'Pilot for Trades: New sign-in to your account from a new device. If this wasn''t you, secure your account now. Reply STOP to opt out.',
       true, now(), now(), NULL, NULL
WHERE NOT EXISTS (
    SELECT 1 FROM public.notification_template
    WHERE notification_type_code = 'platform_security_new_device'
      AND channel = 'sms' AND locale = 'en' AND tenant_id IS NULL
);
```

**Sample 4 — stored with two Jinja placeholders** (the only variable slots in the registered sample):

```sql
INSERT INTO public.notification_template
    (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active,
     created_at, updated_at, created_by, updated_by)
SELECT gen_random_uuid(), NULL, 'platform_maintenance_broadcast', 'sms', 'en', NULL,
       'Pilot for Trades: Scheduled maintenance {{ maint_date }} from {{ maint_window }}. The app may be briefly unavailable. Reply STOP to opt out.',
       true, now(), now(), NULL, NULL
WHERE NOT EXISTS (
    SELECT 1 FROM public.notification_template
    WHERE notification_type_code = 'platform_maintenance_broadcast'
      AND channel = 'sms' AND locale = 'en' AND tenant_id IS NULL
);
```

Rendering with `maint_date="Sun 08-02-2026"` and `maint_window="2:00–3:00 AM ET"` (en-dash U+2013 preserved) must produce the registered Sample 4 **byte-for-byte**:

> `Pilot for Trades: Scheduled maintenance Sun 08-02-2026 from 2:00–3:00 AM ET. The app may be briefly unavailable. Reply STOP to opt out.`

The verbatim-guardrail test (§F.4) asserts exactly this render equality — this is what keeps the parameterized body 806-safe.

**Downgrade**: delete the two template rows (`WHERE notification_type_code IN (...) AND channel='sms' AND tenant_id IS NULL`) then the two type rows (`WHERE code IN (...) AND tenant_id IS NULL`).

### B.3 — NOT NULL pattern

N/A — no schema change. Data inserts satisfy all NOT NULL columns explicitly (audit `created_at`/`updated_at` set via `now()`; `created_by`/`updated_by` NULL = system-seeded, B1 precedent).

### B.4 — Seed Data Rollout (Rule 11.5 — MANDATORY)

- **Layer 1 — Platform values**: mirror B1 §B.6 — extend `seed_platform.py`'s platform-notification block with the two new type+template pairs using the existing **update-or-insert keyed `(notification_type_code, channel)` with `tenant_id IS NULL`** pattern. `ON CONFLICT` is not available (no unique constraint on the natural key); the seed must SELECT-then-UPDATE-or-INSERT. **No DELETE anywhere in `mode_seed`** (Rule 11.1 — update-or-insert only for these rows).
- **Layer 2 — Scenario data**: N/A (no entity columns added; platform templates are not scenario data).
- **Verification**: re-run `seed_platform.py` (idempotent — second run updates in place, row count unchanged) + `pytest -m unit`.
- **README update**: `backend/README-seed-data.md` §4 (Current Seed State) — add the two new `platform_%` rows to the platform notification list.

---

## C. Execution Order

**Part 1 — Python Engineer (3–4h)** — single prompt:

| # | Step | Output |
|---|---|---|
| 1 | Alembic data migration (§B.1 + §B.2 + downgrade) | new revision |
| 2 | `seed_platform.py` parity + `README-seed-data.md` §4 | §B.4 |
| 3 | Additive `template_context` param on the B1 task (impl + wrapper) | §F.1 |
| 4 | New CLI `backend/scripts/broadcast_maintenance_sms.py` | §F.2 |
| 5 | New Lambda handler `backend/lambda/post_authentication/handler.py` | §F.3 |
| 6 | Unit tests: seed rows, task extension, CLI, Lambda handler + `test_platform_sms_b2_verbatim_guardrail.py` | §F.4 |

**Part 2 — DevOps Engineer (~1h)** — separate prompt, runs after Part 1 merges (it packages the as-built handler):

| # | Step | Output |
|---|---|---|
| 7 | `infrastructure/scripts/build-post-authentication-lambda.sh` (mirror `build-post-confirmation-lambda.sh`); deps: `psycopg2-binary`, `sqlalchemy`, `sqlmodel`, **`celery`** | build script |
| 8 | Terraform (security module): `data.archive_file.post_authentication`, `aws_lambda_function.post_authentication` (python3.12, existing `lambda_execution` role, same VPC subnets + `sg-lambda`), `aws_lambda_permission.cognito_post_authentication`; (monitoring module): CloudWatch log group; (networking module): **Redis SG ingress 6379 from `sg-lambda`** — the only networking change | TF diff |
| 9 | Manual CLI (per `aws-cognito-prod-setup.md §11` posture): enable device tracking (**Always remember**) + wire LambdaConfig with **BOTH** triggers (whole-block overwrite warning, §G-1) | live wiring |
| 10 | Smoke test (sign in from a new device → owners receive Sample 3) + doc updates (`aws-cognito-prod-setup.md §11`, `aws-ops-runbook.md §14.5`, `aws-infrastructure-as-built.md`) | verified |

---

## D. New API Endpoints

**None.** No route files are added or modified; no schemas change; **no `python export_openapi_json.py` / `pnpm sync-api-types` handoff** on batch close. (The Lambda is invoked by Cognito, not HTTP; the CLI is an operator script, not an endpoint — §G-4.)

---

## E. Pattern Reuse Decisions

| Pattern (source) | Decision |
|---|---|
| B1 two-layer Celery task (`_impl` + `@celery_app.task` wrapper) | **Reuse + one additive optional param** (`template_context`, §F.1). Decorator, retry semantics, consent gate, FROM resolution, carrier path all unchanged. |
| B1 fail-loud loader `get_platform_sms_body()` | **Reuse unchanged** — both new bodies load through it; no hardcoded fallback anywhere (B1 §G-1 stands). |
| `notification_template` + `render_template()` (Jinja2, `autoescape=True`) | **Reuse** — Sample 4 is the first Pathway C body with `{{ vars }}`; the autoescape implication is handled by the §G-5 allowlist. |
| Direct carrier send (bypass `notification_outbox`) | **Reuse** — B1 §E rationale stands (platform FROM, TCPA consent gate not preference gate). |
| Seed-platform update-or-insert keyed `(notification_type_code, channel)` / `tenant_id IS NULL` | **Reuse** for §B.4 Layer 1 parity. |
| Tenant-overridable templates (§16 system-default/tenant-override) | **Explicitly NOT applied** — campaign-locked strings; no tenant-scoped rows (B1 §E). |
| Post-Confirmation Lambda discipline: ORM-only imports, engine cache, `_resolve_db_url()` env→Secrets-Manager resolution, **never raise to Cognito** | **Reuse verbatim** in the Post-Authentication handler (§F.3) — a raise here would fail a user's *sign-in*, making the discipline even stricter. |
| Manual CLI trigger wiring; `lambda_config` in TF `ignore_changes` | **Reuse** (ADR-0011 posture) — see §G-1 whole-block overwrite warning. |
| Verbatim-guardrail test (B1 §G-2) | **Reuse pattern** in a new B2 guardrail file (§F.4) — including the render-with-registered-values assertion that keeps Sample 4 806-safe. |

---

## F. Shared Module Interfaces

### F.1 — Task extension (the only change to existing backend code)

`backend/tasks/sms_platform_notifications.py` — **additive, backward-compatible**:

```python
def _send_platform_account_notification_sms_impl(
    tenant_id: str,
    type_code: str,
    template_context: dict[str, str] | None = None,   # NEW (B2) — optional
) -> dict[str, Any]:
    # ... steps 1–2 unchanged (FROM resolution, get_platform_sms_body) ...
    # NEW (B2): render only when a context is supplied.
    # Sample 3 path passes None → body used verbatim (B1 behavior preserved).
    if template_context is not None:
        body = render_template(body, template_context)
    # ... steps 3–4 unchanged (endpoint fan-out, carrier sends) ...

@celery_app.task(name="send_platform_account_notification_sms", bind=True,
                 max_retries=3, default_retry_delay=60)   # decorator UNCHANGED
def send_platform_account_notification_sms(
    self,
    tenant_id: str,
    type_code: str,
    template_context: dict[str, str] | None = None,       # NEW (B2) — optional
) -> dict[str, Any]:
    # passes template_context through to _impl; retry semantics unchanged
```

Contract notes: `template_context` values are **strings only** (Celery-serializable); `None` is the default so the existing `platform_payment_failed` caller in `services/stripe_subscriptions.py` needs no change.

### F.2 — Maintenance broadcast CLI (new)

`backend/scripts/broadcast_maintenance_sms.py`:

```python
# Usage:
#   python -m scripts.broadcast_maintenance_sms --date "Sun 08-02-2026" --window "2:00–3:00 AM ET"
#       → DRY RUN (default): prints eligible-tenant count + per-tenant owner-endpoint counts. Enqueues NOTHING.
#   python -m scripts.broadcast_maintenance_sms --date ... --window ... --i-am-sure
#       → enqueues send_platform_account_notification_sms per eligible tenant.

ALLOWLIST = re.compile(r"^[A-Za-z0-9: \-–]+$")   # en-dash U+2013 included — see §G-5

def main(date: str, window: str, i_am_sure: bool) -> int:
    # 1. Validate date/window against ALLOWLIST (reject &, <, >, quotes, braces).
    # 2. Eligible tenants = DISTINCT tenant_id FROM tenant_user WHERE is_active = true,
    #    filtered to those where get_verified_owner_sms_endpoints(db, tenant_id) ≥ 1
    #    (single source of truth for eligibility — same function the task uses).
    # 3. Per tenant: log + (only with --i-am-sure)
    #    send_platform_account_notification_sms.delay(
    #        tenant_id=str(tid),
    #        type_code="platform_maintenance_broadcast",
    #        template_context={"maint_date": date, "maint_window": window},
    #    )
    # 4. Summary log line: tenants_eligible, tasks_enqueued (or "DRY RUN").
```

Logging goes through the standard backend logger → **CloudWatch** when run via `aws ecs execute-command` against the worker service (runbook step in the DevOps prompt). The script contains **no `Pilot for Trades:` literal** (guardrail grep target) and does **not** filter by billing/subscription status (§G-10).

### F.3 — Post-Authentication Lambda handler (new)

`backend/lambda/post_authentication/handler.py` — mirrors `post_confirmation/handler.py` structure (ORM-only imports, module-level engine cache, `_resolve_db_url()` copied pattern):

```python
def handler(event: dict, context) -> dict:
    """
    Cognito Post Authentication trigger (triggerSource = "PostAuthentication_Authentication").
    Fires only after FULLY successful auth (incl. MFA challenges) — never on failed
    logins, never on silent token refresh.

    Gate: alert only when event["request"]["newDeviceUsed"] is True
    (populated only because device tracking = Always remember — §G-1).

    NEVER raises: any exception is logged and `event` is returned — raising
    would fail the user's sign-in.
    """
    # 1. if event.get("request", {}).get("newDeviceUsed") is not True: return event
    # 2. email = event["request"]["userAttributes"]["email"]   (identity join key — §G-9)
    # 3. user = select(User).where(User.email == email, User.is_active.is_(True))
    #       → not found: log, return event
    # 4. tenant_ids = select(TenantUser.tenant_id).where(
    #        TenantUser.user_id == user.id, TenantUser.is_active.is_(True))
    # 5. for tid in tenant_ids:
    #        _get_celery_producer().send_task(
    #            "send_platform_account_notification_sms",
    #            args=[str(tid), "platform_security_new_device"],
    #        )   # no template_context — Sample 3 is static; default queue §G-6
    # 6. return event
```

Broker resolution: env `CELERY_BROKER_URL` (DevOps populates from the `pilot/prod/redis` secret — the same key the ECS worker task consumes; DevOps verifies the exact secret key name against the compute module's task-definition `secrets` block during Part 2). Producer = minimal `Celery("pilot_lambda_producer", broker=url)` created once per warm start — **kombu transport, no import of `core.celery_app`** (which would drag FastAPI/config into the Lambda package). Packaging deps: `psycopg2-binary`, `sqlalchemy`, `sqlmodel`, `celery` (kombu arrives transitively).

### F.4 — Verbatim-guardrail test (new)

`backend/tests/domains/notifications_comms/test_platform_sms_b2_verbatim_guardrail.py`:

1. **Sample 3**: DB body == the registered constant, byte-for-byte.
2. **Sample 4**: `render_template(db_body, {"maint_date": "Sun 08-02-2026", "maint_window": "2:00–3:00 AM ET"})` == the registered Sample 4 constant, byte-for-byte (the 806-safety assertion).
3. **Grep assertions**: no `Pilot for Trades:` literals in `scripts/broadcast_maintenance_sms.py`, `tasks/sms_platform_notifications.py` (outside the existing loader path), or `backend/lambda/post_authentication/handler.py`.

Test-time seeding follows B1: the shared fixture in `tests/domains/notifications_comms/conftest.py` extends from 5 to 7 type+template pairs.

---

## G. Open Questions Resolved (Tom-approved 2026-08-14)

1. **New-device detection mechanism?** → Cognito **device tracking ("Always remember")** + **Post Authentication Lambda** gating on `event.request.newDeviceUsed`. Amplify JS/RN handle device-SRP automatically — no client work. Rejected: (a) alert on every password login (noise — every incognito/QA sign-in pages all owners); (b) custom device fingerprinting (unjustified build); (c) Cognito advanced security (per-MAU cost — and the pool is ESSENTIALS tier where `user_pool_add_ons` is already ignored, so it is not even available). **Whole-block overwrite warning**: `update-user-pool --lambda-config` replaces the ENTIRE LambdaConfig — the wiring command must include **both** `PostConfirmation=<existing ARN>` and `PostAuthentication=<new ARN>` or the live Post-Confirmation trigger (SIGNUP-GA-1) is silently detached.
2. **Lambda → worker transport?** → **Direct Redis broker enqueue** from the VPC-resident Lambda via a minimal Celery producer (`send_task` by name; kombu transport). No API hop, no new endpoint, no auth surface. Documented **contingency** (not built): an outbox event table + 1-minute beat poller, if Part 2 surfaces a VPC→ElastiCache connectivity surprise — the SG ingress rule (§C step 8) makes this unlikely.
3. **Parallel security email?** → **No — SMS-only.** The consent disclosure already covers "security" messages; adding a parallel email path is scope creep with no compliance driver.
4. **Maintenance broadcast trigger?** → **Operator CLI** (`--date` / `--window` / `--i-am-sure`, CloudWatch-logged). Rejected: (a) an operator/admin HTTP endpoint (new RBAC permission + admin surface for a twice-a-year action — scope creep); (b) a Celery beat schedule (maintenance windows are ad-hoc, not periodic).
5. **Sample 4 parameterization vs. error 806?** → Store with `{{ maint_date }}` / `{{ maint_window }}`; the guardrail test renders with the **registered** values and asserts byte-equality with the registered Sample 4. Because `render_template()` runs Jinja2 with `autoescape=True`, context values must never contain `<`, `>`, `&`, or quotes — enforced by the CLI's allowlist regex `^[A-Za-z0-9: \-–]+$` (which also excludes `{`/`}`, so an operator cannot inject Jinja syntax through a value). The registered values (`Sun 08-02-2026`, `2:00–3:00 AM ET`) contain none of these and render byte-identical.
6. **Default queue consumption?** → The worker runs `celery -A core.celery_app worker --concurrency=2` with **no `-Q`** → consumes the default `celery` queue → Lambda `send_task` with no explicit queue is consumed. No routing config changes.
7. **Preference gating (`notification_preference`)?** → **No** — B1 §G-3 stands: the TCPA double-opt-in (`consent_status='opted_in'` + `verification_status='verified'`) is the only gate. Owners who completed it requested account alerts; security + maintenance are exactly that.
8. **Who receives Sample 3?** → **All verified+opted-in owner endpoints of the signing-in user's tenant(s)** — via the existing `get_verified_owner_sms_endpoints()` fan-out, unchanged. A non-owner's new-device sign-in also alerts the owners (account-level security semantics, matching the sample's "your account"). Multi-tenant users fan out to each active tenant.
9. **Identity join key in the Lambda?** → **`user.email`** (citext → case-insensitive). MCP-verified 2026-08-14: the `user` table has **no `cognito_sub` column**; the Post-Confirmation Lambda already joins by email — same pattern.
10. **Billing-status filtering on the broadcast?** → **No** — all tenants with eligible owner endpoints receive maintenance notices (a paused tenant's owners still plan around platform downtime). Consent gate only, per B1.
11. **First-sign-in alert wave at enablement?** → Expected and accepted: when device tracking flips on, each user's first sign-in per device reads as "new" until the device is remembered, then settles. One-time operational note for the runbook (DevOps prompt §docs), not a code problem.

---

## J. Infrastructure, Cost & Master-Document Stewardship

**Infrastructure delta**: one Lambda function + CloudWatch log group + `aws_lambda_permission` + one Redis SG ingress rule (6379 from `sg-lambda`). Cognito device tracking is a no-cost pool setting. **No new AWS service.**

**Cost**: Lambda invocations at MVP scale (100 tenants × few users × few sign-ins/mo) sit deep inside the free tier → **~$0/mo**. CloudWatch logs negligible under existing retention. **Baseline unchanged: ~$888.87/mo** (post-ADR-0014) — no Founder cost review required (no baseline increase). SMS variable cost stays inside the existing Telnyx envelope (~$1.50/active-tenant/mo): maintenance broadcasts are ~1 message × opted-in owners × rare; security alerts are low-volume event-driven.

**Scaling-logic check**: no component upgrade triggers touched; nothing in this batch scales any tier.

**ADR check (§7.1 bar)**: **no new ADR** — this batch implements ADR-0013's Pathway C; the broker-enqueue transport is a local, reversible implementation choice with a documented contingency (§G-2).

**Stewardship on batch close** (Rule 12.3 — same-change updates):

| Doc | Update |
|---|---|
| `pilot-launch-plan.md` | §2.0 row + §2.4 card → status; Appendix C completion summaries (Parts 1 & 2) |
| `pilot-docs-list.md` | Row for this design (on approval); rows for both prompts (on authoring) |
| `backend/README-seed-data.md` | §4 — two new `platform_%` rows |
| `aws-cognito-prod-setup.md §11` | Device-tracking posture + Post-Authentication wiring (DevOps, Part 2) |
| `aws-ops-runbook.md §14.5` | LambdaConfig now two triggers; whole-block overwrite warning restated (DevOps, Part 2) |
| `aws-infrastructure-as-built.md` | New Lambda + SG rule (DevOps, Part 2) |
| `telnyx-10dlc-p4t-tenant-comms-campaign.md` | §6 note: Samples 3 & 4 live in code (§6↔§8 code-match satisfied); Sample 5 remains SUPPORT-B1 |

---

## Handoff

1. **Python Engineer prompt** (runs FIRST): `batch-platform-sms-b2-python-engr-prompt.md` — covers §C steps 1–6. ✅ Authored 2026-08-16. **No OpenAPI handoff** (no endpoint changes — §D).
2. **DevOps Engineer prompt** (runs after Part 1 merges): `batch-platform-sms-b2-devops-prompt.md` — covers §C steps 7–10. ✅ Authored 2026-08-16.

Both prompts authored 2026-08-16 following Tom's same-day design approval.
