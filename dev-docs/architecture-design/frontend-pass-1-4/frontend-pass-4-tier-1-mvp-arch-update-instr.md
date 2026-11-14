# Pilot for Trades — `mvp-arch.md` §16 Update Instructions (Pass 4 Tier 1 Close)

**Purpose**: Update `mvp-arch.md` Chapter 16 (Cross-Cutting Platform Patterns) to reflect the two new patterns established in Pass 4 Tier 1 (mobile-to-web escalation; background sync execution) and to refactor §16.5's reference to the bilateral integration conflict pattern (which now generalizes across calendar and QuickBooks).

**Affected file**: `mvp-arch.md`
**Affected chapter**: §16 (lines 2633–2818 in your v4)
**Total edits**: 4 (1 inventory table update; 3 new subsections appended; 1 doc header version bump)
**Estimated edit time**: 10–15 minutes

When you finish, the chapter has 12 subsections (was 9) and the inventory table reflects 11 named patterns (was 8).

---

## Edit 1 — Doc header version bump (top of `mvp-arch.md`)

Locate the version metadata at the top of `mvp-arch.md` (likely lines 1–10 area). Bump the version from v4.0 to v4.1 to reflect the §16 patterns added in Pass 4 Tier 1. Recommended edit:

**Find**: whatever line currently says version 4.0 (e.g., `**Version**: 4.0`)
**Replace with**: `**Version**: 4.1 (Pass 4 Tier 1 patterns added to §16; full v5 issued at Pass 4 close)`

If your doc has a "Last Updated" line, bump that to today's date (April 27, 2026).

---

## Edit 2 — Update §16.1 Pattern Inventory table

The inventory table currently lists 8 patterns. Three new entries need to be added, and one existing entry needs its reuse count and instances list updated.

**Locate**: lines 2637–2648 in your v4 (the §16.1 table titled "Pattern Inventory").

**Current state of the table** (as in your v4 lines 2640–2648):
```
| Pattern | First Established | Reuse Count |
| :--- | :--- | :--- |
| Track-changes diff vocabulary (amber/green/red) | Flow 5 (Quote approval) | 4 (quote approval, calendar conflict §13.5, mobile sync §15, future QB §5.4) |
| Four-class severity pattern | Flow 3 (Dispatch conflicts) | 3 (dispatch §13.4, calendar sync §13.5, mobile sync §15.6) |
| Confirm-as-turn for destructive voice actions | Flow 1 (Voice quote creation) | All destructive voice intents §6.2 |
| Pre-commit staleness check (409-and-refresh) | Flow 3 (Dispatch board edits) | 6 endpoints across §13.7, §13.5, §14.4, §15.9 |
| System default + tenant override two-tier configuration | Flow 6 (Calendar conflict auto-expiry) | Available platform-wide; pattern formalized below |
| Mobile owner status row + deep-link | Pass 2 QB sync | Extended for calendar §13.5, mobile sync §15.3 |
| Optimistic UI with pending badges | Flow 7 (Mobile offline) | All mobile offline-capable operations §15 |
| Always-preview-before-send for one-way-door actions | Flow 4 (Customer comms) | Customer comms §3.7; extensible to any future irreversible action |
```

**Replace the entire table body** (everything from `| Track-changes diff vocabulary` through the `Always-preview-before-send` row) with this updated table (note the updated reuse counts on the first four rows, plus three new rows at the bottom):

```
| Pattern | First Established | Reuse Count |
| :--- | :--- | :--- |
| Track-changes diff vocabulary (amber/green/red) | Flow 5 (Quote approval) | 5 (quote approval §14, calendar conflict §13.5, mobile sync §15, mobile-conflict escalation §16.10, QB conflict §5.4 / §16.5) |
| Four-class severity pattern | Flow 3 (Dispatch conflicts) | 3 (dispatch §13.4, calendar sync §13.5, mobile sync §15.6) |
| Confirm-as-turn for destructive voice actions | Flow 1 (Voice quote creation) | All destructive voice intents §6.2 |
| Pre-commit staleness check (409-and-refresh) | Flow 3 (Dispatch board edits) | 8 endpoints across §13.7, §13.5, §14.4, §15.9, §5.4, §16.10 |
| System default + tenant override two-tier configuration | Flow 6 (Calendar conflict auto-expiry) | Calendar §13.5, QB conflicts §5.4, background sync §15.10; available platform-wide |
| Mobile owner status row + deep-link | Pass 2 QB sync | Extended for calendar §13.5, mobile sync §15.3, field issues §16.10 |
| Optimistic UI with pending badges | Flow 7 (Mobile offline) | All mobile offline-capable operations §15 |
| Always-preview-before-send for one-way-door actions | Flow 4 (Customer comms) | Customer comms §3.7; extensible to any future irreversible action |
| Bilateral integration conflict resolution pattern (formalized §16.5) | Flow 6 (Calendar) | Calendar §13.5, QuickBooks §5.4 |
| Mobile-to-web escalation pattern | Pass 4 Tier 1 #1 (Owner mobile-conflict UI) | Field issues §16.10; extensible to time-off requests, safety incidents, catalog requests |
| Background sync execution pattern | Pass 4 Tier 1 #3 (Background sync for mobile) | Mobile data queue §15.10; extensible to periodic data refresh, future tech-to-tech messaging |
```

