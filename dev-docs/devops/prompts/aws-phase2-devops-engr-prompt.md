# AWS Deployment — Phase 2 Execution Prompt

**Mode**: `pilot-devops-engineer`  
**Phase**: 2 (Data Layer) + Phase 3 (Security) — executed together due to Terraform dependency order  
**Status doc**: [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md)  
**Deployment plan**: [`dev-docs/devops/aws-deployment-plan-v1.md`](../aws-deployment-plan-v1.md)  
**Estimate**: 30–45 minutes total (RDS Multi-AZ provisioning is the long pole at ~15 min)  
**Platform**: AWS · `us-east-1` · HotRMC account `000000000000`

---

## ⚠️ MANDATORY STOP — Read Before Running Any Command

1. Read [`aws-deployment-plan-v1.md §5 Phase 2`](../aws-deployment-plan-v1.md) — the `⚠️ EXECUTION ORDER CORRECTION` callout explains why the plan's Phase 2/Phase 3 labels are inverted relative to the Terraform dependency graph.
2. Read [`aws-deployment-status.md`](../aws-deployment-status.md) Phase 2 section — Steps 2.1–2.5 are the authoritative execution checklist. Mark each step as you complete it.
3. **Do NOT run** `terraform apply -target=module.database` without first completing Steps 2.1 and 2.2. It will fail — `module.database` requires `kms_key_arn`, `secret_db_arn`, and `secret_redis_arn` outputs that only exist after `module.security` is applied.

---

## Pre-Work: Verify Starting State

Before running any `terraform` command, confirm you are in the right directory and account:

```bash
# 1. Correct working directory
cd infrastructure/terraform/environments/production

# 2. Confirm correct AWS account (must be HotRMC: 000000000000)
aws sts get-caller-identity
# Expected:
# {
#   "Account": "000000000000",
#   "UserId": "<pilot-admin user ID>",
#   "Arn": "arn:aws:iam::000000000000:user/pilot-admin"
# }

# 3. Confirm bastion is reachable (Phase 1 networking is complete)
ssh pilot-bastion "echo bastion-ok"
# Expected: bastion-ok

# 4. Confirm current public IP is in admin_allowed_ips
curl -s https://api.ipify.org
# If NOT 203.0.113.13 (home ISP), update admin_allowed_ips in terraform.tfvars
# and run: terraform apply -target=module.networking BEFORE proceeding
```

---

## Execution Steps

### Step 2.1 — Cognito Import *(~1 min)*

Import the existing production Cognito user pool that was manually created on 2026-06-30. **This must run before `module.security` is applied** — without it, Terraform will attempt to CREATE a new pool and fail on the duplicate email attribute.

```bash
terraform import aws_cognito_user_pool.prod us-east-1_XXXXXXXXX
terraform import aws_cognito_user_pool_client.prod_web us-east-1_XXXXXXXXX/xxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Verify the import is clean:**
```bash
terraform plan -target=module.security 2>&1 | grep -E "cognito|will be created|will be destroyed|Plan:"
# Expected: Plan shows 0 changes for Cognito resources
# If you see "aws_cognito_user_pool.prod will be created" → STOP and re-import
```

**Record in status doc:**
- `Step 2.1` import results (✅ / ❌)
- `terraform plan -target=module.security` Cognito shows no changes (⬜ → ✅)

---

### Step 2.2 — Apply Security Module *(~5–10 min)*

Creates: KMS key, Secrets Manager secret shells (`pilot/prod/db`, `pilot/prod/redis`), Route 53 hosted zone + all DNS records, ACM wildcard cert request, all IAM roles (ECS task, ECS execution, Lambda execution, App Runner, GitHub Actions OIDC).

```bash
terraform apply -target=module.security
```

**When prompted** `Do you want to perform these actions?` → type `yes`

**Capture all outputs immediately after apply:**
```bash
terraform output route53_nameservers
# Record all 4 NS values — needed for GoDaddy cutover in Phase 5

terraform output github_actions_role_arn
# Paste into .github/workflows/deploy-production.yml when Phase 7 runs
```

**Verify key resources exist:**
```bash
# KMS key created
aws kms list-keys --region us-east-1 | grep -c KeyId

