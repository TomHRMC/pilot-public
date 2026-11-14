# Pilot for Trades Design System — Pass 4, Tier 1 #1: Owner-Side Mobile-Conflict Resolution UI

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Web surface where owners resolve owner-escalation severity conflicts originated from technician mobile-sync events. Establishes the mobile-to-web escalation pattern as a platform-level UX vocabulary.
**Resolves**: Pass 3 Flow 7 §12 deferred surface (cross-domain consideration D)
**Depends On**: Pass 3 Flow 6 (calendar conflict resolution) · Pass 3 Flow 7 (offline-to-online sync) · Pass 2 Information Architecture · `mvp-arch.md` §15 (Mobile Offline Operations) · `mvp-arch.md` §16 (Cross-Cutting Platform Patterns)
**Backend additions**: A47 (escalation queue endpoints), A48 (resolution write path)

---

## Purpose

When a technician's mobile device queues an offline operation that fails to sync because of an owner-escalation severity conflict (job deleted while tech worked it; auth/permission boundary changes; severe data integrity issues — per Flow 7 §5), the conflict is parked in a queue and surfaced to the owner for resolution. Pass 3 designed everything except this surface: the tech's mobile experience is locked, the backend escalation routing is locked (A46), and the patterns this UI inherits are locked. What remains is the web resolution UI itself.

This spec also establishes the **mobile-to-web escalation pattern** as platform vocabulary — the inverse of the existing "mobile owner status row + deep-link" pattern. Where the existing pattern has mobile pulling status from web (read-only), this new pattern has mobile creating items that web resolves (write, with loop-closure back to mobile). Phase 2 surfaces (tech time-off requests, tech-flagged safety issues, tech-requested catalog additions) inherit this pattern by default.

## Strategic direction

### Pause, don't lose

The tech's captured data is paused, not lost. This must be visible in every state — in the tech's queue, in the owner's incoming notification, in the resolution view header, and in the post-resolution loop-back to the tech. "Sent to owner for review" should never feel like a dead end; it's a temporary state with a known resolver and a known timeline.

### Web-only resolution; mobile is informational

Same posture as Flow 6 §40. The diff payload requires side-by-side comparison and contextual access to job/customer detail; phone screens can't accommodate it well. Mobile is where the owner *learns* an escalation exists (push notification, owner tab status row); web is where the owner *resolves* it. Voice provides the third channel for the simple binary cases.

### Inherit Flow 6 wholesale; deviate only where mobile-origin context demands it

Flow 6 established the pattern vocabulary for owner-resolves-conflict surfaces. Reusing it here is a positive constraint, not a limitation. Same diff treatment, same buttons, same voice handling, same staleness check, same audit posture. Three places this spec deviates from Flow 6 are explicit and justified: (1) queue location (Dashboard rather than Settings → Integrations because mobile escalations aren't an integration concern), (2) escalation history view (Flow 6 didn't have one because calendar conflicts are bilateral, while mobile-escalations have a clear lifecycle worth visualizing), and (3) loop-closure to the originating tech (Flow 6 doesn't loop because there's no equivalent originator).

### Loop closure is non-negotiable

The mobile-to-web escalation pattern is one round-trip, not fire-and-forget. When the owner resolves on web, the tech's mobile app reflects the outcome. The tech needs to know what was decided, what local data was kept, what was discarded, and that they can keep working. Without loop closure, the tech is left with a permanent "sent to owner" status they can't act on — which violates the sync visibility principle from Flow 7.

### Solo-operator reality

Mike the solo contractor is both the tech who escalates and the owner who resolves. The "sent to owner for review" framing creates apparent dead-state for Mike — he's been told something is waiting on someone who is also him. The design must accommodate this without forcing role-conditional copy that's clumsy for multi-person shops. The answer: universal copy plus universal one-tap affordance. Mike sees "Sent to owner for review · Open on web →" on his mobile tech queue and taps the deep-link directly into the resolution view. The same affordance works correctly for multi-person shops where the tech and owner happen to be different people.

## Locked design decisions

### 1. Queue lives at `Dashboard > Approvals`, sub-tabbed alongside quote approvals

