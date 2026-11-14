# QuickBooks Integration End-to-End Testing Guide
## Tasks 16-19: OAuth, Sync, Conflicts, and Webhooks

**Task Coverage:**
- Task 16: QuickBooks OAuth 2.0 Flow
- Task 17: Sync Mapping & Upsert Logic (Customer Sync)
- Task 18: Conflict Detection & Resolution
- Task 19: Webhook Handler

**Created:** 2026-03-24  
**Environment:** Sandbox (Development)  
**Purpose:** Complete end-to-end manual testing of QuickBooks integration in a single flow

---

## 📌 AI Agent Instructions

**For AI Assistants Walking Users Through Testing:**

This document is designed for an AI agent to guide a user through complete QuickBooks integration testing. When a user asks you to run tests using this document:

### 1. Test Run Documentation Protocol

**For EACH test run**, create a new test results document:
- **Filename Format:** `task-16-19-test-run-##.md` (auto-increment ##: 01, 02, 03, etc.)
- **Location:** Same directory as this document (`dev-docs/testing-support/`)
- **Purpose:** Track each test execution with detailed results

**Test Run Document Template:**
```markdown
# QB Integration Test Run ##
**Date:** YYYY-MM-DD HH:MM  
**Tester:** [Username]  
**Environment:** Sandbox  
**QuickBooks Realm ID:** [realm_id]

## Test Execution Log

### Step # (Task ##): [Step Name]
**Status:** ✅ PASS | ❌ FAIL | ⏭️ SKIPPED  
**Timestamp:** [when executed]  
**Expected:** [what should happen]  
**Actual:** [what happened]  
**Notes:** [observations, issues, etc.]

---

[Repeat for each step]

---

## Test Summary

**Total Steps:** [X]  
**Passed:** [X]  
**Failed:** [X]  
**Skipped:** [X]  
**Overall Status:** ✅ PASS | ❌ FAIL | ⚠️ PARTIAL

## Issues Found

1. **[Issue Description]**
   - Severity: LOW | MEDIUM | HIGH | CRITICAL
   - Step: [step number]
   - Details: [description]
   - Resolution: [if resolved during test]

## Performance Metrics

- OAuth Flow: [X] seconds
- Initial Customer Sync: [X] seconds
- Conflict Detection: [X] seconds
- Webhook Processing: [X] seconds

## Recommendations

[Any suggestions for improvements or next steps]
```

### 2. Testing Flow Protocol

**Walk the user through ONE step at a time:**
1. Present the step number, task reference, and instruction
2. Provide the exact command(s) or action(s) to execute
3. Show the expected output or result
4. Wait for user confirmation before proceeding
5. Document the result in the test run file
6. Move to the next step

**Example interaction:**
```
Agent: "Let's proceed with Step 1 (Task 16): Initiate OAuth Connection

Please open your browser and navigate to:
http://localhost:8000/api/v1/integrations/quickbooks/connect/test

You should be automatically redirected to QuickBooks authorization page.

Expected: Redirect to QuickBooks with your sandbox company listed.

Let me know what happens, or type 'done' when you've completed the authorization."
```

### 3. Error Handling Protocol

**If a step fails:**
1. Document the failure in the test run file
2. Ask the user for error messages or unexpected behavior
3. Check common troubleshooting scenarios (included in this doc)
4. Decide: retry, skip, or abort test
5. Update test run status accordingly

### 4. Cleanup Protocol

**At the end of testing (or when requested):**
1. Ask user if they want to clean up test data
2. Guide them through the cleanup script execution (Appendix A)
3. Remind them to reset QuickBooks sandbox manually
4. Confirm cleanup completed successfully

---

## 🎯 Testing Overview

This document guides you through a **complete QuickBooks integration test** in a single flow:

1. **OAuth Connection** (Task 16) - Establish secure connection to QuickBooks
2. **Customer Sync** (Task 17) - Bidirectional customer synchronization
3. **Conflict Resolution** (Task 18) - Handle simultaneous edits in both systems
4. **Webhook Handling** (Task 19) - Real-time sync via QuickBooks webhooks
5. **Cleanup & Disconnect** - Reset environment for next test

**Total Steps:** ~50 steps  
**Estimated Time:** 60-90 minutes (excluding wait times)  
**Prerequisites:** All services running (details below)

---

## ⚠️ Prerequisites

**Before starting, ensure you have:**

✅ **QuickBooks Developer Account**
- Intuit Developer Account created
- Sandbox App created (Client ID + Secret)
- Sandbox Test Company created
- OAuth Redirect URI configured: `https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback`
- Webhook endpoint configured: `https://your-tunnel.ngrok-free.dev/api/v1/webhooks/quickbooks`
- Webhook Verifier Token obtained
- "Cloud event payload format" enabled in webhook settings

✅ **Environment Variables** (in `backend/.env`)
```bash
QUICKBOOKS_CLIENT_ID=<your_client_id>
QUICKBOOKS_CLIENT_SECRET=<your_client_secret>
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_REDIRECT_URI=https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback
QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN=<your_verifier_token>
ENCRYPTION_KEY=<your_fernet_key>
TEST_ENDPOINT_ENABLED=true
```

✅ **All Services Running**
- PostgreSQL (Docker)
- Redis (Docker)
- Celery Worker
- Celery Beat
- FastAPI Backend (uvicorn)
- ngrok tunnel (static domain)

**Note:** We assume all services are already running. If you need service startup instructions, refer to `task-16-qb-oauth-sandbox-testing-plan.md`.

---

## 🧪 Test Flow: All Tasks 16-19

### SECTION 1: OAUTH CONNECTION (Task 16)

---

### Step 1 (Task 16): Verify Services Running

**Purpose:** Confirm all required services are operational before starting OAuth flow.

**Command:**
```bash
# Test backend health
curl http://localhost:8000/api/v1/hello
```

**Expected Output:**
```json
{"greeting":"Hello from the FastAPI backend!"}
```

**Verify in browser:**
```
https://your-tunnel.ngrok-free.dev/docs
```

**Expected:** FastAPI Swagger docs page loads successfully.

---

### Step 2 (Task 16): Initiate OAuth Connection

**Purpose:** Start OAuth 2.0 flow to connect QuickBooks sandbox account.

**Action:** Open browser and navigate to:
```
http://localhost:8000/api/v1/integrations/quickbooks/connect/test
```

**Expected:** 
- Automatic redirect to QuickBooks authorization page
- URL should contain: `https://appcenter.intuit.com/connect/oauth2?client_id=...`
- Your sandbox test company should appear in dropdown

**Next:** 
1. Select your sandbox test company
2. Click **"Connect"** or **"Authorize"**

---

### Step 3 (Task 16): Verify OAuth Callback Success

**Purpose:** Confirm QuickBooks successfully redirected back with authorization code.

**Expected:**
- Browser displays HTML success page with:
  - ✓ Success checkmark
  - Company ID (realm_id)
  - Connection Status: Active
  - Token expiration time (~1 hour from now)

**Check ngrok Logs:**
- Open: http://127.0.0.1:4040
- Verify callback request appears with status 200

**Check Backend Logs (Terminal):**
```
INFO: Received QuickBooks OAuth callback
INFO: State token validated successfully
INFO: Exchanging authorization code for tokens
INFO: Tokens received and encrypted
INFO: Connection status updated to 'active'
```

---

### Step 4 (Task 16): Verify Database - OAuth Connection

**Purpose:** Confirm OAuth tokens stored encrypted in database.

**Connect to database:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev
```

**Query 1: Check app_service record**
```sql
SELECT 
    id,
    tenant_id,
    provider_code,
    external_account_id,
    is_active,
    created_at
FROM app_service
WHERE provider_code = 'quickbooks'
ORDER BY created_at DESC
LIMIT 1;
```

**Expected:**
- `provider_code`: 'quickbooks'
- `external_account_id`: [realm_id from QB]
- `is_active`: true

**Record:** `REALM_ID=<external_account_id value>`

**Query 2: Check integration_credential**
```sql
SELECT 
    id,
    tenant_id,
    app_service_id,
    connection_status,
    expires_at,
    connected_at,
    last_refresh_at
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;
```

**Expected:**
- `connection_status`: 'active'
- `expires_at`: ~1 hour in future
- `connected_at`: recent timestamp

**Query 3: Verify tokens encrypted**
```sql
SELECT 
    secret_json->>'access_token_encrypted' as access_token,
    secret_json->>'refresh_token_encrypted' as refresh_token
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;
```

**Expected:** Both tokens start with `"gAAAAA..."` (Fernet encrypted)

**Exit psql:**
```sql
\q
```

---

### Step 5 (Task 16): Test Connection Status Endpoint

**Purpose:** Verify status endpoint returns connection details.

**Command:**
```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"
```

**Expected Response:**
```json
{
  "is_connected": true,
  "connection_status": "active",
  "realm_id": "<realm_id>",
  "company_name": "QuickBooks Online",
  "connected_at": "2026-03-24T...",
  "expires_at": "2026-03-24T..." 
}
```

**Success Criteria:**
- `is_connected`: true
- `connection_status`: "active"

---

### SECTION 2: CUSTOMER SYNC (Task 17)

---

### Step 6 (Task 17): Initial Customer Sync from QuickBooks

**Purpose:** Sync all existing customers from QuickBooks sandbox to AevoFab.

**Note:** QuickBooks sandbox comes with ~20-30 pre-populated test customers. This initial sync will pull all of them.

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "status": "success",
  "synced_count": 28,
  "message": "Synced 28 customer(s) from QuickBooks"
}
```

**Watch Celery Worker Logs:**
```
[INFO] Starting customer sync for tenant <tenant_id>
[INFO] Fetching customers from QuickBooks API...
[INFO] Found 28 customer(s) to sync
[INFO] Processing customer: [name] (ID: XX)
[INFO] Created customer in AevoFab database
[INFO] Created sync mapping record
...
[INFO] Customer sync completed successfully
```

**Note:** This step may take 10-30 seconds depending on number of customers.

---

### Step 7 (Task 17): Verify Initial Sync in Database

**Purpose:** Confirm all QB customers synced to AevoFab with mappings.

**Connect to database:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev
```

**Query: Count synced customers**
```sql
SELECT 
    COUNT(*) as total_customers,
    COUNT(DISTINCT ism.external_id) as unique_qb_ids,
    MAX(ism.last_synced_at) as most_recent_sync
FROM customer c
JOIN integration_sync_mapping ism ON ism.entity_id = c.id
WHERE ism.entity_type_code = 'customer';
```

**Expected:** 
- `total_customers`: ~20-30 (matches QB sandbox)
- `unique_qb_ids`: same as total_customers
- `most_recent_sync`: within last few minutes

**Query: View sample customers**
```sql
SELECT 
    c.display_name,
    c.email,
    ism.external_id as qb_customer_id,
    ism.external_version_token as qb_sync_token
FROM customer c
JOIN integration_sync_mapping ism ON ism.entity_id = c.id
WHERE ism.entity_type_code = 'customer'
ORDER BY c.created_at DESC
LIMIT 5;
```

**Expected:** List of 5 customers with QB IDs and sync tokens.

**Exit psql:**
```sql
\q
```

---

### Step 8 (Task 17): Create Test Customer in QuickBooks

**Purpose:** Test QB → AevoFab sync with a new customer.

**Action:**
1. Log into QuickBooks Sandbox: https://app.sandbox.qbo.intuit.com
2. Navigate to **Sales** → **Customers** → **New Customer**
3. Enter customer details:
   ```
   Display Name: Test Sync Electric
   Company Name: Test Sync Company LLC
   Email: testsync@test.com
   Phone: (555) 100-0001
   Billing Address:
     Street: 100 Test St
     City: Denver
     State: CO
     ZIP: 80202
   ```
4. Click **Save**
5. Note the Customer ID from URL: `https://app.sandbox.qbo.intuit.com/app/customerdetail?nameId=XX`

**Record:** `QB_CUSTOMER_ID_1=<nameId value>`

---

### Step 9 (Task 17): Sync New Customer to AevoFab

**Purpose:** Trigger incremental sync to pull the new customer.

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"
```

**Expected Response:**
```json
{
  "status": "success",
  "synced_count": 1,
  "message": "Synced 1 customer(s) from QuickBooks"
}
```

**Verify in database:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT id, display_name, email_primary FROM customer WHERE display_name = 'Test Sync Electric';"
```

**Expected:** 1 row with matching data.

**Record:** `AEVOFAB_CUSTOMER_ID_1=<id value>`

---

### Step 10 (Task 17): Verify Duplicate Prevention

**Purpose:** Confirm re-syncing same customer doesn't create duplicates.

**Command:**
```bash
# Sync again (same customer should be skipped)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"
```

**Expected Response:**
```json
{
  "status": "success",
  "synced_count": 0,
  "message": "Synced 0 customer(s) from QuickBooks"
}
```

**Verify no duplicate:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT COUNT(*) as count FROM customer WHERE display_name = 'Test Sync Electric';"
```

**Expected:** `count = 1` (NOT 2)

---

### Step 11 (Task 17): Test QB → AevoFab Update Detection

**Purpose:** Verify changes in QB sync to AevoFab.

**Action in QuickBooks:**
1. Navigate to "Test Sync Electric" customer in QB sandbox
2. Click **Edit**
3. Change:
   ```
   Email: updated@testsync.com
   Phone: (555) 200-0002
   ```
4. Click **Save**

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"
```

**Verify update:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT email, mobile_phone FROM customer WHERE display_name = 'Test Sync Electric';"
```

**Expected:**
- `email`: 'updated@testsync.com'
- `mobile_phone`: '(555) 200-0002'

---

### Step 12 (Task 17): Create Customer in AevoFab

**Purpose:** Test AevoFab → QB sync (push direction).

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/customers/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "AevoFab Push Test",
    "company_name": "AevoFab Push Company",
    "email_primary": "pushtest@aevofab.example.com",
    "phone_primary": "(555) 300-0003"
  }'
```

**Expected Response:** JSON with customer details including `"id": "<uuid>"`

**Record:** `AEVOFAB_CUSTOMER_ID_2=<id value>`

---

### Step 13 (Task 17): Sync AevoFab Customer to QuickBooks

**Purpose:** Push newly created AevoFab customer to QuickBooks.

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<AEVOFAB_CUSTOMER_ID_2>/test"
```

**Replace `<AEVOFAB_CUSTOMER_ID_2>` with actual UUID from Step 12.**

**Expected Response:**
```json
{
  "status": "success",
  "quickbooks_id": "XX",
  "message": "Customer synced to QuickBooks successfully"
}
```

**Record:** `QB_CUSTOMER_ID_2=<quickbooks_id value>`

**Verify in QuickBooks:**
1. In QB sandbox, go to **Sales** → **Customers**
2. Search for "AevoFab Push Test"
3. Verify fields match AevoFab data

---

### Step 14 (Task 17): Test AevoFab → QB Update

**Purpose:** Verify updates in AevoFab push to QuickBooks.

**Command:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/customers/<AEVOFAB_CUSTOMER_ID_2>/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "AevoFab Push Test",
    "email_primary": "updated@aevofab.example.com",
    "phone_primary": "(555) 400-0004"
  }'
```

**Sync update to QB:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<AEVOFAB_CUSTOMER_ID_2>/test"
```

**Verify in QuickBooks:**
1. Navigate to "AevoFab Push Test" in QB
2. Confirm:
   - Email: `updated@aevofab.example.com`
   - Phone: `(555) 400-0004`

---

### SECTION 3: CONFLICT DETECTION & RESOLUTION (Task 18)

---

### Step 15 (Task 18): Setup - Create Conflict Test Customer

**Purpose:** Create and sync a customer that we'll use for conflict testing.

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/customers/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Conflict Test Electric",
    "company_name": "Conflict Test Company",
    "email_primary": "conflict@test.com",
    "phone_primary": "(555) 500-0005"
  }'
```

**Record:** `CONFLICT_CUSTOMER_ID=<id value>`

**Sync to QB:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<CONFLICT_CUSTOMER_ID>/test"
```

**Record:** `CONFLICT_QB_ID=<quickbooks_id from response>`

---

### Step 16 (Task 18): Record Initial Version Tokens

**Purpose:** Document baseline version tokens before creating conflict.

**Query:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT ism.external_version_token as qb_token, ism.internal_version_token as aevofab_token, c.updated_at FROM integration_sync_mapping ism JOIN customer c ON c.id = ism.entity_id WHERE c.display_name = 'Conflict Test Electric';"
```

**Record these values:**
- `INITIAL_QB_TOKEN=<external_version_token>`
- `INITIAL_AEVOFAB_TOKEN=<internal_version_token>`

---

### Step 17 (Task 18): Edit Customer in AevoFab (Do NOT Sync)

**Purpose:** Create local changes without syncing to QB (half of the conflict).

**Command:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/customers/<CONFLICT_CUSTOMER_ID>/test" \
  -H "Content-Type: application/json" \
  -d '{
    "email_primary": "aevofab_edit@conflict.com"
  }'
