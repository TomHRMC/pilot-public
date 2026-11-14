# AevoFab Backend MVP Additions

**Status**: Running list — updated as UI design progresses
**Last Updated**: April 25, 2026 (Pass 3 Flow 3 complete)
**Purpose**: Track backend/database/API changes required by UI design decisions
**Handoff**: This document is the authoritative list of backend work required before UI coding begins

---

## Overview

As UI design progresses through Passes 2, 3, and 4, decisions surface that require backend changes beyond what's currently in `mvp-arch.md` and the PRD. This document captures those requirements in one place so the dev team has a single source of truth for MVP backend work.

**Workflow**: Each addition below is triggered by a specific design decision. When UI design is complete (end of Pass 4), this document is frozen and becomes the backend work plan. Tom completes backend MVP work before UI coding begins.

**Status tracker**:
- Pass 2 additions (A1–A8): previously documented; A1 Scheduling & Dispatch has since been implemented per `frontend-pass-2-sched-feat-plan.md`
- Pass 3 Flow 1 additions (A9–A13): documented in this file
- Pass 3 Flow 2 additions (A14–A17): documented in this file
- Pass 3 Flow 3 additions (A18–A20): this update

---

## Additions from Pass 2

*(see prior version of this document for full details on A1–A8)*

### Implemented

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
| **Subtotal remaining MVP** | | **43.5–63.5 days** |
| A13 Voice Persona (Post-MVP) | Small | 2–3 |

Plus Pass 3 Flows 4–7 and Pass 4 additions still to come. Plan for approximately 9–12 weeks of remaining backend work before UI implementation begins.

---

*This document is regenerated at the end of each design pass. See the corresponding design spec for the UI decisions that triggered each addition.*
