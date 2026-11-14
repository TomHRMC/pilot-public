> **📦 ARCHIVED 2026-08-20 — SUPERSEDED BY THE DOCKER WORKFLOW.** This Task #12-era (2026-03-19) runbook's central premise — "run Celery locally, not in Docker" and "the backend Dockerfile doesn't exist yet" — is contradicted by the current workflow: `pilot_celery_worker` + `pilot_celery_beat` run in Docker containers automatically. The living doc is `backend/README.md` §Celery ("Now in Docker!"), which absorbed the evergreen verification methods (`inspect registered`, log checks). Archived to `dev-docs/testing-support/archived/` per Tom's decision. **Frozen reference — do not update.**

---

# Celery Worker Testing Guide

**Task Reference:** Task #12 - Celery Setup & Configuration
**Created:** 2026-03-19
**Updated:** 2026-03-19 (Added Docker Compose troubleshooting)
**Purpose:** Step-by-step instructions for testing and verifying Celery worker functionality

## ⚠️ Important: How to Run Celery (Read This First)

### Recommended Approach: Run Locally

**The standard development workflow is to run Celery locally, not in Docker.**

Since you already have Redis running in Docker (`redis-1` container), you should run Celery workers in your local Python environment:

```bash
# Terminal 1 - Start Celery Worker
cd backend
source .venv/bin/activate
celery -A core.celery_app worker --loglevel=info

# Terminal 2 - Start Celery Beat (optional, for scheduled tasks)
cd backend
source .venv/bin/activate
celery -A core.celery_app beat --loglevel=info
```

**Why this works:**
- ✅ Redis is running in Docker (you already have this)
- ✅ Celery connects to Redis at `localhost:6379`
- ✅ Your Python environment has all dependencies installed
- ✅ This is the standard development workflow
- ✅ Faster iteration (no container rebuilds)

### Docker Compose Status

The `docker-compose.yml` includes `celery_worker` and `celery_beat` services, but they require a backend Dockerfile that doesn't exist yet. Creating the Dockerfile is a separate infrastructure task (typically done during AWS deployment setup, not part of Celery configuration).

**If you try to run:**
```bash
docker-compose up celery_worker celery_beat -d
```

**You'll get this error:**
```
failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
```

**Solution:** Run Celery locally as shown above. The docker-compose.yml is configured for future use when the backend Dockerfile is created.

---

## Quick Verification Summary

✅ **Your Result:** You successfully verified task autodiscovery!
**Expected Output:** 3 registered tasks
```
cleanup_expired_idempotency_keys
cleanup_old_failed_keys
tasks.test_task.add_numbers
```

This confirms the Celery configuration is working correctly.

---

## Testing Methods

### Method 1: List Registered Tasks (No Worker Needed)

**Purpose:** Verify task autodiscovery without starting a worker

**Command:**
```bash
cd backend
source .venv/bin/activate
python -c "from core.celery_app import celery_app; from tasks import test_task, cleanup_idempotency_keys; tasks = [t for t in celery_app.tasks.keys() if not t.startswith('celery.')]; print('\n'.join(sorted(tasks)))"
```

**Expected Output:**
```
cleanup_expired_idempotency_keys
cleanup_old_failed_keys
tasks.test_task.add_numbers
```

**What This Proves:**
- Celery app initializes correctly
- Task modules are importable
- Tasks are registered with correct names

---

### Method 2: Start Celery Worker Locally ⭐ RECOMMENDED

**Purpose:** Run a Celery worker to process tasks in real-time
**Status:** ✅ This is the standard development approach

**Prerequisites:**
1. Redis must be running (you likely already have `redis-1` container running)
2. Database connection configured in `.env`
3. Virtual environment activated

**Step-by-Step Instructions:**

#### Step 1: Verify Redis is Running
```bash
# Check if redis container is running
docker ps | grep redis

# Test Redis connection
redis-cli ping
# Expected output: PONG
```

