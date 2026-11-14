# AWS Environment Management & Operations Plan — Pilot for Trades

**Version**: 1.3
**Date**: August 27, 2026
**Author**: Pilot Architect
**Status**: Active — binding operating plan for dev/QA/prod environment usage
**Companion docs**: [`aws-ops-runbook.md`](aws-ops-runbook.md) (day-to-day ops) · [`infrastructure/scripts/README.md`](../../infrastructure/scripts/README.md) (profile scripts) · [`../integrations/stripe/stripe-pricing-config.md`](../integrations/stripe/stripe-pricing-config.md) (Stripe price IDs) · [`../integrations/stripe/stripe-ops-runbook.md`](../integrations/stripe/stripe-ops-runbook.md) (Stripe ops)

---

## Table of Contents

- [AWS Environment Management \& Operations Plan — Pilot for Trades](#aws-environment-management--operations-plan--pilot-for-trades)
  - [Table of Contents](#table-of-contents)
  - [1. Purpose \& Phase Model](#1-purpose--phase-model)
  - [2. Third-Party Integration Inventory \& Test Modes](#2-third-party-integration-inventory--test-modes)
  - [3. Secrets \& Environment Variable Inventory](#3-secrets--environment-variable-inventory)
    - [3.1 Secrets Manager secrets (mounted via `valueFrom` at container start)](#31-secrets-manager-secrets-mounted-via-valuefrom-at-container-start)
    - [3.2 Task-definition environment variables (plain, in Terraform)](#32-task-definition-environment-variables-plain-in-terraform)
  - [4. Phase 1 — Pre-Beta: Prod-as-Integration-Env](#4-phase-1--pre-beta-prod-as-integration-env)
    - [4.1 Rule set (binding)](#41-rule-set-binding)
    - [4.2 What runs where in Phase 1](#42-what-runs-where-in-phase-1)
  - [5. Phase 2 — Charter Beta: Dev / QA / Prod Split](#5-phase-2--charter-beta-dev--qa--prod-split)
    - [5.1 QA environment shape (lean tier, ~+$40–60/mo)](#51-qa-environment-shape-lean-tier-4060mo)
    - [5.2 What runs where in Phase 2](#52-what-runs-where-in-phase-2)
  - [6. Transition: Current → Phase 1](#6-transition-current--phase-1)
  - [7. Transition: Phase 1 → Phase 2](#7-transition-phase-1--phase-2)
  - [8. Cost Management Rules (Profiles)](#8-cost-management-rules-profiles)
    - [Phase 1 rules (now)](#phase-1-rules-now)
    - [Phase 2 rules (beta)](#phase-2-rules-beta)
  - [9. Environment × Testing Responsibility Matrix](#9-environment--testing-responsibility-matrix)
    - [Test Suite Trigger Reference](#test-suite-trigger-reference)
  - [10. Document Maintenance Rules](#10-document-maintenance-rules)

---

## 1. Purpose & Phase Model

Pilot operates under a **$1,000/month infrastructure hard cap** (see [`.roo/rules-pilot-architect/infrastructure-constraints.md`](../../.roo/rules-pilot-architect/infrastructure-constraints.md)). A fully isolated QA environment (own cluster/RDS/ALB/NAT) would add $250–350/month and is **rejected pre-revenue**. Environment strategy is therefore phased:

| Phase | Window | Environments | Trigger to enter |
|---|---|---|---|
| **Phase 1** | Now → start of Charter beta | `local dev` + `prod` (prod runs in vendor **test modes** = de facto integration env) | Already active |
| **Phase 2** | Charter beta onward | `local dev` + `qa` (lean tier on shared infra) + `prod` (live, sacred) | First Charter member invited to sign up |

**Core principle**: *Prod may only be used for integration testing while it contains zero real customer data. The moment a real Charter member signs up, prod becomes sacred and all mutating test activity moves to QA.*

---

## 2. Third-Party Integration Inventory & Test Modes

| Vendor | Test facility | Test-mode cost | Phase 1 posture (prod) | Phase 2 QA posture | Phase 2 prod posture |
|---|---|---|---|---|---|
| **Stripe** | Full test mode (keys, prices, webhooks, cards) | $0 | **Test keys** in `pilot/prod/stripe`; test webhook endpoint → `api.pilotfortrades.com`; card `4242 4242 4242 4242` | Test keys in `pilot/qa/stripe`; separate test webhook endpoint → `qa-api.pilotfortrades.com` | **Live keys**; live webhook endpoint; live price IDs in DB |
| **Telnyx** | No sandbox — real number required; `SmsCarrier` mock for CI/local | ~$1–5/mo | Real Telnyx (10DLC live campaign), low volume. Signup E2E uses real owner phone numbers | Real Telnyx, **separate QA messaging profile + QA phone number** (~$1/mo). Mock carrier remains for local/CI only | Real Telnyx, production messaging profile/number |
| **SendGrid** | Sandbox mode (accepts, never delivers) | $0 | Live key, low volume (signup emails must actually arrive for testing) | Sandbox or dedicated QA key; verify DKIM once, then sandbox | Live key |
| **QuickBooks Online** | Free sandbox companies | $0 | Sandbox company + sandbox app credentials (`QUICKBOOKS_ENVIRONMENT=sandbox`) | Sandbox company (separate from Phase 1 sandbox to avoid cross-talk) | Production app + real tenant companies |
| **Google Maps** | No sandbox; separate key with quota caps | $0–10/mo | Prod key with existing Redis caching (24h TTL) | Separate QA key with **daily quota cap** to bound spend | Prod key, quota alerts |
| **Cognito** | Separate user pools | $0 (free tier) | Prod pool (real signups = test users, purged at cutover). **SMS MFA via SNS (MFA-WIRE-1, 2026-08-16)**: account is SNS-SMS-sandboxed with zero origination numbers + $1 `MonthlySpendLimit` — production access / **US toll-free origination number + toll-free verification (2FA/OTP)** / $25 cap pending Tom's AWS Support case (ADR-0015; `pilot-launch-plan.md` _(private)_ Section 1). Account-level posture → the Phase 2 QA pool's SMS MFA inherits the same dependency | **QA pool** (mirrors prod config per [`aws-cognito-dev-setup-prod-mirror.md`](aws-cognito-dev-setup-prod-mirror.md)) | Prod pool |
| **Cloudflare Turnstile** | Published always-pass/always-fail test keys | $0 | Test keys acceptable; live keys also fine (free) | Test keys | Live keys |
| **OpenAI** (embeddings only) | No sandbox; metered | ~$1/mo QA volume | Live key (help-corpus embeddings) | Same account, low volume | Live key |
| **Voice AI (Whisper/Ollama)** | Own g4dn.xlarge GPU | Already in baseline | Prod GPU, started only for Voice AI test sessions (`profile-b-app.sh ai`) | Shared prod GPU initially; QA traffic routed to it (sub-linear scaling rule) | Prod GPU |
| **Expo push** | Free | $0 | Live | Live | Live |

**Local dev / CI posture**: local dev runs a deliberate subset of **real** integrations (Tom, 2026-08-18): **QuickBooks** (sandbox — multiple sandbox companies supported), **Cognito** (dev pool; MFA Disabled), **SendGrid** (one shared account serves all environments). Still mocked/stubbed in local dev: **Telnyx** (`SMS_CARRIER` mock / `TELNYX_10DLC_MOCK=true` — real Telnyx beyond prod is limited to Phase 2 QA (own messaging profile + number; dev/e2e mock permanently — Tom 2026-08-18, [`batch-db-mgmt-1-design.md`](../architecture-design/batch-designs/batch-db-mgmt-1-design.md) §G-11 Option A), **MFA** (`MFA_COGNITO_MOCK=true`; dev pool MFA is Disabled), **Stripe** (test keys + `stripe listen` CLI forwarding — never live), MSW on the frontend. **CI remains 100% mocked** across all vendors.

---

## 3. Secrets & Environment Variable Inventory

### 3.1 Secrets Manager secrets (mounted via `valueFrom` at container start)

All three backend services (`pilot-api`, `pilot-celery-worker`, `pilot-celery-beat`) mount the shared `local.common_secrets` block ([`infrastructure/terraform/modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf) lines 220–242). **A secret change takes effect only after `aws ecs update-service --force-new-deployment` — no image rebuild is ever needed for secret rotation.**

| Secret | Env vars injected | Phase 1 value | Phase 2 prod value |
|---|---|---|---|
| `pilot/prod/db` | `DATABASE_URL` | prod RDS | prod RDS (QA gets `pilot/qa/db`) |
| `pilot/prod/redis` | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_URL` | prod ElastiCache (DB 0/1/2) | same |
| `pilot/prod/sendgrid` | `api_key` (Console-created; key name is `api_key`, not `SENDGRID_API_KEY` — the Custom Email Sender Lambda handler accepts both) | live key | live key |
| `pilot/prod/telnyx` | `TELNYX_API_KEY`, `TELNYX_PUBLIC_KEY`, `TELNYX_MESSAGING_PROFILE_ID`, `PILOT_PLATFORM_SMS_NUMBER` | live (10DLC campaign) | live |
| `pilot/prod/stripe` | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CONNECT_PLATFORM_KEY`, `STRIPE_CONNECT_WEBHOOK_SECRET` | **`sk_test_…` / `pk_test_…` / test `whsec_…` / sandbox Connect key / test Connect `whsec_…`** | **`sk_live_…` / `pk_live_…` / live `whsec_…` / live Connect key / live Connect `whsec_…`** |
| `pilot/prod/quickbooks` | `QUICKBOOKS_CLIENT_ID`, `QUICKBOOKS_CLIENT_SECRET`, `QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN` | sandbox app creds | production app creds |
| `pilot/prod/encryption` | `ENCRYPTION_KEY` | Fernet key (never rotate without migration plan) | same key |
| `pilot/prod/cognito` | `COGNITO_USER_POOL_ID` | prod pool | prod pool |
| `pilot/prod/google-maps` | `GOOGLE_MAPS_API_KEY` | prod key | prod key |
| `pilot/prod/turnstile` | `CLOUDFLARE_TURNSTILE_SECRET_KEY` | test or live | live |

### 3.2 Task-definition environment variables (plain, in Terraform)

| Var | api | worker | beat | Notes |
|---|---|---|---|---|
| `ENVIRONMENT` | `production` | `production` | `production` | QA tasks use `qa` |
| `TEST_ENDPOINT_ENABLED` | `false` | `false` | `false` | **Must stay `false` in any internet-facing env** |
| `SMS_CARRIER` | `telnyx` | `telnyx` | `telnyx` | Explicit per §19.6/§19.7 addendum — never rely on code default |
| `TELNYX_10DLC_MOCK` | `false` | `false` | `false` | Same — explicit in prod |
| `MFA_COGNITO_MOCK` | `false` (explicit) | — | — | MFA-WIRE-1 (design 2026-08-16): mock↔real Cognito MFA client seam (`services/cognito_mfa_client.py`). Code default = `true` (mock) for local dev/CI — the dev pool has MFA Disabled, so real enrollment only works against prod. Prod api task def must set explicit `false` per the §19.6 addendum lesson (same class of incident as `TELNYX_10DLC_MOCK`) |
| `QUICKBOOKS_ENVIRONMENT` | `production` → **`sandbox` in Phase 1** | same | — | Flip to `production` at cutover |
| `FORWARDED_ALLOW_IPS` | `*` (api only) | — | — | ALB is sole ingress; required for https redirects |
| `SENDGRID_FROM_EMAIL` | `noreply@pilotfortrades.com` | same | — | |
| `TENANT_SITES_BASE_DOMAIN` | `p4tsites.com` (registered via Cloudflare 2026-08-14; ADR-0014) | same | — | C-B16 tenant-site hosting — backend builds `https://{slug}.{domain}` URLs. Local dev: `localhost:3000`. **✅ LIVE in prod 2026-08-26** (C-B16-OPS Step 4 — added to `pilot-api` + `pilot-celery-worker` task defs in TF) |
| `MAP_CACHE_ENABLED` | `true` | `true` | — | TEST-UPLIFT-1A: Maps drive-time Redis cache toggle. Code default = `False` (OFF); prod must set `true` explicitly. Protects ~$77/mo variable Maps spend (per `scaling-logic.md` §4). **TF diff prepared 2026-08-27 — Tom/DevOps applies at next deploy window.** |
| `MAP_CACHE_TTL_SECONDS` | `86400` | `86400` | — | TEST-UPLIFT-1A: Maps cache TTL (24h). Code default = `86400`; set explicitly in prod for parity with the §19.6 addendum lesson. |

Web dashboard (`pilot-web`) env: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_*`, `NEXT_PUBLIC_USE_MOCK_AUTH=false`, `NEXT_PUBLIC_USE_MSW_MOCKS=false`, `NODE_ENV=production`. **`NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` is NOT in the task def** — Next.js inlines `NEXT_PUBLIC_*` at **image build time** (frontend fallback: `pk_test_placeholder`). Changing the publishable key mode requires a **`pilot/web` image rebuild**, not just a redeploy. It only matters when the paid-tier Stripe Elements card form renders (charter/trial paths never load it).

Tenant-site hosting (C-B16): the web task def adds `NEXT_PUBLIC_TENANT_SITES_DOMAIN` (same value as the backend `TENANT_SITES_BASE_DOMAIN` above) — consumed by `src/proxy.ts` host-rewrite (Next.js 16 convention; `middleware.ts` deprecated — TS-BUG-1). Like all `NEXT_PUBLIC_*` values it is inlined at **image build time**, so changing the domain requires a `pilot/web` image rebuild. **✅ LIVE in prod 2026-08-26** (C-B16-OPS Step 4 + Step 5 — added to `pilot-web` task def in TF + Dockerfile `ARG NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com` build-arg added to [`frontend/apps/web/Dockerfile`](../../frontend/apps/web/Dockerfile); web image rebuilt + pushed with `--build-arg NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com`). **TS-BUG-1 (2026-08-26)**: non-public **`TENANT_SITES_DOMAIN=p4tsites.com`** added to `pilot-web` — Dockerfile builder ARG + runner-stage ENV + task-def row (TF, `modules/compute/main.tf` `aws_ecs_task_definition.web`) — read at **runtime** by `src/proxy.ts` (Node.js runtime in Next 16); belt-and-suspenders behind the proxy's hard-coded multi-domain fallback (`p4tsites.com`, `localhost`). Confirmed the hard way: Next.js inlines `process.env.*` at build time in the proxy bundle **even for non-`NEXT_PUBLIC_` vars**, and `request.nextUrl.hostname` is unreliable behind the ALB — `proxy.ts` reads the `Host` header directly (react-engineer rule §37). **Registrar/DNS posture (ADR-0014, 2026-08-14)**: `p4tsites.com` registered via **Cloudflare** ($10.46/yr — Cloudflare is our registrar going forward; GoDaddy $22 / Route 53 $16 declined); DNS lives in Cloudflare (wildcard **DNS-only**; apex/www proxied only to power the edge 301 → `pilotfortrades.com`); **no Route 53 hosted zone**. Cost impact: **+$0.87/mo** amortized (vs. +$1.58 originally estimated — the $0.50/mo hosted zone is avoided).

---

## 4. Phase 1 — Pre-Beta: Prod-as-Integration-Env

### 4.1 Rule set (binding)

1. **Prod runs uniformly in vendor test modes.** Mixed mode (live key + test price ID, or live `whsec_` + test events) is the exact failure class that stranded the 2026-08-10 signup test — live keys never touch prod in Phase 1.
2. **Every signup in Phase 1 is a test tenant.** No real customer accounts. Test tenants are purged with [`backend/scripts/acct-signup-db-cleanup.sql`](../../backend/scripts/acct-signup-db-cleanup.sql) before Phase 2 cutover.
3. **Signup state semantics**: `tenant_signup.signup_state` = last *completed* step (`step3_phone` ⇒ the Plan page). Never hand-advance state or hand-insert `subscription` rows — that skips tier lock, charter number assignment, and Stripe creation. The local `subscription` row is written **only** by the Stripe webhook `handle_subscription_created()` (charter/paid); trial signups intentionally never write one.
4. **Telnyx stays real** (no sandbox exists); volume is trivial and 10DLC campaign health benefits from real traffic.
5. **Migrations against prod follow rolling-deploy (expand/contract) constraints** (inserts-only during testing windows; DDL changes require snapshot per [`aws-ops-runbook.md`](aws-ops-runbook.md)).

### 4.2 What runs where in Phase 1

| Activity | Where |
|---|---|
| Unit/component tests, rapid iteration | Local dev (docker-compose), all vendors mocked |
| PR gating (`pytest -m unit`, frontend suites) | GitHub Actions CI, 100% mocked |
| Signup wizard E2E, SMS double-opt-in (real delivery), Stripe test-card billing + webhook E2E, QBO sandbox sync, Voice AI latency | **Prod** (test modes) |
| Marketing site + waitlist form | Prod (`profile-a-marketing.sh`) |

---

## 5. Phase 2 — Charter Beta: Dev / QA / Prod Split

### 5.1 QA environment shape (lean tier, ~+$40–60/mo)

QA shares fixed-cost infrastructure rather than duplicating it (sub-linear scaling philosophy):

- **Compute**: new ECS services on the existing `pilot-production` cluster (`pilot-qa-api`, `pilot-qa-worker`, `pilot-qa-beat`, `pilot-qa-web`, 0.25 vCPU each) — ~$30–40/mo
- **Database**: separate **RDS `db.t4g.micro`** (~$15/mo) — QA must never share the prod schema (migration rehearsal fidelity)
- **Redis**: additional logical DB indexes on the existing `cache.t4g.micro` — $0
- **Ingress**: listener rules on the existing ALB for `qa-api.pilotfortrades.com` + `qa-app.pilotfortrades.com` — ~$0 marginal
- **Secrets**: `pilot/qa/*` prefix, all vendor test modes (§2, §3)
- **Cognito**: QA user pool mirroring prod config
- **GPU**: shared prod g4dn.xlarge initially (Voice AI QA routes to it); dedicated QA GPU only if contention measured
- **Terraform**: refactor `environments/production` into a reusable environment module, then instantiate `environments/qa` — **Architect approval + cost-delta flag required** before `terraform apply` (infrastructure-constraints.md §1)

Projected total at Phase 2 entry: ~$920–950/mo at the MVP tier — inside the $1k cap with thin buffer. If beta drives prod scale-up triggers ([`scaling-logic.md`](../../.roo/rules-pilot-architect/scaling-logic.md)), re-run the cost model before applying.

### 5.2 What runs where in Phase 2

| Activity | Where |
|---|---|
| Unit/component | Local dev (mocked) |
| PR gating | CI (mocked) |
| All integration + E2E incl. real Telnyx SMS, Stripe test billing, QBO sandbox, migration rehearsal | **QA** |
| Synthetic smoke only: health endpoints, canary login, read-only checks | **Prod** |
| Mutating test flows of any kind in prod | **Forbidden** |

---

## 6. Transition: Current → Phase 1

Execute once, in order (DevOps + Tom):

1. **Stripe secret flip** — Secrets Manager → `pilot/prod/stripe` → replace with test-mode values:
   `secret_key = sk_test_…`, `publishable_key = pk_test_…`, `webhook_secret = whsec_…` (from the **test-mode** webhook endpoint created in step 2).
2. **Register test-mode webhook** — Stripe Dashboard (test mode ON) → Developers → Webhooks → Add endpoint:
   - **Endpoint URL**: `https://api.pilotfortrades.com/api/v1/webhooks/stripe`
   - **Event destination**: "Your account" (not "Connected accounts" — that's for the P2 Stripe Connect invoice-payment flow, `pilot-operations.md` _(private)_ §11)
   - **API version**: current (match the version pinned on the existing ngrok + live-ALB endpoints so all three deliver identical payload shapes)
   - **Events**: all 15 (the canonical set per [`stripe-ops-runbook.md`](../integrations/stripe/stripe-ops-runbook.md) §9 — 10 original + 5 C-B4: `customer.subscription.trial_will_end`, `customer.subscription.paused`, `customer.subscription.resumed`, `checkout.session.completed`, `payment_method.attached`)
   - **Create** → copy the signing secret (`whsec_…`) into step 1.

   This creates a **separate test-mode endpoint** at the same URL as the live-ALB endpoint — Stripe treats live-mode and test-mode webhook endpoints as independent objects, each with its own `whsec_`. The existing ngrok test endpoint stays for local dev only. See [`stripe-ops-runbook.md`](../integrations/stripe/stripe-ops-runbook.md) §9 for the three-endpoint model.
3. **Verify DB price IDs are test-mode** — run the §5 verify query; expected test IDs per §4 — **the `price_REDACTED…` mapping-file family as of 2026-08-18** (the 2026-08-08 test bootstrap re-run superseded the manually-created `price_REDACTED…` family; `_env_profiles.py` realigned 2026-08-18, dev DB catches up on the next converge). Live IDs unchanged (`price_REDACTED…` / `price_REDACTED…` family — the 2026-08-04 live bootstrap adopted them).
4. **QuickBooks** — set `QUICKBOOKS_ENVIRONMENT=sandbox` in the api/worker task defs (Terraform) and point `pilot/prod/quickbooks` at the sandbox app credentials. `terraform apply`.
5. **Redeploy all three backend services** (secrets inject at container start):
   ```bash
   for svc in pilot-api pilot-celery-worker pilot-celery-beat; do
     aws ecs update-service --cluster pilot-production --service $svc --force-new-deployment --region us-east-1
   done
   ```
   No image rebuild. If paid-tier card-form testing is planned, also verify what `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` the `pilot/web` image was built with; rebuild web only if it isn't `pk_test_…`.
6. **Purge prior test signups** — run [`acct-signup-db-cleanup.sql`](../../backend/scripts/acct-signup-db-cleanup.sql) via the RDS tunnel for any half-created tenants (e.g. the Lang Electric Co. row set deleted 2026-08-10).
7. **Verification E2E** — full signup wizard with a real phone (double opt-in YES), charter tier, then verify: `tenant_signup.signup_state='complete'`, `subscription` row present (created by the Stripe webhook), Stripe test-mode dashboard shows the customer + subscription, Telnyx portal shows the opt-in exchange.

---

## 7. Transition: Phase 1 → Phase 2

**Gate**: entry requires (a) first Charter member ready to onboard, (b) Phase 1 verification E2E green, (c) Tom approval of the QA cost delta.

Steps, in order:

1. **Terraform QA environment** — refactor to environment module; instantiate `environments/qa` (services, QA RDS, QA secrets, ALB listener rules, QA Cognito pool). `terraform apply`. Run `generate-infra-state.sh` afterwards.
2. **Seed QA** — DB-MGMT-1 / ADR-0016 flow (2026-08-18): `DATABASE_URL=<qa tunnel URL> python migrations/scripts/provision_schema.py --env qa` (schema-restore from dev), then `DATABASE_URL=<qa tunnel URL> python migrations/scripts/seed_qa_db.py` (Groups A→B→C→D, idempotent converge). Operator-side `SEED_ENV=qa` is equivalent to `--env qa` (flag takes precedence). No scenario data unless a test needs it (trim the orchestrator's Group D step). See [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §7.6.
3. **QA vendor wiring** — `pilot/qa/stripe` test keys + **separate** test webhook endpoint → `qa-api.pilotfortrades.com`; QA Telnyx number + messaging profile; SendGrid sandbox key; QBO fresh sandbox company; Maps QA key with quota; Turnstile test keys.
4. **Prod cutover ceremony** (single session, runbook-logged):
   a. Snapshot prod RDS.
   b. Purge all Phase 1 test tenants via `acct-signup-db-cleanup.sql`.
   c. Run the §5 **live** price-ID SQL against prod `subscription_tier`.
   d. Flip `pilot/prod/stripe` to live keys; register the **live** webhook endpoint; set `QUICKBOOKS_ENVIRONMENT=production`.
   e. `force-new-deployment` on api/worker/beat.
   f. Flip marketing site from `coming_soon` per launch checklist.
5. **Post-cutover verification**:
   - QA: repeat the §6 step-7 E2E against `qa-app.pilotfortrades.com` — must pass fully in test modes.
   - Prod: synthetic smoke only (health, login, read-only dashboard checks). First Charter signup is performed **by the real customer**, observed via logs — never simulated.
   - Confirm no test-mode price IDs remain in prod (`§5` verify query) and no live keys exist anywhere in QA.

---

## 8. Cost Management Rules (Profiles)

Profiles are enforced by the scripts in [`infrastructure/scripts/`](../../infrastructure/scripts/README.md). Always confirm with `./profile-status.sh` after any change.

### Phase 1 rules (now)

| Situation | Profile | Monthly |
|---|---|---|
| **Not coding / not testing** (nights, weekends, gaps) | `./profile-a-marketing.sh` — marketing site live, API minimal | ~$148 |
| Coding/testing app without Voice AI | `./profile-b-app.sh light` | ~$170 |
| Voice AI testing only | `./profile-b-app.sh ai` (GPU on) | ~$562 |
| Extended inactivity (>1 week) | `./profile-off.sh` | ~$102 |

Rule: **the GPU (`g4dn.xlarge`, ~$390/mo running) is started only for active Voice AI sessions and stopped the same day.** Default idle state in Phase 1 is `marketing`, never `app-ai`.

### Phase 2 rules (beta)

- **Beta active (Charter members live)**: prod runs `profile-c-full.sh` continuously — this is customer-facing; do not scale down while members are active.
- **QA when not integration-testing**: `./profile-off.sh`-equivalent for QA services (QA ECS to 0 tasks; QA RDS stop is allowed up to 7 days — AWS auto-restarts stopped RDS after 7 days, so for longer gaps snapshot-and-delete or accept the ~$15/mo).
- **QA light vs normal**: run QA **light** (api + web only, 1 task each, no worker/beat, GPU shared-off) for UI/manual QA; run QA **normal** (all four services + worker/beat) only for integration/E2E sessions involving SMS, Celery jobs, webhooks, or Voice AI.
- Re-check total monthly projection after any profile change against the $1k cap; deltas >$25/mo require Tom sign-off.

---

## 9. Environment × Testing Responsibility Matrix

| Layer | Purpose | Third parties | Mutating signup/billing tests allowed? |
|---|---|---|---|
| Local dev | Unit/component, iteration | All mocked; Cognito login real; Stripe CLI forward optional | Local DB only |
| CI (GitHub Actions) | PR gating | 100% mocked/MSW — no live credentials ever | n/a |
| **Prod (Phase 1)** | Integration/E2E + marketing | Vendor test modes; Telnyx real | **Yes** — all signups are test tenants, purged before cutover |
| **QA (Phase 2)** | Integration/E2E + migration rehearsal | Vendor test modes; Telnyx real QA number | **Yes** — QA only |
| **Prod (Phase 2)** | Customers + synthetic smoke | Live | **No — never** |

### Test Suite Trigger Reference

Per launch-plan §3 "Test environment layering" standing policy. **Never fire real customer SMS on prod.**

| Suite | Trigger command | Where it runs | Vendor posture |
|---|---|---|---|
| Unit | `python -m pytest -m unit` | local dev + CI | all vendors mocked (autouse fixtures) |
| System / domain | `python -m pytest tests/domains/<domain>/ -m unit` | local dev | mocked |
| Integration | `python -m pytest -m integration` | dev stack | per env plan §2 (Stripe test mode; Telnyx mock/live toggle) — **never fire real customer SMS on prod** (launch-plan §3 standing policy) |
| E2E web | Playwright suite (per `aws-ops-runbook.md` §20) | prod (Phase 1 integration env) | live, test tenants only |
| E2E mobile | Maestro specs | iOS Expo dev build | live, test tenants only |
| Vendor-marked | `-m requires_telnyx / requires_stripe / requires_sendgrid / requires_redis` | on demand, env vars coordinated with Tom | vendor test modes |

**Default full-suite gate** (Tom's standing instruction 2026-08-16 — excludes slow vendor/live-service suites):

```bash
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q
```

**Vendor-suite inclusion rule**: if a batch modifies code those suites cover (Telnyx carrier/webhooks, Stripe billing/webhooks, SendGrid email dispatch, or Redis-dependent modules), also run the affected marker suite before sign-off.

---

## 10. Document Maintenance Rules

1. This doc is owned by the **Pilot Architect** (Responsible + Accountable); the DevOps Engineer executes procedures and proposes edits.
2. **Update triggers** (edit this doc in the same change as the triggering work — documentation-as-code):
   - Any secret added/removed/renamed in `local.common_secrets` or task-def env vars → update §3.
   - Any new third-party integration → add to §2 with its test-mode posture.
   - Any change to profile scripts or their cost model → update §8.
   - Any environment added/removed (e.g. QA provisioning) → update §1, §5, §9.
   - Stripe mode flips (test↔live) are recorded here with date.
3. Registry: this doc is listed in [`pilot-docs-list.md`](../../pilot-docs-list.md); keep its version/date in sync on every edit.
4. Rules linkage: this doc is a standing reference in [`.roo/rules-pilot-architect/pilot-architect-rules.md`](../../.roo/rules-pilot-architect/pilot-architect-rules.md) §10 — the Architect reads it before any batch design that touches infrastructure, secrets, environments, or third-party credentials. Backend/frontend engineer inclusion docs do **not** reference it — environment management is an Architect/DevOps concern; engineers only consume the *outcomes* (e.g. `TEST_ENDPOINT_ENABLED=false` in deployed envs, mocked carriers locally) which are already covered by their existing rules.
