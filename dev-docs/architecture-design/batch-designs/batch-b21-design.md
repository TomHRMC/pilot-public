# Batch B21 + FE-B31 + MOB-B9 Design — Recurring Jobs

**Batch**: B21 (Python Engineer) + FE-B31 (React Engineer — web) + MOB-B9 (React Native Engineer — mobile)  
**Launch Plan Name**: Recurring-Jobs-B1  
**Date**: 2026-07-12  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Tom-approved scope  
**Reference**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 10 · Product Roadmap GAP-M1  
**Prerequisites**: B20 complete ✅, Background-Sync-B1 (MOB-B8) complete ✅, alembic head `f7f30492c3e4`

---

## Overview

This batch implements **recurring job patterns** — the ability to define a schedule rule (daily, weekly, monthly, annually with configurable interval) and have Pilot automatically generate job instances on the correct dates.

**Part A (Python Engineer)**: New `job_recurrence_rule` table, `job.recurrence_rule_id` FK column, 5 CRUD endpoints, `generate_due_recurring_jobs` Celery Beat task, `recurring_job_scheduled` notification template seeded via Alembic data migration.

**Part B (React Engineer — web)**: Recurrence toggle + config in `JobFormModal`, new "Recurring" tab under the Jobs nav item, recurring badge on job cards in `JobsPage`.

**Part C (React Native Engineer — mobile)**: Recurring badge on job cards in Today tab and job list, "Part of recurring series" banner on job detail screen. **No create/edit of rules on mobile — web-only for MVP.**

**Part B and Part C run in parallel** after Part A's `python export_openapi_json.py` is complete.

---

## Explicit Scope

### ✅ MVP Included

- `daily` / `weekly` / `monthly` (day-of-month only) / `annually` patterns
- `interval_count` — e.g., `2` + `weekly` = every 2 weeks
- First job created immediately on rule creation (not waiting for Beat task)
- Beat task creates subsequent jobs on schedule
- `ends_on` (date) + `max_occurrences` stop conditions
- Default tech auto-assignment on generated jobs
- Notes template prepopulated on generated jobs
- `recurring_job_scheduled` SMS + email notification to customer when job is generated
- Recurring badge on web job cards + mobile job cards
- Job detail banner on mobile linking back to "Manage on web"
- Pause/resume toggle on rule via `PATCH /{id}` with `is_active`

### ❌ Deferred to P2

- Skip individual occurrence (requires `job_recurrence_skip` table)
- Monthly Nth-weekday patterns (e.g., "3rd Friday")
- Bulk edit (change all future generated jobs when rule is edited)
- Customer notification preferences per-rule
- Mobile create/edit of recurrence rules

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| Product Roadmap GAP-M1 | "Recurring jobs — basic pattern (daily/weekly/monthly/annually)" | P1 launch blocker; Python + React + RN Engr scope |
| PRD §3.4 Field Operations | Job domain features | No recurring job feature documented yet; GAP-M1 is the spec |
| MCP — `job` table columns | Verified all 23 columns | No `recurrence_rule_id` — must add as nullable FK |
| MCP — table listing `%recur%` | Checked for existing recurring tables | Empty — no tables exist yet |
| MCP — `job_status` columns | `code, name, is_terminal, is_default, is_active` | No `label` column — confirmed |
| MCP — `communication_template` | `template_code, channel, subject, body_template, is_active, tenant_id` | tenant_id=NULL = system template; need 2 new rows (sms + email) |
| MCP — alembic_version | `f7f30492c3e4` | Current head (B20); B21 migrations chain from here |
| Tom design review | Approved schema + scope | Skip/Nth-weekday/bulk-edit moved to P2; new `recurring_job_scheduled` template approved; first-job-on-creation confirmed; interval_count required; new Jobs tab for rules list |

---

## B. Migration Plan

### 3 Alembic migrations required

#### Migration 1: Create `job_recurrence_rule` table

