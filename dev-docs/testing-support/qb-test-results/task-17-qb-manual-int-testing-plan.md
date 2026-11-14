# Tasks 16 & 17: QuickBooks Integration Testing Plan
## OAuth Flow & Customer Sync with Deduplication

**Task References:**
- Phase 3, Task #16 - QuickBooks OAuth 2.0 Flow
- Phase 3, Task #17 - Sync Mapping & Upsert Logic

**Created:** 2026-03-21
**Environment:** Sandbox (Development)
**Purpose:** Complete end-to-end testing of QuickBooks integration from OAuth connection through customer synchronization

---

## 📋 Table of Contents

1. [Prerequisites & Setup](#prerequisites--setup)
2. [Part 1: Task 16 - OAuth Flow Testing](#part-1-task-16---oauth-flow-testing)
3. [Part 2: Task 17 - Customer Sync Testing](#part-2-task-17---customer-sync-testing)
4. [Troubleshooting](#-troubleshooting)
5. [Success Criteria](#-success-criteria-summary)

---

## Prerequisites & Setup

### 📌 QuickBooks Developer Account Configuration

**Before starting, ensure you have:**

- ✅ Intuit Developer Account created at https://developer.intuit.com
- ✅ QuickBooks Sandbox App created (Client ID + Secret obtained)
- ✅ OAuth Redirect URI configured: `https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback`
- ✅ Sandbox Test Company created in QuickBooks Developer Portal
- ✅ Webhook Verifier Token obtained (for Task 19 future testing)

**Required Environment Variables:**

```bash
# backend/.env
QUICKBOOKS_CLIENT_ID=<your_qb_sandbox_client_id>
QUICKBOOKS_CLIENT_SECRET=<your_qb_sandbox_client_secret>
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_REDIRECT_URI=https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback
QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN=<your_qb_webhook_verifier_token>
ENCRYPTION_KEY=<your_fernet_key>
TEST_ENDPOINT_ENABLED=true  # Enables /test endpoints for testing without Cognito
```

**Generate Encryption Key (if needed):**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

### 🛠️ Start All Required Services

Open **6 terminal windows** and start each service:

#### Terminal 1: PostgreSQL Database
```bash
cd backend
docker-compose up -d postgres

# Verify connection
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev -c "SELECT 1;"
# Expected: (1 row)
```

#### Terminal 2: Redis (for Celery)
```bash
cd backend
docker-compose up -d redis

# Verify connection
redis-cli ping
# Expected: PONG
```

#### Terminal 3: Celery Worker
```bash
cd backend
source venv/bin/activate
celery -A core.celery_app worker --loglevel=info

# Expected: [INFO/MainProcess] celery@hostname ready
```

#### Terminal 4: Celery Beat (Token Auto-Refresh)
```bash
cd backend
source venv/bin/activate
celery -A core.celery_app beat --loglevel=info

# Expected: [INFO/MainProcess] beat: Starting...
```

#### Terminal 5: FastAPI Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Expected: Uvicorn running on http://0.0.0.0:8000
```

#### Terminal 6: ngrok Tunnel
```bash
ngrok http 8000 --domain=your-tunnel.ngrok-free.dev

# Expected Output:
# Session Status: online
# Forwarding: https://your-tunnel.ngrok-free.dev -> http://localhost:8000
```

**ngrok Web Interface:** Open http://127.0.0.1:4040 to monitor all webhook requests

---

### ✅ Verify All Services Running

```bash
# Test 1: Backend health check
curl http://localhost:8000/api/v1/hello
# Expected: {"status":"healthy"}
```
# Test 2: ngrok tunnel forwarding
open up in a browser: https://your-tunnel.ngrok-free.dev/docs
# Expected: The API docs page comes up in the browser

```bash
# Test 3: Database connection
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev -c "\dt"
# Expected: List of tables including customer, app_service, integration_credential
```

**✅ All services must be running before proceeding to Task 16 testing.**

---

## Part 1: Task 16 - OAuth Flow Testing

### 🎯 Goal
Establish OAuth 2.0 connection to QuickBooks sandbox with encrypted token storage and automatic refresh.

---

### Step 1: Initiate OAuth Connection

#### 1.1 Open OAuth Connect Endpoint

**Method 1: Browser (Recommended)**
```bash
# Open in your default browser
open http://localhost:8000/api/v1/integrations/quickbooks/connect/test
```

**Method 2: Manual Navigation**
1. Open browser
2. Navigate to: `http://localhost:8000/api/v1/integrations/quickbooks/connect/test`

#### 1.2 Expected: Redirect to QuickBooks

You should be automatically redirected to QuickBooks authorization page:
```
https://appcenter.intuit.com/connect/oauth2?
  client_id=<your_qb_sandbox_client_id>&
  redirect_uri=https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback&
  response_type=code&
  scope=com.intuit.quickbooks.accounting&
  state=<GENERATED_UUID>
```

#### 1.3 Authorize in QuickBooks

1. **Log in** to QuickBooks with your Intuit Developer credentials
2. **Select your Sandbox Test Company** from the dropdown
3. **Click "Connect"** or **"Authorize"**

---

### Step 2: Verify OAuth Callback Success

#### 2.1 Expected: HTML Success Page

After authorizing, QuickBooks redirects back to:
```
https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback?
  code=<AUTHORIZATION_CODE>&
  state=<STATE_TOKEN>&
  realmId=1234567890123456
```

You should see a styled HTML success page showing:
- ✓ **Success checkmark**
- **Company ID:** 1234567890123456
- **Connection Status:** Active
- **Connected At:** [timestamp]
- **Token Expires At:** [~1 hour from now]

#### 2.2 Check ngrok Logs

Open http://127.0.0.1:4040 in a browser and verify:
- You see the `/callback` POST request
- Status code: 200 OK
- Request contains `code`, `state`, and `realmId` parameters

#### 2.3 Check Backend Logs

In Terminal 5 (FastAPI), look for:
```
INFO: Received QuickBooks OAuth callback
INFO: State token validated successfully
INFO: Exchanging authorization code for tokens
INFO: Tokens received and encrypted
INFO: Connection status updated to 'active'
```

---

### Step 3: Verify Database Storage

#### 3.1 Check App Service Record

```bash
# Connect to database
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev
```

```sql
-- Verify QuickBooks app service created
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

-- Expected Output:
-- provider_code: 'quickbooks'
-- external_account_id: '1234567890123456' (realm_id)
-- is_active: true
```

#### 3.2 Check Integration Credential Record

```sql
-- Verify credential with encrypted tokens
SELECT
    id,
    tenant_id,
    app_service_id,
    connection_status,
    expires_at,
    connected_at,
    last_refresh_at,
    initiated_by_user_id,
    created_at
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;

-- Expected Output:
-- connection_status: 'active'
-- expires_at: ~1 hour in future
-- connected_at: recent timestamp
```

#### 3.3 Verify Token Encryption

```sql
-- Check tokens are encrypted (NOT plaintext)
SELECT
    secret_json->>'access_token_encrypted' as access_token,
    secret_json->>'refresh_token_encrypted' as refresh_token,
    secret_json->>'state_token' as state_token
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;

-- Expected:
-- Both tokens should start with "gAAAAA..." (Fernet (AES-128-CBC + HMAC) encryption)
-- Tokens should be ~100+ characters (encrypted)
-- Should NOT be readable JSON or plaintext
```

**✅ Success Criteria:**
- `external_account_id` populated in `app_service` table
- `connection_status = 'active'` in `integration_credential` table
- Tokens encrypted and unreadable

---

### Step 4: Test Connection Status Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"

# Expected Response:
{
  "is_connected": true,
  "connection_status": "active",
  "realm_id": "1234567890123456",
  "company_name": "QuickBooks Online",
  "connected_at": "2026-03-21T20:00:00Z",
  "expires_at": "2026-03-21T21:00:00Z"
}
```

**✅ Success Criteria:**
- `is_connected: true`
- `connection_status: "active"`
- `expires_at` is ~1 hour in the future

---

### Step 5: Test Token Refresh

#### 5.1 Manual Token Refresh (Within 1 Hour)

**Note:** Refresh only works if token expires within 5 minutes OR connection is expired. If your token is fresh (>5 min remaining), you'll get "not_needed" response.

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/refresh/test"

# Possible Responses:

# Response 1: Token is still fresh (>5 min remaining)
{
  "status": "not_needed",
  "expires_at": "2026-03-21T21:00:00Z",
  "seconds_until_expiry": 714
}

# Response 2: Token was refreshed (<5 min remaining or expired)
{
  "status": "refreshed",
  "expires_at": "2026-03-21T22:00:00Z",
  "last_refresh_at": "2026-03-21T21:00:00Z"
}
```

#### 5.2 Force Token Expiration (Testing Only)

To test the refresh logic, manually expire the token:

```sql
-- TESTING ONLY: Manually expire token
UPDATE integration_credential
SET expires_at = NOW() - INTERVAL '1 hour',
    connection_status = 'expired'
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
);
```

```bash
# Now check status (should show expired)
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"
# Expected: "is_connected": false, "connection_status": "expired"

# NOTE: Refresh will fail if connection_status = 'expired'
# You must re-connect via OAuth (repeat Step 1)
```

**⚠️ Important:** The refresh endpoint requires `connection_status = 'active'`. If status is `'expired'`, you must re-authenticate via OAuth (Step 1).

---

### Step 6: Test Automatic Token Refresh (Celery Beat)

#### 6.1 Monitor Celery Beat Scheduler

Celery Beat runs the `refresh_quickbooks_tokens` task every **30 minutes**.

In Terminal 4 (Celery Beat), you should see:
```
[2026-03-21 20:30:00,000: INFO/MainProcess] Scheduler: Sending due task refresh-quickbooks-tokens
[2026-03-21 20:30:00,100: INFO/MainProcess] Task refresh_quickbooks_tokens[<uuid>] sent
```

#### 6.2 Monitor Celery Worker Execution

In Terminal 3 (Celery Worker), you should see:
```
[2026-03-21 20:30:00,200: INFO/ForkPoolWorker-1] Task refresh_quickbooks_tokens[<uuid>] received
[2026-03-21 20:30:00,300: INFO/ForkPoolWorker-1] Checking for tokens expiring within 5 minutes...
[2026-03-21 20:30:00,400: INFO/ForkPoolWorker-1] Found 0 credential(s) to refresh (tokens still fresh)
[2026-03-21 20:30:00,500: INFO/ForkPoolWorker-1] Task refresh_quickbooks_tokens[<uuid>] succeeded
```

**Note:** Tokens only refresh if they expire within 5 minutes. If your token is fresh, the task will complete without refreshing.

#### 6.3 Verify Auto-Refresh Works (Wait 55+ Minutes)

To verify auto-refresh actually works:

1. **Wait 55 minutes** after initial OAuth connection
2. Check Celery Worker logs - should show refresh at next 30-min interval
3. Verify database shows updated `last_refresh_at`:

```sql
SELECT
    connection_status,
    expires_at,
    last_refresh_at,
    EXTRACT(EPOCH FROM (expires_at - NOW())) / 60 as minutes_until_expiry
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;

-- After auto-refresh:
-- last_refresh_at: recent timestamp (within last 30 min)
-- minutes_until_expiry: ~55-60 (reset to 1 hour)
```

**✅ Success Criteria:**
- Celery Beat triggers task every 30 minutes
- Tokens auto-refresh 5 minutes before expiration
- No manual intervention needed

---

### Step 7: Test Disconnect Flow

```bash
curl -X DELETE "http://localhost:8000/api/v1/integrations/quickbooks/disconnect/test"

# Expected Response:
{
  "status": "disconnected",
  "disconnected_at": "2026-03-21T20:30:00Z",
  "message": "QuickBooks integration disconnected successfully"
}
```

#### 7.1 Verify Database Update

```sql
SELECT
    connection_status,
    disconnected_at,
    connected_at
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;

-- Expected:
-- connection_status: 'disconnected'
-- disconnected_at: recent timestamp
```

#### 7.2 Verify Status Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"

# Expected Response:
{
  "is_connected": false,
  "connection_status": "disconnected",
  "realm_id": "1234567890123456",
  "company_name": "QuickBooks Online",
  "connected_at": "2026-03-21T20:00:00Z",
  "expires_at": "2026-03-21T21:00:00Z",
  "disconnected_at": "2026-03-21T20:30:00Z"
}
```

---

### ✅ Task 16 Complete Checklist

- [ ] OAuth flow completes without errors
- [ ] HTML success page displays after authorization
- [ ] Tokens stored encrypted in database (start with "gAAAAA...")
- [ ] `external_account_id` (realm_id) populated in `app_service` table
- [ ] Connection status shows "active" via `/status/test` endpoint
- [ ] Manual token refresh endpoint works (or returns "not_needed")
- [ ] Celery Beat runs refresh task every 30 minutes
- [ ] Disconnect endpoint sets status to "disconnected"
- [ ] State token validation prevents CSRF attacks
- [ ] Tenant isolation enforced (verified in database queries)

**⚠️ Before proceeding to Task 17:** Ensure your QuickBooks connection is **active** (not expired or disconnected). Re-run Step 1 if needed.

---

## Part 2: Task 17 - Customer Sync Testing

### 🎯 Goal
Verify bidirectional customer synchronization between QuickBooks and AevoFab with deduplication via `integration_sync_mapping` table.

### ⚠️ Prerequisites Check

Before starting Task 17 tests, verify Task 16 is complete:

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"

# MUST show:
# {
#   "is_connected": true,
#   "connection_status": "active",
#   "realm_id": "1234567890123456"
# }

# If NOT active, re-run Task 16 Step 1 (OAuth connect)
```

---

---

## 🧪 Test Scenarios

### Test 1: QuickBooks → AevoFab Customer Sync (Pull)
**Goal:** Verify that customers created in QuickBooks sync to AevoFab database without duplicates

#### Step 1.1: Create Customer in QuickBooks Sandbox

1. **Log into QuickBooks Sandbox:**
   - URL: https://app.sandbox.qbo.intuit.com
   - Use your Intuit Developer credentials
   - Select your sandbox test company (Company ID: `1234567890123456`)

2. **Create a Test Customer:**
   - Navigate to: **Sales** → **Customer Hub** → **Customers** → **New Customer**
   - Fill in customer details:
     ```
     Display Name: "Test Electric Co"
     Company Name: "Test Electric Company LLC"
     Email: test@electricco.example.com
     Phone: (555) 123-4567
     Billing Address:
       Street: 123 Main St
       City: Austin
       State: TX
       ZIP: 78701
     ```
   - Click **Save**

3. **Note the Customer ID:**
   - After saving, QuickBooks will show the customer page
   - Actual page was: https://sandbox.qbo.intuit.com/app/customerdetail?nameId=58
   - Look at the URL: `https://app.sandbox.qbo.intuit.com/app/customerdetail?nameId=67`
   - The `nameId=67` is the QuickBooks Customer ID (external_id)
   - **Record this for verification:** `QB_CUSTOMER_ID=67`

#### Step 1.2: Trigger Manual Customer Sync

```bash
# Method 1: Sync all customers (incremental)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test" \
  -H "Content-Type: application/json"

# Expected Response:
# {
#   "status": "success",
#   "synced_count": 1,
#   "message": "Synced 1 customer(s) from QuickBooks"
# }

# Method 2: Sync specific customer by ID (future enhancement)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/67/test" \
  -H "Content-Type: application/json"
```

**Watch Celery Worker Logs:**
```
[INFO] Starting customer sync for tenant <tenant_id>
[INFO] Fetching customers from QuickBooks API...
[INFO] Found 1 customer(s) to sync
[INFO] Processing customer: Test Electric Co (ID: 67)
[INFO] No existing mapping found - creating new customer
[INFO] Created customer in AevoFab database
[INFO] Created sync mapping record
[INFO] Customer sync completed successfully
```

#### Step 1.3: Verify Customer in AevoFab Database

```sql
-- Connect to database
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev

-- Verify customer was created
SELECT 
    id,
    display_name,
    company_name,
    email_primary,
    phone_primary,
    created_at,
    updated_at
FROM customer
WHERE display_name = 'Test Electric Co'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: 1 row with matching data
-- Copy the customer.id (UUID) for next verification
```

#### Step 1.4: Verify Sync Mapping Record

```sql
-- Check integration_sync_mapping table
SELECT 
    ism.id,
    ism.tenant_id,
    ism.entity_id,
    ism.entity_type_code,
    ism.external_id,
    ism.external_version_token,
    ism.last_synced_at,
    c.display_name
FROM integration_sync_mapping ism
JOIN customer c ON c.id = ism.entity_id
WHERE ism.entity_type_code = 'customer'
  AND ism.external_id = '67'  -- Replace with your QB Customer ID
ORDER BY ism.created_at DESC
LIMIT 1;

-- Expected Output:
-- entity_id: <UUID from customer table>
-- entity_type_code: 'customer'
-- external_id: '67' (QB Customer ID)
-- external_version_token: '0' (SyncToken from QB)
-- last_synced_at: <recent timestamp>
```

**✅ Success Criteria:**
- Customer exists in `customer` table with correct data
- Mapping exists in `integration_sync_mapping` table
- `external_id` matches QuickBooks Customer ID
- `external_version_token` is populated (SyncToken)

---

### Test 2: Duplicate Prevention (Deduplication)
**Goal:** Verify that re-syncing the same customer does NOT create duplicates

#### Step 2.1: Trigger Sync Again (Same Customer)

```bash
# Sync the same customer again
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test" \
  -H "Content-Type: application/json"

# Expected Response:
# {
#   "status": "success",
#   "synced_count": 1,
#   "message": "Synced 1 customer(s) from QuickBooks"
# }
```

#### Step 2.2: Verify NO Duplicate Created

```sql
-- Count customers with same display name
SELECT 
    display_name,
    COUNT(*) as count,
    array_agg(id::text) as customer_ids
FROM customer
WHERE display_name = 'Test Electric Co'
GROUP BY display_name;

-- Expected: count = 1 (NOT 2)

-- Verify only ONE mapping exists
SELECT 
    external_id,
    COUNT(*) as mapping_count
FROM integration_sync_mapping
WHERE external_id = '67'  -- Replace with your QB Customer ID
GROUP BY external_id;

-- Expected: mapping_count = 1
```

**✅ Success Criteria:**
- Only ONE customer record exists
- Only ONE sync mapping record exists
- Existing customer was updated (not duplicated)

---

### Test 3: Update Detection (QB → AevoFab)
**Goal:** Verify that changes in QuickBooks sync to AevoFab

#### Step 3.1: Edit Customer in QuickBooks

1. **In QuickBooks Sandbox:**
   - Navigate to the "Test Electric Co" customer
   - Click **Edit**
   - Change:
     ```
     Phone: (555) 999-8888
     Email: newemail@electricco.example.com
     ```
   - Click **Save**

2. **Note:** QuickBooks will increment the `SyncToken` (version) from `0` to `1`

#### Step 3.2: Trigger Sync

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"
```

#### Step 3.3: Verify Updates in AevoFab

```sql
-- Check customer was updated (not duplicated)
SELECT 
    id,
    display_name,
    email_primary,
    phone_primary,
    updated_at
FROM customer
WHERE display_name = 'Test Electric Co'
ORDER BY updated_at DESC;

-- Expected:
-- email_primary: 'newemail@electricco.example.com'
-- phone_primary: '(555) 999-8888'
-- updated_at: <recent timestamp after edit>

-- Verify SyncToken was updated in mapping
SELECT 
    external_id,
    external_version_token,
    last_synced_at
FROM integration_sync_mapping
WHERE external_id = '67';

-- Expected:
-- external_version_token: '1' (incremented from '0')
-- last_synced_at: <recent timestamp>
```

**✅ Success Criteria:**
- Customer email and phone updated to new values
- No duplicate customer created
- `external_version_token` incremented to `1`
- `last_synced_at` updated

---

### Test 4: AevoFab → QuickBooks Customer Sync (Push)
**Goal:** Verify that customers created in AevoFab sync to QuickBooks

#### Step 4.1: Create Customer Directly in AevoFab Database

```bash
# Create customer via API (using test endpoint)
curl -X POST "http://localhost:8000/api/v1/customers/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "AevoFab Test Customer",
    "company_name": "AevoFab Electric LLC",
    "email_primary": "aevofab@test.com",
    "phone_primary": "(555) 777-6666"
  }'

# Response will include the customer ID
# Record it: AEVOFAB_CUSTOMER_ID=<uuid>
# 3-21-26 test result:
{
  "id": "ec75f0ab-9537-4430-9a55-25dde8993486",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "type": "person",
  "display_name": "AevoFab Test Customer",
  "first_name": null,
  "last_name": null,
  "company_name": "AevoFab Electric LLC",
  "email": null,
  "mobile_phone": null,
  "is_active": true
}
```

#### Step 4.2: Sync Customer to QuickBooks

```bash
# Sync specific customer to QuickBooks
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<CUSTOMER_ID>/test"

curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/ec75f0ab-9537-4430-9a55-25dde8993486/test"

# Expected Response:
# {
#   "status": "success",
#   "quickbooks_id": "68",
#   "message": "Customer synced to QuickBooks successfully"
# }
```

#### Step 4.3: Verify Customer in QuickBooks Sandbox

1. **Log into QuickBooks Sandbox**
2. Navigate to **Sales** → **Customers**
3. Search for "AevoFab Test Customer"
4. Verify customer details match:
   - Display Name: `AevoFab Test Customer`
   - Company: `AevoFab Electric LLC`
   - Email: `aevofab@test.com`
   - Phone: `(555) 777-6666`

#### Step 4.4: Verify Sync Mapping Created

```sql
-- Check mapping was created for the new customer
SELECT 
    ism.id,
    ism.entity_id,
    ism.external_id,
    ism.external_version_token,
    c.display_name
FROM integration_sync_mapping ism
JOIN customer c ON c.id = ism.entity_id
WHERE c.display_name = 'AevoFab Test Customer';

-- Expected:
-- external_id: '68' (QB-assigned Customer ID)
-- external_version_token: '0' (initial SyncToken)
```

**✅ Success Criteria:**
- Customer appears in QuickBooks sandbox
- All fields match AevoFab data
- Mapping record created with correct `external_id`

---

### Test 5: Bidirectional Update (AevoFab → QB)
**Goal:** Verify that updates in AevoFab push to QuickBooks

#### Step 5.1: Update Customer in AevoFab

```bash
# Update the customer we created in Test 4
curl -X PATCH "http://localhost:8000/api/v1/customers/<CUSTOMER_ID>/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "AevoFab Test Customer",
    "mobile_phone": "(555) 111-2222",
    "email": "updated@aevofab.example.com"
  }'

curl -X PATCH "http://localhost:8000/api/v1/customers/ec75f0ab-9537-4430-9a55-25dde8993486/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "AevoFab Test Customer",
    "mobile_phone": "(555) 111-2222",
    "email": "updated@aevofab.example.com"
  }'
```

#### Step 5.2: Sync Update to QuickBooks

```bash
# Sync the updated customer to QB
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<CUSTOMER_ID>/test"

curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/ec75f0ab-9537-4430-9a55-25dde8993486/test"

# Expected Response:
# {
#   "status": "success",
#   "quickbooks_id": "68",
#   "message": "Customer updated in QuickBooks successfully"
# }
```

#### Step 5.3: Verify Update in QuickBooks

1. **In QuickBooks Sandbox:**
   - Navigate to "AevoFab Test Customer"
   - Verify updated fields:
     - Phone: `(555) 111-2222`
     - Email: `updated@aevofab.example.com`

#### Step 5.4: Verify SyncToken Incremented

```sql
-- Check that SyncToken was updated
SELECT 
    external_id,
    external_version_token,
    last_synced_at
FROM integration_sync_mapping
WHERE entity_id = '<CUSTOMER_ID>';

-- Expected:
-- external_version_token: '1' (incremented from '0')
-- last_synced_at: <recent timestamp>
```

**✅ Success Criteria:**
- QuickBooks customer shows updated phone and email
- `external_version_token` incremented to `1`
- No errors in sync logs

---

### Test 6: Incremental Sync (Timestamp Filtering)
**Goal:** Verify that sync only fetches changed records (not full resync)

#### Step 6.1: Note Initial Sync State

```sql
-- Get timestamp of last sync
SELECT MAX(last_synced_at) as last_sync
FROM integration_sync_mapping
WHERE entity_type_code = 'customer';

-- Record this timestamp: LAST_SYNC_TIME=<timestamp>
--- LAST_SYNC_TIME=`2026-03-21 21:13:00.783424`
```

#### Step 6.2: Create New Customer in QuickBooks

1. **In QuickBooks Sandbox:**
   - Create another customer: "Incremental Test Co"
   - Note the Customer ID (e.g., `60`)

#### Step 6.3: Trigger Incremental Sync

```bash
# Sync customers (should only fetch new/updated since last sync)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"

# Expected Response:
# {
#   "status": "success",
#   "synced_count": 1,
#   "message": "Synced 1 customer(s) from QuickBooks"
# }
```

**Watch Celery Worker Logs for Timestamp Filter:**
```
[INFO] Fetching customers modified since: 2026-03-21T18:30:00Z
[INFO] Found 1 customer(s) to sync (incremental)
```

#### Step 6.4: Verify Only New Customer Synced

```sql
-- Check only the NEW customer was processed
SELECT 
    c.display_name,
    ism.last_synced_at,
    ism.last_synced_at > '<LAST_SYNC_TIME>' as synced_recently
FROM customer c
JOIN integration_sync_mapping ism ON ism.entity_id = c.id
WHERE c.display_name IN ('Test Electric Co', 'AevoFab Test Customer', 'Incremental Test Co')
ORDER BY ism.last_synced_at DESC;

-- Expected:
-- Only 'Incremental Test Co' should have synced_recently = true
```

**✅ Success Criteria:**
- Sync only fetched 1 customer (not all 3)
- Timestamp filter used in QuickBooks API query
- Existing customers not re-processed

---

### Test 7: Multi-Tenant Isolation
**Goal:** Verify that tenants cannot see or sync each other's customers

#### Step 7.1: Create Second Test Tenant (Optional)

```bash
# If you have a second test tenant, connect it to a different QB sandbox company
# Otherwise, verify isolation via database queries
```

#### Step 7.2: Verify Tenant Isolation in Queries

```sql
-- Get the current test tenant_id
SELECT tenant_id, display_name
FROM customer
WHERE display_name = 'Test Electric Co';

-- Record: TEST_TENANT_ID=<uuid>

-- Verify sync mapping is filtered by tenant
SELECT 
    ism.tenant_id,
    COUNT(*) as mapping_count
FROM integration_sync_mapping ism
GROUP BY ism.tenant_id;

-- Expected: Only one tenant_id (your test tenant)

-- Verify QuickBooks connection is tenant-specific
SELECT 
    ic.tenant_id,
    as2.external_account_id,
    ic.connection_status
FROM integration_credential ic
JOIN app_service as2 ON as2.id = ic.app_service_id
WHERE as2.provider_code = 'quickbooks';

-- Expected: Only one connection per tenant
```

**✅ Success Criteria:**
- All customers filtered by `tenant_id`
- All mappings filtered by `tenant_id`
- Cannot sync customers from other tenants

---

### Test 8: Error Handling & Edge Cases

#### Test 8.1: Invalid QuickBooks Customer ID

```bash
# Try to sync non-existent customer
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/99999/test"

# Expected Response (404):
# {
#   "detail": "Customer not found in QuickBooks: 99999"
# }
```

#### Test 8.2: Expired OAuth Token

```sql
-- Manually expire the token
UPDATE integration_credential
SET expires_at = NOW() - INTERVAL '1 hour'
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
);
```

```bash
# Try to sync (should auto-refresh token)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"

# Expected: Sync succeeds after automatic token refresh
```

```sql
-- Verify token was refreshed
SELECT 
    expires_at,
    last_refresh_at,
    expires_at > NOW() as is_valid
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
);

