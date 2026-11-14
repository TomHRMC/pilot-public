# Design Review Brief: MKT-B12 — Marketing Site Charter-Consistency & Team-Voice Copy Overhaul

**Mode**: Pilot Marketing UI Designer
**Batch**: MKT-B12 (Part 1 of 2 — copy review)
**Design spec**: `dev-docs/marketing-analysis/design-specs/mkt-b12-design-spec.md` — **Tom-approved 2026-08-08**; this is your source of truth
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0
**Estimated session**: 1–2 hours (review-only; no pixel spec)
**Platform**: Marketing website (`frontend/apps/marketing/`)
**Companion**: MKT-B12 Part 2 (React Engineer) — implements the manifest after your sign-off. Prompt: `batch-mkt-b12-react-engr-prompt.md`

---

## ⚠️ MANDATORY STOP: Read These First

- **`mkt-b12-design-spec.md`** — in full. Every replacement string is already Tom-approved. Your job is **review**, not rewrite.
- **`.roo/rules-pilot-marketing-ui-designer/`** — your standing rules (brand voice, CRO principles).

---

## Context

The Charter program (C-B1 → C-B15) is fully built, but the marketing site's copy drifted: stale "6 months free" FAQ copy, "Join the Waitlist" CTAs (there is no managed waitlist — after the 12 Charter Members, the next customer is a paying customer), an unconditional "price locked forever" over-promise on the pricing FAQ, and first-person founder voice ("I set it up myself", "Direct line to Tom") across the `/charter` page that Tom wants converted to team voice (we/our). The `/about` page keeps its first-person founder message — that is intentional.

The spec contains a **32-item copy-change manifest (§B)** with exact current → replacement strings and file:line references, all verified against the repo on 2026-08-08.

## Your Task — Review, Don't Rewrite

Review the manifest along three axes and produce a short review memo:

1. **Tone/voice consistency** — Do the replacements read naturally in context? Flag any replacement that is grammatically awkward in its surrounding sentence (the manifest quotes strings, not always full sentences). Pay special attention to:
   - Item 26 (bio callout rewrite — the biggest copy block; team-voice conversion retaining the 15-years electrical and controls engineering credential)
   - Items 8–10 (trade-page final CTA headlines: "Join the Electricians Shaping Pilot" etc. — check they land as headlines)
   - Item 15 (form success state: "You're in — application #{position} received.")
2. **CRO impact** — The CTA label changes ("Join the Waitlist →" → "Join the Charter Program →") touch 3 trade pages, contact, features, and 3 blog CTAs. Confirm the new labels preserve urgency/scarcity. If you believe a different label converts better, propose it — but the final call is Tom's.
3. **Terminology** — "Charter Member" (person) vs "Charter program" (program) per §B.5. Confirm the applications in items 3–5 are consistent, and flag any *other* surface in the repo where a member-noun appears without the term (quick grep).

## Hard Constraints

- **Do not restructure pages, move sections, or change any styling/tokens** — copy-only batch.
- **Do not touch**: `/about` founder voice, legal retention "90 days" clauses, blog editorial time references, `pricing-preview` / `pricing-general-release` pages, the backend `waitlist` endpoint name.
- **Do not weaken the legal-alignment edits** (items 2, 3) — those match the D22/D24 Terms clause and are non-negotiable accuracy fixes, not marketing latitude.
- Items 16 and 18 are explicitly **No change** — do not re-litigate unless you find a genuine defect.

## Deliverable

A review memo appended as a new section **`## Designer Review — MKT-B12`** at the bottom of `mkt-b12-design-spec.md`, containing:

- **Verdict per section** (B.1–B.5): ✅ approved as-is / 🔧 amendment proposed
- **Amendment table** (if any): item #, proposed alternative string, rationale — marked `PENDING TOM` 
- **Sign-off line**: `Designer sign-off: [name] — [date] — APPROVED / APPROVED WITH AMENDMENTS`

Then **STOP** — implementation begins only on Tom's approval of any amendments (Rule §1.5.5 handoff gate). If you approve with zero amendments, say so explicitly so Tom can green-light the React Engineer immediately.
