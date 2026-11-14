# Pilot for Trades Design System — Pass 3, Flow 2: Real-Time Job Profitability

**Version**: 1.0
**Status**: Locked
**Date**: April 25, 2026
**Scope**: Web-based profitability reporting with live job tracking and closed-period analysis
**Depends On**: Pass 1 (tokens), Pass 2 (IA), PRD §3.4 (Field Operations), PRD §3.10 (Sales & Quoting), PRD §3.6 (Invoicing & Billing)
**Backend Reference**: A5 (Reports + Dashboard), new A14 (ETC capture system), new A15 (chart-threshold tenant settings), new A16 (variance notification settings)

---

## Purpose

Flow 2 delivers Pilot's owner value proposition in concrete form: the ability to see, *while jobs are still in progress*, which ones are drifting below margin target — and learn from closed-period results. This is the report that justifies the subscription. Every prior contractor SaaS shows revenue and accounting; Pilot shows profitability as an operational signal.

This spec documents the locked design for Pass 3 Flow 2 after iteration on chart-vs-table thresholding and the introduction of a structured ETC (Estimate to Complete) capture system.

## Strategic Direction

### Two distinct surfaces, one page

The Profitability page presents two related but distinct surfaces:

1. **Live jobs** — currently open jobs with activity. Shows projected final margin based on actuals plus tech ETC. Answers "what should I worry about right now?"
2. **Closed in period** — jobs that closed within the selected timeframe. Shows realized margin distribution. Answers "how did we actually do?"

These are two different mental models (current attention vs. retrospective analysis) and the page explicitly separates them rather than blurring them.

### The chart-or-table decision is data-driven

For both sections, the page renders charts when the job count meets a tenant-configurable threshold (default 8). Below that, it shows a table. This isn't aesthetic — it's correctness. A bar chart with two bars communicates nothing useful and looks broken.

### Period scope and bucketing

- Default period: **last 30 days** (rolling, not month-to-date)
- Period selector: 7d / 30d / MTD / YTD / Custom
- Job inclusion in default view: **closed-in-last-30-days + open jobs with activity**
- Period attribution for closed jobs: **close date** (matches small-contractor mental model)

## Locked Design Decisions

### 1. Live Jobs Section Leads the Page

**Decision**: Live jobs section appears above closed-period section. Cannot be reordered.

**Rationale**: Live jobs are actionable now. Closed jobs are reflective. Putting the actionable thing above the reflective thing matches what the owner is opening this page to do most of the time.

### 2. Live Jobs: Open With Activity Only

**Decision**: The default live jobs view includes only open jobs that have at least one logged time entry or expense. Open jobs with zero activity (just-scheduled, not started) are excluded.

**Rationale**: Profitability requires actuals. Open jobs with no activity are pure estimates from the quote — they're either healthy or they're not, but there's nothing to monitor. Including them dilutes the signal. Pipeline view (open + scheduled but not started) is a separate Phase 2 surface.

### 3. Closed Jobs: Bucketed by Close Date

**Decision**: For period attribution, a closed job belongs to the period in which it closed (`closed_at` falls within the selected range). The job's full margin lands entirely in that period. No work-in-progress allocation across multiple periods.

**Rationale**: Matches how small contractors think — "we made X on the Johnson job in April." Avoids the complexity of percentage-of-completion accounting that the audience neither expects nor benefits from. Owners who need cost-tracking-per-period get that from a separate "cost activity" report (Phase 2).

### 4. Four Margin Buckets, Tenant-Configurable Boundaries

**Decision**: Default buckets are Below 10% (red), 10–20% (amber), 20–30% (green), 30%+ (deep green). Tenant can override boundaries. Tenant can also override the target line (default 20%, used for "below target" indicators).

**Rationale**: Margin expectations vary by trade and business model. Residential service work expects 20–25%; commercial bid work expects 8–15%. Hardcoding boundaries makes the color coding meaningless for tenants outside the default profile. Configurability respects business diversity.

**Implementation**:
- Tenant setting: `margin_bucket_boundaries` — array of percentages (default `[10, 20, 30]` produces four buckets)
- Tenant setting: `margin_target_pct` — single percentage (default `20`)

### 5. Two Bar Charts Tell the Weighting Story

**Decision**: Below the metrics row, two bar charts side by side: "Jobs by margin" (count) and "Revenue by margin" (dollars). Same buckets, same colors. Both are interactive — clicking a bar drills into the underlying jobs.

**Rationale**: Either chart alone misleads.
- Count alone: "I have 2 jobs below 10%" — but are those small or large?
- Revenue alone: "$8K below 10%" — but is that one disaster or many small ones?
- Together: the relationship between count and weight tells the operational story. If 11% of count represents 9% of revenue, exposure is proportional. If 11% of count represents 25% of revenue, a small number of big jobs are the concentrated risk.

This achieves the weighting that a scatter plot would convey, in a form non-technical small-business owners can read at a glance.

### 6. Chart-Threshold Pattern (Single Setting, Both Sections)

