# Implementation Prompt: MKT-B6 Part B — Careers Page Redesign + Form Updates

**Mode**: `pilot-react-engineer`
**Batch**: MKT-B6 Part B
**Plan link**: `dev-docs/analysis/pilot-launch-plan.md` — P0 section
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b6-design-spec.md`
**Estimate**: 2–3 hours
**Platform**: Marketing website only (`frontend/apps/marketing/`)
**Backend companion**: MKT-B6 Part A (Python Engineer) — **must be complete first**. React Engineer's first step is `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/marketing-analysis/design-specs/mkt-b6-design-spec.md`** — every section (A–H)

**Critical rules for this batch:**

- **Rule 8**: No new npm dependencies. `TurnstileProtectedForm` already handles Turnstile. Zero new packages.
- **Rule 10**: Fix any test failure before declaring done.
- **Marketing app scope**: ALL changes confined to `frontend/apps/marketing/`. Do NOT touch `apps/web`, `apps/mobile`, or any `packages/` directory.
- **Backend-first dependency**: MKT-B6 Part A (Python Engineer) must be complete before this batch starts. `pnpm sync-api-types` MUST run before any hook or form POST is written.
- **`NEXT_PUBLIC_CAREERS_OPEN_ROLES` fallback**: If this env var is missing or empty, the role dropdown must still render using the hardcoded default array (never crash).
- **No invented endpoint shapes**: Verify `POST /api/v1/marketing/application` exists in `backend/openapi_schema_map.md` before writing the form POST. If it does not appear → STOP and ask Tom.
- **Careers page full replacement**: The "Open Roles" section and the bottom WaitlistForm CTA are both being replaced. Do not preserve the old mailto link or the WaitlistForm at the bottom of the careers page.

---

## What This Batch Does

Five tasks. All confined to `frontend/apps/marketing/`.

| Task | File | Change |
|---|---|---|
| B-01 | `frontend/apps/marketing/.env.example` | Add `NEXT_PUBLIC_CAREERS_OPEN_ROLES` |
| B-02 | `src/components/forms/WaitlistForm.tsx` | Add optional `name` field |
| B-03 | `src/components/HeroWaitlistForm.tsx` | Add optional `name` field |
| B-04 | `src/components/forms/ApplicationForm.tsx` | Create new careers application form component |
| B-05 | `src/app/careers/page.tsx` | Full redesign with role cards + embedded `ApplicationForm` |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -8
```

Record exact counts. These must still pass at end.

---

## Pre-Work: Sync API Types (MANDATORY — run before writing any form POST code)

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates TypeScript types from the backend OpenAPI spec updated in MKT-B6 Part A.

> **If `pnpm sync-api-types` fails** because the backend changes aren't deployed → note the endpoints, write the POST bodies manually with inline types, and mark as `// TODO: delete when pnpm sync-api-types delivers this type`.

---

## Pre-Work: Verify Endpoints

Verify both endpoints exist before writing any form code:

```bash
grep -A 5 "marketing/application" backend/openapi_schema_map.md
grep -A 5 "marketing/waitlist" backend/openapi_schema_map.md
```

**If `/marketing/application` does NOT appear** → MKT-B6 Part A is not complete. STOP. Do not implement the `ApplicationForm` without a confirmed backend endpoint.

Confirmed endpoints for this batch:
| Endpoint | Method | Verified |
|---|---|---|
| `POST /api/v1/marketing/application` | POST | Confirm in openapi_schema_map.md |
| `POST /api/v1/marketing/waitlist` | POST (existing, name field added) | Confirm name field in schema |

---

## Pre-Work: Read These Source Files

