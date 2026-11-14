# Batch SIGNUP-GA-1 — Self-Serve Cognito Credential Creation (Pre-GA)

**Version**: 2.0
**Date**: 2026-07-29
**Author**: Pilot Architect
**Batch type**: Backend (Python Engineer) + DevOps (Cognito pool/Lambda). A web/mobile FE follow-on (`SIGNUP-GA-1-FE`) is noted but out of scope here.
**Priority / Phase**: P1 / **Pre-GA** (not Beta-blocking — Beta remains concierge; this un-blocks self-serve GA)
**Plan link**: `pilot-launch-plan.md §2.3 row 14a` + §2.3 card
**Input doc**: `pilot-founder-onboarding-process.md §5, §10 (Gap G1, G6)`
**ADRs**: `ADR-0011` (self-sign-up → Lambda) + `ADR-0012` (drop tenant-name uniqueness)
**Python prompt** (to follow, after Tom approval): `batch-signup-ga-1-python-engr-prompt.md`
**DevOps prompt** (to follow, after Tom approval): `batch-signup-ga-1-devops-prompt.md`

> **Why this batch now (Tom, 2026-07-29)**: closing Gap **G1** is the biggest single risk in the self-serve onboarding chain, and Tom wants it built next (after UP-1) so the **full onboarding flow can be tested end-to-end** — marketing lead → self-serve account birth (with a real credential) → login → wizard → dashboard — without a manual concierge step. Beta stays concierge; this batch makes GA self-serve *possible and testable*.

> **v2.0 changes (Tom decisions, 2026-07-29)**: (1) the Post-Confirmation Lambda is specified as a **3-path user-provisioning router** (not "`_signup_impl` in prod") covering all 4 user types; (2) the placeholder-tenant-name design is **simplified** — the `tenant_name_key UNIQUE(name)` constraint is being **dropped** (ADR-0012), so the collision-proof-suffix machinery from v1.0 is removed and the Lambda inserts the friendly name unconditionally; (3) abandoned-signup cleanup keys off `tenant_signup.signup_state`, never the name; (4) `owner_email` persistence confirmed; (5) explicit scope split for user types (i)/(ii)/(iv) as follow-on batches.

---

## A. Input Read Summary

| Input | Section(s) read | What it told us |
|---|---|---|
| `pilot-founder-onboarding-process.md` | §5 (provisioning seam), §6 (wizard state machine), §10 (G1, G3, G6) | Self-registration is **disabled** in Cognito; the wizard collects **no password**; the Post-Confirmation Lambda is the prod bridge Cognito→RDS. G1 = no credential creation in the self-serve path. G6 = **two** `signup` backends (`auth.py` dev/test stand-in vs `signup.py` wizard state machine) must not be conflated. |
| Live DB via `postgres-local` MCP (2026-07-29) | `tenant_signup`, `user`, `tenant_user`, `tenant_user_invite`, `tenant` indexes/constraints | **`tenant_signup` has NO `id` PK** — keyed by `tenant_id` (one signup per tenant). No `owner_email`/name columns (verified — `initiate_signup()` drops them). **`user` has NO `cognito_sub` column** — Cognito↔RDS join is **email** only. **`user.is_platform_user`** (bool, NOT NULL) + **`user.platform_role_code`** (nullable) are the platform-vs-tenant discriminator. **`tenant_user`** has `invited_at`/`joined_at` (invited-vs-joined). **`tenant_user_invite`** exists (`email`, `token_hash`, `expires_at`, `accepted_at`, `invited_by`, `tenant_id`, `is_active`) — makes user-type (iv) deterministic. **`tenant.name` has a UNIQUE index (`tenant_name_key`)** and **no FK anywhere targets `tenant.name`** (all FKs → `tenant.id`). All 5 current `user` rows are `is_platform_user=false`. |
| `tenant_signup.py` | full | `initiate_signup()` creates `Tenant` + `TenantSignup(signup_state='step1_account')`; owner email/name are **not** written. Steps 2–5 advance state; step 5 calls `activate_trial()`. No user row, no Cognito call anywhere in the wizard path. |
| `auth.py::_signup_impl` | full | The dev/test stand-in that creates `User` + `UserEndpoint(email)` + `TenantUser(owner)` + role/status — a **simulation of the prod Post-Confirmation Lambda**. It also does a `Tenant.name` uniqueness pre-check (`400 "Tenant with this name already exists"`, `auth.py`) — the **only** code that treats `tenant.name` as unique. Its only test is `test_auth.py`. |
| `core/auth.py` | `verify_cognito_jwt`, JWKS | JWT verification is JWKS-based; the app resolves the caller to a `user` row by the token's `email` claim (no `sub` linkage). **Email is the join key** between Cognito and RDS. |
| `pilot-operations.md §5, §13` | founders billing (G3), login/MFA | Founders billing (G3) needs a `stripe_customer_id` not created at signup — **out of scope** here. MFA wiring (G4/MFA-WIRE-1) is a **separate** open batch — this batch must not depend on or duplicate it. |
| `infrastructure-constraints.md` | cost cap | Cognito is already the auth authority; self-sign-up adds **$0** (within the Cognito free MAU tier at 100 users). No new AWS service, no baseline delta — no founder cost review required. |
| `pilot-adr-log.md` | Decision Index | No ADR governed credential creation or tenant-name uniqueness. This design proposes **ADR-0011** (self-sign-up → Lambda) and **ADR-0012** (drop tenant-name uniqueness) — both boundary-crossing, multi-option, hard-to-reverse. |

