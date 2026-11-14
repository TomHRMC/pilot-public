# Implementation Prompt: MKT-B9 Part B — Waitlist Form Fields + Hero Copy + Trade Page Fixes (React)

**Mode**: Pilot React Engineer
**Batch**: MKT-B9-B
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b9-design-spec.md`
**Estimated session**: 2–3 hours
**Platform**: Marketing site only (`frontend/apps/marketing/`)
**Backend companion**: MKT-B9-A (Python Engineer) — **must be complete before this batch starts**
**Pure frontend — no backend changes in this part**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b9-design-spec.md`** — every section (A–H)

Critical rules for this batch:

- **MKT-B9-A must be complete first**: Verify `state` and `notes` appear in `backend/openapi_schema_map.md` before touching any frontend file. If they don't appear → STOP and wait for the Python Engineer handoff.
- **Marketing app only**: Touch ONLY `frontend/apps/marketing/`. Do NOT modify `apps/web/`, `apps/mobile/`, or `packages/ui/`.
- **No `pnpm sync-api-types`**: Marketing site does not use `@pilot/shared-types`. Skip entirely.
- **No test suite**: Marketing has zero tests. Phase 2 verification is build + lint only.
- **`WaitlistForm.tsx` is a `"use client"` component**: It already has `"use client"` at the top. Do not remove it. State dropdown and notes textarea are new controlled inputs — follow the exact same state + handler pattern as the existing fields.
- **CSS token verification**: Before using any `var(--*)` token in new JSX, confirm it exists in `src/app/globals.css`. The state dropdown styling is copied directly from the existing trade dropdown — use the exact same inline style object.
- **Early-access hero copy is verbatim**: Tom's exact two-paragraph text must be reproduced character-for-character. Do not paraphrase or reformat. Escape all apostrophes as `&apos;` in JSX.
- **TradePageTemplate fixes all 3 trade pages at once**: The "Free 14-day trial" text lives in `TradePageTemplate.tsx`. One change there affects electrical, plumbing, and HVAC simultaneously. Do NOT edit the individual trade page files for this CTA text fix.
- **Rule 8**: No new npm packages.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome | Rationale |
|---|---|---|
| `state` field required on client | Yes — form validates selection before submit | Geographic data critical for Stage 1 Mid-Atlantic outreach targeting |
| `state` field required on backend | No — optional/nullable | Protects other forms (HeroWaitlistForm, newsletter) that don't send this field |
| State dropdown value format | State abbreviation + special values: "DC", "PR", "Outside the US" | Consistent with how other lookup-style fields work |
| Notes field position | After company size fieldset, before submit button | Last optional field before CTA — correct UX placement |
| Notes trimming before send | `notes.trim() \|\| undefined` — omit if empty | Avoids storing blank strings; backend receives `null` cleanly |
| Hero copy | Tom's exact 2-paragraph text | Verbatim — see design doc §E.2 |
| Trade CTA footer text | "No credit card required · Take 10 seconds" | Matches WaitlistForm.tsx existing footer text; removes stale trial language |

---

## Pre-Work: Verify MKT-B9-A Handoff Complete

Before touching any frontend file, confirm the Python Engineer handoff is done:

```bash
grep -A 10 "waitlist" backend/openapi_schema_map.md | grep -E "state|notes"
```

Expected output: lines showing `state` and `notes` as optional fields in the waitlist request schema. If not found → **STOP. Do not proceed until MKT-B9-A is complete.**

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -5
# Expected: 0 tests (no marketing test suite)
```

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/marketing/src/components/forms/WaitlistForm.tsx
  ← Read in full — understand existing state vars, validateWaitlist function,
    handleSubmit body, trade dropdown styling (copy for state dropdown),
    and the layout order of all existing fields

frontend/apps/marketing/src/app/early-access/page.tsx
  ← Understand the hero section structure — where the subtitle <p> lives,
    what className it has, and what spacing classes are applied

frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx
  ← Find the exact "Free 14-day trial" string — search for it. Understand
    the full template structure before changing anything.

frontend/apps/marketing/src/app/trades/electrical/page.tsx
  ← Find pricingBodyCopy prop and the FAQ at index 3 (the $149 reference)

frontend/apps/marketing/src/app/trades/plumbing/page.tsx
  ← Check for any $149/month references

frontend/apps/marketing/src/app/trades/hvac/page.tsx
  ← Check for any $149/month references

frontend/apps/marketing/src/app/globals.css
  ← Confirm var(--divider-thin), var(--neutral-200), var(--brand-600),
    var(--white), var(--neutral-900), var(--neutral-400) all exist
    (they do — used extensively already, just confirm before using in new JSX)
```

