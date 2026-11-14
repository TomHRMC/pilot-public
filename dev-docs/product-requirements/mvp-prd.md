# Pilot for Trades: AI-Powered Quoting, Dispatch & Profitability Platform for Electrical Contractors

> **Snapshot note:** historical working document, published as last edited during the build and not maintained. Statuses and figures below reflect that date; for current, checked figures see [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../diligence/README.md). The product was never released and never carried customer traffic. "Prod" here means the one pre-release AWS environment, used for the author's own tests.

## Complete MVP Product Requirements Document

**Version**: 3.5 (Aug 2026 — §3.11 designated the master subscription/pricing definition; Founders → Charter alignment per GTM v3 D1/D16/D17)
**Date**: August 30, 2026
**Author**: Solo Founder (AI-Enhanced Development)
**Status**: ACTIVE — MVP build complete (batches B17–MOB-B7); remaining MVP items and all Phase 1.5/2.0 features tracked in `pilot-product-roadmap.md`
**Target Launch**: Beta with first electrical/plumbing contractors; see roadmap for milestone definitions

---

## Version History

| Version | Date | Summary |
| :--- | :--- | :--- |
| 1.0 | 2025 | Initial MVP scope |
| 2.0 | Apr 20, 2026 | Pre-Pass 3 update; finalized core 14 product domains; established voice-first architecture and AWS GPU pipeline |
| 3.0 | Apr 26, 2026 | Captures Pass 3 design pass completion. Adds: quote approval workflow with track-changes review; real-time profitability with ETC capture; dispatch board with four-class conflict detection; customer communication templates with always-preview-before-send rule; bi-directional calendar sync with field-level conflict resolution; mobile offline-to-online sync as a new product domain (§3.15); cross-cutting design patterns now formalized at the platform level (§4). New tenant settings, RBAC permissions, and voice intents incorporated. Pricing updated from a tier range to validated single price ($149/month). Phase 2 expansion to plumbing and HVAC trades referenced. |
| 3.1 | Apr 27, 2026 | Pass 4 interim update for Tier 1.5 — Flow 4 Customer Communications Extension. Adds: bidirectional customer SMS messaging (inbound replies + outbound), conversation threading, free-form tech replies with voice-to-text composition, owner visibility surfaces (web Comm history extension + dashboard widget), subscription SMS quota tier (100 segments/month included; soft cap with overage billing or tenant-controlled hard cap), Telnyx as the carrier choice with carrier-agnostic adapter pattern, A2P 10DLC compliance as pre-launch hygiene. Resolves the Flow 4 Cross-Domain B (reply handling) and the customer-text-into-the-void operational gap. Full v3.1 with all Pass 4 product decisions issues at Pass 4 close. |
| 3.1 (final) | Apr 30, 2026 | Pass 4 design phase complete. Consolidates v3.1 interim plus all Tier 1, 1.5, 2, 3, 4 product decisions. Major additions: multi-tier subscription model with trial-as-tier framing and Stripe integration; multi-method MFA (TOTP/SMS/Email) with tenant-required policy and 7-day grace period; notification preference center with per-user × per-category × per-channel matrix and forced-minimum push for safety-critical categories; owner-side mobile-conflict resolution UI; QuickBooks conflict resolution UI (resolves prior deferral); background sync for mobile (pulled forward from Phase 2); voice persona tone surfaced to UI with three-position enum and per-user override; account settings (profile, password, MFA, sessions, data export); customer-facing public quote/invoice link pages with Stripe one-time payment, customer comments stored entity-bound, and tenant email branding customization; AI-mediated help system with RAG retrieval over markdown corpus and chat session capture for training data; in-flight sync indicator with pending count generalized as platform pattern; Tier 3 onboarding wizard plus post-wizard checklist; mobile push notification permission flow; states catalog covering empty/loading/error treatments. Six new platform UX patterns formalized in §4.1. New §3.16 Help & Support domain. Pass 4 close: all 14 surfaces + Tier 1.5 + Settings IA framework locked. Cumulative backend work A1–A88. |
| 3.1.1 | May 15, 2026 | Phase 4.2 traceability remediation — doc-only corrections. §3.1: Audit Lifecycle Management updated to S3 JSONL/gzip export-before-delete (FIND-165). §3.2: Real-Time Supplier API & CSV Import expanded to specify three connector modes: api, scrape, manual (FIND-057). §3.4: LOTO confirmation feature row corrected — LOTO gate is tenant-configurable via `loto_confirmation_required`, not globally mandatory (FIND-063). §3.6: Public Invoice Link with 90-Day Signed URL clarified — usage tracking (`used_count`, `last_used_at`) recorded on POST `/pay` only (FIND-148). §3.7: Notification channel list corrected — `voice` channel removed from MVP; channels are `email`, `sms`, `push`, `in_app` (FIND-077); Customer Communication Templates expanded to 13 MVP active templates (FIND-083). |
| 3.2 | June 21, 2026 | Strategic market update following FSM competitive gap analysis (June 2026). Major changes: **Pricing model** changed from $149/month multi-tier to **$49/month single flat plan** (unlimited users + SMS/voice AI overages). **MVP build complete** — all batches B17 through MOB-B7 closed June 17, 2026; core business loop, GPS/photo mobile, dispatch board, voice AI session UI, dashboard BI all built. **§3.17 added** — Multi-Vertical Deployment Model: trades vs. services industry segmentation; five architectural abstractions for multi-vertical expansion (`tenant.vertical_code`, vertical feature flags, per-vertical seed catalog, vertical voice AI prompts, onboarding wizard vertical selection); `pilotforservices.com` Phase 2 expansion strategy documented. **§6.2 updated** — Phase 2 references externalized to new canonical roadmap document `pilot-product-roadmap.md`. **§3.11 updated** — subscription model simplified to $49/month single plan with 200 SMS segments + 120 min Voice AI included; storage unlimited; payments pass-through via tenant's own Stripe account. MVP now targets electrical and plumbing simultaneously; HVAC in Phase 1.5 after equipment cards are built; services vertical (cleaning, landscaping, handyman) in Phase 2 via `pilotforservices.com`. |
| 3.3 | July 9, 2026 | **Pricing model evolved to 2-tier (Founders / Starter / Teams) + Schedule Lanes.** Major changes: **(1) Schedule Lanes replace Dispatch Slots** — the licensing unit is now a visual lane on the dispatch board (a concurrent job schedule), not a per-technician seat. Unlimited users on all plans; any user (owner, tech, apprentice) can be assigned to any job in any lane. Starter=5 lanes, Teams=20 lanes; add-on packs available. **(2) Founders Plan added** — time-limited cohort plan: 6 months free, then $49/month locked for life at Starter-level limits. Closes when founder cap is reached. **(3) Enterprise plan removed** — `is_active=false`; no Enterprise features built or marketed. **(4) Teams plan updated** — $149/month, 20 schedule lanes, 300 Voice AI min/mo, 500 SMS segs/mo. **(5) Starter limits updated** — 90 Voice AI min/mo, 100 SMS segs/mo, 5 schedule lanes. **(6) Add-on pricing** — +1 lane $10/mo, +5 lanes $40/mo. **(7) Dispatch board UI redesign required** — current tech-as-column layout must be replaced with lane-based layout to match the schedule lane licensing model; see §7 Scheduling & Dispatch. **§3.11 updated** throughout to reflect new tier structure, schedule lane enforcement, and Founders plan mechanics. |
| 3.4 | Aug 13, 2026 | **Tenant Website Hosting for SMS Compliance (C-B16)** added to the notifications/comms feature table — three-option model: (1) Compliance Kit email, (2) Pilot-hosted compliance site (landing + privacy + terms with locked 10DLC SMS clauses, free on all paid tiers, auto-populates the 10DLC brand `website` field), (3) Hosted Starter Site paid add-on (post-MVP, C-B17). Resolves the sole-proprietor TCR brand-vetting failure gap (C-SPIKE-2). |
| 3.5 | Aug 30, 2026 | **§3.11 corrections + master designation.** Founders plan renamed to **Charter** cohort plan per GTM v3 locked decision D1 (DB code `charter_plan`); free period corrected from 6 months to **90 days** per D16 (stale since the C-B1 rename); post-free billing clarified as $49/mo billed monthly at the annual rate per D17; 12-member hard cohort cap added. §3.11 is designated the **master subscription/pricing definition** for all engineering and design modes (wired into their rules files) — plan names, prices, allowances, limits, enforcement modes, and overage rates must trace to this section; features the table marks unlimited (users, jobs, quotes, invoices, customers, QB syncs, emails, calendar syncs) must never carry entitlement gates (phantom-gate rule, PLP-FIX-1 §H). |

---