```sql
CREATE TABLE job_recurrence_rule (
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES "user"(id),
    updated_by UUID REFERENCES "user"(id),
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    customer_id UUID NOT NULL REFERENCES customer(id),
    site_id UUID NOT NULL REFERENCES site(id),
    pattern VARCHAR(20) NOT NULL,            -- 'daily' | 'weekly' | 'monthly' | 'annually'
    interval_count INTEGER NOT NULL DEFAULT 1, -- e.g., 2 = every 2 weeks
    starts_on DATE NOT NULL,
    ends_on DATE,                            -- NULL = runs indefinitely
    max_occurrences INTEGER,                 -- NULL = no limit
    occurrences_created INTEGER NOT NULL DEFAULT 0,
    next_job_at TIMESTAMPTZ,                -- cached; updated by Beat task after each creation
    last_job_created_at TIMESTAMPTZ,
    estimated_duration_minutes INTEGER,
    default_tech_user_id UUID REFERENCES "user"(id),
    notes_template TEXT,                    -- prepopulated on each generated job
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT chk_pattern CHECK (pattern IN ('daily','weekly','monthly','annually')),
    CONSTRAINT chk_interval_positive CHECK (interval_count >= 1)
);

-- Standard triggers: audit_log, updated_at_sync, immutable_guard on tenant_id
-- Indexes:
CREATE INDEX ix_job_recurrence_rule_tenant_id ON job_recurrence_rule(tenant_id);
CREATE INDEX ix_job_recurrence_rule_next_job_at ON job_recurrence_rule(next_job_at) WHERE is_active = true;
CREATE INDEX ix_job_recurrence_rule_customer_id ON job_recurrence_rule(customer_id);
```

#### Migration 2: Add `recurrence_rule_id` to `job` table

**3-part NOT NULL pattern** does NOT apply here — this is a nullable FK (not all jobs have a rule). Simple single-step:

```sql
ALTER TABLE job ADD COLUMN recurrence_rule_id UUID REFERENCES job_recurrence_rule(id);
CREATE INDEX ix_job_recurrence_rule_id ON job(recurrence_rule_id);
```

#### Migration 3: Seed `recurring_job_scheduled` communication templates

Data migration — inserts 2 system template rows (`tenant_id = NULL`):

```sql
SET LOCAL session_replication_role = 'replica';

INSERT INTO communication_template (template_code, channel, subject, body_template, is_active, tenant_id)
VALUES
  ('recurring_job_scheduled', 'sms', NULL,
   'Hi {{customer_name}}, your scheduled {{service_description}} with {{company_name}} is confirmed for {{scheduled_date}} at {{scheduled_time}}. Reply STOP to opt out.',
   true, NULL),
  ('recurring_job_scheduled', 'email', 'Your {{service_description}} is scheduled',
   'Hi {{customer_name}},\n\nYour scheduled {{service_description}} with {{company_name}} is confirmed.\n\nDate: {{scheduled_date}}\nTime: {{scheduled_time}}\nAddress: {{site_address}}\n\nIf you need to reschedule, please contact us at {{company_phone}}.\n\nThank you,\n{{company_name}}',
   true, NULL)
ON CONFLICT (template_code, channel) DO NOTHING;
```

**Template variables** (resolved at notification dispatch time):
- `customer_name`, `company_name`, `company_phone`, `service_description` (rule notes_template or "Service Visit"), `scheduled_date`, `scheduled_time`, `site_address`

### Pre-migration MCP verification queries (Python Engineer runs before writing any code)

```sql
-- 1. Confirm job_recurrence_rule table does NOT exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'job_recurrence_rule';

-- 2. Confirm job.recurrence_rule_id does NOT exist
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job' AND column_name = 'recurrence_rule_id';

-- 3. Confirm communication_template schema (verify column names before seeding)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'communication_template'
ORDER BY ordinal_position;

-- 4. Confirm recurring_job_scheduled template does NOT exist (idempotency check)
SELECT template_code, channel FROM public.communication_template
WHERE template_code = 'recurring_job_scheduled';

-- 5. Confirm current alembic head
SELECT version_num FROM public.alembic_version;

-- 6. Verify triggers exist for audit/updated_at pattern (reference)
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_table = 'job_recurrence_rule' LIMIT 5;
-- (Expected: 0 — table doesn't exist yet; re-run after migration 1 passes)
```

---

## C. Execution Order