# Secret shells created (values will be empty until Step 2.3 populates them)
aws secretsmanager describe-secret --secret-id "pilot/prod/db" --query 'Name' --output text
aws secretsmanager describe-secret --secret-id "pilot/prod/redis" --query 'Name' --output text
# Expected: pilot/prod/db and pilot/prod/redis

# Route 53 zone created
aws route53 list-hosted-zones --query "HostedZones[?Name=='pilotfortrades.com.'].Id" --output text
# Expected: /hostedzone/<zone-id>
```

**Record in status doc:**
- `Step 2.2` result (✅ / ❌)
- `route53_nameservers` — all 4 NS values
- `github_actions_role_arn` value
- KMS key created (⬜ → ✅)
- Secret shells created (⬜ → ✅)
- Route 53 zone + DNS records created (⬜ → ✅)
- ACM cert status: PENDING (expected — validates after Phase 5 DNS cutover)
- IAM roles created (⬜ → ✅)

---

### Step 2.3 — Apply Database Module *(~10–15 min for RDS Multi-AZ)*

Creates: RDS `pilot-production` (db.t4g.micro, PostgreSQL 17, Multi-AZ, 20GB gp2, KMS-encrypted, 28-day backups), ElastiCache `pilot-production` (cache.t4g.micro, Redis 7.1), and auto-populates the `pilot/prod/db` and `pilot/prod/redis` Secrets Manager secrets.

```bash
terraform apply -target=module.database
```

**When prompted** → type `yes`

> RDS Multi-AZ provisioning takes 10–15 minutes. The terminal will hang at `aws_db_instance.postgres: Still creating...` — this is normal. Do not interrupt.

**Capture outputs after apply:**
```bash
terraform output -raw rds_endpoint
# Example: pilot-production.xxxxxxxx.us-east-1.rds.amazonaws.com
# Record this — needed for SSH tunnel in Step 2.4

terraform output -raw redis_endpoint
# Example: pilot-production.xxxxxx.0001.use1.cache.amazonaws.com
```

**Verify secrets were populated:**
```bash
aws secretsmanager get-secret-value --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text | python3 -c "import sys,json; d=json.load(sys.stdin); print('host:', d['host'], '| dbname:', d['dbname'])"
# Expected: host: pilot-production.xxx.rds.amazonaws.com | dbname: pilot_prod

aws secretsmanager get-secret-value --secret-id "pilot/prod/redis" \
  --query 'SecretString' --output text | python3 -c "import sys,json; d=json.load(sys.stdin); print('broker:', d['broker_url'])"
# Expected: broker: redis://pilot-production.xxx.cache.amazonaws.com:6379/1
```

**Record in status doc:**
- `Step 2.3` result (✅ / ❌)
- `rds_endpoint` value (sensitive — record in status doc `Step 2.3` only)
- `redis_endpoint` value
- `pilot/prod/db` secret populated (⬜ → ✅)
- `pilot/prod/redis` secret populated (⬜ → ✅)

---

### Step 2.4 — Verify RDS via SSH Tunnel *(~5 min)*

Confirm the bastion can reach RDS and credentials are valid before any application code runs against it.

```bash
# Open SSH tunnel in background (leave running while you psql)
RDS_EP=$(terraform output -raw rds_endpoint)
ssh -L 5432:${RDS_EP}:5432 pilot-bastion -N &
TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"

# Wait 3 seconds for tunnel to establish
sleep 3

