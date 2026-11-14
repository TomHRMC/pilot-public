# Pilot for Trades Design System — Pass 3, Flow 7: Offline-to-Online Sync

**Version**: 1.0
**Status**: Draft for review
**Date**: April 25, 2026
**Scope**: Mobile offline behavior for tech operations; sync queue UX; conflict resolution on the device; auth and storage edge cases; voice offline capture
**Depends On**: Pass 1 (tokens, voice state machine, mobile dark default), Pass 2 (mobile IA), Pass 3 Flow 1 (voice patterns, confirm-as-turn), Pass 3 Flow 2 (ETC capture), Pass 3 Flow 3 (four-class conflict pattern), Pass 3 Flow 4 (always-preview-before-send), Pass 3 Flow 6 (track-changes vocabulary, conflict resolution language), `mvp-arch.md` §7.6 (Idempotency Keys), `mvp-arch.md` §3 (Background Processing), `mvp-arch.md` §4.5 (Cognito MFA)
**Backend Reference**: New additions A37–A46 documented at the end of this spec

---

## Purpose

Flow 7 is the hardest design problem in the MVP. The mobile app must work continuously when the tech is in a basement, attic, parking garage, or rural area without signal — and reconcile gracefully when the device returns to network. Done badly, the tech loses work, the data is wrong, or the owner's reports are missing chunks of reality. Done well, the tech doesn't notice the network state at all; everything just works.

The design problem is two-sided. From the tech's perspective: optimistic UI is essential — nothing is more frustrating than tapping "clock in" and waiting on a spinner that never resolves. From the platform's perspective: every offline operation needs an eventual reconciliation path that handles the messy reality of conflicting changes the tech couldn't see while offline.

Flow 7 is also load-bearing for Phase 2 ambitions: the pattern established here for tech-side offline-with-reconcile carries over to any future offline-capable surface (potentially the dispatch board on tablets in the field, the AR aging surface for an owner reviewing payments while traveling).

## Strategic Direction

### Optimistic UI is mandatory; field reality demands it

A tech in a basement cannot wait 30 seconds to find out whether their clock-in succeeded. The platform commits to a model where every offline-capable operation appears successful immediately on the device, with a non-disruptive "pending sync" badge until confirmation arrives. Sync failures become *visible problems to address* later, not *blocked operations* in the moment. This pattern is universal across every locked decision below.

### Sync visibility is non-negotiable

The tech must always know what's queued, what's in flight, and what failed. A silent backlog of unsynced data is a category-A bug — it's how data loss happens. The sync queue surface is therefore a first-class UI, accessible at all times via a persistent global indicator, not buried under settings.

### Auto-resolve where possible; escalate where necessary

Most offline operations sync without conflict. A few create conflicts the tech can resolve on the phone. A small subset require the owner. The platform classifies conflicts into four severity tiers — mirroring the dispatch board's four-class pattern from Flow 3 and the differentiated treatment from Flow 6 — and routes each to the right resolver. The explicit goal is that tech intervention is rare and owner intervention is rarer still.

### Photos are heavy; treat them differently

Time entries and expenses are kilobyte payloads. Photos are megabyte payloads. The MVP cannot treat them as the same queue without exposing the tech to constant cellular data drain or stuck syncs. Photos go into a separate upload pipeline with WiFi preference (configurable) and resumable transfer. Data sync runs on cellular; photos prefer WiFi.

### Voice is captured offline; processed online

The Whisper + Llama processing pipeline lives on Pilot's GPU instance — there's no on-device transcription in the MVP. Voice audio captured offline is stored locally and uploaded for processing when the device reconnects. The tech sees "voice captured" not "voice failed," and the resulting intent runs through the normal disambiguation flow when transcription completes.

## Locked Design Decisions

### 1. Offline-Capable Operations: Explicit MVP Set

**Decision**: The platform commits to a specific list of operations that work fully offline. Anything not on the list must explicitly fail or queue with a clear message when triggered offline.

**Fully offline-capable**:
- Clock in / clock out
- Time entry creation (with ETC per Flow 2)
- Expense capture (with attached photo)
- Site / job photo capture
- Status changes on already-assigned jobs (in progress, complete, etc.)
- LOTO check confirmation (with device timestamp)
- Voice audio capture (transcription deferred per Decision 7)
- Free-text notes on a job
- NEC code calculations (math; cached NEC reference data)
- Change order creation against an already-assigned job

