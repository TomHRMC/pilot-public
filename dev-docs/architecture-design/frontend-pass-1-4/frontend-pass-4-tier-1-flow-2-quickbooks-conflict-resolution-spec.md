# Pilot for Trades Design System — Pass 4, Tier 1 #2: QuickBooks Conflict Resolution UI

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Web surface where owners resolve bi-directional sync conflicts between Pilot and QuickBooks Online. Validates that the calendar-conflict pattern from Flow 6 generalizes to a different bilateral integration domain.
**Resolves**: `mvp-arch.md` §5.4 ("UI inheritance from Calendar Conflict Resolution — deferred to Pass 4")
**Depends On**: Pass 3 Flow 6 (calendar conflict resolution) · Pass 4 Tier 1 #1 (owner-side mobile-conflict resolution) · `mvp-arch.md` §5 (QuickBooks Integration) · `mvp-arch.md` §13.5 (Calendar conflict resolution architecture) · `mvp-arch.md` §16 (Cross-Cutting Platform Patterns)
**Backend additions**: A49 (QB conflict queue endpoints), A50 (QB conflict resolution write path)

---

## Purpose

When the bi-directional QuickBooks sync detects a conflict (both Pilot and QB modified the same entity since last sync), the conflict is parked in `integration_sync_conflict` and surfaced to the owner for resolution. The architecture for detection and storage exists (per `mvp-arch.md` §5.4); the resolution UI does not. Pass 4 Tier 1 #2 designs that UI.

The framing that matters: this is the **second instance of the integration-conflict pattern** Flow 6 established. If Flow 6's vocabulary transfers cleanly to QB, the pattern is officially generalizable to any future bilateral integration (Phase 2: Salesforce, HubSpot, generic webhook integrations). If pieces don't transfer, this spec surfaces them — and the §16 §16 pattern entry gets revised accordingly. The expected outcome is a high-inheritance, low-novelty spec — and that's the point. Pattern reuse compounds.

This spec assumes accounting-data stakes are higher than scheduling-data stakes. A wrong calendar-conflict resolution costs a tech showing up at the wrong time. A wrong invoice-conflict resolution costs incorrect AR balance, incorrect revenue recognition, potentially incorrect tax filing. Four design decisions deviate from Flow 6 explicitly because of that stakes asymmetry.

## Strategic direction

### Per-entity master rules require per-entity UI nuance

QuickBooks bi-directional sync is not uniform across entity types. From `mvp-arch.md` §5.3:

| Entity | Pilot → QB | QB → Pilot | Conflict master |
| :--- | :---: | :---: | :--- |
| **Customers** | ✅ | ✅ | User choice |
| **Quotes** | ✅ (as Estimates) | ✅ | Pilot |
| **Invoices** | ✅ | ✅ | QB |
| **Payments** | ❌ | ✅ | (one-way; no conflicts possible) |
| **Expenses** | ✅ | ✅ | User choice |
| **Tax Components** | ✅ | ❌ | (one-way; no conflicts possible) |

Four entity types can produce conflicts (Customers, Quotes, Invoices, Expenses). Two are one-way and produce no conflicts (Payments QB→Pilot only; Tax Components Pilot→QB only). The four conflicting types have different master rules. The UI honors these rules through column ordering and recommended-action treatment, not by changing the underlying two-button decision pattern.

### Accounting integrity is more expensive to fix than scheduling

Flow 6 took the stance that conflicts are recoverable through normal "edit the event" flows. That holds for QB Customer / Expense conflicts (small consequence) but not for Invoices (recovery requires re-issuing or voiding, with potential tax-period implications). The UI does not block accounting-stakes resolutions, but it does surface their consequences clearly: the invoice-conflict resolution view includes a financial-delta callout that calendar conflicts don't have.

### Voice scope is stricter than Flow 6