```
frontend/apps/marketing/src/components/forms/WaitlistForm.tsx
  ← Full file — understand field structure and POST body before adding name

frontend/apps/marketing/src/components/HeroWaitlistForm.tsx
  ← Full file — understand compact form layout before adding name

frontend/apps/marketing/src/components/forms/ContactForm.tsx
  ← Full file — pattern reference for ApplicationForm (TurnstileProtectedForm usage, error handling, success state)

frontend/apps/marketing/src/components/forms/TurnstileProtectedForm.tsx
  ← Understand useTurnstileProtection() hook and SubmitSpinner, FormErrorAlert exports

frontend/apps/marketing/src/app/careers/page.tsx
  ← Full file — understand existing structure before replacing Open Roles section
```

---

## Task B-01 — Frontend Env Var

**File**: `frontend/apps/marketing/.env.example`

Add:
```
# MKT-B6: Comma-separated list of open job roles for the careers form dropdown.
# Update without a code deploy by changing NEXT_PUBLIC_CAREERS_OPEN_ROLES in .env
NEXT_PUBLIC_CAREERS_OPEN_ROLES="AI / ML Engineer,Full-Stack Engineer (Trades Domain),Customer Success (Trades Background a Plus),Sales / Growth"
```

---

## Task B-02 — WaitlistForm: Add Optional Name Field

**File**: `frontend/apps/marketing/src/components/forms/WaitlistForm.tsx`

Read the full file first. Add an optional `name` text input as the **first field** in the form (before email). Label: "Your Name (optional)".

```tsx
<div>
  <label
    htmlFor="waitlist-name"
    className="block text-sm font-medium mb-1"
    style={{ color: "var(--neutral-700)" }}
  >
    Your Name <span className="text-xs font-normal" style={{ color: "var(--neutral-400)" }}>(optional)</span>
  </label>
  <input
    id="waitlist-name"
    type="text"
    value={name}
    onChange={(e) => setName(e.target.value)}
    placeholder="Your name"
    className="w-full px-4 py-3 rounded-lg text-base"
    style={{ border: "1px solid var(--neutral-200)", background: "var(--white)", color: "var(--neutral-900)", outline: "none" }}
    autoComplete="name"
  />
</div>
```

Add `name` state: `const [name, setName] = useState("")`

