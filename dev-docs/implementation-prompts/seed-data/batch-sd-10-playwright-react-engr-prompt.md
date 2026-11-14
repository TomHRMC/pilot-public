# Implementation Prompt: SD-10 Tier 2 — Playwright Web E2E (5 Critical Paths)

**Mode**: Pilot React Engineer  
**Batch**: SD-10 Tier 2  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §E2E Test Harness  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md` §SD-10  
**Scenario catalog**: `dev-docs/testing-support/scenario-coverage-catalog.md` — read this fully before writing any test  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`) — Playwright browser tests against the live web app  
**Backend companion**: SD-10 Tier 1 (Python Engineer) must be complete — `pilot_e2e_db` must be seeded and the nightly CI workflow must be passing before this batch starts

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/testing-support/scenario-coverage-catalog.md`** — every section (Parts 1–5): this is the authoritative source for what each Playwright spec must assert
- **`dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md`** — §SD-10 Part B (harness architecture decisions)

**Critical rules for this batch:**

- **Rule — Real backend, no MSW**: These are Playwright E2E tests running against the live `pilot_e2e_db`. Do NOT use MSW handlers — all API calls go to the real FastAPI backend. `NEXT_PUBLIC_USE_MOCK_AUTH` must be `false` for Playwright.
- **Rule — Specific value assertions**: Every test MUST assert on specific business values, not just page load or HTTP 200. See scenario catalog Part 2 for the exact assertions per scenario.
- **Rule — E2E DB isolation**: Tests run against `pilot_e2e_db` (port 5433) — never against the dev DB. The `seed_e2e_db.py` script seeds it once before the suite. Do not add `beforeEach` DB resets inside individual tests.
- **Rule 1.1**: Before writing any navigation step, verify the exact route URL in `apps/web/src/app/(authed)/` directory structure.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done.
- **Rule — Flaky test policy**: A test that relies on timing (`waitForTimeout`) is not acceptable. Use `waitForSelector`, `waitForResponse`, or `expect(locator).toBeVisible()` with explicit timeouts. Never use `page.waitForTimeout(N)`.

---

## Design Decisions (Do Not Re-Litigate)

From `batch-sd-design-sprint-design.md` §SD-10 — these decisions are final:

| Decision | Outcome | Rationale |
|:---|:---|:---|
| Playwright runs against real backend | Yes — `pilot_e2e_db` | MSW cannot validate actual API contract compliance |
| `NEXT_PUBLIC_USE_MOCK_AUTH` | `false` for Playwright | Real auth flow must be exercised |
| Authentication in tests | Use Playwright's `storageState` to save authenticated sessions | Avoids re-logging in on every test |
| Test isolation | `pilot_e2e_db` is seeded once before the suite, not reset per test | Resets per test are too slow for Playwright |
| Flakiness policy | Max 2 failures in 5 runs → quarantine + file P2 bug | Zero tolerance for flaky CI gate |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Verify E2E Stack Is Running

Before writing any Playwright test, confirm the E2E environment is running:

```bash
# Start E2E services if not already running
docker-compose -f <repo>/docker-compose.e2e.yml up -d

# Verify E2E DB is seeded
DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db \
SMS_CARRIER=mock \
ENVIRONMENT=e2e \
cd <repo>/backend && python tests/e2e/seed_e2e_db.py

# Start the Next.js web app pointing at E2E backend
NEXT_PUBLIC_API_URL=http://localhost:8001 pnpm --filter web dev
```

Verified endpoints for this batch (all confirmed present in Tier 1 and `openapi_schema_map.md`):

| Flow | Key Endpoints Used |
|:---|:---|
| Auth | Auth via Cognito mock / test token |
| Quote-to-Cash | `POST /api/v1/quotes`, `GET /api/v1/invoices/{id}`, `POST /api/v1/payments` |
| Dispatch | `POST /api/v1/jobs`, `PATCH /api/v1/jobs/{id}`, `POST /api/v1/jobs/{id}/time-entries` |
| SMS Thread | `GET /api/v1/comms/threads`, `POST /api/v1/comms/send` |
| Dunning | `GET /api/v1/invoices?overdue=true` |

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/app/(authed)/                          ← understand route structure before writing navigation
frontend/apps/web/src/app/(authed)/quotes/page.tsx           ← quote builder entry point
frontend/apps/web/src/app/(authed)/invoices/page.tsx         ← invoices list + overdue filter
frontend/apps/web/src/app/(authed)/jobs/page.tsx             ← jobs list
frontend/apps/web/src/app/(authed)/comms/page.tsx            ← customer communications inbox
frontend/apps/web/playwright.config.ts                       ← current Playwright config (baseURL, browser, timeouts)
```

