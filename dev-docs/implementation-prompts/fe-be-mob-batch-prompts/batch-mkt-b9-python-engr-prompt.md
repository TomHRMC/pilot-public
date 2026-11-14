# Implementation Prompt: MKT-B9 Part A — Waitlist Form: State + Notes Fields + Newsletter Admin Notification (Backend)

**Mode**: Pilot Python Engineer
**Batch**: MKT-B9-A
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P0 Marketing Website
**Design doc**: `dev-docs/marketing-analysis/design-specs/mkt-b9-design-spec.md`
**Estimated session**: 1.5–2.5 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: MKT-B9-B (React Engineer) — runs after A-6 handoff

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 4**: Alembic migration MUST be a blank migration (`alembic revision -m "..."`) — never `--autogenerate`. Only `op.add_column()` + `op.drop_column()` are needed here.
- **Rule 1**: Never guess column names. MCP pre-work below confirms the live schema state — verify before writing any migration or model code.
- **Rule 3**: After updating the endpoint, run `python export_openapi_json.py` — the React Engineer needs the updated `openapi_schema_map.md` to start Part B.
- **Rule 2**: After updating the model file, regenerate `backend/db_models_map.md` via `python generate_db_model_map.py`.
- **Rule 11**: Fix any failing test immediately — do not proceed while tests are failing.
- **Marketing endpoints are unauthenticated**: These routes do NOT use `require_permission()`, `get_current_user()`, or `set_audit_context_sync()`. Do not add any of those — they are public form endpoints by design.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Fix any pre-existing failures before touching any file.

---

## Pre-Work: Run MCP Verification Queries

Run all of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Confirm current columns on marketing_waitlist_signup
-- Expected: 12 columns (id, email, trade, company_size, source, utm_source,
--           utm_medium, utm_campaign, created_at, converted_at, is_active, name)
-- state and notes should NOT be present yet
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'marketing_waitlist_signup'
ORDER BY ordinal_position;

-- 2. Confirm current Alembic head revision
SELECT version_num FROM public.alembic_version;

-- 3. Confirm the marketing route exists in the backend
-- (just a table existence check — no data needed)
SELECT COUNT(*) FROM marketing_waitlist_signup;
```

> **MCP Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE via MCP.

**If `state` or `notes` already appear in query 1 → STOP and ask Tom** — someone may have run this migration already.

---

## Pre-Work: Read These Source Files

```
backend/app/models/marketing.py
  ← Understand exact MarketingWaitlistSignup field definition pattern before adding state/notes

backend/api/schemas/marketing.py
  ← Understand WaitlistSignupRequest before adding state/notes fields

backend/api/routes/marketing.py
  ← Find the waitlist POST handler — read the MarketingWaitlistSignup instantiation
    to know exactly where to add state= and notes= arguments

backend/migrations/versions/ (most recent marketing migration)
  ← Use as migration pattern reference — find with: ls -la backend/migrations/versions/ | grep mkt
```

---

## Task A-1 — Alembic Migration

Create a blank migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "mkt_b9_add_state_notes_to_marketing_waitlist_signup"
```

Open the generated file and implement:

```python
import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        "marketing_waitlist_signup",
        sa.Column("state", sa.String(), nullable=True),
    )
    op.add_column(
        "marketing_waitlist_signup",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketing_waitlist_signup", "notes")
    op.drop_column("marketing_waitlist_signup", "state")
```

**Why no NOT NULL / backfill**: Both columns are intentionally nullable — optional form fields. No 3-part pattern needed.

**Why no `SET LOCAL session_replication_role = 'replica'`**: No seed data INSERTs — pure schema change only.

Run the migration cycle:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show the new revision as head
```

Verify via MCP that `state` and `notes` now appear:

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'marketing_waitlist_signup'
ORDER BY ordinal_position;
```

Expected: 14 columns. `state` (varchar, nullable), `notes` (text, nullable) at the bottom.

---

## Task A-2 — Model Update

In `backend/app/models/marketing.py`, add two fields to `MarketingWaitlistSignup` after the `company_size` field:

```python
state: str | None = Field(
    default=None,
    sa_column=Column(String, nullable=True),
)
notes: str | None = Field(
    default=None,
    sa_column=Column(Text, nullable=True),
)
```

Read the existing field definitions (especially `name`) for the exact pattern before writing. The new fields follow the same `str | None = Field(default=None, sa_column=Column(..., nullable=True))` pattern.

After editing the model file:

```bash
python generate_db_model_map.py
grep "state\|notes" backend/db_models_map.md
# Both should appear under MarketingWaitlistSignup
```

---

## Task A-3 — Schema Update

In `backend/api/schemas/marketing.py`, add to `WaitlistSignupRequest` after the existing fields:

```python
state: str | None = None
notes: str | None = None
```

Place `state` after `company_size`, `notes` after `state`, matching the logical form field order.