**Partial offline** (functional with caveats):
- Customer / job lookup — works for cached entities; UI shows "offline — limited data" for uncached records
- Material catalog lookup — same as customer
- Job assignments — read from cache; if reassignment happened server-side, conflict surfaces on sync (per Decision 5)

**Not offline-capable** (requires online):
- Customer creation (avoids deduplication nightmare; tech can capture details as a note for online creation later)
- Quote send (needs server-rendered PDF + delivery)
- Customer comms send (per Decision 14 — preserves Flow 4 always-preview-with-live-ETA rule)
- Calendar sync, QuickBooks sync, dispatch board, owner approval actions
- Voice command processing (capture is offline; processing requires online)

**Rationale**: This list is a backend contract, not a UX preference. Every operation in the offline set must work with no network and must reconcile cleanly on sync. Operations not in the set must fail explicitly with an offline-aware message rather than silently dropping data. Documenting the set up front prevents surprise gaps later.

### 2. Connection State Indicator: Global App-Level Pill

**Decision**: A pill-shaped indicator in the top status bar of every mobile screen displays the combined connection + sync state:

| State | Visual | Behavior |
| :--- | :--- | :--- |
| Online and synced | Hidden | No visual noise when nothing is happening |
| Online with pending items | Amber dot · "12 syncing" | Pulsing while items in flight |
| Offline with queued items | Red dot · "Offline · 12" | Solid; shows queued count |
| Action needed (regardless of connection) | Red dot · "Action needed (1)" | Visible regardless; takes priority over other states |

Tapping the indicator opens the sync queue drawer (Decision 4).

**Rationale**: The tech's awareness of their own sync state should be ambient, not consulted. A persistent indicator that's hidden when irrelevant and prominent when not strikes the right balance. The action-needed state always surfaces because it represents a problem the tech can sometimes resolve while still offline (e.g., picking a side in a tech-resolvable conflict where both versions are locally available).

### 3. Optimistic UI for All Offline-Capable Operations

**Decision**: Every offline-capable operation shows immediate success in the UI when triggered. A small "pending sync" badge marks the affected entity until sync confirms (badge clears) or fails (badge becomes red with retry/resolve affordance).

Examples:
- Clock in → instantly shows "clocked in at 8:02 AM" on the Today tab; small amber dot next to the entry until synced
- Time entry → appears in the day's list immediately with pending badge
- Photo capture → thumbnail appears in the expense's photo grid with a small "uploading" overlay; clears when uploaded; turns red with retry if upload failed

**Rationale**: Field operations cannot tolerate spinner-and-wait UX. Optimistic UI requires the platform to commit to eventually-consistent semantics, but the alternative — blocking the tech during sync — is worse in every realistic scenario. The badge plus the queue surface (Decision 4) keeps the tech informed without slowing them down.

### 4. Sync Queue Surface as Bottom Sheet

**Decision**: The sync queue is a bottom-sheet drawer accessible by tapping the connection state indicator (Decision 2). Contents grouped by status, in attention-priority order:

1. **Action needed** — items that failed and require tech input (top of drawer, red accent)
2. **Syncing** — items currently in flight (amber accent; per-item progress for photos)
3. **Pending** — items queued and awaiting connection or sync trigger (neutral)
4. **Recently synced** — last 10 successfully synced items (bottom; muted; green checkmarks)

Each item shows: type icon (clock for time entry, camera for photo, mic for voice, etc.), summary line ("Time entry · Johnson panel"), captured timestamp, status pill or action button. Failed items have inline "Resolve" or "Retry" buttons.

**Rationale**: Bottom sheet matches phone interaction grammar; doesn't require navigating away from current task. Four-section grouping prioritizes attention: action-needed first, in-flight second, queued third, completed last. The "recently synced" section answers the "did my data go through?" question without requiring a separate history surface.

### 5. Four Conflict Severity Classes

**Decision**: When sync detects a conflict, the platform classifies it into one of four severity tiers — mirroring the four-class pattern from Flow 3 (dispatch conflicts) and the differentiated treatment from Flow 6 (calendar conflicts):

| Class | Treatment | Trigger examples |
| :--- | :--- | :--- |
| **Auto-resolve silent** | Sync proceeds; no notification | Time entry recorded against a still-valid assignment; expense category exists server-side; photo uploads to expected job |
| **Auto-resolve with notice** | Sync proceeds; toast or queue-surface note | Expense category was renamed server-side (mapped automatically); minor field defaults updated since capture |
| **Tech-resolvable** | Sync paused for this item; appears in "Action needed"; tech picks resolution on phone | Job was reassigned to another tech mid-shift; quote line item the tech captured against was modified; expense exceeds tenant per-item limit |
| **Owner escalation** | Sync paused; flagged to owner via notification; tech sees "sent to owner" status | Job was deleted while tech worked it; severe data integrity issue; auth/permission boundary changes |

