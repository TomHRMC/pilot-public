# Implementation Prompt: MKT-B6 Part A — Careers Backend + Email Routing Refactor

**Mode**: Pilot Python Engineer
**Batch**: MKT-B6 Part A
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` — P0 section
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b6-design-spec.md`
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: MKT-B6 Part B (React Engineer) — runs after this batch; React Engineer's first step is `pnpm sync-api-types`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document
- **`dev-docs/marketing-analysis/design-specs/mkt-b6-design-spec.md`** — every section (A–H)

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify before writing any migration or query. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → run `python generate_db_model_map.py`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py`.
- **Rule 4**: All Alembic migrations MUST be **blank** (`alembic revision -m "..."`) — never `--autogenerate`.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture.
- **Rule 11**: If ANY test fails — fix it before declaring done.
- **Email routing rule**: `SUPPORT_EMAIL_ADDRESS` is used by the help system (`backend/tasks/help_corpus.py`). Do NOT remove it from `config.py`. Only the three marketing notification tasks are being migrated to per-form vars.
- **`name` field is nullable**: The waitlist `name` migration must NOT use the 3-part NOT NULL pattern. The field stays nullable — existing rows have no name and there is no meaningful backfill. Just `ADD COLUMN ... NULL`.
- **Rate limit on application endpoint**: Use `5/hour` (stricter than the 10/hour contact form).

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Fix any pre-existing failures before proceeding.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm marketing_waitlist_signup has NO name column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'marketing_waitlist_signup'
ORDER BY ordinal_position;

-- 2. Confirm marketing_job_application does NOT exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'marketing_job_application';

-- 3. Count existing waitlist rows (verify backfill not needed — name stays nullable)
SELECT COUNT(*) FROM marketing_waitlist_signup;

-- 4. Confirm current alembic head
SELECT version_num FROM public.alembic_version;

-- 5. Confirm SUPPORT_EMAIL_ADDRESS is still needed by help system
-- (just verify help_feedback_submission table exists to confirm help system is active)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'help_feedback_submission';
```

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE. If a query fails → STOP and ask Tom.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/core/config.py
  ← Understand the Settings class structure; find SUPPORT_EMAIL_ADDRESS location;
    confirm NEWSLETTER_UNSUBSCRIBE_SECRET and MARKETING_SITE_BASE_URL placement pattern

backend/tasks/marketing_notifications.py
  ← Read the FULL file — understand all three existing tasks before modifying any

backend/app/models/marketing.py
  ← Full file — understand MarketingWaitlistSignup structure before adding name field

backend/api/schemas/marketing.py
  ← Full file — understand WaitlistSignupRequest before adding name; see pattern for new schemas

backend/api/routes/marketing.py
  ← Full file — understand _waitlist_signup_impl, _contact_submission_impl, _dispatch pattern

backend/tasks/help_corpus.py
  ← Find send_feedback_email — confirm it still uses SUPPORT_EMAIL_ADDRESS (do NOT break it)
