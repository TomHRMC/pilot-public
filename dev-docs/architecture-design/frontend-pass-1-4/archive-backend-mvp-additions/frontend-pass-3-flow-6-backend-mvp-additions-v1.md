# AevoFab Backend MVP Additions

**Status**: Running list — updated as UI design progresses
**Version**: v3 (supersedes v2)
**Last Updated**: April 25, 2026 (Pass 3 Flow 6 complete)
**Purpose**: Track backend/database/API changes required by UI design decisions
**Handoff**: This document is the authoritative list of backend work required before UI coding begins

---

## Table of Contents

- [AevoFab Backend MVP Additions](#aevofab-backend-mvp-additions)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
    - [MVP Additions Already Implemented](#mvp-additions-already-implemented)
    - [Still To Implement](#still-to-implement)
    - [A2. Quote Approval Workflow](#a2-quote-approval-workflow)
    - [A3. Time-Limited Discounts with Margin Cap](#a3-time-limited-discounts-with-margin-cap)
    - [A4. Templated Customer Communications](#a4-templated-customer-communications)
    - [A5. Reports Domain with Pin-to-Dashboard](#a5-reports-domain-with-pin-to-dashboard)
    - [A6. Voice AI Feedback Loop](#a6-voice-ai-feedback-loop)
    - [A7. Field Mode Support (Web App Infrastructure)](#a7-field-mode-support-web-app-infrastructure)
    - [A8. Communication History on Customer](#a8-communication-history-on-customer)
  - [Additions from Pass 3 Flow 1 (Voice Quote Creation)](#additions-from-pass-3-flow-1-voice-quote-creation)
    - [A9. Session Number Computation](#a9-session-number-computation)
    - [A10. Voice Command Grammar for Session Management](#a10-voice-command-grammar-for-session-management)
    - [A11. Ollama-Generated Session Titles](#a11-ollama-generated-session-titles)
    - [A12. Conversation Message Structured Content Payload with Live/Snapshot Modes](#a12-conversation-message-structured-content-payload-with-livesnapshot-modes)
    - [A13. Voice Persona Tone Configuration (Post-MVP — Captured for Roadmap)](#a13-voice-persona-tone-configuration-post-mvp--captured-for-roadmap)
  - [Additions from Pass 3 Flow 2 (Real-Time Job Profitability)](#additions-from-pass-3-flow-2-real-time-job-profitability)
    - [A14. ETC (Estimate to Complete) Capture System](#a14-etc-estimate-to-complete-capture-system)
    - [A15. Chart-or-Table Threshold Setting](#a15-chart-or-table-threshold-setting)
    - [A16. ETC Variance Notification System](#a16-etc-variance-notification-system)
    - [A17. Margin Bucket Configuration](#a17-margin-bucket-configuration)
  - [Additions from Pass 3 Flow 3 (Dispatch Board)](#additions-from-pass-3-flow-3-dispatch-board)
    - [A18. Tech Color Assignment \& Configuration](#a18-tech-color-assignment--configuration)
    - [A19. Dispatch Board API Endpoints (Optimistic Locking + Real-Time Updates)](#a19-dispatch-board-api-endpoints-optimistic-locking--real-time-updates)
    - [A20. Drive-Time Caching Verification](#a20-drive-time-caching-verification)
  - [Additions from Pass 3 Flow 4 (Customer Communications)](#additions-from-pass-3-flow-4-customer-communications)
    - [A21. Per-Message Channel Override](#a21-per-message-channel-override)
    - [A22. Voice Intent Grammar for Customer Communications](#a22-voice-intent-grammar-for-customer-communications)
    - [A23. Communication Preview Endpoint (Pre-Send Validation)](#a23-communication-preview-endpoint-pre-send-validation)
  - [Additions from Pass 3 Flow 5 Architectural Pre-Work (Quote Line Item Architecture)](#additions-from-pass-3-flow-5-architectural-pre-work-quote-line-item-architecture)
    - [A24. Quote Line Item Schema Extension (Visibility + Hierarchy)](#a24-quote-line-item-schema-extension-visibility--hierarchy)
    - [A25. Quote Template Schema with Style and Versioning](#a25-quote-template-schema-with-style-and-versioning)
    - [A26. System Template Update Notification Flow](#a26-system-template-update-notification-flow)
    - [A27. Save Quote as Template](#a27-save-quote-as-template)
    - [A28. Multi-Line Description Editing UI Support](#a28-multi-line-description-editing-ui-support)
  - [Additions from Pass 3 Flow 5 (Quote Approval Workflow)](#additions-from-pass-3-flow-5-quote-approval-workflow)
    - [A29. Pending Edit Storage During Owner Review](#a29-pending-edit-storage-during-owner-review)
    - [A30. Approval Comment \& Annotation System](#a30-approval-comment--annotation-system)
    - [A31. Voice Intent Grammar for Approval Actions](#a31-voice-intent-grammar-for-approval-actions)
  - [Additions from Pass 3 Flow 6 (Calendar Conflict Resolution)](#additions-from-pass-3-flow-6-calendar-conflict-resolution)
    - [A32. Calendar Conflict Diff Payload](#a32-calendar-conflict-diff-payload)
    - [A33. Pre-Resolution Staleness Check](#a33-pre-resolution-staleness-check)
    - [A34. Auto-Expiry of Stale Conflicts (with Platform-Default + Tenant-Override Settings Infrastructure)](#a34-auto-expiry-of-stale-conflicts-with-platform-default--tenant-override-settings-infrastructure)
    - [A35. Mobile Pending-Conflicts Status \& Notification Rate Limiting](#a35-mobile-pending-conflicts-status--notification-rate-limiting)
    - [A36. Voice Intent Grammar for Calendar Conflicts](#a36-voice-intent-grammar-for-calendar-conflicts)
  - [Summary of New Tenant Settings (Pass 2 + Pass 3)](#summary-of-new-tenant-settings-pass-2--pass-3)
  - [Summary of New Platform Settings (NEW in Pass 3 Flow 6)](#summary-of-new-platform-settings-new-in-pass-3-flow-6)
  - [Summary of New RBAC Permissions (Pass 2 + Pass 3)](#summary-of-new-rbac-permissions-pass-2--pass-3)
  - [Rough Effort Estimate (Remaining MVP Additions)](#rough-effort-estimate-remaining-mvp-additions)


---

## Overview

As UI design progresses through Passes 2, 3, and 4, decisions surface that require backend changes beyond what's currently in `mvp-arch.md` and the PRD. This document captures those requirements in one place so the dev team has a single source of truth for MVP backend work.

**Workflow**: Each addition below is triggered by a specific design decision. When UI design is complete (end of Pass 4), this document is frozen and becomes the backend work plan. Tom completes backend MVP work before UI coding begins.

**Status tracker**:
- Pass 2 additions (A1–A8): previously documented; A1 Scheduling & Dispatch has since been implemented per `frontend-pass-2-sched-feat-plan.md`
- Pass 3 Flow 1 additions (A9–A13): documented in this file
- Pass 3 Flow 2 additions (A14–A17): documented in this file
- Pass 3 Flow 3 additions (A18–A20): documented in this file
- Pass 3 Flow 4 additions (A21–A23): documented in this file
- Pass 3 Flow 5 architectural pre-work (A24–A28): documented in this file — see also `quote-line-item-architecture.md`
- Pass 3 Flow 5 additions (A29–A31): documented in this file
- Pass 3 Flow 6 additions (A32–A36): this update — introduces the new platform-default + tenant-override settings pattern via A34

---

### MVP Additions Already Implemented

- **A1 Scheduling & Dispatch** — implemented per `frontend-pass-2-sched-feat-plan.md` (completed 4-24-2026)

### Still To Implement

- **A2 Quote Approval Workflow** — quote state machine extensions, `require_approval_for_tech_quotes` tenant setting, approval endpoints
- **A3 Time-Limited Discounts** — owner-only with margin cap (`max_discount_pct_owner` tenant setting)
- **A4 Templated Customer Communications** — `customer_communication`, `communication_template` tables; voice-triggerable
- **A5 Reports + Dashboard Widgets** — six report endpoints, pin-to-dashboard customization
- **A6 Voice AI Feedback** — `voice_feedback` table, training data export pipeline
- **A7 Field Mode Backend** — `field_mode_enabled` user preference, route-level RBAC enforcement
- **A8 Communication History on Customer** — API endpoint folding into A4

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

## Additions from Pass 3 Flow 1 (Voice Quote Creation)

### A9. Session Number Computation

**Triggered by**: Per-day-reset session numbering for voice addressability in the session history drawer.

**Scope**:
- Derived property (not a stored column). Computed via SQL window function at query time.
- Session number = `ROW_NUMBER() OVER (PARTITION BY DATE(created_at AT TIME ZONE tenant.timezone), user_id ORDER BY created_at ASC)`
- Tenant timezone must be honored — midnight rollover is local, not UTC
- API response: `GET /api/v1/voice/sessions` returns session number alongside each session record
- Voice addressability:
  - "Chat 2" → today's session #2 for current user
  - "Yesterday's chat 3" → day-scoped lookup
  - Missing reference → AI asks rather than guesses (see A10)

**Performance note**: for users with many sessions per day, consider materialized view or cached daily number if query becomes expensive at scale. Not a concern at MVP launch volume; flag for monitoring.

**Effort estimate**: Small — 1 day (query construction + test coverage).

---

### A10. Voice Command Grammar for Session Management

**Triggered by**: Voice-based session operations (rename, delete, open, query).

**Scope**:
- Additions to `voice_action_router.py` handler registry:
  - `rename_session` — updates `conversation_session.context_summary`
  - `delete_session` — soft-deletes a session (with confirm-as-turn flow)
  - `open_session` — switches the active session in the UI
  - `query_session_summary` — AI reads back a session's summary + recent messages
- Each handler validates the numeric reference against the per-day window (A9)
- Missing-reference path: handler returns a disambiguation response for the AI to voice, rather than executing on a guess
- Confirm-as-turn implementation for destructive actions: `delete_session` returns a pending-confirmation state in `context_window_json`; next user turn with affirmative intent commits, any other response cancels

**Intent → action mapping** (authoritative list for voice_action_router.py):

| Intent | Example | Target |
| :--- | :--- | :--- |
| `rename_session` | "rename chat 2 to Johnson panel" | `conversation_session.context_summary` |
| `delete_session` | "delete chat 4" | `conversation_session.is_active = FALSE` |
| `open_session` | "open chat 3" | UI state change (client-side) |
| `query_session_summary` | "what did I work on in chat 1?" | Read-only response |

**Effort estimate**: Small-Medium — 2–3 days (handler implementations + test coverage for each + disambiguation flows).

---

### A11. Ollama-Generated Session Titles

**Triggered by**: `conversation_session.context_summary` populated automatically after the first meaningful turn.

**Scope**:
- New Celery task: `generate_session_title` — enqueued after the first substantive assistant message in a session
- Calls Ollama with a prompt pattern like: "Summarize this brief conversation in 3-5 words, suitable as a scannable title in a chat history list. Conversation: [...]"
- Updates `conversation_session.context_summary` with the result
- Only fires once per session, and only if `context_summary` is still NULL (user-set titles take precedence)
- Fallback: if Ollama fails or times out, `context_summary` remains NULL; UI shows "Untitled session" with the first few words of the first user message as a soft fallback

**Configuration** (for future voice persona tone slider — see A13):
- Prompt template is a tenant-level config value (default conservative phrasing for MVP)
- Template variable placeholder: `{tone}` → currently hardcoded to "neutral, descriptive"

**Effort estimate**: Small — 1–2 days (Celery task + prompt engineering + tests).

---

### A12. Conversation Message Structured Content Payload with Live/Snapshot Modes

**Triggered by**: Inline rendering of structured artifacts (quote cards) as assistant messages within the conversation thread, plus historical accuracy requirements for completed sessions and cross-context quote viewing.

**Scope**:
- Extend `conversation_message` (schema decision left to dev team: add `structured_content JSONB` column OR leverage existing content_text with a type discriminator) to support structured assistant output
- Assistant turns can carry either plain text OR a structured payload:
  - `artifact_type` — e.g., `quote_preview`, `job_preview`, `schedule_preview`, `comm_preview`
  - `entity_id` — the referenced entity (e.g., quote.id)
  - `entity_version_id` — nullable; populated only for snapshot mode
  - `render_mode` — `live` | `snapshot`
  - `snapshot_payload` — nullable JSONB; populated only for snapshot mode, contains frozen entity state as of capture time
  - `render_hints` — UI hints like which line items are newly added (for visual differentiation)
- Mobile app renders based on `render_mode`:
  - `live` → fetch current entity state by `entity_id`
  - `snapshot` → render directly from `snapshot_payload`
- Plain text messages render as standard chat bubbles

**Live vs snapshot logic**:

| When created | Initial render_mode |
| :--- | :--- |
| New assistant turn during active authoring (pre-submission) | `live` |
| New assistant turn in a session where quote was already submitted | `snapshot` |

**Freeze triggers — two events only**:

1. **Submission** (primary trigger): when the user successfully executes Submit for approval (tech) or Send (owner) on a quote, a synchronous freeze operation runs before the API call returns. This iterates all quote_preview messages in the session with `render_mode = 'live'`, captures the final submitted `quote_version` state as `snapshot_payload`, and flips `render_mode` to `snapshot`. The user is returned to the home screen only after the freeze is complete. No Celery task — synchronous for consistency (the freeze must be visible before the user can navigate away and return).

2. **New artifact turn during active authoring** (secondary trigger): when the assistant emits a new quote_preview turn (e.g., after "add five breakers"), the prior quote_preview messages in the same session freeze to `snapshot` at that moment, capturing their state as of that moment. Only the newly emitted turn remains `live`. This preserves the "each card shows what it showed at that moment" principle without waiting for submission.

**Not a trigger**: session age, session inactivity timeout, archival, or any abstract "session completion" notion. Abandoned sessions keep their `live` cards until either (a) the user returns and submits, or (b) the underlying draft quote is garbage-collected by retention policy. If the quote is garbage-collected, the UI renders the message as "this quote was discarded" rather than attempting to render from a dangling reference.

**Critical correctness constraint**: A message never transitions from `snapshot` back to `live`. Once frozen, always frozen. This guarantees historical accuracy.

**Rationale**: Treating structured artifacts as conversation messages (rather than separate out-of-band UI state) preserves the chat metaphor and makes session replay correct. The live-vs-snapshot split honors the two distinct mental models users have: "the current thing I'm building" (live, ephemeral) vs "what the AI showed me at that moment" (snapshot, immutable). This also aligns with the existing `quote_version` immutability architecture.

**Historical context consistency**: the same `snapshot` rendering contract is used for quotes viewed from customer records, quote lists, approval queues, and audit surfaces. A single rendering primitive covers both "scrollback in a session" and "historical quote review from customer page" — neither should ever show live state against an immutable version.

**Effort estimate**: Medium — 4–6 days (schema decision, rendering contract, freeze-task implementation, scrollback freeze-on-new-turn logic, API changes, mobile renderer, comprehensive tests for the state transitions).

---

### A13. Voice Persona Tone Configuration (Post-MVP — Captured for Roadmap)

**Triggered by**: Future UX refinement — giving tenants control over AI personality tone.

**Scope**:
- Tenant setting: `voice_persona_tone` (numeric scale 0–100, default 50; or enum `conservative | balanced | playful`)
- Affects:
  - Ollama prompts for session title generation (A11)
  - Ollama prompts for assistant turn responses
  - Empty-state welcome text in the Voice tab
- Owner-configurable from web Settings > Voice AI > Configuration
- Client-side preview: owner hears three example interactions at different slider positions before committing

**Status**: Post-MVP. Noted here so it doesn't get lost when we're heads-down on MVP.

**Effort estimate**: Small — 2–3 days (post-MVP).

---

## Additions from Pass 3 Flow 2 (Real-Time Job Profitability)

### A14. ETC (Estimate to Complete) Capture System

**Triggered by**: Real-time projected margin calculation requires forward-looking labor estimates beyond actuals-to-date. Captures the tech's own assessment of remaining work to convert lagging margin signals into leading ones.

**Scope**:

**Schema changes**:
- New columns on `job_time_entry` (or equivalent existing time-tracking table):
  - `hours_remaining_estimate NUMERIC(6,2) NULL` — tech's ETC at the moment of this time entry
  - `hours_remaining_was_overridden BOOLEAN NULL` — true if tech changed the auto-populated value
  - `override_note TEXT NULL` — required when override increases hours by more than tenant threshold
- New optional FK `quote_line_id UUID NULL → quote_line(id)` on `job_time_entry` — when present, ETC is per-task; when null, ETC is per-job

**Mobile UX**:
- ETC prompt appears at two trigger points (per spec):
  1. **End-of-day clock-out** — before the tech can finalize their workday, prompt for ETC on each job they touched today
  2. **Mid-day task completion** — when tech marks a labor line complete and moves to the next one, prompt for ETC on the next task
- Auto-populated value = `quoted_hours - (prior_logged_hours + just-entered_hours)`
- One-tap "Confirm" button when value is unchanged
- Override flow:
  - Increase > tenant threshold → require note (cannot save without)
  - Decrease > tenant threshold → optional note
  - Within ±threshold → optional note regardless of direction

**Latest-ETC query pattern** for projected margin computation:

```sql
-- Per task
SELECT DISTINCT ON (job_id, quote_line_id)
       job_id, quote_line_id, hours_remaining_estimate, created_at
  FROM job_time_entry
 WHERE tenant_id = :tenant_id
   AND hours_remaining_estimate IS NOT NULL
 ORDER BY job_id, quote_line_id, created_at DESC;

-- Per job (when no quote_line_id)
SELECT DISTINCT ON (job_id)
       job_id, hours_remaining_estimate, created_at
  FROM job_time_entry
 WHERE tenant_id = :tenant_id
   AND quote_line_id IS NULL
   AND hours_remaining_estimate IS NOT NULL
 ORDER BY job_id, created_at DESC;
```

**Backward compatibility**: tenants existing pre-implementation have time entries without ETC values. The projected margin calculation for those jobs falls back to: `projected_total_hours = MAX(quoted_hours, hours_worked_so_far)`. Once any tech enters an ETC for that job, the system uses the ETC.

**API endpoints**:
- `POST /api/v1/jobs/{id}/time-entries` — accepts new ETC fields
- `GET /api/v1/jobs/{id}/projected-margin` — computed projected margin endpoint

**Effort estimate**: Medium-Large — 6–8 days (schema, mobile prompt UX, validation logic, latest-ETC query patterns, projected margin computation).

---

### A15. Chart-or-Table Threshold Setting

**Triggered by**: Profitability page's chart-vs-table threshold pattern; will be reused across all reports.

**Scope**:
- Tenant setting: `report_chart_threshold` — integer (default 8)
- Applied at API layer: report endpoints return `display_mode: 'chart' | 'table'` based on returned row count vs threshold
- Frontend reads this and renders accordingly
- Editable via Settings → Reports

**Effort estimate**: Trivial — half a day. Just a setting and an API computation.

---

### A16. ETC Variance Notification System

**Triggered by**: Owner needs immediate notification when projected job hours significantly exceed original quote.

**Scope**:
- Tenant setting: `etc_variance_owner_notify_pct` — integer percent (default 50)
- Tenant setting: `etc_variance_note_required_pct` — integer percent (default 10)
- Trigger: every time a `job_time_entry` is saved with an ETC value, evaluate if the projected total exceeds the threshold
- Comparison: `(current_projected_total_hours / original_quoted_hours - 1) * 100`
- When threshold exceeded AND owner has not already been notified for this job's variance:
  - Push notification to owner
  - Email to owner (using existing notification_outbox infrastructure from Pass 2 A4)
  - Mark job as `variance_owner_notified_at` (prevents repeat notifications until variance worsens further)
- Notification content includes: job name, customer, original quote, current projected, percent over

**Re-notification logic**: if variance worsens past the next threshold band (e.g., from 50% over to 80% over), notify again. Implementation detail to be designed by dev team — suggest tracking last notified percentage and re-notifying when it grows by another threshold-amount.

**Effort estimate**: Small-Medium — 2–3 days.

---

### A17. Margin Bucket Configuration

**Triggered by**: Tenant-configurable margin boundaries for the profitability bar charts.

**Scope**:
- Tenant setting: `margin_bucket_boundaries` — JSON array of integers (default `[10, 20, 30]`)
- Tenant setting: `margin_target_pct` — integer (default 20) — used for "below target" indicators
- API: report endpoints use these boundaries when computing bucket counts/revenue
- Frontend: chart axis labels reflect tenant's actual boundaries
- Settings UI: Settings → Reports → Margin buckets — edit boundaries with preview of current data redistributed

**Validation**: boundaries must be ascending integers between 0 and 100. Length determines bucket count (3 boundaries = 4 buckets, 2 boundaries = 3 buckets, etc.).

**Effort estimate**: Small — 1–2 days.

---

## Additions from Pass 3 Flow 3 (Dispatch Board)

### A18. Tech Color Assignment & Configuration

**Triggered by**: Color-coded tech identity throughout the dispatch board (filter dots, avatar fills, job block borders, job block backgrounds).

**Scope**:
- New column on `user` table (or equivalent identity table): `display_color VARCHAR(7) NULL` — hex color code, e.g., `#3B43D6`
- Color is auto-assigned at user creation from a default palette of 8–12 hues, cycling to ensure no two active users share the same color
- Owner can override color per tech in Settings → Users
- API: tech color returned with user object on all relevant endpoints
- Frontend: dispatch board, Today tab on mobile, scheduling reports all consume this color

**Default palette**: 12 distinct hues drawn from extending the Pass 1 brand color ramps, with WCAG AA contrast verified for both white-text-on-color and color-on-white-background usage.

**Tenant setting**: `tech_color_palette` — array of hex codes (default = system palette of 12). Tenants with custom branding can override.

**Effort estimate**: Small — 1–2 days.

---

### A19. Dispatch Board API Endpoints (Optimistic Locking + Real-Time Updates)

**Triggered by**: Dispatch board's high-frequency drag-and-drop interactions and the requirement to reflect external calendar changes within minutes.

**Scope**:

**API endpoints** (most already specced in `mvp-arch.md` §13.7, but with additional behavior):
- `GET /api/v1/schedule/board` — extended to include drive-time data computed from cache when possible, fresh map provider call when cache miss
- `POST /api/v1/schedule/jobs/{id}/move` — atomic operation accepting both new tech and new time-window. Performs conflict check before commit. Returns either success or structured conflict response.
- `POST /api/v1/schedule/jobs/{id}/check-conflicts` — preview-only endpoint for what-if checks during drag operations. No commit.

**Optimistic concurrency control**:
- `job` and `job_tech_assignment` records carry a `version` integer column
- Move endpoints accept `expected_version` parameter
- Concurrent modification (two owners on the same board, or owner + voice command) returns 409 Conflict with the current state
- Frontend handles 409 by refreshing the affected job and offering retry

**Real-time push for external changes**:
- Server-sent events (SSE) endpoint: `GET /api/v1/schedule/board/stream` — emits change events when:
  - Calendar pull task processes external changes
  - Another owner makes a change
  - Voice command applies a change
  - Tech checks in / completes a job (state change)
- Frontend listens and applies smooth updates to the affected cells
- Falls back to 60-second polling if SSE unavailable

**Effort estimate**: Medium-Large — 6–8 days (endpoint refinement, optimistic locking on existing schema, SSE infrastructure).

---

### A20. Drive-Time Caching Verification

**Triggered by**: Dispatch board's drag-and-drop interactions can trigger many drive-time recomputations. Ensure caching prevents API cost overrun.

**Scope**:
- Verify that the existing `compute_customer_etas` task (per `mvp-arch.md` §13.6) and any related drive-time computation paths use a Redis-cached lookup keyed on `(origin_lat, origin_lng, dest_lat, dest_lng, hour_of_day)`
- Cache TTL: 24 hours (per architecture spec)
- Cache hit on dispatch board drag operations means same-day rearrangements are free after the first compute
- Add metric: `map_provider.cache_hit_ratio` to monitoring dashboard
- Add alarm: cache hit ratio < 70% over 1 hour (suggests cache key mismatch or TTL too short)

**Note**: this isn't strictly a new feature — it's a verification + observability item. Worth calling out because dispatch board UX depends on it being correct.

**Effort estimate**: Small — 1–2 days (verification, metric instrumentation, alarm setup).

---

## Additions from Pass 3 Flow 4 (Customer Communications)

Flow 4 builds heavily on Pass 2 A4 (Templated Customer Communications). The schema (`customer_communication`, `communication_template`), the API endpoint (`POST /api/v1/communications/send`), the voice intent handler, and the notification dispatch are already specced in A4. The additions below are the design-driven refinements that Flow 4 made explicit.

### A21. Per-Message Channel Override

**Triggered by**: Tech ability to override customer's stored preferred channel for a single message without changing the customer's stored preference.

**Scope**:
- Extend `customer_communication` table to record:
  - `customer_preferred_channel` (the customer's stored preference at send time)
  - `actual_channel` (the channel actually used)
  - `channel_override_flag` (boolean — true when these differ)
- API endpoint `POST /api/v1/communications/send` accepts an optional `channel_override` parameter (`'sms' | 'email'`) which forces the actual_channel regardless of customer preference
- Customer record's preferred channel field is unchanged by override
- Web comm history surfaces channel overrides as visible metadata (per spec — "channel overridden from SMS to email")

**Schema confirmation needed**: confirm that the `customer` table has a `preferred_contact_channel` field. If not, add it (`VARCHAR(10)` enum: `'sms' | 'email'`, NOT NULL DEFAULT `'sms'`).

**Effort estimate**: Small — 1–2 days (schema additions, API parameter, history rendering).

---

### A22. Voice Intent Grammar for Customer Communications

**Triggered by**: Voice describes intent (not template name) — "tell Johnson I'm 20 out" must map to `on_my_way` template with computed ETA, not require Mike to say a template name.

**Scope**:
- Additions to `voice_action_router.py` handler registry (per Pass 2 A4 baseline, now expanded with Flow 4 patterns):
  - `send_customer_communication` — top-level intent
  - Intent matcher routes utterance fragments to template codes:
    - "I'm [X] out" / "[X] minutes away" / "[X] minutes" → `on_my_way` with ETA = now + X minutes
    - "running [X] late" / "[X] minutes late" → `running_late` with delay = X
    - "I'm here" / "I just arrived" / "starting work" → `arrived`
    - "the job's done" / "we're done" / "all finished" / "job complete" → `job_complete`
    - "parts delay" / "waiting on parts" → `parts_delay`
    - "confirm [date/time]" → `confirm_appointment`
- Confidence threshold for ambiguous utterances — when intent matching falls below threshold, AI asks for clarification rather than picking
- Variable extraction:
  - Time durations ("20 out", "30 late") parsed and converted to ETAs/delays
  - Customer names extracted, matched against tenant's customer DB, disambiguated if ambiguous (per Flow 1 disambiguation pattern)
- Customer resolution priority (per Flow 4 spec):
  1. Explicit context (voice triggered from customer/job page)
  2. Named in utterance
  3. Disambiguation prompt when name ambiguous
  4. Customer prompt when no name and no context

**Effort estimate**: Medium — 4–5 days. The intent matching is non-trivial — requires Llama prompt engineering for variable extraction and confidence scoring, plus integration with the disambiguation conversation pattern.

---

### A23. Communication Preview Endpoint (Pre-Send Validation)

**Triggered by**: Always-preview-before-send rule means the UI needs to render the exact message that will be sent, with all variables substituted, before the user confirms.

**Scope**:
- New API endpoint: `POST /api/v1/communications/preview`
- Request: `template_code`, `customer_id`, `variables` (object), `channel_override` (optional)
- Response:
  - `rendered_subject` (for email)
  - `rendered_body` (the actual message text)
  - `recipient_name`
  - `recipient_address` (phone number for SMS, email for email)
  - `actual_channel`
  - `editable_variables` (array of variable names with their current values, used by the inline-edit UI to know what's editable)
- This endpoint does NOT log to `customer_communication` and does NOT dispatch the message — it's read-only template rendering
- Same template engine as the send endpoint (A4), just no dispatch

**Rationale**: Frontend can't reliably render templates client-side (variable substitution rules, channel-specific rendering, opt-out footer compliance text, etc.). Server-side rendering ensures the preview matches what gets sent.

**Effort estimate**: Small — 1–2 days. Largely a refactor of the existing template rendering logic into a separate endpoint that doesn't dispatch.

---

## Additions from Pass 3 Flow 5 Architectural Pre-Work (Quote Line Item Architecture)

These items are foundational schema/architectural changes triggered by the quote-style decisions documented in `quote-line-item-architecture.md`. They must be implemented before Flow 5's UI can be built, and they affect Flow 1 (voice quote creation) and Flow 2 (profitability calculations).

### A24. Quote Line Item Schema Extension (Visibility + Hierarchy)

**Triggered by**: Need to support component, deliverable, and lump-sum quote styles with one flexible data model.

**Scope**:

**Schema additions to `quote_line` (or equivalent existing table)**:
- `customer_visible BOOLEAN NOT NULL DEFAULT TRUE` — if false, line is internal cost-tracking only, never shown to customer
- `parent_line_id UUID NULL REFERENCES quote_line(id) ON DELETE RESTRICT` — when present, this line is a child of another line for cost roll-up purposes
- `display_order INT NOT NULL` — explicit ordering, separate from creation order, allowing lines to be reordered without timestamp manipulation
- `is_section_header BOOLEAN NOT NULL DEFAULT FALSE` — when true, line renders as a visual section divider (e.g., "Services", "Materials") with no price column

**Description field verification**: confirm `description` is `TEXT` with no length cap. Real-world quotes have descriptions running 700+ characters with bullet formatting. If currently `VARCHAR` with a cap, migrate to `TEXT`.

**Constraints**:
- A child line (`parent_line_id IS NOT NULL`) cannot be customer-visible if its parent is not (children inherit at-most the parent's visibility — enforced via CHECK constraint or trigger)
- A section header line (`is_section_header = TRUE`) must have `parent_line_id IS NULL`
- A line cannot be its own parent or create a cycle (parent_line_id depth ≤ 1 for MVP — single level of hierarchy)

**Roll-up semantics** (documented for dev team):
- A parent line's customer-facing total is the value stored in its own `total_amount` field (NOT auto-computed from children)
- A parent line's *cost basis* is the sum of children's `total_amount` values
- Margin = parent's `total_amount` − sum_of_children's_amounts

**Effort estimate**: Medium — 3–4 days (schema migration, constraint logic, application code updates for line item CRUD, PDF rendering pipeline updates to handle visibility flags and section headers).

---

### A25. Quote Template Schema with Style and Versioning

**Triggered by**: Per-template style selection and system-template-versioning model.

**Scope**:

**Naming convention**: rename existing "quote template" references in code to use the full prefix `quote_template` to disambiguate from `communication_template` (Pass 2 A4). Audit existing schema, API routes, and code paths.

**Schema for quote templates**:
```
quote_template
  id                        UUID PRIMARY KEY
  tenant_id                 UUID NULL  -- NULL means system template; UUID means tenant-owned
  name                      TEXT NOT NULL
  description               TEXT NULL
  style                     TEXT NOT NULL  -- 'component' | 'deliverable' | 'lump_sum'
  category                  TEXT NULL  -- e.g., 'service_call', 'installation', 'inspection'
  system_template_id        UUID NULL  -- when this is a tenant fork, references the system template
  forked_from_version       INT NULL  -- the version of the system template at fork time
  current_version           INT NOT NULL DEFAULT 1
  is_active                 BOOLEAN NOT NULL DEFAULT TRUE
  is_system_template        BOOLEAN NOT NULL DEFAULT FALSE
  created_at                TIMESTAMPTZ
  updated_at                TIMESTAMPTZ
  created_by_user_id        UUID NULL
```

**Companion table for template line items**:
```
quote_template_line
  -- mirrors quote_line structure including customer_visible, parent_line_id,
  -- display_order, is_section_header, description, default_quantity, default_amount
  -- with template-variable placeholders allowed in text fields ({customer_name}, {site_address}, etc.)
```

**API endpoints**:
- `GET /api/v1/quote-templates` — list with filters (style, category, system vs. tenant)
- `POST /api/v1/quote-templates` — create tenant template
- `POST /api/v1/quote-templates/{id}/fork` — fork a system template to tenant ownership
- `POST /api/v1/quote-templates/{id}/disable` — soft-disable a tenant template
- `POST /api/v1/quotes/from-template/{template_id}` — instantiate a new quote from a template

**System template seed**:
- AevoFab ships at least three system templates as MVP defaults:
  - `service_call_basic` (component-style)
  - `installation_standard` (deliverable-style)
  - `fixed_bid_simple` (lump-sum-style)
- Seeded into the database via a migration on initial deploy and per new tenant creation
- System templates have `tenant_id = NULL` and `is_system_template = TRUE`
- New tenants automatically have these visible in their template list as read-only references

**Effort estimate**: Medium-Large — 5–7 days (schema, fork mechanism, seed data, API endpoints, naming refactor).

---

### A26. System Template Update Notification Flow

**Triggered by**: Locked decision that system template version updates notify tenants but don't auto-push.

**Scope**:
- New nightly Celery task: `check_system_template_updates`
  - For each active tenant template with a non-null `system_template_id`, check if `forked_from_version < current_version` of the source system template
  - If yes, generate an in-app notification: "AevoFab has released v{N} of [Template Name] — review changes"
  - Notifications dedup per (tenant_id, system_template_id, system_template_version) so a tenant isn't re-pinged about the same update
- Settings UI: "Template updates available" section showing pending updates with a "View changes" link
- Pull mechanism: when tenant clicks "Pull v2," create a new tenant template forked from the new system template version; old tenant template is preserved (and optionally disabled by tenant)
- Quotes already created from the old tenant template continue to render correctly because each quote's line items are immutable per existing quote_version pattern

**Effort estimate**: Small-Medium — 2–3 days.

---

### A27. Save Quote as Template

**Triggered by**: Locked decision allowing owners to save any quote as a tenant template.

**Scope**:
- API endpoint: `POST /api/v1/quotes/{id}/save-as-template`
- Request: `name`, `category` (optional), `style` (defaults from quote's style if it has one)
- Server-side processing:
  1. Copy all customer-visible and hidden lines from the quote into a new `quote_template_line` set
  2. Replace customer-specific values with template variables: `customer_name`, `site_address`, `customer_phone`, `customer_email`, dates, quote numbers
  3. Strip transaction-specific data (the actual `quote_id`, the specific final total)
  4. Preserve material quantities and labor hours as defaults but mark them as override-able
- The variable namespace for templating must match existing variable conventions used by communication templates (Pass 2 A4) where overlapping
- RBAC: `quote_template.create` permission — owner/admin only (techs cannot save quotes as templates)

**Open question for dev team review**: define the complete variable namespace. Initial set:
```
{customer_name}        — full customer name
{customer_first_name}  — customer first name
{site_address}         — site street address
{site_city_state_zip}  — site city/state/zip line
{job_date}             — scheduled job date
{quote_date}           — quote creation date
```

**Effort estimate**: Medium — 3–4 days (API endpoint, variable substitution logic, scrubbing rules, RBAC integration).

---

### A28. Multi-Line Description Editing UI Support

**Triggered by**: Real-world quotes have line item descriptions running 700+ characters with bullet formatting (e.g., Contractor A "Generator Install Air-Cooled" with 12 bullets).

**Scope**:
- **Backend**: confirm `quote_line.description` and `quote_template_line.description` are `TEXT` (not `VARCHAR(255)` or similar). If migration needed, do it as part of A24.
- **Mobile editing UI**: multi-line text area replacing any current single-line input. For MVP, plain `<textarea>` is sufficient — bullet auto-formatting on `-` keystroke is Phase 2 polish.
- **Web editing UI**: same multi-line area, more screen space. Phase 2 could upgrade to a markdown-aware editor (e.g., simple Markdown preview).
- **PDF rendering**: customer-facing quote PDF must preserve newlines and render bullet-prefixed lines (`- `, `* `) as visual bullets.
- **Voice editing constraint**: composing 700-character descriptions verbally is impractical. Voice handles short edits; long descriptions are template-derived and edited via touch. This is a UX constraint, not a code path.

**Effort estimate**: Small — 1–2 days (mostly the PDF rendering update; mobile/web editor changes are minor).

---

## Additions from Pass 3 Flow 5 (Quote Approval Workflow)

Flow 5 builds on Pass 2 A2 (Quote Approval Workflow baseline) and the architectural pre-work (A24–A28). The schema for the `pending_approval` and `approved` quote states, the basic submission endpoints, and the notification dispatch are already specced in A2. The additions below are the design-driven refinements that Flow 5's UI requires.

### A29. Pending Edit Storage During Owner Review

**Triggered by**: Owner can make multiple edits to a quote during review and commit them all at once via "Approve with edits." Edits must persist across page reloads but remain invisible to the tech until commit.

**Scope**:

**Schema additions**:
- New table or extension to existing quote storage: `quote_pending_edit`
  ```
  quote_pending_edit
    id                  UUID PRIMARY KEY
    tenant_id           UUID NOT NULL
    quote_id            UUID NOT NULL → quote(id)
    quote_version_id    UUID NOT NULL → quote_version(id)  -- the version being reviewed
    editor_user_id      UUID NOT NULL → user(id)  -- the owner doing the editing
    edit_type           TEXT NOT NULL  -- 'modify_line' | 'add_line' | 'delete_line' | 'edit_notes'
    target_line_id      UUID NULL → quote_line(id)  -- for modify/delete; null for add
    edit_payload        JSONB NOT NULL  -- the proposed change (new values, new line content, etc.)
    annotation          TEXT NULL  -- optional explanation provided by owner
    created_at          TIMESTAMPTZ
    updated_at          TIMESTAMPTZ
  ```

**Lifecycle**:
- Pending edits are created when the owner makes a modification on the review surface
- They persist across page reloads (server-side, scoped to editor + quote version)
- "Cancel my edits" deletes all pending edits for that owner on that quote version
- "Approve with edits" applies all pending edits as a single atomic operation, creating a new quote version, then deletes the pending edit records
- If the owner abandons the review without explicit action, pending edits expire after 24 hours (Celery cleanup task)

**API endpoints**:
- `GET /api/v1/quotes/{id}/pending-edits` — list current owner's pending edits for this quote
- `POST /api/v1/quotes/{id}/pending-edits` — create a pending edit
- `PATCH /api/v1/quotes/{id}/pending-edits/{edit_id}` — modify a pending edit
- `DELETE /api/v1/quotes/{id}/pending-edits/{edit_id}` — revert an individual pending edit
- `DELETE /api/v1/quotes/{id}/pending-edits` — cancel all pending edits
- `POST /api/v1/quotes/{id}/approve-with-edits` — atomic: apply all pending edits, create new version, transition to approved state

**Concurrency**: when two owners review the same quote simultaneously, each has their own `quote_pending_edit` rows scoped by `editor_user_id`. The first to commit wins; the second receives a 409 Conflict and must refresh.

**Effort estimate**: Medium — 4–5 days (schema, atomic apply logic, concurrency handling, cleanup task, API endpoints).

---

### A30. Approval Comment & Annotation System

**Triggered by**: Kickback workflow requires inline comments on specific lines + overall comment; reject requires overall comment; approve-with-edits supports optional per-edit annotations.

**Scope**:

**Schema**:
- New table: `quote_approval_comment`
  ```
  quote_approval_comment
    id                    UUID PRIMARY KEY
    tenant_id             UUID NOT NULL
    quote_id              UUID NOT NULL → quote(id)
    quote_version_id      UUID NOT NULL  -- which version this comment is anchored to
    target_line_id        UUID NULL → quote_line(id)  -- null for overall comment
    author_user_id        UUID NOT NULL → user(id)
    comment_type          TEXT NOT NULL  -- 'kickback' | 'rejection' | 'edit_annotation'
    content               TEXT NOT NULL
    created_at            TIMESTAMPTZ
  ```

**Visibility**:
- Comments visible to the original tech submitter, the owner, the approver (if different), and any user with `quote.view` permission
- Comments persist forever (audit trail) — no soft delete from the comment side
- If a quote line referenced by a comment is later deleted, the comment is preserved with line context captured at comment creation

**API endpoints**:
- `GET /api/v1/quotes/{id}/comments` — list all approval comments for this quote
- `POST /api/v1/quotes/{id}/kickback` — atomic: transition quote to draft state with provided comments
- `POST /api/v1/quotes/{id}/reject` — atomic: transition quote to rejected state with required overall comment

**Required-comment validation**:
- Kickback request must include either at least one line-level comment OR a non-empty overall comment (or both)
- Reject request must include a non-empty overall comment
- Approve-with-edits has no required comments (annotations are optional per-edit)

**Effort estimate**: Small-Medium — 3–4 days.

---

### A31. Voice Intent Grammar for Approval Actions

**Triggered by**: Owner can voice-trigger approval actions from any AevoFab surface ("approve Mike's panel quote", "show me Mike's pending quotes", "kick back the panel quote").

**Scope**:
- Additions to `voice_action_router.py` handler registry:
  - `approve_quote` — atomic approval with no edits
  - `reject_quote` — requires spoken comment which is captured as the rejection reason
  - `kickback_quote` — requires spoken comment which is captured as the overall kickback comment (line-level comments not voice-supported per spec; touch required for those)
  - `list_pending_quotes` — read-only, returns spoken summary of pending approvals
- Disambiguation pattern: when multiple quotes match the voice command (e.g., "Mike's quote" with two pending), AI asks "Which one — the panel upgrade or the service call?"
- Voice cannot commit complex inline edits — voice handlers reject any utterance that attempts line-level modification ("change the labor to 8 hours") with a response routing the owner to web: "I can approve, reject, or kick back the quote, but line edits need to happen on web. Open quote on web?"

**Constraint rationale**: voice-driven complex edits are too error-prone given Whisper accuracy in field conditions and the financial implications of wrong edits to a customer-facing quote.

**Effort estimate**: Small-Medium — 2–3 days (intent matching, disambiguation, refusal-with-redirect logic).

---

## Additions from Pass 3 Flow 6 (Calendar Conflict Resolution)

Flow 6 builds on the existing calendar sync infrastructure (`mvp-arch.md` §13.5, §13.7) and introduces a new platform-default + tenant-override settings pattern via A34. The base endpoints (`GET /api/v1/calendar/conflicts`, `POST /api/v1/calendar/conflicts/{id}/resolve`) already exist; the additions below extend them with diff payload, staleness check, auto-expiry, mobile/voice integration, and the new platform settings infrastructure.

### A32. Calendar Conflict Diff Payload

**Triggered by**: Resolution view requires server-rendered field-level diff plus base-state context for accurate "what changed since last sync" rendering.

**Scope**:

- Extend `calendar_sync_conflict` schema:
  - `aevofab_snapshot` (existing, JSONB) — current AevoFab state at conflict detection
  - `external_snapshot` (existing, JSONB) — current calendar state at conflict detection
  - `base_snapshot` (NEW, JSONB NULL) — last shared state before conflict; populated at detection time from the most recent successful sync log entry
  - `aevofab_modified_by_user_id` (NEW, UUID NULL) — who made the AevoFab-side change
  - `aevofab_modified_at` (NEW, TIMESTAMPTZ NOT NULL)
  - `external_modified_at` (NEW, TIMESTAMPTZ NOT NULL)
  - `urgency_score` (NEW, INT computed) — derived from related job's `scheduled_start_at` proximity for sort order
  - `related_job_id` (NEW, UUID NULL → field_ops.job)

- Extend `GET /api/v1/calendar/conflicts/{id}` response:
  - All snapshot fields above
  - `field_diffs`: server-computed list of fields that differ. For each field: `field_name`, `aevofab_value`, `external_value`, `base_value`, `aevofab_change` (`unchanged | modified | added | removed`), `external_change` (same enum)
  - This pre-computes the diff so the client doesn't need diff logic and rendering stays consistent across web and (future) mobile

**Effort estimate**: Small-Medium — 2–3 days (schema additions, base-snapshot capture in detection task, server-side diff computation, API response shape).

---

### A33. Pre-Resolution Staleness Check

**Triggered by**: Conflicts may be modified between detection and the owner's resolve action. Without a check, the owner can silently overwrite a state they didn't see.

**Scope**:

- `POST /api/v1/calendar/conflicts/{id}/resolve` accepts `expected_aevofab_modified_at` and `expected_external_modified_at` parameters
- Server re-evaluates: if either timestamp on the live conflict record exceeds the expected, returns 409 Conflict with the refreshed conflict payload
- Frontend handles 409 by refreshing the resolution view and surfacing a "this conflict has been updated" banner; owner re-decides
- Same pattern as the dispatch board's optimistic locking from A19

**Effort estimate**: Small — 1 day (API parameter validation, refresh pattern reuse from A19).

---

### A34. Auto-Expiry of Stale Conflicts (with Platform-Default + Tenant-Override Settings Infrastructure)

**Triggered by**: Conflicts unresolved for long periods clutter the conflict count and degrade its signal value. Source-of-truth posture supports defaulting to local on neglect. Settings need to be tunable both globally (by AevoFab) and per-tenant.

**Scope**:

**New pattern: platform_setting infrastructure** (introduced here; reusable for future settings):

- New table:
  ```
  platform_setting
    setting_key       VARCHAR PRIMARY KEY
    setting_value     JSONB NOT NULL
    description       TEXT NULL
    updated_at        TIMESTAMPTZ NOT NULL
    updated_by_user_id UUID NULL  -- AevoFab admin user
  ```
- Admin-only API endpoint: `PATCH /api/v1/admin/platform-settings/{key}` — Tom-only access, gated by the existing admin-role check that protects `tenant_product_feature_override` per `mvp-arch.md` §3.11
- Settings resolution helper: `resolve_setting(tenant_id, key, hardcoded_fallback)` that returns the first non-NULL value found in: tenant_setting → platform_setting → hardcoded_fallback. To be used wherever the conflict-expiry settings (and any future two-tier settings) are read.

**Initial seeded platform settings**:
- `default_calendar_conflict_auto_expire_days` = 30
- `default_calendar_conflict_warning_days_before_expiry` = 7

**Tenant settings** (additions):
- `calendar_conflict_auto_expire_days` — integer, NULL by default (inherits platform)
- `calendar_conflict_warning_days_before_expiry` — integer, NULL by default (inherits platform)
- 0 disables auto-expiry for that tenant; NULL inherits platform value

**Celery Beat task**: `expire_stale_calendar_conflicts` (daily)
- For each conflict, look up effective `auto_expire_days` and `warning_days` via `resolve_setting()`
- For each conflict older than `auto_expire_days - warning_days`: enqueue notification "N conflicts will auto-resolve in X days"
- For each conflict older than `auto_expire_days`: invoke resolve endpoint internally with `accept_local`, log to `calendar_sync_log` with `auto_resolved_stale = TRUE`, send notification

**Settings UI**:
- Tenant-facing: Settings → Integrations → Calendar → "Auto-resolution" panel with two integer inputs that show the inherited platform value as placeholder text when tenant value is NULL
- Admin-facing: out of scope for tenant Settings UI; Tom edits platform_setting via admin API for MVP. Full admin UI is Post-MVP.

**Pattern reusability note**: Several existing tenant settings are candidates to migrate to the platform-default + tenant-override pattern if it proves valuable: `report_chart_threshold` (A15), `etc_variance_owner_notify_pct` and `etc_variance_note_required_pct` (A14/A16), `max_discount_pct_owner` (A3). Decision on whether to migrate any of these is a future design call.

**Effort estimate**: Medium — 4–5 days (platform_setting table, admin API endpoint, settings-resolution helper, Celery task, notification path, audit flagging, settings UI plumbing). The infrastructure is reusable for any future two-tier settings, so the cost is amortized.

---

### A35. Mobile Pending-Conflicts Status & Notification Rate Limiting

**Triggered by**: Mobile Owner tab needs a status row showing pending conflict count for parity with the QuickBooks pattern; notification storms during outage recovery need rate limiting.

**Scope**:

- `GET /api/v1/calendar/status` (existing, per `mvp-arch.md` §13.7) extended to return:
  - `connection_status: 'connected' | 'syncing' | 'error' | 'disconnected'`
  - `last_successful_sync_at`
  - `pending_conflicts_count`
  - `requires_reconnect: boolean` (true when token-expired error)
- Mobile Owner tab consumes this for the "Calendar sync" row rendering
- Push notifications on conflict detection use existing `notification_outbox` infrastructure (`mvp-arch.md` §13.5)
- Rate limit: max 4 conflict-detection notifications per tenant per hour. Exceeding the limit collapses subsequent detections into a single batched notification ("3 more conflicts detected — resolve on web")

**Effort estimate**: Small — 1 day (response shape additions, rate-limit logic; frontend consumption is design only).

---

### A36. Voice Intent Grammar for Calendar Conflicts

**Triggered by**: Voice resolution capability per Flow 6 Decision 11 — owners can list, describe, and commit whole-version resolutions via voice from any AevoFab surface.

**Scope**:

- Additions to `voice_action_router.py` handler registry:
  - `list_pending_calendar_conflicts` — read-only summary of count + urgency
  - `describe_calendar_conflict` — read field-level diffs aloud; entity disambiguation per Flow 1 pattern
  - `resolve_calendar_conflict` — confirm-as-turn destructive commit (whole-version accept only)
  - `resolve_deletion_conflict` — same confirm-as-turn pattern with explicit destructive verbs
- Disambiguation when entity reference matches multiple conflicts ("You have two Johnson conflicts — the panel upgrade or the service call?")
- Voice describe overflow threshold tenant setting: `voice_describe_overflow_field_count` — integer, default 4; when more fields differ than this, AI redirects to text-link rather than reading aloud
- Field-level partial choice attempts ("keep AevoFab's date but the calendar's note") return a redirect handler: "Mixing fields isn't a voice action — open the conflict on web"
- Confirm-as-turn implementation reuses Flow 1's pattern (per A10): handler returns a pending-confirmation state in `context_window_json`; next user turn with affirmative intent commits, any other response cancels

**Voice grammar reference** (authoritative for `voice_action_router.py`):

| Intent | Example utterances | Action |
| :--- | :--- | :--- |
| `list_pending_calendar_conflicts` | "do I have any pending sync conflicts?", "are there any conflicts?" | Read-only count + urgency summary |
| `describe_calendar_conflict` | "what changed in the Johnson conflict?", "what's the conflict on the panel upgrade?" | Read field diffs aloud or redirect to text |
| `resolve_calendar_conflict` | "accept the AevoFab version of the Johnson conflict", "use the calendar version", "keep my version of the panel upgrade" | Confirm-as-turn → commit whole-version accept |
| `resolve_deletion_conflict` | "for the deleted Johnson event, recreate it on the calendar", "delete it from AevoFab too" | Confirm-as-turn → commit deletion-resolution path |
| (rejected) field-level voice editing | "keep AevoFab's date but the calendar's note" | Redirect: "Mixing fields isn't a voice action — open the conflict on web" |

**Effort estimate**: Small-Medium — 2–3 days (handler implementations, disambiguation reuse from Flow 1, confirm-as-turn reuse from A10, redirect handler for field-level mix attempts, overflow threshold setting plumbing).

---

## Summary of New Tenant Settings (Pass 2 + Pass 3)

| Setting | Default | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `require_approval_for_tech_quotes` | ON (multi-user), OFF (solo) | Quote approval workflow | A2 |
| `max_discount_pct_owner` | 15% | Margin cap for owner-applied discounts | A3 |
| `voice_persona_tone` | `balanced` | AI personality tone (Post-MVP) | A13 |
| `report_chart_threshold` | 8 | Min jobs to render charts vs table in reports | A15 |
| `etc_variance_note_required_pct` | 10% | ETC override note required when increase exceeds this | A14/A16 |
| `etc_variance_owner_notify_pct` | 50% | Owner notified when projected exceeds quote by this | A16 |
| `margin_bucket_boundaries` | `[10, 20, 30]` | Bucket boundaries for profitability charts | A17 |
| `margin_target_pct` | 20% | Target margin for below-target indicators | A17 |
| `tech_color_palette` | 12-hue system default | Custom color palette for tech identity | A18 |
| `calendar_conflict_auto_expire_days` | NULL → inherit platform | Days before unresolved conflicts auto-resolve to AevoFab; 0 disables | A34 |
| `calendar_conflict_warning_days_before_expiry` | NULL → inherit platform | Days before auto-expiry to send pre-warning notification | A34 |
| `voice_describe_overflow_field_count` | 4 | When voice describing a conflict, redirect to screen if more fields differ | A36 |

## Summary of New Platform Settings (NEW in Pass 3 Flow 6)

Platform settings are AevoFab-controlled defaults that tenants can optionally override. Introduced via the `platform_setting` table and `resolve_setting()` helper in A34. Editable only by AevoFab admins via `PATCH /api/v1/admin/platform-settings/{key}`.

| Setting | Default | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `default_calendar_conflict_auto_expire_days` | 30 | Fleet-wide default for tenant `calendar_conflict_auto_expire_days` | A34 |
| `default_calendar_conflict_warning_days_before_expiry` | 7 | Fleet-wide default for tenant pre-warning days | A34 |

## Summary of New RBAC Permissions (Pass 2 + Pass 3)

| Permission | Roles | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `quote.submit_for_approval` | technician | Submit tech-created quote for owner review | A2 |
| `quote.approve` | owner, accountant | Approve or reject pending quotes | A2 |
| `quote.apply_discount` | owner, accountant | Apply time-limited discounts within margin cap | A3 |
| `voice.provide_feedback` | owner, accountant | Flag voice misrecognitions, provide corrections | A6 |
| `schedule.manage` | owner, accountant | Dispatch, assignments (implemented in Pass 2) | A1 |
| `schedule.view_own` | technician | View own assigned schedule (implemented in Pass 2) | A1 |
| `voice.manage_own_sessions` | all | Rename, delete, open own conversation sessions | A10 |
| `quote_template.create` | owner, accountant | Save quote as template, create new tenant templates from scratch | A27 |
| `quote_template.edit` | owner, accountant | Edit existing tenant templates | A25 |
| `quote_template.fork_system` | owner, accountant | Fork system templates to tenant ownership | A25 |

## Rough Effort Estimate (Remaining MVP Additions)

| Item | Size | Days |
| :--- | :--- | :---: |
| A2 Quote Approval | Medium | 3–5 |
| A3 Time-Limited Discounts | Small-Medium | 2–3 |
| A4 Customer Communications | Medium | 4–6 |
| A5 Reports + Dashboard Widgets | Medium-Large | 5–7 |
| A6 Voice Feedback | Medium | 3–4 |
| A7 Field Mode Backend | Small | 1–2 |
| A9 Session Number Computation | Small | 1 |
| A10 Voice Session Grammar | Small-Medium | 2–3 |
| A11 Ollama Title Generation | Small | 1–2 |
| A12 Structured Message Payload | Medium | 4–6 |
| A14 ETC Capture System | Medium-Large | 6–8 |
| A15 Chart-Threshold Setting | Trivial | 0.5 |
| A16 ETC Variance Notifications | Small-Medium | 2–3 |
| A17 Margin Bucket Configuration | Small | 1–2 |
| A18 Tech Color Assignment | Small | 1–2 |
| A19 Dispatch Board API + SSE | Medium-Large | 6–8 |
| A20 Drive-Time Caching Verification | Small | 1–2 |
| A21 Per-Message Channel Override | Small | 1–2 |
| A22 Voice Intent Grammar for Comms | Medium | 4–5 |
| A23 Communication Preview Endpoint | Small | 1–2 |
| A24 Quote Line Item Schema (Visibility + Hierarchy) | Medium | 3–4 |
| A25 Quote Template Schema with Style and Versioning | Medium-Large | 5–7 |
| A26 System Template Update Notifications | Small-Medium | 2–3 |
| A27 Save Quote as Template | Medium | 3–4 |
| A28 Multi-Line Description Editing Support | Small | 1–2 |
| A29 Pending Edit Storage During Review | Medium | 4–5 |
| A30 Approval Comment & Annotation System | Small-Medium | 3–4 |
| A31 Voice Intent Grammar for Approval | Small-Medium | 2–3 |
| A32 Calendar Conflict Diff Payload | Small-Medium | 2–3 |
| A33 Pre-Resolution Staleness Check | Small | 1 |
| A34 Auto-Expiry + Platform Settings Infrastructure | Medium | 4–5 |
| A35 Mobile Pending-Conflicts Status & Rate Limiting | Small | 1 |
| A36 Voice Intent Grammar for Calendar Conflicts | Small-Medium | 2–3 |
| **Subtotal remaining MVP** | | **84–117.5 days** |
| A13 Voice Persona (Post-MVP) | Small | 2–3 |

Plus Pass 3 Flow 7 (offline-to-online sync) and Pass 4 additions still to come. Plan for approximately 17–24 weeks of remaining backend work before UI implementation begins.

---

*This document is regenerated at the end of each design pass. See the corresponding design spec for the UI decisions that triggered each addition.*