**If Redis is NOT running, start it:**
```bash
# Option A: Using Docker Compose (recommended)
docker-compose up redis -d

# Option B: Using standalone Docker
docker run -d -p 6379:6379 --name redis-dev redis:alpine
```

#### Step 2: Start Celery Worker (MAIN PROCESS)
Open a new terminal and run:

```bash
cd backend
source .venv/bin/activate
celery -A core.celery_app worker --loglevel=info
```

**Expected Output:**
```
 -------------- celery@your-hostname v5.x.x
---- **** ----- 
--- * ***  * -- Darwin-23.x.x
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> app:         pilot_worker:0x...
- ** ---------- .> transport:   redis://localhost:6379/1
- ** ---------- .> results:     redis://localhost:6379/2
- *** --- * --- .> concurrency: 8 (prefork)
-- ******* ---- .> task events: OFF
--- ***** ----- 
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . cleanup_expired_idempotency_keys
  . cleanup_old_failed_keys
  . tasks.test_task.add_numbers

[2026-03-19 17:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/1
[2026-03-19 17:00:00,000: INFO/MainProcess] mingle: searching for neighbors
[2026-03-19 17:00:01,000: INFO/MainProcess] mingle: all alone
[2026-03-19 17:00:01,000: INFO/MainProcess] celery@your-hostname ready.
```

**What to Look For:**
- ✅ "celery@your-hostname ready" message
- ✅ All 3 tasks listed under `[tasks]`
- ✅ Connected to Redis broker
- ✅ No error messages

**To Stop Worker:**
Press `Ctrl+C` in the terminal

#### Step 3: Start Celery Worker in Background (Optional)

If you want Celery running in the background:

```bash
cd backend
source .venv/bin/activate

# Start worker in background
nohup celery -A core.celery_app worker --loglevel=info > celery_worker.log 2>&1 &

# View logs
tail -f celery_worker.log

# Stop background worker
pkill -f "celery.*worker"
```

---

### Method 3: Start Celery Beat Scheduler ⭐ RECOMMENDED

**Purpose:** Run the beat scheduler to trigger periodic tasks (cron jobs)
**Status:** ✅ This is the standard development approach

**Prerequisites:**
- Redis running (you already have this)
- Celery worker running (in separate terminal - see Method 2)

**Step-by-Step Instructions:**

#### Step 1: Start Beat Scheduler
Open a NEW terminal (keep worker terminal running) and run:

```bash
cd backend
source .venv/bin/activate
celery -A core.celery_app beat --loglevel=info
```

**Expected Output:**
```
celery beat v5.x.x is starting.
__    -    ... __   -        _
LocalTime -> 2026-03-19 17:00:00
Configuration ->
    . broker -> redis://localhost:6379/1
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler
    . db -> celerybeat-schedule
    . logfile -> [stderr]@%INFO
    . maxinterval -> 5.00 minutes (300s)

[2026-03-19 17:00:00,000: INFO/MainProcess] beat: Starting...
[2026-03-19 17:00:00,000: INFO/MainProcess] Scheduler: Sending due task cleanup-expired-idempotency-keys (cleanup_expired_idempotency_keys)
```

**What to Look For:**
- ✅ "beat: Starting..." message
- ✅ Scheduled tasks are listed
- ✅ No error messages
- ✅ Tasks are sent when they become due (based on cron schedule)

**To Stop Beat:**
Press `Ctrl+C` in the terminal

#### Step 2: Start Beat in Background (Optional)

```bash
cd backend
source .venv/bin/activate

# Start beat in background
nohup celery -A core.celery_app beat --loglevel=info > celery_beat.log 2>&1 &

# View logs
tail -f celery_beat.log

# Stop background beat
pkill -f "celery.*beat"
```

---

### Method 4: Inspect Running Workers

**Purpose:** Query active workers for their status and registered tasks

**Prerequisites:**
- Redis running
- At least one Celery worker running

**Step-by-Step Instructions:**

