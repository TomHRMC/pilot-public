# Pilot for Trades Design System — Pass 4, Tier 3 #8 + #9: States Catalog + First-Time-User States

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Empty / loading / error state treatments for every Pass 1–3 flow plus Pass 4 surface, plus first-time-user empty states with onboarding hooks. Shape B deliverable per Pass 4 framework — pattern guide plus two application matrices.
**Depends On**: Pass 1 design tokens · all Pass 1–3 flow specs · all Pass 4 Tier 1, Tier 1.5, Tier 2 specs · Settings IA framework
**Backend additions**: A72 (first-session tracking — small)
**Deliverable shape**: Shape B (Pattern guide + application matrix) per Pass 4 framework doc

---

## Purpose

Pass 1–3 + Pass 4 Tier 1–2 designed the happy paths. Tier 3 #8 + #9 fills in everything between — what users see when there's no data, when data is loading, when errors occur, and when they're new to the product and need onboarding hooks woven into otherwise-empty surfaces.

The temptation here is to spec each state per flow. That would produce 14 separate state specs that drift visually over time as different designers (or AI tools) interpret "loading" slightly differently in each context. Wrong approach.

The right approach: **define each state treatment once with token usage, component patterns, and copy guidance. Then map every flow / surface to which catalog entry applies.** This is Shape B per the Pass 4 framework — a single catalog plus an application matrix.

Two catalogs in this spec:

1. **States catalog** — 12 distinct treatments across empty, loading, and error categories
2. **First-time-user states catalog** — 8 first-time-relevant treatments (subset of empty states, plus onboarding hooks)

Plus two application matrices mapping the 14 surfaces to which treatments apply.

