# Implementation Prompt: Enhance DB Model Map + OpenAPI Schema Map Generator

**Mode**: Pilot Python Engineer  
**Estimated effort**: 1–2 hour session  
**Priority**: High — these artifacts directly prevent AI agent rework in all subsequent batches

---

## Context

We have two existing scripts that generate reference files used by all AI agents working on this codebase:

1. **`backend/generate_db_model_map.py`** → generates **`backend/db_models_map.md`**: lists every class in `backend/app/` organized by file
2. **`backend/export_openapi_json.py`** → generates **`backend/openapi.json`**: the full FastAPI OpenAPI spec

Two problems have been causing repeated agent rework:

1. `db_models_map.md` **conflates DB table classes with Enums/Schemas** — agents write queries against classes like `InvoiceStatus` or `Currency` thinking they are DB tables, when they're actually Python string Enums.
2. `openapi.json` is **too large to navigate quickly** — agents skip or skim it, leading to wrong endpoint URLs and wrong parameter names in frontend hooks.

---

## Task Overview

You must complete three things in this session:

1. **Enhance `generate_db_model_map.py`** to separate `table=True` SQLModel classes from Enums/Schemas, and include the actual `__tablename__` value for table classes.
2. **Enhance `export_openapi_json.py`** to also generate a human/agent-readable `openapi_schema_map.md` summary file in the same run.
3. **Update two README files** that document these tools.

---

## Pre-Work: Read These Files First

**MANDATORY — read every file listed before writing a single line of code:**

```
backend/generate_db_model_map.py       ← the script to enhance
backend/export_openapi_json.py         ← the script to enhance
backend/README-app-db-models.md        ← the README to update
backend/README-export-openapi-json.md  ← the README to update
backend/db_models_map.md               ← the current output (first 80 lines)
```

Use `read_file` for each. Do not assume you know what's in them — they may have been updated since you last saw them.

Also run:
```bash
cd backend && source .venv/bin/activate && python export_openapi_json.py
```
to confirm the script currently works before modifying it.

---

## Task 1: Enhance `generate_db_model_map.py`

### What to change

The current script outputs ALL class definitions equally. The fix: use Python AST to detect which classes are SQLModel table classes (have `table=True` in their class definition keyword arguments) and extract their `__tablename__` assignment.

### Required output format

The new `db_models_map.md` must group classes per file into two sections:

```markdown
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
```

If a file has no DB tables (only enums/schemas), show only the "Enums / Schemas / Helpers" section.  
If a file has no enums/schemas (only tables), show only the "DB Tables" section.  
Files with zero classes are still skipped entirely.

### AST detection logic

A class is a DB table if its class definition has keyword argument `table=True`. In Python AST this means the class is defined as:

```python
class MyModel(SomeBase, SQLModel, table=True):
    ...
```

Which appears in the AST as a `ClassDef` with `keywords` list containing an entry where `kw.arg == 'table'` and `kw.value` is a `Constant` with value `True`.

The `__tablename__` is a module-level assignment inside the class body:
```python
class MyModel(...):
    __tablename__ = "my_model"
```
In AST: an `Assign` node in `class_node.body` where `targets[0].id == '__tablename__'` and the value is an `ast.Constant`.

If `__tablename__` is not found (some models inherit it), output `→ table: (inherited)`.

### Implementation approach

```python
def classify_classes(file_path):
    """Returns (table_classes, non_table_classes) where each table class is (name, tablename)."""
    try:
        with open(file_path, encoding="utf-8") as f:
            node = ast.parse(f.read(), filename=str(file_path))
    except Exception:
        return [], []
    
    table_classes = []    # list of (class_name, tablename_str)
    other_classes = []    # list of class_name strings
    
    for n in node.body:
        if not isinstance(n, ast.ClassDef):
            continue
        
        # Check for table=True keyword in class definition
        is_table = any(
            kw.arg == 'table' and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in n.keywords
        )
        
        if is_table:
            # Find __tablename__
            tablename = "(inherited)"
            for stmt in n.body:
                if (isinstance(stmt, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == '__tablename__' for t in stmt.targets)
                        and isinstance(stmt.value, ast.Constant)):
                    tablename = stmt.value.value
                    break
            table_classes.append((n.name, tablename))
        else:
            other_classes.append(n.name)
    
    return table_classes, other_classes
```