Flow 6 supported voice resolution for binary cases (with confirm-as-turn safeguards). For QB, voice supports **status query only**; all resolution routes to web. The stakes asymmetry doesn't justify the convenience. This is a deliberate scope cut, not an oversight, and it's recorded explicitly so Phase 2 can reconsider if operational data shows owners want voice resolution for low-stakes entities (Customers).

### Auto-expiry default is flipped from Flow 6

Flow 6 enables auto-expiry by default (system default 30 days → `accept_local`) because Pilot is the unambiguous calendar master and silent fallback to Pilot is safe. QB has no unambiguous master across entities (per §5.3). Auto-expiry is **OFF by default for all QB conflict types**; tenants who want it must opt in per entity type and pick the direction. This is the opposite default of Flow 6 and the reasoning is explicit: silent overwrites of accounting data carry costs that silent overwrites of scheduling data don't.

### Configuration-class issues are explicitly out of scope

Mapping ambiguities, tax agency lookup failures, and missing chart-of-accounts entries can also surface during sync. These are configuration issues, not data conflicts — they live in a separate "QuickBooks setup health" surface that's a Phase 2 / onboarding deliverable. This spec covers only version-token conflicts on the four bilateral entity types.

## Locked design decisions

### 1. Surface lives at `Settings > Integrations > QuickBooks > Conflicts`

**Decision**: The QB conflicts surface lives at `/settings/integrations/quickbooks/conflicts` (queue list) and `/settings/integrations/quickbooks/conflicts/{id}` (resolution view). This is parallel to Flow 6's `/settings/integrations/calendar/conflicts/{id}` placement.