```

**⚠️ CRITICAL:** Do NOT sync yet. This is key to creating the conflict.

**Verify local change:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT email_primary, updated_at FROM customer WHERE display_name = 'Conflict Test Electric';"
```

**Expected:** 
- `email_primary`: 'aevofab_edit@conflict.com'
- `updated_at`: NEW timestamp (different from Step 16)

---

### Step 18 (Task 18): Edit Same Customer in QuickBooks

**Purpose:** Create remote changes in QB (second half of conflict).

**Action in QuickBooks:**
1. Navigate to "Conflict Test Electric" in QB sandbox
2. Click **Edit**
3. Change:
   ```
   Email: qb_edit@conflict.com
   Phone: (555) 600-0006
   ```
4. Click **Save**

**Note:** QuickBooks increments SyncToken (version) when you save.

---

### Step 19 (Task 18): Trigger Sync - Conflict Should Be Detected

**Purpose:** Sync attempts to pull QB changes but detects local changes exist → CONFLICT.

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"
```

**Expected Response:**
```json
{
  "status": "success",
  "synced_count": 0,
  "conflicts_detected": 1,
  "message": "Detected 1 conflict(s) requiring resolution"
}
```

**Watch Celery Worker Logs:**
```
[INFO] Processing customer: Conflict Test Electric
[INFO] Conflict detected: Both QB and AevoFab modified since last sync
[INFO] QB SyncToken changed: 0 → 1
[INFO] AevoFab updated_at changed
[INFO] Queuing conflict for manual resolution
```

---

### Step 20 (Task 18): Verify Conflict Record Created

**Purpose:** Confirm conflict queued in database with both versions.

**Query:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev
```

