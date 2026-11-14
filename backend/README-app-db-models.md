# Pilot for Trades — Database Models & Import Mapping Tools

This directory contains two utility scripts that statically analyze the Pilot for Trades codebase and generate comprehensive Markdown reference files for AI coding agents and developers.

Instead of executing imports at runtime (which triggers circular dependency errors in large FastAPI apps), both scripts use Python's built-in `ast` (Abstract Syntax Tree) module to safely parse source files without running any application code.

**Use these generated files as AI agent context** — giving an agent `db_models_map.md` and `app_model_import.md` ensures it references correct file paths and import statements when writing new code or tests.

---

## Scripts at a Glance

| Script | Output File | What It Scans | What It Extracts |
| :--- | :--- | :--- | :--- |
| [`generate_db_model_map.py`](generate_db_model_map.py) | `db_models_map.md` | Application source directory (e.g. `app/`) | All class definitions separated into **DB Tables** (`table=True`) and **Enums / Schemas / Helpers**, organized by file |
| [`generate_app_import_map.py`](generate_app_import_map.py) | `app_model_import.md` | Test directory (e.g. `tests/`) | Deduplicated model import statements from all test/factory/fixture files |

> **Run both scripts from the `backend/` directory.**

---

## 1. `generate_db_model_map.py` → `db_models_map.md`

### What it does

Recursively scans a target directory for all `.py` files and uses AST to classify every class definition into two groups:

1. **DB Tables** — SQLModel classes with `table=True` in their class definition. These are actual database tables, queryable via `select()`. The `__tablename__` value is extracted and shown next to each class.
2. **Enums / Schemas / Helpers** — All other class definitions (Python enums, Pydantic/SQLModel schemas, mixins, base classes, etc.). **These are NOT database tables and must never be used in `select()` queries or `db.get()` calls.**

> ⚠️ **Critical for AI agents**: Only `DB Tables` entries are queryable via `select()`. Never use `db.get()` or `select()` against Enum/Schema classes — they are not database tables.

**Directories automatically skipped:** `__pycache__`, `venv`, `.venv`, `alembic`, `tests`  
**`__init__.py` files:** included only if they actually define classes (otherwise skipped).  
**Files with zero classes:** skipped entirely.  
**Files with only DB Tables:** only the "DB Tables" section is shown.  
**Files with only Enums/Schemas:** only the "Enums / Schemas / Helpers" section is shown.

### How to Use the Output (`db_models_map.md`)

1. **Before writing a query or service method**: search `db_models_map.md` for the class name you plan to use (e.g. `Customer`, `Job`, `Invoice`).
2. **Confirm it appears under "DB Tables"** — if it's under "Enums / Schemas / Helpers", it is NOT a database table and cannot be used in `select()` or `db.get()`.
3. **Copy the `__tablename__`** value shown next to the class if you need to reference the raw table name in a migration or raw SQL query.
4. **Copy the file path** from the `###` header (e.g. `models/billing.py`) to find the correct import: `from app.models.billing import Invoice`.

### How to run

Run from the `backend/` directory, passing your application source folder as the argument and redirecting stdout to the output file:

```bash
# From the backend/ directory (with venv active):
python generate_db_model_map.py app > db_models_map.md
```

Replace `app` with whatever directory contains your SQLModel/SQLAlchemy model classes.

### Example output (`db_models_map.md`)

```markdown
# Pilot for Trades Database Models Map

**Source Directory:** `/Users/you/project/backend/app`

> **Key**: Only **DB Tables** entries are queryable via `select()`. Never use `db.get()` or `select()` against Enum/Schema classes — they are not database tables.

### `models/billing.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `Invoice` → table: `invoice`
- `InvoiceLine` → table: `invoice_line`
- `Payment` → table: `payment`
- `Subscription` → table: `subscription`

**Enums / Schemas / Helpers** (NOT DB tables — do not use in `select()` queries):
- InvoiceStatus
- Currency
- PaymentStatus
- PaymentType

---

### `models/mixins.py`

**Enums / Schemas / Helpers** (NOT DB tables — do not use in `select()` queries):
- StandardAuditMixin
- SoftDeleteMixin

---
```

### When to Regenerate

Re-run this script any time you:

- Add a new model file to `app/models/`
- Add a new class to any existing model file in `app/models/`
- Rename or move a model class
- Onboard a new AI agent that needs codebase context

```bash
cd backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
```

This is a **Definition of Done** requirement — no task that modifies model files is complete until `db_models_map.md` is current.

---

## 2. `generate_app_import_map.py` → `app_model_import.md`

### What it does

Recursively scans a target directory for **test files, `conftest.py`, factory files, and fixture files** — then extracts every `from <module> import <Name>` statement where the imported name starts with an uppercase letter (the Python convention for classes and models).

The result is a **deduplicated, alphabetically sorted** list of all model import statements actually used across your test suite. This makes it trivial to copy the correct import paths into new test files or to audit which models are being tested.

**Files scanned:** any file whose name starts with `test_`, is named `conftest.py`, or contains `factory` or `fixture` in its name.

**Standard/third-party libraries filtered out** (not included in output):
`pytest`, `unittest`, `typing`, `datetime`, `sqlalchemy`, `pydantic`, `uuid`, `enum`, `mock`, `factory`

### How to run

Run from the `backend/` directory, passing your tests directory as the argument and redirecting stdout to the output file:

```bash
# From the backend/ directory:
python generate_app_import_map.py tests > app_model_import.md
```

Replace `tests` with the path to your test directory if it differs.

### Example output (`app_model_import.md`)

```markdown
# Pilot for Trades Consolidated Model Imports

**Source Directory:** `/Users/you/project/backend/tests`

*Note: This is a deduplicated list of all application models imported across the test suite.*

- `from app.models.customer import Customer`
- `from app.models.job import Job`
- `from app.models.job import JobAssignment`
- `from app.models.job import JobTimeEntry`
- `from app.models.quote import Quote`
- `from app.models.quote import QuoteLine`
```

### When to Regenerate

Re-run this script any time you:

- Add a new test file to `tests/`
- Add new factory or fixture files that import models

```bash
cd backend && source .venv/bin/activate
python generate_app_import_map.py tests > app_model_import.md
```

---

## Running Both Scripts Together

To regenerate both reference files in a single step, run from the `backend/` directory:

```bash
python generate_db_model_map.py app > db_models_map.md && \
python generate_app_import_map.py tests > app_model_import.md
```

---

## How the Scripts Work (Technical Detail)

Both scripts use `ast.parse()` to convert source files into a syntax tree **without importing or executing the code**. This means:

- No `ImportError` or circular import failures
- No side effects (no DB connections, no app startup)
- Works even on files with incomplete dependencies

[`generate_db_model_map.py`](generate_db_model_map.py) walks `node.body` looking for `ast.ClassDef` nodes, then checks each class for the `table=True` keyword argument to classify it as a DB table. For DB tables, it also searches the class body for an `__tablename__` assignment.

[`generate_app_import_map.py`](generate_app_import_map.py) walks `node.body` looking for `ast.ImportFrom` nodes, then filters to names beginning with an uppercase letter.
