# TEAM-INVITE-1 — Batch Design: Tenant-Owner "Invite Employee" + Invite-Landing SignUp

**Batch code**: TEAM-INVITE-1 (Launch plan Ord 8, card §3.8, §7 founder-gate row)
**Version**: 1.0 · **Date**: 2026-09-03 · **Author**: Pilot Architect
**Status**: APPROVED (Tom, 2026-09-03) — Python + React prompts both authored; designer gate waived by Tom (§G.12)
**Batch shape**: Mixed (§1.3) — **Part A (Python, runs first)** → **Part B (React, gated on Part A OpenAPI regen + designer spec)**
**Estimate**: Part A ~3–4 h · Part B ~4–5 h
**Depends on**: SIGNUP-GA-1 ✅ (Lambda Path 2 — pending-invite attach — already built; ADR-0011)
**Prompts**: `batch-team-invite-1-python-engr-prompt.md` (Part A) · `batch-team-invite-1-react-engr-prompt.md` (Part B — after designer spec)
**Designer spec**: **waived by Tom 2026-09-03** (§G.12) — §H/§I of this doc is the Part B surface spec

---

## Why this batch (founder-gate framing)

Every founder with employees must invite them before launch (§7 gate: "founders can invite up to ~5 employees"). Today the only path is the **"coming soon" placeholder dialog** in `TeamSettingsPage.tsx` — a literal user-visible "coming soon" string, a **P0 gap per Rule 9.4**. The backend attach half (Lambda Path 2) already exists and is battle-tested; this batch builds the missing 80%: invite creation/email, token lifecycle, the landing page, and role-at-invite.

---

## A. Input Read Summary