Also run:

```bash
# Confirm TradePageTemplate location and confirm it's a shared file:
find frontend/apps/marketing/src/components/trades -name "*.tsx"

# Find "Free 14-day trial" string location:
grep -rn "Free 14-day trial\|14-day\|trial" frontend/apps/marketing/src/ --include="*.tsx"
```

---

## Context: What This Batch Does

| # | Change | File | Type |
|---|---|---|---|
| 1 | Add state dropdown + notes textarea + updated validation + updated submit body | `src/components/forms/WaitlistForm.tsx` | Update |
| 2 | Replace hero subtitle with Tom's 2-paragraph text | `src/app/early-access/page.tsx` | Update |
| 3 | Fix "Free 14-day trial" → "No credit card required · Take 10 seconds" | `src/components/trades/TradePageTemplate.tsx` | Update |
| 4 | Fix 2 stale $149/month references | `src/app/trades/electrical/page.tsx` | Update |
| 5 | Fix any stale pricing references (check only) | `src/app/trades/plumbing/page.tsx` | Update if needed |
| 6 | Fix any stale pricing references (check only) | `src/app/trades/hvac/page.tsx` | Update if needed |

---

## STEP 1 — Update `WaitlistForm.tsx`

**File**: `frontend/apps/marketing/src/components/forms/WaitlistForm.tsx`

Read the full file before editing. This is a `"use client"` component — do not remove that directive.

### 1.1 — Add US states constant (at the top of the file, after imports)

Add the full `US_STATES` array before the `EMAIL_REGEX` constant. The exact array data is in design doc §E.1. It must include all 50 states + DC + PR + "Outside the US" as the final option.

```typescript
const US_STATES = [
  { value: "AL", label: "Alabama" },
  // ... (full list from design doc §E.1) ...
  { value: "Outside the US", label: "Outside the US" },
];
```

### 1.2 — Update `validateWaitlist` function

Add `state` as a 5th parameter and add validation for it:

```typescript
function validateWaitlist(
  name: string,
  email: string,
  trade: string,
  companySize: string,
  state: string,
): string | null {
  if (!name.trim()) return "Please enter your name.";
  if (!email.trim()) return "Please enter your email address.";
  if (!EMAIL_REGEX.test(email.trim()))
    return "Please enter a valid email address.";
  if (!trade) return "Please select your trade.";
  if (!companySize) return "Please select your team size.";
  if (!state) return "Please select your location.";
  return null;
}
```

### 1.3 — Add state + notes state variables to `WaitlistFields`

Add after the existing `companySize` state variable:

```typescript
const [state, setState] = useState("");
const [notes, setNotes] = useState("");
```

### 1.4 — Update `validateWaitlist` call in `handleSubmit`

```typescript
const validationError = validateWaitlist(name, email, trade, companySize, state);
```

### 1.5 — Update submit body in `handleSubmit`

Add `state` and `notes` to the JSON body:

```typescript
body: JSON.stringify({
  name: trimmedName,
  email: trimmedEmail,
  trade,
  company_size: companySize,
  state,                              // required, validated above
  notes: notes.trim() || undefined,   // optional — omit if empty
  source: source ?? "early_access_page",
  cf_turnstile_response: turnstileToken,
  honeypot,
  ...utmRef.current,
}),
```

### 1.6 — Add state dropdown JSX

Insert the state dropdown **after the trade `<div>`** and **before the `<fieldset>` for company size**.

Use the exact same inline style object as the existing trade dropdown. Copy the `onFocus`/`onBlur` handlers verbatim. The only differences are: `id="wl-state"`, `value={state}`, `onChange={(e) => setState(e.target.value)}`, placeholder text, and the options rendered from `US_STATES`.

Label: `Your state` with required asterisk.

See design doc §E.1 for the full JSX.

### 1.7 — Add notes textarea JSX

Insert **after the company size `<fieldset>`** and **before the `{status === "error" && errorMsg && <FormErrorAlert .../>}` line**.