```sql
SELECT 
    ic.id as conflict_id,
    ic.local_payload_json->>'email_primary' as aevofab_email,
    ic.remote_payload_json->'PrimaryEmailAddr'->>'Address' as qb_email,
    ic.detected_at,
    ic.resolved_at,
    c.display_name
FROM integration_sync_conflict ic
JOIN customer c ON c.id = ic.entity_id
WHERE c.display_name = 'Conflict Test Electric'
ORDER BY ic.detected_at DESC
LIMIT 1;
```

**Expected:**
- `aevofab_email`: 'aevofab_edit@conflict.com'
- `qb_email`: 'qb_edit@conflict.com'
- `detected_at`: recent timestamp
- `resolved_at`: NULL (unresolved)

**Record:** `CONFLICT_ID=<conflict_id value>`

**Exit psql:**
```sql
\q
```

---

### Step 21 (Task 18): Verify Customer Data NOT Overwritten

**Purpose:** Ensure conflict detection prevented data loss.

**Query:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT email_primary, phone_primary FROM customer WHERE display_name = 'Conflict Test Electric';"
```

**Expected (UNCHANGED from Step 17):**
- `email_primary`: 'aevofab_edit@conflict.com' (local edit preserved)
- `phone_primary`: '(555) 500-0005' (original, NOT QB's new value)

---

### Step 22 (Task 18): List Unresolved Conflicts

**Purpose:** Test conflict listing API endpoint.

**Command:**
```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/test"
```

**Expected Response:** Array with at least 1 conflict showing both local and remote payloads.

---

### Step 23 (Task 18): Resolve Conflict - Accept Local (AevoFab Wins)

**Purpose:** Test "accept_local" resolution strategy.

**Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/<CONFLICT_ID>/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "accept_local",
    "notes": "AevoFab version is correct"
  }'
```

