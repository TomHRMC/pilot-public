# Pilot for Trades Backend API

This directory contains the core Python application for Pilot for Trades, built with FastAPI, SQLModel, and Celery.

---

## 🚀 Quick Start: Development Workflow

To run the full Pilot for Trades backend stack locally, you need **2 terminals** + **6 Docker containers**.

### Prerequisites

1. **Docker Desktop** running with all 6 containers (managed by root `docker-compose.yml`):
   - `pilot_postgres` - PostgreSQL 17 database
   - `pilot_redis` - Redis for Celery broker
   - `pilot_celery_worker` - Background task processor
   - `pilot_celery_beat` - Scheduled task scheduler
   - `pilot_ollama` - Ollama for LLM intent parsing
   - `pilot_whisper` - Whisper Large-v3 for speech-to-text

2. **Python 3.14+ virtual environment** activated for FastAPI server:
   ```bash
   cd backend
   source .venv/bin/activate
   ```

3. **Environment variables** configured in `backend/.env`:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

---

### Terminal Setup (2 Terminals Only!)

**🎉 New Simplified Workflow:** Celery worker and beat now run in Docker containers automatically. You only need to manually run ngrok and FastAPI server.

#### **Terminal 1: ngrok Tunnel** (for QuickBooks OAuth & Webhooks)
```bash
ngrok http --domain=your-tunnel.ngrok-free.dev 8000
```

**Why:** QuickBooks requires HTTPS for OAuth callbacks and webhooks. Keep this running during development.

**Verify:** Visit https://your-tunnel.ngrok-free.dev/docs (should show FastAPI docs)

---

#### **Terminal 2: FastAPI Server** (uvicorn)
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Why:** Runs the main API with hot-reload enabled.

**Verify:** Visit http://localhost:8000/docs (should show OpenAPI documentation)

---

### Monitoring Docker Services

**Celery Worker & Beat** now run in Docker containers. Monitor them with:

```bash
# View Celery worker logs (from project root)
docker compose logs -f celery_worker

# View Celery beat logs
docker compose logs -f celery_beat

# View all container logs
docker compose logs -f

# Check container health status
docker compose ps

# Restart Celery worker (if needed)
docker compose restart celery_worker

# Restart Celery beat (if needed)
docker compose restart celery_beat
```

**Verify Celery is working:**
```bash
# Check worker is connected
docker compose logs celery_worker | grep "ready"

# Check beat is sending tasks
docker compose logs celery_beat | grep "Sending due task"

# Inspect registered tasks
docker exec -it pilot_celery_worker celery -A core.celery_app inspect registered
```

---

### Docker Container Status

Verify all required containers are running (from project root):

```bash
docker ps
```

**Expected output (6 containers):**
```
CONTAINER ID   IMAGE                                NAMES                      STATUS
abc123...      pgvector/pgvector:pg17              pilot_postgres           Up (healthy)
def456...      redis:7-alpine                      pilot_redis              Up (healthy)
ghi789...      pilot-celery_worker               pilot_celery_worker      Up
jkl012...      pilot-celery_beat                 pilot_celery_beat        Up
mno345...      ollama/ollama:latest                pilot_ollama             Up
pqr678...      fedirz/faster-whisper-server        pilot_whisper            Up
```

**If containers are not running:**
```bash
# From project root - start all 6 containers
docker compose up -d

# Start only backend stack (skip AI services to save resources)
docker compose up -d postgres redis celery_worker celery_beat

# Rebuild containers after code changes
docker compose up -d --build celery_worker celery_beat
```

---

## Local Setup (First Time Only)

### 1. Environment Variables
Ensure you have a `.env` file in the `backend/` directory. If you don't have one, copy the example file:
```bash
cd backend
cp .env.example .env
```

**Critical environment variables:**
```bash
# Database
DATABASE_URL=postgresql://pilot_user:<password>@localhost:5432/pilot_dev

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ngrok (for QuickBooks OAuth/Webhooks)
API_BASE_URL=https://your-tunnel.ngrok-free.dev
QUICKBOOKS_REDIRECT_URI=${API_BASE_URL}/api/v1/integrations/quickbooks/callback

# QuickBooks (from Intuit Developer Portal)
QUICKBOOKS_CLIENT_ID=your_client_id_here
QUICKBOOKS_CLIENT_SECRET=your_client_secret_here
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN=your_verifier_token_here

# Encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your_fernet_key_here

# SendGrid (for email notifications)
SENDGRID_API_KEY=your_sendgrid_api_key_here
SENDGRID_FROM_EMAIL=noreply@pilotfortrades.com

# Test Endpoints
TEST_ENDPOINT_ENABLED=true
ENVIRONMENT=dev
TEST_TENANT_ID=00000000-0000-0000-0000-000000000001
TEST_USER_ID=00000000-0000-0000-0000-000000000002
```

