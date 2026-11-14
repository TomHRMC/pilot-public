# Pilot for Trades Design System — Pass 4, Tier 1 #3: Background Sync for Mobile

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Background sync for the mobile sync queue when the app is not in the foreground. Pulled forward from Phase 2. Closes Pass 4 Tier 1.
**Resolves**: Pass 3 Flow 7 §8 ("Not in MVP" note now removed)
**Depends On**: Pass 3 Flow 7 (offline-to-online sync) · Pass 2 Information Architecture · `mvp-arch.md` §15 (Mobile Offline Operations)
**Backend additions**: A51 (push token registry + silent push handling + sync session management)
**Deliverable shape**: Shape F (Background system design with thin UI). Per framework doc, this surface is mostly architectural with a small UI footprint.

---

## Purpose

Pass 3 Flow 7 §8 explicitly excluded background sync from MVP, citing battery cost, iOS background-task constraints, and multi-process state complexity. The Pass 4 framework doc reversed that decision — pre-launch user research will quickly surface that techs killing the app between jobs is normal, and queues sitting unsynced for hours violates Flow 7's strategic principle of sync visibility being non-negotiable. Adding background sync post-launch means a major mobile architecture change after real customers are using the system. Doing it now while the surrounding sync infrastructure is still being built keeps the implementation cost minimal.

This spec defines what background sync does, what it does *not* do, what platform constraints shape it, and the small UI surface needed to make it visible to the tech and configurable by the tenant. The bulk of the work is system-design and platform-specific scaffolding; the user-facing surface is two new UI elements (a settings toggle and a "last background attempt" indicator) plus targeted updates to existing Flow 7 surfaces.

## Strategic direction

### Background sync is a queue uploader, not a data refresher

The strategic frame from the framework doc holds: this surface is *only* the queue uploader. It is not periodic data refresh (pulling jobs/customers/quotes/etc. while backgrounded), not background voice processing, not background photo uploads. Those exclusions inherit from Flow 7 §6 and §7 and remain in effect. Photos and voice stay foreground-only for the same reasons — they're heavy operations with battery and data costs that don't justify background execution.

What background sync *does* do: when the OS gives the app a brief execution window in the background (silent push received, periodic background fetch, network state change), the app drains the data sync queue. The four-class severity model from Flow 7 §5 still applies — auto-resolves silent in background, auto-with-notice surfaces a notification, tech-resolvable items wait for foreground, owner-escalations route to web per Tier 1 #1.

### Battery and data discipline are platform-level commitments

The reason Flow 7 originally excluded background sync wasn't capability — both iOS and Android support it — but operational caution. A poorly-tuned background sync drains battery, eats cellular data, and gets the app deprioritized by both OSes. The defaults this spec establishes are conservative; tenants can opt to be more aggressive (more frequent attempts) but must do so explicitly via settings. The platform's reputation for battery efficiency is a long-tail asset.

### Visibility is non-negotiable; the tech always sees background sync activity

The tech should never be surprised by what the app did while they weren't looking. Every background sync attempt — whether successful, partial, or failed — is recorded and visible when the tech reopens the app. The "last background attempt" indicator exists for this purpose. Silent failure is the failure mode this surface most carefully guards against.

### iOS and Android have asymmetric capabilities; the design accommodates both

iOS imposes stricter limits on background execution than Android. The design works within iOS constraints first, then takes advantage of Android's looser scheduling where it doesn't compromise pattern consistency. The tech experience is uniform across platforms; the underlying implementation diverges.

## Platform constraints (the part that actually drives the design)

### iOS background execution model

iOS allows three relevant background execution paths for an app like Pilot:

| Mechanism | Trigger | Time budget | Frequency |
| :--- | :--- | :--- | :--- |
| **Background fetch (BGAppRefreshTask)** | OS-scheduled, opportunistic | ~30 seconds | OS decides; typical 1–2x per hour for actively-used apps, less for idle ones |
| **Silent push (content-available)** | Server-initiated APNs notification | ~30 seconds | Server-controlled, but iOS may throttle |
| **Background processing (BGProcessingTask)** | OS-scheduled, when device is plugged in and idle | Several minutes | Rare; typically overnight |

Pilot uses **silent push as the primary trigger** with **background fetch as the fallback**. Background processing is not used in MVP — it would only run when the device is charging overnight, which is too narrow a window to be operationally useful.

