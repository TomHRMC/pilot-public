# Cognito Self-Sign-Up Testing Guide

**Version**: 1.0
**Date**: 2026-07-30
**Author**: Pilot DevOps Engineer
**Related**: [ADR-0011](../architecture-design/pilot-adr-log.md) (self-sign-up → Lambda) · [ADR-0012](../architecture-design/pilot-adr-log.md) (drop tenant-name uniqueness) · [aws-cognito-prod-setup.md §11](aws-cognito-prod-setup.md) · [aws-ops-runbook.md §14.5](aws-ops-runbook.md)

---

## Section 1 — How the Self-Sign-Up Flow Works

### Overview

The Pilot for Trades self-sign-up flow allows a new contractor to create their own account without admin intervention. This is the GA (General Availability) path that closes onboarding Gap G1. The flow spans three AWS services — Cognito, Lambda, and RDS — and is governed by ADR-0011 (self-sign-up → Lambda) + ADR-0012 (drop tenant-name uniqueness).

### The 4-Step Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COGNITO SELF-SIGN-UP FLOW                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. SIGN UP                                                                 │
│     Client (web/mobile) → Cognito SignUp (email + password)                 │
│     Cognito creates an UNCONFIRMED user                                     │
│     Cognito sends a verification code to the email                          │
│                                                                             │
│  2. VERIFY EMAIL                                                            │
│     User checks inbox → enters the 6-digit code                            │
│     Client → Cognito ConfirmSignUp (email + code)                           │
│     Cognito marks the user CONFIRMED                                        │
│                                                                             │
│  3. POST-CONFIRMATION LAMBDA FIRES                                          │
│     Cognito triggers the Lambda (PostConfirmation event)                    │
│     Lambda resolves DB_SECRET_ARN → connects to RDS                         │
│     Lambda routes based on email:                                           │
│       Path 1: existing user → no-op (idempotent)                            │
│       Path 2: pending invite → attach to existing tenant                    │
│       Path 3: new owner → create tenant + user + tenant_user(owner)         │
│                                                                             │
│  4. RDS ROWS CREATED (Path 3 only)                                          │
│     tenant: "{local_part}'s Company" (placeholder name, ADR-0012)           │
│     user: email, is_platform_user=false                                     │
│     tenant_user: role=owner, status=active, joined_at=now()                 │
│     user_endpoint: email channel, is_primary=true                           │
│                                                                             │
│  After confirmation, the user can log in and the wizard (step 1)            │
│  resolves-or-attaches to the Lambda-created tenant by email.                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The 3-Path Router (Lambda)

The Post-Confirmation Lambda fires on **every** Cognito confirmation in the pool, so it must **route**, not blindly create a tenant. The routing key is `email`:

| Path | Condition | Action | User Type |
|---|---|---|---|
| **Path 1** | A `user` row already exists for the email | **No-op** (idempotent — safe for re-fires) | Platform owner, platform user, or a re-fire |
| **Path 2** | A pending `tenant_user_invite` exists (accepted_at IS NULL, is_active, not expired) | Create `user`, attach `tenant_user` to the invite's tenant, set `accepted_at` | Invited employee (type iv) |
| **Path 3** | No `user` and no pending invite | Create `tenant` (placeholder name) + owner `user` + `tenant_user(owner)` | New self-serve owner (type iii) |

**Critical safety property**: the Lambda **never raises to Cognito**. All errors are logged and swallowed (returns `event`). An unhandled exception would make Cognito treat the confirmation as failed and strand the user.

### Key Configuration Points

| Setting | Value | Where |
|---|---|---|
| `allow_admin_create_user_only` | `false` | Cognito pool (Terraform `security/main.tf`) |
| `auto_verified_attributes` | `["email"]` | Cognito pool (set via CLI — `schema` is in `ignore_changes`) |
| `EmailSendingAccount` | `COGNITO_DEFAULT` | Cognito pool (built-in email, 50/day limit) |
| `LambdaConfig.PostConfirmation` | Lambda ARN | Cognito pool (wired via CLI — `lambda_config` is in `ignore_changes`) |
| `DB_SECRET_ARN` | `pilot/prod/db` secret ARN | Lambda env var (resolved at runtime via boto3) |
| `COGNITO_USER_POOL_ID` | `us-east-1_XXXXXXXXX` | Lambda env var |
| `ENVIRONMENT` | `production` | Lambda env var |
| Lambda handler | `handler.handler` | Lambda config (handler.py at zip root) |
| Lambda runtime | `python3.12` | Lambda config |
| Lambda VPC | Private subnets + `sg_lambda` | Lambda config (must reach RDS in-VPC) |
| `sg_rds` ingress | 5432 from `sg_lambda` | Networking module (inline block) |