**Decision**: A single tenant-configurable threshold determines whether each section shows charts or a table. Default: 8 jobs. Below threshold → table. At or above → charts (with optional drill-back-to-table via collapsible section).

**Rationale**: Charts with 1–4 bars are useless and look broken. Tables work fine at any volume. A single threshold applied consistently across both sections makes the page's behavior predictable. The collapsible "Show all jobs as a table" inside the chart view preserves access to the row-level data.

**Implementation**:
- Tenant setting: `report_chart_threshold` — integer (default `8`)
- Applied independently to live count and closed count: a tenant could see charts in closed (24 jobs) but a table in live (4 jobs) within the same period

**Below-threshold table notice**: when a section falls back to table view, a small inline note explains: "Charts appear when 8+ jobs are in scope. Adjust threshold in Settings → Reports." This makes the system's logic visible rather than hidden.

### 7. Drill-Down Pattern: Click Bar → See Jobs

**Decision**: Clicking any bar in the closed-period charts opens an inline drill-down panel below the charts, showing the jobs in that bucket with their close dates, revenue, and margins. The bar shows an active state (outlined) while its drill-down is open. Closing the drill-down clears the active state.

**Rationale**: Drill-downs as inline panels (rather than modals or page navigation) preserve context — the owner sees the chart and the underlying data simultaneously. Closing returns them to the chart without losing their place. Modals would steal focus and break the scanning flow.

**Live jobs drill-in**: clicking a live job row navigates to the job detail page with margin decomposition. Out of scope for this flow; will be detailed in a future flow (likely Pass 3.5).

### 8. Hot Indicator on Below-Target Live Jobs

**Decision**: Live jobs with projected margin below the tenant's target margin show a red dot indicator next to the job name and have a subtle red row tint.

**Rationale**: At-a-glance scannability. An owner with 12 live jobs needs to spot the troubled ones in 2 seconds. The red dot is small enough to not dominate but distinctive enough to draw the eye. Row tint adds peripheral signal for someone scanning quickly. Combined, they answer "where are my problems?" without requiring the owner to read margin numbers.

### 9. Progress Bar Reflects Projected Hours, Not Quoted Hours

**Decision**: The progress bar in the live jobs table uses the formula `hours_worked_so_far / (hours_worked_so_far + hours_remaining)`. This always renders 0–100% and is based on the tech's most recent ETC.

**Rationale**: Naive "% of quoted hours consumed" can exceed 100% when a job runs over, which breaks visual scaling and undersells severity. Using `worked / (worked + remaining)` is always 0–100% and reflects current reality from the tech's perspective.

**Over-quote indicator**: when `hours_worked + hours_remaining > original_quoted_hours`, the progress bar fills with red and the percentage value gets a warning glyph. This visually distinguishes "the tech thinks we'll go over the original commitment" from a healthy in-progress signal.

### 10. ETC (Estimate to Complete) System — Major New Capability

**Decision**: Time entries on mobile capture two values per entry: hours worked (existing) and hours remaining (new). The system uses the most recent ETC per labor line for projected margin calculation.

This is a significant new capability spanning mobile UX, backend, and reporting. Detailed below in its own section.

#### 10a. ETC Granularity

**Per labor line when quote is line-itemized**: if the quote breaks labor into multiple lines (rough-in, trim-out, finish), each line tracks its own ETC. The tech's ETC entry is for the specific task they're working on.

**Per job when quote labor is single-line**: if labor is quoted as one aggregate line, ETC is captured per job. Coarser signal, but appropriate for the simpler quote structure.

**Implementation**: ETC stored on `job_time_entry` table with optional `quote_line_id` reference. Latest-ETC query uses MAX(created_at) per (job_id, quote_line_id) tuple.

#### 10b. ETC Capture Triggers

**Two triggers, captured at the moment information is freshest**:

1. **End-of-day clock-out** — when a tech ends their workday (final clock-out before going home), the mobile app prompts for ETC on each job they worked on that day. Required.
2. **Mid-day task completion** — when a tech marks a labor line as complete (e.g., finished the rough-in, moving to trim-out), the mobile app prompts for ETC on the *next* labor line they're starting. Required.

**Not a trigger**: brief pauses (lunch, equipment runs, intra-task clock-outs). Asking for ETC on every clock-in/out adds friction without information value.

#### 10c. ETC Auto-Population With Override Pattern

**Decision**: When the ETC prompt appears, the field is auto-populated with `quoted_hours - (prior_logged_hours + just-entered_hours)`. The tech can:

- **Tap "Confirm" without changing the value** — one-tap acknowledgment that the quote is on track. No note required.
- **Modify the value upward** (job will take longer than quoted) — note required.
- **Modify the value downward** (job will close faster than quoted) — note optional.
- **Modify within ±N%** of auto-populated value (tenant-configurable, default 10%) — note optional regardless of direction.

**Rationale**: Auto-populate matches the on-track expectation; one-tap confirmation when nothing's wrong respects field friction. The asymmetry on overrides reflects what the owner actually needs to know. An owner doesn't need an explanation for being ahead of schedule. They do need an explanation when work is taking longer — that's the moment a problem becomes visible, and the tech's reasoning becomes valuable structured data.

