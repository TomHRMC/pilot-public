# Pilot for Trades Design System — Pass 2: Information Architecture

**Version**: 1.0
**Status**: Locked
**Date**: April 22, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Domain-to-surface mapping, web sitemap, mobile sitemap, tablet strategy
**Depends On**: Pass 1 Foundation · `mvp-prd.md` · `mvp-arch.md`

---

## Purpose

Pass 2 maps Pilot's PRD feature domains to their appropriate surface (web, mobile, or shared) and produces navigable sitemaps for both apps. This is the load-bearing IA document — every screen designed in Pass 3+ lives at a known location in these trees.

## Strategic Direction

### Persona-Driven Surface Assignment

The web app is owner-primary. The mobile app is technician-primary with a progressive-disclosure owner tab for solo operators. Each domain is assigned to the surface(s) where its interactions make the most sense given the primary user and their physical context.

### Progressive Disclosure for Solo Operators

Mike the solo contractor is both technician and owner. Rather than building two apps or a role-detection split, the mobile app ships with four tabs visible to all roles (Today, Jobs, Voice, Code) and a fifth Owner tab conditionally rendered when the user's Cognito role is `owner`. Multi-person shops see this naturally — the tech's phone shows four tabs; the owner's phone shows five. Solo Mike gets all five.

### Vertical Expansion Safety

Tab names and route names use trade-neutral vocabulary where possible. The "Code" tab houses the NEC calculators for electrical MVP, but will accept plumbing pipe-sizing and HVAC duct calculators as content variants when those verticals onboard. No rename required for vertical expansion.

## Domain-to-Surface Mapping

The complete mapping across 14 domains (13 from PRD + Scheduling & Dispatch as net-new):

| # | Domain | Web | Mobile Tech | Mobile Owner | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| 3.1 | Audit & Compliance | ✓ view | — | — | Review-only; `Settings > Audit log` |
| 3.2 | Catalog & Pricing | ✓ manage | ✓ consume | — | Web manages markups, suppliers; mobile consumes pricing when quoting |
| 3.3 | CRM | ✓ primary | ✓ lookup | — | Full CRUD on web. Voice-create + lookup on mobile. Full mobile CRUD is Post-MVP. |
| 3.4 | Field Operations & Jobs | ✓ monitor | ✓ **PRIMARY** | — | The mobile app's reason to exist |
| 3.5 | Identity, Access, Tenant | ✓ admin | — | — | User management, RBAC setup |
| 3.6 | Invoicing & Billing | ✓ **PRIMARY** | — | ✓ send / view | Owner tab gets send-invoice and AR status |
| 3.7 | Notifications & Comms | ✓ config | ✓ receive | — | Web configures templates/channels; mobile receives push and sends templated customer comms |
| 3.8 | Platform Infrastructure | ✓ health | — | — | Admin observability; minimal UI for MVP |
| 3.9 | QuickBooks Integration | ✓ **PRIMARY** | — | ✓ status only | Conflict resolution stays web; mobile owner sees sync indicator and deep-links out |
| 3.10 | Sales & Quoting | ✓ build dense | ✓ voice create + submit | ✓ approve / send / discount | Quote approval workflow, owner margin cap, time-limited discounts |
| 3.11 | Subscriptions & Usage | ✓ primary | — | ✓ status link | Plan management on web; mobile owner sees usage indicator |
| 3.12 | Tax Calculation | ✓ config | — | — | Jurisdiction setup, tax-exempt config |
| 3.13 | Voice AI | ✓ transcripts + feedback + config | ✓ **PRIMARY** | — | Voice IS the mobile interface; web handles quality feedback loop |
| 3.14 | Scheduling & Dispatch | ✓ **PRIMARY** | ✓ consume | — | **New domain — see PRD addition below.** Calendar, dispatch, availability, route planning. Mobile tech sees "today's schedule" on Today tab. |

**Asymmetry summary**: Seven domains are web-primary with mobile-peripheral. Three are truly mobile-primary (Field Ops, Voice AI, Scheduling consumption). The rest are shared or admin-only. This matches the reality that **the web app IS the business** and **the mobile app is the field operation**.

## Key Decisions

### 1. Scheduling & Dispatch as New Domain (PRD Gap)

**Decision**: Scheduling & Dispatch is added as PRD Section 3.14. This is a net-new feature set requiring database schema, API endpoints, Celery tasks, and UI across both apps.

**Rationale**: The current PRD implicitly handles scheduling under Field Operations & Jobs but never defines it as a first-class feature. Dispatch/scheduling is a differentiator in field service software and a primary value driver for multi-tech shops. Cannot ship MVP without it.

**MVP minimum scope** (to be formally written into Section 3.14):
- Job scheduling with tech assignment, time window, site coordinates
- Tech availability (working hours, PTO, unavailable blocks)
- Dispatch conflict detection (double-booking, infeasible travel time)
- Route sequencing (daily job order optimization)
- Tech notifications on assignment and changes
- Customer-facing ETA data feed (consumed by Communicate feature)