---

## Section 2 — Running the Full Test

### 2.0 — Prerequisites

Before running the test, ensure ALL of the following are in place:

#### Environment Requirements

| Requirement | How to verify |
|---|---|
| AWS CLI authenticated | `aws sts get-caller-identity` → returns account `000000000000` |
| Bastion running | `aws ec2 describe-instances --filters "Name=tag:Name,Values=pilot-production-bastion" --query 'Reservations[0].Instances[0].State.Name' --output text` → `running` |
| SSH tunnel open on 5433 | `nc -z 127.0.0.1 5433` → succeeds (see [runbook §9.1](aws-ops-runbook.md#91-open-ssh-tunnel-for-direct-db-access-vs-code--psql)) |
| E2e Docker NOT on 5433 | `lsof -i :5433` → should show `ssh`, not `com.docke` (e2e is now on 5434) |
| Prod DB schema synced | `stripe_connect_account_id` column exists on `tenant` table (see [runbook §9.5](aws-ops-runbook.md#95-db-backup--restore-dev--prod-schema-sync)) |
| Core + platform seed data | `tenant_user_role` has `owner` + `technician` roles; `tenant_user_status` has `active` status |
| Cognito pool: self-sign-up enabled | `aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX --query 'UserPool.AdminCreateUserConfig.AllowAdminCreateUserOnly'` → `false` |
| Cognito pool: auto-verify email | `aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX --query 'UserPool.AutoVerifiedAttributes'` → `["email"]` |
| Cognito pool: trigger wired | `aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX --query 'UserPool.LambdaConfig.PostConfirmation'` → Lambda ARN |
| Lambda deployed | `aws lambda get-function --function-name pilot-production-post-confirmation --query 'Configuration.CodeSha256'` → non-placeholder SHA |
| A real email you can check | Needed to receive the Cognito verification code |

#### Constants used throughout this guide

```bash
# Cognito
USER_POOL_ID="us-east-1_XXXXXXXXX"
CLIENT_ID="xxxxxxxxxxxxxxxxxxxxxxxxxx"
LAMBDA_NAME="pilot-production-post-confirmation"
LOG_GROUP="/aws/lambda/pilot-production-post-confirmation"

# RDS (via SSH tunnel)
RDS_EP="pilot-production.xxx.us-east-1.rds.amazonaws.com"
DB_HOST="127.0.0.1"
DB_PORT="5433"
DB_NAME="pilot_prod"
DB_USER="pilot_user"
```

### 2.1 — Open the SSH Tunnel (if not already open)

```bash
# Check if tunnel is already open
nc -z 127.0.0.1 5433 && echo "Tunnel already open ✅" || {
  # Open the tunnel
  ssh -f -N -L 5433:${RDS_EP}:5432 pilot-bastion
  sleep 2
  nc -z 127.0.0.1 5433 && echo "Tunnel opened ✅" || echo "Tunnel failed ❌"
}
```

### 2.2 — Fetch the Prod DB Password

```bash
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
echo "Password fetched (length: ${#DB_PASS})"
```

### 2.3 — Verify Prerequisites (quick check)

```bash
# Verify schema has the columns the Lambda needs
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='tenant' AND column_name = 'stripe_connect_account_id';"

# Verify seed data (roles + statuses)
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT code FROM tenant_user_role WHERE code = 'owner'; SELECT code FROM tenant_user_status WHERE code = 'active';"

# Verify Cognito pool config
aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID \
  --query 'UserPool.[AdminCreateUserConfig.AllowAdminCreateUserOnly, AutoVerifiedAttributes, LambdaConfig.PostConfirmation]' --output json

# Verify no existing test user in RDS
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT count(*) FROM public.\"user\" WHERE email = 'TEST_EMAIL@gmail.com';"
```

### 2.4 — Step 1: Cognito SignUp

Replace `TEST_EMAIL@gmail.com` with a real email you can check, and `TestPassword123!` with a password meeting the pool policy (min 12 chars, upper/lower/number/symbol).

```bash
# ── Set your test email + password ────────────────────────────────────────────
TEST_EMAIL="your.email@gmail.com"
TEST_PASSWORD="<test-user-password>"

# ── SignUp ───────────────────────────────────────────────────────────────────
aws cognito-idp sign-up \
  --client-id $CLIENT_ID \
  --username "$TEST_EMAIL" \
  --password "$TEST_PASSWORD" \
  --user-attributes Name=email,Value="$TEST_EMAIL" \
  --output json
```

**Expected output:**
```json
{
    "UserConfirmed": false,
    "CodeDeliveryDetails": {
        "Destination": "y***@g***",
        "DeliveryMedium": "EMAIL",
        "AttributeName": "email"
    },
    "UserSub": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

If `CodeDeliveryDetails` is missing or `DeliveryMedium` is not `"EMAIL"`, the pool's `auto_verified_attributes` is not set. See [Section 3 — Troubleshooting](#section-3--troubleshooting).

### 2.5 — Step 2: Confirm the Email

Check your email inbox for a message from Cognito with a 6-digit verification code. Then:

```bash
# ── Set the verification code from your email ─────────────────────────────────
VERIFICATION_CODE="123456"   # ← replace with the actual code

# ── ConfirmSignUp ────────────────────────────────────────────────────────────
aws cognito-idp confirm-sign-up \
  --client-id $CLIENT_ID \
  --username "$TEST_EMAIL" \
  --confirmation-code "$VERIFICATION_CODE"

echo "ConfirmSignUp exit: $?"
```

**Expected**: exit code 0, no output (success). This fires the Post-Confirmation Lambda.

If you get `NotAuthorizedException: User cannot be confirmed. Current status is CONFIRMED`, the user was already confirmed (possibly from a prior test run). Skip to verification.

### 2.6 — Step 3: Verify the Lambda Fired (CloudWatch Logs)

```bash
# Wait a few seconds for the Lambda to complete
sleep 5

# Get the latest log stream
STREAM=$(aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime --descending --limit 1 \
  --query 'logStreams[0].logStreamName' --output text)

# Show the log events
aws logs get-log-events \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name "$STREAM" \
  --limit 20 \
  --query 'events[*].message' --output text
```

**Expected for a brand-new email (Path 3):**
```
[INFO]  Found credentials in environment variables.
[INFO]  Path 3: new owner your.email@gmail.com, creating tenant
```

**Expected for a re-fire / existing user (Path 1):**
```
[INFO]  Path 1: existing user your.email@gmail.com, no-op
```

Cognito may fire the Lambda **twice** on a single confirmation. The first invocation creates the rows (Path 3), and the second hits Path 1 (no-op). This is expected and proves the idempotency design works.

### 2.7 — Step 4: Verify RDS Rows Were Created

```bash
# ── Verify the user row ───────────────────────────────────────────────────────
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT id, email, is_platform_user, created_at FROM public.\"user\" WHERE email = '$TEST_EMAIL';"

# ── Verify the tenant row (placeholder name) ──────────────────────────────────
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT id, name, is_active, created_at FROM public.tenant WHERE name ILIKE '%${TEST_EMAIL%@*}%';"

# ── Verify the tenant_user link (owner role) ─────────────────────────────────
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT tu.tenant_id, tu.user_id, tu.role_code, tu.joined_at FROM public.tenant_user tu JOIN public.\"user\" u ON u.id = tu.user_id WHERE u.email = '$TEST_EMAIL';"
```

**Expected (Path 3 — new owner):**
- `user` row: `email = your.email@gmail.com`, `is_platform_user = false`
- `tenant` row: `name = "your.email's Company"` (placeholder), `is_active = true`
- `tenant_user` row: `role_code = owner`, `joined_at = <now>`

### 2.8 — Step 5: Test Idempotency (Path 1 No-Op)

Re-invoke the Lambda directly with a synthetic event to confirm Path 1 fires (no duplicate rows created):

```bash
# ── Invoke Lambda directly (simulates a re-fire) ──────────────────────────────
aws lambda invoke \
  --function-name $LAMBDA_NAME \
  --cli-binary-format raw-in-base64-out \
  --payload "{\"version\":\"1\",\"triggerSource\":\"PostConfirmation_ConfirmSignUp\",\"userPoolId\":\"$USER_POOL_ID\",\"userName\":\"test-sub\",\"request\":{\"userAttributes\":{\"email\":\"$TEST_EMAIL\",\"email_verified\":\"true\"}},\"response\":{}}" \
  /tmp/lambda-response.json

echo "Lambda invoke exit: $?"
cat /tmp/lambda-response.json

# ── Check CloudWatch — should show Path 1 ────────────────────────────────────
sleep 3
STREAM=$(aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime --descending --limit 1 \
  --query 'logStreams[0].logStreamName' --output text)
aws logs get-log-events \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name "$STREAM" \
  --limit 5 \
  --query 'events[*].message' --output text

# ── Verify no duplicate rows ──────────────────────────────────────────────────
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT count(*) as user_count FROM public.\"user\" WHERE email = '$TEST_EMAIL'; SELECT count(*) as tenant_count FROM public.tenant WHERE name ILIKE '%${TEST_EMAIL%@*}%';"
```

**Expected**: Path 1 no-op in logs; user_count = 1, tenant_count = 1 (no duplicates).

### 2.9 — Cleanup: Remove Only Test-Created Data

This cleanup removes **only** the rows created by the test (keyed by the test email). It does NOT touch any existing tenants or users in the database.

**Prerequisites**: the variables `USER_POOL_ID`, `CLIENT_ID`, `DB_PASS`, and the SSH tunnel must be set up first. If you're running this section standalone (not continuing from §2.4), initialize them now:

```bash
# Constants (from §2.0)
USER_POOL_ID="us-east-1_XXXXXXXXX"
CLIENT_ID="xxxxxxxxxxxxxxxxxxxxxxxxxx"

# DB password (from §2.2)
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# SSH tunnel must be open on 5433 (from §2.1)
nc -z 127.0.0.1 5433 || { echo "ERROR: SSH tunnel not open — run §2.1 first"; exit 1; }
```

```bash
# ── 1. Delete the Cognito user ────────────────────────────────────────────────
# Set the test email you used in §2.4
USER_POOL_ID="us-east-1_XXXXXXXXX"
TEST_EMAIL="owner@example.com"
aws cognito-idp admin-delete-user \
  --user-pool-id $USER_POOL_ID \
  --username "$TEST_EMAIL"
echo "Cognito user deleted ✅"

# ── 2. Get the test user's ID + tenant ID from RDS ────────────────────────────
USER_ID=$(PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -t -A -c "SELECT id FROM public.\"user\" WHERE email = '$TEST_EMAIL';")
TENANT_ID=$(PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -t -A -c "SELECT tenant_id FROM public.tenant_user WHERE user_id = '$USER_ID';")

echo "Test user_id: $USER_ID"
echo "Test tenant_id: $TENANT_ID"

# ── 3. Delete RDS rows (bypassing guard triggers) ────────────────────────────
# The user_endpoint table has guard triggers that prevent deleting the only
# primary email endpoint. We use session_replication_role=replica to bypass
# ALL triggers (including FK constraints) for this session only, then reset.
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" << EOF
-- Bypass all triggers for this session (safe — session-scoped, auto-resets)
SET session_replication_role = 'replica';

-- Delete in FK-safe order: tenant_user → user_endpoint → user → tenant
DELETE FROM tenant_user WHERE user_id = '$USER_ID';
DELETE FROM user_endpoint WHERE user_id = '$USER_ID';
DELETE FROM "user" WHERE id = '$USER_ID';
DELETE FROM tenant WHERE id = '$TENANT_ID';

-- Reset to normal
SET session_replication_role = 'origin';
EOF
echo "RDS rows deleted ✅"

# ── 4. Verify cleanup ─────────────────────────────────────────────────────────
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT count(*) as users FROM public.\"user\" WHERE email = '$TEST_EMAIL'; SELECT count(*) as endpoints FROM public.user_endpoint WHERE value = '$TEST_EMAIL'; SELECT count(*) as tenants FROM public.tenant WHERE id = '$TENANT_ID';"
```

**Expected**: all counts = 0.

⚠️ **Safety**: this cleanup only deletes rows keyed by `$TEST_EMAIL` and `$USER_ID`/`$TENANT_ID`. It does NOT touch any other tenants or users. If the test email was already cleaned up, the DELETEs will affect 0 rows (safe no-op).

### 2.10 — Verify Triggers Are Re-Enabled

After cleanup, verify all DB triggers are back to normal:

```bash
PGPASSWORD="$DB_PASS" psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SHOW session_replication_role; SELECT tgname, tgenabled FROM pg_trigger WHERE tgrelid = 'user_endpoint'::regclass AND tgenabled != 'O';"
```

**Expected**: `session_replication_role = origin`; the trigger query returns 0 rows (all enabled).

---

## Section 3 — Troubleshooting

### Verification email not received

**Symptom**: `SignUp` succeeds but no email arrives. `CodeDeliveryDetails` is missing from the response.

**Cause**: `auto_verified_attributes` is not set on the pool (it's `null`).

**Fix**:
> **Superseded** — a single-setting `update-user-pool` resets every setting you leave out (Lambda triggers, device and MFA config). Use the full-carry command in `aws-cognito-prod-setup.md` and `aws-ops-runbook.md` instead. (Both pools were deleted on 2026-11-14.)

```bash
aws cognito-idp update-user-pool \
  --user-pool-id $USER_POOL_ID \
  --auto-verified-attributes email
```

⚠️ `update-user-pool` overwrites the **entire** `LambdaConfig` block. If other triggers are configured, include them all in the same call. Verify before and after with `describe-user-pool --query 'UserPool.LambdaConfig'`.

### Lambda error: "No module named 'handler'"

**Symptom**: `UserLambdaValidationException: PostConfirmation failed with error Unable to import module 'handler': No module named 'handler'`

**Cause**: `handler.py` is not at the root of the Lambda zip. The handler config is `handler.handler` (module `handler`, function `handler`), so `handler.py` must be at the zip root.

**Fix**: Rebuild the package with the build script (which copies `handler.py` to the build root), then redeploy:
```bash
./infrastructure/scripts/build-post-confirmation-lambda.sh
cd infrastructure/terraform/environments/production
terraform plan -target=module.security.aws_lambda_function.post_confirmation -out=lambda.tfplan
terraform apply lambda.tfplan
```

### Lambda error: "column ... of relation ... does not exist"

**Symptom**: Lambda connects to RDS but the INSERT fails with `UndefinedColumn`.

**Cause**: The prod DB schema is behind dev — the Lambda's ORM models reference columns that don't exist in prod yet.

**Fix**: Sync the prod schema from dev (see [runbook §9.5](aws-ops-runbook.md#95-db-backup--restore-dev--prod-schema-sync)):
```bash
# Dump dev schema
pg_dump -h localhost -U pilot_user -s -x -O pilot_dev > archive/db-backups/schema-only/schema_dump_$(date +%Y%m%d_%H%M%S).sql

# Wipe + apply to prod (see runbook §9.5.7 for the full workflow)
```

### Lambda error: "password authentication failed"

**Symptom**: Lambda fails to connect to RDS.

**Cause**: The `DB_SECRET_ARN` secret's password doesn't match the RDS instance password (drift).

**Fix**: Verify the secret password works via `psql` through the tunnel. If it fails, the RDS password may have been changed outside Terraform. Check Terraform state for the `random_password` resource.

### SSH tunnel: "password authentication failed for user pilot_user"

**Symptom**: `psql` through the tunnel fails with auth error, but the Lambda connects fine.

**Cause**: Port 5433 is occupied by the e2e Docker container (`pilot_e2e_postgres`), not the SSH tunnel. `psql` is hitting the dev e2e DB with the prod password.

**Fix**: Stop the e2e container (it's now on port 5434, but if an old container is still on 5433):
```bash
docker stop pilot_e2e_postgres
# Reopen the tunnel
ssh -f -N -L 5433:${RDS_EP}:5432 pilot-bastion
```

### Cleanup: "Cannot delete the only primary email endpoint"

**Symptom**: `DELETE FROM user_endpoint` fails with the guard trigger error.

**Cause**: The `guard_user_endpoint_primary_email_fn` trigger prevents deleting the only primary email for a user.

**Fix**: Use `session_replication_role = 'replica'` to bypass all triggers for the session (see [Section 2.9](#29--cleanup-remove-only-test-created-data)). This is session-scoped and auto-resets.

### Cognito: "User cannot be confirmed. Current status is CONFIRMED"

**Symptom**: `AdminConfirmSignUp` or `ConfirmSignUp` fails with this error.

**Cause**: The user was already confirmed (from a prior test run or a double-fire).

**Fix**: This is harmless — the user is already confirmed. Skip to verification (Step 3).

---

## Section 4 — Configuration Reference

### Cognito Pool Settings (as-built)

| Setting | Value | Managed by |
|---|---|---|
| Pool ID | `us-east-1_XXXXXXXXX` | Imported (manually created) |
| Pool name | `pilot-production` | Terraform (in `ignore_changes`) |
| Client ID | `xxxxxxxxxxxxxxxxxxxxxxxxxx` | Imported |
| `allow_admin_create_user_only` | `false` (self-sign-up enabled) | Terraform |
| `auto_verified_attributes` | `["email"]` | CLI (pool `schema` is in `ignore_changes`) |
| `EmailSendingAccount` | `COGNITO_DEFAULT` | CLI (50 emails/day limit) |
| `LambdaConfig.PostConfirmation` | Lambda ARN | CLI (`lambda_config` is in `ignore_changes`) |
| `deletion_protection` | `ACTIVE` | Terraform |
| Password policy | min 12, upper/lower/number/symbol | Terraform |
| MFA | Optional | Terraform |

### Lambda Configuration (as-built)

| Setting | Value |
|---|---|
| Function name | `pilot-production-post-confirmation` |
| Handler | `handler.handler` |
| Runtime | `python3.12` |
| Memory | 256 MB |
| Timeout | 30s |
| VPC | Private subnets + `sg_lambda` |
| `DB_SECRET_ARN` | `arn:aws:secretsmanager:us-east-1:000000000000:secret:pilot/prod/db-XXXXXX` |
| `COGNITO_USER_POOL_ID` | `us-east-1_XXXXXXXXX` |
| `ENVIRONMENT` | `production` |
| Tracing | X-Ray Active |
| IAM role | `pilot-production-lambda-execution-role` (VPC access + `secretsmanager:GetSecretValue` on db secret + `kms:Decrypt`) |

### Lambda Package Dependencies

| Package | Version | Notes |
|---|---|---|
| `psycopg2-binary` | 2.9.11 | Linux manylinux wheel (NOT mac-built) |
| `SQLAlchemy` | 2.0.48 | Linux wheel |
| `sqlmodel` | 0.0.37 | Pure Python |
| `pydantic` | 2.12.5 | Pure Python |
| `pgvector` | 0.4.2 | Required by `app/models/ai.py` + `help.py` (eagerly imported by `__init__.py`) |
| `boto3` / `botocore` | (runtime) | **NOT packaged** — pre-bundled in the Lambda Python runtime |

### Build Script

```bash
# Build the Lambda package (run from repo root, before terraform plan)
./infrastructure/scripts/build-post-confirmation-lambda.sh
```

This produces `infrastructure/terraform/modules/security/build/post_confirmation/` which the Terraform `data.archive_file.post_confirmation` zips at plan/apply time. The build dir is gitignored.

### Trigger Wiring (manual — CLI)

The `lambda_config` attribute is deliberately kept in the pool's `lifecycle.ignore_changes` to prevent Terraform from forcing pool replacement. The trigger is wired manually:

```bash
# Verify current LambdaConfig (don't clobber other triggers)
aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --query 'UserPool.LambdaConfig'

# Wire the Post-Confirmation trigger
aws cognito-idp update-user-pool \
  --user-pool-id $USER_POOL_ID \
  --lambda-config PostConfirmation=$(aws lambda get-function \
    --function-name $LAMBDA_NAME \
    --query 'Configuration.FunctionArn' --output text)
```

⚠️ `update-user-pool` overwrites the **entire** `LambdaConfig` block. If the describe shows other triggers, include them all in the same call.

---

## Section 5 — Rollback

If self-sign-up or the Lambda misbehaves:

```bash
# 1. Re-close self-registration immediately (existing users/login unaffected)
cd infrastructure/terraform/environments/production
# Edit modules/security/main.tf: allow_admin_create_user_only = true
terraform apply -target=aws_cognito_user_pool.prod

# 2. (Optional) Unwire the trigger
aws cognito-idp update-user-pool \
  --user-pool-id $USER_POOL_ID \
  --lambda-config PostConfirmation=""
```

Existing users and logins are unaffected by rollback — only new self-sign-ups are blocked.
