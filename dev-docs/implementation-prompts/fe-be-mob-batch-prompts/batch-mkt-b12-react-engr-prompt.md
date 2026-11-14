# Implementation Prompt: MKT-B12 — Marketing Site Charter-Consistency & Team-Voice Copy Overhaul

**Mode**: Pilot React Engineer
**Batch**: MKT-B12 (Part 2 of 2 — implementation)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b12-design-spec.md` — Tom-approved 2026-08-08; contains the complete 32-item copy-change manifest (§B)
**Designer dependency**: The Marketing UI Designer's review memo (`## Designer Review — MKT-B12` section appended to the design doc) must show **APPROVED** (or amendments Tom-approved) before you start. If the memo is missing → STOP and ask Tom.
**Estimated session**: 2–3 hours
**Platform**: Marketing app only (`frontend/apps/marketing/`) — copy-only; zero component, layout, styling, or API changes
**Backend companion**: none

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b12-design-spec.md`** — every section (A–G + Designer Review memo). The §B manifest is your work order.

**Critical rules for this batch:**

- **Copy fidelity**: Implement the §B replacement strings **exactly** as written — they are Tom-approved and, for items 2/3/17, legally aligned with the Terms page D22/D24 clause. Do not "improve" wording. If a string looks wrong in context → STOP and ask Tom.
- **Scope discipline**: Copy-only. No layout changes, no new components, no CSS changes, no new dependencies, no refactors. If a replacement would break JSX structure → STOP and ask Tom.
- **Do not touch** (design doc §A "Out of scope"): `about/page.tsx` founder message first-person voice; legal "90 days" retention clauses; blog editorial time references; `pricing-preview/page.tsx`; `pricing-general-release/page.tsx`; the `/api/v1/marketing/waitlist` endpoint string in fetch calls (backend contract unchanged — only user-visible copy changes).
- **Marketing app conventions** (from MKT-B11): the marketing app does **not** use `apiClient` / `@pilot/shared-api`; it uses `fetch()` directly and CSS variables from `globals.css`. You should not need either in this batch — no fetch or style changes.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — fix it before declaring the batch done. If you cannot identify the root cause → STOP and ask Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -5
pnpm --filter marketing build 2>&1 | tail -5   # type-check + static build
```

Record the exact counts. These must still pass at the end of the batch. If tests are already failing → do NOT proceed; confirm with Tom or fix first.

## Pre-Work: Read These Source Files

Read each with `read_file` before editing it (line numbers in the manifest are from 2026-08-08 — verify before editing; files may have shifted):

```
frontend/apps/marketing/src/app/charter/page.tsx                    ← items 21–31 (bulk of batch)
frontend/apps/marketing/src/app/pricing/page.tsx                    ← items 1–3 (charterFaqs)
frontend/apps/marketing/src/app/about/page.tsx                      ← item 7 ONLY — do not touch founder message
frontend/apps/marketing/src/app/features/page.tsx                   ← items 11, 19, 20
frontend/apps/marketing/src/app/contact/page.tsx                    ← item 12
frontend/apps/marketing/src/app/legal/privacy/page.tsx              ← item 17 (legal doc — exact strings only)
frontend/apps/marketing/src/app/trades/electrical/page.tsx          ← item 8
frontend/apps/marketing/src/app/trades/hvac/page.tsx                ← item 9
frontend/apps/marketing/src/app/trades/plumbing/page.tsx            ← item 10
frontend/apps/marketing/src/components/forms/CharterApplicationForm.tsx ← items 15, 32
frontend/apps/marketing/src/content/blog/product/introducing-pilot-for-trades.mdx ← items 4–6
frontend/apps/marketing/src/content/blog/hvac/hvac-bidding-ai-2026.mdx          ← item 13
frontend/apps/marketing/src/content/blog/electrical/voice-quoting-for-electricians.mdx ← item 14
```

## Pre-Work: Verify No Other Instances

Run these greps before starting and again after finishing — the "after" runs must return zero hits (excluding the explicit out-of-scope list):

```bash
cd <repo>/frontend/apps/marketing/src

grep -rn --include="*.tsx" --include="*.mdx" -iE "6 months free|six months free|3 months free|Beta Founder" .
grep -rn --include="*.tsx" --include="*.mdx" -iE "join the waitlist|on the waitlist" .
grep -rn --include="*.tsx" -E "Works on 3G|SOC 2 roadmap" .
grep -rn --include="*.tsx" -E "Tom reviews|Tell me |I set it up myself|Direct line to Tom|I'm one guy" .
```

