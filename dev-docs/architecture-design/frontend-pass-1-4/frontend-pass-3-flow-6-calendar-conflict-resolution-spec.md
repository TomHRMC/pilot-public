# Pilot for Trades Design System — Pass 3, Flow 6: Calendar Conflict Resolution

**Version**: 1.1
**Status**: Revised after first review — incorporating voice-resolution active and tenant-overridable expiry timeframes
**Date**: April 25, 2026
**Scope**: Web-based UI for resolving bi-directional calendar sync conflicts; mobile owner status surface; voice resolution channel
**Depends On**: Pass 1 (tokens), Pass 2 (IA), Pass 3 Flow 1 (voice patterns, confirm-as-turn), Pass 3 Flow 3 (dispatch board, calendar sync indicator), Pass 3 Flow 5 (track-changes vocabulary), `mvp-arch.md` §5.4 (QuickBooks conflict resolution pattern), `mvp-arch.md` §13.5 (Bi-Directional Calendar Sync), `mvp-arch.md` §13.7 (Calendar API endpoints)
**Backend Reference**: §13.7 endpoints already specced (`GET /api/v1/calendar/conflicts`, `POST /api/v1/calendar/conflicts/{id}/resolve`); new additions A32–A36 documented at the end of this spec

**Changelog**:
- **v1.1** (Apr 25): Decision 11 revised — voice now actively resolves conflicts (not status-only) with confirm-as-turn safeguards; Decision 13 revised — auto-expiry timeframes are system defaults that each tenant can override; A34 revised accordingly; new A36 captures voice resolution intent grammar.
- **v1.0** (Apr 25): Initial draft.

---

## Purpose

Flow 6 designs the surface where the tenant owner resolves bi-directional sync conflicts between Pilot and the connected calendar (Google Calendar at beta). This is a low-frequency, high-stakes interaction — most owners will encounter a conflict less than once a month, but when one appears, picking the wrong version means either losing scheduling work the dispatcher did or losing a calendar update made in the field.

The flow is also load-bearing for two patterns that don't yet have UI: the QuickBooks conflict resolution from §5.4 (data path defined, no UI yet) and any future bi-directional integration Pilot adds. Whatever conflict-resolution UX vocabulary Flow 6 establishes, those will inherit. Designing for that reuse is part of the brief.

## Strategic Direction

### Conflicts are unusual events; design for "what happened" not "you know how this works"

Most owners will go weeks between conflicts. They will be confused when one appears. The UI must not assume familiarity — every conflict surface must answer three questions on first read: what changed in Pilot, what changed in the calendar, and which version is correct. Brief contextual copy and clear before/after framing matter more than terseness.

### Per-conflict resolution; no bulk actions in MVP

Each conflict is its own decision. There is no "accept all my version" or "accept all calendar version" button. After a long sync outage producing 20 conflicts, the owner walks through them one at a time. Bulk operations look convenient and turn dangerous fast — the owner who clicks "accept all local" because they were rushed is the owner who later discovers a calendar update they wanted to keep. Phase 2 may revisit this with usage data.

### Pilot is the long-run default

§13.1 establishes Pilot as the source of truth and the calendar as a mirror. The UI honors this in two places: passive expiry of unresolved conflicts defaults to `accept_local`, and the column ordering on the diff places Pilot on the left (the read-leftward primacy slot). The owner can absolutely accept the calendar's version — but the platform's posture is that scheduling decisions live in Pilot unless told otherwise.

### Voice is a first-class resolution channel, with safeguards

Earlier iteration of this spec restricted voice to status queries only. On reflection, that contradicts Pilot's voice-first positioning — if the owner can voice-approve a quote (Flow 5), they should be able to voice-resolve a conflict. The locked design now allows voice resolution for the simple "accept this side" case, but with safeguards: confirm-as-turn before commit (per Flow 1), explicit readback of what gets committed, and a deliberate route-to-web for the more complex deletion-conflict and post-staleness recovery paths where the cognitive load is too high for voice.