**Implementation**:
- Tenant setting: `etc_variance_note_required_pct` — default `10` (percent change at which note transitions from optional to required when increasing)
- Note required logic at API: `change_pct = (override_value - autopopulated_value) / autopopulated_value`. Note required when `change_pct > etc_variance_note_required_pct / 100`.

#### 10d. Owner Notification on Major Variance

**Decision**: When a tech's ETC pushes projected total hours over a tenant-configurable threshold (default 50% over original quoted hours), the owner receives a push notification + email immediately. This is independent from the note-required logic — it triggers based on impact, not direction of change.

**Rationale**: Some variances are too significant to wait for the owner to discover via the dashboard. A 50%+ over-quote on labor is a "we're definitely going to lose margin on this" signal, and the owner can intervene while the job is still active (re-scope with the customer, get a change order signed, redirect resources).

**Implementation**:
- Tenant setting: `etc_variance_owner_notify_pct` — default `50` (percent over original quote at which notification fires)
- Comparison: `(current_projected_total_hours / original_quoted_hours) - 1`. Notify when `> etc_variance_owner_notify_pct / 100`.
- The comparison reference is the *original quote*, not the auto-populated value at the moment of override. The notification is about "is the job going significantly over commitment?" not "did this single entry change a lot?"

### 11. Three Metric Cards Above Closed Charts

**Decision**: Above the closed-period charts, three large-number metric cards: Revenue, Profit, Avg Margin. Each shows period-over-period delta.

**Rationale**: For owners who want the 2-second answer ("am I on track?"), the metric cards deliver it without parsing the charts. The deltas convert numbers to direction — "up $4,860 vs prior 30 days" tells more story than "$47,240."

### 12. Pin to Dashboard

**Decision**: Single "Pin to dashboard" button in the page header. Clicking adds the page's summary cards as widgets to the Dashboard overview. Toggle state shows pinned/unpinned. (See A5 in backend additions for dashboard widget infrastructure.)

**Rationale**: Page-level pinning is sufficient for MVP. Per-chart pinning is more granular but adds UX complexity (which charts? how do they fit in dashboard layout?) — defer to Phase 2.

## UX Patterns Established (Inherited by Future Reports)

Flow 2's design becomes the template for:

| Pattern | Reuse |
| :--- | :--- |
| Period selector (7d / 30d / MTD / YTD / Custom) | Every reports surface |
| Chart-or-table threshold | Every count-based reporting view |
| Tenant-configurable bucket boundaries | Any health-categorized report |
| Drill-down as inline panel | All chart-based reports |
| Three-metric-card row above charts | Dashboard widgets, top-of-page summaries |
| Hot indicator on exception rows | Any list view with health categorization |
| Pin-to-dashboard at page level | Every report and analysis surface |

Subsequent reports flows (revenue, AR aging, tech productivity, tax liability, voice analytics) will consume these patterns.

## Deferred Items (For Future Iteration)

- **Live job drill-in** (job detail page with margin decomposition) — Pass 3.5 candidate
- **Pipeline view** (include open jobs with no activity yet) — toggle, Phase 2
- **Custom date range picker** UX — placeholder pill exists, full design Pass 3.5
- **Margin bucket configuration UI** — link exists, design when we tackle Settings flows
- **Per-chart pinning** — Phase 2
- **Multi-period comparison** (overlay last 30d vs prior 30d as ghost bars) — Phase 2
- **Export to CSV / PDF** — Phase 2
- **Tech-level filter** (show only Mike's jobs) — Phase 2
- **Customer-level filter** (show only commercial customers) — Phase 2
- **Job type segmentation** (residential vs commercial vs service) — Phase 2

## Validation Checklist

Before implementation begins:

- [ ] Dev team aligned on the live-vs-closed model and close-date period attribution
- [ ] ETC capture triggers reviewed against existing time-entry mobile flow (any conflicts?)
- [ ] Override note logic reviewed against existing audit trail patterns
- [ ] Owner notification path uses existing notification_outbox + push infrastructure (yes, per Pass 2 A4)
- [ ] Tenant settings additions cataloged in Settings UI roadmap
- [ ] Dashboard widget rendering supports the three metric cards + pinned-page-summary pattern
- [ ] Performance review: chart aggregation queries against expected data volumes (10K+ jobs per tenant per year)

## Next: Pass 3 Flow 3

Recommended next: **tech-to-customer templated communications**. Reasons: extends voice patterns established in Flow 1 (the templated-message dispatch is voice-triggerable), exercises the notification infrastructure from Pass 2 A4, and is a relatively contained design surface compared to dispatch board or quote approval. Quick win that reinforces the platform's voice-first positioning before we tackle the more complex governance flows.

Alternative candidates if you'd rather: dispatch board interactions (newest domain, freshest in our heads), quote approval workflow (closes the governance loop), or the offline sync flow (hardest, best saved for last).