#### Step 1: List Active Workers
```bash
cd backend
source .venv/bin/activate
celery -A core.celery_app inspect active
```

**Expected Output:**
```json
{
    "celery@your-hostname": []
}
```
Empty list means no tasks currently executing (normal for idle worker).

#### Step 2: List Registered Tasks
```bash
celery -A core.celery_app inspect registered
```

**Expected Output:**
```json
{
    "celery@your-hostname": [
        "cleanup_expired_idempotency_keys",
        "cleanup_old_failed_keys",
        "tasks.test_task.add_numbers"
    ]
}
```

#### Step 3: Check Scheduled Tasks
```bash
celery -A core.celery_app inspect scheduled
```

**Expected Output:**
```json
{
    "celery@your-hostname": []
}
```
Empty if no tasks are scheduled to run in near future.

#### Step 4: Get Worker Stats
```bash
celery -A core.celery_app inspect stats
```

**Expected Output:**
```json
{
    "celery@your-hostname": {
        "broker": {
            "transport": "redis",
            "hostname": "localhost:6379"
        },
        "pool": {
            "max-concurrency": 8,
            "processes": [...]
        },
        "total": {
            "tasks.test_task.add_numbers": 0,
            "cleanup_expired_idempotency_keys": 0,
            "cleanup_old_failed_keys": 0
        }
    }
}
```

---

### Method 5: Test Health Monitoring Endpoint

**Purpose:** Verify the health endpoint returns worker status

**Prerequisites:**
- FastAPI app running (port 8000)
- At least one Celery worker running

**Step-by-Step Instructions:**

#### Step 1: Start the API Server
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

#### Step 2: Query Health Endpoint
```bash
curl http://localhost:8000/api/v1/health/celery
```

**Expected Output (Worker Running):**
```json
{
  "status": "healthy",
  "workers_active": 1,
  "broker_connected": true,
  "scheduled_tasks": 0,
  "timestamp": "2026-03-19T21:00:00.000000Z"
}
```

**Expected Output (No Workers):**
```json
{
  "detail": "No Celery workers available"
}
```
HTTP Status: 503 Service Unavailable

#### Step 3: Test with Browser
Open in browser: http://localhost:8000/api/v1/health/celery

---

### Method 6: Manually Execute a Test Task

**Purpose:** Trigger a task manually to verify end-to-end execution

**Prerequisites:**
- Redis running
- Celery worker running

**Step-by-Step Instructions:**

#### Step 1: Send Test Task to Queue
```bash
cd backend
source .venv/bin/activate
python -c "
from core.celery_app import celery_app
from tasks.test_task import add_numbers

# Queue the task (async)
result = add_numbers.apply_async(args=[5, 3])
print(f'Task ID: {result.id}')
print(f'Task sent to queue!')
print(f'Result (will wait 2 seconds): {result.get(timeout=10)}')
"
```

**Expected Output:**
```
Task ID: abc123-def456-...
Task sent to queue!
Result (will wait 2 seconds): 8
```

**What This Proves:**
- Task was queued successfully
- Worker picked up the task
- Task executed correctly (5 + 3 = 8)
- Result was stored and retrieved

#### Step 2: Check Worker Logs
In the worker terminal, you should see:
```
[2026-03-19 17:00:00,000: INFO/MainProcess] Task tasks.test_task.add_numbers[abc123-def456-...] received
[2026-03-19 17:00:02,000: INFO/ForkPoolWorker-1] Task tasks.test_task.add_numbers[abc123-def456-...] succeeded in 2.001s: 8
```

---

### Method 7: Run Automated Tests

**Purpose:** Run the comprehensive test suite to verify all functionality

**Step-by-Step Instructions:**

#### Step 1: Run All Tests
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

**Expected Output:**
```
======================= test session starts ========================
...
======================= 221 passed, 2 warnings in 3.88s ===========
```

#### Step 2: Run Only Celery Tests
```bash
pytest tests/test_celery.py -v
```

