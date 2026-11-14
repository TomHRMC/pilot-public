# PLP-FIX-9 + FIX-7/8 Delta — Production Verification Plan (Tom)

**Date**: 2026-09-05 · **Author**: Pilot Architect · **For**: Tom
**What this covers**: the four delta items owed from the 09-05 FIX-7/8 run (① duplicate-pending 409 + Resend, ② office_staff matrix, ③ INV-BUG-7 repro, ④ Revoke-clip) **plus** the PLP-FIX-9 fix board (INV-BUG-6-rem, 7, 8, 9, 10, 11, 12 + the INV-D-5 comms grant) once FIX-9 deploys.
**Two stages**: **Stage 1** runs NOW against current prod (FIX-7 + FIX-8 live; FIX-9 not yet executed). **Stage 2** runs after PLP-FIX-9 Part A (seed converge) + Part B (web image) land on prod.
**Gate linkage**: Stage 1 Tests 1–3 green + Stage 2 board green → **Ord 27 (TEAM-INVITE-2) ✅** and the **§7 invite gate ✅** flip in one launch-plan version (Architect action); tracker INV-BUG-3, 6, 7, 8, 9, 10, 11, 12 move to CLOSED in `tom-ui-issues-tracking.md`. This plan **supersedes the delta list ①–④** in the 09-05 run record — that record stays as history.
**Time budget**: Stage 1 ~20 min · Stage 2 ~30–40 min (Phase 0 deploys not included)
**You need**: prod web access as **owner**, the standing **tech1** / **office1** / **accountant** logins from the 09-04/09-05 runs, one **fresh long Gmail alias** (e.g. `you+delta-run@gmail.com` — doubles as the long-email row for ④), the SSH tunnel + `PSQL` helper from the 09-03 plan's Phase 0 (same commands), and a **browser profile you have never signed in with** (or fully cleared site data for `app.pilotfortrades.com`).

---

## Stage 1 — run now (prod as it stands: FIX-7 + FIX-8 live)

No deploy gates — everything Stage 1 touches shipped 09-04/09-05 and was deploy-verified in the 09-05 run's Phase 0.

### Test 1 — ① Duplicate-pending invite → 409 explainer + Resend offer

1. Prod web as **owner** → **Settings → Team** → **Invite team member** → enter your **fresh long alias** as **Field Technician** → **Send invite** → success; the pending row appears.
2. Immediately invite the **same alias** again.
3. **Expected**: the dialog **stays open** with the **duplicate-pending explainer** + a **Resend invite** action — no black *"This page couldn't load"* screen, no crash.
4. Click **Resend** → a new email arrives; the **original** email's link now renders the neutral *"no longer valid"* page.
5. DB verify:

```sql
PSQL "SELECT count(*) FROM public.tenant_user_invite WHERE email = 'you+delta-run@gmail.com' AND accepted_at IS NULL AND is_active;"
-- expect: 1
```

**Fail signature**: error-boundary crash → the web image is stale (FIX-7 Part B); generic "something went wrong" with no Resend offer → the API type-URI mapping isn't live (FIX-7 Part A).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 2 — ② office_staff matrix as office1 (pre-FIX-9 expectations)

Sign in to the **web** app as **office1**:

| Check | Expected NOW (FIX-9 not shipped) |
|---|---|
| Lands on `/dashboard` | Yes — no wizard, no block banner |
| Settings → **Team** menu item | Present |
| Team page | Members list renders; **no Invite button, no role dropdowns** |
| **Schedule** | Board loads — no 403 error page |
| **Reports** (Profitability) | Renders with data |
| **Jobs / Catalog** nav items | Hidden |
| **Comms** nav item | **Hidden — correct for now.** The INV-D-5 grant ships with FIX-9 Part A; Stage 2 Test 4 re-checks this row expecting VISIBLE |

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 3 — ③ INV-BUG-7 repro: technician session must not show customer data

Technicians get the block banner + auto sign-out ~5 s after web login (verified 09-05) — so **open DevTools → Network (tick "Preserve log") BEFORE signing in**, and review the calls after the sign-out; the recording survives.

- **3a — Clean profile**: fresh browser profile (never signed in) → sign in as **tech1**.
  **Expected**: in the Network log, `GET /customers` (and any sites/quotes/invoices calls) return **403**; the visible page shows a graceful empty state, **no customer data**. Any create attempt 403s.
  **🚨 If ANY write persists as technician, or data renders from a clean profile → P0 — stop and report immediately.** Server gates were code-verified present at design; a clean-profile breach would contradict that verification.
- **3b — Cache-bleed repro** (documents the bug FIX-9 cures): same browser → sign in as **owner** → open **Customers** (data renders) → **sign out** → sign in as **tech1** → watch the Customers area in the seconds before the block sign-out.
  **Expected on current prod**: you may see the **owner's cached customer data flash** for tech1 — that is INV-BUG-7 (stale query-cache across sessions). **Record what you see** (screenshot if it happens) — this is the "before" evidence. Stage 2 Test 5 re-runs this exact sequence expecting zero leakage.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