**Key findings**:
1. The self-serve gap is that **step 1 never creates an authentication credential**, and the app has **no `cognito_sub` linkage** (email is the only join). The design must create a Cognito user whose email exactly matches the `user.email` the Lambda will create — no schema change to store a `sub` is required (that is a separate, larger decision).
2. The **4-user-type taxonomy is already encoded** in the schema (`is_platform_user`, `platform_role_code`, `tenant_user.invited_at/joined_at`, `tenant_user_invite`). The Lambda does **not** need new columns — it needs to **use** what's there. A naive "Lambda always creates a tenant" is wrong for 3 of the 4 types.
3. **Nothing FKs off `tenant.name`** — the `tenant_name_key` UNIQUE index is display-only and its sole code dependency is the `_signup_impl` pre-check we are already reworking for G6. Dropping it (ADR-0012) removes the only exception path that could strand a Cognito confirmation.

---

## A.1 — Decisions recorded: ADR-0011 (Accepted) + ADR-0012 (Accepted)

Both ADRs are recorded in `pilot-adr-log.md`. Summary here for continuity:

- **ADR-0011 — Self-serve credential creation via Cognito self-sign-up feeding the Post-Confirmation Lambda.** Client calls Cognito `SignUp` (email+password) via Amplify; on email confirmation the **existing** Post-Confirmation Lambda writes to RDS; the wizard step 1 **resolves-or-attaches by email** (never forks a second tenant). Backend takes **no** Cognito admin IAM and never handles the password. Self-registration re-enabled but rate-limited + Turnstile-guarded at the `/sign-up` edge. Rejected: (A) backend `AdminCreateUser` — too much backend IAM + password handling; (C) Hosted UI — poor brand/UX.
- **ADR-0012 — Drop global tenant-name uniqueness (`tenant.name` is display-only).** Nothing FKs off `tenant.name`; the only code dependency is the `_signup_impl` pre-check. Dropping `tenant_name_key` (a) allows legitimately-identical business names across regions (e.g., two "ABC Plumbing, LLC" in MD and DE), and (b) **removes the collision path that could throw inside the Post-Confirmation Lambda and strand a Cognito confirmation** — the load-bearing reason it composes with ADR-0011. Rejected: keep the constraint + collision-proof-suffix machinery (unnecessary complexity guarding a constraint with no referential value).

> **Architect note**: This batch is **Architect-designed but cross-agent** (Python Engineer + DevOps). The Python Engineer half cannot merge to prod behavior until DevOps lands the pool/Lambda change. Tom's approval of ADR-0011 **and** ADR-0012 is the hard gate before either half starts.

---

## A.2 — The 4 user types and the Lambda's 3 code paths

