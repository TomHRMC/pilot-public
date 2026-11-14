# QuickBooks OAuth 2.0 Sandbox Testing Guide

**Task Reference:** Phase 3, Task #16 - QuickBooks OAuth Flow  
**Created:** 2026-03-20  
**Environment:** Sandbox (Development)  
**Purpose:** Manual testing of QuickBooks OAuth integration via ngrok tunnel

---

## Prerequisites

### 1. QuickBooks Developer Account Setup

**Required:**
- ✅ Intuit Developer Account created
- ✅ QuickBooks Sandbox App created (Client ID + Secret obtained)
- ✅ OAuth Redirect URI configured: `https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback`
- ✅ Sandbox Test Company created in QuickBooks Developer Portal
- ✅ `TEST_ENDPOINT_ENABLED=true` set in backend `.env` file to enable the `/test` endpoints

**Verify Configuration:**
```bash
# Check .env file contains:
QUICKBOOKS_CLIENT_ID=<your_client_id>
QUICKBOOKS_CLIENT_SECRET=<your_client_secret>
QUICKBOOKS_REDIRECT_URI=https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_AUTH_URL=https://appcenter.intuit.com/connect/oauth2
QUICKBOOKS_TOKEN_URL=https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer
ENCRYPTION_KEY=<your_fernet_key>
```
```bash
# .env file contains the following as of 3-20-2026
API_BASE_URL=https://your-tunnel.ngrok-free.dev
QUICKBOOKS_CLIENT_ID=<your_qb_sandbox_client_id>
QUICKBOOKS_CLIENT_SECRET=<your_qb_sandbox_client_secret>
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_REDIRECT_URI=https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback
QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN=<your_qb_webhook_verifier_token>
ENCRYPTION_KEY=<your_fernet_key>
QUICKBOOKS_TEST_REALM_ID=<your_qb_test_realm_id>
```

### 2. ngrok Setup

**Static Domain:** `your-tunnel.ngrok-free.dev`

**Installation Check:**
```bash
# Verify ngrok is installed
ngrok version

# Expected output: ngrok version 3.x.x
```

---

## Testing Workflow

### Step 1: Start Required Services

#### 1.1 Start PostgreSQL Database
```bash
# If using Docker
cd backend
docker-compose up -d postgres

# Verify connection
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev -c "SELECT 1;"
```

#### 1.2 Start Redis (for Celery)
```bash
# If using Docker
docker-compose up -d redis

# Verify connection
redis-cli ping
# Expected: PONG
```

#### 1.3 Start Celery Worker
```bash
cd backend
source venv/bin/activate
celery -A core.celery_app worker --loglevel=info
```

#### 1.4 Start Celery Beat (Token Refresh Scheduler)
```bash
# In a new terminal
cd backend
source venv/bin/activate
celery -A core.celery_app beat --loglevel=info
```

#### 1.5 Start FastAPI Backend
```bash
# In a new terminal
cd backend
source venv/bin/activate
# command from AI engine
# uvicorn app.main:app --reload --port 8000
# my actual command
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 
```

**Verify Backend is Running:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

#### 1.6 Start ngrok Tunnel
```bash
# In a new terminal
ngrok http 8000 --domain=your-tunnel.ngrok-free.dev
```

**Expected Output:**
```
Session Status                online
Account                       <your_account> (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://your-tunnel.ngrok-free.dev -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Verify ngrok is Working:**
```bash
# this has NOT been implemented yet, look below
curl https://your-tunnel.ngrok-free.dev/health
# Expected: {"status":"healthy"}
```

```bash
# actually we have not implemented health yet, but do have hello
curl https://your-tunnel.ngrok-free.dev/api/v1/hello
# Expected: {"greeting":"Hello from the FastAPI backend!"}
```

---

### Step 2: Prepare Test User & Tenant

You need an authenticated user to initiate the OAuth flow.

#### 2.1 Create Test Tenant & User (if not exists)
```bash
# Option 1: Use existing test endpoint
curl -X POST http://localhost:8000/test/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "mike@test-contractor.example.com",
    "password": "TestPass123!",
    "tenant_name": "Mike Test Contractor LLC"
  }'