-- Expected: is_valid = true, last_refresh_at = recent
```

#### Test 8.3: Disconnected QuickBooks

```bash
# Disconnect QuickBooks
curl -X DELETE "http://localhost:8000/api/v1/integrations/quickbooks/disconnect/test"

# Try to sync (should fail gracefully)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"

# Expected Response (400):
# {
#   "detail": "QuickBooks integration is not connected"
# }
```

```bash
# Reconnect for further testing
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/connect/test"
# Follow OAuth flow again
```

**✅ Success Criteria:**
- Invalid IDs return 404 errors (not 500)
- Expired tokens auto-refresh transparently
- Disconnected state prevents syncs with clear error message

---

## 🔍 Verification Queries

### Complete System Health Check

```sql
-- 1. Check QuickBooks connection status
SELECT 
    as2.tenant_id,
    as2.provider_code,
    as2.external_account_id as realm_id,
    ic.connection_status,
    ic.expires_at,
    ic.last_refresh_at,
    EXTRACT(EPOCH FROM (ic.expires_at - NOW())) / 60 as minutes_until_expiry
FROM app_service as2
JOIN integration_credential ic ON ic.app_service_id = as2.id
WHERE as2.provider_code = 'quickbooks'
ORDER BY ic.created_at DESC;

-- Expected: connection_status = 'active', minutes_until_expiry > 5