Also check what Playwright infrastructure already exists:
```bash
find frontend/apps/web -name "*.playwright.ts" -o -name "*.e2e.ts" | head -20
find frontend/apps/web -name "playwright.config.ts" | head -5
ls frontend/apps/web/src/__tests__/  # check for existing e2e folder
```

---

## Context: What This Batch Does

This batch adds 5 Playwright browser E2E tests to `apps/web` — one per critical path defined in the scenario coverage catalog. Each test:
1. Navigates to the correct web page in a real browser
2. Performs the user actions (click, fill, submit)
3. Asserts on specific visible UI content — not just "page loaded" but "invoice total shows $150.00", "SMS unread badge shows 1"

These tests run in the **nightly GitHub Actions E2E workflow** (already set up in `.github/workflows/e2e-nightly.yml` by the Python Engineer). They do NOT run on every PR.

**Test file locations**:
```
frontend/apps/web/src/__tests__/e2e/
├── cp1_auth_rbac.playwright.ts
├── cp2_quote_to_cash.playwright.ts
├── cp3_dispatch_field_sync.playwright.ts
├── cp4_customer_sms.playwright.ts
└── cp5_dunning_cycle.playwright.ts
```

---

## STEP 1 — Configure `playwright.config.ts` for E2E Mode

Read `frontend/apps/web/playwright.config.ts` before editing.

Add or update the config to support E2E mode (separate from the existing MSW-based unit tests):

```typescript
// playwright.config.ts — E2E profile additions
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./src/__tests__/e2e",
  testMatch: "**/*.playwright.ts",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    // No mock auth — real backend
    storageState: "playwright-auth.json",  // pre-authenticated session
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Global setup seeds auth state
  globalSetup: "./src/__tests__/e2e/global-setup.ts",
  timeout: 30000,
  retries: process.env.CI ? 2 : 0,
});
```

---

## STEP 2 — Global Setup: Pre-Authenticated Session

Create `frontend/apps/web/src/__tests__/e2e/global-setup.ts`:

```typescript
import { chromium, FullConfig } from "@playwright/test";

async function globalSetup(config: FullConfig) {
  const { baseURL } = config.projects[0].use;
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Navigate to login and authenticate as the owner user
  // Adjust to match the actual login flow in the web app
  await page.goto(`${baseURL}/login`);

  // Fill in the test credentials
  // dev@pilot.local is the owner user — seeded by seed_e2e_db.py
  await page.fill('[name="email"]', "dev@pilot.local");
  await page.fill('[name="password"]', process.env.E2E_TEST_PASSWORD ?? "TestPassword123!");
  await page.click('[type="submit"]');

  // Wait for dashboard to confirm successful login
  await page.waitForURL("**/dashboard", { timeout: 10000 });

  // Save the authenticated browser state
  await page.context().storageState({ path: "playwright-auth.json" });
  await browser.close();
}

export default globalSetup;
```

> **Important**: Read the actual login page implementation before writing the login selectors. The field names (`[name="email"]`) may differ. Use `page.locator('[data-testid="email-input"]')` if `data-testid` attributes are present. Verify the post-login redirect URL matches the actual app behavior.

---

## STEP 3 — CP-1: Auth + Tenant Isolation

File: `frontend/apps/web/src/__tests__/e2e/cp1_auth_rbac.playwright.ts`