**Replace `<CONFLICT_ID>` with UUID from Step 20.**

**Expected Response:**
```json
{
  "status": "resolved",
  "conflict_id": "<conflict_id>",
  "resolution_strategy": "accept_local",
  "resolved_at": "2026-03-24T...",
  "message": "Conflict resolved successfully"
}
```

**Verify QuickBooks Updated:**
1. In QB sandbox, navigate to "Conflict Test Electric"
2. Confirm email now shows: `aevofab_edit@conflict.com` (AevoFab version pushed to QB)

---

### Step 24 (Task 18): Create Second Conflict for "Accept Remote" Test

**Purpose:** Test QB wins scenario.

**Create customer:**
```bash
curl -X POST "http://localhost:8000/api/v1/customers/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "QB Wins Test",
    "email_primary": "qb-example@test.com"
  }'
```

**Record:** `QB_WINS_CUSTOMER_ID=<id>`

**Sync to QB:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<QB_WINS_CUSTOMER_ID>/test"
```

**Edit in AevoFab:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/customers/<QB_WINS_CUSTOMER_ID>/test" \
  -H "Content-Type: application/json" \
  -d '{"email_primary": "aevo@qb-example.com"}'
```

**Edit in QB:** Change email to `quickbooks@qb-example.com`

**Trigger sync:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"
```

**Expected:** Conflict detected.

---

### Step 25 (Task 18): Resolve Conflict - Accept Remote (QB Wins)

**Purpose:** Test "accept_remote" resolution strategy.

**List conflicts to get new conflict ID:**
```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/test" | grep -A 5 "QB Wins Test"
```

**Record:** `CONFLICT_ID_2=<conflict_id>`

**Resolve:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/<CONFLICT_ID_2>/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "accept_remote",
    "notes": "QuickBooks version is authoritative"
  }'
```

**Verify AevoFab updated:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT email_primary FROM customer WHERE display_name = 'QB Wins Test';"
```

**Expected:** `email_primary` = 'quickbooks@qb-example.com' (QB version)

---

### Step 26 (Task 18): Test One-Sided Edit (No Conflict)

**Purpose:** Verify editing only in QB doesn't trigger conflict.

**Create customer:**
```bash
curl -X POST "http://localhost:8000/api/v1/customers/test" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "No Conflict Test", "email_primary": "noconflict@test.com"}'
```

**Record:** `NO_CONFLICT_ID=<id>`

**Sync to QB:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<NO_CONFLICT_ID>/test"
```

**Edit ONLY in QB:** Change email to `onlygb@test.com` (do NOT edit in AevoFab)