### Part A — Python Engineer (runs first)

| # | Task | File(s) | Notes |
|---|---|---|---|
| A1 | Run all MCP pre-work queries | — | Verify no existing tables/columns |
| A2 | Create Migration 1: `job_recurrence_rule` table | New migration file | Blank migration; include all 3 standard triggers |
| A3 | Create Migration 2: `job.recurrence_rule_id` nullable FK | New migration file | Single ALTER TABLE; no 3-part pattern |
| A4 | Create Migration 3: seed `recurring_job_scheduled` communication templates | New migration file | 2 INSERT rows with `ON CONFLICT DO NOTHING` |
| A5 | Run `alembic upgrade head` + `downgrade -1` + `upgrade head` cycle for all 3 | — | Verify upgrade/downgrade for each |
| A6 | Create `JobRecurrenceRule` SQLModel in `app/models/fulfillment.py` | Existing model file | Add after `Job` class |
| A7 | Update `Job` SQLModel — add `recurrence_rule_id` nullable FK field | `app/models/fulfillment.py` | |
| A8 | Create `api/schemas/recurrence.py` — request/response schemas | New schema file | `RecurrenceRuleCreate`, `RecurrenceRuleUpdate`, `RecurrenceRuleResponse`, `RecurrenceRuleListItem` |
| A9 | Create `api/routes/job_recurrence_rules.py` — 5 endpoints + `/test` counterparts | New route file | CRUD + pause/resume |
| A10 | Register router in `app/main.py` at `/api/v1` | `app/main.py` | |
| A11 | Create `tasks/recurring_jobs.py` — `generate_due_recurring_jobs` Celery task | New task file | Two-layer pattern |
| A12 | Register task module + Beat schedule in `core/celery_app.py` | `core/celery_app.py` | Daily at 06:00 UTC |
| A13 | `python -m pytest -m unit --tb=short -q` — fix any failures | — | |
| A14 | `python export_openapi_json.py` → handoff to FE-B31 + MOB-B9 | — | Both run in parallel after this |
| A15 | `python generate_db_model_map.py` | — | |
| A16 | `python schema_manager.py --help` then use appropriate CRUD command | — | Update JSON schema file — `schema_manager.py` is a CRUD script; run `--help` first to see available commands |

### Part B — React Engineer (web, runs in parallel with Part C after A14)

| # | Task | File(s) | Notes |
|---|---|---|---|
| B1 | `pnpm sync-api-types` | — | First step, mandatory |
| B2 | Create `useCreateRecurrenceRule` + `useListRecurrenceRules` + `useUpdateRecurrenceRule` hooks | `features/jobs/hooks/` | |
| B3 | Extend `JobFormModal` — recurrence toggle + config fields | `features/jobs/components/JobFormModal.tsx` | When toggle on: shows pattern, interval, start date, end date (optional), default tech (optional) |
| B4 | Add recurring badge to job card in `JobsPage` | `features/jobs/components/JobsPage.tsx` | Small `↻` badge when `recurrence_rule_id` present |
| B5 | Create `RecurringJobsPage` — list of rules | `features/jobs/components/RecurringJobsPage.tsx` | New component |
| B6 | Create `/jobs/recurring` route | `app/(authed)/jobs/recurring/page.tsx` | Thin server component |
| B7 | Add "Recurring" tab to Jobs nav | `features/jobs/components/JobsPage.tsx` or nav component | Tab alongside existing list |
| B8 | MSW handlers + tests | New + existing | |

### Part C — React Native Engineer (mobile, runs in parallel with Part B after A14)

| # | Task | File(s) | Notes |
|---|---|---|---|
| C1 | `pnpm sync-api-types` | — | First step, mandatory |
| C2 | Add recurring badge to job cards in Today tab + JobsTabScreen | `app/(tabs)/(home)/index.tsx`, `features/jobs/` | Small `↻` indicator |
| C3 | Add "Part of recurring series" banner to job detail screen | `features/jobs/components/detail/` | Shows pattern + "Manage on web" text |
| C4 | MSW handlers + tests | New + existing | |

---

## D. New API Endpoints (Part A)