```

#### 2.2 Obtain JWT Token
```bash
# Note: You'll need to implement a test login endpoint or use Cognito
# For now, manually extract JWT from browser after login
```

**FOLLOW UP:** We do not have a local sign up endpoint yet, nor have we setup Cognito. TODO!!!

---

### Step 3: Test OAuth Flow

#### 3.1 Initiate OAuth Connection

**Note on Test Endpoints:**
Since the main application relies on AWS Cognito which is not fully set up yet, we will use the test endpoints (appended with `/test`). These endpoints bypass the standard JWT authentication, injecting a predefined `TestUserContext`. Ensure `TEST_ENDPOINT_ENABLED=true` is in your `.env`.

**Method 1: Browser (Recommended for Manual Testing)**

1. Open browser and navigate to the test connection endpoint:
   ```
   http://localhost:8000/api/v1/integrations/quickbooks/connect/test
   ```

2. You should be redirected to QuickBooks authorization page:
   ```
   https://appcenter.intuit.com/connect/oauth2?
     client_id=<YOUR_CLIENT_ID>&
     redirect_uri=https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback&
     response_type=code&
     scope=com.intuit.quickbooks.accounting&
     state=<GENERATED_UUID>
   ```

3. **Select your Sandbox Test Company** from the dropdown
4. Click **"Connect"** or **"Authorize"**

**Method 2: curl without JWT Token (Test Endpoint)**

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/connect/test" \
  -v

# Expected: 302 Redirect to QuickBooks
```

#### 3.2 Verify Callback Handling

After authorizing in QuickBooks, you should be redirected back to:
```
https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback?
  code=<AUTHORIZATION_CODE>&
  state=<STATE_TOKEN>&
  realmId=<COMPANY_ID>
```

