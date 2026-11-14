# Architecture Document Addition — Section 13: Scheduling & Dispatch

**Insertion point**: After Section 12 (Local Development Environment), before Cost Analysis.
**Table of Contents update**: Insert as §13; Cost Analysis and Appendices renumber accordingly (or leave Cost Analysis and Appendices unnumbered as currently shown in `mvp-arch.md`).

---

## 13. Scheduling & Dispatch

### 13.1 Architecture Overview

Scheduling is the domain that coordinates *when* and *who* for every job on the platform. It sits between Sales & Quoting (which produces jobs) and Field Operations (which executes them), and integrates with three external systems: a map provider (for distance-matrix and geocoding), a calendar provider (for bi-directional sync with the tenant's company calendar), and a mobile GPS feed (for live ETA calculation).

The domain exposes three primary UI surfaces:

| Surface | Platform | Users | Purpose |
| :--- | :--- | :--- | :--- |
| **Dispatch Board** | Web | Owner, dispatcher | Plan and assign jobs across techs and time |
| **Today's Schedule** | Mobile | Technician | View assigned jobs in chronological order |
| **Calendar Settings** | Web | Owner | Connect company calendar, manage sync |

**Core principles:**

- **AevoFab is the source of truth**: the dispatch board is authoritative; external calendar is a mirror
- **Conflict-aware**: double-booking, availability violations, and travel infeasibility are detected server-side and surfaced in UI
- **Manual-with-assist for MVP**: owner controls sequencing; system provides drive times and warnings but never auto-optimizes
- **Provider-abstract**: map and calendar integrations use abstract interfaces, Google Maps + Google Calendar as first implementations

### 13.2 Data Model

The scheduling domain introduces seven new tables in a dedicated `scheduling` PostgreSQL schema, plus additive column extensions to the existing `field_ops.job` table. The tables divide into three functional groups:

| Group | Tables | Purpose |
| :--- | :--- | :--- |
| **Assignment & availability** | `job_tech_assignment`, `tech_availability` | Who is assigned to which job; when each tech is available |
| **Calendar integration** | `tenant_calendar_integration`, `calendar_sync_log`, `calendar_sync_conflict` | OAuth connection to external calendar; sync audit and conflict resolution |
| **Schedule extensions** | `field_ops.job` (additive columns) | Scheduled timestamps, duration estimate, external event linkage |

Full DDL, index definitions, constraint rationale, migration ordering, and testing considerations live in the domain schema document: `dev-docs/analysis/scheduling-dispatch-db-schema.md`. That document is the authoritative source for the database design; this architecture section describes only the logical model and how the scheduling domain interacts with the rest of the platform.

**Key design decisions captured in the schema doc**:

- Many-to-many `job_tech_assignment` schema with MVP UI single-tech constraint enforced via DB-level partial unique index
- iCal RRULE-based recurring working hours (via `python-dateutil`); one-off PTO/unavailability blocks with GiST range indexing for conflict lookups
- One calendar integration per tenant (shared company calendar model for MVP)
- Append-only `calendar_sync_log` with 90-day hot retention consistent with audit policy
- Fernet-encrypted OAuth tokens stored via AWS Secrets Manager consistent with Section 9.1

### 13.3 Provider-Abstract Interfaces

Both map and calendar integrations are implemented behind abstract Python protocols to support provider swaps without code changes to consumers.

**Map provider interface** (`backend/integrations/map_provider/base.py`):

```python
from typing import Protocol
from decimal import Decimal

class Coordinates(TypedDict):
    lat: Decimal
    lng: Decimal

class DistanceMatrixResult(TypedDict):
    drive_time_seconds: int
    drive_distance_meters: int

class MapProvider(Protocol):
    async def geocode(self, address: str) -> Coordinates: ...
    async def reverse_geocode(self, coords: Coordinates) -> str: ...
    async def distance_matrix(
        self,
        origins: list[Coordinates],
        destinations: list[Coordinates],
        departure_time: datetime | None = None,
    ) -> list[list[DistanceMatrixResult]]: ...
```

Initial implementation: `GoogleMapsProvider` using the Distance Matrix API and Geocoding API. Configuration selects the provider at startup via `MAP_PROVIDER` environment variable. Alternate future implementations: `MapboxProvider`, `OSRMSelfHostedProvider`.

**Calendar provider interface** (`backend/integrations/calendar_provider/base.py`):

```python
class ExternalCalendarEvent(TypedDict):
    external_event_id: str
    starts_at: datetime
    ends_at: datetime
    title: str
    location: str | None
    description: str | None
    last_modified_at: datetime

class CalendarProvider(Protocol):
    async def oauth_authorize_url(self, redirect_uri: str, state: str) -> str: ...
    async def oauth_exchange_code(self, code: str) -> OAuthTokens: ...
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens: ...
    async def list_events(
        self,
        access_token: str,
        calendar_id: str,
        since_cursor: str | None,
    ) -> tuple[list[ExternalCalendarEvent], str]: ...
    async def create_event(
        self,
        access_token: str,
        calendar_id: str,
        event: JobScheduledEventPayload,
    ) -> str: ...
    async def update_event(
        self,
        access_token: str,
        calendar_id: str,
        external_event_id: str,
        event: JobScheduledEventPayload,
    ) -> None: ...
    async def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        external_event_id: str,
    ) -> None: ...
```

Initial implementation: `GoogleCalendarProvider`. Future: `OutlookCalendarProvider`, `IcalFeedProvider`.

### 13.4 Conflict Detection

Three conflict classes are evaluated whenever a job is placed on the dispatch board (via drag-drop, voice command, or API). Evaluation happens in the `scheduling.conflict_service` module and is called from the dispatch API endpoints before any write.

**Double-booking**: query the `field_ops.job` table for overlapping jobs assigned to the same tech using the GiST `tstzrange` overlap operator for efficient range intersection.

**Availability violation**: check that the proposed `[start, end]` interval falls entirely within one of the tech's working-hours windows (computed from `tech_availability` via RRULE expansion) and does not intersect any `pto` or `unavailable` blocks.

**Travel infeasibility**: for the tech's previous stop on the same day (ordered by `scheduled_start_at`), compute required drive time via the map provider's distance matrix. If `previous_job.scheduled_end_at + drive_time > new_job.scheduled_start_at`, flag as infeasible. Same check applies to the next stop if one exists.

All three checks produce structured conflict records:

```python
class SchedulingConflict(BaseModel):
    conflict_type: Literal['double_booking', 'availability', 'travel_infeasibility']
    severity: Literal['block', 'warn']
    detail: dict
```

**UI behavior**: `block`-severity conflicts prevent submission; `warn`-severity conflicts surface as dismissable warnings. MVP: all conflicts are `warn`. The owner can always force-override by acknowledging the warning. Phase 2 may introduce `block` severity for specific conflict types (e.g., PTO violation).

### 13.5 Bi-Directional Calendar Sync

The sync strategy closely mirrors the QuickBooks bi-directional pattern documented in Section 5. Modifications happen in both AevoFab and the external calendar; a collision resolver handles conflicts.

**Push (AevoFab → Calendar)**: when a job's `scheduled_start_at`, `scheduled_end_at`, `site_id`, or tech assignment changes, a Celery task (`push_job_to_calendar`) is enqueued. The task refreshes the access token if near expiry, calls the calendar provider's `create_event` (first sync) or `update_event` (subsequent), stores the returned `external_event_id` on the job, and logs the sync event to `calendar_sync_log`.

**Pull (Calendar → AevoFab)**: a Celery Beat task runs every 5 minutes per active tenant integration. The task calls the calendar provider's `list_events` with the tenant's `last_sync_cursor`, matches returned events to existing jobs by `external_event_id`, applies changes when the external version is newer, creates new scheduled blocks for unmatched events, and updates `last_sync_cursor` / `last_sync_at`.

**Conflict detection and resolution**: when a pull detects a conflict (both sides modified since last sync), JSONB snapshots of both versions are written to `calendar_sync_conflict` and a notification is enqueued to the owner. The owner resolves via the web dispatch board UI, choosing `accept_local` (push AevoFab version to calendar) or `accept_remote` (apply calendar version to AevoFab).

**Failure handling**: sync failures (network errors, provider rate limits, expired refresh tokens) are retried with exponential backoff via Celery's built-in retry mechanism. After N retries, the integration's `sync_status` transitions to `error` and the owner is notified. The tenant's normal operations (dispatch, mobile app) are unaffected — they always operate against the AevoFab database regardless of sync state.

### 13.6 Celery Task Registry

New scheduled and event-driven tasks introduced by the scheduling domain:

| Task | Trigger | Purpose |
| :--- | :--- | :--- |
| `push_job_to_calendar` | Event-driven (job schedule changed) | Push AevoFab job to external calendar |
| `pull_calendar_events` | Celery Beat, every 5 min per tenant | Pull external calendar changes into AevoFab |
| `refresh_calendar_oauth_tokens` | Celery Beat, hourly | Proactively refresh tokens expiring soon |
| `compute_customer_etas` | Event-driven (tech GPS update) | Recompute ETA for tech's next stop; update Customer Comms feed |
| `notify_tech_of_assignment` | Event-driven (job assigned/reassigned) | Enqueue push + notification_outbox entry |
| `archive_calendar_sync_log` | Celery Beat, daily | Archive sync log rows > 90 days old (consistent with audit retention) |

### 13.7 API Design

New endpoints under `/api/v1/schedule/` and `/api/v1/calendar/`. All follow existing conventions: RFC 7807 errors, cursor pagination, `Idempotency-Key` header support, RBAC enforcement via `require_permission()`.

| Method | Path | Purpose | Required Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/schedule/board` | Dispatch board data (jobs × techs × date range) | `schedule.manage` |
| `GET` | `/api/v1/schedule/today` | Current user's assigned jobs for today | `schedule.view_own` |
| `POST` | `/api/v1/schedule/jobs/{id}/assign` | Assign tech to job | `schedule.manage` |
| `POST` | `/api/v1/schedule/jobs/{id}/reschedule` | Change scheduled time | `schedule.manage` |
| `POST` | `/api/v1/schedule/jobs/{id}/check-conflicts` | Preview conflicts for proposed change | `schedule.manage` |
| `GET` | `/api/v1/schedule/availability/{user_id}` | Tech availability windows | `schedule.manage` or self |
| `POST` | `/api/v1/schedule/availability/{user_id}` | Set tech availability | `schedule.manage` or self |
| `POST` | `/api/v1/schedule/drive-times` | Batch drive-time calculation for sequence | `schedule.manage` |
| `POST` | `/api/v1/calendar/connect` | Initiate OAuth flow | `integrations.manage` |
| `GET` | `/api/v1/calendar/callback` | OAuth callback handler | (public with state token) |
| `POST` | `/api/v1/calendar/disconnect` | Disconnect calendar integration | `integrations.manage` |
| `GET` | `/api/v1/calendar/status` | Sync status and recent activity | `integrations.manage` |
| `GET` | `/api/v1/calendar/conflicts` | List pending sync conflicts | `integrations.manage` |
| `POST` | `/api/v1/calendar/conflicts/{id}/resolve` | Resolve conflict | `integrations.manage` |

### 13.8 Cost Considerations

**Map provider costs (Google Maps Platform at beta)**:

- Distance Matrix API: $5 per 1,000 elements (origin × destination pairs)
- Geocoding API: $5 per 1,000 requests
- Rate-limited per-tenant to prevent runaway costs

**Estimated usage at 100 customers, avg 5 jobs/day per tenant**:

- ~500 dispatch board operations/day × 10 distance-matrix elements = 5,000 elements
- ~100 new customer geocodes/day = 100 requests
- Monthly: ~150,000 matrix elements + ~3,000 geocodes = **~$770/month**

**Cost optimization strategies**:

- Cache drive times for (origin, destination, hour-of-day) tuples for 24 hours in Redis
- Batch distance-matrix calls (up to 25×25 per request)
- Defer ETA recomputation to GPS updates with >200m movement
- Post-MVP: evaluate self-hosted OSRM on the existing GPU instance (eliminates map API costs, adds ~$0 incremental infrastructure)

**Calendar provider costs (Google Calendar API)**:

- Free tier: 1M queries/day per Google Cloud project
- At 100 customers with 5-minute pull cycles: ~29K queries/day, well within free tier
- No material cost until well past 1,000 customers

### 13.9 Failure Modes & Recovery

| Failure Mode | Detection | Recovery |
| :--- | :--- | :--- |
| Map provider outage | HTTP error, timeout | Dispatch still works; drive times and ETAs show "unavailable" — owner can override manually |
| Calendar provider outage | OAuth refresh fails, API 5xx | Integration `sync_status = error`; tenant notified; dispatch unaffected |
| OAuth refresh token expired | Token refresh returns invalid_grant | Force-disconnect integration; notify owner to reconnect |
| Clock skew between AevoFab and calendar | Sync detects future-dated events | Log warning; accept events as-is (provider time is source of truth) |
| Drive time calculation exceeds SLA | Request > 2s timeout | Return cached value if available; else return no drive time (warn badge hidden) |
| Tech GPS unavailable for ETA | No recent location update within 10 min | Omit ETA from customer comms; auto-ETA templates fall back to "Tech is on the way" |

### 13.10 Monitoring

New CloudWatch metrics and dashboards:

- `scheduling.conflicts.detected.count` — dispatch conflicts surfaced per hour
- `scheduling.conflicts.overridden.count` — warnings dismissed by owner
- `calendar_sync.push.success.count` / `calendar_sync.push.failure.count`
- `calendar_sync.pull.success.count` / `calendar_sync.pull.failure.count`
- `calendar_sync.conflicts.pending.gauge` — current count of unresolved sync conflicts
- `map_provider.requests.count` (by API: geocode, reverse_geocode, distance_matrix)
- `map_provider.latency.p95.ms`
- `map_provider.cost.usd.gauge` — estimated monthly cost projection

New alarms:

- Calendar sync failure rate > 5% over 15 minutes
- Map provider cost projection > $1,500/month
- Pending sync conflicts > 20 for any tenant

---

## Notes for Architecture Doc Editor

- **Section numbering**: inserting as §13 shifts existing Cost Analysis and Appendices. Update TOC accordingly.
- **Version History**: add a new entry. Suggested: `v3.2 (2026-04-XX): Added Section 13 (Scheduling & Dispatch) — bi-directional calendar sync, dispatch board, provider-abstract interfaces for map and calendar, new Celery tasks, new API endpoints under /api/v1/schedule/ and /api/v1/calendar/. Database schema maintained in dev-docs/analysis/scheduling-dispatch-db-schema.md.`
- **Appendix B (Key Technical Decisions)**: add rows for scheduling-related architectural decisions:

```
| **Map provider** | Provider-abstract interface, Google Maps first | Enables vendor-neutral code; swap to Mapbox or self-hosted OSRM without refactor |
| **Calendar provider** | Provider-abstract interface, Google Calendar first | Same rationale; avoids lock-in |
| **Tech assignment** | Many-to-many schema, single-tech UI for MVP | Phase 2 multi-tech crews require no migration |
| **Route optimization** | Manual with drive-time assist for MVP | Automatic optimization deferred to Phase 2; solo operators prefer manual control |
| **Dispatch source of truth** | AevoFab is authoritative, calendar mirrors | Consistent with QuickBooks sync pattern |
| **Calendar sync scope** | One shared company calendar per tenant | Matches solo-operator mental model; multi-tech-personal-calendar deferred to Phase 2 |
```

- **Appendix D (Useful Commands Reference)**: consider adding map provider and calendar sync debugging commands post-implementation.
- The `schedule.manage` and `schedule.view_own` permissions were identified in the Pass 2 backend additions doc. Verify they're wired into the RBAC seeding (permissions are documented in `scheduling-dispatch-db-schema.md`).