### D1. Create Recurrence Rule — `POST /api/v1/job-recurrence-rules`

```
POST /api/v1/job-recurrence-rules
Auth: Cognito JWT required
Permission: require_permission("jobs.create")
Idempotency-Key: required (offline mobile creation may eventually be supported)

Request:
{
  "customer_id": "uuid",
  "site_id": "uuid",
  "pattern": "daily" | "weekly" | "monthly" | "annually",
  "interval_count": 1,          # default 1; must be >= 1
  "starts_on": "2026-08-01",    # ISO date (not datetime)
  "ends_on": "2027-08-01",      # optional
  "max_occurrences": null,      # optional
  "estimated_duration_minutes": 120,  # optional
  "default_tech_user_id": "uuid",     # optional
  "notes_template": "Annual inspection"  # optional
}

Response 201:
{
  "id": "uuid",
  "tenant_id": "uuid",
  "customer_id": "uuid",
  "site_id": "uuid",
  "pattern": "weekly",
  "interval_count": 1,
  "starts_on": "2026-08-01",
  "ends_on": null,
  "max_occurrences": null,
  "occurrences_created": 1,       # 1 because first job created immediately
  "next_job_at": "2026-08-08T...", # next scheduled date after first job
  "last_job_created_at": "2026-08-01T...",
  "is_active": true,
  "first_job_id": "uuid"          # ID of the job just created
}

Side effects:
  1. Creates the first job immediately (do not wait for Beat task)
  2. Enqueues customer notification for the first job
  3. Sets next_job_at to the next occurrence
  4. Sets occurrences_created = 1
```

Also add `POST /api/v1/job-recurrence-rules/test` unauthenticated test endpoint.

### D2. List Recurrence Rules — `GET /api/v1/job-recurrence-rules`

```
GET /api/v1/job-recurrence-rules?is_active=true&limit=50&offset=0
Auth: Cognito JWT required
Permission: require_permission("jobs.view")

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "pattern": "weekly",
      "interval_count": 1,
      "customer_name": "...",   # joined from customer
      "site_address": "...",    # joined from site
      "next_job_at": "...",
      "occurrences_created": 5,
      "is_active": true,
      "default_tech_display_name": "..." # joined from user, nullable
    }
  ],
  "total": 12
}
```

### D3. Get Recurrence Rule — `GET /api/v1/job-recurrence-rules/{rule_id}`

Returns full `RecurrenceRuleResponse` (same shape as POST 201 response). IDOR-safe: `WHERE id = rule_id AND tenant_id = current_user.tenant_id`.

### D4. Update Recurrence Rule — `PATCH /api/v1/job-recurrence-rules/{rule_id}`

```
PATCH /api/v1/job-recurrence-rules/{rule_id}
Permission: require_permission("jobs.edit")

Request (all fields optional):
{
  "is_active": false,            # pause/resume
  "ends_on": "2027-01-01",
  "default_tech_user_id": "uuid",
  "notes_template": "...",
  "estimated_duration_minutes": 90
}

Note: pattern, interval_count, starts_on are NOT patchable (creates a new rule instead).
Response 200: full RecurrenceRuleResponse
```

### D5. Delete Recurrence Rule — `DELETE /api/v1/job-recurrence-rules/{rule_id}`

Soft-delete: sets `is_active = false`. Does NOT cancel any already-generated jobs. Returns `204 No Content`.

---

## E. Celery Task Design (Part A)

### `backend/tasks/recurring_jobs.py`