```

Also run:
```bash
grep -n "SUPPORT_EMAIL_ADDRESS" backend/tasks/*.py
```
Verify `help_corpus.py` uses `SUPPORT_EMAIL_ADDRESS` — this is why we do NOT remove it.

---

## Background — What This Batch Does

Currently all three marketing form admin notifications route to a single `SUPPORT_EMAIL_ADDRESS` env var. This batch:
1. Adds 4 per-form email address env vars + 1 roles list var
2. Updates the 3 existing Celery tasks to use their dedicated vars
3. Adds `name` (nullable) to the waitlist model + migration
4. Creates a new `MarketingJobApplication` model + migration + Celery task + endpoint

---

## Task A-01 — Config: Add 5 New Env Vars

**File**: `backend/core/config.py`

After the existing `SUPPORT_EMAIL_ADDRESS = "support@pilotfortrades.com"` line, add:

```python
# MKT-B6: Per-form notification routing
# Each marketing form routes admin notifications to its own inbox.
# SUPPORT_EMAIL_ADDRESS above is retained for the help system (help_corpus.py).
NEWSLETTER_EMAIL_ADDR: str = "newsletter@pilotfortrades.com"
SALES_EMAIL_ADDR: str = "sales@pilotfortrades.com"
CONTACT_US_EMAIL_ADDR: str = "info@pilotfortrades.com"
CAREERS_EMAIL_ADDR: str = "careers@pilotfortrades.com"

# Comma-separated list of open role titles for the careers form dropdown.
# Update this value in .env without a code deploy to change what roles appear.
CAREERS_OPEN_ROLES: str = "AI / ML Engineer,Full-Stack Engineer (Trades Domain),Customer Success (Trades Background a Plus),Sales / Growth"
```

**Intermediate unit test run**:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task A-02 — Notification Tasks: Per-Form Email Routing

**File**: `backend/tasks/marketing_notifications.py`

Read the full file first. Then make three targeted changes:

**Change 1** — `send_waitlist_confirmation`: Find the admin notification `send_email(to=settings.SUPPORT_EMAIL_ADDRESS, ...)` call. Change `to=settings.SUPPORT_EMAIL_ADDRESS` → `to=settings.SALES_EMAIL_ADDR`.

**Change 2** — `send_contact_confirmation`: Find the admin notification `send_email(to=settings.SUPPORT_EMAIL_ADDRESS, ...)` call. Change to `to=settings.CONTACT_US_EMAIL_ADDR`.

**Change 3** — `send_newsletter_confirmation`: Find the admin notification send_email call (if it uses `SUPPORT_EMAIL_ADDRESS`). Change to `to=settings.NEWSLETTER_EMAIL_ADDR`. If it already uses a different var, verify and document.

**Change 4** — Add `send_application_confirmation` at the bottom of the file (see design doc §D Task A-02 for the full task code). Follow the same `@celery_app.task(name="...", bind=True, max_retries=3, default_retry_delay=60)` decorator pattern as the existing tasks.

**Intermediate unit test run**:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task A-03 — Models: Add `name` + New `MarketingJobApplication`

**File**: `backend/app/models/marketing.py`

**Change 1**: In `MarketingWaitlistSignup`, add `name` as the SECOND field (after `id`, before `email`):
```python
name: str | None = Field(
    default=None,
    sa_column=Column(String, nullable=True),
)
```

**Change 2**: Add `MarketingJobApplication` at the bottom of the file. See design doc §D Task A-03 for the full model definition. Follow the exact same patterns as `MarketingContactSubmission` — same mixin-free SQLModel, same `created_at` server default pattern, same index declarations.

After model changes:
```bash
python generate_db_model_map.py
grep "MarketingJobApplication\|MarketingWaitlistSignup" backend/db_models_map.md
```

Verify both appear under **DB Tables**.

**Intermediate unit test run**:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task A-04 — Migration 1: Add `name` to Waitlist

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "mkt_b6_add_name_to_marketing_waitlist_signup"
```

In the generated file:

```python
import sqlalchemy as sa
from alembic import op

def upgrade() -> None:
    # name is nullable — no backfill needed (existing rows have no name)
    op.add_column(
        "marketing_waitlist_signup",
        sa.Column("name", sa.String(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("marketing_waitlist_signup", "name")
```

Test the cycle:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current  # must show new revision
```

---

## Task A-05 — Migration 2: Create `marketing_job_application`

```bash
alembic revision -m "mkt_b6_create_marketing_job_application"
```

See design doc §D Task A-05 for the complete `upgrade()` and `downgrade()` implementation. Use `postgresql.UUID` for the `id` column — import from `sqlalchemy.dialects.postgresql`.

Test the cycle:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current  # must show new revision
```

**Schema JSON sync** after both migrations:
```bash
python schema_manager.py --help   # CRUD script — read available commands first (set, delete, inspect, etc.)
# Then use the appropriate CRUD command for the new table and column
```

---

## Task A-06 — Schemas: Add `name` + New Application Schemas

**File**: `backend/api/schemas/marketing.py`

**Change 1**: In `WaitlistSignupRequest`, add `name` as an optional field after `email`:
```python
name: str | None = None
```

**Change 2**: Add at the bottom of the file (see design doc §D Task A-06 for the full `JobApplicationRequest` + `JobApplicationResponse` class definitions). Follow the exact same `BaseModel` pattern as `ContactSubmissionRequest`.

---

## ⚠️ POST-COMPLETION AMENDMENT — Task A-11 (Added June 27, 2026)

> **Context**: MKT-B6 Part A is complete. This is a single additional task added because live testing showed `me@me.t` (1-char TLD) was accepted by Pydantic's `EmailStr` and stored in the DB. `email-validator==2.3.0` does not enforce minimum TLD length by default. This task adds a `field_validator` to all 4 marketing schemas that have an `email` field.

### Task A-11 — Email Format Validation: Add TLD Length Guard to All Marketing Schemas

**File**: `backend/api/schemas/marketing.py`

Add the following import at the top of the file (if not already present):
```python
import re
from pydantic import field_validator
```

Add the following **class method validator** to EACH of the four marketing schema classes that have an `email: EmailStr` field:
- `WaitlistSignupRequest`
- `ContactSubmissionRequest`
- `NewsletterSubscribeRequest`
- `JobApplicationRequest`

```python
@field_validator("email")
@classmethod
def validate_email_tld(cls, v: str) -> str:
    """
    Pydantic's EmailStr (email-validator 2.x) does not enforce minimum TLD length.
    This validator adds that check: TLD must be at least 2 characters.
    Catches obvious junk like me@me.t which EmailStr accepts.
    """
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', v):
        raise ValueError("Enter a valid email address (e.g. name@example.com)")
    return v.lower()
```

Add this validator to each class directly below the `email: EmailStr` field declaration, before any other fields or methods.

**Test**: After adding, run a quick unit test:
```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest tests/batch_mkt_b6/ -v 2>&1 | tail -10
```

Add one regression test to `tests/batch_mkt_b6/test_mkt_b6_application.py`:
```python
def test_application_submit_invalid_email_tld(client, test_tenant):
    """me@me.t should be rejected — 1-char TLD fails our validator."""
    resp = client.post("/api/v1/marketing/application/test", json={
        "name": "Test",
        "email": "me@me.t",
        "role": "AI / ML Engineer",
        "linkedin_url": "https://linkedin.com/in/test",
        "why_interested": "I want to join.",
        "cf_turnstile_response": "test",
    })
    assert resp.status_code == 422
```

After tests pass, re-run OpenAPI export (email field validators appear in the schema):
```bash
python export_openapi_json.py
```

**Also delete the junk test record from the DB** (this is a one-time manual data fix — not a migration):
```sql
-- Run via postgres-local MCP (read-only) to confirm the record exists first:
SELECT email, subscribed_at FROM marketing_newsletter_subscriber WHERE email = 'me@me.t';

-- Then delete it via psql in your local terminal (NOT via MCP — MCP is read-only):
-- psql -d your_db_name -c "DELETE FROM marketing_newsletter_subscriber WHERE email = 'me@me.t';"
```

---

## Task A-07 — Routes: Update Waitlist + Add Application Endpoints

**File**: `backend/api/routes/marketing.py`

Read the full file first. Then:

**Change 1**: Update imports to include `JobApplicationRequest`, `JobApplicationResponse`, `MarketingJobApplication`, and `send_application_confirmation`.

**Change 2**: In `_waitlist_signup_impl`, update the `MarketingWaitlistSignup(...)` constructor to pass `name=data.name`.

**Change 3**: Add the new `/application` section after the newsletter section. See design doc §D Task A-07 for the full `_application_submit_impl`, `/application/test`, and `/application` route definitions.

**Important**: The application route uses `@limiter.limit("5/hour")` — stricter than the 10/hour used by other marketing forms.

**Intermediate unit test run**:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task A-08 — Update `.env.example`

**File**: `backend/.env.example`

Add after the existing `SUPPORT_EMAIL_ADDRESS=support@pilotfortrades.com` line:

```
NEWSLETTER_EMAIL_ADDR=newsletter@pilotfortrades.com
SALES_EMAIL_ADDR=sales@pilotfortrades.com
CONTACT_US_EMAIL_ADDR=info@pilotfortrades.com
CAREERS_EMAIL_ADDR=careers@pilotfortrades.com
CAREERS_OPEN_ROLES=AI / ML Engineer,Full-Stack Engineer (Trades Domain),Customer Success (Trades Background a Plus),Sales / Growth
```

---

## Task A-09 — Tests

**Domain folder**: `backend/tests/batch_mkt_b6/` (new folder — create it)

Write unit tests for the new `/application` endpoint. Follow the same pattern as existing marketing tests in `backend/tests/batch_mkt_b1_5/`.

Minimum test coverage:
1. `test_application_submit_success` — POST to `/api/v1/marketing/application/test` with valid data → 201, `status="success"`, row exists in DB
2. `test_application_submit_honeypot_blocked` — POST to public endpoint with non-empty honeypot → 400 (use `with override_turnstile():` pattern if it exists, or skip the Turnstile check for the test endpoint)
3. `test_application_submit_missing_required_fields` — POST with missing `name` or `role` → 422
4. `test_waitlist_signup_with_name` — POST to `/api/v1/marketing/waitlist/test` with `name` field → 201, `name` stored in DB
5. `test_waitlist_signup_without_name` — POST without `name` → 201 (backward compat, name is nullable)

Every test file MUST declare:
```python
pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]
```

Use `client` fixture (never module-level TestClient). Use `/test` endpoints (not public endpoints — they skip Turnstile). Scope assertions by inserted ID — never count total rows.

---

## Task A-10 — Regenerate OpenAPI

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify new endpoints appear:
```bash
grep -A 5 "marketing/application" backend/openapi_schema_map.md
grep -A 5 "waitlist" backend/openapi_schema_map.md  # verify name field appears
```

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/batch_mkt_b6/ -v 2>&1 | tail -20
grep -A 5 "marketing/application" backend/openapi_schema_map.md
echo "=== MKT-B6-A FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Regression baseline captured (`pytest -m unit | tail -5`)
- [ ] All 5 MCP pre-work queries run — no unexpected results
- [ ] All mandatory source files read (`config.py`, `marketing_notifications.py`, `models/marketing.py`, `schemas/marketing.py`, `routes/marketing.py`, `help_corpus.py`)
- [ ] `SUPPORT_EMAIL_ADDRESS` confirmed still present and used by `help_corpus.py` (not removed)
- [ ] A-01: 5 new env vars added to `config.py` and `.env.example`
- [ ] A-02: 3 existing notification tasks updated to per-form email vars; `send_application_confirmation` added
- [ ] A-03: `name` (nullable) added to `MarketingWaitlistSignup`; `MarketingJobApplication` model created
- [ ] A-04: Migration 1 — `name` column added, upgrade/downgrade cycle passes
- [ ] A-05: Migration 2 — `marketing_job_application` table created, upgrade/downgrade cycle passes
- [ ] `python schema_manager.py --help` run; then appropriate CRUD command used to update `pilot-db-schema-v2.6h.json` after both migrations
- [ ] A-06: `name` added to `WaitlistSignupRequest`; `JobApplicationRequest` + `JobApplicationResponse` added
- [ ] A-07: Waitlist impl updated for `name`; `/application` + `/application/test` endpoints added
- [ ] A-08: `.env.example` updated
- [ ] A-09: 5 unit tests pass in `tests/batch_mkt_b6/`
- [ ] All new test files use `pytestmark` with `domain_platform_infrastructure` + `unit`
- [ ] No module-level `TestClient` in any test file
- [ ] A-10: `python export_openapi_json.py` run — `marketing/application` appears in `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`)
- [ ] **Phase 2**: Full test suite passes (`pytest`)
- [ ] Final test count (before → after) documented

---

## Completion Summary

After all DoD items are complete, add a Completion Summary to `dev-docs/analysis/pilot-launch-plan.md` MKT-B6 section:

```markdown
### MKT-B6 Part A — Backend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- Added per-form email routing (NEWSLETTER_EMAIL_ADDR, SALES_EMAIL_ADDR, CONTACT_US_EMAIL_ADDR, CAREERS_EMAIL_ADDR)
- Added `name` (nullable) to `marketing_waitlist_signup` via Alembic migration
- Created `marketing_job_application` table + model via Alembic migration
- Added `POST /api/v1/marketing/application` endpoint (rate limit: 5/hour)
- Added `send_application_confirmation` Celery task routing to `CAREERS_EMAIL_ADDR`

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/core/config.py` | Updated — +5 env vars |
| `backend/tasks/marketing_notifications.py` | Updated — 3 tasks rerouted; 1 task added |
| `backend/app/models/marketing.py` | Updated — name field; new model |
| `backend/api/schemas/marketing.py` | Updated — name field; 2 new schemas |
| `backend/api/routes/marketing.py` | Updated — waitlist name; 2 new endpoints |
| `backend/.env.example` | Updated — 5 new vars |
| `backend/migrations/versions/[hash]_mkt_b6_add_name_...py` | Created |
| `backend/migrations/versions/[hash]_mkt_b6_create_job_application.py` | Created |
| `backend/tests/batch_mkt_b6/test_mkt_b6_application.py` | Created |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/batch_mkt_b6/test_mkt_b6_application.py` | `platform_infrastructure` | 5 | ✅ |
```

---

## After This Task — Handoff to React Engineer

After `python export_openapi_json.py` runs and this prompt is complete:

1. Commit all changes
2. React Engineer (MKT-B6 Part B) must run `pnpm sync-api-types` as their first Pre-Work step
3. Hand off `batch-mkt-b6-react-engr-prompt.md` to the React Engineer