**Deferred to Phase 2**: recurring jobs, skill-based routing, crew assignments, predictive scheduling, customer self-service booking.

### 2. Quote Approval Workflow

**Decision**: Quote state machine adds `pending_approval` and `approved` states. Tenant setting `require_approval_for_tech_quotes` controls whether tech-created quotes require owner review before customer-facing send.

**Rationale**: Multi-person shops need governance around what techs quote to customers. Solo operators don't. A tenant-level toggle satisfies both. Default behavior: ON for multi-user tenants, OFF for solo operators.

**State machine**:
- Original: `draft → sent → accepted / declined / expired → converted`
- New: `draft → pending_approval → approved → sent → accepted / declined / expired → converted`
- When setting is OFF, tech-created quotes skip directly from `draft → sent` (original behavior preserved for solo operators)

**UI surfaces**:
- Mobile tech: "Submit for approval" replaces "Send" when setting is ON
- Mobile owner: `Owner > Approvals` queue
- Web owner: `Dashboard > Approvals` queue and `Quotes > Approvals` detail view
- Notifications: owner gets push + email when tech submits

### 3. Time-Limited Discounts (Owner-Only, Margin Cap Enforced)

**Decision**: Owners can apply time-limited discounts (e.g., "5% off if signed in 7 days") to sent quotes from both web and mobile. Techs cannot. Margin cap is configured per tenant to prevent excessive discounting.

**Rationale**: Common small-business sales tactic. Owner-only is correct — techs should not be able to give away margin unilaterally. Cap prevents even the owner from accidentally destroying job profitability.

**Architecture**:
- New tenant setting: `max_discount_pct_owner` (default 15%)
- Discount creates a new quote version (leverages existing immutable versioning)
- `discount_expires_at` timestamp on the discount line item
- Celery Beat task transitions discount to expired at deadline
- Enforcement: API validates discount_pct ≤ tenant's max_discount_pct_owner

### 4. Templated Customer Communications (Voice-Triggerable)

**Decision**: MVP ships templated customer messages only. Free-form messaging is Phase 2.

**Rationale**: Templated-only gives cleaner audit trail, no moderation risk, faster in the field (one-tap vs thumb-typing), leverages existing Notifications infrastructure.

**MVP templates** (initial set, extensible):
- "On my way, ETA [auto-calculated from route data]"
- "Running [X] min late"
- "Arrived, starting work"
- "Job complete, invoice to follow"
- "Parts delay, will update when resolved"
- "Please confirm appointment [date/time]"

**Voice triggers**: "Tell Johnson I'm 20 out" → identifies customer, picks on-my-way template, fills ETA from route data, fires SMS via notification_outbox.

**Architecture**: All comms logged to a new `customer_communication` table for audit. Visible on web under `Customers > [customer] > Comm history`.

### 5. Reports as Top-Level Nav with Pin-to-Dashboard

**Decision**: Reports promoted from sub-surface to top-level navigation. All standard reports support "Pin to Dashboard" which adds them as customizable widgets on the Dashboard overview.

**Rationale**: For a 1-5 person shop, reports are the primary value delivery — they literally cannot see profitability today. This deserves top-level prominence. Pin-to-dashboard lets each owner customize their home screen to show what matters to them.

**MVP reports**:
- Profitability (by job, customer, period, tech)
- Revenue (cash flow, forecast, period compare)
- AR Aging (consolidated here; Billing deep-links in)
- Tech Productivity (hours, jobs closed, utilization)
- Tax Liability (collected, owed by jurisdiction)
- Voice Analytics (commands, intents, misrecognition rate)

**Pin mechanism**: Each report has a "Pin to Dashboard" action → adds widget to Dashboard grid. Dashboard adds a `Customize` surface for arranging/removing widgets. Stored as tenant-scoped user preference.

**Deferred to Phase 2**: ad-hoc report builder, custom SQL, scheduled report emails, report sharing.

### 6. Voice AI Under Settings (Quality Feedback Loop)

**Decision**: Voice AI admin moved from Dashboard to `Settings > Voice AI` with three subroutes: Transcripts, Feedback, Configuration.

**Rationale**: The feedback mechanism is strategically critical beyond debugging. Every owner-flagged misrecognition becomes labeled training data for fine-tuning the Llama 3.2 model. Over time this creates a moat — Pilot's model gets smarter at trade-specific terminology while competitors using generic LLMs stay flat. Treating it as a first-class feature (not a debug tool) signals this intent.

**Structure**:
- `Transcripts` — searchable history, filterable by tech/date/intent
- `Feedback` — flagged misrecognitions, corrections ("you heard 'twelve-gauge'; I said '12 AWG'") feed training pipeline
- `Configuration` — wake word settings, per-user voice prefs, cloud-fallback toggle

Operational metric (voice minutes consumed, cost) stays under `Reports > Voice Analytics`.