**No `field_validator` needed** for either field — these are free-form optional strings. The existing email TLD validator is unchanged.

---

## Task A-4 — Route Handler Update

In `backend/api/routes/marketing.py`, find the waitlist POST handler. Read the existing `MarketingWaitlistSignup(...)` instantiation, then add the two new fields:

```python
signup = MarketingWaitlistSignup(
    email=payload.email,
    name=payload.name,
    trade=payload.trade,
    company_size=payload.company_size,
    source=payload.source,
    utm_source=payload.utm_source,
    utm_medium=payload.utm_medium,
    utm_campaign=payload.utm_campaign,
    state=payload.state,    # NEW
    notes=payload.notes,    # NEW
)
```

The idempotency handling for duplicate email already exists in the route — do not change it. Only the instantiation block changes.

**Intermediate unit test run**:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```
All tests must pass before proceeding to A-5.

---

## Task A-0 (Addendum) — Newsletter Admin Notification Fix

**File**: `backend/tasks/marketing_notifications.py`

Read the full file before editing. The `send_newsletter_confirmation` task (line ~224) sends a confirmation email to the subscriber but **has no admin notification**. Every other marketing notification task (`send_waitlist_confirmation`, `send_contact_confirmation`, `send_application_confirmation`) sends both a subscriber email AND an admin notification. The newsletter task is missing its admin half.

**Root cause**: The original implementation simply omitted the second `send_email()` call. No design intent — it's a gap.

**Fix**: Add a second `send_email()` call inside `send_newsletter_confirmation` after the existing subscriber send, routing to `settings.NEWSLETTER_EMAIL_ADDR`.

**Confirm the config variable exists first** (it does — added in MKT-B6-A):
```bash
grep "NEWSLETTER_EMAIL_ADDR" backend/core/config.py
# Expected: NEWSLETTER_EMAIL_ADDR: str = "newsletter@pilotfortrades.com"
```

**Implementation** — add after the existing `subscriber_result = send_email(...)` block:

```python
# 2. Admin notification to newsletter@
admin_body = (
    f"<h3>New Newsletter Subscriber</h3>"
    f"<ul>"
    f"<li><strong>Email:</strong> {email}</li>"
    f"<li><strong>Source:</strong> {source or 'not specified'}</li>"
    f"<li><strong>Trade interest:</strong> {', '.join(trade_interest) if trade_interest else 'not specified'}</li>"
    f"</ul>"
)
admin_result = send_email(
    to=settings.NEWSLETTER_EMAIL_ADDR,
    subject=f"New newsletter subscriber: {email}",
    body=admin_body,
)
```

Update the return dict to include `admin_result`:

```python
return {
    "status": "sent",
    "subscriber_result": subscriber_result,
    "admin_result": admin_result,  # NEW
}
```

No migration, no schema changes, no config changes. `settings.NEWSLETTER_EMAIL_ADDR` is already defined.

**Intermediate unit test run** after this change:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task A-5 — Tests

**Test file**: `backend/tests/domains/platform_infrastructure/test_mkt_b9_waitlist_fields.py`

```python
import pytest

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]
```

**5 required tests**:

```python
def test_waitlist_signup_with_state_and_notes(client):
    """New state + notes fields are accepted and persisted."""
    res = client.post("/api/v1/marketing/waitlist/test", json={
        "name": "Dave S.",
        "email": "dave@teststater.example.com",
        "trade": "electrical",
        "company_size": "2-5",
        "source": "test",
        "state": "PA",
        "notes": "I run a 3-person shop in Philly.",
        "cf_turnstile_response": "test-token",
    })
    assert res.status_code in (200, 201)
    # Verify state and notes are stored — re-fetch or check response if schema includes them

def test_waitlist_signup_without_state_or_notes(client):
    """state and notes are optional — omitting both is valid."""
    res = client.post("/api/v1/marketing/waitlist/test", json={
        "name": "Mike R.",
        "email": "mike@testnostate.com",
        "trade": "electrical",
        "company_size": "solo",
        "source": "test",
        "cf_turnstile_response": "test-token",
    })
    assert res.status_code in (200, 201)

def test_waitlist_signup_with_state_only(client):
    """state provided without notes is valid."""
    res = client.post("/api/v1/marketing/waitlist/test", json={
        "name": "Chris W.",
        "email": "chris@teststateonly.com",
        "trade": "electrical",
        "company_size": "solo",
        "source": "test",
        "state": "DC",
        "cf_turnstile_response": "test-token",
    })
    assert res.status_code in (200, 201)

def test_waitlist_signup_with_outside_us_state(client):
    """'Outside the US' is a valid state value."""
    res = client.post("/api/v1/marketing/waitlist/test", json={
        "name": "Test User",
        "email": "test@testoutsideus.com",
        "trade": "electrical",
        "company_size": "solo",
        "source": "test",
        "state": "Outside the US",
        "cf_turnstile_response": "test-token",
    })
    assert res.status_code in (200, 201)