Critical iOS constraints:
- iOS reduces background fetch frequency for apps the user opens infrequently. A tech who only opens Pilot once a day at end-of-shift will get minimal background fetch budget. Silent push is the only reliable trigger for these users.
- The OS may throttle silent push if the app processes them slowly or if the device is in low-power mode. Each silent push must complete within ~30 seconds.
- iOS does not guarantee any specific background execution. The implementation must treat all background runs as opportunistic; foreground sync remains the source of truth.

### Android background execution model

Android's primary mechanism is **WorkManager** with constraints:

| Constraint | Effect |
| :--- | :--- |
| Network availability | WorkManager defers work until network is available |
| Battery not low | Defers when battery is critically low |
| Charging (optional) | Can require device charging |
| Doze mode | Doze defers all background work; exempts only high-priority FCM messages |

Pilot uses:
- **WorkManager periodic worker** (15-minute minimum interval, OS-coalesced with other work) for opportunistic sync
- **High-priority FCM messages** as the equivalent of iOS silent push for urgent triggers (Doze-exempt)

Doze mode is the Android equivalent of iOS's aggressive background throttling. A tech's phone left on a counter for an hour enters Doze; queued work waits. High-priority FCM bypasses Doze but should be rate-limited per A35 to avoid OS-level deprioritization.

### Cross-platform symmetry

The tech experience must be uniform across platforms. From the tech's perspective:
- "Background sync runs while the app is closed" is the user-facing model
- "Sometimes the OS makes it wait" is acknowledged in the UI ("Last background attempt: 4 hr ago" rather than "every 30 seconds guaranteed")
- The settings toggle behaves identically on both platforms

The implementation diverges; the design does not.

## Locked design decisions

### 1. Background sync triggers — two primary, one fallback

**Decision**: Background sync attempts on these triggers (extending Flow 7 §8):

| Trigger | iOS implementation | Android implementation | Frequency cap |
| :--- | :--- | :--- | :--- |
| **Server-initiated push** | Silent push (content-available APNs) | High-priority FCM | At most 1 per `background_sync_push_interval_minutes` per device (default 5; tenant-configurable per Decision 4) |
| **OS-scheduled opportunistic** | Background fetch (BGAppRefreshTask) | WorkManager periodic worker | OS-decided; min 15 min interval |
| **Network state change** | Limited iOS support; relies on push or foreground | Connectivity broadcast (deprecated; use WorkManager constraint) | OS-decided |