-- 2. Check customer sync mappings
SELECT 
    ism.entity_type_code,
    COUNT(*) as total_mappings,
    COUNT(DISTINCT ism.external_id) as unique_qb_ids,
    MAX(ism.last_synced_at) as most_recent_sync
FROM integration_sync_mapping ism
WHERE ism.entity_type_code = 'customer'
GROUP BY ism.entity_type_code;

-- Expected: total_mappings >= 3 (from tests above)

-- 3. Check for orphaned mappings (no matching customer)
SELECT 
    ism.id,
    ism.external_id,
    ism.entity_id
FROM integration_sync_mapping ism
LEFT JOIN customer c ON c.id = ism.entity_id
WHERE ism.entity_type_code = 'customer'
  AND c.id IS NULL;

-- Expected: 0 rows (no orphans)

-- 4. Check for customers without mappings
SELECT 
    c.id,
    c.display_name,
    c.created_at
FROM customer c
LEFT JOIN integration_sync_mapping ism ON ism.entity_id = c.id AND ism.entity_type_code = 'customer'
WHERE ism.id IS NULL;

-- Expected: 0 rows (all customers should have mappings after sync)
```

---

## 📊 Performance Benchmarks

### Expected Sync Performance

| Operation | Records | Expected Time | Acceptable Max |
|-----------|---------|---------------|----------------|
| Initial customer sync | 10 | < 5 seconds | 10 seconds |
| Initial customer sync | 100 | < 30 seconds | 60 seconds |
| Incremental sync | 1 new | < 2 seconds | 5 seconds |
| Single customer push | 1 | < 3 seconds | 5 seconds |
| Token refresh | - | < 2 seconds | 5 seconds |

### Performance Test

```bash
# Time a full customer sync
time curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"