**Rationale**: Treating all conflicts uniformly forces the tech into decisions they don't need to make (silent auto-resolves) or escalates issues the owner shouldn't be bothered with. Four classes match the operational reality: most conflicts are non-issues, some need the tech's judgment, a few need the owner. Pattern-consistent with Flow 3 and Flow 6 — third reuse of the four-class severity model, officially a platform pattern.

### 6. Photo Upload as Separate Queue with WiFi Preference

**Decision**: Photo uploads run on a separate queue from data sync, with a tenant-configurable WiFi preference setting (`photo_upload_wifi_only`, default TRUE).

- Data sync runs on any connection (WiFi or cellular)
- Photo uploads default to WiFi-only; photos wait for WiFi when `photo_upload_wifi_only = TRUE`
- Tenant or user can override: "Upload photos on cellular when offline > 24 hours"
- Resumable upload: chunked (per-file checkpoint) so a partial upload that drops connection mid-transfer resumes from the last completed chunk
- Photo queue surface: same drawer as data sync, with photos in the "Pending" or "Syncing" section labeled "WiFi pending" or showing per-photo progress

**Rationale**: Photos are 100x heavier than data payloads. Default WiFi prevents accidental cellular data charges and reduces sync failure rates. The 24-hour cellular fallback prevents indefinitely-stuck photos for techs whose WiFi is unreliable. Resumable uploads handle the very common "tech walked out of WiFi range mid-upload" case.

### 7. Voice: Capture Offline, Process Online

**Decision**: Voice commands captured offline save the audio file locally and queue for transcription on reconnection. The tech experience:

- During capture: normal voice UI per Flow 1 (listening state, waveform, etc.)
- After capture (offline): confirmation toast — "Voice captured — will process when online"
- After reconnection: normal voice intent flow runs against the audio (Whisper transcribes, Llama parses); if disambiguation is needed, surfaces as a notification rather than blocking
- If the resulting intent is destructive, confirm-as-turn applies — the deferred result behaves like a fresh intent and asks for confirmation before committing (per Flow 1 and Flow 6 patterns)

**Rationale**: Voice is too central to the mobile experience to be unavailable offline. Capturing audio for deferred processing preserves the optimistic-UI principle without compromising the always-online voice processing model. The tech's mental model: "I said the thing; the system has it; it'll happen when it can."

### 8. Sync Triggers

**Decision**: Sync runs on these triggers:
- App foreground transition (every time the app comes to foreground)
- Network state change to online (OS-reported reachability change)
- Periodic check every 30 seconds while the app is active and online
- Manual trigger from the queue surface ("Sync now" button)

**Not in MVP**: background sync (when the app is closed and the device receives connectivity). Reasons: battery cost; iOS background-task constraints; complexity of multi-process sync state.

**Rationale**: Foreground-and-online-change covers the common cases. Periodic check handles flaky network. Manual trigger is for "I want this to sync NOW." Background sync is a real Phase 2 feature but does not gate MVP value — most techs return to the app frequently enough that foreground sync covers their reality.

### 9. Force-Quit Recovery

**Decision**: On app launch (cold start or warm), the sync queue persists in local storage and resumes from the last known state. Items that were in "syncing" state on previous launch are retried using their client-generated idempotency UUIDs (preventing duplicates).

**Rationale**: Tech force-quits the app, drops the device, runs out of battery — all common. The sync queue is durable across these events. Idempotency keys are essential here: a time entry that was sent to the server but whose response was lost during force-quit should not produce a duplicate on retry. This requirement drives backend addition A39.

### 10. Auth Expiry While Offline

**Decision**: When the access token expires while the tech is offline:
- Captured offline data persists locally (no data loss)
- On reconnection, sync attempts the refresh token first
- If refresh succeeds, sync resumes silently
- If refresh fails (refresh token also expired or revoked), the app surfaces a re-auth prompt; captured data remains preserved through re-auth
- After successful re-auth, sync resumes from the queue

**Backend constraint**: The 24-hour idempotency window from §7.6 plus the refresh token TTL (Cognito default 30 days) define the maximum offline period before captured data is at risk. Architecture review confirms 30-day refresh tokens are adequate for the 72-hour hard limit (Decision 13).