**Sync:**
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"
```

**Expected Response:**
```json
{
  "status": "success",
  "synced_count": 1,
  "conflicts_detected": 0
}
```

**Verify AevoFab updated:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT email_primary FROM customer WHERE display_name = 'No Conflict Test';"
```

**Expected:** `email_primary` = 'onlygb@test.com' (synced without conflict)

---

### SECTION 4: WEBHOOK HANDLER (Task 19)

---

### Step 27 (Task 19): Verify Webhook Endpoint Configured

**Purpose:** Confirm webhook endpoint registered in QuickBooks Developer Portal.

**Manual Verification:**
1. Log into Intuit Developer Portal: https://developer.intuit.com
2. Navigate to your app → **Webhooks** section
3. Verify:
   - Endpoint URL: `https://your-tunnel.ngrok-free.dev/api/v1/webhooks/quickbooks`
   - Entities enabled: Customer, Invoice
   - "Cloud event payload format" checkbox: ✅ CHECKED
   - Webhook Verifier Token matches `.env` file

**If not configured:** Follow QuickBooks webhook setup documentation.

---

### Step 28 (Task 19): Verify ngrok Tunnel Active

**Purpose:** Ensure webhook endpoint is publicly accessible.

**Check ngrok dashboard:**
```
http://127.0.0.1:4040
```

**Expected:** Dashboard shows tunnel status "online"

**Test public endpoint:**
```bash
curl https://your-tunnel.ngrok-free.dev/api/v1/hello
```

**Expected:** Returns greeting message.

---

### Step 29 (Task 19): Create Customer in QuickBooks (Webhook Trigger)

**Purpose:** Test real-time webhook delivery when customer created in QB.

**Action in QuickBooks:**
1. Navigate to **Sales** → **Customers** → **New Customer**
2. Enter:
   ```
   Display Name: Webhook Test Customer
   Email: webhook@test.com
   ```
3. Click **Save**

**Expected (within 5 seconds):**
- QuickBooks sends webhook to ngrok URL
- ngrok forwards to localhost:8000
- Webhook handler processes event
- Celery task triggered for customer sync

---

### Step 30 (Task 19): Monitor Webhook Delivery

**Purpose:** Verify webhook received and processed correctly.

**Check ngrok dashboard:** http://127.0.0.1:4040
- Look for POST request to `/api/v1/webhooks/quickbooks`
- Status should be 200 OK
- Inspect payload (should be Cloud Events format)

**Check backend logs (FastAPI terminal):**
```
INFO: QuickBooks webhook received: com.intuit.quickbooks.customer.create - <event_id>
INFO: Queued sync for Customer <entity_id> (create)
```

**Check Celery worker logs:**
```
[INFO] Task sync_quickbooks_entity[<uuid>] received
[INFO] Syncing Customer <entity_id> for tenant <tenant_id>
[INFO] Fetching customer from QuickBooks API...
[INFO] Created customer in AevoFab database
[INFO] Task sync_quickbooks_entity[<uuid>] succeeded
```

---

### Step 31 (Task 19): Verify Webhook-Synced Customer in Database

**Purpose:** Confirm webhook triggered sync created customer in AevoFab.

**Query:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT id, display_name, email_primary, created_at FROM customer WHERE display_name = 'Webhook Test Customer' ORDER BY created_at DESC LIMIT 1;"
```

**Expected:** 1 row with recent `created_at` timestamp.

**Success:** Customer synced automatically via webhook (no manual sync needed).

---

### Step 32 (Task 19): Test Webhook Update Event

**Purpose:** Verify webhooks trigger updates correctly.

**Action in QuickBooks:**
1. Navigate to "Webhook Test Customer"
2. Click **Edit**
3. Change email to: `webhook_updated@test.com`
4. Click **Save**

**Monitor webhook:**
- Check ngrok dashboard for new POST (event type: `com.intuit.quickbooks.customer.update`)
- Check Celery logs for sync task

**Verify update:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT email_primary, updated_at FROM customer WHERE display_name = 'Webhook Test Customer';"
```

**Expected:** `email_primary` = 'webhook_updated@test.com'

---

### Step 33 (Task 19): Test Webhook Signature Verification

**Purpose:** Confirm webhook security prevents unauthorized requests.

**Command (simulate webhook without valid signature):**
```bash
curl -X POST "http://localhost:8000/api/v1/webhooks/quickbooks" \
  -H "Content-Type: application/json" \
  -H "intuit-signature: FAKE_SIGNATURE" \
  -d '{
    "specversion": "1.0",
    "type": "com.intuit.quickbooks.customer.create",
    "data": {"realmId": "123", "entityName": "Customer", "entityId": "999"}
  }'
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Invalid signature"
}
```

**Success:** Webhook handler rejects unauthorized requests.

---

### Step 34 (Task 19): Verify Webhook Event Logging

**Purpose:** Confirm all webhook events logged for audit trail.

**Query:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev
```

```sql
SELECT 
    source_app,
    event_type,
    signature_valid,
    processed_at,
    created_at
FROM integration.webhook_event
ORDER BY created_at DESC
LIMIT 5;
```

**Expected:** Rows for recent webhook events with `signature_valid = true`.

**Exit psql:**
```sql
\q
```

---

### SECTION 5: CLEANUP & DISCONNECT

---

### Step 35 (Cleanup): Run Cleanup Script

**Purpose:** Remove all test data from AevoFab database.

**Create cleanup script file:**
```bash
# Copy script from Appendix A to:
touch backend/tests/scripts/cleanup_qb_tests.py
# Paste script content (see Appendix A)
```

**Run cleanup:**
```bash
cd backend
python tests/scripts/cleanup_qb_tests.py
```

**Expected Output:**
```
🧹 Starting QuickBooks integration test cleanup...
✅ Deleted XX webhook events
✅ Deleted XX conflicts
✅ Deleted XX sync mappings
✅ Deleted XX test customers
✨ Cleanup complete! Database reset to pre-test state.