```typescript
import { test, expect } from "@playwright/test";

// Uses storageState from global setup (owner session)

test.describe("CP-1: Auth + Tenant Isolation", () => {
  test("owner can access dashboard and sees BI data", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).not.toHaveURL(/login/);
    // Assert dashboard has actual content — not just a loading spinner
    // Read the dashboard page to find the correct data-testid or text content
    await expect(page.locator("h1, h2")).toContainText(/Dashboard|Overview/i);
  });

  test("invoice list shows only tenant-scoped invoices", async ({ page }) => {
    await page.goto("/invoices");
    // Assert no invoices from other tenants leak through
    // The E2E tenant's invoices should be the only ones visible
    await expect(page.locator('[data-testid="invoices-table"], [data-testid="empty-state"]')).toBeVisible();
  });
});
```

> **Read `apps/web/src/app/(authed)/dashboard/page.tsx` and `apps/web/src/app/(authed)/invoices/page.tsx` before writing selectors.**

---

## STEP 4 — CP-2: Quote-to-Cash

File: `frontend/apps/web/src/__tests__/e2e/cp2_quote_to_cash.playwright.ts`

This is the highest-value test. It exercises the full core product loop through the UI.

```typescript
import { test, expect } from "@playwright/test";

test.describe("CP-2: Quote-to-Cash", () => {
  test("create quote → send → customer accepts → invoice paid", async ({ page }) => {
    // Step 1: Navigate to quotes and create a new quote
    await page.goto("/quotes/new");
    // Fill in customer, line item (Standard Outlet Install, qty 1, $150)
    // [Read the quote builder component before writing these steps]

    // Step 2: Send the quote
    // Click "Send Quote" button, confirm the modal/dialog

    // Step 3: Verify status is "Sent"
    await expect(page.locator('[data-testid="quote-status"]')).toContainText(/Sent/i);

    // Step 4: Simulate customer acceptance via the public link
    // The quote builder shows the public link — navigate to it in a new page context
    // const publicLink = await page.locator('[data-testid="quote-public-link"]').textContent();
    // await page.goto(publicLink!);
    // await page.click('[data-testid="accept-quote-btn"]');

    // Step 5: Return to invoices and find the created invoice
    await page.goto("/invoices");
    // Assert the invoice appears with correct total
    await expect(page.locator('[data-testid="invoice-total"]').first()).toContainText("$150");

    // Step 6: Record payment and assert invoice is paid
    // [Read the invoice detail page and payment modal components]
    // await page.click('[data-testid="record-payment-btn"]');
    // ... fill in payment details ...
    // await expect(page.locator('[data-testid="invoice-status"]')).toContainText(/Paid/i);
  });
});
```

> **This test is the most complex. Read these files before writing it:**
> - `apps/web/src/features/quotes/components/QuoteBuilder.tsx` (or equivalent)
> - `apps/web/src/features/invoices/components/InvoiceDetail.tsx`
> - `apps/web/src/features/public-quote/PublicQuotePage.tsx`
> 
> The comments above are a structure guide — replace with actual selectors found in those files.

---

## STEP 5 — CP-3: Dispatch + Field Sync

File: `frontend/apps/web/src/__tests__/e2e/cp3_dispatch_field_sync.playwright.ts`

```typescript
import { test, expect } from "@playwright/test";

test.describe("CP-3: Dispatch + Field Sync", () => {
  test("create job → assign tech → log time entry → mark complete", async ({ page }) => {
    // Navigate to jobs list and create a new job
    await page.goto("/jobs/new");
    // [Read jobs create page before writing selectors]

    // Assign tech user (tech@pilot.local)
    // Log a 2-hour time entry at master rate

    // Verify time entry cost ($240 = 2h × $120/hr)
    await expect(page.locator('[data-testid="time-entry-cost"]').first()).toContainText("$240");

    // Mark job complete
    // Assert job status shows "Completed"
    await expect(page.locator('[data-testid="job-status"]')).toContainText(/Completed/i);
  });
});
```

---

## STEP 6 — CP-4: Customer SMS Thread

File: `frontend/apps/web/src/__tests__/e2e/cp4_customer_sms.playwright.ts`

```typescript
import { test, expect } from "@playwright/test";

test.describe("CP-4: Customer SMS Thread", () => {
  test("SMS thread shows unread badge after inbound reply", async ({ page }) => {
    // Navigate to comms inbox
    await page.goto("/comms");

    // The E2E DB has 2 unread messages (seeded by seed_scenario_customer_comms.py)
    // Assert the unread badge is visible
    await expect(page.locator('[data-testid="unread-badge"], [aria-label*="unread"]')).toBeVisible();

    // Open the first thread with unread messages
    // Assert the message count is correct
    // [Read comms/page.tsx before writing thread selectors]
  });
});
```