Update POST body to include: `name: name || undefined` (don't send empty string — backend accepts `null`/`undefined`).

---

## Task B-03 — HeroWaitlistForm: Add Optional Name Field

**File**: `frontend/apps/marketing/src/components/HeroWaitlistForm.tsx`

Read the full file first. The hero form is compact (single-row email + button). Add name as a **full-width row above** the email+button row. Same optional label pattern as B-02. Keep the email + button on the same row.

POST body: include `name: name || undefined`.

---

## Task B-04 — New ApplicationForm Component

**File**: `frontend/apps/marketing/src/components/forms/ApplicationForm.tsx`

New `"use client"` component. Use `TurnstileProtectedForm` as the wrapper (same pattern as `ContactForm`). Export as default.

**Fields in order**:
1. Full Name (required, `type="text"`, `autoComplete="name"`)
2. Email Address (required, `type="email"`, `autoComplete="email"`)
3. Role Applying For (required `<select>` — options from `process.env.NEXT_PUBLIC_CAREERS_OPEN_ROLES?.split(",") ?? DEFAULT_ROLES`)
4. **LinkedIn Profile URL (REQUIRED, `type="url"`, placeholder `https://linkedin.com/in/your-name`)** — label: `LinkedIn Profile URL *` — required attr + validation that value is non-empty before submit
5. Portfolio / GitHub / Personal Site URL (optional, `type="url"`, placeholder `https://github.com/your-handle`) — label: `Portfolio / GitHub / Personal Site URL`
6. Why are you interested in joining our team? (required `<textarea>`, maxLength 2000, show `{whyInterested.length}/2000` counter — same pattern as ContactForm)

```tsx
// Default roles — fallback if env var is missing
const DEFAULT_ROLES = [
  "AI / ML Engineer",
  "Full-Stack Engineer (Trades Domain)",
  "Customer Success (Trades Background a Plus)",
  "Sales / Growth",
];

const OPEN_ROLES =
  process.env.NEXT_PUBLIC_CAREERS_OPEN_ROLES?.split(",").map((r) => r.trim()).filter(Boolean) ??
  DEFAULT_ROLES;
```

**POST target**: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/marketing/application`

**POST body**:
```typescript
{
  name,
  email,
  role,
  linkedin_url: linkedinUrl,         // required — never null; validated before submit
  portfolio_url: portfolioUrl || null, // optional — null if empty
  why_interested: whyInterested,
  source_page: "/careers",
  cf_turnstile_response: turnstileToken ?? "",
  honeypot,
}
```

**Success state**: Replace form with confirmation card (same green card pattern as ContactForm):
```
✓ Application received!
We review every application personally. If it's a fit, you'll hear from us at [applicant email].
```

**Error state**: `<FormErrorAlert message={errorMsg} />` (same as ContactForm).

**Styling**: Match `ContactForm` exactly — same input styles, same focus handlers, same `btn-primary` submit button, same disabled state on submit.

---

## Task B-05 — Careers Page Redesign

**File**: `frontend/apps/marketing/src/app/careers/page.tsx`

Read the full file first. Keep: Hero section, "The Problem We're Solving", culture/values grid, "The Honest Version" section. Replace everything after "The Honest Version" section with the new content below.

**New imports to add at top**:
```tsx
import ApplicationForm from "../../components/forms/ApplicationForm";
```

**Remove**:
- The entire "Open Roles" section (currently has `mailto:careers@pilotfortrades.com` link + `anticipatedRoles` list)
- The bottom WaitlistForm CTA section (the blue section with `<WaitlistForm source="careers_page" />`)
- The `import WaitlistForm` statement (no longer needed)
- The `anticipatedRoles` array constant

**Add — Two new sections (Open Roles + Application Form)**:

```tsx
{/* Open Roles */}
<section
  className="section-padding"
  style={{ background: "var(--surface-marketing-alt)" }}
  aria-labelledby="openroles-heading"
>
  <div className="container-marketing max-w-4xl mx-auto">
    <h2
      id="openroles-heading"
      className="text-section-title mb-6"
      style={{ color: "var(--neutral-900)" }}
    >
      Open Roles
    </h2>
    <p className="text-body-lg mb-12" style={{ color: "var(--neutral-700)" }}>
      We are gearing up for our public launch and expanding the core team. If you
      are passionate about building high-impact tools that save solo contractors
      from 9 PM paperwork, we want you on board.
    </p>

    {/* Role cards — no Apply Now buttons; details bullets added */}
    <div className="flex flex-col gap-6">
      {[
        {
          title: "AI / ML Engineer",
          desc: "You will own the brain behind our voice quoting. We need someone who can train models to perfectly understand trade-specific language (from \"Romex\" to \"P-traps\") and calculate complex profitability algorithms in seconds.",
          details: [
            "**Stack:** Python, PyTorch / Hugging Face, Whisper (ASR), Llama 3 (LLM), FastAPI, PostgreSQL + pgvector",
            "**Location:** 100% Remote — US time zones preferred; exceptional candidates considered globally",
            "**You bring:** 3+ years shipping ML/AI in production and a track record of owning the full model lifecycle",
          ],
        },
        {
          title: "Full-Stack Engineer (Trades Domain)",
          desc: "You will build the tools our contractors rely on in the field. This means engineering an offline-first mobile experience, bulletproof dispatch boards, and lightning-fast web interfaces that work flawlessly, even in a basement with spotty cell service.",
          details: [
            "**Stack:** React Native (Expo SDK 54), Next.js 15 (App Router), TypeScript, Python (FastAPI), PostgreSQL, WatermelonDB",
            "**Location:** 100% Remote — US time zones preferred",
            "**You bring:** 4+ years shipping production web and mobile software; offline-first or field-ops experience is a strong plus",
          ],
        },
        {
          title: "Customer Success (Trades Background a Plus)",
          desc: "You are the bridge between our software and the hard-working folks using it. You will help solo plumbers, electricians, and HVAC techs onboard smoothly, troubleshoot their setups, and ensure they are getting their evenings back.",
          details: [
            "**Tools:** Intercom, Slack, video call platforms — no deep technical stack required",
            "**Location:** 100% Remote — US time zones",
            "**You bring:** 2+ years in SaaS customer success or trades industry experience; empathy for field workers is non-negotiable",
          ],
        },
        {
          title: "Sales / Growth",
          desc: "You will lead our go-to-market efforts to get Pilot into the hands of more contractors. We need someone who can speak directly to trade business owners, understand their pain points, and clearly demonstrate the value of our platform.",
          details: [
            "**Tools:** HubSpot or equivalent CRM, LinkedIn Sales Navigator, demo tools",
            "**Location:** 100% Remote — US time zones",
            "**You bring:** 3+ years in SMB SaaS sales with a proven close rate; blue-collar industry experience is a significant advantage",
          ],
        },
      ].map((role) => (
        <div
          key={role.title}
          className="rounded-xl p-6"
          style={{
            background: "var(--white)",
            border: "var(--divider-thin) solid var(--neutral-200)",
          }}
        >
          <h3
            className="text-xl font-semibold mb-2"
            style={{ color: "var(--neutral-900)" }}
          >
            {role.title}
          </h3>
          <p className="text-base mb-4" style={{ color: "var(--neutral-600)" }}>
            {role.desc}
          </p>
          <ul className="flex flex-col gap-1 list-none p-0 m-0">
            {role.details.map((detail, i) => (
              <li
                key={i}
                className="text-sm"
                style={{ color: "var(--neutral-600)" }}
                dangerouslySetInnerHTML={{
                  __html: detail.replace(
                    /\*\*(.+?)\*\*/g,
                    '<strong style="color: var(--neutral-800)">$1</strong>'
                  ),
                }}
              />
            ))}
          </ul>
        </div>
      ))}
    </div>
  </div>
</section>

{/* Visual divider + Application Form */}
<section
  className="section-padding"
  style={{ background: "var(--surface-marketing)" }}
  aria-labelledby="apply-heading"
>
  <div className="container-marketing max-w-2xl mx-auto">
    <h2
      id="apply-heading"
      className="text-section-title mb-3"
      style={{ color: "var(--neutral-900)" }}
    >
      Apply Now
    </h2>
    <p className="text-body-lg mb-8" style={{ color: "var(--neutral-600)" }}>
      Tell us who you are and why this matters to you. We review every application
      personally.
    </p>
    <ApplicationForm />
  </div>
</section>
```

The page now ends with the form section — no blue CTA section at the bottom.

---

## ⚠️ POST-COMPLETION AMENDMENTS — Tasks B-06 + B-07 (Added June 27, 2026)

> **Context**: MKT-B6 Part B is complete. Two small additional tasks are added: (1) client-side email format validation (backend also being fixed in Python A-11, but frontend should validate before even submitting), and (2) UTM parameter capture on the newsletter form so marketing attribution isn't lost. Both are targeted edits to existing files.

---

### Task B-06 — Email Format Validation: Add TLD Guard to All 4 Marketing Forms

**Files**: `ContactForm.tsx`, `WaitlistForm.tsx`, `HeroWaitlistForm.tsx`, `ApplicationForm.tsx`

In every form that has an email input, add this validation check **before the POST is sent** (in the `handleSubmit` function, after checking for honeypot/Turnstile):

```tsx
// Email TLD length guard — browser type="email" allows me@me.t; this catches it
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
if (!EMAIL_REGEX.test(email)) {
  setErrorMsg("Please enter a valid email address (e.g. name@example.com).");
  setStatus("error");
  return;
}
```

Place this check immediately after the Turnstile token check and before `setStatus("submitting")`. The error displays via the existing `<FormErrorAlert>` component — no new UI needed.

---

### Task B-07 — UTM Tracking: Capture URL Parameters in NewsletterForm

**File**: `src/components/forms/NewsletterForm.tsx`

Read the full file first. The form currently sends `utm_source`, `utm_medium`, and `utm_campaign` as `null`/`undefined`. Update the form to:

1. Read UTM params from the URL on mount (`window.location.search`)
2. Fall back to `"website"` / `"organic"` for organic traffic (no UTM on URL)
3. Pass them in the POST body

```tsx
// Add this helper above the component function
function getUtmParams(): { utm_source: string; utm_medium: string; utm_campaign: string | null } {
  if (typeof window === "undefined") {
    return { utm_source: "website", utm_medium: "organic", utm_campaign: null };
  }
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get("utm_source") ?? "website",
    utm_medium: params.get("utm_medium") ?? "organic",
    utm_campaign: params.get("utm_campaign") ?? null,
  };
}
```

In the form's `handleSubmit`, include UTM values in the POST body:
```tsx
const { utm_source, utm_medium, utm_campaign } = getUtmParams();

