# Pilot for Trades Design System — Pass 4 Framework

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Strategic direction and surface sequencing for all 14 Pass 4 design surfaces, integration of pre-launch hygiene items, per-surface deliverable definitions, cross-cutting dependencies, validation gates between tiers
**Depends On**: Pass 1 (foundation/tokens), Pass 2 (information architecture), Pass 3 (seven locked flow specs) · `mvp-prd.md` v3.0 · `mvp-arch.md` v4.0 · `backend-mvp-additions-v4.md` (A1–A46 cumulative)

---

## Purpose

Pass 4 closes the loop on Passes 1–3 and gets Pilot to launch readiness. It does three distinct kinds of work:

1. **Resolves deferred surfaces from Passes 1–3** (Tier 1) — the items where Pass 3 locked a design decision that pointed to a Pass 4 follow-on, plus the one Phase 2 surface (background sync) that's been pulled forward because launch-readiness requires it.
2. **Surfaces tenant configuration and account management** (Tier 2) — every threshold, override, and preference Pass 3 introduced now needs a UI. There are a lot of these. This is where the system-default-with-tenant-override pattern (Pass 3 §16 of arch doc v4) gets its first dedicated UI treatment.
3. **Fills in everything between the happy paths** (Tiers 3 and 4) — empty/error/loading states, first-time-user states, onboarding, push permission flows, polish refinements, customer-facing public link styling, help/about/feedback, and the pre-launch hygiene items (privacy/ToS/EULA, email templates, beta tester onboarding, support handoff).

Unlike Pass 3, where each flow was a multi-decision design problem requiring a full spec, Pass 4 deliverables are heterogeneous: some are full flow specs (mobile-conflict resolution UI, onboarding), some are pattern guides applied across many flows (states catalog), some are settings-screen design with shared IA, some are incremental addenda to existing specs. This framework defines what "locked" means for each shape.

The defining constraint of Pass 4 is **scope discipline**. Items that don't block launch get explicitly deferred to Phase 2 with documented rationale, not silently carried.

## Strategic direction

### Pass 4 inherits the platform vocabulary; it does not establish new patterns

Pass 3 established eight cross-cutting platform UX patterns (formalized in arch doc v4 §16). Pass 4's job is to apply these patterns, not invent new ones. Where a Pass 4 surface seems to need a new pattern, the framework's first response is "can we reuse an existing one?" New patterns require explicit justification and get added to §16 if accepted.

The two genuinely new patterns Pass 4 will introduce are:

- **Mobile-to-web escalation**, established by Tier 1 #1 (owner-side mobile-conflict resolution UI). This is the inverse of the existing "mobile owner status row + deep-link" pattern — instead of mobile pulling status from web, web is now pulling escalations from mobile.
- **Settings IA for system-default-with-tenant-override**, established as part of Tier 2 #4. The pattern itself exists from Pass 3; what Pass 4 adds is a dedicated visual treatment for inherited-vs-overridden state, with an affordance to revert.

Both new patterns get added to arch doc v4 §16 as part of their respective surfaces' locked spec. Pass 4 does not introduce any other new platform vocabulary.

### Tier-by-tier inheritance

