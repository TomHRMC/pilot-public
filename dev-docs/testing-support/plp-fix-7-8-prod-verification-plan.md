# PLP-FIX-7 + PLP-FIX-8 — Production Verification Plan (Tom)

**Date**: 2026-09-05 · **Author**: Pilot Architect · **For**: Tom
**What shipped (code-complete)**: **PLP-FIX-7** (2026-09-04 — Part A: invite 409 specific type URIs + office_staff `jobs.view` seed grant; Part B: server-authoritative RBAC end-to-end, login role-race fix, 409 inline explainers, pending-invite filter + email truncation, Reports-blank fix) · **PLP-FIX-8** (2026-09-05 — new-device SMS alert resolves to the **authenticating user's** verified+opted-in endpoints, not the owner's)
**Gate linkage**: a green board flips **Ord 27 (TEAM-INVITE-2) ✅** and the **§7 invite gate ✅** in the same launch-plan version (Architect action), and INV-BUG-1…6 move to CLOSED in the tracker. This plan **supersedes the Tests 5/6/10 re-run** in `team-invite-1-prod-test-plan.md` — it is that re-run, expanded for INV-BUG-4/5/6.
**Time budget**: ~30–45 min (Phase 0 deploys not included) · **You need**: prod web access as **owner**, the standing **tech1** + **office1** logins from the 09-04 run, **one fresh long Gmail alias** (e.g. `you+duplicate-pending-invite@gmail.com` — doubles as the INV-BUG-6 long-email check), the SSH tunnel + `PSQL` helper from the 09-03 plan's Phase 0 (same commands), and a **browser profile you have never signed in with** (or fully cleared site data for `app.pilotfortrades.com`) for Test 6.

---

## Phase 0 — Deploy gates (do these FIRST — every box must be checked)

Deploy order matters: **API + converge → web** (FIX-7); **worker → Lambda** (FIX-8).

| # | Gate | How to verify | Pass condition |
|---|---|---|---|
| 0.1 | **API image deployed** (FIX-7 Part A — 409 type URIs) | GitHub Actions green on the 09-04 merge; ECS `pilot-api` service shows a new deployment ≥ 2026-09-04 | New deployment live |
| 0.2 | **Prod seed converge run** (office_staff `jobs.view`) | `PSQL "SELECT permissions ? 'jobs.view' FROM public.tenant_user_role WHERE code='office_staff';"` | `t` — if `f`, run the converge: `cd backend && source .venv/bin/activate && DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5433/pilot_prod" AWS_DEFAULT_REGION=us-east-1 python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test` (type `PILOT-PROD-SEED`), then re-check |
| 0.3 | **Web image deployed** (FIX-7 Part B) | ECS `pilot-web` service shows a new deployment ≥ 2026-09-04 (after 0.1) | New deployment live |
| 0.4 | **Worker image deployed** (FIX-8 — Celery carries `recipient_user_id`) | ECS worker service shows a new deployment ≥ 2026-09-05 | New deployment live |
| 0.5 | **Post-Authentication Lambda redeployed** (FIX-8) | `aws lambda get-function-configuration --function-name <post-authentication-fn> --query 'LastModified' --region us-east-1` (fn name per `aws-infrastructure-as-built.md`); redeploy via `build-post-authentication-lambda.sh` + Terraform if stale | LastModified ≥ 2026-09-05, **after** 0.4 |

**Stop-and-fix rule**: Tests 1–5 fail for their own reasons if 0.1–0.3 aren't done; Test 6 is **meaningless** unless 0.4 AND 0.5 are both done (old Lambda → owner fan-out by design).

---

## Test 1 — INV-BUG-1a: existing-member invite → inline explainer (Test 6 re-run)

1. Prod web as **owner** → **Settings → Team** → **Invite team member** → enter **tech1's email** (now a full user) → **Send invite**.
2. **Expected**: the dialog **stays open** and shows the *"this person already has a Pilot account"* explainer — **no** black *"This page couldn't load"* screen, no second path, no email sent.

**Fail signature**: error-boundary crash → the web image is stale (0.3) or the type-URI mapping isn't live (0.1).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Test 2 — INV-BUG-1b + INV-BUG-6: duplicate pending invite → explainer + Resend offer (Test 5 re-run)

1. Invite your **fresh long alias** as **Field Technician** → success; the pending row appears.
   - **INV-BUG-6 check**: the long email renders **truncated with ellipsis** (hover → full-email tooltip); the table does **not** overflow its container.
2. Immediately invite the **same alias** again.
3. **Expected**: the dialog shows the **duplicate-pending explainer** with a **Resend invite** action — no crash.
4. Click **Resend** (this also closes the Resend-from-409-offer variant left untested on 09-04): new email arrives; the **original** email's link now renders the neutral *"no longer valid"* page.
5. **DB verify**:

```sql
PSQL "SELECT count(*) FROM public.tenant_user_invite WHERE email = 'you+duplicate-pending-invite@gmail.com' AND accepted_at IS NULL AND is_active;"
-- expect: 1
```

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Test 3 — INV-BUG-2: technician web block engages (Test 10 tech half re-run)

1. Sign in to the **web** app as **tech1**.
2. **Expected**: the info banner — *"The Pilot web app is for owners and office staff. Please use the mobile app."* — then **automatic sign-out after ~5 s** → back at `/login`. No error loop, no dead end, no app shell with blank pages.

**Fail signature**: tech lands inside the app shell with menu items → the login role-race fix isn't live (0.3) — screenshot + STOP.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Test 4 — INV-BUG-3: office_staff nav + pages match prod grants (Test 10 office half re-run)

