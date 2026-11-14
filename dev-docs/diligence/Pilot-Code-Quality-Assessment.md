# Pilot for Trades — AI-Run Code-Quality Review
### What three adversarially prompted AI reviews found — and what it shows about building code to production standards with AI

> **Method:** three separate AI review passes — backend (FastAPI), web (Next.js/React/TS), mobile (React Native/Expo/TS) — each instructed to act as a skeptical senior engineer, read and sample the real repository (not the docs), gather objective signals from ~15 representative files per codebase, and report weaknesses rather than praise. Findings are summarized below with my responses, including the weaknesses. **No human third party has reviewed this code.** I publish it because the point of this project isn't "the AI wrote a lot of code" — it's whether the code is *good*, and whether the person directing the AI has the judgment to know the difference.

---

## Bottom line

**All three reviews rated the codebases as "good code" with senior-grade fundamentals.** The weaknesses are the recognizable scars of a fast, largely solo build: a few oversized modules, some repo clutter, typing asserted but not machine-enforced, and — the one that matters — a **mobile offline-sync subsystem that was mid-integration when the project was deliberately hibernated**. None are architectural dead ends; each is a bounded, nameable punch list.

That combination is the whole demonstration: AI-augmented delivery can produce engineering built to production standards *and* leave a short, well-understood cleanup list — provided an experienced architect is directing it and knows exactly where the edges are. Publishing the weaknesses alongside the strengths is the point, not a risk: it's the difference between someone who can wield AI and someone who just ran it.

---

## Backend (FastAPI / Python) — **Good: senior-grade, solid-mid**

~100K LOC app code · 74 route modules · ~250 Pydantic schema classes in `api/schemas/` · ~4,950 test functions / ~11,000 assertions · mutation testing present.