**Stage 1 done → report per "Reporting back" below. The gate stays open until Stage 2.**

---

## Stage 2 — after PLP-FIX-9 deploys (Part A converge + Part B web image)

### Phase 0 — Deploy gates (both must be checked)

Deploy shape: FIX-9 is **seed + web only** — no API/worker/Lambda changes, zero endpoint deltas.

| # | Gate | How to verify | Pass condition |
|---|---|---|---|
| 0.1 | **Prod seed converge run** (Part A — office_staff comms + all-role self-service security grants) | Standard converge: `cd backend && source .venv/bin/activate && DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5433/pilot_prod" AWS_DEFAULT_REGION=us-east-1 python migrations/scripts/seed_prod_db.py --mode seed --stripe-mode test` (type `PILOT-PROD-SEED`), then: `PSQL "SELECT permissions ? 'communications.send' FROM public.tenant_user_role WHERE code='office_staff';"` and `PSQL "SELECT permissions ? 'mfa.enroll_self' FROM public.tenant_user_role WHERE code='technician';"` | Both return `t` |
| 0.2 | **Web image deployed** (Part B) | ECS `pilot-web` service shows a new deployment ≥ the FIX-9 merge | New deployment live |

### Test 4 — INV-D-5: office_staff Comms unlocked (② recheck)

1. Sign in as **office1** → the **Comms** nav item is now **VISIBLE**.
2. Open a customer → the **Comms tab** renders the thread (previously hidden for office staff).
3. Send a short reply in an existing thread → sends without error.
4. Dashboard → the customer-messages widget renders content (not hidden, not an error panel).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 5 — INV-BUG-7 cure: session cache-clear (③ recheck)

Re-run Test 3b exactly: owner login → Customers (data renders) → **sign out** → tech1 login.
**Expected**: **zero** owner data flashes for tech1 — 403 empty states only. Then sign out → owner login → Customers renders normally (cache rebuilt clean — the clear must not break normal use).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 6 — INV-BUG-8: employee self-service Security page

As **accountant**, then repeat as **office1**: **Settings → My Account → Security**.
**Expected**: the MFA methods section **loads** (no *"We couldn't load your MFA methods"*); session history loads; **start** TOTP enrollment → the QR/secret step opens (**cancel before completing** — no need to finish enrollment).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 7 — INV-BUG-9: write affordances hidden on view-only roles

As **accountant**:

| Surface | Expected |
|---|---|
| Jobs list | **No** "+ Add Job" button |
| Invoice detail | **No** Send Invoice / Record Payment buttons |
| Quote detail | Line items fully read-only — no "+ Add Line Item", no "Save Line" |

**Expected side effect, NOT a bug** (design §G.6): **office1 also loses** "+ Add Job" and Send/Record Payment after the sweep — office_staff holds `jobs.view` + `invoices.create` but not `jobs.create` / `invoices.update`. If office staff should have those, that's a future grant ruling, not this batch.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 8 — INV-BUG-10: 403 grace on embedded panels

1. As **accountant** → open any **job detail** → the **Technicians box** renders assignments **read-only** — no "Failed to load technicians" error panel.
2. As **accountant** → **Dashboard** → the customer-messages widget is **hidden** (not an error).
3. As **office1** → **Schedule** board → renders with **default lanes** — no full-page "Unable to load subscription lane count" error.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 9 — INV-BUG-11: invoice-builder line renders on add

As **owner** → Invoices → **New invoice** (standalone) → add a line item.
**Expected**: the row appears in the list **immediately** (before any save). **Save as Draft** → reopen the invoice → the line persisted (regression check).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

### Test 10 — ④ Revoke-clip + INV-BUG-12 Comms-tab gate

- **10a — ④ INV-BUG-6-rem**: use the Stage-1 long-alias pending row (re-invite the alias if it was accepted/revoked) → the row's **Revoke** button is **fully visible** — no right-side clip in the Actions column. (Email still ellipsizes with tooltip — that part already works.)
- **10b — INV-BUG-12**: as **accountant** → open any customer → the **Comms tab is hidden**. (office1 sees it — covered in Test 4.)

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

---

## Reporting back

Fill each Result line (Pass/Fail + notes + screenshots for UI failures). Then:

- **Stage 1 green (Tests 1–3)** → tell the Architect: delta ①②③ confirmed; the gate stays open pending Stage 2.
- **Stage 2 board green (Tests 4–10)** → **Ord 27 (TEAM-INVITE-2) ✅** and the **§7 invite gate ✅** flip in one launch-plan version; tracker INV-BUG-3, 6, 7, 8, 9, 10, 11, 12 → CLOSED.
- **Any failure** → paste the test #, what you saw, screenshots, and any DB/log output. Phase-0-green failures are real regressions and get a PLP-class fix batch.

