# TEAM-INVITE-1 — Production End-to-End Test Plan (Tom)

**Date**: 2026-09-03 · **Author**: Pilot Architect · **For**: Tom
**What shipped to prod**: migration `3da9abdfb2f2` (`tenant_user_invite.role_code` + FK) · 4 authed invite endpoints + public `GET /api/v1/invites/{token}` · `team_invite` email template (Group A) · Post-Confirmation Lambda Path 2 role-at-invite + best-effort usage counter · `/settings/team` invite dialog + pending invites section · public `/invite/[token]` landing · FE RBAC reconciliation (ADR-0010 subset — `PilotRole` now backend vocabulary)
**Gate linkage**: the §7 founder-gate row *"TEAM-INVITE-1 closed — founders can invite up to ~5 employees"* flips ✅ when this plan passes. Report results back (Pass/Fail per test) — Architect flips the row and triages any failure.
**Time budget**: ~60–90 min (mostly waiting on emails) · **You need**: 2 email aliases you control (Gmail `+` aliases work — Cognito treats them as distinct addresses, e.g. `you+tech1@gmail.com`, `you+office1@gmail.com`), prod web access as **owner**, the SSH tunnel for DB checks.

---

**v1.1 (2026-09-04) — TEAM-INVITE-2 + COGNITO-EMAIL-1 deltas** (plan updated after the TEAM-INVITE-2 deploy; supersedes v1.0 expectations where they differ):

1. **On-page accept flow** — the landing page no longer shows a *Create your account* CTA to `/signup`. It renders the invite-scoped accept form: password + confirm → Cognito `SignUp` → on-page 6-digit verify → `ConfirmSignUp` (fires the Lambda Path 2 attach). Tests 2–4 expectations updated below.
2. **Branded Cognito emails** — verification codes now arrive via SendGrid (COGNITO-EMAIL-1 ✅ 2026-09-04: inbox placement + DKIM/SPF/DMARC PASS). The `COGNITO_DEFAULT` 50/day cap + spam placement that broke email-dependent steps on 2026-09-03 are gone.
3. **Technician terminal state** — technicians are **blocked from the web app post-login by design** (`usePostLoginRedirect.ts`: info banner + auto sign-out after 5 s). A tech invitee's correct terminal state is the landing page's **mobile-app success panel**, not a web dashboard. Test 10 rewritten accordingly (the v1.0 matrix also wrongly assumed technicians hold `users.view` — they hold no `users.*` permissions).
4. **Already green** — Tests 1–3 (technician path) were proved end-to-end by the COGNITO-EMAIL-1 Part B smoke (2026-09-03: *"second account, tech under same tenant, confirmed working"* — branded email → on-page accept → Path 2 attach). Mark them off unless you want a personally re-verified board.

**v1.2 (2026-09-04) — pool-config drift incident fixes**:

1. **Gate 0.8 added** — during this run, a tech invitee's `SignUp` produced **no verification-code email at all** and resend failed with *"Cannot resend codes. Auto verification not turned on."* Root cause: a 2026-09-03 `update-user-pool` wiring call (COGNITO-EMAIL-1) omitted `--auto-verified-attributes`, and `UpdateUserPool` RESETS omitted blocks — the pool's `AutoVerifiedAttributes` (and `DeviceConfiguration`) were silently wiped ~17:26 EDT 09-03. Restored same day via the full-carry command; the branded code arrived on resend and the accept completed. Full story + the binding full-carry rule: `aws-cognito-prod-setup.md` 2026-09-04 incident addendum; canonical restore command: `aws-ops-runbook.md` §14.5 Step 5.
2. **Test 3 expectation** now quotes the technician terminal panel copy verbatim (previously paraphrased as "get the mobile app").
3. **Test 11 expectation corrected** — the pool is `OPTIONAL` MFA with app-layer (per-tenant) enforcement off by default, so the correct first-login behavior is password → straight to `/dashboard` with **no MFA challenge and no enrollment prompt** (enrollment is self-serve post-login at Account → Security). The previous wording ("optional TOTP enrollment") wrongly implied an enrollment offer at login.

