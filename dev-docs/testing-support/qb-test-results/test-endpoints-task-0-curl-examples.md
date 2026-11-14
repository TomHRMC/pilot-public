# Test Endpoints - Manual Curl Testing Guide

## Overview
This document provides curl examples for all 21 test endpoints implemented in Phase 2.

## Prerequisites
1. Server must be running: `cd backend && uvicorn app.main:app --reload`
2. Environment variable must be set: `TEST_ENDPOINT_ENABLED=true` (in backend/.env)
3. Test tenant seeded in database: `00000000-0000-0000-0000-000000000001`

## Base URL
```
http://localhost:8000/api/v1
```

---

## 1. Customers (2 endpoints)

### POST /customers/test
```bash
curl -X POST http://localhost:8000/api/v1/customers/test \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Test Customer",
    "type": "person",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "mobile_phone": "+1-555-0100"
  }'
```

### GET /customers/test
```bash
curl http://localhost:8000/api/v1/customers/test
```

---

## 2. Sites (2 endpoints)

### POST /sites/test
```bash
# First create a customer, then use its ID:
CUSTOMER_ID="<uuid-from-above>"

curl -X POST http://localhost:8000/api/v1/sites/test \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "name": "Main Office",
    "notes": "Downtown location"
  }'
```

### GET /sites/test
```bash
curl http://localhost:8000/api/v1/sites/test
```

---

## 3. Catalog (3 endpoints)

### POST /catalog/supplier-items/test
```bash
curl -X POST http://localhost:8000/api/v1/catalog/supplier-items/test \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": "00000000-0000-0000-0000-000000000003",
    "sku": "WIRE-12-2-250",
    "name": "12/2 NM-B Wire 250ft",
    "description": "Residential wiring cable",
    "uom_id": "00000000-0000-0000-0000-000000000004",
    "category_id": "00000000-0000-0000-0000-000000000005"
  }'
```

### GET /catalog/supplier-items/test
```bash
curl http://localhost:8000/api/v1/catalog/supplier-items/test
```

### GET /catalog/pricing-cache/test
```bash
curl http://localhost:8000/api/v1/catalog/pricing-cache/test

# With SKU filter:
curl "http://localhost:8000/api/v1/catalog/pricing-cache/test?sku=WIRE-12-2-250"
```

---

## 4. Voice (1 endpoint)

### POST /voice/command/test
```bash
curl -X POST http://localhost:8000/api/v1/voice/command/test \
  -F "audio=@test-audio.m4a" \
  -F "session_id="
```

**Note:** Requires actual audio file (m4a format) for Whisper transcription.

---

## 5. Auth (1 endpoint)

### POST /auth/signup/test
```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup/test?email=newuser@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "New Test Company",
    "first_name": "Jane",
    "last_name": "Smith"
  }'
```

---

## 6. Jobs (4 endpoints)

### POST /jobs/test
```bash
# Use customer_id and site_id from above:
CUSTOMER_ID="<uuid>"
SITE_ID="<uuid>"

curl -X POST http://localhost:8000/api/v1/jobs/test \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "site_id": "'$SITE_ID'",
    "scheduled_start": "2026-04-01T09:00:00Z",
    "scheduled_end": "2026-04-01T17:00:00Z"
  }'
```

### GET /jobs/test
```bash
curl http://localhost:8000/api/v1/jobs/test
```

### POST /jobs/{job_id}/time-entries/test
```bash
JOB_ID="<uuid-from-above>"

curl -X POST http://localhost:8000/api/v1/jobs/$JOB_ID/time-entries/test \
  -H "Content-Type: application/json" \
  -d '{
    "started_at": "2026-04-01T09:00:00Z",
    "ended_at": "2026-04-01T17:00:00Z",
    "notes": "Panel upgrade installation"
  }'
```

### POST /jobs/{job_id}/expenses/test
```bash
JOB_ID="<uuid>"

curl -X POST http://localhost:8000/api/v1/jobs/$JOB_ID/expenses/test \
  -H "Content-Type: application/json" \
  -d '{
    "job_expense_category_code": "materials",
    "description": "Wire 12/2 250ft",
    "vendor_name": "Local Supply",
    "incurred_at": "2026-04-01T10:00:00Z",
    "cost_cents": 5000,
    "is_billable": true
  }'
```

---

## 7. Quotes (7 endpoints)

### POST /quotes/test
```bash
curl -X POST http://localhost:8000/api/v1/quotes/test \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "site_id": "'$SITE_ID'",
    "currency": "USD"
  }'
```