# Expected: < 5 seconds for small dataset
```

---

## 🐛 Troubleshooting

### Issue 1: Customer Not Syncing from QB

**Symptoms:**
- Sync completes but customer not in AevoFab database

**Debug Steps:**
```bash
# Check Celery worker logs for errors
# Look for QuickBooks API responses

# Verify customer exists in QB
# Log into QB sandbox and confirm customer is visible
```

**Common Causes:**
- QuickBooks API permissions issue (check scopes)
- Customer marked as inactive in QB
- Sync filtering by timestamp excluded customer

---

### Issue 2: Duplicate Customers Created

**Symptoms:**
- Multiple customer records with same name

**Debug Steps:**
```sql
-- Check for duplicate mappings
SELECT 
    external_id,
    COUNT(*) as count,
    array_agg(entity_id::text) as customer_ids
FROM integration_sync_mapping
WHERE entity_type_code = 'customer'
GROUP BY external_id
HAVING COUNT(*) > 1;
```

**Solution:**
- Delete duplicate customer manually
- Fix mapping record to point to correct customer
- Re-run sync

---

### Issue 3: SyncToken Mismatch (Conflict)

**Symptoms:**
- Error: "QuickBooks returned 400: Stale SyncToken"

**Explanation:**
- Another user/system modified customer in QB
- AevoFab has outdated SyncToken

**Solution:**
```bash
# Force pull from QuickBooks (refresh SyncToken)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"