# Fetch DB password from Secrets Manager
DB_PASS=$(aws secretsmanager get-secret-value --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# Connect
psql "host=localhost port=5432 dbname=pilot_prod user=pilot_user password=$DB_PASS"
```

**In the psql shell, verify:**
```sql
-- Confirm PostgreSQL version
SELECT version();
-- Expected: PostgreSQL 17.x

-- Confirm pgvector is NOT yet installed (it gets added by first Alembic migration in Phase 6)
SELECT extname FROM pg_extension WHERE extname = 'vector';
-- Expected: 0 rows (correct — pgvector is added by Alembic, not here)

-- Confirm max_connections parameter is 100
SHOW max_connections;
-- Expected: 100

\q
```

**Close the tunnel:**
```bash
kill $TUNNEL_PID
```

**Record in status doc:**
- `Step 2.4` result: can connect to RDS via tunnel (✅ / ❌)
- pgvector extension: ⬜ (correct — added by Alembic in Phase 6, not here)

---

### Step 2.5 — Verify Google Maps API Key IP Restriction *(~2 min)*

This was completed as part of Phase 1 handoff (NAT EIP `203.0.113.10` added to Google Cloud Console on 2026-07-01). Confirm it is still in place:

```bash
# Confirm the prod NAT EIP matches what was registered
terraform output nat_gateway_eip
# Expected: 203.0.113.10
```

Then verify in Google Cloud Console → APIs & Services → Credentials → `PilotForTrades-Prod` key that `203.0.113.10` is in the IP allowlist.

**Record in status doc:**
- `Step 2.5` confirmed (⬜ → ✅)
- NAT EIP `203.0.113.10` in Google Maps IP allowlist: ✅ (already done)

---

## Definition of Done

Phase 2 is complete when ALL of the following are true:

- [ ] `terraform import` for both Cognito resources succeeded
- [ ] `terraform apply -target=module.security` completed with 0 errors
- [ ] `route53_nameservers` (4 NS records) captured in [`aws-deployment-status.md`](../aws-deployment-status.md) Step 2.2
- [ ] `github_actions_role_arn` captured in [`aws-deployment-status.md`](../aws-deployment-status.md) Step 2.2
- [ ] `terraform apply -target=module.database` completed with 0 errors
- [ ] `rds_endpoint` and `redis_endpoint` captured in [`aws-deployment-status.md`](../aws-deployment-status.md) Step 2.3
- [ ] `pilot/prod/db` Secrets Manager secret has `host`, `password`, `url` populated
- [ ] `pilot/prod/redis` Secrets Manager secret has `broker_url`, `result_url`, `rate_url` populated
- [ ] RDS verified reachable via SSH tunnel: `psql` connects, `SELECT version()` returns PostgreSQL 17.x
- [ ] Phase Status Summary table in [`aws-deployment-status.md`](../aws-deployment-status.md) updated: Phase 2 → ✅ Complete · Phase 3 → ✅ Complete (merged)

---

## Completion Summary

When all steps are done, post this summary in chat:

```
## Phase 2 + Phase 3 Complete

**Date**: <date>

### Resources Provisioned
- RDS pilot-production (db.t4g.micro, pg17, Multi-AZ): ✅
- ElastiCache pilot-production (cache.t4g.micro, Redis 7.1): ✅
- KMS key (pilot-production): ✅
- Secrets Manager secrets (pilot/prod/db, pilot/prod/redis): ✅ populated
- Route 53 hosted zone (pilotfortrades.com): ✅
- Route 53 DNS records (MX, SPF, DKIM, DMARC, ACM validation): ✅
- ACM wildcard cert (*.pilotfortrades.com): PENDING (validates after Phase 5 DNS cutover)
- IAM roles (ECS task, execution, Lambda, App Runner, GitHub Actions): ✅

### Outputs Captured
- rds_endpoint: <value>
- redis_endpoint: <value>
- route53_nameservers: <NS1, NS2, NS3, NS4>
- github_actions_role_arn: <arn>

### Verification
- psql connect via SSH tunnel: ✅
- pilot/prod/db secret has host + url: ✅
- pilot/prod/redis secret has broker_url: ✅

### Issues Encountered
<list any issues or "None">

### Next Phase
Phase 4: terraform apply -target=module.compute (ECR repos + GPU instance)
```

---

## Phase 4 Preview (After Phase 2 is Complete)

Phase 4 (`module.compute`) is the next Terraform target. It creates: ECR repos (`pilot/api`, `pilot/worker`, `pilot/beat`, `pilot/web`), the EC2 g4dn.xlarge GPU instance, ALB, ECS cluster + task definitions + services, App Runner web dashboard, and CloudFront distribution. Phase 4 also depends on `module.security` outputs (ECS IAM roles, ACM cert ARN) — which will now be available since Step 2.2 ran first.

There is **no standalone `terraform apply -target=module.storage`** needed before Phase 4 — the storage module depends on `cloudfront_oac_arn` from `module.compute`, so it must run after compute:

```bash
# Phase 4 correct sequence (from infrastructure/terraform/environments/production/):
terraform apply -target=module.compute    # ECR + GPU + ALB + ECS + App Runner + CloudFront (~10–20 min)
terraform apply -target=module.storage   # S3 buckets (needs CloudFront OAC ARN from compute output)
terraform apply -target=module.monitoring # CloudWatch + GuardDuty + SNS alarms
```
