# Implementation Prompt: B21 — Recurring Jobs Backend

**Mode**: Pilot Python Engineer  
**Batch**: B21 (Recurring-Jobs-B1 — Backend)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch 10 (Recurring-Jobs-B1)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b21-design.md`  
**Estimated session**: 4–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companions**: FE-B31 (React web) + MOB-B9 (React Native mobile) — both run in parallel after `python export_openapi_json.py` is confirmed

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: This batch requires 3 Alembic migrations. ALWAYS use blank migrations (`alembic revision -m "name"` — NEVER `--autogenerate`). Each migration must implement `downgrade()` that exactly reverses `upgrade()`.
- **Rule 2**: Never guess column names. Run ALL MCP pre-work queries before writing any code. The `communication_template` schema and `job` table column names must be verified before writing any migration or model code.
- **Rule 3**: `_generate_job_number()` function — find its exact location and signature with grep before calling it in `_create_job_from_rule()`. Do NOT assume it's importable from a specific file without checking.
- **Rule 4**: The Beat task uses `crontab(hour=6, minute=0)` — check existing `celery_app.py` to verify the correct `crontab` import before adding the schedule.
- **Rule 5**: All Celery tasks use the two-layer pattern — `_impl(params, db: Session)` for business logic + `@celery_app.task` wrapper. Never put business logic in the Celery entry point.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with `WHERE tenant_id = :tid`.
- **Rule 7**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before any DB write.
- **Rule 8**: All API errors follow RFC 7807 Problem Details format — `{"type": "...", "title": "...", "status": N, "detail": "..."}`. No plain string `detail`.
- **Rule 9**: If ANY test fails — pre-existing or new — fix it before declaring done.
- **Rule 10**: Read `tasks/notification_worker.py` AND `services/template_renderer.py` before writing `_enqueue_recurring_job_notification_impl()`. Reuse the existing notification dispatch pattern — do not invent a new one.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count. Fix any pre-existing failures or confirm with Tom before starting.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these before writing any code:

```sql
-- 1. Confirm job_recurrence_rule does NOT exist yet
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'job_recurrence_rule';

-- 2. Confirm job.recurrence_rule_id does NOT exist
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job' AND column_name = 'recurrence_rule_id';

-- 3. Verify communication_template schema (ALL column names before seeding)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'communication_template'
ORDER BY ordinal_position;

-- 4. Confirm recurring_job_scheduled template does NOT already exist
SELECT template_code, channel FROM public.communication_template
WHERE template_code = 'recurring_job_scheduled';

-- 5. Confirm current alembic head
SELECT version_num FROM public.alembic_version;

-- 6. Verify job.customer_id and job.site_id are NOT NULL (no default FK cascade concerns)
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
AND column_name IN ('customer_id', 'site_id', 'status_id', 'job_number', 'is_active')
ORDER BY ordinal_position;

-- 7. Verify job_status structure for getting default status in Beat task
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_status'
ORDER BY ordinal_position;
```

> **MCP Usage Rule**: Read-only verification only. Never INSERT/UPDATE/DELETE via MCP.

---

## Pre-Work: Read These Source Files

```
backend/app/models/fulfillment.py          ← WHY: understand Job + JobStatus + JobTechAssignment models before adding JobRecurrenceRule
backend/api/routes/jobs.py                 ← WHY: find _generate_job_number() — confirm its exact signature and import path
backend/api/schemas/schemas.py             ← WHY: understand existing job-related schema patterns before creating recurrence.py
backend/tasks/notification_worker.py       ← WHY: understand existing notification dispatch pattern to reuse for recurring_job_scheduled
backend/services/template_renderer.py      ← WHY: understand how templates are rendered and dispatched
backend/core/celery_app.py                 ← WHY: find existing crontab import and Beat schedule format before adding new schedule
backend/migrations/versions/[most recent]  ← WHY: understand existing blank migration pattern (header comment, upgrade/downgrade structure)
backend/db_models_map.md                   ← WHY: confirm model names and table mappings before creating new models
```

Also run:
```bash
# Find _generate_job_number — confirm exact location
grep -rn "_generate_job_number\|generate_job_number" backend/ --include="*.py" | head -10

