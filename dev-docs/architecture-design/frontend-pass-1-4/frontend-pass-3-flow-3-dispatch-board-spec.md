# Pilot for Trades Design System — Pass 3, Flow 3: Dispatch Board

**Version**: 1.0
**Status**: Locked
**Date**: April 25, 2026
**Scope**: Web-based dispatch board for scheduling jobs across techs and time
**Depends On**: Pass 1 (tokens), Pass 2 (IA), PRD §3.14 (Scheduling & Dispatch), `mvp-arch.md` §13 (Scheduling Architecture), `scheduling-dispatch-db-schema.md`
**Backend Reference**: A1 (Scheduling, implemented), with potential additions noted in this spec

---

## Purpose

Flow 3 designs the primary scheduling interface for Pilot — the surface where the owner (or designated dispatcher) plans the day's work, assigns techs to jobs, and resolves conflicts before they impact field operations. The dispatch board is the operational counterpart to the profitability report: profitability tells the owner how things are going, the dispatch board lets them act on it.

This is the most interaction-dense surface in the MVP. Every other web surface is read-heavy with limited interaction; the dispatch board is action-heavy with continuous spatial manipulation.

## Strategic Direction

### Familiarity over novelty

The dispatch board adopts the Google Calendar interaction grammar verbatim: tab-based time scale (Day, 4-Day, Week, Month), date navigation (prev / next / today), grid layout (time on Y-axis, resources on X-axis), and drag-to-reschedule. Owners already know how this works. Inventing a new pattern would force every owner to learn Pilot's calendar metaphor before being productive.

The novelty lives in what's underneath: real-time conflict detection, drive-time awareness, projected margin, voice control, and integration with quote acceptance and tech assignment workflows. The chrome is familiar; the engine is new.

### Filters as a calendar abstraction

Borrowing Google's "calendars in the sidebar" pattern, Pilot presents jobs grouped by attribute (tech, status, customer type, job type, priority) rather than as a flat unscheduled list. The owner toggles checkboxes to filter the visible set. This lets a single sidebar serve multiple workflows: "show me only Mike's day," "show me only commercial customers," "show me only rush jobs."

### Conflicts handled by class, not uniformly

We identified four conflict classes during design (overlap collision, availability violation, drive-time infeasibility, secondary warnings). Each gets UI treatment proportional to its severity. Hard conflicts (overlap) block the action; soft conflicts (availability, drive time) allow override; informational signals (site closed, long route) appear as subtle indicators.

## Locked Design Decisions

### 1. Time Scale Tabs: Day / 4-Day / Week / Month

**Decision**: Four tabs at the top of the dispatch board, mirroring Google Calendar exactly.

- **Day**: full hour-by-hour grid, all techs as columns. Default view.
- **4-Day**: rolling four-day horizontal view. Useful for "rest of this week" planning.
- **Week**: Monday–Sunday horizontal view.
- **Month**: month-grid summary cells (count of jobs per day, color-coded by load). Used for navigation only — clicking a date drops into Day view for that date.

**Rationale**: Google Calendar parity reduces learning curve. Day is the operational view; Month is the navigational view; Week and 4-Day are the planning views in between.

**Year view explicitly excluded from MVP**. Small contractors don't plan a year out at the calendar level.

### 2. Tech Rows × Time Columns Grid

**Decision**: In Day view, the grid renders as rows of hours (60px per hour) with columns of techs. Each cell is a (tech, time-slot) intersection where jobs are placed.

**Rationale**: This is the established dispatching layout — used by ServiceTitan, FieldEdge, Jobber, and every other field service product. Inventing an alternative (e.g., gantt-chart style with techs as rows and time horizontally) would confuse experienced dispatchers transferring from incumbents.

**Hour range**: 6 AM – 7 PM by default, scrollable to extend. Tenant-configurable. Most service work happens within this range; covering outliers as scroll rather than always-visible keeps grid density manageable.

### 3. Filter Sidebar with Five Groupings

**Decision**: Left sidebar with five filter groupings, all visible from MVP day one:

1. **Tech** — checkbox per active tech, color-coded
2. **Status** — Unassigned, Scheduled, In progress, Confirmed
3. **Customer** — Commercial, Residential (and any tenant-defined customer segments)
4. **Job type** — Service calls, Installs, Inspections (tenant-configurable)
5. **Priority** — Rush, Standard, Warranty

Each filter shows a count of matching jobs.

**Rationale**: Filters are checkboxes with trivial implementation cost. Shipping all five from launch is faster than guessing which ones owners will want and adding the rest in v2. The "I don't need these" complaint is a configuration affordance, not a feature reduction.

**Filter behavior**: pure visibility filtering. Hidden items remain in the database with their assignments intact; they simply don't render. Drag-and-drop targets only what's visible. This matches Google Calendar's "uncheck to hide" model and avoids the much trickier "unassign on hide" semantics.

### 4. Tech Color Coding

**Decision**: Each tech is assigned a color from a palette of 8–12 distinct hues. Color appears in:
- Sidebar filter dot
- Grid header avatar
- Job block left border (3px accent)
- Job block background tint (~10% opacity of tech color)

**Rationale**: Color is the primary visual encoding for "whose job is this." Critical for week and 4-day views where columns aren't necessarily organized by tech. The 3px left-border accent on job blocks gives the color sufficient visual weight to scan quickly without overwhelming the block content.

**Palette**: derived from the brand color ramps in Pass 1, expanded with additional hues for tenants with 4+ techs. Tenant-configurable per tech in settings.

### 5. Drag-and-Drop Mechanics

**Decision**: Three drag operations, all directly on the grid:

1. **Drag a job vertically within its tech column** → reschedule to a different time
2. **Drag a job horizontally between tech columns** → reassign to a different tech
3. **Drag the bottom edge of a job block** → resize duration (extend or shrink)

**Visual feedback during drag**:
- The block becomes semi-transparent at its origin
- A ghost block follows the cursor
- Drop targets highlight as the cursor moves over them
- Conflict indicators appear in real-time on the ghost block

**Rationale**: All three operations are continuations of the same direct-manipulation idiom. Every other dispatch tool has converged on this; deviating would be perverse.

### 6. Conflict Behavior — Differentiated by Class

**Decision**: Four distinct conflict/warning classes, each with proportional UI treatment.

| Class | Behavior | Trigger |
| :--- | :--- | :--- |
| **Overlap collision** | Blocked. Drag snaps back. Toast: "[Tech] is already on [other job] from X–Y. Move that one first or reassign this." | Two assignments to the same tech with overlapping time |
| **Availability violation** | Warn-with-override. Toast: "[Tech]'s working hours are X–Y. Reassign anyway?" Owner clicks confirm. | Job placed outside tech's working hours, in PTO, or in unavailable block |
| **Drive-time infeasibility** | Warn-with-override. Inline drive-time marker between consecutive jobs renders red and labeled "tight" or "infeasible." | Required drive between consecutive stops can't fit in scheduled gap |
| **Site closed / long route** | Subtle indicator on job block. No friction. | Site has hours outside scheduled time, or tech's day total exceeds threshold |

**Why differentiated**: a single uniform "warn on everything" pattern produces alert fatigue — owners learn to ignore warnings. A single uniform "block on everything" produces frustration — owners overrule the system in legitimate cases (rush call into Saturday, rush drive between two stops). Differentiation respects what's actually impossible vs. what's merely unwise.

**The block-on-overlap case is the only hard rule**: assigning the same tech to two overlapping jobs is logically inconsistent at the data level and should never be permitted. Even voice commands and API calls must respect this. Every other rule allows override because business judgment legitimately exceeds the system's awareness.

### 7. Drive-Time Markers Between Consecutive Jobs

**Decision**: Between two consecutive jobs assigned to the same tech, a horizontal dotted line renders with the drive-time label inline ("12 min", "8 min"). When the drive time is infeasible (next job starts before this drive could complete), the marker turns red and the label includes a warning ("18 min · tight" or "45 min · infeasible").

**Rationale**: Drive time is a critical scheduling input for field service that no incumbent surfaces in the dispatch view. Owners currently calculate it mentally or in a separate map app. Showing it inline turns "infeasible" from a discovery-after-the-tech-calls-stuck-in-traffic into a planning constraint.