This is the second-shortest spec in Pass 4 by intent (behind Tier 4 #12 which is an addendum). The page count comes from the application matrix, not from prose — most of the design thinking is in the catalog itself.

## Strategic direction

### Define once; apply everywhere

Pilot's UI grows through the 14 specs we've built so far and will continue growing. If each surface defines its own loading treatment, the platform fragments visually and operationally — different skeleton animations, different error copy patterns, different empty-state imagery. The states catalog locks these decisions once.

### Empty states aren't all the same

Five distinct kinds of "no data" exist across Pilot, and they carry different meanings:
- *No data ever* — genuine first-time-user state, calls for onboarding hooks
- *No data right now* — filter applied or time-bounded view, calls for "adjust filter" or "expand range" affordances
- *No data because action blocked* — RBAC denial or feature off, calls for explainer not action
- *No data due to network* — sync hasn't completed, calls for retry affordance
- *No data after action* — user just deleted everything, calls for confirmation that the action worked

Conflating these into one "empty state" pattern produces wrong UX. Each type calls for different copy, different affordances, different visual weight.

### Loading states span three temporal scales

Not all loading is the same:
- *Page-level loading* (>500ms) — page skeleton with shimmer
- *In-flow loading* (50ms–2s) — inline spinner with progress copy
- *Background activity* (continuous) — small persistent indicator without blocking interaction

These need different visual weight. A page skeleton for a 100ms operation feels broken; an inline spinner for a 5-second operation feels stuck.

### Error states have severity classes that map to user response

Four error severity classes map to the four-class severity pattern from arch doc §16.6 (formalized for sync conflicts) but applied to errors generally:
- *Recoverable transient* — retry button, no other context needed
- *Recoverable user-action* — fix input or change something on the page
- *Recoverable session* — session expired, re-auth flow
- *Unrecoverable* — data integrity issue or severe failure, contact support

Each maps to a different visual treatment and a different recovery path.

### First-time-user states get richer treatment than ongoing-empty states

A first-time tenant signing in for the first time deserves a welcoming experience with onboarding hooks. A returning tenant who happened to delete all their customers and is briefly empty deserves a neutral "nothing here yet" with a normal create affordance. Same data shape (empty list); different states; different visual treatments.

The first-time-user matrix only applies to surfaces where "no data ever" is the expected initial state (no jobs yet, no customers yet, etc.). Surfaces where the data shape is inherently bounded (audit log, integration sync log) don't have first-time states because they're empty for everyone briefly until activity occurs.

## States catalog

Twelve treatments organized by category. Each treatment has: visual specification, copy template, affordance pattern, token usage, and component reference.

### Empty state treatments (5)

#### E1. Empty — No data ever (use first-time-user variant from F1–F8 if applicable)

**When to use**: a list that has never had data in this tenant. Falls back to first-time-user variant when the user is in their first session per A72.

**Visual**:
- Centered card-like container with neutral 1px border, neutral-50 background
- Subtle illustration (lucide icon at 64px, neutral-400 fill) representing the entity type
- Heading: "No [entity type] yet" (neutral-900, text-lg, font-medium)
- Body: 1–2 lines explaining what this list will hold (neutral-600, text-sm)
- Primary CTA button (brand-indigo, full text label like "Create your first customer" or "Add a job")

**Copy template**:
> No [customers / jobs / quotes / etc.] yet
>
> Once you [create / add / receive] one, it'll appear here.
>
> [Create your first [entity]]

**Token usage**: `bg-neutral-50`, `border-neutral-200`, `text-neutral-900`, `text-neutral-600`, `text-brand-indigo`

**Component reference**: `<EmptyState variant="first-time" entity="..." />`

#### E2. Empty — No data right now (filter applied)

**When to use**: a list where data exists in this tenant but the current filter / time range / search query produces no results.

**Visual**:
- Similar centered container as E1, slightly less visually prominent (smaller container, no illustration)
- Heading: "No [entity type] match"
- Body: explains what filter is filtering it out, specific to context
- Two affordances: "Clear filter" (neutral text button) and "Expand date range" (neutral text button) — context-dependent

**Copy template** (varies by filter type):
> No customers match "Smith"
> Try a different search or [Clear search]
>
> No jobs in the last 7 days
> Try [Expand to last 30 days] or [Clear date filter]

**Token usage**: `bg-neutral-25`, `text-neutral-700`, `text-brand-indigo` (links)

**Component reference**: `<EmptyState variant="filter-applied" filterType="..." />`

#### E3. Empty — No data because action blocked (RBAC or feature off)

**When to use**: the user lacks permission to see data, or a feature is disabled at tenant level.

**Visual**:
- Same container as E1 but with informational tint (neutral background)
- Lock icon (lucide, 32px, neutral-400)
- Heading: explains the block — "You don't have access to this" or "[Feature] is turned off for your team"
- Body: tells user what to do — "Ask your owner to enable [feature]" or "Owner-only feature"
- No primary CTA — this isn't a state the user can resolve themselves
- Optional secondary "Learn more" link to help article

**Copy template**:
> [Feature] is turned off for your team
>
> Your owner can enable this in Settings.
>
> [Learn more]

**Token usage**: `bg-neutral-50`, `text-neutral-700`, `text-brand-indigo` (Learn more)

**Component reference**: `<EmptyState variant="blocked" reason="..." />`

#### E4. Empty — No data due to network (sync incomplete)

**When to use**: list is empty because data hasn't been fetched yet (network failure, sync queued, or initial sync incomplete).

**Visual**:
- Same container, with offline / cloud-down icon (lucide, 32px, alert-amber)
- Heading: "Couldn't load [entity type]"
- Body: brief explanation appropriate to the cause (offline, sync queued, etc.)
- Primary CTA: "Try again" (brand-indigo)
- For mobile when offline: "Working offline — synced data appears here when you reconnect"

**Copy template**:
> Couldn't load customers
>
> Check your connection and try again.
>
> [Try again]

**Token usage**: `bg-alert-amber-50`, `border-alert-amber-200`, `text-neutral-900`, `text-brand-indigo`

**Component reference**: `<EmptyState variant="network-incomplete" />`

#### E5. Empty — No data after action (just-deleted or just-completed)

**When to use**: user just performed an action that emptied the list (deleted last item, archived everything, completed all tasks).

**Visual**:
- Briefer treatment than E1–E4 — this is a transient acknowledgment, not a long-lived state
- Heading: "All done!" or "Nothing left here"
- Body: confirms the action — "You've completed all assigned jobs for today" or "All quotes archived"
- Optional CTA: "View archive" or "See all" (text link, neutral)
- Auto-dismisses if user navigates away; doesn't persist

**Copy template**:
> All done!
>
> You've completed all assigned jobs for today.
>
> [View archive]

**Token usage**: `bg-margin-50`, `text-margin-700`, `text-brand-indigo` (link)

**Component reference**: `<EmptyState variant="post-action" actionType="..." />`

### Loading state treatments (3)

#### L1. Page-level skeleton (>500ms operations)

**When to use**: route changes, large queries, initial page load. Anything where the user's expected wait is >500ms.

**Visual**:
- Skeleton placeholders matching the page's actual layout structure
- Neutral-100 background blocks with subtle shimmer animation (1.5s loop, brand-indigo-tinted gradient)
- Skeleton matches at component level: a list shows skeleton list rows; a chart shows skeleton bars; a form shows skeleton fields
- Skeleton respects the Pass 1 token system — same spacing, same border radius, same proportions as the real content

**Copy**: none. Skeletons don't show text labels. Rendering text "Loading..." adds visual noise.

**Timing**: skeleton appears within 100ms of the request firing. If the request resolves within 100ms, the skeleton never renders (avoids the flash-of-skeleton anti-pattern).

**Token usage**: `bg-neutral-100`, `bg-gradient-to-r from-neutral-100 via-brand-indigo-50 to-neutral-100` for shimmer

**Component reference**: `<PageSkeleton layout="list|chart|form|detail" />`

#### L2. In-flow progress (50ms–5s operations)

**When to use**: discrete user actions that take perceptible time but aren't full page loads. Voice processing, sending a quote, syncing one queue item, generating a report.

**Visual**:
- Inline spinner (lucide loader-2 with rotation animation, brand-indigo)
- Adjacent progress copy that's specific to the action
- Disables the triggering button or surface during the operation
- For longer operations (>2s), the copy can update with intermediate state ("Listening..." → "Processing..." → "Confirming...")

**Copy template** (action-specific):
> [● spinner] Sending your quote...
> [● spinner] Listening...
> [● spinner] Generating PDF...

**Timing**: appears immediately on action trigger. If operation completes within 50ms, the spinner shouldn't visibly render (prevents flicker).

**Token usage**: `text-brand-indigo`, `text-neutral-700` (label)

**Component reference**: `<InlineProgress action="..." />`

#### L3. Background activity indicator (continuous, non-blocking)

**When to use**: persistent operations that don't block interaction. SSE connection state, sync queue activity, voice listening session, integration sync polling.

**Visual**:
- Small dot or icon in a fixed position (typically top-right of the relevant zone or in app shell)
- Color carries meaning: green dot for healthy, amber for warning, red for error
- Optional label on hover/tap with last-update time
- Does not block any interaction — user can do anything while this indicator runs

**Copy template** (on hover):
> Syncing · last updated 12s ago
> Connected · all systems normal
> Working offline · 5 items queued

**Token usage**: `bg-margin-500` (healthy), `bg-alert-amber-500` (warning), `bg-fault-500` (error)

**Component reference**: `<BackgroundIndicator state="healthy|warning|error|offline" />`

### Error state treatments (4)

#### Er1. Error — Recoverable transient (retry)

**When to use**: network failure, server 5xx, temporary backend hiccup. Errors that may resolve on retry without user intervention.

**Visual**:
- Centered card (similar to E1) with alert-amber tint
- Alert icon (lucide alert-triangle, alert-amber-500)
- Heading: "Something went wrong"
- Body: brief description (specific if known, generic otherwise)
- Primary CTA: "Try again" (brand-indigo)
- Optional "Cancel" or "Go back" (neutral text)

**Copy template**:
> Something went wrong
>
> We couldn't load your customers. The connection might be having a hiccup.
>
> [Try again]   [Cancel]

**Token usage**: `bg-alert-amber-50`, `border-alert-amber-200`, `text-neutral-900`

**Component reference**: `<ErrorState variant="transient" retryAction={...} />`

#### Er2. Error — Recoverable user-action (fix input)

**When to use**: validation errors, conflict-with-existing-data, business-rule violations. Errors that require the user to change something on the form/page.

**Visual**:
- Inline error treatment, not full-page — appears at the form field or section level
- Red text + small alert icon next to the offending field/section
- Helper text below the field explaining what's wrong and how to fix it
- The form's primary action button stays disabled until the error is resolved

**Copy template** (field-specific):
> Phone number is required for SMS notifications
> Discount can't exceed 15% (your tenant max)
> This customer already has an open quote — try editing the existing one

**Token usage**: `text-fault-700`, `border-fault-300` (input border on error)

**Component reference**: `<FieldError field="..." message="..." />`

#### Er3. Error — Recoverable session (re-auth)

**When to use**: session expired, refresh token invalid, MFA required mid-session.

**Visual**:
- Modal-feeling overlay (preserves user's current page state behind the modal)
- Lock icon (lucide lock, alert-amber-500)
- Heading: "Sign in to continue"
- Body: brief explanation that the session expired and current work is preserved
- Primary CTA: "Sign in" (brand-indigo) — opens the login flow as a sub-modal
- After successful re-auth, the user returns to exactly where they were

**Copy template**:
> Sign in to continue
>
> Your session expired. Don't worry — your work is saved.
>
> [Sign in]

**Token usage**: `bg-neutral-900` overlay (40% opacity), `bg-white` modal, `text-neutral-900`

**Component reference**: `<SessionExpiredModal returnPath={...} />`

#### Er4. Error — Unrecoverable (contact support)

**When to use**: data integrity errors, catastrophic failures, situations where retry won't help.

**Visual**:
- Centered card with fault-red border (more visually prominent than transient errors)
- Alert-circle icon (lucide alert-circle, fault-700)
- Heading: "Something serious went wrong"
- Body: explains the situation; usually generic for security reasons
- Primary CTA: "Contact support" (brand-indigo) — opens email or support form
- Reference ID below the error (so support can look up the specific occurrence)

**Copy template**:
> Something serious went wrong
>
> We couldn't complete this action. Our team has been notified.
>
> [Contact support]
>
> Reference ID: ERR-2026-04-27-XK29-A4F2

**Token usage**: `bg-fault-50`, `border-fault-300`, `text-fault-900`, `text-neutral-600` (reference ID)

**Component reference**: `<ErrorState variant="unrecoverable" referenceId={...} />`

## First-time-user states catalog

Eight first-time-user variants, each tied to a specific entity type that's empty in the user's first session. These supersede the generic E1 treatment when the user is in their first session per A72 below.

Common pattern across all eight:
- Larger container (~1.5x the standard E1 dimensions)
- Welcoming tone in copy
- Onboarding hook that ties to the next logical action
- Optional secondary "Skip for now" or "Watch a quick tour" link
- Lucide icon at 96px (larger than E1's 64px), brand-indigo-500 fill

### F1. First-time — No customers yet

> Welcome to Pilot for Trades!
>
> Customers are at the center of your work. Add your first one to get started — you can import from QuickBooks, paste a list, or add them one by one.
>
> [Add a customer]   [Import from QuickBooks]   [Skip for now]

### F2. First-time — No jobs yet

> Time to schedule your first job
>
> Jobs are how you track what your team is working on. Schedule one for today, this week, or whenever — it'll appear here.
>
> [Schedule a job]   [Watch a quick tour]

### F3. First-time — No quotes yet

> Create your first quote
>
> Quotes get sent to customers and turn into jobs once accepted. You can use a template or build one from scratch.
>
> [Create a quote]   [Use voice — say "create quote"]

### F4. First-time — No team members yet (solo operator)

> Just you for now? That's fine.
>
> Pilot works great for solo operators. When you're ready to add a team member, you can invite them from here.
>
> [Invite a team member]   [Continue solo]

### F5. First-time — No invoices yet

> Invoices appear here once jobs are completed
>
> Once you've completed a job, the invoice flow turns it into something the customer can pay.
>
> [Show me how this works]

### F6. First-time — No reports yet (data accumulation)

> Reports come alive after a few weeks of activity
>
> Once you've got jobs, quotes, and invoices flowing, the profitability and operational reports here will be useful. Check back after a few weeks.
>
> [Take a tour of the reports]   [Sample report walkthrough]

### F7. First-time — No customer messages yet

> Customer messages will appear here
>
> When you text customers from Pilot or they reply to your messages, you'll see the conversation here. Try sending a templated "On my way" message to get started.
>
> [Send a templated message]

### F8. First-time — No catalog items yet

> Set up your catalog to speed up quoting
>
> Add the materials and services you commonly use, with prices and markups. Once your catalog is set up, building quotes takes seconds.
>
> [Add catalog items]   [Import from supplier]   [Skip for now]

## Application matrix — states (Pass 1–3 + Pass 4)

Each row is a flow or surface. Columns map to which catalog entry applies for each state type. "—" means the state is N/A for that surface (e.g., a static settings page doesn't have a "no data" empty state).

| Surface | Empty (no data) | Empty (filter) | Empty (blocked) | Empty (network) | Loading (page) | Loading (in-flow) | Loading (background) | Error (transient) | Error (validation) | Error (session) | Error (unrecoverable) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Pass 3 Flow 1 — Voice quote creation | E1 | — | E3 | E4 | L1 | L2 | L3 | Er1 | Er2 | Er3 | Er4 |
| Pass 3 Flow 2 — Profitability drill-down | E1 | E2 | E3 | E4 | L1 | L2 | L3 | Er1 | — | Er3 | Er4 |
| Pass 3 Flow 3 — Dispatch board | E1 | E2 | E3 | E4 | L1 | L2 | L3 | Er1 | Er2 | Er3 | Er4 |
| Pass 3 Flow 4 — Customer comms (outbound) | — | — | E3 | E4 | — | L2 | L3 | Er1 | Er2 | Er3 | Er4 |
| Pass 3 Flow 5 — Quote approval workflow | E1 | E2 | E3 | E4 | L1 | L2 | L3 | Er1 | Er2 | Er3 | Er4 |
| Pass 3 Flow 6 — Calendar conflict resolution | E5 | E2 | E3 | E4 | L1 | L2 | L3 | Er1 | — | Er3 | Er4 |
| Pass 3 Flow 7 — Offline-to-online sync | E5 | — | — | E4 | — | L2 | L3 | Er1 | — | Er3 | Er4 |
| Pass 4 Tier 1 #1 — Owner mobile-conflict UI | E5 | E2 | E3 | E4 | L1 | L2 | L3 | Er1 | — | Er3 | Er4 |
| Pass 4 Tier 1 #2 — QuickBooks conflict UI | E5 | E2 | E3 | E4 | L1 | L2 | L3 | Er1 | — | Er3 | Er4 |
| Pass 4 Tier 1 #3 — Background sync | — | — | E3 | E4 | — | — | L3 | Er1 | — | Er3 | Er4 |
| Pass 4 Tier 1.5 — Customer comms extension | E1 | — | E3 | E4 | L1 | L2 | L3 | Er1 | Er2 | Er3 | Er4 |
| Pass 4 Tier 2 #4 — Configurable thresholds | — | — | E3 | E4 | L1 | L2 | — | Er1 | Er2 | Er3 | Er4 |
| Pass 4 Tier 2 #5 — Notification preferences | — | — | E3 | E4 | L1 | L2 | — | Er1 | Er2 | Er3 | Er4 |
| Pass 4 Tier 2 #6 — Voice persona tone | — | — | E3 | E4 | L1 | L2 | — | Er1 | Er2 | Er3 | Er4 |
| Pass 4 Tier 2 #7 — Account settings | — | — | E3 | E4 | L1 | L2 | L3 | Er1 | Er2 | Er3 | Er4 |

### Per-surface notes (only where non-trivial)

**Pass 3 Flow 1 (Voice quote creation)**: in-flow loading L2 has multiple sub-states during voice processing (Listening / Processing / Confirming) per Flow 1's six-state voice machine. The states catalog L2 entry covers the visual treatment; the substates are flow-specific copy.

**Pass 3 Flow 3 (Dispatch board)**: the calendar grid view, the conflict modal, and the resolution panel each have their own loading skeleton variants per L1. The dispatch board's full-screen mode disables L3 background indicators per Tier 2 #5 Decision 8 (in-app banners suppressed during full-screen flows).

**Pass 3 Flow 6 / Pass 4 Tier 1 #1, #2 (Conflict resolution surfaces)**: Empty state E5 (post-action) applies when a conflict was just resolved and the queue is empty. Subtle confirmation feel rather than welcoming feel.

**Pass 3 Flow 7 (Offline-to-online sync)**: queue surface uses E5 when queue empties (synced everything); E4 when offline. L2 (in-flow) for individual queue item processing; L3 (background) for ongoing sync activity. Er2 (validation) doesn't apply here — sync errors are transient or unrecoverable, not user-fixable.

**Pass 4 Tier 1 #3 (Background sync)**: this surface is mostly system-design with thin UI. The settings sub-page itself uses Tier 2 #4 patterns. The "last sync attempt" indicator on the queue surface uses L3 with status-aware coloring.

**Pass 4 Tier 1.5 (Customer comms extension)**: free-form reply composition uses L2 during voice transcription and during message send. Conversation thread screen uses L1 for initial load and L3 for SSE-driven incremental updates.

**Pass 4 Tier 2 #4–#7 (Settings surfaces)**: most settings surfaces don't have meaningful "empty" states because settings always have a value (system default if nothing else). The "No data" empty states are universally `—` (N/A) for these surfaces. Loading and error states all apply.

## Application matrix — first-time-user states

Only surfaces with first-time-relevant states. First-time-user states supersede E1 (generic empty) when the user is in their first session per A72.

| Surface | First-time treatment |
| :--- | :--- |
| Pass 3 Flow 2 — Profitability drill-down | F6 (Reports come alive after a few weeks) |
| Pass 3 Flow 3 — Dispatch board (no jobs yet) | F2 (Schedule your first job) |
| Pass 3 Flow 4 — Customer comms (no messages yet) | F7 (Customer messages appear here) |
| Pass 3 Flow 5 — Quote approval (no quotes yet) | F3 (Create your first quote) |
| Customers list (no customers yet — surface across all flows referencing customers) | F1 (Welcome — add your first customer) |
| Jobs list (no jobs yet — surface across all flows referencing jobs) | F2 (Schedule your first job) |
| Invoicing (no invoices yet) | F5 (Invoices appear after job completion) |
| Users & Roles (solo operator, no team yet) | F4 (Just you for now? That's fine) |
| Catalog (no catalog items yet) | F8 (Set up your catalog) |
| Pass 4 Tier 2 #5 — Notification preferences | — (defaults exist; never first-time-empty) |
| Pass 4 Tier 2 #7 — Account settings (Active sessions has 1 entry — current session) | — (always at least 1 session) |
| Pass 4 Tier 2 #4–#6 — All settings surfaces | — (settings always have values) |

## Component patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| `<EmptyState>` component with 5 variants | **NEW** | — |
| `<FirstTimeEmptyState>` component with 8 variants | **NEW** | — |
| `<PageSkeleton>` with layout-aware variants | **NEW** | Pass 1 design tokens |
| `<InlineProgress>` for action-scoped loading | **NEW** | Pass 1 voice state machine pattern |
| `<BackgroundIndicator>` for continuous activity | **NEW** | — |
| `<ErrorState>` with 4 variants | **NEW** | Arch doc §16.6 four-class severity (extended from sync to errors generally) |
| `<FieldError>` for validation errors | **NEW** | — |
| `<SessionExpiredModal>` for re-auth flows | **NEW** | — |
| Skeleton-flicker prevention (100ms threshold) | **NEW** | — |
| Spinner-flicker prevention (50ms threshold) | **NEW** | — |
| Reference ID surfacing on unrecoverable errors | **NEW** | — |
| First-time-user-aware empty state rendering | **NEW** | — |

Twelve new component patterns. Most of these are component-library work — implementing the catalog produces a set of reusable components that every Pass 1–4 surface consumes. The components are the deliverable; the catalog is the spec.

## Cross-domain considerations

### A. The catalog is implemented as a component library, not duplicated per flow

Each catalog entry maps to a single React/Gluestack component in `packages/ui/src/states/`. Every flow imports the appropriate component rather than implementing its own. This is the central enforcement mechanism for the "define once, apply everywhere" principle.

Component naming follows the catalog IDs: `<EmptyStateE1>` through `<EmptyStateE5>`, `<LoadingL1>` through `<LoadingL3>`, `<ErrorEr1>` through `<ErrorEr4>`. Plus `<FirstTimeEmptyF1>` through `<FirstTimeEmptyF8>`. Component IDs match the catalog IDs for traceability.

### B. First-time-user detection requires backend support

Determining whether a user is in their "first session" requires backend tracking. A72 below covers this — a small `user_session_history` table that tracks the user's first login timestamp and total session count. Frontend queries this once on app load and uses the result to decide between E1 and F1–F8 rendering.

A user is considered "first-time" if their total session count is ≤ 3 OR their first login was within the past 7 days. This handles the common case where a new user logs in a few times during onboarding without losing the first-time experience too quickly.

### C. Empty state copy is content work; designs reserve space

The catalog entries above include suggested copy templates. Final copy authoring is content work, not design work — Tom owns final wording. The design reserves the structural pattern (heading + body + CTA) and the visual treatment; copy fills in.

This is parallel to how the Pass 4 framework handles legal copy in pre-launch hygiene — design locks the surface, content fills in.

### D. Skeleton component requires layout knowledge per page

`<PageSkeleton layout="...">` needs a layout type parameter because skeleton content should match the actual page structure. Five layout types cover MVP needs:
- `list` — row-based skeleton for list views
- `chart` — bar/line skeleton for chart-heavy pages
- `form` — field-row skeleton for forms
- `detail` — card-grouped skeleton for detail views
- `dashboard` — multi-widget grid skeleton

Phase 2 may add more layout types as new page archetypes emerge.

### E. Error reference IDs are operational infrastructure

Er4 (unrecoverable errors) surfaces a reference ID. The format is `ERR-YYYY-MM-DD-XXXX-XXXX` where the trailing characters are a unique identifier mapping to a server-side log entry. The user provides this to support; support looks it up in logs.

Backend infrastructure: every Er4-class error (severe failures, data integrity issues) generates a log entry tagged with the reference ID at the moment the error fires. The frontend receives the reference ID in the API error response payload. This is a small backend addition (maybe 1 day of work) — captured as part of the existing logging infrastructure rather than a new addition.

### F. Tier 4 polish refinements may apply

Tier 4 #12 (dispatch board sync indicator amber-with-count refinement) is an addendum to Flow 3 that touches the L3 background indicator visual specifically. Tier 4 #12 inherits this catalog's L3 entry and refines it for the specific dispatch board case. No conflict between this spec and Tier 4 #12.

Tier 4 #13 (customer-facing public link styling) and Tier 4 #14 (help/about/feedback) will reference this catalog when surfacing their own state treatments.

### G. Onboarding flow (Tier 3 #10) reuses first-time-user states heavily

The onboarding flow walks new tenants through initial setup. Each step that lands on a feature surface for the first time benefits from the F1–F8 first-time-user variants. Onboarding's job is to guide the user through setup; the first-time-user states' job is to welcome them when they arrive at any surface.

Tier 3 #10 will reference this spec for the first-time-user variants and will not redesign them.

### H. Audit log captures error reference IDs

Per Settings IA framework Cross-Domain G, Er4-class unrecoverable errors are captured in audit log with the reference ID. This makes support investigations efficient — owner can search audit log by reference ID to see what was happening at the time of the error.

### I. Mobile state treatments adapt visually

All catalog entries apply on both web and mobile. Mobile renders adapt for phone width:
- Empty state containers fill the viewport with appropriate padding
- Page-level skeletons match the mobile layout (vertical stacking, simpler grid)
- Error modals (Er3) become full-screen on mobile rather than overlay
- Background indicators move to the app shell top bar on mobile rather than a fixed page position

Component implementations handle the responsive variation; the catalog entries here cover the desktop visual; mobile adapts naturally.

### J. Translation-ready architecture for Phase 2 multi-language

Catalog entry copy templates are written as resource keys ready for i18n. Phase 2 multi-language work translates the keys without re-designing the components. Recommended key naming: `state.empty.first_time.no_customers.heading`, `state.error.transient.body`, etc.

## Deferred items (Phase 2 / for future iteration)

- **Animated illustrations for empty states** — Phase 2; static lucide icons in MVP
- **Custom error pages per error class** (404, 500 routing) — Phase 2; current Er1/Er4 cover most cases
- **Progressive loading** (show partial content while remaining loads) — Phase 2 optimization
- **Skeleton animation customization per tenant brand** — Phase 2; standard shimmer in MVP
- **Multi-step error recovery wizards** — Phase 2; current treatment links to support for unrecoverable errors
- **In-context tutorial overlays in empty states** — Phase 2 with onboarding tour features
- **Empty state A/B testing for activation** — Phase 2 once analytics infrastructure exists
- **Localized first-time copy variants** — Phase 2 with multi-language UI
- **Error rate dashboards for owner** — Phase 2; reference IDs in MVP, no aggregate visibility yet
- **First-time user "tour" feature** with coach marks — Phase 2; Tier 3 #9 provides empty-state hooks but not full tours

## Validation checklist

Before implementation begins:

- [ ] All 12 catalog entries (E1–E5, L1–L3, Er1–Er4) implemented as components in `packages/ui/src/states/`
- [ ] All 8 first-time-user variants (F1–F8) implemented as components
- [ ] Component IDs match catalog IDs (`<EmptyStateE1>`, `<LoadingL1>`, etc.)
- [ ] PageSkeleton layout variants implemented (list, chart, form, detail, dashboard)
- [ ] Skeleton-flicker prevention tested (100ms threshold)
- [ ] Spinner-flicker prevention tested (50ms threshold)
- [ ] Application matrix reviewed against existing flows — every cell verified
- [ ] First-time-user matrix reviewed for surfaces where F-variants apply
- [ ] A72 first-session detection endpoint specified
- [ ] Backend logging integration for Er4 reference IDs verified
- [ ] Mobile-responsive variants tested for all 12 + 8 components
- [ ] Copy templates committed (Tom-owned) for production-ready content
- [ ] i18n key naming scheme documented for Phase 2 readiness

## Backend additions (new for Tier 3 #8 + #9)

### A72. First-Session Detection for First-Time-User States

**Triggered by**: Cross-Domain B — first-time-user state rendering requires backend tracking of session history.

**Scope**:
- New table `user_session_history`
  - `tenant_id` UUID
  - `user_id` UUID
  - `first_login_at` TIMESTAMPTZ
  - `total_session_count` INTEGER DEFAULT 0
  - `last_login_at` TIMESTAMPTZ
  - Unique on (tenant_id, user_id)
- Increment `total_session_count` on every successful login
- Set `first_login_at` only on the row's first creation
- API: `GET /api/v1/users/me/session-history` — returns the user's first_login_at and total_session_count
- Frontend uses this on app load to determine first-time-user status:
  - `isFirstTime = total_session_count <= 3 || first_login_at >= 7 days ago`
- Cached on the frontend for the session duration; refreshed on next login

**Effort estimate**: Small — 1–2 days. Schema + endpoint + login-flow integration.

### Total Tier 3 #8 + #9 backend additions

A72 (1–2 days) = **1–2 days**.

The vast majority of Tier 3 #8 + #9 implementation is frontend component work, not backend infrastructure. Component library implementation is estimated 8–12 days of frontend work, but this is component-library scope rather than backend-additions scope.

---

## What this surface does NOT cover

- The actual component-library implementation — that's frontend coding work, not design spec work
- Onboarding flow itself — Tier 3 #10
- Mobile push notification permission flow — Tier 3 #11
- Help system / coach marks / tours — Phase 2
- Multi-language i18n implementation — Phase 2
- Tenant-branded skeleton or empty-state customization — Phase 2

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A72 added (1 addition). Cumulative through Tier 3 #8 + #9: A1–A72.

**Backend day estimate update**:
- Pre-Tier-3-#8/#9 cumulative remaining MVP: 205–271.5 days
- Tier 3 #8 + #9 additions: 1–2 days
- New cumulative remaining MVP: **206–273.5 days**

**Frontend component-library work** (not in backend ledger but worth tracking): estimated 8–12 days for the 20 components covered by this catalog.

**Framework doc**: Tier 3 #8 and #9 status flips from `pending` to `locked`. Tier 3 continues with #10 (onboarding) and #11 (mobile push permission).

**No new arch doc patterns needed**: state treatments are frontend component patterns, not platform-level patterns. The catalog itself is the documentation.

**No new PRD additions**: state treatments are UX-implementation detail, not product feature scope.

## Next: Tier 3 #10 — Onboarding Flow

Tier 3 #10 is a Shape A full flow spec — substantially larger than this Tier 3 #8 + #9 deliverable. Onboarding walks new tenants through initial setup with guided steps that surface the tenant-configurable settings users need to know about. Inherits the F1–F8 first-time-user states from this catalog as the empty-state language for surfaces the user lands on during onboarding.

Estimated 500–650 lines per the framework's Shape A deliverable definition.

After Tier 3 #10, Tier 3 closes with #11 (mobile push notification permission request flow), then Tier 4 begins (#12 polish, #13 customer-facing styling, #14 help/about/feedback).