⚠️  Remember to reset QuickBooks Sandbox manually!
```

---

### Step 36 (Cleanup): Verify Database Cleanup

**Purpose:** Confirm all test customers removed from AevoFab.

**Query:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT COUNT(*) as remaining_customers FROM customer WHERE tenant_id = '00000000-0000-0000-0000-000000000001';"
```

**Expected:** `remaining_customers = 0` (all test data removed)

---

### Step 37 (Cleanup): Reset QuickBooks Sandbox

**Purpose:** Remove all test customers from QuickBooks sandbox.

**Option 1: Manual Deletion (for <10 test customers)**
1. Log into QB sandbox: https://app.sandbox.qbo.intuit.com
2. Navigate to **Sales** → **Customers**
3. For each test customer created during testing:
   - Click customer name
   - Click **Edit** → **Make inactive**

**Option 2: Reset Sandbox Company (recommended)**
1. Go to Intuit Developer Portal: https://developer.intuit.com
2. Navigate to **Dashboard** → **Sandbox**
3. Find your test company
4. Click **Reset Company Data**
5. Confirm reset

**Note:** Resetting sandbox will remove ALL customers (including the ~20-30 default ones). You'll need to re-run OAuth (Step 2) after reset.

---

### Step 38 (Disconnect): Disconnect QuickBooks Integration

**Purpose:** Test disconnect flow and clean up OAuth connection.

**Command:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/integrations/quickbooks/disconnect/test"
```

**Expected Response:**
```json
{
  "status": "disconnected",
  "disconnected_at": "2026-03-24T...",
  "message": "QuickBooks integration disconnected successfully"
}
```

---

### Step 39 (Disconnect): Verify Disconnection in Database

**Purpose:** Confirm connection status updated to disconnected.

**Query:**
```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT connection_status, disconnected_at FROM integration_credential WHERE app_service_id IN (SELECT id FROM app_service WHERE provider_code = 'quickbooks') ORDER BY created_at DESC LIMIT 1;"
```

**Expected:**
- `connection_status`: 'disconnected'
- `disconnected_at`: recent timestamp

---

### Step 40 (Disconnect): Verify Status Endpoint Shows Disconnected

**Purpose:** Confirm status API reflects disconnection.

**Command:**
```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"
```

**Expected Response:**
```json
{
  "is_connected": false,
  "connection_status": "disconnected",
  "realm_id": "<realm_id>",
  "disconnected_at": "2026-03-24T..."
}
```

---

## ✅ Test Completion Checklist

Use this checklist to track overall test progress:

### Task 16: OAuth Flow
- [ ] Step 1: Services verified running
- [ ] Step 2: OAuth flow initiated successfully
- [ ] Step 3: Callback received and processed
- [ ] Step 4: Tokens stored encrypted in database
- [ ] Step 5: Status endpoint returns active connection

### Task 17: Customer Sync
- [ ] Step 6-7: Initial sync pulled all QB customers
- [ ] Step 8-10: Created customer in QB synced to AevoFab
- [ ] Step 11: Updates in QB synced to AevoFab
- [ ] Step 12-14: Created customer in AevoFab synced to QB
- [ ] Duplicate prevention verified

### Task 18: Conflict Detection
- [ ] Step 15-21: Simultaneous edits triggered conflict
- [ ] Step 22: Conflict listing API works
- [ ] Step 23: "Accept local" resolution pushed to QB
- [ ] Step 24-25: "Accept remote" resolution updated AevoFab
- [ ] Step 26: One-sided edit synced without conflict

### Task 19: Webhooks
- [ ] Step 27-28: Webhook endpoint configured and accessible
- [ ] Step 29-31: Customer creation triggered webhook sync
- [ ] Step 32: Customer update triggered webhook sync
- [ ] Step 33: Invalid signature rejected
- [ ] Step 34: Webhook events logged

### Cleanup
- [ ] Step 35-36: Database cleanup completed
- [ ] Step 37: QuickBooks sandbox reset
- [ ] Step 38-40: Integration disconnected successfully

---

## 📊 Performance Benchmarks

| Operation | Expected Time | Your Result |
|-----------|---------------|-------------|
| OAuth flow (complete) | < 10 seconds | _____ |
| Initial customer sync (30 customers) | < 30 seconds | _____ |
| Incremental sync (1 customer) | < 2 seconds | _____ |
| Conflict detection | < 1 second | _____ |
| Conflict resolution | < 3 seconds | _____ |
| Webhook receipt to sync complete | < 5 seconds | _____ |
| Customer push to QB | < 3 seconds | _____ |

---

## 🐛 Troubleshooting Guide

### Issue: OAuth Callback Fails

**Symptoms:** Redirect to callback URL shows error

**Solutions:**
1. Verify ngrok tunnel is running and accessible
2. Check redirect URI matches exactly in QB app settings
3. Verify `ENCRYPTION_KEY` is valid Fernet key
4. Check backend logs for specific error message

---

### Issue: Customer Sync Returns 0 Records

**Symptoms:** Sync completes but no customers synced

**Solutions:**
1. Verify QB connection is active: `curl .../status/test`
2. Check if token expired (re-run OAuth if needed)
3. Verify customers exist in QB sandbox
4. Check Celery worker is running and processing tasks

---

### Issue: Conflict Not Detected

**Symptoms:** Simultaneous edits don't trigger conflict

**Solutions:**
1. Verify you edited in AevoFab first (without syncing)
2. Confirm you edited in QB second
3. Check both edits modified different fields (conflict detection looks at version tokens, not specific fields)
4. Review Celery worker logs for conflict detection logic

---

### Issue: Webhook Not Received

**Symptoms:** Create customer in QB but no webhook delivered

**Solutions:**
1. Verify ngrok tunnel is running and public
2. Check webhook endpoint configured in QB Developer Portal
3. Verify webhook entities enabled (Customer, Invoice)
4. Check "Cloud event payload format" is enabled
5. Review ngrok dashboard for incoming requests
6. Test endpoint manually: `curl https://<domain>/api/v1/webhooks/quickbooks`