**Expected Output:**
```
tests/test_celery.py::TestCeleryConfiguration::test_celery_app_exists PASSED
tests/test_celery.py::TestCeleryConfiguration::test_broker_configuration PASSED
tests/test_celery.py::TestCeleryConfiguration::test_result_backend_configuration PASSED
...
======================= 24 passed in 0.07s =========================
```

#### Step 3: Run Tests with Coverage
```bash
pytest tests/test_celery.py -v --cov=core.celery_app --cov=tasks
```

---

### Method 8: Using Docker Compose (Full Stack)

**Purpose:** Run the complete stack (Redis + Worker + Beat) in containers

**Step-by-Step Instructions:**

#### Step 1: Start All Services
```bash
# From project root
docker-compose up redis celery_worker celery_beat
```

**Expected Output:**
```
redis_1         | Ready to accept connections
celery_worker_1 | [2026-03-19 17:00:00,000: INFO/MainProcess] celery@... ready.
celery_beat_1   | [2026-03-19 17:00:00,000: INFO/MainProcess] beat: Starting...
```

#### Step 2: View Logs for Specific Service
```bash
# Worker logs
docker-compose logs -f celery_worker

# Beat logs
docker-compose logs -f celery_beat

# Redis logs
docker-compose logs -f redis
```

#### Step 3: Stop Services
```bash
docker-compose down
```

#### Step 4: Restart a Specific Service
```bash
docker-compose restart celery_worker
```

---

## Troubleshooting

### Problem: "No nodes replied within time constraint"

**Cause:** No Celery workers are running

**Solution:**
1. Verify Redis is running: `redis-cli ping`
2. Start a worker: `celery -A core.celery_app worker --loglevel=info`
3. Try the inspect command again

---

### Problem: "ConnectionError: Error 61 connecting to localhost:6379"

**Cause:** Redis is not running

**Solution:**
```bash
# Start Redis via Docker
docker-compose up redis -d

# Or standalone
docker run -d -p 6379:6379 redis:alpine

# Verify it's running
redis-cli ping
```

---

### Problem: Tasks not executing

**Cause:** Worker is running but tasks aren't being processed

**Solution:**
1. Check worker logs for errors
2. Verify task name matches: `celery -A core.celery_app inspect registered`
3. Check broker connection: `redis-cli -h localhost -p 6379 ping`
4. Try sending a test task (Method 6 above)

---

### Problem: "ImportError: No module named 'tasks'"

**Cause:** Python path not set correctly or running from wrong directory

**Solution:**
```bash
# Always run from backend/ directory
cd backend
source .venv/bin/activate
celery -A core.celery_app worker --loglevel=info
```

---

## Summary of Commands

### Quick Reference

```bash
# 1. List registered tasks (no worker needed)
cd backend && source .venv/bin/activate
python -c "from core.celery_app import celery_app; from tasks import test_task, cleanup_idempotency_keys; tasks = [t for t in celery_app.tasks.keys() if not t.startswith('celery.')]; print('\n'.join(sorted(tasks)))"

# 2. Start Redis
docker-compose up redis -d

# 3. Start Celery worker
cd backend && source .venv/bin/activate
celery -A core.celery_app worker --loglevel=info

# 4. Start Celery Beat (separate terminal)
cd backend && source .venv/bin/activate
celery -A core.celery_app beat --loglevel=info

# 5. Check health endpoint (API must be running)
curl http://localhost:8000/api/v1/health/celery

# 6. Run tests
cd backend && source .venv/bin/activate
pytest tests/test_celery.py -v

# 7. Inspect running workers
celery -A core.celery_app inspect registered
celery -A core.celery_app inspect active
celery -A core.celery_app inspect stats
```

---

## Next Steps

Now that Celery is configured and verified, you can:

1. **Build Task #13:** Profitability Rollup Worker
2. **Build Task #14:** Notification Outbox Worker
3. **Build Task #15:** Session Expiration Job

All of these tasks will use this Celery infrastructure for background processing.