### 2. Create Virtual Environment

If you don't have a virtual environment yet:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Ensure your packages are up to date:

```bash
pip install -r requirements.txt
```

### 4. Database Migrations

Run Alembic migrations to create database schema:

```bash
alembic upgrade head
```

### 5. Seed Test Data (Optional)

Create test tenant and user for `/test` endpoints:

```bash
python migrations/scripts/seed_core.py
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
```

See [`README-seed-data.md`](README-seed-data.md) for the full seed system (Groups A–D, `--env`/`SEED_ENV` targeting, QA/prod orchestrators — DB-MGMT-1 / ADR-0016).

---

## Running the Application

### Start the FastAPI Server

To run the Python FastAPI app from the command line for local development (with hot-reloading enabled):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access the API:**
- Local: http://localhost:8000/docs
- Public (via ngrok): https://your-tunnel.ngrok-free.dev/docs

### Celery Worker & Beat (Now in Docker!)

**✅ Celery services now run automatically in Docker containers.**

Previously, you needed to manually run Celery worker and beat in separate terminals. Now they start automatically with `docker compose up -d`.

**Check Celery status:**
```bash
# From project root
docker compose logs celery_worker | tail -20
docker compose logs celery_beat | tail -20
```

**Scheduled tasks (managed by Celery Beat):**
- `cleanup_expired_idempotency_keys` - Daily at 2:00 AM (removes keys > 24 hours old)
- `cleanup_old_failed_keys` - Daily at 2:30 AM (removes keys > 7 days old)
- `poll_pending_notifications` - Every 30 seconds (processes email/SMS queue)
- `expire_old_sessions` - Daily at 3:00 AM (expires sessions > 24 hours)
- `archive_old_sessions` - Daily at 3:30 AM (archives sessions > 30 days)
- `cleanup_orphaned_messages` - Daily at 4:00 AM (deletes orphaned conversation messages)
- `refresh_quickbooks_tokens` - Every 30 minutes (refreshes OAuth tokens)
- `sync_all_tenants_customers` - Every 15 minutes (syncs QuickBooks customers)
- `archive_audit_logs` - Daily at 1:00 AM (archives old audit logs)

**Trigger a task manually (for testing):**
```bash
# From backend directory with .venv activated
python -c "from tasks.test_task import test_task; test_task.delay('Hello from manual trigger')"

# Or via Docker
docker exec -it pilot_celery_worker python -c "from tasks.test_task import test_task; test_task.delay('Test')"
```

---

## Testing with Test Endpoints

Most authenticated API routes have unauthenticated `/test` twins (about 330), which return 403 unless `ENVIRONMENT` is dev or qa and `TEST_ENDPOINT_ENABLED=true`. These test endpoints enable rapid development and testing without JWT token generation overhead.

### Overview

**Purpose:** Eliminate the need for JWT authentication during development and testing.

**Benefits:**
- ⚡ **Faster Testing:** No JWT token generation needed (~10-15s → <5s per test)
- 🧪 **Simpler Tests:** No auth mocking required in Pytest
- 👥 **Easier Onboarding:** New developers can test APIs in minutes
- 🔄 **Identical Logic:** Test endpoints share the same business logic as authenticated endpoints

### Security

**Test endpoints are ONLY available when:**
1. `TEST_ENDPOINT_ENABLED=true` in your `.env` file
2. `ENVIRONMENT` is set to `dev` or `qa` (blocked in staging/production)

**Production Safety:**
- Default: `TEST_ENDPOINT_ENABLED=false`
- Returns HTTP 403 when disabled or in production/staging
- Test data isolated to dedicated test tenant

### Setup

1. **Enable test endpoints** in your `.env` file:
```bash
TEST_ENDPOINT_ENABLED=true
ENVIRONMENT=dev
TEST_TENANT_ID=00000000-0000-0000-0000-000000000001
TEST_USER_ID=00000000-0000-0000-0000-000000000002
```

2. **Seed test tenant and user** (one-time setup):
```bash
source .venv/bin/activate
python migrations/scripts/seed_core.py
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
```

3. **Restart the FastAPI server** to pick up the new routes:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Available Test Endpoints

All authenticated endpoints have `/test` suffix variants:

| Authenticated Endpoint | Test Endpoint (No Auth) |
|------------------------|--------------------------|
| `POST /api/v1/customers` | `POST /api/v1/customers/test` |
| `GET /api/v1/customers` | `GET /api/v1/customers/test` |
| `POST /api/v1/quotes` | `POST /api/v1/quotes/test` |
| `GET /api/v1/quotes` | `GET /api/v1/quotes/test` |
| ... | ... |

### Usage Examples