---

### Issue: Webhook Signature Fails

**Symptoms:** Webhook returns 401 Invalid Signature

**Solutions:**
1. Verify `QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN` in `.env` matches Intuit portal
2. Check token has no extra spaces or quotes
3. Regenerate verifier token in Intuit portal if needed
4. Restart FastAPI backend after updating `.env`

---

### Issue: Database Connection Fails

**Symptoms:** psql commands return connection refused

**Solutions:**
1. Verify PostgreSQL container is running: `docker ps`
2. Check connection string is correct
3. Restart PostgreSQL: `docker-compose restart postgres`

---

### Issue: Cleanup Script Fails

**Symptoms:** Python cleanup script throws errors

**Solutions:**
1. Verify script has correct tenant_id (default: `00000000-0000-0000-0000-000000000001`)
2. Check database connection string
3. Run manual SQL cleanup instead (see Appendix B)

---

## 📚 Reference Documentation

- **Task 16 Detailed Guide:** `task-16-qb-oauth-sandbox-testing-plan.md`
- **Task 17 Detailed Guide:** `task-17-qb-manual-int-testing-plan.md`
- **Task 18 Detailed Guide:** `task-18-qb-manual-conflict-testing-plan.md`
- **Implementation Roadmap:** `phase-2-5-implementation-roadmap.md` (Lines 1391-1905)
- **QuickBooks API Docs:** https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/customer
- **QuickBooks Webhooks Docs:** https://developer.intuit.com/app/developer/qbo/docs/develop/webhooks/overview

---

## 📝 Appendix A: Cleanup Script

**File:** `backend/tests/scripts/cleanup_qb_tests.py`

```python
#!/usr/bin/env python3
"""
QuickBooks Integration Test Cleanup Script

Purpose: Remove ALL test data created during QB integration testing including:
- All customers synced from QuickBooks sandbox (~20-30 default customers)
- Test customers created during manual testing
- Integration sync mappings
- Integration sync conflicts
- Webhook events

WARNING: Only run in DEV environment!

Usage:
    cd backend
    python tests/scripts/cleanup_qb_tests.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, delete
from app.db import engine, AsyncSession
from app.models.customer import Customer
from app.models.system import (
    IntegrationSyncMapping,
    IntegrationSyncConflict,
    AppService,
    IntegrationCredential
)


async def cleanup_all_qb_test_data():
    """
    Clean up ALL QuickBooks test data including initial sync
    
    WARNING: This will delete ALL customers and mappings for the test tenant!
    """
    # CHANGE THIS if using a different test tenant
    test_tenant_id = "00000000-0000-0000-0000-000000000001"
    
    print("🧹 Starting QuickBooks integration test cleanup...")
    print(f"⚠️  Target Tenant: {test_tenant_id}")
    print()
    
    # Confirmation prompt
    confirm = input("This will delete ALL customers and sync data. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Cleanup cancelled.")
        return
    
    async with AsyncSession(engine) as db:
        
        # 1. Delete webhook events
        try:
            # Note: Adjust table name if webhook_event model exists
            # Skipping if table doesn't exist yet
            print("⏩ Skipping webhook events (table may not exist yet)")
        except Exception as e:
            print(f"⚠️  Warning: {e}")
        
        # 2. Delete all conflicts
        result = await db.execute(
            delete(IntegrationSyncConflict)
            .where(IntegrationSyncConflict.tenant_id == test_tenant_id)
        )
        print(f"✅ Deleted {result.rowcount} conflict record(s)")
        
        # 3. Get all customer IDs for this tenant
        customers = await db.execute(
            select(Customer.id)
            .where(Customer.tenant_id == test_tenant_id)
        )
        customer_ids = [c.id for c in customers.scalars().all()]
        customer_count = len(customer_ids)
        
        # 4. Delete all sync mappings for these customers
        if customer_ids:
            result = await db.execute(
                delete(IntegrationSyncMapping)
                .where(IntegrationSyncMapping.entity_id.in_(customer_ids))
                .where(IntegrationSyncMapping.entity_type_code == 'customer')
            )
            print(f"✅ Deleted {result.rowcount} sync mapping(s)")
        
        # 5. Delete ALL customers (including initial QB sandbox sync)
        result = await db.execute(
            delete(Customer)
            .where(Customer.tenant_id == test_tenant_id)
        )
        print(f"✅ Deleted {result.rowcount} customer record(s)")
        
        await db.commit()
        
        print()
        print("✨ Cleanup complete! Database reset to pre-test state.")
        print()
        print("📋 Next Steps:")
        print("1. Reset QuickBooks Sandbox in Intuit Developer Portal")
        print("2. Optionally disconnect QB integration (or leave for next test)")
        print()
        print("To reconnect for next test:")
        print("  curl -X GET http://localhost:8000/api/v1/integrations/quickbooks/connect/test")


async def cleanup_specific_test_customers():
    """
    Alternative: Clean up only test customers created during manual testing
    
    This preserves the initial QB sandbox customers if you want to keep them.
    """
    test_tenant_id = "00000000-0000-0000-0000-000000000001"
    
    # List of customer names created during testing
    test_customer_names = [
        'Test Sync Electric',
        'AevoFab Push Test',
        'Conflict Test Electric',
        'QB Wins Test',
        'No Conflict Test',
        'Webhook Test Customer'
    ]
    
    print("🧹 Starting selective cleanup (test customers only)...")
    
    async with AsyncSession(engine) as db:
        
        # 1. Delete conflicts
        result = await db.execute(
            delete(IntegrationSyncConflict)
            .where(IntegrationSyncConflict.tenant_id == test_tenant_id)
        )
        print(f"✅ Deleted {result.rowcount} conflict(s)")
        
        # 2. Get test customer IDs
        customers = await db.execute(
            select(Customer.id)
            .where(Customer.tenant_id == test_tenant_id)
            .where(Customer.display_name.in_(test_customer_names))
        )
        customer_ids = [c.id for c in customers.scalars().all()]
        
        # 3. Delete mappings for test customers
        if customer_ids:
            result = await db.execute(
                delete(IntegrationSyncMapping)
                .where(IntegrationSyncMapping.entity_id.in_(customer_ids))
            )
            print(f"✅ Deleted {result.rowcount} sync mapping(s)")
        
        # 4. Delete test customers
        result = await db.execute(
            delete(Customer)
            .where(Customer.tenant_id == test_tenant_id)
            .where(Customer.display_name.in_(test_customer_names))
        )
        print(f"✅ Deleted {result.rowcount} test customer(s)")
        
        await db.commit()
        
        print()
        print("✨ Selective cleanup complete!")
        print("ℹ️  Initial QB sandbox customers preserved.")


if __name__ == "__main__":
    print()
    print("QuickBooks Integration Test Cleanup")
    print("=" * 50)
    print()
    print("Choose cleanup mode:")
    print("1. Delete ALL customers and sync data (recommended)")
    print("2. Delete only test customers created during manual testing")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(cleanup_all_qb_test_data())
    elif choice == "2":
        asyncio.run(cleanup_specific_test_customers())
    else:
        print("❌ Invalid choice. Exiting.")
```

