# 📖 OpenAPI Export Script (`export_openapi_json.py`)

This directory contains the `export_openapi_json.py` script, which is responsible for extracting the live OpenAPI (Swagger) specification from our FastAPI application and saving it as **two output files** in one run.

## Why do we need this?

FastAPI automatically generates an OpenAPI schema in memory when the server runs. However, our React/React Native frontend needs a static file to generate strict TypeScript interfaces. This script bridges that gap, ensuring our frontend and backend are always speaking the exact same language.

In addition to the machine-readable JSON, the script generates a human/agent-readable Markdown summary (`openapi_schema_map.md`) that AI agents and engineers can scan instantly to find the correct path, parameters, and response shape for any endpoint — **without parsing the full JSON**.

## Expected Output

Running this script generates **two files** in the root of the `backend/` directory:

| File | Description |
|---|---|
| `openapi.json` | Full machine-readable OpenAPI spec (all paths, schemas, components). Consumed by `pnpm sync-api-types` to generate frontend TypeScript types. |
| `openapi_schema_map.md` | Human/agent-readable endpoint summary, grouped by tag. **The first file to check before writing any frontend hook or backend route.** |

> *Note: `openapi.json` is a generated artifact; this repo commits it (see below) so the API contract is reviewable. `openapi_schema_map.md` is committed as a developer reference.*

## How to Run It

You must run this script from within the active Python virtual environment so it has access to the FastAPI app and its dependencies.

```bash
# 1. Navigate to the backend folder
cd backend

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Execute the script — both files are generated in one run
python export_openapi_json.py
```

Expected output:
```
✅ Successfully exported OpenAPI schema to openapi.json
✅ Successfully exported OpenAPI schema map to openapi_schema_map.md
```

## How to Use Each File

### `openapi_schema_map.md` — before writing any frontend hook or backend route

1. Open `openapi_schema_map.md` and search (Ctrl+F / Cmd+F) for the resource name (e.g. `customers`, `jobs`, `reports`).
2. Find the exact endpoint path, HTTP method, and all parameter names/types.
3. Confirm auth is `Required` or `None` before wiring up the frontend hook.
4. Copy the response schema title (e.g. `CustomerListResponse`) to look up the full shape in `openapi.json` if needed.

### `openapi.json` — for TypeScript type generation

```bash
# From the frontend/ directory:
pnpm sync-api-types
```

This reads `backend/openapi.json` and regenerates all TypeScript interfaces. Run after every `python export_openapi_json.py` call.

---

## Who Uses Each File

| File | Used By | Purpose |
|---|---|---|
| `openapi.json` | `pnpm sync-api-types`, backend agents | Full spec; machine-parseable |
| `openapi_schema_map.md` | React Engineer, Python Engineer (pre-route check) | Fast lookup — path, params, response shape |

## When to Re-run

Run this script after **any endpoint is added, modified, or removed**. Both files must be current before any frontend implementation begins.

This is a **Definition of Done** requirement — no task that touches API routes is complete until `export_openapi_json.py` has been re-run and both output files reflect the current state of the API.

```bash
cd backend && source .venv/bin/activate && python export_openapi_json.py
```

## Schema Availability by Environment

*(Folded in from the archived `README-openapi-json-status.md` on 2026-08-20.)*

### How it works

[`app/main.py`](app/main.py) controls whether the live schema endpoints are served:

```python
# /docs, /redoc, and /openapi.json are disabled in production.
# They remain enabled in dev and qa for internal developer testing.
_is_production = _settings.ENVIRONMENT == "production"
app = FastAPI(
    title="Pilot for Trades API",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)
```

The `ENVIRONMENT` value comes from [`core/config.py`](core/config.py) and is set via the `.env` file or ECS task environment variables.

### Behavior per environment

| Environment | `/docs` | `/redoc` | `/openapi.json` (live) | `openapi.json` (committed file) |
|---|---|---|---|---|
| `dev` | ✅ Served | ✅ Served | ✅ Served | ✅ Present |
| `qa` | ✅ Served | ✅ Served | ✅ Served | ✅ Present |
| `staging` | ❌ 404 | ❌ 404 | ❌ 404 | ✅ Present |
| `production` | ❌ 404 | ❌ 404 | ❌ 404 | ✅ Present |

When `ENVIRONMENT=production`, FastAPI never registers the schema route at all — the 404 is a hard route miss, not a permission error. There is **zero schema leakage in production**.

> **The committed `openapi.json` file in this directory is for tooling use only.** It is never served by the production API server. Keep it regenerated and committed when routes change so that Postman collections and frontend type generation stay in sync during dev/qa work.

---

## Example `openapi_schema_map.md` Entry

```markdown
### customers

#### `GET /api/v1/customers`
**Summary**: List customers for tenant  
**Auth**: Required  

**Parameters**:
- `search` (query, string, optional) — Filter by name or email
- `page` (query, integer, optional, default: 1)
- `page_size` (query, integer, optional, default: 50)

**Response 200**: `CustomerListResponse`
```json
{
  "items": [{"id": "string", "display_name": "string", ...}],
  "total": 0,
  "page": 1
}
```

---
```
