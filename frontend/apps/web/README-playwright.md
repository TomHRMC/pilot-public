# Pilot for Trades - Playwright E2E Testing Guide

This document explains the End-to-End (E2E) testing architecture for the Pilot for Trades web application. It outlines how Playwright is configured to hit the **real** FastAPI backend and PostgreSQL database, bypassing frontend mocks to validate true system behavior.

---

## 1. Playwright Setup & Key Files

Historically, the frontend was developed against Mock Service Worker (MSW) and a mock Cognito authentication provider. To run true E2E tests, we have introduced a secondary configuration that disables these mocks and interacts directly with the live backend.

### Key Files in `apps/web/`

- **`playwright.config-nomock.ts`**
  - **Purpose:** The execution configuration for real E2E tests.
  - **Key Changes:** Injects `NEXT_PUBLIC_USE_MOCK_AUTH=false` and `NEXT_PUBLIC_USE_MSW_MOCKS=false` into the web server startup command. It also registers the global setup and teardown scripts.
- **`e2e/globalSetup.ts`**
  - **Purpose:** Runs _once_ before the entire test suite starts.
  - **Behavior:** Pings the backend health endpoint (`/api/v1/health/celery`). It then uses the `/api/v1/auth/signup/test` endpoint to automatically provision the baseline test tenant (`00000000-0000-0000-0000-000000000001`) and owner.
- **`e2e/globalTeardown.ts`**
  - **Purpose:** Runs _once_ after the test suite finishes.
  - **Behavior:** Cleans up generated test data (e.g., fetching test customers and soft-deleting them via `/test` endpoints). This prevents "junk data" accumulation, which previously caused page-overflow test fragility in the backend.
- **`e2e/playwright.author.example.ts`**
  - **Purpose:** A reference template for authoring new tests.
  - **Behavior:** Demonstrates how to use Playwright's `request` fixture to hit backend `/test` endpoints (e.g., seeding a customer instantly) _before_ executing the UI interactions via the `page` fixture.

---

## 2. Setting Up the E2E Database Environment

Running E2E tests against your development database will pollute your local state. You must provision a dedicated E2E database.

### Step 2.1: Create the E2E Database

Connect to your local Postgres instance and create a fresh database:

```sql
CREATE DATABASE pilot_e2e_db;
```

### Step 2.2: Configure the Backend Environment

Create a `.env.e2e` file in your `backend/` directory. This ensures the backend connects to the test database and exposes the 128 `/test` endpoints needed for setup/teardown.

```env
# backend/.env.e2e
ENVIRONMENT=qa
TEST_ENDPOINT_ENABLED=true

# Connect to the dedicated E2E DB
DATABASE_URL=postgresql://user:password@localhost:5432/pilot_e2e_db

# Use Mocks for External Services so tests don't incur charges or send real texts
SMS_CARRIER=mock
STRIPE_WEBHOOK_SECRET=whsec_test_...

```

### Step 2.3: Run Database Migrations

Before running tests, apply your Alembic migrations to the new E2E database to build the schema:

```bash
cd backend
source .venv/bin/activate
# Override the database URL temporarily for Alembic
ALEMBIC_DATABASE_URL=postgresql://user:password@localhost:5432/pilot_e2e_db alembic upgrade head

```

_Note: If you have seed data in `migrations/seed_test_data.py`, ensure it runs against this database as well._

---

## 3. How to Run the E2E Tests

### Step 3.1: Start the Backend

Start your FastAPI server and Celery worker using the E2E environment configuration.

```bash
cd backend
source .venv/bin/activate
set -a; source .env.e2e; set +a
uvicorn app.main:app --reload --port 8000

```

_(Optionally, start Celery in a separate terminal using the same `.env.e2e` file)._

### Step 3.2: Execute Playwright

Run Playwright from the frontend web directory, explicitly passing the "no-mock" configuration file. Playwright will handle starting the Next.js frontend with mocks disabled.

```bash
cd frontend/apps/web

# Run the test suite headlessly
npx playwright test --config=playwright.config-nomock.ts

# Or run with the UI mode to debug and visually watch the tests run
npx playwright test --config=playwright.config-nomock.ts --ui

```

---

## 4. Best Practices for Authoring Tests

When you write new tests (referencing `playwright.author.example.ts`), keep the following rules in mind:

1. **Arrange with APIs, Act with UI:** Do not use the UI to set up test state. If you are testing the "Quote Approval" flow, do not make Playwright click through the "Create Customer" and "Create Quote" forms. Instead, use `await request.post('/api/v1/quotes/test', ...)` to seed the quote, then use `page.goto()` to load the UI and test the approval action.
2. **Rely on the Test Context:** The 128 endpoints in your backend that end in `/test` automatically map to the test tenant (`00000000-0000-0000-0000-000000000001`). You do not need to pass JWTs to these endpoints; they are designed specifically for fast E2E state orchestration.
3. **Clean Up After Yourself:** If a test generates highly specific data that might break a subsequent test, use an `test.afterEach` block to delete it via the API, rather than relying entirely on `globalTeardown.ts`.
4. **Wait for Network, Not Time:** Never use `page.waitForTimeout(5000)`. Always wait for API responses or UI state changes. For example: `await expect(page.locator('text=Approved')).toBeVisible();` or `await page.waitForResponse('/api/v1/quotes/*/approve');`.

I've generated the `README-playwright.md` file detailing your E2E testing strategy, highlighting the shift from MSW/MockAuth to the real FastAPI backend, database provisioning, environment configurations (`.env.e2e`), and how to correctly use the 128 `/test` endpoints for data seeding without accumulating state debt.