**IA Rationale**: Same logic as Flow 6 §1. QB conflicts are an integration concern; they live with the integration. Promoting them to top-level navigation would alarm new owners who would assume conflicts are common (they aren't, except briefly during heavy bookkeeping periods). The existing QuickBooks integration page already has tabs for Connection, Mapping, Sync log; Conflicts becomes a fourth tab.

**Difference from Tier 1 #1**: Mobile-conflict escalations live at `Dashboard > Approvals > Field issues` because they're operational (techs in the field). QB conflicts live at `Settings > Integrations` because they're integration-domain. The two surfaces are deliberately not co-located even though they share Flow 6's underlying pattern — owners reach for them from different mental models.

### 2. Conflicts list as a compact table with entity-type filter pills

**Decision**: The conflicts list renders as a paginated table with these columns:

| Entity | Type | Pilot change | QuickBooks change | Detail | Resolve |

- **Entity**: name/identifier of the conflicting entity ("Smith Construction LLC" for a customer; "INV-2026-0341" for an invoice; "Q-1024" for a quote)
- **Type**: pill — `Customer`, `Quote`, `Invoice`, `Expense`. Color-coded subtly to reinforce entity recognition.
- **Pilot change**: who, when, brief summary ("Mike updated address, 2 hr ago"; "Auto-generated from job completion, 4 hr ago")
- **QuickBooks change**: source label, when, brief summary ("via QB, 1 hr ago"; "QB user 'bookkeeper@…', 3 hr ago" if available from QB metadata)
- **Detail**: deep-link icon to the affected entity's detail page in Pilot (opens new tab, e.g., `/customers/{id}` or `/invoices/{id}`)
- **Resolve**: button → opens resolution view

A filter chip row above the table:
- **Entity type**: multi-select pills — `Customers (N)` `Quotes (N)` `Invoices (N)` `Expenses (N)` (counts shown only when non-zero)
- **Master**: optional pills — `Pilot is master` `QB is master` `User choice`. Useful when an owner wants to triage by who-decides-what.

Default sort: by **financial impact, descending then detection time descending**. Invoice and quote conflicts above customer and expense conflicts; within each group, newest-detected first. Sort toggles available on column headers.

**Rationale**: Calendar conflicts (Flow 6) sort by `scheduled_start_at` because the urgency is "what affects soonest." QB conflicts have no scheduled-time analog; the urgency is "what has the largest financial consequence if I get it wrong." Invoice conflicts >> Quote conflicts > Customer/Expense conflicts as a default urgency hierarchy. Owners who use Pilot as their primary accounting view want financial-impact-first; owners who use QB as their primary accounting view will likely have fewer conflicts surfaced here (because they edit QB-side).

### 3. Resolution view inherits Flow 6's two-column diff with master-aware column ordering

**Decision**: The resolution view is a focused single-conflict screen with two columns. Same routing posture as Flow 6 §4 — modal-feeling but URL-routed, bookmarkable, refresh-able.

**Master-aware column ordering**:

| Conflict type | Left column (master / read-leftward primacy) | Right column |
| :--- | :--- | :--- |
| Quote | Pilot | QuickBooks |
| Invoice | QuickBooks | Pilot |
| Customer | Pilot (default; tenant override flips) | QuickBooks |
| Expense | Pilot (default; tenant override flips) | QuickBooks |

The master side gets the leftward primacy slot — the side the eye reads first. This is a subtle UI signal that matches the policy decision without requiring the owner to read documentation. For Quotes and Invoices, the column ordering is fixed (Pilot is always master for Quotes; QB is always master for Invoices). For Customers and Expenses, the tenant has a per-entity-type "preferred master" setting that determines column ordering; default is Pilot-left.

**Rationale**: Flow 6 had no master-versus-master tension because Pilot was always the calendar master. QB has heterogeneous masters by entity. Putting the master on the left is a learnable visual convention that reduces cognitive load on the binary decision.

### 4. Field-level diff vocabulary inherits Flow 6 / Flow 5 — fifth reuse

**Decision**: Same field-level diff vocabulary as Flow 6 §5 (and Flow 5, Flow 7 §11, Tier 1 #1):

| Field state | Color | Treatment |
| :--- | :--- | :--- |
| Unchanged from baseline | Neutral | Plain text |
| Modified | Amber (alert palette) | Background tint, prior value as struck-through helper text |
| Added | Margin (green) | Background tint, "(added)" annotation |
| Removed | Fault (red) | Strikethrough, "(removed)" annotation |

**Baseline** for QB conflicts is `base_snapshot` — the last shared state at successful prior sync, stored in `integration_sync_conflict` per the §5.4 architecture extension. Same baseline semantics as Flow 6 §5.

**Rationale**: Fifth reuse of the track-changes pattern. At this point the pattern is so well-established that any deviation should require explicit justification rather than reuse. Owners who've encountered any prior conflict-resolution surface (Flow 5 quote approval, Flow 6 calendar, Flow 7 §11 mobile, Tier 1 #1 mobile escalations) transfer the visual grammar directly.

### 5. Bottom action bar is two big buttons; deletion-conflict treatment when needed

**Decision**: Same as Flow 6 §6 — two primary actions:

- **Use Pilot version** (variable position based on master per Decision 3) — primary indigo when Pilot is the master; secondary neutral otherwise
- **Use QuickBooks version** (variable position) — primary indigo when QB is the master; secondary neutral otherwise

Below: small text link "Resolve later." Header has back affordance to the conflicts list.

**Master-aware primary button treatment**: the master-side button gets the brand-indigo primary treatment; the non-master gets the neutral-with-brand-tinted-border secondary treatment. This reinforces the policy alignment without removing the alternative — the owner can always pick the non-master, but the visual default nudges toward the policy-aligned choice.

**Deletion-conflict variants** (Flow 6 §7 pattern applied to QB):

- **`Deleted in Pilot ↔ Modified in QB`**: "Pilot no longer has this customer. QuickBooks has updated their address. → [Restore the Pilot customer with QB's updates] or [Delete the QB customer too]"
- **`Modified in Pilot ↔ Deleted in QB`**: "QuickBooks no longer has this invoice. Pilot has invoice updates pending. → [Recreate the QB invoice from Pilot] or [Delete the Pilot invoice]"

Two-path verb-based decision; both paths preserve the recently-modified version. Same logic as Flow 6 §7.

**Rationale**: Same logic as Flow 6 — existence-level decisions need verb-based clarity. Master-aware primary button is a small visual nudge that helps owners without overriding their judgment.

### 6. Invoice-specific financial-delta callout

**Decision**: For invoice conflicts only, a financial-delta callout sits between the context header and the two-column diff. The callout shows:

- **Total amount delta**: "Pilot: $1,250.00 | QuickBooks: $1,287.50 | Δ +$37.50 (QuickBooks higher)"
- **AR impact preview**: "Customer Smith's AR balance will [increase $37.50 / decrease $X / be unchanged]" depending on which side gets accepted
- **Tax-period flag**: when the conflict spans a closed accounting period or crosses a tax filing boundary, an amber banner: "⚠ This invoice spans tax period [Q1 2026]. Resolution may affect filed returns. Consider consulting your bookkeeper."
- **QB transaction history link**: deep-link out to the invoice in QB's web UI (in a new tab) so the owner can verify the QB-side state and any related transactions before deciding.

**Rationale**: Calendar conflicts are mostly recoverable through normal flows (edit the event after resolution). Invoice conflicts have downstream financial consequences — AR balances, customer statements, period reporting, tax filing. The financial-delta callout makes those consequences visible at decision time, not afterward. The tax-period flag specifically calls out the highest-stakes case (resolution affecting an already-filed period) where the owner should pause and confirm with their bookkeeper.

**Scope deliberately limited**: this callout applies only to invoices. Customer and Expense conflicts have no financial-delta semantics (Customer field changes are non-financial; Expense delta is small and readable from the field-level diff directly). Adding callouts for those entity types would dilute the signal value of the invoice callout.

### 7. Pre-commit staleness check (the 409-and-refresh pattern)

**Decision**: When the owner clicks "Use Pilot version" or "Use QuickBooks version" (web), the API re-evaluates the conflict state before committing. If the underlying integration_sync_mapping or either side's version token has changed since the resolution view was rendered, the API returns 409 with the refreshed conflict payload. The web UI re-renders with a banner: "This conflict has been updated. Review and pick again."

This reuses Flow 6 §8's pattern; same payload shape; same banner copy.

**Auto-recovery scenario**: if the sync task processed a complete state-restoration on one side between conflict detection and owner viewing (e.g., the QB user reverted their change), the conflict auto-resolves and the owner sees a queue-level toast: "This conflict resolved itself before you got to it." This is the parallel to Tier 1 #1 Decision 6's `auto_recovered` 409 type, applied to QB.

**Rationale**: Sixth reuse of the staleness check pattern (Flow 6, Flow 7 §11, Tier 1 #1, plus implicitly inherited from Flow 5's quote approval edit-while-reviewing case). At this point it's platform vocabulary; any conflict-resolution surface uses it.

### 8. Voice scope: status query only; all resolution routes to web

**Decision**: Voice supports a single intent for QB conflicts:

**Status query** (`list_pending_qb_conflicts`):
- "Do I have any QuickBooks conflicts?" / "Any sync issues with QB?" → AI responds with count, entity-type breakdown, and brief urgency summary ("You have 4 — two invoice conflicts totaling about $200 in deltas, one customer address mismatch, and one quote update conflict.")

**No resolution intent in MVP**. All resolution paths route to web. AI responds to attempted voice resolution: "QuickBooks conflicts need the diff view to be safe — opening on web." A push notification with deep-link follows.

**Rationale**: This is the deliberate deviation from Flow 6 §11. The accounting-stakes asymmetry doesn't justify voice convenience for resolution. Customers might be a candidate for voice resolution (low stakes), but the operational cost of building one-entity-type voice support — and the user-confusion cost of "voice works for these conflicts but not those" — outweighs the convenience benefit at MVP scale. Phase 2 reconsiders based on operational data; the door is explicitly open in the §16 pattern entry.

**Voice intent registry update**: arch doc §6 adds `list_pending_qb_conflicts` (alongside the existing `list_pending_calendar_conflicts`). No `resolve_qb_*` intents.

### 9. Auto-expiry off by default; tenant opt-in per entity type with direction selection

**Decision**: Auto-expiry is **OFF by default for all QB conflict types**. Tenants can opt in per entity type via Settings (the actual Settings UI lands in Tier 2 #4); the per-entity opt-in includes a direction selector:

| Entity | System default | Tenant opt-in directions allowed |
| :--- | :--- | :--- |
| Customer | OFF | `accept_local` or `accept_remote` |
| Quote | OFF | `accept_local` recommended (Pilot is master) |
| Invoice | OFF | `accept_remote` recommended (QB is master) |
| Expense | OFF | `accept_local` or `accept_remote` |

When a tenant enables auto-expiry for an entity type:
- Default expiry interval: 60 days (longer than Flow 6's 30 — accounting periods are quarterly, so 60 ensures conflicts surface within at most one quarter)
- Pre-warning notification: 14 days before auto-resolution (longer than Flow 6's 7 — bookkeeping cadence is slower)
- Both intervals tenant-configurable, both nullable to disable pre-warning

**Rationale**: Calendar conflicts (Flow 6) have low recovery cost and a clear master, so silent fallback is safe. QB conflicts have higher recovery cost and heterogeneous masters; silent fallback is unsafe by default. Tenants who actively use the bi-directional sync and accept silent fallback (typically tenants using QB-side bookkeeping primarily) opt in. Tenants who prefer manual oversight (typical for Pilot-primary tenants) leave the default.

**Settings UI deferral**: the actual UI for this opt-in lands in Tier 2 #4 (Settings UIs for configurable thresholds). This spec only declares the policy and the data shape; the UI is part of the broader Tier 2 settings work.

### 10. Mobile owner status row + deep-link — already exists, parity confirmed

**Decision**: The QB sync mobile owner status row was established in Pass 2 §3.9 (mobile owner sees QB sync status with deep-link to web). This spec confirms parity with the calendar pattern from Flow 6 §10:

- **Healthy**: green dot, "QuickBooks sync · synced 5 min ago"
- **Pending conflicts**: amber dot, "QuickBooks sync · N pending conflicts," subtitle "Resolve on web →"
- **Connection error (token expired)**: red dot, "QuickBooks sync · reconnect needed → Settings"

Tapping the row deep-links to `/settings/integrations/quickbooks/conflicts` (mobile browser opens the conflicts list).

Push notifications fire when a conflict is first detected, rate-limited per A35 (existing infrastructure). Parallel to Flow 6 §10.

**Rationale**: Pattern parity between calendar and QB is intentional — owners should learn the integration-status grammar once. No design work needed here beyond confirming the row exists and behaves the same; pure pattern reuse.

### 11. Resolution is auditable but not undoable through this UI

**Decision**: When a conflict is resolved (web-only per Decision 8), the chosen version commits and pushes to the other side via the existing sync mechanism. There is no "undo resolution" button. Audit trail in `integration_sync_log` records the resolution decision, resolver identity, channel (always `web` since voice resolution isn't in MVP), pre-commit Pilot snapshot, pre-commit QB snapshot, and post-commit state.

**Rationale**: Same as Flow 6 §9 and Tier 1 #1 Decision 10. Undo competes with normal "edit the entity" flows. Audit preserves truth.

### 12. Empty state teaches normalcy

**Decision**: When there are no pending QB conflicts:

> **No QuickBooks conflicts.** Your data is in sync.
>
> *Last successful sync: 4 minutes ago. Next sync: in 11 minutes.*

A small expandable "Recent sync activity" panel below shows the last 10 successful sync cycles as a compact log (entity type, direction, count, timestamp). This is informational, not interactive.

A separate route at `/settings/integrations/quickbooks/conflicts/history` shows the historical archive of resolved conflicts with full filters (entity type, date range, master direction, resolver). Same pattern as Flow 6 §12 and Tier 1 #1 Decision 11.

**Rationale**: Empty state teaches normalcy (third reuse of this empty-state principle). Sync activity panel reassures owners that the integration is working when there's nothing to resolve. History route handles audit/investigation use cases.

## UX patterns established (for inheritance by future flows / Phase 2)

| Pattern | This spec | Inherits from |
| :--- | :--- | :--- |
| Track-changes diff vocabulary | Reused — fifth occurrence | Flow 5 → Flow 6 → Flow 7 §11 → Tier 1 #1 → here |
| Side-by-side two-column diff | Reused | Flow 6 §4 |
| Two-button bottom action bar with "Resolve later" | Reused | Flow 6 §6 |
| Deletion-conflict distinct verb-based treatment | Reused | Flow 6 §7 |
| Pre-commit staleness check | Reused — sixth occurrence | Flow 6 §8 (and others) |
| Modal-feeling but routed | Reused | Flow 6 §4 |
| Audit-but-no-undo | Reused | Flow 6 §9, Tier 1 #1 |
| Empty state teaches normalcy | Reused | Flow 6 §12 |
| Mobile owner status row + deep-link | Reused — third instance | Pass 2 §3.9, Flow 6 §10 |
| **Master-aware column ordering** | **NEW** | — |
| **Per-entity-type configuration overlay on the integration-conflict pattern** | **NEW** | — |
| **Financial-delta callout for entity-specific stakes (invoices)** | **NEW** | — |

Three small new vocabulary additions (all entity-specific extensions of existing patterns), nine reuses. Pattern density is even higher than Tier 1 #1 — this is intentional and validates that Flow 6's pattern generalizes.

## Cross-domain considerations

### A. The integration-conflict pattern is now official platform vocabulary

Flow 6 and Tier 1 #2 between them confirm that the bilateral integration-conflict pattern (queue list with detection-based sorting + side-by-side diff resolution view + two-button bottom action bar + pre-commit staleness check + auto-expiry with system-default-and-tenant-override + mobile owner status row + audit-but-no-undo) is reusable for any future bilateral integration. Phase 2 surfaces (Salesforce, HubSpot, generic webhooks) inherit this pattern by default; deviations require explicit justification.

The **arch doc §16 entry "calendar conflict resolution architecture"** should be renamed to "**bilateral integration conflict resolution pattern**" and refactored to describe the pattern abstractly with calendar and QB as the two reference instances. This is a §16 documentation update task for Tom (low effort; mostly renaming and minor restructure).

### B. The `integration_sync_conflict` schema extension is non-trivial but well-scoped

Per `mvp-arch.md` §5.4 ("**Pass 4 work required**"), the existing `integration_sync_conflict` table needs:
- `base_snapshot JSONB` — last shared state for accurate field-level diffs
- `field_diffs JSONB` — server-computed list of fields that differ (parallel to A32 from Flow 6)
- `expected_pilot_modified_at TIMESTAMPTZ` and `expected_remote_modified_at TIMESTAMPTZ` — added to the resolve endpoint for the staleness check (parallel to A33)
- `auto_expire_at TIMESTAMPTZ NULL` — when tenant opts in per Decision 9; nullable for the OFF-by-default case
- `pre_warning_at TIMESTAMPTZ NULL` — when tenant opts in
- `resolution_channel TEXT` — always `'web'` for MVP per Decision 8

Captured in A49 / A50 below.

### C. Configuration-class issues are explicitly out of scope; Phase 2 / onboarding handle them

Mapping ambiguities, tax agency lookup failures, and missing chart-of-accounts entries are not data conflicts — they're configuration health issues. They surface in two places:

- **During onboarding** (Tier 3 #10): the QB connection wizard walks the owner through initial customer mapping, tax agency setup, and account linkage. Ambiguities are resolved at setup time.
- **In a future "Setup health" surface** (Phase 2): a dedicated surface flags ongoing configuration drift (e.g., a new QB account category appears that doesn't have a Pilot mapping). Out of scope for MVP.

This Tier 1 #2 surface explicitly excludes configuration issues. The conflicts list filters them out (entity_type filter is the explicit allowlist of `customer`, `quote`, `invoice`, `expense`).

### D. Notification rate limiting via existing A35

QB conflict notifications use the same rate-limiting infrastructure as calendar conflicts (A35) and mobile escalations (A35 reuse in Tier 1 #1). The aggregation logic ("3 new QB conflicts in the last hour") works identically. No new infrastructure.

### E. Tenant sync_preference for Customer/Expense direction

Decision 3's "tenant override flips column ordering for Customer/Expense" requires a tenant-level setting. This setting already exists conceptually per `mvp-arch.md` §5.3 ("User choice (sync_preference)"); the actual settings UI lands in Tier 2 #4 alongside the auto-expiry opt-in. The conflict resolution view reads the current setting at render time.

### F. Auto-expiry deviation from Flow 6 — explicit and justified

Decision 9's OFF-by-default auto-expiry is a deliberate deviation from Flow 6's ON-by-default. Both decisions are correct for their domain. The §16 pattern entry needs to specify that auto-expiry default is *domain-determined*, not a fixed pattern attribute — calendar's master is unambiguous so ON is safe; QB's masters are heterogeneous so OFF is conservative. Future bilateral integrations should pick their default based on master clarity and recovery cost.

### G. Voice intent registry: only one new intent

Decision 8 adds `list_pending_qb_conflicts` to arch doc §6 voice intent registry. No `resolve_qb_*` intents in MVP. The Pass 4 close PRD update (v3.1) records this as a deliberate scope cut with rationale.

## Deferred items (Phase 2 / for future iteration)

- **Voice resolution for low-stakes QB entities** (Customers, Expenses) — Phase 2; reconsider based on operational data
- **Bulk resolution** — Phase 2; per-conflict only in MVP (same as Flow 6 §3)
- **Configuration health surface** — Phase 2; mapping ambiguities, tax agency lookup, account linkage drift
- **Owner-defined resolution rules** — e.g., "always accept QB version for invoices over $5,000" — Phase 2
- **Sync analytics dashboard** — conflict rate per entity type, average resolution time — Phase 2
- **Cross-conflict batch view** — when one logical change produces multiple related conflicts (e.g., a customer rename affects all their invoices) — Phase 2
- **Diff-aware merge** — owner picks Pilot's name + QB's address rather than full-side-or-other — Phase 2
- **Customer-specific direction override** — tenant has Pilot-default for customers but wants QB-default for one specific customer — Phase 2
- **Reverse-sync verification** — after resolution, verify the push-to-other-side actually committed — Phase 2 (MVP relies on existing sync log)

## Validation checklist

Before implementation begins:

- [ ] Dev team aligned on `Settings > Integrations > QuickBooks` four-tab structure (Connection, Mapping, Sync log, Conflicts)
- [ ] Web routing structure committed: `/settings/integrations/quickbooks/conflicts` + `/{id}` + `/history`
- [ ] A49 endpoints specified (queue list with entity-type and master filters, conflict detail, history list)
- [ ] A50 endpoints specified (resolve write path with pre-commit staleness check, three 409 payload types, audit log)
- [ ] `integration_sync_conflict` schema extension committed (base_snapshot, field_diffs, expected_*_modified_at, auto_expire_at, pre_warning_at, resolution_channel)
- [ ] Master-aware column ordering logic specified per entity type (read tenant `sync_preference` for Customer/Expense)
- [ ] Invoice financial-delta callout backend computation specified (delta amount, AR impact preview, tax-period detection, QB deep-link URL builder)
- [ ] Auto-expiry default OFF for all entity types confirmed with dev team; per-entity opt-in data model specified
- [ ] Voice intent `list_pending_qb_conflicts` added to arch doc §6 registry
- [ ] Mobile owner "QuickBooks sync · N pending conflicts" status row code path tested for parity with calendar pattern
- [ ] Notification rate limiting (A35) tested for QB-conflict aggregation
- [ ] Configuration-class issues explicitly excluded from queue (entity_type filter is allowlist, not denylist)

## Backend additions (new for Tier 1 #2)

### A49. QuickBooks Conflict Queue Endpoints

**Triggered by**: Decisions 1, 2, 12 — queue list with filters, conflict detail with master-aware payload, history archive.

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

### A50. QuickBooks Conflict Resolution Write Path

**Triggered by**: Decisions 5, 7, 11 — resolution commit with pre-commit staleness check, three 409 payload types, audit log capture.

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
  - Insert `integration_sync_log` entry capturing `conflict_id`, `resolver_user_id`, `resolution_action`, `resolution_channel` (always `'web'` for MVP), `pre_commit_pilot_snapshot`, `pre_commit_qb_snapshot`, `post_commit_state`, `resolved_at`

**Auto-expiry Celery task extension**:
- Existing pattern from A34 (Flow 6's calendar auto-expiry) extends to QB
- New Celery Beat task `auto_expire_qb_conflicts_per_tenant` runs hourly
- For each conflict where `auto_expire_at <= now()`, commits the tenant-configured direction
- Pre-warning task fires `notification_outbox` entry at `pre_warning_at`

**Effort estimate**: Medium — 4–5 days. The variation across entity types and resolution types is the main cost (each entity needs domain-specific commit logic). Auto-expiry Celery extension is small additional work.

---

## What this surface does NOT cover

- **Configuration-class conflicts** (mapping, tax agency, account linkage) — Phase 2 / handled in Tier 3 #10 onboarding.
- **Payment conflicts** — impossible per §5.3 (one-way QB→Pilot).
- **Tax Component conflicts** — impossible per §5.3 (one-way Pilot→QB).
- **Voice resolution intents** — explicit MVP scope cut per Decision 8.
- **Bulk operations** — Phase 2 (same as Flow 6 §3).
- **Settings UI for auto-expiry opt-in** — Tier 2 #4 (Settings UIs for configurable thresholds).
- **The "QuickBooks setup health" surface** — Phase 2 separate spec.

## Next: Tier 1 #3 — Background Sync for Mobile

Tier 1 #3 closes Tier 1 with mostly architectural design and a thin UI surface. The scope:
- Push token registration on app launch
- Silent push handling for sync triggers when app is backgrounded
- Background sync session management with state persistence
- iOS background task constraints (limited CPU time, scheduled execution windows)
- Android background scheduling (WorkManager + Doze mode considerations)
- The thin UI surface: a settings toggle "Background sync on" (default ON), a status indicator on the existing Flow 7 sync queue surface showing "last background sync attempt: X ago," and any new mobile owner status row updates needed to reflect background sync health

After Tier 1 #3 locks, Tier 1 closes with three deliverables (mobile-conflict UI, QB conflict UI, background sync) and Tier 2 begins with the Settings IA framework doc as prerequisite.

The framework doc estimated A51 for background sync (renumbering the framework's A50). Cumulative additions through Tier 1: A47 (mobile-conflict queue), A48 (mobile-conflict resolve), A49 (QB conflict queue + schema extension), A50 (QB conflict resolve + auto-expiry), A51 (background sync infrastructure). Five additions across three surfaces, ~22–28 days of backend work for Tier 1 total.
