# AevoFab Backend MVP Additions

**Status**: Running list — updated as UI design progresses
**Last Updated**: April 24, 2026 (Pass 3 Flow 1 complete)
**Purpose**: Track backend/database/API changes required by UI design decisions
**Handoff**: This document is the authoritative list of backend work required before UI coding begins

---

## Overview

As UI design progresses through Passes 2, 3, and 4, decisions surface that require backend changes beyond what's currently in `mvp-arch.md` and the PRD. This document captures those requirements in one place so the dev team has a single source of truth for MVP backend work.

**Workflow**: Each addition below is triggered by a specific design decision. When UI design is complete (end of Pass 4), this document is frozen and becomes the backend work plan. Tom completes backend MVP work before UI coding begins.

**Status tracker**:
- Pass 2 additions (A1–A8): previously documented; A1 Scheduling & Dispatch has since been implemented per `frontend-pass-2-sched-feat-plan.md`
- Pass 3 Flow 1 additions (A9–A13): this document

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

## Summary of New Tenant Settings (Pass 2 + Pass 3)

| Setting | Default | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `require_approval_for_tech_quotes` | ON (multi-user), OFF (solo) | Quote approval workflow | A2 |
| `max_discount_pct_owner` | 15% | Margin cap for owner-applied discounts | A3 |
| `voice_persona_tone` | `balanced` | AI personality tone (Post-MVP) | A13 |

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
| **Subtotal remaining MVP** | | **26–39 days** |
| A13 Voice Persona (Post-MVP) | Small | 2–3 |

Plus Pass 3 Flows 2–5 and Pass 4 additions still to come. Plan for approximately 6–8 weeks of remaining backend work before UI implementation begins.

---

*This document is regenerated at the end of each design pass. See the corresponding design spec for the UI decisions that triggered each addition.*
