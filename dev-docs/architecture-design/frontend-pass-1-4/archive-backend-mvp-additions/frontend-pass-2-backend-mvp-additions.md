# AevoFab Backend MVP Additions

**Status**: Running list — updated as UI design progresses
**Last Updated**: April 22, 2026 (Pass 2 complete)
**Purpose**: Track backend/database/API changes required by UI design decisions
**Handoff**: This document is the authoritative list of backend work required before UI coding begins

---

## Overview

As UI design progresses through Passes 2, 3, and 4, decisions surface that require backend changes beyond what's currently in `mvp-arch.md` and the PRD. This document captures those requirements in one place so the dev team has a single source of truth for MVP backend work.

**Workflow**: Each addition below is triggered by a specific design decision. When UI design is complete (end of Pass 4), this document is frozen and becomes the backend work plan. Tom completes backend MVP work before UI coding begins.

---

## Additions from Pass 2

### A1. New Domain: Scheduling & Dispatch (PRD Section 3.14)

**Triggered by**: Pass 2 sitemap exposed that scheduling is implicit in current PRD but not enumerated as MVP domain.

**Scope**:
- New domain section in PRD (Section 3.14)
- Database schema: `schedule_block`, `tech_availability`, `route_optimization_result` (or equivalent naming)
- API endpoints: CRUD for schedules, availability, conflict detection endpoint, route sequencing endpoint
- Celery tasks: dispatch conflict detection, route optimization (deferred async), tech notification on assignment change
- Integration: map provider (Google Maps API or Mapbox) for distance/time matrix

**MVP feature minimum**:
- Job scheduling with tech assignment, time window, site coordinates
- Tech availability (working hours, PTO, unavailable blocks)
- Dispatch conflict detection (double-booking, infeasible travel time)
- Route sequencing (daily job order optimization)
- Tech notifications on assignment and changes
- Customer-facing ETA data feed (consumed by Communicate feature — A4 below)

**Deferred to Phase 2**: recurring jobs, skill-based routing, crew assignments, predictive scheduling, customer self-service booking.

**Effort estimate**: Large — this is the single biggest backend addition. Plan for 3–4 weeks of backend work.

---

### A2. Quote Approval Workflow

**Triggered by**: Quote approval workflow decision in Pass 2.

**Scope**:
- Quote state machine update: add `pending_approval` and `approved` states
  - Full state machine: `draft → pending_approval → approved → sent → accepted / declined / expired → converted`
  - When approval setting is OFF, tech-created quotes skip directly from `draft → sent`
- New tenant setting: `require_approval_for_tech_quotes`
  - Default ON for multi-user tenants, OFF for solo operators
  - Lives in `tenant_settings` or equivalent
- API endpoint: `POST /api/v1/quotes/{id}/submit-for-approval`
- API endpoint: `POST /api/v1/quotes/{id}/approve` (and `/reject`)
- Notification: push + email to owner when tech submits quote for approval
- Audit log: record approval/rejection with approver identity and any modifications

**Affected existing features**: quote version control (must handle approval modifications as new version), RBAC (tech role needs new `quote.submit_for_approval` permission; owner/accountant roles need `quote.approve`)

**Effort estimate**: Medium — 3–5 days.

---

### A3. Time-Limited Discounts with Margin Cap

**Triggered by**: Owner-only discount action in Pass 2 (mobile + web).

**Scope**:
- New tenant setting: `max_discount_pct_owner` (default 15%)
- New quote line item type: `discount_line` (or extend existing line items with `is_discount` flag)
  - Fields: `discount_pct`, `discount_amount_cents`, `discount_expires_at`
- Applies as new immutable quote version (leverages existing version control)
- Celery Beat task: transition discount to expired at `discount_expires_at`
- API validation: reject requests where `discount_pct > tenant.max_discount_pct_owner`
- API endpoint: `POST /api/v1/quotes/{id}/apply-discount`
- RBAC: `quote.apply_discount` permission — owner/admin only, not tech

**Effort estimate**: Small-Medium — 2–3 days.

---

### A4. Templated Customer Communications

**Triggered by**: Customer comms feature in Pass 2 (tech-to-customer messaging).

**Scope**:
- New database table: `customer_communication`
  - Fields: tenant_id, customer_id, job_id (nullable), sender_user_id, template_code, rendered_message, channel (sms/email), status, sent_at
  - Full audit trail per message sent
- New lookup table: `communication_template`
  - Fields: template_code, channel, subject (for email), body_template (with placeholders)
- Template variable substitution engine (ETA from route data, customer name, job number, etc.)
- API endpoint: `POST /api/v1/communications/send` with template_code and variables
- Voice intent handler: `send_customer_communication` — parses "Tell Johnson I'm 20 out" into template_code + variables
- Integration: uses existing `notification_outbox` for reliable dispatch
- Web route: `Customers > [customer] > Comm history` reads from this table

**MVP template set**:
- `on_my_way` — "On my way, ETA [eta]"
- `running_late` — "Running [minutes] min late"
- `arrived` — "Arrived, starting work"
- `job_complete` — "Job complete, invoice to follow"
- `parts_delay` — "Parts delay, will update when resolved"
- `confirm_appointment` — "Please confirm appointment [date/time]"

**Effort estimate**: Medium — 4–6 days.

---

### A5. Reports Domain with Pin-to-Dashboard

**Triggered by**: Reports promoted to top-level nav with dashboard customization in Pass 2.