```tsx
{/* Notes (optional) */}
<div>
  <label
    htmlFor="wl-notes"
    className="block text-sm font-medium mb-1"
    style={{ color: "var(--neutral-700)" }}
  >
    Anything you want me to know?{" "}
    <span className="font-normal" style={{ color: "var(--neutral-400)" }}>
      (optional)
    </span>
  </label>
  <textarea
    id="wl-notes"
    value={notes}
    onChange={(e) => setNotes(e.target.value)}
    placeholder="Tell me about your business, what you're struggling with, or anything else."
    rows={3}
    className="w-full px-4 py-3 rounded-lg text-base resize-y"
    style={{
      border: "var(--divider-thin) solid var(--neutral-200)",
      background: "var(--white)",
      color: "var(--neutral-900)",
      outline: "none",
      minHeight: "80px",
    }}
    onFocus={(e) =>
      (e.currentTarget.style.borderColor = "var(--brand-600)")
    }
    onBlur={(e) =>
      (e.currentTarget.style.borderColor = "var(--neutral-200)")
    }
  />
</div>
```

**Intermediate verification** after Step 1:
```bash
cd <repo>/frontend
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10
```
Fix any TypeScript errors before Step 2.

---

## STEP 2 — Update `early-access/page.tsx` Hero Subtitle

**File**: `frontend/apps/marketing/src/app/early-access/page.tsx`

Read the file before editing. Find the hero subtitle — it is a `<p>` element directly below the `<h1>` in the hero section.

Replace the current single subtitle `<p>` with two `<p>` elements containing Tom's exact text. Escape all apostrophes as `&apos;`.

**Paragraph 1** (use `text-section-subtitle` class, `mb-6` spacing):

> I&apos;m building Pilot myself. I&apos;m an electrician&apos;s son, and I spent over 15 years on electrical and instrumentation teams in manufacturing before moving into software. I need a small number of electrical contractors willing to run it on real jobs and tell me what I got wrong. No trial period, no complicated setup — six months free, then $49/month locked in for as long as you stay.

**Paragraph 2** (use `text-base` class, `mb-10` spacing — preserves gap before form card):

> Here&apos;s the honest part: Pilot isn&apos;t fully built yet. I&apos;m targeting end of summer for it to be ready for real, everyday use. If you sign up now, you&apos;re getting in before that — which means some rough edges, and it means I&apos;m going to ask a lot of you: a weekly call with me (15-20 minutes, your schedule), actually running it on real jobs once it&apos;s ready, and telling me the second something breaks or doesn&apos;t make sense — not just the big stuff, the small annoying stuff too. In exchange, you get six months free and a price that never goes up, ever, for you. I&apos;ll review every signup myself, and I&apos;ll reach out personally before we get started.

Both paragraphs use `style={{ color: "var(--white-8)" }}` — matching the existing hero subtitle color.

---

## STEP 3 — Fix Trade Page CTA Footer Text

**File**: `frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx`

Read the full file. Search for the string "Free 14-day trial" (or "14-day") and find its exact location. Replace the text with:

```
No credit card required · Take 10 seconds
```

This fix applies to every trade page (electrical, plumbing, HVAC) because they all use this shared template. Do NOT make this change in the individual trade page files.

**Intermediate verification** after Step 3:
```bash
pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10
pnpm --filter marketing build 2>&1 | tail -15
```

---

## STEP 4 — Fix Stale $149/Month Pricing References on Trade Pages

**File 1**: `frontend/apps/marketing/src/app/trades/electrical/page.tsx`

Two changes:

**Change 1** — `pricingBodyCopy` prop:
```typescript
// BEFORE:
pricingBodyCopy="Starting at $149/month. One platform for quoting, ..."

// AFTER:
pricingBodyCopy="$49/month, everything included. One platform for quoting, dispatch, invoicing, profitability tracking, and QuickBooks sync. Saves 15+ hours per week in admin time — that's $750+ worth of billable hours back in your pocket."
```

**Change 2** — FAQ at index 3 (`answer` field, the one that says "Starter plan ($149/mo)"):
```typescript
// BEFORE:
answer: "It's built for you. Pilot's Starter plan ($149/mo) is designed for solo..."

// AFTER:
answer: "It's built for you. Pilot is $49/month, everything included — designed for solo and small electrical contractors. You're the exact person losing 15 hours a week to admin because you don't have an office manager. Pilot is your digital office manager — except it never calls in sick."
```

**File 2**: `frontend/apps/marketing/src/app/trades/plumbing/page.tsx`

Search for `$149` or `$149/mo` or `Starter plan`. If found, update to `$49/month, everything included`. If not found, no change needed — document this in the completion summary.

**File 3**: `frontend/apps/marketing/src/app/trades/hvac/page.tsx`

Same check as plumbing. Update any stale pricing references.

---

## Final Verification

### Phase 1 — Targeted checks (run after each step)