**Decision**: The owner-side mobile-conflict escalation queue lives at `Dashboard > Approvals` as a second tab within the existing approvals surface (Pass 2 established the first tab for tech-submitted quote approvals). The tab labels are **Quotes** and **Field issues**. Each tab has its own count badge.

URL: `/dashboard/approvals/field-issues` (queue list) and `/dashboard/approvals/field-issues/{escalation_id}` (resolution view).

**Rationale considered and rejected**:
- *`Settings > Integrations`* — wrong because mobile escalations aren't an integration concern. They're operational. Settings → Integrations is for QuickBooks and Google Calendar, where the conflict source is an external system.
- *Top-level "Conflicts" navigation* — wrong because escalations are low-frequency. Promoting them to top-level navigation would imply they're as common as Jobs or Quotes, which would alarm new owners. Same logic Flow 6 §2 used to keep calendar conflicts off top-level nav.
- *Schedule* — wrong because not all escalations are schedule-related (expense conflicts, photo conflicts, etc. all surface here too).

**Rationale chosen**: Dashboard → Approvals already collects "items waiting on owner." A field-tech-escalation is a kind of approval — the owner is approving (or denying) a tech's captured work that couldn't auto-commit. The tab labeling distinguishes the two flows for owners who use both.

**Tab label choice**: "Field issues" rather than "Mobile conflicts" or "Tech escalations." "Field issues" is plain-language and survives vertical expansion to plumbing/HVAC. "Mobile" and "tech" are device-and-role-specific words that read worse to owners.

### 2. Queue list as a compact table with operational urgency sorting

**Decision**: The escalation list renders as a paginated table with these columns:

| Tech | Operation | Issue | Captured | Status | Resolve |

- **Tech**: name + role icon (technician)
- **Operation**: what the tech tried to capture — pill with operation type icon ("Time entry", "Expense", "Photo", "Status change", "LOTO confirmation")
- **Issue**: plain-language summary of why this escalated ("Job was deleted while Mike was working it"; "Expense exceeded tenant per-item limit by $340"; "Permission revoked mid-shift")
- **Captured**: timestamp of when the tech captured the operation, relative format ("3 hr ago"; "Yesterday 4:12 PM")
- **Status**: pill — `Pending` (most), `Auto-recovered` (rare; conflict resolved itself before owner triaged it), `Stale` (tech force-discarded their pending sync — see §6)
- **Resolve**: button → opens resolution view

Default sort: by **escalation creation time, descending** (newest first). A sort toggle on the "Captured" column flips to capture-time ascending for owners who want to triage oldest pending first.

A filter chip row above the table:
- **Active techs** (default on) — only shows escalations from techs whose mobile app has been active in the last 24 hours; auto-recovered and stale-tech escalations are deprioritized
- **Operation type** — pill multi-select to filter by operation
- **Auto-recovered** (off by default) — shows escalations that resolved themselves before triage, useful for audit

**Rationale**: Mobile escalations have a different urgency profile than calendar conflicts. A calendar conflict is urgent based on when the affected event is scheduled (Flow 6 sorts by `scheduled_start_at`). A mobile escalation is urgent based on whether the tech is currently waiting on it. Filter-by-active-techs surfaces the operationally hot ones; the time-descending sort within that filter handles the rest. Most owners will see this view two or three times a month at most; the filtering needs to be obvious without being noisy.

### 3. Resolution view inherits Flow 6's two-column diff with mobile-origin context header

**Decision**: The resolution view is a focused single-escalation screen with two columns. **Left = "What [Tech] captured" (the tech's mobile-side state at capture); right = "Current server state" (what's on the server now).** Above both columns sits a **context header** explaining what happened and why this is escalating to the owner.

Same as Flow 6 §4, the view is **modal-feeling but routed** — its own URL (`/dashboard/approvals/field-issues/{escalation_id}`), bookmarkable, refresh-able, back-navigable.