### GET /quotes/test
```bash
curl http://localhost:8000/api/v1/quotes/test
```

### GET /quotes/{quote_id}/test
```bash
QUOTE_ID="<uuid-from-above>"

curl http://localhost:8000/api/v1/quotes/$QUOTE_ID/test
```

### PATCH /quotes/{quote_id}/test
```bash
curl -X PATCH http://localhost:8000/api/v1/quotes/$QUOTE_ID/test \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "USD"
  }'
```

### POST /quotes/{quote_id}/lines/test
```bash
curl -X POST http://localhost:8000/api/v1/quotes/$QUOTE_ID/lines/test \
  -H "Content-Type: application/json" \
  -d '{
    "position": 1,
    "description": "Panel upgrade 200A",
    "quantity": 1,
    "unit": "ea",
    "unit_price_cents": 50000
  }'
```

### POST /quotes/{quote_id}/versions/test
```bash
curl -X POST http://localhost:8000/api/v1/quotes/$QUOTE_ID/versions/test
```

### POST /quotes/{quote_id}/versions/{version_id}/public-link/test
```bash
VERSION_ID="<uuid-from-above>"

curl -X POST http://localhost:8000/api/v1/quotes/$QUOTE_ID/versions/$VERSION_ID/public-link/test \
  -H "Content-Type: application/json" \
  -d '{
    "expires_at": "2026-04-30T23:59:59Z"
  }'
```

---

## Complete Test Script

Here's a complete bash script to test the entire workflow:

```bash
#!/bin/bash
set -e

BASE_URL="http://localhost:8000/api/v1"

echo "1. Creating customer..."
CUSTOMER_RESPONSE=$(curl -s -X POST $BASE_URL/customers/test \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Test Customer",
    "type": "person",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe.'$(date +%s)'@example.com"
  }')
CUSTOMER_ID=$(echo $CUSTOMER_RESPONSE | jq -r '.id')
echo "Customer ID: $CUSTOMER_ID"

echo "2. Creating site..."
SITE_RESPONSE=$(curl -s -X POST $BASE_URL/sites/test \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "name": "Main Office"
  }')
SITE_ID=$(echo $SITE_RESPONSE | jq -r '.id')
echo "Site ID: $SITE_ID"

echo "3. Creating quote..."
QUOTE_RESPONSE=$(curl -s -X POST $BASE_URL/quotes/test \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "site_id": "'$SITE_ID'",
    "currency": "USD"
  }')
QUOTE_ID=$(echo $QUOTE_RESPONSE | jq -r '.id')
echo "Quote ID: $QUOTE_ID"

echo "4. Adding quote line..."
curl -s -X POST $BASE_URL/quotes/$QUOTE_ID/lines/test \
  -H "Content-Type: application/json" \
  -d '{
    "position": 1,
    "description": "Panel upgrade 200A",
    "quantity": 1,
    "unit": "ea",
    "unit_price_cents": 50000
  }' | jq '.'

echo "5. Creating quote version..."
VERSION_RESPONSE=$(curl -s -X POST $BASE_URL/quotes/$QUOTE_ID/versions/test)
VERSION_ID=$(echo $VERSION_RESPONSE | jq -r '.id')
echo "Version ID: $VERSION_ID"

echo "6. Creating job..."
JOB_RESPONSE=$(curl -s -X POST $BASE_URL/jobs/test \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "site_id": "'$SITE_ID'",
    "scheduled_start": "2026-04-01T09:00:00Z"
  }')
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.id')
echo "Job ID: $JOB_ID"

echo ""
echo "✅ All test endpoints working!"
```

---

## Verification Checklist

After running tests, verify in the database:

```sql
-- All records should have the test tenant_id
SELECT 'customers' as table_name, count(*) as count 
FROM customer WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
UNION ALL
SELECT 'sites', count(*) FROM site WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
UNION ALL
SELECT 'quotes', count(*) FROM quote WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
UNION ALL
SELECT 'jobs', count(*) FROM job WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
```

---

## Security Notes

- ⚠️ Test endpoints are **DISABLED by default** (TEST_ENDPOINT_ENABLED=false)
- ⚠️ They return **HTTP 403** when disabled
- ⚠️ They should **NEVER** be enabled in staging or production
- ✅ Only enable in local development and QA environments
- ✅ All test data is isolated to test tenant: `00000000-0000-0000-0000-000000000001`
