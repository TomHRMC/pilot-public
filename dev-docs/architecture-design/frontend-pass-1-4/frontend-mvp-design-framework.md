# Pilot for Trades — Frontend Design Framework

**Status as of April 30, 2026**: **Pass 4 design phase complete.** All 14 surfaces + Tier 1.5 + Settings IA framework locked. PRD v3.1 final, Arch doc v5, and Backend ledger v6 issued at Pass 4 close. **The design framework's job is done; implementation phase begins.**

**Document version**: 3 (rewritten April 30, 2026 to reflect Pass 4 close and pivot toward implementation phase). This is the third and final full rewrite anticipated for MVP.

---

## How to read this doc

This is the design team's source of truth — but with Pass 4 design phase complete, the framework doc's role shifts from "tracking what's locked vs. pending" to "documenting what was produced and pointing forward to implementation."

The document covers:

- **What the four design passes produced** (with 14 surfaces locked, the Settings IA framework, and Tier 1.5 customer comms extension)
- **The cross-cutting platform UX vocabulary** — 16 patterns formalized in arch doc §16
- **Parallel tracks closed at Pass 4 close** — PRD v3.1 final, Arch doc v5, Backend ledger v6
- **Implementation-phase workstreams** — backend MVP work, frontend coding, pre-launch hygiene, beta testing, soft launch
- **What does NOT exist as design output** — visual mockups, Figma files, pixel-perfect screens — and why