Expected residual hits after implementation (allowed): `/api/v1/marketing/waitlist` fetch URLs, code comments referencing the WaitlistForm rename history, item 16 ("Charter Crew" — kept), item 18 ("not a waitlist" contrast — kept), `about/page.tsx` founder first-person voice.

---

## Implementation

Work the manifest in file order (group edits per file to minimize churn):

1. `charter/page.tsx` — items 21–31 (11 edits, the largest block; includes the bio-callout rewrite, item 26)
2. `pricing/page.tsx` — items 1–3 (both in `charterFaqs`; note the same strings render into the FAQ JSON-LD — no separate change needed, it derives from the same array)
3. Trade pages ×3 — items 8–10 (`finalCtaHeadline` props only; `finalCtaBody` already says "Be one of the first twelve" — leave it)
4. `features/page.tsx` — items 11, 19, 20 (item 20 is a bullet **removal** — delete the array element cleanly, no dangling comma)
5. `contact/page.tsx` — item 12
6. `about/page.tsx` — item 7 only
7. `legal/privacy/page.tsx` — item 17 (heading + first body sentence only; do not alter any other legal text)
8. `CharterApplicationForm.tsx` — items 15, 32
9. Blog MDX ×3 — items 4–6, 13, 14

**JSX escaping**: the marketing codebase uses `{"'"}` / `'` conventions for apostrophes in JSX text. Match the surrounding file's existing convention exactly (check how neighboring strings escape `'` before writing yours). MDX files use plain markdown — no escaping needed.

## Test Requirements

No new components or hooks → no new test files required. You MUST, however:

1. **Update existing tests** that assert old copy. Check at minimum:
   - `src/components/__tests__/PricingCharterCallout.test.tsx`
   - `src/components/__tests__/CharterAvailabilityBadge.test.tsx` (expected no impact — verify)
   - Any test matching: `grep -rn -iE "waitlist|6 months|3G|SOC 2|Tell me|Tom reviews" apps/marketing/src --include="*.test.tsx"`
2. **Add one lightweight content-guard test** (new file `src/app/__tests__/charter-copy.test.tsx` or extend the nearest existing page test): render `/charter` and assert (a) "Charter program is" team-voice copy present — e.g. `screen.getByText(/reviewed personally by our team/i)`, and (b) `screen.queryByText(/Tom reviews/i)` is null. This guards the two highest-risk regressions (legal-alignment strings are covered by existing pricing tests if present — extend them to assert "90 days free" and the forfeiture clause if trivially possible; do not force it if the FAQ isn't rendered in the existing test's scope).

## Final Verification Gate

**Phase 1 — targeted:**
```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -5
```

**Phase 2 — full (must pass before declaring done):**
```bash
pnpm --filter marketing build 2>&1 | tail -10   # tsc + Next static build must succeed
pnpm --filter marketing test 2>&1 | tail -5     # full marketing suite green
```
Plus the four "after" greps above returning zero non-allowed hits.

## Definition of Done

- [ ] All 32 manifest items implemented exactly as specified (or per Tom-approved designer amendments)
- [ ] Items marked "No change" (16, 18) verified untouched
- [ ] Out-of-scope list respected (about-page voice, legal retention clauses, preview pages, endpoint names)
- [ ] Existing tests updated for new copy; content-guard test added
- [ ] Phase 1 targeted tests pass
- [ ] Phase 2 full build + suite passes; zero new lint/type errors
- [ ] Post-implementation greps clean (allowed residuals only)
- [ ] No dependency, styling, component, or API changes of any kind

## Handoff Note

This batch fixes the **repo** copy. The **deployed** marketing site is a stale pre-C-B1 build (see design doc §A) — after merge, Tom verifies the deployed site. Flag in your completion summary if you notice anything in the repo suggesting the deploy pipeline for marketing is manual.

## Completion Summary

When finished, report in this exact format:

```
## MKT-B12 Completion Summary
- Manifest items implemented: N/32 (list any deviations + why)
- Files changed: [list]
- Tests updated: [list]; content-guard test added: [path]
- Test counts: baseline X → final Y (marketing); build: PASS/FAIL
- Grep verification: clean / [residuals listed with justification]
- Deviations from spec: [none / describe]
- Deploy-pipeline observations: [any]
```