---

## STEP 7 — CP-5: Dunning Cycle (Overdue Invoice Filter)

File: `frontend/apps/web/src/__tests__/e2e/cp5_dunning_cycle.playwright.ts`

```typescript
import { test, expect } from "@playwright/test";

test.describe("CP-5: Dunning / Overdue Invoice", () => {
  test("overdue filter returns invoices past due date", async ({ page }) => {
    await page.goto("/invoices");

    // The E2E DB should have at least 1 overdue invoice
    // Click the overdue toggle (or "Show overdue only" filter — read InvoicesPage.tsx)
    // [SD-FE-1 added this toggle — read the implemented component]

    // After filtering, assert at least 1 invoice is visible with an overdue indicator
    await expect(page.locator('[data-testid="invoice-overdue-badge"], [data-testid="invoices-table"] tr').first()).toBeVisible();
  });
});
```

---

## STEP 8 — Update `e2e-nightly.yml` to Run Playwright

The nightly GitHub Actions workflow was created by the Python Engineer in SD-10 Tier 1. Update it to also run the Playwright tests after the pytest E2E tests:

```yaml
# Add to .github/workflows/e2e-nightly.yml AFTER the pytest step:

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm install -g pnpm && pnpm install

      - name: Install Playwright browsers
        working-directory: frontend/apps/web
        run: pnpm dlx playwright install --with-deps chromium

      - name: Start web app (E2E mode)
        working-directory: frontend/apps/web
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8001
          NEXT_PUBLIC_USE_MOCK_AUTH: "false"
        run: pnpm build && pnpm start &
        # Wait for app to be ready
      
      - name: Wait for web app
        run: npx wait-on http://localhost:3000 --timeout 60000

      - name: Run Playwright E2E tests
        working-directory: frontend/apps/web
        env:
          PLAYWRIGHT_BASE_URL: http://localhost:3000
          E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}
        run: pnpm dlx playwright test src/__tests__/e2e/ 2>&1 | tee playwright-results.txt

      - name: Upload Playwright results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-results
          path: |
            frontend/apps/web/playwright-results.txt
            frontend/apps/web/test-results/
```

> Add `E2E_TEST_PASSWORD` to GitHub Actions secrets via Settings → Secrets. The value is the password for `dev@pilot.local` in the E2E environment.

---

## Test Requirements

### Assertion quality rule (MANDATORY)

Every Playwright test must assert on **specific visible content**, not just page load:

- ✅ `await expect(page.locator('[data-testid="invoice-total"]')).toContainText("$150")`
- ✅ `await expect(page.locator('[data-testid="job-status"]')).toContainText(/Completed/i)`
- ❌ `await expect(page).not.toHaveURL(/login/)` ← not sufficient on its own

### Anti-flakiness rules (MANDATORY)

- ❌ `await page.waitForTimeout(2000)` — BANNED. Use explicit selectors.
- ✅ `await page.waitForSelector('[data-testid="invoice-paid"]')` — explicit wait
- ✅ `await expect(locator).toBeVisible({ timeout: 10000 })` — explicit timeout

### Test file placement

All Playwright tests go in `frontend/apps/web/src/__tests__/e2e/` with `.playwright.ts` extension. They are NOT co-located with source components.

---

## Final Verification

### Phase 1 — Unit tests still pass (confirm no regressions)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

### Phase 2 — Playwright tests pass (run against live E2E stack)

Ensure `docker-compose.e2e.yml` is running and `pilot_e2e_db` is seeded:

```bash
cd <repo>/frontend/apps/web

# Run all 5 E2E specs
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
E2E_TEST_PASSWORD=TestPassword123! \
pnpm dlx playwright test src/__tests__/e2e/ --reporter=list 2>&1 | tail -20

echo "=== SD-10 PLAYWRIGHT TIER 2 FINAL VERIFICATION COMPLETE ==="
```

> **Any Playwright failure must be fixed before the batch is declared done.** If a test is intermittently failing (passes 3/5 runs), it must be stabilized before declaring done — not just "it passed once."