#### Create Customer (No Authentication Required)
```bash
curl -X POST http://localhost:8000/api/v1/customers/test \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Mike the Solo Contractor",
    "type": "person",
    "email": "mike@electrical.example.com",
    "mobile_phone": "+1-555-0123"
  }'
```

**Response:**
```json
{
  "id": "uuid-here",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "display_name": "Mike the Solo Contractor",
  "type": "person",
  "email": "mike@electrical.example.com",
  "mobile_phone": "+1-555-0123",
  "created_at": "2026-03-16T19:00:00Z",
  ...
}
```

#### List Customers in Test Tenant
```bash
curl http://localhost:8000/api/v1/customers/test
```

#### Create Quote (No Authentication Required)
```bash
curl -X POST http://localhost:8000/api/v1/quotes/test \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "uuid-from-previous-create",
    "quote_number": "Q-2026-001",
    "status": "draft"
  }'
```

### Test Tenant Context

All test endpoints use the following hardcoded context:
- **Tenant ID:** `00000000-0000-0000-0000-000000000001`
- **User ID:** `00000000-0000-0000-0000-000000000002`
- **Email:** `dev@pilot.local`

Data created via test endpoints is isolated to this test tenant and won't affect other tenants.

### Testing Environment Guards

**Verify test endpoints are blocked in production:**
```bash
# Set environment to production
export ENVIRONMENT=production

# This should return HTTP 403
curl -X POST http://localhost:8000/api/v1/customers/test \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Test", "type": "person"}'
```

**Expected Response:**
```json
{
  "detail": {
    "error": "test_endpoints_disabled",
    "message": "Test endpoints are only available in DEV/QA environments when TEST_ENDPOINT_ENABLED=true. Current environment: production, TEST_ENDPOINT_ENABLED=true",
    "hint": "If you're in development, set TEST_ENDPOINT_ENABLED=true and ENVIRONMENT=dev in your .env file"
  }
}
```

### Pytest Integration

Test endpoints simplify testing by eliminating JWT mocking:

```python
# OLD: Complex auth mocking
def test_create_customer_with_auth(db_session, mock_jwt):
    # ... 20 lines of JWT setup ...
    pass

# NEW: Direct test endpoint usage
def test_create_customer_test_endpoint(db_session):
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    response = client.post("/api/v1/customers/test", json={
        "display_name": "Jane Smith",
        "type": "person"
    })
    
    assert response.status_code == 201
    assert response.json()["display_name"] == "Jane Smith"
```

Run the test suite:
```bash
source .venv/bin/activate
pytest backend/tests/test_test_endpoints.py -v
```

### Troubleshooting

**"404 Not Found" when accessing test endpoints:**
- Ensure the FastAPI server is restarted after adding test endpoints
- Verify the correct path: `/api/v1/customers/test` (not `/v1/customers/test`)

**"403 Forbidden" when accessing test endpoints:**
- Check `TEST_ENDPOINT_ENABLED=true` in `.env`
- Check `ENVIRONMENT=dev` (or `qa`) in `.env`
- Restart the server after changing `.env`

**Test tenant not found:**
- Run the seed scripts: `python migrations/scripts/seed_core.py && python migrations/scripts/seed_platform.py && python migrations/scripts/seed_test_tenant.py`
- Verify in database: `SELECT * FROM tenant WHERE id = '00000000-0000-0000-0000-000000000001';`

### API Documentation

Test endpoints appear in the OpenAPI docs at:
- **Local:** http://localhost:8000/docs
- **Look for endpoints with `/test` suffix**

---

## Local Development: External Webhooks & OAuth (ngrok)

Because external providers like QuickBooks strictly require secure `https://` URLs for webhooks and OAuth callbacks, we use **ngrok** to expose the local FastAPI server to the internet.

### 1. Start the Tunnel
To open the secure tunnel to your local port 8000, open a new terminal tab and run:
```bash
ngrok http --domain=your-tunnel.ngrok-free.dev 8000
```

*(Keep this terminal tab open. If ngrok is closed, external integrations will fail to reach your local machine).*

### 2. Update Environment Variables

Ensure your `backend/.env` file has the correct `API_BASE_URL` matching your active tunnel:

```env
API_BASE_URL=https://your-tunnel.ngrok-free.dev
QUICKBOOKS_REDIRECT_URI=${API_BASE_URL}/api/v1/integrations/quickbooks/callback
```

### 3. Verify the Tunnel

You can verify the tunnel is working by hitting the local API documentation over the public internet:

* **Browser:** `https://your-tunnel.ngrok-free.dev/docs`

* **cURL Webhook Test Command:**
```bash
curl -X POST https://your-tunnel.ngrok-free.dev/api/v1/webhooks/quickbooks \
     -H "Content-Type: application/json" \
     -d '{"event": "invoice.created", "customer": "test"}'
```

* **cURL Webhook Test Response:**
{"status":"received"}