```python
# Two-layer pattern — _impl() is testable; @celery_app.task wraps it

def _compute_next_job_at(
    pattern: str,
    interval_count: int,
    from_date: date,
) -> date:
    """
    Pure function — compute the next occurrence after from_date.
    pattern='daily'   → from_date + interval_count days
    pattern='weekly'  → from_date + interval_count * 7 days
    pattern='monthly' → same day of month, + interval_count months (use dateutil.relativedelta)
    pattern='annually'→ same day of year, + interval_count years
    """
    ...  # implement with python-dateutil relativedelta


def _create_job_from_rule(
    rule: JobRecurrenceRule,
    scheduled_date: date,
    db: Session,
    user_context,  # AuthenticatedUser or TestUserContext
) -> Job:
    """
    Create a Job from a recurrence rule. Called by:
    1. The create-rule endpoint (first job, immediately)
    2. The Beat task (subsequent jobs)
    """
    # Get default job_status (is_default = True)
    default_status = db.exec(
        select(JobStatus)
        .where(JobStatus.tenant_id == rule.tenant_id)
        .where(JobStatus.is_default == True)
    ).first()

    # Compute scheduled_start_at (scheduled_date + tenant timezone to midnight)
    # For MVP: use noon UTC on scheduled_date
    start_at = datetime(scheduled_date.year, scheduled_date.month, scheduled_date.day,
                        12, 0, 0, tzinfo=UTC)
    end_at = None
    if rule.estimated_duration_minutes:
        end_at = start_at + timedelta(minutes=rule.estimated_duration_minutes)

    # Generate job_number
    job_number = _generate_job_number(rule.tenant_id, db)

    job = Job(
        tenant_id=rule.tenant_id,
        customer_id=rule.customer_id,
        site_id=rule.site_id,
        status_id=default_status.id,
        scheduled_start_at=start_at,
        scheduled_end_at=end_at,
        estimated_duration_minutes=rule.estimated_duration_minutes,
        recurrence_rule_id=rule.id,
        job_number=job_number,
        is_active=True,
    )
    db.add(job)
    db.flush()  # get job.id

    # Optional: auto-assign default tech
    if rule.default_tech_user_id:
        assignment = JobTechAssignment(
            tenant_id=rule.tenant_id,
            job_id=job.id,
            user_id=rule.default_tech_user_id,
        )
        db.add(assignment)

    return job


def _generate_due_recurring_jobs_impl(db: Session) -> dict:
    """
    Scan all active rules where next_job_at <= NOW().
    For each eligible rule, create the next job and advance next_job_at.
    """
    now_utc = datetime.now(UTC)
    due_rules = db.exec(
        select(JobRecurrenceRule)
        .where(JobRecurrenceRule.is_active == True)
        .where(JobRecurrenceRule.next_job_at <= now_utc)
    ).all()

    created = 0
    skipped = 0
    for rule in due_rules:
        # Check stop conditions
        if rule.ends_on and rule.ends_on < now_utc.date():
            rule.is_active = False
            db.add(rule)
            skipped += 1
            continue
        if rule.max_occurrences and rule.occurrences_created >= rule.max_occurrences:
            rule.is_active = False
            db.add(rule)
            skipped += 1
            continue

        # Create job
        scheduled_date = rule.next_job_at.date()
        job = _create_job_from_rule(rule, scheduled_date, db, _system_context(rule.tenant_id))

        # Advance rule state
        next_date = _compute_next_job_at(rule.pattern, rule.interval_count, scheduled_date)
        rule.next_job_at = datetime(next_date.year, next_date.month, next_date.day, 12, 0, 0, tzinfo=UTC)
        rule.occurrences_created += 1
        rule.last_job_created_at = now_utc
        db.add(rule)

        # Enqueue customer notification
        _enqueue_recurring_job_notification.delay(str(rule.id), str(job.id))

        created += 1

    db.commit()
    return {"created": created, "deactivated": skipped}


@celery_app.task(name="tasks.recurring_jobs.generate_due_recurring_jobs")
def generate_due_recurring_jobs() -> dict:
    """Beat task — runs daily at 06:00 UTC."""
    with next(get_db()) as db:
        return _generate_due_recurring_jobs_impl(db)


def _enqueue_recurring_job_notification_impl(rule_id: str, job_id: str, db: Session) -> None:
    """
    Send recurring_job_scheduled notification to customer.
    Uses existing notification_outbox / template_renderer pattern.
    Read notification_worker.py and template_renderer.py for the established pattern.
    """
    ...  # implement using existing notification dispatch system


@celery_app.task(name="tasks.recurring_jobs.enqueue_recurring_job_notification")
def _enqueue_recurring_job_notification(rule_id: str, job_id: str) -> None:
    with next(get_db()) as db:
        _enqueue_recurring_job_notification_impl(rule_id, job_id, db)
```