# This will update the SyncToken to latest version
```

---

## ✅ Complete Test Checklist

Use this checklist to track your testing progress:

### Prerequisites
- [ ] Task 16 OAuth flow working
- [ ] QuickBooks connection active
- [ ] All services running (Postgres, Redis, Celery, FastAPI, ngrok)

### Test 1: QB → AevoFab Sync
- [ ] Created customer in QuickBooks sandbox
- [ ] Triggered manual sync
- [ ] Verified customer in AevoFab database
- [ ] Verified mapping record created
- [ ] Verified `external_id` and `external_version_token`

### Test 2: Duplicate Prevention
- [ ] Re-synced same customer
- [ ] Verified NO duplicate created
- [ ] Verified customer was updated (not created)

### Test 3: Update Detection (QB → AevoFab)
- [ ] Edited customer in QuickBooks
- [ ] Synced changes to AevoFab
- [ ] Verified updates reflected in database
- [ ] Verified `external_version_token` incremented

### Test 4: AevoFab → QB Sync
- [ ] Created customer in AevoFab
- [ ] Synced to QuickBooks
- [ ] Verified customer in QB sandbox
- [ ] Verified mapping created

### Test 5: Bidirectional Update
- [ ] Updated customer in AevoFab
- [ ] Synced to QuickBooks
- [ ] Verified update in QB sandbox
- [ ] Verified `external_version_token` incremented

### Test 6: Incremental Sync
- [ ] Created new customer in QB
- [ ] Triggered incremental sync
- [ ] Verified only new customer synced
- [ ] Verified timestamp filtering worked

### Test 7: Tenant Isolation
- [ ] Verified customers filtered by `tenant_id`
- [ ] Verified mappings filtered by `tenant_id`
- [ ] Verified no cross-tenant data leakage

### Test 8: Error Handling
- [ ] Tested invalid customer ID (404 error)
- [ ] Tested expired token (auto-refresh)
- [ ] Tested disconnected state (clear error)

---

## 📝 Test Report Template

After completing all tests, document your results:

```markdown
# Task 17 Test Results