The Post-Confirmation Lambda fires on **every** confirmation in the pool, so it must **route**, not blindly create a tenant. The four user types map to three code paths:

| # | User type | How the type is known at confirmation time | Lambda path |
|---|---|---|---|
| (i) | **Platform owner** (Tom) | Provisioned by admin; `user.is_platform_user=true` + `platform_role_code` set; **no** `tenant_user_invite` and **no** self-serve marker | **Path 1 — existing/platform user: no-op** (do not create a tenant) |
| (ii) | **Platform user** (Tom's employees) | Admin-created via a future platform-admin UI; `is_platform_user=true` | **Path 1 — no-op** (row already created by the admin flow) |
| (iii) | **Tenant owner** (self-serve GA — *this batch's product goal*) | Cognito `SignUp` with **no** matching `user` and **no** pending `tenant_user_invite` for the email | **Path 3 — new-owner create**: create `tenant` (placeholder name) + owner `user` + `tenant_user(owner, joined_at=now)` |
| (iv) | **Tenant user** (employee invited by a tenant owner) | A **pending** `tenant_user_invite` (`accepted_at IS NULL`, `is_active=true`, not expired) exists for the email | **Path 2 — pending-invite attach**: create the `user`, attach `tenant_user` to the invite's `tenant_id`, set `joined_at`/`accepted_at`; **do not** create a tenant |

**Routing key**: the Lambda branches on `email` against `user` (already exists → Path 1 no-op) → then `tenant_user_invite` (pending invite → Path 2 attach) → else (→ Path 3 new-owner create).

**Scope**: SIGNUP-GA-1 **builds the full 3-path router now** (cheap to do once; protects types i/ii/iv from misfires even before their UIs ship) but only ships the **type-(iii)** self-serve product surface. Types (i)/(ii) platform-admin provisioning UI and type-(iv) invite-send UI are **follow-on batches** (§H).

---

## B. Migration Plan

**Two schema changes, both in a single blank Alembic migration** (both nullable-safe / drop-only — no 3-part NOT NULL pattern, no backfill):

### B.1 — Drop `tenant_name_key` UNIQUE(name) (ADR-0012)
```python
op.drop_constraint("tenant_name_key", "tenant", type_="unique")
```
- **MCP-confirmed** the object is a UNIQUE index/constraint named `tenant_name_key` on `public.tenant(name)`; no FK targets `tenant.name`.
- **Downgrade** re-adds it (`op.create_unique_constraint("tenant_name_key", "tenant", ["name"])`) — but note this is a one-way door in practice: once duplicate names exist, downgrade will fail (documented, acceptable).

### B.2 — Add `tenant_signup.owner_email` (+ optional names), nullable (Tom-approved)
```python
op.add_column("tenant_signup", sa.Column("owner_email", sa.Text(), nullable=True))
op.add_column("tenant_signup", sa.Column("owner_first_name", sa.Text(), nullable=True))
op.add_column("tenant_signup", sa.Column("owner_last_name", sa.Text(), nullable=True))
```
- Fixes the latent "drop the owner email/name passed to `initiate_signup()`" bug and makes step-1 resolution + abandoned-signup observability deterministic.
- Roll into `seed_*` per Rule 20 for any scenario seed that creates `tenant_signup` rows (Python Engineer confirms which via MCP + `README-seed-data.md`).

> **MCP verification queries (Python Engineer must re-run before any SQL, Rule 3):**
> ```sql
> -- confirm the unique index exists and its exact name before dropping
> SELECT indexname, indexdef FROM pg_indexes
> WHERE schemaname='public' AND tablename='tenant' AND indexdef ILIKE '%UNIQUE%';
> -- confirm tenant_signup shape (no id PK, no owner_email yet)
> SELECT column_name, data_type, is_nullable FROM information_schema.columns
> WHERE table_schema='public' AND table_name='tenant_signup' ORDER BY ordinal_position;
> -- confirm user has no cognito_sub (email is the only join)
> SELECT column_name FROM information_schema.columns
> WHERE table_schema='public' AND table_name='user' AND (column_name ILIKE '%cognito%' OR column_name ILIKE '%sub%');
> -- confirm invite table shape for Path 2
> SELECT column_name, data_type, is_nullable FROM information_schema.columns
> WHERE table_schema='public' AND table_name='tenant_user_invite' ORDER BY ordinal_position;
> ```

**Pre-migration state**: `tenant.name` UNIQUE; `tenant_signup` keyed by `tenant_id`, no owner-identity columns; `user` has no `cognito_sub`.

---

## C. Execution Order

| # | Step | Owner | Notes |
|---|---|---|---|
| 1 | **Tom approves ADR-0011 + ADR-0012** | Tom | Hard gate — nothing starts until both approved |
| 2 | Cognito pool: re-enable self-sign-up (email+password, email verification), rate-limit/Turnstile-guarded; implement/confirm the Post-Confirmation Lambda **3-path router** (packaging, IAM, VPC) | **DevOps** (Terraform) | Owns pool config + Lambda deploy; Python authors the handler logic (§F) — DevOps owns packaging/deploy/IAM/VPC. Must land before prod behavior. |
| 3 | MCP re-verify `tenant`, `tenant_signup`, `user`, `tenant_user_invite` | Python | Rule 3 gate |
| 4 | Alembic blank migration: **drop `tenant_name_key`** + add `tenant_signup.owner_email` (+names) nullable | Python | §B |
| 5 | Author the **Lambda handler 3-path router** (Python authors logic; DevOps packages/deploys) | Python + DevOps | §A.2 + §F |
| 6 | Remove the `_signup_impl` `Tenant.name` uniqueness pre-check (`auth.py`) + retire `test_auth.py` assertion (ADR-0012 + G6) | Python | Makes the dev/test stand-in match the real Lambda |
| 7 | `tenant_signup.py::initiate_signup()` → persist owner email/names; make step-1 **resolve-or-attach** to a Lambda-created tenant by email (idempotent, race-safe); overwrite placeholder `tenant.name` with real `business_name` | Python | Core logic change |
| 8 | Reconcile the two `signup` backends (G6): document + guard so `auth.py::_signup_impl` is the clearly-labeled dev/test Lambda stand-in; wizard uses `signup.py` only | Python | Naming/comment clarity + a guard test |
| 9 | Abandoned-signup cleanup helper: `tenant` JOIN `tenant_signup` WHERE `signup_state != 'complete'` AND `created_at < now() - interval 'N days'` | Python | §F — keyed on `signup_state`, **never** the name |
| 10 | Unit + integration tests (router 3 paths, resolve-or-attach idempotency, duplicate-email, race, placeholder-name insert with no unique constraint, dev/test stand-in still works) | Python | §G |
| 11 | Regenerate OpenAPI; close G1 + note G6 in onboarding doc; update mvp-arch §4.4; confirm ADR-0011/0012 in log | Python + Architect | Handoff + master-doc stewardship |
| 12 | *(separate)* `SIGNUP-GA-1-FE` — password field + Cognito `SignUp` (Amplify) on web `/sign-up` + mobile | React + RN | Out of scope of this design; own prompt after `pnpm sync-api-types` |

---

## D. New / Changed API Endpoints

**No brand-new REST resource.** Changes to the existing wizard step-1 path only:

### `POST /api/v1/signup` (existing — behavior change)
- **Auth**: step 1 remains **public** (no JWT — pre-login account birth). Steps 2–5 stay JWT-gated (`tenant.signup.complete`).
- **New behavior (resolve-or-attach)**: given owner email + business fields:
  1. If a `tenant` + owner `user` already exist for this email (created by the Post-Confirmation Lambda Path 3 after Cognito confirmation) → **attach** / return a `TenantSignup(step1_account)` for that tenant, persist business fields, and **overwrite the placeholder `tenant.name` with the real `business_name`**. Idempotent. **Do not create a second tenant.**
  2. If no tenant exists yet for the email (client called `/signup` before Cognito confirmation) → create a `TenantSignup` in a **pending-credential** posture keyed by `owner_email`, reconciled when the Lambda fires. (Recommended FE ordering: Cognito `SignUp` **first**, then `/signup` after confirmation, so case 1 is normal.)
- **Idempotency**: repeated calls with the same email must not create duplicate tenants/signups (natural key = owner email). Return the existing signup state (mirrors marketing-waitlist dedup).
- **Errors** (RFC 7807): `409` if the email maps to a tenant already past `step1_account` (resume, don't recreate) — reuse the existing `signup-state-conflict` shape; `422` invalid business fields.

> **No Cognito call from the backend** (Option B). The credential is created client-side via Cognito `SignUp` (Amplify) and confirmed by email code; the Post-Confirmation Lambda does the RDS write. The backend's job is **resolve-or-attach** idempotency + placeholder-name overwrite, not credential creation.

---

## E. Pattern Reuse Decisions (`mvp-arch.md §16`)

| Pattern | Applies? | How |
|---|---|---|
| 409-and-refresh staleness guard (ADR-0008) | ✅ | Reuse the `signup-state-conflict` 409 shape for "email already past step 1". |
| Natural-key idempotency (ADR-0006) | ✅ | Owner email is the natural key for resolve-or-attach; repeated `/signup` calls are idempotent (mirror waitlist dedup). The Lambda router is likewise idempotent — a re-fired confirmation for an existing `user` hits Path 1 (no-op). |
| Tenant-scoped `select()` (ADR-0005) | ✅ | All lookups by `email` / `tenant_id` via `select()`; no `db.get()`. |
| OpenAPI contract (ADR-0007) | ✅ | Regenerate after the endpoint behavior/schema change; `pnpm sync-api-types` for the FE follow-on. |
| Idempotency-Key header | ➖ | Step 1 is public/pre-login; natural-key (email) idempotency is the mechanism, not the header. |
| Post-Confirmation Lambda as the single account-birth path (mvp-arch §4.4) | ✅ | **Preserved** — the Lambda still owns tenant+user creation (now as a 3-path router); the wizard attaches, never forks a second creation path. |

---

## F. Shared Module Interfaces

### Post-Confirmation Lambda — 3-path router (Python authors logic; DevOps packages/deploys)

```python
def post_confirmation_handler(event, context):
    """
    Cognito Post-Confirmation trigger. Fires on EVERY confirmation → must ROUTE.
    email = event["request"]["userAttributes"]["email"]  (lowercased)

    Path 1 — existing/platform user (types i, ii, or a re-fire): a `user` row
             already exists for `email` → NO-OP (never create a tenant). Idempotent.
    Path 2 — pending-invite attach (type iv): a pending `tenant_user_invite`
             (accepted_at IS NULL, is_active, not expired) exists for `email` →
             create the `user`, attach `tenant_user` to invite.tenant_id with
             joined_at=now, set invite.accepted_at. Do NOT create a tenant.
    Path 3 — new-owner create (type iii, self-serve GA): no `user`, no pending
             invite → create `tenant` (placeholder name), owner `user`,
             `tenant_user(owner, joined_at=now)`, owner role/status.

    MUST NEVER raise to Cognito (an unhandled exception fails the confirmation and
    can strand the user). Catch/log all errors; the placeholder-name insert is
    now unconditional because tenant_name_key was dropped (ADR-0012).
    """
```

**Placeholder tenant name** (Path 3): `"{email_local_part}'s Company"` (e.g. `tom@pilotfortrades.com` → `"tom's Company"`), inserted **unconditionally** — no collision check, no UUID suffix, no unique-violation retry (ADR-0012 removed the constraint). The wizard step-1 (`initiate_signup`) overwrites it with the real `business_name`, so the placeholder is only ever visible in the abandoned-signup window.

### `backend/services/tenant_signup.py::initiate_signup()` (changed)

```python
def initiate_signup(
    db, business_name, trade, business_size, zip_code, time_zone,
    owner_email, owner_first_name, owner_last_name, request=None,
) -> dict:
    """
    SELF-SERVE (ADR-0011):
      1. Look up an existing owner `user` by email (created by the Lambda Path 3
         after Cognito SignUp confirmation) → its tenant.
      2. If found: attach/return a TenantSignup(step1_account) for that tenant,
         persist business fields + owner_email/names, and OVERWRITE tenant.name
         with the real business_name. Idempotent.
      3. If not found (client raced ahead of confirmation): create a
         pending-credential TenantSignup keyed by owner_email, reconciled when the
         Lambda fires.
    MUST NOT create a second tenant when the Lambda already made one for this email.
    Returns: { tenant_id, signup_state, owner_email, credential_pending: bool }
    """
```
- **Persist owner email/names** (previously dropped) → deterministic, pre-login-resumable resolution.
- **Overwrite `tenant.name`** with the real `business_name` (now safe — no unique constraint).
- **Race safety**: wrap resolve-or-attach in one transaction; on any concurrent-insert anomaly, re-select and attach rather than error.
- **No Celery / no new scheduled task.** **No backend boto3 Cognito call.**

### Abandoned-signup cleanup helper (new, `signup_state`-keyed — NOT name-keyed)

```sql
SELECT t.id, ts.owner_email, ts.signup_state, t.created_at
FROM public.tenant t
JOIN public.tenant_signup ts ON ts.tenant_id = t.id
WHERE ts.signup_state <> 'complete'
  AND t.created_at < now() - (:days || ' days')::interval;
```
- Deterministically identifies abandoned self-serve signups; the `"...'s Company"` name pattern is a **human hint only**, never the reaping key (a real contractor could legitimately be named "Dave's Company"). Reporting can surface `owner_email` for observability. Actual deletion is a separate, guarded operation (not auto-run in this batch).

### DevOps interface (cross-agent)
- Cognito pool: `AllowAdminCreateUserOnly = false` (re-enable self-sign-up), email verification required, password policy retained (min 12, upper/lower/number/symbol). Terraform in the Cognito module. Deploy/package the Post-Confirmation Lambda **3-path router** (Python authors the handler; DevOps owns packaging, IAM role, VPC config). Update `aws-infrastructure-as-built.md` + `aws-cognito-prod-setup.md`. **Owned by DevOps; this design specifies the requirement, not the Terraform.**

---

## G. Open Questions Resolved

| Q | Resolution |
|---|---|
| Backend `AdminCreateUser` vs Cognito self-sign-up? | **Self-sign-up (Option B, ADR-0011)** — reuses the Lambda, keeps Cognito admin IAM out of the backend, password never touches our servers. |
| Does the Lambda create a tenant on every confirmation? | **No** — it is a **3-path router** (§A.2). Only type-(iii) new-owner (Path 3) creates a tenant. Types (i)/(ii) → Path 1 no-op; type (iv) → Path 2 attach. |
| Does the wizard still "create the tenant"? | **No** — in self-serve the Lambda (Path 3) creates tenant+user; the wizard **resolves-or-attaches** by email and overwrites the placeholder name. Beta concierge already behaves this way. |
| How does Cognito link to the app user with no `cognito_sub`? | **Email match** — the only existing join (MCP-confirmed no `cognito_sub`). Adding `cognito_sub` is a separate, larger decision, explicitly not taken here. |
| How is the placeholder tenant name made safe? | **ADR-0012 drops `tenant_name_key`** → the friendly `"{local-part}'s Company"` is inserted **unconditionally**; no collision-proofing needed. This also removes the only exception path that could strand a Cognito confirmation. |
| How is an abandoned signup found for cleanup? | By **`tenant_signup.signup_state != 'complete'`** past an age threshold — deterministic. The name pattern is a human hint only, never the reaping key. |
| Is a schema change required? | **Yes** — one blank migration: **drop `tenant_name_key`** (ADR-0012) + add nullable `tenant_signup.owner_email`/names (Tom-approved). |
| Does this touch MFA? | **No** — MFA is MFA-WIRE-1 (G4), separate. Standard Cognito first-login/MFA challenge applies. |
| Does this fix founders billing G3 (`stripe_customer_id`)? | **No** — out of scope; tracked separately. |
| The two `signup` endpoints (G6)? | Clarify in code + docs: `auth.py::_signup_impl` = **dev/test stand-in for the prod Lambda router**; `signup.py` = wizard state machine. Remove its `tenant.name` uniqueness pre-check (ADR-0012) so it matches the real Lambda. Add a guard test so they don't drift. |
| Types (i)/(ii)/(iv) scope? | Router **built now** (all 3 paths); their **UIs are follow-on batches** (§H). |
| Is this Beta-blocking? | **No** — Beta stays concierge. Pre-GA; sequenced next after UP-1 so Tom can test the full self-serve chain. |
| Cost impact? | **$0** — Cognito already the auth authority; self-sign-up within the free MAU tier at 100 users. No baseline delta, no founder cost review. |

---

## H. Cross-Agent Handoff, Dependencies & Scope Split

**This batch (SIGNUP-GA-1):**
1. **Tom** approves ADR-0011 **and** ADR-0012 — hard gate.
2. **DevOps** lands the Cognito pool self-sign-up re-enable (Terraform) + packages/deploys the Post-Confirmation Lambda 3-path router; updates `aws-infrastructure-as-built.md` + `aws-cognito-prod-setup.md` (Architect verifies — §12.1 stewardship).
3. **Python Engineer** authors the Lambda router logic + the migration (drop constraint + `owner_email`) + `initiate_signup()` resolve-or-attach + G6 reconciliation + cleanup helper; regenerates OpenAPI.
4. **React + RN** (`SIGNUP-GA-1-FE`, separate prompt) add the password field + Cognito `SignUp` (Amplify) to web `/sign-up` and mobile — after `pnpm sync-api-types`.
5. **Architect** closes Gap **G1** (+ notes G6) in `pilot-founder-onboarding-process.md`, updates `mvp-arch.md §4.4`, and confirms ADR-0011/0012 on batch close (§12 stewardship).

**Follow-on batches (out of scope here — router already protects them):**

| Follow-on | Adds | Lambda path already handling it |
|---|---|---|
| **`SIGNUP-GA-1-FE`** | Password field + Amplify `SignUp` on web + mobile signup screens | (feeds Path 3) |
| **`TEAM-INVITE-1`** (type iv) | Tenant-owner "invite employee" UI + `tenant_user_invite` write endpoint + invite-landing SignUp screen | **Path 2** (pending-invite attach) |
| **`PLATFORM-ADMIN-1`** (types i/ii) | Platform-admin UI → `AdminCreateUser` + `user(is_platform_user=true)` write | **Path 1** (no-op — row created by admin flow) |

---

## I. Definition of Done (design-level)

- ADR-0011 **and** ADR-0012 approved by Tom and marked **Accepted** in `pilot-adr-log.md` (Decision Index + entries).
- DevOps Cognito self-sign-up change + Lambda 3-path router landed; `aws-infrastructure-as-built.md` + `aws-cognito-prod-setup.md` updated (Architect-verified).
- Migration drops `tenant_name_key` and adds nullable `tenant_signup.owner_email`/names.
- Lambda routes all 3 paths correctly and **never raises to Cognito**; Path 3 inserts the placeholder name unconditionally.
- `initiate_signup()` is resolve-or-attach + idempotent + race-safe; overwrites the placeholder `tenant.name`; **never** creates a duplicate tenant for an email the Lambda already provisioned; owner email/names persisted.
- G6 reconciled: `_signup_impl` name pre-check removed (+ `test_auth.py` retired); dev/test stand-in still works and now mirrors the real Lambda; guard test added.
- OpenAPI regenerated; onboarding doc G1 closed (G6 noted); `mvp-arch.md §4.4` reflects the self-serve 3-path router + the `cognito_sub` correction + name-uniqueness note.
- Full end-to-end **self-serve** onboarding testable in a non-prod env: Cognito `SignUp` → email confirm → Lambda Path 3 creates tenant+user → `/signup` attaches wizard + overwrites name → login → wizard steps 2–5 → dashboard.

---

*Authored by Pilot Architect. Python Engineer prompt (`batch-signup-ga-1-python-engr-prompt.md`) + DevOps prompt (`batch-signup-ga-1-devops-prompt.md`) to follow using the standard inclusion files **after Tom approves ADR-0011 + ADR-0012**. The FE (`SIGNUP-GA-1-FE`), `TEAM-INVITE-1`, and `PLATFORM-ADMIN-1` are separate batches. Beta remains concierge; this batch un-blocks self-serve GA and lets Tom test the full onboarding chain.*
