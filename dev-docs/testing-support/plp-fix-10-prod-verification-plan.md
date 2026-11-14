# PLP-FIX-10 — Production Verification Plan (Tom)

**Date**: 2026-09-06 · **Author**: Pilot Architect · **For**: Tom
**What this covers**: the six PLP-FIX-10 fixes — INV-BUG-13 (dispatch board blank for office_staff), INV-BUG-10a (Technicians-box 403), INV-BUG-14 (checklist Show doesn't persist), INV-BUG-15 (settings tables truncate), INV-BUG-16 (Generate-&-Copy-Link visible to view-only roles), INV-BUG-17 (session history never recorded) — once the deploy lands. Single stage: everything below runs post-deploy.
**Gate linkage**: a green board (Checks 1–6) → **Ord 27 (TEAM-INVITE-2) ✅** and the **§7 invite gate ✅** flip in one launch-plan version (Architect action); tracker INV-BUG-10, 13, 14, 15, 16, 17 move to CLOSED in `tom-ui-issues-tracking.md`. That closes the entire TEAM-INVITE lineage (TEAM-INVITE-1 → FIX-7 → FIX-8 → FIX-9 → FIX-10).
**Time budget**: ~25–35 min (Phase 0 deploys not included)
**You need**: prod web access as **owner**, the standing **office1** / **accountant** logins from the 09-04/09-06 runs, one **fresh long Gmail alias** (e.g. `you+fix10-verify@gmail.com`) for the Check 4 long-email row, and the SSH tunnel + `PSQL` helper from the 09-03 plan's Phase 0 (same commands).

---

## Phase 0 — Deploy gates (all four, in this order)

Deploy shape: **code-only** — no migration, no seed converge (Rule 11.5 N/A recorded in Part A). **Order matters**: the Post-Auth Lambda enqueues a task the worker must already know, so the Lambda goes **after** API + worker. Pre-redeploy Lambda events simply don't record logins — no errors, no backfill.

| # | Gate | How to verify | Pass condition |
|---|---|---|---|
| 0.1 | **API image deployed** (Part A — checklist-unhide route/service fix) | ECS `pilot-api` service shows a new deployment ≥ the FIX-10 merge | New deployment live |
| 0.2 | **Worker image deployed** (Part A — `record_user_login` task registered) | ECS `pilot-worker` service shows a new deployment ≥ the FIX-10 merge | New deployment live |
| 0.3 | **Post-Auth Lambda redeployed** (Part A — enqueues login recording on every authentication) — **after 0.1 + 0.2** | `infrastructure/scripts/build-post-authentication-lambda.sh` + Terraform apply per the Part A deploy note | Lambda last-modified ≥ now |
| 0.4 | **Web image deployed** (Part B — all four surface fixes) | ECS `pilot-web` service shows a new deployment ≥ the FIX-10 merge | New deployment live |

---

## Check 1 — INV-BUG-13: office_staff sees the dispatch board

1. Sign in to the web app as **office1** → open **Schedule** (`/schedule`).
2. **Expected**: the full dispatch board renders — lanes, job cards, no blank content section, no error page.
3. Sign in as **accountant** → **Schedule**.
   **Expected**: **no board** — either the Schedule nav item is absent or the board area renders nothing. This is **grant truth** (accountant holds no schedule grants — accepted side effect per design §G.1 / INV-D-6; a re-grant is an RBAC-CONFIG-1 ruling, §2 row 2-18). **Not a failure.**
4. Sanity: sign in as **owner** → board renders as before.

**Fail signature**: office1 still blank → the web image is stale (gate 0.4). office1 gets an *error page* (not blank) → different failure class — capture the page + Network tab and report.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Check 2 — INV-BUG-10a: Technicians box 403 grace

1. As **accountant** → **Jobs** → open any job detail.
   **Expected**: the page loads cleanly — **no "Failed to load technicians"** error panel; the **Technicians section is hidden entirely** (grant truth — the assignments endpoint is `schedule.view_all`-gated and accountant lacks it).
2. As **office1** → open the same job detail.
   **Expected**: the Technicians box renders with current assignments **and** the add-picker + remove buttons are visible (office_staff holds `schedule.view_all` + `schedule.manage`).
3. Exercise it: add **tech1** via the picker → assignment appears → **reload** → it persists → remove it again (leaves the job as found).

**Fail signature**: accountant still sees the error → stale web image (0.4). office1 sees the box read-only (no picker) → `schedule.manage` grant missing — contradicts the prod-verified grants; report immediately.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Check 3 — INV-BUG-14: checklist "Show" persists

1. As **owner** → **Dashboard** → collapse the **Setup checklist** (Hide) → the collapsed pill renders.
2. Click **Show** → the widget expands **and stays expanded** (the pre-fix bug: it re-collapsed on its own).
3. **Reload the page** → still expanded.
4. **Sign out → sign back in** → still expanded.
5. Re-hide it at the end if you want the dashboard back as it was.

**Fail signature**: expands then re-collapses on reload → the API image is stale (gate 0.1 — the BE one-way-write fix isn't live). Expands but collapses again on logout/login → same cause.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Check 4 — INV-BUG-15: settings tables show full values + horizontal scroll (④ final close)

1. As **owner** → **Settings → Team** → the **members table** shows **complete email values** at desktop width — no `tom@g…` ellipsis on long addresses.
2. **Pending Invites** table: if no long-email row exists, invite your **fresh long alias** (any role) → the row renders the **full address**; the **Revoke** button is **fully visible** — no right-side clip (this is the ④ re-check that closes the FIX-7/8 delta for good).
3. Narrow the browser window to ~half width → both tables **scroll horizontally** instead of crushing columns; **Resend / Revoke stay fully visible** inside the scroll region. Keyboard check (WCAG): tab into the table region → arrow keys scroll it.

**Fail signature**: truncated emails at desktop width, crushed columns, or clipped action buttons → stale web image (0.4).

**Cleanup**: revoke the leftover pending invite from step 2 (it auto-expires in 7 days otherwise).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Check 5 — INV-BUG-16: Generate-&-Copy-Link hidden for view-only roles

1. As **accountant** → **Invoices** → open any invoice detail.
   **Expected**: **no "Generate & Copy Link" / "Copy Public Link" button** anywhere on the page (hidden, not merely disabled).
2. As **owner** → open the same invoice.
   **Expected**: the button renders and works — generate + copy, then paste the link in an incognito tab → the public payment page loads (sanity on an untouched path).

**Fail signature**: the button renders for accountant (even greyed) → stale web image (0.4).

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

## Check 6 — INV-BUG-17: session history records sign-ins

The wiring fires on **every** post-deploy authentication (new device or not). Allow ~30–60 s after each sign-in for the worker to process the task.

1. As **office1**: sign out → sign in → sign out → sign in (two authentications post-deploy).
2. **Settings → Security** → the **session history** section now renders data: **first login, last login, and a count ≥ 2** (pre-fix: empty for every user; the endpoint 404'd).
3. Repeat as **owner** (two sign-ins) → same section populates.
4. DB verify:

```sql
PSQL "SELECT user_id, total_session_count, first_login_at, last_login_at FROM public.user_session_history ORDER BY last_login_at DESC LIMIT 5;"
-- expect: rows for office1 + owner, total_session_count ≥ 2, last_login_at ≈ your sign-in times
```

**Fail signature**: Security page still empty / endpoint 404s → the **worker** image is stale (gate 0.2 — task unregistered; check worker logs for `record_user_login`) **or** the Post-Auth Lambda wasn't redeployed (gate 0.3 — check its log group for enqueue lines). No rows in the DB with a green UI → impossible by construction; re-run the query.

| Result | ☐ Pass ☐ Fail — notes: |
|---|---|

---

## Reporting back

Fill each Result line (Pass/Fail + notes + screenshots for UI failures). Then:

- **Board green (Checks 1–6)** → tell the Architect: **Ord 27 (TEAM-INVITE-2) ✅** and the **§7 invite gate ✅** flip in one launch-plan version; tracker **INV-BUG-10, 13, 14, 15, 16, 17 → CLOSED**. The TEAM-INVITE lineage closes.
- **Any failure** → paste the check #, what you saw, screenshots, and any DB/log output. Phase-0-green failures are real regressions and get a PLP-class fix batch.

**Stays open regardless** (not part of this board): RBAC-CONFIG-1 grant discussion (§2 row 2-18) · INV-BUG-12 accountant comms visibility (accepted per INV-D-6 Option A) · office1 comms send-reply (deferred to the Phase 2 full UI suite per Tom — launch plan §4.1) · INV-BUG-17's A70 active-sessions half (deferred at design — rows link to never-issued app refresh tokens; future device-identity batch).

### Cleanup

- Revoke the leftover pending invite from Check 4.
- Nothing else — Check 2's add/remove is self-reverting; Check 3 ends however you leave it.

---

## Run record — 2026-09-06 (Tom)

**Phase 0 deploys**: landed (checks 1/3/4/5 prove the API + web images; worker + Lambda assumed per the deploy order — the Check 6 DB query below is the proof).

**Checks**:

- **Check 1 (board)**: ✅ **PASS** — office1 sees the full dispatch board; accountant has no Schedule nav item at all (grant truth as designed).
- **Check 2 (tech box)**: ⚠️ **FUNCTIONAL PASS + Tom ruling reverses the design** — accountant: no "Failed to load technicians" error and no data leak (gates work); the job detail page still renders a bare **"Technicians" header** with no content — root cause: `JobDetailPage.tsx` renders the `<h4>` **outside** the gated `TechAssignmentSection` (the section correctly returns null; the parent header doesn't). office1 sees the real assigned tech. **Tom ruled 2026-09-06: "the accountant should be able to view jobs including what techs have been assigned"** → the section-hidden outcome is superseded by a grant widening → **INV-BUG-18 → PLP-FIX-11 (Ord 32)**: seed-grant accountant `schedule.view_all` (read-only; picker stays `schedule.manage`; side effect = Schedule nav + read-only board) + gate the bare header.
- **Check 3 (checklist)**: ✅ **PASS** — owner: Hide → Show expands and persists (checklist shows for the owner only — expected: onboarding widget).
- **Check 4 (tables)**: ✅ **PASS** — pending-invites table shows all columns; horizontal scroll when content exceeds the viewport.
- **Check 5 (link gate)**: ✅ **PASS** — no Generate-&-Copy-Link for accountant; owner retains all buttons.
- **Check 6 (session history)**: ❌ **UI DOES NOT EXIST — plan error (architect design-verification miss)** — `GET /api/v1/users/me/session-history` has **zero frontend consumers**; the Security page's "Active Sessions" card/page is A70 (`user_session_metadata` — a different, separately-deferred feature). The prompt's "the existing Security page renders it" was never true. **Tom ruled 2026-09-06**: add session history to the Active Sessions UI in a **future batch** → SESSION-HISTORY-UI-1 (launch plan §6c). The Part A wiring is therefore verified **DB-only**:

```sql
PSQL "SELECT user_id, total_session_count, first_login_at, last_login_at FROM public.user_session_history ORDER BY last_login_at DESC LIMIT 5;"
-- expect: rows for the users signed in during this run (owner/office1/accountant), total_session_count ≥ 1, last_login_at ≈ sign-in times
-- 0 rows → worker image (0.2) or Post-Auth Lambda redeploy (0.3) didn't land; check worker logs for record_user_login
```

**Outcome — gate flip pending one DB query.** Checks 1/3/4/5 green; check 2 → PLP-FIX-11 per Tom's ruling; check 6 → UI deferred per Tom, BE wiring awaiting the row-count confirmation above. On rows present: **Ord 27 (TEAM-INVITE-2) ✅ + §7 invite gate ✅** flip in the next launch-plan version; tracker INV-BUG-10/13/14/15/16 CLOSED (done 2026-09-06), INV-BUG-17 closes (BE half), INV-BUG-18 stays open → PLP-FIX-11.