### Regenerate and verify

After updating the script, regenerate the file and verify the output looks correct:

```bash
cd backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
```

Spot-check: `Invoice` should appear as a DB Table with `table: invoice`. `InvoiceStatus` should appear as an Enum/Schema. `StandardAuditMixin` should appear as an Enum/Schema (it is NOT `table=True`).

---

## Task 2: Enhance `export_openapi_json.py` to Also Generate `openapi_schema_map.md`

### What to change

After writing `openapi.json`, the script must also write `openapi_schema_map.md` — a Markdown summary of every endpoint that is immediately useful to both AI agents and developers without parsing the full JSON.

### Required `openapi_schema_map.md` format

```markdown
# Pilot for Trades — OpenAPI Schema Map

**Generated**: 2026-06-03T14:00:00Z  
**Source**: openapi.json  
**Purpose**: Human/agent-readable endpoint summary. Check this before writing any frontend hook or backend route.

---

## Endpoints by Tag

### customers

#### `GET /api/v1/customers`
**Summary**: List customers for tenant  
**Auth**: Required — `customers.view`  
**Query params**:
- `search` (string, optional) — Filter by name or email
- `page` (integer, optional, default: 1)
- `page_size` (integer, optional, default: 50)

**Response 200**: `CustomerListResponse`
```json
{
  "items": [{"id": "uuid", "display_name": "string", "type": "string", ...}],
  "total": 0,
  "page": 1
}
```

---

#### `POST /api/v1/customers`
**Summary**: Create a new customer  
**Auth**: Required — `customers.create`  
**Request body**: `CustomerCreate`
```json
{"display_name": "string", "type": "person|company", ...}
```

**Response 201**: `CustomerResponse`

---
```

### Implementation approach

After `json.dump(schema, f, indent=2)` in `export_schema()`, add a call to a new `export_schema_map(schema, map_path)` function. This function:

1. Iterates `schema['paths']` — each key is a path string (e.g., `/api/v1/customers`)
2. For each path, iterates the HTTP methods (`get`, `post`, `patch`, `delete`)
3. Extracts: `summary`, `tags`, `parameters` (name, in, required, schema.type, description), `requestBody` schema ref or inline, `responses` (status codes + schema refs or examples)
4. Groups endpoints by the first tag
5. Writes Markdown

**Key extraction helpers:**

```python
def _resolve_schema_ref(schema_obj, full_spec):
    """Follow a $ref if present, otherwise return the object itself."""
    if '$ref' in schema_obj:
        ref_path = schema_obj['$ref'].lstrip('#/').split('/')
        node = full_spec
        for part in ref_path:
            node = node[part]
        return node
    return schema_obj

def _schema_to_example(schema_obj, full_spec, depth=0):
    """Generate a simple example JSON structure from a schema (max 2 levels deep)."""
    if depth > 2:
        return "..."
    resolved = _resolve_schema_ref(schema_obj, full_spec)
    if resolved.get('type') == 'object':
        props = resolved.get('properties', {})
        return {k: _schema_to_example(v, full_spec, depth+1) for k, v in list(props.items())[:8]}
    elif resolved.get('type') == 'array':
        items = resolved.get('items', {})
        return [_schema_to_example(items, full_spec, depth+1)]
    elif resolved.get('type') == 'string':
        return resolved.get('example', 'string')
    elif resolved.get('type') == 'integer':
        return resolved.get('example', 0)
    elif resolved.get('type') == 'boolean':
        return False
    elif resolved.get('type') == 'number':
        return 0.0
    else:
        return resolved.get('title', 'object')
```

**For auth/permission extraction**: FastAPI security schemes show up in `operation.get('security', [])`. The permission string is typically in the operation's `description` or a custom extension. If not explicitly present, write `Required` when `security` is non-empty, `None` when `security` is empty or absent.

**Default output path**: `openapi_schema_map.md` in the same directory as `openapi.json` (i.e., `backend/`).

### Updated script signature