**Context header content** (always present, always above the diff):
- Plain-language explainer: "Mike captured a 2.5-hour time entry for the Johnson panel upgrade at 4:12 PM yesterday. The job was deleted at 3:45 PM the same day, before his time entry reached the server."
- Tech identity row: avatar + name + tech role + last-active indicator ("active now" or "last active 4 hr ago")
- Capture timestamp + sync-attempt timestamp + escalation timestamp (collapsible details panel for the technically-curious owner)

**Rationale**: Flow 6 has a header but the calendar conflict context is mostly implicit (the event's title is enough; the owner already knows what events are). Mobile escalations need explicit context because the owner often hasn't seen the tech's captured operation before — it's net-new information arriving via this screen. The plain-language explainer is the most important UI element on the page; a poorly-worded explainer means the owner makes the wrong decision.

**Explainer copy is server-generated** and stored on the escalation row at creation time, so it survives even if the underlying entities (job, customer) are subsequently modified or deleted further. This is a deviation from Flow 6, where the diff is computed live from current state. Mobile escalations need a stable narrative because the tech's captured-state-vs-server-state moment is gone by the time the owner reads it.

### 4. Field-level diff vocabulary inherits Flow 6 / Flow 5 track-changes — fourth reuse

**Decision**: Within each column, the same field-level diff vocabulary applies:

| Field state | Color | Treatment |
| :--- | :--- | :--- |
| Unchanged from baseline | Neutral | Plain text |
| Modified | Amber (alert palette) | Background tint, value with prior value as struck-through helper text below |
| Added | Margin (green) | Background tint, "(added)" annotation |
| Removed | Fault (red) | Strikethrough, "(removed)" annotation |

**Rationale**: This is the fourth reuse of the track-changes pattern (Flow 5 quote approval, Flow 6 calendar conflict resolution, Flow 7 §11 mobile tech-resolvable conflicts, now this). Owners who learn it once for any one of these surfaces transfer it directly. This pattern is platform vocabulary at this point.

**Mobile-origin nuance**: the "baseline" for a mobile escalation is the **tech's local snapshot at capture time** (what the tech saw on their phone when they tapped the button). The "current" is the server state at resolution time. Diff direction is visual (amber/green/red on either side of the comparison), not semantic — the column header tells you which side is which.

### 5. Bottom action bar is two big buttons; deletion-conflict treatment when one side doesn't exist

**Decision**: The resolution view has two primary actions at the bottom:

- **Use [Tech]'s version** (primary; brand indigo) — commits the tech's captured operation; updates server state to match
- **Use server version** (secondary; neutral with brand-tinted border) — discards the tech's captured operation; keeps server state unchanged

Below them, a small text link: "Resolve later." Header has a back affordance to the queue.

**Deletion-conflict variant** — when one side has no state (Flow 6 §7's pattern applied here):

- **`Tech captured against deleted server entity`** (most common — tech captured a time entry / expense / photo against a job that was deleted): "Mike captured a 2.5-hour time entry against the Johnson panel upgrade. That job was deleted before sync. → [Restore the job and accept the time entry] or [Discard the time entry]"
- **`Tech captured a status change conflicting with server-side state change`**: "Mike marked the Williams installation complete. Server already shows it complete (Luis closed it 12 minutes earlier). → [Accept Luis's completion (no change)] or [Override with Mike's completion]"
- **`Tech captured under permissions that have been revoked`**: "Mike captured an expense for Williams installation. Mike's expense permission was revoked at 2:00 PM. → [Accept the expense (Mike was authorized at capture time)] or [Reject the expense]"

Both paths preserve the recently-captured version unless the owner explicitly chooses otherwise.

**Rationale**: Same logic as Flow 6 §7. A "use one side or the other" button doesn't communicate the existence-level decision involved in some escalation types (restore a deleted job, override a peer-tech's status change, ratify a permission-revoked capture). Verb-based buttons make the consequence explicit. The owner is making a small business decision, not just a data-merge decision.

### 6. Pre-commit staleness check (the 409-and-refresh pattern)

**Decision**: When the owner clicks any commit button (web or voice), the API re-evaluates the escalation state before committing. Three staleness scenarios trigger a 409:

1. **Underlying server state changed** — e.g., another owner restored the deleted job between escalation creation and resolution attempt. The 409 response includes refreshed escalation state. Web UI re-renders with a banner: "This issue has been updated. Review and pick again." Voice path: "The issue has changed since you last looked at it — opening on web."
2. **Auto-recovery happened during triage** — the underlying conflict resolved itself (e.g., another tech's parallel capture restored the entity). 409 response with status `auto_recovered`. Web UI shows a success banner: "This issue auto-recovered while you were viewing it. Mike's data has been committed automatically." Routes back to the queue.
3. **Tech force-discarded their pending sync** — the originating tech reset their queue (cross-domain F item, Phase 2 capability stub). 409 response with status `stale`. Web UI shows: "Mike discarded this captured data from his device. There's nothing to commit. Closing this issue." Routes back to queue.

**Rationale**: Flow 6 §8 established the 409-and-refresh pattern; this is its third reuse (after Flow 6 itself and the Flow 7 tech-resolvable surface A33). The three staleness scenarios above are specific to mobile escalations because their state has more failure modes than calendar conflicts (which are just two-system bilateral).

**Backend implication**: A48 implements three distinct 409 response payloads (`server_changed`, `auto_recovered`, `stale`) so the web UI can render the correct banner without inferring from a generic 409.

### 7. Voice resolution active for the binary cases, with confirm-as-turn safeguards

**Decision**: Voice supports both status query and active resolution. Two intents (parallel to Flow 6 §11):

**Status query** (`list_pending_field_issues`):
- "Do I have any field issues?" → AI responds with count, tech identities, and brief urgency summary ("You have 2 — Mike's time entry against the deleted Johnson job, and Luis's expense over the per-item limit.")

**Resolution** (`resolve_field_issue`):
- "Resolve Mike's time entry — use his version" / "...use server version"
- "Accept Mike's time entry"
- Identifier resolution: by tech name, operation type, or affected customer/job. AI disambiguates if multiple match.
- **Confirm-as-turn before commit**: AI reads back what gets committed and what gets discarded.
  > "Accepting Mike's 2.5-hour time entry against the Johnson panel upgrade. That restores the deleted job and posts Mike's hours. Total job cost increases by $187.50 in labor. Confirm?"
- The owner's "yes" / "confirm" / "do it" commits; any other utterance cancels and the AI offers to read the diff via web link.
- **Voice resolution honors the staleness check** (per Decision 6): if state shifted between identification and confirmation, the AI announces "the issue has changed since you last looked at it — opening on web" and routes to web with deep-link.

**Resolution paths that route to web instead** (voice-unsuitable):
- **Deletion-conflict treatments** (Decision 5 variants) — verb-based path choices ("restore," "override," "discard") are too easy to mis-pick by voice.
- **Post-staleness recovery** — once state shifted, owner needs to see new state visually.
- **Permission-revoked captures** — owner often wants to see *what* was captured before deciding whether to ratify; voice readback is too thin for an audit-significant decision.

**Rationale**: Pilot's voice-first positioning extends to all owner workflows that don't require dense visual comparison. Same logic as Flow 6 §11. Confirm-as-turn safeguard plus explicit field-readback before commit make wrong-resolution risk acceptable for the simple accept-this-side case.

### 8. Loop closure: tech's mobile app reflects the resolution outcome

**Decision**: When the owner resolves on web (or via voice), three downstream effects happen on the originating tech's mobile device:

1. **Sync queue item update**: the queue item that was in "sent to owner for review" status transitions to one of three terminal states:
   - `resolved_in_favor_of_tech` — owner accepted tech's version; the operation is now on the server; queue item dismisses with a brief success animation
   - `resolved_in_favor_of_server` — owner discarded tech's captured operation; queue item shows a final state for 24 hours then auto-dismisses, with copy: "Owner kept the server version. Your captured [operation] was discarded."
   - `resolved_with_action` — owner picked a deletion-conflict path that has consequence beyond the captured data (e.g., job restored). Queue item shows: "Owner restored [Job] and accepted your time entry."

2. **Push notification to the originating tech** (rate-limited per A35): "Your [operation] has been [resolved]. Tap to see details."

3. **Persistent activity log entry**: in the tech's mobile-app activity log (existing surface from Flow 7), a permanent entry records: timestamp, what was captured, what got resolved, by whom, what the outcome was. This is durable history — the queue item dismisses, but the log persists.

**Rationale**: Without loop-closure, the tech is left with a permanent "sent to owner" status they can't act on. Worse, they don't know whether their captured work survived. The three-effect pattern (queue update + push + log) ensures the tech has both immediate awareness and long-term reference.

**Backend implication**: A48 (resolution write path) emits a `mobile_sync_event` update on resolution, which propagates to the tech's device on next sync foreground. Push notification fires via existing notification_outbox per A4 + A35.

### 9. Solo-operator one-tap path: deep-link from mobile to web

**Decision**: For all roles — including solo operators where tech and owner are the same person — the mobile tech-side queue item that's in "sent to owner for review" status shows a "**Open on web →**" link directly under the status text. Tapping the link opens the web resolution view in the device's mobile browser.

The mobile owner tab additionally shows a "Field issues" status row alongside the existing Calendar sync and QuickBooks sync rows (parity with Flow 6 §10):

- **Healthy**: green dot, "Field issues · None pending"
- **Pending issues**: amber dot, "Field issues · N pending," subtitle "Resolve on web →"
- (No "connection error" state — escalations don't fail; they queue)

Tapping the row deep-links to `/dashboard/approvals/field-issues` in the mobile browser.

**Rationale**: For multi-person shops, the deep-link is convenient — owner gets push, taps notification, lands directly in resolution view. For solo Mike, the deep-link is essential — without it, he sees "sent to owner" with no obvious next action and would have to manually navigate to web. Same single affordance handles both cases without role-conditional UI.

**Universal copy choice**: "Sent to owner for review" is correct for both cases. For solo Mike, "owner" refers to himself and the readback is grammatically fine. The alternative ("Sent for review") is awkward in multi-person shops where techs benefit from knowing their captured work is going up the chain. Universal copy + universal deep-link is the cleanest answer.

### 10. Resolution is auditable but not undoable through this UI

**Decision**: When an escalation is resolved (web or voice), the chosen action commits and the loop-closure effects propagate to the tech. There is no "undo resolution" button. If the owner realizes they picked wrong, they handle it through normal flows — re-create a deleted entity, edit a committed time entry, etc. The audit trail (`mobile_sync_event_audit`) preserves the resolution decision, the resolver's identity, the channel (web vs voice), the tech's pre-commit data, the server's pre-commit state, and the post-commit state.

**Rationale**: Same as Flow 6 §9. Undo would compete with normal "edit the thing" path and create confusing two-paths-to-fix. Audit preserves the truth. Editing affordance fixes mistakes.

**Audit scope is broader than Flow 6**: because mobile escalations involve a person who isn't the resolver (the originating tech), the audit log includes both identities — useful for HR / payroll / compliance review when an owner ratifies or discards a tech's captured work.

### 11. Empty state + escalation history view

**Decision**: When there are no pending escalations, the queue surface shows a calm empty state:

> **No field issues to resolve.** Your team's captures are all syncing cleanly.
>
> *Field issues appear here when a tech's mobile capture can't auto-commit — usually because something changed on the server while the tech was offline. They're rare; most teams see one or two a month.*

Below the empty-state message, a **"Recent issue history"** expandable panel shows the last 30 resolved escalations as a compact log: tech name, operation, outcome, resolver, timestamp. This panel persists when the queue has pending items too — the empty-state message is replaced with the queue table, but history stays available.

A separate route at `/dashboard/approvals/field-issues/history` shows the full historical archive with filters (tech, date range, operation, outcome, resolver). This is the audit surface owners reach for when reviewing a tech's record or investigating a payroll/profitability anomaly.

**Rationale**: Empty state teaches normalcy (parallel to Flow 6 §12) — escalations are rare; not seeing any is the expected state. The brief inline history reassures new owners that the surface works without forcing them into a separate audit screen for casual review. The full history route handles compliance use cases.

### 12. Mobile-to-web escalation as platform pattern (added to arch doc §16)

**Decision**: This surface establishes the **mobile-to-web escalation pattern** as the eleventh entry in arch doc v4 §16 (Cross-Cutting Platform Patterns).

**Pattern definition**:
> When mobile-originated activity requires owner judgment that the tech cannot or should not make autonomously, the activity is paused at the mobile origin, escalated to a web-side queue with push notification to the owner, resolved by the owner on web (or via voice for binary cases), and looped back to the originating tech with the resolution outcome reflected in their mobile experience. Resolution honors the pre-commit staleness check pattern. Audit trail records both the originator and the resolver.

**Pattern characteristics**:
- *Origin*: a mobile-side action that classifies into a severity tier requiring owner involvement (per the four-class severity pattern, the "owner_escalation" class)
- *Routing*: persistent server-side queue + push notification + entry in the appropriate web `Approvals` sub-surface
- *Resolution*: web-only diff view inheriting Flow 6's two-column treatment, with voice resolution for binary cases
- *Loop closure*: originating mobile device receives status update, push notification, and persistent activity log entry
- *Auditability*: both originator and resolver are captured in the audit log

**Reusable for** (Phase 2 surfaces this pattern fits):
- Tech-submitted time-off requests
- Tech-flagged safety incidents requiring owner review
- Tech-requested catalog item additions (a part the tech needs that isn't in the catalog)
- Tech-flagged customer issues escalating to owner
- Tech-requested expense limit overrides

**Distinct from the existing "mobile owner status row + deep-link" pattern**: that pattern is read-only (mobile shows web status). This pattern is full round-trip (mobile creates, web resolves, mobile reflects).

**Rationale**: Naming and formalizing the pattern now means Phase 2 surfaces inherit a known structure rather than reinventing escalation flows ad-hoc. The arch doc §16 update (which Tom owns as a follow-on edit) places this pattern alongside the eight Pass 3 patterns.

## UX patterns established (for inheritance by future flows / Phase 2)

| Pattern | Established here | Inherits from |
| :--- | :--- | :--- |
| Mobile-to-web escalation pattern | **NEW (formalized in §12 above; added to arch doc §16)** | — |
| Track-changes diff vocabulary (amber/green/red) | Reused — fourth occurrence | Flow 5 → Flow 6 → Flow 7 §11 → here |
| Side-by-side two-column diff | Reused | Flow 6 §4 |
| Two-button bottom action bar with "Resolve later" escape | Reused | Flow 6 §6 |
| Deletion-conflict distinct verb-based treatment | Reused, extended with two new variants | Flow 6 §7 |
| Pre-commit staleness check (409-and-refresh) | Reused, extended with three distinct 409 payload types | Flow 6 §8, Flow 7 A33 |
| Modal-feeling but routed (own URL, bookmarkable) | Reused | Flow 6 §4 |
| Voice resolution with confirm-as-turn safeguards | Reused | Flow 6 §11 |
| Audit-but-no-undo | Reused, extended to capture both originator and resolver | Flow 6 §9 |
| Empty state teaches normalcy | Reused | Flow 6 §12 |
| Mobile owner status row + deep-link | Reused — third instance after Pass 2 (QB) and Flow 6 (Calendar) | Pass 2 §9 |
| Loop closure to originating mobile device | **NEW** (specific to mobile-origin escalations) | — |

Two genuinely new vocabulary additions; eight reuses. The pattern density is intentionally high — this surface is pattern-establishing largely *by demonstrating* that Flow 6's vocabulary generalizes cleanly to a different conflict source.

## Cross-domain considerations

### A. The QuickBooks conflict resolution UI (Tier 1 #2, next) inherits this design *and* Flow 6

The next Pass 4 surface — Tier 1 #2 QuickBooks conflict resolution UI — sits between Flow 6 (calendar conflicts) and this surface (mobile escalations) in pattern lineage. Flow 6 covers the bilateral integration-conflict case; this surface covers the originator-and-resolver case; QB conflict UI is bilateral *and* integration-conflict, so it inherits primarily from Flow 6 with this surface's queue-location and naming pattern as secondary input. The Tier 1 #2 spec confirms which reuses cleanest.

### B. Notification rate limiting on the originating tech (loop closure)

Decision 8's push notification to the originating tech reuses A35 rate limiting (originally established for owner-direction notifications in Flow 6). Edge case: if an owner batches resolution of 5+ escalations from the same tech in quick succession, the tech could receive 5+ push notifications. A35 already handles this as an aggregate notification ("3 of your captures were resolved by your owner"), but the aggregation needs to be tested against the resolution event source specifically.

### C. Activity log retention on tech mobile

Decision 8's persistent activity log on the tech's mobile device needs a retention policy. Recommendation: keep the last 90 days locally; older entries fetched from server on demand. Aligns with general mobile data retention thinking — the tech rarely needs entries older than a quarter, and unbounded local storage growth is a known problem. **Captured as a sub-scope item under A48** rather than a separate addition.

### D. Auto-recovery during triage requires server-side detection and notification

Decision 6's "auto-recovered while you were viewing it" scenario requires the server to detect the auto-recovery and either push a state change to any active web sessions or rely on the next pre-commit check to surface it. Push-based detection (via SSE per arch doc §13.11) is preferred because it avoids the owner staring at a stale view that only updates on commit-attempt. **Captured in A47 scope**.

### E. Tech force-discard of pending sync (currently absent, Phase 2 feature)

Decision 6's "stale" 409 case anticipates a Phase 2 mobile feature where techs can force-discard a pending sync (e.g., "I'm not going to wait for the owner; cancel this capture; I'll re-capture later if needed"). This feature isn't in MVP, but the resolution UI needs to handle the case correctly when it arrives. Specifying the 409 payload now means Phase 2 implementation is a one-side change (mobile only); web UI already accommodates.

### F. RBAC scope for the resolution surface

Only users with the `owner` role (or equivalent permission per A33-style RBAC) can access `/dashboard/approvals/field-issues`. Multi-person shops with a designated dispatcher role might want dispatcher-level access in Phase 2 — flagged as a Phase 2 RBAC scope expansion.

### G. The "Auto-recovered" status in the queue list (Decision 2)

Decision 2 includes `Auto-recovered` as a queue status, but Decision 6 says auto-recovery during owner viewing routes the owner back to the queue with a success banner. So when does an `Auto-recovered` entry appear in the queue?

Answer: when auto-recovery happens *between* escalation creation and the owner's first visit to the queue. The owner sees "this issue auto-recovered before you got to it; here's what happened" as a passive entry, useful for audit but requires no action. Most owners will dismiss-or-ignore these entries; making them visible (rather than silently disposing) provides confidence that the auto-recovery logic is working.

## Deferred items (Phase 2 / for future iteration)

- **Bulk resolution** — same logic as Flow 6 §3; per-conflict only in MVP. Phase 2 can add bulk-resolve for low-stakes escalation classes (e.g., per-tech "accept all my recent expense escalations").
- **Owner-defined escalation rules** — e.g., "auto-accept all time entries from techs with 2+ years tenure" — Phase 2; default classification matrix from A40 covers MVP.
- **Escalation analytics / dashboard** — escalation rate per tech, average resolution time, common operation types — Phase 2.
- **Tech force-discard of pending sync** — see Cross-Domain E. Phase 2 mobile feature; web-side handling stubbed per Decision 6.
- **Tech direct messaging from resolution view** — owner wants to ask the tech a clarifying question before resolving — Phase 2; for MVP owners message techs through existing customer-comms or out-of-band.
- **Manual-edit-during-resolution** — owner wants to commit a custom value rather than picking either side — Phase 2; for MVP, owner picks a side then edits via normal flows (same as Flow 6 §9).
- **Dispatcher-role access** — Cross-Domain F; Phase 2 RBAC expansion.
- **Field-issue auto-expiry to a default outcome** — explicitly *not* added because the data-loss risk (silently discarding tech's captured work) is too high. Escalations stay open until resolved. Phase 2 may add owner-aged-escalation reminders ("3+ day pending escalations") rather than auto-expiry.

## Validation checklist

Before implementation begins:

- [ ] Dev team aligned on `Dashboard > Approvals` two-tab structure (Quotes + Field issues)
- [ ] Web routing structure committed: `/dashboard/approvals/field-issues` + `/dashboard/approvals/field-issues/{id}` + `/dashboard/approvals/field-issues/history`
- [ ] A47 endpoints specified (queue list, escalation detail, history list)
- [ ] A48 endpoints specified (resolve write path with three distinct 409 payload types)
- [ ] Server-generated explainer copy templates defined per operation × escalation reason matrix
- [ ] Loop-closure event flow specified end-to-end (web resolve → server commit → tech mobile sync queue update + push + activity log)
- [ ] Voice intent grammar `list_pending_field_issues` and `resolve_field_issue` specified in voice intent registry (extension to arch doc §6)
- [ ] Mobile owner tab "Field issues" status row added to mobile sitemap (mobile sitemap update)
- [ ] Tech mobile activity log retention policy committed (90-day default per Cross-Domain C)
- [ ] Push notification rate limiting tested against batch-resolution scenario (Cross-Domain B)
- [ ] Auto-recovery detection mechanism picked: SSE push vs. pre-commit-check-only (Cross-Domain D)
- [ ] RBAC scope confirmed: owner-role-only for MVP; dispatcher access deferred (Cross-Domain F)
- [ ] Audit log schema captures both originator and resolver identities

## Backend additions (new for Tier 1 #1)

### A47. Owner-Side Mobile-Conflict Escalation Queue Endpoints

**Triggered by**: Decisions 1, 2, 11 — queue list with filtering, escalation detail with explainer copy, history archive.

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

**Triggered by**: Decisions 5, 6, 8, 10 — resolution commit with pre-commit staleness check, three distinct 409 payload types, loop-closure to originating tech, audit log capture.

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

**Voice channel routing**: when resolution comes in via voice (per Decision 7), the same endpoint handles it; `resolution_channel` is set on the audit entry. Voice intent handler `resolve_field_issue` calls this endpoint internally.

**Effort estimate**: Medium-Large — 5–7 days. The variation across resolution types per operation is the main cost (each type needs domain-specific commit logic). The 409 payload differentiation, loop-closure event emission, and audit capture are smaller incremental costs.

---

## What this surface does NOT cover

- **Tech-resolvable conflict UI** — Pass 3 Flow 7 §11 covers it on mobile.
- **Auto-resolve silent / auto-resolve with notice classes** — Pass 3 Flow 7 §5; no UI.
- **Calendar sync conflicts** — Pass 3 Flow 6.
- **QuickBooks sync conflicts** — Tier 1 #2 (next).
- **Bulk operations / dispatcher RBAC / advanced analytics** — Phase 2; see Deferred Items.
- **Push notification permission request flow** — Pass 4 Tier 3 #11 (mobile push permission UX); this surface assumes permission was already granted.

## Next: Tier 1 #2 — QuickBooks Conflict Resolution UI

The Tier 1 #2 spec inherits from Flow 6 (calendar conflict resolution) primarily and from this spec secondarily. Its job is to validate that the calendar-conflict pattern generalizes to a different bilateral integration domain (accounting sync vs scheduling), and to surface any Flow 6 decisions that don't transfer cleanly.

Open questions for Tier 1 #2 to confirm:
- Does the QB conflict UI live under `Settings > Integrations > QuickBooks` (parallel to Flow 6's `Settings > Integrations > Calendar`)?
- Does it inherit Flow 6's auto-expiry pattern (system default + tenant override) or does QB's stricter accounting integrity warrant manual-only resolution?
- Are there QB-specific conflict classes (e.g., tax liability mismatch, unmapped account) that don't fit the Flow 6 vocabulary cleanly?
- Voice resolution scope: same as Flow 6, or stricter for an accounting-data domain?

After Tier 1 #2 locks, Tier 1 #3 (background sync for mobile) closes Tier 1 and Tier 2 (settings work) begins with the Settings IA framework doc.