**Scope**:
- New API endpoints per report type (all read-only aggregations):
  - `GET /api/v1/reports/profitability`
  - `GET /api/v1/reports/revenue`
  - `GET /api/v1/reports/ar-aging`
  - `GET /api/v1/reports/tech-productivity`
  - `GET /api/v1/reports/tax-liability`
  - `GET /api/v1/reports/voice-analytics`
- All reports support common query params: date_range, tenant_scope (auto), filter_by, group_by
- Dashboard customization:
  - New table: `user_dashboard_widget`
    - Fields: user_id, tenant_id, widget_type, widget_config_json, position_x, position_y, width, height
  - API: `GET/POST/PATCH/DELETE /api/v1/dashboard/widgets`
- Report caching: consider materialized views or Redis-cached aggregates for performance (not blocking; add if needed)

**Effort estimate**: Medium-Large — 5–7 days (individual reports are small; the mass of them adds up).

---

### A6. Voice AI Feedback Loop

**Triggered by**: Voice AI feedback mechanism decision in Pass 2.

**Scope**:
- New table: `voice_feedback`
  - Fields: tenant_id, user_id, transcript_id, original_transcription, corrected_text, intent_misparsed (boolean), feedback_notes
- API endpoint: `POST /api/v1/voice/feedback` — owner flags a transcript as misrecognized, provides correction
- API endpoint: `GET /api/v1/voice/transcripts` — searchable transcript history
- API endpoint: `GET /api/v1/voice/feedback` — list flagged items for training export
- Training data export: nightly Celery task writes corrected pairs to S3 in model fine-tuning format (format TBD based on training pipeline choice)
- RBAC: `voice.provide_feedback` permission — owner/admin only

**Strategic note**: This is the data pipeline for future Llama fine-tuning. Treat it as a first-class feature, not a debug tool. The data it captures creates a long-term moat.

**Effort estimate**: Medium — 3–4 days (excludes fine-tuning pipeline, which is Phase 2).

---

### A7. Field Mode Support (Web App Infrastructure)

**Triggered by**: Tablet strategy decision in Pass 2 — Field mode infrastructure in MVP.

**Scope**:
- New user preference: `field_mode_enabled` (boolean, defaults off for owner, on for technician on tablet viewport)
- Viewport detection: server-side via user agent + client-side viewport measurement
- Route-level RBAC enforcement: technician role + field mode = hide admin routes at API and UI layer
- API endpoint: `PATCH /api/v1/users/me/preferences` — toggle field_mode_enabled
- Backend validation: prevent tech + field mode from calling admin endpoints (belt-and-suspenders; UI already hides them)

**Note**: Most of this is frontend work. Backend scope is minimal — just the preference field and the route-level guards.

**Effort estimate**: Small — 1–2 days backend.

---

### A8. Communication History on Customer

**Triggered by**: Customer Comm history route under Customers section (Pass 2).

**Scope**: Mostly covered by A4 (communications table). This item is just the API endpoint to read the history by customer:
- `GET /api/v1/customers/{id}/communications` with pagination

**Effort estimate**: Trivial — half a day, folds into A4.

---

## Additions from Pass 3 (placeholder)

*To be populated during Pass 3 (key flow prototyping).*

---

## Additions from Pass 4 (placeholder)

*To be populated during Pass 4 (onboarding, states, polish).*

---

## Summary of New Tenant Settings

| Setting | Default | Purpose |
| :--- | :--- | :--- |
| `require_approval_for_tech_quotes` | ON (multi-user), OFF (solo) | Quote approval workflow |
| `max_discount_pct_owner` | 15% | Margin cap for owner-applied discounts |

## Summary of New RBAC Permissions

| Permission | Roles | Purpose |
| :--- | :--- | :--- |
| `quote.submit_for_approval` | technician | Submit tech-created quote for owner review |
| `quote.approve` | owner, accountant | Approve or reject pending quotes |
| `quote.apply_discount` | owner, accountant | Apply time-limited discounts within margin cap |
| `voice.provide_feedback` | owner, accountant | Flag voice misrecognitions, provide corrections |
| `schedule.manage` | owner, accountant | Create/modify schedule blocks, assign techs |
| `schedule.view_own` | technician | View own assigned schedule only |

## Summary of New Database Tables

From Pass 2:
- `schedule_block` (A1)
- `tech_availability` (A1)
- `route_optimization_result` (A1) — or cached/transient
- `customer_communication` (A4)
- `communication_template` (A4)
- `user_dashboard_widget` (A5)
- `voice_feedback` (A6)

## Rough Effort Estimate (Pass 2 Additions)

| Item | Size | Days |
| :--- | :--- | :---: |
| A1 Scheduling & Dispatch | Large | 15–20 |
| A2 Quote Approval | Medium | 3–5 |
| A3 Time-Limited Discounts | Small-Medium | 2–3 |
| A4 Customer Communications | Medium | 4–6 |
| A5 Reports + Dashboard Widgets | Medium-Large | 5–7 |
| A6 Voice Feedback | Medium | 3–4 |
| A7 Field Mode Backend | Small | 1–2 |
| **Total** | | **33–47 days** |

Plus Pass 3 and Pass 4 additions to come. Plan for approximately 6–8 weeks of backend work after UI design is complete, before UI implementation begins.

---

*This document is regenerated at the end of each design pass. See `pass-2-design-spec.md` for the UI decisions that triggered each addition.*