**Computation**: triggered by the map provider (Google Maps Distance Matrix API per `mvp-arch.md` §13). Cached for 24h on (origin, destination, hour-of-day) tuple. Recomputed when a job is moved or its site changes.

### 8. Availability Visualization

**Decision**: Tech columns visually mark working hours and unavailable periods:
- **Inside working hours**: white background with horizontal hour lines
- **Outside working hours**: light gray fill with "OFF" label centered
- **PTO**: diagonal striped pattern with "PTO" label

**Rationale**: Owners need to see when a tech is and isn't available without reading the sidebar. Visual zoning makes legitimate scheduling slots obvious; placing a job into a gray zone is the moment availability conflicts surface.

### 9. Now-Line (Current Time Indicator)

**Decision**: A horizontal red line spans all tech columns at the current time. Updates every minute. Visible only on Day, 4-Day, and Week views (not Month).

**Rationale**: Standard calendar convention. Tells the owner "where are we right now" at a glance. Critical for in-progress dispatching ("can we still get Mike to the next stop on time?").

### 10. Voice Integration

**Decision**: A "Voice" button in the top-right of the dispatch board opens the conversational voice interface from Flow 1, scoped to scheduling intents. The same `voice_action_router.py` handlers (`schedule_job`, `reassign_job`, `reschedule_job`) drive voice-initiated changes. The dispatch board updates in real-time as voice commands resolve.

**Voice conflict behavior**: voice commands respect the same four-class conflict logic. Overlap collisions block (voice responds: "Luis is already on Williams panel at that time — should I reschedule Williams instead?"). Other conflicts warn (voice responds: "That puts Luis outside his working hours — should I do it anyway?").

**Rationale**: The dispatch board and voice are alternative manipulation modes for the same underlying data. Owners should be able to drag a job, voice-command a job move, or have a tech voice-command a reschedule from the field — all converging on the same scheduling state.

### 11. Calendar Sync Status Indicator

**Decision**: A small status indicator in the top bar shows calendar sync state:
- **Green dot + "synced"** with last-sync timestamp — normal
- **Amber dot + "syncing"** — sync in progress
- **Red dot + "sync error"** with link to resolve — needs owner attention

**Rationale**: Bi-directional calendar sync (per `mvp-arch.md` §13.5) means changes can come from outside Pilot. Owners need to know whether the board they're looking at reflects the latest external calendar state. Visible health beats invisible silence.

### 12. Bottom Info Bar

**Decision**: A condensed info bar below the grid shows: techs working today, jobs scheduled, drive-time warnings count, conflicts blocked count, last-updated timestamp.

**Rationale**: At-a-glance health summary for the owner. Gives the day's shape in one glance without scanning the whole grid. The "conflicts blocked" count is particularly useful — it tells the owner "you tried 3 things the system rejected today, you might want to look at why."

### 13. Job Block Content Hierarchy

**Decision**: Job blocks display, in order of visual weight:
1. **Job title** (e.g., "Johnson — 200A panel upgrade") — largest, bold
2. **Customer + site** (e.g., "Tom Johnson · 42 Oak St") — secondary
3. **Time range** (e.g., "8 AM – 11 AM") — tertiary
4. **Tags** (Rush, Warranty, Drive-time warning) — top-right, color-coded

When the block is too short to show all four, content gracefully truncates: time range disappears first, then customer/site, leaving title + tags.

**Rationale**: Title is what the dispatcher mentally references jobs by. Customer/site disambiguates jobs with similar titles. Time is computed information that's also visible from grid position. Tags are exception signals.

### 14. Month View as Pure Navigation

**Decision**: Month view shows a calendar grid with each day as a cell. Cell content: day number, total job count, mini bar indicating capacity (color shifts from green → amber → red as load increases). Clicking a day drops into Day view for that date. No drag-and-drop in Month view.

**Rationale**: Month view's job is to support "how busy is next Tuesday?" planning, not job-level manipulation. The grid would be too dense to interact with. Treating Month as navigation keeps it useful and fast.

## UX Patterns Established (Inherited by Future Flows)