```python
def export_schema(output_path="openapi.json", map_path="openapi_schema_map.md"):
    try:
        schema = app.openapi()
        
        # Always write openapi.json
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"✅ Successfully exported OpenAPI schema to {output_path}")
        
        # Always write openapi_schema_map.md
        export_schema_map(schema, map_path)
        print(f"✅ Successfully exported OpenAPI schema map to {map_path}")
        
    except Exception as e:
        print(f"❌ Failed to export schema: {e}")
        sys.exit(1)
```

### Regenerate and verify

```bash
cd backend && source .venv/bin/activate
python export_openapi_json.py
```

Verify two files are written: `openapi.json` (unchanged behavior) and `openapi_schema_map.md` (new file).

Spot-check `openapi_schema_map.md`: Find `GET /api/v1/reports/profitability`. Confirm it shows `date_from` and `date_to` as required params (NOT `period`). This is the exact endpoint that was wrong in FE-B4 and caused rework.

Find `GET /api/v1/scheduling/dispatch-board`. Confirm the path is exactly this (NOT `/api/v1/schedule/board`). This was another source of rework.

---

## Task 3: Update `README-app-db-models.md`

Update **`backend/README-app-db-models.md`** to reflect the enhanced output format:

1. Update the "What it does" section for `generate_db_model_map.py` to explain that it now separates DB table classes from Enums/Schemas and includes `__tablename__`.
2. Update the "Example output" section to show the new grouped format with `DB Tables` and `Enums / Schemas / Helpers` sections.
3. Update the "When to Regenerate" section to match the mandatory triggers now in `pilot-python-engineer-methods.md` §16.5:
   - After any model file in `app/models/` is added or modified
   - After any class is renamed
4. Add a note explaining why the table/enum separation matters: "Only `DB Tables` entries are queryable via `select()`. Never use `db.get()` or `select()` against Enum/Schema classes — they are not database tables."

---

## Task 4: Update `README-export-openapi-json.md`

Update **`backend/README-export-openapi-json.md`** to reflect that the script now generates two files:

1. Update the title and intro to say "generates TWO output files"
2. Update the "Expected Output" section to list both files:
   - `openapi.json` — full machine-readable OpenAPI spec; consumed by `pnpm sync-api-types` to generate frontend TypeScript types
   - `openapi_schema_map.md` — human/agent-readable endpoint summary; **the first file to check before writing any frontend hook or backend route**
3. Update the "How to Run It" section — the command is unchanged (`python export_openapi_json.py`), but explain that both files are generated in one run
4. Add a new "Who Uses Each File" section:

   | File | Used By | Purpose |
   |---|---|---|
   | `openapi.json` | `pnpm sync-api-types`, backend agents | Full spec; machine-parseable |
   | `openapi_schema_map.md` | React Engineer, Python Engineer (pre-route check) | Fast lookup — path, params, response shape |

5. Add a "When to Re-run" section with the mandatory trigger: "Run this script after any endpoint is added, modified, or removed. Both files must be current before any frontend implementation begins."

---

## Definition of Done

- [x] `python generate_db_model_map.py app > db_models_map.md` runs cleanly with no errors
- [x] `db_models_map.md` output separates `DB Tables` from `Enums / Schemas / Helpers` for every file
- [x] `Invoice` appears as `DB Table → table: invoice`; `InvoiceStatus` appears under `Enums / Schemas / Helpers`
- [x] `StandardAuditMixin` appears under `Enums / Schemas / Helpers` (it is NOT `table=True`)
- [x] `python export_openapi_json.py` runs cleanly with no errors
- [x] Both `openapi.json` and `openapi_schema_map.md` are written in one run
- [x] `openapi_schema_map.md` contains every endpoint in the schema, grouped by tag
- [x] `GET /api/v1/reports/profitability` shows `date_from` and `date_to` as required params
- [x] `GET /api/v1/scheduling/dispatch-board` shows the correct path
- [x] `README-app-db-models.md` updated with new output format description
- [x] `README-export-openapi-json.md` updated with two-file output description
- [x] No regressions: existing `openapi.json` content is unchanged (just now generated alongside the map)
- [x] No new tests are required for these utility scripts (they are dev-time tools, not application code)
- [x] Update this Definition of Done list with completion checks next to each item if completed
then in the dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md file:
- [x] Mark this task (BETA-B0 batch) as complete in the impl plan tracker in Section 9
- [x] Summary of work accomplished added to new sub-section in impl plan tracker in Section 9