Server-initiated push is the primary trigger because it's the only one the backend can control. The backend issues a silent push when:
- A queue item has been pending sync >15 minutes (suggests app was closed before sync completed)
- A retryable failure on a previous attempt warrants retry
- Owner escalation resolution routes back to the originating tech (loop closure per Tier 1 #1 Decision 8)

OS-scheduled opportunistic is the fallback for cases where push delivery is delayed or throttled.

**Frequency cap rationale**: The default 5-minute interval caps battery cost at the worst case (a tech with a stuck queue triggering retries). The cap is enforced server-side via the tenant-effective `background_sync_push_interval_minutes` setting (system default + tenant override per arch doc §16.5); the device implementation trusts what arrives. Tenants with operational reasons to deviate (faster recovery for stuck queues; slower for stricter battery policy) configure per Decision 4.

**Existing Flow 7 §8 triggers preserved unchanged**:
- App foreground transition
- Network state change to online (when app is foreground)
- Periodic 30-second check while foreground active
- Manual "Sync now" button

### 2. Background sync execution scope — data sync only

**Decision**: Background runs execute the **data sync queue only**. Specifically:

| Operation type | Background sync | Rationale |
| :--- | :--- | :--- |
| Time entry, expense, status change, LOTO, change order | ✅ Yes | Lightweight payloads; high tech impact when stuck |
| Photo upload | ❌ No | Heavy; cellular data risk; Flow 7 §6 keeps WiFi-only foreground |
| Voice audio upload + processing | ❌ No | Heavy; Flow 7 §7 keeps online-only via foreground processing |
| Periodic data refresh (pull from server) | ❌ No | Out of scope; Phase 2 separate concern |

The data sync queue from Flow 7 is a single queue containing only the operations in row 1. Photos and voice live in separate queues with their own behavior. Background sync drains the data queue and does not touch the others.

**Rationale**: This matches the Phase 2 forward inheritance — photos and voice retain their foreground constraints because their cost profiles haven't changed. Adding them to background sync would require revisiting Flow 7 §6's WiFi preference and §7's processing pipeline, which is out of scope for this surface.

### 3. Conflict handling in background — auto-resolves only; everything else waits

**Decision**: Background sync only commits items that fall into the four-class severity model's two auto-resolve classes:

| Severity class (from Flow 7 §5) | Background behavior |
| :--- | :--- |
| Auto-resolve silent | Commit; no notification |
| Auto-resolve with notice | Commit; queue a foreground notification (delivered when app opens or via standard notification per A35) |
| Tech-resolvable | Pause; wait for foreground; surfaced in "Action needed" on next app open |
| Owner escalation | Route to web per Tier 1 #1; tech sees "sent to owner" status on next app open |

Background sync does not surface tech-resolvable conflicts via push notification. The argument: a tech-resolvable conflict requires the tech to see the diff, which requires the app to be open. Surfacing it via push and asking the tech to open the app to resolve adds zero value over surfacing it on next app open.

**Rationale**: The two auto-resolve classes account for the majority of conflicts in normal operation (per Flow 7 §5). Allowing background to commit them keeps the queue draining. Pausing the others until foreground preserves the tech's chance to see context before deciding.

### 4. Battery, data, and frequency behavior — four configurable thresholds

**Decision**: Four tenant settings govern background sync's resource consumption and trigger frequency:

| Setting | Default | Range | Effect |
| :--- | :--- | :--- | :--- |
| `background_sync_enabled` | TRUE | boolean | Master toggle; FALSE disables all background sync |
| `background_sync_wifi_only` | FALSE | boolean | TRUE restricts background sync to WiFi-only connections |
| `background_sync_battery_floor_pct` | 20 | 5–50 | Below this battery percentage, background sync is skipped |
| `background_sync_push_interval_minutes` | 5 | 1–60 | Minimum interval between server-initiated silent push triggers per device. System-default-with-tenant-override per arch doc §16.5 (system default `system_background_sync_push_interval_minutes` defaults to 5; tenants override per their operational needs). |

Per-user override of `background_sync_enabled` is allowed (a tech who wants to disable background sync on their device for battery reasons). Tenant-level setting is the default; user override stored in user preferences.

The other three settings are tenant-level only — owners decide on data, battery, and frequency policy across the team. Per-user override would create dispatcher-side unpredictability about what's actually syncing.

**Rationale**: The default `background_sync_wifi_only = FALSE` allows cellular sync because data payloads are small (KB-scale, not MB-scale like photos). Setting it TRUE for tenants with strict cellular policies (utility crews, government contractors) is supported. The 20% battery floor is a standard threshold — below it, the OS itself starts deferring background work, so this setting mostly aligns with platform behavior. The 5-minute push interval default is conservative enough to protect battery and avoid OS-level deprioritization for most tenants; tenants with stuck-queue retry sensitivity (high-frequency capture environments) can lower it; tenants with strict battery policies can raise it. The 1-minute floor exists to prevent self-DoS via misconfiguration; the 60-minute ceiling exists because below-once-per-hour effectively negates background sync's value.

**Settings UI deferral**: actual settings UI lands in Tier 2 #4 alongside the other tenant settings work. This spec only declares the policy and data shape.

### 5. UI element 1 — Status indicator on the sync queue surface

**Decision**: The existing Flow 7 §4 sync queue bottom-sheet drawer adds one new informational row at the top, just below the drawer header:

> **Last background sync: 12 min ago** (3 items synced) · *Background sync on*

States rendered:

| State | Display |
| :--- | :--- |
| Recent successful background run | "Last background sync: 12 min ago (3 items synced)" |
| Recent successful run with no work | "Last background sync: 18 min ago" (no count when nothing was queued) |
| Recent failed run | "Last background sync: 7 min ago · Retried 3 times · Will try again" (amber) |
| Background sync disabled (tenant or user) | "Background sync off · Items will sync when you open the app" (neutral; settings deep-link) |
| Never run yet | "Background sync ready" (after first foreground sync confirms permissions and registration) |
| iOS permission not granted (silent push category) | "Background sync needs permission" (amber; deep-link to iOS settings) |

Tapping the row deep-links to `Settings > Sync & Storage > Background sync` (the actual settings location confirmed in Tier 2 #4).

**Rationale**: This row makes background sync activity visible without cluttering the existing four-section queue grouping (Flow 7 §4). It sits *above* the four sections because it answers "what happened while I wasn't looking?" before the tech consults the four sections to decide what to do next. The amber treatment for failure cases matches existing platform vocabulary.

**Why not a separate top-level surface**: a dedicated background-sync screen would be over-engineered for what is a one-liner of state. The sync queue is already the right surface; this row extends it.

### 6. UI element 2 — Settings toggle (deferred visual to Tier 2 #4)

**Decision**: A settings toggle at `Settings > Sync & Storage > Background sync` controls the tenant-level `background_sync_enabled`. A second toggle below it controls per-user override (visible only when tenant has it enabled — per-user override of TRUE doesn't apply when the tenant has globally disabled).

The visual UI lands in Tier 2 #4. This spec defines:
- The settings location (`Settings > Sync & Storage > Background sync`)
- The two toggles (tenant default + user override)
- The four tenant settings from Decision 4 also live in this same settings sub-surface
- A passive informational paragraph below the toggles: "Background sync runs while Pilot is closed to keep your captured data flowing. We use minimal battery and data, but you can disable this if needed."
- A "Last background attempt" status row at the bottom of the settings page (mirrors the queue surface row from Decision 5)

**Rationale**: Settings consolidation. All sync-related settings (background sync, WiFi-only, battery floor, push interval, soft/hard offline limits from Flow 7 §13, photo retention from Flow 7 cross-domain F) live under `Sync & Storage`. Tier 2 #4 specs the full IA; this surface contributes the data shape and copy.

### 7. Push notification permission request — handled separately in Tier 3 #11

**Decision**: This surface assumes push notification permission has been granted. The actual permission request flow (when the OS prompt fires, what context surrounds it, what happens on denial) is Pass 4 Tier 3 #11 work.

When permission is *not* granted:
- Background sync still attempts via OS-scheduled opportunistic triggers (which don't require notification permission on iOS; on Android, FCM messages with `data` payload don't require notification permission either)
- Silent push throttling is more aggressive without notification permission (iOS specifically penalizes silent push for apps without notification permission)
- The queue surface row from Decision 5 shows: "Background sync limited · Enable notifications for best performance" with a deep-link to OS settings

**Rationale**: Decoupling permission UX from sync infrastructure. Tier 3 #11 owns the request flow; this surface owns the degraded-mode behavior when permission is denied. The fallback (opportunistic-only) keeps background sync functional but slower.

### 8. Owner-side visibility — no new surface; mobile owner status row covers it

**Decision**: Owners do not get a dedicated "team background sync health" surface in MVP. The existing mobile owner status rows (Pass 2 §3.9 / Flow 6 §10 / Tier 1 #1 Decision 9) provide adequate visibility for the small-team operational case:

- Owner sees their own device's background sync status via the queue surface row (Decision 5)
- Owner sees field issues (Tier 1 #1) when techs hit owner-escalation conflicts in background or foreground — same path either way
- Tech-level background sync health (which tech's queue is stuck, when, why) is not a Phase 1 concern

**Rationale**: A team-wide background sync dashboard would be premature for 1–5 person shops. Solo Mike sees his own; multi-person shops see escalations when they happen. Phase 2 may add a sync-analytics surface for tenants with 10+ techs.

### 9. Failure modes — explicit handling, all visible to tech

**Decision**: Three categories of background sync failure, each with defined behavior:

| Failure category | Detection | Tech-side surface | Recovery |
| :--- | :--- | :--- | :--- |
| **Transient (network, server 5xx)** | Standard retry detection | Queue row indicates retry status; "Last background sync · Retried 3 times" | Automatic exponential backoff per existing infrastructure; surfaces in queue if persistent |
| **Auth (refresh token expired)** | Refresh token call returns 401 | Queue row indicates auth needed; standard re-auth flow on next foreground per Flow 7 §10 | Foreground re-auth required |
| **OS-throttled (no execution window granted)** | Backend detects no sync attempts for >2 hours despite queued items | Queue row indicates "Background sync delayed by your phone · Last attempted X ago" | OS-determined; no app action |

Persistent failures (>3 consecutive failed background runs) trigger a foreground notification on next app open: "Background sync has been failing — open the queue to see what's happening." This is the only proactive notification background sync generates.

**Rationale**: Silent failure is the failure mode this design most carefully guards against. Every failure has a path to tech awareness; nothing is hidden. The three categories cover the realistic failure modes without over-engineering.

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| Background sync queue uploader (vs. data refresher) | **NEW** | Flow 7 §6, §7 (which kept photos/voice foreground; this preserves that) |
| Platform-asymmetric implementation, uniform UX | **NEW** | — |
| Failure visibility on next app open | **NEW** | Flow 7's "sync visibility is non-negotiable" principle |
| Auto-resolves only in background; defer judgment to foreground | **NEW** | Flow 7 §5 four-class severity model |
| Optimistic UI with pending badges | Reused | Flow 7 §3 |
| Mobile owner status row (no new instance) | Confirmed adequacy | Pass 2 §3.9, Flow 6 §10, Tier 1 #1 |

Three small new patterns, two reuses. These new patterns inform Phase 2 work for periodic data refresh (which would inherit "platform-asymmetric, uniform UX" and "failure visibility on next app open").

## Cross-domain considerations

### A. Push token registry is foundational and reused beyond background sync

Backend addition A51 includes push token registration on app launch. This infrastructure is also reused by:
- Tier 1 #1 Decision 8 (loop closure push to originating tech after owner resolves a field issue)
- Future Phase 2 features (tech-to-tech messaging, dispatcher push, customer notification when tech is en route)

A51's push token registry is the canonical infrastructure; subsequent uses inherit it. The spec for A51 below scopes only what's needed for background sync, but the infrastructure is reusable.

### B. The tenant-configurable push frequency cap is shared with A35

A35 (notification rate limiting from Flow 6) limits how frequently a single tenant generates owner-facing notifications. The `background_sync_push_interval_minutes` cap (Decision 4) is a separate dimension (per-device for sync triggers). They don't conflict; they govern different message types. The `notification_outbox` infrastructure handles both via category-based rate limiting.

### C. Settings location commits Tier 2 #4 IA

This spec commits the settings location to `Settings > Sync & Storage > Background sync`. Tier 2 #4 must accommodate this — the Sync & Storage settings sub-surface needs to host:
- Background sync toggle (tenant + user override)
- WiFi-only toggle
- Battery floor threshold
- Offline soft/hard limits (from Flow 7 §13)
- Photo retention (from Flow 7 cross-domain F)

The Tier 2 IA framework doc (prerequisite to Tier 2 #4) confirms whether `Sync & Storage` is the right grouping name vs. an alternative. If the IA framework doc renames it, this spec inherits the rename.

### D. iOS Background Modes capability and entitlements

The mobile app needs to declare specific Background Modes in its iOS app capabilities:
- `Background fetch` for BGAppRefreshTask
- `Remote notifications` for silent push

These entitlements are part of the Apple App Store submission. This is a one-time setup that doesn't gate Pass 4 design but does gate beta deployment.

### E. Android FCM setup and high-priority message permissions

Similarly on Android:
- FCM project configuration with the appropriate API keys
- Use of high-priority FCM messages requires careful management — Google can deprioritize an app that overuses high-priority messages

These are infrastructure setup tasks owned by Tom; flagged here for awareness.

### F. Connection state pill behavior unchanged

Flow 7 §2's connection state pill remains exactly as designed. Background sync activity does not modify the pill (the pill represents the foreground state of the app). When the app comes to foreground, the pill renders the post-background-sync state — which the tech reads as "I left this with 12 items queued; now there are 9; the 3 that synced did so in background." The queue surface row from Decision 5 explains the "what happened while I was away" question.

### G. Force-quit recovery (Flow 7 §9) unchanged

The persistent local sync queue from Flow 7 §9 is the source of truth for both foreground and background sync. Background sync reads the same queue, executes the same sync logic, and updates the same state. Force-quit recovery on app launch picks up wherever the last execution (foreground or background) left off.

## Deferred items (Phase 2 / for future iteration)

- **Periodic data refresh in background** (pulling jobs/customers/quotes/etc. while backgrounded) — Phase 2; significant scope expansion that would change the queue model
- **Background photo uploads** — Phase 2; would need to revisit Flow 7 §6 WiFi preference and chunked upload battery cost
- **Background voice audio upload** — Phase 2; would need to revisit Flow 7 §7 pipeline
- **Per-user advanced background sync controls** (custom intervals, custom battery floors) — Phase 2; tenant-level + simple user toggle covers MVP
- **Team-wide background sync health dashboard for owners** — Phase 2; mobile owner status rows cover MVP
- **Predictive background sync triggers** (e.g., trigger more aggressively before tech arrives at known site) — Phase 2; opportunistic + push covers MVP
- **Background sync analytics in Reports** — Phase 2; basic per-device "last attempt" suffices for MVP debugging
- **Selective background sync by operation priority** (e.g., sync time entries first, change orders last) — Phase 2; FIFO from existing queue order in MVP

## Validation checklist

Before implementation begins:

- [ ] Dev team aligned on iOS background fetch + silent push as primary triggers
- [ ] Dev team aligned on Android WorkManager periodic + high-priority FCM
- [ ] A51 push token registration endpoint specified (canonical infrastructure for future reuse per Cross-Domain A)
- [ ] A51 silent push handler specified for both iOS APNs and Android FCM
- [ ] A51 sync session management (idempotency, partial-completion recovery) specified
- [ ] Tenant-configurable per-device push frequency cap (default 5 min via `background_sync_push_interval_minutes`) implemented and tested
- [ ] Background sync execution scope confirmed: data queue only; no photos, no voice, no data refresh
- [ ] Auto-resolve-only behavior in background confirmed and tested against four-class severity model
- [ ] Three tenant settings + one user override implemented
- [ ] Queue surface row (Decision 5) all 6 states implemented and tested
- [ ] Persistent failure (>3 consecutive) foreground notification implemented and rate-limited
- [ ] iOS Background Modes capability declared in app entitlements
- [ ] Android FCM project configured with high-priority message support
- [ ] Permission denial degraded-mode behavior tested (Decision 7)
- [ ] Force-quit recovery tested across foreground-to-background and background-to-foreground transitions

## Backend addition (new for Tier 1 #3)

### A51. Background Sync Infrastructure

**Triggered by**: Decisions 1, 2, 4, 9 — push token registry, silent push handlers, sync session management, frequency cap enforcement.

**Scope**:

**Push token registry** (canonical infrastructure):
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
- Server-side aggregation: this telemetry feeds the queue surface row from Decision 5 (the "last background sync · X items synced" status) on next app open

**Frequency cap enforcement**:
- Server-side rate limiting on silent push dispatch (Decision 1, Decision 4: 1 per tenant-effective `background_sync_push_interval_minutes`, default 5)
- New platform setting `system_background_sync_push_interval_minutes` (default 5) and tenant setting `background_sync_push_interval_minutes` (nullable; null inherits system default) per arch doc §16.5 system-default-with-tenant-override pattern
- Server-side detection of OS throttling (Decision 9: backend detects no sync attempts for >2 hours despite queued items, surfaces "Background sync delayed by your phone" to client on next sync)

**Effort estimate**: Medium-Large — 6–8 days. The push token registry and silent push dispatcher are the largest pieces (3–4 days). Sync session management and frequency cap enforcement are smaller (2–3 days). Platform-specific testing across iOS and Android adds 1 day.

---

## What this surface does NOT cover

- **Periodic data refresh in background** — Phase 2.
- **Background photo or voice uploads** — Phase 2.
- **Push notification permission request UX** — Pass 4 Tier 3 #11.
- **Settings UI visual design for the toggles and thresholds** — Pass 4 Tier 2 #4.
- **Team-wide background sync health for owners** — Phase 2.
- **Custom user-level intervals or thresholds beyond the simple toggle** — Phase 2.

## Tier 1 close

This spec closes Pass 4 Tier 1. Three surfaces locked: owner-side mobile-conflict resolution UI (Tier 1 #1), QuickBooks conflict resolution UI (Tier 1 #2), background sync for mobile (Tier 1 #3). Two new platform patterns established (mobile-to-web escalation; integration-conflict pattern generalization confirmed via QB). Five backend additions A47–A51 totaling ~22–31 days of estimated backend work.

The Tier 1 → Tier 2 gate per the framework doc:
- [x] All three Tier 1 specs locked
- [ ] Mobile-to-web escalation pattern added to arch doc v4 §16 (Tom's separate task)
- [ ] Pre-commit staleness check confirmed reusable for both new conflict surfaces (confirmed in #1 and #2)
- [ ] Backend ledger v5 includes A47–A51 (this spec's A51 is the last; cumulative tracking ready for ledger update)
- [ ] Settings IA framework doc started (does not need to be locked; just started so Tier 2 can begin)

## Next: Tier 2 — Settings IA Framework Doc

Tier 1 close marks the start of Tier 2. The first deliverable is the Settings IA framework doc (the prerequisite to Tier 2 #4–#7). This is a one-time deliverable that locks:
- Visual treatment for inherited-from-system vs tenant-override
- Revert-to-default affordance
- Page-level layout pattern shared across web and mobile
- Settings sub-surface hierarchy (where `Sync & Storage` lives, where Voice persona tone lives, where Account settings lives, etc.)

The Settings IA framework doc is approximately 30–50% the size of a typical Pass 3 flow spec per the Pass 4 framework. After it locks, Tier 2 #4 (configurable thresholds), #5 (notification preferences), #6 (voice persona tone), and #7 (account settings) follow as Shape C deliverables.