The three new rows at the bottom are the patterns added by Pass 4 Tier 1.

---

## Edit 3 — Refactor §16.5 (System Default + Tenant Override) — minor, optional but recommended

Your existing §16.5 reads cleanly. The only update is to extend its "Settings using this pattern (Pass 3)" list to include the new Pass 4 settings. This is appended to the existing list, not a rewrite.

**Locate**: lines 2746–2750 in your v4.

**Current state**:
```
**Settings using this pattern** (Pass 3):

- `calendar_conflict_auto_expire_days` / `system_calendar_conflict_auto_expire_days`
- `calendar_conflict_pre_warning_days` / `system_calendar_conflict_warn_days_before`

Available for any future setting where platform admins want global control with tenant flexibility.
```

**Replace with**:
```
**Settings using this pattern** (Pass 3):

- `calendar_conflict_auto_expire_days` / `system_calendar_conflict_auto_expire_days`
- `calendar_conflict_pre_warning_days` / `system_calendar_conflict_warn_days_before`

**Settings using this pattern** (Pass 4 Tier 1):

- `background_sync_push_interval_minutes` / `system_background_sync_push_interval_minutes` (per Pass 4 Tier 1 #3 Decision 4)
- `qb_auto_expire_*_enabled` family (per-entity-type for customers, quotes, invoices, expenses) (per Pass 4 Tier 1 #2 Decision 9)
- `qb_auto_expire_*_direction` paired settings (`accept_local | accept_remote` per entity type)
- `qb_auto_expire_days` / `system_qb_auto_expire_days` (default 60; Pass 4 Tier 1 #2 Decision 9)
- `qb_pre_warning_days` / `system_qb_pre_warning_days` (default 14)

Available for any future setting where platform admins want global control with tenant flexibility.
```

---

## Edit 4 — Append three new subsections to §16

After §16.9 (Mobile Owner Status Row + Deep-Link, ending around line 2816 in your v4), and before the `---` separator that ends Chapter 16 (around line 2818), append the three new subsections below.

**Insertion point**: between the line `**Extensible to**: any future bi-directional integration or async-status surface.` (line 2816) and the `---` separator (line 2818). You're inserting *before* the closing `---`, so the chapter still ends cleanly at the separator.

**Content to insert** (three new subsections — paste verbatim):

````markdown
### 16.10 Bilateral Integration Conflict Resolution Pattern