---

## 📝 Appendix B: Manual SQL Cleanup

**Alternative to Python script - direct SQL commands:**

```bash
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev
```

```sql
-- Set test tenant ID
\set test_tenant_id '00000000-0000-0000-0000-000000000001'

-- OPTION 1: Delete EVERYTHING (recommended)

BEGIN;

-- Delete conflicts
DELETE FROM integration.integration_sync_conflict
WHERE tenant_id = :'test_tenant_id';

-- Delete sync mappings
DELETE FROM integration.integration_sync_mapping
WHERE tenant_id = :'test_tenant_id'
  AND entity_type_code = 'customer';

-- Delete ALL customers
DELETE FROM customer.customer
WHERE tenant_id = :'test_tenant_id';

-- Verify cleanup
SELECT 
    (SELECT COUNT(*) FROM integration.integration_sync_conflict WHERE tenant_id = :'test_tenant_id') as conflicts,
    (SELECT COUNT(*) FROM integration.integration_sync_mapping WHERE tenant_id = :'test_tenant_id') as mappings,
    (SELECT COUNT(*) FROM customer.customer WHERE tenant_id = :'test_tenant_id') as customers;

-- If counts are all 0, commit:
COMMIT;

-- If something looks wrong:
-- ROLLBACK;


-- OPTION 2: Delete only specific test customers

BEGIN;

-- Delete conflicts
DELETE FROM integration.integration_sync_conflict
WHERE tenant_id = :'test_tenant_id';

-- Delete mappings for test customers
DELETE FROM integration.integration_sync_mapping
WHERE tenant_id = :'test_tenant_id'
  AND entity_id IN (
    SELECT id FROM customer.customer
    WHERE display_name IN (
      'Test Sync Electric',
      'AevoFab Push Test',
      'Conflict Test Electric',
      'QB Wins Test',
      'No Conflict Test',
      'Webhook Test Customer'
    )
  );

-- Delete test customers
DELETE FROM customer.customer
WHERE tenant_id = :'test_tenant_id'
  AND display_name IN (
    'Test Sync Electric',
    'AevoFab Push Test',
    'Conflict Test Electric',
    'QB Wins Test',
    'No Conflict Test',
    'Webhook Test Customer'
  );

COMMIT;
```

**Exit psql:**
```sql
\q
```

---

## 🎯 Success Criteria Summary

**Testing is COMPLETE when:**

✅ **Task 16 (OAuth):**
- OAuth flow completes without errors
- Tokens stored encrypted in database
- Connection status shows "active"
- Manual token refresh works
- Celery Beat auto-refresh scheduled

✅ **Task 17 (Sync):**
- QB → AevoFab sync works (pull)
- AevoFab → QB sync works (push)
- Updates sync bidirectionally
- No duplicate records created
- Incremental sync only fetches changed records

✅ **Task 18 (Conflicts):**
- Simultaneous edits trigger conflict (not silent overwrite)
- Conflicts queue with both versions preserved
- "Accept local" pushes to QB successfully
- "Accept remote" updates AevoFab successfully
- One-sided edits sync without triggering conflicts

✅ **Task 19 (Webhooks):**
- Webhook endpoint receives QB notifications
- HMAC signature verification prevents unauthorized access
- Customer create/update events trigger automatic sync
- Webhook events logged for audit trail
- Sync completes within 5 seconds

✅ **Cleanup:**
- All test data removed from AevoFab
- QuickBooks sandbox reset
- Integration disconnected cleanly

---

**Document Version:** 1.0  
**Created:** 2026-03-24  
**Last Updated:** 2026-03-24  
**Status:** Ready for AI-Guided Testing  
**Maintained By:** AevoFab Architecture Team

---

## 💡 Tips for Improving the Testing Process

**For Future Iterations:**

1. **Automated Test Data Generation:** Create a script that pre-populates test customers with known IDs to speed up testing

2. **Screenshot Capture:** Use a tool to auto-capture screenshots of QuickBooks UI during testing for documentation

3. **Test Data Versioning:** Track which QB sandbox company ID is used for each test run to identify environment-specific issues

4. **Performance Logging:** Automatically record timing for each step to build performance baseline

5. **Parallel Testing:** Once stable, consider running multiple test scenarios in parallel (requires separate QB sandbox companies)

6. **Integration with CI/CD:** Convert manual steps to automated E2E tests using Playwright for QB UI automation

7. **Test Run Comparison:** Create a tool to diff test run results across multiple executions to spot regressions

---

**End of Document**