**Beat schedule**: Daily at `06:00 UTC` — add to `celery_app.py`:
```python
"generate-due-recurring-jobs": {
    "task": "tasks.recurring_jobs.generate_due_recurring_jobs",
    "schedule": crontab(hour=6, minute=0),
},
```

---

## F. Pattern Reuse Decisions

| Pattern | Applied in B21 |
|---|---|
| Two-layer Celery task | `generate_due_recurring_jobs` + `_enqueue_recurring_job_notification` both use `_impl` + `@celery_app.task` wrapper |
| `/test` endpoint counterpart | All 5 CRUD endpoints have `/test` unauthenticated counterparts using `TestUserContext` |
| IDOR-safe `select().where(tenant_id == ...)` | Every rule fetch in routes and Beat task is tenant-scoped |
| `set_audit_context_sync()` | Called in every mutation endpoint (POST, PATCH, DELETE) |
| RFC 7807 error format | All `HTTPException` raises use Problem Details dict |
| `_generate_job_number()` | Reuse from `api/routes/jobs.py` — confirm exact function location/signature in pre-work |
| `communication_template` + notification dispatch | `_enqueue_recurring_job_notification_impl` reads the `recurring_job_scheduled` template and dispatches via existing `notification_worker` / `template_renderer` pattern |
| `crontab` Beat schedule | Uses celery `crontab(hour=6, minute=0)` — check existing `celery_app.py` for existing `crontab` imports |

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **First job created on rule creation or by Beat?** | On rule creation — creates immediately so owner sees something right away. Beat creates all subsequent jobs. |
| **Where does the recurring rules list live on web?** | New "Recurring" tab under existing Jobs nav (alongside the main job list). Route: `/jobs/recurring`. |
| **Is `interval_count` required?** | Yes — required for "every 2 weeks" scenarios. Defaults to 1 if not specified. |
| **What patterns are supported in MVP?** | `daily`, `weekly`, `monthly` (day-of-month only), `annually`. Monthly Nth-weekday deferred to P2. |
| **Skip occurrence in MVP?** | No — deferred to P2. |
| **Bulk edit in MVP?** | No — PATCH updates the rule (affects future Beat-generated jobs) but does NOT retroactively change already-created jobs. |
| **Notification template?** | New system template `recurring_job_scheduled` with SMS + email variants. Seeded via Alembic data migration. |
| **Pattern for notification dispatch?** | Read `tasks/notification_worker.py` + `services/template_renderer.py` in pre-work to understand existing notification dispatch — reuse the same pattern. |
| **`job_number` generation for recurring-generated jobs?** | Reuse `_generate_job_number()` from `api/routes/jobs.py`. Python Engineer: grep for this function in pre-work to confirm exact location/signature. |
| **Mobile UI for rule creation?** | No — web-only for MVP. Mobile only shows recurring badge + detail banner. |

---

## H. Surface Mockup Reference

### H.1 — `JobFormModal` with Recurrence Toggle (Web)

```
┌──────────────────────────────────────────────────────────────────┐
│  Create Job                                                       │
│  Customer: [dropdown]    Site: [dropdown]                        │
│  Schedule: [date/time]   Tech: [dropdown]                        │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  ☐ Make this a recurring job                                │ │
│  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (collapsed when unchecked)│ │
│  │                                                              │ │
│  │  [when checked, reveals:]                                    │ │
│  │  Pattern:  [Weekly ▼]   Every: [1] [week(s)]               │ │
│  │  Starts:   [2026-08-01]                                      │ │
│  │  Ends:     ○ Never  ○ On [date]  ○ After [N] jobs           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  [Cancel]                          [Create Job]                   │
└──────────────────────────────────────────────────────────────────┘
```

### H.2 — Recurring Badge on Job Card (Web + Mobile)

```
┌─────────────────────────────────────────────────────────────────┐
│  ↻  JOB-000012                              Scheduled            │
│     Johnson Panel Upgrade                                        │
│     Jane Smith • 123 Main St               Aug 1, 9am–11am      │
└─────────────────────────────────────────────────────────────────┘
  ↑ "↻" badge visible when recurrence_rule_id is present
```