Flow 3's design becomes the template for:

| Pattern | Reuse |
| :--- | :--- |
| Google Calendar grammar (Day/4-Day/Week/Month tabs) | Any time-based view |
| Filter sidebar with grouped checkboxes | Reports filtering, customer list filtering |
| Color coding by entity (tech, customer) | Anywhere multiple entities coexist visually |
| Differentiated conflict severity | All write surfaces with validation |
| Inline status indicators (sync, voice activity) | All long-running async operations |
| Voice-as-secondary-input | Any complex interaction surface |

## Cross-Domain Considerations Surfaced

Designing this flow surfaced several questions that touch other domains. Captured here for the dev team review.

### A. Tech assignment for unassigned jobs is a separate flow

The dispatch board shows an "Unassigned" status filter, but the design doesn't specify where unassigned jobs come from or how they reach the board. They originate from accepted quotes (per the existing quote → job conversion flow) and inherit no tech by default. The owner uses the dispatch board to assign them.

**Open question for dev team**: should accepted-quote-becomes-job auto-place the new job on the dispatch board (in an "Unassigned" virtual column), or does the dispatch board need a separate "Unassigned queue" panel that the owner pulls from? My instinct is the former — virtual unassigned column on the right edge of the grid in Day view. Specced this way going forward unless the team prefers otherwise.

### B. The filter sidebar's customer and job-type filters may need configuration UI

Tenants will define their own customer segments and job types. The filter sidebar reads from those tenant-specific values. Settings UI for managing these is needed. **Captured as a Pass 4 deferred item** rather than blocking Flow 3.

### C. Drive-time computation cost

Per `mvp-arch.md` §13.8, Distance Matrix API costs scale with usage. The dispatch board recomputes drive times on every drag operation. Need to verify the caching strategy actually holds — if the owner drags a job around the grid 10 times before settling, that should not be 10 distance-matrix API calls. Caching by (origin, destination, hour-of-day) handles this, but the cache TTL of 24h means same-day drag operations are free after the first compute. **Worth confirming with dev team that this caching is wired correctly.**

### D. Real-time updates from external calendar

If a Google Calendar event is added/modified by the owner outside Pilot, the next pull cycle (every 5 minutes per spec) brings it into the dispatch board. The board should refresh smoothly when this happens — not a hard reload, but an animated update of the affected cells. **Captured as a Pass 4 polish item.**

## Deferred Items (For Future Iteration)

- **Resize-by-drag-edge** — visually present in spec but interaction is stubbed in prototype
- **Unassigned queue panel** vs. virtual column — open question for dev team
- **Customer/job-type filter configuration UI** — Pass 4 (Settings flows)
- **Real-time external calendar update animation** — Pass 4 (polish)
- **Multi-select drag** (drag multiple jobs at once) — Phase 2
- **Recurring job creation flow** — Phase 2
- **Skill-based routing** (auto-suggest the right tech for a job type) — Phase 2
- **Mobile dispatcher view** — Field Mode for owners on tablets handles initial need; full mobile dispatch is Phase 2

## Validation Checklist

Before implementation begins:

- [ ] Dev team aligned on the four conflict classes and their differentiated UI behaviors
- [ ] Drive-time caching strategy reviewed against drag-frequency expectations
- [ ] Color palette for tech assignment finalized (8–12 distinct hues, accessible contrast)
- [ ] Voice intent handlers (`schedule_job`, `reassign_job`, `reschedule_job`) confirmed to respect conflict-class logic
- [ ] Tenant configuration plan for grid hour range, working hour defaults, color assignments
- [ ] Real-time update strategy from calendar pull cycles defined (websocket? long-poll? page refresh?)

## Next: Pass 3 Flow 4

Recommended next: **tech-to-customer templated communications**. Reasons: contained design surface, extends voice patterns from Flow 1, exercises notification infrastructure already designed in Pass 2 A4. Quick win after the heavier dispatch board work.

Updated remaining flow order (per session-start decision):
- Flow 4: Tech-to-customer templated communications
- Flow 5: Quote approval workflow
- Flow 6: Calendar conflict resolution
- Flow 7: Offline-to-online sync (saved for last — hardest)