### Cleanup

- Revoke leftover pending invites (they auto-expire in 7 days otherwise). The alias user, if accepted, can stay attached or be removed via `aws-ops-runbook.md` §9.9 (invite-accept teardown).

---

## Run record — 2026-09-06 (Tom)

**Phase 0 / Stage 1** (run on the pre-FIX-9 web image; converge + web deploy landed before Stage 2):

- **Test 1 (①)**: ✅ **PASS (functional)** — duplicate-pending 409 → inline explainer + Resend offer; new email arrives; original link renders the neutral page; DB count = 1. **New finding → INV-BUG-15**: Team + Pending Invites tables are fixed-width; a long email shows only "tom@g…". Tom-ruled direction: content-sized column min-widths + horizontal scroll on overflow.
- **Test 2 (②)**: ⚠️ **MOSTLY PASS** — Team page ✅ / Reports ✅ / Catalog hidden ✅ / Comms hidden ✅ (pre-converge expectation) / Jobs visible ✅ (**correct** per the FIX-7 `jobs.view` grant — this plan's "hidden" expectation was wrong). **Schedule → blank content section → INV-BUG-13 (P1)**. Invite-button/role-dropdown absence not explicitly re-confirmed.
- **Test 3 (③)**: ✅ **PASS** — clean-profile tech1: all API calls 403, no data rendered, no cache bleed, auto-logout intact.

**Stage 2** (post-FIX-9: converge ✅ — `communications.send` on office_staff `t`, `mfa.enroll_self` on technician `t`; web image ✅):

- **Test 4 (INV-D-5)**: ✅ **PASS** — office1 sees Comms nav + customer Comms tab; dashboard loads. (Send-reply sub-check not exercised.)
- **Test 5 (INV-BUG-7 cure)**: ✅ **PASS** — 3b re-run: zero owner-data flash for tech1; owner re-login rebuilds cache clean.
- **Test 6 (INV-BUG-8)**: ✅ **PASS** — MFA methods load for non-owner. (Session-history + enrollment-start sub-checks not explicitly confirmed.)
- **Test 7 (INV-BUG-9)**: ✅ **PASS** — accountant: no +Add Job; no Send/Record Payment; quote detail read-only. Observation: "Generate & Copy link" still renders (greyed) → INV-BUG-16 (hide-not-disable consistency).
- **Test 8 (INV-BUG-10)**: ❌ **FAIL — all three sub-checks root-caused same-day**: (a) accountant still gets "Failed to load technicians" — `GET /jobs/{job_id}/assignments` is gated **`schedule.view_all`** (FIX-9 design assumed `jobs.view` — design miss); accountant lacks it → assignments query 403s → ErrorState. (b) accountant still sees Recent Customer Messages — the `*.view` wildcard (INV-D-4) expands to `communications.view` in BOTH the FE and BE matchers → `.view`-based comms gates are structurally ineffective for accountant → **INV-D-6 ruling queued**. (c) office1 Schedule still blank → **INV-BUG-13**: `DispatchBoardPage` wraps the whole board in `RoleGate role={["owner","accountant"]}` (legacy pre-ADR-0010 role list) — office_staff renders nothing.
- **Test 9 (INV-BUG-11)**: ✅ **PASS** — custom line renders immediately on add. (Save-as-Draft persistence not explicitly re-confirmed.)
- **Test 10**: ❌ **SPLIT** — 10a ④: folded into the INV-BUG-15 table-layout ruling (explicit Revoke-visibility re-check owed in PLP-FIX-10 verification). 10b (INV-BUG-12): **FAIL for accountant** (`*.view` wildcard → INV-D-6); technician path fixed by the Part B gate.

**Outcome — gate NOT flipped.** Ord 27 + §7 invite gate stay 🔄/☐. All failures root-caused; fixes → **PLP-FIX-10 (Ord 31)**. Pending rulings: **INV-D-6** (accountant wildcard: accept wide-read vs enumerate view codes) and the RBAC-CONFIG-1 grant discussion (office_staff jobs edit, permissions admin UI).

**Sub-check completion — 2026-09-06 (Tom)**: ② Team invite controls ✅ (no Invite button, no role dropdowns — ② fully green except Schedule/INV-BUG-13) · ④ Revoke fully visible ✅ (**all four FIX-7/8 delta items now closed**) · ⑨ Save-as-Draft persistence ✅ · office1 comms send-reply: **deferred to the Phase 2 full UI suite per Tom** (no comms thread exists to reply to — launch plan §4.1 carries it) · ⑥ session history: **empty for office + accountant → INV-BUG-17** — root-caused at intake: `_upsert_session_history` has zero production callers (never wired to a login event; `user_session_history` 0 rows locally; endpoint 404s) → PLP-FIX-10 Part A (Python).