Sign in to the **web** app as **office1**:

| Check | Expected |
|---|---|
| Lands on `/dashboard` | Yes — no wizard, no block banner |
| Settings → **Team** menu item | **Present** (was absent on 09-04) |
| Team page | Members list renders (`users.view` held); **no Invite button, no role dropdowns** (`users.manage` is owner-only) |
| **Schedule** | Board loads — no 403 error page (`jobs.view` grant + converge 0.2) |
| **Reports** (Profitability) | Renders with data (was blank on 09-04) |
| **Jobs / Comms / Catalog** nav items | **Hidden** (office_staff holds none of those permissions) |

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Test 5 — INV-BUG-5: accepted invites leave Pending Invites

1. Complete the Test-2 alias accept cycle (email → landing → on-page password → branded 6-digit code → technician mobile-app panel).
2. Back as **owner** → **Settings → Team**: the alias appears in the **members list** and **not** in Pending Invites.
3. Also confirm the 09-04 accounts: **tech1 and office1 must NOT appear in Pending Invites** — only genuinely pending rows (or the section hides entirely when empty).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Test 6 — INV-BUG-4: new-device SMS goes to the signing-in user, not the owner (PLP-FIX-8)

**Precondition**: gates 0.4 + 0.5 both green. Use a **fresh browser profile** (or cleared site data) for each sign-in so the device registers as new.

1. **Employee new-device sign-in**: fresh profile → sign in as **office1**.
   **Expected**: the **owner's phone receives NO** *"New sign-in to your account from a new device"* SMS. (office1 has no verified+opted-in phone → nobody is notified — correct by design.)
2. **Owner new-device sign-in** (regression guard): fresh profile → sign in as **owner**.
   **Expected**: the owner's phone **does** receive the new-device SMS (the owner IS the authenticating user).
3. **Optional log check**: worker logs for the sign-in window show `recipient=user` lines for these events (and no `recipient=owners` line for the office1 sign-in).

**Fail signature**: office1's sign-in texts the owner → the Lambda (0.5) or worker (0.4) is stale; check both `LastModified`/deployment times before reporting.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

---

## Reporting back

Fill each Result line (Pass/Fail + notes + screenshots for UI failures). Then:

- **Green board (all 6 pass)** → tell the Architect: **Ord 27 (TEAM-INVITE-2) ✅** and the **§7 invite gate ✅** flip in the same launch-plan version; INV-BUG-1…6 move to the CLOSED list in `tom-ui-issues-tracking.md`; the parked **office_staff `comms.send`** product decision (widen the seed grant or leave Comms owner-only) gets a ruling.
- **Any failure** → paste the test #, what you saw, and any DB/log output. Phase-0-green failures are real regressions and get a PLP-class fix batch.

### Cleanup

- The Test-2 alias user can stay attached (standing second technician) or be removed via `aws-ops-runbook.md` §9.9 (invite-accept teardown) if you want the email back.
- Any leftover pending invites: revoke them — they also auto-expire in 7 days.

---

## Run record — 2026-09-05 (Tom)

**Phase 0**: all 5 deploy gates green. Test 6 effectively ran during gate checks: non-owner login → **no** new-device text; owner in a new browser → text arrived; owner logout + back in (same device) → no text. Device tracking intact.
**Test 1 (INV-BUG-1a)**: ✅ **PASS** — existing-member (accountant) invite → inline error on the dialog, no crash.
**Test 2 (INV-BUG-1b/6)**: ⚠️ **PARTIAL** — the duplicate-pending 409 + Resend-offer variant was **not exercised** (delta-run item ①). INV-BUG-6 remainder found: email truncation works (ellipsis), but the **Actions column clips the right side of the Revoke button** on the long-email row.
**Test 3 (INV-BUG-2)**: ✅ **PASS** — tech login → "The Pilot web app is for owners and office staff…" banner → ~5 s auto sign-out.
**Test 4 (INV-BUG-3)**: ⚠️ **WRONG ROLE** — run as **accountant**, not office1; the office_staff matrix is still owed (delta-run item ②). The accountant + technician tours verified the nav layer against prod grants and surfaced **6 new findings + 5 product decisions** → tracker INV-BUG-7…12 / INV-D-1…D-5 (`tom-ui-issues-tracking.md`).
**Test 5 (INV-BUG-5)**: ✅ **PASS** — accepted invites leave Pending Invites.
**Test 6 (INV-BUG-4)**: ✅ **PASS** — see Phase 0.

**Outcome — gate NOT flipped.** Delta run owed:
① Duplicate-pending invite → 409 explainer + Resend offer (verification-plan Test 2, steps 2–4).
② office_staff matrix as **office1** (verification-plan Test 4 table). **Sequence note (INV-D-5, Tom-ruled 2026-09-05)**: the matrix expects Comms **HIDDEN** only until PLP-FIX-9 Part A ships the office_staff comms grant + the prod converge runs — after that deploy, Comms **VISIBLE** is the correct expectation.
③ **INV-BUG-7 repro**: clean browser profile → tech1 login → Network tab open — expected: `GET /customers` (and sites/quotes/invoices) return **403** with a graceful empty state, and any create attempt 403s. If any write persists as technician → **P0, report immediately**.
④ INV-BUG-6 Revoke-clip re-check after the CSS follow-up ships (PLP-FIX-9 Part B).

> **Superseded 2026-09-05**: this delta list now lives in `plp-fix-9-prod-verification-plan.md` — Stage 1 (①②③) runnable immediately; Stage 2 (④ + the full FIX-9 board) after the FIX-9 deploy. Run that plan; this run record stays as the 09-05 historical record.