// In the fetch body:
{
  email,
  source,           // already present (e.g. "footer")
  utm_source,
  utm_medium,
  utm_campaign,
  cf_turnstile_response: turnstileToken ?? "",
  honeypot,
}
```

This ensures every newsletter subscriber has at least `utm_source="website"` and `utm_medium="organic"` recorded — even for direct/organic traffic. External campaigns using proper UTM links will have their full attribution captured automatically.

---

## Two-Phase Final Verification

### Phase 1 — Targeted Tests

```bash
cd <repo>/frontend
pnpm --filter marketing test 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B6-B FINAL VERIFICATION COMPLETE ==="
```

Pass criteria: `=== MKT-B6-B FINAL VERIFICATION COMPLETE ===` appears. Zero TypeScript errors. Build succeeds.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] `POST /api/v1/marketing/application` confirmed in `openapi_schema_map.md` before writing form
- [ ] Design doc read in full before writing any code
- [ ] All mandatory source files read before modifying
- [ ] B-01: `NEXT_PUBLIC_CAREERS_OPEN_ROLES` added to `frontend/apps/marketing/.env.example`
- [ ] B-02: `WaitlistForm` has optional `name` field; POST body includes `name: name || undefined`
- [ ] B-03: `HeroWaitlistForm` has optional `name` field; POST body updated
- [ ] B-04: `ApplicationForm.tsx` created — LinkedIn URL **required**; portfolio optional; all fields, Turnstile wrapper, success/error states, `DEFAULT_ROLES` fallback
- [ ] B-05: Careers page redesigned — role cards with detail bullets (no "Apply Now" buttons); separate form section with `var(--surface-marketing)` background; old `mailto:` link + `WaitlistForm` CTA removed
- [ ] `NEXT_PUBLIC_CAREERS_OPEN_ROLES` missing/empty → form still renders with `DEFAULT_ROLES` (no crash)
- [ ] No files outside `frontend/apps/marketing/` modified
- [ ] Phase 1: Tests pass (same count as baseline)
- [ ] **Phase 2 FULL verification passes** (`=== MKT-B6-B FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter marketing exec tsc --noEmit 2>&1 | tail -5 && pnpm --filter marketing build 2>&1 | tail -10 && pnpm --filter marketing lint 2>&1 | tail -5 && echo "=== MKT-B6-B FINAL VERIFICATION COMPLETE ==="
  ```

---

## Completion Summary

```
## MKT-B6 Part B Completion Summary

**Date**: [date]
**Phase 1 (tests)**: [X tests, Y pass, Z fail] — baseline was [baseline count]
**Phase 2 (build)**: [Pass / Fail] — TypeScript errors: [N]

**Tasks completed**:
- B-01: NEXT_PUBLIC_CAREERS_OPEN_ROLES env var ✅
- B-02: WaitlistForm name field ✅
- B-03: HeroWaitlistForm name field ✅
- B-04: ApplicationForm component ✅
- B-05: Careers page redesign ✅

**Notes**: [Any deviations, TypeScript warnings, or items for Tom review]
```