**Edge case** — tenant disabled the user mid-offline: re-auth fails permanently. Captured data remains preserved locally; UI shows "Account disabled — contact your owner. Captured data is saved locally" with an export-or-discard affordance.

**Rationale**: The worst case for offline-capture is data loss. The architecture's idempotency + token refresh design prevents this for normal field durations. The re-auth-with-data-preserved flow handles the extreme cases.

### 11. Tech-Resolvable Conflict UI: Vertical Stacked Layout

**Decision**: When a tech-resolvable conflict appears in the "Action needed" section, tapping "Resolve" opens a focused screen with the conflict explained and the two versions stacked vertically (not side-by-side — phone screens cannot accommodate Flow 6's web layout).

Layout:
- **Conflict explainer** at top — plain-language description ("Your time entry doesn't match — the job was reassigned to Luis after you started")
- **Two stacked cards**:
  - Top: "Your version" — what the tech captured
  - Bottom: "Server version" — current server state
  - Both use Flow 6's field-level diff vocabulary (amber=modified, green=added, red=removed) — fourth reuse of the track-changes pattern
- **Bottom action bar**: stacked vertical buttons — primary "Use my version," secondary "Use server version"
- **Tertiary**: "Send to owner for review" link below the action buttons (escalation path per Decision 12)

**Rationale**: Phone screens cannot accommodate side-by-side. Vertical stack preserves the two-version comparison while fitting the device. Escalation-to-owner stays available because some tech-classifiable conflicts genuinely need owner judgment that the tech recognizes only when looking at the actual diff.

### 12. Owner Escalation Path

**Decision**: When a conflict cannot be tech-resolved (severity = `owner_escalation`) or the tech chooses to escalate (per Decision 11), the conflict is sent to the owner:

- Tech sees: "Sent to owner for review" status on the queue item; that item's local data is preserved but its sync is paused pending owner action
- Owner receives: push notification + entry in `notification_outbox` per existing Pass 2 A4 infrastructure
- Owner resolves on web: a new web surface (mobile-tech-conflict resolution) shows the conflict with full context — the tech's captured data, the server state, the conflict cause. Owner picks a side or makes a manual edit.
- After owner resolution: tech's queue item updates to "resolved by owner" or similar; tech's local data may be modified to match (if owner picked server version with edits) or remain (if owner picked tech version)

**Web UI for owner resolution**: deferred to Pass 4. Rationale: it's a low-frequency screen, the design language is largely inheritable from Flow 6, and Pass 3 should not block on every adjacent screen.

**Rationale**: Some conflicts are above a tech's pay grade — job deletion mid-shift, permission changes, policy exceptions. Routing those to the owner preserves data integrity while keeping the tech moving. The Pass 4 deferral is appropriate because the surface is rare and the design language already exists.

### 13. Time-Bounded Offline Operation

**Decision**: Two thresholds for offline operation:
- **Soft limit at 24 hours**: when the device has been offline > 24 hours, the connection state indicator changes to "Long offline · 12 items" with a slightly more prominent treatment. Tech sees a one-time toast on app open: "You've been offline 24+ hours. Sync as soon as you can."
- **Hard limit at 72 hours**: after 72 hours offline, the app blocks new offline operations (clock-in/out, time entry, expense, photo) until a sync occurs. Tech sees a full-screen warning with offline state details and a manual "try sync now" button.

**Tenant setting**: `offline_hard_limit_hours` (default 72, nullable for tenants who explicitly want unlimited offline) — but no soft-limit override (24 hours is a UX threshold, not a policy threshold).

**Rationale**: Indefinite offline operation is a data-integrity hazard — devices get lost, stolen, or wiped; refresh tokens expire; backend schemas evolve. Soft limit is awareness; hard limit is risk reduction. Tenants who genuinely operate in extreme offline conditions (rural utility work, mining sites, remote plumbing/HVAC service) can disable the hard limit; the default protects most tenants.

### 14. Customer Comms Stay Online-Only

**Decision**: Customer-facing communications (per Flow 4) cannot be sent offline. Voice intent capture works offline (per Decision 7), but the actual SMS/email send is blocked until online.

When offline, attempting to send a customer comm:
- Voice: "Tell Tom I'm 20 out" → captured offline → on reconnect, normal Flow 4 always-preview flow runs (with live ETA from current network position, which may differ from offline position)
- Touch: tapping a template card while offline shows a notice: "Customer comms send when online — tap to compose, send when network returns" — composes and queues, but flag as "preview pending"
- Always-preview rule still applies: tech sees the rendered message before send, on reconnection

**Rationale**: Per Flow 4, customer comms are one-way doors (a wrong message cannot be unsent). The always-preview rule is the safeguard. Sending offline would break the live-ETA computation and could send misleading information. Capturing offline and previewing on reconnect preserves both the field-friendly capture flow and the customer-facing accuracy.

## UX Patterns Established (Inherited by Future Flows / Phase 2)

Flow 7's design becomes the template for:

| Pattern | Reuse |
| :--- | :--- |
| Optimistic UI with pending badge | Any future write surface that needs offline tolerance |
| Sync queue as bottom sheet, grouped by status | Any future async operation visualization |
| Four conflict severity classes with proportional UI | Reinforces the Flow 3 + Flow 6 pattern; now officially platform-wide |
| Resumable chunked uploads for heavy media | Phase 2 file uploads, document attachments |
| Voice capture offline with deferred processing | Phase 2 voice surfaces in offline-capable contexts |
| Idempotency UUIDs for client-originated operations | All future write paths from offline-capable clients |
| Force-quit recovery with persistent local queue | Any local-state-bearing mobile feature |
| Two-tier time limit (soft warning + hard block) | Any future feature with implicit time-decay risk |
| Vertical-stacked diff for mobile conflict resolution | Any future mobile surface needing two-version comparison |

## Cross-Domain Considerations

### A. Idempotency UUIDs are required throughout

Per `mvp-arch.md` §7.6, the platform supports `Idempotency-Key` headers with 24-hour deduplication. Flow 7 requires that all offline-capable mobile operations generate client-side UUIDs at capture time and pass them as idempotency keys. The 24-hour window must be confirmed adequate for typical offline operation; longer windows may be needed for the 72-hour offline scenario. **Captured as A39 below.**

### B. Resumable uploads need infrastructure work

The architecture currently has straightforward POST endpoints for photo upload. Resumable chunked uploads (Decision 6) need a multi-part upload protocol — either S3 multipart upload directly from client (with signed URLs) or an Pilot-mediated chunked endpoint. **Captured as A41 below.**

### C. Voice capture offline triggers a new audio storage path

Currently voice audio flows directly from mobile to the GPU instance for Whisper. Offline capture means audio is stored locally, then uploaded as a unit when online. This requires: local audio storage on device with size limits, upload-then-process pipeline (separate from real-time voice), and an extension to `voice_command_log` to track captured-vs-processed timestamps. **Captured as A42.**

### D. Owner escalation surface is Pass 4 work

The owner-side conflict resolution UI (Decision 12) is intentionally deferred. Risk: if Pass 3 ends without it, the dev team has no UI to build for owner-side resolution at MVP. Mitigation: Flow 6's vocabulary covers most of it; the owner-resolution surface for Flow 7's escalations is essentially Flow 6's pattern applied to a different conflict source. Pass 4 should prioritize this early.

### E. The hard-limit blocking behavior may surprise tenants

Decision 13's 72-hour hard limit could leave a tech unable to capture new operations when their device has been offline that long (rural multi-day work). The tenant setting allows opt-out, but the default is conservative. Tenants doing legitimate extended-offline work need to be made aware of this setting during onboarding. Flagged as a Pass 4 onboarding concern.

### F. Local storage cleanup

After successful sync, can the local copy be deleted? For data: yes, after sync is confirmed. For photos: optionally — keeping local copies enables fast viewing but consumes storage. Recommendation: keep local photos for 7 days post-sync, then delete (refetch from server if needed). Tenant setting `photo_local_retention_days` for adjustment. Captured as a sub-scope item under A41.

### G. LOTO offline confirmation has a legal angle worth flagging

Decision 1 includes LOTO confirmation in the offline-capable set. Legally, the confirmation is valid (the tech genuinely confirmed it on their device with an authenticated session). But for liability documentation, the timestamp gap between device-capture and server-receipt may matter. The audit log captures both `client_capture_at` and `server_received_at` per A37 to make this distinction visible. **Worth a legal/policy review item for the dev team** before MVP launch.

## Deferred Items (For Future Iteration)

- **Background sync** (when app is closed) — Phase 2; battery and iOS constraints
- **Bulk retry of all failed items** — Phase 2; single-item retry in MVP
- **Multi-device offline coordination** (tech with both phone and tablet offline) — Phase 2
- **Sync analytics dashboard** for owners (which techs sync most/least, conflict rates) — Phase 2
- **Custom retry policies per operation type** — Phase 2
- **Predictive caching** (pre-cache job details before tech arrives at known low-signal site) — Phase 2
- **Owner-side mobile conflict resolution** — Phase 2; web is enough for MVP
- **End-to-end encryption of offline-stored data** — Phase 2; rely on OS-level device encryption for MVP
- **Cross-tech offline coordination** (two techs offline on the same job, both capturing time) — Phase 2
- **Sync queue export** for tech to email themselves a record before re-auth — Phase 2

## Validation Checklist

Before implementation begins:

- [ ] Dev team aligned on the offline-capable operation set (Decision 1) — no surprises later
- [ ] Idempotency UUID generation pattern defined for client SDK (A39)
- [ ] Resumable upload protocol picked: S3 multipart vs Pilot-mediated (A41)
- [ ] Voice offline capture pipeline designed end-to-end (A42)
- [ ] Conflict severity classification engine specced (A40) — per-operation classification matrix written out
- [ ] Push notification flow for owner escalations confirmed against existing notification_outbox (A4)
- [ ] Refresh token TTL confirmed adequate for 72-hour offline scenario (A44) — Cognito 30-day default verified
- [ ] Local storage size limits defined for queue, audio, photos
- [ ] Force-quit recovery tested across iOS and Android lifecycle scenarios (A43)
- [ ] Sync trigger frequency tested for battery impact (Decision 8)
- [ ] Customer comms blocked-send-with-preview flow tested for the offline-to-online transition (Decision 14)
- [ ] LOTO offline confirmation reviewed with legal/policy advisor before MVP launch (cross-domain G)

## Backend Additions (New for Flow 7)

The following additions extend the running ledger and fold into `backend-mvp-additions-v4.md`. Flow 7 is the most backend-intensive Pass 3 flow because offline-capable mobile is essentially new infrastructure.

### A37. Offline-Capable Operations API Contract

**Triggered by**: Decision 1 — explicit set of operations must be supported by both client SDK and backend with consistent contracts.

**Scope**:
- Document each offline-capable operation as accepting client-generated idempotency UUIDs
- Each endpoint validates idempotency on receipt
- Schema additions: `client_capture_at TIMESTAMPTZ NULL` on tables for offline-capturable operations (job_time_entry, expense, photo, change_order, etc.) — distinct from `created_at` which is server-side
- Audit log captures both timestamps for offline-captured operations; the gap (`server_received_at - client_capture_at`) becomes a queryable metric

**Effort estimate**: Small-Medium — 2–3 days (mostly schema additions and contract documentation; idempotency already exists per §7.6).

### A38. Sync Queue State Model

**Triggered by**: Decision 4 — sync queue surface needs a server-side counterpart for cross-device visibility (tenant owner reviewing tech's sync state, support troubleshooting).

**Scope**:
- New table: `mobile_sync_event` — append-only log of sync attempts per device per operation
  - Fields: `tenant_id`, `user_id`, `device_id`, `operation_type`, `operation_payload_summary`, `status` (`pending | syncing | succeeded | failed | conflict`), `conflict_severity`, `client_capture_at`, `synced_at`, `error_detail`, `idempotency_uuid`
- API: `GET /api/v1/mobile-sync/state/{user_id}` — admin view (owner/support) of a tech's sync state
- Retention: 30 days hot, then archived consistent with audit log policy

**Effort estimate**: Medium — 3–4 days.

### A39. Idempotency UUIDs for Offline Operations

**Triggered by**: Decisions 1, 9 — every offline-capable operation needs a client-generated UUID for safe retry.

**Scope**:
- Extend `Idempotency-Key` header support per §7.6 to accept client-generated UUIDs (already supported; document the contract)
- 24-hour deduplication window confirmed (per existing infrastructure)
- Client SDK: generate UUID at capture time, persist with operation in local queue, send with sync attempt
- Server: existing idempotency-key infrastructure handles deduplication on retry; expand coverage to all offline-capable endpoints from A37
- Validate that 24-hour window is adequate for the 72-hour offline scenario (Decision 13). If a tech captures at hour 0, force-quits at hour 23, comes back online at hour 50, the idempotency window has expired but the sync still hasn't completed. Mitigation: client persists the idempotency UUID indefinitely; server uses both the idempotency window AND a longer-window check on natural keys (e.g., `(user_id, job_id, clock_in_at)` for time entries) to deduplicate. This is captured as a server-side enhancement.

**Effort estimate**: Small-Medium — 3–4 days (client SDK + server-side natural-key dedup enhancement).

### A40. Conflict Severity Classification Engine

**Triggered by**: Decision 5 — four severity classes need a server-side classifier that runs during sync.

**Scope**:
- New module: `services/mobile_sync_conflict.py`
- Per operation type, define classification rules: which conditions are auto-silent, auto-with-notice, tech-resolvable, owner-escalation
- API: classification runs during sync attempt; returns `SyncResolution` object with `severity`, `auto_resolved` flag, `tech_action_required` flag, `owner_escalation_required` flag, `payload` (the resolution data)
- For each operation type, document the classification matrix:
  - **Time entry sync conflicts**: job reassignment, time overlap, expense exceeded, etc.
  - **Expense sync conflicts**: category renamed, exceeds limit, supplier deleted, etc.
  - **Photo sync conflicts**: storage limit, job deleted, etc.
  - **Status change conflicts**: job already completed by another tech, etc.
- Classification matrix is data-driven (a configuration table, not hardcoded) so it can be tuned without code changes

**Effort estimate**: Medium-Large — 5–7 days (per-operation classification logic, comprehensive test coverage, configuration table, all four severity classes for each operation type).

### A41. Resumable Photo Upload Pipeline

**Triggered by**: Decision 6 — resumable chunked uploads to handle network interruption.

**Scope**:
- Pick implementation: S3 multipart upload directly from client (signed URLs) vs Pilot-mediated chunked endpoint
- **Recommendation**: S3 multipart with signed URLs — offloads heavy lifting to S3, avoids Pilot as a chunk-relay middleman, scales better
- API: `POST /api/v1/photos/initiate-upload` returns multipart upload session with chunk URLs
- API: `POST /api/v1/photos/complete-upload` finalizes after all chunks succeed
- Client SDK: track per-chunk completion in local state; resume from last-completed chunk on retry
- WiFi/cellular preference: client-side scheduling; server doesn't enforce
- Server-side cleanup: incomplete uploads expire after 24 hours
- Local cleanup (cross-domain F): tenant setting `photo_local_retention_days` (default 7) — local photos kept this long after server confirmation, then auto-purged

**Effort estimate**: Medium — 4–5 days.

### A42. Voice Command Offline Capture & Deferred Processing

**Triggered by**: Decision 7 — voice audio captured offline, transcribed when online.

**Scope**:
- Extend `voice_command_log`:
  - `captured_at TIMESTAMPTZ NOT NULL` — when audio was captured (client-side)
  - `uploaded_at TIMESTAMPTZ NULL` — when audio reached server
  - `transcribed_at TIMESTAMPTZ NULL` — when Whisper completed
  - `parsed_at TIMESTAMPTZ NULL` — when Llama completed
  - `processing_status TEXT` — `pending_upload | uploading | transcribing | parsing | completed | failed`
- API: `POST /api/v1/voice/upload-audio` accepts audio file + capture timestamp; queues for processing
- Celery task: `process_voice_audio_async` — runs Whisper + Llama against uploaded audio, emits intent for routing
- Client SDK: store audio locally when offline; upload via this endpoint when online; UI shows "queued" state per Decision 7
- Confirmation flow: if intent requires confirmation per Flow 1's confirm-as-turn pattern, notification fires when intent processing completes; tech responds in normal voice or touch flow

**Effort estimate**: Medium — 4–5 days (schema, async pipeline, client SDK, integration with existing voice intent flow).

### A43. Force-Quit Recovery State Persistence

**Triggered by**: Decision 9 — sync queue must survive force-quit and resume.

**Scope**:
- Client-side: local queue persists in device storage (Core Data on iOS, Room on Android, or shared persistence layer in Expo)
- Each queue item carries: client UUID, operation type, payload, status, retry count, last error
- On app launch: load queue from storage, mark "syncing" items as "pending" (idempotency keys handle the duplicate-protection on retry per A39)
- Mostly client-side work; server-side just needs to honor idempotency on retry

**Effort estimate**: Medium — 4–5 days client SDK; minimal backend.

### A44. Auth Expiry Offline Handling

**Triggered by**: Decision 10 — graceful re-auth after token expiry preserves captured data.

**Scope**:
- Verify Cognito refresh token TTL is at least 7 days (Cognito default 30 days — adequate for 72-hour hard limit)
- Client SDK: on sync attempt with expired access token, attempt refresh; if refresh fails, surface re-auth prompt while preserving local queue
- After re-auth: resume sync; queue remains intact
- Edge case (per Decision 10): tenant disabled the user mid-offline. Re-auth fails permanently. UI: "Account disabled — contact your owner. Captured data is saved locally" with an export-or-discard affordance
- Export format for the disabled-account edge case: simple JSON dump of unsynced queue items, emailable to a separate address

**Effort estimate**: Small-Medium — 2–3 days.

### A45. Tech-Resolvable Conflict UI Endpoints

**Triggered by**: Decision 11 — tech resolves conflicts on phone with proper API support.

**Scope**:
- API: `GET /api/v1/mobile-sync/conflicts/{conflict_id}` — returns the conflict detail (tech version, server version, severity, classification reason, field-level diff)
- API: `POST /api/v1/mobile-sync/conflicts/{conflict_id}/resolve` — accepts `resolution: 'use_local' | 'use_server' | 'escalate_to_owner'`
- Pre-resolution staleness check (per A33 pattern from Flow 6): if server state changed between conflict surface and resolution, return 409 with refreshed state
- Audit: every resolution logged to `mobile_sync_event`

**Effort estimate**: Small-Medium — 2–3 days (largely follows A33 pattern).

### A46. Owner Escalation Routing & Notification

**Triggered by**: Decision 12 — owner-escalated conflicts surface in owner's queue with notification.

**Scope**:
- New table: `mobile_sync_owner_escalation`
  - Fields: `tenant_id`, `originating_user_id`, `conflict_id` (→ `mobile_sync_event`), `escalated_at`, `status` (`pending | resolved | rejected`), `resolved_by_user_id`, `resolved_at`, `resolution_action`
- API: `GET /api/v1/owner/mobile-sync-escalations` — list pending escalations for owner
- API: `POST /api/v1/owner/mobile-sync-escalations/{id}/resolve` — owner resolves
- Notification: push + `notification_outbox` entry on escalation creation (per existing infrastructure)
- Web UI for resolution: deferred to Pass 4 (per cross-domain consideration D)

**Effort estimate**: Medium — 3–4 days backend; UI deferred.

---

## Pass 3 Wrap

Flow 7 closes Pass 3. The collected output across the seven flows is:
- 7 locked flow specs (Flows 1–7), with Flow 1 going to v2 after iteration
- 3 architectural pre-work documents (Pass 1 foundation, Pass 2 IA, quote line item architecture)
- A consolidated backend additions ledger v4 covering A1–A46
- 16 mockups and prototypes across the flows

**Recommended next steps** (parallel tracks per the framework doc):

**1. PRD revision decision.** Pass 3 surfaced enough new capabilities — ETC capture, chart thresholds, configurable buckets, four conflict severity classes, three quote styles, voice-active conflict resolution, offline-capable operation set, owner escalation flow — that the framework doc already flagged this question. Recommendation: issue a PRD v2 covering the Pass 3 additions, even at the cost of a few weeks. The dev team builds against the PRD; leaving capabilities only in design specs and the backend ledger fragments the source of truth.

**2. Pass 4 scope confirmation.** Pass 4 is "polish, states, onboarding" per the framework doc, but the deferred-items lists across Pass 3 flows have accumulated significant work. Worth a session at the Pass 3-to-4 boundary to triage the deferred backlog into Pass 4 (must-have), Phase 2 (post-MVP), and Cut entirely. Highest-priority Pass 4 items appearing across multiple flows:
- Owner-side mobile-conflict resolution UI (Flow 7 cross-domain D)
- Settings UIs for configurable thresholds (margin buckets, ETC variance, chart thresholds, conflict auto-expiry, photo retention, offline hard limit)
- Empty/error/loading states for every flow
- Onboarding flows that surface tenant-configurable settings users need to know about

**3. Backend implementation begins.** Per the framework doc's dependency chain, backend MVP work (~104–149 days at the v4 estimate) starts after Pass 4 wraps. Some teams parallelize earlier — backend work on the more-stable Pass 1/2/3 foundations can start now if the team has bandwidth.

**4. Naming track resolution.** Naming has resolved to **Pilot for Trades** (customer-facing) with **Pilot** as the casual short form. The internal codename `pilot` (lowercase) is used uniformly across infrastructure, code, and data identifiers. URL: `pilotfortrades.com`. No further naming work is required before beta testing.