def test_missing_required_trade_still_422(client):
    """state/notes being optional doesn't change required field behavior."""
    res = client.post("/api/v1/marketing/waitlist/test", json={
        "name": "Test",
        "email": "test@testerror.com",
        "company_size": "solo",
        "source": "test",
        "state": "PA",
        "cf_turnstile_response": "test-token",
        # trade is intentionally omitted
    })
    assert res.status_code == 422
```

**Note on `/test` endpoint**: Read the existing marketing route to confirm the `/waitlist/test` unauthenticated endpoint exists. If it does not, the Python Engineer must add it following the standard `TestUserContext` pattern from the inclusions file §11. Check first:

```bash
grep -n "waitlist/test\|waitlist.*test" backend/api/routes/marketing.py
```

---

## Task A-6 — OpenAPI Regeneration + Handoff

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
grep -A 10 "waitlist" backend/openapi_schema_map.md
```

Verify `state` and `notes` appear in the request schema for the waitlist endpoint in `openapi_schema_map.md`. Both should show as optional (`required: false` or absence from the `required` array).

```bash
python schema_manager.py --help   # CRUD script — read available commands first (set, delete, inspect, etc.)
# Then use the appropriate CRUD command for state + notes additions
```

**Handoff to React Engineer**: Commit all changes. Notify that Part B (React) can begin. Part B's first step is verifying `state` and `notes` appear in `openapi_schema_map.md`.

---

## Final Verification

### Phase 1 — Unit tests (run after each task group)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full suite (once, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/platform_infrastructure/ -v 2>&1 | tail -20
grep -A 5 "waitlist" backend/openapi_schema_map.md
echo "=== MKT-B9-A FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MKT-B9-A

- [ ] Regression baseline captured (unit tests: `X passed`)
- [ ] MCP queries run — confirmed `state` and `notes` absent from `marketing_waitlist_signup` before migration
- [ ] All source files read before writing any code
- [ ] **A-0**: `send_newsletter_confirmation` updated — admin `send_email()` to `settings.NEWSLETTER_EMAIL_ADDR` added; `admin_result` in return dict; `settings.NEWSLETTER_EMAIL_ADDR` confirmed in `config.py` before editing
- [ ] A-1: Alembic migration created and tested (upgrade → downgrade → upgrade → current)
- [ ] A-1: MCP confirms `state` (varchar nullable) + `notes` (text nullable) now exist on table
- [ ] A-2: `MarketingWaitlistSignup` model updated with `state` + `notes` fields
- [ ] A-2: `python generate_db_model_map.py` run — both fields appear in `db_models_map.md`
- [ ] A-3: `WaitlistSignupRequest` schema updated with `state: str | None = None` + `notes: str | None = None`
- [ ] A-4: Route handler updated — `state=payload.state`, `notes=payload.notes` added to model instantiation
- [ ] A-5: Test file created — 5 tests, all pass, domain marker + `pytest.mark.unit` declared
- [ ] A-6: `python export_openapi_json.py` run — `state` + `notes` visible in `openapi_schema_map.md`
- [ ] A-6: `python schema_manager.py --help` run; then appropriate CRUD command used — `pilot-db-schema-v2.6h.json` updated
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`)
- [ ] **Phase 2**: Full suite passes (`pytest`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §P0

---

## Completion Summary

After all DoD items pass, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §P0:

```markdown
### MKT-B9-A — Waitlist State + Notes Fields (Backend): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed
**Final**: X+5 passed (+5 new tests)

#### What Was Accomplished
- `send_newsletter_confirmation` fixed — admin notification to `newsletter@pilotfortrades.com` now sent on every subscriber (was missing since original implementation)
- Alembic migration adds `state` (VARCHAR nullable) + `notes` (TEXT nullable) to `marketing_waitlist_signup`
- `MarketingWaitlistSignup` model updated with both fields
- `WaitlistSignupRequest` schema updated — both fields optional
- Waitlist POST route handler maps new fields
- 5 unit tests in `platform_infrastructure` domain

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/tasks/marketing_notifications.py` | Updated — admin send_email() added to send_newsletter_confirmation |
| `backend/migrations/versions/YYYY_MM_DD_HHmm-{hash}_mkt_b9_add_state_notes_to_marketing_waitlist_signup.py` | Created |
| `backend/app/models/marketing.py` | Updated — state + notes fields |
| `backend/api/schemas/marketing.py` | Updated — state + notes in WaitlistSignupRequest |
| `backend/api/routes/marketing.py` | Updated — state + notes in model instantiation |
| `backend/tests/domains/platform_infrastructure/test_mkt_b9_waitlist_fields.py` | Created |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/db_models_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via schema_manager.py |
```