**Note:** The `/callback` endpoint does NOT require JWT authentication (it's called directly by QuickBooks). It validates the `state` token instead for CSRF protection.

**Expected Success Page (Dev/Test Environments):**

In development/test environments, you'll see a styled HTML success page showing:
- ✓ Success checkmark
- Company ID (realmId)
- Connection status (Active)
- Connected timestamp
- Token expiration time

**Check ngrok Web Interface:**
1. Open http://127.0.0.1:4040 in browser
2. You should see the callback request logged
3. Inspect request headers and query parameters

**Expected Backend Logs:**
```
INFO: Received QuickBooks OAuth callback
INFO: State token validated successfully
INFO: Exchanging authorization code for tokens
INFO: Tokens received and encrypted
INFO: Connection status updated to 'active'
```

#### 3.3 Verify Database Storage

```sql
-- Connect to database
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev

-- Check app_service record
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

-- Expected: 1 row with external_account_id = <realmId>

-- Check integration_credential record
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

-- Expected: 1 row with connection_status = 'active'

-- Verify tokens are encrypted (should be unreadable)
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

-- Expected: Both tokens should start with "gAAAAA..." (Fernet encrypted)
```

---

### Step 4: Test Connection Status Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"

# Expected Response:
{
  "is_connected": true,
  "connection_status": "active",
  "connected_at": "2026-03-20T18:00:00Z",
  "external_account_id": "1234567890",
  "expires_at": "2026-03-20T19:00:00Z",
  "company_name": "QuickBooks Online",
  "realm_id": "<your_qb_test_realm_id>"
}
```

---

### Step 5: Test Token Refresh (Manual)

#### 5.1 Trigger Manual Token Refresh

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/refresh/test"

# Expected Response:
{
  "status": "refreshed",
  "expires_at": "2026-03-20T20:00:00Z",
  "last_refresh_at": "2026-03-20T19:00:00Z"
}
```

#### 5.2 Verify Database Update

```sql
SELECT 
    connection_status,
    expires_at,
    last_refresh_at,
    connected_at
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;

-- Expected: last_refresh_at should be updated to current time
-- Expected: expires_at should be ~1 hour in the future
```

---

### Step 6: Test Automatic Token Refresh (Celery Beat)

**Note:** QuickBooks access tokens expire after **1 hour**. The Celery Beat task runs every **30 minutes** and refreshes tokens that expire within **5 minutes**.

#### 6.1 Monitor Celery Beat Logs

In the terminal running Celery Beat, you should see:
```
[2026-03-20 18:30:00,000: INFO/MainProcess] Scheduler: Sending due task refresh-quickbooks-tokens
[2026-03-20 18:30:00,100: INFO/MainProcess] Task refresh_quickbooks_tokens[<uuid>] received
```

#### 6.2 Monitor Celery Worker Logs

In the terminal running Celery Worker, you should see:
```
[2026-03-20 18:30:00,200: INFO/ForkPoolWorker-1] Task refresh_quickbooks_tokens[<uuid>]: 
Checking for tokens expiring within 5 minutes...
[2026-03-20 18:30:00,300: INFO/ForkPoolWorker-1] Found 1 credential(s) to refresh
[2026-03-20 18:30:00,400: INFO/ForkPoolWorker-1] Successfully refreshed token for tenant <tenant_id>
[2026-03-20 18:30:00,500: INFO/ForkPoolWorker-1] Task refresh_quickbooks_tokens[<uuid>] succeeded
```

#### 6.3 Verify Token Refresh in Database

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

-- Expected: last_refresh_at updated within last 30 minutes
-- Expected: minutes_until_expiry ~= 55-60 (tokens refresh 5 min before expiry)
```

---

### Step 7: Test Disconnect Flow

```bash
curl -X DELETE "http://localhost:8000/api/v1/integrations/quickbooks/disconnect/test"

# Expected Response:
{
  "status": "disconnected",
  "disconnected_at": "2026-03-20T19:30:00Z",
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

-- Expected: connection_status = 'disconnected'
-- Expected: disconnected_at = current timestamp
```

---

## Troubleshooting

### Issue 1: ngrok Tunnel Not Accessible

**Symptoms:**
- Callback fails with "Connection refused"
- QuickBooks shows redirect error

**Solution:**
```bash
# Check ngrok is running
curl https://your-tunnel.ngrok-free.dev/health

# Check ngrok web interface
open http://127.0.0.1:4040

# Restart ngrok if needed
ngrok http 8000 --domain=your-tunnel.ngrok-free.dev
```

### Issue 2: State Token Validation Fails

**Symptoms:**
- Error: "Invalid state token" in callback

**Solution:**
```sql
-- Check if credential record exists with state token
SELECT id, secret_json->>'state_token' as state, connection_status
FROM integration_credential
WHERE connection_status = 'pending'
ORDER BY created_at DESC;

-- If no pending records, initiate OAuth again
```

### Issue 3: Token Decryption Fails

**Symptoms:**
- Error: "Invalid token" or cryptography exceptions

**Solution:**
```bash
# Verify ENCRYPTION_KEY in .env
grep ENCRYPTION_KEY backend/.env

# Key should be 44 characters (Fernet format)
# Regenerate if needed:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Issue 4: Celery Task Not Running

**Symptoms:**
- No token refresh logs after 30 minutes

**Solution:**
```bash
# Check Celery Beat schedule
cd backend
source venv/bin/activate
python -c "from core.celery_app import celery_app; print(celery_app.conf.beat_schedule)"

# Verify task is registered
python -c "from core.celery_app import celery_app; celery_app.loader.import_default_modules(); print('refresh_quickbooks_tokens' in celery_app.tasks)"

# Restart Celery Beat
# Ctrl+C to stop, then:
celery -A core.celery_app beat --loglevel=info
```

### Issue 5: QuickBooks API Returns 401 Unauthorized

**Symptoms:**
- Token refresh fails with 401 error
- Status shows "expired"

**Solution:**
```sql
-- Check token expiration
SELECT 
    expires_at,
    NOW() as current_time,
    expires_at < NOW() as is_expired
FROM integration_credential
WHERE app_service_id IN (
    SELECT id FROM app_service WHERE provider_code = 'quickbooks'
)
ORDER BY created_at DESC
LIMIT 1;

-- If expired, reconnect manually (repeat Step 3)
```

---

## Success Criteria

- ✅ OAuth flow completes without errors
- ✅ Tokens stored encrypted in database (not plaintext)
- ✅ `external_account_id` indexed in `app_service` table
- ✅ Connection status shows "active"
- ✅ Manual token refresh endpoint works
- ✅ Automatic token refresh runs every 30 minutes
- ✅ Disconnect endpoint sets status to "disconnected"
- ✅ State token prevents CSRF attacks
- ✅ Tenant isolation enforced (can't see other tenants' connections)

---

## Next Steps After Successful Testing

1. **Task 17:** Implement Sync Mapping & Upsert Logic
   - Customer sync (bi-directional)
   - Invoice sync (QB → AevoFab)
   - Deduplication via `integration_sync_mapping`

2. **Task 19:** Implement Webhook Handler
   - Use `external_account_id` for O(1) tenant lookup
   - Trigger incremental syncs on QuickBooks changes

---

## Reference Links

- **QuickBooks OAuth 2.0 Docs:** https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0
- **QuickBooks API Explorer:** https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/customer
- **ngrok Dashboard:** https://dashboard.ngrok.com/
- **Task 16 Implementation:** phase-2-5-implementation-roadmap.md

---

**Created:** 2026-03-20  
**Last Updated:** 2026-03-20  
**Status:** Ready for Manual Testing