| Input | What it yielded |
|---|---|
| Launch plan `pilot-launch-plan.md` §3.8 card + §7 gate + PLAT-DEBT RBAC row | Scope, design requirements (no seat limits, `increment_user_count()` on acceptance, ADR-0010 invite-exposed subset, designer gate Rule 1.5, seed rollout Rule 11.5) |
| `mvp-prd.md` (invite search) | PRD is thin here — only the setup-checklist "invite team" item (line 358). Requirements authority = card §3.8 + ADR-0011 |
| `mvp-arch.md` §1035–1037 (3-path router) + §1227–1235 (checklist) | Path 2 contract (email-keyed attach); `team_invited` checklist column + auto-completion requirement |
| `pilot-adr-log.md` ADR-0010, ADR-0011, ADR-0012 | RBAC vocabulary reconciliation direction (FE `tech`→`technician`, `operator`→`accountant` read-only **set replacement**); Cognito self-`SignUp` is the ratified path (AdminCreateUser rejected — security surface); Lambda must never raise to Cognito |
| MCP `postgres-local` — `tenant_user_invite` columns (12) | id, tenant_id, email (citext), token_hash, expires_at, accepted_at, invited_by, is_active + 4 audit cols. **No `role_code` column** — confirmed gap |
| MCP — constraints on `tenant_user_invite` / `tenant_user` / `tenant_user_role` | `uq_tenant_user_invite_tenant_id_email` (natural key for idempotency); `tenant_user_role` PK = `code` (valid FK target); `tenant_user.role_code → tenant_user_role(code)` = the exact FK pattern to mirror; audit trigger `audit_tenant_user_invite_changes` exists |
| MCP — `tenant_user_role` rows (4) | owner (`*` + users.manage), technician, office_staff, accountant permission JSONB — invite-exposed role set = all 4 |
| `backend/lambda/post_confirmation/handler.py` (full) | Path 2 hardcodes role `"technician"` with an **explicit TEAM-INVITE-1 comment** (lines 248–250); `_find_pending_invite` conditions (accepted_at NULL, is_active, not expired, latest first); never-raise invariant; attach creates `user` + `user_endpoint` + `tenant_user(active)` + sets `accepted_at` |
| `backend/api/routes/roles.py` (full) | `GET /users` (users.view), `POST /users/{user_id}/role` (users.manage) with last-owner guard, `/test` twin pattern (registered BEFORE authenticated), `_impl()` shared-function house pattern |
| `backend/services/tier_limit_enforcer.py` | `check_user_add_allowed()` always `(True, {})` (MKT-B11 invariant — call for forward-compat, never reintroduce limit UX); `increment_user_count()` body (current-period `tenant_subscription_usage`, monthly-aligned row creation) |
| `backend/services/email_template_renderer.py` | `render_and_send(db, template_id, context, to_address, tenant_id=None)` — resolves `EmailTemplate` by string PK, branding for `customer_facing` only, dispatches via SendGrid `send_email`. The invite-email pipeline |
| `backend/services/onboarding_service.py` | `mark_team_invited(db, tenant_id)` exists with **zero callers** — wire at invite-send (same caller-less class as PLP-FIX-6's `mark_first_customer`) |
| `backend/migrations/scripts/data/email_templates/welcome.json` + `email_template` MCP columns | JSON file shape (template_id/display_name/category/subject/bodies/variables[]); category `"internal"` = Pilot standard branding; seed_core owns `email_template` (ADR-0016) |
| `frontend/apps/web/src/features/settings/components/TeamSettingsPage.tsx` | Existing `/settings/team` surface: user list + role reassign (works); **"coming soon" InviteDialog (P0, Rule 9.4)**; `ROLE_OPTIONS` already in BE vocabulary |
| `frontend/packages/ui/src/auth/types.ts` + `role-gate/permissions.ts` + AuthProvider + help-anchor/types.ts | FE registry `PilotRole = "owner" \| "tech" \| "office_staff" \| "operator"` — the ADR-0010 divergence; `help-anchor/types.ts` duplicates the union |
| `frontend/apps/web/src/app` router + `features/users/` | `/settings/team` exists under `(authed)/settings/`; public-route precedent `i/[token]`, `q/[token]`; new public route `invite/[token]` fits the same pattern; `features/users/` has only `useTenantUsers` |
| `backend/README-seed-data.md` §4, §7 | `email_template` = 16 rows (→17); audit-mixin 4-column DDL rule; seed-rollout template (§20 inclusions) |
| `pilot-architect-methods.md` §3, §3.9 | Required sections A–I; designer-mode coordination workflow |

---

## Part A — Backend (Python Engineer)

## B. Migration Plan

### B.1 Pre-Migration Verification (MCP, 2026-09-03 — completed at design time)

| Check | Result |
|---|---|
| `tenant_user_invite` columns | 12 columns; **no `role_code`** — gap confirmed |
| `uq_tenant_user_invite_tenant_id_email` | Exists (tenant_id, email) — natural idempotency key |
| `tenant_user_role` PK | `code` — valid FK target |
| FK pattern to mirror | `tenant_user_role_code_fkey` on `tenant_user.role_code → tenant_user_role(code)` |
| Audit trigger | `audit_tenant_user_invite_changes` exists — no new trigger work |
| `email_template` row count | 16 (→ 17 with `team_invite`) |

**Prompt-authoring gate**: the Python prompt must re-run `SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('tenant_user_invite','tenant_user_role')` via `postgres-local` before writing any SQL, per Rule §3.

### B.2 Migration 1 — `tenant_user_invite.role_code` (nullable add; 3-part pattern NOT required)

| Table | Column | Type | Nullable | Default | FK |
|---|---|---|---|---|---|
| `tenant_user_invite` | `role_code` | `VARCHAR` | **YES** | NULL | `fk_tenant_user_invite_role_code → tenant_user_role(code)` |

```sql
ALTER TABLE public.tenant_user_invite ADD COLUMN role_code VARCHAR NULL;
ALTER TABLE public.tenant_user_invite
  ADD CONSTRAINT fk_tenant_user_invite_role_code
  FOREIGN KEY (role_code) REFERENCES public.tenant_user_role(code);
```

- **Nullable, no backfill, no NOT NULL lock** — pre-existing rows (none in prod; test rows in dev) simply mean "role unspecified → technician fallback" (§F Lambda contract).
- No new table → no `audit_log`/`immutable_guard`/`updated_at_sync` trigger work (audit trigger already present).
- Model: add `role_code: str | None` to `TenantUserInvite` with FK.
- Down migration drops constraint + column.

### B.3 Seed Data Rollout (Rule 11.5 — mandatory)

**Layer 1 — Core/Platform (`seed_core.py`, Group A)**:

1. New file `backend/migrations/scripts/data/email_templates/team_invite.json` — `template_id="team_invite"`, `category="internal"` (Pilot standard branding; NOT `customer_facing` — no tenant branding lookup), variables: `invitee_email, tenant_name, role_name, invite_url, expires_date`.
2. `seed_core.py` email_template section picks it up via the existing JSON-file loop (engineer verifies — the loader walks `data/email_templates/*.json`); idempotent `ON CONFLICT DO NOTHING`.
3. Copy requirements: subject "You've been invited to join {{tenant_name}} on Pilot for Trades"; body names the inviter's company, the role (`{{role_name}}`), a single CTA button/link `{{invite_url}}`, expiry line (`{{expires_date}}`), and a plain-text fallback URL. No marketing chrome; transactional tone. HTML + plain in the JSON per the welcome.json shape.
4. README §4 update: `email_template` 16 → **17** + row note (TEAM-INVITE-1).

**Layer 2 — Scenario/dev data (`seed_test_tenant.py`, Group C)**:

5. One **pending** `tenant_user_invite` row for the test tenant so the FE pending-list develops against real data: `email='newguy@pilot.local'`, `role_code='technician'`, `expires_at = NOW() + interval '7 days'`, `invited_by = owner (...0002)`, `token_hash = sha256('dev-invite-token-0001')` (compute at seed time via hashlib — never store the raw token; document raw token in the script comment for FE landing-page dev: `dev-invite-token-0001`). Value-scoped DELETE+INSERT idempotency per Rule 11.1 (match `(tenant_id, email)` — the unique constraint also makes `ON CONFLICT DO NOTHING` viable here; engineer's choice, cite Rule 11.1 either way).

**Verification**: `seed_core.py --mode inspect` shows `email_template=17`; `pytest -m unit` green; README §4 updated in the same PR.

**Prod converge**: after deploy, Tom re-runs `seed_prod_db.py --mode seed --stripe-mode test` (email_template is Group A — today's 2026-09-03 converge makes this the first exercise of the cadence rule).

### B.4 Lambda packaging/deploy note

The Path 2 handler change (§F.3) ships in the same repo but deploys via `infrastructure/scripts/build-post-confirmation-lambda.sh` + the Lambda deploy runbook — **Tom/DevOps step after Part A merges**, called out in the prompt's handoff section. The API deploy and the Lambda deploy are independent (the Lambda change is backward-compatible: NULL `role_code` → technician fallback, so old invites + new invites both work under either code version).

---

## C. Execution Order (Part A)

| # | Step | Depends on |
|---|---|---|
| 1 | Regression baseline `pytest -m unit --tb=no -q \| tail -5` + MCP verification queries (§B.1 gate) | — |
| 2 | Migration: `role_code` column + FK (§B.2) | 1 |
| 3 | Model update `TenantUserInvite.role_code` | 2 |
| 4 | Seed rollout: `team_invite.json` + seed_core + README §4 + test-tenant pending invite (§B.3) | 2 |
| 5 | Schemas `api/schemas/team_invites.py` (request/response) | 3 |
| 6 | Service `services/team_invite_service.py` (§F.1) | 3, 4 |
| 7 | Routes `api/routes/team_invites.py` — 4 authenticated + 1 public + `/test` twins (§D) | 5, 6 |
| 8 | Router registration in the app + `openapi.json` regen (`python export_openapi_json.py`) | 7 |
| 9 | Lambda Path 2 update + tests (§F.3) | 2 |
| 10 | Unit tests (§D per-endpoint + service + Lambda) — domain folder per inclusions | 7, 9 |
| 11 | Two-phase verification gate; handoff (OpenAPI commit → notify React Engineer **after designer spec approval**) | 10 |

---

## D. New API Endpoints (Part A)

All authenticated endpoints: tenant-scoped `select()` with explicit `WHERE tenant_id = :tid` (`db.get()` banned); `Idempotency-Key` header required on every POST (24h TTL store; natural-key fallback = `uq_tenant_user_invite_tenant_id_email` → 409 mapping); `/test` twins registered **before** the authenticated twins (house pattern from `roles.py`).

| # | Method & Path | Auth | RBAC | Purpose |
|---|---|---|---|---|
| D1 | `POST /api/v1/users/invites` | JWT | `users.manage` | Create + send invite |
| D2 | `GET /api/v1/users/invites` | JWT | `users.view` | List tenant invites (all states) |
| D3 | `POST /api/v1/users/invites/{invite_id}/resend` | JWT | `users.manage` | New token + expiry + resend |
| D4 | `POST /api/v1/users/invites/{invite_id}/revoke` | JWT | `users.manage` | Deactivate (`is_active=false`) |
| D5 | `GET /api/v1/invites/{token}` | **Public** | — | Validate token for landing page |

### D1 — `POST /api/v1/users/invites`

**Request**: `{ "email": "newguy@example.com", "role_code": "technician" }`
**Rules**:
1. Pydantic `EmailStr` (422 on format) — DB CHECK is the backstop, never the validator.
2. `role_code` must be an active `tenant_user_role` row → 400 `invalid_role` (RFC 7807).
3. `check_user_add_allowed(db, tenant_id)` — call for forward-compat (always true; MKT-B11 invariant, §G.4).
4. If a `user` row exists for the email → **409 `invite_user_exists`** ("this person already has a Pilot account"; multi-tenant membership is out of scope, §G.5).
5. If a pending (accepted_at NULL, is_active, not expired) invite exists for `(tenant_id, email)` → **409 `invite_pending_exists`** with the existing invite id in the detail (FE offers resend).
6. Else: generate token (§F.2), insert row (`role_code`, `invited_by=current_user`, 7-day expiry), send email (§F.4), `mark_team_invited(db, tenant_id)` (non-fatal wrapper — the invite must not fail if the checklist write fails), commit.

**Response 201**: `{ "id", "email", "role_code", "expires_at", "created_at" }` — **never** the raw token.
**Errors**: 400 `invalid_role` · 409 `invite_user_exists` / `invite_pending_exists` · 422 validation.

### D2 — `GET /api/v1/users/invites`

**Response 200**: `[{ "id", "email", "role_code", "invited_by", "created_at", "expires_at", "accepted_at", "is_active", "status" }]` where `status` is computed: `accepted` (accepted_at set) → `revoked` (not is_active) → `expired` (expires_at ≤ now) → `pending`. Ordered `created_at DESC`. No pagination (≤ dozens per tenant).

### D3 — `POST /api/v1/users/invites/{invite_id}/resend`

404 `invite_not_found` (tenant-scoped) · 409 `invite_already_accepted` / `invite_revoked`. Rotates token (new raw + hash), resets `expires_at = now + 7d`, resends email. Response 200: `{ "id", "email", "expires_at" }`.

### D4 — `POST /api/v1/users/invites/{invite_id}/revoke`

404 `invite_not_found` · 409 `invite_already_accepted`. Sets `is_active=false`. Response 200: `{ "id", "is_active": false }`.

### D5 — `GET /api/v1/invites/{token}` (public)

- **No auth**, but **uniform 404** for every failure mode (unknown token, expired, accepted, revoked) — no enumeration oracle; one RFC 7807 body `invite_invalid`.
- SlowAPI per-IP limit mirroring the public-route precedent (verify against `public_quotes.py`); 10/min is plenty for a human clicking an email link.
- Success 200: `{ "tenant_name", "email", "role_code", "expires_at" }` — the landing page's only data. Token lookup by `sha256(token)` = `token_hash` via the existing `ix_tenant_user_invite_token_hash` index.
- Invite URL construction (for the email): reuse the existing public-link base-URL config used by quote/invoice public links (engineer verifies the config key against `public_link_signer.py` / public link routes) — `/invite/{raw_token}` on the web app origin.

---

## E. Pattern Reuse Decisions (Part A)

| §16 Pattern | Applied? | How / why |
|---|---|---|
| Idempotency-Key (mandatory POST) | ✅ | D1/D3/D4 — 24h TTL store + `uq_tenant_user_invite_tenant_id_email` natural-key fallback → 409 |
| 409-and-refresh | ✅ | `invite_pending_exists`/`invite_user_exists` carry structured codes so the FE can invalidate `team-invites` + `tenant-users` queries |
| System-default/tenant-override | ✅ (platform level) | `team_invite` email template is platform-owned (`category="internal"`); no tenant override this batch |
| Audit discipline | ✅ | Existing audit trigger + `created_by=invited_by`; Lambda attach sets `accepted_at` (actor NULL, system-initiated — SIGNUP-GA-1 accepted posture) |
| Always-preview-before-send | ❌ (justified) | Governs **customer-facing** comms. A single-recipient transactional invite with fixed copy has nothing to preview; the dialog shows the exact recipient + role before send instead |
| Optimistic UI / track-changes / confirm-as-turn / four-class severity / mobile escalation / in-flight sync / bilateral conflict | N/A | Web settings surface + public landing; no offline, no voice, no sync conflicts |

---

## F. Shared Module Interfaces (Part A)

### F.1 New service — `backend/services/team_invite_service.py`

```python
def create_invite(db, *, tenant_id: UUID, email: str, role_code: str,
                  invited_by: UUID) -> tuple[TenantUserInvite, str]      # (row, raw_token)
def resend_invite(db, *, tenant_id: UUID, invite_id: UUID) -> tuple[TenantUserInvite, str]
def revoke_invite(db, *, tenant_id: UUID, invite_id: UUID) -> TenantUserInvite
def list_invites(db, *, tenant_id: UUID) -> list[TenantUserInvite]
def validate_invite_token(db, *, raw_token: str) -> TenantUserInvite | None  # D5; None = uniform 404
```

All tenant-scoped; business-rule errors raised as the service's typed exceptions mapped by the route to the §D RFC 7807 codes (mirror the quote_service error-mapping pattern).

### F.2 Token helper

```python
def _generate_invite_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)          # 256-bit
    return raw, hashlib.sha256(raw.encode()).hexdigest()
```

Raw token appears exactly twice: the email URL, the API response of nothing. DB stores only the hash.

### F.3 Lambda Path 2 change — `handler.py`

```python
role_code = invite.role_code if invite.role_code else "technician"   # NULL fallback = pre-TEAM-INVITE-1 rows
role = _get_or_create_role(db, role_code)
```

Plus **best-effort usage reporting** (§G.7): after the attach `db.commit()` succeeds, a **second, separately-wrapped** transaction mirrors `increment_user_count()` inline (current-period `tenant_subscription_usage`; monthly-aligned create-if-missing). Any failure there is logged and swallowed — an analytics row must never jeopardize account birth (ADR-0011 never-raise invariant). The Lambda stays model-only (no services import — packaging constraint); the inline mirror carries a comment pointing at the canonical function.

### F.4 Email send

`render_and_send(db, "team_invite", context={"invitee_email", "tenant_name", "role_name", "invite_url", "expires_date"}, to_address=email)` — category `internal` ⇒ `tenant_id=None` (Pilot standard branding). Role display name resolved from `tenant_user_role.name` (e.g. "Field Technician").

### F.5 Celery

None. No beat schedule changes.

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| G.1 | Role at invite time vs post-acceptance edit? | **At invite time** — new nullable `tenant_user_invite.role_code` (§B.2). The Lambda comment (handler.py–250) explicitly anticipates this batch. The card's "no new schema expected" yields to evidence: the table lacks any role carrier, and post-acceptance-only would force every founder through a second edit step. Nullable add keeps old rows + old Lambda both valid (technician fallback) |
| G.2 | Cognito `AdminCreateUser` or self-serve `SignUp`? | **Self-serve `SignUp`** — ADR-0011 Option B is ratified (backend never takes Cognito admin IAM, never handles passwords). The COGNITO-EMAIL-1 card's "*AdminCreateUser* invites (TEAM-INVITE-1)" phrasing is a stale assumption: the invite email is app-sent via SendGrid (`render_and_send`, already branded); Cognito only sends its own verification email for the SignUp — which COGNITO-EMAIL-1 still covers. **Flag for Tom**: COGNITO-EMAIL-1 scope note needs a one-line amendment at design time |
| G.3 | Invite expiry window? | **7 days** from creation; resend refreshes the window. Lambda already enforces `expires_at > now()` |
| G.4 | Seat-limit enforcement? | **None — permanent invariant** (MKT-B11; `check_user_add_allowed()` always `(True, {})`). Called for forward-compat only; no limit UX anywhere |
| G.5 | Invite email belongs to an existing `user`? | **409 `invite_user_exists`** — multi-tenant membership is deferred (SD-DEFER `user_endpoint` scoping question). Clean failure beats silent Path-1 no-op confusion |
| G.6 | Which roles are invite-exposed? | **All four** (owner, technician, office_staff, accountant) — co-owner invites are a real 2-person-shop case; the last-owner guard lives in assign-role, not invite. Consequence: the invite UI exposes `accountant`, so the **ADR-0010 FE `operator`→`accountant` permission-set replacement IS triggered** (card condition met) — Part B scope (§I.5) |
| G.7 | Where does `increment_user_count()` fire? | **Lambda, post-commit, best-effort** (§F.3) — acceptance happens only there; an app-side signal doesn't exist. Separate transaction so analytics can never rollback the attach |
| G.8 | Email template category? | `"internal"` (Pilot branding) — the invite is Pilot→invitee, not tenant→customer; no tenant branding lookup |
| G.9 | Public endpoint abuse? | Uniform 404 for all failure modes + SlowAPI per-IP limit + hash-indexed lookup. Token = UX gate + display context; **Cognito email verification is the security boundary** (attach is email-keyed per ADR-0011 — a stolen link alone grants nothing without inbox control) |
| G.10 | New `users.invite` permission? | **No** — reuse `users.manage` (owner-only today). FE registry gains a `users.manage` PermissionKey (owner set only) so the invite button and BE RBAC align (§I.5) |
| G.11 | `tenant_user` pre-creation with `invited` status? | **No** — the invite row tracks lifecycle; `tenant_user` is born `active` at attach (existing Lambda behavior). The `invited`/`pending` statuses remain for future use; introducing a second state carrier would split the source of truth |
| G.12 | Designer-spec gate for Part B? | **Waived by Tom, 2026-09-03** — same posture as PLP-FIX-5 (§G.8 there): the surfaces compose existing patterns (settings dialog + badge/table reuse on `/settings/team`; a single-state public landing) and §H/§I here carry the full state/component contract. No `pilot-web-ui-designer` spec will be produced; the React prompt references §H/§I directly as the surface spec. Recorded per Rule 1.5's Tom-gate (the gate is his to waive) |

---

## Part B — Frontend (React Engineer — gated on designer spec + Part A OpenAPI regen)

## H. Surface Mockup Reference

**Designer spec**: **waived by Tom 2026-09-03 (§G.12)** — this §H + §I serve as the Part B surface spec, referenced directly by the React prompt. Platform scope: **web only** (mobile team-management is a future batch; invite acceptance happens via email link → web landing even for mobile-first techs).

**Designer commission brief (what the spec must cover)**:

| Surface | Route | States to spec |
|---|---|---|
| 1. Invite dialog (replaces the P0 "coming soon" `InviteDialog`) | `/settings/team` | Form (email + role select, all 4 roles with plain-language descriptions), send-in-flight, success (copied-to-list confirmation), 409 `invite_pending_exists` (offer resend), 409 `invite_user_exists` explainer, 422 inline email error |
| 2. Pending invites section | `/settings/team` (below members list) | Rows: email, role badge, sent date, expiry countdown, `pending`/`expired` status chip, **Resend** + **Revoke** actions with confirm; accepted invites collapse into the members list (source: D2 + D1 reuse of `useTenantUsers`) |
| 3. Invite landing | `/invite/[token]` (new public route, sibling to `q/[token]`/`i/[token]`) | Valid: "Join {tenant_name}" + email + role name + expiry + SignUp CTA (email prefilled, Cognito `SignUp` → verification → login → lands in tenant). Invalid/expired/accepted: single neutral "this link is no longer valid" state (mirrors D5's uniform 404) + contact-the-owner guidance |

**Locked-pattern composition check (Architect verifies before referencing the spec)**: composes §16 patterns (optimistic UI on invite mutations; 409-and-refresh on duplicate) — no new top-level UX; **token-only** (`pilotPreset`, zero hex); **Accessibility Notes subsection** (WCAG 2.2 AA: ≥24×24 targets, focus-visible rings, status not color-only, reduced-motion); **component-existence check** against `frontend/packages/ui/src/index.ts` (RoleBadge-like badge, dialog primitives, form inputs likely already exist — no orphans with §I).

## I. Component Manifest (Part B)

| # | Component / module | Destination | Establish vs flesh |
|---|---|---|---|
| I.1 | `InviteMemberDialog` (replaces placeholder `InviteDialog`) | `apps/web/src/features/settings/components/` | Replace (P0 "coming soon" removal — Rule 9.4) |
| I.2 | `PendingInvitesSection` (+ row actions) | `apps/web/src/features/settings/components/` | New |
| I.3 | Invite landing page + valid/invalid states | `apps/web/src/app/invite/[token]/page.tsx` + `features/users/components/InviteLanding*.tsx` | New public route |
| I.4 | Hooks: `useTeamInvites`, `useCreateInvite`, `useResendInvite`, `useRevokeInvite` (apiClient, TanStack `retry:false`, MSW handlers + barrel registration) | `apps/web/src/features/settings/hooks/` (or `features/users/hooks/` — designer/React reconcile with `useTeamUsers` location) | New |
| I.5 | **RBAC vocabulary reconciliation (ADR-0010 invite-exposed subset)**: `PilotRole` `"tech"`→`"technician"`, `"operator"`→`"accountant"` in `auth/types.ts`; `ROLE_PERMISSION_MAP` keys + **accountant set replaced with the BE read-only set** (`*.view` family + reports — **not** a string swap of the manager set); new `users.manage` key (owner only); AuthProvider `role_code` mapping becomes identity; `help-anchor/types.ts` union updated; **census-first task**: grep `"tech"`/`"operator"` literals across `apps/web`, `apps/mobile`, `packages/ui` — if mobile blast radius exceeds the ~2 h cap, fall back to boundary-mapping at AuthProvider and defer the full rename to PLAT-DEBT (record the call in the completion summary) | `packages/ui/` | Modify |
| I.6 | Landing-page fetch: public invite lookup | reuse the public-route fetch pattern from `features/public-quote`/`public-invoice` (no auth context) | New |

**§16 pattern consumption**: optimistic UI (invite mutations), 409-and-refresh (duplicate/existing-user), Idempotency-Key on all mutations (via apiClient), hide-not-disable RoleGate gating of the invite button (`users.manage`).

---

## Deploy & sequencing notes

1. **Part A deploys first** (migration + endpoints + seed). Migration is additive/nullable — zero downtime; blue-green per `aws-ops-runbook.md` §19.6.
2. **Lambda redeploy** (§B.4) can ship with Part A or after — both code versions are mutually compatible.
3. **Prod seed converge** after Part A deploy (email_template Group A) — Tom, per §B.3.
4. **Part B** ships after the designer spec is Tom-approved + `pnpm sync-api-types` confirms the D1–D5 contracts.
5. **§7 gate row flips** when Part B closes + Tom's end-to-end smoke passes: owner invites a real email → invite email lands → SignUp → verification → attach → login → correct role.
6. **E2E tail** (not this batch): E2E-WEB-1 absorbs the founder-invite journey into Playwright.

## Explicitly out of scope

- Multi-tenant membership (one `user` → many tenants) — SD-DEFER
- Mobile team-management surfaces
- Cognito `AdminCreateUser` flow (ADR-0011 rejected path)
- Invite acceptance for **platform** roles (PLATFORM-ADMIN-1)
- Full RBAC matrix expansion (PLAT-DEBT; only the invite-exposed rename subset lands here)
- `tenant_user` suspension/removal UI (exists? — separate audit; not this batch)