```bash
cd <repo>/frontend

pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -10
pnpm --filter marketing build 2>&1 | tail -20
pnpm --filter marketing lint 2>&1 | tail -10
```

### Phase 2 — Full canonical verification (run once at the end)

```bash
cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit && pnpm --filter marketing build && pnpm --filter marketing lint && echo "=== MKT-B9-B FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MKT-B9-B

- [ ] MKT-B9-A handoff verified — `state` and `notes` confirmed in `openapi_schema_map.md` before starting
- [ ] Baseline captured (0 tests — marketing has no test suite)
- [ ] All source files read before writing any code
- [ ] **STEP 1**: `WaitlistForm.tsx` updated:
  - [ ] `US_STATES` constant added with all 50 states + DC + PR + "Outside the US"
  - [ ] `validateWaitlist` function updated — `state` added as required 5th parameter
  - [ ] `state` + `notes` state variables added to `WaitlistFields`
  - [ ] `validateWaitlist` call in `handleSubmit` passes 5 arguments
  - [ ] Submit body includes `state` + `notes: notes.trim() || undefined`
  - [ ] State dropdown inserted after trade dropdown, before company size fieldset
  - [ ] Notes textarea inserted after company size fieldset, before error alert
  - [ ] TypeScript compiles clean after Step 1
- [ ] **STEP 2**: `early-access/page.tsx` updated — hero subtitle replaced with 2-paragraph Tom text (verbatim, apostrophes escaped)
- [ ] **STEP 3**: `TradePageTemplate.tsx` updated — "Free 14-day trial" → "No credit card required · Take 10 seconds"
- [ ] **STEP 4**: `electrical/page.tsx` — `pricingBodyCopy` updated to $49/month + FAQ index 3 updated
- [ ] **STEP 4**: `plumbing/page.tsx` — checked for stale $149 references (updated or confirmed clean)
- [ ] **STEP 4**: `hvac/page.tsx` — checked for stale $149 references (updated or confirmed clean)
- [ ] Zero TypeScript errors (`tsc --noEmit` passes)
- [ ] Zero ESLint warnings (`lint` passes)
- [ ] Build passes (`pnpm --filter marketing build` succeeds)
- [ ] Manually verified in browser (dev server): WaitlistForm shows state dropdown and notes textarea; early-access hero shows 2-paragraph Tom text; trade pages show "No credit card required · Take 10 seconds"
- [ ] **Phase 2 FULL verification passes** (`=== MKT-B9-B FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit && pnpm --filter marketing build && pnpm --filter marketing lint && echo "=== MKT-B9-B FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Completion Summary added to `pilot-launch-plan.md` §P0

---

## Completion Summary

After all DoD items pass, add to `dev-docs/analysis/pilot-launch-plan.md` §P0:

```markdown
### MKT-B9-B — Waitlist Form Fields + Hero Copy + Trade Page Fixes (React): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: 0 tests (no marketing test suite)
**Final**: 0 tests (out of scope)
**Build**: ✅ Pass — TypeScript errors: 0, ESLint warnings: 0

#### What Was Accomplished
- `WaitlistForm.tsx`: state dropdown (50 US states + DC + PR + "Outside the US") added as required field; notes textarea added as optional field; validateWaitlist updated; submit body updated
- `early-access/page.tsx`: hero subtitle replaced with Tom's 2-paragraph founder text (verbatim)
- `TradePageTemplate.tsx`: "Free 14-day trial" → "No credit card required · Take 10 seconds" (fixes all 3 trade pages)
- `electrical/page.tsx`: pricingBodyCopy + FAQ index 3 updated from $149/month to $49/month
- `plumbing/page.tsx`: [updated / no changes needed — document which]
- `hvac/page.tsx`: [updated / no changes needed — document which]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/marketing/src/components/forms/WaitlistForm.tsx` | Updated — US_STATES, state dropdown, notes textarea, updated validation and submit |
| `frontend/apps/marketing/src/app/early-access/page.tsx` | Updated — 2-paragraph hero subtitle |
| `frontend/apps/marketing/src/components/trades/TradePageTemplate.tsx` | Updated — CTA footer text |
| `frontend/apps/marketing/src/app/trades/electrical/page.tsx` | Updated — pricingBodyCopy + FAQ pricing |
| `frontend/apps/marketing/src/app/trades/plumbing/page.tsx` | [Updated / No change] |
| `frontend/apps/marketing/src/app/trades/hvac/page.tsx` | [Updated / No change] |
```
