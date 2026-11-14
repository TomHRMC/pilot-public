# Pilot for Trades - Maestro E2E Testing Guide (Mobile)

This document explains the End-to-End (E2E) testing architecture for the Pilot for Trades mobile application (Expo/React Native) using **Maestro**.

Unlike Playwright, which runs in a Node.js environment with global setup/teardown hooks, Maestro operates directly against your compiled mobile app binary (iOS Simulator / Android Emulator). To seed and tear down data against the 128 `/test` endpoints, Maestro uses its native `runScript` command to execute HTTP requests via a built-in JavaScript client.

---

## 1. Maestro Setup & Key Files

Your mobile E2E tests live in `apps/mobile/e2e/`. We divide this directory into two concepts: **Flows** (the YAML files that Maestro executes) and **Scripts** (the JavaScript files that interact with your backend `/test` endpoints).

### Directory Structure

```text
apps/mobile/e2e/
├── flows/
│   └── batch_fe_b5/
│       └── tech-quote-approval.flow.yaml   # The Maestro UI instructions
└── scripts/
├── seed_customer.js                    # API script to create a customer
├── seed_quote.js                       # API script to create a quote
└── teardown_tenant.js                  # API script to wipe test data

```

### The API Seeding Script (`scripts/seed_quote.js`)

Maestro provides a global `http` object to make REST calls. We use this to hit your `/test` endpoints before the UI automation starts.

```javascript
// apps/mobile/e2e/scripts/seed_quote.js
// Maestro's built-in HTTP client doesn't need external imports

// 1. Create a baseline customer in the test tenant
const customerRes = http.post("http://localhost:8000/api/v1/customers/test", {
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    display_name: "E2E Mobile Customer",
    type: "person",
  }),
});

const customer = json(customerRes.body);

// 2. Create a pending quote for that customer
const quoteRes = http.post("http://localhost:8000/api/v1/quotes/test", {
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    customer_id: customer.id,
    site_id: "00000000-0000-0000-0000-000000000000", // Update to a valid test site ID
    currency: "USD",
  }),
});

const quote = json(quoteRes.body);

// 3. Export data to the Maestro YAML flow
output.quoteId = quote.id;
output.quoteTotal = "0.00"; // Based on whatever lines you seeded
```

### The Maestro Flow (`flows/batch_fe_b5/tech-quote-approval.flow.yaml`)

The YAML file references the script, launches the app, and interacts with the UI.

```yaml
appId: com.pilotfortrades.app
---
# 1. API Setup: Seed the database
- runScript: ../../scripts/seed_quote.js

# 2. Launch the Expo app (state is cleared to ensure a fresh session)
- launchApp:
    clearState: true

# 3. UI Interactions: Log in as the test tech
- tapOn: "Email"
- inputText: "tech@test-tenant.com"
- tapOn: "Password"
- inputText: "TestPassword123!"
- tapOn: "Sign In"

# 4. Navigate and assert the seeded data exists
- tapOn: "Quotes"
- tapOn: "Pending"
- assertVisible: "E2E Mobile Customer"

# 5. API Teardown: Clean up
- runScript: ../../scripts/teardown_tenant.js
```

---

## 2. Setting Up the Mobile E2E Environment

To run these tests, you must compile your Expo app _without_ the development mocks, pointing it at your E2E FastAPI database.

### Step 2.1: Configure Mobile Environment Variables

Create or update `apps/mobile/.env.e2e`:

```env
# Disable Mocks so the app talks to the real backend
EXPO_PUBLIC_USE_MSW_MOCKS=false
EXPO_PUBLIC_USE_MOCK_AUTH=false

# Point to your local E2E backend (Ensure your backend is running with .env.e2e!)
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_WS_URL=ws://localhost:8000

```

### Step 2.2: Build the Expo App for the Simulator

Maestro interacts with the compiled app binary. You need to build a development build for your iOS Simulator or Android Emulator.

```bash
cd apps/mobile

# Load the E2E environment variables
set -a; source .env.e2e; set +a

# Build and install on iOS Simulator
npx expo run:ios

# OR Build and install on Android Emulator
npx expo run:android

```

---

## 3. Running the Maestro Tests

Once your backend is running (`uvicorn app.main:app --port 8000` using the `pilot_e2e_db` database) and your mobile app is installed on the simulator:

### Run the full suite:

```bash
# Ensure you have Maestro installed: curl -Ls "[https://get.maestro.mobile.dev](https://get.maestro.mobile.dev)" | bash
cd apps/mobile
maestro test e2e/flows/

```

### Run a single test visually:

```bash
cd apps/mobile
maestro test e2e/flows/batch_fe_b5/tech-quote-approval.flow.yaml

```

### Use Maestro Studio (Highly Recommended)

Maestro Studio is an interactive UI that allows you to point and click your way through the simulator to generate the YAML commands instantly.

```bash
maestro studio

```

---

## 4. Best Practices for Mobile Authoring

1. **TestIDs over Text:** While `tapOn: "Sign In"` works, designs change. Use `- tapOn:\n    id: "submit-login-btn"` utilizing the `testID` props your React Engineer agent applied to the Gluestack UI components.
2. **State Management:** Always use `clearState: true` under `launchApp` in your YAML to ensure AsyncStorage (like JWT tokens and Field Mode toggles) is wiped between runs.
3. **Teardown is Mandatory:** Just like Playwright, if you do not run a teardown script at the end of your YAML file (e.g., calling `DELETE /api/v1/quotes/{quote_id}/test`), your `pilot_e2e_db` will accumulate audit logs and break future pagination/conflict tests.

### Why Maestro is Different (and Better for Mobile)
Maestro approaches E2E slightly differently than Playwright:
1. **No Global Setup File:** Instead of a `globalSetup.ts` file, you use Maestro's `- runScript:` YAML command at the beginning of each test flow to execute a `.js` file.
2. **Built-in HTTP Client:** Maestro's JavaScript runtime comes with a global `http` object. This allows your `.js` scripts to easily hit your backend's 128 `/test` endpoints directly to seed customers, quotes, or jobs before the app even launches on the simulator.
3. **Data Passing:** The JS script assigns data to an `output` object (e.g., `output.quoteId = quote.id;`). Your YAML file can then use that variable (e.g., `- assertVisible: ${output.quoteId}`) later in the test!

### The Database Constraint remains
Just like Playwright, **you must ensure the backend is running with `.env.e2e` pointing to your `pilot_e2e_db` PostgreSQL instance.** If you run Maestro tests against your daily development database, it will permanently alter your local data.
