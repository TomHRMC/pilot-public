# Pilot for Trades — Backend MVP Additions

**Status**: Running list — updated as UI design progresses
**Version**: 5 (extended through Pass 4 Tier 1 — three Tier 1 surfaces complete; Tier 2 next)
**Last Updated**: April 27, 2026 (Pass 4 Tier 1 complete: A47–A51 added)
**Purpose**: Track backend/database/API changes required by UI design decisions
**Handoff**: This document is the authoritative list of backend work required before UI coding begins

---

## Table of Contents

- [Pilot for Trades — Backend MVP Additions](#pilot-for-trades--backend-mvp-additions)
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
    - [A34. Auto-Expiry of Stale Conflicts (System Default + Tenant Override)](#a34-auto-expiry-of-stale-conflicts-system-default--tenant-override)
    - [A35. Mobile Pending-Conflicts Status \& Notification Rate Limiting](#a35-mobile-pending-conflicts-status--notification-rate-limiting)
    - [A36. Voice Intent Grammar for Calendar Conflict Resolution](#a36-voice-intent-grammar-for-calendar-conflict-resolution)
  - [Additions from Pass 3 Flow 7 (Offline-to-Online Sync)](#additions-from-pass-3-flow-7-offline-to-online-sync)
    - [A37. Offline-Capable Operations API Contract](#a37-offline-capable-operations-api-contract)
    - [A38. Sync Queue State Model (Server-Side Visibility)](#a38-sync-queue-state-model-server-side-visibility)
    - [A39. Idempotency UUIDs for Offline Operations](#a39-idempotency-uuids-for-offline-operations)
    - [A40. Conflict Severity Classification Engine](#a40-conflict-severity-classification-engine)
    - [A41. Resumable Photo Upload Pipeline](#a41-resumable-photo-upload-pipeline)
    - [A42. Voice Command Offline Capture \& Deferred Processing](#a42-voice-command-offline-capture--deferred-processing)
    - [A43. Force-Quit Recovery State Persistence](#a43-force-quit-recovery-state-persistence)
    - [A44. Auth Expiry Offline Handling](#a44-auth-expiry-offline-handling)
    - [A45. Tech-Resolvable Conflict UI Endpoints](#a45-tech-resolvable-conflict-ui-endpoints)
    - [A46. Owner Escalation Routing \& Notification](#a46-owner-escalation-routing--notification)
  - [Summary of New Tenant Settings (Pass 2 + Pass 3)](#summary-of-new-tenant-settings-pass-2--pass-3)
  - [Summary of New RBAC Permissions (Pass 2 + Pass 3)](#summary-of-new-rbac-permissions-pass-2--pass-3)
  - [Additions from Pass 4 Tier 1 (Owner Mobile-Conflict UI, QuickBooks Conflict UI, Background Sync)](#additions-from-pass-4-tier-1-owner-mobile-conflict-ui-quickbooks-conflict-ui-background-sync)
    - [A47. Owner-Side Mobile-Conflict Escalation Queue Endpoints](#a47-owner-side-mobile-conflict-escalation-queue-endpoints)
    - [A48. Owner-Side Mobile-Conflict Resolution Write Path](#a48-owner-side-mobile-conflict-resolution-write-path)
    - [A49. QuickBooks Conflict Queue Endpoints + Schema Extension](#a49-quickbooks-conflict-queue-endpoints--schema-extension)
    - [A50. QuickBooks Conflict Resolution Write Path + Auto-Expiry Celery Extension](#a50-quickbooks-conflict-resolution-write-path--auto-expiry-celery-extension)
    - [A51. Background Sync Infrastructure](#a51-background-sync-infrastructure)
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
- Pass 3 Flow 6 additions (A32–A36): documented in this file
- Pass 3 Flow 7 additions (A37–A46): documented in this file
- Pass 4 Tier 1 additions (A47–A51): this update

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
- Pilot ships at least three system templates as MVP defaults:
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
  - If yes, generate an in-app notification: "Pilot has released v{N} of [Template Name] — review changes"
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

**Triggered by**: Owner can voice-trigger approval actions from any Pilot surface ("approve Mike's panel quote", "show me Mike's pending quotes", "kick back the panel quote").

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

Flow 6 designs the UI for resolving bi-directional calendar sync conflicts. The architecture (`mvp-arch.md` §13.5) and base endpoints (`mvp-arch.md` §13.7 — `GET /api/v1/calendar/conflicts`, `POST /api/v1/calendar/conflicts/{id}/resolve`) are already specced; the additions below are design-driven refinements: a richer conflict payload for diff rendering, optimistic-locking-style staleness check, configurable auto-expiry, mobile parity, and voice resolution intent grammar.

### A32. Calendar Conflict Diff Payload

**Triggered by**: Resolution view (web and voice readback) requires server-rendered field-level diff plus base-state context for accurate "what changed since last sync" framing.

**Scope**:

- Extend `calendar_sync_conflict` schema:
  - `pilot_snapshot` (existing, JSONB) — current Pilot state at conflict detection
  - `external_snapshot` (existing, JSONB) — current calendar state at conflict detection
  - `base_snapshot` (NEW, JSONB NULL) — last shared state before conflict; populated at detection time from the most recent successful sync log entry
  - `pilot_modified_by_user_id` (NEW, UUID NULL) — who made the Pilot-side change
  - `pilot_modified_at` (NEW, TIMESTAMPTZ NOT NULL)
  - `external_modified_at` (NEW, TIMESTAMPTZ NOT NULL)
  - `urgency_score` (NEW, INT computed) — derived from related job's `scheduled_start_at` proximity for sort order
  - `related_job_id` (NEW, UUID NULL → field_ops.job)

- Extend `GET /api/v1/calendar/conflicts/{id}` response:
  - All snapshot fields above
  - `field_diffs`: server-computed list of fields that differ. For each field: `field_name`, `pilot_value`, `external_value`, `base_value`, `pilot_change` (`unchanged | modified | added | removed`), `external_change` (same enum)
  - This pre-computes the diff so the client doesn't need diff logic, voice readback can render from the same payload, and rendering stays consistent

**Effort estimate**: Small-Medium — 2–3 days (schema additions, base-snapshot capture in detection task, server-side diff computation, API response shape).

---

### A33. Pre-Resolution Staleness Check

**Triggered by**: Conflicts may be modified between detection and the owner's resolve action. Without a check, the owner can silently overwrite a state they didn't see. Applies to both web and voice resolution paths.

**Scope**:

- `POST /api/v1/calendar/conflicts/{id}/resolve` accepts `expected_pilot_modified_at` and `expected_external_modified_at` parameters
- Server re-evaluates: if either timestamp on the live conflict record exceeds the expected, returns 409 Conflict with the refreshed conflict payload
- Frontend handles 409 by refreshing the resolution view and surfacing a "this conflict has been updated" banner; owner re-decides
- Voice handler (A36) handles 409 by aborting confirmation, announcing the change, and routing to web with a deep link
- Same pattern as the dispatch board's optimistic locking from A19

**Effort estimate**: Small — 1 day (API parameter validation, refresh pattern reuse from A19; voice handler integration is in A36's scope).

---

### A34. Auto-Expiry of Stale Conflicts (System Default + Tenant Override)

**Triggered by**: Conflicts unresolved for long periods clutter the conflict count and degrade the metric's signal value. Two-tier configuration (platform-wide default; per-tenant override) gives both Pilot and individual tenants tuning control.

**Scope**:

**System-level configuration** (file/config-based for MVP; admin UI is Phase 2):
- `SYSTEM_CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS` — default `30`
- `SYSTEM_CALENDAR_CONFLICT_PRE_WARNING_DAYS` — default `7`
- These live in application settings; a deploy is required to change them in MVP

**Tenant-level overrides** (UI editable per tenant):
- `calendar_conflict_auto_expire_days` — integer; UNSET (no row) falls back to system default; tenant can explicitly set to NULL via UI to disable auto-expiry entirely (NULL is a sentinel, distinct from UNSET)
- `calendar_conflict_pre_warning_days` — integer; UNSET falls back to system default; explicitly nullable via UI to disable pre-warning
- Validation: when both are set, `pre_warning_days < auto_expire_days` enforced server-side; reject with 400 otherwise
- Settings UI: Settings → Integrations → Calendar → "Auto-resolution" subsection, with two integer inputs and explicit "Use system default" / "Disable" toggles

**Resolution logic** (server-side, when evaluating a conflict's age):
```
expire_days = tenant.calendar_conflict_auto_expire_days
if UNSET (no row): use SYSTEM default
if NULL (explicit disable): no auto-expiry for this tenant
otherwise: use the tenant value
```
Same logic for `pre_warning_days`.

**New Celery Beat task**: `expire_stale_calendar_conflicts` (daily)
- For each conflict, compute its applicable `expire_days` and `pre_warning_days` per the resolution logic above
- If conflict age >= `expire_days - pre_warning_days` and pre-warning not yet sent for this conflict: enqueue notification "N conflicts will auto-resolve in [pre_warning_days] days"
- If conflict age >= `expire_days`: invoke the existing resolve endpoint internally with `accept_local`, log to `calendar_sync_log` with `auto_resolved_stale = TRUE`, send notification

**Audit query**: `auto_resolved_stale = TRUE` flag distinguishes auto-resolutions from owner-initiated ones in any future investigation.

**Implementation note for dev team**: the system-default mechanism is new infrastructure if Pilot doesn't already have a "system config registry" pattern. Suggested implementation for MVP: a single `system_config.py` module exposing typed constants, loaded at app startup from environment variables with config-file values as fallback. Phase 2 may upgrade this to an admin-tier database table editable by Pilot support staff.

**Effort estimate**: Medium — 3–4 days (task implementation, two-tier resolution logic, settings UI plumbing for both fields with default/disable/override states, audit flagging, system-config infrastructure if not present).

---

### A35. Mobile Pending-Conflicts Status & Notification Rate Limiting

**Triggered by**: Mobile Owner tab needs a status row showing pending conflict count for parity with the QuickBooks pattern; notification storms during outage recovery need rate limiting.

**Scope**:

- `GET /api/v1/calendar/status` (existing, per `mvp-arch.md` §13.7) extended to return:
  - `connection_status: 'connected' | 'syncing' | 'error' | 'disconnected'`
  - `last_successful_sync_at`
  - `pending_conflicts_count`
  - `requires_reconnect: boolean` (true when token-expired error)
- Mobile Owner tab consumes this for the "Calendar sync" row rendering (parallel to the existing QuickBooks sync row)
- Push notifications on conflict detection use existing `notification_outbox` infrastructure (per `mvp-arch.md` §13.5)
- Rate limit: max 4 conflict-detection notifications per tenant per hour. Exceeding the limit collapses subsequent detections into a single batched notification ("3 more conflicts detected — resolve on web")

**Effort estimate**: Small — 1 day (response shape additions, rate-limit logic; frontend consumption is design only).

---

### A36. Voice Intent Grammar for Calendar Conflict Resolution

**Triggered by**: Decision 11 in the Flow 6 spec — voice can actively resolve modified-modified conflicts via the confirm-as-turn pattern, with explicit route-to-web for deletion conflicts and post-staleness recovery.

**Scope**:

**New voice intents** (added to `voice_action_router.py`):

| Intent | Example utterances | Handler behavior |
| :--- | :--- | :--- |
| `list_pending_calendar_conflicts` | "Do I have any pending sync conflicts?" / "What conflicts are pending?" | Read-only; AI announces count + brief urgency summary |
| `resolve_calendar_conflict` | "Resolve the Johnson conflict — accept Pilot" / "Accept the calendar version of the Williams conflict" | Identifier match, disambiguation, confirm-as-turn, then commit via existing resolve endpoint |

**Identifier matching**: handler looks up conflicts by:
1. Customer name (e.g., "Johnson")
2. Job title (e.g., "panel upgrade")
3. Scheduled date qualifier (e.g., "Thursday's" or "next week's")

If multiple match → AI asks disambiguating question following Flow 1's disambiguation pattern: "You have two Johnson conflicts — the panel upgrade or the inspection?"

**Confirm-as-turn copy template** (read by AI before committing):

```
"Accepting the [side] version of [conflict_identifier].
[That keeps:] [summary of what's preserved from chosen side].
[That discards:] [summary of what's lost from the rejected side].
Confirm?"
```

The summary text is rendered server-side using the field-level diff payload from A32 — the same payload that drives the visual diff. This keeps web and voice presentations consistent: what the diff highlights visually is what the readback announces verbally.

**Confirm-as-turn flow** (per Flow 1's `delete_session` pattern):
1. AI returns a pending-confirmation state in `context_window_json`
2. Owner's next utterance evaluated for affirmative intent ("yes" / "confirm" / "do it" / "go ahead")
3. Affirmative → API call with the resolve action
4. Anything else → cancel; AI offers "Want to see it on web instead?" with a push notification deep link

**Pre-staleness check integration** (per A33): if the resolve API returns 409 between identification and confirmation, AI announces "the conflict has changed since you last looked at it — opening the diff view on web" and pushes the deep link via `notification_outbox`.

**Refusal-with-redirect for unsupported cases**:
- Deletion conflicts → "That's a deletion conflict — it needs the diff view to be safe. I'll open it on web." Push notification with deep link.
- Multi-resolution attempts ("resolve all my conflicts") → "I can do them one at a time — which one first?" routes to per-conflict resolution.
- Field-level edits ("change the time to 3pm in the Johnson conflict") → "I can pick a side, but I can't edit the values via voice. Want me to open it on web?"

**RBAC**: existing `integrations.manage` permission is sufficient; voice handler honors the same RBAC check as the web endpoint.

**Effort estimate**: Medium — 4–5 days (intent matching, identifier disambiguation, server-side voice readback rendering using A32 diff payload, confirm-as-turn flow integration with `context_window_json` from A12, refusal-with-redirect logic, integration tests covering the staleness-check race).

---

## Additions from Pass 3 Flow 7 (Offline-to-Online Sync)

Flow 7 is the most backend-intensive Pass 3 flow because offline-capable mobile is essentially new infrastructure. Ten additions across data model, API contract, conflict classification, upload pipeline, voice deferred processing, force-quit recovery, auth, and owner escalation.

### A37. Offline-Capable Operations API Contract

**Triggered by**: Decision 1 of Flow 7 — explicit set of operations must be supported by both client SDK and backend with consistent contracts.

**Scope**:
- Document each offline-capable operation as accepting client-generated idempotency UUIDs
- Each endpoint validates idempotency on receipt
- Schema additions: `client_capture_at TIMESTAMPTZ NULL` on tables for offline-capturable operations (`job_time_entry`, `expense`, `photo`, `change_order`, `loto_check`, `job_status_change`, `job_note`) — distinct from `created_at` which is server-side
- Audit log captures both timestamps for offline-captured operations; the gap (`server_received_at - client_capture_at`) becomes a queryable metric for offline-duration analysis

**Operations covered** (per Flow 7 Decision 1):
- Clock in / clock out
- Time entry creation (with ETC fields per A14)
- Expense capture (with attached photo via A41)
- Photo capture (separate upload pipeline via A41)
- Status changes on already-assigned jobs
- LOTO check confirmation
- Voice audio capture (deferred processing via A42)
- Free-text notes on a job
- Change order creation against an already-assigned job

**Effort estimate**: Small-Medium — 2–3 days (mostly schema additions and contract documentation; idempotency already exists per §7.6).

---

### A38. Sync Queue State Model (Server-Side Visibility)

**Triggered by**: Decision 4 of Flow 7 — sync queue surface needs a server-side counterpart for cross-device visibility (tenant owner reviewing tech's sync state, support troubleshooting, audit).

**Scope**:
- New table: `mobile_sync_event` — append-only log of sync attempts per device per operation
  ```
  mobile_sync_event
    id                          UUID PRIMARY KEY
    tenant_id                   UUID NOT NULL
    user_id                     UUID NOT NULL
    device_id                   TEXT NOT NULL  -- client-reported device identifier
    operation_type              TEXT NOT NULL  -- 'time_entry' | 'expense' | 'photo' | etc.
    operation_payload_summary   JSONB  -- non-PII summary of what was synced
    status                      TEXT NOT NULL  -- 'pending' | 'syncing' | 'succeeded' | 'failed' | 'conflict'
    conflict_severity           TEXT NULL  -- 'auto_silent' | 'auto_notice' | 'tech_resolvable' | 'owner_escalation'
    client_capture_at           TIMESTAMPTZ NOT NULL
    synced_at                   TIMESTAMPTZ NULL
    error_detail                JSONB NULL
    idempotency_uuid            UUID NOT NULL
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
  ```
- API: `GET /api/v1/mobile-sync/state/{user_id}` — admin view (owner/support) of a tech's sync state, paginated
- Retention: 30 days hot, then archived consistent with audit log policy (per §3.1 audit lifecycle)
- Index: `(tenant_id, user_id, status)` for fast queries by status

**Effort estimate**: Medium — 3–4 days.

---

### A39. Idempotency UUIDs for Offline Operations

**Triggered by**: Decisions 1, 9 of Flow 7 — every offline-capable operation needs a client-generated UUID for safe retry, plus extension of idempotency window for the 72-hour offline scenario.

**Scope**:
- Document the idempotency contract: every offline-capable endpoint accepts `Idempotency-Key` header with a client-generated UUID v4
- Server-side: existing idempotency-key infrastructure (per §7.6) handles deduplication on retry; expand coverage to all offline-capable endpoints from A37
- **24-hour idempotency window adequacy review**: a tech could capture at hour 0, force-quit at hour 23, come back online at hour 50. The 24-hour idempotency window has expired but the sync still hasn't completed.
- **Mitigation — natural-key dedup**: server uses both the idempotency window AND a longer-window check on natural keys for offline-capable operations:
  - Time entry: `(user_id, job_id, clock_in_at)` unique on a 7-day window
  - Expense: `(user_id, job_id, captured_at, amount_cents)` unique on a 7-day window
  - LOTO check: `(user_id, job_id, captured_at)` unique on a 7-day window
  - Photo: `(user_id, job_id, captured_at, file_hash)` unique on a 30-day window
- Client SDK: generate UUID at capture time, persist with operation in local queue, send with sync attempt. UUID stays stable across retries.

**Effort estimate**: Small-Medium — 3–4 days (client SDK pattern + server-side natural-key dedup enhancement for offline-capable operations).

---

### A40. Conflict Severity Classification Engine

**Triggered by**: Decision 5 of Flow 7 — four severity classes need a server-side classifier that runs during sync.

**Scope**:
- New module: `services/mobile_sync_conflict.py`
- Per operation type, define classification rules: which conditions are auto-silent, auto-with-notice, tech-resolvable, owner-escalation
- API: classification runs during sync attempt; returns `SyncResolution` object with:
  ```
  severity: 'auto_silent' | 'auto_notice' | 'tech_resolvable' | 'owner_escalation'
  auto_resolved: bool
  tech_action_required: bool
  owner_escalation_required: bool
  payload: dict  # the resolution data, conflict description, etc.
  ```
- Per-operation classification matrix (data-driven, in a configuration table for runtime tuning):

  | Operation | Trigger | Severity |
  | :--- | :--- | :--- |
  | Time entry | Job still assigned to tech, no time overlap | `auto_silent` |
  | Time entry | Job reassigned to different tech | `tech_resolvable` |
  | Time entry | Job deleted while tech worked it | `owner_escalation` |
  | Time entry | Time overlaps existing entry (same tech) | `tech_resolvable` |
  | Expense | Category exists, under limit | `auto_silent` |
  | Expense | Category was renamed server-side | `auto_notice` |
  | Expense | Exceeds tenant per-item limit | `tech_resolvable` |
  | Expense | Job deleted while expense captured | `owner_escalation` |
  | Photo | Job exists | `auto_silent` |
  | Photo | Storage limit exceeded | `tech_resolvable` |
  | Photo | Job deleted while photo captured | `owner_escalation` |
  | Status change | Tech-assigned job, normal transition | `auto_silent` |
  | Status change | Job already completed by another tech | `owner_escalation` |
  | Change order | Quote version still active | `auto_silent` |
  | Change order | Quote version superseded | `tech_resolvable` |
  | LOTO check | Job still in progress | `auto_silent` |
  | LOTO check | Job completed before LOTO sync arrived | `auto_notice` |

- Configuration table allows Pilot admins to tune the classification matrix without code deploys (e.g., reclassify a specific trigger from `tech_resolvable` to `auto_notice` based on operational data)

**Effort estimate**: Medium-Large — 5–7 days (per-operation classification logic, comprehensive test coverage for each row in the matrix, configuration table, all four severity paths).

---

### A41. Resumable Photo Upload Pipeline

**Triggered by**: Decision 6 of Flow 7 — resumable chunked uploads to handle network interruption; separate queue from data sync.

**Scope**:

**Implementation choice**: S3 multipart upload directly from client with signed URLs. Rationale: offloads heavy lifting to S3, avoids Pilot as a chunk-relay middleman, scales better at any tenant volume.

**API endpoints**:
- `POST /api/v1/photos/initiate-upload`
  - Request: `tenant_id` (from JWT), `job_id`, `expense_id` (optional), `file_size_bytes`, `mime_type`, `client_capture_at`, `idempotency_uuid`
  - Response: S3 multipart upload session ID, list of presigned chunk URLs (one per chunk), `pilot_photo_id`
- `POST /api/v1/photos/complete-upload`
  - Request: `pilot_photo_id`, `s3_session_id`, `chunk_etags` (list)
  - Response: photo record with final URL
  - Server-side: validates all chunks present, calls S3 CompleteMultipartUpload, records the photo

**Client SDK**:
- Track per-chunk completion in local state
- Resume from last-completed chunk on retry (skip already-uploaded chunks)
- Configurable chunk size (default 5MB)

**WiFi/cellular preference**:
- Client-side scheduling; server doesn't enforce
- Tenant setting `photo_upload_wifi_only` (default TRUE)
- User override: "Upload on cellular when offline > 24 hours" — client-side configurable

**Server-side cleanup**:
- Incomplete uploads expire after 24 hours via S3 lifecycle rule
- Celery task `cleanup_incomplete_photo_uploads` validates and removes orphaned `photo` records weekly

**Local cleanup** (per Flow 7 cross-domain F):
- Tenant setting `photo_local_retention_days` (default 7)
- Local photos kept this long after server confirmation, then auto-purged from device
- Client SDK manages this; server tracks confirmation timestamps

**Effort estimate**: Medium — 4–5 days (S3 multipart integration, chunk management, signed URL generation, client SDK chunked upload logic, local cleanup logic).

---

### A42. Voice Command Offline Capture & Deferred Processing

**Triggered by**: Decision 7 of Flow 7 — voice audio captured offline, transcribed when online.

**Scope**:

**Schema extensions to `voice_command_log`**:
- `captured_at TIMESTAMPTZ NOT NULL` — when audio was captured (client-side)
- `uploaded_at TIMESTAMPTZ NULL` — when audio reached server
- `transcribed_at TIMESTAMPTZ NULL` — when Whisper completed
- `parsed_at TIMESTAMPTZ NULL` — when Llama completed
- `processing_status TEXT NOT NULL` — `pending_upload | uploading | transcribing | parsing | completed | failed`
- `audio_object_key TEXT` — S3 key for the uploaded audio file (existing field; verify present)
- `idempotency_uuid UUID NOT NULL` — for safe retry

**API endpoints**:
- `POST /api/v1/voice/upload-audio`
  - Accepts: audio file (multipart), `captured_at` timestamp, `idempotency_uuid`, optional context (which screen, active conversation_session_id)
  - Returns: `voice_command_log_id`, processing status pointer
  - Queues a Celery task for processing
- `GET /api/v1/voice/command/{id}` — poll for processing status and result

**Celery task**: `process_voice_audio_async`
- Loads audio from S3
- Runs Whisper transcription
- Runs Llama intent parsing
- Routes to intent handler (existing flow)
- Updates `voice_command_log.processing_status` through state machine
- If intent requires confirmation (per Flow 1 confirm-as-turn), enqueue notification rather than blocking

**Confirmation deferred flow**:
- If intent processing produces a destructive action, the result is held in a "pending confirmation" state
- Notification fires to the originating user: "Your voice command 'delete the Davis chat' is ready to confirm"
- Tap → opens Voice tab with confirmation prompt; tech responds yes/no in normal voice or touch flow
- Confirmation timeout: 24 hours; after that, the deferred command is auto-cancelled with a notification

**Client SDK**:
- Store audio locally when offline; upload via this endpoint when online
- UI shows "queued" state in sync queue (per Flow 7 Decision 4)

**Effort estimate**: Medium — 4–5 days (schema, async pipeline, deferred-confirmation flow, client SDK, integration with existing voice intent flow).

---

### A43. Force-Quit Recovery State Persistence

**Triggered by**: Decision 9 of Flow 7 — sync queue must survive force-quit and resume.

**Scope**:

**Client-side** (mostly):
- Local queue persists in device storage
  - iOS: Core Data with synchronous writes for queue mutations
  - Android: Room with transactional writes
  - Expo / cross-platform: shared persistence layer (likely SQLite via Expo's persistence APIs)
- Each queue item carries: client UUID, operation type, payload (full request body), status, retry count, last error, last attempt timestamp
- On app launch: load queue from storage, mark "syncing" items as "pending" (idempotency keys handle the duplicate-protection on retry)

**Server-side** (minimal):
- Honor idempotency on retry per A39 (largely existing)
- Verify `mobile_sync_event` (A38) records prior sync attempts for the same `idempotency_uuid` to enable client-side awareness of "this might already be synced; check before retry"

**Cross-platform behavior tests required** (per Flow 7 validation checklist):
- iOS: app force-quit → relaunch → queue resumes
- iOS: app backgrounded > 30 minutes → relaunch → queue resumes
- Android: app force-stop → relaunch → queue resumes
- Android: app killed by OS memory pressure → relaunch → queue resumes
- Both: device reboot mid-sync → relaunch → queue resumes

**Effort estimate**: Medium — 4–5 days client SDK (persistence layer, lifecycle integration, tests across iOS/Android/Expo); minimal backend.

---

### A44. Auth Expiry Offline Handling

**Triggered by**: Decision 10 of Flow 7 — graceful re-auth after token expiry preserves captured data.

**Scope**:

**Refresh token TTL verification**:
- Cognito refresh token TTL must be at least 7 days (default 30 days — adequate for 72-hour hard limit per Flow 7 Decision 13)
- Document this in operational runbook so it's not accidentally lowered

**Client SDK behavior**:
- On sync attempt with expired access token: attempt refresh
- If refresh succeeds: sync resumes silently
- If refresh fails:
  - Surface re-auth prompt while preserving local queue
  - Captured data remains in local storage; not deleted
  - Tech enters credentials → new tokens issued → sync resumes from queue

**Edge case — tenant disabled the user mid-offline**:
- Re-auth fails permanently (not a token issue, an account issue)
- UI: "Account disabled — contact your owner. Captured data is saved locally."
- Export affordance: "Email me a JSON copy of unsynced data" — tech enters an external email address; client SDK assembles a JSON dump and sends via local mail client (not via Pilot API since the account is disabled)
- After 30 days locally, captured data auto-purges to prevent indefinite local retention

**Effort estimate**: Small-Medium — 2–3 days (refresh flow client SDK, account-disabled UX, JSON export client-side).

---

### A45. Tech-Resolvable Conflict UI Endpoints

**Triggered by**: Decision 11 of Flow 7 — tech resolves conflicts on phone with proper API support.

**Scope**:

**API endpoints**:
- `GET /api/v1/mobile-sync/conflicts/{conflict_id}` — returns the conflict detail:
  - Tech's captured version (full payload)
  - Server's current version (full payload)
  - Severity classification (per A40)
  - Classification reason (human-readable, e.g., "Job reassigned to different tech")
  - Field-level diff (per A32 pattern from Flow 6, adapted for mobile sync conflicts)
- `POST /api/v1/mobile-sync/conflicts/{conflict_id}/resolve`
  - Accepts: `resolution: 'use_local' | 'use_server' | 'escalate_to_owner'`
  - For `use_local`: applies tech's version, may push to other affected entities
  - For `use_server`: discards tech's version, marks the corresponding queue item as resolved
  - For `escalate_to_owner`: creates `mobile_sync_owner_escalation` row (per A46), notifies owner

**Pre-resolution staleness check** (per A33 pattern from Flow 6):
- API accepts `expected_server_version_id` parameter
- If server state changed between conflict surface and resolution attempt, returns 409 with refreshed conflict payload
- Client refreshes the resolution screen with new state

**Audit**: every resolution logged to `mobile_sync_event` with status `succeeded` (with `resolution_action` field capturing which path was taken).

**Effort estimate**: Small-Medium — 2–3 days (largely follows A33 pattern; field-level diff logic mostly reusable from A32).

---

### A46. Owner Escalation Routing & Notification

**Triggered by**: Decision 12 of Flow 7 — owner-escalated conflicts surface in owner's queue with notification; web UI deferred to Pass 4.

**Scope**:

**New table**: `mobile_sync_owner_escalation`
```
mobile_sync_owner_escalation
  id                       UUID PRIMARY KEY
  tenant_id                UUID NOT NULL
  originating_user_id      UUID NOT NULL  -- the tech
  conflict_id              UUID NOT NULL  -- → mobile_sync_event(id)
  escalated_at             TIMESTAMPTZ NOT NULL
  escalation_reason        TEXT NOT NULL  -- 'auto_severity' | 'tech_chose'
  status                   TEXT NOT NULL  -- 'pending' | 'resolved' | 'rejected'
  resolved_by_user_id      UUID NULL
  resolved_at              TIMESTAMPTZ NULL
  resolution_action        TEXT NULL  -- 'used_local' | 'used_server' | 'manual_edit' | 'rejected'
  resolution_payload       JSONB NULL  -- if owner did a manual edit, the resulting state
```

**API endpoints**:
- `GET /api/v1/owner/mobile-sync-escalations` — list pending escalations for owner; filter by user, date range, operation type
- `GET /api/v1/owner/mobile-sync-escalations/{id}` — escalation detail with full conflict context
- `POST /api/v1/owner/mobile-sync-escalations/{id}/resolve` — owner resolves; accepts `resolution_action` and optional `resolution_payload` for manual edits

**Notification flow**:
- On escalation creation: push + `notification_outbox` entry to owner per existing infrastructure
- On owner resolution: push to originating tech ("Your conflict was resolved by Sarah — your local data was kept" or similar)

**Web UI for resolution**: deferred to Pass 4 per Flow 7 cross-domain consideration D. The design language is largely inheritable from Flow 6's two-column diff pattern adapted for the mobile-sync-conflict source.

**Effort estimate**: Medium — 3–4 days backend (table, endpoints, notification integration); UI deferred to Pass 4.

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
| `calendar_conflict_auto_expire_days` | system default (30); nullable to disable | Days before unresolved sync conflict auto-resolves to Pilot version | A34 |
| `calendar_conflict_pre_warning_days` | system default (7); nullable to disable | Days before auto-expiry to send pre-warning notification | A34 |
| `photo_upload_wifi_only` | TRUE | Restrict photo uploads to WiFi connections | A41 |
| `photo_local_retention_days` | 7 | How long synced photos remain on device before auto-purge | A41 |
| `offline_hard_limit_hours` | 72 (nullable for unlimited) | Hours of offline operation before app blocks new captures | Flow 7 D13 |

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

## Additions from Pass 4 Tier 1 (Owner Mobile-Conflict UI, QuickBooks Conflict UI, Background Sync)

### A47. Owner-Side Mobile-Conflict Escalation Queue Endpoints

**Triggered by**: Pass 4 Tier 1 #1 Decisions 1, 2, 11 — queue list with filtering, escalation detail with explainer copy, history archive.

**Scope**:
- `GET /api/v1/owner/field-issues` — list pending escalations for the requesting owner's tenant
  - Query parameters: `status` (default `pending`; accepts `pending | auto_recovered | stale | all`), `tech_active_within_hours` (default 24, accepts `null` for all), `operation_type` (multi-value), `sort` (default `-escalated_at`; accepts `-escalated_at | escalated_at | -captured_at | captured_at`), `limit`, `offset`
  - Response: paginated list with `{escalation_id, tech_user_id, tech_name, tech_role, tech_last_active_at, operation_type, operation_summary, escalation_reason_explainer, captured_at, escalated_at, status, server_state_summary}` per row
- `GET /api/v1/owner/field-issues/{escalation_id}` — full escalation detail for resolution view
  - Response: full diff payload with `tech_local_snapshot` (JSONB), `server_state_snapshot` (JSONB), `field_diffs` (computed), `escalation_reason_explainer` (server-generated copy), `escalation_type` (`field_diff | deletion_conflict_tech_captured_against_deleted | deletion_conflict_status_change_collision | permission_revoked_capture`), `available_resolutions` (enum array based on type), audit context
- `GET /api/v1/owner/field-issues/history` — historical archive
  - Same shape as queue list but with status filter defaulting to resolved states
  - Additional response fields: `resolved_at`, `resolved_by_user_id`, `resolution_action`, `resolution_channel` (`web | voice`)

**Server-Sent Events extension** (per arch doc §13.11): the existing SSE channel for `Dashboard` adds escalation-list-state events so an owner viewing the queue sees real-time updates when new escalations arrive or when auto-recovery fires.

**Server-generated explainer copy** is computed at escalation creation time (in A46) and stored in `mobile_sync_owner_escalation.escalation_reason_explainer TEXT`. This deviates from the calendar conflict pattern (where diff is computed live) because the originating context can be lost between creation and resolution.

**Effort estimate**: Medium — 4–6 days (three endpoints, SSE extension, explainer copy templates per escalation reason, comprehensive test coverage).

### A48. Owner-Side Mobile-Conflict Resolution Write Path

**Triggered by**: Pass 4 Tier 1 #1 Decisions 5, 6, 8, 10 — resolution commit with pre-commit staleness check, three distinct 409 payload types, loop-closure to originating tech, audit log capture.

**Scope**:
- `POST /api/v1/owner/field-issues/{escalation_id}/resolve` — commits the resolution
  - Request body: `{resolution: 'use_tech' | 'use_server' | 'restore_and_accept' | 'override_with_tech' | 'discard_tech' | 'accept_authorized_at_capture' | 'reject_unauthorized', expected_server_state_at_view_time: ISO8601_timestamp}`
  - Response 200: `{committed: true, resolution_outcome: <enum>, post_commit_state: <JSONB>, originator_notification_dispatched: bool}`
  - Response 409 with `payload.staleness_type = 'server_changed'`: `{refreshed_escalation: <full detail payload>, message: "..."}`
  - Response 409 with `payload.staleness_type = 'auto_recovered'`: `{auto_recovery_outcome: <enum>, message: "..."}`
  - Response 409 with `payload.staleness_type = 'stale'`: `{tech_force_discarded: true, message: "..."}`
- Pre-commit staleness check follows A33 pattern from Flow 6 with the three distinct payload types
- Resolution write path:
  - For `use_tech` / `restore_and_accept` / `override_with_tech` / `accept_authorized_at_capture`: commit tech's captured operation to the appropriate domain (time entry, expense, photo, status change, LOTO, voice command); update originator queue item to `resolved_in_favor_of_tech` (or `resolved_with_action` for restore-and-accept variants)
  - For `use_server` / `discard_tech` / `reject_unauthorized`: discard tech's captured operation (purge from `mobile_sync_pending_operation`); update originator queue item to `resolved_in_favor_of_server`
- Loop closure:
  - Update `mobile_sync_event.status` and `mobile_sync_event.resolution_*` fields on the originating queue item
  - Insert push notification to originating tech via existing `notification_outbox` infrastructure (rate-limited per A35; aggregation when multiple resolved in a window)
  - Insert persistent activity log entry on originating tech mobile via `mobile_sync_event_log` (extends existing schema with `resolution_*` fields)
- Audit:
  - Insert `mobile_sync_event_audit` entry capturing `escalation_id`, `originator_user_id`, `resolver_user_id`, `resolution_action`, `resolution_channel`, `tech_local_snapshot_at_commit`, `server_state_snapshot_at_commit`, `post_commit_state`, `resolved_at`

**Voice channel routing**: when resolution comes in via voice (per Tier 1 #1 Decision 7), the same endpoint handles it; `resolution_channel` is set on the audit entry. Voice intent handler `resolve_field_issue` calls this endpoint internally.

**Mobile activity log retention** (per Tier 1 #1 Cross-Domain C): tech mobile keeps last 90 days of activity log entries locally; older entries fetched from server on demand.

**Effort estimate**: Medium-Large — 5–7 days. The variation across resolution types per operation is the main cost (each type needs domain-specific commit logic). The 409 payload differentiation, loop-closure event emission, and audit capture are smaller incremental costs.

### A49. QuickBooks Conflict Queue Endpoints + Schema Extension

**Triggered by**: Pass 4 Tier 1 #2 Decisions 1, 2, 12 — queue list with filters, conflict detail with master-aware payload, history archive. Also resolves the Pass 4 work flagged in arch doc §5.4.

**Scope**:
- `GET /api/v1/integrations/quickbooks/conflicts` — list pending conflicts for the requesting owner's tenant
  - Query parameters: `entity_type` (multi-value: `customer | quote | invoice | expense`), `master` (multi-value: `pilot | quickbooks | user_choice`), `sort` (default `-financial_impact,-detected_at`), `limit`, `offset`
  - Response: paginated list per row with `{conflict_id, entity_type, entity_identifier, entity_summary, master_direction, pilot_change_summary, qb_change_summary, detected_at, financial_delta_cents (nullable, populated for invoices), affected_entity_url}`
- `GET /api/v1/integrations/quickbooks/conflicts/{id}` — full conflict detail
  - Response: `{conflict_id, entity_type, base_snapshot, pilot_snapshot, qb_snapshot, field_diffs (server-computed), master_direction, master_recommended_action, conflict_subtype (`field_diff | deleted_in_pilot_modified_in_qb | modified_in_pilot_deleted_in_qb`), available_resolutions, financial_delta_payload (for invoices), tax_period_warning (boolean, for invoices spanning closed period)}`
- `GET /api/v1/integrations/quickbooks/conflicts/history` — historical archive with filters

**Server-Sent Events extension** (per arch doc §13.11): existing SSE channel for `Settings > Integrations > QuickBooks` adds conflict-list-state events for real-time queue updates.

**Schema extension to `integration_sync_conflict`**:
- `base_snapshot JSONB NOT NULL` — last shared state at successful prior sync
- `field_diffs JSONB NOT NULL` — server-computed field-level diff array
- `pilot_modified_at TIMESTAMPTZ NOT NULL`
- `pilot_modified_by_user_id UUID NULL`
- `qb_modified_at TIMESTAMPTZ NOT NULL`
- `qb_modified_by_external_user_label TEXT NULL` — when QB metadata exposes the modifying user
- `auto_expire_at TIMESTAMPTZ NULL` — populated when tenant opts in per entity type
- `pre_warning_at TIMESTAMPTZ NULL`

**Effort estimate**: Medium — 4–5 days. Schema extension + three endpoints + SSE wiring + diff computation per entity type. Computation per entity type is the main cost (each entity type has a different shape and field set).

### A50. QuickBooks Conflict Resolution Write Path + Auto-Expiry Celery Extension

**Triggered by**: Pass 4 Tier 1 #2 Decisions 5, 7, 11 — resolution commit with pre-commit staleness check, two 409 payload types, audit log capture. Also Decision 9 — auto-expiry off by default but tenant-configurable per entity type.

**Scope**:
- `POST /api/v1/integrations/quickbooks/conflicts/{id}/resolve` — commits the resolution
  - Request body: `{resolution: 'accept_local' | 'accept_remote' | 'restore_and_accept_remote' | 'recreate_and_keep_local' | 'delete_both', expected_pilot_modified_at: ISO8601, expected_qb_modified_at: ISO8601}`
  - Response 200: `{committed: true, resolution_outcome, post_commit_state, push_to_other_side_dispatched: bool}`
  - Response 409 with `staleness_type = 'server_changed'`: `{refreshed_conflict, message}`
  - Response 409 with `staleness_type = 'auto_recovered'`: `{auto_recovery_outcome, message}`
- Pre-commit staleness check pattern from A33 (Flow 6); same shape applied to QB
- Resolution write path:
  - For `accept_local`: push Pilot snapshot to QB via existing sync mechanism; update mapping `external_version_token`
  - For `accept_remote`: write QB snapshot to Pilot's domain entity; update mapping `internal_version_token`
  - For deletion-conflict variants: combination of restore + push, or delete + push, depending on the variant
  - Update `integration_sync_conflict.status` to `resolved`
- Audit:
  - Insert `integration_sync_log` entry capturing `conflict_id`, `resolver_user_id`, `resolution_action`, `resolution_channel` (always `'web'` for MVP since voice resolution is explicitly out of scope per Tier 1 #2 Decision 8), `pre_commit_pilot_snapshot`, `pre_commit_qb_snapshot`, `post_commit_state`, `resolved_at`

**Auto-expiry Celery task extension**:
- Existing pattern from A34 (Flow 6's calendar auto-expiry) extends to QB
- New Celery Beat task `auto_expire_qb_conflicts_per_tenant` runs hourly
- For each conflict where `auto_expire_at <= now()`, commits the tenant-configured direction
- Pre-warning task fires `notification_outbox` entry at `pre_warning_at`
- Per-entity-type tenant settings for opt-in: `qb_auto_expire_customer_enabled`, `qb_auto_expire_quote_enabled`, `qb_auto_expire_invoice_enabled`, `qb_auto_expire_expense_enabled` (all default FALSE per Tier 1 #2 Decision 9); paired direction settings `qb_auto_expire_*_direction` (`accept_local | accept_remote`)
- Default expiry interval: 60 days (vs Flow 6's 30; accounting cadence is quarterly)
- Default pre-warning: 14 days (vs Flow 6's 7)

**Voice intent registry extension**: arch doc §6 adds `list_pending_qb_conflicts` (status query only). No `resolve_qb_*` intents in MVP per Tier 1 #2 Decision 8.

**Effort estimate**: Medium — 4–5 days. The variation across entity types and resolution types is the main cost (each entity needs domain-specific commit logic). Auto-expiry Celery extension is small additional work.

### A51. Background Sync Infrastructure

**Triggered by**: Pass 4 Tier 1 #3 Decisions 1, 2, 4, 9 — push token registry, silent push handlers, sync session management, frequency cap enforcement (tenant-configurable).

**Scope**:

**Push token registry** (canonical infrastructure for future reuse beyond background sync):
- Schema: new table `mobile_device_push_token`
  - `tenant_id`, `user_id`, `device_id` (client-generated UUID), `platform` (`ios | android`), `push_token` (APNs or FCM), `app_version`, `os_version`, `registered_at`, `last_seen_at`, `notification_permission_granted` (boolean, current value), `revoked_at`
  - Unique constraint on (`tenant_id`, `user_id`, `device_id`)
- API: `POST /api/v1/mobile/push-tokens` — register or refresh device push token (called on every app launch)
- API: `DELETE /api/v1/mobile/push-tokens/{device_id}` — revoke token (called on logout or token invalidation)
- Token rotation: when APNs/FCM returns "invalid token" on send, the token is marked revoked and the next push attempt to that device is skipped

**Silent push dispatcher**:
- New module `services/mobile_background_sync.py`
- Detects when a device's queue has pending items >15 minutes old → triggers silent push
- Detects retryable failure on prior attempt → triggers silent push at next exponential backoff window
- Detects field-issue resolution loop closure (per Tier 1 #1 Decision 8) → triggers silent push to originating tech
- Per-device frequency cap: at most 1 silent push per tenant-effective `background_sync_push_interval_minutes` (default 5; system default + tenant override per arch doc §16.5; rate limit table `mobile_push_rate_limit`)
- iOS payload shape: `{aps: {content-available: 1}, sync_session_id: "..."}`
- Android payload shape: high-priority FCM with `data` payload `{sync_session_id: "..."}`

**Sync session management**:
- Schema: new table `mobile_sync_session`
  - `session_id` (UUID), `tenant_id`, `user_id`, `device_id`, `triggered_by` (`silent_push | os_opportunistic | foreground | manual`), `started_at`, `completed_at`, `outcome` (`success | partial | failed | throttled`), `items_attempted`, `items_committed`, `items_deferred`, `items_failed`, `failure_reason`
- Client reports session telemetry on completion via `POST /api/v1/mobile/sync-sessions/{session_id}/complete`
- Server-side aggregation: this telemetry feeds the queue surface row from Tier 1 #3 Decision 5 (the "last background sync · X items synced" status) on next app open

**Frequency cap enforcement**:
- Server-side rate limiting on silent push dispatch (Tier 1 #3 Decision 1, Decision 4: 1 per tenant-effective `background_sync_push_interval_minutes`, default 5)
- New platform setting `system_background_sync_push_interval_minutes` (default 5) and tenant setting `background_sync_push_interval_minutes` (nullable; null inherits system default) per arch doc §16.5 system-default-with-tenant-override pattern
- Server-side detection of OS throttling (Tier 1 #3 Decision 9: backend detects no sync attempts for >2 hours despite queued items, surfaces "Background sync delayed by your phone" to client on next sync)

**Tenant settings introduced** (per Tier 1 #3 Decision 4):
- `background_sync_enabled` (boolean; default TRUE; user override allowed)
- `background_sync_wifi_only` (boolean; default FALSE; tenant-only)
- `background_sync_battery_floor_pct` (integer; default 20; range 5–50; tenant-only)
- `background_sync_push_interval_minutes` (integer; default 5; range 1–60; tenant-only; system-default-with-tenant-override per §16.5)

**Effort estimate**: Medium-Large — 6–8 days. The push token registry and silent push dispatcher are the largest pieces (3–4 days). Sync session management and frequency cap enforcement are smaller (2–3 days). Platform-specific testing across iOS and Android adds 1 day.

---

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
| A34 Auto-Expiry of Stale Conflicts (System Default + Tenant Override) | Medium | 3–4 |
| A35 Mobile Pending-Conflicts Status & Notification Rate Limiting | Small | 1 |
| A36 Voice Intent Grammar for Calendar Conflict Resolution | Medium | 4–5 |
| A37 Offline-Capable Operations API Contract | Small-Medium | 2–3 |
| A38 Sync Queue State Model (Server-Side Visibility) | Medium | 3–4 |
| A39 Idempotency UUIDs for Offline Operations | Small-Medium | 3–4 |
| A40 Conflict Severity Classification Engine | Medium-Large | 5–7 |
| A41 Resumable Photo Upload Pipeline | Medium | 4–5 |
| A42 Voice Command Offline Capture & Deferred Processing | Medium | 4–5 |
| A43 Force-Quit Recovery State Persistence | Medium | 4–5 |
| A44 Auth Expiry Offline Handling | Small-Medium | 2–3 |
| A45 Tech-Resolvable Conflict UI Endpoints | Small-Medium | 2–3 |
| A46 Owner Escalation Routing & Notification | Medium | 3–4 |
| A47 Owner-Side Mobile-Conflict Escalation Queue Endpoints | Medium | 4–6 |
| A48 Owner-Side Mobile-Conflict Resolution Write Path | Medium-Large | 5–7 |
| A49 QuickBooks Conflict Queue Endpoints + Schema Extension | Medium | 4–5 |
| A50 QuickBooks Conflict Resolution Write Path + Auto-Expiry Celery Extension | Medium | 4–5 |
| A51 Background Sync Infrastructure | Medium-Large | 6–8 |
| **Subtotal remaining MVP (Pass 4 Tier 1 complete)** | | **140–192.5 days** |
| A13 Voice Persona (Post-MVP) | Small | 2–3 |

Plus Pass 4 Tier 2, Tier 3, and Tier 4 polish, states, and onboarding additions still to come. Plan for approximately **28–38 weeks** of backend work before UI implementation begins, depending on team parallelism. Some of the more-stable Pass 1/2/3 foundations could begin backend implementation in parallel with Pass 4 design if team bandwidth permits.

---

*This document is regenerated at the end of each design pass. See the corresponding design spec for the UI decisions that triggered each addition.*