# Find existing JobTechAssignment model for the auto-assign pattern
grep -rn "JobTechAssignment\|job_tech_assignment" backend/ --include="*.py" | head -10

# Find crontab import in celery_app.py
grep -n "crontab" backend/core/celery_app.py | head -5

# Find existing notification dispatch calls to understand the pattern
grep -rn "notification_outbox\|dispatch_notification\|template_renderer" backend/ --include="*.py" | head -10
```

---

## Background / Context

This batch implements recurring job patterns — the ability to schedule a job series (e.g., weekly electrical inspection, annual service) that auto-generates job instances on the configured cadence. The `job_recurrence_rule` table stores the template; a Celery Beat task runs daily at 06:00 UTC and creates jobs when due.

**Key design decisions (from §G of design doc)**:
- Creating a rule immediately creates the FIRST job (not waiting for Beat task)
- Beat task creates all subsequent jobs
- `pattern` values: `daily` | `weekly` | `monthly` | `annually` (day-of-month only; Nth-weekday is P2)
- `interval_count` allows "every 2 weeks" patterns
- Notification dispatch on each generated job via `recurring_job_scheduled` template

---

## Task 1 — Three Alembic Migrations

### Migration 1: Create `job_recurrence_rule` table

```bash
cd <repo>/backend
alembic revision -m "b21_create_job_recurrence_rule"
```

Write `upgrade()` to create the table with:
- Standard audit mixin columns (created_at, updated_at, created_by, updated_by)
- All columns per design doc §B Migration 1
- CHECK constraint: `pattern IN ('daily','weekly','monthly','annually')`
- CHECK constraint: `interval_count >= 1`
- Standard triggers: audit_log, updated_at_sync, immutable_guard on tenant_id

```python
# In upgrade():
op.create_table('job_recurrence_rule',
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
    sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.id'), nullable=False),
    sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customer.id'), nullable=False),
    sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('site.id'), nullable=False),
    sa.Column('pattern', sa.String(20), nullable=False),
    sa.Column('interval_count', sa.Integer(), server_default='1', nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=True),
    sa.Column('max_occurrences', sa.Integer(), nullable=True),
    sa.Column('occurrences_created', sa.Integer(), server_default='0', nullable=False),
    sa.Column('next_job_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('last_job_created_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
    sa.Column('default_tech_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=True),
    sa.Column('notes_template', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.CheckConstraint("pattern IN ('daily','weekly','monthly','annually')", name='chk_recurrence_pattern'),
    sa.CheckConstraint("interval_count >= 1", name='chk_interval_count_positive'),
)
# Indexes
op.create_index('ix_job_recurrence_rule_tenant_id', 'job_recurrence_rule', ['tenant_id'])
op.create_index('ix_job_recurrence_rule_next_job_at', 'job_recurrence_rule', ['next_job_at'],
    postgresql_where=sa.text('is_active = true'))
op.create_index('ix_job_recurrence_rule_customer_id', 'job_recurrence_rule', ['customer_id'])

# Triggers (read existing migration for the exact trigger installation pattern)
op.execute("SELECT create_audit_log_trigger('job_recurrence_rule')")
op.execute("SELECT create_updated_at_trigger('job_recurrence_rule')")
op.execute("""
    CREATE TRIGGER immutable_tenant_id_job_recurrence_rule
    BEFORE UPDATE ON job_recurrence_rule
    FOR EACH ROW EXECUTE FUNCTION guard_tenant_id_immutability();
""")
```

> **Verify trigger function names in pre-work**: Run `SELECT proname FROM pg_proc WHERE proname LIKE '%audit%' OR proname LIKE '%updated_at%' OR proname LIKE '%tenant%' LIMIT 20;` to confirm exact function names before using them.

### Migration 2: Add `recurrence_rule_id` to `job`

```bash
alembic revision -m "b21_add_recurrence_rule_id_to_job"
```

Simple nullable FK — no 3-part pattern needed (nullable, no backfill required):

```python
def upgrade():
    op.add_column('job', sa.Column(
        'recurrence_rule_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('job_recurrence_rule.id'),
        nullable=True
    ))
    op.create_index('ix_job_recurrence_rule_id', 'job', ['recurrence_rule_id'])

def downgrade():
    op.drop_index('ix_job_recurrence_rule_id', table_name='job')
    op.drop_column('job', 'recurrence_rule_id')
```

### Migration 3: Seed `recurring_job_scheduled` communication templates

```bash
alembic revision -m "b21_seed_recurring_job_scheduled_templates"
```

Data migration — verify `communication_template` column names via MCP query #3 before writing. The `ON CONFLICT` clause requires knowing the unique constraint on `(template_code, channel)` — verify with:
```sql
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint 
WHERE conrelid = 'communication_template'::regclass AND contype IN ('u','p');
```

```python
def upgrade():
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO communication_template (template_code, channel, subject, body_template, is_active, tenant_id)
        VALUES
          ('recurring_job_scheduled', 'sms', NULL,
           'Hi {{customer_name}}, your scheduled {{service_description}} with {{company_name}} is confirmed for {{scheduled_date}} at {{scheduled_time}}. Reply STOP to opt out.',
           true, NULL),
          ('recurring_job_scheduled', 'email',
           'Your {{service_description}} is scheduled',
           'Hi {{customer_name}},\n\nYour scheduled {{service_description}} with {{company_name}} is confirmed.\n\nDate: {{scheduled_date}}\nTime: {{scheduled_time}}\nAddress: {{site_address}}\n\nIf you need to reschedule, please contact us at {{company_phone}}.\n\nThank you,\n{{company_name}}',
           true, NULL)
        ON CONFLICT DO NOTHING
    """)

def downgrade():
    op.execute("""
        DELETE FROM communication_template 
        WHERE template_code = 'recurring_job_scheduled'
        AND tenant_id IS NULL
    """)
```

### Run all 3 migrations — verify cycle

```bash
alembic upgrade head
alembic downgrade -1   # verify migration 3 downgrade
alembic upgrade head
alembic downgrade -1   # verify migration 2 downgrade
alembic upgrade head
alembic downgrade -1   # verify migration 1 downgrade
alembic upgrade head
alembic current        # must show new head revision
```

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — SQLModel Classes

In `backend/app/models/fulfillment.py`, add `JobRecurrenceRule` class (read the file first for exact import and mixin patterns):

```python
class JobRecurrenceRule(StandardAuditMixin, table=True):
    __tablename__ = "job_recurrence_rule"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    customer_id: uuid.UUID = Field(foreign_key="customer.id", nullable=False)
    site_id: uuid.UUID = Field(foreign_key="site.id", nullable=False)
    pattern: str = Field(max_length=20)            # daily|weekly|monthly|annually
    interval_count: int = Field(default=1, ge=1)
    starts_on: date = Field(nullable=False)
    ends_on: Optional[date] = Field(default=None)
    max_occurrences: Optional[int] = Field(default=None)
    occurrences_created: int = Field(default=0)
    next_job_at: Optional[datetime] = Field(default=None)
    last_job_created_at: Optional[datetime] = Field(default=None)
    estimated_duration_minutes: Optional[int] = Field(default=None)
    default_tech_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id")
    notes_template: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
```

Also update `Job` model — add:
```python
recurrence_rule_id: Optional[uuid.UUID] = Field(default=None, foreign_key="job_recurrence_rule.id")
```

Run `python generate_db_model_map.py` after model changes.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — Request/Response Schemas

Create `backend/api/schemas/recurrence.py` (new file):

```python
# backend/api/schemas/recurrence.py
# Read api/schemas/schemas.py and api/schemas/quotes.py for the established pattern before writing

from pydantic import BaseModel, model_validator, Field
from datetime import date, datetime
from typing import Optional, Literal
import uuid

RecurrencePattern = Literal["daily", "weekly", "monthly", "annually"]


class RecurrenceRuleCreate(BaseModel):
    customer_id: uuid.UUID
    site_id: uuid.UUID
    pattern: RecurrencePattern
    interval_count: int = Field(default=1, ge=1)
    starts_on: date
    ends_on: Optional[date] = None
    max_occurrences: Optional[int] = Field(default=None, ge=1)
    estimated_duration_minutes: Optional[int] = Field(default=None, ge=1)
    default_tech_user_id: Optional[uuid.UUID] = None
    notes_template: Optional[str] = None

    @model_validator(mode="after")
    def validate_end_conditions(self):
        if self.ends_on and self.starts_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be after starts_on")
        if self.ends_on and self.max_occurrences:
            raise ValueError("Specify ends_on OR max_occurrences, not both")
        return self


class RecurrenceRuleUpdate(BaseModel):
    """Only these fields are patchable. Pattern/interval/starts_on are immutable."""
    is_active: Optional[bool] = None
    ends_on: Optional[date] = None
    max_occurrences: Optional[int] = Field(default=None, ge=1)
    default_tech_user_id: Optional[uuid.UUID] = None
    notes_template: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(default=None, ge=1)


class RecurrenceRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    site_id: uuid.UUID
    pattern: str
    interval_count: int
    starts_on: date
    ends_on: Optional[date]
    max_occurrences: Optional[int]
    occurrences_created: int
    next_job_at: Optional[datetime]
    last_job_created_at: Optional[datetime]
    estimated_duration_minutes: Optional[int]
    default_tech_user_id: Optional[uuid.UUID]
    notes_template: Optional[str]
    is_active: bool
    first_job_id: Optional[uuid.UUID] = None  # only set on POST response


class RecurrenceRuleListItem(BaseModel):
    id: uuid.UUID
    pattern: str
    interval_count: int
    customer_name: Optional[str]
    site_address: Optional[str]
    next_job_at: Optional[datetime]
    occurrences_created: int
    is_active: bool
    default_tech_display_name: Optional[str]


class RecurrenceRuleListResponse(BaseModel):
    items: list[RecurrenceRuleListItem]
    total: int
```

---

## Task 4 — API Routes

Create `backend/api/routes/job_recurrence_rules.py`. Read `api/routes/jobs.py` and `api/routes/customers.py` for the full established pattern (router prefix, test endpoints, IDOR patterns, audit context).

### Key implementation notes:

**`_create_rule_impl()`** — called by both POST and POST/test endpoints:
1. IDOR-validate `customer_id` belongs to tenant: `select(Customer).where(Customer.id == req.customer_id, Customer.tenant_id == tenant_id)`
2. IDOR-validate `site_id` belongs to customer: `select(Site).where(Site.id == req.site_id, Site.customer_id == req.customer_id)`
3. IDOR-validate `default_tech_user_id` belongs to tenant (if provided): check `tenant_user` table
4. Create `JobRecurrenceRule` row
5. Compute initial `next_job_at` = `starts_on` as datetime (noon UTC)
6. Call `_create_job_from_rule()` to generate the first job immediately
7. Advance `next_job_at` to the NEXT occurrence after `starts_on`
8. Set `occurrences_created = 1`
9. db.commit()
10. Enqueue notification: `_enqueue_recurring_job_notification.delay(str(rule.id), str(first_job.id))`
11. Return `RecurrenceRuleResponse` with `first_job_id`

**`_compute_next_job_at(pattern, interval_count, from_date: date) -> date`** — pure function:
- `daily` → `from_date + timedelta(days=interval_count)`
- `weekly` → `from_date + timedelta(weeks=interval_count)`
- `monthly` → `from_date + relativedelta(months=interval_count)` (requires `python-dateutil` — check if already in `requirements.txt`)
- `annually` → `from_date + relativedelta(years=interval_count)`

**Error codes**:
- 404: rule not found (or belongs to different tenant)
- 422: `ends_on` before `starts_on`; invalid `customer_id`/`site_id` cross-ownership
- 409: rule already deactivated (trying to delete an already-inactive rule is silently OK — idempotent)

Register router in `app/main.py`:
```python
from api.routes import job_recurrence_rules
app.include_router(job_recurrence_rules.router, prefix="/api/v1")
```

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 5 — Celery Beat Task

Create `backend/tasks/recurring_jobs.py`. Read `tasks/notification_worker.py` AND `services/template_renderer.py` FIRST to understand how templates are dispatched before writing `_enqueue_recurring_job_notification_impl`.

**`_compute_next_job_at()`** and **`_create_job_from_rule()`** — implement as described in design doc §E.

**Beat task registration** in `core/celery_app.py`:
1. Add `"tasks.recurring_jobs"` to the `imports` list
2. Add to `beat_schedule`:
```python
"generate-due-recurring-jobs": {
    "task": "tasks.recurring_jobs.generate_due_recurring_jobs",
    "schedule": crontab(hour=6, minute=0),
},
```

> Verify `crontab` is already imported in `celery_app.py`. If not, add: `from celery.schedules import crontab`.

**Check `python-dateutil` availability**:
```bash
grep "dateutil\|python-dateutil" backend/requirements.txt
```
If not present: add `python-dateutil>=2.9.0` to `requirements.txt` and `pip install python-dateutil`.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 6 — Write Tests

### Test file 1: `backend/tests/domains/field_operations/test_b21_recurrence_rule_crud.py`

```python
pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]
```

Tests (8 total):
1. `test_create_rule_creates_first_job` — POST to `/test` creates rule AND a job (verify job has `recurrence_rule_id` set)
2. `test_create_rule_sets_next_job_at` — `next_job_at` is set to the NEXT occurrence (not `starts_on`)
3. `test_create_rule_invalid_customer_tenant` — customer belonging to second_tenant returns 404 (IDOR protection)
4. `test_create_rule_ends_on_before_starts_on` — returns 422
5. `test_list_rules_tenant_scoped` — only tenant's own rules returned
6. `test_update_rule_pause` — PATCH `is_active: false` → rule.is_active becomes false
7. `test_update_rule_immutable_pattern` — PATCH with `pattern` field ignored (not in schema)
8. `test_delete_rule_soft_deletes` — DELETE sets `is_active = false`; job still exists

### Test file 2: `backend/tests/domains/field_operations/test_b21_recurrence_compute.py`

```python
pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]
```

Tests (6 total — pure function tests, no DB needed for `_compute_next_job_at`):
1. `test_daily_next_date` — daily, interval=1 → next day
2. `test_weekly_next_date` — weekly, interval=2 → 14 days later
3. `test_monthly_next_date` — monthly, interval=1 → same day next month
4. `test_monthly_next_date_end_of_month` — Jan 31 + 1 month → Feb 28 (dateutil handles this)
5. `test_annually_next_date` — annually, interval=1 → same day next year
6. `test_interval_count_respected` — weekly, interval=3 → 21 days later

### Test file 3: `backend/tests/domains/field_operations/test_b21_beat_task.py`

```python
pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]
```

Tests (5 total — test `_generate_due_recurring_jobs_impl()` directly, mock `_enqueue_recurring_job_notification.delay`):
1. `test_beat_creates_job_for_due_rule` — rule with `next_job_at` in past → job created; `occurrences_created` incremented; `next_job_at` advanced
2. `test_beat_skips_inactive_rule` — `is_active=false` rule not processed
3. `test_beat_deactivates_expired_rule` — rule where `ends_on` is in past → `is_active` set to false
4. `test_beat_deactivates_maxed_rule` — rule where `occurrences_created >= max_occurrences` → `is_active` set to false
5. `test_beat_skips_future_rule` — rule with `next_job_at` in future → not processed

---

## Test Requirements

- Domain: `field_operations` → folder `tests/domains/field_operations/`
- `pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]`
- Use `client` fixture (never module-level `TestClient`)
- Use `test_tenant`, `test_user` fixtures — no hardcoded UUIDs
- Use `second_tenant` for IDOR/tenant-isolation tests
- Mock `_enqueue_recurring_job_notification.delay` with `unittest.mock.patch` in beat task tests
- `mock_entitlement_allowed` autouse applies — no changes needed for this batch
- Test `_compute_next_job_at` as a pure function — no DB, no client needed

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite + Export

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Domain-specific check
python -m pytest tests/domains/field_operations/ -v 2>&1 | tail -20

# Regenerate OpenAPI
python export_openapi_json.py
grep -A 5 "job-recurrence-rules" backend/openapi_schema_map.md

# Regenerate model map
python generate_db_model_map.py
grep "JobRecurrenceRule" backend/db_models_map.md

# Update schema JSON — schema_manager.py is a CRUD script, NOT a sync script
# Run --help first to see available commands (set, delete, inspect, etc.)
python schema_manager.py --help
# Then use the appropriate CRUD command for your new tables/columns, e.g.:
# python schema_manager.py set job_recurrence_rule id uuid ...

echo "=== B21-PYTHON FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing failures confirmed (or confirmed with Tom)
- [ ] All 7 MCP pre-work queries run — results recorded; no unexpected findings
- [ ] All source files read before coding (`fulfillment.py`, `jobs.py`, `notification_worker.py`, `template_renderer.py`, `celery_app.py`)
- [ ] `_generate_job_number()` location confirmed via grep before use
- [ ] `crontab` import in `celery_app.py` confirmed before adding Beat schedule
- [ ] **Migration 1**: `job_recurrence_rule` table with CHECK constraints, indexes, triggers — upgrade/downgrade cycle passes
- [ ] **Migration 2**: `job.recurrence_rule_id` nullable FK — upgrade/downgrade cycle passes
- [ ] **Migration 3**: `recurring_job_scheduled` sms + email templates seeded — `ON CONFLICT DO NOTHING`; upgrade/downgrade cycle passes
- [ ] `JobRecurrenceRule` SQLModel class added to `fulfillment.py`
- [ ] `Job.recurrence_rule_id` nullable FK field added to `Job` model
- [ ] `api/schemas/recurrence.py` created — `RecurrenceRuleCreate` validates `ends_on`/`max_occurrences` mutual exclusion
- [ ] `api/routes/job_recurrence_rules.py` created — 5 endpoints + 5 `/test` counterparts; all IDOR-safe
- [ ] Router registered in `app/main.py`
- [ ] `set_audit_context_sync()` called in POST, PATCH, DELETE endpoints
- [ ] All errors follow RFC 7807 Problem Details format
- [ ] `tasks/recurring_jobs.py` created — `_compute_next_job_at()` pure function; `_create_job_from_rule()` creates job + assigns tech; Beat task + notification task both use two-layer pattern
- [ ] `core/celery_app.py` updated — `tasks.recurring_jobs` in imports; `generate-due-recurring-jobs` Beat schedule at `crontab(hour=6, minute=0)`
- [ ] All 3 test files created in `tests/domains/field_operations/` with correct `pytestmark`
- [ ] `python export_openapi_json.py` run — new endpoints appear in `openapi_schema_map.md`
- [ ] `python generate_db_model_map.py` run — `JobRecurrenceRule` in `db_models_map.md`
- [ ] `python schema_manager.py --help` run first; then appropriate CRUD command used to update `pilot-db-schema-v2.6h.json` for new tables/columns
- [ ] **Phase 1**: All unit tests pass — zero failures
- [ ] **Phase 2**: Full test suite passes — zero failures including integration
- [ ] Final test count documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §Phase 1 Batch 10

---

## Handoff Instructions

After all DoD items complete:
1. Run `python export_openapi_json.py` — confirm `openapi.json` + `openapi_schema_map.md` updated
2. Commit all changes
3. **Notify FE-B31 (React web) AND MOB-B9 (React Native) simultaneously — both can start in parallel**
4. Both engineers' first step: `pnpm sync-api-types`

---

## Completion Summary

Add to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 10:

```markdown
### B21 — Recurring Jobs Backend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [3 migrations: job_recurrence_rule table, job.recurrence_rule_id FK, template seed]
- [5 CRUD endpoints + /test counterparts]
- [generate_due_recurring_jobs Beat task at 06:00 UTC]
- [recurring_job_scheduled notification dispatch]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/migrations/versions/[ts]-b21_create_job_recurrence_rule.py` | Created |
| `backend/migrations/versions/[ts]-b21_add_recurrence_rule_id_to_job.py` | Created |
| `backend/migrations/versions/[ts]-b21_seed_recurring_job_scheduled_templates.py` | Created |
| `backend/app/models/fulfillment.py` | Updated |
| `backend/api/schemas/recurrence.py` | Created |
| `backend/api/routes/job_recurrence_rules.py` | Created |
| `backend/app/main.py` | Updated |
| `backend/tasks/recurring_jobs.py` | Created |
| `backend/core/celery_app.py` | Updated |
| `backend/openapi.json` + `openapi_schema_map.md` | Regenerated |
| `backend/db_models_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/field_operations/test_b21_recurrence_rule_crud.py` | `domain_field_operations` | 8 | ✅ |
| `tests/domains/field_operations/test_b21_recurrence_compute.py` | `domain_field_operations` | 6 | ✅ |
| `tests/domains/field_operations/test_b21_beat_task.py` | `domain_field_operations` | 5 | ✅ |
```