**Tester:** [Your Name]
**Date:** [YYYY-MM-DD]
**Environment:** Sandbox
**QuickBooks Company ID:** [Realm ID]

## Test Summary
- Total Tests: 8
- Passed: [X/8]
- Failed: [X/8]
- Skipped: [X/8]

## Detailed Results

### Test 1: QB → AevoFab Sync
- Status: [PASS/FAIL]
- Notes: [Any observations]

### Test 2: Duplicate Prevention
- Status: [PASS/FAIL]
- Notes: [Any observations]

[... continue for all tests ...]

## Issues Found
1. [Issue description]
   - Severity: [Low/Medium/High/Critical]
   - Steps to reproduce: [...]

## Performance Metrics
- Full sync (10 customers): [X] seconds
- Incremental sync (1 customer): [X] seconds
- Push to QB: [X] seconds

## Recommendations
[Any suggestions for improvements]
```

---

## 🎯 Success Criteria Summary

Task 17 is considered **complete** when ALL of the following are verified:

1. ✅ Customers created in QuickBooks sync to AevoFab database
2. ✅ Customers created in AevoFab sync to QuickBooks
3. ✅ No duplicate records created after multiple sync cycles
4. ✅ Updates in either system sync bidirectionally
5. ✅ `integration_sync_mapping` table has correct `external_id` and `external_version_token`
6. ✅ Incremental sync only fetches changed records (timestamp filtering)
7. ✅ Tenant isolation enforced (no cross-tenant data)
8. ✅ Error handling works correctly (invalid IDs, expired tokens, disconnected state)

---

## 📚 Reference Documentation

- **Implementation Plan:** `task-17-sync-mapping-impl-plan.md`
- **Roadmap:** `phase-2-5-implementation-roadmap.md` (Lines 1036-1337)
- **Task 16 Testing:** `quickbooks-oauth-sandbox-testing.md`
- **Sync Service:** `backend/services/quickbooks_sync.py`
- **Integration Routes:** `backend/api/routes/integrations.py`
- **QuickBooks API Docs:** https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/customer

---

## 🚀 Next Steps After Task 17

Once all Task 17 tests pass, proceed to:

### ➡️ Task 18: Conflict Detection & Resolution

**See dedicated testing guide:** `task-18-manual-conflict-testing-plan.md`

**What You'll Test:**
- ✅ Simultaneous edits in both QuickBooks and AevoFab trigger conflicts
- ✅ Conflicts queue correctly for manual resolution
- ✅ Three resolution strategies: `accept_local`, `accept_remote`, `merge`
- ✅ One-sided edits sync normally without triggering conflicts
- ✅ Error handling (404, 400, 422)
- ✅ Reset/cleanup procedures for re-testing

**Key Concept:**
Conflict detection compares **both** version tokens:
- **QuickBooks `SyncToken`** (external_version_token)
- **AevoFab `updated_at`** (internal_version_token)

If **both** changed since last sync → **CONFLICT** (manual resolution required)
If only **one** changed → normal sync (no conflict)

**Quick Start:**
```bash
# Verify Tasks 16 & 17 complete
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"

# Run first conflict test (see Task 18 guide for details)
# 1. Create customer in AevoFab, sync to QB
# 2. Edit in AevoFab (change email)
# 3. Edit same customer in QB (change email + phone)
# 4. Trigger sync → conflict detected
# 5. Resolve via API with chosen strategy
```

---

### ➡️ Task 19: Webhook Handler (Future)

Once Task 18 is complete:
- Test real-time sync via QuickBooks webhooks
- Verify HMAC signature validation
- Test webhook-triggered incremental syncs
- Test webhook-triggered conflict detection

---

**Created:** 2026-03-21
**Last Updated:** 2026-03-22
**Status:** Ready for Manual Testing (Tasks 16, 17, 18)
**Maintained By:** AevoFab Architecture Team