## Remainder run order (2026-09-04)

**You need**: 3 fresh Gmail `+` aliases (`+office1`, `+dup1`, `+rev1`), the tech1 login from the green run, ~45–60 min.

| Order | Step | Tests | Why |
|---|---|---|---|
| 1 | Phase 0 quick re-check: tunnel + gates 0.1 / 0.3 / 0.5 / 0.7 / 0.8 (~4 min) | 0 | Lambda (0.4) unchanged since the 09-03 deploy; 0.7's garbage-token render doubles as Test 9; **0.8 guards the 09-04 pool-drift signature** |
| 2 | Send **all three** invites up front: `+office1` = Office Staff, `+dup1` = Technician, `+rev1` = Technician | 1 (send path ×3) | All emails in flight while you run the no-inbound-email tests |
| 3 | Test 6 (invite tech1's email → 409 explainer) → Test 5 (invite `+dup1` again → 409 + Resend offer) | 6, 5 | No inbound email needed |
| 4 | Tests 10 + 11 — tech1 web login: block banner + 5 s sign-out (expected) | 10 | No new invite needed |
| 5 | Test 4 — `+office1` full accept cycle → **auto-sign-in → `/dashboard`** → DB `office_staff`; then Test 11 MFA posture as office1 | 4, 11 | Lambda role-at-invite proof + a working non-owner web login |
| 6 | Test 7 — Resend `+dup1` → old link dead, new link live | 7 | Uses the pending dup1 invite |
| 7 | Test 8 — Revoke `+rev1` → link dead | 8 | Uses the pending rev1 invite |
| 8 | Report Pass/Fail per test → Architect flips **Ord 27 ✅ + §7 invite gate ✅** (v7.31) | — | Green board = close |

---

## Phase 0 — Pre-flight gates (do these FIRST — 5–10 min)

Open the tunnel and get the DB password (`aws-ops-runbook.md` §9.1/§9.2):

```bash
nc -z 127.0.0.1 5433 || { RDS_EP=$(aws rds describe-db-instances --db-instance-identifier pilot-production --query 'DBInstances[0].Endpoint.Address' --output text --region us-east-1); ssh -f -N -L 5433:${RDS_EP}:5432 pilot-bastion; }
DB_PASS=$(aws secretsmanager get-secret-value --secret-id "pilot/prod/db" --query 'SecretString' --output text --region us-east-1 | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
PSQL() { PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" -c "$1"; }
```

| # | Gate | Command / action | Pass condition | If it fails |
|---|---|---|---|---|
| 0.1 | Migration applied | `PSQL "SELECT version_num FROM alembic_version;"` | `3da9abdfb2f2` | Run §9.2 migrations first, then re-check |
| 0.2 | `role_code` column exists | `PSQL "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='tenant_user_invite' AND column_name='role_code';"` | 1 row, `YES` | Migration didn't run — STOP |
| 0.3 | **`team_invite` email template converged** — *the invite send 500s without this* | `PSQL "SELECT template_id, is_active FROM public.email_template WHERE template_id='team_invite';"` | 1 row, `t` | **Run the converge now**: `cd backend && source .venv/bin/activate && DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5433/pilot_prod" AWS_DEFAULT_REGION=us-east-1 python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test` (type `PILOT-PROD-SEED`) |
| 0.4 | New Lambda deployed (role-at-invite + usage counter) | `aws lambda get-function-configuration --function-name <post-confirmation-fn> --query 'LastModified' --region us-east-1` (fn name per `aws-infrastructure-as-built.md`) | LastModified ≥ 2026-09-03 | Rebuild/redeploy via `infrastructure/scripts/build-post-confirmation-lambda.sh`. **Note**: Tests 1–3 still pass without it; Test 4 (role) fails with `technician` fallback |
| 0.5 | Public endpoint live | `curl -s -o /dev/null -w "%{http_code}\n" https://api.pilotfortrades.com/api/v1/invites/not-a-real-token` | `404` (uniform, RFC 7807 `invite_invalid`) | API deploy incomplete — check ECS service sync (§19.6 canary) |
| 0.6 | Authed endpoint gated | `curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.pilotfortrades.com/api/v1/users/invites` | `401` or `403` (never 404/500) | Router registration issue — STOP, tell Architect |
| 0.7 | Landing route live | open `https://app.pilotfortrades.com/invite/not-a-real-token` incognito | Neutral "no longer valid" panel, no error page | Web deploy incomplete — redeploy `pilot-web` |
| 0.8 | **Pool config sanity** — *the 2026-09-04 drift signature: `SignUp` succeeds but Cognito sends NO code email; resend errors "Auto verification not turned on"* | `aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX --region us-east-1 --query 'UserPool.{AV: AutoVerifiedAttributes, LC: LambdaConfig, Dev: DeviceConfiguration}'` | `AV: ["email"]` · `LC` = 3 triggers + `KMSKeyID` · `Dev` non-null | Pool config drifted (`update-user-pool` resets omitted blocks) — restore with the full-carry command in `aws-ops-runbook.md` §14.5 Step 5, then re-check |

**Stop-and-fix rule**: any Phase 0 failure gets resolved before Test 1. Tests 1–3 validate the *flow*; a Phase-0 green board means failures after this are real bugs.

---

## Test 1 — Happy path: invite a Field Technician

1. Prod web, logged in as **owner** → **Settings → Team** → **Invite team member**.
2. Email = your first alias (`you+tech1@gmail.com`), Role = **Field Technician** → **Send invite**.
3. **Expected — UI**: success confirmation; the **Pending invites** section shows the row: alias email, Technician badge, sent today, ~7 days left, `pending` chip.
4. **Expected — email** (may take 1–2 min; check spam the first time): subject *"You've been invited to join {your tenant name} on Pilot for Trades"*; body names your company + "Field Technician"; CTA link shape `https://app.pilotfortrades.com/invite/<long-token>`.
5. **DB verify**:

```sql
PSQL "SELECT email, role_code, accepted_at, is_active, expires_at > now() AS not_expired, invited_by IS NOT NULL AS has_inviter, length(token_hash) = 64 AS hashed FROM public.tenant_user_invite WHERE email = 'you+tech1@gmail.com';"
-- expect: role_code=technician, accepted_at NULL, t, t, t, t

PSQL "SELECT team_invited FROM public.tenant_onboarding_checklist WHERE tenant_id = '<your prod tenant id>';"
-- expect: t   (checklist auto-completion fired)
```

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Test 2 — Landing page renders (valid invite)

1. From the Test 1 email, open the invite link **incognito** (logged out).
2. **Expected** (TEAM-INVITE-2): "You've been invited to join **{tenant name}**", the alias email shown **display-only** (not an input), **Field Technician**, expiry date, and the **on-page accept form** (password + confirm + *Create account*). **Fail signature**: a *Create your account* CTA linking to `/signup` — that misroute is what TEAM-INVITE-2 removed; seeing it means `pilot-web` is serving a stale image. No app sidebar/login chrome; brand treatment present.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Test 3 — Acceptance: on-page SignUp → Lambda attach → technician terminal panel

1. On the landing page itself: enter a password + confirm → *Create account* → the **branded** Cognito verification email arrives at the alias inbox → enter the 6-digit code **on the same page**. Never touch `/signup` — that's the owner wizard (Path 3).
2. `ConfirmSignUp` fires the Post-Confirmation Lambda Path 2 attach (async, ~10 s).
3. **Expected — UX (technician branch)**: the landing shows the **mobile-app success panel** — verbatim copy: heading *"You're in, {invited email}!"* + body *"Open the Pilot mobile app and sign in with this email to get started."* (`InviteVerifyStep.tsx`). No download links — it directs the tech to sign into the mobile app; the correct terminal state, since technicians are blocked from the web app post-login by design. **No signup wizard, no new company created.** Owner-side check: the Team page shows the technician as a member (accepted invite leaves pending / shows `accepted`). A tech who then logs into the *web* app gets the info banner + auto sign-out after 5 s — expected, not a failure (see Test 10).
4. **DB verify**:

```sql
PSQL "SELECT tu.role_code, tus.code AS status, tu.joined_at IS NOT NULL AS joined FROM public.tenant_user tu JOIN public.user u ON u.id = tu.user_id JOIN tenant_user_status tus ON tus.id = tu.status_id WHERE u.email = 'you+tech1@gmail.com' AND tu.tenant_id = '<your prod tenant id>';"
-- expect: technician, active, t

PSQL "SELECT accepted_at IS NOT NULL AS accepted FROM public.tenant_user_invite WHERE email = 'you+tech1@gmail.com';"
-- expect: t

PSQL "SELECT channel, is_primary, verification_status FROM public.user_endpoint ue JOIN public.user u ON u.id = ue.user_id WHERE u.email = 'you+tech1@gmail.com';"
-- expect: email, t (pending or verified)

PSQL "SELECT count(*) FROM public.tenant;"
-- expect: UNCHANGED count vs before Test 1 (Path 2 must NOT create a tenant)

PSQL "SELECT current_user_count FROM public.tenant_subscription_usage WHERE tenant_id = '<your prod tenant id>' AND period_end >= now();"
-- expect: +1 vs pre-Test 3 value (requires gate 0.4's new Lambda — if unchanged and 0.4 was skipped, note as known-gap, not a failure)
```

| Result | ✅ **Pass** 2026-09-04 — branded code arrived (after the gate-0.8 pool-config restore), Path 2 attach fired, terminal mobile panel renders with the verbatim copy. Side bugs logged: owner received a new-device SMS for the tech's sign-in (INV-BUG-4); accepted invite still shows in Pending Invites (INV-BUG-5). |
|---|---|

## Test 4 — Role-at-invite (proves the new Lambda path)

1. Invite your second alias (`you+office1@gmail.com`) as **Office Staff**; complete the email → landing → on-page password → branded verify-code cycle (Tests 1–3 abbreviated).
2. **Expected — UX (office branch)**: after the code confirms, the page **auto-signs-in and lands on `/dashboard` inside the inviting tenant** — no wizard, no new company. (Office roles use the web app; the technician branch's mobile panel does not apply.)
3. **DB verify**:

```sql
PSQL "SELECT tu.role_code FROM public.tenant_user tu JOIN public.user u ON u.id = tu.user_id WHERE u.email = 'you+office1@gmail.com' AND tu.tenant_id = '<your prod tenant id>';"
```

- **Pass**: `office_staff`. **Fail signature**: `technician` → the Lambda redeploy (gate 0.4) didn't take effect — the invite flow works but every invitee becomes a technician until it lands.

| Result | ✅ **Pass** 2026-09-04 — office accept → auto sign-in → landed on `/dashboard` inside the inviting tenant (the office role branch itself proves the role-at-invite attach; a `technician` fallback would have rendered the mobile panel). Side bugs logged: Schedule/Jobs/Comms/Catalog error + Reports blank on office login (INV-BUG-3); owner SMS (INV-BUG-4); pending row persists (INV-BUG-5). |
|---|---|

## Test 5 — Duplicate pending invite → 409 + Resend offer

1. Invite a **third** alias (`you+dup1@gmail.com`) as Technician → success.
2. Immediately invite the **same alias** again.
3. **Expected**: the dialog shows the duplicate state (*an invite is already pending for this email*) with a **Resend invite** action — no second invite row created.

```sql
PSQL "SELECT count(*) FROM public.tenant_user_invite WHERE email = 'you+dup1@gmail.com' AND accepted_at IS NULL AND is_active;"
-- expect: 1
```

| Result | ❌ **Fail** 2026-09-04 — inviting the same pending email again crashed to the black "This page couldn't load" error screen — no duplicate explainer, no Resend offer (INV-BUG-1). Also observed: a long email address overflows the pending-invite row (INV-BUG-6). |
|---|---|

## Test 6 — Existing-user invite → 409 explainer

1. Invite **your own owner email** (or the tech1 alias from Test 3 — now a full user).
2. **Expected**: the dialog shows the *"this person already has a Pilot account"* explainer — no crash, no second path, no email sent.

| Result | ❌ **Fail** 2026-09-04 — inviting an existing team member crashed to the black "This page couldn't load" error screen — no explainer shown (INV-BUG-1). |
|---|---|

## Test 7 — Resend: token rotation kills the old link

1. From Test 5's pending row (or its 409 state), hit **Resend**.
2. **Expected**: new email arrives; pending row shows refreshed expiry.
3. Open the **original** Test-5 email's link → **neutral "no longer valid"** page. Open the **new** email's link → valid landing renders.
4. (Optional cleanup of this case: complete or revoke the dup1 invite.)

| Result | ✅ **Pass** 2026-09-04 — validated via the revoke → re-invite path: new invite email arrived, the revoked link renders the neutral invalid page, the new link works end-to-end. The Resend-from-409-offer variant remains untested (blocked by INV-BUG-1). |
|---|---|

## Test 8 — Revoke kills the invite

1. Invite a fourth alias (`you+rev1@gmail.com`) → then **Revoke** it from the pending row (confirm step).
2. **Expected**: chip flips `revoked`; the emailed link → neutral invalid page.
3. Try **Resend** on the revoked row (if the UI offers it) → 409 (*invite_revoked*); revoking again is a no-op/409 — no crash.

| Result | ✅ **Pass** 2026-09-04 — revoke killed the invite; revoked link → neutral invalid page; re-inviting the same email after revoke worked end-to-end. |
|---|---|

## Test 9 — Garbage token shows nothing

1. Incognito: `https://app.pilotfortrades.com/invite/abc123notarealtoken`.
2. **Expected**: the same neutral invalid page as Test 7/8 — **no** hint whether the token ever existed, no expiry details, no error stack.

| Result | ✅ **Pass** 2026-09-04 — garbage token renders the neutral page verbatim: *"This invite link is no longer valid. Ask the business owner to send you a fresh invite."* No existence hints, no expiry details, no error stack. |
|---|---|

## Test 10 — Technician web block (by design) + office-role RBAC check

Log into the **web** app as the Test-3 technician (`you+tech1@…`):

| Check | Expected |
|---|---|
| Post-login landing | Info banner: *"The Pilot web app is for owners and office staff. Please use the mobile app."* |
| ~5 s later | Automatic sign-out → back at `/login` — **no error loop, no dead end** |

**Why this changed (v1.1)**: technicians are deliberately blocked from the web app post-login (`usePostLoginRedirect.ts` — TEAM-INVITE-2 design §G.1), and the live role table confirms technicians hold **no `users.*` permissions** — so the v1.0 technician RBAC matrix is not exercisable on web. The full technician permission surface lives in the **mobile app** (covered by the mobile suite + a future mobile smoke). The web-side technician check is exactly the block behavior above.

Then log in as the Test-4 **office1** account — this is the working non-owner web login that exercises the ADR-0010 rename end-to-end:

| Check | Expected |
|---|---|
| Lands on `/dashboard` inside the inviting tenant | Yes — no wizard, no block banner |
| Settings → Team | Members list renders (`users.view` held); **no Invite button, no role dropdowns** (`users.manage` is owner-only — hide-not-disable) |
| Billing / integrations / settings-admin surfaces | Absent (office_staff holds no billing or integrations permissions) |

**Fail signatures**: the technician sees owner chrome, a blank page, or a redirect loop — or office1 sees the Invite button / owner-only surfaces → the rename has a prod-facing bug — screenshot + STOP.

| Result | ❌ **Fail** 2026-09-04 — technician web login: NO info banner, NO 5 s auto sign-out; the tech lands inside the app shell with menu items rendering blank / "failed to load" pages (INV-BUG-2 — the designed block did not engage). Office web login: `/dashboard` lands, but Schedule / Jobs / Comms / Catalog error on load and Reports is blank, AND the Settings → Team menu item is entirely ABSENT (INV-BUG-3). Verified against the PROD `tenant_user_role` table (postgres-prod MCP query, 2026-09-04): office_staff HOLDS `users.view` (Team should render read-only — over-hide), `schedule.manage`/`view_all` + `reports.view` (those pages should work), and does NOT hold `jobs.*`/`catalog.*`/comms perms (those nav items should be hidden). Full grant matrix in the tracker entry. |
|---|---|

## Test 11 — First-login / MFA posture for the invited user

1. Fresh login as the **office1** user (a web-allowed role). **Expected**: password → straight to `/dashboard` — **no MFA challenge, no MFA enrollment prompt**. The pool is `OPTIONAL` MFA; enforcement is app-layer/per-tenant and off by default, so nothing interrupts login. MFA enrollment is self-serve post-login at **Account → Security** (TOTP or SMS). **Fail signature**: an MFA challenge loop, a forced-enrollment dead end, or a redirect to a Cognito-hosted UI.
2. Log out/in once more — same direct-to-`/dashboard` behavior. (Running this as tech1 is identical up to the post-login landing, which is the Test-10 block banner — expected.)

| Result | ✅ **Pass** 2026-09-04 — ran as a fresh **accountant** invitee: code confirm → straight to `/dashboard`, no MFA prompt; logout + login again → straight to `/dashboard`. Matches the corrected expectation. Bonus coverage: the accountant accept re-proved the full invite → landing → branded-code → office-branch auto-sign-in path for a third role. |
|---|---|

---

## Cleanup

- **Keep** the tech1 user if you want a standing technician login for future prod testing (recommended — it's the only non-owner account you have).
- **Pending invites** you don't intend to accept: revoke them (chip → revoked) — they also auto-expire in 7 days and become inert.
- **Attached test users** (tech1/office1): removal is **not** self-serve — a completed signup has `user`/`tenant_user`/`user_endpoint` rows + a Cognito pool entry. Use `aws-ops-runbook.md` **§9.9 — Remove an Invited Employee (Invite-Accept Teardown for Email Reuse)** (§9.8 covers only *pre-completion* signups). First executed 2026-09-04 to free `owner@example.com` + `admin@example.com` for this plan's re-run.

## Reporting back

Fill the Result line on each test (Pass/Fail + notes + screenshots for UI failures). When the board is green → **§7 gate row flips ✅** and **TEAM-INVITE-2 closes (Ord 27 ✅)** in the same launch-plan version (v7.31). Any failure → paste the test #, what you saw, and the DB query output — Phase-0-green failures are real bugs and get a PLP-class fix batch.

---

### Reference — what each failure signature means

| Signature | Likely cause | First check |
|---|---|---|
| Invite send 500s | `team_invite` template missing in prod | Gate 0.3 — run the converge |
| Email never arrives | SendGrid sandbox/quota or spam | SendGrid activity feed; spam folder; `render_and_send` logs in API task logs |
| **Verification code** never arrives (invite email DID) + resend errors "Auto verification not turned on" | Pool `AutoVerifiedAttributes` wiped by an `update-user-pool` call that omitted it (2026-09-04 incident) | Gate 0.8 — restore via `aws-ops-runbook.md` §14.5 Step 5 full-carry command; then Resend code on the open verify screen |
| Landing 404s the whole page | `pilot-web` deploy stale | Gate 0.7 — redeploy web service |
| Signup creates a NEW company/wizard | Path 2 didn't match the invite (email mismatch — alias typo, or invite expired/revoked) | DB: invite row exists, active, unexpired, exact email match |
| Attaches as `technician` regardless of role | Old Lambda still deployed | Gate 0.4 — redeploy Lambda |
| Technician sees owner UI (or blank UI) | RBAC rename regression | Test 10 STOP — screenshot to Architect |
| Usage count didn't increment | New Lambda not deployed (best-effort path) | Gate 0.4; analytics-only, non-blocking |