### 7. Tablet Strategy: Field Mode Infrastructure in MVP

**Decision**: Tablets use the web app with a "Field mode" toggle. Field mode infrastructure (tokens, breakpoints, role-aware rendering) ships in MVP. Full tablet-technician UX design is Post-MVP.

**Rationale**: Don't build a third app. Web + mobile is already two codebases for a solo founder with a small team. Tablet is a form factor, not a persona — and the right answer is "tech-appropriate web view on a 768–1024px screen."

**Field mode behavior** (when toggled on or auto-enabled at tablet viewport):
- Touch targets enlarge from 36px to 48px (uses `touchTargets.tablet` from Pass 1 tokens)
- Admin surfaces hidden: Tax config, Markups, User management, Subscription, Audit log, Voice AI Configuration
- Left sidebar collapses to icon-only
- Dark theme default for sunlight legibility
- Voice promoted to persistent top-bar element
- `Jobs > Today` is the default landing route

**Field mode visible**: Dashboard (simplified), Schedule, Jobs, Quotes, Customers (read + create only), Voice AI, basic Reports (tech's own job profitability).

**RBAC enforcement**: Technician role + Field mode is locked to the field-appropriate subset even if URLs are typed directly. Owner + Field mode shows the full view with enlarged targets.

**MVP scope**: Token support (done in Pass 1), mode toggle in Settings, viewport detection, sidebar collapse behavior, role-based route hiding.

**Post-MVP**: Full visual redesign of key flows for tablet proportions, dedicated tablet-tech onboarding, offline-capable tablet mode.

## Web Sitemap Summary

Eight top-level nav sections:

| Section | Purpose | Key routes |
| :--- | :--- | :--- |
| Dashboard | Owner home; customizable widget grid | Overview, Customize, Approvals |
| Schedule | Dispatch and calendar | Calendar, Dispatch board, Tech availability, Route planning |
| Quotes | Full quote lifecycle | All quotes, New quote, Approvals, Templates, Quote detail |
| Jobs | Job monitoring and detail | All jobs, Job detail, Time entries, Expenses, Change orders |
| Customers | CRM primary | All customers, Customer detail, Sites, Contacts, Comm history |
| Billing | Invoicing, payments, tax | Invoices, Payments, Dunning, Tax config |
| Reports | All standard reports (pinnable) | Profitability, Revenue, AR aging, Tech productivity, Tax liability, Voice analytics |
| Settings | Config and admin | Company, Users & roles, Subscription, Catalog, Voice AI, Integrations, Notifications, Audit log, Field mode |

See `pilot-web-sitemap-v2.svg` for the full visual tree.

## Mobile Sitemap Summary

Five bottom-nav tabs (Owner tab gated by RBAC):

| Tab | Visible to | Key routes |
| :--- | :--- | :--- |
| Today | All roles | Clock in/out, Today's schedule, Current timer, Inbox |
| Jobs | All roles | Assigned jobs, Job detail, Communicate, Log expense, Change order, Complete job, LOTO check |
| Voice | All roles | Press to speak, Voice history, Quick lookup |
| Code | All roles | Voltage drop, Conduit fill, Ampacity, NEC reference, Saved calcs |
| Owner | Owner role only | Approvals, Pending quotes (with discount action), Send quote, Send invoice, AR status, QB sync status, Plan usage |

See `pilot-mobile-sitemap-v2.svg` for the full visual tree.

**Naming consideration**: The "Code" tab name works for electrical (NEC) but collides semantically with software "code" in the codebase. So, we will be renaming the tab label to `Calcs` and changing the route from `/code` to `/calcs`.

## What Pass 2 Does NOT Cover

Intentionally deferred:

- **Screen-level layouts** — that's Pass 3+
- **Component library** — Pass 3
- **Data visualization patterns for reports** — Pass 3 when we design the first report
- **Onboarding flows** — Pass 4
- **Error/empty/loading states** — Pass 4 after components exist
- **Tablet-tech flow designs** — Post-MVP (infrastructure only in MVP)

## Validation Checklist

Before moving to Pass 3, verify:

- [ ] PRD Section 3.14 (Scheduling & Dispatch) drafted with MVP feature set
- [ ] Backend additions doc (`backend-mvp-additions.md`) reviewed
- [ ] Dev team aligned on quote state machine changes
- [ ] Dev team aligned on new tenant settings: `require_approval_for_tech_quotes`, `max_discount_pct_owner`
- [ ] Route structure approved by dev team (file-based routing in both apps)
- [ ] "Code" vs "Calcs" tab label decision made

## Next: Pass 3

Pass 3 will prototype 5 key flows in interactive form:
1. Voice quote creation with context continuity
2. Real-time job profitability drill-down (web + mobile)
3. Offline-to-online sync with conflict resolution (mobile)
4. QuickBooks conflict resolution (web)
5. Owner's AR aging → dunning action flow (web)

Each flow produces a clickable prototype and a flow-spec doc that Claude Code consumes when implementing.