- [Pilot for Trades: AI-Powered Quoting, Dispatch \& Profitability Platform for Electrical Contractors](#pilot-for-trades-ai-powered-quoting-dispatch--profitability-platform-for-electrical-contractors)
  - [Complete MVP Product Requirements Document](#complete-mvp-product-requirements-document)
  - [Version History](#version-history)
  - [Executive Summary](#executive-summary)
    - [Revolutionary Value Proposition](#revolutionary-value-proposition)
  - [Section 1: Strategic Foundation](#section-1-strategic-foundation)
    - [1.1 Problem Statement \& Market Validation](#11-problem-statement--market-validation)
    - [1.2 Customer Analysis \& User Personas](#12-customer-analysis--user-personas)
    - [1.3 Value Proposition Canvas](#13-value-proposition-canvas)
  - [Section 2: AI-First Product Architecture](#section-2-ai-first-product-architecture)
    - [2.1 Voice-Controlled AI System Design](#21-voice-controlled-ai-system-design)
    - [2.2 Conversational Continuity \& Confirmation Patterns](#22-conversational-continuity--confirmation-patterns)
    - [2.3 Voice Command Categories](#23-voice-command-categories)
  - [Section 3: Core MVP Features](#section-3-core-mvp-features)
    - [3.1 Audit \& Compliance](#31-audit--compliance)
    - [3.2 Catalog \& Pricing](#32-catalog--pricing)
    - [3.3 CRM (Customer Relationship Management)](#33-crm-customer-relationship-management)
    - [3.4 Field Operations \& Jobs](#34-field-operations--jobs)
    - [3.5 Identity, Access \& Tenant Management](#35-identity-access--tenant-management)
    - [3.6 Invoicing \& Billing](#36-invoicing--billing)
    - [3.7 Notifications \& Communications](#37-notifications--communications)
    - [3.8 Platform Infrastructure](#38-platform-infrastructure)
    - [3.9 QuickBooks Integration](#39-quickbooks-integration)
    - [3.10 Sales \& Quoting](#310-sales--quoting)
    - [3.11 Subscriptions \& Usage](#311-subscriptions--usage)
    - [3.12 Tax Calculation](#312-tax-calculation)
    - [3.13 Voice AI](#313-voice-ai)
    - [3.14 Scheduling \& Dispatch](#314-scheduling--dispatch)
    - [3.15 Mobile Offline Operations](#315-mobile-offline-operations)
    - [3.16 Help \& Support](#316-help--support)
  - [Section 3.17 — Multi-Vertical Deployment Model](#section-317--multi-vertical-deployment-model)
    - [Industry Segmentation](#industry-segmentation)
    - [Vertical Deployment Timeline](#vertical-deployment-timeline)
    - [Multi-Vertical Architecture Pattern](#multi-vertical-architecture-pattern)
    - [What Is NOT Abstracted](#what-is-not-abstracted)
  - [Section 4: Cross-Cutting Design Patterns \& Technical Implementation Approach](#section-4-cross-cutting-design-patterns--technical-implementation-approach)
    - [4.1 Platform UX Vocabulary](#41-platform-ux-vocabulary)
    - [4.2 Technical Stack](#42-technical-stack)
    - [4.3 Configuration Conventions](#43-configuration-conventions)
  - [Section 5: Risk Management \& Mitigation](#section-5-risk-management--mitigation)
    - [5.1 Technical Risks](#51-technical-risks)
    - [5.2 Business Risks](#52-business-risks)
  - [Section 6: Success Criteria \& Next Steps](#section-6-success-criteria--next-steps)
    - [6.1 MVP Success Criteria](#61-mvp-success-criteria)
    - [6.2 Roadmap](#62-roadmap)
  - [Conclusion](#conclusion)

---

## Executive Summary

### Revolutionary Value Proposition

Pilot for Trades was designed as a voice-first, AI-powered platform for electrical contractors that unifies quoting, dispatch, customer communications, real-time profitability tracking, and field operations. Where most existing tools are form-driven, Pilot delivers a conversational AI experience that understands electrical terminology, integrates real-time material pricing, manages the day's dispatch via voice, sustains continuity across multi-turn conversations, and provides instant profitability insights through natural voice commands — including hands-free operation while driving between sites and offline-tolerant capture in basements, attics, and rural service areas.

**Market Opportunity** (early-research estimates, unverified): a multi-billion-dollar construction software market growing at double-digit rates, with hundreds of thousands of electrical contracting businesses. Current tools force manual processes that waste 15+ hours weekly on administrative tasks.

**Premium Positioning**: $149/month (the price point at the time; see §3.11 for the later pricing) positions Pilot as premium but accessible, targeting $50K–$100K MRR within 18 months through revolutionary AI-first approach.

**Phase 2 Expansion**: After establishing product-market fit with electrical contractors, the platform's domain abstractions extend to plumbing and HVAC trades. The voice intent layer, the field operations model, and the dispatch board are trade-agnostic; only the catalog (NEC code reference, electrical material taxonomies, electrical-specific calculations) is electrical-specific. Phase 2 adds plumbing and HVAC catalogs, code references, and trade-specific calculation modules.

---

## Section 1: Strategic Foundation

### 1.1 Problem Statement & Market Validation

**Core Problem**: Small electrical contractors (1–5 employees) lose significant money through inefficient quoting processes, volatile material pricing, lack of real-time job profitability visibility, friction between dispatcher and field, and manual customer communication overhead.

**Quantified Pain Points**:

- **Time Waste**: 15+ hours weekly on manual quoting and administrative tasks
- **Financial Losses**: $1,500–$4,000 per job from material price volatility and underquoting
- **Cash Flow Crisis**: many contractors wait 30+ days for payment (anecdotal, from early research)
- **Profitability Blindness**: Contractors operate "flying blind" until job completion — they have no estimate-to-complete (ETC) signal mid-job to course-correct
- **Dispatcher-Field Friction**: Last-minute schedule changes are communicated by phone or text and lost; field techs miss reassignments while in basements without signal
- **Customer Communication Overhead**: Owners spend significant time individually composing routine status updates (running late, on the way, job complete) that should be templated and one-tap

**Market Evidence**:

- 421K members in r/electricians actively discuss business challenges
- Direct quotes: "I hate quoting jobs... would save 10 hours a week" (Reddit validation)
- Forum analysis shows 60%+ of discussions focus on quoting and profitability struggles

**Target Market**:

- **TAM**: 500,000 electrical contracting businesses in the US
- **SAM**: 75,000 small contractors (1–10 employees) seeking efficiency tools
- **SOM**: 2,500 early adopters willing to pay premium for AI-first solutions

### 1.2 Customer Analysis & User Personas

**Primary Persona — Mike, the solo or small-team electrical contractor**:

- Age: 35–55, 15+ years electrician experience, 3–7 years business owner
- Team size: 1–3 employees; annual revenue: $300K–$800K
- Technical comfort: moderate (smartphone, basic software)

**Goals**:

- Increase profit margins from 3–5% to industry target 20%
- Reduce quoting time from 3 hours to 30 minutes
- Real-time job profitability visibility
- Eliminate manual data entry between systems
- Manage day's dispatch and customer communications without sitting at a desk

**Pain Points**:

- "Quoting takes forever and I lose jobs to faster competitors"
- "Material prices change daily, making quotes obsolete"
- "Never know if I'm making money until the job is done"
- "I'm constantly typing the same 'running 20 minutes late' text to customers"
- "Half my crew is out of cell range half the day"

**AI Interaction Preferences**:

- Voice commands while driving between jobs
- Natural language: "What's the profit on the Johnson panel upgrade?" — and follow-ups: "What was that in margin terms?"
- Conversational continuity across multi-turn interactions
- Immediate feedback and confirmations; explicit confirmation before destructive actions

**Secondary Persona — Luis, the field tech**:

- Mobile-first; rarely opens the web app
- Works in basements, attics, parking garages, rural areas — frequently offline
- Wants to clock in, capture expenses, and update job status without typing
- Trusts the platform only if data captured offline reliably appears on sync

**Tertiary Persona — Sarah, the bookkeeper or office manager**:

- Web-first; reviews quotes for approval, manages customer comms templates, monitors profitability
- Often the bottleneck for quote approval in multi-user shops; needs review tooling that surfaces what changed since last review
- Manages QuickBooks reconciliation; needs sync conflict resolution to be visible and tractable

### 1.3 Value Proposition Canvas

**Customer Jobs**:

- Create accurate electrical estimates quickly
- Track job profitability in real-time, including mid-job ETC visibility
- Maintain professional customer relationships with timely status communication
- Comply with electrical codes and regulations
- Coordinate dispatch and field operations across the team

**Pain Relievers**:

- AI eliminates manual material price lookups
- Voice control enables hands-free operation
- Real-time tracking prevents cost overruns; ETC signals course-correction opportunities mid-job
- Automated QuickBooks sync eliminates double entry; bi-directional calendar sync eliminates dispatcher-field disconnects
- Templated customer comms reduce per-message overhead from minutes to seconds
- Offline-tolerant mobile capture eliminates lost data when techs work without signal

**Gain Creators**:

- 80% faster quote generation
- 95% material pricing accuracy
- Real-time profitability alerts with ETC variance notifications
- 50% reduction in administrative overhead
- Voice-driven approval and conflict resolution workflows for owners on the move

---

## Section 2: AI-First Product Architecture

### 2.1 Voice-Controlled AI System Design

**Core AI Components**:

- **Model**: Llama 3.x Instruct — designed to be fine-tuned on electrical-trade vocabulary; currently runs stock (prompt-engineered + context), pending the training step (see roadmap GAP-M15)
- **Hosting**: AWS GPU instance (g4dn.xlarge tier; sub-2-second response time target)
- **Speech-to-Text**: OpenAI Whisper Large-v3 (locally hosted on the same instance)
- **Text-to-Speech**: Native browser/mobile TTS APIs
- **Training Data (target for the planned fine-tune)**: 10,000+ electrical voice command patterns

### 2.2 Conversational Continuity & Confirmation Patterns

The Voice AI is a stateful, multi-turn conversational layer — not a one-shot command parser. Pass 3 design established four conversational patterns now binding across the platform.

**Conversation Sessions**: Voice interactions are organized into named, numbered conversation sessions (e.g., "#3 — Johnson panel quote"). Sessions carry a `context_window_json` with active references (`active_quote_id`, `active_job_id`, `active_customer_id`) that resolve pronouns ("update it", "add to that job") across multiple turns. Session titles are auto-generated by the model from the first meaningful exchange and can be renamed via voice or touch.

**Confirm-as-Turn for Destructive Actions**: Any voice intent that creates, modifies, or deletes durable data (quote send, calendar conflict resolution, schedule change, quote approval, job deletion, sync conflict resolution) routes through an explicit confirmation turn before commit. The AI states the specific action ("You're about to send the Johnson panel quote to tom@johnson.example.com — confirm?") and waits for affirmative response. Non-affirmative responses cancel and return the AI to passive listening. This pattern is universal across the platform.

**Disambiguation Before Guessing**: When a spoken reference matches multiple entities (two Johnsons, two pending conflicts, two active quotes), the AI asks rather than picks. Disambiguation prompts surface the discriminating attribute ("Which Johnson — the panel upgrade or the service call?").

**Refusal-with-Redirect for Out-of-Scope Intents**: When a voice request exceeds what the voice channel can do (e.g., blended conflict resolution that mixes two versions, complex multi-line edits), the AI refuses cleanly and offers a redirect path: "I can pick a side, but I can't blend them. Want me to text you the link to edit on web?"

### 2.3 Voice Command Categories

**Navigation Commands**:

- "Go to dashboard" — navigate anywhere in app
- "Show me quotes" — display specific information
- "Open jobs" — launch functionality

**Data Entry Commands**:

- "Add customer Tom Johnson" — create new records
- "Set wire size to 12 AWG" — update form fields
- "Delete last item" — remove with confirmation

**Electrical Calculations**:

- "Calculate voltage drop for 12 AWG copper 100 feet at 240 volts"
- "What's ampacity for 10 AWG THHN in conduit"
- "Show me conduit fill for 4 THHN wires"

**Business Queries**:

- "What's profit on Johnson job?"
- "Show me this month's revenue"
- "Which jobs are over budget?"

**Workflow Commands** (Pass 3 additions):

- Quote approval: "Approve the Johnson quote" / "Reject the Davis quote — pricing too aggressive"
- Customer comms: "Tell Tom I'm 20 minutes out" → routes to always-preview-before-send (§3.7)
- Dispatch: "Reassign the Davis job to Luis" / "Reschedule the Johnson panel upgrade to Thursday at 10am"
- Sync conflict resolution: "Accept the Pilot version of the Johnson conflict" / "Restore the Davis job from calendar"
- Session management: "Switch to the Johnson session" / "Rename this session to 'Davis 200A panel'"

---

## Section 3: Core MVP Features

> **Scope**: This section defines the complete set of MVP features across all 15 product domains. These features represent the authoritative reference for AI-agent-driven design and implementation. Implementation status and gap analysis are tracked separately in `dev-docs/analysis/db-schema-domain-mvp-features-impl-analysis.md`. Backend additions triggered by design decisions are tracked in the running ledger `frontend-pass-3-flow-7-backend-mvp-additions-v4.md`.

---

### 3.1 Audit & Compliance

**Domain Purpose**: Provide an immutable, tamper-proof audit record of every data mutation across the platform to satisfy both internal data integrity requirements and future regulatory obligations.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Trigger-Based Mutation Capture** | An `audit.log_changes()` PostgreSQL trigger fires on all core tables, capturing full JSONB `OLD`/`NEW` snapshots for every `INSERT`, `UPDATE`, and `DELETE` operation. Every mutation is attributable to a specific actor. |
| **Financial De-duplication** | Database-level `UNIQUE` constraints on `invoice` and `payment` idempotency keys physically prevent duplicate revenue records from being written, regardless of application-layer retries or webhook replays. |
| **Audit Lifecycle Management (90-Day Hot Storage + S3 Archive)** | A scheduled Celery task (`archive_audit_logs`) exports audit records older than 90 days to S3 (`pilot-audit-archive` bucket) as JSONL/gzip before deleting them from hot storage. S3 lifecycle rule: Glacier Instant Retrieval after 90 days; Deep Archive after 3 years. Folder structure: `YYYY/MM/DD/{tenant_id}/audit-events-{timestamp}.jsonl.gz`. Rows are deleted from RDS only after confirmed S3 upload — if S3 upload fails, the delete is skipped and retried on the next run. This preserves the full audit trail for dispute resolution and compliance review while managing database growth. (FIND-165 — Phase 4.2 correction) |
| **Platform vs. User Attribution** | An `actor_type` discriminator on the audit log distinguishes between three attribution classes: direct technician edits, automated system/Celery tasks, and external QuickBooks webhook events. |
| **Offline Capture Timestamp Distinction** | Audit log captures both `client_capture_at` (when the offline-capable operation was captured on the device) and `server_received_at` (when sync delivered it). The gap is queryable for offline-duration analysis and potential legal/policy review (e.g., LOTO confirmation timestamp distinction). |
| **Resolution Decision Audit Trail** | Every conflict resolution — quote approval/rejection, calendar sync conflict resolution, mobile sync conflict resolution, QuickBooks sync conflict resolution — is logged with the resolver's identity, the chosen path, and a distinguishing flag for auto-resolved vs. user-resolved decisions. |

---

### 3.2 Catalog & Pricing

**Domain Purpose**: Maintain a real-time, multi-supplier material catalog with historically immutable pricing snapshots to ensure every quote and invoice reflects accurate, auditable cost data.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Real-Time Supplier API & CSV Import** | The platform supports three supplier catalog synchronization modes, each configured per-supplier via a `ConnectorConfig` record: **API Mode** (`mode='api'`) — the system polls the supplier's HTTP API on a configurable cron schedule; connection details (API endpoint URL, auth credentials, field mapping) stored in connector config; Celery sync task calls the API, normalizes the response, and upserts `SupplierItem` and `SupplierItemPrice` records; run results written to connector run log. **Scrape Mode** (`mode='scrape'`) — the system scrapes a supplier's website on a configurable cron schedule; CSS/XPath selectors and target URL stored in connector config; Celery sync task fetches the page and upserts records; intended for suppliers with no API but a consistent web catalog. **Manual / CSV Import Mode** (`mode='manual'`) — no background sync; tenant owner uploads a CSV file via admin UI (`POST /api/v1/catalog/suppliers/{id}/import`); system parses the CSV, validates required columns (SKU, description, unit price, UoM), and upserts `SupplierItem` + `SupplierItemPrice` rows; run log records import result. All three modes maintain the same append-only price history model: existing active prices are not overwritten; a new `SupplierItemPrice` row is created for each changed price. (FIND-057 — Phase 4.2 correction) |
| **Historical Price Immutability (Snapshotting)** | Supplier item prices and pricebook item versions use append-only temporal records with GiST exclusion constraints. Once a price is used on a quote or job, it is immutably frozen; no retroactive price changes can corrupt historical records. |
| **Category-Specific Markups** | Tenant markup configurations support distinct markup percentages per material/expense category (e.g., wire, conduit, fixtures), enabling fine-grained margin control by material type. |
| **Labor Burden Rate Version Catalog** | A `labor_rate_version` catalog table manages differentiated burdened hourly rates by technician skill level or role. This drives accurate pre-job labor cost estimation and catalog-driven quoting for labor line items. |
| **Cross-Tenant Pricing Security (IDOR Prevention)** | All supplier item and pricing cache lookups are strictly scoped to the requesting tenant's `tenant_id`. No tenant can read another tenant's private catalog prices through any API path. |

---

### 3.3 CRM (Customer Relationship Management)

**Domain Purpose**: Model the full commercial hierarchy from Customer to Site, supporting both residential and commercial client structures with role-aware contact and payment management.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Tenant vs. Property Manager Billing** | Polymorphic contact and address structures support separate primary contacts and billing contacts on a single site, enabling proper invoicing splits between a property manager and a tenant end-user. |
| **Commercial vs. Residential Customer Profiling** | A `customer.type` discriminator (`person` vs. `company`) drives downstream UI, reporting, and tax logic appropriate to each customer class. |
| **Multi-Site Management** | A single customer record can own multiple service sites (1:N), enabling contractors who manage property portfolios to operate without duplicating customer data. |
| **Stored Payment Methods (Vaulting)** | Customer payment methods are vaulted via a PSP token, fingerprint, brand, and expiry metadata. No raw card data is stored in Pilot's database, minimizing PCI-DSS scope (Stripe-hosted card fields). |
| **Site-Specific Access Details (Structured Fields)** | Each site record stores structured `gate_code`, `access_instructions`, and `hazard_notes` fields — discrete columns (not generic notes) — enabling Voice AI to read precise, actionable arrival instructions to field technicians at job start. |

---

### 3.4 Field Operations & Jobs

**Domain Purpose**: Power the end-to-end on-site workflow: job assignment, time tracking, expense logging, photo documentation, change order capture, ETC capture, and real-time cost visibility — all accessible via voice command from the field, all tolerant of offline operation.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Basic Job Assignment** | Jobs are assigned to technicians with a unique-constraint guard preventing double-assignment of the same technician to the same job. |
| **Basic Time Tracking (Clock In / Clock Out)** | Technicians clock in and out of jobs. The billing `hourly_rate_cents` is frozen as a snapshot at clock-in time, ensuring historical payroll accuracy regardless of future rate changes. |
| **Ad-Hoc Expense Logging** | Field technicians can log job-specific material and miscellaneous expenses with mandatory markup percentage capture, feeding directly into real-time job cost calculations. |
| **Voice-Command Field Logging** | Voice AI intent handlers are directly wired to job time entry and expense creation, enabling hands-free clock-in, clock-out, and expense logging from the field without touching the screen. |
| **Real-Time Job Costing (Actuals vs. Estimates)** | Actual labor and material cost totals on each job are continuously updated via asynchronous Celery workers as time entries and expenses are submitted, providing live budget-vs.-actual visibility. |
| **Estimate-to-Complete (ETC) Capture System** | Each time entry captures a tech-provided ETC value ("how many more hours to complete?") at clock-out time. This enables mid-job profitability projection — actuals + ETC vs. quoted budget — surfacing course-correction opportunities before completion. ETC variance triggers vary by configurable thresholds: a note is required when an ETC override increases total projected hours by more than `etc_variance_note_required_pct` (default 10%); the owner is notified when the projection exceeds the quote by more than `etc_variance_owner_notify_pct` (default 50%). |
| **Photo Documentation** | Field technicians can upload photos (stored in S3) directly linked to a job record, enabling before/after documentation, punch-list tracking, and dispute evidence. Photos use a separate upload pipeline from data sync (see §3.15) with WiFi preference and resumable chunked transfer. |
| **On-Site Change Order Management** | Field technicians can create and modify scope changes (change orders) on active jobs from the mobile app. All change orders are linked to a quote version and trigger automatic job total recalculations in the database. |
| **Receipt OCR Automation (Expense Auto-Fill)** | Uploaded material receipt images are processed asynchronously by a local RapidOCR pipeline (CPU, in the app container) that parses the receipt total and auto-populates the `cost_cents` field on the expense record, eliminating manual re-entry. |
| **GPS-Verified Check-Ins** | Technician latitude, longitude, and GPS variance are captured at clock-in time, providing on-site presence verification for payroll accuracy and enabling geofencing-based dispute resolution. |
| **LOTO (Lock Out / Tag Out) Safety Confirmation (Tenant-Configurable)** | Field techs confirm LOTO verification on the mobile app before starting electrical work. The confirmation is offline-capable (per §3.15) with both `client_capture_at` and `server_received_at` timestamps preserved for liability documentation. LOTO gating is controlled by tenant setting `loto_confirmation_required` (default `false`): when **enabled**, the Voice AI gates job-completion and clock-out commands until LOTO is confirmed; when **disabled**, LOTO confirmation is available as an optional audit action (tech can confirm for the paper trail) but does not gate any workflow. The `loto_confirmation` table records LOTO events in both cases. Not every electrical job requires LOTO; the owner configures this per their team's workflows. (FIND-063 — Phase 4.2 correction) |
| **Free-Text Job Notes** | Techs can add timestamped free-text notes to a job (offline-capable per §3.15). Notes are surfaced on the job detail page chronologically alongside time entries, expenses, and photos. |
| **Scheduled Timestamps on Every Job** | Every `job` record carries `scheduled_start_at` and `scheduled_end_at` timestamps populated by the Scheduling domain. These drive the dispatch board, tech's today view, and customer ETA calculation. |
| **Tech Assignment Link to Jobs** | Every job links to one or more tech users via the `job_tech_assignment` table. MVP UI limits this to one tech per job; schema supports many-to-many for Phase 2 crews. |
| **Live Job Profitability View** | The job detail page surfaces a live profitability view: actual cost (labor + materials), projected cost (actuals + ETC), quoted budget, and projected margin. Below `margin_target_pct` (default 20%) jobs receive a visual indicator. Margin buckets for reporting use configurable boundaries (`margin_bucket_boundaries`, default `[10, 20, 30]`). |

---

### 3.5 Identity, Access & Tenant Management

**Domain Purpose**: Enforce strict multi-tenant data isolation, role-based access control (RBAC), and identity integrity across all platform users from solo contractors to multi-technician teams.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Strict Tenant Isolation (Tenant Stamping)** | Every tenant-owned table is stamped with a `tenant_id` column. An immutability trigger on those tables prevents `tenant_id` reassignment after record creation, guarding against cross-tenant reassignment at the database level (route-level exceptions: Known Limitations #27). |
| **Case-Insensitive Login (CITEXT)** | User email addresses use the PostgreSQL `CITEXT` type, preventing case-variant duplicate account creation. |
| **Pre-Seeded Role Definitions (Owner / Technician / Accountant)** | The platform ships with pre-seeded roles. The `technician` role has `voice.use` and `nec.calculate` permissions but explicitly excludes `integrations.manage` and financial admin permissions, enforcing least-privilege by default. |
| **Identity Integrity (Highlander Rule — One Primary Email)** | A pair of database triggers enforces that each user account has exactly one primary email endpoint at all times. The `user.email` column stays synchronized with the designated primary endpoint automatically. |
| **Platform Staff Isolation** | A database trigger (`guard_tenant_user_platform_isolation`) prevents Pilot internal staff accounts from being added to tenant-owned data tables, maintaining an auditable separation between operator and customer data. |
| **RBAC Permission Decorator Coverage (All Routes)** | The `require_permission()` FastAPI dependency is applied to authenticated tenant routes; public, webhook and signed-link routes are scoped by token or signature. Critical routes are gated to `owner` and `accountant` roles only; technician-role users cannot access financial admin endpoints. |
| **Pass 3 RBAC Additions** | New permissions added: `quote.submit_for_approval` (technician); `quote.approve` (owner, accountant); `quote.apply_discount` (owner, accountant); `voice.provide_feedback` (owner, accountant); `voice.manage_own_sessions` (all roles); `quote_template.create` (owner, accountant); `quote_template.edit` (owner, accountant); `quote_template.fork_system` (owner, accountant); `schedule.manage` (owner, accountant); `schedule.view_own` (technician). |
| **Multi-Method MFA Enrollment (TOTP + SMS + Email)** | Users can enroll any combination of three MFA methods: authenticator app (TOTP), SMS, and email. Self-service multi-method enrollment is encouraged at first setup to prevent lockouts. At login, the user picks which enrolled method to use for that session. 10 single-use recovery codes generated at first enrollment as ultimate fallback; regenerable on demand. Method cards surface security trade-offs honestly (TOTP labeled "Most secure. Recommended.") without forcing the choice. |
| **Tenant-Required MFA Policy with 7-Day Grace Period** | Owners can enable tenant-wide MFA-required policy at `Settings > Users & Roles > Security policy`. When enabled, all tenant users have a 7-day grace period to enroll at least one MFA method. During grace, warning banners and daily reminders escalate. Login-trigger enforcement: any login during grace activates immediate enrollment for that session; after 7 days, all unenrolled users are forced into enrollment on next login. Existing authenticated sessions continue working until next login (preserves in-flight tech work). When tenant disables MFA-required, existing user MFA stays on; new users aren't required. |
| **Owner Reset of User MFA (Support Escape Hatch)** | Owners can reset MFA for any user via `Settings > Users & Roles > [user detail] > Reset MFA`, removing all enrolled methods + recovery codes. The user re-enrolls on next login. Notified user receives email + push confirmation. Audit log captures the reset event with actor and target identities. Owner self-reset of own MFA is also supported (with password re-verification) for the rare case where the owner has lost access to all enrolled methods. |
| **Active Sessions Management** | Users can view all currently-logged-in sessions for their account at `My Account > Security > Active sessions` with device + browser + last-active timestamp + approximate location. Per-session revoke and "Revoke all other sessions" affordances. The latter is the user's primary self-service security action when suspecting compromise. Revoke immediately invalidates the refresh token; next API request from that session forces re-login. |
| **Profile Management (Name, Photo, Phone, Time Zone)** | User-personal profile editing at `My Account > Profile`: display name, profile photo (upload + crop), phone number (used for SMS MFA when enrolled), email (read-only in MVP; account migration is Phase 2), language preference (English only in MVP), time zone (auto-detected default; user-overridable). Phone number changes require re-verification of SMS MFA method if enrolled. |
| **Password Change with Cross-Device Session Invalidation** | Password change at `My Account > Password` requires current password verification + new password meeting tenant policy (12+ chars, complexity, history). On successful change, all sessions other than the current one are auto-revoked as a security best practice. User stays logged in on the changing device; other devices require re-login. |
| **Personal Data Export Request** | Users can request a full export of their accessible tenant data (RBAC-scoped — owners get full tenant; technicians get only their own jobs/time/expenses/communications) at `My Account > Data export`. Background job generates CSV files per entity type, bundled into a ZIP with manifest, delivered via email with a 7-day signed download URL. Frequency limit: one export per user per 24 hours. |
| **Tenant Signup Wizard (5-Step)** | New tenant signup uses a minimum-required wizard: (1) Account creation with email/password/business info; (2) Legal acceptance for ToS/Privacy/EULA with versioned hashing; (3) Optional phone verification (only required if user wants SMS notifications or SMS MFA — customer SMS messaging works regardless via tenant Telnyx number); (4) Subscription tier selection with Trial pre-selected; (5) Confirmation and routing to dashboard (or Stripe payment if paid tier picked). Email verification decoupled from wizard completion to avoid blocking on email delivery delays. |
| **Resumable Wizard State** | Users who abandon mid-wizard return to where they left off on next login. State persisted per-tenant; pre-filled fields where state is known; users can navigate back through completed steps. |
| **Post-Wizard Setup Checklist (Pinned Dashboard Widget)** | After wizard completion, users land on the standard dashboard with a pinned "Setup checklist" widget. Eight items: account/legal/tier (auto-completed during wizard), add first customer, set up catalog, connect QuickBooks, connect calendar, invite team. Auto-completion detection: items mark done when completed via any path (e.g., adding a customer via voice marks the checklist item done). Hide, skip individual items, or dismiss permanently options. Persists per-tenant across users. |
| **Mobile Setup Phase on First Mobile Login** | When any user logs into mobile for the first time, brief mobile setup phase fires: welcome screen, push notification permission request (with pre-explainer screen before OS prompt — see §3.7), brief tutorial cards on Today tab and voice mic. Skippable. Routes to Today tab on completion. |
| **Tax Setup Just-In-Time Sub-Flow** | Tax setup is the only onboarding step that gates downstream functionality — users cannot generate invoices without tax rates configured. Rather than forcing it in the wizard, Pilot uses a contextual sub-flow: when the user attempts to convert a quote to invoice or generate an invoice directly, the "Set up tax rates first" sub-flow appears with auto-detected tax jurisdiction (from ZIP), default rate suggestion, and tax-exempt opt-in. Once configured, subsequent invoices use saved tax setup. |
| **Pass 4 RBAC Additions** | New permissions added at Pass 4: `field_issue.view`, `field_issue.resolve` (owner, accountant) — Tier 1 #1; `qb_conflict.view`, `qb_conflict.resolve` (owner, accountant) — Tier 1 #2; `notification_preference.tenant_default.edit` (owner), `notification_preference.user_override.edit` (all) — Tier 2 #5; `voice_persona_tone.tenant_default.edit` (owner), `voice_persona_tone.user_override.edit` (all when allowed), `voice_persona_tone.user_override_policy.edit` (owner) — Tier 2 #6; `mfa.enroll_self`, `mfa.reset_self` (all), `mfa.reset_user`, `mfa.policy.edit` (owner) — Tier 2 #7; `account.session.revoke_own`, `account.data_export.request` (all) — Tier 2 #7; `subscription.view` (owner, accountant), `subscription.tier.change` (owner) — Tier 3 #10; `legal_acceptance.accept`, `tenant.signup.complete` (auto during signup) — Tier 3 #10; `onboarding_checklist.skip_item`, `onboarding_checklist.dismiss` (owner, accountant) — Tier 3 #10; `mobile_push_permission.update` (all on own device) — Tier 3 #11; `email_branding.edit` (owner, accountant) — Tier 4 #13; `public_link.revoke` (owner, accountant) — Tier 4 #13; `feedback.submit` (all) — Tier 4 #14; `help_chat.delete_own_history` (all; Phase 2 surface stub) — Tier 4 #14. |
| **Operator Role (Pilot Platform-Level)** | A special platform-level role outside tenant RBAC, exclusively for Pilot operator (Tom). Manages cross-tenant settings via hidden Pilot routes. Operator-controlled values include: per-tenant trial length override, per-tenant subscription tier override (force a tier without payment), tenant suspension/restoration, tenant deletion with data purge, system default settings. For MVP, operator-admin functions are managed via direct DB updates; hidden Pilot routes are deferred operator infrastructure. |

---

### 3.6 Invoicing & Billing

**Domain Purpose**: Convert approved quotes and completed jobs into professional invoices, give customers a frictionless digital payment experience, and automate overdue AR recovery.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **One-Click Quote / Job → Invoice Conversion** | A single action converts an accepted quote or completed job into an invoice, carrying over all line items (including change orders) with exact pricing preserved via polymorphic source references. |
| **AR Aging Dashboards** | Partial indexes on invoice balance and status-plus-due-date fields enable real-time accounts receivable aging reports without full table scans, showing the contractor exactly which invoices are current, 30-day, 60-day, and 90-day overdue. |
| **ACH / Bank Transfers** | The payment type catalog supports ACH, card, and check payment methods, enabling contractors to accept bank transfer payments in addition to credit cards for larger commercial invoices. |
| **Card on File (Payment Vaulting)** | Customer card and bank details are stored as PSP tokens, enabling one-click payment processing for repeat customers without requiring re-entry of payment information. |
| **Public Payment Links (Tokenized Invoice Access)** | Each invoice can generate a secure, tokenized public URL. Customers can view the invoice and submit payment from a phone link without requiring a platform login. |
| **Automated Dunning (Overdue AR Reminders)** | A Celery Beat scheduled task monitors for overdue invoices and automatically enqueues SMS and email reminders to the `notification_outbox`, reducing the manual follow-up burden on the contractor. |
| **QuickBooks Invoice & Payment Push Sync** | All Pilot-created invoices and recorded payments are pushed to QuickBooks Online via Celery tasks, eliminating double-entry bookkeeping entirely. |
| **Stripe One-Time Payment for Invoices** | Customers paying via the public invoice link use Stripe Elements (PCI-compliant card collection; Pilot servers never see raw card data). Same Stripe account as subscription billing; parallel API surface (Stripe Payment Intents). Customer can adjust payment amount up or down from invoice total — when amount differs, a comment is required explaining the variance ("paying 90% per agreed discount"; "tip for Tom"). Stripe webhook confirms payment success; invoice balance updates accordingly. Failed payments surface inline with retry option. |
| **Customer Payment Comments (Entity-Bound)** | Comments left by customers on the public invoice payment surface are stored on the payment record (`payment.customer_payment_comment`), not routed into customer comm threads. Visible on the payment detail and on the related invoice detail in Pilot. Tenant notification per Tier 2 #5 "Billing" category. One-way for MVP; if tenant wants to respond, they use existing Customer Comms (§3.7). |
| **Variance Payment Accounting Integrity** | Underpayments preserve the unpaid balance on the invoice; overpayments are flagged for tenant review. Stripe captures the actual amount paid; Pilot records `amount_variance_cents`. QuickBooks sync (§3.9) handles partial payments natively. Tenant decides handling for overpayment (refund, credit forward, accept). |
| **Public Invoice Link with 90-Day Signed URL** | Each invoice generates a signed-URL public page that customers access without a Pilot login. URL expires 90 days from generation; customer accessing an expired link sees a "contact tenant for fresh link" page. Tenant can manually revoke. Already-paid invoices show paid status with payment history; partially-paid invoices show remaining balance with both "Pay remaining" and "Pay different amount" affordances. State-aware revisit handling prevents accidental double-actions. Usage tracking (`used_count`, `last_used_at`) is recorded on the POST `/pay` action only — not on passive GET views. This preserves HTTP GET idempotency (RFC 7231 §4.3.1) while still capturing meaningful payment interactions. (FIND-148 — Phase 4.2 correction) |
| **Customer-Facing Page Tenant Branding** | Public invoice pages render with the tenant's email branding settings: logo, brand color, signature line, custom footer text. "Powered by Pilot for Trades" small footer link. Branding settings managed at `Settings > Communications > Email branding`. Default rendering uses tenant name in heavy text + Pilot brand-indigo if no custom branding configured. |

---

### 3.7 Notifications & Communications

**Domain Purpose**: Deliver reliable, multi-channel (email, SMS, push) communications to customers and technicians with full delivery auditability, strict regulatory compliance, and templated workflows that minimize per-message overhead. SMS supports bidirectional customer-tech conversations with threading, free-form tech replies (voice-to-text supported), and full owner visibility — all customer communications stay inside Pilot, with the tech never needing to use their personal phone's SMS to reach customers.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Reliable Message Queuing (Transactional Outbox)** | All outbound notifications are written to a `notification_outbox` table before dispatch. A Celery worker processes the outbox with exponential backoff on failures, guaranteeing at-least-once delivery with full status tracking. |
| **Email / SMS / Push / In-App Channel Enforcement** | A `notification_channel` lookup table enforces the four MVP delivery channel codes: `email`, `sms`, `push`, `in_app`. A FK from `notification_outbox.channel` to `notification_channel(code)` enforces relational integrity at the database layer. Note: `voice` (robo-call/IVR outbound delivery) is deferred to Phase 2 — evaluate based on customer demand. (FIND-077 — Phase 4.2 correction) |
| **A2P 10DLC Compliance (SMS Opt-In Tracking)** | Customer SMS opt-in consent, opt-in timestamp, and opt-in source are stored per-record, meeting 2026 US carrier audit requirements. Pilot-level brand and campaign registration with The Campaign Registry is a separate pre-launch operational requirement (see "A2P 10DLC Compliance as Pre-Launch Hygiene" feature row). |
| **Delivery Attempt History** | Every delivery attempt — including provider response code, duration, and outcome — is logged immutably in `notification_delivery_attempt`. |
| **SMS STOP / Opt-Out Webhook Handler** | The inbound SMS webhook handler (Telnyx in MVP; carrier-agnostic via the `SmsCarrier` adapter) processes customer "STOP" SMS replies, immediately setting the opt-out flag and timestamp on the customer record. This is a hard legal requirement under TCPA law and A2P 10DLC carrier rules. Customer "STOP" replies are detected during inbound message routing and bypass normal threading; they update the customer record directly. |
| **Schedule Change Notifications** | Tech assignment changes, schedule modifications, and dispatch reassignments trigger notification_outbox entries for the affected tech. Suppressed for self-assigned actions by the owner-operator. |
| **Customer Communication Templates (13 MVP Active Templates)** | The platform ships with 13 active MVP customer communication templates managed via the `customer_comm_template_type` catalog table (authoritative registry — replacing the raw CHECK constraint). Active MVP templates: `on_my_way` (during_job, tech, manual, sms), `running_late` (during_job, tech, manual, sms), `arrived` (during_job, tech, manual, sms), `job_complete` (post_job, tech, manual, sms), `parts_delay` (during_job, tech, manual, sms), `confirm_appointment` (pre_appointment, tech, manual, sms), `tech_assigned` (pre_appointment, system, automated, sms), `invoice_sent` (post_job, system, automated, email), `payment_received` (post_job, system, automated, email), `payment_reminder` (post_job, system, automated, sms), `change_order_approval` (during_job, owner, manual, sms), `quote_accepted` (quoting, system, automated, email), `quote_expiring` (quoting, system, automated, email). Each template carries category, initiator (tech/owner/system), send_mode (manual/automated/both), and preferred_channel. 14 additional Phase 2 templates are pre-registered as inactive rows in the catalog (full list in `dev-docs/traceability/17-cust-comms-templates.md`). (FIND-083 — Phase 4.2 correction) |
| **Always-Preview-Before-Send Rule** | Every customer communication — whether voice-initiated, touch-initiated, or template-driven — renders a final preview to the originating user before the actual send. The preview shows the rendered message body, the recipient channel, and the recipient identity. The user must explicitly confirm send. This is a non-negotiable safeguard: customer comms are one-way doors, and the platform protects against accidental sends, voice misrecognitions, and stale ETAs. |
| **Per-Message Channel Override** | While each customer has a default communication channel (SMS, email, or both), the user can override the channel on a per-message basis from the preview screen ("send via SMS for this one even though their default is email"). |
| **Communication Preview API Endpoint** | A dedicated `POST /api/v1/communications/preview` endpoint accepts a template selection plus context (job, customer, message variant) and returns the fully rendered message body, recipient information, and channel selection — without sending. The frontend always calls preview before send. |
| **Voice Intent Grammar for Customer Comms** | Voice intent handlers route phrases like "Tell Tom I'm 20 minutes out" to the `on_my_way` template with computed live ETA, then surface the rendered preview before send. Customer comms cannot be sent offline (per §3.15); offline voice capture results in a preview pending sync, sent on reconnection with a recomputed live ETA. |
| **Bidirectional SMS Conversation Threading** | Customer SMS replies route through Pilot to the originating tech with conversation threading by `(tenant_id, customer_id, tech_id, tenant_phone_number_id)`. Inbound messages display alongside outbound in chat-style chronological view. Customer never reaches the tech's personal phone — all SMS routes through the tenant's Pilot-assigned Telnyx number. |
| **Free-Form Tech Reply Composition** | Once a customer replies, the tech can compose free-form text responses through Pilot mobile (templates remain the only option for tech-initiated outreach). Free-form composition supports voice-to-text dictation as the primary input method, with touch typing as fallback. Tier 2 #5's "Customer activity" notification category gains forced-minimum push for inbound customer replies (the originating tech cannot mute push for this category). |
| **Voice-to-Text SMS Reply (Voice Intent)** | The voice intent `reply_to_customer_sms` extends Pilot's voice intent registry. Tech says "Reply to John saying running 30 minutes late," AI captures, transcribes via Whisper, renders preview with segment count + remaining quota, confirms via confirm-as-turn pattern, then dispatches via Telnyx. Always-preview-before-send safeguard applies to voice-composed replies. |
| **Owner Visibility — Web Comm History + Dashboard Widget** | The web `Customers > [customer] > Comm history` surface extends to render inbound and outbound messages in chat-style threaded view. A dashboard widget "Recent customer messages" provides ambient awareness of comm activity across the tenant. Owner mobile receives push for inbound customer messages per Tier 2 #5's "Customer activity" category default. |
| **Telnyx as MVP Carrier; Carrier-Agnostic Adapter Layer** | SMS infrastructure uses Telnyx as the MVP carrier. All carrier interactions go through an `SmsCarrier` adapter interface, allowing future provider swaps as a one-class change. A `MockSmsCarrier` implementation supports integration testing without real carrier API calls. |
| **One Telnyx Number per Tenant; Lazy Provisioning at First Use** | Each tenant gets one Telnyx phone number, provisioned at first SMS use rather than at signup (avoids number rental cost for tenants who never send SMS). Add-on numbers available at +$5/month each (manual provisioning via support in MVP; self-service is Phase 2). |
| **Mobile Inbox "Customer Messages" Sub-Section** | The mobile Today tab gains a "Customer messages" sub-section showing recent threads with unread counts. Tapping a thread opens the conversation thread screen with composition zone (voice-first, touch-fallback). |
| **A2P 10DLC Compliance as Pre-Launch Hygiene** | A2P 10DLC brand and campaign registration with The Campaign Registry is a hard prerequisite for reliable US carrier deliverability. Registration owned operationally by Tom; targets completion 4–6 weeks before MVP launch. Without 10DLC approval, SMS still sends but deliverability is poor (carrier filtering). |
| **Tenant Website Hosting for SMS Compliance (C-B16)** | Sole-proprietor tenants without a website fail TCR 10DLC brand vetting (website URL + About/Contact/ToS/Privacy pages + SMS-specific privacy disclosure are verified). Pilot offers three options at `Settings > Website`: **(1) Compliance Kit** — strong requirements warning at URL entry + one-time emailed requirements content (with pre-merged Privacy/Terms kit text) + always-downloadable Requirements Guide PDF (full TCR requirements + worked examples), for the tenant's own site; **(2) Hosted Compliance Site** — Pilot hosts a 3-page site (business-identity landing + privacy + terms, locked versioned templates containing the required SMS clauses) at `{slug}.{tenant-sites-domain}`, free on all paid tiers (Charter included), auto-populates the 10DLC brand `website` field; **(3) Hosted Starter Site** (post-MVP, C-B17) — full single-page business site as a paid add-on. Hosted pages are public and unauthenticated by design (TCR vet access); publish follows preview-and-confirm per the always-preview-before-send rule; compliance language is tenant-noneditable. |
| **Notification Preference Matrix (Per-User × Per-Category × Per-Channel)** | Each user controls notification preferences at `Settings > Notifications > Preferences` via an 8-category × 3-channel matrix (push / email / in-app banner). Categories: Quote approvals, Field issues, Sync conflicts, Job activity, Customer activity, Billing, Background sync alerts, System announcements. Three-tier resolution chain: user override → tenant default → system default. Per-row revert and per-cell revert affordances. Page-level "Mute all push (non-critical)" / "Mute all email" / "Reset to tenant defaults" controls. |
| **Forced-Minimum Push for Safety-Critical Categories** | Four categories have forced-minimum push that cannot be muted by user override: Field issues (all users), Job activity assignment-only sub-trigger (the tech being assigned), System announcements critical-only sub-trigger (all users), Customer activity inbound-SMS-reply sub-trigger (the originating tech in conversation only — not other recipients). User-context-asymmetric semantics for Customer activity is a new pattern: same category, different forced-minimum based on whether user is the tech in conversation or another user receiving ambient awareness. |
| **Tenant-Level Notification Defaults** | Owners set tenant-level default policies at `Settings > Notifications > Tenant defaults` separate from personal preferences. Same matrix structure; edits affect tenant defaults, not the owner's user override. RBAC: owner-only access. |
| **In-App Banner Notification Channel** | New channel for in-app real-time delivery via Server-Sent Events. Slim slide-down notification at top of active page; auto-dismiss after 6 seconds (12 seconds for critical); manually dismissable; click-to-navigate to relevant entity. Notification center bell in app shell shows unread count from last 24 hours + history of last 50. Shared component across web and mobile. ARIA accessibility for screen reader announcement. |
| **Notification Category Registry** | All backend notification firing sites classify into one of the 8 categories with optional sub-trigger metadata. Category registry seeded at deployment with category metadata (display label, description, forced-minimum push policy). Sub-triggers (e.g., `customer_activity.inbound_sms_reply`, `job_activity.assignment`) drive the asymmetric forced-minimum behavior. |
| **Delivery Dispatcher Preference Gate** | The notification delivery dispatcher consults user preferences before dispatching each channel for each recipient. Per-recipient evaluation handles the user-context-asymmetric forced-minimum (e.g., the tech in a conversation gets forced push for inbound SMS replies; the owner watching ambient does not). Compose with rate limiting: a notification must clear both rate limit (existing) and user preferences to be delivered. |
| **Push Deep-Link Routing** | Push notifications include deep-link metadata routing the user to the relevant entity when tapped. Per-category deep-link mapping: Quote approvals → quote detail; Field issues → field issue resolution; Sync conflicts → integration conflicts queue; Job activity → job detail; Customer activity → comm history thread; Billing → invoices/subscription; Background sync alerts → mobile sync queue; System announcements → announcements archive (Phase 2 surface route reserved). |
| **Tenant Email Branding (Structured Customization)** | At `Settings > Communications > Email branding`, tenants customize their customer-facing email branding: logo upload, brand color picker, signature text, optional custom footer text. Live preview + test-send-to-my-address. Customer-facing emails (quote sent, invoice sent, payment received, etc.) render with tenant branding; internal emails (welcome, password reset, MFA reset, etc.) use Pilot standard branding. Full template editing deferred to Phase 2. |
| **16 Transactional Email Templates** | MVP ships with 16 transactional email templates organized by category: welcome, email verification code, quote sent, quote accepted, quote declined, quote expiring, invoice sent, payment received (tenant + customer receipt), payment failed, subscription renewal, subscription payment failed, trial expiring soon, trial expired, password reset, MFA reset by owner, data export ready. Single consistent template framework with per-template content slots. Variable substitution (customer name, quote total, signed URL, etc.) at render time. Content authoring is Tom-owned pre-launch hygiene work. |

---

### 3.8 Platform Infrastructure

**Domain Purpose**: Provide the foundational reliability, security, and operational integrity guarantees that all other product domains depend on — multi-tenancy, idempotency, rate limiting, real-time event delivery, and the cross-cutting design patterns formalized at the platform level.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Multi-Tenant Isolation (Full Stamp Coverage)** | All data tables carry `tenant_id`. Immutability guards on all tables prevent `tenant_id` reassignment after creation. |
| **UTC "Triple-Lock" Enforcement** | All timestamp columns use `TIMESTAMPTZ`. All Python datetime objects use `datetime.now(UTC)`. All Pydantic schema fields use `AwareDatetime`. |
| **Idempotency / Double-Tap Protection** | A 24-hour idempotency key table with pessimistic row-level locking prevents duplicate API requests from creating duplicate financial records. Extended for offline operations (per §3.15) with client-generated UUIDs and natural-key fallback dedup on a 7-day window for the 72-hour offline scenario. |
| **Basic Rate Limiting (1,000 req/hr per Tenant)** | Tenant-scoped rate limiting is enforced in the FastAPI app via SlowAPI (Redis-backed) on routes that opt in. |
| **Financial Hard-Delete Lockdown** | All structural foreign keys in the financial data hierarchy are configured with `ON DELETE RESTRICT`. |
| **Soft-Delete Cascade Triggers** | PostgreSQL `AFTER UPDATE OF is_active` triggers propagate parent deactivation through CRM, Sales, and Billing hierarchies. |
| **Server-Sent Events (SSE) for Live Dispatch Board** | The dispatch board (§3.14) uses SSE to push live updates — schedule changes, tech assignments, conflict status — to all connected dispatcher clients without polling. |
| **Pre-Commit Staleness Check Pattern (409-and-Refresh)** | A platform-wide concurrency pattern: write endpoints accept expected-version timestamps and return `409 Conflict` with refreshed state when the underlying record has changed since the client last viewed it. Used by dispatch board edits, calendar conflict resolution, mobile sync conflict resolution, and quote approval. |
| **Two-Tier Configuration Pattern (System Default + Tenant Override)** | Settings that need both platform-wide control and per-tenant flexibility use a system default at the platform admin level plus a nullable per-tenant override. Effective value resolution: tenant override → system default → fallback constant. Used for calendar conflict auto-expiry windows, with the pattern available for any future setting. |
| **Mobile Sync Queue Infrastructure** | Server-side `mobile_sync_event` append-only log captures every sync attempt per device per operation, enabling cross-device visibility (owner reviewing tech's sync state, support troubleshooting). 30-day hot retention, archived consistent with audit log policy. |
| **Conflict Severity Classification Engine** | A data-driven, configurable classification engine routes detected conflicts into four severity tiers: `auto_silent`, `auto_notice`, `tech_resolvable`, `owner_escalation`. Used by mobile sync conflicts (per §3.15) with a per-operation classification matrix tunable without code deploys. |
| **Resumable Multipart Photo Upload Pipeline** | S3 multipart upload directly from client with signed URLs handles photo uploads. Client SDK tracks per-chunk completion and resumes from last-completed chunk on retry, eliminating "tech walked out of WiFi range mid-upload" data loss. Server-side cleanup of incomplete uploads expires after 24 hours via S3 lifecycle rule. |
| **Voice Audio Deferred Processing Pipeline** | Audio captured offline uploads to a dedicated endpoint on reconnection, queues for Whisper transcription and Llama intent parsing via Celery, and surfaces results through the normal voice intent flow with deferred-confirmation handling for destructive intents. |

---

### 3.9 QuickBooks Integration

**Domain Purpose**: Provide a fully bi-directional, conflict-aware sync between Pilot and QuickBooks Online, eliminating manual double-entry bookkeeping.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Bi-Directional Customer Sync** | Customer records sync in both directions between Pilot and QuickBooks using internal and external version tokens for change detection. |
| **Sync Dashboard & Queue Visibility** | Every sync operation — success, failure, and conflict — is logged to `integration_sync_log` and `integration_sync_conflict`. |
| **Conflict Resolution UI (Bilateral Integration Conflict Pattern)** | When sync detects a conflict (both Pilot and QuickBooks modified the same entity since last sync), the conflict is captured in `integration_sync_conflict` with both snapshots plus the last-shared-state baseline for accurate field-level diff. Resolution UI at `Settings > Integrations > QuickBooks > Conflicts` renders side-by-side two-column diff (master direction-aware: Pilot-left for Quote conflicts, QB-left for Invoice conflicts; tenant override for Customer/Expense). Field-level track-changes vocabulary (amber/green/red). Two primary action buttons with master-aware primary-button treatment. Deletion-conflict variants use distinct verb-based treatment. Pre-commit staleness check with three 409 payload types (server changed, auto-recovered, stale). Voice scope: status query only (no voice resolution due to accounting integrity stakes). |
| **Invoice & Payment Push Sync** | Pilot invoices and collected payments are pushed to QuickBooks as Estimate/Invoice and Payment records via Celery workers. |
| **Tax Liability Sync (Tax Agency Mapping)** | Pilot tax components are mapped to specific QuickBooks Tax Agency liability accounts via `external_tax_agency_id`. |
| **Sync Conflict Notification to Owner** | When a sync conflict is written to the conflict log, the system automatically enqueues an SMS or email notification to the tenant owner. |
| **Per-Entity Auto-Expiry Configuration (Tenant Opt-In)** | Auto-expiry is OFF by default for all four bilateral entity types (Customers, Quotes, Invoices, Expenses) — opposite of calendar's default-ON because QB has heterogeneous masters and accounting recovery cost is higher. Tenants opt in per entity type with paired enable + direction (`accept_local | accept_remote`) settings: `qb_auto_expire_customer_enabled` + `qb_auto_expire_customer_direction` (and parallel for quote, invoice, expense). When enabled, auto-expiry timing uses `qb_auto_expire_days` (default 60; longer than calendar's 30 because accounting cadence is quarterly) and `qb_pre_warning_days` (default 14). Save-on-group-complete pattern in the settings UI prevents half-baked enable-without-direction state. |
| **Invoice-Specific Financial-Delta Callout** | For invoice conflicts only, the resolution view includes a financial-delta callout above the diff showing total amount delta, AR impact preview, tax-period spanning warning when applicable, and a deep-link out to the invoice in QB's web UI. This recognizes that invoice conflicts have downstream consequences (AR balances, customer statements, tax filing) that calendar conflicts don't have. |
| **In-Flight Sync Indicator with Pending Count** | The QuickBooks sync indicator extends the platform-level In-Flight Sync Indicator pattern (§4.1): shows synced state plus a count of pending operations in either direction. Five compositional states: synced-idle, synced-with-pending, syncing-active, sync-error, sync-paused. Hover/tap surfaces individual pending entity changes (capped at 5 with "+N more"). Manual sync trigger inline in the indicator. Tunable threshold (`tenant_sync_indicator_pending_amber_threshold`, default 5) shifts visual emphasis to amber when pending count is operationally meaningful. |

---

### 3.10 Sales & Quoting

**Domain Purpose**: Power the full quote-to-cash lifecycle: rapid AI-assisted quote creation, real-time material pricing, professional customer-facing proposals with multiple presentation styles, structured quote approval workflow, time-limited discounts, digital acceptance, and automatic conversion to jobs.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Voice-Command Quote Creation** | Contractors can initiate a new quote using a natural language voice command. The Voice AI routes the intent to a quote creation handler. Multi-turn refinement is supported via conversation sessions (§2.2). |
| **Real-Time Material Pricing** | Quote line items pull live material pricing from the supplier pricing cache. All prices used on a quote are immutably snapshotted at time of quote creation. |
| **Immutable Quote Version Control (Revisions)** | Every modification to a sent quote creates a new, append-only version record. |
| **Pre-Sale Profit Margin Visibility** | Each quote line item stores both customer-facing selling price and internal cost basis. |
| **Three Quote Presentation Styles** | Quotes can be presented to customers in three styles: `clean` (single all-in price with optional summary lines), `line_itemed` (full itemization with quantities, descriptions, unit prices, line subtotals), `hybrid` (sectioned with grouped subtotals; details shown per section). The contractor chooses style at quote creation; the customer sees only the chosen style on the public proposal. Style is preserved on the immutable version record. |
| **Quote Line Item Visibility & Hierarchy** | Each line item carries `is_visible_to_customer` and `parent_line_item_id` fields, enabling internal-only items (notes, internal cost categorizations) and parent-child relationships for sectioned line items. The hybrid presentation style uses these to render grouped sections. |
| **Quote Template System with Style and Versioning** | Templates carry both content and a default presentation style. Templates are versioned: editing a template creates a new version while preserving the prior version for in-flight quotes. Both `system` (Pilot-curated) and `tenant` templates are supported. Tenants can fork system templates to make them tenant-owned and editable. |
| **System Template Update Notifications** | When Pilot updates a system template (e.g., a new NEC reference, a pricing methodology improvement), tenants whose recent quotes used that template receive a notification with a link to review and optionally adopt the update. |
| **Save Quote as Template** | From any quote, contractors can save the current quote (with line items, style, and metadata) as a new tenant template. |
| **Multi-Line Description Editing Support** | Quote line item descriptions support multiple paragraphs of text (rich text not required at MVP; plain text with line breaks). The editor supports inline editing without requiring a separate modal. |
| **Quote Approval Workflow (Tech Submit, Owner Approve)** | When `require_approval_for_tech_quotes` tenant setting is ON (default for multi-user tenants; OFF for solo), tech-created quotes are submitted to a pending state for owner review. The tech sees their quote as "submitted for approval"; the owner sees a pending queue. The owner approves, rejects with comments, or edits-and-approves. |
| **Track-Changes Review for Quote Edits** | When a quote is in pending-approval state, owner edits are stored as pending changes (not committed) until the owner approves. The review UI shows inline track-changes diff against the tech's submitted version using the platform-wide track-changes vocabulary (amber=modify, green=add, red=remove). |
| **Approval Comments & Annotations** | Owner can add inline annotations on specific line items during review (e.g., "Verify this material is in stock") and a top-level approval/rejection comment. Annotations persist on the version record. |
| **Voice-Initiated Quote Approval** | Owners can approve, reject, or request edits to pending quotes via voice ("Approve the Johnson quote"; "Reject the Davis quote — pricing too aggressive"). Confirm-as-turn applies (§2.2). Voice cannot make line-item edits — those route to the web review UI via refusal-with-redirect. |
| **Time-Limited Discounts with Margin Cap** | Owners (and accountants) can apply time-limited discounts (e.g., 10% off if accepted within 7 days). Discounts are capped at the tenant-configured `max_discount_pct_owner` (default 15%) to prevent margin destruction. Excessive-discount attempts trigger a warning and require explicit override confirmation. |
| **Interactive Web Proposals (Public Quote Links)** | A secure, SHA-256-tokenized public URL is generated for each quote, enabling the contractor to share a professional, mobile-friendly proposal with the customer via email or SMS — no login required for the customer. |
| **Digital Acceptance (Click-to-Accept / E-Sign)** | Customers can accept a quote directly from the public link. The acceptance record captures the customer's name, email, IP address, and user agent. |
| **Quote Expiration Auto-Transition** | A Celery Beat scheduled task automatically monitors sent quotes past their `expires_at` date and transitions their status to `expired`. |
| **Read Receipts & Quote View Analytics** | Every customer interaction with a public quote link is logged. |
| **Auto-Conversion: Accepted Quote → Job** | When a quote is accepted, a single API call validates the acceptance, creates the job record, copies all relevant data, links the job to the accepted quote version, and transitions the quote status to `converted`. |
| **Change Order Management** | Field technicians can create and modify change orders on active jobs from the mobile app. Change orders are linked to a quote version and trigger automatic job total recalculations. |
| **Public Quote Link with 90-Day Signed URL** | Each quote generates a signed-URL public page customers access without Pilot login. URL expires 90 days from generation. Already-acted-upon revisits show acceptance/decline confirmation rather than action buttons. State-aware rendering prevents double-actions. |
| **Customer Quote Acceptance with Optional Comment** | Customer accepts the quote from the public link; an optional comment field captures context ("Let's get started ASAP — when can you begin?"). Comment stored on the quote record (`quote.customer_acceptance_comment`), visible prominently on the quote detail in Pilot. Tenant notified per Tier 2 #5 "Customer activity" category. |
| **Customer Quote Decline with Reason + Comment** | Customer declines with a structured reason (Pricing / Scope / Timing / Other contractor / Other) plus optional free-text comment. Stored on the quote record (`quote.customer_decline_comment`, `quote.customer_decline_reason`). Tenant notified with comment in body. Once declined, quote stays in declined state — tenant generates a new quote if they revise based on feedback. |
| **Customer-Facing Page Tenant Branding** | Public quote pages use the tenant's email branding settings (logo, brand color, signature, custom footer) — same configuration as customer-facing emails. Subtle "Powered by Pilot for Trades" footer; tenant brand prominent. |
| **Quote Already-Acted-Upon Handling** | Customer revisiting a public link after taking action sees the resulting state (accepted with date and comment; declined with reason and comment; expired). No accidental re-actions possible. |

---

### 3.11 Subscriptions & Usage

**Domain Purpose**: Model tiered SaaS subscription plans, enforce schedule lane and feature entitlements at the API layer, meter AI and SMS usage in real time, and automate recurring billing and overage charges.

> **Pricing Model (v3.5, Aug 2026)**: Pilot uses a 2-tier paid model (Starter / Teams) plus a time-limited **Charter cohort plan** (formerly "Founders" — renamed per GTM v3 locked decision D1; free period is 90 days per D16) and a 14-day trial. The core licensing metric is **schedule lanes** — the number of concurrent jobs that can be active on the dispatch board simultaneously. Unlimited users, jobs, quotes, invoices, customers, QB syncs, emails, and calendar syncs on all plans. **This §3.11 is the master subscription/pricing definition for all engineering and design work — values elsewhere (docs, rules snapshots, seed data, UI copy) must trace to this table.**

> **⚠️ Maintenance cascade (MANDATORY for any agent editing this section)**: a change to any plan name, price, allowance, limit, enforcement mode, or overage rate in §3.11 is **not done** when the PRD edit lands. The same change must refresh the dated snapshots in ALL of these files (each cites this section as master):
>
> - `.roo/rules-pilot-python-engineer/python-engineer-rules.md` — §18 (and the §17 valid-code list)
> - `.roo/rules-pilot-react-engineer/react-engineer-rules.md` — §30
> - `backend/python-engr-std-prompt-inclusions.md` — §19
> - `frontend/react-engr-std-prompt-inclusions.md` — §19
> - `.roo/rules-pilot-devops-engineer/subscription-pricing-master-reference.md`
> - `.roo/rules-pilot-web-ui-designer/subscription-pricing-master-reference.md`
> - `.roo/rules-pilot-voice-ui-designer/subscription-pricing-master-reference.md`
> - `.roo/rules-pilot-marketing-ui-designer/subscription-pricing-master-reference.md`
>
> …and must reconcile the derived/runtime surfaces in the same change: `dev-docs/pilot-operations.md` §2–§3, §5–§6 (tier→plan→ppfv cascade), `backend/migrations/scripts/seed_core.py` (`PRODUCT_FEATURE_ROWS`), `backend/migrations/scripts/seed_platform.py` (`PLAN_FEATURE_LIMITS` + `PRODUCT_PLAN_PRICES`), `dev-docs/integrations/stripe/stripe-pricing-config.md` §4 (price IDs), and `pilot-docs-list.md` (version/date sync). Strategy/framing changes decided in `pilot-gtm-strategy-v3.md` §5–§6 must be reflected here first — the cascade runs from this table. **The Architect owns this cascade; a §3.11 edit without it is an incomplete change.**

#### Pricing Table

| Plan | Price (billed annually; month-to-month $59 Starter / $179 Teams) | Schedule Lanes | Voice AI | SMS Segments | Overage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Charter** (12-member cohort, formerly Founders) | $0 × 90 days, then **$49/mo locked for life** (billed monthly at the annual rate) | 5 | 90 min | 100 segs | No overages during free period; soft cap thereafter; free period operator-extendable per tenant (case by case; not an advertised offer) (GTM v3 D16) |
| **Trial** | $0 (14 days) | 5 | 90 min | 100 segs | Hard cap — no CC required, no overages |
| **Starter** | **$49/mo** | 5 | 90 min | 100 segs | Voice AI $0.05/min; SMS $0.05/seg |
| **Teams** | **$149/mo** | 20 | 300 min | 500 segs | Voice AI $0.05/min; SMS $0.05/seg |
| ~~Enterprise~~ | ~~$499/mo~~ | ~~75~~ | ~~1,000 min~~ | ~~2,500 segs~~ | **Removed** — `is_active=false` |

**Schedule lane add-ons**: +1 lane $10/mo · +5 lanes (pack) $40/mo

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Schedule Lanes (Dispatch Capacity Licensing)** | A **schedule lane** is a visual row on the dispatch board — a concurrent job slot that holds one or more non-overlapping jobs throughout the day. Any user (owner, tech, apprentice, office staff) can be assigned to any job in any lane at no additional charge. Unlimited users applies with zero asterisks. The lane is the scheduling resource, not the person. Starter=5 lanes; Teams=20 lanes. Add-on packs available (+1 lane/$10/mo, +5 lanes/$40/mo). Enforcement: when a tenant attempts to schedule a new job whose time window would overlap all existing lanes, the system blocks with an upgrade prompt. |
| **Charter (Founders) Plan** | Time-limited cohort plan for the first 12 paying-customer candidates — the cohort size is hard-capped in software (GTM v3 D15). **90 days free** (full Starter-level limits, no card required), then **$49/month locked at Starter limits for life**, billed monthly at the annual rate with no annual commitment (GTM v3 D16/D17). The price lock applies to the Starter feature set (5 schedule lanes, 90 Voice AI min/mo, 100 SMS segs/mo). Members remain on `charter_plan` indefinitely at $49/mo; their price never increases. If a member's business grows beyond Starter limits (e.g., needs 20+ lanes or 300+ Voice AI minutes), they upgrade to Teams at the standard $149/month. Plan deactivated (`is_active=false`) when the cohort cap is reached; existing members remain grandfathered at $49/mo forever regardless of deactivation. The 90-day free period can be extended per tenant by an operator, case by case — it is not an advertised offer or an incentive (GTM v3 D16). **Marketing copy angle**: *"Lock in $49/month forever — your price never goes up. When your business is ready for more, Teams is always available."* |
| **Tiered Subscription Plans** | Multiple subscription tiers backed by `product_plan` and `product_feature` records. Each tier defines schedule lane count, Voice AI minutes, SMS segments, and overage rates. Tier metadata is data-driven — adding/editing tiers is a DB update, not a code change. |
| **Monthly vs. Annual Billing Intervals** | Subscriptions support monthly and annual billing intervals. Annual billing carries a 17% discount vs. monthly. |
| **Metered Consumption Tracking (Usage Ledger)** | Every Voice AI minute and SMS segment consumed is written as an immutable row to the append-only `usage_ledger` table. Schedule lane usage is enforced at job-scheduling time (not metered post-hoc). |
| **Included Allowances & Soft / Hard Plan Limits** | Each feature on each plan version stores `included_quantity`, `limit_quantity`, `overage_price_cents`, and `limit_enforcement` ('soft' or 'block'). Trial plan uses 'block' enforcement (no overages). Paid plans use 'soft' enforcement (usage continues, overage billed at period end). |
| **Feature Entitlement / Plan Limit Enforcement (API Middleware)** | The `require_permission()` FastAPI dependency reads the active subscription's feature entitlements and enforces plan limits at the API layer. Schedule lane enforcement runs at job-scheduling time via a dedicated lane-availability check. |
| **Grandfathered Pricing (Temporal Plan Versions)** | Plan pricing is versioned with temporal GiST exclusion constraints. Charter members locked at $49/mo indefinitely via this mechanism — any future price change does not affect existing Charter subscribers. |
| **Automated Recurring Billing & Usage Aggregation** | A Celery Beat task aggregates consumption per tenant per feature on a billing cycle cadence, writes to `subscription_usage`, and triggers overage charges via Stripe at month-end. |
| **Admin Tenant Feature Override API** | An admin-only API endpoint allows Pilot support staff to write manual feature limit overrides via `tenant_product_feature_override`. |
| **SMS Subscription Quota** | Starter includes 100 SMS segments/month; Teams includes 500/month. Add-on Telnyx numbers each add 100 segments at +$5/month per number. |
| **Tenant-Controlled SMS Cap Policy (Soft / Hard)** | Tenants choose: (a) soft cap (default) — SMS overages billed at $0.05/segment at month-end with no operational interruption; (b) hard cap — all outbound SMS blocked at 100% quota. Setting `sms_quota_cap_policy` (default `soft`); owner-only edit. Trial plans are always hard-capped. |
| **In-Month SMS Usage Visibility** | Tech and owner see real-time SMS usage and remaining quota. Mobile composition zone shows segment count + remaining; web dashboard widget shows current, projected month-end, policy. Notifications fire at 80% and 100% usage thresholds. |
| **SMS Overage Billing** | Soft-cap tenants accrue overage charges at $0.05/segment at month-end, added to the next subscription invoice as a line item. Failed sends not counted (atomic rollback on carrier failure). MMS not included in MVP. |
| **Voice AI Overage Billing** | Soft-cap tenants accrue overage charges at $0.05/minute at month-end, added to the next subscription invoice as a line item. |
| **Trial-as-Tier Framing** | The trial is a subscription tier with `is_trial=true`, $0 price, 14-day duration, Starter-level limits, and hard cap enforcement. Full feature parity with Starter. No special "trial mode" branching in the codebase — every code path answers "what tier?" via the clean tier system. |
| **Operator-Controlled Trial Length** | Trial duration defaults to 14 days, with per-tenant override capability via `tenant_tier_override.override_trial_length_days`. Operator manages via direct DB updates for MVP. |
| **Trial Expiration with Read-Only Paywall** | When a trial ends without conversion, the tenant enters "trial expired" state with read-only access and a paywall surface. New data creation, SMS, and voice operations blocked. Pre-expiration warnings at 7 days, 3 days, 1 day, and on expiration day (email + push + in-app banner). Data preserved for dormant trial resurrection. |
| **Stripe Integration for Subscription Billing** | Stripe Subscriptions for recurring billing of paid tiers. Stripe Elements for PCI-compliant card collection at signup or trial conversion. Stripe Customer Portal deferred to Phase 2; MVP has read-only billing display at `Settings > Subscription & Billing` with "Upgrade plan" affordance. Stripe webhooks handle subscription events (created, updated, deleted, payment success, payment failure). |
| **Trial-to-Paid Conversion Flow** | At any point during trial (or at expiration), tenant converts to Starter or Teams via tier picker + Stripe Elements. Stripe Customer record created on first paid conversion and reused for tier changes. |
| **Subscription Usage Tracking** | MVP tracks three usage metrics per tenant: Voice AI minutes, outbound SMS segments, and schedule lane peak concurrent count. Period-aligned to subscription billing cycle. |
| **Operator-Controlled Tier Overrides** | For special cases (comp accounts, support escalations), operator can override a tenant's tier without payment. Stored in `tenant_tier_override.override_tier_id` with required `override_reason`. Audit-logged. |
| **Dispatch Board Redesign (Schedule Lane UI)** | The dispatch board UI must be redesigned from the current tech-as-column layout to a lane-based layout where each lane is a horizontal row holding non-overlapping jobs. Any user can be assigned to any job in any lane. This is a P1 item required before general availability — see §3.8 Scheduling & Dispatch. |

---

### 3.12 Tax Calculation

**Domain Purpose**: Calculate accurate, multi-jurisdiction, multi-component sales tax on every quote and invoice line item, with full historical immutability and QuickBooks tax agency mapping.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Compound / Stacked Taxes (State + City + Special District)** | The tax engine produces multiple componentized `*_tax_component` rows per line item. |
| **Material vs. Labor Taxability Rules** | A `taxability_code` lookup is applied at the individual line-item level. |
| **Tax-Exempt Customers** | When a customer is assigned `taxability_code = 'exempt'`, the tax calculation engine returns explicit zero-tax components. |
| **Historical Tax Snapshot Immutability** | Each `*_tax_component` record carries a foreign key to the exact `tax_rate_version` active at the time the quote or invoice was created. |
| **IRS-Compliant Rounding** | Tax component amounts are calculated using `math.ceil(subtotal_cents * rate_pct / 100)` at the individual component level before summing. |
| **GiST Constraint Hardening for Taxability Codes** | The `tax_rate_version` exclusion constraint discriminates by both `jurisdiction_code` AND `taxability_code`. |

---

### 3.13 Voice AI

**Domain Purpose**: Deliver the Pilot "Digital Apprentice" experience — a conversational AI layer that understands electrical trade terminology, sustains continuity across multi-turn conversations, routes voice commands to platform actions with appropriate confirmation and disambiguation, processes offline-captured audio via deferred pipeline, and assists technicians with NEC code calculations.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Voice-Driven Time & Expense Logging** | Technicians can clock in, clock out, and log material expenses using natural language voice commands. Offline-capable per §3.15. |
| **Voice Customer & Quote Creation** | Contractors can create new customer records and initiate new quotes through voice commands. |
| **Conversation Sessions with Numbered Identifiers** | Voice interactions are organized into named, numbered sessions ("#3 — Johnson panel quote"). Session numbers monotonically increment per tenant. Sessions are user-resumable, renamable, and listable across both web and mobile. |
| **AI-Generated Session Titles (Ollama)** | Session titles are auto-generated by Llama from the first meaningful exchange (e.g., "Johnson 200A panel quote draft"), updated as the session evolves, and overridable by user. |
| **Pronoun Resolution & Session Continuity** | A `context_window_json` on each session tracks active references (`active_quote_id`, `active_job_id`, `active_customer_id`), enabling pronoun resolution ("update it", "add to that job") across multiple turns. Context survives session pause/resume. |
| **Confirm-as-Turn for Destructive Actions** | All voice intents that create, modify, or delete durable data route through an explicit confirmation turn before commit. Universal across the platform: quote send, calendar conflict resolution, schedule changes, quote approval, job deletion, sync conflict resolution. |
| **Disambiguation Pattern** | When a spoken reference matches multiple entities, the AI asks rather than picks. Discriminating attributes are surfaced in the disambiguation prompt. |
| **Refusal-with-Redirect for Out-of-Scope Intents** | Out-of-channel requests (blended conflict resolution, complex multi-line edits) refuse cleanly and offer a redirect to the appropriate web surface. |
| **Voice Feedback Loop** | Owners and accountants can flag voice misrecognitions in-context ("that's not what I said") which queue for review. The feedback corpus informs model fine-tuning over time. |
| **Structured Message Payload (Live/Snapshot Modes)** | Conversation messages support a structured content payload that can render in either live mode (current data, e.g., live ETC for a job) or snapshot mode (frozen at message time, e.g., the quote draft as seen at that turn). The frontend distinguishes the two visually. |
| **Voice Persona Tone (Three-Position Enum with Per-User Override)** | Tenant-level setting `voice_persona_tone` controls AI personality across voice readback, session titles, assistant turn responses, and Voice tab empty states. Three positions: `conservative` (formal, brief), `balanced` (default), `playful` (warmer, conversational). Per-user override allowed by default; tenant can disable per-user override via meta-toggle. Three-tier resolution: user override → tenant override → system default → fallback. Each tone has dedicated Ollama prompt templates (one per voice context). Three preview audio clips (one per tone) are server-cached MP3s playable from the settings UI. Session titles use the session creator's tone (creation-time artifact). Empty-state copy uses the viewing user's tone. Customer-facing surfaces (SMS templates, transactional emails) explicitly NOT affected by tone — fixed branding regardless of tenant tone. |
| **NEC Code Assistance (Voltage Drop & Conduit Fill)** | The Voice AI calculates NEC voltage drop, conduit fill, and ampacity in response to spoken queries. Calculations draw from the integrated NEC 2023 Reference Guide corpus. |
| **Safety Protocol Prompts (LOTO Verification)** | Structured `safety_loto_verified` field in `context_window_json` is checked before allowing job-completion commands. The system blocks progress until LOTO is confirmed. |
| **Schedule-Aware Voice Intents** | Intents `schedule_job`, `reassign_job`, `reschedule_job`, `check_next_job` enable voice-driven dispatch management. Each handler validates against scheduling conflict detection before executing. |
| **Comms-Aware Voice Intents** | Intents `tell_customer`, `update_customer`, `quote_status_to_customer` route to template-driven customer comms with always-preview-before-send (§3.7). |
| **Approval-Aware Voice Intents** | Intents `approve_quote`, `reject_quote`, `request_edits` enable voice-driven quote approval. |
| **Sync-Conflict-Aware Voice Intents** | Intents covering calendar sync conflict resolution: `query_pending_calendar_conflicts`, `resolve_calendar_conflict_local`, `resolve_calendar_conflict_remote`, plus four explicit-verb variants for deletion conflicts. All use confirm-as-turn. |
| **Offline Voice Audio Capture** | Voice audio captured while offline saves locally and uploads on reconnection (per §3.15). The tech sees "voice captured" not "voice failed"; the resulting intent runs through normal disambiguation/confirmation when transcription completes. |
| **AI-Mediated Help (RAG over Markdown Corpus)** | Help is delivered via AI chat conversation using the same Llama 3.x infrastructure as voice intents (separate prompt + RAG context). Help corpus is markdown files in S3 with structured frontmatter; chunks embedded into pgvector for semantic retrieval. User queries trigger top-K chunk retrieval; chunks injected into prompt as grounding context. Chat sessions captured (90 days unscrubbed, then anonymized) for training data. AI knowledge boundaries explicitly enforced — does not take actions, does not access tenant data, does not give legal/financial advice. Three escalation triggers route stuck users to feedback submission. |
| **Context-Aware Help Opener** | When user opens help from inside a settings page or flow, AI receives a minimal context payload (current route, entity type if applicable, recent action types in last 5 minutes, user role, tenant metadata) for grounded responses. Action types only — no entity contents — for privacy. AI initial message reflects context: "I see you're on the QuickBooks integration page — how can I help?" |
| **Help Voice Intent + Voice-Driven Mode** | Voice intent grammar extends with `open_help` and `ask_help_question` intents. Users can interact with help entirely via voice — voice input on chat composition, TTS readback of AI responses (using user's effective voice persona tone for consistency), continued voice-only flow until user types or taps to switch to text. |
| **Past Conversations Recall** | Users can review prior help chat sessions at `Help > Past conversations` with AI-generated brief titles per session (reuses A11 session title infrastructure). Tapping opens the session's full chat history; user can continue where they left off (within 90-day retention). |

---

### 3.14 Scheduling & Dispatch

**Domain Purpose**: Own the authoritative schedule of when each job happens, which tech is assigned, and in what order the day's stops are run. Provide the dispatch board with live updates and four-class conflict detection, the tech-facing today view on mobile, automated feasibility warnings when drive times don't fit, and bi-directional sync with an external company calendar — including a full conflict resolution surface for the inevitable bi-directional sync collisions.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Job Scheduling with Time Windows** | Every job carries `scheduled_start_at` and `scheduled_end_at` timestamp pair, a site reference, and a tech assignment. |
| **Tech Availability Windows** | Each tech user carries `tech_availability` records defining recurring working hours, PTO blocks, and one-off unavailable periods. |
| **Single-Tech Assignment (UI) with Multi-Tech Schema** | The MVP UI limits job assignment to one tech per job. The underlying `job_tech_assignment` table supports many-to-many for Phase 2 multi-tech crews without database migration. |
| **Four-Class Dispatch Conflict Detection** | When a job is placed, the system computes four classes of conflict: `overlap` (two jobs of the same tech overlap), `availability` (outside working hours / inside PTO), `travel` (insufficient drive time between consecutive jobs), `info` (advisory but not blocking, e.g., scheduled tightly). Each class has a distinct visual treatment on the dispatch board. Voice-commanded scheduling actions are blocked if they would create a blocking-severity conflict. |
| **Manual Route Sequencing with Drive-Time Assist** | The dispatch board orders a tech's daily jobs chronologically. When the owner reorders, the system recomputes drive times via the map provider's distance-matrix API and displays them inline between stops. |
| **Drive-Time Caching** | Distance-matrix lookups are cached server-side keyed on origin/destination pair to reduce API costs and improve dispatch UI responsiveness. Cache invalidation on address changes only. |
| **Dispatch Board (Tech × Time Grid) with Live Updates** | The primary scheduling UI on web renders as a grid of tech columns × time rows, with job cards placed at their scheduled time slots. Server-Sent Events push live updates to all connected dispatchers — schedule changes, tech assignments, conflict status — without polling. Drag-to-reschedule, drag-to-reassign, and resize-to-extend interactions are supported. Unscheduled jobs queue in an "Unassigned" column for drag-to-dispatch. |
| **Tech Color Palette (12-Hue System Default)** | Each tech is assigned a distinct color for visual identification on the dispatch board. The platform ships with a 12-hue system default; tenants can override with a custom palette via `tech_color_palette` setting. |
| **Today's Schedule on Mobile** | The mobile `Today` tab pulls each tech's assigned jobs for the current day, ordered by `scheduled_start_at`, annotated with site address, customer name, and drive time to next stop. |
| **Tech Assignment Notifications** | When a tech is assigned, reassigned, or has a scheduled time changed, push notification + `notification_outbox` entry are generated. Suppressed for self-assignment. |
| **Customer ETA Data Feed** | Computed ETA for each tech's next customer stop, derived from current GPS location, route sequence, and live drive-time estimates. Consumed by §3.7 customer comms templates. |
| **Calendar Provider Sync (Shared Company Calendar)** | Each tenant's owner connects one external calendar (Google Calendar at beta; provider-abstract at architecture layer) as the tenant's shared company calendar. All scheduled jobs bi-directionally sync. |
| **OAuth 2.0 Calendar Connection Flow** | Tenant owner initiates calendar provider OAuth from `Settings > Integrations > Calendar`. Tokens encrypted at rest via Fernet. Token refresh automated via Celery Beat. Connection health surfaced as a status indicator on the dispatch board and on the mobile Owner tab. |
| **Calendar Sync Conflict Detection** | Bi-directional sync detects three classes of conflict: `Modified ↔ Modified` (both sides edited), `Deleted ↔ Modified` (one side deleted, other edited), `Modified ↔ Deleted` (inverse). Conflict state captured with `pilot_snapshot`, `external_snapshot`, and `base_snapshot` (last shared state) for accurate field-level diff display. |
| **Calendar Conflict Resolution Web UI** | A dedicated resolution surface at `/settings/integrations/calendar/conflicts/{id}` renders the conflict as a side-by-side two-column diff (Pilot on the left, external calendar on the right) with field-level track-changes highlighting (amber=modify, green=add, red=remove). Two primary actions: "Use Pilot version" / "Use [Provider] version." Deletion-conflicts use a distinct verb-explicit treatment ("Restore", "Delete", "Recreate"). The conflict list sorts by soonest-impacting first (ascending by affected job's `scheduled_start_at`); past-dated and unscheduled conflicts drop to the bottom. |
| **Pre-Resolution Staleness Check (Calendar Conflicts)** | When the owner clicks resolve, the API re-evaluates the conflict before committing. If either side has been modified since detection, returns 409 with refreshed payload; UI re-renders with updated state and an alert banner. Same pattern as the dispatch board's optimistic locking. |
| **Calendar Conflict Auto-Expiry (System Default + Tenant Override)** | Conflicts unresolved past the auto-expire threshold auto-resolve to `accept_local` (Pilot as source of truth). System defaults: 30-day auto-expire, 7-day pre-warning notification. Each tenant can override either or disable entirely. |
| **Mobile Calendar Sync Status Row** | The mobile Owner tab carries a "Calendar sync" status row alongside the existing QuickBooks sync row. States: synced (green), pending conflicts (amber with count, "Resolve on web → or via voice →"), connection error (red). Tapping deep-links to web for touch resolution; voice resolution works from any surface. |
| **Voice-Active Calendar Conflict Resolution** | Voice supports active conflict resolution (not just status query) with confirm-as-turn for all resolution variants: `accept_local`, `accept_remote`, plus four explicit-verb variants for deletion-conflict resolution. Field-level edits remain web-only via refusal-with-redirect. |
| **Schedule Version History & Audit** | Every modification to `job.scheduled_start_at`, `job.scheduled_end_at`, or tech assignment writes an audit log entry. Dispatch board supports a "history" view per job. |
| **Map Provider Integration (Abstracted)** | Provider-abstract geocoding, distance-matrix, and reverse-geocoding interface. Google Maps Platform at beta; alternate providers swappable via configuration. |

---

### 3.15 Mobile Offline Operations

**Domain Purpose**: Ensure the mobile app works continuously when the tech is in a basement, attic, parking garage, or rural area without signal — and reconciles gracefully when the device returns to network. Make every offline-capable operation appear successful immediately on the device, surface sync state ambiently, classify and resolve conflicts at the right level (auto, tech, or owner), and treat data integrity as the non-negotiable contract.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **Explicit Offline-Capable Operation Set** | The platform commits to a specific list of operations that work fully offline: clock in/out, time entry creation (with ETC), expense capture (with attached photo), site/job photo capture, status changes on already-assigned jobs, LOTO check confirmation, voice audio capture (deferred processing), free-text notes on a job, NEC code calculations, change order creation against an already-assigned job. Customer/job/material lookups are partially offline (cached entities only). Customer creation, quote send, customer comms send, dispatch, and calendar/QB sync are explicitly online-only. |
| **Optimistic UI with Pending Badges** | Every offline-capable operation shows immediate success in the UI when triggered. A "pending sync" badge marks the affected entity until sync confirms (badge clears) or fails (badge becomes red with retry/resolve affordance). |
| **Global Connection State Indicator** | A persistent pill in the top status bar of every mobile screen displays combined connection + sync state. Hidden when synced and online; amber when syncing; red when offline (with queued count); red with action-needed prefix when conflict requires attention. Tapping opens the sync queue drawer. |
| **Sync Queue Bottom Sheet** | The sync queue is a bottom-sheet drawer accessible by tapping the connection state indicator. Contents grouped in attention-priority order: Action needed (red, top); Syncing (amber, with per-photo progress); Pending (neutral, queued); Recently synced (muted, last 10). Each item shows type, summary, capture timestamp, and status pill or action button. |
| **Four-Class Sync Conflict Severity** | When sync detects a conflict, the platform classifies it into one of four severity tiers: `auto_silent` (sync proceeds, no notification); `auto_notice` (sync proceeds with toast or queue note); `tech_resolvable` (sync paused; appears in Action needed; tech picks resolution on phone); `owner_escalation` (sync paused; flagged to owner; tech sees "sent to owner"). Per-operation classification matrix is data-driven and tunable without code deploys. |
| **Tech-Resolvable Conflict UI (Vertical Stacked)** | When a tech-resolvable conflict appears, the resolution screen renders a phone-adapted vertical-stacked layout: explainer at top, "Your version" and "Server version" cards stacked vertically with field-level track-changes highlighting (amber=modify, green=add, red=remove), bottom action bar with "Use my version" (primary), "Use server version" (secondary), and "Send to owner for review" (tertiary). Pre-resolution staleness check applies. |
| **Owner Escalation Path with Loop Closure** | Conflicts classified as `owner_escalation` route to the owner via push notification + `notification_outbox` entry plus an entry in the web `Dashboard > Approvals > Field issues` queue. Owner-side resolution UI on web shows full diff with track-changes vocabulary, two-button bottom action bar with deletion-conflict variants, pre-commit staleness check with three 409 payload types. Resolution loops back to the originating tech with status update, push notification, and persistent activity log entry on tech mobile. Voice resolution active for binary cases with confirm-as-turn safeguard. The mobile-to-web escalation pattern is now formalized as a platform pattern (§4.1) — generalizable to future tech-submitted activities (time-off requests, safety incidents, catalog requests, etc.). |
| **Photo Upload as Separate Queue with WiFi Preference** | Photo uploads run on a separate queue from data sync. Tenant setting `photo_upload_wifi_only` (default TRUE) restricts to WiFi by default; user override available for "upload on cellular when offline > 24 hours." Resumable chunked transfer via S3 multipart with signed URLs. Per-chunk completion tracked client-side; resume from last-completed chunk on retry. Local cleanup: synced photos auto-purge after `photo_local_retention_days` (default 7). |
| **Voice Capture Offline, Process Online** | Voice commands captured offline save audio locally and queue for transcription on reconnection. Tech sees "Voice captured — will process when online." Normal voice intent flow runs on reconnect; if disambiguation or destructive-action confirmation is needed, surfaces as a notification rather than blocking. Confirmation deferred timeout: 24 hours. |
| **Sync Triggers (Foreground + Background)** | Foreground sync runs on: app foreground transition; OS network state change to online; periodic check every 30 seconds while app active and online; manual trigger from the queue surface. Background sync (when app is closed) is now in MVP scope (pulled forward from Phase 2): server-initiated silent push as primary trigger (rate-limited per tenant-effective `background_sync_push_interval_minutes`, default 5); OS-scheduled opportunistic execution as fallback (BGAppRefreshTask on iOS, WorkManager periodic on Android). **MVP background sync scope is strictly limited to the data sync queue only.** The following are explicitly excluded from background sync in MVP and remain foreground-only: (1) **Photo uploads** — foreground-only due to battery and bandwidth concern; (2) **Voice audio uploads** — foreground-only (audio files are large; background upload risks OS termination mid-transfer); (3) **Tech-resolvable conflicts** — cannot auto-resolve in background because they require user input (the conflict resolution UI cannot be shown when the app is closed). Auto-resolves (`auto_silent`, `auto_notice`) proceed in background; `tech_resolvable` and `owner_escalation` conflicts are deferred to the next foreground session. Failure visibility on next app open. **Phase 1.5 expansion (P2)**: Tenant-configurable opt-in to background photo uploads and voice audio uploads, gated by a tenant-settable battery floor (e.g., `photo_background_upload_battery_floor_pct`). These expansion items are tracked in the launch plan P2 section. |
| **Force-Quit Recovery via Persistent Local Queue** | Sync queue persists in local device storage (Core Data on iOS, Room on Android, SQLite via Expo's persistence APIs cross-platform). Each item carries client-generated UUID, operation type, full payload, status, retry count, last error. On app launch, queue resumes from last known state; in-flight items revert to pending and retry with idempotency keys protecting against duplicates. |
| **Idempotency UUIDs for Offline Operations** | Every offline-capable operation generates a client-side UUID v4 at capture time and passes it as the `Idempotency-Key` header on sync. The platform's existing 24-hour idempotency window handles normal retries; for the 72-hour offline scenario, server-side natural-key dedup (e.g., `(user_id, job_id, clock_in_at)` for time entries) on a 7-day window prevents duplicates after the idempotency window has expired. |
| **Auth Expiry Offline Handling** | When the access token expires while offline, captured data persists locally (no data loss). On reconnection, sync attempts refresh token first; if refresh succeeds, sync resumes silently. If refresh fails, the app surfaces a re-auth prompt while preserving the local queue; after re-auth, sync resumes. Edge case: tenant disabled the user mid-offline → re-auth fails permanently; UI offers "Account disabled — contact your owner. Captured data is saved locally" with a JSON export-or-discard affordance. |
| **Time-Bounded Offline Operation (Soft 24h / Hard 72h)** | Soft limit at 24 hours: connection state indicator changes to "Long offline · N items," tech sees one-time toast on app open. Hard limit at 72 hours: app blocks new offline operations until a sync occurs; full-screen warning. Tenant setting `offline_hard_limit_hours` (default 72; nullable for unlimited) configurable; soft limit is fixed (UX threshold, not policy threshold). |
| **Customer Comms Stay Online-Only** | Customer-facing communications cannot be sent offline. Voice intent capture works offline (deferred processing); the actual SMS/email send is blocked until online. Touch attempts to send a template card while offline compose-and-queue with a "preview pending" flag; on reconnection, the always-preview rule (§3.7) renders the message with live ETA before send. This preserves the one-way-door safety property of customer comms. |
| **Server-Side Sync Visibility Log** | The `mobile_sync_event` append-only log captures every sync attempt per device per operation, enabling cross-device visibility for owners reviewing tech sync state and for support troubleshooting. 30-day hot retention. |
| **Field Issues Web Queue at `Dashboard > Approvals > Field issues`** | Owners review pending mobile-conflict escalations in a paginated table at `/dashboard/approvals/field-issues` with filtering by tech active status, operation type, and resolution status. Sort by escalation creation time descending by default. Empty state teaches normalcy ("No field issues to resolve. Your team's captures are all syncing cleanly."). Recent issue history available alongside pending queue. |
| **Background Sync Settings (Tenant + User Override)** | Four tenant settings control background sync behavior: `background_sync_enabled` (default TRUE; user override allowed), `background_sync_wifi_only` (default FALSE), `background_sync_battery_floor_pct` (default 20; range 5–50), `background_sync_push_interval_minutes` (default 5; range 1–60; system default + tenant override). Mobile users see read-only display of WiFi-only and battery floor settings; per-user override of master enabled toggle is editable on mobile per the three-question inclusion rule from Settings IA. |

### 3.16 Help & Support

**Domain Purpose**: Provide AI-mediated, context-aware help that scales with Pilot's growth and reduces solo-founder support burden. Pilot's voice-first AI-first identity extends into help: users open help and have a chat-style conversation with AI that knows the product, retrieves relevant articles for grounding, and walks them through what they need.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **AI-Mediated Help with RAG** | Users open help (from main nav, settings, or contextual "?" anchors throughout the app) and engage with AI in a chat-style interface. AI uses the same Llama 3.x infrastructure as voice intents (separate prompt + RAG context). RAG retrieval over markdown help corpus stored in S3, embedded into pgvector for semantic search. Top-K chunks retrieved at query time and injected into prompt as grounding context. |
| **Markdown Corpus in S3 with Frontmatter Metadata** | Help articles are markdown files in S3 with structured frontmatter (article_id, title, category, related_concepts, ui_surfaces, related_articles, last_updated, audience). Same files serve both AI retrieval and direct article reading. Audience filtering applied during retrieval (e.g., owner-only articles excluded for technician queries). MVP corpus targets ~60 articles across 12 categories. |
| **Three Help Entry Points** | Main navigation (persistent "?" icon in app shell — non-contextual), settings sub-page (`Settings > Help & About`), and selective contextual "?" icons next to specific labels and concepts on complex surfaces (sync conflicts, MFA enrollment, voice intents, etc.). Contextual entry passes minimal context payload (route, entity type if applicable, recent action types, role, tenant metadata) to AI for grounded responses. |
| **Web Side-Drawer Chat / Mobile Full-Screen Chat** | Help chat panel is a slide-out drawer from right edge of viewport on web (400px wide; doesn't block main app); full-screen view on mobile. Chat history scrolls; latest message at bottom. Composition zone at bottom with voice mic + text input + send. AI messages have AI avatar; user messages have user avatar. Suggested follow-up action buttons within AI messages (Read full article, Walk me through it, That answered it, Still confused). |
| **Voice Input + Voice-Only Mode** | Voice button in chat composition initiates Whisper capture; transcribed text appears in input field for editing before send. Voice readback of AI responses available via "🔊 Listen" icon (uses user's effective voice persona tone). Voice intent grammar extends with `open_help` and `ask_help_question` intents — user can interact with help entirely via voice. |
| **AI Knowledge Boundaries** | AI is scoped to "how to use Pilot" knowledge plus surface context. Explicitly does NOT take actions on user's behalf, does NOT access tenant-specific data, does NOT provide financial/legal/compliance advice, does NOT make product roadmap commitments, does NOT operate outside Pilot domain. Three escalation triggers route stuck users to feedback submission: explicit user request for human help, low AI confidence after 3 turns, question outside scope. |
| **Past Conversations Recall** | Users can review prior help sessions with AI-generated brief titles. Within-session continuity preserved across surface navigation. Cross-session reset on full close or sign-out. Per-device isolation (no cross-device sync in MVP). |
| **Chat Session Capture for Training Data** | Sessions captured by default with anonymization at training-pipeline stage. Three-tier retention: active session (until close), recent unscrubbed (90 days for debugging + history recall + training source), permanent training corpus (anonymized). Anonymization pipeline runs at 90-day boundary: PII detection (emails, phones, names, business names, addresses, IDs) + tenant-identifying data scrubbing. User-facing transparency: "Pilot uses help conversations to improve our help content. Personal information is removed before use." |
| **Selective Contextual Help Anchors** | "?" icons placed at specific complex surfaces: settings (sync auto-expiry, sync direction, notification preferences with forced-minimum, background sync, voice persona, SMS quota cap, margin buckets, tax configuration), feature surfaces (MFA methods, field issues queue severity, calendar/QuickBooks conflict resolution, quote approval, onboarding tax setup). Selective placement keeps content authoring scope manageable. |
| **About / Version / Legal Surface** | At `Settings > Help & About > About`: Pilot logo, web version, mobile version (build), API version, support contact info, three quick paths to help (chat, feedback, support email), legal links (ToS, Privacy, EULA, OSS licenses), copyright notice. Mobile renders same content in vertical stack. |
| **Structured Feedback Submission** | At `Settings > Help & About > Send feedback`. Required category (Bug report / Feature request / Question / General feedback) + required text (5000 char max) + auto-filled reply-to email. Submission creates email to support inbox with subject prefix `[Pilot Feedback - {Category}]`, full feedback body + tenant info + user role + timestamp, reply-to user's email. Confirmation page after submit. From-help-chat escalation pre-fills category as "Question" and conversation context. |
| **Email Intake for Feedback (MVP); Ticket System Phase 2** | Feedback submissions go via email to `support@pilotfortrades.com` (configurable). Solo founder operational reality — the inbox is the support channel for the foreseeable future. Phase 2 introduces a ticket system when volume justifies the infrastructure overhead. |
| **Diagnostic Data Attachment for Bug Reports (Phase 2)** | Currently feedback is text-only. Phase 2 will add opt-in diagnostic data attachment for bug reports: recent actions, browser info, error logs, screenshots. MVP relies on user's free-text description; Tom replies via email asking for more info if unclear. |

---

---

## Section 3.17 — Multi-Vertical Deployment Model

**Purpose**: Pilot for Trades is designed from the ground up to serve multiple field service verticals from a single codebase. This section documents the customer deployment plan across verticals and the architectural decisions made to support multi-vertical expansion without requiring product forks or major refactoring.

### Industry Segmentation

Pilot recognizes two distinct segments within the field service market:

**Trades Vertical** — Licensed, skilled work requiring material procurement, code compliance, complex quoting, and permit management. Core examples: electrical, plumbing, HVAC, gas fitting, fire suppression.

**Services Vertical** — Recurring, route-based work that is primarily labor with simple consumables. Core examples: cleaning, lawn care/landscaping, pest control, handyman, pool maintenance.

These two segments have fundamentally different workflows:

| Dimension | Trades | Services |
|---|---|---|
| Job type | Project-based, one-time | Recurring, route-based |
| Quoting | Complex — material pricing, markup, approval workflow | Simple — flat rate or package pricing |
| Materials | Significant bill of materials | Minimal or consumables only |
| Regulatory | Licensed work, permits, code compliance | Minimal licensing; no permits |
| Average job value | $500–$10,000+ | $100–$500 |
| Duration | Hours to weeks | Hours, same-day |
| Sales cycle | Quote approval required | Often instant booking |

Pilot's core infrastructure — customer CRM, dispatch board, voice AI, QuickBooks sync, calendar sync, offline mobile, invoicing, payment processing, SMS communications — is identical across both segments. What varies is the **catalog content**, **calculation tools available**, **scheduling model** (project vs. recurring route), and **regulatory context**.

### Vertical Deployment Timeline

| Phase | Vertical | Brand | Domain |
|---|---|---|---|
| **MVP (Phase 1.0)** | Electrical | Pilot for Trades | pilotfortrades.com |
| **MVP (Phase 1.0)** | Plumbing | Pilot for Trades | pilotfortrades.com |
| **Phase 1.5** | HVAC | Pilot for Trades | pilotfortrades.com |
| **Phase 2.0** | Cleaning, Landscaping, Handyman, Other Services | Pilot for Services | pilotforservices.com |

The `pilotforservices.com` domain will serve as a dedicated marketing entry point for the services segment, resolving to the same application with services-tuned onboarding, terminology, and feature emphasis. No separate infrastructure is required.

### Multi-Vertical Architecture Pattern

Five architectural components make vertical expansion a configuration exercise rather than a development exercise:

**1. `tenant.vertical_code`**
Every tenant record carries a `vertical_code` enum (`electrical | plumbing | hvac | cleaning | landscaping | handyman | other`). This is captured during signup (onboarding wizard step 1) and exposed through `AuthContext` to all frontend components. Every conditional vertical decision keys off this single field.

**2. Vertical Feature Flag System (`vertical_feature_config`)**
A data-driven table controls which platform features are enabled for each vertical without code changes. Example: `nec_calculations` is enabled for `electrical`, disabled for `plumbing` and `cleaning`. Adding a new vertical is adding rows to this table. The frontend consults `features.isEnabled(feature_key)` rather than hard-coding `if vertical === 'electrical'` checks.

| Feature Key | Electrical | Plumbing | HVAC | Cleaning |
|---|---|---|---|---|
| `nec_calculations` | ✅ | ❌ | ❌ | ❌ |
| `loto_workflow` | ✅ | ❌ | ❌ | ❌ |
| `permit_tracking` | ✅ | ✅ | ✅ | ❌ |
| `pipe_sizing_calc` | ❌ | ✅ | ❌ | ❌ |
| `refrigerant_tracking` | ❌ | ❌ | ✅ | ❌ |
| `equipment_cards` | ✅ | ✅ | ✅ | ❌ |
| `route_scheduling` | ❌ | ❌ | ❌ | ✅ |
| `recurring_billing` | ❌ | ❌ | 🟡 (maintenance plans) | ✅ |

**3. Vertical Seed Catalog**
Pricebook seed data is stored in per-vertical JSON files (`catalog_electrical.json`, `catalog_plumbing.json`, etc.) rather than embedded in Python scripts. When a new tenant completes signup, the onboarding system seeds their catalog from the file matching their `vertical_code`. Adding plumbing catalog data requires only creating `catalog_plumbing.json` — zero code changes.

**4. Voice AI System Prompt per Vertical**
The Llama system prompt is keyed by `vertical_code`. The electrical prompt includes NEC context and electrical trade terminology. The plumbing prompt references IAPMO/UPC codes. The HVAC prompt references ASHRAE. The cleaning prompt focuses on scheduling, client relationships, and supplies. Each vertical's voice AI feels native to that trade.

**5. Onboarding Wizard Vertical Selection**
Signup step 1 asks "What type of business do you run?" The selection drives: catalog seeding, feature flag loading, setup checklist content (plumbing tenants don't see "Set up NEC reference"), and initial voice AI context. MVP offers: Electrical | Plumbing | Other. Phase 1.5 adds HVAC. Phase 2 adds the full services vertical list.

### What Is NOT Abstracted

The following remain trades-specific in Phase 1.0 and are not generalized until the services vertical requires them:
- Route-based recurring scheduling (needed for cleaning; builds on GAP-M1 recurring jobs)
- Automated recurring billing for maintenance plans (HVAC and cleaning Phase 2)
- Trade code calculation engine (NEC, pipe sizing, BTU — vertical-specific; not generalized)

---

## Section 4: Cross-Cutting Design Patterns & Technical Implementation Approach

Pass 3 and Pass 4 design surfaced and formalized a set of cross-cutting patterns that now constitute Pilot's UX vocabulary at the platform level. These are not implementation details — they are product requirements, because they define how the platform behaves consistently across surfaces. New domains added in Phase 2 inherit these patterns by default; deviations require explicit justification. Sixteen patterns total: eight from Pass 3, six new in Pass 4 (Tier 1 + Tier 1.5 + Tier 4 #12), plus two visual-treatment extensions of existing patterns (system-default-with-tenant-override visual, three-tier resolution chain).

### 4.1 Platform UX Vocabulary

**Track-Changes Diff Vocabulary**

A consistent visual language for diffs across the platform: **amber** for modified fields (with prior value as struck-through helper text), **green** for added fields ("(added)" annotation), **red** for removed fields (strikethrough + "(removed)" annotation). Used in:

- Quote approval review (§3.10): owner-pending edits during review
- Calendar conflict resolution (§3.14): field-level diff between Pilot and external calendar versions
- Mobile sync conflict resolution (§3.15): field-level diff between tech's captured version and server version
- QuickBooks conflict resolution (§3.9, UI deferred): future Pass 4

This is now a platform requirement: any compare-and-pick surface inherits this vocabulary. New diff surfaces designed in Phase 2 must use the same palette.

**Four-Class Severity Pattern**

Conflicts and warnings classify into four severity tiers with proportional UI treatment. Used in:

- Dispatch board conflicts (§3.14): `overlap`, `availability`, `travel`, `info`
- Calendar sync conflicts (§3.14): three lifecycle conflict types plus the resolution-pending state
- Mobile sync conflicts (§3.15): `auto_silent`, `auto_notice`, `tech_resolvable`, `owner_escalation`

The pattern recognizes that not every conflict needs the same level of attention. Routing classifications correctly is the difference between an attentive user and an alert-fatigued user.

**Confirm-as-Turn for Destructive Voice Actions**

Every voice intent that creates, modifies, or deletes durable data routes through an explicit confirmation turn before commit. The AI states the specific action and waits for affirmative response. Non-affirmative responses cancel and return to passive listening. Universal across the platform: quote send, calendar conflict resolution, schedule changes, quote approval, sync conflict resolution, customer comms send.

**Pre-Commit Staleness Check (409-and-Refresh)**

Write endpoints accept expected-version timestamps and return `409 Conflict` with refreshed state when the underlying record has changed since the client last viewed it. UI handles 409 by refreshing the view and surfacing a "this has been updated" banner; user re-decides. Used by dispatch board edits, calendar conflict resolution, mobile sync conflict resolution, and quote approval.

**System Default + Tenant Override Two-Tier Configuration**

Settings that need both platform-wide control and per-tenant flexibility use a system default at the platform admin level plus a nullable per-tenant override. Effective value resolution: tenant override → system default → fallback constant. Used for calendar conflict auto-expiry windows; the pattern is available for any future setting.

**Mobile Owner Status Row + Deep-Link**

Cross-surface integration health surfaces as a status row on the mobile Owner tab: green/amber/red dot, integration name, last sync time, count of pending items, and a deep-link to the appropriate web surface for resolution (touch) or a hint at voice resolution (mobile). Used for QuickBooks sync, calendar sync, and (extensible) any future bi-directional integration.

**Optimistic UI with Pending Badges**

Operations that may take time to complete render as immediately successful in the UI, with a "pending sync" or "in progress" badge until confirmation. Failed operations transition to red with a retry/resolve affordance. Universal for offline-capable operations on mobile (§3.15) and applicable to any future async-write surface.

**Always-Preview-Before-Send for One-Way-Door Actions**

Customer-facing communications (§3.7) and any other one-way-door action render a final preview to the originating user before commit. The preview shows the rendered content, recipient, and channel. The user must explicitly confirm send. Voice-initiated, touch-initiated, and template-driven flows all converge on this preview before send.

**Carrier-Agnostic Adapter Layer Pattern**
External service integrations (SMS carriers, payment processors, mapping providers, email services) live behind a thin adapter interface that abstracts the provider-specific API. Configured per-deployment via environment variable; future provider swaps are a one-class change. First instance: SMS via Telnyx (Pass 4 Tier 1.5).

**Subscription Quota with Soft/Hard Cap Pattern**
Subscription tiers include a metered allowance with tenant-controlled cap behavior: soft cap continues operating with overage billing; hard cap blocks at limit. Used for SMS quota (100 segments/month included; Pass 4 Tier 1.5). Available for any future per-event metered feature.

**Lazy Provisioning of External Resource at First Use Pattern**
External resources with per-instance cost (Telnyx phone numbers in MVP; Phase 2 candidates: dedicated voice processing slots, customer-facing portal subdomains) are provisioned at first use rather than at tenant signup, avoiding cost waste for tenants who never use the feature. Pre-provisioning UI affordance available for tenants who want explicit setup.

**Bilateral Integration Conflict Resolution Pattern (Formalized)**

The pattern that emerged from calendar sync conflict resolution (Pass 3 Flow 6) generalized through QuickBooks conflict resolution (Pass 4 Tier 1 #2). Common structure: paginated queue list sorted by urgency, side-by-side two-column diff with track-changes vocabulary, two-button bottom action bar with master-aware primary treatment, deletion-conflict variants with distinct verb-based treatment, pre-commit staleness check, modal-feeling but URL-routed, audit-but-no-undo, empty state teaches normalcy, mobile owner status row + deep-link, and system-default + tenant-override auto-expiry where applicable.

Pattern attributes that are domain-determined rather than fixed: auto-expiry default (ON when master is unambiguous like calendar; OFF when masters are heterogeneous like QuickBooks); voice resolution scope (full active resolution when stakes permit; status-query-only for accounting-data domain); column ordering and primary-button treatment (master-aware when masters are heterogeneous; uniform when single master).

Reference instances: calendar sync (§3.14), QuickBooks sync (§3.9). Future bilateral integrations (Salesforce, HubSpot, generic webhooks) inherit by default.

**Mobile-to-Web Escalation Pattern**

When mobile-originated activity requires owner judgment that the tech cannot or should not make autonomously, the activity is paused at the mobile origin, escalated to a web-side queue with push notification to the owner, resolved by the owner on web (or via voice for binary cases), and looped back to the originating tech with the resolution outcome reflected in their mobile experience. Resolution honors the pre-commit staleness check pattern. Audit trail records both originator and resolver.

Pattern characteristics: origin in a mobile-side action that classifies into the four-class severity model's `owner_escalation` class; routing via persistent server-side queue + push notification + entry in web `Approvals` sub-surface; resolution via web-only diff view inheriting the bilateral integration conflict resolution pattern's two-column treatment, with voice resolution for binary cases; loop closure with status update + push notification + persistent activity log entry to the originating tech; auditability of both originator and resolver.

Reference instance: Pass 4 Tier 1 #1 (owner-side mobile-conflict resolution). Future Phase 2 surfaces inheriting: tech-submitted time-off requests, tech-flagged safety incidents, tech-requested catalog item additions, tech-flagged customer issues, tech-requested expense limit overrides.

Distinct from the read-only "mobile owner status row + deep-link" pattern — this is full round-trip (mobile creates, web resolves, mobile reflects).

**Background Sync Execution Pattern**

When a mobile queue requires execution outside of foreground app sessions, the platform uses an asymmetric implementation strategy with a uniform user experience. Primary trigger is server-initiated push (silent push on iOS, high-priority FCM on Android), rate-limited per device with a tenant-configurable interval. Fallback trigger is OS-scheduled opportunistic execution (BGAppRefreshTask on iOS, WorkManager periodic on Android) when push delivery is delayed or throttled. Execution scope is lightweight operations only — heavy operations (photos, voice audio, periodic data refresh) remain foreground-only unless explicitly upgraded. Conflict handling: auto-resolves only in background; anything requiring user judgment defers to foreground. Failure visibility: every background run reports outcome to a tech-visible "last attempt" indicator on next app open; persistent failures (>3 consecutive) trigger a foreground notification.

Reference instance: Pass 4 Tier 1 #3 (background sync for mobile data queue). Future Phase 2 surfaces inheriting: periodic data refresh, background photo upload (if upgraded from foreground), tech-to-tech messaging delivery.

**In-Flight Sync Indicator with Pending Count**

A sync surface (calendar, QuickBooks, mobile, background) renders its current state plus a count of pending operations. Five compositional states cover synced-idle, synced-with-pending, syncing-active, sync-error, sync-paused. Hover/tap surfaces individual pending items as ambient awareness (capped at 5 with "+N more"). Manual sync trigger inline for owner-initiated immediate sync where applicable. Tunable threshold (`tenant_sync_indicator_pending_amber_threshold`, default 5) shifts visual emphasis to amber when pending count is operationally meaningful. Real-time updates via SSE.

Reference instances: calendar sync, QuickBooks sync, mobile data sync, background sync. Future Phase 2 surfaces: any future bilateral-sync integration.

### 4.2 Technical Stack

**Backend**: Python 3.12+ / FastAPI; PostgreSQL with pgvector extension; Celery + Redis for background processing (with hybrid EventBridge/Lambda for scheduled compute); SlowAPI for rate limiting; Alembic for migrations; SQLAlchemy ORM. AWS deployment.

**Frontend (Web)**: Next.js 16 / React 19; TypeScript; Tailwind CSS with custom design tokens (per Pass 1 spec); Server-Sent Events client for live dispatch board.

**Frontend (Mobile)**: Expo SDK 54 / React Native; cross-platform persistence layer for offline queue; native push notification integration; Whisper streaming voice capture client.

**AI/Voice**: Whisper Large-v3 for speech-to-text (locally hosted); Llama 3.x Instruct for intent parsing and conversational continuity (electrical-vocabulary fine-tune planned; currently stock + prompt engineering); AWS GPU instance (g4dn.xlarge tier) targeting sub-2-second response time.

**Auth**: AWS Cognito with custom MFA; refresh token TTL 30 days (adequate for the 72-hour offline scenario per §3.15).

**Storage**: S3 for photos and voice audio; S3 multipart upload with signed URLs for resumable photo transfers; standard S3 for voice audio (single-shot uploads acceptable given file size).

**Integrations**: QuickBooks Online (bi-directional); Google Calendar (bi-directional, provider-abstract for Phase 2 Outlook/iCal); Telnyx for SMS; SendGrid for email; Stripe for payments; Google Maps Platform for geocoding/distance-matrix (provider-abstract).

### 4.3 Configuration Conventions

**Tenant Settings**: Tenant-scoped configuration values live in a shared `tenant_setting` table keyed by string identifier. New settings introduced through Pass 3:

| Setting | Default | Source |
| :--- | :--- | :--- |
| `require_approval_for_tech_quotes` | ON (multi-user), OFF (solo) | §3.10 |
| `max_discount_pct_owner` | 15% | §3.10 |
| `voice_persona_tone` | `balanced` (Post-MVP) | §3.13 |
| `report_chart_threshold` | 8 | §3.4 |
| `etc_variance_note_required_pct` | 10% | §3.4 |
| `etc_variance_owner_notify_pct` | 50% | §3.4 |
| `margin_bucket_boundaries` | `[10, 20, 30]` | §3.4 |
| `margin_target_pct` | 20% | §3.4 |
| `tech_color_palette` | 12-hue system default | §3.14 |
| `calendar_conflict_auto_expire_days` | system default (30); nullable | §3.14 |
| `calendar_conflict_pre_warning_days` | system default (7); nullable | §3.14 |
| `calendar_conflict_auto_expire_enabled` | TRUE; FALSE disables | §3.14 |
| `photo_upload_wifi_only` | TRUE | §3.15 |
| `photo_local_retention_days` | 7 | §3.15 |
| `offline_hard_limit_hours` | 72 (nullable for unlimited) | §3.15 |

**System-Wide Defaults**: Platform-admin-configurable values that act as the fallback when a tenant override is null. Pass 3 introduced two:

| Setting | Default |
| :--- | :--- |
| `system_calendar_conflict_auto_expire_days` | 30 |
| `system_calendar_conflict_warn_days_before` | 7 |

---

## Section 5: Risk Management & Mitigation

### 5.1 Technical Risks

**AI Model Dependencies**:

- Risk: Local AI model performance degradation
- Mitigation: Public AI API fallback; model monitoring; regular updates; voice feedback loop (§3.13) feeds correction corpus
- Concern: Using public AI APIs will increase costs and will need to be strictly managed and controlled by tenant.

**Voice Recognition Accuracy**:

- Risk: Poor accuracy in noisy construction environments
- Mitigation: Whisper Large-v3 noise tolerance; multiple microphone support; visual fallbacks for all voice intents; confirm-as-turn for destructive actions catches misrecognitions before commit

**Integration Failures**:

- Risk: QuickBooks API or Google Calendar API changes/outages
- Mitigation: API versioning; webhook backups; manual sync options; provider-abstract architecture allows alternate providers (Outlook/iCal for calendar); two-tier auto-expiry on conflicts ensures backlogs don't accumulate indefinitely during outages
- Concern: Using an alternate calendar provider introduces a concern if a tenant wants to switch after using one provider for awhile that will need to be addressed.

**Offline Data Integrity** *(new, surfaced by Pass 3 Flow 7)*:

- Risk: Sync conflict edge cases lose tech-captured data; force-quit drops queue items; auth expiry mid-offline strands data
- Mitigation: Idempotency UUIDs with natural-key fallback dedup on a 7-day window; persistent local queue across force-quit; refresh token TTL adequate for 72-hour hard limit; hard limit prevents indefinite offline accumulation; JSON export affordance for the disabled-account edge case

**Voice Processing Latency for Deferred Offline-Captured Commands** *(new, surfaced by Pass 3 Flow 7)*:

- Risk: Voice commands captured offline produce stale results when processed hours later; tech expects a current-moment response
- Mitigation: Deferred-confirmation flow surfaces the result as a notification; destructive intents still go through confirm-as-turn at commit time; client-capture-at vs. server-received-at gap visible in audit log

**Sync Conflict Resolution Burden on Owners** *(new, surfaced by Pass 3 Flow 6)*:

- Risk: Owner accumulates a backlog of conflicts they never resolve; conflicts go stale; metric signal value degrades
- Mitigation: Two-tier auto-expiry with pre-warning notification; voice-active resolution lets owner triage from the road; mobile status row surfaces backlogs
- Concern: Need to make sure owner knows about the auto-expiry process and how it will trigger and impact conflicts that reach the limit.

### 5.2 Business Risks

**Founder Dependency**:

- Risk: Solo founder becomes bottleneck
- Mitigation: AI agent automation; comprehensive documentation; backup plans
- Concern: Solo founder maintaining all features within their full understanding will need to be supported with thorough documentation

**Cash Flow Management**:

- Risk: High customer acquisition costs
- Mitigation: Monthly revenue tracking; cost controls; investor relationships
- Concern: To reduce high acquisition costs will need assistance from AI agent with a low-to-no cost marketing approach to implement

**Scope Creep from Pass 3 Surface** *(new)*:

- Risk: Pass 3 surfaced substantial new product surface (~117–161 days of backend additions); team builds against design specs without consolidated PRD source-of-truth
- Mitigation: This v3 PRD update consolidates Pass 3 surface into the authoritative product reference; backend additions tracked in a separate ledger that cross-references this PRD
- Observed: AI-generated effort estimates ran high (e.g., dispatch backend work A1 was estimated at 5 days and delivered in under 1)

---

## Section 6: Success Criteria & Next Steps

### 6.1 MVP Success Criteria

**Technical Milestones**:

- Voice recognition >95% accuracy for electrical terms
- Quote generation <30 seconds end-to-end (voice-initiated to draft)
- 99.9% uptime for core services
- Mobile app functionality across iOS and Android
- Offline data integrity: 100% of offline-captured operations sync successfully on reconnection within the 72-hour hard limit
- Sub-2-second voice response time end-to-end (capture → transcribe → parse → respond)

**Business Milestones**:

- 50 paying customers within 6 months of launch
- $7,500 MRR by month 6 (50 customers × $149/month)
- <5% monthly churn rate
- >4.5/5 customer satisfaction score
- ≥ 80% tenant signup wizard completion rate of started signups
- ≥ 60% MFA enrollment rate among multi-user tenants within 30 days of signup
- ≥ 70% help chat session resolution rate of user queries answered without escalation to feedback

**Product Milestones** (new):

- ≤1 sync conflict per tenant per month requiring owner escalation (above this, classification matrix needs tuning)
- ≥80% of customer comms sent via templated workflow (vs. free-form composition)
- ≥60% of quote approvals completed within 24 hours of submission (multi-user shops)
- Voice-initiated workflow share: ≥30% of quote creations, ≥50% of clock-in/out events

### 6.2 Roadmap

> **Canonical Roadmap Reference**: The product roadmap is now maintained in a dedicated document that supersedes the phase lists below. See `dev-docs/product-requirements/pilot-product-roadmap.md` for the complete, living phase breakdown with milestone triggers, all GAP-M feature assignments, and non-engineering action items.

**MVP Launch (Phase 1.0)**:

- Beta with 5–10 hand-selected electrical contractors (electrical-first focus)
- All P0 launch blockers resolved: recurring jobs, GPU deployment, background sync, A2P 10DLC, QuickBooks production review
- All P1 MVP items shipped: Wisetack financing, signature capture, quote follow-up reminder, review request automation, WIP dashboard
- Iterate on voice intent grammar, dispatch board patterns, and offline sync reliability based on real field usage
- ✅ Naming track resolved: **Pilot for Trades** (customer-facing brand) / **Pilot** (casual short form) / `pilot` (internal codename) / `pilotfortrades.com` (primary domain)
- ✅ Pricing confirmed: **Founders $0→$49/mo · Starter $49/mo · Teams $149/mo** — unlimited users, unlimited jobs/quotes/invoices, schedule lane licensing (5 lanes Starter / 20 lanes Teams), + usage overages (Voice AI $0.05/min, SMS $0.05/segment). See §3.11 for full pricing table.

**Phase 1.5 — Post-Launch Enhancements** *(trigger: 10+ active customers, 5+ real jobs each)*:

- Good/Better/Best tiered quote presentation
- Online booking request form + Reserve with Google partnership application
- Persistent customer portal
- Mobile job forms and checklists
- Live dispatcher GPS map + route optimization
- Expanded reporting suite (revenue/tech/customer reports)
- Public REST API design and documentation

**Phase 2.0 — Expansion** *(trigger: 50–100 paying customers, product-market fit confirmed)*:

- Trade expansion: Plumbing and HVAC catalogs, code references, trade-specific calculation modules
- Public REST API launch + Zapier integration
- VOIP integration (evaluate beta demand before committing)
- Maintenance agreements and recurring billing
- HVAC flat-rate book (licensed from a flat-rate publisher; partner not chosen — revisit at 50 customers)
- Advanced AI features: photo-to-quote, local market pricing, conversation analysis
- Platform depth: multi-tech crews, bulk conflict resolution, multi-calendar, Outlook/iCal
- Cleaning vertical: route-based scheduling, recurring cleans

Full feature-phase mapping, milestone definitions, and non-engineering action items: `pilot-product-roadmap.md`.

---

## Conclusion

Pilot for Trades represents a compelling opportunity to transform the electrical contracting industry — and ultimately the broader trades — through AI-first, voice-controlled software. The MVP build completion (batches B17 through MOB-B7, June 2026) delivers the core business loop: customer management, AI-assisted quoting, dispatch, invoicing, customer communications, and offline-first mobile operations.

The platform's UX vocabulary — track-changes diff colors, four-class severity, confirm-as-turn for destructive voice actions, system-default-with-tenant-override two-tier config, optimistic UI with pending badges, always-preview for one-way-door actions — is formalized at the platform level. Phase 1.5 and Phase 2 features inherit this vocabulary by default.

The combination of proven market demand, competitive $49/month pricing (unlimited users — below typical per-seat FSM pricing in the author's 2026 research, plus voice AI), completed core product design, and a clear phased roadmap positions Pilot for Trades for rapid growth and market leadership in the evolving field service software landscape.