For backend AI agents and developers consuming this doc: the canonical sources of truth for engineering work are listed in [What backend implementation reads](#what-backend-implementation-reads). The framework doc itself is design-team scoped; consume it for context, not as engineering input.

## The four-pass design framework

Frontend design work was organized into four passes, each producing a different kind of output. Each pass was a distinct level of abstraction — you couldn't do a higher pass well without the lower passes locked. **All four passes are now complete.**

### Pass 1 — Foundation (complete)

The visual primitives. Everything that doesn't change between screens.

Delivered:
- Five-color token system (`brand`, `alert`, `margin`, `fault`, `neutral`)
- Typography scale for web vs mobile
- Spacing, radii, touch target sizes
- Six-state voice state machine
- Theming infrastructure (light + dark, themeable from day one)
- Implementation files: `tokens.ts`, `tailwind.preset.ts`, `globals.css`, `gluestack-config.ts` — ready to drop into the monorepo

Output: `dev-docs/architecture-design/frontend-pass-1-design-spec.md` plus the four implementation files.

### Pass 2 — Information Architecture (complete)

The map of the apps. What lives where, on which platform, behind which permission.

Delivered:
- Domain-to-surface mapping (15 PRD domains → web / mobile-tech / mobile-owner)
- Web sitemap (8 top-level sections originally; extended to 11 in Pass 4 Settings IA framework)
- Mobile sitemap (5 bottom-nav tabs with role-gated owner tab)
- "Calcs" tab decision for vertical expansion
- Field Mode tablet strategy
- Progressive disclosure model for solo operators

Output: `dev-docs/architecture-design/frontend-pass-2-design-spec.md` plus the two SVG sitemaps.

### Pass 3 — Key Flow Prototyping (complete)

Working interactive prototypes of the highest-leverage flows, plus locked design specs that capture every decision. Most of the design *time* lived here because each flow was a multi-decision design problem.

The original list of 5 flows expanded to 7 during execution as Pass 2's IA work surfaced additional candidate flows:

| # | Flow | Output |
| :--- | :--- | :--- |
| 1 | Voice quote creation (mobile, chat-style) | Spec + interactive HTML prototype |
| 2 | Real-time job profitability drill-down (web) | Spec |
| 3 | Dispatch board interactions (web) | Spec |
| 4 | Tech-to-customer templated communications (mobile + web) | Spec |
| 5 | Quote approval workflow (mobile + web) | Spec |
| 6 | Calendar conflict resolution (web) | Spec + interactive HTML prototype |
| 7 | Offline-to-online sync with conflict resolution (mobile) | Spec + interactive HTML prototype |

Each flow produced a locked spec doc and updates to the running backend additions ledger. Three flows additionally produced interactive HTML prototypes for visual reference.

Output: `dev-docs/architecture-design/frontend-pass-3-flow-N-*-spec.md` for each flow (7 specs), plus interactive HTML prototypes for Flows 1, 6, and 7.

### Pass 4 — Polish, States, Onboarding (complete)

The work that turned a designed-but-skeletal product into a shipping one. Pass 4 scope was **fourteen design surfaces** in four priority tiers, plus the Settings IA framework as a non-numbered Tier 2 prerequisite, plus the Tier 1.5 customer comms extension that surfaced mid-pass.

The defining constraint of Pass 4 was scope discipline — items that didn't block MVP launch were explicitly deferred to Phase 2 with documented rationale rather than silently carried.

See [Pass 4 surfaces produced](#pass-4-surfaces-produced) below.

## Pass 4 surfaces produced

All 14 surfaces locked. Plus the Settings IA framework prerequisite and the Tier 1.5 customer comms extension that surfaced from Tier 2 #5 scoping.

### Tier 1 — High-stakes blockers

Tier 1 established new platform patterns that propagated to Tier 2–4.

| # | Surface | Spec |
| :--- | :--- | :--- |
| 1 | Owner-side mobile-conflict resolution UI (web) | `frontend-pass-4-tier-1-flow-1-owner-mobile-conflict-resolution-spec.md` |
| 2 | QuickBooks conflict resolution UI (web) | `frontend-pass-4-tier-1-flow-2-quickbooks-conflict-resolution-spec.md` |
| 3 | Background sync for mobile | `frontend-pass-4-tier-1-flow-3-background-sync-spec.md` |

**Patterns established**: mobile-to-web escalation pattern (#1), bilateral integration conflict resolution pattern formalized (validated by #2), background sync execution pattern (#3).

**Backend additions A47–A51** added to ledger.

### Tier 1.5 — Flow 4 Customer Comms Extension

Surfaced from the Tier 2 #5 notification preferences discussion when the operational hole was identified: customer SMS replies had nowhere to go in current Pilot. Pulled forward as an MVP-blocking surface because the alternative (tech missing customer reply, showing up to no one) was a trust-shattering moment for early adoption.

| Surface | Spec |
| :--- | :--- |
| Flow 4 Customer Comms Extension (inbound SMS, threading, free-form replies, voice-to-text, owner visibility, quota) | `frontend-pass-4-tier-1-5-flow-4-customer-comms-extension-spec.md` |

**Strategic frame**: All customer comms stay inside Pilot. Tech never uses their personal phone's SMS to reach customers. Customer SMS routes through tenant's Telnyx number; threading by `(customer × tech × tenant phone number)`; tech replies via free-form composition (with voice-to-text as primary input); owner sees all conversations on web.

**Patterns established**: carrier-agnostic adapter layer pattern, subscription quota with soft/hard cap pattern, lazy provisioning of external resource at first use pattern.

**Pre-launch hygiene added**: A2P 10DLC brand and campaign registration with The Campaign Registry. Owned by Tom; targets completion 4–6 weeks before MVP launch.

**Backend additions A59–A66** added to ledger. Note: A56–A58 reserved for Tier 2 #5 in numbering scheme.

### Tier 2 prerequisite — Settings IA Framework

The framework doc that enabled Tier 2 #4–#7 design. Locked the IA tree across web and mobile, the system-default-with-tenant-override visual treatment, the page-level layout pattern, the three-category save behavior, and the three-question mobile inclusion rule.

| Deliverable | Spec |
| :--- | :--- |
| Settings IA framework | `frontend-pass-4-tier-2-settings-ia-framework.md` |

**New visual treatments established** (extensions of existing §16 patterns rather than new top-level patterns): system-default-with-tenant-override visual treatment (3 states + revert-to-default micro-confirmation), three-category save behavior (save-on-blur / save-on-group-complete / explicit Save), three-tier user/tenant/system resolution chain.

### Tier 2 — Broad-but-shallow surfaces

| # | Surface | Spec |
| :--- | :--- | :--- |
| 4 | Settings UIs for configurable thresholds | `frontend-pass-4-tier-2-flow-4-configurable-thresholds-spec.md` |
| 5 | Notification preference center | `frontend-pass-4-tier-2-flow-5-notification-preference-center-spec.md` |
| 6 | Voice persona tone setting UI | `frontend-pass-4-tier-2-flow-6-voice-persona-tone-spec.md` |
| 7 | Account settings | `frontend-pass-4-tier-2-flow-7-account-settings-spec.md` |

**Tier 2 highlight**: 18 distinct settings across 7 sub-surfaces in #4. Three canonical mockups (system-default-with-tenant-override, save-on-group-complete, per-user override) established for #5–#7 inheritance.

**Backend additions**: A52–A58 plus A67–A71.

### Tier 3 — States, onboarding, and entry points

| # | Surface | Spec |
| :--- | :--- | :--- |
| 8 | Empty / error / loading states for every Pass 1–3 flow | `frontend-pass-4-tier-3-flow-8-9-states-catalog-spec.md` |
| 9 | First-time-user empty states | `frontend-pass-4-tier-3-flow-8-9-states-catalog-spec.md` |
| 10 | Onboarding flows that surface tenant-configurable settings | `frontend-pass-4-tier-3-flow-10-11-onboarding-and-push-permission-spec.md` |
| 11 | Mobile push notification permission request flow | `frontend-pass-4-tier-3-flow-10-11-onboarding-and-push-permission-spec.md` |

**Tier 3 highlights**: 12 catalog entries (5 empty + 3 loading + 4 error) covering all Pass 1–4 surfaces, plus 8 first-time-user variants. Tier 3 #10 was the largest single Pass 4 spec — tenant signup wizard, post-wizard checklist, trial-to-paid conversion, mobile setup phase. #11 covers the push permission timing strategy with pre-explainer screen before OS prompt.

**Backend additions**: A72–A78.

### Tier 4 — Polish and pre-launch hygiene

| # | Surface | Spec |
| :--- | :--- | :--- |
| 12 | In-flight sync indicator with pending count (Flow 3 dispatch board refinement) | `frontend-pass-4-tier-4-flow-12-in-flight-sync-indicator-spec.md` |
| 13 | Customer-facing public quote/invoice link styling pass | `frontend-pass-4-tier-4-flow-13-customer-facing-public-link-styling-spec.md` |
| 14 | Help / about / feedback surfaces | `frontend-pass-4-tier-4-flow-14-help-about-feedback-spec.md` |

**Tier 4 highlights**: #12 generalized as a platform pattern (in-flight sync indicator with pending count, applied to all four sync surfaces). #13 hosted significant pre-launch hygiene content — 16 transactional email templates, customer-facing public quote/invoice pages with Stripe one-time payment + amount variance, tenant email branding. #14 introduced AI-mediated help with RAG retrieval over markdown corpus stored in S3, chat session capture for training data, voice integration.

**Backend additions**: A79–A88.

### Pass 4 close totals

- **16 design specs** delivered (14 numbered surfaces + Settings IA framework + Tier 1.5 extension)
- **42 cumulative backend additions** added in Pass 4 (A47–A88)
- **7 new platform UX patterns** formalized in arch doc §16 (Tier 1's three + Tier 1.5's three + Tier 4 #12's one)
- **3 visual treatment extensions** that ride on existing §16 patterns
- **Estimated backend MVP work cumulative**: 259–334.5 days (~38–48 weeks depending on team parallelism)

## Cross-cutting platform UX vocabulary

The platform UX vocabulary spans 16 patterns across Passes 3 and 4. All formalized in arch doc v5 §16. Future Phase 2 design surfaces inherit these patterns by default; deviations require explicit justification.

### Pass 3 patterns (8)

| Pattern | First established | §16 location |
| :--- | :--- | :--- |
| Track-changes diff vocabulary (amber/green/red) | Flow 5 (Quote approval) | §16.2 |
| Confirm-as-turn for destructive voice actions | Flow 1 (Voice quote creation) | §16.3 |
| Pre-commit staleness check (409-and-refresh) | Flow 3 (Dispatch board edits) | §16.4 |
| System default + tenant override two-tier configuration | Flow 6 (Calendar conflict auto-expiry) | §16.5 |
| Four-class severity pattern | Flow 3 (Dispatch conflicts) | §16.6 |
| Always-preview-before-send for one-way-door actions | Flow 4 (Customer comms) | §16.7 |
| Optimistic UI with pending badges | Flow 7 (Mobile offline) | §16.8 |
| Mobile owner status row + deep-link | Pass 2 QB sync | §16.9 |

### Pass 4 patterns (7 new + 3 visual treatment extensions)

Tier 1, Tier 1.5, and Tier 4 #12 added seven new platform-level patterns (formalized in arch doc v5 §16.10–§16.13 and §17):

| Pattern | Established | §16 / §17 location |
| :--- | :--- | :--- |
| Bilateral integration conflict resolution pattern (formalized) | Tier 1 #2 — validates calendar/QB pattern generalization | §16.10 (renamed from prior calendar-specific entry) |
| Mobile-to-web escalation pattern | Tier 1 #1 | §16.11 |
| Background sync execution pattern | Tier 1 #3 | §16.12 |
| Carrier-agnostic adapter layer pattern | Tier 1.5 — Telnyx as the first instance | §17.1 |
| Subscription quota with soft/hard cap pattern | Tier 1.5 — SMS segments as the first instance | §17.6 |
| Lazy provisioning of external resource at first use | Tier 1.5 — Telnyx number provisioning | §17.3 |
| In-Flight Sync Indicator with Pending Count | Tier 4 #12 — generalized across all four sync surfaces | §16.13 |

The Settings IA framework added three visual treatments that extend existing §16 patterns rather than introducing new top-level patterns:

| Visual treatment | Extends | Captured in |
| :--- | :--- | :--- |
| System-default-with-tenant-override visual treatment (3 states + revert-to-default micro-confirmation) | §16.5 (data shape) | Settings IA framework Decision 4; Tier 2 #4 Mockup A |
| Three-category save behavior (save-on-blur / save-on-group-complete / explicit Save) | New visual primitive used across all settings surfaces | Settings IA framework Decision 5; Tier 2 #4 Mockup B (group-complete) |
| Three-tier user/tenant/system resolution chain | §16.5 (extends two-tier to three-tier) | Settings IA framework Decision 6; Tier 2 #4 Mockup C |

The three-question mobile inclusion rule and the code-level-vs-data-driven placement decision are framework-internal patterns rather than platform UX vocabulary; they live in the Settings IA framework doc.

## Parallel tracks — closed at Pass 4 close

All three canonical doc tracks have issued their Pass 4 close versions.

### PRD update track

| Version | Status | Notes |
| :--- | :--- | :--- |
| v3.0 | ✓ issued at Pass 3 close | Captures all 15 product domains; formalizes Pass 3 cross-cutting platform UX vocabulary; finalizes pricing at $149/month |
| v3.1 (interim) | ✓ issued | Pass 4 Tier 1.5 — extends §3.7 with bidirectional SMS, threading, free-form replies, voice-to-text, owner visibility; extends §3.11 with SMS quota tier; adds three new cross-cutting patterns |
| **v3.1 (final)** | **✓ issued at Pass 4 close** | **Consolidates v3.1 interim plus all Tier 1, 1.5, 2, 3, 4 product decisions. Major additions: multi-tier subscription model with trial-as-tier framing and Stripe integration; multi-method MFA with tenant-required policy and 7-day grace period; notification preference center; AI-mediated help system; customer-facing public quote/invoice pages; new §3.16 Help & Support domain.** |

### Architecture doc track

| Version | Status | Notes |
| :--- | :--- | :--- |
| v4.0 | ✓ issued at Pass 3 close | Three new chapters: §14 Quote Approval & Templates, §15 Mobile Offline Operations, §16 Cross-Cutting Platform Patterns |
| v4.1 | ✓ applied | Pass 4 Tier 1 patterns added to §16 (§16.10–§16.12) |
| v4.2 | ✓ applied | Pass 4 Tier 1.5 — adds §17 SMS Infrastructure |
| **v5** | **✓ issued at Pass 4 close** | **Consolidates v4.1, v4.2 patches plus Pass 4 Tier 2/3/4 architectural additions. Four new top-level chapters: §17 SMS, §18 Customer-Facing Public Surfaces, §19 Help System, §20 Subscription Tier + Stripe Integration. Multiple sub-section additions: §3.5 Notification Preference Center, §4.5 MFA expansion, §4.7 Onboarding State Machine, §4.8 Account Settings, §16.13 In-Flight Sync Indicator.** |

### Backend additions track

| Version | Status | Cumulative additions | Cumulative remaining MVP backend work |
| :--- | :--- | :--- | :--- |
| v4 | ✓ issued at Pass 3 close | A1–A46 | 117–161.5 days |
| v5 | ✓ issued at Tier 1 close | A1–A55 | 148–203.5 days |
| v5.1 | ✓ applied | A1–A55 (Tier 2 #4 explicitly integrated) | 148–203.5 days |
| v5.2 | ✓ applied | A1–A66 | 171–229.5 days |
| **v6** | **✓ issued at Pass 4 close** | **A1–A88 (87 cumulative additions)** | **259–334.5 days (~38–48 weeks)** |

### Naming track (resolved)

Naming has resolved to **Pilot for Trades** (customer-facing brand) with **Pilot** as the casual short form. The internal codename across infrastructure, code, database identifiers, npm namespace (`@pilot/`), Docker images, ECS resources, and Terraform state is `pilot` (lowercase). URL: `pilotfortrades.com`. Previously `aevofab` and renamed throughout. There is no longer a stealth-codename split.

### Pre-launch hygiene track

Pre-launch hygiene items are distributed across host surfaces rather than tracked as a separate tier. Most are now content/operational work owned by Tom; a few have hard pre-launch dependencies.

| Hygiene item | Host surface | Delivery type | Owner |
| :--- | :--- | :--- | :--- |
| **A2P 10DLC brand + campaign registration** (Telnyx / The Campaign Registry) — required for reliable US SMS deliverability | Tier 1.5 (locked design); 4–6 week approval timeline; **must complete before MVP launch** | Operations / compliance | Tom |
| Privacy policy copy | Tier 3 #10 (acceptance) + Tier 4 #13 (footer) + Tier 4 #14 (help link) | Content/legal | Tom + legal review |
| Terms of Service copy | Tier 3 #10 + Tier 4 #13 + Tier 4 #14 | Content/legal | Tom + legal review |
| EULA copy | Tier 3 #10 (acceptance) | Content/legal | Tom + legal review |
| 16 transactional email templates (visual design + content) | Tier 4 #13 | Design + content | Tom (content) |
| Help corpus articles (~60 markdown articles) | Tier 4 #14 | Content | Tom |
| Beta tester onboarding plan | Adjacent to Tier 3 #10 | Operations | Tom |
| Customer support handoff flows | Tier 4 #14 | Operations + design | Tom (operations) |
| OAuth callback URL re-registration with QuickBooks Developer Portal and Google Cloud Console (`pilotfortrades.com` redirect URIs) | Operational | Operations | Tom |
| Email sender domain setup (`pilotfortrades.com` SPF, DKIM, DMARC records) | Operational | Operations | Tom |
| Stripe statement descriptor update to "PILOT FOR TRADES" | Operational | Operations | Tom |
| Mobile app store listing names and bundle IDs (recommended `com.pilotfortrades.app`) | Operational | Operations | Tom |
| Marketing site at `pilotfortrades.com` | Operational | Marketing | Tom |
| Optional short-link domain registration (`pilot.tr` or similar) | Tier 4 #13 (Phase 2 if not ready at launch) | Operations | Tom |

**10DLC registration is the highest-priority pre-launch hygiene item** — 4–6 week approval timeline gates reliable SMS deliverability. Start immediately if not already underway.

## What does NOT exist as design output

This is worth being explicit about. Pass 1–4 produced specs and patterns — not visual mockups in the traditional sense. **What you have:**

- Pass 1 design tokens as actual code-ready files
- Pass 2 SVG sitemaps for web and mobile
- 16 spec files at Pass 4 close (7 Pass 3 flow specs + 14 Pass 4 surface specs accounting for paired specs + Settings IA framework + Tier 1.5 extension)
- 3 interactive HTML prototypes (Flows 1, 6, 7) for visual reference on the most complex flows
- ASCII art mockups embedded in spec docs for layout reference
- Component patterns + token usage documented across all specs

**What you do NOT have:**

- Figma or equivalent visual design files
- Pixel-perfect screen designs for every surface
- Component library implementations (the components themselves — `<EmptyState>`, `<InFlightSyncIndicator>`, `<NotificationBanner>`, etc. — are spec'd but not coded)
- Interactive prototypes for the 11 surfaces beyond Flows 1, 6, 7

**This was deliberate.** The four-pass framework explicitly traded "comprehensive visual mockups" for "comprehensive design specifications." Every surface has decisions locked, patterns identified, backend additions captured — but the actual visual rendering happens during frontend coding using the Pass 1 tokens. ASCII art mockups in spec docs are *layout sketches* that frontend implementers translate into code.

**For frontend coding**: when a developer (or AI agent like Claude Code) implements a surface, they read the relevant spec, apply the Pass 1 tokens, implement components per the spec catalogs, and the screens emerge. There's no "Figma → developer translates" step because the spec docs already capture all decisions a designer would have made.

**If richer visual artifacts are desired later**, that would be an optional new phase ("Pass 5: Visual Design Implementation" or similar) building Figma mockups for each of the 14 surfaces. This is defensible but optional — many AI-first products skip Figma entirely and let design tokens + spec docs drive frontend implementation directly. Recommended approach: skip dedicated visual mockup phase. If during implementation specific surfaces need more visual prototyping, do it just-in-time per-surface rather than as a comprehensive phase.

## Implementation phase — what comes next

The four-pass design framework is complete. Five workstreams now drive MVP launch:

### 1. Backend implementation (largest workstream)

**Scope**: A1–A88 from the v6 backend additions ledger. Cumulative ~259–334.5 days of work.

**A1 already implemented** (Scheduling & Dispatch). All other additions are pending.

**Recommended phasing** (per backend ledger v6 implementation guidance):

- **Wave 1 — foundational**: A39 (idempotency UUIDs), A40 (conflict severity classification), A53 (three-tier resolution chain), A52 (settings catalog), A55 (per-user overrides) — patterns used everywhere downstream
- **Wave 2 — Pass 3 features**: A2–A46 — bulk of MVP feature backlog
- **Wave 3 — Pass 4 Tier 1 + Tier 1.5**: A47–A51 (conflict resolution surfaces), A59–A66 (SMS infrastructure)
- **Wave 4 — Pass 4 Tier 2 + Tier 3**: A56–A58 (notification preferences), A67–A78 (settings, account, onboarding)
- **Wave 5 — Pass 4 Tier 4**: A79–A88 (sync indicator polish, customer-facing public surfaces, help system)

**External dependencies that block delivery** (non-engineering):

- A2P 10DLC registration (4–6 weeks; blocks SMS deliverability at scale)
- Stripe account setup and webhook configuration
- Domain registration (`pilotfortrades.com`, optional `pilot.tr` short-link)
- SendGrid (or chosen email provider) sender domain SPF/DKIM/DMARC setup
- Legal copy authoring (ToS, Privacy, EULA) for A74 acceptance flow
- Help content authoring (~60 articles) for A85 corpus

### 2. Frontend coding

**Scope**: build the actual web (Next.js 16 + shadcn/ui) and mobile (Expo SDK 54 + Gluestack-UI) apps from Pass 1–4 design specs.

**Approach**: per-surface implementation reading spec docs + applying Pass 1 tokens + implementing components per the catalogs. Component library work (the `<EmptyState>`, `<InFlightSyncIndicator>`, `<NotificationBanner>`, `<MFAEnrollmentWizard>`, etc.) is real work that runs alongside per-surface implementation.

**Begins**: after backend foundation stable (Wave 1 + early Wave 2 of backend work). Some surfaces can be developed in parallel with later backend waves.

**Component library scope**: estimated ~30 reusable components across the 14 surfaces. The states catalog from Tier 3 #8/#9 alone produces 20 components (12 state catalog entries + 8 first-time-user variants).

### 3. Pre-launch hygiene

**Scope**: see the Pre-launch hygiene track table above. Mix of operational, content, and legal work.

**Critical-path items**:

- A2P 10DLC registration (start immediately; 4–6 weeks)
- Help corpus content authoring (~60 articles; can start before frontend coding)
- 16 email template content (paired with Tier 4 #13 visual design which is locked)
- Legal copy review (ToS, Privacy, EULA)

**Most other items can run in parallel** with backend or frontend work.

### 4. Beta testing

**Target**: 5–10 hand-selected electrical contractors as beta testers.

**Prerequisites before beta**:

- Backend MVP work substantially complete (target: A1–A88 implemented + tested)
- Frontend coding substantially complete for the 14 Pass 4 surfaces
- Pre-launch hygiene critical-path items complete (10DLC approved; legal copy reviewed; help corpus authored)
- Beta tester onboarding plan operationalized

**Beta scope**: real workflow validation. Tom recruits tenants, supports them directly via help feedback channel (per Tier 4 #14 email-based support), iterates on bugs and friction points. Beta typically 4–8 weeks before soft launch.

### 5. Soft launch

**Target**: 25+ paying customers.

Standard SaaS launch motions: marketing site live; sales channel (whatever Tom decides); operational readiness for self-service signup; support channel handling production support load.

### Sequencing visualization

```
Pass 1 (done) → Pass 2 (done) → Pass 3 (done) → Pass 4 (done)
                                                       │
                            PRD v3.1 final (✓) + Arch doc v5 (✓) + Backend ledger v6 (✓)
                                                       │
                            Backend MVP work (A1–A88; 259–334.5 days; in waves)
                                                       │
                            Frontend coding (begins as backend foundation stabilizes;
                                            runs in parallel with backend Waves 2+)
                                                       │
                            Pre-launch hygiene (parallel; 10DLC critical-path)
                                                       │
                            Beta testing (5–10 electrical contractors; 4–8 weeks)
                                                       │
                            Soft launch (target: 25+ paying customers)
```

## What backend implementation reads

For backend AI agents and developers, the canonical sources of truth are:

| Document | Purpose | Current version |
| :--- | :--- | :--- |
| `mvp-arch.md` | Architecture and patterns; engineering source of truth | v5 |
| `mvp-prd.md` | Product requirements; feature scope and behavior | v3.1 (final) |
| `backend-mvp-additions.md` | Cumulative backend additions ledger; A1–A88 | v6 |
| Per-surface design specs in `dev-docs/architecture-design/` | Locked design decisions per surface | (see Pass 4 surfaces produced) |

**This framework doc is design-team scoped.** Backend implementation pulls engineering input from the four documents above. The framework doc is for status awareness and historical context.

**Sequencing guidance for backend implementation**:

1. **Safe to start**: A1–A88 are all locked. No further design changes affecting any addition.
2. **Implement patterns centrally, not per-endpoint**: pre-commit staleness check (§16.4), system-default-with-tenant-override (§16.5), four-class severity (§16.6), pre-commit staleness payload variants (§16.10), notification rate limiting (A35), idempotency UUIDs (A39), three-tier resolution chain (§16.5 / Settings IA framework), carrier-agnostic adapter (§17.1), in-flight sync indicator (§16.13).
3. **Start with foundational additions** (Wave 1 above) before working on additions that depend on them.
4. **External dependencies block delivery, not development**: 10DLC registration, Stripe setup, etc. Code can be built and tested with mocks; production deployment requires the external dependencies in place.

## How this doc gets updated

This is rewrite #3 (and the third anticipated rewrite for MVP). With Pass 4 design phase complete, the doc's role shifts from "tracking what's locked vs. pending" to "documenting what was produced and pointing forward to implementation."

Future updates anticipated:

- **Touch-up at MVP launch**: implementation phase complete; final state captured (which features actually launched, any descoped items, post-launch roadmap)
- **Phase 2 framework doc**: when Phase 2 design begins (vertical expansion to plumbing/HVAC, advanced features deferred from MVP), a new framework doc captures Phase 2 scope. The MVP framework doc becomes archived reference material.

Between now and MVP launch, the framework doc gets minor touch-ups only — version bumps for canonical docs (PRD, arch, ledger), implementation-phase milestone markers (backend Wave N complete, frontend per-surface complete, beta started, etc.).

## Final reflections — what the design framework achieved

For the record at Pass 4 close:

- **16 design specs delivered** across four passes, plus the Settings IA framework prerequisite and Tier 1.5 customer comms extension
- **88 backend additions** documented with effort estimates and cross-references — ~259–334.5 days of MVP backend work captured
- **16 platform UX patterns** formalized in arch doc §16, providing the vocabulary for Phase 2 inheritance
- **Seven new platform-level patterns introduced in Pass 4** (mobile-to-web escalation, bilateral integration conflict resolution generalized, background sync execution, carrier-agnostic adapter, subscription quota with cap, lazy provisioning, in-flight sync indicator) — vocabulary the platform now speaks
- **Strategic deferrals** documented explicitly with Phase 2 rationale rather than silently carried (customer registration, ticket system, full template editing, multi-language UI, Stripe Connect direct-to-tenant routing, etc.)
- **Three canonical docs consolidated at Pass 4 close**: PRD v3.1 final, Arch doc v5, Backend ledger v6 — each is the design-frozen artifact backend implementation works against

The MVP scope is locked. Implementation begins. The design framework's job is done.