### H.3 — RecurringJobsPage Tab (Web)

```
Jobs  |  Recurring  ← new tab
────────────────────────────────────────────────────────────────
↻ Johnson Panel Upgrade  ·  Weekly  ·  Jane Smith  ·  Next: Aug 8   [● Active]  [Edit]
↻ Smith Annual Inspection  ·  Annually  ·  Bob Jones  ·  Next: Dec 1  [● Active]  [Edit]
↻ Wilson HVAC Check  ·  Monthly  ·  Unassigned  ·  Next: Aug 15     [⏸ Paused]  [Edit]
```

### H.4 — Job Detail Banner (Mobile)

```
┌─────────────────────────────────────────────────────────────────┐
│  Job Detail — JOB-000012                                        │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ↻ Part of a recurring series (Weekly)                   │  │
│  │  Manage schedule on web →                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Johnson Panel Upgrade · Jane Smith                              │
│  ...                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## I. Component Manifest

### Part A — Python Engineer

| File | New or Modify | Notes |
|---|---|---|
| `backend/migrations/versions/[ts]-b21_create_job_recurrence_rule.py` | **New** | Migration 1: table + triggers + indexes |
| `backend/migrations/versions/[ts]-b21_add_recurrence_rule_id_to_job.py` | **New** | Migration 2: nullable FK column |
| `backend/migrations/versions/[ts]-b21_seed_recurring_job_templates.py` | **New** | Migration 3: 2 communication_template rows |
| `backend/app/models/fulfillment.py` | **Modify** | Add `JobRecurrenceRule` class; add `recurrence_rule_id` to `Job` |
| `backend/api/schemas/recurrence.py` | **New** | All recurrence request/response schemas |
| `backend/api/routes/job_recurrence_rules.py` | **New** | 5 endpoints + 5 `/test` counterparts |
| `backend/app/main.py` | **Modify** | Register router at `/api/v1` |
| `backend/tasks/recurring_jobs.py` | **New** | Beat task + notification dispatch task |
| `backend/core/celery_app.py` | **Modify** | Register task module + Beat schedule (`crontab(hour=6, minute=0)`) |
| `backend/openapi.json` | **Regenerated** | After A14 |
| `backend/openapi_schema_map.md` | **Regenerated** | After A14 |
| `backend/db_models_map.md` | **Regenerated** | After A15 |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | **Updated** | Via `schema_manager.py --help` then CRUD command after A16 |

### Part B — React Engineer (web)

| Component | Path | New or Modify |
|---|---|---|
| `useCreateRecurrenceRule` | `features/jobs/hooks/useCreateRecurrenceRule.ts` | **New** |
| `useListRecurrenceRules` | `features/jobs/hooks/useListRecurrenceRules.ts` | **New** |
| `useUpdateRecurrenceRule` | `features/jobs/hooks/useUpdateRecurrenceRule.ts` | **New** |
| `JobFormModal` | `features/jobs/components/JobFormModal.tsx` | **Modify** — add recurrence toggle + config fields |
| `JobsPage` | `features/jobs/components/JobsPage.tsx` | **Modify** — recurring badge + "Recurring" tab |
| `RecurringJobsPage` | `features/jobs/components/RecurringJobsPage.tsx` | **New** |
| `/jobs/recurring/page.tsx` | `app/(authed)/jobs/recurring/page.tsx` | **New** — thin server component |
| `recurrenceRuleHandlers.ts` | `mocks/handlers/recurrenceRuleHandlers.ts` | **New** |
| `mocks/handlers/index.ts` | `mocks/handlers/index.ts` | **Modify** — register handlers |

### Part C — React Native Engineer (mobile)

| Component | Path | New or Modify |
|---|---|---|
| Recurring badge | `features/jobs/components/` (job card component) | **Modify** — add `↻` indicator |
| Recurring banner | `features/jobs/components/detail/` (job detail) | **Modify** — add "Part of recurring series" banner |
| `recurrenceRuleHandlers.ts` | `mocks/handlers/recurrenceRuleHandlers.ts` | **New** |
| `mocks/handlers/index.ts` | `mocks/handlers/index.ts` | **Modify** — register handlers |
