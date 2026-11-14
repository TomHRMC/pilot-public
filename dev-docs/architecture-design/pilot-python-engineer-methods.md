# 🚀 Pilot for Trades Python Engineer Methods — Backend Coding Standards & Patterns

> **Snapshot note:** historical working document, published as last edited during the build and not maintained. Statuses and figures below reflect that date; for current, checked figures see [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../diligence/README.md). The product was never released and never carried customer traffic. "Prod" here means the one pre-release AWS environment, used for the author's own tests.

- [🚀 Pilot for Trades Python Engineer Methods — Backend Coding Standards \& Patterns](#-pilot-for-trades-python-engineer-methods--backend-coding-standards--patterns)
  - [1. Project Structure Reference](#1-project-structure-reference)
  - [2. Environment Setup (Always Required)](#2-environment-setup-always-required)
  - [3. Finding Models: Key Reference Files](#3-finding-models-key-reference-files)
    - [3.1 Model-to-File Mapping](#31-model-to-file-mapping)
    - [3.2 Model Import Reference](#32-model-import-reference)
    - [3.3 API Endpoint Reference — `openapi.json` + `openapi_schema_map.md`](#33-api-endpoint-reference--openapijson--openapi_schema_mapmd)
  - [4. Querying the Database (MCP Tool)](#4-querying-the-database-mcp-tool)
    - [4.1 Pre-Batch Verification Queries](#41-pre-batch-verification-queries)
  - [5. Model Design Standards](#5-model-design-standards)
    - [5.1 SQLModel Base Pattern](#51-sqlmodel-base-pattern)
    - [5.2 Choose the Right Mixin](#52-choose-the-right-mixin)
    - [5.3 Datetime Rules — Always UTC-Aware](#53-datetime-rules--always-utc-aware)
    - [5.4 Soft Delete — Standard Pattern](#54-soft-delete--standard-pattern)
    - [5.5 JSONB Fields](#55-jsonb-fields)
    - [5.6 Enums](#56-enums)
  - [6. SQLModel Query Patterns (CRITICAL)](#6-sqlmodel-query-patterns-critical)
    - [6.1 Basic Select](#61-basic-select)
    - [6.2 Always Filter by `tenant_id` — `db.get()` is BANNED on tenant-scoped models](#62-always-filter-by-tenant_id--dbget-is-banned-on-tenant-scoped-models)
    - [6.3 Create / Update / Delete Cycle](#63-create--update--delete-cycle)
  - [7. Settings \& Configuration](#7-settings--configuration)
  - [8. API Route Design Pattern](#8-api-route-design-pattern)
    - [8.1 Router Setup](#81-router-setup)
    - [8.2 Dual-Endpoint Architecture (Authenticated + Test)](#82-dual-endpoint-architecture-authenticated--test)
    - [8.3 Standard HTTP Methods](#83-standard-http-methods)
  - [9. Authentication \& RBAC](#9-authentication--rbac)
    - [9.1 Dependency Injection Pattern](#91-dependency-injection-pattern)
    - [9.2 Permission Format](#92-permission-format)
    - [9.3 `AuthenticatedUser` Object](#93-authenticateduser-object)
    - [9.4 Audit Context](#94-audit-context)
  - [10. Schema (Pydantic) Design Standards](#10-schema-pydantic-design-standards)
    - [10.1 Request Schema (Create/Update)](#101-request-schema-createupdate)
    - [10.2 Response Schema](#102-response-schema)
    - [10.3 Nested Schemas](#103-nested-schemas)
  - [11. Test Context Endpoints](#11-test-context-endpoints)
  - [12. Middleware Stack (Registered in main.py)](#12-middleware-stack-registered-in-mainpy)
  - [13. Alembic Migration Standards](#13-alembic-migration-standards)
    - [13.1 Always Use Blank Migrations — Never Autogenerate](#131-always-use-blank-migrations--never-autogenerate)
    - [13.2 Migration Verification Loop](#132-migration-verification-loop)
    - [13.3 Raw SQL in Migrations](#133-raw-sql-in-migrations)
    - [13.4 Strict Schema Naming \& Triggers](#134-strict-schema-naming--triggers)
  - [14. Error Handling Conventions](#14-error-handling-conventions)
    - [14.1 Standard HTTP Exceptions](#141-standard-http-exceptions)
    - [14.2 Enum Validation](#142-enum-validation)
  - [15. Known Test Fragility — Audit Event Volume](#15-known-test-fragility--audit-event-volume)
    - [15.1 `test_query_events_returns_tenant_isolated_results` Page-Overflow Risk](#151-test_query_events_returns_tenant_isolated_results-page-overflow-risk)
  - [15b. Common Anti-Patterns — Never Do These](#15b-common-anti-patterns--never-do-these)
  - [16. Standard Implementation Task Workflow](#16-standard-implementation-task-workflow)
    - [16.1 Pre-Work: Establish Regression Baseline](#161-pre-work-establish-regression-baseline)
    - [16.2 The Standard 4-Step Execution Loop](#162-the-standard-4-step-execution-loop)
    - [🛑 CRITICAL CONSTRAINTS](#-critical-constraints)
    - [16.3 API \& Service Layer Refactoring (When Required)](#163-api--service-layer-refactoring-when-required)
    - [16.4 Stop \& Rollback Conditions](#164-stop--rollback-conditions)
    - [16.5 Definition of Done Checklist](#165-definition-of-done-checklist)
    - [16.6 Integration Test Rule: Service Functions with DB Persistence](#166-integration-test-rule-service-functions-with-db-persistence)
  - [17. Celery Task Patterns](#17-celery-task-patterns)
    - [17.1 Periodic Poll Task (no bind, no retry)](#171-periodic-poll-task-no-bind-no-retry)
    - [17.2 Event-Driven Retryable Task (bind=True, max\_retries)](#172-event-driven-retryable-task-bindtrue-max_retries)
    - [17.3 Registering a New Task](#173-registering-a-new-task)
    - [17.4 Testing a Celery Task](#174-testing-a-celery-task)
  - [18. Server-Sent Events (SSE) Endpoint Pattern](#18-server-sent-events-sse-endpoint-pattern)
    - [18.1 Why SSE for Dispatch Board and Sync Indicators](#181-why-sse-for-dispatch-board-and-sync-indicators)
    - [18.2 SSE Endpoint Implementation (FastAPI `StreamingResponse`)](#182-sse-endpoint-implementation-fastapi-streamingresponse)
    - [18.3 Emitting Events from a Write Endpoint](#183-emitting-events-from-a-write-endpoint)
    - [18.4 SSE Anti-Patterns](#184-sse-anti-patterns)
  - [19. Webhook Handler Pattern](#19-webhook-handler-pattern)
    - [19.1 Canonical Webhook Route Structure](#191-canonical-webhook-route-structure)
    - [19.2 Telnyx-Specific Pattern (B11/A59)](#192-telnyx-specific-pattern-b11a59)
    - [19.3 Stripe-Specific Pattern (B14/A76)](#193-stripe-specific-pattern-b14a76)
  - [20. Pre-Commit Staleness Check Pattern](#20-pre-commit-staleness-check-pattern)
    - [20.1 Shared Utility](#201-shared-utility)
    - [20.2 Using the Utility in a Route](#202-using-the-utility-in-a-route)
  - [21. Three-Tier Settings Resolver Pattern](#21-three-tier-settings-resolver-pattern)
    - [21.1 The Three-Tier Chain](#211-the-three-tier-chain)
    - [21.2 Implementation](#212-implementation)
    - [21.3 Usage in a Route](#213-usage-in-a-route)
  - [22. Carrier-Agnostic Adapter Pattern](#22-carrier-agnostic-adapter-pattern)
    - [22.1 Abstract Base Class](#221-abstract-base-class)
    - [22.2 Mock Implementation (for testing without real carrier)](#222-mock-implementation-for-testing-without-real-carrier)
    - [22.3 Anti-Patterns](#223-anti-patterns)

## 1. Project Structure Reference

> **Note**: The structure below reflects the pre-A1 baseline. New route files, service modules, and Celery task files are added per the implementation plan batches B1–B16. Consult `pilot-app-mvp-backend-impl-plan.md` for what's being added in each batch. Update this reference after each batch completes.

```
pilot/
├── backend/                    # FastAPI backend + Celery workers
│   ├── api/                    # Main API folder
│   │   ├── routes/             # API route handlers
│   │   │   ├── addresses.py
│   │   │   ├── admin_tenants.py
│   │   │   ├── audit.py
│   │   │   ├── auth.py
│   │   │   ├── calendar_integration.py
│   │   │   ├── catalog.py
│   │   │   ├── contacts.py
│   │   │   ├── customers.py
│   │   │   ├── health.py
│   │   │   ├── integrations.py
│   │   │   ├── invoices.py
│   │   │   ├── jobs.py
│   │   │   ├── quotes.py
│   │   │   ├── roles.py
│   │   │   ├── scheduling.py
│   │   │   ├── sites.py
│   │   │   ├── voice.py
│   │   │   └── webhooks.py         # QB HMAC webhook + Twilio SMS STOP handler
│   │   │   # New route files added per B1–B16 (see implementation plan)
│   │   └── schemas/            # Pydantic request/response schemas
│   │       ├── addresses.py
│   │       ├── contacts.py
│   │       ├── quotes.py
│   │       ├── roles.py
│   │       ├── schemas.py           # Primary shared schemas
│   │       └── voice.py
│   ├── app/                    # Main app folder
│   │   ├── models/             # SQLModel DB models
│   │   │   ├── ai.py                # ConversationSession, VoiceCommandLog
│   │   │   ├── auth.py              # TenantUser, TenantUserRole, Auth* models
│   │   │   ├── billing.py           # Invoice, InvoiceLine, Payment, Subscription
│   │   │   ├── catalog.py           # Supplier, SupplierItem, CatalogItem
│   │   │   ├── core.py              # User, Tenant, TenantSettings, PlatformRole
│   │   │   ├── crm.py               # Customer, Site, Contact, Address
│   │   │   ├── fulfillment.py       # Job, ChangeOrder, JobExpense, TimeEntry
│   │   │   ├── mixins.py            # StandardAuditMixin, AppendOnlyMixin, MachineLogMixin
│   │   │   ├── quoting.py           # Quote, QuoteLine, QuoteLineTaxComponent
│   │   │   ├── scheduling.py        # JobTechAssignment, TechAvailability, TenantCalendarIntegration, CalendarSyncLog, CalendarSyncConflict
│   │   │   └── system.py            # System-level tables
│   │   └── main.py                  # FastAPI app factory & router registration
│   ├── core/                   # Core utilities
│   │   ├── auth.py                  # JWT validation, AuthenticatedUser, get_current_user
│   │   ├── celery_app.py            # Celery configuration
│   │   ├── config.py                # Settings (pydantic-settings), env vars
│   │   ├── datetime_utils.py        # UTC enforcement, NaiveDatetimeError
│   │   ├── db.py                    # SQLModel engine, get_db(), set_audit_context_sync()
│   │   ├── encryption.py            # Fernet token encryption (AES-128-CBC + HMAC)
│   │   ├── idempotency.py           # Idempotency key middleware
│   │   ├── middleware.py            # RequestIDMiddleware (X-Request-ID tracing)
│   │   ├── permissions.py           # RBAC: require_permission(), has_permission()
│   │   ├── quickbooks_webhook.py    # verify_quickbooks_signature()
│   │   ├── rate_limit.py            # Slowapi rate limiting
│   │   ├── tax_calculation.py       # Tax computation utilities
│   │   └── test_context.py          # TestUserContext, get_test_context()
│   ├── migrations/             # Alembic migrations
│   │   ├── versions/                # Migration version files
│   │   └── seed_test_data.py        # Test data seeding script
│   ├── services/               # Business logic services
│   │   ├── ai_service.py            # Whisper + Ollama integration
│   │   ├── email_service.py         # SendGrid email
│   │   ├── entitlement_service.py
│   │   ├── map_service.py
│   │   ├── quickbooks_sync.py       # QuickBooks data sync
│   │   ├── scheduling_service.py
│   │   ├── sms_service.py           # Current Twilio SMS (to be replaced by sms_carrier.py in B11/A59)
│   │   ├── template_renderer.py
│   │   └── voice_action_router.py
│   ├── tasks/                  # Celery background tasks
│   │   ├── archive_audit_logs.py
│   │   ├── calendar_sync.py
│   │   ├── cleanup_idempotency_keys.py
│   │   ├── cleanup_sessions.py
│   │   ├── notification_worker.py
│   │   ├── profitability_rollup.py
│   │   ├── quickbooks_sync.py
│   │   ├── quickbooks_token_refresh.py
│   │   └── test_task.py
│   │   # New task files added per B1–B16 (see implementation plan)
│   ├── tests/                  # Pytest test suite (see PROVENANCE.md for current counts)
│   ├── app_model_imports.md    # App model imports reference
│   ├── db_models_map.md        # Model-to-file mapping reference
│   └── README.md               # Backend documentation
```

---

## 2. Environment Setup (Always Required)

**You must always activate the virtual environment before running any Python command.**

```bash
cd <repo>/backend
source .venv/bin/activate
```

All `pytest`, `alembic`, and `python` commands require this. Never assume the venv is already active in a new terminal.

---

## 3. Finding Models: Key Reference Files

### 3.1 Model-to-File Mapping

Before writing or modifying any model, consult `backend/db_models_map.md` to find which `.py` file contains each table/model. Do not guess — look it up.

> ⚠️ **`db_models_map.md` separates DB table classes (SQLModel `table=True`) from Enums/Schemas.** Only `DB Tables` rows are queryable via `select()`. Enum/Schema classes in the same file are NOT DB tables. Always check the `DB Tables` section before writing a query.

> ⚠️ **After ANY change to a model file**, you MUST regenerate this file before the task is considered complete:
> ```bash
> cd backend && source .venv/bin/activate
> python generate_db_model_map.py app > db_models_map.md
> ```

**Quick reference:**
| Model File | Contains |
|---|---|
| `app/models/core.py` | `User`, `Tenant`, `TenantSettings`, `PlatformRole`, `UserPreference` |
| `app/models/auth.py` | `TenantUser`, `TenantUserRole`, `AuthRefreshToken`, `AuthApiToken`, SSO models |
| `app/models/crm.py` | `Customer`, `Site`, `Contact`, `Address`, lifecycle status lookup tables |
| `app/models/billing.py` | `Invoice`, `InvoiceLine`, `Payment`, `Subscription`, `InvoiceLineTaxComponent` |
| `app/models/quoting.py` | `Quote`, `QuoteLine`, `QuoteLineTaxComponent` |
| `app/models/fulfillment.py` | `Job`, `ChangeOrder`, `ChangeOrderLine`, `JobExpense`, `TimeEntry` |
| `app/models/catalog.py` | `Supplier`, `SupplierItem`, `CatalogItem`, pricing models |
| `app/models/ai.py` | `ConversationSession`, `ConversationMessage`, `VoiceCommandLog` |
| `app/models/mixins.py` | `StandardAuditMixin`, `AppendOnlyMixin`, `MachineLogMixin` |

### 3.2 Model Import Reference

Use `backend/generate_app_import_map.py` to regenerate a deduplicated import map from the test suite:

```bash
cd <repo>/backend
source .venv/bin/activate
python generate_app_import_map.py tests > app_model_imports.md
```

Always check `app_model_imports.md` (if present in `backend/`) for the correct import path for any model before writing import statements.

> ⚠️ **After ANY new test file is added**, you MUST regenerate this file before the task is considered complete:
> ```bash
> cd backend && source .venv/bin/activate
> python generate_app_import_map.py tests > app_model_imports.md
> ```

### 3.3 API Endpoint Reference — `openapi.json` + `openapi_schema_map.md`

Two files together provide complete API coverage:

- **`backend/openapi.json`** — machine-readable full OpenAPI spec; the authoritative source for all endpoint paths, parameter names/types, request bodies, and response schemas. Generated by `python export_openapi_json.py`.
- **`backend/openapi_schema_map.md`** — human/agent-readable summary of every endpoint; quickly confirms path, required params, and response shape without parsing the full JSON. Generated by the same `export_openapi_json.py` script.

> ⚠️ **After ANY endpoint is added, modified, or deleted**, you MUST regenerate BOTH files by running:
> ```bash
> cd backend && source .venv/bin/activate
> python export_openapi_json.py
> ```
> This single script updates both `openapi.json` and `openapi_schema_map.md` in one step.

**Before writing any new route**, verify the endpoint does not already exist:
```bash
python3 -c "
import json
spec = json.load(open('openapi.json'))
matches = [p for p in spec['paths'] if 'YOUR_KEYWORD' in p]
print(matches)
"
```

---

## 4. Querying the Database (MCP Tool)

Use the `postgres-local` MCP server to inspect the live database schema, verify column names, check constraints, and validate data — **before writing migrations or model code**.

```
Tool: mcp--postgres-local--query
SQL: SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'customer' ORDER BY ordinal_position;
```

**Use this to:**
- Confirm exact FK column names before writing trigger SQL
- Verify column types before adding model fields
- Check existing indexes or constraints before adding new ones
- Debug data issues during development

Never assume a column name — always query the live schema to confirm.

### 4.1 Pre-Batch Verification Queries

Run these before starting the relevant batch to confirm what already exists — avoid writing migrations for columns that are already there.

**Before B11 (SMS/Telnyx) — verify TCPA opt-in/opt-out columns:**
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'customer' AND column_name LIKE 'sms%'
ORDER BY column_name;
```
Expected if pre-existing: `sms_opted_out`, `sms_opt_out_at`, `sms_opt_in_consent`, `sms_opt_in_at`, `sms_opt_in_source`. If absent, add them in B11/A59 migration.

**Before B3 (Dispatch Board) — verify Receipt OCR and schedule history:**
```sql
-- Check for OCR-related Celery task routines
SELECT routine_name FROM information_schema.routines
WHERE routine_name LIKE '%receipt%' OR routine_name LIKE '%ocr%';

-- Check for existing customer preferred_contact_channel column (needed by A21)
SELECT column_name FROM information_schema.columns
WHERE table_name = 'customer' AND column_name = 'preferred_contact_channel';
```

**Before B5 (Reports) — verify dunning Celery task:**
```sql
-- Check task files from the OS (cannot use SQL for this — check backend/tasks/ directory listing)
-- SQL: verify any dunning-related cron stored procedures
SELECT routine_name FROM information_schema.routines
WHERE routine_name LIKE '%dun%' OR routine_name LIKE '%overdue%';
```

**Before any batch — confirm a table's exact column list:**
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'YOUR_TABLE_NAME'
ORDER BY ordinal_position;
```

**Check existing indexes on a table (avoid duplicate index migrations):**
```sql
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'YOUR_TABLE_NAME'
ORDER BY indexname;
```

**Check existing constraints (avoid duplicate constraint migrations):**
```sql
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'YOUR_TABLE_NAME';
```

---

## 5. Model Design Standards

### 5.1 SQLModel Base Pattern

All database models inherit from the appropriate mixin + `SQLModel`. Use `table=True` for DB-mapped models.

```python
import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel
from .mixins import StandardAuditMixin


class MyModel(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "my_model"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    name: str = Field(nullable=False)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    # Override audit FK constraints (Phase 6.0.1 pattern):
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
```

### 5.2 Choose the Right Mixin

| Mixin | Use For | Provides |
|---|---|---|
| `StandardAuditMixin` | Mutable records (customers, jobs, quotes) | `created_at`, `updated_at` (auto-updates), `created_by`, `updated_by` |
| `AppendOnlyMixin` | Immutable/ledger records (payments, audit log) | `created_at`, `created_by` only |
| `MachineLogMixin` | Automated system events | `created_at` only |

### 5.3 Datetime Rules — Always UTC-Aware

❌ **WRONG:**
```python
from datetime import datetime
created_at = datetime.utcnow()  # naive datetime — will break
```

✅ **CORRECT:**
```python
from datetime import UTC, datetime
created_at = datetime.now(UTC)  # timezone-aware UTC
```

For model fields, use the mixin pattern or:
```python
from pydantic import AwareDatetime
from sqlalchemy import DateTime
from sqlmodel import Field

expires_at: AwareDatetime = Field(
    default=None,
    sa_column=Column(DateTime(timezone=True))
)
```

Use `core.datetime_utils.safe_now_utc()` for one-liner UTC timestamps:
```python
from core.datetime_utils import safe_now_utc
user.last_login_at = safe_now_utc()
```

### 5.4 Soft Delete — Standard Pattern

Every mutable model that supports soft delete uses:
```python
is_active: bool = Field(
    default=True,
    sa_column=Column(Boolean, server_default=text("true"), nullable=False),
)
```

Soft delete is performed by setting `is_active = False` — **never hard-delete business records**.

### 5.5 JSONB Fields

```python
from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field

preferences: Dict[str, Any] = Field(
    default_factory=dict,
    sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
)
```

### 5.6 Enums

Use `str, Enum` so values are stored as strings in the DB and are serializable:

```python
from enum import Enum

class CustomerType(str, Enum):
    person = "person"
    company = "company"
```

---

## 6. SQLModel Query Patterns (CRITICAL)

**Always use `select()` + `exec()`. Never use `.query()`.**

### 6.1 Basic Select

```python
from sqlmodel import select

# Single record
customer = db.exec(
    select(Customer)
    .where(Customer.id == customer_id)
    .where(Customer.tenant_id == current_user.tenant_id)
).first()

# Multiple records with pagination
customers = db.exec(
    select(Customer)
    .where(Customer.tenant_id == current_user.tenant_id)
    .offset(skip)
    .limit(limit)
).all()
```

### 6.2 Always Filter by `tenant_id` — `db.get()` is BANNED on tenant-scoped models

Every query on tenant-scoped data **must** include `.where(Model.tenant_id == current_user.tenant_id)`. This is the primary multi-tenancy enforcement mechanism.

**`db.get(Model, pk)` is permanently banned on any model that has a `tenant_id` column.** No exceptions — not even for secondary lookups, display-name-only fetches, or cases where the calling code already holds a tenant-scoped parent entity. The pattern looks safe in isolation but creates cross-tenant data leakage risk whenever a PK value is derived from user input, a JSON blob (e.g., `context_window_json`), or a mapping row. The FK constraint guarantees referential integrity but does **not** guarantee tenant ownership.

❌ **BANNED — even when you believe the FK keeps it safe:**
```python
customer = db.get(Customer, job.customer_id)          # ← no — job.customer_id is a FK, not a tenant assertion
customer = db.get(Customer, UUID(active_customer_id)) # ← no — active_customer_id from JSON context
customer = db.get(Customer, mapping.entity_id)        # ← no — mapping.entity_id from integration table
```

✅ **REQUIRED — always, without exception:**
```python
customer = db.exec(
    select(Customer)
    .where(Customer.id == job.customer_id)
    .where(Customer.tenant_id == current_user.tenant_id)
).first()
```

> **Return `404` (not `403`) for cross-tenant access attempts.** This prevents UUID enumeration attacks — never reveal whether a record exists in another tenant.

> **Architectural rule (FIND-132, 2026-05-10):** This policy is absolute. "It's just a display name lookup" is not an exception. "The parent entity was already tenant-scoped" is not an exception. Every single `db.get()` on a tenant-scoped model is an IDOR waiting to happen and must be replaced with the tenant-scoped query pattern.

### 6.3 Create / Update / Delete Cycle

```python
# CREATE
new_obj = MyModel(tenant_id=current_user.tenant_id, **data)
db.add(new_obj)
db.commit()
db.refresh(new_obj)  # Always refresh after commit to get DB-generated values
return new_obj

# UPDATE — mutate fields directly, then add/commit/refresh
obj.name = new_name
db.add(obj)
db.commit()
db.refresh(obj)

# SOFT DELETE
obj.is_active = False
db.add(obj)
db.commit()
```

---

## 7. Settings & Configuration

All environment variables are accessed via the singleton `core.config.settings`:

```python
from core.config import settings

# Access any configured value
url = settings.QUICKBOOKS_BASE_URL
env = settings.ENVIRONMENT  # "dev" | "qa" | "staging" | "production"
```

**Never** hardcode URLs, credentials, or environment-specific values in route or service code. Add new config values to `backend/core/config.py` as `Settings` class attributes with appropriate defaults.

---

## 8. API Route Design Pattern

### 8.1 Router Setup

Each route file in `api/routes/` creates its own `APIRouter`:

```python
# api/routes/my_resource.py
from fastapi import APIRouter
router = APIRouter()
```

Routes are registered in `backend/app/main.py` with a prefix and tags:
```python
app.include_router(my_resource.router, prefix="/api/v1/my-resource", tags=["my-resource"])
```

**Registering a new route file** — two steps required in `backend/app/main.py`:
```python
# 1. Import the router module at the top of main.py
from api.routes import my_new_resource

# 2. Register it in the app factory (inside create_app() or at module level)
app.include_router(
    my_new_resource.router,
    prefix="/api/v1/my-new-resource",
    tags=["my-new-resource"],
)
```

The router is picked up automatically on next app restart. Run `uvicorn app.main:app --reload` and check `http://localhost:8000/docs` to confirm the endpoints appear.

### 8.2 Dual-Endpoint Architecture (Authenticated + Test)

**Every CRUD route must have two versions** — an authenticated endpoint and a `/test` endpoint for dev/QA use without JWT. The shared logic lives in a private `_impl()` function.

```
⚠️ Register /test endpoints BEFORE authenticated endpoints in the file
   to prevent route matching conflicts (/{id} would match /test).
```

**Canonical structure for every route file:**

```python
# ==================== SHARED BUSINESS LOGIC ====================

def _create_resource_impl(
    data: ResourceCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> MyModel:
    """Shared logic — accepts both AuthenticatedUser and TestUserContext."""
    obj = MyModel(
        tenant_id=user_context.tenant_id,
        **data.model_dump()
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ==================== TEST ENDPOINTS (register FIRST) ====================

@router.post("/test", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource_test(data: ResourceCreate, db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_resource_impl(data, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================

@router.post("/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(
    data: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("resource.create")),
):
    """Production endpoint — requires JWT + permission."""
    return _create_resource_impl(data, db, current_user)
```

### 8.3 Standard HTTP Methods

| Operation | HTTP Method | Route | Status Code |
|---|---|---|---|
| Create | `POST` | `/` | `201 Created` |
| List | `GET` | `/` | `200 OK` |
| Get one | `GET` | `/{id}` | `200 OK` |
| Update | `PATCH` | `/{id}` | `200 OK` |
| Soft delete | `DELETE` | `/{id}` | `200 OK` + message dict |

---

## 9. Authentication & RBAC

### 9.1 Dependency Injection Pattern

Use `core.auth.get_current_user` for auth-only routes, or `core.permissions.require_permission()` for auth + permission enforcement:

```python
from core.auth import AuthenticatedUser
from core.permissions import require_permission

# Auth + permission check (preferred for all protected routes)
@router.get("/{id}")
def get_resource(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("resource.view")),
):
    ...
```

### 9.2 Permission Format

```
resource.action
```

Permissions are stored as a JSONB array on `platform_role.permissions`. The full list is seeded in migration `2026_03_27_2353-8a632bb9329d_seed_default_rbac_roles.py`.

**Pre-A1 permissions (baseline set):**

| Resource | Actions |
|---|---|
| `customers` | `create`, `view`, `update`, `delete` |
| `sites` | `create`, `view`, `update`, `delete` |
| `quotes` | `create`, `view`, `update`, `delete` |
| `jobs` | `create`, `view`, `update`, `delete` |
| `invoices` | `create`, `view`, `update`, `delete` |
| `voice` | `create`, `view` |
| `audit` | `view` |
| `integrations` | `create`, `view`, `update` |
| `users` | `create`, `view`, `update`, `delete` |

Wildcard `"*"` grants all permissions (owner role). `"resource.*"` grants all actions on a resource.

**Pass 3 + Pass 4 additions** (added via batch migrations; use these permission strings in new routes):

```
quote.submit_for_approval      # tech submits draft for owner review
quote.approve                  # owner/accountant approves/rejects pending quotes
quote.apply_discount           # owner/accountant applies time-limited discounts
voice.provide_feedback         # owner/accountant flags voice misrecognitions
voice.manage_own_sessions      # all roles — rename, delete, open own sessions
quote_template.create          # owner/accountant — save quote as template
quote_template.edit            # owner/accountant — edit existing tenant templates
quote_template.fork_system     # owner/accountant — fork system templates
schedule.manage                # owner/office_staff — dispatch and assignments
schedule.view_own              # technician — view own assigned schedule
field_issue.view               # owner/accountant — view mobile conflict escalations
field_issue.resolve            # owner/accountant — resolve mobile conflict escalations
qb_conflict.view               # owner/accountant — view QB sync conflicts
qb_conflict.resolve            # owner/accountant — resolve QB sync conflicts
notification_preference.tenant_default.edit  # owner only
notification_preference.user_override.edit   # all roles
voice_persona_tone.tenant_default.edit       # owner only
voice_persona_tone.user_override.edit        # all roles when allowed
mfa.enroll_self                # all roles
mfa.reset_self                 # all roles
mfa.reset_user                 # owner — reset another user's MFA
mfa.policy.edit                # owner — set tenant MFA required policy
account.session.revoke_own     # all roles
account.data_export.request    # all roles
subscription.view              # owner/accountant
subscription.tier.change       # owner only
```

> **Canonical source**: `dev-docs/product-requirements/mvp-prd.md §3.5` Pass 3/4 RBAC Additions sections. New permissions are seeded in the batch migration that introduces the feature — do not add them to the role seed migration, add them to the feature migration instead.

### 9.3 `AuthenticatedUser` Object

After `get_current_user` resolves, the route receives an `AuthenticatedUser` object:

```python
current_user.id           # UUID — user's ID
current_user.user_id      # UUID — alias for .id
current_user.tenant_id    # UUID — active tenant (use for all DB queries)
current_user.role_code    # str — e.g., "owner", "technician"
current_user.permissions  # List[str] — cached, in-memory
current_user.has_permission("quotes.create")  # bool — fast in-memory check
```

### 9.4 Audit Context

When a route mutates data that must be audit-logged, call `set_audit_context_sync()` **before** the mutation. This sets the PostgreSQL session variable `app.user_id` for the audit trigger:

```python
from core.db import set_audit_context_sync

@router.post("/")
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.create")),
):
    set_audit_context_sync(db, current_user.id)  # Must come before db.add/commit
    customer = Customer(tenant_id=current_user.tenant_id, ...)
    db.add(customer)
    db.commit()
    ...
```

---

## 10. Schema (Pydantic) Design Standards

All API schemas live in `api/schemas/`. Primary schemas are in `api/schemas/schemas.py`.

### 10.1 Request Schema (Create/Update)

```python
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class ResourceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: UUID
```

### 10.2 Response Schema

Response schemas must include `model_config = ConfigDict(from_attributes=True)` for SQLModel compatibility:

```python
from pydantic import BaseModel, ConfigDict
from uuid import UUID

class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Required for ORM → Pydantic

    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    is_active: bool
```

### 10.3 Nested Schemas

When a response needs to include related data (e.g., a Site with its Address):

```python
class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    name: Optional[str]
    is_active: bool
    address: Optional[AddressResponse] = None  # Nested — populated if loaded
```

---

## 11. Test Context Endpoints

Test endpoints use `core.test_context.get_test_context()` to provide a `TestUserContext` object in place of `AuthenticatedUser`. Both objects expose the same interface (`id`, `tenant_id`) for compatibility with `_impl()` functions.

```python
from core.test_context import TestUserContext, get_test_context

# TestUserContext values (from config):
# id        = UUID("00000000-0000-0000-0000-000000000002")
# tenant_id = UUID("00000000-0000-0000-0000-000000000001")
```

**Environment guards:**
- `TEST_ENDPOINT_ENABLED=true` — must be set in `.env`
- `ENVIRONMENT=dev` or `ENVIRONMENT=qa` — test endpoints are blocked in `staging` and `production`

---

## 12. Middleware Stack (Registered in main.py)

Middleware executes in **reverse registration order**. The current stack:

| Middleware | Source | Purpose |
|---|---|---|
| `RequestIDMiddleware` | `core/middleware.py` | Injects/validates `X-Request-ID` UUID for distributed tracing |
| `idempotency_middleware` | `core/idempotency.py` | Prevents duplicate POSTs using idempotency keys |
| `CORSMiddleware` | FastAPI built-in | Allows localhost:3000 and localhost:5173 in dev |

**Do not** add new global middleware without understanding the ordering implications.

Use `request.state.request_id` in any route handler to access the trace ID. Use `log_with_request_id()` for traceable logs:

```python
from core.middleware import log_with_request_id

@router.post("/")
def create_something(request: Request, ...):
    log_with_request_id(request, "Creating resource", "info")
```

---

## 13. Alembic Migration Standards

### 13.1 Always Use Blank Migrations — Never Autogenerate

```bash
cd backend
source .venv/bin/activate
alembic history                  # Check current head and down_revision
alembic revision -m "descriptive_migration_name"
```

**Never use `--autogenerate`** for production migrations. Write all `upgrade()` and `downgrade()` SQL manually to maintain full control.

### 13.2 Migration Verification Loop

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

All three must succeed cleanly. A migration that doesn't cleanly downgrade is not accepted.

### 13.3 Raw SQL in Migrations

Use `op.execute()` for DDL that SQLAlchemy can't express:

```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE customer
        ADD CONSTRAINT chk_customer_type
        CHECK (type IN ('person', 'company'));
    """)

def downgrade() -> None:
    op.execute("ALTER TABLE customer DROP CONSTRAINT chk_customer_type;")
```

### 13.4 Strict Schema Naming & Triggers

When writing migrations for new tables or constraints, you MUST follow these schema rules to prevent `schema_diff.py` failures:

* **Explicit Naming:** NEVER rely on auto-generated constraint names. Explicitly provide the `name=` parameter for all `sa.PrimaryKeyConstraint`, `sa.ForeignKeyConstraint`, `sa.UniqueConstraint`, and `sa.CheckConstraint` definitions to match the exact JSON blueprint patterns (e.g., `name="fk_table_column"`).

* **Mandatory Triggers:** Every new standard table MUST include three explicit `op.execute()` triggers in the `upgrade()` function:

  1. `audit_log`: `CREATE TRIGGER audit_<table>_changes AFTER INSERT OR DELETE OR UPDATE ON public.<table> FOR EACH ROW EXECUTE FUNCTION audit.log_changes()`
  2. `immutable_guard`: `CREATE TRIGGER trg_<table>_guard_created_immutable BEFORE UPDATE ON public.<table> FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()`
  3. `updated_at_sync`: `CREATE TRIGGER trg_<table>_set_updated_at BEFORE UPDATE ON public.<table> FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()`

* **Clean Downgrades:** In `downgrade()`, always use `DROP TRIGGER IF EXISTS` for all three triggers *before* calling `op.drop_table()`.

---

## 14. Error Handling Conventions

### 14.1 Standard HTTP Exceptions

```python
from fastapi import HTTPException, status

# 400 Bad Request — invalid input
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Customer with this email already exists in this tenant",
)

# 404 Not Found — resource missing or wrong tenant
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Customer not found",
)

# 403 Forbidden — permission denied (use PermissionDeniedError from core.permissions)
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Insufficient permissions",
)
```

### 14.2 Enum Validation

Always validate enum input with a try/except to return a clean 400:

```python
try:
    ctype = CustomerType(customer_in.type)
except ValueError:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid type: {customer_in.type}. Valid values: {[e.value for e in CustomerType]}",
    )
```

---

## 15. Known Test Fragility — Audit Event Volume

### 15.1 `test_query_events_returns_tenant_isolated_results` Page-Overflow Risk

**File:** `backend/tests/test_audit_logging.py`
**Test:** `TestAuditAPI::test_query_events_returns_tenant_isolated_results`

This test queries the audit log with a 6-day lookback window and asserts that 5 fixture rows created with `entity_id` values like `"cust-0"` are present in the response. It is vulnerable to **page-overflow failure** as the test-run audit event volume grows.

**Root cause:** Every API call in the test suite that mutates data fires the `audit.log_changes()` trigger, inserting rows into the `audit_event` table. Once the number of events in the 6-day window exceeds the query `limit`, the fixture rows may fall off the page and the assertion fails.

**Fix applied (4-23-2026):** Limit increased from `500` → `5000` at line ~439.

**Future agents:** If this test starts failing again with the same `"Test events not found in response"` message, the fix is to increase the `limit` parameter in the `query_audit_events(...)` call inside this test. Do NOT delete the test or lower the fixture creation count.

**Long-term recommendation:** Refactor the test to filter by `entity_id IN ('cust-0', ..., 'cust-4')` directly rather than relying on a page-wide scan, which would eliminate the fragility entirely.

---

## 15b. Common Anti-Patterns — Never Do These

| ❌ Wrong | ✅ Correct |
|---|---|
| `db.query(Model).filter(...)` | `db.exec(select(Model).where(...))` |
| `datetime.utcnow()` | `datetime.now(UTC)` |
| Hard-delete: `db.delete(obj)` | Soft-delete: `obj.is_active = False; db.add(obj)` |
| Accessing settings via `os.environ.get()` | `from core.config import settings; settings.MY_KEY` |
| Forgetting `db.refresh(obj)` after commit | Always `db.refresh(obj)` to get DB-generated values |
| Querying without `tenant_id` filter | Always `.where(Model.tenant_id == user_context.tenant_id)` |
| Hardcoding test tenant/user IDs | Use `settings.TEST_TENANT_ID` / `settings.TEST_USER_ID` |
| Importing from `sqlalchemy.orm` for queries | Use `sqlmodel.select` only |
| Using `session` as a fixture in tests | Use `db_session` fixture |
| Hardcoding test tenant/user IDs | Use the `test_tenant` or `test_user` fixtures from conftest |
| `status.HTTP_422_UNPROCESSABLE_ENTITY` | `status.HTTP_422_UNPROCESSABLE_CONTENT` — `UNPROCESSABLE_ENTITY` is deprecated in Starlette ≥0.30 and produces a `DeprecationWarning` in every test run. **Always use `HTTP_422_UNPROCESSABLE_CONTENT`**. Existing occurrences in `calendar_conflicts.py` were already corrected (B7a). |

---

## 16. Standard Implementation Task Workflow

Every backend task — whether it's a DB model update, schema migration, API change, or security hardening — follows the same execution loop. **Do not skip steps. Do not reorder them.**

---

### 16.1 Pre-Work: Establish Regression Baseline

Before touching **any** file, capture the current test state. This is your immutable checkpoint.

```bash
cd <repo>/backend
source .venv/bin/activate

# Step 1: Unit tests only (fast baseline)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Only after you have completed a task, and have re-run the Unit tests, then only if Tom says OK, then run:

```bash
# Full suite (unit + integration — for baseline capture only)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record both outputs before writing a single line of code.** All tests passing at this point must still pass at the end.

---

### 16.2 The Standard 4-Step Execution Loop

#### Step 1 — ORM Model Updates

1. Open `backend/db_models_map.md` and locate the exact `.py` file for every table in scope.
2. Open `backend/app_model_imports.md` to confirm correct import paths before adding imports.
3. **For every new table: confirm the mixin assignment from the batch design doc's §A migration plan before writing the class declaration.** Every table must inherit from exactly one of:
   - `StandardAuditMixin` — mutable records; adds `created_at`, `updated_at`, `created_by`, `updated_by` + 3-trigger set (`audit_changes`, `guard_created_immutable`, `set_updated_at`)
   - `AppendOnlyMixin` — immutable/ledger records; adds `created_at`, `created_by` + 2-trigger set (`audit_changes`, `guard_created_immutable`)
   - `MachineLogMixin` — automated system events; adds `created_at` only + audit trigger
   
   If the design doc does not specify a mixin, **stop and raise the question before writing code** — do not default to no mixin. See `backend/app/models/mixins.py` for the canonical definitions.
4. Make all required model changes (add fields, add `index=True`, add `is_active`, fix FK definitions, etc.).
5. Verify the FastAPI app still boots cleanly after model changes — circular import crashes appear at startup, not at test time.

**Common model change types and their patterns:**

| Change Type | ORM Pattern |
|---|---|
| Add new field | `field_name: type = Field(...)` with correct `sa_column` |
| Add FK index | `field_name: uuid.UUID = Field(foreign_key="table.id", index=True)` |
| Add tenant stamp | `tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)` |
| Add soft-delete | `is_active: bool = Field(default=True, sa_column=Column(Boolean, server_default=text("true"), nullable=False))` |
| Add `is_active` audit FK override | `created_by: Optional[uuid.UUID] = Field(default=None, sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")))` |

---

#### Step 2 — Manual Alembic Migration

**Never use `--autogenerate`.** It pulls in unrelated schema diffs and ghost changes. Always generate a blank migration and write it manually.

```bash
cd <repo>/backend
source .venv/bin/activate

# Check history to confirm the correct down_revision before writing the file
alembic history

# Generate blank migration with a descriptive name
alembic revision -m "phase_fe_1_batch_b1_quote_line_visibility_hierarchy"
```

**Migration naming convention for A2–A88 frontend feature work:**
```
phase_fe_1_batch_b{N}_{domain_description}
```
Examples matching the implementation plan batches:
- `phase_fe_1_batch_b1_quote_line_visibility_hierarchy`
- `phase_fe_1_batch_b3_dispatch_board_optimistic_locking`
- `phase_fe_1_batch_b6_calendar_conflict_diff_payload`
- `phase_fe_1_batch_b11_sms_carrier_adapter_tcpa_columns`
- `phase_fe_1_batch_b14_stripe_subscription_webhook_dedup`

**Historical convention** (pre-A1 migrations in `migrations/versions/`):
```
phase_{X}_{Y}_batch_{N}_{domain_description}
```
Examples from existing migrations:
- `phase_7_0_batch_5_tenant_stamping_communications_webhooks`
- `phase_8_0_batch_5_indexes_billing_subscriptions`
- `phase_9_0_batch_2_soft_delete_sync_triggers`

Use the `phase_fe_1_batch_b{N}_` prefix for all new A2–A88 work so it is clearly distinguishable from historical schema-sync phases.

**3-Part migration pattern for additive column changes (tenant stamping, new columns):**

```python
def upgrade() -> None:
    # Part 1: Add column as NULLABLE first
    op.add_column('table_name', sa.Column('new_col', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_table_new_col', 'table_name', 'referenced_table', ['new_col'], ['id'])
    op.create_index('ix_table_new_col', 'table_name', ['new_col'])

    # Part 2: Backfill existing rows
    op.execute("""
        UPDATE table_name
        SET new_col = parent_table.value
        FROM parent_table
        WHERE table_name.parent_id = parent_table.id
    """)

    # Part 3: Lock it down to NOT NULL
    op.alter_column('table_name', 'new_col', nullable=False)


def downgrade() -> None:
    op.drop_index('ix_table_new_col', table_name='table_name')
    op.drop_constraint('fk_table_new_col', 'table_name', type_='foreignkey')
    op.drop_column('table_name', 'new_col')
```

**Index-only migration pattern:**

```python
def upgrade() -> None:
    op.create_index('ix_table_column_name', 'table_name', ['column_name'])

def downgrade() -> None:
    op.drop_index('ix_table_column_name', table_name='table_name')
```

**Trigger migration pattern (plpgsql):**

```python
def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_child_table()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE child_table
                SET is_active = false
                WHERE fk_column = NEW.id
                  AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_parent_to_child
        AFTER UPDATE OF is_active ON parent_table
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_child_table();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_parent_to_child ON parent_table;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_child_table();")
```

**Migration verification loop (mandatory after every migration):**

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

All three must succeed cleanly. A migration that does not downgrade cleanly is not accepted.

---

#### Step 3 — Master Blueprint Sync

After every migration, update `dev-docs/db-design/pilot-db-schema-v2.6h.json` — the Golden Master JSON — to reflect the changes. This is not optional.

**Rule: Master JSON Schema Formatting Constraints**
When updating the `pilot-db-schema-v2.6h.json` master blueprint, you **MUST strictly adhere** to the existing structural format. Our `schema_diff.py` tool uses strict literal string parsing against PostgreSQL dumps. Do not invent keys, do not use shorthand, and do not mix Python ORM concepts into the database JSON.

**Strict Constraints:**
* **No Inline Foreign Keys:** Do not define `fk` or `on_delete` properties inside the individual `columns` objects. All foreign keys must be explicitly defined in the table-level `"foreign_keys"` array as discrete objects.
* **Indexes MUST use `definition`:** Do not use `"columns": [...]` arrays to define indexes. Every index must have a `"definition"` key containing the exact, raw `CREATE INDEX` PostgreSQL statement.
* **Triggers MUST use `definition`:** Every trigger must have a `"definition"` key containing the exact, raw `CREATE TRIGGER` PostgreSQL statement. 
* **No ORM Metadata:** Do not include keys like `"mixin"`, `"constraints": {"fks": []}`, or ORM-specific logic. This JSON represents the physical PostgreSQL database, not the SQLAlchemy models.

**The Golden Template:**
Every new table object must perfectly match this exact key structure:
```JSON
  {
    "table_name": {
      "comment": "Description of the table.",
      "columns": {
        "id": { "type": "uuid", "nullable": false }
      },
      "primary_key": [ "id" ],
      "unique": [],
      "indexes": [
        {
          "name": "ix_table_name_id",
          "definition": "CREATE INDEX ix_table_name_id ON public.table_name USING btree (id)"
        }
      ],
      "check_constraints": [],
      "foreign_keys": [
        {
          "name": "fk_table_name_other_table",
          "columns": [ "other_id" ],
          "ref_table": "other_table",
          "ref_columns": [ "id" ],
          "on_delete": "RESTRICT"
        }
      ],
      "triggers": [
        {
          "name": "audit_table_name_changes",
          "definition": "CREATE TRIGGER audit_table_name_changes AFTER INSERT OR DELETE OR UPDATE ON public.table_name FOR EACH ROW EXECUTE FUNCTION audit.log_changes()"
        }
      ]
    }
  }
```

**New column pattern:**
```json
{
  "name": "tenant_id",
  "type": "uuid",
  "nullable": false,
  "foreign_key": "tenant.id"
}
```

**New index pattern:**
```json
{
  "name": "ix_table_column",
  "definition": "CREATE INDEX ix_table_column ON public.table_name USING btree (column_name)"
}
```

**New trigger pattern:**
```json
{
  "name": "trg_soft_delete_parent_to_child",
  "event": "AFTER UPDATE OF is_active",
  "timing": "FOR EACH ROW",
  "condition": "OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false",
  "function": "cascade_soft_delete_to_child_table()",
  "purpose": "Soft-delete cascade: parent → child"
}
```

**New unique constraint pattern:**

> ⚠️ **IMPORTANT**: The `schema_diff.py` script looks for the key `"unique"` (NOT `"unique_constraints"`) when comparing unique constraints on a table. Always use `"unique"` as the JSON key for table-level unique constraints:

```json
{
  "unique": [
    ["tenant_id", "name"],
    ["code"]
  ]
}
```

❌ **Wrong** — schema_diff.py will NOT recognize this:
```json
{
  "unique_constraints": [
    { "name": "uq_table_name", "columns": ["tenant_id", "name"] }
  ]
}
```

✅ **Correct** — use the `"unique"` key with arrays of column names:
```json
{
  "unique": [
    ["tenant_id", "name"]
  ]
}
```

#### Step 4 - Schema Management Instructions & Constraints

You are responsible for safely interacting with the project's massive database schema JSON file (e.g., `pilot-db-schema-v2.6h.json`). 

### 🛑 CRITICAL CONSTRAINTS
1. **NEVER use `sed`, `awk`, `grep`, or inline Python scripts to mutate the schema JSON file directly.** Line-based editing will corrupt the JSON syntax and break the application.
2. **ALWAYS use the `schema_manager.py` tool** located in the `backend` directory for all schema interactions. This tool parses the AST safely.
3. **Never pass raw JSON strings via the command line.** Quote escaping will fail. Always write your payloads to a temporary file, pass the file to the script, and then clean up.

---

##### Standard Workflow for Adding or Editing Schema

Follow this exact progressive discovery workflow when tasked with updating the database design. **Always use the path-based `schema_manager.py` tool**; never edit the JSON file manually with line-based editors. Refer to `README-schema_manager.md` for full command details and array vs. attribute targeting.

**Step 1: Inspect the Current State** Before creating or modifying an object, verify the existing structure and project conventions using the `get` command.

```bash
# View a whole table
python schema_manager.py get --path tables.user
# View specific columns or arrays
python schema_manager.py get --path tables.user.columns

```

**Step 2: Prepare the Payload** Write the exact JSON structure for your update into a temporary file. This prevents CLI quote-escaping errors.

```bash
cat << 'EOF' > temp_payload.json
{
  "type": "uuid",
  "nullable": true,
  "description": "FK to the customer who owns this record."
}
EOF

```

**Step 3: Execute the Mutation** Use the appropriate command (`set`, `array-append`, `array-update`, or `delete`) with the dot-notation `--path` to safely apply changes.

*To add or overwrite a Column, Table, or Attribute (Dictionaries):*

```bash
python schema_manager.py set --path tables.existing_table.columns.new_column --payload temp_payload.json

```

*To add an Index, FK, Trigger, or Global Function (Arrays):*

```bash
python schema_manager.py array-append --path tables.existing_table.foreign_keys --payload temp_payload.json

```

*To modify an existing Index, FK, or Global Function in-place (Arrays):*

```bash
python schema_manager.py array-update --path functions --match-key name --match-value log_changes --payload temp_payload.json

```

**Step 4: Clean Up** Always delete your temporary payload file after a successful operation to keep the workspace clean.

```bash
rm temp_payload.json

```

##### Post-Updating of the JSON File Schema

After updating the JSON, ask the user to:
1. Dump the live DB schema
2. Copy the dump to `dev-docs/db-design/`
3. Run `python schema_diff.py --group-by environment`

**Zero discrepancies are required before the task is considered complete.**

---

#### Step 5 — Regression Testing & New Test Coverage

**Unit tests only during active development:**

```bash
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Fix all failures before proceeding. Do not move to integration tests until unit tests are 100% green.

> ⚠️ **Unit tests alone are not sufficient for service functions with DB persistence.** If a service function computes a value that gets written to a DB column, you must also write an integration test that reads the column back and verifies the value was persisted. See **§16.6**.

**Write new tests for every change made.** Place them in the appropriate subfolder under `tests/`:

```
tests/
├── integration/          # Integration tests (real external services)
├── phase_4/              # Phase 4.x migration & schema tests
├── phase_5/              # Phase 5.x migration & schema tests
├── phase_6/              # Phase 6.x migration & schema tests
├── phase_7/              # Phase 7.x tenant isolation & batch tests
├── phase_9/              # Phase 9.x soft-delete & FK lockdown tests
├── batch_1a/             # Batch 1-A security fix tests
├── batch_1b/             # Batch 1-B FK hard-delete lockdown tests
├── batch_1c/             # Batch 1-C schema column & soft-delete tests
├── batch_1d/             # Batch 1-D revenue API endpoint tests
└── (root)                # General feature tests not tied to a phase/batch
```

**Naming convention within a subfolder:**

| Change Type | Filename Pattern |
|---|---|
| New model field or FK | `test_task_X_description.py` |
| Soft-delete cascade trigger | `test_task_X_soft_delete_pathways.py` |
| Tenant isolation (IDOR) | `test_task_X_tenant_isolation.py` |
| API route / endpoint | `test_task_X_api_route_description.py` |

**Rules:**
- Create a new batch subfolder (e.g. `batch_1e/`) when starting a new batch of work
- General feature tests that don't belong to a specific phase/batch stay in `tests/` root
- **Never create a `tests/unit/` subdirectory** — that structure has been retired
- All fixtures from `tests/conftest.py` are automatically inherited by every subfolder
- **Always use the test_tenant fixture** from conftest and not hardcoded UUIDs.

**Final full-suite run (only after all unit tests pass):**

```bash
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

---

### 16.3 API & Service Layer Refactoring (When Required)

When a task involves adding `tenant_id` to models that are accessed in routes or services, **every `session.get()` call on those models must be replaced**.

**See §6.2 for the full canonical rule.** The short version: `db.get(Model, pk)` is permanently banned on any tenant-scoped model. Always use the tenant-scoped `select()` query pattern. Return `404` (not `403`) for cross-tenant access attempts.

---

### 16.4 Stop & Rollback Conditions

Halt immediately and do not proceed if any of the following occur:

| Condition | Immediate Action |
|---|---|
| `alembic upgrade head` fails | Run `alembic downgrade -1`, fix the migration SQL, re-apply |
| Circular import crash on app startup | Reference `backend/app_model_imports.md`, use string FK references (`foreign_key="tenant.id"`), do not import model classes directly in model files |
| Soft-delete trigger causes infinite recursion | Remove trigger, add `WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)` guard, re-apply |
| Backfill SQL fails with NULL constraint violation | Stop — a parent record has been deleted; report to user before proceeding |
| Any previously passing test now fails | Treat as regression, find root cause before continuing — **do not delete tests** |
| `schema_diff.py` reports discrepancies after migration | Do not mark task complete; resolve discrepancies first |

---

### 16.5 Definition of Done Checklist

Every task is **not complete** until every item below is checked:

- [ ] Pre-modification test baseline captured (unit tests + full suite counts recorded)
- [ ] All ORM models in scope verified/updated (use `db_models_map.md` to find files)
- [ ] Correct import paths verified (use `app_model_imports.md`)
- [ ] `alembic history` checked and `down_revision` confirmed correct before writing migration
- [ ] Blank Alembic migration created with descriptive name (no `--autogenerate`)
- [ ] Migration `upgrade()` and `downgrade()` manually coded and verified
- [ ] Migration triple-verified: `upgrade head` → `downgrade -1` → `upgrade head` all succeed
- [ ] `pilot-db-schema-v2.6h.json` updated (columns, indexes, triggers, FKs as applicable)
- [ ] User ran `python schema_diff.py --group-by environment` and reported **ZERO discrepancies**
- [ ] All `session.get(Model, id)` calls refactored to tenant-scoped `select()` queries (if applicable)
- [ ] New unit tests written covering all changes made (one test per pathway minimum)
- [ ] Any service function that computes a value for DB persistence has an **integration test** verifying the column is populated (not just a unit test on the function) — see **§16.6**
- [ ] 100% of unit tests pass with zero regressions
- [ ] Full suite passes with zero regressions (run once, after unit tests green) — vendor/live-service suites excluded by default per rules §15 (`-m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e"`); affected vendor marker suites run + recorded when the batch touches Telnyx/Stripe/SendGrid/Redis-covered code
- [ ] Task phase plan document updated — batch marked ✅ COMPLETE with migration filename and test file reference
- [ ] Final test counts documented (before/after)
- [ ] **FIND-166**: If adding a new lookup/reference table or seed rows, update `dev-docs/traceability/18-seed-data-catalog.md` with the table name, row count, and delivery migration
- [ ] **If any model file was modified**: `python generate_db_model_map.py app > db_models_map.md` regenerated ✅
- [ ] **If any test file was added**: `python generate_app_import_map.py tests > app_model_imports.md` regenerated ✅
- [ ] **If any endpoint was added, modified, or deleted**: `python export_openapi_json.py` run to update BOTH `openapi.json` AND `openapi_schema_map.md` ✅

---

### 16.6 Integration Test Rule: Service Functions with DB Persistence

**Rule**: Any service function that computes a value for DB persistence must have an integration test that verifies the value actually lands in the correct DB column. A unit test on the service function alone is insufficient.

**Anti-pattern — unit test only (NOT sufficient):**

```python
# This unit test always passes — it proves the function computes correctly,
# but proves NOTHING about whether the value is persisted to the DB column.
def test_compute_financial_delta_returns_500():
    result = compute_financial_delta(
        "invoice",
        {"amount_due_cents": 10000},
        {"amount_due_cents": 9500}
    )
    assert result == 500  # ✅ passes — but DB column may not exist or never be written
```

**Required integration test pattern:**

```python
# Integration test — verifies the computed value lands in the correct DB column.
def test_qb_conflict_creation_persists_financial_delta(db_session, test_tenant):
    # Simulate the full path: trigger conflict → create DB row via the service → read it back
    conflict = create_qb_invoice_conflict_via_service(db_session, test_tenant)

    db_conflict = db_session.exec(
        select(IntegrationSyncConflict)
        .where(IntegrationSyncConflict.id == conflict.id)
        .where(IntegrationSyncConflict.tenant_id == test_tenant.id)
    ).first()

    assert db_conflict is not None
    assert db_conflict.conflict_subtype == "invoice"                      # column exists and is populated ✅
    assert db_conflict.financial_delta_payload is not None                # column exists and is not NULL ✅
    assert db_conflict.financial_delta_payload["delta_cents"] == 500      # correct value persisted ✅
```

**How to identify functions requiring this rule:**

Any service function that:
1. Returns a computed value (delta, flag, classification code, computed amount, etc.)
2. Is called from a write path that creates or updates a DB row
3. Has the return value stored in a specific column (even if that column is nullable)

**Common patterns requiring integration tests:**

| Pattern | What to test in the DB |
|---|---|
| `compute_X()` → stored in `table.x_column` | `assert row.x_column == expected_value` |
| `detect_X_warning()` → stored in `table.x_flag` | `assert row.x_flag is True / False` |
| `classify_X()` → stored in `table.x_code` | `assert row.x_code == "expected_code"` |
| `calculate_X_amount()` → stored in `table.x_cents` | `assert row.x_cents == expected_cents` |
| `ocr_service.extract_expense()` → stored in `job_expense.cost_cents` | `assert expense.cost_cents == extracted_total` |

**Root cause of this rule (FIND-090, Phase 4.1, 2026-05-08):**

`compute_financial_delta()` and `detect_tax_period_warning()` in `services/qb_conflict_diff.py` had passing unit tests. Batch B8/A49 was marked ✅ Complete. But the DB columns they were supposed to populate (`conflict_subtype`, `financial_delta_payload`) were never added in a migration. The gap was invisible until an MCP schema query revealed the columns didn't exist in the live DB. If an integration test had been written — "create a conflict via the service → read the `conflict_subtype` column back from the DB" — it would have immediately caught the missing columns with an `AttributeError` or schema validation failure.

**The checklist item in §16.5** enforces this rule before any task can be marked complete.

---

## 17. Celery Task Patterns

Every new Celery task follows one of two patterns depending on whether it needs retry logic. Both patterns are derived from the real codebase at `backend/tasks/`.

### 17.1 Periodic Poll Task (no bind, no retry)

Used for tasks that run on a schedule and process a batch of records. Errors are logged and raised; Celery Beat will re-schedule on the next interval.

```python
# tasks/my_new_cleanup_task.py
import logging
from typing import Dict
from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session, select
from app.models.some_model import SomeModel

logger = logging.getLogger(__name__)


@celery_app.task(name="my_cleanup_task")
def my_cleanup_task() -> Dict[str, int]:
    """
    Process pending records. Run by Celery Beat on a schedule.
    Returns a count dict for logging/monitoring.
    """
    db: Session = next(get_db())
    processed = 0

    try:
        records = db.exec(
            select(SomeModel)
            .where(SomeModel.status == "pending")
            .limit(100)
        ).all()

        for record in records:
            # do work here
            record.status = "processed"
            db.add(record)
            processed += 1

        db.commit()
        return {"processed": processed}

    except Exception as e:
        db.rollback()
        logger.error(f"Error in my_cleanup_task: {e}")
        raise

    finally:
        db.close()
```

### 17.2 Event-Driven Retryable Task (bind=True, max_retries)

Used for tasks that are enqueued on-demand (e.g., triggered from a route) and need retry on failure (network errors, provider timeouts).

```python
# tasks/my_event_task.py
import logging
from typing import Any, Dict
from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session

logger = logging.getLogger(__name__)


@celery_app.task(
    name="my_event_task",
    bind=True,             # gives access to self.retry()
    max_retries=3,         # total retry attempts after initial failure
)
def my_event_task(self, record_id: str) -> Dict[str, Any]:
    """
    Process a single record. Enqueued via .delay() from a route.
    Retries on transient errors with 60-second countdown.
    """
    db: Session = next(get_db())

    try:
        result = _my_event_task_impl(record_id, db)
        return result

    except ValueError:
        # Don't retry validation errors — they won't fix themselves
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing record {record_id}: {e}")
        # Retry on unexpected DB or network errors
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


def _my_event_task_impl(record_id: str, db: Session) -> Dict[str, Any]:
    """Inner implementation — separated for testability without Celery."""
    # ... actual work here ...
    return {"status": "done", "record_id": record_id}
```

### 17.3 Registering a New Task

**Step 1** — Add the module to `imports` in `backend/core/celery_app.py`:

```python
celery_app.conf.update(
    imports=[
        # ... existing entries ...
        "tasks.my_new_cleanup_task",  # add your new module here
    ],
)
```

**Step 2** — If it's a scheduled (Beat) task, add it to `beat_schedule` in the same file:

```python
beat_schedule={
    # ... existing entries ...
    "my-cleanup-task-daily": {
        "task": "my_cleanup_task",              # must match the name= in @celery_app.task()
        "schedule": crontab(hour=5, minute=30), # daily at 5:30 AM UTC
    },
    "my-poll-task-every-15min": {
        "task": "my_poll_task",
        "schedule": crontab(minute="*/15"),     # every 15 minutes
    },
    "my-task-every-30s": {
        "task": "my_frequent_task",
        "schedule": 30.0,                       # every 30 seconds (float = seconds interval)
    },
}
```

**Step 3** — For event-driven tasks, enqueue from a route using `.delay()`:

```python
# Inside a route handler — enqueue without blocking the HTTP response
from tasks.my_event_task import my_event_task

# Fire and forget (most common pattern)
my_event_task.delay(str(record.id))

# With countdown delay
my_event_task.apply_async(args=[str(record.id)], countdown=60)
```

### 17.4 Testing a Celery Task

Test the `_impl()` function directly — do not test the Celery wrapper in unit tests.

```python
# tests/batch_bN/test_my_event_task.py
from tasks.my_event_task import _my_event_task_impl

def test_my_event_task_impl_processes_record(db_session, test_tenant):
    # Arrange: create test record
    record = SomeModel(tenant_id=test_tenant.id, status="pending")
    db_session.add(record)
    db_session.commit()

    # Act
    result = _my_event_task_impl(str(record.id), db_session)

    # Assert
    assert result["status"] == "done"
    db_session.refresh(record)
    assert record.status == "processed"
```

---

## 18. Server-Sent Events (SSE) Endpoint Pattern

SSE is **implemented** in `backend/services/dispatch_board_stream.py` (B3/A19). This section documents the canonical pattern for reuse in future SSE endpoints. SSE is the correct choice when updates flow server → client only; use WebSockets only if bidirectional streaming is required.

### 18.1 Why SSE for Dispatch Board and Sync Indicators

- Updates are server → client only (no client-initiated push needed — mutations go through normal REST endpoints)
- Works through standard HTTP infrastructure without special WebSocket proxy configuration
- Auto-reconnects on transient network failures (browser `EventSource` API)
- Scales simply — one SSE connection per client; at 100 tenants with 1–2 dispatchers each, expect 100–200 active connections, well within Fargate capacity

### 18.2 SSE Endpoint Implementation (FastAPI `StreamingResponse`)

```python
# api/routes/dispatch_board.py  (new file for B3/A19)
import asyncio
import json
import logging
from typing import AsyncGenerator
from uuid import UUID

from core.auth import AuthenticatedUser
from core.permissions import require_permission
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory channel registry: tenant_id → set of queue objects
# In production, this is backed by Redis Pub/Sub for multi-instance support
_sse_channels: dict[str, set[asyncio.Queue]] = {}


async def _event_generator(
    request: Request,
    tenant_id: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a tenant's dispatch board channel."""
    queue: asyncio.Queue = asyncio.Queue()

    # Register this client in the channel
    if tenant_id not in _sse_channels:
        _sse_channels[tenant_id] = set()
    _sse_channels[tenant_id].add(queue)

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Wait for an event (with heartbeat timeout)
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat comment to keep connection alive through proxies
                yield ": heartbeat\n\n"

    finally:
        # Deregister client on disconnect
        _sse_channels.get(tenant_id, set()).discard(queue)


@router.get(
    "/board/stream",
    response_class=StreamingResponse,
    summary="SSE stream for dispatch board live updates",
)
async def dispatch_board_stream(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """
    Server-Sent Events endpoint for the dispatch board.

    Authenticated via JWT in the Authorization header (or query param for SSE clients
    that can't set headers — JWT is validated and immediately discarded after auth).

    Returns a streaming response in text/event-stream format.
    Events are emitted when jobs are rescheduled, reassigned, or conflict status changes.
    """
    tenant_id = str(current_user.tenant_id)

    return StreamingResponse(
        _event_generator(request, tenant_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering (important for SSE)
        },
    )


def emit_to_tenant(tenant_id: str, event_type: str, payload: dict) -> None:
    """
    Broadcast an event to all SSE clients connected for a tenant.

    Called from write-path route handlers or Celery tasks after committing changes.

    Args:
        tenant_id: Target tenant (events are always tenant-scoped)
        event_type: e.g., "job_rescheduled", "job_reassigned", "conflict_detected"
        payload: Event-specific data dict
    """
    event = {"type": event_type, **payload}
    channels = _sse_channels.get(str(tenant_id), set())

    for queue in list(channels):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"SSE queue full for tenant {tenant_id}, dropping event")
```

### 18.3 Emitting Events from a Write Endpoint

```python
# Inside a route that modifies schedule data (e.g., POST /board/jobs/{id}/move)
from api.routes.dispatch_board import emit_to_tenant

def move_job(job_id: UUID, new_start: datetime, current_user: AuthenticatedUser, db: Session):
    # ... do the DB write ...
    db.commit()

    # Emit SSE event to all connected dispatchers for this tenant
    emit_to_tenant(
        tenant_id=str(current_user.tenant_id),
        event_type="job_rescheduled",
        payload={
            "job_id": str(job_id),
            "new_start_at": new_start.isoformat(),
        },
    )
    return updated_job
```

### 18.4 SSE Anti-Patterns

| ❌ Wrong | ✅ Correct |
|---|---|
| Calling `emit_to_tenant()` before `db.commit()` | Always emit AFTER the DB commit succeeds |
| One global SSE channel (no tenant isolation) | One channel entry per `tenant_id` — events never cross tenant boundaries |
| Missing `X-Accel-Buffering: no` header | Always set this — without it, nginx will buffer SSE frames and clients see delays |
| Relying on SSE as the only delivery path | SSE is ambient/best-effort; never use it for critical one-time notifications — use `notification_outbox` for that |

---

## 19. Webhook Handler Pattern

Two webhook implementations exist: QuickBooks HMAC-SHA256 (in `api/routes/webhooks.py`) and Twilio SMS STOP handler (same file). The pattern below extracts what's consistent across both.

### 19.1 Canonical Webhook Route Structure

```python
# api/routes/webhooks.py (add new handlers to this existing file)
import json
import logging
import uuid
from datetime import UTC, datetime

from app.models.system import WebhookEvent
from core.db import get_db
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlmodel import Session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/my-provider")
async def my_provider_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Webhook receiver for MyProvider.

    Security:  Signature verified on raw body BEFORE parsing.
    Idempotency: event_id checked against WebhookEvent table; duplicates return 200 immediately.
    Response:  Must return 200 within 5 seconds; heavy work goes to BackgroundTasks or Celery.
    """
    # Step 1: Get raw body before any parsing (needed for HMAC verification)
    payload_bytes = await request.body()

    # Step 2: Verify signature (return 401 if invalid — provider will retry)
    if not _verify_signature(request, payload_bytes):
        logger.warning("Invalid webhook signature from MyProvider")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Step 3: Parse payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = payload.get("id")  # provider-side unique ID for this event

    # Step 4: Idempotency — log webhook event (dedup on event_id if provider retries)
    existing = db.exec(
        select(WebhookEvent)
        .where(WebhookEvent.event_id == event_id)
        .where(WebhookEvent.source_app == "my_provider")
    ).first()
    if existing:
        logger.info(f"Duplicate webhook {event_id} — already processed, returning 200")
        return {"status": "duplicate", "event_id": event_id}

    webhook_log = WebhookEvent(
        id=uuid.uuid4(),
        tenant_id=None,      # populate if tenant can be resolved from payload
        source_app="my_provider",
        event_type=payload.get("type"),
        event_id=event_id,
        payload=payload,
        signature_valid=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(webhook_log)
    db.commit()

    # Step 5: Dispatch heavy work to BackgroundTasks or Celery (do NOT block response)
    background_tasks.add_task(
        _process_event,
        event_id=event_id,
        payload=payload,
    )

    # Step 6: Return 200 quickly
    return {"status": "received", "event_id": event_id}


def _verify_signature(request: Request, payload_bytes: bytes) -> bool:
    """Verify provider-specific HMAC or public-key signature."""
    import hashlib
    import hmac
    from core.config import settings

    expected = request.headers.get("X-My-Provider-Signature", "")
    computed = hmac.new(
        settings.MY_PROVIDER_WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, computed)


def _process_event(event_id: str, payload: dict) -> None:
    """Called by BackgroundTasks — import Celery task here to avoid circular deps."""
    from tasks.my_provider_sync import sync_entity_task
    sync_entity_task.delay(event_id=event_id, payload=payload)
```

### 19.2 Telnyx-Specific Pattern (B11/A59)

The Telnyx inbound SMS webhook sends `application/json` (not form-encoded like Twilio). Telnyx signature verification uses a public-key scheme via their SDK. The abstract `SmsCarrier.verify_webhook_signature()` method (see §22) encapsulates this.

### 19.3 Stripe-Specific Pattern (B14/A76)

Stripe sends `application/json` with a `Stripe-Signature` header. Stripe provides a Python helper for verification. The `stripe_webhook_event_processed` dedup table (unique on `event_id`) prevents double-processing on Stripe retries.

```python
import stripe
from core.config import settings

def _verify_stripe_signature(request: Request, payload_bytes: bytes) -> None:
    """Raises stripe.error.SignatureVerificationError if invalid."""
    sig_header = request.headers.get("Stripe-Signature", "")
    stripe.Webhook.construct_event(
        payload_bytes, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
```

---

## 20. Pre-Commit Staleness Check Pattern

Used by 8+ endpoints in A2–A88 (A19, A33, A45, A48, A50, A62, A80). Implement the shared utility once in B3/A19; all later batches import from it.

### 20.1 Shared Utility

```python
# utils/staleness_check.py  (new file — create in B3)
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException, status


def assert_not_stale(
    expected_updated_at: datetime | None,
    actual_updated_at: datetime,
    refreshed_payload: Dict[str, Any],
    entity_label: str = "record",
) -> None:
    """
    Raise 409 Conflict if the client's expected version doesn't match the DB.

    Call this BEFORE any write operation on a resource the user has been viewing.

    Args:
        expected_updated_at: Timestamp the client last saw (from request body).
                             If None, skip the check (not all endpoints require it).
        actual_updated_at:   Current `updated_at` from the freshly-fetched DB row.
        refreshed_payload:   The full refreshed entity dict to include in the 409 response.
        entity_label:        Human-readable label for the error message.

    Raises:
        HTTPException(409): With the refreshed payload so the client can re-render.
    """
    if expected_updated_at is None:
        return  # caller opted out of staleness check for this request

    # Strip microseconds to match serialization precision
    expected = expected_updated_at.replace(microsecond=0)
    actual = actual_updated_at.replace(microsecond=0)

    if expected != actual:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/stale-state",
                "title": "Record Updated",
                "status": 409,
                "detail": f"This {entity_label} was updated since you last viewed it. "
                          "Please refresh and re-submit.",
                "refreshed": refreshed_payload,
            },
        )
```

### 20.2 Using the Utility in a Route

```python
# Example: dispatch board move endpoint
from utils.staleness_check import assert_not_stale

@router.post("/jobs/{job_id}/move")
def move_job(
    job_id: UUID,
    payload: JobMoveRequest,  # includes optional expected_updated_at field
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == current_user.tenant_id)
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for concurrent modification before writing
    assert_not_stale(
        expected_updated_at=payload.expected_updated_at,
        actual_updated_at=job.updated_at,
        refreshed_payload=JobResponse.model_validate(job).model_dump(),
        entity_label="job",
    )

    # Safe to write — client had current version
    job.scheduled_start_at = payload.new_start_at
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job)
```

---

## 21. Three-Tier Settings Resolver Pattern

Used by A53 (B9) as the foundational resolver; consumed by A54, A55, A58, A67, A68. Build in B9; all later batches import from `services/setting_resolver.py`.

### 21.1 The Three-Tier Chain

```
User override (if tenant allows) → Tenant override → System default → Fallback constant
```

### 21.2 Implementation

```python
# services/setting_resolver.py  (new file — create in B9/A53)
from typing import Any
from uuid import UUID

from sqlmodel import Session, select


def get_effective_setting(
    db: Session,
    tenant_id: UUID,
    setting_key: str,
    fallback: Any = None,
) -> tuple[Any, str]:
    """
    Two-tier resolver: tenant override → system default → fallback constant.

    Returns:
        (value, scope) where scope is 'tenant' | 'system' | 'fallback'
    """
    from app.models.settings import TenantSetting, SystemConfig  # import here to avoid circular

    # Tier 1: tenant override
    tenant_setting = db.exec(
        select(TenantSetting)
        .where(TenantSetting.tenant_id == tenant_id)
        .where(TenantSetting.key == setting_key)
    ).first()

    if tenant_setting is not None:
        return tenant_setting.value, "tenant"

    # Tier 2: system default
    system_setting = db.exec(
        select(SystemConfig).where(SystemConfig.key == f"system_{setting_key}")
    ).first()

    if system_setting is not None:
        return system_setting.value, "system"

    # Tier 3: fallback constant (hardcoded in calling code)
    return fallback, "fallback"


def get_effective_setting_for_user(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    setting_key: str,
    fallback: Any = None,
) -> tuple[Any, str]:
    """
    Three-tier resolver: user override → tenant override → system default → fallback.

    Only applies when the setting metadata marks `allow_user_override = True`.

    Returns:
        (value, scope) where scope is 'user' | 'tenant' | 'system' | 'fallback'
    """
    from app.models.settings import UserSettingOverride, TenantSetting  # avoid circular

    # Check if tenant allows user override for this key
    tenant_setting = db.exec(
        select(TenantSetting)
        .where(TenantSetting.tenant_id == tenant_id)
        .where(TenantSetting.key == setting_key)
    ).first()

    allows_user_override = getattr(tenant_setting, "allow_user_override", True)

    if allows_user_override:
        user_override = db.exec(
            select(UserSettingOverride)
            .where(UserSettingOverride.tenant_id == tenant_id)
            .where(UserSettingOverride.user_id == user_id)
            .where(UserSettingOverride.setting_key == setting_key)
        ).first()

        if user_override is not None:
            return user_override.value, "user"

    # Fall through to two-tier resolver
    return get_effective_setting(db, tenant_id, setting_key, fallback)
```

### 21.3 Usage in a Route

```python
from services.setting_resolver import get_effective_setting_for_user

# Inside a voice intent handler resolving tone
tone, scope = get_effective_setting_for_user(
    db=db,
    tenant_id=current_user.tenant_id,
    user_id=current_user.id,
    setting_key="voice_persona_tone",
    fallback="balanced",
)
# tone = "playful" | "balanced" | "conservative"
# scope = "user" | "tenant" | "system" | "fallback"
```

---

## 22. Carrier-Agnostic Adapter Pattern

First implemented in B11/A59 for SMS via Telnyx. The existing `sms_service.py` is a concrete Twilio implementation — A59 replaces/wraps it with an ABC that makes provider swaps a one-class change.

### 22.1 Abstract Base Class

```python
# services/sms_carrier.py  (new file — create in B11/A59)
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass
class InboundMessage:
    from_number: str
    to_number: str
    body: str
    carrier_message_id: str
    received_at: str  # ISO timestamp from carrier


@dataclass
class SendResult:
    status: str          # "sent" | "failed"
    carrier_message_id: str | None
    error_message: str | None
    http_status: int
    retryable: bool


@dataclass
class ProvisionedNumber:
    phone_number: str    # E.164 format
    carrier_provisioning_id: str
    monthly_fee_cents: int


class SmsCarrier(ABC):
    """
    Abstract interface for SMS carrier integrations.
    All carrier interactions must go through this interface.

    Configuration: SMS_CARRIER env var selects the implementation at startup.
    Future provider swaps are a one-class change (new concrete subclass).
    """

    @abstractmethod
    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber: ...

    @abstractmethod
    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult: ...

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool: ...

    @abstractmethod
    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage: ...

    @abstractmethod
    def get_delivery_status(self, carrier_message_id: str) -> str: ...

    @abstractmethod
    def release_number(self, phone_number: str) -> None: ...
```

### 22.2 Mock Implementation (for testing without real carrier)

```python
# services/sms_carrier.py  (continued — MockSmsCarrier)
from typing import List


class MockSmsCarrier(SmsCarrier):
    """
    In-memory mock implementation for integration testing.
    Captures all calls without making real API requests.

    Usage:
        from unittest.mock import patch
        with patch("services.sms_carrier.get_sms_carrier", return_value=MockSmsCarrier()):
            ...
    """

    def __init__(self):
        self.sent_messages: List[dict] = []
        self.provisioned_numbers: List[str] = []

    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber:
        number = f"+1{area_code}5550001"
        self.provisioned_numbers.append(number)
        return ProvisionedNumber(
            phone_number=number,
            carrier_provisioning_id=f"mock-{number}",
            monthly_fee_cents=100,
        )

    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult:
        self.sent_messages.append({
            "from": from_number, "to": to_number, "body": body
        })
        return SendResult(
            status="sent",
            carrier_message_id=f"mock-msg-{len(self.sent_messages)}",
            error_message=None,
            http_status=200,
            retryable=False,
        )

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        return True  # Always valid in tests

    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage:
        import json
        data = json.loads(payload)
        return InboundMessage(
            from_number=data["from"],
            to_number=data["to"],
            body=data["body"],
            carrier_message_id=data.get("id", "mock-id"),
            received_at=data.get("received_at", "2026-01-01T00:00:00Z"),
        )

    def get_delivery_status(self, carrier_message_id: str) -> str:
        return "delivered"

    def release_number(self, phone_number: str) -> None:
        if phone_number in self.provisioned_numbers:
            self.provisioned_numbers.remove(phone_number)


def get_sms_carrier() -> SmsCarrier:
    """
    Factory function — select implementation from SMS_CARRIER env var.
    Call this instead of instantiating a carrier directly.
    """
    from core.config import settings

    carrier_name = getattr(settings, "SMS_CARRIER", "mock")

    if carrier_name == "telnyx":
        from services.telnyx_sms_carrier import TelnyxSmsCarrier
        return TelnyxSmsCarrier()
    else:
        return MockSmsCarrier()
```

### 22.3 Anti-Patterns

| ❌ Wrong | ✅ Correct |
|---|---|
| Importing Telnyx SDK directly in a route | Always call through `get_sms_carrier()` |
| Hardcoding `TelnyxSmsCarrier()` in service code | Use the factory `get_sms_carrier()` everywhere |
| Mocking at the Telnyx SDK level in tests | Mock at the `SmsCarrier` interface level (`MockSmsCarrier`) |