---

## Definition of Done — SD-10 Tier 2

Update `dev-docs/analysis/pilot-launch-plan.md` §E2E Test Harness when each item is done:

- [ ] Regression baseline captured (web unit tests pass)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] `docker-compose.e2e.yml` confirmed running with seeded `pilot_e2e_db`
- [ ] `playwright.config.ts` updated for E2E mode (`testDir = e2e/`, `storageState`, `NEXT_PUBLIC_USE_MOCK_AUTH=false`)
- [ ] `global-setup.ts` created — authenticates as `dev@pilot.local`, saves `playwright-auth.json`
- [ ] `cp1_auth_rbac.playwright.ts` — owner dashboard + tenant isolation assertions ✅
- [ ] `cp2_quote_to_cash.playwright.ts` — quote total = $150, invoice status = Paid ✅
- [ ] `cp3_dispatch_field_sync.playwright.ts` — time entry cost = $240, job status = Completed ✅
- [ ] `cp4_customer_sms.playwright.ts` — unread badge visible after inbound reply ✅
- [ ] `cp5_dunning_cycle.playwright.ts` — overdue filter returns overdue invoices ✅
- [ ] `.github/workflows/e2e-nightly.yml` updated with Playwright step
- [ ] `E2E_TEST_PASSWORD` secret added to GitHub Actions
- [ ] No `waitForTimeout()` calls in any test — all waits use explicit selectors or `expect(locator).toBeVisible()`
- [ ] All 5 Playwright tests pass consistently (run 3 times, all pass)
- [ ] Web unit tests still pass — zero regressions (`pnpm --filter web test`)
- [ ] **Phase 2 FULL verification command passes** (`=== SD-10 PLAYWRIGHT TIER 2 FINAL VERIFICATION COMPLETE ===`)
- [ ] `dev-docs/testing-support/scenario-coverage-catalog.md` Tier 2 column updated to ✅ for all 5 CPs
- [ ] Completion Summary added

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §E2E Test Harness:

```markdown
### SD-10 Tier 2 — Playwright Web E2E (5 Critical Paths): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web unit) | 0 Playwright tests existing
**Final**: X passed (web unit, no regressions) | 5 Playwright E2E tests passing

#### What Was Accomplished
- [Brief description]

#### Files Changed / Created
| File | Action |
|---|---|
| `frontend/apps/web/playwright.config.ts` | Updated — E2E profile, storageState, testDir |
| `frontend/apps/web/src/__tests__/e2e/global-setup.ts` | Created — pre-auth session |
| `frontend/apps/web/src/__tests__/e2e/cp1_auth_rbac.playwright.ts` | Created |
| `frontend/apps/web/src/__tests__/e2e/cp2_quote_to_cash.playwright.ts` | Created |
| `frontend/apps/web/src/__tests__/e2e/cp3_dispatch_field_sync.playwright.ts` | Created |
| `frontend/apps/web/src/__tests__/e2e/cp4_customer_sms.playwright.ts` | Created |
| `frontend/apps/web/src/__tests__/e2e/cp5_dunning_cycle.playwright.ts` | Created |
| `.github/workflows/e2e-nightly.yml` | Updated — Playwright step added |
| `dev-docs/testing-support/scenario-coverage-catalog.md` | Updated — Tier 2 ✅ markers |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `e2e/cp1_auth_rbac.playwright.ts` | Playwright E2E | N | ✅ |
| `e2e/cp2_quote_to_cash.playwright.ts` | Playwright E2E | N | ✅ |
| `e2e/cp3_dispatch_field_sync.playwright.ts` | Playwright E2E | N | ✅ |
| `e2e/cp4_customer_sms.playwright.ts` | Playwright E2E | N | ✅ |
| `e2e/cp5_dunning_cycle.playwright.ts` | Playwright E2E | N | ✅ |
```

---

## After This Task — README Completeness

After this batch closes, `README-seed-data.md` §10 is complete for all tasks **except SD-07 and SD-08** (SD-BE-2 — product feature revision + email template copy update). SD-BE-2 must still close for the full seed data roadmap to be done.

Tier 3 (Maestro mobile E2E) is a separate future batch and is not required for the seed data README to close.