**Strengths:**
- **The things that actually matter for multi-tenant SaaS are done well:** JWKS signature validation with rotation, DI-based RBAC (`Depends(require_permission("quotes.create"))`, ~350 permission-check call-sites), tenant isolation enforced in queries *and* in a dedicated isolation test suite (with a documented "404-not-403 to prevent enumeration" rationale; route-level exceptions: Known Limitations #27).
- **Careful Postgres modeling** — CITEXT/JSONB/TSTZRANGE/exclusion constraints, TZ-aware timestamps, audit mixins, DB-trigger audit context.
- **Test rigor beyond MVP norms** — ~4,950 domain-organized test functions, e2e critical paths, and *mutation testing* (a tell that the author cares about test *effectiveness*, not coverage theater).

**What I'd flag myself (and how I think about it):**
1. *A few 2,000–5,000-line modules (`voice_action_router.py` is 5,189).* Known and bounded: dispatch is table-driven and handlers reuse the route `_impl()` logic, so it's verbose, not tangled — a mechanical per-domain split, first on the cleanup list.
2. *Repo scar tissue — a hardcoded localhost dev-DB password default, scratch files, a leftover `twilio` dep (removed from the requirements in the public snapshot), some doc drift.* Cosmetic solo-build residue; real secrets and `.env` are git-ignored and the password is a localhost dev default (already scrubbed in the public snapshot). A tidy-up pass clears it.
3. *Typing asserted but not enforced (no mypy; return hints on ~27% of functions), and `/test` endpoints on the production surface.* Runtime contracts are strong via pervasive Pydantic response models (~88% of routes); the `/test` endpoints are env-gated and double-blocked in prod. Adding mypy to CI, backfilling return hints, and enabling the JWT `iss`, `aud` and `token_use` claim checks are straightforward hardening steps (the audience check is already flagged in-code).

---

## Web (Next.js / React / TypeScript) — **Good: very clean type and lint hygiene**

Web app: ~156K lines including tests (~1,090 files) · ~2,350 test cases + 27 Playwright e2e · generated OpenAPI type contract.

**Strengths:**
- **Type/lint discipline at scale that looks like a seasoned team, not a solo build:** across ~156K lines, only **9 `any`** (one in a test) and **no `@ts-ignore`** (3 `@ts-expect-error`, all in test setup), strict mode, `--max-warnings 0`, 0 `console.log`, and a *custom ESLint rule* enforcing design-token usage.
- **Clean architecture + hard state boundary** — feature-sliced layout, shared `apiClient`/`queryClient`, TanStack Query for server state vs. 3 small Zustand stores for client state (an enforced rule).
- **Error handling and accessibility treated as first-class** — a well-built RFC-7807 error normalizer designed never to throw; 782 ARIA usages and **399 role-based test queries** (a11y is tested, not just claimed).

**What I'd flag myself (and how I think about it):**
1. *The generated OpenAPI types are bypassed by hand-written interfaces + `as` casts in the data layer.* A deliberate, TODO-tracked stopgap pending backend type exposure; the generator is wired (`pnpm sync-api-types`). Finishing the wiring removes the hand-types — managed debt, not drift.
2. *Forms are hand-rolled with `useState` instead of the installed react-hook-form + zod.* They work and reset cleanly; standardizing on RHF+zod is a consistency refactor, not a capability gap.
3. *No React ErrorBoundaries, and a few 500–800-line page components.* Adding top-level + route error boundaries is a small, high-value add; the large pages are decomposable and none are tangled.

---

## Mobile (React Native / Expo / TypeScript) — **Good fundamentals; the offline layer is the one material item**

~31K LOC (non-test) · no god-files (largest 607 lines) · 13 `any` / 0 ts-ignore · real Cognito/MFA.

**Strengths:**
- **Strict typing and real RN/Expo depth** — almost no escape hatches, a dynamic-`require` adapter split to keep native SQLite out of the web bundle, a background-sync time budget under iOS's 30s cap, a genuine Amplify v6 MFA flow (TOTP/SMS/email + recovery codes).
- **Clean feature-sliced architecture** with shared workspace packages and the same server/client state discipline as web.

**The one material finding — stated plainly:** the **offline-first sync subsystem — the product's differentiator and its riskiest surface — was mid-integration (~70%) when the project was deliberately hibernated.** The *design* is senior-grade (idempotency keys, a conflict-severity router, a concurrent-sync guard), but several documented behaviors aren't yet wired, and there's a real data-safety gap:
- No WatermelonDB `schemaMigrations` at schema **v3** → a future schema bump would recreate the local DB and wipe unsynced data. **Highest-severity item.**
- One model (`NecCalcLog`) isn't registered; `SyncProvider`, force-quit recovery, and the foreground "Sync Now" path are referenced but not wired; documented exponential backoff isn't actually read.
- The sync tests are hollow — they exercise `fetch`/mocks, not the orchestrator — so this risky code has effectively no behavioral coverage.

**How I think about it (and why I'm telling you first):** that subsystem was being integrated when I hibernated the project at a founder-ready state — I stopped before finishing it on purpose. The design is done; the remaining work is a bounded punch list I can name exactly: add the local-DB migrations, register the model, wire the orchestrator for foreground + force-quit recovery, implement the backoff read, and write real orchestrator/conflict tests. That's a known, scoped sprint — not a redesign. Knowing precisely where AI-accelerated work still needs the human to finish and verify it is exactly the judgment this project is meant to show.

---

## Cross-cutting honesty notes
- **Test rigor is real where it counts most** (backend: mutation testing; web: role-based a11y tests) and **weakest exactly on the mobile sync engine** — stated precisely rather than claiming uniform coverage.
- **Measured coverage** (fresh runs, 2026-10-13): backend **76%** line+branch, web **~71%** lines, mobile **~75%** lines — a consistent full-stack band, with the thin spots in background workers and the sync engine as noted.
- **"Technical design follows the SOC 2 security criteria — built to the controls, not audited."** Never "certified."
- **Key-person risk is real** (solo build, no human peer review) — stated plainly; the method docs (METHOD, AI-PITFALLS) and 952 design docs (private original) exist specifically to make a team takeover tractable.

## What this demonstrates
Read all of it — the strengths and the cleanup list. What the review shows isn't that AI can emit code; it's that an experienced architect directing AI made the **right calls on the parts that are expensive to get wrong** — auth, multi-tenancy, the data model, test effectiveness — and names precisely where the build stopped short. That judgment is the transferable asset this project exists to demonstrate.