This pattern governs owner-resolves-conflict surfaces for any bilateral integration where both Pilot and an external system can modify the same entity. Reference instances: calendar sync (Pass 3 Flow 6, formalized in §13.5) and QuickBooks sync (Pass 4 Tier 1 #2, formalized in §5.4). Future bilateral integrations (Salesforce, HubSpot, generic webhook integrations) inherit this pattern by default; deviations require explicit justification.

**Pattern attributes that are domain-determined rather than fixed**:

- **Auto-expiry default**: ON when the master is unambiguous and silent fallback to a known direction is safe (calendar — Pilot is master). OFF when masters are heterogeneous or recovery cost is high (QuickBooks — different masters per entity type, accounting integrity stakes). Tenants can opt in/out per entity type via the §16.5 system-default-with-tenant-override pattern.
- **Voice resolution scope**: full active resolution when stakes permit (calendar). Status-query-only when stakes are too high for voice's confirm-as-turn safeguard (QuickBooks accounting data).
- **Column ordering and primary-button treatment**: master-aware (column with the master entity gets leftward primacy and primary-indigo button) when masters are heterogeneous. Reduces to fixed ordering when the master is uniform across all entity types within the integration.

**Pattern attributes that are fixed**:

- Side-by-side two-column diff with track-changes vocabulary (§16.2)
- Two-button bottom action bar with "Resolve later" escape
- Deletion-conflict distinct verb-based treatment (existence-level decisions use verb buttons rather than side-pickers)
- Pre-commit staleness check (§16.4)
- Modal-feeling but URL-routed (bookmarkable, refresh-able)
- Audit-but-no-undo (audit log preserves resolution; mistakes corrected via normal edit flows)
- Empty state teaches normalcy (informative, not alarming)
- Mobile owner status row + deep-link (§16.9)
- System-default + tenant-override auto-expiry (when applicable per the domain-determined attribute above; uses §16.5)

**Reference UI implementations**:

- §13.5 (Calendar conflict resolution architecture)
- §5.4 (QuickBooks conflict resolution; UI added in Pass 4 Tier 1 #2)

### 16.11 Mobile-to-Web Escalation Pattern

When mobile-originated activity requires owner judgment that the tech cannot or should not make autonomously, the activity is paused at the mobile origin, escalated to a web-side queue with push notification to the owner, resolved by the owner on web (or via voice for binary cases), and looped back to the originating tech with the resolution outcome reflected in their mobile experience. Resolution honors the pre-commit staleness check pattern (§16.4). Audit trail records both the originator and the resolver.

**Pattern characteristics**:

- *Origin*: a mobile-side action that classifies into a severity tier requiring owner involvement (per the four-class severity pattern §16.6, the "owner_escalation" class)
- *Routing*: persistent server-side queue + push notification + entry in the appropriate web `Approvals` sub-surface
- *Resolution*: web-only diff view inheriting the bilateral integration conflict resolution pattern's two-column treatment (§16.10), with voice resolution for binary cases
- *Loop closure*: originating mobile device receives status update, push notification, and persistent activity log entry
- *Auditability*: both originator and resolver are captured in the audit log

**Reference instance**: Pass 4 Tier 1 #1 (owner-side mobile-conflict resolution; backend in A47–A48).

**Future surfaces inheriting this pattern** (Phase 2): tech-submitted time-off requests, tech-flagged safety incidents, tech-requested catalog item additions, tech-flagged customer issues escalating to owner, tech-requested expense limit overrides.

**Distinct from §16.9 mobile owner status row + deep-link**: that pattern is read-only (mobile shows web status). This pattern is full round-trip (mobile creates, web resolves, mobile reflects).

### 16.12 Background Sync Execution Pattern

When a mobile queue requires execution outside of foreground app sessions, the platform uses an asymmetric implementation strategy with a uniform user experience. Reference instance: Pass 4 Tier 1 #3 (background sync for mobile data queue; backend in A51).

**Pattern attributes**:

- *Primary trigger*: server-initiated push (silent push on iOS, high-priority FCM on Android), rate-limited per device with a tenant-configurable interval (uses §16.5 system-default-with-tenant-override pattern; setting `background_sync_push_interval_minutes`, default 5)
- *Fallback trigger*: OS-scheduled opportunistic execution (BGAppRefreshTask on iOS, WorkManager periodic on Android); used when push delivery is delayed or throttled
- *Execution scope*: lightweight operations only; heavy operations (photos, voice audio, periodic data refresh) remain foreground-only unless explicitly upgraded
- *Conflict handling*: auto-resolves only in background (per §16.6 four-class severity pattern, only `auto_silent` and `auto_with_notice` classes commit in background); `tech_resolvable` and `owner_escalation` classes defer to foreground
- *Failure visibility*: every background run reports outcome to a tech-visible "last attempt" indicator on next app open; persistent failures (>3 consecutive) trigger a foreground notification
- *Platform-asymmetric implementation, uniform UX*: tech experience is identical across iOS and Android; underlying mechanisms differ

**Future surfaces inheriting this pattern** (Phase 2): periodic data refresh (pulling jobs/customers/quotes/etc. while backgrounded), background photo upload (if upgraded from foreground), tech-to-tech messaging delivery, future asynchronous server-to-mobile push delivery.

**Push token registry** is canonical infrastructure introduced by A51; reused by mobile-to-web escalation loop closure (§16.11) and any future surface requiring server-to-mobile push.

````

---

## Edit 5 (optional cleanup) — Update §13.5 forward-reference to QB

Your §13.5 (Calendar Conflict Resolution Architecture) has language saying QB conflict resolution UI is "deferred to Pass 4." That deferral is now resolved. Consider a single-line update.

**Search for** (somewhere in §13.5, likely a paragraph mentioning the QB cross-domain consideration): something like *"The QuickBooks conflict resolution UI inherits this design wholesale; deferred to Pass 4."* or similar phrasing.

**Replace with**: *"The QuickBooks conflict resolution UI inherits this design (formalized as the bilateral integration conflict resolution pattern in §16.10). Implemented in Pass 4 Tier 1 #2; backend in A49–A50."*

Same applies to any similar forward-reference language in §5.4 — your v4 has a paragraph there saying "**UI inheritance from Calendar Conflict Resolution (§13.5) — deferred to Pass 4**." That sentence can now be flipped to past tense and reference Tier 1 #2.

These are minor cleanups; they don't gate anything but tighten the cross-references.

---

## Verification checklist after edits

- [ ] Doc header version bumped to v4.1 (Edit 1)
- [ ] §16.1 Pattern Inventory table has 11 rows, with three new entries at the bottom (Edit 2)
- [ ] First four rows in §16.1 table have updated reuse counts and instance lists (Edit 2)
- [ ] §16.5 has the new "Settings using this pattern (Pass 4 Tier 1)" subsection (Edit 3)
- [ ] §16 chapter has subsections §16.10, §16.11, §16.12 inserted before the closing `---` separator (Edit 4)
- [ ] §13.5 and §5.4 forward-references to "Pass 4 deferred" updated to past tense (Edit 5, optional)
- [ ] Chapter 16 ends cleanly at the `---` separator before Cost Analysis chapter starts

After these edits, Chapter 16 grows from ~185 lines (in your v4) to roughly ~290–310 lines.