Tier 1 establishes the two new patterns above. Tier 2 inherits from Tier 1 (the Settings IA must accommodate the system-default-with-tenant-override visual treatment that Tier 1 #1 informs through threshold settings) and applies Pass 3 patterns. Tier 3 inherits from Tier 2 (onboarding flows surface tenant-configurable settings, so the Settings IA must be locked first). Tier 4 inherits from Tier 3 (customer-facing public link styling reuses content patterns from email templates, which surfaced in Tier 3 onboarding).

### Solo founder operational reality

Pass 4 has 14 design surfaces plus distributed pre-launch hygiene items. Sequencing matters because each tier feeds the next, and rework upstream is expensive. The framework prioritizes pattern-establishing work first (Tier 1), then settings work that cascades (Tier 2), then state coverage and onboarding (Tier 3), then polish (Tier 4). Within tiers, dependencies are explicit and any surface that *can* run in parallel is flagged as such.

## Resolution of open strategic questions

### 1. Background sync for mobile — implement pre-launch (confirmed)

**Decision**: Pass 4 produces design and the backend ledger v5 includes the implementation work.

**Rationale**: The Pass 3 Flow 7 offline sync spec depends on foreground sync. Pre-launch user research will quickly surface that techs killing the app between jobs is normal, and queues sitting unsynced for hours violates the "sync visibility is non-negotiable" strategic principle. Adding it post-launch means a major mobile architecture change after real customers are using the system. Doing it now while the surrounding sync infrastructure is still being built keeps the implementation cost minimal.

**Cost impact on backend ledger**: estimated +5–8 days of backend work (push-token registration, silent push handling, sync session management, plus mobile platform-specific background fetch APIs). Will be specified precisely in the Tier 1 #3 spec.

**Scope guard**: background sync is only the queue uploader. Not periodic data refresh, not background voice processing, not background photo uploads (those stay foreground for battery reasons). The locked spec will name these scope cuts explicitly.

### 2. Naming track resolution — resolved (Pilot for Trades)

**Decision**: Naming has resolved to **Pilot for Trades** as the customer-facing brand name, with **Pilot** as the casual short form used in voice readback, button labels, and conversational copy. URL: `pilotfortrades.com`.

**Internal codename**: The internal codename across infrastructure, code, database identifiers, npm namespace (`@pilot/`), Docker images, ECS resources, and Terraform state is `pilot` (lowercase). This was previously `aevofab` and has been renamed throughout the design docs and (separately) in the codebase, infrastructure, and DB schema. There is no longer a stealth-codename split — the customer-facing name is "Pilot for Trades" and the internal codename is "pilot."

**Convention used in this and subsequent Pass 4 docs**:
- Document titles and first-reference prose in customer-facing copy: "Pilot for Trades"
- Voice readback, UI button labels, casual prose, internal references: "Pilot"
- Code identifiers, file names, infrastructure resources: `pilot` (lowercase)

**Implication for Pass 4 sequencing**: With naming resolved, the previously hard-gated Tier 3 #10 (onboarding) and Tier 4 #13 (customer-facing public link styling) no longer carry a naming dependency. They can proceed when their tier readiness conditions are otherwise met.

**Operational follow-on items not gated by Pass 4 design** but required pre-launch:
- OAuth callback URL re-registration with QuickBooks Online and Google Cloud Console (`pilotfortrades.com` redirect URIs)
- Email sender domain setup (`pilotfortrades.com` SPF, DKIM, DMARC records)
- Stripe statement descriptor update ("PILOT FOR TRADES")
- Mobile app store listing names and bundle IDs (recommended `com.pilotfortrades.app`, optional)
- Internal repo and dev-tool path renames (e.g., `.roo/rules-pilot-architect/`)

### 3. Pre-launch hygiene items — Pass 4 scope (confirmed, distributed)

**Decision**: Pre-launch hygiene items are folded into Pass 4 but distributed across existing tiers as additions to host surfaces, not as a separate Tier 5. This keeps the 14 design surfaces as the design backbone and acknowledges that many hygiene items are content/legal/operations work rather than standalone design.

See [Pre-launch hygiene integration](#pre-launch-hygiene-integration) below for the per-item mapping.

**Operational note**: privacy policy, ToS, and EULA copy require legal review. Pass 4 design reserves space for them and locks the surfaces they appear on, but the copy itself is content/legal output, not Pass 4 design output. Tom owns the legal review timeline.

## Surface inventory and sequencing

### Tier 1 — High-stakes blockers

Tier 1 surfaces establish the two new platform patterns Pass 4 introduces. They run sequentially because each feeds into a downstream tier.

| # | Surface | Sequence | Rationale |
| :--- | :--- | :---: | :--- |
| 1 | Owner-side mobile-conflict resolution UI (web) | 1st | Establishes mobile-to-web escalation pattern. Largest pattern-establishing surface in Pass 4. Pass 3 Flow 7 §12 deferred this explicitly. |
| 2 | QuickBooks conflict resolution UI (web) | 2nd | Validates that the calendar conflict pattern (Pass 3 Flow 6) generalizes to a different domain (accounting sync vs scheduling). If pattern generalizes cleanly, Tier 2 confidently inherits it for any future-conflict-resolution surface. |
| 3 | Background sync for mobile | 3rd | Mostly system-design with thin UI surface (mostly status indicators that already exist from Flow 7). Sequenced last in Tier 1 because it clarifies the state Tier 2 settings UIs need to expose (sync interval, WiFi-only toggle, etc.). |

**Tier 1 exit gate**: Tier 2 starts when (a) all three Tier 1 specs are locked, (b) the two new platform patterns are added to arch doc v4 §16, and (c) the backend ledger v5 includes Tier 1 backend additions.

### Tier 2 — Broad-but-shallow surfaces

Tier 2 starts with a Settings IA framework doc (a one-time deliverable that establishes how settings pages look and behave in both apps), then applies that framework across all settings surfaces. This mirrors the Pass 3 framework-first approach.

| Order | Surface | Notes |
| :---: | :--- | :--- |
| 0 | Settings IA framework doc | One-time deliverable. Locks the visual treatment for inherited-from-system vs tenant-override, the revert-to-default affordance, and the page-level layout pattern shared across web and mobile. **Not one of the 14 surfaces** — it's prerequisite framing for #4–#7. |
| 1 | #4 Settings UIs for configurable thresholds | Margin buckets, ETC variance %, chart threshold, calendar conflict auto-expiry, photo retention, offline hard limit. The largest Tier 2 surface. |
| 2 | #5 Notification preference center | Inherits the system-default-with-tenant-override visual from #4. Per category × per channel matrix. |
| 3 | #6 Voice persona tone setting UI | Smallest Tier 2 surface. Surfaces the existing schema field that has no UI today. |
| 4 | #7 Account settings | Profile, password, MFA enrollment, integrations management. Independent of #4–#6 but sequenced last in Tier 2 because MFA enrollment is a flow that could pull into Tier 3 onboarding. |

**Tier 2 exit gate**: all settings surfaces locked, settings IA pattern committed to arch doc v4 §16, backend ledger v5 updated with read/write endpoints for tenant settings.

### Tier 3 — States, onboarding, and entry points

Tier 3 has two distinct workstreams that can run in parallel once Tier 2 closes:

**States workstream (#8 + #9 paired):**

| # | Surface | Notes |
| :--- | :--- | :--- |
| 8 | Empty / error / loading states for every Pass 1–3 flow | Delivered as a **states catalog** (pattern guide) plus an **application matrix** (which flow gets which catalog entry) plus per-flow application notes for non-trivial cases. Not 7 separate flow specs. |
| 9 | First-time-user empty states (no jobs, no quotes, no customers yet) | Extension of the states catalog. First-time-user states differ from generic empty states in that they include onboarding hooks (e.g., "Create your first customer" CTA wired to the customer creation flow). |

**Onboarding workstream (#10 + #11 paired):**

| # | Surface | Notes |
| :--- | :--- | :--- |
| 10 | Onboarding flows surfacing tenant-configurable settings | Full flow spec like Pass 3. Inherits Settings IA from Tier 2 to surface the right defaults during onboarding. Includes ToS/privacy acceptance and email/phone verification. |
| 11 | Mobile push notification permission request flow | Smaller flow spec, but distinct from #10 because the permission ask happens after onboarding, contextually (e.g., when assigning a tech to a job for the first time on mobile). |

**Tier 3 exit gate**: states catalog and application matrix locked; onboarding flow spec locked; push permission flow spec locked; backend ledger v5 includes any new endpoints (mostly for first-time-tenant provisioning and push token registration if not already covered in Tier 1 #3).

### Tier 4 — Polish and pre-launch hygiene

Tier 4 surfaces are largely independent and can run in parallel.

| # | Surface | Notes |
| :--- | :--- | :--- |
| 12 | Flow 3 dispatch board sync indicator amber-with-count refinement | Incremental addendum to existing Flow 3 spec, not a new flow spec. Smallest surface in Pass 4. |
| 13 | Customer-facing public quote/invoice link styling pass | Visual design + email template designs + content (privacy footer, support contact, branding). Hosts the privacy policy footer link. |
| 14 | Help / about / feedback surfaces | Full flow spec. Hosts the customer support handoff content. Surfaces the feedback channel into the Voice AI feedback loop where applicable. |

**Tier 4 exit gate**: all three surfaces locked; pre-launch hygiene items distributed across host surfaces complete (or have explicit content/legal handoffs documented); backend ledger v5 finalized.

### Settings IA framework doc — sequence position

The Settings IA framework doc sits between Tier 1 and Tier 2 as a prerequisite to Tier 2 #4. It is not one of the 14 surfaces but it is a Pass 4 deliverable. It will likely run ~30–50% the size of a typical Pass 3 flow spec.

## Pre-launch hygiene integration

Distributed across existing tiers as additions to host surfaces. Each hygiene item has a delivery type — design output (Pass 4 produces it), content/legal output (Pass 4 reserves space; Tom owns content), or operations output (Pass 4 reserves a surface; Tom owns process).

| Hygiene item | Host surface | Delivery type | Owner |
| :--- | :--- | :--- | :--- |
| Privacy policy copy | Tier 3 #10 (onboarding acceptance) + Tier 4 #13 (customer-facing footer link) + Tier 4 #14 (help surface link) | Content/legal | Tom + legal review |
| Terms of Service copy | Tier 3 #10 (onboarding acceptance) + Tier 4 #13 (footer) + Tier 4 #14 (help) | Content/legal | Tom + legal review |
| EULA copy | Tier 3 #10 (onboarding acceptance) | Content/legal | Tom + legal review |
| Transactional email template *visual design* | Tier 4 #13 (paired with public link styling) | Design output | Pass 4 design |
| Transactional email template *copy* | Tier 4 #13 | Content output | Tom |
| Beta tester onboarding plan | Adjacent to Tier 3 #10 as a parallel ops doc | Operations | Tom |
| Customer support handoff flows | Tier 4 #14 | Operations + design | Tom + Pass 4 design |

**Note on email templates**: visual design lives in Tier 4 #13 because customer-facing email styling needs to match the public link styling (same brand surface, same name treatment, same legal footer pattern). Treating them as one design problem rather than two is the right call. Copy authoring is a separate workstream from Pass 4 design, but Pass 4 reserves slots for which templates exist (categorized by trigger event: quote sent, invoice sent, payment received, appointment confirmed, etc.).

**Note on legal review**: privacy policy, ToS, and EULA copy don't need to be locked before Pass 4 design completes. Pass 4 locks the surfaces (e.g., "the onboarding screen has a checkbox accepting ToS and privacy policy at this point in the flow"), and the legal copy fills in afterward without requiring design changes.

## Per-surface deliverables — what "locked" means

Pass 4 deliverables come in five distinct shapes. Each surface gets categorized.

### Shape A — Full flow spec (Pass 3 pattern)

Like every Pass 3 flow. Includes:
- Strategic direction and key design decisions with rationale
- Locked screen-level layouts where applicable
- Interactive HTML prototype for high-leverage flows
- UX patterns established or reused (with explicit reuse callouts)
- Cross-domain considerations
- Backend additions for the cumulative ledger

**Surfaces in shape A**: Tier 1 #1, Tier 1 #2, Tier 3 #10, Tier 3 #11, Tier 4 #14 (5 surfaces).

### Shape B — Pattern guide + application matrix

A reusable visual treatment plus a matrix mapping the catalog entries to where they apply. Smaller than a full flow spec because the per-flow application is mostly a matrix entry, not a full spec.

Includes:
- Visual treatments for each state (empty, loading, error variants by severity and recoverability)
- Token usage and naming
- Application matrix (rows = Pass 1–3 flows; columns = states; cells = catalog entry or "N/A")
- Per-flow application notes only for non-trivial cases (e.g., the offline conflict resolution flow's error states have nuance the catalog doesn't cover by default)

**Surfaces in shape B**: Tier 3 #8, Tier 3 #9 (2 surfaces, delivered as one combined catalog).

### Shape C — Settings IA + per-setting spec

A one-time IA framework doc (the prerequisite deliverable between Tier 1 and Tier 2), then individual settings get short locked specs:
- Setting name, scope (system default, tenant override, user override), data type, validation rules
- Visual treatment within the IA framework
- Backend additions if not already in ledger
- Cross-references to the flow(s) where the setting takes effect

Per-setting specs are short (often 1–2 pages); the IA framework doc is the bigger deliverable.

**Surfaces in shape C**: Tier 2 #4, #5, #6, #7 (4 surfaces, plus the prerequisite IA framework doc).

### Shape D — Incremental addendum

A diff against an existing Pass 3 spec. Captures only the change, with explicit reference to the current spec section being modified.

**Surfaces in shape D**: Tier 4 #12 (1 surface).

### Shape E — Visual design + content composition

Visual design output (the public link page, email template visuals) plus a content slot inventory (privacy footer copy, sender names, dynamic fields). Distinct from a flow spec because there's no user flow being designed — it's static surface styling.

**Surfaces in shape E**: Tier 4 #13 (1 surface).

### Shape F — Background system design with thin UI

Mostly architectural design with limited UI surface. Closer to an architecture-doc chapter than a flow spec, but with locked UI for the parts that surface to users.

**Surfaces in shape F**: Tier 1 #3 background sync (1 surface).

### Total count check

Tier 1: 3 (Shapes A, A, F). Tier 2: 4 + IA framework doc (Shape C ×4 + IA doc). Tier 3: 4 (Shape B ×1 covering #8 + #9, Shape A ×2 covering #10 + #11). Tier 4: 3 (Shapes D, E, A). **14 surfaces, 6 distinct deliverable shapes, plus the Tier 2 IA framework doc as a non-numbered prerequisite.**

## Cross-cutting concerns and dependencies

### Pattern reuse from Pass 3 (§16 of arch doc v4)

Pass 4 is a heavy consumer of Pass 3 patterns. The expected reuse:

| Pass 3 pattern | Where Pass 4 reuses it |
| :--- | :--- |
| Track-changes diff vocabulary (amber/green/red) | Tier 1 #1 (mobile-conflict diff), Tier 1 #2 (QB conflict diff) |
| Four-class severity (auto-silent → escalation) | Tier 1 #1 (the "escalation" class is exactly the surface being designed), Tier 1 #2 (QB conflicts get classified into the same four classes) |
| Confirm-as-turn for destructive actions | Tier 4 #14 (delete account confirmation), Tier 2 #7 (password change confirmation) |
| Pre-commit staleness check (409-and-refresh) | Tier 1 #1 (owner about to resolve a conflict that mobile already auto-recovered from), Tier 1 #2 (QB sync state changed during owner resolution) |
| System default + tenant override two-tier config | Tier 2 #4, the foundational pattern for the entire Tier 2 settings work |
| Mobile owner status row + deep-link | Tier 1 #1 (the *inverse* of this — web pulling from mobile escalations rather than mobile pulling web status — is the new pattern) |
| Optimistic UI with pending badges | Tier 2 (settings changes apply optimistically; revert-to-default is undo-able), Tier 4 #14 (feedback submission shows pending state) |
| Always-preview-before-send | Tier 4 #13 (customer-facing public link preview before share); Tier 4 #14 (feedback preview before submit if it includes diagnostic data) |

**No new patterns expected beyond mobile-to-web escalation (Tier 1 #1) and the Settings IA visual treatment (Tier 2).** If a surface designer reaches for a new pattern, that's a flag — the framework requires either a justification for why an existing pattern doesn't fit, or a check against the §16 inventory to confirm reusability.

### Inter-tier dependencies

Read this graph as "X must lock before Y starts":

```
Tier 1 #1 (mobile-conflict UI) ─────┐
                                     ├──→ Tier 2 IA framework doc ──→ Tier 2 #4–#7
Tier 1 #3 (background sync) ─────────┘                                      │
                                                                            ↓
                                                                       Tier 3 #10
                                                                            │
                                                                            ↓
                                               Tier 3 #8 + #9 (states catalog) ──→ Tier 4 (parallel)
                                                       │
                                                       ↓
                                                 Tier 3 #11
                                                       │
                                                       ↓
                                                  Tier 4 #12, #13, #14 (independent of each other)
```

Naming is no longer a dependency — see [§ Naming track resolution](#2-naming-track-resolution--resolved-pilot-for-trades) above.

### Dependencies onto external tracks

- **Legal review** → Tier 3 #10 acceptance flow content, Tier 4 #13 footer content. Doesn't gate design lock; locks surface position only.
- **Beta tester program operationalization** → Tier 3 #10 adjacent ops doc. Doesn't gate Pass 4 design.

## Backend ledger plan (v4 → v5)

The cumulative ledger extends from A1–A46 (v4) to approximately A47–A65 (v5), with the bulk of new additions concentrated in Tier 1 and Tier 2.

**Tier 1 estimated backend additions:**

- A47 — Owner mobile-conflict escalation queue endpoints (list, detail, resolve). Probably 4–6 endpoints. Estimated 6–8 days.
- A48 — Mobile-conflict resolution write path with idempotency and pre-commit staleness check. Reuses existing 409 infrastructure. Estimated 3–4 days.
- A49 — QuickBooks conflict resolution endpoints. Mirror of A47 but for QB sync conflicts. Estimated 5–7 days. (May be slightly less if it can directly reuse calendar-conflict resolution infrastructure from Pass 3.)
- A50 — Background sync infrastructure: push token registration, silent push handling, sync session management. Estimated 5–8 days.

**Tier 2 estimated backend additions:**

- A51–A56 — Read/write endpoints for the six tenant settings groups (margin buckets, ETC variance %, chart threshold, calendar auto-expiry, photo retention, offline hard limit). Mostly thin CRUD over existing tables. Estimated 1–2 days per group, ~8–12 days total.
- A57 — Notification preference matrix endpoints. Read/write per-category × per-channel preferences. Estimated 2–3 days.
- A58 — Voice persona tone setting endpoint. Already in schema; just exposing the setting. Estimated 0.5 day.
- A59 — Account settings: profile update, password change, MFA enrollment endpoints. MFA is the heavyweight here. Estimated 3–5 days.
- A60 — Integrations management endpoints (read connection state, disconnect/reconnect for QuickBooks and Google Calendar). Estimated 2–3 days.

**Tier 3 estimated backend additions:**

- A61 — First-time-tenant provisioning endpoint (creates default settings, sample data optionally, etc.). Estimated 2–3 days.
- A62 — Onboarding state tracking (where is this user in onboarding; resumability). Estimated 1–2 days.

**Tier 4 estimated backend additions:**

- A63 — Public link signing and verification (already partially exists for invoices in arch doc v4; extend to quotes if not already covered). Estimated 1–2 days.
- A64 — Email template rendering pipeline + transactional email send endpoints. Estimated 3–4 days.
- A65 — Feedback submission endpoint. Estimated 1 day.

**Total Tier 1–4 estimated additions: ~45–66 days.** Cumulative backend MVP work moves from 117–161.5 days (v4) to roughly **162–227.5 days** by Pass 4 close.

These are framing estimates. Each surface's locked spec produces its actual additions and accurate estimates.

## Validation gates

### Tier 0 — Framework gate (this doc)

Before Tier 1 starts, this framework needs to be reviewed and locked. Specifically:
- [ ] Tier sequencing approved
- [ ] Pre-launch hygiene mapping approved
- [ ] Per-surface deliverable shapes approved
- [ ] Three open strategic question resolutions confirmed
- [ ] Backend ledger plan v4 → v5 framing reviewed for sanity

### Tier 1 → Tier 2 gate

- [ ] All three Tier 1 specs locked
- [ ] Mobile-to-web escalation pattern added to arch doc v4 §16
- [ ] Pre-commit staleness check confirmed reusable for both new conflict surfaces
- [ ] Backend ledger v5 includes A47–A50
- [ ] Settings IA framework doc started (does not need to be locked; just started so Tier 2 can begin)

### Tier 2 → Tier 3 gate

- [ ] Settings IA framework doc locked
- [ ] All four Tier 2 surfaces locked
- [ ] System-default-with-tenant-override visual pattern added to arch doc v4 §16
- [ ] Backend ledger v5 includes A51–A60

### Tier 3 → Tier 4 gate

- [ ] States catalog + application matrix locked
- [ ] Onboarding flow locked
- [ ] Push permission flow locked
- [ ] Backend ledger v5 includes A61–A62
- [ ] Email template inventory drafted (i.e., we know which templates exist, even if copy isn't final)

### Pass 4 close gate

- [ ] All 14 design surfaces locked
- [ ] Settings IA framework doc locked
- [ ] Pre-launch hygiene mapping completed (legal copy in review with explicit owner; ops docs drafted; design surfaces lock the slots)
- [ ] Arch doc v4 §16 updated with two new patterns
- [ ] PRD v3.1 issued (likely smaller than v3.0 update; mostly captures Pass 4 settings and any new product-level decisions)
- [ ] Backend ledger v5 finalized
- [ ] Frontend coding can begin once backend foundation stable

## What Pass 4 does NOT cover

Intentionally deferred to Phase 2 or post-launch:

- **Tablet-tech full UX redesign** — Pass 2 deferred this to Post-MVP; Pass 4 confirms the deferral. Tablet uses Field Mode (Pass 2 §7) which ships in MVP; full tablet-tech flows wait until tablet adoption signal exists.
- **Mobile owner full-CRUD on customers** — Pass 2 §3 deferred to Post-MVP; Pass 4 confirms. Owner mobile remains progressive disclosure with key actions only.
- **Reports ad-hoc builder, custom SQL, scheduled email reports** — Pass 2 §5 deferred; Pass 4 confirms.
- **Voice free-form messaging** (vs the templated MVP set) — Pass 2 §4 deferred to Phase 2.
- **Recurring jobs, skill-based routing, crew assignments, predictive scheduling, customer self-service booking** — Pass 2 §1 deferred to Phase 2.
- **Background voice processing, background photo uploads** — explicitly excluded from Tier 1 #3 background sync scope. Foreground only for battery reasons.
- **Customer-facing self-service portal** — beyond the public quote/invoice link, no customer login surface in MVP.
- **Multi-language UI** — English only at launch.
- **Web onboarding flows for the technician role** — onboarding focuses on owner/solo-operator first-time setup. Tech onboarding on web is minimal (invite-link → set password → done) and doesn't need a designed flow beyond a simple form.
- **Help center / knowledge base content** — Tier 4 #14 designs the help surface; populating it with articles is a content workstream Tom owns separately.
- **In-app product tours / coachmarks beyond first-time-user states** — Tier 3 covers first-time-user empty states with onboarding hooks; full coachmark/tour systems are Phase 2.

## Out of scope: tracked separately, not blocked

These are not Pass 4 design work but interact with it:

- **Backend MVP implementation** — runs in parallel with Pass 4 design. Pass 1/2/3-validated foundations can be built now; Pass 4-additions get layered in as ledger v5 entries land.
- **Pre-launch operational items beyond hygiene** — billing/payment setup, infrastructure provisioning, monitoring/alerting, on-call runbooks. Tom owns operationally.
- **Marketing site, sales collateral, product positioning copy** — adjacent to but distinct from product UI design.
- **Beta tester recruitment** — adjacent to Tier 3 #10 ops doc but is a separate sales/community workstream.

## Next: First Tier 1 surface

The next Pass 4 deliverable is the **owner-side mobile-conflict resolution UI (web)**. Pass 3 Flow 7 §12 deferred this with the following context to inherit:
- Conflict severity classification (the "escalation" class) already exists from Flow 7 §5
- Tech device captures the conflict, queues it for owner review, and shows tech a "waiting on owner" state already
- Owner notification path (push to owner mobile + appearance on web dashboard) needs wiring
- Resolution UI on web needs full design — what does the owner see? What's the diff payload look like? What auto-recovery options are presented?
- Pre-commit staleness check from Flow 6 §7 must apply: owner sees "this conflict was auto-recovered while you were viewing it" and gets a 409-and-refresh

The Tier 1 #1 spec will deliver: strategic direction for mobile-to-web escalation as a platform pattern, locked screen-level layouts for the owner-side resolution UI on web, the diff payload visual treatment (reusing track-changes vocabulary), notification path wiring, backend additions A47–A48.

Locked sequencing: this framework → Tier 1 #1 → Tier 1 #2 → Tier 1 #3 → Tier 2 IA framework doc → Tier 2 #4–#7 → Tier 3 #8–#11 (with naming gate before #10) → Tier 4 #12–#14 (with naming gate before #13) → Pass 4 close → frontend coding begins.

