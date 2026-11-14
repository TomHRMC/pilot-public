# Pilot for Trades — Beta Test Plan

> **Snapshot note:** historical working document, published as last edited during the build and not maintained. Statuses and figures below reflect that date; for current, checked figures see [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../diligence/README.md). The product was never released and never carried customer traffic.

**Version**: 1.0
**Date**: 2026-06-02
**Author**: Tom (Founder) + Pilot Architect
**Status**: 🟡 READY FOR REVIEW — All test cases written; review before first execution
**Updated**: 2026-08-20 — duplicate stub tail removed (stray "pending" copies of P2-SC04–SC10 + a second Phase 3 stub block; the full content lives above); Appendix B + pre-launch hygiene statuses synced to as-built state; env-aware seed note added (DB-MGMT-1); exit-checklist launch-plan link corrected

---

## Table of Contents

- [Document Purpose & How to Use](#document-purpose--how-to-use)
- [Pre-Test Environment Setup](#pre-test-environment-setup)
  - [S1 — Docker Stack Verification](#s1--docker-stack-verification)
  - [S2 — Voice AI Stack Verification](#s2--voice-ai-stack-verification)
  - [S3 — Seed Data Population](#s3--seed-data-population)
  - [S4 — Test Accounts & Credentials Reference](#s4--test-accounts--credentials-reference)
    - [Tier 1: Seeded Users (non-auth surface testing)](#tier-1-seeded-users-non-auth-surface-testing)
    - [Tier 2: Real Test Users (auth + MFA surface testing — create during P1-S01)](#tier-2-real-test-users-auth--mfa-surface-testing--create-during-p1-s01)
  - [S5 — Known Limitations for Local Testing](#s5--known-limitations-for-local-testing)
- [Test Result Legend](#test-result-legend)
- [Phase 1 — Surface Verification (Feature-by-Feature)](#phase-1--surface-verification-feature-by-feature)
  - [P1-S01 — Identity, Access & Tenant Management](#p1-s01--identity-access--tenant-management)
    - [P1-S01-A: Signup Wizard (5-Step)](#p1-s01-a-signup-wizard-5-step)
    - [P1-S01-B: Login, JWT & Session Management](#p1-s01-b-login-jwt--session-management)
    - [P1-S01-C: Multi-Factor Authentication (TOTP / SMS / Email)](#p1-s01-c-multi-factor-authentication-totp--sms--email)
    - [P1-S01-D: RBAC — Role-Based Access Control](#p1-s01-d-rbac--role-based-access-control)
    - [P1-S01-I: Settings Sidebar Navigation Readability (BETA-B7)](#p1-s01-i-settings-sidebar-navigation-readability-beta-b7)
    - [P1-S01-E: Tenant-Required MFA Policy + Grace Period](#p1-s01-e-tenant-required-mfa-policy--grace-period)
    - [P1-S01-F: Post-Wizard Setup Checklist](#p1-s01-f-post-wizard-setup-checklist)
    - [P1-S01-G: Profile, Password & Active Sessions](#p1-s01-g-profile-password--active-sessions)
    - [P1-S01-H: Personal Data Export](#p1-s01-h-personal-data-export)
  - [P1-S02 — Catalog & Pricing](#p1-s02--catalog--pricing)
    - [P1-S02-A: Pricebook Item Management](#p1-s02-a-pricebook-item-management)
    - [P1-S02-B: Supplier Catalog Sync (Manual / CSV Import)](#p1-s02-b-supplier-catalog-sync-manual--csv-import)
    - [P1-S02-C: Labor Rate Versions](#p1-s02-c-labor-rate-versions)
    - [P1-S02-D: Category Markups](#p1-s02-d-category-markups)
    - [P1-S02-E: Historical Price Immutability on Quotes](#p1-s02-e-historical-price-immutability-on-quotes)
  - [P1-S03 — CRM (Customer Relationship Management)](#p1-s03--crm-customer-relationship-management)
    - [P1-S03-A: Customer Create / Edit / Soft-Delete](#p1-s03-a-customer-create--edit--soft-delete)
    - [P1-S03-B: Multi-Site Management](#p1-s03-b-multi-site-management)
    - [P1-S03-C: Site Access Details](#p1-s03-c-site-access-details)
    - [P1-S03-D: Tenant vs. Property Manager Billing](#p1-s03-d-tenant-vs-property-manager-billing)
  - [P1-S04 — Sales & Quoting](#p1-s04--sales--quoting)
    - [P1-S04-A: Quote Creation (Touch)](#p1-s04-a-quote-creation-touch)
    - [P1-S04-B: Line Item Management (3 Presentation Styles)](#p1-s04-b-line-item-management-3-presentation-styles)
    - [P1-S04-C: Real-Time Material Pricing & Snapshots](#p1-s04-c-real-time-material-pricing--snapshots)
    - [P1-S04-D: Quote Templates](#p1-s04-d-quote-templates)
    - [P1-S04-E: Quote Approval Workflow](#p1-s04-e-quote-approval-workflow)
    - [P1-S04-F: Time-Limited Discounts with Margin Cap](#p1-s04-f-time-limited-discounts-with-margin-cap)
    - [P1-S04-G: Public Quote Link & Customer Acceptance](#p1-s04-g-public-quote-link--customer-acceptance)
    - [P1-S04-H: Quote → Job Auto-Conversion](#p1-s04-h-quote--job-auto-conversion)
    - [P1-S04-I: Quote Expiration](#p1-s04-i-quote-expiration)
  - [P1-S05 — Field Operations & Jobs](#p1-s05--field-operations--jobs)
    - [P1-S05-A: Job Assignment & Tech Assignment](#p1-s05-a-job-assignment--tech-assignment)
    - [P1-S05-B: Clock In / Clock Out](#p1-s05-b-clock-in--clock-out)
    - [P1-S05-C: ETC Variance Notifications](#p1-s05-c-etc-variance-notifications)
    - [P1-S05-D: Expense Logging](#p1-s05-d-expense-logging)
    - [P1-S05-E: Photo Documentation](#p1-s05-e-photo-documentation)
    - [P1-S05-F: Change Orders](#p1-s05-f-change-orders)
    - [P1-S05-G: LOTO Safety Confirmation](#p1-s05-g-loto-safety-confirmation)
    - [P1-S05-H: Live Job Profitability View](#p1-s05-h-live-job-profitability-view)
    - [P1-S05-I: GPS-Verified Check-In](#p1-s05-i-gps-verified-check-in)
  - [P1-S06 — Scheduling & Dispatch](#p1-s06--scheduling--dispatch)
    - [P1-S06-A: Dispatch Board](#p1-s06-a-dispatch-board)
    - [P1-S06-B: Live Dispatch Board Updates (SSE)](#p1-s06-b-live-dispatch-board-updates-sse)
    - [P1-S06-C: Four-Class Conflict Detection](#p1-s06-c-four-class-conflict-detection)
    - [P1-S06-D: Tech Availability Windows & PTO](#p1-s06-d-tech-availability-windows--pto)
    - [P1-S06-E: Route Sequencing + Drive-Time](#p1-s06-e-route-sequencing--drive-time)
    - [P1-S06-F: Today's Schedule (Mobile Tech View)](#p1-s06-f-todays-schedule-mobile-tech-view)
    - [P1-S06-G: Calendar Sync (Google OAuth)](#p1-s06-g-calendar-sync-google-oauth)
    - [P1-S06-H: Calendar Conflict Detection & Resolution](#p1-s06-h-calendar-conflict-detection--resolution)
    - [P1-S06-I: Pre-Commit Staleness Check (409-and-Refresh)](#p1-s06-i-pre-commit-staleness-check-409-and-refresh)
  - [P1-S07 — Invoicing & Billing](#p1-s07--invoicing--billing)
    - [P1-S07-A: Quote/Job → Invoice Conversion](#p1-s07-a-quotejob--invoice-conversion)
    - [P1-S07-B: Tax Setup JIT Sub-Flow (412 Gate)](#p1-s07-b-tax-setup-jit-sub-flow-412-gate)
    - [P1-S07-C: Public Invoice Link & Stripe Payment](#p1-s07-c-public-invoice-link--stripe-payment)
    - [P1-S07-D: AR Aging Dashboard](#p1-s07-d-ar-aging-dashboard)
    - [P1-S07-E: Automated Dunning](#p1-s07-e-automated-dunning)
    - [P1-S07-F: Customer-Facing Invoice Page Branding](#p1-s07-f-customer-facing-invoice-page-branding)
  - [P1-S08 — Tax Calculation](#p1-s08--tax-calculation)
    - [P1-S08-A: Multi-Jurisdiction Tax Components](#p1-s08-a-multi-jurisdiction-tax-components)
    - [P1-S08-B: Material vs. Labor Taxability](#p1-s08-b-material-vs-labor-taxability)
    - [P1-S08-C: Tax-Exempt Customer](#p1-s08-c-tax-exempt-customer)
    - [P1-S08-D: Historical Tax Snapshot Immutability](#p1-s08-d-historical-tax-snapshot-immutability)
  - [P1-S09 — Notifications & Communications](#p1-s09--notifications--communications)
    - [P1-S09-A: Notification Outbox & At-Least-Once Delivery](#p1-s09-a-notification-outbox--at-least-once-delivery)
    - [P1-S09-B: 13 Customer Communication Templates](#p1-s09-b-13-customer-communication-templates)
    - [P1-S09-C: SMS Inbound Reply Threading](#p1-s09-c-sms-inbound-reply-threading)
    - [P1-S09-D: SMS STOP / Opt-Out Handling](#p1-s09-d-sms-stop--opt-out-handling)
    - [P1-S09-E: Notification Preference Matrix](#p1-s09-e-notification-preference-matrix)
    - [P1-S09-F: In-App Banner Notification (SSE)](#p1-s09-f-in-app-banner-notification-sse)
  - [P1-S10 — QuickBooks Integration](#p1-s10--quickbooks-integration)
    - [P1-S10-A: OAuth Connect Flow](#p1-s10-a-oauth-connect-flow)
    - [P1-S10-B: Conflict Detection + Resolution UI](#p1-s10-b-conflict-detection--resolution-ui)
    - [P1-S10-C: In-Flight Sync Indicator](#p1-s10-c-in-flight-sync-indicator)
  - [P1-S11 — Mobile Offline Operations](#p1-s11--mobile-offline-operations)
    - [P1-S11-A: Offline Capability Contract](#p1-s11-a-offline-capability-contract)
    - [P1-S11-B: Reconnect and Sync](#p1-s11-b-reconnect-and-sync)
    - [P1-S11-C: Four-Class Conflict Resolution](#p1-s11-c-four-class-conflict-resolution)
    - [P1-S11-D: Background Sync](#p1-s11-d-background-sync)
  - [P1-S12 — Voice AI](#p1-s12--voice-ai)
    - [P1-S12-A: End-to-End Voice Pipeline](#p1-s12-a-end-to-end-voice-pipeline)
    - [P1-S12-B: Multi-Turn Context Management](#p1-s12-b-multi-turn-context-management)
    - [P1-S12-C: Confirm-as-Turn for Destructive Actions](#p1-s12-c-confirm-as-turn-for-destructive-actions)
    - [P1-S12-D: Disambiguation Pattern](#p1-s12-d-disambiguation-pattern)
    - [P1-S12-E: Voice Field Operations Intents](#p1-s12-e-voice-field-operations-intents)
    - [P1-S12-F: NEC Code Calculations](#p1-s12-f-nec-code-calculations)
    - [P1-S12-G: Voice Persona Tone](#p1-s12-g-voice-persona-tone)
    - [P1-S12-H: Offline Voice Capture + Deferred Processing](#p1-s12-h-offline-voice-capture--deferred-processing)
  - [P1-S13 — Subscriptions & Usage](#p1-s13--subscriptions--usage)
    - [P1-S13-A: Trial Tier Behavior](#p1-s13-a-trial-tier-behavior)
    - [P1-S13-B: Trial Expiration + Paywall](#p1-s13-b-trial-expiration--paywall)
    - [P1-S13-C: SMS Quota Enforcement](#p1-s13-c-sms-quota-enforcement)
  - [P1-S14 — Audit & Compliance](#p1-s14--audit--compliance)
    - [P1-S14-A: Trigger-Based Mutation Capture](#p1-s14-a-trigger-based-mutation-capture)
  - [P1-S15 — Platform Infrastructure Patterns](#p1-s15--platform-infrastructure-patterns)
    - [P1-S15-A: Multi-Tenant Isolation](#p1-s15-a-multi-tenant-isolation)
    - [P1-S15-B: RFC 7807 Error Responses](#p1-s15-b-rfc-7807-error-responses)
    - [P1-S15-C: Rate Limiting](#p1-s15-c-rate-limiting)
    - [P1-S15-D: States Catalog (Empty / Loading / Error)](#p1-s15-d-states-catalog-empty--loading--error)
    - [P1-S15-E: Cursor-Based Pagination](#p1-s15-e-cursor-based-pagination)
    - [P1-S15-F: UTC Triple-Lock](#p1-s15-f-utc-triple-lock)
    - [P1-S15-G: In-Flight Sync Indicator (5-State Compositional Model)](#p1-s15-g-in-flight-sync-indicator-5-state-compositional-model)
  - [P1-S16 — Help & Support](#p1-s16--help--support)
    - [P1-S16-A: AI-Mediated Help Chat (RAG)](#p1-s16-a-ai-mediated-help-chat-rag)
    - [P1-S16-B: Web Side-Drawer + Mobile Full-Screen Chat](#p1-s16-b-web-side-drawer--mobile-full-screen-chat)
    - [P1-S16-C: AI Knowledge Boundaries + Escalation](#p1-s16-c-ai-knowledge-boundaries--escalation)
    - [P1-S16-D: Voice-Driven Help](#p1-s16-d-voice-driven-help)
    - [P1-S16-E: Past Conversations Recall](#p1-s16-e-past-conversations-recall)
    - [P1-S16-F: Structured Feedback Submission](#p1-s16-f-structured-feedback-submission)
    - [P1-S16-G: About / Version / Legal Surface](#p1-s16-g-about--version--legal-surface)
- [Phase 2 — Scenario-Based Testing (End-to-End User Journeys)](#phase-2--scenario-based-testing-end-to-end-user-journeys)
  - [P2-SC01 — New Tenant Onboarding (Signup → First Quote)](#p2-sc01--new-tenant-onboarding-signup--first-quote)
  - [P2-SC02 — Voice-First Quote-to-Cash (Owner-Operator, Mobile)](#p2-sc02--voice-first-quote-to-cash-owner-operator-mobile)
  - [P2-SC03 — Multi-User Shop: Tech Submits, Owner Approves, Customer Pays](#p2-sc03--multi-user-shop-tech-submits-owner-approves-customer-pays)
  - [P2-SC04 — Full Dispatch Day (Scheduling, Conflicts, Live Updates)](#p2-sc04--full-dispatch-day-scheduling-conflicts-live-updates)
  - [P2-SC05 — Tech Goes Offline (Basement → Surface → Sync Resolution)](#p2-sc05--tech-goes-offline-basement--surface--sync-resolution)
  - [P2-SC06 — QuickBooks Full Cycle (Connect → Sync → Conflict → Resolve)](#p2-sc06--quickbooks-full-cycle-connect--sync--conflict--resolve)
  - [P2-SC07 — Customer Communication Lifecycle (Template → Inbound Reply → Thread)](#p2-sc07--customer-communication-lifecycle-template--inbound-reply--thread)
  - [P2-SC08 — Trial Expiration + Conversion (Paywall → Stripe Payment)](#p2-sc08--trial-expiration--conversion-paywall--stripe-payment)
  - [P2-SC09 — Security Incident Response (Compromise → MFA Reset → Session Revoke)](#p2-sc09--security-incident-response-compromise--mfa-reset--session-revoke)
  - [P2-SC10 — ETC Variance Alert → Course Correction (Mid-Job Profitability)](#p2-sc10--etc-variance-alert--course-correction-mid-job-profitability)
- [Phase 3 — External Beta Testing (Contractor Cohort)](#phase-3--external-beta-testing-contractor-cohort)
  - [Beta Tester Recruitment Criteria](#beta-tester-recruitment-criteria)
  - [Beta Onboarding Playbook](#beta-onboarding-playbook)
  - [Beta Success Criteria (Gates Soft Launch)](#beta-success-criteria-gates-soft-launch)
  - [Beta Duration & Iteration Cadence](#beta-duration--iteration-cadence)
  - [Feedback Infrastructure](#feedback-infrastructure)
  - [Beta Exit Checklist](#beta-exit-checklist)
- [Appendix A — Seed Data Reference](#appendix-a--seed-data-reference)
- [Appendix B — Pre-Launch Hygiene Gaps](#appendix-b--pre-launch-hygiene-gaps)
- [Appendix C — Staging-Only Validations](#appendix-c--staging-only-validations)

---

## Document Purpose & How to Use

This document is the authoritative testing protocol for Pilot for Trades from owner self-testing through external beta. It follows a two-phase progression:

- **Phase 1 — Surface Verification**: Test each of the 16 product domains feature-by-feature, from simple to complex. Minimal cross-surface dependencies. Maps to unit + integration test layer.
- **Phase 2 — Scenario Testing**: Test realistic end-to-end contractor workflows that cross multiple surfaces. Maps to e2e test layer.
- **Phase 3 — External Beta**: Managed cohort of 8 contractors, per the Implementation Framework §Workstream 4.

**How to run**: Work through Phase 1 sections sequentially. Within each section, complete all sub-sections before moving to the next section. Mark each test case with the result legend below. Capture notes inline. Do NOT proceed to Phase 2 until all Phase 1 sections have zero 🔴 items.

---

## Pre-Test Environment Setup

### S1 — Docker Stack Verification

> **Run before any testing session begins.**

| # | Check | Command | Expected Result | Status |
|---|-------|---------|-----------------|--------|
| S1-01 | Docker daemon running | `docker ps` | Containers listed | ☐ |
| S1-02 | FastAPI backend app | Open `http://localhost:8000` | Status: Healthy | ☐ |
| S1-03 | PostgreSQL container up | `docker ps \| grep pilot_postgres` | Status: Up | ☐ |
| S1-04 | Redis container up | `docker ps \| grep pilot_redis` | Status: Up | ☐ |
| S1-05 | Celery worker container up | `docker ps \| grep pilot_celery_worker` | Status: Up | ☐ |
| S1-06 | Celery beat container up | `docker ps \| grep pilot_celery_beat` | Status: Up | ☐ |
| S1-07 | Whisper container up | `docker ps \| grep pilot_whisper` | Status: Up | ☐ |
| S1-08 | Ollama container up | `docker ps \| grep pilot_ollama` | Status: Up | ☐ |
| S1-09 | API health check | `curl http://localhost:8000/api/v1/health` | `{"status":"ok"}` | ☐ |
| S1-10 | Next.js web app | Open `http://localhost:3000` | Login page renders | ☐ |
| S1-11 | Expo mobile app | Open `http://localhost:8081` | QR code appears | ☐ |

### S2 — Voice AI Stack Verification

> **Confirmed local model versions (2026-06-02):**
> - Whisper: `Systran/faster-whisper-large-v3-turbo` (production-equivalent accuracy)
> - Ollama: `llama3.1:8b` (4.9 GB, CPU inference)
> - ⚠️ **Latency**: CPU-only inference. Voice pipeline will be 5–20s locally vs. <2s in production with GPU. Latency SLO validation is **staging-only** (see Appendix C).

| # | Check | Command | Expected Result | Status |
|---|-------|---------|-----------------|--------|
| S2-01 | Whisper model confirmed | `docker exec pilot_whisper env \| grep -i model` | `WHISPER__MODEL=Systran/faster-whisper-large-v3-turbo` | ☐ |
| S2-02 | Ollama model confirmed | `docker exec pilot_ollama ollama list` | `llama3.1:8b` listed | ☐ |
| S2-03 | Whisper responds | `curl -X POST http://localhost:8080/v1/audio/transcriptions -F "file=@test.wav" -F "model=turbo"` | Transcription JSON returned | ☐ |
| S2-04 | Ollama responds | `curl http://localhost:11434/api/generate -d '{"model":"llama3.1:8b","prompt":"Hello","stream":false}'` | JSON response with `response` field | ☐ |
| S2-05 | Full voice pipeline (API) | POST `/api/v1/voice/command` with test audio | Intent parsed + response returned | ☐ |

### S3 — Seed Data Population

> **Run in this exact order. Each script is idempotent (ON CONFLICT DO NOTHING).**

```bash
cd <repo>/backend
source .venv/bin/activate

python migrations/scripts/seed_core.py           # Group A: lookup tables
python migrations/scripts/seed_platform.py       # Group B: product plans + notification templates
python migrations/scripts/seed_test_tenant.py    # Group C: tenant + 3 users + pricing engine
python migrations/scripts/seed_scenario_quote_to_cash.py  # Group D: 5 customers, pricebook, draft quote
python migrations/scripts/seed_scenario_dispatch.py       # Group D: 5 jobs, assignments, PTO block

# Verify
python migrations/scripts/reset_dev_db.py --mode inspect
```

> **⚠️ WARNING**: Running seed scripts against the same DB used by `pytest` causes test interference. Run seed scripts for UI testing sessions. Wipe Group D with `python migrations/scripts/reset_dev_db.py --wipe-only` before running `pytest`.

> **ℹ️ 2026-08-20 — env-aware seeds (DB-MGMT-1)**: all seed scripts are now env-aware (`--env dev` is the default for local work; `SEED_ENV` is also honored). The commands above remain valid against the dev DB. See `backend/README-seed-data.md` §7.5–7.7 for the env-value matrix + provisioning runbooks.

### S4 — Test Accounts & Credentials Reference

**⚠️ Two-tier user strategy — read before testing.**

#### Tier 1: Seeded Users (non-auth surface testing)

Use for all non-auth tests: quoting, dispatch, field ops, catalog, etc. These bypass the signup wizard and provide instant access to the test tenant data.

| Role | Email | Password | UUID |
|------|-------|----------|------|
| **Owner** | `dev@pilot.local` | *(see `backend/.env`)* | `00000000-0000-0000-0000-000000000002` |
| **Technician** | `tech@pilot.local` | *(see `backend/.env`)* | `00000000-0000-0000-0000-000000000003` |
| **Office Staff** | `office@pilot.local` | *(see `backend/.env`)* | `00000000-0000-0000-0000-000000000004` |
| **Tenant** | — | — | `00000000-0000-0000-0000-000000000001` |

> ⚠️ **MFA limitation**: `*.pilot.local` addresses are fake — they cannot receive Cognito email OTPs or SMS OTPs from AWS. TOTP (authenticator app) works for seeded users since it requires no real email/phone. For Email OTP and SMS OTP channel testing, use Tier 2 accounts below.

#### Tier 2: Real Test Users (auth + MFA surface testing — create during P1-S01)

Create these via the signup wizard during P1-S01. This simultaneously exercises the signup flow, real AWS Cognito registration, and real MFA enrollment — exactly as a real beta tester will experience it. Use Gmail `+` addressing to create multiple inboxes from your single Gmail account without creating new accounts.

| Persona | Suggested Email | Phone | Purpose |
|---------|----------------|-------|---------|
| **Test Owner** | `your-email+pilot-owner@gmail.com` | Your real mobile | Tests owner signup wizard, TOTP + SMS + Email OTP, session management, data export |
| **Test Tech** | `your-email+pilot-tech@gmail.com` | Optional | Tests technician RBAC restrictions; TOTP-only MFA sufficient |
| **Test Accountant** | `your-email+pilot-accountant@gmail.com` | Optional | Tests accountant-role permission gates |

> ℹ️ **Cognito MFA delivery — no 10DLC required**:
> - **TOTP**: Authenticator app (Google Authenticator, Authy, 1Password) — no network delivery; works locally
> - **SMS OTP**: Delivered via **AWS SNS** (not Telnyx/MockSmsCarrier — completely separate pipeline). Requires a real phone number registered on the Tier 2 account.
> - **Email OTP**: Delivered via **Cognito's own SES integration** (not SendGrid). Requires a real email address. Gmail `+` addressing works.
> - 10DLC registration only affects Pilot's customer-facing SMS (appointment templates, comms) — not Cognito MFA.

> 🔑 **Recovery codes**: 10 single-use recovery codes are generated at first MFA enrollment. Store in your password manager during test runs — needed for the "lost device" recovery path test in P1-S01-C.

### S5 — Known Limitations for Local Testing

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Voice AI latency: 5–20s on CPU (vs. <2s target) | Functional tests valid; latency SLO not measurable | Staging-only validation — see Appendix C |
| SMS (MockSmsCarrier): messages not delivered to real phones | All SMS logic works; no real phone delivery | Verify via API response + DB outbox table |
| Stripe: test mode only | Real card not charged; use Stripe test card `4242 4242 4242 4242` | Test mode is sufficient for Phase 1 |
| Google Calendar OAuth: requires registered callback URL | OAuth flow may not redirect correctly locally | Use ngrok or test with pre-configured integration credential in DB |
| QuickBooks OAuth: requires ngrok for callback | Same as Calendar | Use ngrok tunnel on port 8000 |
| Push notifications: not deliverable to simulators | Push logic validates; notification not received | Test push with physical device for Phase 1-S09-J |
| GPS verification: simulator uses mock coordinates | GPS capture records lat/lng; accuracy not verifiable | Test on physical device for P1-S05-I |
| Email delivery: SendGrid not configured locally | Email templates render; delivery not verified | Use Mailtrap or check `notification_outbox` table directly |

---

## Test Result Legend

| Symbol | Meaning |
|--------|---------|
| ☐ | Not yet executed |
| ✅ | **Pass** — Feature works as PRD specifies; correct output; no data loss |
| ⚠️ | **Pass with note** — Feature works; UX friction or minor deviation observed; non-blocking for beta |
| 🔴 | **Fail** — Data corruption, incorrect business logic, missing gating, security gap; must fix before proceeding |
| ⏭️ | **Skipped** — Not testable in current environment; documented in Appendix C |

> **Rule**: Do not proceed to Phase 2 until all Phase 1 test cases are ✅ or ⚠️ (no 🔴 items remain).

---

## Phase 1 — Surface Verification (Feature-by-Feature)

> *(Test case details to be written in each section below — this skeleton is pending your TOC review and sign-off before test cases are drafted)*

### P1-S01 — Identity, Access & Tenant Management

> **Setup**: Run seed scripts (S3) before this section. For sub-sections A, B, C, E, G, H use Tier 2 real accounts. For sub-sections D and F, Tier 1 seeded users are sufficient.

---

#### P1-S01-A: Signup Wizard (5-Step)

##### P1-S01-A-01 — Complete 5-step signup wizard end-to-end
- **User**: Tier 2 real account (create fresh — `your-email+pilot-owner@gmail.com`)
- **Surface**: Web — `/signup`
- **PRD Ref**: §3.5 Tenant Signup Wizard
- **Status**: ☐

**Steps:**
1. Navigate to `http://localhost:3000/signup`
2. **Step 1 — Account**: Enter business name, select trade (`electrical`), business size (`1-3`), ZIP code, time zone → click **Next**
3. **Step 2 — Legal**: Check ToS, Privacy Policy, EULA boxes → click **Accept & Continue**
4. **Step 3 — Phone** (optional): Enter real mobile number → receive SMS OTP via AWS SNS → enter code → click **Verify** *(or click **Skip** to test skip path)*
5. **Step 4 — Tier**: Confirm Trial is pre-selected (full features, $0, time-bounded) → click **Start Trial**
6. **Step 5 — Confirm**: Review summary → click **Go to Dashboard**

**Expected Result:**
- Dashboard loads at `/dashboard`
- Pinned "Setup checklist" widget visible with first 3 items auto-checked (account created, legal accepted, tier selected)
- DB check: `SELECT signup_state FROM tenant_signup WHERE tenant_id = <new_id>` → `complete`
- DB check: `SELECT account_created, legal_accepted, tier_selected FROM tenant_onboarding_checklist WHERE tenant_id = <new_id>` → all `true`

**Notes:** _______________

---

##### P1-S01-A-02 — Abandon wizard mid-way, resume from correct step
- **User**: Tier 2 real account (second fresh account)
- **Surface**: Web — `/signup`
- **PRD Ref**: §3.5 Resumable Wizard State
- **Status**: ☐

**Steps:**
1. Start signup wizard; complete Step 1 (account info) and Step 2 (legal)
2. Close the browser tab without completing Step 3
3. Re-open browser, navigate to `http://localhost:3000` and log in with the new account
4. Observe the routing

**Expected Result:**
- App routes to Step 3 (Phone) — not Step 1
- Step 1 and Step 2 marked as completed in wizard progress indicator
- Step 1 fields pre-filled with previously entered data if navigating back

**Notes:** _______________

---

##### P1-S01-A-03 — Back navigation through completed steps
- **User**: Tier 2 real account (mid-wizard state from A-02 or a fresh run)
- **Surface**: Web — `/signup`
- **PRD Ref**: §3.5 Resumable Wizard State
- **Status**: ☐

**Steps:**
1. During wizard, navigate forward to Step 3
2. Click **Back** to return to Step 2 (Legal)
3. Verify legal acceptance state is preserved
4. Click **Back** again to Step 1
5. Verify business info fields are pre-filled

**Expected Result:**
- Back navigation works at each step
- Previously entered data persists across back/forward navigation
- Legal checkboxes remain checked after navigating back and forward

**Notes:** _______________

---

#### P1-S01-B: Login, JWT & Session Management

##### P1-S01-B-01 — Successful login (owner)
- **User**: Tier 2 test owner account (post-wizard)
- **Surface**: Web — `/login`
- **PRD Ref**: §4.2 JWT Authentication Flow
- **Status**: ☐

**Steps:**
1. Navigate to `http://localhost:3000/login`
2. Enter email and password → click **Sign In**
3. If MFA enrolled, complete the MFA challenge
4. Observe routing

**Expected Result:**
- Redirected to `/dashboard`
- JWT (access token) present in browser session (check DevTools → Application → Cookies or localStorage)
- Access token expires in 1 hour (check `exp` claim via JWT decoder)

**Notes:** _______________

---

##### P1-S01-B-02 — Login failure: wrong password
- **User**: Tier 2 test owner account
- **Surface**: Web — `/login`
- **PRD Ref**: §4.2 JWT Authentication Flow
- **Status**: ☐

**Steps:**
1. Navigate to login page
2. Enter correct email but wrong password → click **Sign In**
3. Observe error message
4. Enter correct credentials → verify successful login

**Expected Result:**
- Error message displayed ("Invalid credentials" or equivalent — RFC 7807 error format)
- User remains on login page
- No JWT issued
- Correct credentials succeed after failure

**Notes:** _______________

---

##### P1-S01-B-03 — Logout clears session
- **User**: Tier 2 test owner account (logged in)
- **Surface**: Web — app shell
- **PRD Ref**: §4.1 AWS Cognito Configuration
- **Status**: ☐

**Steps:**
1. Log in successfully
2. Click user avatar / account menu → click **Sign Out**
3. Attempt to navigate to `/dashboard` directly
4. Attempt to call `GET /api/v1/customers` with the previous access token

**Expected Result:**
- After logout, redirected to `/login`
- Direct navigation to `/dashboard` redirects to `/login`
- API call with revoked token returns `401 Unauthorized`

**Notes:** _______________

---

#### P1-S01-C: Multi-Factor Authentication (TOTP / SMS / Email)

##### P1-S01-C-01 — Enroll TOTP (authenticator app)
- **User**: Tier 2 test owner account (no MFA enrolled yet)
- **Surface**: Web — `My Account > Security > MFA`
- **PRD Ref**: §4.5 Multi-Factor Authentication
- **Status**: ☐

**Steps:**
1. Navigate to `Settings > My Account > Security`
2. Click **Add MFA method** → select **Authenticator app (TOTP)**
3. UI displays QR code — scan with Google Authenticator / Authy / 1Password
4. Enter the 6-digit code shown in the authenticator app → click **Verify**
5. UI shows 10 recovery codes — copy and store them
6. Confirm enrollment is shown as "Verified" on the MFA methods list

**Expected Result:**
- TOTP method appears as enrolled with "Verified" status
- Recovery codes displayed once and dismissable
- DB check: `SELECT method_type, verification_status FROM user_mfa_method WHERE user_id = <uid>` → row with `method_type='totp'`, `verification_status='verified'`
- 10 rows in `user_mfa_recovery_code` for this user

**Notes:** _______________

---

##### P1-S01-C-02 — Login challenge with TOTP
- **User**: Tier 2 test owner account (TOTP enrolled from C-01)
- **Surface**: Web — `/login`
- **PRD Ref**: §4.5 Login challenge flow
- **Status**: ☐

**Steps:**
1. Log out if currently logged in
2. Navigate to login page → enter credentials → click **Sign In**
3. MFA challenge screen appears with TOTP option
4. Open authenticator app → enter current 6-digit code → click **Verify**

**Expected Result:**
- After correct TOTP code, redirected to dashboard
- `user_mfa_method.last_used_at` updated for the TOTP method

**Notes:** _______________

---

##### P1-S01-C-03 — Enroll SMS OTP (real phone number)
- **User**: Tier 2 test owner account
- **Surface**: Web — `My Account > Security > MFA`
- **PRD Ref**: §4.5 Supported methods
- **Status**: ☐

**Steps:**
1. Navigate to MFA settings
2. Click **Add MFA method** → select **SMS (text message)**
3. UI shows security note about SMS vulnerability — confirm you understand
4. Enter real mobile phone number → click **Send code**
5. Receive 6-digit SMS code via AWS SNS → enter code → click **Verify**

**Expected Result:**
- SMS OTP method enrolled and shown as "Verified"
- DB check: second row in `user_mfa_method` with `method_type='sms'`
- Method card shows last 4 digits of phone number as metadata

**Notes:** _______________

---

##### P1-S01-C-04 — Wrong TOTP code 5 times → method locked → switch to SMS
- **User**: Tier 2 test owner account (both TOTP and SMS enrolled)
- **Surface**: Web — `/login` MFA challenge
- **PRD Ref**: §4.5 Wrong-code handling
- **Status**: ☐

**Steps:**
1. Log out → log in → reach MFA challenge screen (TOTP selected)
2. Enter an intentionally wrong 6-digit code 5 times
3. Observe lock message for TOTP method
4. Click **Use a different method** → select **SMS**
5. Receive and enter SMS code → complete login

**Expected Result:**
- After 5 wrong TOTP codes, TOTP method shows "Locked for 15 minutes" message (enforced by AWS Cognito)
- User can switch to enrolled SMS method without being locked out of the account
- Login completes successfully via SMS OTP

**Notes:** _______________

---

##### P1-S01-C-05 — Recovery code fallback (lost all enrolled methods)
- **User**: Tier 2 test owner account (TOTP enrolled; recovery codes saved from C-01)
- **Surface**: Web — `/login` MFA challenge
- **PRD Ref**: §4.5 Recovery codes
- **Status**: ☐

**Steps:**
1. Log out → log in → reach MFA challenge screen
2. Click **Use recovery code** link
3. Enter one of the 10 recovery codes saved during TOTP enrollment
4. Complete login

**Expected Result:**
- Login succeeds using recovery code
- Used recovery code marked as consumed (DB: `user_mfa_recovery_code.used_at` is non-null)
- Recovery code cannot be reused — entering same code again is rejected

**Notes:** _______________

---

##### P1-S01-C-06 — Owner resets another user's MFA (support escape hatch)
- **User**: Tier 2 test owner (owner role) + Tier 2 test tech (technician role, MFA enrolled)
- **Surface**: Web — `Settings > Users & Roles > [user detail] > Reset MFA`
- **PRD Ref**: §3.5 Owner Reset of User MFA
- **Status**: ☐

**Steps:**
1. Log in as owner
2. Navigate to `Settings > Users & Roles` → find the test technician user
3. Click into tech's user detail → click **Reset MFA**
4. Confirm the action in the confirmation dialog
5. Log out, then attempt login as the technician

**Expected Result:**
- Owner sees confirmation that MFA was reset
- Audit log entry created with actor (owner) and target (tech) identities
- Tech receives email notification that their MFA was reset (check `notification_outbox` or email inbox)
- On next tech login, MFA challenge is skipped (no enrolled methods) — or re-enrollment is prompted if tenant MFA is required

**Notes:** _______________

---

#### P1-S01-D: RBAC — Role-Based Access Control

##### P1-S01-D-01 — Technician role: blocked from financial admin endpoints
- **User**: Tier 1 `tech@pilot.local` (technician role)
- **Surface**: API + Web
- **PRD Ref**: §4.3 Role-Based Access Control
- **Status**: ☐

**Steps:**
1. Log in as technician (`tech@pilot.local`)
2. Attempt to navigate to `Settings > Integrations > QuickBooks`
3. Attempt to navigate to `Invoices` section
4. Attempt API call: `GET /api/v1/invoices` with technician JWT
5. Attempt API call: `GET /api/v1/audit` with technician JWT

**Expected Result:**
- `Settings > Integrations` section is hidden or disabled (hide-not-disable RBAC per FE implementation)
- `Invoices` section is not accessible from technician's navigation
- API returns `403 Forbidden` with RFC 7807 error body: `"required_permission": "invoices.view"`, `"user_role": "technician"`
- Audit log endpoint returns `403 Forbidden`

**Notes:** _______________

---

##### P1-S01-D-02 — Owner role: full access to all routes
- **User**: Tier 1 `dev@pilot.local` (owner role)
- **Surface**: Web + API
- **PRD Ref**: §4.3 RBAC — owner role has `["*"]`
- **Status**: ☐

**Steps:**
1. Log in as owner (`dev@pilot.local`)
2. Navigate through all main navigation sections: Dashboard, Jobs, Quotes, Customers, Dispatch, Invoices, Settings
3. Verify each section loads without 403 errors

**Expected Result:**
- All navigation sections accessible
- No 403 errors in browser console during navigation
- Settings sub-sections (Integrations, Users & Roles, Notifications, Subscription) all render

**Notes:** _______________

---

##### P1-S01-D-03 — Accountant role: can approve quotes, cannot manage users
- **User**: Tier 2 test accountant account
- **Surface**: Web + API
- **PRD Ref**: §4.3 accountant role permissions
- **Status**: ☐

**Steps:**
1. Log in as accountant
2. Navigate to a pending quote → verify **Approve** and **Reject** buttons are present
3. Attempt to navigate to `Settings > Users & Roles`
4. Attempt API call: `POST /api/v1/users` (invite new user) with accountant JWT

**Expected Result:**
- Quote approval buttons visible and functional (accountant has `quote.approve` permission)
- `Settings > Users & Roles` is hidden or inaccessible for accountant
- User invite API returns `403 Forbidden`

**Notes:** _______________

---

#### P1-S01-I: Settings Sidebar Navigation Readability (BETA-B7)

##### P1-S01-I-01 — Settings sidebar group labels are clearly larger than sub-items
- **User**: Tier 1 owner
- **Surface**: Web — Settings sidebar
- **PRD Ref**: §3.6 Settings & Configuration navigation
- **Status**: ☐
- **Prerequisite**: BETA-B7 complete

**Steps:**
1. Log in as owner and navigate to **Settings > Operations**
2. Observe the sidebar group label "Operations" and its sub-items ("Margin buckets", "Profitability rules", "Field operations")
3. Navigate to **Settings > Integrations**
4. Expand to see sub-item "QuickBooks" and its child "Auto-expiry & sync"

**Expected Result:**
- Group labels ("Operations", "My Account", "Integrations", etc.) render noticeably larger and bolder than sub-items — visually distinct as section headers
- Sub-items ("Margin buckets") are clearly smaller than their parent group label
- "Auto-expiry & sync" (under QuickBooks) is indented further than "QuickBooks" and appears in a muted grey — clearly tertiary
- No sub-item appears larger than its parent group label (the pre-BETA-B7 regression is gone)

**Notes:** _______________

---

#### P1-S01-E: Tenant-Required MFA Policy + Grace Period

##### P1-S01-E-01 — Enable tenant-wide MFA requirement
- **User**: Tier 2 test owner (owner role only)
- **Surface**: Web — `Settings > Users & Roles > Security policy`
- **PRD Ref**: §3.5 Tenant-Required MFA Policy
- **Status**: ☐

**Steps:**
1. Log in as owner
2. Navigate to `Settings > Users & Roles > Security policy`
3. Toggle **Require MFA for all users** to ON
4. Confirm in the dialog (note: 7-day grace period starts now)
5. Log in as the test technician (no MFA enrolled) in a separate browser/incognito session

**Expected Result:**
- Owner sees confirmation that policy is enabled with grace period start date shown
- DB check: `SELECT tenant_mfa_required, tenant_mfa_grace_period_starts_at FROM platform_setting WHERE tenant_id = <tid>` → `true` + current timestamp
- Technician login shows a warning banner about MFA enrollment requirement and grace period deadline
- Technician is NOT immediately blocked from accessing the app (7-day grace)

**Notes:** _______________

---

##### P1-S01-E-02 — Login during grace period triggers enrollment prompt
- **User**: Tier 2 test tech (no MFA enrolled, tenant MFA required)
- **Surface**: Web — `/login`
- **PRD Ref**: §4.5 Grace period behavior (login-trigger enforcement)
- **Status**: ☐

**Steps:**
1. With tenant MFA policy enabled (from E-01), log out the technician
2. Log back in as technician
3. Observe the post-login flow

**Expected Result:**
- After successful password authentication, app immediately routes to MFA enrollment flow for this session
- Tech can enroll at least one method
- After enrollment, tech accesses the app normally

**Notes:** _______________

---

#### P1-S01-F: Post-Wizard Setup Checklist

##### P1-S01-F-01 — Checklist auto-completion when action taken via any path
- **User**: Tier 2 test owner (freshly completed wizard from A-01)
- **Surface**: Web — Dashboard
- **PRD Ref**: §3.5 Post-Wizard Setup Checklist
- **Status**: ☐

**Steps:**
1. Log in as the test owner who just completed the wizard
2. Observe the setup checklist widget — note which items are pending
3. Navigate to Customers → create a new customer via the form (NOT via the checklist's "Add now" button)
4. Return to Dashboard
5. Observe the checklist

**Expected Result:**
- "Add first customer" item auto-marks as complete
- `tenant_onboarding_checklist.first_customer_added = true` and `first_customer_added_at` is populated
- Auto-completion happens regardless of how the customer was created (form, voice command, or checklist button)

**Notes:** _______________

---

##### P1-S01-F-02 — Skip and dismiss checklist items
- **User**: Tier 2 test owner
- **Surface**: Web — Dashboard checklist widget
- **PRD Ref**: §3.5 Post-Wizard Setup Checklist
- **Status**: ☐

**Steps:**
1. On the dashboard, find the checklist widget
2. Click **Skip** on the "Connect QuickBooks" item
3. Click **Dismiss** on the "Invite team" item
4. Reload the page

**Expected Result:**
- Skipped item remains visible but marked as skipped
- Dismissed item no longer shows in the checklist
- State persists across page reload (stored server-side per-tenant)
- DB check: `tenant_onboarding_checklist.quickbooks_skipped = true`, `team_skipped = true`

**Notes:** _______________

---

#### P1-S01-G: Profile, Password & Active Sessions

##### P1-S01-G-01 — Update display name and profile photo
- **User**: Tier 2 test owner
- **Surface**: Web — `My Account > Profile`
- **PRD Ref**: §3.5 Profile Management
- **Status**: ☐

**Steps:**
1. Navigate to `My Account > Profile`
2. Change display name to a new value → click **Save**
3. Upload a profile photo (any PNG/JPG image) → crop if prompted → click **Save**
4. Reload the page

**Expected Result:**
- Display name updated and shown in the app shell / avatar area after save
- Profile photo visible after upload; persists after reload
- Changes reflected in `user` table

**Notes:** _______________

---

##### P1-S01-G-02 — Change password → other sessions auto-revoked
- **User**: Tier 2 test owner (logged in on two browsers/tabs)
- **Surface**: Web — `My Account > Password`
- **PRD Ref**: §3.5 Password Change with Cross-Device Session Invalidation
- **Status**: ☐

**Steps:**
1. Open two browser sessions logged in as the test owner (e.g., Chrome + Safari)
2. In Browser A, navigate to `My Account > Password`
3. Enter current password + new password → click **Change Password**
4. Observe Browser A (the changing session)
5. Attempt any API action or page navigation in Browser B

**Expected Result:**
- Browser A remains logged in after password change
- Browser B receives `401 Unauthorized` on next request → redirected to login page
- DB check: `user_session_metadata` shows `revoked_at` set on all sessions except the current one

**Notes:** _______________

---

##### P1-S01-G-03 — View active sessions and revoke a specific session
- **User**: Tier 2 test owner (logged in on multiple devices/browsers)
- **Surface**: Web — `My Account > Security > Active sessions`
- **PRD Ref**: §4.8.1 Active Sessions List + Revoke
- **Status**: ☐

**Steps:**
1. Log in from at least 2 different browsers (Chrome + Safari, or Chrome + incognito)
2. In the first browser, navigate to `My Account > Security > Active sessions`
3. Verify both sessions are listed with device/browser label + approximate location
4. Click **Revoke** on the second session
5. Attempt any action in the second browser

**Expected Result:**
- Active sessions list shows multiple sessions with device labels, last-active timestamps, IP/location
- After revoke, second browser gets `401` on next action → routes to login
- Revoking a session does not affect the first browser's session

**Notes:** _______________

---

#### P1-S01-H: Personal Data Export

##### P1-S01-H-01 — Owner requests and receives full tenant data export
- **User**: Tier 2 test owner
- **Surface**: Web — `My Account > Data export`
- **PRD Ref**: §3.5 Personal Data Export Request, §4.8.2
- **Status**: ☐

**Steps:**
1. Navigate to `My Account > Data export`
2. Click **Request export**
3. Wait for Celery task to process (check `data_export_request.status` via DB or poll the UI)
4. Receive email with download link (check inbox for `your-email+pilot-owner@gmail.com`)
5. Click the download link → download ZIP
6. Unzip and verify contents

**Expected Result:**
- `data_export_request` row created with `status = 'pending'` → transitions to `'ready'`
- Email received with 7-day signed S3 URL
- ZIP contains: `customers.csv`, `jobs.csv`, `quotes.csv`, `invoices.csv`, `time_entries.csv`, `expenses.csv`, `communications.csv`, `MANIFEST.json`
- `MANIFEST.json` includes tenant_id, requesting user, timestamp, data scope (`full_tenant`)

**Notes:** _______________

---

##### P1-S01-H-02 — 24-hour frequency limit enforced
- **User**: Tier 2 test owner (just completed H-01)
- **Surface**: Web — `My Account > Data export`
- **PRD Ref**: §4.8.2 Frequency limit
- **Status**: ☐

**Steps:**
1. Immediately after H-01 completes, attempt to request another data export

**Expected Result:**
- Button is disabled or request is rejected with a message indicating one export per 24 hours is allowed
- No new `data_export_request` row created

**Notes:** _______________

---

##### P1-S01-H-03 — Technician export scoped to own data only
- **User**: Tier 1 `tech@pilot.local` (technician role)
- **Surface**: Web — `My Account > Data export`
- **PRD Ref**: §3.5 Personal Data Export — RBAC-scoped
- **Status**: ☐

**Steps:**
1. Log in as technician
2. Navigate to `My Account > Data export` → request export
3. Download and inspect the ZIP

**Expected Result:**
- Export succeeds but contains only the technician's own data: their own `time_entries.csv`, `expenses.csv`, and `communications.csv`
- Does NOT contain all tenant customers, all quotes, or all invoices (those are owner/accountant scope)
- `MANIFEST.json` shows `data_scope = 'user_specific'`

**Notes:** _______________

### P1-S02 — Catalog & Pricing

> **Setup**: Seed scripts (S3) must be run — Group D includes 5 pricebook items. Log in as owner (`dev@pilot.local`) for all sub-sections unless noted.

---

#### P1-S02-A: Pricebook Item Management

##### P1-S02-A-01 — View seeded pricebook items
- **User**: Tier 1 owner (`dev@pilot.local`)
- **Surface**: Web — Catalog / Pricebook
- **PRD Ref**: §3.2 Catalog & Pricing
- **Status**: ☐

**Steps:**
1. Log in as owner → navigate to `Catalog > Pricebook`
2. Verify the 5 seeded items are displayed

**Expected Result:**
- 5 items visible: Standard Outlet Installation ($150), 200A Panel Upgrade ($1,800), 15A Circuit Breaker ($18), EMT Conduit ($3.50/ft), Residential Permit Fee ($250)
- Each item shows SKU, name, unit price, category, taxability code
- Items scoped to test tenant only (no cross-tenant leakage)

**Notes:** _______________

---

##### P1-S02-A-02 — Create new pricebook item
- **User**: Tier 1 owner
- **Surface**: Web — Catalog / Pricebook
- **PRD Ref**: §3.2 Catalog & Pricing
- **Status**: ☐

**Steps:**
1. Navigate to `Catalog > Pricebook` → click **Add item**
2. Enter: SKU `WIRE-12AWG-01`, Name `12 AWG THHN Wire`, Unit Price `$0.85/ft`, Category `material`, Taxability `taxable`
3. Click **Save**

**Expected Result:**
- New item appears in the pricebook list
- `pricebook_item` row created with correct `tenant_id`
- Append-only `pricebook_item_version` row created with the initial price ($0.85)

**Notes:** _______________

---

##### P1-S02-A-03 — Edit pricebook item creates new version (price immutability)
- **User**: Tier 1 owner
- **Surface**: Web — Catalog / Pricebook
- **PRD Ref**: §3.2 Historical Price Immutability
- **Status**: ☐

**Steps:**
1. Open the `12 AWG THHN Wire` item created in A-02
2. Edit the unit price to `$0.92/ft` → click **Save**
3. DB check: `SELECT unit_price_cents, created_at FROM pricebook_item_version WHERE pricebook_item_id = <id> ORDER BY created_at`

**Expected Result:**
- UI shows updated price of $0.92/ft
- 2 rows in `pricebook_item_version` — original $0.85 NOT overwritten (append-only confirmed)
- Latest price is the active one shown in the catalog

**Notes:** _______________

---

##### P1-S02-A-04 — Technician cannot manage catalog items (RBAC)
- **User**: Tier 1 `tech@pilot.local` (technician role)
- **Surface**: Web + API
- **PRD Ref**: §4.3 RBAC — technician role excludes `catalog.*`
- **Status**: ☐

**Steps:**
1. Log in as technician → navigate to `Catalog` section
2. Attempt API call: `POST /api/v1/catalog/pricebook-items/test` with technician JWT

**Expected Result:**
- Catalog management UI hidden or inaccessible for technician
- API returns `403 Forbidden` with `required_permission: "catalog.create"`, `user_role: "technician"`

**Notes:** _______________

---

#### P1-S02-B: Supplier Catalog Sync (Manual / CSV Import)

##### P1-S02-B-01 — Manual CSV import of supplier items
- **User**: Tier 1 owner
- **Surface**: Web — `Catalog > Suppliers > [supplier] > Import`
- **PRD Ref**: §3.2 Real-Time Supplier API & CSV Import (manual mode, `mode='manual'`)
- **Status**: ☐

**Steps:**
1. Navigate to `Catalog > Suppliers` → select or create a supplier (e.g., "Home Depot Pro")
2. Click **Import CSV** → upload a test CSV with columns: SKU, description, unit_price, unit_of_measure
3. Confirm import → wait for processing

**Expected Result:**
- CSV parsed; `SupplierItem` and `SupplierItemPrice` rows created for each valid row
- Import result logged in the connector run log
- Items visible in the supplier's catalog view
- Invalid rows (missing required columns) shown as import errors — import does not crash; valid rows still imported

**Notes:** _______________

---

##### P1-S02-B-02 — Price history: re-import with changed prices creates new rows
- **User**: Tier 1 owner
- **Surface**: Web — Catalog / Suppliers
- **PRD Ref**: §3.2 Historical Price Immutability (Snapshotting)
- **Status**: ☐

**Steps:**
1. Import a CSV with item SKU `TEST-ITEM-01` at price `$10.00`
2. Re-import the same CSV with `TEST-ITEM-01` at price `$11.50`
3. DB check: `SELECT price_cents, created_at FROM supplier_item_price WHERE sku = 'TEST-ITEM-01' ORDER BY created_at`

**Expected Result:**
- 2 `SupplierItemPrice` rows for `TEST-ITEM-01` — original $10.00 NOT overwritten (append-only)
- Latest price ($11.50) shown in catalog UI
- Historical row preserved

**Notes:** _______________

---

#### P1-S02-C: Labor Rate Versions

##### P1-S02-C-01 — View seeded labor rates and create new version
- **User**: Tier 1 owner
- **Surface**: Web — `Catalog > Labor Rates`
- **PRD Ref**: §3.2 Labor Burden Rate Version Catalog
- **Status**: ☐

**Steps:**
1. Navigate to labor rates section
2. Verify 3 seeded rates: Master ($120/hr), Journeyman ($85/hr), Apprentice ($55/hr)
3. Create a new rate version: Master at $125/hr effective today
4. DB check: `SELECT hourly_rate_cents, created_at FROM labor_rate_version WHERE tenant_id = '...0001' ORDER BY created_at`

**Expected Result:**
- 3 original seeded rates visible
- New version row created (append-only) — old $120/hr row preserved
- UI shows $125/hr as the current Master rate

**Notes:** _______________

---

#### P1-S02-D: Category Markups

##### P1-S02-D-01 — View and edit markup percentage by category
- **User**: Tier 1 owner
- **Surface**: Web — `Catalog > Markups` or Settings
- **PRD Ref**: §3.2 Category-Specific Markups
- **Status**: ☐

**Steps:**
1. Navigate to markup settings → verify seeded markup: `materials` = 20%
2. Change markup for `materials` to 25% → save
3. Create a new quote with a material line item → verify 25% markup applied to cost basis

**Expected Result:**
- Markup change saved
- New quote applies 25% markup — old quotes NOT retroactively affected
- DB check: `SELECT markup_pct FROM tenant_markup_version WHERE tenant_id = '...0001' AND category = 'materials' ORDER BY created_at` → 2 rows (20%, 25%)

**Notes:** _______________

---

#### P1-S02-E: Historical Price Immutability on Quotes

##### P1-S02-E-01 — Price change does not affect existing sent quote
- **User**: Tier 1 owner
- **Surface**: Web — Catalog + Quotes
- **PRD Ref**: §3.2 Historical Price Immutability
- **Status**: ☐

**Steps:**
1. Open the seeded draft quote (John Smith, $240) or create a new quote with "15A Circuit Breaker" at $18.00
2. Send the quote (or advance status to `sent` via API)
3. Return to Catalog → edit the 15A Circuit Breaker price to $22.00
4. Re-open the sent quote

**Expected Result:**
- Sent quote still shows $18.00 per unit (snapshot frozen at quote creation)
- DB check: `SELECT unit_price_cents FROM quote_line WHERE quote_id = <id>` → 1800 (unchanged)
- New quotes after the price change will pick up $22.00

**Notes:** _______________

### P1-S03 — CRM (Customer Relationship Management)

> **Setup**: Seed scripts run (Group D has 5 customers, 3 sites). Log in as owner (`dev@pilot.local`).

---

#### P1-S03-A: Customer Create / Edit / Soft-Delete

##### P1-S03-A-01 — View seeded customers
- **User**: Tier 1 owner
- **Surface**: Web — Customers list
- **PRD Ref**: §3.3 CRM
- **Status**: ☐

**Steps:**
1. Navigate to `Customers`
2. Verify 5 seeded customers are listed

**Expected Result:**
- 5 customers visible: John Smith (person/active), Mary Johnson (person/active), Apex Commercial LLC (company/active), Bob Davis (person/prospect), Inactive Customer (person/dormant)
- Customer type badge (person vs. company) displayed correctly
- Lifecycle status shown (active, prospect, dormant)

**Notes:** _______________

---

##### P1-S03-A-02 — Create residential customer
- **User**: Tier 1 owner
- **Surface**: Web — Customers
- **PRD Ref**: §3.3 Commercial vs. Residential Customer Profiling
- **Status**: ☐

**Steps:**
1. Click **New Customer** → select type: `Person` (residential)
2. Enter: Name `Sarah Williams`, Phone `+1 718 555 0199`, Email `sarah@example.com`, lifecycle `active`
3. Save

**Expected Result:**
- Customer created with `customer.type = 'person'`
- Appears in customer list with correct type badge
- Audit log entry captured

**Notes:** _______________

---

##### P1-S03-A-03 — Create commercial customer
- **User**: Tier 1 owner
- **Surface**: Web — Customers
- **PRD Ref**: §3.3 Commercial vs. Residential Customer Profiling
- **Status**: ☐

**Steps:**
1. Click **New Customer** → select type: `Company` (commercial)
2. Enter: Company name `Metro Properties LLC`, Primary contact name, Phone
3. Save

**Expected Result:**
- Customer created with `customer.type = 'company'`
- Company name field displayed (vs. individual name for person type)
- Downstream UI (invoicing, quoting) reflects company-specific treatment

**Notes:** _______________

---

##### P1-S03-A-04 — Edit customer and verify soft-delete
- **User**: Tier 1 owner
- **Surface**: Web — Customer detail
- **PRD Ref**: §3.3 CRM; §3.8 Soft-Delete Cascade Triggers
- **Status**: ☐

**Steps:**
1. Open `Bob Davis` (prospect) → edit phone number → save
2. Verify change persists
3. Deactivate the customer (soft-delete / mark inactive)
4. DB check: `SELECT is_active FROM customer WHERE id = <id>`

**Expected Result:**
- Phone update saved and reflected in UI
- Soft-delete sets `is_active = false` (NOT a hard delete)
- Customer no longer appears in active customer lists but accessible via archived/inactive filter
- Cascade trigger propagates deactivation to related sites

**Notes:** _______________

---

#### P1-S03-B: Multi-Site Management

##### P1-S03-B-01 — View seeded sites for John Smith
- **User**: Tier 1 owner
- **Surface**: Web — Customer detail → Sites tab
- **PRD Ref**: §3.3 Multi-Site Management
- **Status**: ☐

**Steps:**
1. Open customer `John Smith`
2. Navigate to the Sites tab

**Expected Result:**
- `Smith Residence` site displayed: 123 Main St, Brooklyn NY 11201
- Site shows lifecycle status `active`

**Notes:** _______________

---

##### P1-S03-B-02 — Add second site to existing customer
- **User**: Tier 1 owner
- **Surface**: Web — Customer detail → Sites
- **PRD Ref**: §3.3 Multi-Site Management
- **Status**: ☐

**Steps:**
1. Open `John Smith` → Sites tab → click **Add site**
2. Enter: Site name `Smith Vacation Property`, address `55 Ocean Ave, Long Beach NY 11561`
3. Save

**Expected Result:**
- Second site created and linked to John Smith
- Both sites appear in the customer's sites list
- Each site is selectable independently for job/quote creation

**Notes:** _______________

---

#### P1-S03-C: Site Access Details

##### P1-S03-C-01 — Add gate code, access instructions, hazard notes
- **User**: Tier 1 owner
- **Surface**: Web — Site detail
- **PRD Ref**: §3.3 Site-Specific Access Details
- **Status**: ☐

**Steps:**
1. Open `Smith Residence` site → click **Edit**
2. Enter: Gate code `#4521`, Access instructions `Park on the side street, entrance through back gate`, Hazard notes `Dog on premises — ring bell before entering`
3. Save

**Expected Result:**
- Structured access fields saved as discrete columns (not generic notes)
- DB check: `SELECT gate_code, access_instructions, hazard_notes FROM site WHERE id = <id>` → values present
- Voice AI should read these fields when tech starts a job at this site

**Notes:** _______________

---

#### P1-S03-D: Tenant vs. Property Manager Billing

##### P1-S03-D-01 — Commercial site with separate billing contact
- **User**: Tier 1 owner
- **Surface**: Web — Customer / Site / Contacts
- **PRD Ref**: §3.3 Tenant vs. Property Manager Billing
- **Status**: ☐

**Steps:**
1. Open `Apex Commercial LLC` → Sites → `Apex HQ` (Chicago IL)
2. Add a primary site contact: `Jane Property Manager, jane@apex.example.com`
3. Add a separate billing contact: `Accounts Payable, ap@apexcorp.example.com, 312-555-0100`
4. Create a quote → convert to invoice → verify invoice billing address

**Expected Result:**
- Both contacts visible on the site with distinct roles (primary vs. billing)
- Invoice uses billing contact details for the "bill to" address
- Quote/invoice does not confuse the two contact roles

**Notes:** _______________

---

---

### P1-S04 — Sales & Quoting

> **Setup**: Seed scripts run (5 customers, 5 pricebook items, 1 draft quote seeded). Log in as owner (`dev@pilot.local`).

---

#### P1-S04-A: Quote Creation (Touch)

##### P1-S04-A-01 — Open and inspect seeded draft quote
- **User**: Tier 1 owner
- **Surface**: Web — Quotes
- **PRD Ref**: §3.10 Sales & Quoting
- **Status**: ☐

**Steps:**
1. Navigate to `Quotes`
2. Open the seeded draft quote (John Smith / Smith Residence, $240)
3. Inspect line items

**Expected Result:**
- Quote detail shows: Customer `John Smith`, Site `Smith Residence`, Status `draft`
- 2 line items: Standard Outlet Installation ($150 × 1), 15A Circuit Breaker ($18 × 5 = $90)
- Subtotal $240, tax shown if tax jurisdiction configured
- Presentation style visible (likely `line_itemed` for draft)

**Notes:** _______________

---

##### P1-S04-A-02 — Create new quote (touch, web)
- **User**: Tier 1 owner
- **Surface**: Web — Quotes → New Quote
- **PRD Ref**: §3.10 Voice-Command Quote Creation (touch fallback)
- **Status**: ☐

**Steps:**
1. Navigate to `Quotes` → click **New Quote**
2. Select customer: `Mary Johnson`, site: her seeded site (Austin TX)
3. Set presentation style: `clean` (single all-in price)
4. Add line item: select `200A Panel Upgrade` from pricebook → set quantity 1
5. Add line item: select `EMT Conduit` → set quantity 50 ft
6. Set quote expiration: 30 days from today
7. Click **Save as draft**

**Expected Result:**
- Quote created in `draft` status with correct customer/site/items
- Subtotal calculated: $1,800 + ($3.50 × 50 = $175) = $1,975 + markup
- Expiration date stored on quote record
- `presentation_style = 'clean'` saved on the immutable version record

**Notes:** _______________

---

#### P1-S04-B: Line Item Management (3 Presentation Styles)

##### P1-S04-B-01 — Switch presentation styles and verify customer-facing rendering
- **User**: Tier 1 owner
- **Surface**: Web — Quote detail
- **PRD Ref**: §3.10 Three Quote Presentation Styles
- **Status**: ☐

**Steps:**
1. On the quote from A-02, change presentation style to `line_itemed`
2. Generate the public quote link (P1-S04-H) → open in incognito as if you were the customer
3. Verify line items are fully itemized
4. Change style to `hybrid` → re-open the public link

**Expected Result:**
- `clean`: customer sees single all-in price with optional summary lines — no individual line item breakdown
- `line_itemed`: full itemization with quantities, unit prices, line subtotals
- `hybrid`: grouped sections with subtotals per section
- Style change creates a new immutable version on the quote

**Notes:** _______________

---

##### P1-S04-B-02 — Internal-only line item hidden from customer view
- **User**: Tier 1 owner
- **Surface**: Web — Quote detail + Public quote link
- **PRD Ref**: §3.10 Quote Line Item Visibility & Hierarchy
- **Status**: ☐

**Steps:**
1. On any draft quote, add a new line item → uncheck `Visible to customer` (internal-only)
2. Enter internal note: `Labor burden — do not show customer`
3. Save → generate public quote link → open in incognito

**Expected Result:**
- Internal-only line item NOT visible on the public customer-facing quote
- Internal item IS visible in the owner's Pilot quote detail view
- `quote_line.is_visible_to_customer = false` confirmed in DB

**Notes:** _______________

---

#### P1-S04-C: Real-Time Material Pricing & Snapshots

*(See P1-S02-E-01 for price change snapshot immutability. This sub-section validates price pull from pricebook at quote creation.)*

##### P1-S04-C-01 — Quote line items pull live price from pricebook at creation
- **User**: Tier 1 owner
- **Surface**: Web — Quote creation
- **PRD Ref**: §3.10 Real-Time Material Pricing
- **Status**: ☐

**Steps:**
1. Create a new quote → add line item `15A Circuit Breaker` from pricebook search
2. Verify the price shown is the current pricebook price ($18.00)
3. Verify the pre-sale margin is shown (selling price vs. cost basis)

**Expected Result:**
- Line item auto-populates with current catalog price ($18.00)
- Margin/cost visibility shown on the quote detail (selling price vs. internal cost)
- Price is snapshotted on the `quote_line` record at creation — not dynamically re-fetched

**Notes:** _______________

---

#### P1-S04-D: Quote Templates

##### P1-S04-D-01 — Save quote as template
- **User**: Tier 1 owner
- **Surface**: Web — Quote detail
- **PRD Ref**: §3.10 Quote Template System
- **Status**: ☐

**Steps:**
1. Open a quote with multiple line items
2. Click **Save as template** → name it `Standard Outlet Package`
3. Navigate to `Catalog > Quote Templates`

**Expected Result:**
- Template appears in the tenant templates list
- Template preserves line items, presentation style, and metadata
- Creating a new quote from the template pre-fills those items

**Notes:** _______________

---

#### P1-S04-E: Quote Approval Workflow

##### P1-S04-E-01 — Tech submits quote for owner approval
- **User**: Tier 1 `tech@pilot.local` (technician role) + owner
- **Surface**: Web + Mobile — Quotes
- **PRD Ref**: §3.10 Quote Approval Workflow
- **Prerequisite**: Tenant setting `require_approval_for_tech_quotes = ON` (set in Settings)
- **Status**: ☐

**Steps:**
1. Log in as technician → create a new quote for any customer
2. Click **Submit for Approval** → confirm
3. Log in as owner → navigate to `Quotes > Pending Approval` (or Approvals queue)
4. Owner opens the submitted quote

**Expected Result:**
- Quote status transitions to `pending_approval`
- Tech sees quote as "Submitted for approval" with pending badge
- Owner sees the quote in the pending queue with tech's details
- Owner has **Approve**, **Reject**, and **Edit and Approve** action buttons

**Notes:** _______________

---

##### P1-S04-E-02 — Owner approves quote with track-changes diff
- **User**: Tier 1 owner (reviewing tech's submitted quote from E-01)
- **Surface**: Web — Quote approval review
- **PRD Ref**: §3.10 Track-Changes Review; §4.1 Track-Changes Diff Vocabulary
- **Status**: ☐

**Steps:**
1. As owner, open pending quote → click **Edit and Approve**
2. Modify a line item price (e.g., increase quantity on one item)
3. Add an approval comment on a specific line item
4. Click **Approve**

**Expected Result:**
- Track-changes diff visible: modified fields in amber, new fields in green, removed in red
- Owner edits shown as pending changes until approval
- After approval, quote status = `approved`
- Approval comment stored on the version record
- Tech notified of approval

**Notes:** _______________

---

##### P1-S04-E-03 — Owner rejects quote with comment
- **User**: Tier 1 owner
- **Surface**: Web — Quote approval
- **PRD Ref**: §3.10 Quote Approval Workflow
- **Status**: ☐

**Steps:**
1. As owner, open a pending quote → click **Reject**
2. Enter rejection comment: `Pricing too aggressive — reduce labor by 15%`
3. Confirm rejection

**Expected Result:**
- Quote status transitions to `rejected`
- Rejection comment visible to tech on the quote detail
- Tech notified of rejection with comment in notification body

**Notes:** _______________

---

#### P1-S04-F: Time-Limited Discounts with Margin Cap

##### P1-S04-F-01 — Apply time-limited discount within cap
- **User**: Tier 1 owner
- **Surface**: Web — Quote detail
- **PRD Ref**: §3.10 Time-Limited Discounts with Margin Cap
- **Status**: ☐

**Steps:**
1. Open any approved or draft quote → click **Apply Discount**
2. Enter: 10% discount, valid for 7 days
3. Save and preview the quote total

**Expected Result:**
- Discount applied and reflected in the quote total
- Expiration date shown on the public quote link
- Discount within the `max_discount_pct_owner` cap (default 15%) — no warning needed

**Notes:** _______________

---

##### P1-S04-F-02 — Discount exceeding margin cap triggers warning
- **User**: Tier 1 owner
- **Surface**: Web — Quote detail
- **PRD Ref**: §3.10 Time-Limited Discounts with Margin Cap
- **Status**: ☐

**Steps:**
1. Attempt to apply a 20% discount (exceeds default cap of 15%)
2. Observe the system response

**Expected Result:**
- Warning displayed: discount exceeds `max_discount_pct_owner` (15%)
- Explicit override confirmation required to proceed
- Discount is NOT silently applied — user must actively override

**Notes:** _______________

---

#### P1-S04-G: Public Quote Link & Customer Acceptance

##### P1-S04-G-01 — Generate and open public quote link
- **User**: Tier 1 owner (generates link); customer (opens link — open in incognito)
- **Surface**: Web — Quote detail + Public quote page
- **PRD Ref**: §3.10 Public Quote Link with 90-Day Signed URL
- **Status**: ☐

**Steps:**
1. On an `approved` quote, click **Send to customer** (or **Generate link**)
2. Copy the generated signed URL
3. Open the URL in an incognito browser window (simulating a customer with no Pilot account)
4. Inspect the customer-facing quote page

**Expected Result:**
- Public page accessible without Pilot login
- Quote displays with tenant branding (business name, if branding configured)
- Line items shown per the chosen presentation style
- "Accept" and "Decline" action buttons visible
- "Powered by Pilot for Trades" subtle footer

**Notes:** _______________

---

##### P1-S04-G-02 — Customer accepts quote with optional comment
- **User**: Simulated customer (incognito browser)
- **Surface**: Public quote page
- **PRD Ref**: §3.10 Customer Quote Acceptance with Optional Comment
- **Status**: ☐

**Steps:**
1. On the public quote page (from G-01) → click **Accept Quote**
2. Enter acceptance comment: `Let's get started ASAP — when can you begin?`
3. Confirm acceptance

**Expected Result:**
- Quote status transitions to `accepted`
- Acceptance comment stored: `quote.customer_acceptance_comment = 'Let's get started ASAP...'`
- Customer sees confirmation state (not the action buttons again — no double-action possible)
- Owner notified of acceptance (check `notification_outbox` or notification bell)
- Revisiting the public link shows accepted state, not action buttons

**Notes:** _______________

---

##### P1-S04-G-03 — Customer declines quote with structured reason
- **User**: Simulated customer (incognito browser, separate quote)
- **Surface**: Public quote page
- **PRD Ref**: §3.10 Customer Quote Decline with Reason + Comment
- **Status**: ☐

**Steps:**
1. Open a different public quote link (approve another quote first)
2. Click **Decline** → select reason: `Pricing` → enter comment: `Got a lower bid from another contractor`
3. Confirm decline

**Expected Result:**
- Quote status = `rejected` (from customer's action)
- `quote.customer_decline_reason = 'pricing'`, `quote.customer_decline_comment = 'Got a lower bid...'`
- Owner notified with decline reason + comment in notification body

**Notes:** _______________

---

#### P1-S04-H: Quote → Job Auto-Conversion

##### P1-S04-H-01 — Accepted quote converts to job
- **User**: Tier 1 owner
- **Surface**: Web — Quote detail (accepted quote from G-02)
- **PRD Ref**: §3.10 Auto-Conversion: Accepted Quote → Job
- **Status**: ☐

**Steps:**
1. Open the accepted quote
2. Click **Convert to Job** (or this may happen automatically on acceptance — verify behavior)
3. Navigate to Jobs list

**Expected Result:**
- New job record created linked to the accepted quote version
- Job carries all relevant quote data (customer, site, line items)
- Quote status = `converted`
- Job status = `draft` or `scheduled` (depending on app configuration)

**Notes:** _______________

---

#### P1-S04-I: Quote Expiration

##### P1-S04-I-01 — Manually trigger quote expiration (DB date manipulation)
- **User**: Tier 1 owner (DB access)
- **Surface**: DB + Web — Quotes list
- **PRD Ref**: §3.10 Quote Expiration Auto-Transition
- **Status**: ☐

**Steps:**
1. Find a `sent` quote → DB: `UPDATE quote SET expires_at = NOW() - INTERVAL '1 day' WHERE id = <id>`
2. Manually trigger the expiration Celery task: `docker exec pilot_celery_worker celery -A tasks call tasks.quotes.expire_overdue_quotes`
3. Check the quote status in the UI

**Expected Result:**
- Quote status transitions to `expired`
- Expired quote no longer shows action buttons on the public link (shows "This quote has expired")
- Customer revisiting the expired public link sees the "contact tenant for fresh link" page

**Notes:** _______________

---

---

### P1-S05 — Field Operations & Jobs

> **Setup**: Seed scripts run (5 jobs seeded, including 1 in_progress and 1 scheduled). Log in as owner or tech as noted per test case. Mobile app required for some sub-sections.

---

#### P1-S05-A: Job Assignment & Tech Assignment

##### P1-S05-A-01 — View seeded jobs
- **User**: Tier 1 owner
- **Surface**: Web — Jobs list
- **PRD Ref**: §3.4 Field Operations & Jobs
- **Status**: ☐

**Steps:**
1. Navigate to `Jobs`
2. Verify 5 seeded jobs with correct statuses

**Expected Result:**
- 5 jobs visible: Scheduled (tomorrow 9am), In Progress (today 8am), Completed (yesterday), Completed (3 days ago), Draft
- Each job shows title, status badge, assigned tech (where assigned)
- Jobs scoped to test tenant

**Notes:** _______________

---

##### P1-S05-A-02 — Assign tech to unassigned job
- **User**: Tier 1 owner
- **Surface**: Web — Job detail
- **PRD Ref**: §3.4 Basic Job Assignment
- **Status**: ☐

**Steps:**
1. Open `Completed - Awaiting Invoice` job (no tech assigned)
2. Click **Assign tech** → select `tech@pilot.local`
3. Save

**Expected Result:**
- `job_tech_assignment` row created linking job to technician
- Job detail shows technician name and avatar
- Technician notified of assignment (check `notification_outbox`)

**Notes:** _______________

---

##### P1-S05-A-03 — Double-assignment guard (same tech, same job)
- **User**: Tier 1 owner
- **Surface**: API
- **PRD Ref**: §3.4 Basic Job Assignment (UNIQUE constraint)
- **Status**: ☐

**Steps:**
1. Attempt to assign the same tech to the same job twice via API: `POST /api/v1/jobs/<id>/assign-tech/test` with same `tech_user_id` twice

**Expected Result:**
- Second assignment attempt returns an error (unique constraint violation)
- Job is not double-assigned

**Notes:** _______________

---

#### P1-S05-B: Clock In / Clock Out

##### P1-S05-B-01 — Tech clocks in to a job (mobile)
- **User**: Tier 1 `tech@pilot.local` on mobile
- **Surface**: Mobile — Today tab → Job detail
- **PRD Ref**: §3.4 Basic Time Tracking
- **Status**: ☐

**Steps:**
1. Log in as tech on mobile
2. Navigate to Today tab → find the `In Progress - Panel Upgrade` job
3. Tap **Clock In**

**Expected Result:**
- Clock-in recorded with current timestamp
- `time_entry.clock_in_at` = now
- `time_entry.hourly_rate_cents` = frozen snapshot of tech's current billing rate (from labor_rate_version)
- Job shows "Currently clocked in" indicator

**Notes:** _______________

---

##### P1-S05-B-02 — Tech clocks out with ETC
- **User**: Tier 1 `tech@pilot.local` on mobile (clocked in from B-01)
- **Surface**: Mobile — Job detail
- **PRD Ref**: §3.4 Basic Time Tracking + §3.4 ETC Capture System
- **Status**: ☐

**Steps:**
1. Tap **Clock Out**
2. UI prompts: "How many more hours to complete this job?" → enter `3.5`
3. Confirm clock-out

**Expected Result:**
- `time_entry.clock_out_at` = now; `time_entry.etc_hours_remaining = 3.5`
- Total elapsed time calculated correctly
- Job's live profitability view updates with new actuals + ETC projection

**Notes:** _______________

---

#### P1-S05-C: ETC Variance Notifications

##### P1-S05-C-01 — ETC override exceeds variance threshold → note required
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Clock out dialog
- **PRD Ref**: §3.4 ETC Capture System (etc_variance_note_required_pct = 10%)
- **Status**: ☐

**Steps:**
1. Clock in again → clock out on a job where the new ETC would increase total projected hours by >10% from quote
2. Observe if a note is required at clock-out

**Expected Result:**
- System requires a note before accepting the ETC when variance exceeds 10% threshold
- ETC is not saved without the required note

**Notes:** _______________

---

#### P1-S05-D: Expense Logging

##### P1-S05-D-01 — Log ad-hoc material expense (mobile)
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Job detail → Expenses
- **PRD Ref**: §3.4 Ad-Hoc Expense Logging
- **Status**: ☐

**Steps:**
1. On an active job, tap **Add Expense**
2. Enter: category `materials`, description `15A breakers from Home Depot`, amount `$45.99`, markup `20%`
3. Save

**Expected Result:**
- Expense created and linked to the job
- Job cost totals updated asynchronously (Celery worker updates actuals)
- `job_expense.cost_cents = 4599`, `markup_pct = 20`, `category = 'materials'`
- Live profitability view reflects the new expense

**Notes:** _______________

---

##### P1-S05-D-02 — Receipt photo upload triggers OCR auto-fill
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Add Expense with photo
- **PRD Ref**: §3.4 Receipt OCR Automation
- **Status**: ☐

**Steps:**
1. Tap **Add Expense** → tap **Take photo of receipt** (or select from camera roll)
2. Upload a receipt image (use any store receipt photo)
3. Wait for OCR processing

**Expected Result:**
- OCR pipeline runs asynchronously (AWS Textract or GPT-4V)
- `cost_cents` field auto-populated from receipt total
- Processing state visible while OCR runs ("Reading receipt...")
- Tech can override the auto-filled amount if incorrect

**Notes:** _______________

---

#### P1-S05-E: Photo Documentation

##### P1-S05-E-01 — Upload before/after photos (mobile)
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Job detail → Photos
- **PRD Ref**: §3.4 Photo Documentation
- **Status**: ☐

**Steps:**
1. On an active job, navigate to Photos tab
2. Tap **Add photo** → select 2 photos from camera roll (or take live photos)
3. Wait for upload (WiFi preferred — check `photo_upload_wifi_only` tenant setting)

**Expected Result:**
- Photos upload successfully via S3 multipart pipeline
- Photos appear in the job's photo gallery
- `job_photo` rows created in DB with S3 object keys
- Photos persist after app restart (synced to server, not just local)

**Notes:** _______________

---

#### P1-S05-F: Change Orders

##### P1-S05-F-01 — Tech creates change order on active job (mobile)
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Job detail → Change Orders
- **PRD Ref**: §3.4 On-Site Change Order Management
- **Status**: ☐

**Steps:**
1. On the `In Progress - Panel Upgrade` job, tap **Add Change Order**
2. Enter: description `Additional 20A circuit for garage`, cost estimate `$350`
3. Save

**Expected Result:**
- Change order created and linked to the active job and its quote version
- Job total recalculated to include the change order
- Change order visible on both mobile (tech view) and web (owner view)

**Notes:** _______________

---

#### P1-S05-G: LOTO Safety Confirmation

##### P1-S05-G-01 — LOTO confirmation (tenant-configurable — test with setting ON)
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Job detail → LOTO
- **PRD Ref**: §3.4 LOTO Safety Confirmation (tenant-configurable via `loto_confirmation_required`)
- **Status**: ☐

**Steps:**
1. DB: set tenant setting `loto_confirmation_required = true` for test tenant
2. On mobile, attempt to clock out of an active job without confirming LOTO
3. Observe gate behavior
4. Confirm LOTO via the LOTO confirmation button
5. Attempt clock-out again

**Expected Result:**
- With `loto_confirmation_required = true`, clock-out (and job-completion voice commands) are BLOCKED until LOTO confirmed
- LOTO confirmation saves with both `client_capture_at` and `server_received_at` timestamps
- After LOTO confirmed, clock-out proceeds normally
- `loto_confirmation` row created in DB

**Notes:** _______________

---

##### P1-S05-G-02 — LOTO optional audit action when setting OFF
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Job detail → LOTO
- **PRD Ref**: §3.4 LOTO (FIND-063 — not globally mandatory)
- **Status**: ☐

**Steps:**
1. DB: set tenant setting `loto_confirmation_required = false` (or confirm default is false)
2. Clock out of a job without confirming LOTO — verify clock-out is NOT blocked
3. Optionally confirm LOTO anyway — verify confirmation is still recorded

**Expected Result:**
- Clock-out succeeds without LOTO when setting is OFF
- LOTO confirmation is still available as an optional action (for the paper trail)
- `loto_confirmation` row created if confirmed, absent if not confirmed

**Notes:** _______________

---

#### P1-S05-H: Live Job Profitability View

##### P1-S05-H-01 — Verify live profitability view after time entries and expenses
- **User**: Tier 1 owner
- **Surface**: Web — Job detail → Profitability tab
- **PRD Ref**: §3.4 Live Job Profitability View
- **Status**: ☐

**Steps:**
1. Open a job with at least one time entry (from B-01) and one expense (from D-01)
2. Navigate to the job's profitability view

**Expected Result:**
- Profitability view shows: Actual labor cost, Actual material cost, Projected cost (actuals + ETC × rate), Quoted budget, Projected margin %
- Jobs below `margin_target_pct` (default 20%) shown with visual indicator
- Numbers updated after Celery worker runs (may have short delay)

**Notes:** _______________

---

#### P1-S05-I: GPS-Verified Check-In

##### P1-S05-I-01 — Clock-in captures GPS coordinates (physical device)
- **User**: Tier 1 tech on physical iOS/Android device
- **Surface**: Mobile — Clock In
- **PRD Ref**: §3.4 GPS-Verified Check-Ins
- **Status**: ☐ *(Requires physical device — simulator uses mock coordinates)*

**Steps:**
1. On physical device, allow location permissions for the Pilot app
2. Clock in to a job → check DB after clock-in

**Expected Result:**
- `time_entry.gps_latitude`, `gps_longitude`, `gps_accuracy_meters` populated at clock-in
- Location capture happens silently (no user-facing prompt beyond the clock-in action)

**Notes:** _______________

---

---

### P1-S06 — Scheduling & Dispatch

> **Setup**: Seed scripts run (5 jobs with schedules seeded). Log in as owner. Web browser required for dispatch board; mobile for today view.

---

#### P1-S06-A: Dispatch Board

##### P1-S06-A-01 — View dispatch board with seeded jobs
- **User**: Tier 1 owner
- **Surface**: Web — Dispatch Board
- **PRD Ref**: §3.14 Scheduling & Dispatch
- **Status**: ☐

**Steps:**
1. Navigate to the Dispatch Board
2. Observe the tech × time grid layout

**Expected Result:**
- Grid shows tech columns × time rows
- `Scheduled - Outlet Installation` job card placed at tomorrow 9am in the primary tech's column
- `In Progress - Panel Upgrade` job card at today 8am
- Unscheduled jobs (Draft - Estimate Only) visible in the "Unassigned" column
- Each tech column uses their assigned color from the 12-hue palette

**Notes:** _______________

---

##### P1-S06-A-02 — Drag-to-reschedule a job on the dispatch board
- **User**: Tier 1 owner
- **Surface**: Web — Dispatch Board
- **PRD Ref**: §3.14 Dispatch Board with drag-to-reschedule
- **Status**: ☐

**Steps:**
1. On the dispatch board, drag the `Scheduled - Outlet Installation` job card to a different time slot (e.g., 11am instead of 9am)
2. Release to confirm the new time

**Expected Result:**
- Job reschedules to the new time slot
- `job.scheduled_start_at` updated in DB
- Tech notified of schedule change (check `notification_outbox`)
- Audit log entry created for the schedule change

**Notes:** _______________

---

##### P1-S06-A-03 — Drag-to-reassign to different tech
- **User**: Tier 1 owner
- **Surface**: Web — Dispatch Board
- **PRD Ref**: §3.14 Dispatch Board — drag-to-reassign
- **Status**: ☐

**Steps:**
1. Drag a job card from the primary tech's column to the office staff's column (or create a second tech user first)
2. Confirm reassignment

**Expected Result:**
- `job_tech_assignment` updated to reflect the new tech
- Old tech loses the job from their column; new tech's column shows the job card
- Both old and new tech notified of the change
- Self-assignment suppresses notification (owner reassigning own job)

**Notes:** _______________

---

##### P1-S06-A-04 — Month Calendar Grid View
- **User**: Tier 1 owner
- **Surface**: Web — Dispatch Board → Month tab
- **PRD Ref**: §3.14 Scheduling & Dispatch
- **Status**: ☐
- **Prerequisite**: BETA-B7 complete

**Steps:**
1. Navigate to the Dispatch Board
2. Click the **Month** tab in the toolbar
3. Observe the calendar grid
4. Click on a day cell that has a seeded job chip

**Expected Result:**
- Month tab renders a 7-column × 5-row calendar grid (Sun–Sat header row)
- "Month view coming soon" text is **absent** from the page
- Today's date is highlighted with a brand-color circle around the date number
- Job chips appear on the correct date cells for seeded jobs
- Cells with more than 2 jobs show a `+N more` chip
- Padding cells (before the first day of the range) are greyed out and non-interactive
- Clicking a day cell with a job navigates to the Day view for that date (tab switches to "Day", grid shows the clicked date)
- Prev/Next navigation advances the calendar by 30 days

**Notes:** _______________

---

#### P1-S06-B: Live Dispatch Board Updates (SSE)

##### P1-S06-B-01 — Verify SSE live update when second browser modifies a job
- **User**: Tier 1 owner (two browsers)
- **Surface**: Web — Dispatch Board (both browsers open simultaneously)
- **PRD Ref**: §3.14 Dispatch Board — Server-Sent Events
- **Status**: ☐

**Steps:**
1. Open the dispatch board in Browser A
2. In Browser B, reschedule a job (from A-02)
3. Without refreshing Browser A, observe the dispatch board

**Expected Result:**
- Browser A automatically updates to show the new job time without a page refresh
- SSE event delivers within 1–2 seconds of the change in Browser B
- No error in browser console related to SSE connection

**Notes:** _______________

---

#### P1-S06-C: Four-Class Conflict Detection

##### P1-S06-C-01 — Overlap conflict: two jobs for same tech at same time
- **User**: Tier 1 owner
- **Surface**: Web — Dispatch Board
- **PRD Ref**: §3.14 Four-Class Dispatch Conflict Detection
- **Status**: ☐

**Steps:**
1. Schedule a second job for the primary tech at the same time as `Scheduled - Outlet Installation` (tomorrow 9am–1pm)
2. Observe the dispatch board

**Expected Result:**
- Conflict detected and flagged as `overlap` severity
- Both job cards show an overlap indicator (distinct visual treatment)
- Owner can still proceed (overlap is a warning, not a hard block) — or blocked if logic enforces it

**Notes:** _______________

---

##### P1-S06-C-02 — Availability conflict: job scheduled during tech PTO block
- **User**: Tier 1 owner
- **Surface**: Web — Dispatch Board
- **PRD Ref**: §3.14 Four-Class Dispatch Conflict Detection (availability class)
- **Status**: ☐

**Steps:**
1. Recall that the seed data includes a PTO block: Technician has PTO next Friday 8am–5pm
2. Attempt to schedule a job for the primary tech on next Friday during the PTO block

**Expected Result:**
- `availability` conflict detected and flagged with distinct visual treatment from overlap
- Conflict indicator on the job card
- Voice-commanded scheduling blocked for blocking-severity conflicts

**Notes:** _______________

---

#### P1-S06-D: Tech Availability Windows & PTO

##### P1-S06-D-01 — View and edit tech working hours
- **User**: Tier 1 owner
- **Surface**: Web — Settings or Tech profile → Availability
- **PRD Ref**: §3.14 Tech Availability Windows
- **Status**: ☐

**Steps:**
1. Navigate to the tech's profile/availability settings
2. View recurring working hours
3. Add a one-off unavailable block: next Monday 1pm–3pm (dentist appointment)

**Expected Result:**
- Availability block saved
- Scheduling a job for the tech during that block triggers an `availability` conflict on the dispatch board

**Notes:** _______________

---

#### P1-S06-E: Route Sequencing + Drive-Time

##### P1-S06-E-01 — Manual route sequencing with drive-time assist
- **User**: Tier 1 owner
- **Surface**: Web — Dispatch Board / Route view
- **PRD Ref**: §3.14 Manual Route Sequencing with Drive-Time Assist
- **Status**: ☐

**Steps:**
1. Ensure the primary tech has at least 2 jobs scheduled for the same day (create a second job for today if needed)
2. In the dispatch board's route view, reorder the day's stops manually
3. Observe drive time calculations between stops

**Expected Result:**
- Drive times displayed between consecutive stops after reorder
- Drive time fetched from distance-matrix API (Google Maps) and cached
- Travel conflicts (`travel` class) flagged if drive time is insufficient between consecutive jobs

**Notes:** _______________

---

#### P1-S06-F: Today's Schedule (Mobile Tech View)

##### P1-S06-F-01 — Tech views today's assigned jobs on mobile
- **User**: Tier 1 `tech@pilot.local` on mobile
- **Surface**: Mobile — Today tab
- **PRD Ref**: §3.14 Today's Schedule on Mobile
- **Status**: ☐

**Steps:**
1. Log in as tech on mobile → navigate to Today tab
2. Observe jobs listed for today

**Expected Result:**
- Today tab shows `In Progress - Panel Upgrade` (today 8am–5pm)
- Jobs ordered by `scheduled_start_at`
- Each job shows site address, customer name, and drive time to next stop
- Jobs for other days NOT shown in the today view

**Notes:** _______________

---

#### P1-S06-G: Calendar Sync (Google OAuth)

##### P1-S06-G-01 — Connect Google Calendar via OAuth (requires ngrok)
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Integrations > Calendar`
- **PRD Ref**: §3.14 OAuth 2.0 Calendar Connection Flow
- **Status**: ⏭️ *(Requires ngrok or registered OAuth callback URL — see Appendix C)*

**Steps (when ngrok available):**
1. Start ngrok: `ngrok http 8000`
2. Register the ngrok HTTPS URL as an OAuth callback in Google Cloud Console
3. Navigate to `Settings > Integrations > Calendar` → click **Connect Google Calendar**
4. Complete OAuth flow in the Google consent screen
5. Return to Pilot — verify connection status

**Expected Result:**
- OAuth tokens stored (encrypted via Fernet) in `integration_credential`
- Connection status shows "Connected" with the tenant's Google Calendar email
- `app_service` record updated with `status = 'connected'`

**Notes:** _______________

---

#### P1-S06-H: Calendar Conflict Detection & Resolution

##### P1-S06-H-01 — Manually seed a calendar conflict and resolve via web UI
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Integrations > Calendar > Conflicts`
- **PRD Ref**: §3.14 Calendar Conflict Resolution Web UI
- **Prerequisite**: Calendar connected (G-01), or manually insert conflict record in DB
- **Status**: ☐

**Steps (DB method for local testing):**
1. Insert a test conflict record directly:
   ```sql
   INSERT INTO integration_sync_conflict (
     tenant_id, entity_type, conflict_type, pilot_snapshot, external_snapshot, base_snapshot,
     field_diffs, status, created_at, updated_at
   ) VALUES (
     '00000000-0000-0000-0000-000000000001', 'calendar_event', 'modified_modified',
     '{"title":"Panel Upgrade","start":"2026-06-10T09:00:00Z"}',
     '{"title":"Panel Upgrade - Revised","start":"2026-06-10T10:00:00Z"}',
     '{"title":"Panel Upgrade","start":"2026-06-10T09:00:00Z"}',
     '[{"field":"start","pilot_value":"09:00","external_value":"10:00"}]',
     'open', NOW(), NOW()
   )
   ```
2. Navigate to `Settings > Integrations > Calendar > Conflicts`
3. Open the conflict → review the side-by-side diff
4. Click **Use Pilot version**

**Expected Result:**
- Conflict resolution UI shows two-column diff: Pilot (left) vs. Google Calendar (right)
- Track-changes vocabulary: amber for modified fields, green for added, red for removed
- Resolving conflict: `conflict.status = 'resolved'`, resolution logged with actor identity
- Audit log entry created

**Notes:** _______________

---

#### P1-S06-I: Pre-Commit Staleness Check (409-and-Refresh)

##### P1-S06-I-01 — Concurrent dispatch edit triggers 409 staleness response
- **User**: Tier 1 owner (two browsers)
- **Surface**: Web — Dispatch Board
- **PRD Ref**: §3.8 Pre-Commit Staleness Check Pattern; §16.4
- **Status**: ☐

**Steps:**
1. Open a job for editing in Browser A (note the `updated_at` timestamp)
2. In Browser B, edit and save the same job (changes `updated_at`)
3. Back in Browser A, attempt to save the edit (stale `updated_at`)

**Expected Result:**
- API returns `409 Conflict` with refreshed payload (updated state from Browser B's change)
- Browser A displays "This has been updated" banner with refreshed data
- User can review the new state and re-decide
- No silent data loss — Browser A's edit is NOT applied on top of stale data

**Notes:** _______________

---

---

### P1-S07 — Invoicing & Billing

> **Setup**: At least one accepted quote (from P1-S04-G-02) needs to exist, or create one now. Tax jurisdiction must be configured (will be tested via 412 gate in S07-B). Log in as owner.

---

#### P1-S07-A: Quote/Job → Invoice Conversion

##### P1-S07-A-01 — Convert accepted quote to invoice (with tax setup gate)
- **User**: Tier 1 owner
- **Surface**: Web — Quote detail (accepted quote)
- **PRD Ref**: §3.6 One-Click Quote/Job → Invoice Conversion; §4.7.6 Tax Setup JIT
- **Status**: ☐

**Steps:**
1. Open the accepted quote (from P1-S04-G-02 or create a new accepted quote)
2. Click **Convert to Invoice**
3. If tax is not configured, observe the 412 gate sub-flow
4. Configure tax if prompted (ZIP auto-detection, confirm rate)
5. Complete the conversion

**Expected Result:**
- If no tax configured: 412 (Precondition Required) response → tax setup sub-flow appears
- After tax setup: invoice created with all quote line items + tax components
- Invoice status = `issued`
- All line items carried over with pricing preserved (polymorphic source references)

**Notes:** _______________

---

##### P1-S07-A-02 — Convert completed job to invoice
- **User**: Tier 1 owner
- **Surface**: Web — Job detail (completed job)
- **PRD Ref**: §3.6 One-Click Quote/Job → Invoice Conversion
- **Status**: ☐

**Steps:**
1. Open a completed job (seeded: `Completed - Awaiting Invoice`)
2. Click **Create Invoice**
3. Verify all job data (time entries, expenses, change orders) is included

**Expected Result:**
- Invoice created from the completed job
- Labor line items from time entries, material line items from expenses
- Change orders included as separate line items
- Invoice total reflects actuals (not just the original quote)

**Notes:** _______________

---

#### P1-S07-B: Tax Setup JIT Sub-Flow (412 Gate)

##### P1-S07-B-01 — Trigger tax setup sub-flow on first invoice attempt
- **User**: Tier 1 owner (fresh tenant with no tax configured)
- **Surface**: Web — Invoice creation
- **PRD Ref**: §4.7.6 Tax Setup Just-In-Time Sub-Flow
- **Status**: ☐

**Steps:**
1. Ensure no tax jurisdiction is configured for the test tenant (reset if needed)
2. Attempt to convert a quote to invoice
3. Observe the 412 sub-flow
4. Confirm the auto-detected jurisdiction (from ZIP captured at signup)
5. Complete tax setup → retry invoice creation

**Expected Result:**
- First invoice attempt returns 412 with tax setup sub-flow
- ZIP code from signup auto-populates the tax jurisdiction suggestion
- After configuring tax, subsequent invoice creation works without the gate

**Notes:** _______________

---

#### P1-S07-C: Public Invoice Link & Stripe Payment

##### P1-S07-C-01 — Generate public invoice link and make test payment
- **User**: Tier 1 owner (generates link); simulated customer (incognito)
- **Surface**: Web — Invoice detail + Public invoice page
- **PRD Ref**: §3.6 Public Payment Links; §3.6 Stripe One-Time Payment
- **Status**: ☐

**Steps:**
1. Open a created invoice → click **Send to customer** (generates signed public URL)
2. Open the URL in incognito
3. On the public invoice page, click **Pay**
4. Enter Stripe test card: `4242 4242 4242 4242`, any future exp date, any CVC
5. Confirm payment

**Expected Result:**
- Public invoice page shows invoice details + tenant branding
- Stripe Elements renders the card form (PCI-compliant — no raw card data hits Pilot server)
- Payment succeeds → invoice status = `paid`, balance = $0
- Stripe webhook received and processed (Celery worker confirms payment)
- Customer sees payment confirmation page
- `payment.customer_payment_comment` optional field available

**Notes:** _______________

---

##### P1-S07-C-02 — Underpayment: partial amount, comment required
- **User**: Simulated customer (incognito, fresh invoice)
- **Surface**: Public invoice page
- **PRD Ref**: §3.6 Variance Payment Accounting Integrity
- **Status**: ☐

**Steps:**
1. On a fresh invoice public page, adjust the payment amount to be less than the invoice total (e.g., pay $100 on a $240 invoice)
2. Observe that a comment is required when amount differs from invoice total
3. Enter comment: `Paying 50% deposit per agreed terms` → submit payment

**Expected Result:**
- Comment required when payment amount differs from invoice total
- Payment recorded at $100; invoice shows remaining balance of $140
- `payment.amount_variance_cents` populated
- Invoice status stays `issued` (not `paid`) — partial balance remains
- `used_count` and `last_used_at` on the public link updated after POST `/pay` (not on passive GET)

**Notes:** _______________

---

#### P1-S07-D: AR Aging Dashboard

##### P1-S07-D-01 — View AR aging report with multiple invoice statuses
- **User**: Tier 1 owner
- **Surface**: Web — Invoices / Dashboard AR section
- **PRD Ref**: §3.6 AR Aging Dashboards
- **Status**: ☐

**Steps:**
1. Ensure at least 3 invoices exist: one `issued` (current), one overdue (manually set `due_date` to past), one `paid`
2. Navigate to the AR aging dashboard

**Expected Result:**
- AR aging buckets visible: Current (0–30 days), 30-day overdue, 60-day, 90-day+
- Correct invoices appear in each bucket
- Paid invoices NOT shown in the aging report (or shown in a separate "Paid" section)
- Partial indexes on invoice balance/status enable fast query (performance not verifiable locally, but query should return quickly)

**Notes:** _______________

---

#### P1-S07-E: Automated Dunning

##### P1-S07-E-01 — Trigger dunning task for overdue invoice
- **User**: Tier 1 owner + DB access
- **Surface**: DB + `notification_outbox`
- **PRD Ref**: §3.6 Automated Dunning (Overdue AR Reminders)
- **Status**: ☐

**Steps:**
1. Create an invoice → set `due_date` to 31 days ago via DB: `UPDATE invoice SET due_date = NOW() - INTERVAL '31 days' WHERE id = <id>`
2. Trigger the dunning Celery task: `docker exec pilot_celery_worker celery -A tasks call tasks.invoices.send_dunning_reminders`
3. Check `notification_outbox` for the outbound reminder

**Expected Result:**
- Dunning task enqueues an SMS or email reminder to the customer
- `notification_outbox` row created with correct recipient (customer) and template (`payment_reminder`)
- Reminder NOT sent for paid invoices (task filters correctly)

**Notes:** _______________

---

#### P1-S07-F: Customer-Facing Invoice Page Branding

##### P1-S07-F-01 — Configure tenant email branding and verify on public invoice page
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Communications > Email branding` + Public invoice page
- **PRD Ref**: §3.6 Customer-Facing Page Tenant Branding; §3.7 Tenant Email Branding
- **Status**: ☐

**Steps:**
1. Navigate to `Settings > Communications > Email branding`
2. Upload a logo, set brand color (e.g., `#003366`), enter signature line: `Tom's Electric — Licensed & Insured`
3. Save → click **Send test email to my address** to preview
4. Open a public invoice link

**Expected Result:**
- Email branding settings saved
- Public invoice page renders with uploaded logo, brand color, signature line
- "Powered by Pilot for Trades" small footer still present
- Test email received at owner's address with the configured branding

**Notes:** _______________

---

### P1-S08 — Tax Calculation

> **Setup**: Tax jurisdiction must be configured (done during P1-S07-B). At least one invoice with tax components needed. Log in as owner.

---

#### P1-S08-A: Multi-Jurisdiction Tax Components

##### P1-S08-A-01 — Invoice shows correct multi-component tax breakdown
- **User**: Tier 1 owner
- **Surface**: Web — Invoice detail
- **PRD Ref**: §3.12 Tax Calculation — Compound/Stacked Taxes
- **Status**: ☐

**Steps:**
1. Create a quote with a customer in `US-TX-HARRIS` jurisdiction (Mary Johnson, Austin TX → actually Harris County)
2. Convert to invoice
3. Inspect the invoice's tax breakdown

**Expected Result:**
- Multiple tax component rows generated: state (6.25%), city (1%), county (0.5%), special district — summing to the Harris County combined rate (8.25% from seeded data)
- Each component displayed as a separate line item on the invoice
- Total tax = sum of all components (IRS-compliant ceiling rounding at component level)

**Notes:** _______________

---

#### P1-S08-B: Material vs. Labor Taxability

##### P1-S08-B-01 — Labor line items not taxed; material line items taxed
- **User**: Tier 1 owner
- **Surface**: Web — Invoice detail (invoice with mixed line items)
- **PRD Ref**: §3.12 Material vs. Labor Taxability Rules
- **Status**: ☐

**Steps:**
1. Create an invoice with 2 line items: one labor (e.g., Standard Outlet Installation, taxability `labor`) and one material (15A Circuit Breaker, taxability `taxable`)
2. Inspect the tax calculation

**Expected Result:**
- Labor line item: $0 tax (taxability_code = `labor`)
- Material line item: tax calculated at the jurisdiction rate
- Tax components shown separately per taxable line item

**Notes:** _______________

---

#### P1-S08-C: Tax-Exempt Customer

##### P1-S08-C-01 — Tax-exempt customer generates zero-tax invoice
- **User**: Tier 1 owner
- **Surface**: Web — Customer settings + Invoice
- **PRD Ref**: §3.12 Tax-Exempt Customers
- **Status**: ☐

**Steps:**
1. Set a customer to tax-exempt: edit customer → set `taxability_code = 'exempt'`
2. Create an invoice for this customer with material line items
3. Inspect tax on the invoice

**Expected Result:**
- Tax calculation returns explicit zero-tax components (not null — explicit zeros logged for audit)
- Invoice shows $0.00 tax
- Tax components still written to DB with `amount_cents = 0` (immutable record of the calculation)

**Notes:** _______________

---

#### P1-S08-D: Historical Tax Snapshot Immutability

##### P1-S08-D-01 — Tax rate change does not affect existing invoices
- **User**: Tier 1 owner + DB access
- **Surface**: DB + Web — Invoice
- **PRD Ref**: §3.12 Historical Tax Snapshot Immutability
- **Status**: ☐

**Steps:**
1. Create an invoice → note the tax rate version used: `SELECT tax_rate_version_id FROM invoice_tax_component WHERE invoice_id = <id>`
2. Insert a new `tax_rate_version` row with a different rate for the same jurisdiction (simulating a rate change)
3. Re-open the original invoice

**Expected Result:**
- Existing invoice still shows the original tax rate from when it was created
- `invoice_tax_component.tax_rate_version_id` FK still points to the original rate version (immutable)
- New invoices for the same customer will pick up the new rate

**Notes:** _______________

---

### P1-S09 — Notifications & Communications

> **Setup**: Seed scripts run. Log in as owner or tech as noted. MockSmsCarrier is active — verify SMS via `notification_outbox` and `notification_delivery_attempt` tables, not real phone delivery.

---

#### P1-S09-A: Notification Outbox & At-Least-Once Delivery

##### P1-S09-A-01 — Verify notification outbox populated after triggering action
- **User**: Tier 1 owner
- **Surface**: DB — `notification_outbox`
- **PRD Ref**: §3.7 Reliable Message Queuing (Transactional Outbox)
- **Status**: ☐

**Steps:**
1. Perform an action that generates a notification (e.g., assign a tech to a job from P1-S05-A-02)
2. DB check: `SELECT recipient_user_id, channel, template_type, status FROM notification_outbox WHERE tenant_id = '...0001' ORDER BY created_at DESC LIMIT 5`

**Expected Result:**
- Notification row exists in `notification_outbox` with `status = 'delivered'` (or `'pending'` if Celery hasn't processed it yet)
- `delivery_attempt` row in `notification_delivery_attempt` with provider response
- At-least-once: if initial delivery fails, retry is attempted (check `retry_count` field if delivery fails)

**Notes:** _______________

---

#### P1-S09-B: 13 Customer Communication Templates

##### P1-S09-B-01 — Send "On My Way" template via web UI (always-preview-before-send)
- **User**: Tier 1 tech (`tech@pilot.local`) or owner
- **Surface**: Web or Mobile — Job detail → Send Customer Message
- **PRD Ref**: §3.7 Customer Communication Templates; §3.7 Always-Preview-Before-Send Rule
- **Status**: ☐

**Steps:**
1. On an active job, navigate to Customer Communications
2. Select template: `on_my_way` → system auto-populates ETA based on current schedule
3. Review the preview screen (shows rendered message body, recipient, channel)
4. Click **Send**

**Expected Result:**
- Preview screen appears BEFORE send — user sees the exact message the customer will receive
- Rendered message shows computed ETA (e.g., "I'm on my way — estimated arrival in 20 minutes")
- After confirmation: `notification_outbox` row created with `template_type = 'on_my_way'`, `channel = 'sms'`
- MockSmsCarrier records the send (no real delivery to customer's phone in local env)

**Notes:** _______________

---

##### P1-S09-B-02 — Attempt to send directly without preview (verify gate)
- **User**: Tier 1 tech
- **Surface**: API
- **PRD Ref**: §3.7 Always-Preview-Before-Send (non-negotiable safeguard)
- **Status**: ☐

**Steps:**
1. Attempt API call: `POST /api/v1/communications/send` directly (bypassing the preview endpoint) with a tech JWT
2. Verify whether the API enforces the preview-before-send flow

**Expected Result:**
- Either: the send endpoint requires a `preview_token` from a prior preview call → rejects direct send without preview
- Or: the preview is enforced at the UI layer only (acceptable — document which is true)

**Notes:** _______________

---

##### P1-S09-B-03 — Verify all 13 active templates render without error
- **User**: Tier 1 owner
- **Surface**: API — `POST /api/v1/communications/preview`
- **PRD Ref**: §3.7 Customer Communication Templates (13 MVP active templates)
- **Status**: ☐

**Steps:**
For each of the 13 active templates, call the preview endpoint:
1. `on_my_way` — uses active job + current ETA
2. `running_late` — requires a delay duration
3. `arrived` — simple template
4. `job_complete`
5. `parts_delay`
6. `confirm_appointment`
7. `tech_assigned`
8. `invoice_sent`
9. `payment_received`
10. `payment_reminder`
11. `change_order_approval`
12. `quote_accepted`
13. `quote_expiring`

**Expected Result:**
- All 13 templates render without errors
- Variable substitution works (customer name, job address, ETA, quote total, etc.)
- Preview endpoint returns rendered body, recipient info, channel selection

**Notes:** _______________

---

#### P1-S09-C: SMS Inbound Reply Threading

##### P1-S09-C-01 — Simulate inbound SMS reply and verify threading
- **User**: Tier 1 owner + DB/API access
- **Surface**: Web — `Customers > [customer] > Comm history`; Mobile — Customer Messages
- **PRD Ref**: §3.7 Bidirectional SMS Conversation Threading
- **Status**: ☐

**Steps:**
1. First send an outbound SMS to a customer (from B-01)
2. Simulate an inbound reply via the webhook: `POST /api/v1/webhooks/sms/inbound` with a test payload:
   ```json
   {
     "from": "+12125551001",
     "to": "<tenant_telnyx_number>",
     "body": "Thanks! I'll be home."
   }
   ```
3. Navigate to `Customers > John Smith > Comm History`

**Expected Result:**
- Inbound reply appears in the comm history alongside the outbound message (chat-style chronological view)
- Thread keyed on `(tenant_id, customer_id, tech_id, tenant_phone_number_id)`
- Customer's reply NOT delivered to the tech's personal phone — routed through Pilot
- Mobile "Customer Messages" sub-section shows unread count indicator

**Notes:** _______________

---

#### P1-S09-D: SMS STOP / Opt-Out Handling

##### P1-S09-D-01 — Customer STOP reply removes opt-in flag
- **User**: DB/API access
- **Surface**: DB — `customer.sms_opt_out`
- **PRD Ref**: §3.7 SMS STOP / Opt-Out Webhook Handler (TCPA compliance)
- **Status**: ☐

**Steps:**
1. Simulate a STOP inbound message: `POST /api/v1/webhooks/sms/inbound` with body `"STOP"` from John Smith's phone number
2. DB check: `SELECT sms_opt_out, sms_opt_out_at FROM customer WHERE id = <john_smith_id>`

**Expected Result:**
- `customer.sms_opt_out = true` set immediately
- `sms_opt_out_at` timestamp recorded
- Subsequent attempt to send SMS to John Smith rejected with opt-out error (no SMS sent after STOP)

**Notes:** _______________

---

#### P1-S09-E: Notification Preference Matrix

##### P1-S09-E-01 — User sets notification preference overrides (per-category, per-channel)
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Notifications > Preferences`
- **PRD Ref**: §3.7 Notification Preference Matrix
- **Status**: ☐

**Steps:**
1. Navigate to `Settings > Notifications > Preferences`
2. View the 8-category × 3-channel matrix (push / email / in-app)
3. Turn off **email** for `Job activity` category
4. Turn off **push** for `Billing` category
5. Save preferences

**Expected Result:**
- Preferences saved as user overrides (not tenant defaults)
- After saving: trigger a job activity notification (e.g., assign a job to owner's own account)
- Email channel NOT delivered for that notification (preference respected)
- In-app and push channels still delivered (only email turned off)

**Notes:** _______________

---

##### P1-S09-E-02 — Forced-minimum push cannot be muted
- **User**: Tier 1 tech (or any user)
- **Surface**: Web — `Settings > Notifications > Preferences`
- **PRD Ref**: §3.7 Forced-Minimum Push for Safety-Critical Categories
- **Status**: ☐

**Steps:**
1. Navigate to notification preferences
2. Attempt to turn off push for the `Field issues` category

**Expected Result:**
- Push for `Field issues` cannot be toggled off (UI shows it as locked/forced-minimum)
- Tooltip or label explains this is a safety-critical forced minimum
- Setting control is disabled (greyed out / locked) for the forced-minimum channels

**Notes:** _______________

---

#### P1-S09-F: In-App Banner Notification (SSE)

##### P1-S09-F-01 — In-app banner appears for real-time notification
- **User**: Tier 1 owner (web, active session)
- **Surface**: Web — active page (any page with app shell)
- **PRD Ref**: §3.7 In-App Banner Notification Channel
- **Status**: ☐

**Steps:**
1. Keep the web app open (owner logged in)
2. From another tab or API call, trigger an event that sends an in-app notification (e.g., tech assignment change)
3. Observe the web app

**Expected Result:**
- Slim slide-down notification banner appears at the top of the active page within 1–2 seconds
- Banner auto-dismisses after 6 seconds
- Notification center bell icon shows unread count badge
- Clicking the banner or notification bell item deep-links to the relevant entity

**Notes:** _______________

---

### P1-S10 — QuickBooks Integration

> **Setup**: QuickBooks Developer sandbox account required. Use ngrok for OAuth callback locally (`ngrok http 8000`). If QB connection is not available, manual DB insertion of sync conflict records is used for UI testing sub-sections.

---

#### P1-S10-A: OAuth Connect Flow

##### P1-S10-A-01 — Connect QuickBooks sandbox via OAuth
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Integrations > QuickBooks`
- **PRD Ref**: §5.1 OAuth 2.0 Connection Flow
- **Status**: ☐ *(Requires ngrok + QB Developer sandbox)*

**Steps:**
1. Start ngrok: `ngrok http 8000`; update QB Developer app callback URL
2. Navigate to `Settings > Integrations > QuickBooks` → click **Connect QuickBooks**
3. Authenticate with Intuit → grant access → return to Pilot

**Expected Result:**
- OAuth tokens stored encrypted in `integration_credential` (Fernet: AES-128-CBC + HMAC)
- `app_service` record updated with QB `realm_id` (external_account_id)
- Connection status shows "Connected" in the UI
- Initial customer sync triggered (Celery task enqueued)

**Notes:** _______________

---

#### P1-S10-B: Conflict Detection + Resolution UI

##### P1-S10-B-01 — Manually seed QB conflict and resolve via web UI
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Integrations > QuickBooks > Conflicts`
- **PRD Ref**: §5.4 Conflict Detection & Resolution; §3.9 QB Conflict Resolution UI
- **Status**: ☐

**Steps:**
1. Insert test conflict in DB:
   ```sql
   INSERT INTO integration_sync_conflict (
     tenant_id, entity_type, conflict_type,
     pilot_snapshot, external_snapshot, base_snapshot, field_diffs,
     status, created_at, updated_at
   ) VALUES (
     '00000000-0000-0000-0000-000000000001', 'customer', 'modified_modified',
     '{"name":"John Smith","email":"john@smith.example.com"}',
     '{"name":"John A. Smith","email":"john@smith.example.com"}',
     '{"name":"John Smith","email":"john@smith.example.com"}',
     '[{"field":"name","pilot_value":"John Smith","external_value":"John A. Smith"}]',
     'open', NOW(), NOW()
   )
   ```
2. Navigate to `Settings > Integrations > QuickBooks > Conflicts`
3. Open the conflict → review track-changes diff
4. Click **Use Pilot version** → confirm

**Expected Result:**
- Conflict queue shows the seeded conflict with "Customer — Modified ↔ Modified" label
- Two-column diff: Pilot (left), QuickBooks (right) — amber for modified `name` field
- Resolving with "Use Pilot version": conflict status = `resolved`, resolution logged with actor
- Voice status-query intent available ("Do I have any QuickBooks conflicts?") — voice resolution NOT available (refusal-with-redirect per §5.4)

**Notes:** _______________

---

#### P1-S10-C: In-Flight Sync Indicator

##### P1-S10-C-01 — Sync indicator shows correct compositional states
- **User**: Tier 1 owner
- **Surface**: Web — QuickBooks integration surface
- **PRD Ref**: §3.9 In-Flight Sync Indicator with Pending Count
- **Status**: ☐

**Steps:**
1. Navigate to QuickBooks settings
2. Observe the sync indicator in idle state (synced)
3. Trigger a manual sync → observe "syncing active" state
4. After sync completes, observe idle state again

**Expected Result:**
- 5 compositional states observable: synced-idle (green), synced-with-pending (amber badge), syncing-active (spinner), sync-error (red), sync-paused (if applicable)
- Manual sync trigger inline in the indicator
- Pending count shown when there are pending operations

**Notes:** _______________

---

### P1-S11 — Mobile Offline Operations

> **Setup**: Mobile app running (Expo on physical device strongly preferred for realistic network simulation). Seed scripts run with jobs assigned to tech user.

---

#### P1-S11-A: Offline Capability Contract

##### P1-S11-A-01 — Verify explicit offline-capable operations work without network
- **User**: Tier 1 tech on mobile (physical device)
- **Surface**: Mobile
- **PRD Ref**: §3.15 Explicit Offline-Capable Operation Set
- **Status**: ☐

**Steps:**
1. Enable airplane mode on the device (no WiFi, no cellular)
2. Confirm the global connection state indicator shows offline/red
3. Test each offline-capable operation:
   - Clock in to an assigned job ✓
   - Log an expense ✓
   - Add a free-text job note ✓
   - Take a job photo ✓
   - Add a change order to an assigned job ✓
   - Confirm LOTO (if enabled) ✓
4. Each operation should show immediate success (optimistic UI)

**Expected Result:**
- All 6 operations complete immediately on device (no "network error" messages)
- Pending sync badge appears on each affected entity
- `mobile_sync_queue` (local storage) shows queued items
- Connection state indicator shows queued item count

**Notes:** _______________

---

#### P1-S11-B: Reconnect and Sync

##### P1-S11-B-01 — Re-enable network; verify auto-sync clears queue
- **User**: Tier 1 tech on mobile (continuing from A-01)
- **Surface**: Mobile — Sync Queue + Server DB
- **PRD Ref**: §3.15 Sync Triggers (Foreground + Background)
- **Status**: ☐

**Steps:**
1. Re-enable network (turn off airplane mode)
2. Observe the sync queue bottom sheet — items should transition from "Pending" to "Syncing" to "Recently synced"
3. DB check: verify all offline-captured operations are now in the server DB

**Expected Result:**
- Auto-sync triggers within 30 seconds of network restore (foreground sync trigger)
- `mobile_sync_event` server-side log shows sync attempts
- All queued items clear to "Recently synced" (no failures)
- Pending sync badges clear from the UI
- Connection state indicator returns to hidden (synced + online)

**Notes:** _______________

---

#### P1-S11-C: Four-Class Conflict Resolution

##### P1-S11-C-01 — Tech-resolvable conflict: time entry conflict
- **User**: Tier 1 tech on mobile + owner on web
- **Surface**: Mobile — Sync queue; Web — Dashboard > Approvals > Field Issues
- **PRD Ref**: §3.15 Four-Class Sync Conflict Severity; Tech-Resolvable UI
- **Status**: ☐

**Steps (manually seed conflict for testing):**
1. DB: insert a `mobile_sync_conflict` record with `severity = 'tech_resolvable'` for a time entry conflict
2. On mobile, open the sync queue → find the conflict in "Action needed"
3. Review the vertical-stacked conflict UI: "Your version" vs "Server version" with track-changes
4. Tap **Use my version** → confirm

**Expected Result:**
- Tech sees conflict in "Action needed" section at top of queue (priority ordering)
- Vertical layout with "Your version" and "Server version" stacked
- Track-changes diff: amber for modified, green for added, red for removed
- Pre-resolution staleness check applies before committing
- After resolution: conflict cleared, entity updated on server

**Notes:** _______________

---

##### P1-S11-C-02 — Owner escalation: conflict routed to web queue
- **User**: Tier 1 tech on mobile + owner on web
- **Surface**: Mobile + Web — `Dashboard > Approvals > Field Issues`
- **PRD Ref**: §3.15 Owner Escalation Path with Loop Closure
- **Status**: ☐

**Steps:**
1. DB: insert a `mobile_sync_conflict` record with `severity = 'owner_escalation'`
2. On mobile, tech sees "Sent to owner for review" message in the sync queue
3. On web, owner navigates to `Dashboard > Approvals > Field Issues`
4. Owner resolves the conflict → chooses a resolution
5. Return to mobile — tech sees resolution notification

**Expected Result:**
- Field Issues queue on web shows the escalated conflict with tech name, operation type, timestamps
- Owner resolution UI shows full diff with two-button action bar
- After resolution: tech receives push notification with outcome
- Activity log entry on tech's mobile shows the resolution

**Notes:** _______________

---

#### P1-S11-D: Background Sync

##### P1-S11-D-01 — Background sync executes when app is closed
- **User**: Tier 1 tech on mobile (physical device with background app refresh enabled)
- **Surface**: Mobile — offline queue + server DB
- **PRD Ref**: §3.15 Background Sync (Silent Push + OS Scheduled)
- **Status**: ☐

**Steps:**
1. Capture some offline operations (from A-01)
2. Close the Pilot mobile app completely (force-quit)
3. Wait 5–10 minutes (background sync interval)
4. Re-open the app → check queue state

**Expected Result:**
- Background sync ran while app was closed (server-initiated silent push or OS-scheduled)
- On re-open: queue shows items as "Recently synced" or empty — not still "Pending"
- `mobile_sync_event` log on server shows a sync run with `trigger = 'background'`
- Failure visibility: if background sync failed, "Last sync: X minutes ago — failed" indicator shows on next open

**Notes:** _______________

---

### P1-S12 — Voice AI

> **Setup**: Whisper (`faster-whisper-large-v3-turbo`) and Ollama (`llama3.1:8b`) running in Docker. Voice requires audio input — use mobile mic or web mic. ⚠️ CPU inference: expect 5–20s latency locally vs. <2s production target. Test functional behavior, not latency.

---

#### P1-S12-A: End-to-End Voice Pipeline

##### P1-S12-A-01 — Basic voice command processed end-to-end
- **User**: Tier 1 owner
- **Surface**: Web or Mobile — Voice mic
- **PRD Ref**: §6.1 End-to-End Architecture
- **Status**: ☐

**Steps:**
1. Open the Voice tab (or tap the mic button)
2. Say: `"What jobs do I have today?"`
3. Wait for Whisper transcription + Ollama intent parsing

**Expected Result:**
- Audio captured and sent to `POST /api/v1/voice/command`
- Whisper transcribes: `"What jobs do I have today?"`
- Ollama parses intent: `query_job_etc_status` or `navigate` → list today's jobs
- Response returned and spoken via TTS: today's jobs listed by name and time
- `voice_command_log` row created with `processing_status = 'completed'`

**Notes:** _______________

---

#### P1-S12-B: Multi-Turn Context Management

##### P1-S12-B-01 — Pronoun resolution across multiple turns
- **User**: Tier 1 owner
- **Surface**: Web or Mobile — Voice
- **PRD Ref**: §6.3 Multi-Turn Context Management
- **Status**: ☐

**Steps:**
1. Say: `"Create a quote for John Smith"`
2. Wait for response (quote created, `active_customer_id` + `active_quote_id` in context)
3. Say: `"Add a 200-amp panel upgrade to it"`
4. Wait for response

**Expected Result:**
- Turn 1: Quote created for John Smith; AI responds "Created quote for John Smith. What would you like to add?"
- Turn 2: AI resolves "it" from `active_quote_id` in `context_window_json` → adds the line item
- No disambiguation prompt needed (context resolves "it" without ambiguity)
- `conversation_session.context_window_json.active_quote_id` set after Turn 1

**Notes:** _______________

---

#### P1-S12-C: Confirm-as-Turn for Destructive Actions

##### P1-S12-C-01 — Quote send requires confirmation turn
- **User**: Tier 1 owner
- **Surface**: Web or Mobile — Voice
- **PRD Ref**: §6.6 Confirm-as-Turn for Destructive Actions
- **Status**: ☐

**Steps:**
1. With a quote in context (from B-01), say: `"Send the quote to the customer"`
2. AI should NOT immediately send — observe the confirmation prompt
3. Say: `"Yes"` (or `"Confirm"`)

**Expected Result:**
- After "Send the quote": AI states the specific action and waits — `"You're about to send the John Smith quote to [email] — confirm?"`
- `context_window_json.pending_confirmation` populated with intent details
- After `"Yes"`: quote send executes; pending_confirmation cleared
- If you say `"Cancel"` instead: action aborted; AI returns to passive listening

**Notes:** _______________

---

#### P1-S12-D: Disambiguation Pattern

##### P1-S12-D-01 — Ambiguous entity reference triggers disambiguation prompt
- **User**: Tier 1 owner
- **Surface**: Web or Mobile — Voice
- **PRD Ref**: §2.2 Disambiguation Before Guessing
- **Status**: ☐

**Steps:**
1. Ensure at least 2 customers with similar names exist (e.g., `John Smith` and `John Davis`)
2. Say: `"Create a quote for John"`

**Expected Result:**
- AI asks rather than guesses: `"Which John — Smith or Davis?"`
- After answering, AI proceeds with the specified John
- No silent guess made when multiple matches exist

**Notes:** _______________

---

#### P1-S12-E: Voice Field Operations Intents

##### P1-S12-E-01 — Clock in via voice (offline-capable)
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Voice
- **PRD Ref**: §6.2 Voice Field Operations Intents — `clock_in`
- **Status**: ☐

**Steps:**
1. Say: `"Clock in to the Panel Upgrade job"`
2. AI identifies the correct job by name and triggers clock-in

**Expected Result:**
- `clock_in` intent dispatched
- Time entry created with `clock_in_at = now`
- AI confirms: `"Clocked in to In Progress - Panel Upgrade. Good luck!"`
- Works offline (captured locally, syncs on reconnect)

**Notes:** _______________

---

##### P1-S12-E-02 — Log expense via voice
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Voice
- **PRD Ref**: §6.2 `add_expense`
- **Status**: ☐

**Steps:**
1. Say: `"Add $45.99 expense for breakers from Home Depot"`
2. Confirm-as-turn if prompted

**Expected Result:**
- `add_expense` intent dispatched
- Expense created: `cost_cents = 4599`, `description = 'breakers from Home Depot'`
- AI confirms the expense and asks if markup should be applied (or uses default markup)
- Offline-capable: works without network

**Notes:** _______________

---

#### P1-S12-F: NEC Code Calculations

##### P1-S12-F-01 — Voltage drop calculation
- **User**: Tier 1 owner or tech
- **Surface**: Web or Mobile — Voice
- **PRD Ref**: §6.8 NEC Code Assistance
- **Status**: ☐

**Steps:**
1. Say: `"Calculate voltage drop for 200 feet of 12 AWG copper at 240 volts with 20 amps"`

**Expected Result:**
- Intent: `calculate_voltage_drop`
- AI calculates using NEC formula: `VD = 2 × R × I × L / 1000`
- Response: voltage drop value in volts + percentage of supply voltage + pass/fail vs. NEC 3% guideline
- Calculation drawn from NEC 2023 Reference Guide corpus

**Notes:** _______________

---

##### P1-S12-F-02 — Conduit fill calculation
- **User**: Tier 1 owner or tech
- **Surface**: Voice
- **PRD Ref**: §6.8 NEC Code Assistance
- **Status**: ☐

**Steps:**
1. Say: `"What's the conduit fill for 4 THHN 12 AWG wires in a 3/4 inch EMT conduit?"`

**Expected Result:**
- AI returns total fill percentage vs. NEC maximum (40% for 3+ conductors)
- Pass/fail result stated clearly
- Response grounded in NEC 2023 reference corpus

**Notes:** _______________

---

#### P1-S12-G: Voice Persona Tone

##### P1-S12-G-01 — Switch voice persona tone and verify AI response style changes
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Voice > Persona Tone`
- **PRD Ref**: §3.13 Voice Persona Tone (Three-Position Enum)
- **Status**: ☐

**Steps:**
1. Set persona tone to `conservative` (formal, brief) → ask a voice question
2. Change to `playful` (warmer, conversational) → ask the same question
3. Observe the difference in AI response style

**Expected Result:**
- `conservative`: formal, brief responses (e.g., "Quote created for John Smith.")
- `playful`: warmer, more conversational (e.g., "Got it! Created a quote for John Smith — what would you like to add first?")
- Tone affects voice readback, session title generation, and assistant turn responses
- Customer-facing surfaces (SMS templates, emails) NOT affected by tone setting

**Notes:** _______________

---

#### P1-S12-H: Offline Voice Capture + Deferred Processing

##### P1-S12-H-01 — Voice command captured offline, processed on reconnect
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Voice (offline)
- **PRD Ref**: §6.7 Deferred Voice Processing Pipeline; §3.15 Voice Capture Offline
- **Status**: ☐

**Steps:**
1. Enable airplane mode on device
2. Open Voice tab → record a voice command: `"Log 3 hours on the Panel Upgrade job"`
3. Observe immediate feedback on device
4. Re-enable network

**Expected Result:**
- With no network: Tech sees `"Voice captured — will process when online"` (NOT "Voice failed")
- Audio saved locally
- On network restore: audio uploaded → Whisper transcribes → Llama parses → time entry created
- Tech sees notification or voice tab update when processing completes
- If destructive intent: confirmation prompt surfaced as notification, not blocking

**Notes:** _______________

---

### P1-S13 — Subscriptions & Usage

> **Setup**: Test tenant is on the Trial tier (seeded by `seed_test_tenant.py`). DB manipulation needed for expiration tests.

---

#### P1-S13-A: Trial Tier Behavior

##### P1-S13-A-01 — Verify trial tier has full feature parity
- **User**: Tier 1 owner (trial tier tenant)
- **Surface**: Web — all surfaces
- **PRD Ref**: §3.11 Trial-as-Tier Framing
- **Status**: ☐

**Steps:**
1. Verify tenant is on Trial tier: `SELECT subscription_tier_id FROM tenant WHERE id = '...0001'` → should resolve to the trial tier
2. Navigate through key surfaces: Quotes, Dispatch, Voice, Settings, Integrations
3. Attempt feature-gated actions: create a quote, use voice, view integrations

**Expected Result:**
- All MVP features accessible on Trial tier (full Starter parity)
- No paywalls or "Upgrade to use this feature" prompts during trial
- Trial duration shown somewhere (e.g., "X days remaining in trial" banner or badge)

**Notes:** _______________

---

#### P1-S13-B: Trial Expiration + Paywall

##### P1-S13-B-01 — Simulate trial expiration and verify read-only paywall
- **User**: Tier 1 owner + DB access
- **Surface**: Web — all surfaces
- **PRD Ref**: §3.11 Trial Expiration with Read-Only Paywall; §4.7.5 Trial Expiration Enforcement
- **Status**: ☐

**Steps:**
1. DB: `UPDATE tenant SET trial_ends_at = NOW() - INTERVAL '1 day' WHERE id = '...0001'`
2. Trigger expiration Celery task: `docker exec pilot_celery_worker celery -A tasks call tasks.tenants.enforce_trial_expirations`
3. Refresh the web app
4. Attempt to create a new quote
5. Attempt to send an SMS

**Expected Result:**
- Paywall surface appears after trial expiration
- Existing data readable (can view quotes, jobs, customers)
- Write operations blocked: new quote creation → paywall prompt (`402 Payment Required` from API)
- SMS sending blocked
- Voice intents limited to read-only operations
- "Upgrade Plan" CTA prominent

**Notes:** _______________

---

#### P1-S13-C: SMS Quota Enforcement

##### P1-S13-C-01 — SMS usage visible in mobile and web
- **User**: Tier 1 owner
- **Surface**: Web — Dashboard; Mobile — SMS composer
- **PRD Ref**: §3.11 In-Month SMS Usage Visibility
- **Status**: ☐

**Steps:**
1. Send a few test SMS messages via MockSmsCarrier (from P1-S09-B-01)
2. Navigate to the SMS usage display in the web dashboard
3. On mobile, open the SMS composer for a customer

**Expected Result:**
- Current SMS segment count visible (e.g., "3 of 100 segments used this month")
- Remaining quota shown
- On mobile composer, segment count for the current message shown inline
- Owner status row appears on mobile when usage > 70%

**Notes:** _______________

---

##### P1-S13-C-02 — Hard cap blocks SMS when quota exhausted
- **User**: Tier 1 owner + DB access
- **Surface**: Web / API
- **PRD Ref**: §3.11 Tenant-Controlled SMS Cap Policy (hard cap)
- **Status**: ☐

**Steps:**
1. DB: set tenant SMS policy to hard cap: `UPDATE platform_setting SET value = 'hard' WHERE tenant_id = '...0001' AND key = 'sms_quota_cap_policy'`
2. DB: set usage to 100/100: set the SMS segment usage counter to 100 (max for trial/starter)
3. Attempt to send an SMS

**Expected Result:**
- SMS blocked with a clear "Monthly SMS quota exhausted" message
- No SMS written to `notification_outbox` (hard block prevents send)
- Owner sees upgrade prompt or "wait until next billing cycle" message

**Notes:** _______________

---

### P1-S14 — Audit & Compliance

> **Setup**: Seed scripts run. Audit log tests observe what was written by earlier test actions. Log in as owner (audit.view permission required).

---

#### P1-S14-A: Trigger-Based Mutation Capture

##### P1-S14-A-01 — Audit log captures customer create/update/delete
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Audit Log` (or API `GET /api/v1/audit`)
- **PRD Ref**: §3.1 Trigger-Based Mutation Capture
- **Status**: ☐

**Steps:**
1. From earlier tests, a customer was created (P1-S03-A-02), edited (P1-S03-A-04), and soft-deleted
2. Navigate to the audit log → filter by entity type `customer` and tenant ID
3. Inspect entries

**Expected Result:**
- 3 audit log entries for the customer lifecycle: INSERT, UPDATE, soft-delete UPDATE
- Each entry has: `actor_id`, `actor_type`, `table_name`, `old_data` (JSONB), `new_data` (JSONB), `timestamp`
- Hard-delete NOT in the log (soft-delete sets `is_active = false`, captured as UPDATE)

**Notes:** _______________

---

##### P1-S14-A-02 — Platform attribution vs. user attribution
- **User**: DB inspection
- **Surface**: DB — `audit_log`
- **PRD Ref**: §3.1 Platform vs. User Attribution (`actor_type` discriminator)
- **Status**: ☐

**Steps:**
1. Trigger a Celery task that modifies data (e.g., quote expiration task from P1-S04-I-01)
2. DB check: `SELECT actor_type, actor_id FROM audit_log WHERE table_name = 'quote' AND old_data->>'status' = 'sent' AND new_data->>'status' = 'expired'`

**Expected Result:**
- `actor_type = 'system'` for Celery-task-driven mutations (not a user)
- `actor_type = 'user'` for direct user edits
- Platform actions clearly distinguishable from user actions in the audit log

**Notes:** _______________

---

##### P1-S14-B: Financial De-duplication

##### P1-S14-B-01 — Idempotency key prevents duplicate invoice
- **User**: API access
- **Surface**: API — `POST /api/v1/invoices`
- **PRD Ref**: §3.1 Financial De-duplication; §3.8 Idempotency Keys
- **Status**: ☐

**Steps:**
1. Call `POST /api/v1/invoices` with `Idempotency-Key: test-invoice-key-001` → invoice created
2. Call the same endpoint again with identical `Idempotency-Key: test-invoice-key-001`

**Expected Result:**
- Second call returns the same invoice response (idempotent — no duplicate created)
- DB check: only 1 invoice with the content from the request — not 2
- Unique constraint on `(tenant_id, idempotency_key)` prevents duplicates at DB level

**Notes:** _______________

---

### P1-S15 — Platform Infrastructure Patterns

> **Setup**: Docker stack running, seeds populated. These are cross-cutting tests that validate underlying platform guarantees.

---

#### P1-S15-A: Multi-Tenant Isolation

##### P1-S15-A-01 — Tenant data not accessible cross-tenant
- **User**: Tier 1 owner (test tenant) + a second tenant (manually create or use DB)
- **Surface**: API
- **PRD Ref**: §3.5 Strict Tenant Isolation; §3.8 Multi-Tenant Isolation
- **Status**: ☐

**Steps:**
1. Note the test tenant ID: `00000000-0000-0000-0000-000000000001`
2. Create a second tenant (manually via DB insert or signup wizard with second email)
3. Log in as the second tenant's owner → attempt `GET /api/v1/customers` to retrieve customers
4. Verify customers from the test tenant (John Smith, Mary Johnson, etc.) are NOT returned

**Expected Result:**
- Second tenant's API response contains only their own customers (0 if newly created)
- Test tenant's customers never appear in another tenant's responses
- DB triggers prevent `tenant_id` reassignment after record creation

**Notes:** _______________

---

#### P1-S15-B: RFC 7807 Error Responses

##### P1-S15-B-01 — All error paths return RFC 7807 format
- **User**: API access
- **Surface**: API
- **PRD Ref**: §7.4 Error Response Format (RFC 7807)
- **Status**: ☐

**Steps:**
Test 3 error scenarios and verify response format:
1. `401 Unauthorized`: call any authenticated endpoint without a JWT
2. `403 Forbidden`: call `GET /api/v1/audit` with technician JWT
3. `404 Not Found`: call `GET /api/v1/customers/00000000-0000-0000-0000-deadbeef0001` (nonexistent ID)

**Expected Result:**
Each response body contains: `type` (URI), `title` (human-readable), `status` (HTTP code), `detail` (specific message)

Example 403:
```json
{
  "type": "https://pilotfortrades.com/errors/forbidden",
  "title": "Insufficient Permissions",
  "status": 403,
  "detail": "You do not have permission to perform this action",
  "required_permission": "audit.view",
  "user_role": "technician"
}
```

**Notes:** _______________

---

#### P1-S15-C: Rate Limiting

##### P1-S15-C-01 — Rate limit returns 429 after exceeding threshold
- **User**: API access (script or rapid manual calls)
- **Surface**: API
- **PRD Ref**: §3.8 Basic Rate Limiting (1,000 req/hr per Tenant)
- **Status**: ☐

**Steps:**
1. Script 1,001 rapid GET requests to `/api/v1/customers` using the test tenant JWT

**Expected Result:**
- First 1,000 requests succeed (200 OK)
- 1,001st request returns `429 Too Many Requests`
- `Retry-After` header present in 429 response
- Rate limit resets after 1 hour

**Notes:** _______________

---

#### P1-S15-D: States Catalog (Empty / Loading / Error)

##### P1-S15-D-01 — Empty state renders for empty list views
- **User**: Tier 2 test owner (fresh tenant, no data)
- **Surface**: Web — Quotes, Customers, Jobs lists
- **PRD Ref**: §3.15 States Catalog (5 empty state variants per FE-B1)
- **Status**: ☐

**Steps:**
1. Log in as a freshly-created Tier 2 test owner (no data seeded for this tenant)
2. Navigate to: Quotes list, Customers list, Jobs list, Dispatch Board
3. Observe the rendered state for each empty list

**Expected Result:**
- Each empty list shows an appropriate empty state component (not a blank screen, not an error)
- Empty state has a descriptive message and a primary CTA (e.g., "No quotes yet — Create your first quote")
- Empty states use the correct variant (first-time-user variant different from "you filtered it to zero" variant)
- First-time-user empty states match the `<FirstTimeUserState>` variants from the states catalog

**Notes:** _______________

---

##### P1-S15-D-02 — Error state renders when API returns 500
- **User**: Tier 1 owner
- **Surface**: Web — any list or detail view
- **PRD Ref**: §3.15 States Catalog (4 error state variants)
- **Status**: ☐

**Steps:**
1. Temporarily stop the FastAPI container: `docker stop pilot_api`
2. Navigate to the Customers list in the web app
3. Restart the container: `docker start pilot_api`

**Expected Result:**
- Error state component renders (not a blank screen or unhandled JS error)
- Error message is user-friendly (not a raw stack trace)
- Retry button available
- After restarting the API and clicking retry, data loads successfully

**Notes:** _______________

---

#### P1-S15-E: Cursor-Based Pagination

##### P1-S15-E-01 — Large list paginates correctly
- **User**: Tier 1 owner
- **Surface**: API — `GET /api/v1/customers`
- **PRD Ref**: §7.8 Cursor-Based Pagination
- **Status**: ☐

**Steps:**
1. DB: ensure more than 20 customers exist (create additional ones or adjust page size to a small number for testing)
2. Call `GET /api/v1/customers?limit=5`
3. Use the `next_cursor` from the response to call the next page: `GET /api/v1/customers?limit=5&cursor=<next_cursor>`
4. Repeat until `next_cursor` is null (last page)

**Expected Result:**
- First response contains 5 customers + a `next_cursor` value
- Subsequent pages return the next batch without repeats or gaps
- Last page has `next_cursor = null` (no more pages)
- Total item count correct across all pages

**Notes:** _______________

---

#### P1-S15-F: UTC Triple-Lock

##### P1-S15-F-01 — All timestamps stored as UTC with timezone awareness
- **User**: DB inspection
- **Surface**: DB — timestamp columns across key tables
- **PRD Ref**: §3.8 UTC Triple-Lock Enforcement
- **Status**: ☐

**Steps:**
1. Create a customer, a quote, and a time entry (from prior tests)
2. DB check: `SELECT created_at, updated_at FROM customer WHERE id = <id>`
3. Check that the timezone offset is present: `SELECT created_at AT TIME ZONE 'America/New_York' FROM customer WHERE id = <id>`

**Expected Result:**
- All timestamp columns store `TIMESTAMPTZ` (not `TIMESTAMP WITHOUT TIME ZONE`)
- Timestamps include timezone info (e.g., `2026-06-02 17:00:00+00` — UTC offset)
- Converting to a local timezone via `AT TIME ZONE` returns the expected local time

**Notes:** _______________

---

#### P1-S15-G: In-Flight Sync Indicator (5-State Compositional Model)

##### P1-S15-G-01 — All 5 sync indicator states observable
- **User**: Tier 1 owner
- **Surface**: Web — any surface with sync indicator (dispatch, QuickBooks, calendar)
- **PRD Ref**: §16.13 In-Flight Sync Indicator with Pending Count
- **Status**: ☐

**Steps:**
1. **Synced-idle**: No pending operations — observe the sync indicator
2. **Synced-with-pending**: Queue some operations that haven't synced yet
3. **Syncing-active**: Trigger a sync and observe during processing
4. **Sync-error**: Stop the API mid-sync to cause a failure
5. **Sync-paused**: If applicable, pause sync from settings

**Expected Result:**
- Each state has a distinct visual treatment (green/amber/red/spinner)
- Pending count badge appears in the amber (synced-with-pending) state
- Manual sync trigger available inline in the indicator
- Hover/tap shows up to 5 individual pending items with "+N more"

**Notes:** _______________

---

### P1-S16 — Help & Support

> **Setup**: Help corpus (markdown articles) must be loaded in S3 and embedded into pgvector for RAG to work. If corpus is not set up, test the UI components and chat interface without RAG (AI will respond with general knowledge + note lack of corpus). Log in as owner or tech as noted.

---

#### P1-S16-A: AI-Mediated Help Chat (RAG)

##### P1-S16-A-01 — Open help chat and ask a product question
- **User**: Tier 1 owner
- **Surface**: Web — Help panel (side-drawer)
- **PRD Ref**: §3.16 AI-Mediated Help with RAG; §19.4 Help AI Agent
- **Status**: ☐

**Steps:**
1. Click the `?` icon in the app shell navigation
2. Help side-drawer opens (400px wide, slides from right)
3. Type or speak: `"How do I create a quote?"`
4. Wait for AI response

**Expected Result:**
- Help panel opens as a slide-out drawer (not a new page)
- AI responds with grounded guidance on quote creation
- If corpus loaded: response references specific steps in Pilot's UI
- If corpus not loaded: AI gives general response + indicates it can't find a specific article
- Suggested follow-up buttons appear in AI response ("Read full article", "Walk me through it")

**Notes:** _______________

---

##### P1-S16-A-02 — Context-aware help opener from complex settings surface
- **User**: Tier 1 owner
- **Surface**: Web — QuickBooks conflict resolution page
- **PRD Ref**: §3.16 Three Help Entry Points; §3.16 Context-Aware Help Opener
- **Status**: ☐

**Steps:**
1. Navigate to `Settings > Integrations > QuickBooks > Conflicts`
2. Click the contextual `?` icon (should be present per §3.16 Selective Contextual Help Anchors)
3. Observe the AI's initial message

**Expected Result:**
- Help drawer opens with context-aware initial message: `"I see you're on the QuickBooks conflict resolution page — how can I help?"`
- AI has received a minimal context payload (current route, entity type, user role) — not entity contents
- Response is grounded in the current surface context (not generic "how can I help?")

**Notes:** _______________

---

#### P1-S16-B: Web Side-Drawer + Mobile Full-Screen Chat

##### P1-S16-B-01 — Web: side-drawer doesn't block main app
- **User**: Tier 1 owner
- **Surface**: Web — Help panel open alongside Quotes list
- **PRD Ref**: §3.16 Web Side-Drawer Chat
- **Status**: ☐

**Steps:**
1. Navigate to the Quotes list
2. Open help (`?` icon)
3. With help drawer open, attempt to click on a quote in the main content area

**Expected Result:**
- Help drawer slides in from the right at 400px width
- Main content area remains visible and interactive (not blocked/greyed out)
- Clicking a quote while help is open navigates to the quote detail in the main area
- Help drawer can be closed via the X button

**Notes:** _______________

---

##### P1-S16-B-02 — Mobile: help opens as full-screen
- **User**: Tier 1 tech on mobile
- **Surface**: Mobile — Help
- **PRD Ref**: §3.16 Mobile Full-Screen Chat
- **Status**: ☐

**Steps:**
1. On mobile, tap the `?` icon (or navigate to Help from nav)
2. Help opens full-screen
3. Type a question → receive a response

**Expected Result:**
- Full-screen help view on mobile (not a drawer)
- Chat history scrolls; latest message at bottom
- Composition zone at bottom with voice mic + text input + send
- AI avatar and user avatar distinguish messages

**Notes:** _______________

---

#### P1-S16-C: AI Knowledge Boundaries + Escalation

##### P1-S16-C-01 — AI refuses out-of-scope requests and escalates
- **User**: Tier 1 owner
- **Surface**: Web — Help panel
- **PRD Ref**: §3.16 AI Knowledge Boundaries; §19.7 AI Knowledge Boundaries and Escalation
- **Status**: ☐

**Steps:**
1. Open help → type: `"Can you delete my QuickBooks account for me?"`
2. Ask: `"What's the legal liability of not having a LOTO program?"`
3. Ask the same question 3 more times rephrased (to trigger low-confidence escalation after 3 turns)

**Expected Result:**
- Request 1 ("delete QB account"): AI refuses — `"I can't take actions on your behalf"` — and redirects to the QuickBooks integration settings
- Request 2 (legal advice): AI refuses — `"I don't provide legal or compliance advice"` — and suggests contacting a labor attorney or OSHA
- After 3 turns without resolution: AI surfaces escalation trigger — "Would you like to submit a feedback request for a human to follow up?" or provides feedback form link

**Notes:** _______________

---

#### P1-S16-D: Voice-Driven Help

##### P1-S16-D-01 — Open help and ask question via voice
- **User**: Tier 1 owner
- **Surface**: Web or Mobile — Help chat
- **PRD Ref**: §3.16 Voice Input + Voice-Only Mode; §3.13 Help Voice Intent
- **Status**: ☐

**Steps:**
1. Open help drawer → tap the voice mic button in the composition zone
2. Say: `"How do I connect to QuickBooks?"`
3. Whisper transcribes → text appears in input field
4. Submit the question (edit if needed, or submit directly)
5. Click the 🔊 "Listen" icon on the AI response

**Expected Result:**
- Voice input transcribed correctly by Whisper (`faster-whisper-large-v3-turbo`)
- Transcribed text editable before submission
- AI response includes 🔊 Listen icon for TTS readback
- TTS uses the user's effective voice persona tone for readback
- Voice intent `open_help` + `ask_help_question` work from the main voice tab too

**Notes:** _______________

---

#### P1-S16-E: Past Conversations Recall

##### P1-S16-E-01 — Previous help sessions accessible and resumable
- **User**: Tier 1 owner
- **Surface**: Web — `Help > Past conversations`
- **PRD Ref**: §3.16 Past Conversations Recall
- **Status**: ☐

**Steps:**
1. Have at least 2 help sessions from prior tests (close and reopen help between questions)
2. Navigate to `Help > Past conversations`
3. Click on a prior session

**Expected Result:**
- Past sessions listed with AI-generated titles (e.g., "QuickBooks connection setup", "Creating a quote")
- Clicking a session opens the full chat history
- User can continue from a prior session (new messages appended)
- Sessions from prior tests within the 90-day retention window are visible

**Notes:** _______________

---

#### P1-S16-F: Structured Feedback Submission

##### P1-S16-F-01 — Submit a bug report via feedback form
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Help & About > Send Feedback`
- **PRD Ref**: §3.16 Structured Feedback Submission
- **Status**: ☐

**Steps:**
1. Navigate to `Settings > Help & About > Send Feedback`
2. Select category: `Bug report`
3. Enter text: `"When I try to create a quote for a commercial customer, the site selector doesn't show the correct sites"`
4. Verify reply-to email is auto-filled with owner's email
5. Click **Submit**

**Expected Result:**
- Feedback confirmation page shown after submit
- Email sent to `support@pilotfortrades.com` with subject: `[Pilot Feedback - Bug report]`
- Email body includes: feedback text + tenant info + user role + timestamp + reply-to owner's email
- (Check dev mail inbox or SMTP logs to verify email sent)

**Notes:** _______________

---

#### P1-S16-G: About / Version / Legal Surface

##### P1-S16-G-01 — About page shows correct version info and legal links
- **User**: Tier 1 owner
- **Surface**: Web — `Settings > Help & About > About`; Mobile — same
- **PRD Ref**: §3.16 About / Version / Legal Surface
- **Status**: ☐

**Steps:**
1. Navigate to `Settings > Help & About > About`
2. Inspect all displayed information

**Expected Result:**
- Pilot logo displayed
- Web version string shown (e.g., `v1.0.0-beta`)
- API version shown (from `/api/v1/health` or similar)
- Support contact info present
- Legal links all work (ToS, Privacy, EULA, OSS Licenses) — even if placeholder pages
- Copyright notice present
- Three quick paths to help: Chat, Feedback, Support email — all functional

**Notes:** _______________

---

## Phase 2 — Scenario-Based Testing (End-to-End User Journeys)

> **Prerequisites**: All Phase 1 sections complete with zero 🔴 items. Seed scripts run fresh. Both web and mobile apps running.

> **How to run**: Each scenario is a single continuous session. Complete all steps before marking the scenario. Document any cross-surface integration failures separately from Phase 1 surface bugs.

---

### P2-SC01 — New Tenant Onboarding (Signup → First Quote)

**Goal**: Validate the complete new-user journey from zero to a professional quote sent to a customer — the most critical activation funnel.

**Personas**: Owner only (solo contractor scenario)
**Estimated duration**: 30–45 minutes
**Status**: ☐

**Steps:**
1. Open a fresh incognito browser → navigate to `/signup`
2. Complete the 5-step wizard with real email + real phone (Tier 2 account)
3. Land on Dashboard → verify setup checklist pinned widget
4. Navigate to `Catalog > Pricebook` → add 2 pricebook items (a labor item and a material item)
5. Navigate to `Customers` → create a new residential customer with a service site and gate code
6. Navigate to `Quotes` → create a new quote for the customer using the pricebook items
7. Set presentation style to `line_itemed`, add a 30-day expiration
8. Generate the public quote link → open in a separate incognito tab as the customer
9. Customer accepts the quote with an optional comment
10. Back in Pilot: observe the acceptance notification → convert to job

**Cross-Surface Integrations Tested:**
- Signup Wizard → Dashboard checklist auto-completion (S01-A + S01-F)
- Catalog → Quote pricing snapshot (S02-A + S04-C)
- CRM → Quote customer/site association (S03 + S04)
- Quote → Public link → Acceptance → Job conversion (S04-G + S04-H)
- Notification delivery for quote acceptance (S09-A)

**Pass Criteria:**
- New tenant fully onboarded with no errors
- Quote accurately reflects pricebook prices with margin visible
- Public link renders correctly with tenant branding
- Customer acceptance recorded with comment
- Job created and linked to accepted quote version
- Setup checklist auto-updated at each step

**Notes:** _______________

---

### P2-SC02 — Voice-First Quote-to-Cash (Owner-Operator, Mobile)

**Goal**: Validate the core differentiator — a contractor creates a quote entirely by voice, dispatches the tech, and the customer pays via the public invoice link. Zero keyboard required.

**Personas**: Owner (voice commands throughout)
**Estimated duration**: 45–60 minutes
**Status**: ☐

**Steps:**
1. Log in as owner on mobile → open Voice tab
2. Say: `"Create a new quote for Mary Johnson"` → confirm creation
3. Say: `"Add a 200-amp panel upgrade"` → line item added from pricebook
4. Say: `"Add 50 feet of EMT conduit"` → second line item
5. Say: `"What's the total?"` → AI reads back quote total
6. Say: `"Send the quote to Mary"` → confirm-as-turn fires → confirm → quote sent
7. Customer accepts quote via public link (in a separate browser)
8. Say: `"Any new quote acceptances?"` → AI confirms Mary accepted
9. Say: `"Schedule the Mary Johnson job for tomorrow at 9am"` → job scheduled
10. Say: `"Assign the job to the tech"` → tech assigned
11. Tech (separate mobile) clocks in via voice: `"Clock in to the Johnson job"`
12. Tech clocks out with ETC: `"Clock out — 2 more hours remaining"`
13. Owner: `"Convert the Johnson job to invoice"` (or do via touch)
14. Generate public invoice link → customer pays via Stripe test card

**Cross-Surface Integrations Tested:**
- Voice → Quote creation + line items (S12-G + S04-A)
- Voice → Quote send (confirm-as-turn) (S12-C)
- Voice → Dispatch scheduling (S12-I + S06-A)
- Voice → Field operations (clock in/out + ETC) (S12-E + S05-B)
- Invoice + Stripe payment (S07-C)

**Pass Criteria:**
- All voice commands recognized and routed to correct intents
- Confirm-as-turn fires for quote send and job scheduling
- No voice commands bypass expected confirmations
- Invoice payment processes successfully via Stripe test mode
- Complete audit trail from quote create → invoice paid

**Notes:** _______________

---

### P2-SC03 — Multi-User Shop: Tech Submits, Owner Approves, Customer Pays

**Goal**: Validate the multi-user approval workflow — tech creates a quote, owner reviews and approves with track-changes edits, customer pays.

**Personas**: Tech + Owner (2 users, simultaneous sessions)
**Estimated duration**: 30–45 minutes
**Status**: ☐

**Steps:**
1. Log in as tech (`tech@pilot.local`) on web → create a new quote for Apex Commercial LLC
2. Set `require_approval_for_tech_quotes = true` in tenant settings (if not already)
3. Tech clicks **Submit for Approval** → quote enters `pending_approval`
4. Log in as owner in a second browser → navigate to Quotes > Pending Approval
5. Owner opens the quote → reviews tech's line items
6. Owner edits one line item (changes quantity) → track-changes diff shows amber modification
7. Owner adds an approval comment on a specific line item
8. Owner clicks **Approve** → quote status = `approved`
9. Generate public quote link → open in incognito as the Apex procurement contact
10. Customer accepts with a comment
11. Owner converts accepted quote to invoice → generates public invoice link
12. Customer pays full invoice amount via Stripe test card

**Cross-Surface Integrations Tested:**
- Multi-user RBAC (tech submits, owner approves) (S01-D + S04-E)
- Track-changes review diff vocabulary (S04-F)
- Approval notification routing (S09-A)
- Commercial customer invoice + public payment (S07-C)
- Audit trail: tech create → owner approve → customer accept → payment

**Pass Criteria:**
- Tech cannot approve own quote (RBAC enforced)
- Track-changes diff correctly highlights the owner's modification
- Approval comment preserved on the version record
- Customer acceptance and payment both confirmed
- Audit log shows distinct actor_ids for tech, owner, and system

**Notes:** _______________

---

### P2-SC04 — Full Dispatch Day (Scheduling, Conflicts, Live Updates)

**Goal**: Validate the dispatch board as a real dispatcher would use it — scheduling, rescheduling, conflict handling, and seeing live updates across two browser sessions.

**Personas**: Owner (dispatcher)
**Estimated duration**: 30–40 minutes
**Status**: ☐

**Steps:**
1. Open Dispatch Board in two browser windows (Browser A = primary, Browser B = observer)
2. Create 3 jobs for the same tech tomorrow: Job A (9am–12pm), Job B (1pm–4pm), Job C (3pm–6pm)
3. Note: Job C and Job B overlap at 3pm–4pm → observe conflict detection
4. Drag Job C to 5pm–8pm to resolve the overlap → observe Browser B updates live (SSE)
5. Schedule Job D during the PTO block (Friday 8am–5pm) → observe availability conflict
6. Enable drive-time assist → reorder the day's stops → observe drive-time calculations between jobs
7. Reassign Job B from primary tech to a second tech user (create second tech if needed)
8. Observe: primary tech gets "assignment removed" notification; second tech gets "assigned" notification

**Cross-Surface Integrations Tested:**
- Dispatch board grid + drag interactions (S06-A)
- Four-class conflict detection (overlap + availability) (S06-C)
- SSE live updates across multiple clients (S06-B)
- Drive-time assist (S06-E)
- Tech reassignment notifications (S09-A)

**Pass Criteria:**
- Overlap conflict detected and visually flagged
- SSE update in Browser B within 2 seconds of Browser A action
- Drag-to-reschedule and drag-to-reassign both functional
- Drive-time calculations appear between consecutive stops
- Notifications generated for both techs on reassignment

**Notes:** _______________

---

### P2-SC05 — Tech Goes Offline (Basement → Surface → Sync Resolution)

**Goal**: Validate the complete offline lifecycle — tech loses connectivity, captures field data, reconnects, syncs, and resolves a conflict.

**Personas**: Tech (mobile, physical device) + Owner (web)
**Estimated duration**: 45–60 minutes
**Status**: ☐

**Steps:**
1. Tech (mobile, physical device) is assigned to the `In Progress - Panel Upgrade` job
2. Enable airplane mode → confirm offline indicator shows
3. Tech clocks in to the job (offline capture)
4. Tech adds a material expense: `$52.99 for 15A breakers` (offline)
5. Tech takes 2 job photos (offline — queued for upload when WiFi available)
6. Tech adds a free-text note: `"Main panel was corroded — additional work needed"` (offline)
7. Tech creates a change order: `"Replaced corroded main lug — additional $200"` (offline)
8. Re-enable network → observe sync queue drain
9. DB verify: time entry, expense, change order, note all present server-side
10. Meanwhile: owner modifies the same job's scheduled time on web (creates a staleness scenario)
11. Observe conflict classification → if tech-resolvable, tech resolves on mobile; if owner-escalation, owner resolves on web

**Cross-Surface Integrations Tested:**
- Full offline capability contract (S11-A)
- Optimistic UI with pending badges (S11-B)
- Sync queue drain + auto-sync (S11-B reconnect)
- Conflict classification engine (S11-C)
- Photo upload as separate queue (S11-H)
- Loop closure notification to tech after owner resolves (S11-F)

**Pass Criteria:**
- All 5 offline operations captured without error in airplane mode
- All 5 sync successfully on reconnection within 30 seconds
- Photos queued separately (WiFi-preference behavior observable)
- Conflict classified correctly and routed to correct resolver
- Audit timestamps: `client_capture_at` ≠ `server_received_at` (gap = offline duration)

**Notes:** _______________

---

### P2-SC06 — QuickBooks Full Cycle (Connect → Sync → Conflict → Resolve)

**Goal**: Validate the complete QuickBooks integration lifecycle from OAuth connection through conflict resolution.

**Personas**: Owner (QuickBooks account required)
**Estimated duration**: 45–60 minutes
**Status**: ☐ *(Requires QB Developer sandbox + ngrok)*

**Steps:**
1. Start ngrok → register callback URL in QB Developer app
2. Connect QuickBooks from `Settings > Integrations > QuickBooks` → complete OAuth
3. Verify initial sync: Pilot pushes existing customers to QB → QB customer appears in QB sandbox
4. Modify the same customer in both QB (change `name` suffix to `LLC`) and Pilot (change `email`) simultaneously
5. Wait for sync cycle (15 min) or manually trigger sync
6. Observe conflict detected in `Settings > Integrations > QuickBooks > Conflicts`
7. Resolve: "Use Pilot version" for the email field; note that QB name is NOT overwritten
8. Wait for post-resolution sync to confirm Pilot data is now in QB
9. Create a Pilot invoice → verify it appears as an Estimate in QB after sync

**Cross-Surface Integrations Tested:**
- OAuth flow + token encryption (S10-A)
- Bi-directional customer sync (S10-B)
- Conflict detection + resolution UI with track-changes (S10-B)
- Invoice → QB Estimate push (S10-C)
- In-flight sync indicator during sync (S10-C)

**Pass Criteria:**
- OAuth tokens stored encrypted in DB (verify via `integration_credential.secret_json` is not plaintext)
- Conflict detected correctly when both sides modified
- Track-changes diff shows correct field modifications
- Resolution committed and replayed to QB correctly
- Invoice synced to QB as Estimate with correct line items

**Notes:** _______________

---

### P2-SC07 — Customer Communication Lifecycle (Template → Inbound Reply → Thread)

**Goal**: Validate the complete customer SMS workflow — outbound template, inbound reply, threading, owner visibility.

**Personas**: Tech (sends initial), Owner (sees thread), Customer (simulated)
**Estimated duration**: 30–40 minutes
**Status**: ☐

**Steps:**
1. Tech logs in on mobile → opens the `Scheduled - Outlet Installation` job
2. Taps **Send Customer Message** → selects `on_my_way` template
3. Preview shows rendered message with ETA → Tech confirms send
4. Verify `notification_outbox` row created (MockSmsCarrier — no real delivery)
5. Simulate inbound SMS reply: `POST /api/v1/webhooks/sms/inbound` with `{"from": "+12125551001", "body": "Thanks! See you soon."}`
6. Check tech's mobile `Customer Messages` section — inbound reply visible
7. Tech taps the thread → types a free-form reply: `"I'll be there in 10 minutes"`
8. Owner navigates to `Customers > John Smith > Comm History` → sees full thread (outbound + inbound + tech reply)
9. Owner also checks the Dashboard widget "Recent customer messages"

**Cross-Surface Integrations Tested:**
- Always-preview-before-send (S09-B)
- Bidirectional SMS threading (S09-C)
- Free-form tech reply (S09-F)
- Owner visibility across web comm history + dashboard widget (S09-B)
- MockSmsCarrier + webhook simulation (S09-C)

**Pass Criteria:**
- Preview shown before send (never bypassed)
- Inbound reply routed to correct tech thread (not another tech's thread)
- Thread keyed correctly on `(tenant_id, customer_id, tech_id, tenant_phone_number_id)`
- Owner sees full thread including the tech's free-form reply
- Customer's personal phone never receives anything (MockSmsCarrier confirms)

**Notes:** _______________

---

### P2-SC08 — Trial Expiration + Conversion (Paywall → Stripe Payment)

**Goal**: Validate the subscription lifecycle — trial expiration enforces a paywall, then tenant converts to a paid tier via Stripe.

**Personas**: Owner
**Estimated duration**: 20–30 minutes
**Status**: ☐

**Steps:**
1. DB: `UPDATE tenant SET trial_ends_at = NOW() - INTERVAL '1 day' WHERE id = '...0001'`
2. Trigger expiration task: `docker exec pilot_celery_worker celery -A tasks call tasks.tenants.enforce_trial_expirations`
3. Refresh web app → observe paywall
4. Attempt to create a new quote → confirm 402 paywall response
5. Attempt to send SMS → confirm blocked
6. Click **Upgrade Plan** → navigate to tier picker
7. Select Professional tier → enter Stripe test card `4242 4242 4242 4242`
8. Complete payment → verify tenant tier upgraded
9. Attempt to create a quote again → confirm write access restored

**Cross-Surface Integrations Tested:**
- Trial expiration enforcement (Celery task) (S13-B)
- 402 paywall at API layer (S13-B)
- Trial-to-paid conversion (Stripe Elements) (S13-D)
- Stripe webhook handler (subscription created event) (S13-D)
- Post-conversion write access restoration (S13-B)

**Pass Criteria:**
- Paywall appears after trial expiration
- Existing data readable during expired state (read-only confirmed)
- Write operations blocked at API layer (402 — not just UI-hidden)
- Stripe payment processes in test mode
- After payment: tier updated in DB, write access immediately restored

**Notes:** _______________

---

### P2-SC09 — Security Incident Response (Compromise → MFA Reset → Session Revoke)

**Goal**: Validate the security self-service tools — a user suspects account compromise, revokes all sessions, resets MFA, and regains exclusive control.

**Personas**: Owner (compromised account)
**Estimated duration**: 20–30 minutes
**Status**: ☐

**Steps:**
1. Log in as Tier 2 test owner from 3 different browsers (simulating attacker + 2 legit devices)
2. On Browser A (the "safe" device), navigate to `My Account > Security > Active sessions`
3. Verify 3 sessions listed with device + location info
4. Click **Revoke all other sessions** (keeps Browser A)
5. Attempt any action in Browser B and Browser C → confirm 401 returned → forced to login page
6. Observe that Browser A session is still valid
7. Change password from Browser A → confirm Browsers B and C (if re-logged in) would be revoked again
8. Navigate to MFA settings → click **Reset MFA** (owner self-reset requires password re-verify)
9. Re-enroll TOTP with a fresh authenticator registration

**Cross-Surface Integrations Tested:**
- Active sessions list + revoke (S01-G-03)
- Cross-device session invalidation on password change (S01-G-02)
- Owner self-reset of MFA (S01-C-06 variant)
- Audit log: session revoke events logged with actor

**Pass Criteria:**
- All 3 sessions visible with device labels
- "Revoke all other sessions" immediately invalidates Browsers B and C
- Browser A remains logged in after revocation
- Password change auto-revokes any newly-established sessions on other devices
- MFA re-enrollment succeeds after self-reset

**Notes:** _______________

---

### P2-SC10 — ETC Variance Alert → Course Correction (Mid-Job Profitability)

**Goal**: Validate the ETC capture and variance notification system — a tech's ETC indicates a budget overrun, owner is notified, and can take corrective action mid-job.

**Personas**: Tech (mobile) + Owner (web/mobile)
**Estimated duration**: 20–30 minutes
**Status**: ☐

**Steps:**
1. Create a quote for a job with a labor budget of 8 hours at $120/hr = $960 quoted labor
2. Convert quote to job → assign tech → schedule it
3. Tech clocks in (day 1) → clocks out with ETC: `"16 hours remaining"` (original estimate was 8 — this exceeds `etc_variance_owner_notify_pct` of 50%)
4. Observe: owner should receive a notification that projected cost exceeds quote by >50%
5. Owner opens the job's live profitability view → sees actuals + ETC vs. quoted budget
6. Owner navigates to the job on mobile → taps the Owner mobile status row for the job
7. Owner creates a change order to account for the additional scope
8. Tech clocks out next session with ETC: `"0 hours remaining"` (job now done)
9. Owner converts job to invoice including the change order

**Cross-Surface Integrations Tested:**
- ETC capture at clock-out (S05-B + S05-C)
- ETC variance owner notification (S09-A triggered by Celery)
- Live profitability view (S05-H)
- Change order creation by owner (S05-F)
- Invoice includes change order line items (S07-A)

**Pass Criteria:**
- ETC variance notification fires when projected hours exceed quoted by >50%
- Live profitability view accurately shows actuals + ETC projection
- Change order created and reflected in invoice total
- Audit log shows all ETC captures with `client_capture_at` timestamps

**Notes:** _______________

---

## Phase 3 — External Beta Testing (Contractor Cohort)

### Beta Tester Recruitment Criteria

Target cohort: **8 electrical contractors** matching these criteria:

- **Active electrical contractor** — sole proprietor or small team (1–5 employees); matches Pilot's primary persona
- **Currently using digital tools** — some QuickBooks experience; uses email and smartphone for work; NOT greenfield digital transformation
- **Geographically diverse** — target ≥3 different US states/tax jurisdictions to surface multi-jurisdiction tax setup edge cases
- **Mix of business sizes** — at least 2 solo operators + at least 2 small teams (gives Phase 1 + Phase 2 code path coverage)
- **Tom's existing electrical contractor network** — primary recruitment pool; relationships yield honest feedback
- **Willingness to use early-stage software** — not allergic to finding bugs; committed to providing direct feedback during a 4–8 week window
- **Not direct competitors of each other** — avoid awkward comparisons within the cohort

**Tester slots:**

| # | Persona | Size | QB? | Key Surface to Test |
|---|---------|------|-----|---------------------|
| 1 | Solo owner-operator | 1 person | Yes | Voice-first workflow, offline ops |
| 2 | Solo owner-operator | 1 person | No | Quote-to-cash baseline, voice |
| 3 | Small shop owner | 3–4 employees | Yes | Dispatch board, multi-user, QB sync |
| 4 | Small shop owner | 3–4 employees | Yes | MFA policy, RBAC, approval workflow |
| 5 | Owner + office manager | 2+ | Maybe | Customer comms, notifications |
| 6 | Owner + 1–2 techs | 3 people | No | Offline sync, field ops, mobile |
| 7 | Owner (different tax jurisdiction) | Any | Optional | Tax calculation, invoicing |
| 8 | Owner (rural — spotty connectivity) | Any | Optional | Offline resilience, deferred sync |

---

### Beta Onboarding Playbook

Each beta tester receives:

1. **Welcome email** (Tom-authored): why they were chosen, what to expect, how long, what's in it for them (lifetime discount, influence on product direction), support contact
2. **Onboarding call** (30–60 min Zoom per tester): live walkthrough of signup, key flows, voice command primer, "here's what to try first"
3. **Quick-start reference** (1-page PDF or Notion doc): top 5 things to try this week, where to report issues, how to reach Tom
4. **Beta cohort channel** (Slack or Discord): group channel for testers to share findings, ask each other questions, Tom monitors and responds
5. **Dedicated support email** (`beta@pilotfortrades.com` or Tom's direct email): for urgent bugs or access issues

**Onboarding sequence per tester:**
1. Tom sends welcome email + Calendly link for onboarding call
2. Tester signs up via the actual `/signup` wizard (with Tom monitoring the Cognito user pool)
3. Onboarding call: walkthrough + Q&A + first task assigned
4. Week 1 task: sign up, create first customer, create first quote by voice, send to yourself as the "customer"
5. Week 2: dispatch a job, have a tech (if they have staff) use the mobile app
6. Week 3–4: connect QuickBooks (if applicable), test customer comms, test offline if their work takes them underground

---

### Beta Success Criteria (Gates Soft Launch)

All of the following must be satisfied before proceeding to soft launch:

**Critical (blocking):**
- [ ] Zero unresolved 🔴 items from Phase 1 testing
- [ ] All 10 Phase 2 scenarios completed with zero 🔴 items
- [ ] No data loss incidents during beta (offline sync integrity confirmed)
- [ ] No security incidents (cross-tenant leakage, authentication bypass, etc.)
- [ ] No incorrect financial calculations (invoice totals, tax, margin) across ≥3 beta tenants

**Feature coverage:**
- [ ] At least 6 of 8 testers complete a full quote-to-invoice-to-payment cycle
- [ ] At least 5 testers send customer SMS via Pilot (validates Telnyx SMS in production)
- [ ] At least 3 testers demonstrate offline-to-online sync (validates Phase 3 Flow 7 in production)
- [ ] At least 2 testers exercise QuickBooks integration (validates §3.9 in production)
- [ ] At least 4 testers use voice commands for at least one workflow (validates Voice AI in production)

**Qualitative:**
- [ ] At least 6 of 8 testers indicate they'd continue using Pilot if it became paid
- [ ] Net Promoter Score (informal) positive — more testers would recommend than not
- [ ] No cohort-wide complaint about a specific surface or flow (isolated feedback is fine; systemic is a 🔴)

**Pre-launch hygiene (from Appendix B):**
- [x] 10DLC brand + campaign approved (SMS deliverable to real phones) — `CXXXXXX` approved 2026-08-07; loop proven 2026-08-10 with real texts to the author's own phone
- [x] Stripe production account configured and tested — live mode configured and validated; no real payment taken (env-mgmt §4.1.1)
- [ ] Domain `pilotfortrades.com` registered + email sender verified
- [ ] OAuth callback URLs registered (QB + Google Calendar)
- [ ] Legal copy finalized (ToS, Privacy, EULA)
- [ ] Help corpus beta-quality minimum (~60 articles)
- [x] Marketing landing page live at `pilotfortrades.com`

---

### Beta Duration & Iteration Cadence

- **Duration**: 4–8 weeks. Less than 4 weeks doesn't allow testers to build workflow rhythm. More than 8 weeks delays soft launch without proportional learning.
- **Weekly cohort touchpoint**: 30-minute Zoom or async Loom update from Tom — what was fixed this week, what to focus on next week, any changes to beta environment
- **Per-tester ad hoc**: Tom responds to individual bug reports within 1 business day; critical bugs within 4 hours
- **Continuous deployment**: fixes deployed to beta environment as ready (no formal release cycles — CI/CD to beta on merge)
- **No feedback backlog**: every piece of feedback acknowledged within 48 hours even if the fix isn't scheduled yet

---

### Feedback Infrastructure

- **In-product**: `Settings > Help & About > Send Feedback` (email intake to `support@pilotfortrades.com`)
- **Beta cohort channel**: Slack or Discord — async discussion, Tom monitors daily
- **GitHub Issues** (Tom-internal): Tom logs all beta feedback as issues; labels: `bug`, `ux-friction`, `feature-request`, `by-design`
- **Weekly summary**: Tom compiles a weekly "what I heard" summary and shares with cohort for validation
- **Exit survey**: 10-question Google Form sent at week 4 or 6 to capture structured feedback before soft launch decision

---

### Beta Exit Checklist

Complete this checklist before making the soft launch decision:

- [ ] All Beta Success Criteria above satisfied
- [ ] Exit survey responses collected from ≥6 of 8 testers
- [ ] All critical bugs (🔴 from Phase 1 or Phase 2) resolved and re-verified
- [ ] All ⚠️ items from Phase 1 reviewed — either fixed or explicitly accepted as known issues
- [ ] Staging environment validated (Appendix C items — GPU latency, real SMS, real OAuth)
- [ ] Production deployment smoke test passed (rolling deploy + health check)
- [ ] Monitoring + alerting operational (CloudWatch dashboards, alerting Tom on incidents)
- [ ] Support email + response SLA confirmed (Tom committed to 1 business day / 4 hours critical)
- [x] Launch plan created — `pilot-launch-plan.md` (the living v6.0 tracker)
- [ ] Tom makes the call: **GO / NO-GO for soft launch**

---

## Appendix A — Seed Data Reference

*(See `dev-docs/seed-data/seed-scripts-usage-reference-analysis.md` §7 for full reference)*

**Summary of seeded data available for testing:**

| Entity | Count | Notes |
|--------|-------|-------|
| Customers | 5 | John Smith, Mary Johnson, Apex Commercial LLC, Bob Davis (prospect), Inactive Customer |
| Sites | 3 | Smith Residence (Brooklyn NY), Johnson site (Austin TX), Apex HQ (Chicago IL) |
| Pricebook Items | 5 | Standard Outlet Install, 200A Panel Upgrade, 15A Breaker, EMT Conduit, Residential Permit |
| Draft Quote | 1 | John Smith → Smith Residence; $240.00 (2 line items) |
| Jobs | 5 | Scheduled, In Progress, Completed ×2, Draft |
| Tech Assignments | 3 | On 3 of the 5 jobs |
| PTO Block | 1 | Technician: next Friday 8am–5pm |

**Data gaps for Phase 1 testing (create via UI during testing):**

| Missing Entity | Needed For | Creation Method |
|----------------|-----------|-----------------|
| Invoices (issued, paid, void) | P1-S07 | Create via UI from existing quotes/jobs |
| SMS threads + inbound messages | P1-S09-D | Create via MockSmsCarrier + test inbound webhook |
| QB conflict records | P1-S10-D | Manually create via API or DB insert for conflict UI testing |
| Calendar conflict records | P1-S06-H | Trigger via bi-directional sync with calendar conflict scenario |
| MFA-enrolled users | P1-S01-C | Enroll during test session |
| Voice conversation sessions | P1-S12-B | Create via voice command during testing |
| Trial-expired tenant state | P1-S13-B | Manually set `trial_ends_at` to past date via DB for this test |
| Help chat sessions | P1-S16-A | Create during help system testing |

---

## Appendix B — Pre-Launch Hygiene Gaps

The following items are **not tested** in Phase 1 (local environment) and must be validated in staging before external beta:

> **2026-08-20 status sync**: items verified complete since v1.0 are marked ✅; remaining ☐ items still require staging/GA validation.

| Item | Status | Blocks |
|------|--------|--------|
| A2P 10DLC brand + campaign registration | ✅ Done 2026-08-07 — `CXXXXXX` approved; live carrier loop proven 2026-08-10 | Real SMS deliverability (Phase 3) |
| Stripe production account configured | ✅ Done 2026-08 — three-account structure + bootstrap script live; live mode configured and validated; no real payment taken (env-mgmt §4.1.1) | Real subscription billing (Phase 3) |
| Telnyx production phone number pool | ✅ Done 2026-08-10 — production number live on `CXXXXXX` | Real SMS (Phase 3) |
| QuickBooks Developer App OAuth callbacks | ☐ Pending | QB OAuth without ngrok (Phase 3) |
| Google Cloud Console OAuth callbacks | ☐ Pending | Calendar OAuth without ngrok (Phase 3) |
| Email sender domain SPF/DKIM/DMARC | ☐ Pending | Real email delivery (Phase 3) |
| Help corpus (~60 markdown articles) | ☐ Pending | RAG retrieval quality (Phase 3) |
| Legal copy (ToS, Privacy, EULA) | ☐ Pending | Signup wizard legal step (Phase 3) |
| Mobile app store listings + bundle IDs | ☐ Pending | TestFlight / Play Store internal (Phase 3) |

---

## Appendix C — Staging-Only Validations

The following test cases **cannot be validated locally** and require the staging environment (AWS ECS Fargate + RDS + ElastiCache + EC2 GPU):

| Validation | Why Local is Insufficient |
|-----------|--------------------------|
| Voice AI latency SLO (p95 < 2 seconds) | CPU inference locally is 5–20s; requires NVIDIA T4 GPU on `g4dn.xlarge` |
| Real SMS delivery + opt-out webhook | Requires Telnyx production number + 10DLC approval |
| Real QuickBooks OAuth (no ngrok) | Requires registered HTTPS callback URL at `pilotfortrades.com` |
| Real Google Calendar OAuth (no ngrok) | Same as QB OAuth |
| Real email delivery (SendGrid) | Requires verified sender domain |
| Celery Beat scheduled task execution | Verify actual task firing intervals (audit archival, dunning, trial expiration) |
| RDS Multi-AZ failover | Requires production AWS environment |
| Rolling-deploy smoke test | Requires ECS + ALB |
| Push notification delivery (APNs/FCM) | Requires physical device + registered app bundle |