### Resolution UI is web-only; mobile is informational

The mobile Owner tab gets a notification badge and a deep-link to web; no resolution surface lives on mobile. Two reasons: (1) the diff rendering needs the screen real estate of a desktop browser, and (2) conflict resolution is a deliberate "I'm at my desk" action rather than a "between job sites" one. This mirrors the QuickBooks status-row + deep-link pattern already specced in Pass 2. (Voice resolution is the exception that proves the rule — voice is a separate input channel, not a mobile-screen channel.)

## Locked Design Decisions

### 1. Two Web Entry Points: Status Indicator + Settings → Integrations → Calendar

**Decision**: Conflicts can be reached from two entry points on web:

1. **Dispatch board calendar sync indicator** (already designed in Flow 3). When pending conflicts exist, the indicator shows an amber dot with a count ("3 conflicts"). Clicking the indicator routes to the conflicts list.
2. **Settings → Integrations → Calendar**. The deliberate "I came here to manage calendar sync" entry point. Houses connection status, sync activity log, and the conflicts list as a section.

Both routes land on the same `/settings/integrations/calendar` surface, with the conflicts section anchored if reached from the indicator.

**Rationale**: The dispatch board is where conflicts first become visible (the owner's already-open work surface). Settings is where the owner consciously navigates when sync is the topic. Two entry points serve two states of mind; both terminate at the same place.

### 2. No Top-Level "Conflicts" Navigation

**Decision**: Calendar sync conflicts do not get a dedicated top-nav slot. The notification-driven routing plus the Settings location is sufficient.

**Rationale**: Adding a global "Conflicts" nav for an infrequent feature pollutes the IA and creates a naming collision with the dispatch board's existing conflicts-blocked count from Flow 3 (those are scheduling conflicts, not sync conflicts — different domain entirely). Keeping calendar sync conflicts inside Settings → Integrations avoids the collision.

### 3. Conflicts List as a Compact Table with Urgency Sorting

**Decision**: The conflicts list renders as a paginated table inside the Calendar settings surface, with these columns:

| Event | Conflict type | Pilot change | Calendar change | Job link | Resolve |

- **Event**: title of the conflicting job/event
- **Conflict type**: pill/icon — `Modified ↔ Modified`, `Deleted ↔ Modified`, `Modified ↔ Deleted`
- **Pilot change**: who, when, brief summary ("Mike rescheduled, 3 hr ago")
- **Calendar change**: source label, when, brief summary ("via Google Calendar, 1 hr ago")
- **Job link**: deep link to the affected job's detail page (opens new tab)
- **Resolve**: button → opens resolution view

Default sort: by **proximity-to-scheduled-start** — the affected job's `scheduled_start_at` ascending, soonest-first. A conflict on a job scheduled for tomorrow appears above a conflict on a job scheduled for October regardless of which was detected more recently. A sort toggle (header click on "Event" column) flips to detection-time-descending for owners who prefer fresh-first.

**Rationale**: The owner is triaging by "what could affect upcoming work" not "what just landed." Tomorrow's conflicts are operationally urgent; October's can wait. Detection-time sort is natural for notification-driven UIs but less useful when there's a backlog. Offering it as a toggle covers both mental models.

### 4. Resolution View as Side-by-Side Two-Column Diff

**Decision**: The resolution view is a focused single-conflict screen with two columns. Left = Pilot; right = the connected calendar (labeled "Google Calendar" at beta, provider-name-aware via the integration record). Each column shows the current state of the event with field-level highlighting of what differs.

The view is **modal-feeling but routed** — it has its own URL (`/settings/integrations/calendar/conflicts/{id}`), so it's bookmarkable, refresh-able, and back-navigable. Not a true modal. The owner's full attention should be on this one decision, but they should also be able to drop into a job detail page in another tab to verify context, then return.

**Rationale**: Side-by-side beats sequential or stacked treatments for diffs because the eye can compare without scrolling. URL routing instead of true modal preserves the open-the-job-in-another-tab workflow that's natural for "let me check what's actually scheduled" verification.

### 5. Field-Level Diff Vocabulary Reuses Flow 5's Track-Changes Palette

**Decision**: Within each column, fields are shown with a consistent visual diff vocabulary:

| Field state | Color | Treatment |
| :--- | :--- | :--- |
| Unchanged from last sync | Neutral | Plain text |
| Modified in this version | Amber (alert palette) | Background tint, value shown with prior value as struck-through helper text below |
| Added in this version (e.g., new note, new attendee) | Margin (green) | Background tint, "(added)" annotation |
| Removed in this version (e.g., site address cleared) | Fault (red) | Strikethrough on the field, "(removed)" annotation |

This is the same palette and treatment pattern Flow 5 established for owner-pending edits during quote review. Semantically consistent: amber means "look here, something changed."

**Rationale**: Reuse of Flow 5's vocabulary establishes a platform-wide diff treatment. Owners who learn it once for quote approval transfer it directly to calendar conflict resolution and (future) QuickBooks conflict resolution. Single mental model across all "compare-and-pick" surfaces. This is the third reuse — it's officially a pattern.

### 6. Bottom Action Bar Is Two Big Buttons

**Decision**: The resolution view has two primary actions at the bottom of the screen:

- **Use Pilot version** (primary; brand indigo)
- **Use Google Calendar version** (secondary; neutral with brand-tinted border)

Below them, a small text link: "Resolve later." The header has a back affordance to the conflicts list.

**Rationale**: Two buttons match the binary decision. Making Pilot primary reflects the source-of-truth posture without removing the alternative. The "Resolve later" escape hatch acknowledges that some conflicts need offline thinking ("did I really delete that, or was that an accident?") without treating non-action as a hidden third path. The owner returns to the list intentionally.

### 7. Deletion Conflicts Have a Distinct Treatment

**Decision**: When the conflict is `Deleted ↔ Modified` or `Modified ↔ Deleted` (one side deleted the event, the other modified it), the resolution view does not render side-by-side fields. Instead, it renders a focused "what do you want to do?" question with two paths:

- **`Deleted in Pilot ↔ Modified in calendar`**: "Pilot no longer has this job. The calendar event was modified after deletion. → [Restore the job from the calendar] or [Delete from calendar too]"
- **`Modified in Pilot ↔ Deleted in calendar`**: "The calendar event was deleted. Pilot still has the job. → [Recreate the calendar event from Pilot] or [Delete the Pilot job]"

Both paths preserve the recently-modified version. Both paths are explicit about what gets created or destroyed.

**Rationale**: A deletion isn't a field-level change; it's an existence-level change. Treating it as "compare these two versions" misleads the owner about what they're picking. Two-button decision with explicit verbs ("restore," "recreate," "delete") is cognitively clearer.

### 8. Pre-Resolution Staleness Check

**Decision**: When the owner clicks "Use Pilot version" or "Use Calendar version" (web), or confirms a voice resolution, the API re-evaluates the conflict before committing. If either side has been modified since the conflict was first detected (e.g., the calendar pull just brought in a new change), the API returns 409 Conflict with the refreshed conflict payload. The web UI re-renders the resolution view with the updated state and surfaces a brief banner: "This conflict has been updated. Review and pick again." The voice path responds: "The conflict has changed since you last looked at it — opening the diff view on web," and stops voice resolution.

**Rationale**: The conflict-detection task runs every 5 minutes; an owner who took 10 minutes to read the diff (or who starts a voice resolution after seeing a notification) might be looking at stale state. Without this check, the owner could accept their version and silently overwrite a calendar change they hadn't seen. The 409-and-refresh pattern matches what the dispatch board does for optimistic locking (per A19), keeping the platform's concurrency story consistent across surfaces.

### 9. Resolution Is Auditable but Not "Undoable" via this UI

**Decision**: When a conflict is resolved (web or voice), the chosen version is committed and pushed to the other side. There is no "undo resolution" button. If the owner realizes they picked wrong, they edit the event normally — which generates a fresh sync push to the calendar. The audit trail (`calendar_sync_log`) preserves the resolution decision, the resolver's identity, and whether it was committed via web or voice.

**Rationale**: An undo button would compete with the natural "edit the event" path and create a confusing two-paths-to-fix situation. The audit trail satisfies the "who did what" question; the editing affordance satisfies the "fix it" question. Conflicts are conceptually one-shot decisions; once committed, they're history.

### 10. Mobile Owner: Notification + Status Row + Deep Link

**Decision**: On the mobile Owner tab, a "Calendar sync" status row sits alongside the existing "QuickBooks sync" row. State rendering:

- **Healthy**: green dot, "Calendar sync · synced 2 min ago"
- **Pending conflicts**: amber dot, "Calendar sync · N pending conflicts," subtitle "Resolve on web →"
- **Connection error (token expired)**: red dot, "Calendar sync · reconnect needed → Settings"

Tapping a row deep-links to the corresponding web URL.

Push notifications fire when a conflict is first detected, with the same content that lands in `notification_outbox` per §13.5. Rate-limited per A35.

**Rationale**: Parity with the QuickBooks pattern means owners learn the integration-status grammar once. The mobile screen surface is informational because the resolution UI is too dense for a phone, and because conflict resolution is rarely time-urgent enough to demand mobile-first. Voice resolution (Decision 11) is the exception — it works from anywhere including the phone, but bypasses the mobile screen entirely.

### 11. Voice Resolution Is Active, with Confirm-as-Turn Safeguards

**Decision**: Voice supports both status query and active resolution. Two intents:

**Status query** (`list_pending_calendar_conflicts`):
- "Do I have any pending sync conflicts?" → AI responds with count and brief urgency summary ("You have 3 — one is on Thursday's Johnson panel upgrade, plus two scheduled for next month.")

**Resolution** (`resolve_calendar_conflict`):
- "Resolve the Johnson conflict — accept Pilot" / "...accept calendar"
- "Accept the Pilot version of the Johnson conflict"
- Identifier resolution: by customer name, job title, or scheduled date. AI disambiguates if multiple match (per Flow 1 disambiguation pattern): "You have two Johnson conflicts — the panel upgrade or the inspection?"
- **Confirm-as-turn before commit**: the AI reads back what gets committed and what gets discarded before executing. Example for the running scenario:
  > "Accepting the Pilot version of Tom Johnson's panel upgrade conflict. That keeps the reschedule to Thursday at 2 PM. The calendar's note about the 30A subpanel breaker won't be saved. Confirm?"
- The owner's "yes" / "confirm" / "do it" commits; any other utterance cancels and the AI offers to read the diff via web link.
- **Voice resolution honors the staleness check (A33)**: if state has shifted between identification and confirmation, the AI announces "the conflict has changed since you last looked at it — opening the diff view on web" and routes to web with a deep link.

**Resolution paths that route to web instead**:
- **Deletion conflicts** (Decision 7): the existence-level decision and the verb-based path choices ("restore," "recreate," "delete") are too easy to mis-pick by voice. AI responds: "That's a deletion conflict — it needs the diff view to be safe. I'll open it on web." A push notification with the deep-link follows.
- **Post-staleness recovery** (above): once the diff has shifted, the owner needs to see the new state visually.

**Rationale**: Pilot's voice-first positioning extends to all owner workflows that don't require dense visual comparison. The confirm-as-turn safeguard plus the explicit field-readback before commit make wrong-resolution risk acceptable for the simple accept-this-side case. Deletion conflicts and post-staleness recovery stay on web because the cognitive load and consequence cost are too high to mediate through speech alone. This mirrors Flow 5's "voice approves but doesn't edit" principle: voice handles the binary decision, touch handles the complex one.

### 12. Empty State Teaches Normalcy

**Decision**: When there are no pending conflicts, the conflicts section shows a calm, informative empty state: "No sync conflicts. Last successful sync: 2 minutes ago." Below it, a small expandable "Recent sync activity" panel showing the last 10 sync events as a compact log (event title, direction, timestamp, status).

**Rationale**: An empty page leaves the owner uncertain whether sync is working. The empty-state copy plus the sync-activity log answers "is this functioning?" without requiring the owner to learn what "no conflicts" means in this context. The activity log also doubles as a debugging surface when something does go wrong.

### 13. Auto-Expiry With System Defaults That Tenants Can Override

**Decision**: Conflicts unresolved for a configurable time period auto-resolve to `accept_local` (Pilot as source of truth). At a configurable point before expiry, the owner gets a pre-warning notification.

**System defaults** (configurable platform-wide by Pilot admins):
- Auto-expire: **30 days**
- Pre-warning: **7 days before expiry**

**Tenant overrides** (each tenant can override either or both):
- `calendar_conflict_auto_expire_days` — integer; null falls back to system default; explicitly nullable by tenant to disable auto-expiry
- `calendar_conflict_pre_warning_days` — integer; null falls back to system default; explicitly nullable to disable pre-warning
- Validation: when both are set, `pre_warning_days < auto_expire_days` enforced server-side

The auto-resolution is logged with a distinguishing flag (`auto_resolved_stale = TRUE`) in `calendar_sync_log` so it's visibly distinguishable from owner-initiated resolution in any future audit.

**Rationale**: Conflicts that sit forever in abandoned tenants pollute the conflict-count metric and degrade the metric's signal value. Auto-expiry to local is consistent with the Pilot-as-source-of-truth posture from §13.1. The pre-warning gives the owner one final chance to act. Two-tier configuration (system defaults + tenant overrides) reflects two realities: Pilot needs to adjust platform-wide defaults based on operational data; individual tenants have legitimate reasons to want different behavior (strict manual resolution for a security-conscious operation; more aggressive auto-expiry for a high-volume one). Both values configurable + nullable means tenants who want zero auto-resolution can have that, and tenants who want auto-resolution but no pre-warning noise can have that too.

### 14. Connection Management Lives in the Same Settings Surface

**Decision**: Settings → Integrations → Calendar contains, in order: connection status (with reconnect action when disconnected), conflicts section, sync activity log. When the integration is in error state due to expired refresh token (per §13.9), reconnection is the owner's primary action; conflicts remain visible but are pinned with an amber banner: "Sync error blocking automatic conflict push — reconnect to resume." Conflicts can still be resolved while disconnected; the resolutions queue locally and push once reconnected.

**Rationale**: Consolidating connection management and conflict resolution on one Settings page matches the QuickBooks pattern and avoids hunting across pages. The "queue and push later" behavior keeps the owner productive even when sync infrastructure has temporarily failed — they can do the cognitive work of resolving conflicts now, even if the push is deferred.

## UX Patterns Established (Inherited by Future Flows)

Flow 6's design becomes the template for:

| Pattern | Reuse |
| :--- | :--- |
| Side-by-side two-column diff with field-level highlighting | QuickBooks conflict resolution UI; any future bi-directional integration |
| Diff color vocabulary (amber=modify, green=add, red=remove) — third reuse after Flow 5 | Cementing the platform-wide track-changes pattern |
| Per-conflict resolution; no bulk actions in MVP | Any future high-stakes bulk-vs-single decision flow |
| Pre-commit staleness check with 409-and-refresh | All async-conflict-prone write paths |
| Distinct deletion-conflict UX from field-conflict UX | Any future sync feature involving entity lifecycle |
| Status row in mobile Owner tab for integration health | All bi-directional integrations |
| Voice resolution with confirm-as-turn readback for binary decisions | Any future voice-resolvable approval/conflict flow (extends Flow 5's voice pattern) |
| Voice routes to web for cognitively complex sub-cases | Any voice flow with hidden complexity (deletion, multi-version, error recovery) |
| Auto-expiry with pre-warning notification | Any backlog-of-decisions UI that risks indefinite accumulation |
| System-default + tenant-override two-tier configuration | Any tenant setting with legitimate platform-wide and per-tenant tuning needs |

## Cross-Domain Considerations

### A. The QuickBooks conflict resolution UI inherits this design wholesale

QuickBooks bi-directional sync (§5) has the same data model (JSONB snapshots of both versions, `accept_local` / `accept_remote`) but no UI specced. The Flow 6 patterns transfer directly: same Settings → Integrations location, same two-column diff treatment, same field-level vocabulary, same auto-expiry logic, same mobile status row, same voice-resolve-with-confirm pattern. When QB conflict resolution UI gets designed (Pass 4 or beyond), it should reference Flow 6 as the canonical pattern rather than re-deciding any of this.

### B. Base-snapshot capture is needed for accurate diff display

Per §13.5, the conflict log stores both current versions but doesn't explicitly store the base (last-successful-sync) state. To render "what changed in each side since they were last in agreement," the UI either needs to query `calendar_sync_log` for the prior shared state OR the conflict-detection task needs to capture it. The simpler approach is to capture `base_snapshot` at conflict-detection time. **Captured as backend addition A32 below.**

### C. Conflict counting in the dispatch board's top status indicator

Flow 3's calendar sync indicator currently has three states (synced / syncing / error). With pending conflicts present, the indicator should distinguish "sync is working but you have unresolved conflicts" from "sync is broken." Suggesting a fourth state: amber dot with a count ("3 conflicts"), distinct from the green synced state and the red broken-sync state. This is a Flow 3 refinement, not a new backend addition (the count is already retrievable via existing endpoints).

### D. Notification frequency and rate limiting

If a tenant accumulates 10 conflicts in a day, do they get 10 notifications or one batched notification? Recommendation: one push notification per detection event, but rate-limited per tenant (no more than 4/hour). Detail to confirm with dev team; doesn't block design. Captured in A35 scope.

### E. Calendar provider name in UI

The right-column header reads "Google Calendar" at beta. The architecture is provider-abstract (§13.3). The UI should read the provider's display name from the integration record rather than hardcoding "Google Calendar," so that if Outlook or another provider is added, the column header updates automatically. Trivial implementation note for the dev team.

### F. System-default tier configuration is new infrastructure

Decision 13's system-default + tenant-override pattern requires a system-level configuration mechanism that doesn't yet exist for most tenant settings (which are tenant-only). For MVP simplicity, system defaults can live as constants in code/configuration files; tenant overrides live in `tenant_setting`. If Pilot later wants admin-tier UI to change defaults platform-wide without a deploy, that's a Phase 2 addition. **Captured as a note in A34** rather than a separate backend addition.

## Deferred Items (For Future Iteration)

- **Bulk resolution actions** — explicitly excluded from MVP per Strategic Direction; revisit only with usage data showing volume warrants it
- **Three-way diff with base snapshot visible** — MVP shows two current versions with field-level diffs; full base-state visualization is a Phase 2 polish
- **Conflict resolution preview** — "show me what will happen if I accept this version" — Phase 2
- **Owner-defined auto-resolution rules** — e.g., "always trust Pilot when calendar change is older than 24 hours" — Phase 2
- **Per-event sync exclusions** — owner marks specific events as "don't sync to calendar" — Phase 2
- **Mobile resolution UI** — explicitly out of scope; revisit only if data shows web-only is a friction point
- **Multi-calendar support** — MVP is one calendar per tenant; multi-calendar is Phase 2 or later
- **Outlook / iCal feed providers** — provider abstraction is in place per §13.3; second provider is Phase 2
- **Conflict history search** — search resolved conflicts by event, date, resolver, decision — Phase 2
- **Admin-tier UI for system-default settings** — Phase 2; system defaults stay configuration-file-only for MVP
- **Voice-driven deletion conflict resolution** — explicitly routed to web in MVP; revisit only if owner data shows the "open on web" interruption is friction

## Validation Checklist

Before implementation begins:

- [ ] Dev team aligned on the two-column diff treatment as the canonical pattern (will be reused for QuickBooks)
- [ ] Pre-resolution staleness check (A33) wired to existing optimistic-locking pattern from A19
- [ ] Auto-expiry Celery task (A34) added to scheduling task registry; pre-warning notification path tested
- [ ] System-default + tenant-override resolution logic confirmed for both expiry and pre-warning settings
- [ ] Base snapshot capture (A32) verified to fit within existing `calendar_sync_conflict` schema or noted as a clean schema addition
- [ ] Mobile Owner tab UI parity with QuickBooks sync row pattern confirmed
- [ ] Voice intent for status query (`list_pending_calendar_conflicts`) added to `voice_action_router.py` registry
- [ ] Voice intent for resolution (`resolve_calendar_conflict`) added with confirm-as-turn pattern, identifier-disambiguation, and route-to-web fallback for deletion / post-staleness cases (A36)
- [ ] Voice readback copy reviewed by Tom (the "what gets kept / what gets discarded" wording is the highest-stakes voice surface in MVP)
- [ ] Flow 3 calendar sync indicator amber-with-count state added to Pass 4 polish list
- [ ] Field-level diff computation (server-side, A32) reviewed for performance against expected payload sizes
- [ ] Audit-trail completeness for resolution decisions verified against `calendar_sync_log` retention policy; resolver-channel (web vs voice) captured
- [ ] Provider display name pulled from integration record, not hardcoded as "Google Calendar"

## Backend Additions (New for Flow 6)

The following additions extend the running ledger. These will fold into `backend-mvp-additions-v3.md`.

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

### A33. Pre-Resolution Staleness Check

**Triggered by**: Conflicts may be modified between detection and the owner's resolve action. Without a check, the owner can silently overwrite a state they didn't see. Applies to web AND voice resolution paths.

**Scope**:

- `POST /api/v1/calendar/conflicts/{id}/resolve` accepts `expected_pilot_modified_at` and `expected_external_modified_at` parameters
- Server re-evaluates: if either timestamp on the live conflict record exceeds the expected, returns 409 Conflict with the refreshed conflict payload
- Frontend handles 409 by refreshing the resolution view and surfacing a "this conflict has been updated" banner; owner re-decides
- Voice handler (A36) handles 409 by aborting confirmation, announcing the change, and routing to web with a deep link
- Same pattern as the dispatch board's optimistic locking from A19

**Effort estimate**: Small — 1 day (API parameter validation, refresh pattern reuse from A19; voice handler integration is in A36's scope).

### A34. Auto-Expiry of Stale Conflicts (System Default + Tenant Override)

**Triggered by**: Conflicts unresolved for long periods clutter the conflict count and degrade the metric's signal value. Two-tier configuration (platform-wide default; per-tenant override) gives both Pilot and individual tenants tuning control.

**Scope**:

**System-level configuration** (file/config-based for MVP; admin UI is Phase 2):
- `SYSTEM_CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS` — default `30`
- `SYSTEM_CALENDAR_CONFLICT_PRE_WARNING_DAYS` — default `7`
- These live in application settings; a deploy is required to change them in MVP

**Tenant-level overrides** (UI editable per tenant):
- `calendar_conflict_auto_expire_days` — integer; NULL falls back to system default; tenant can explicitly set to NULL via UI to disable auto-expiry entirely (resolved as a sentinel, distinct from "use the default")
- `calendar_conflict_pre_warning_days` — integer; NULL falls back to system default; explicitly nullable via UI to disable pre-warning
- Validation: when both are set, `pre_warning_days < auto_expire_days` enforced server-side; reject with 400 otherwise
- Settings UI: Settings → Integrations → Calendar → "Auto-resolution" subsection, with two integer inputs and explicit "Use system default" toggles plus "Disable" toggles

**Resolution logic** (server-side, when evaluating a conflict's age):
```
expire_days = tenant.calendar_conflict_auto_expire_days
if expire_days IS UNSET (no row): use SYSTEM default
if expire_days IS NULL (explicit disable): no auto-expiry
otherwise: use the tenant value
```
Same logic for `pre_warning_days`.

**Celery Beat task**: `expire_stale_calendar_conflicts` (daily)
- For each conflict, compute its applicable `expire_days` and `pre_warning_days` per the resolution logic above
- If conflict age >= `expire_days - pre_warning_days` and pre-warning not yet sent for this conflict: enqueue notification "N conflicts will auto-resolve in 7 days" (or the configured pre-warning window)
- If conflict age >= `expire_days`: invoke the existing resolve endpoint internally with `accept_local`, log to `calendar_sync_log` with `auto_resolved_stale = TRUE`, send notification

**Audit query**: `auto_resolved_stale = TRUE` flag distinguishes auto-resolutions from owner-initiated ones in any future investigation.

**Note for dev team**: the system-default mechanism is new infrastructure if Pilot doesn't already have a "system config registry" pattern. Suggested implementation for MVP: a single `system_config.py` module exposing typed constants, loaded at app startup from environment variables with the config-file values as fallback. Phase 2 may upgrade this to an admin-tier database table editable by Pilot support staff.

**Effort estimate**: Medium — 3–4 days (task implementation, two-tier resolution logic, settings UI plumbing for both fields with default/disable/override states, audit flagging).

### A35. Mobile Pending-Conflicts Status & Notification Rate Limiting

**Triggered by**: Mobile Owner tab needs a status row showing pending conflict count for parity with the QuickBooks pattern; notification storms during outage recovery need rate limiting.

**Scope**:

- `GET /api/v1/calendar/status` (existing, per §13.7) extended to return:
  - `connection_status: 'connected' | 'syncing' | 'error' | 'disconnected'`
  - `last_successful_sync_at`
  - `pending_conflicts_count`
  - `requires_reconnect: boolean` (true when token-expired error)
- Mobile Owner tab consumes this for the "Calendar sync" row rendering
- Push notifications on conflict detection use existing `notification_outbox` infrastructure (§13.5)
- Rate limit: max 4 conflict-detection notifications per tenant per hour. Exceeding the limit collapses subsequent detections into a single batched notification ("3 more conflicts detected — resolve on web")

**Effort estimate**: Small — 1 day (response shape additions, rate-limit logic; frontend consumption is design only).

### A36. Voice Intent Grammar for Calendar Conflict Resolution

**Triggered by**: Decision 11 — voice can actively resolve modified-modified conflicts via the confirm-as-turn pattern, with explicit route-to-web for deletion conflicts and post-staleness recovery.

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
- Field-level edits in the conflict ("change the time to 3pm in the Johnson conflict") → "I can pick a side, but I can't edit the values via voice. Want me to open it on web?"

**RBAC**: existing `integrations.manage` permission is sufficient; voice handler honors the same RBAC check as the web endpoint.

**Effort estimate**: Medium — 4–5 days (intent matching, identifier disambiguation, server-side voice readback rendering using A32 diff payload, confirm-as-turn flow integration with `context_window_json` from A12, refusal-with-redirect logic, integration tests covering the staleness-check race).

---

## Next: Pass 3 Flow 7

The final Pass 3 flow is **offline-to-online sync with conflict resolution (mobile)** — the hardest flow, saved for last per the locked sequence. It will inherit the conflict-resolution vocabulary established here (and in Flow 5's track-changes work), but for a much messier domain: clock-ins, photos, expenses, and time entries created without network, then reconciled when the device comes back online. Different from Flow 6 in that resolution is largely automatic with edge-case escalation, rather than always-owner-resolved.

After Flow 7 completes, Pass 3 wraps and the natural next step is consolidating new requirements into a v3 of `backend-mvp-additions.md` (now extended through A36) and considering whether to issue a PRD v2 covering everything Pass 3 surfaced (per the framework doc's parallel-track concern).
