# AWS Deployment — Phase 6 Execution Prompt

**Mode**: `pilot-devops-engineer`  
**Phase**: 6 (ECS Fargate Services — Backend + Web Dashboard) — continuing from Step 6.1 complete
**Status doc**: [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md)  
**Deployment plan**: [`dev-docs/devops/aws-deployment-plan-v1.md`](../aws-deployment-plan-v1.md)  
**Platform**: AWS · `us-east-1` · HotRMC account `000000000000`

---

## ⚠️ MANDATORY STOP — Read These Docs Before Running Any Command

1. [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md) — read the **Phase 6 Step 6.1** section for the correct SSH tunnel commands, venv path, and migration results
2. [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md) Phase Status Summary — current state of all phases
3. [`infrastructure/scripts/.infra-state.env.example`](../../../infrastructure/scripts/.infra-state.env.example) — understand the infra state flags

---

## Current State (as of 2026-07-02)

| Item | Value | Status |
|---|---|---|
| AWS Account | HotRMC `000000000000` | ✅ Active |
| Current IP | Check with `curl -s https://api.ipify.org` | May need tfvars update |
| Bastion | `203.0.113.12` (`i-0xxxxxxxxxxxxxxx2`) | ✅ Running |
| RDS | `pilot-production.xxx.us-east-1.rds.amazonaws.com` | ✅ Available, schema `9b3f7ea49606` |
| Redis | `pilot-production.xxx.cache.amazonaws.com` | ✅ Available |
| CloudFront | `EXXXXXXXXXXXX2` | ✅ Live with ACM cert |
| Marketing site | `https://pilotfortrades.com` | ✅ Live (coming_soon mode) |
| ACM cert | `arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx2` | ✅ ISSUED |
| ECS cluster | `pilot-production` | ✅ Created, services NOT yet deployed |
| ECR repos | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/{api,worker,beat,web}` | ✅ Created, images NOT yet pushed |
| GPU instance | Not yet provisioned | ⬜ Pending AWS vCPU quota |

### `terraform.tfvars` Gate Variables (current)
```
acm_cert_validated = true     ✅ (set after Phase 5)
ecr_images_available = false  ← set to true AFTER Step 6.2 docker push
gpu_quota_approved = false    ← set to true AFTER AWS quota approved
```

### `.infra-state.env` Current Values
```
INFRA_NETWORKING="true"
INFRA_DATABASE="true"
INFRA_STORAGE="true"
INFRA_BASTION="true"   BASTION_INSTANCE_ID="i-0xxxxxxxxxxxxxxx2"
INFRA_GPU="false"
INFRA_ECS="false"
# Note: INFRA_APP_RUNNER removed — App Runner sunset April 30, 2026
CLOUDFRONT_DIST_ID="EXXXXXXXXXXXX2"
```

---

## Pre-Work: Verify Starting State

```bash
# 1. Correct AWS account
aws sts get-caller-identity
# Expected: "Account": "000000000000"

# 2. Check current IP — may need to add to tfvars + apply
curl -s https://api.ipify.org

# 3. Check if IP is in admin_allowed_ips
cat infrastructure/terraform/environments/production/terraform.tfvars

# 4. If IP changed, add it and apply just the SG rule:
# Edit terraform.tfvars, then:
cd infrastructure/terraform/environments/production
terraform apply -target='module.networking.aws_security_group_rule.bastion_ssh_ingress["<NEW_IP>"]' -auto-approve

# 5. Verify bastion reachable
ssh -o ConnectTimeout=10 pilot-bastion "echo bastion-ok"
```

---

## Step 6.1 — DB Reset + Re-run Migration (FIRST ACTION)

The initial migration succeeded but two bugs were found (see status doc). Before proceeding to Docker build, **reset the production DB and re-run all migrations from scratch** to verify full idempotency. No customer data exists yet — this is safe.

```bash
# Open SSH tunnel
RDS_EP="pilot-production.xxx.us-east-1.rds.amazonaws.com"
ssh -f -N -L 5432:${RDS_EP}:5432 pilot-bastion -o StrictHostKeyChecking=no
sleep 2 && nc -z localhost 5432 && echo "Tunnel ready ✅"

# Fetch password
export DB_PASS=$(aws secretsmanager get-secret-value --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# Reset schemas
PGPASSWORD="$DB_PASS" psql "host=localhost port=5432 dbname=pilot_prod user=pilot_user" << 'EOF'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO pilot_user;
DROP SCHEMA IF EXISTS audit CASCADE;
EOF

# Re-run all migrations from scratch
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5432/pilot_prod"
cd backend
.venv/bin/alembic upgrade head 2>&1 | tee /tmp/alembic-migration-prod-clean.txt

# Verify
.venv/bin/alembic current
PGPASSWORD="$DB_PASS" psql "host=localhost port=5432 dbname=pilot_prod user=pilot_user" \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

# Close tunnel
pkill -f "5432:${RDS_EP}"
```

**Expected**: All migrations run clean, `9b3f7ea49606` at head, `vector 0.8.1` installed.

---

## Step 6.2 — Docker Build + ECR Push (All 4 Images)

Check if Dockerfiles exist before building:
```bash
ls backend/Dockerfile
ls frontend/apps/web/Dockerfile    # or wherever Next.js web app lives
```

ECR login:
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  000000000000.dkr.ecr.us-east-1.amazonaws.com
```

Build and push `pilot/api` (FastAPI):
```bash
cd backend
docker build -t pilot-api .
docker tag pilot-api:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api:latest
```

Build and push `pilot/worker` (same Dockerfile, different CMD):
```bash
docker tag pilot-api:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/worker:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/worker:latest
```

Build and push `pilot/beat` (same Dockerfile, different CMD):
```bash
docker tag pilot-api:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/beat:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/beat:latest
```

Build and push `pilot/web` (Next.js web dashboard):
```bash
cd frontend/apps/web   # or wherever the Next.js app lives
docker build -t pilot-web .
docker tag pilot-web:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
```

> **Note**: `pilot/worker`, `pilot/beat`, and `pilot/api` likely use the same Docker image with different `CMD` overrides set in the ECS task definitions. Check the ECS task definitions in [`infrastructure/terraform/modules/compute/main.tf`](../../../infrastructure/terraform/modules/compute/main.tf) to confirm.

---

## Step 6.3 — Enable ECS Backend Services

After backend ECR images are pushed (Steps 6.1–6.2):

```bash
# Set gate variable
cd infrastructure/terraform/environments/production
# Edit terraform.tfvars — add:
# ecr_images_available = true

# Apply compute module (creates ECS backend services: api, worker, beat)
terraform apply -target=module.compute -auto-approve
```

> **Note**: The `pilot-web` ECS service (web dashboard) is a separate step — see Step 6.4 below. App Runner was sunset April 30, 2026 and is no longer an option. See [`dev-docs/devops/prompts/aws-phase6-step6.4-devops-engr-prompt.md`](aws-phase6-step6.4-devops-engr-prompt.md) for the complete `pilot-web` ECS service implementation.

---

## Step 6.4 — Wait for ECS Services to Stabilize

```bash
aws ecs wait services-stable \
  --cluster pilot-production \
  --services pilot-api pilot-celery-worker pilot-celery-beat \
  --region us-east-1
echo "ECS services stable ✅"
```

> This can take 3–5 minutes. If it times out, check ECS console for deployment errors.

---

## Step 6.5 — API Health Check

```bash
curl -sf https://api.pilotfortrades.com/api/v1/health/celery | python3 -m json.tool
# Expected: {"status": "healthy", "workers_active": 2, "broker_connected": true, ...}
```

---

## Step 6.6 — Web Dashboard (`pilot-web` ECS Service)

> **AWS App Runner was sunset April 30, 2026.** The web dashboard is implemented as `pilot-web`, the 4th ECS Fargate service. This is a Terraform implementation step — not a simple `curl` check.
>
> **Execute the full Phase 6 Step 6.4 implementation** using the dedicated prompt:
> [`dev-docs/devops/prompts/aws-phase6-step6.4-devops-engr-prompt.md`](aws-phase6-step6.4-devops-engr-prompt.md)
>
> After implementation:
```bash
curl -sI https://app.pilotfortrades.com | head -5
# Expected: HTTP/2 200
```

---

## Step 6.7 — Switch Marketing Site to Live Mode

```bash
aws s3 cp - s3://pilot-production-marketing/site-config.json \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "application/json" \
  --region us-east-1 <<< '{"mode":"live"}'

aws cloudfront create-invalidation \
  --distribution-id "EXXXXXXXXXXXX2" \
  --paths "/site-config.json" \
  --region us-east-1
```

---

## Step 6.8 — Update Infrastructure State

```bash
cd infrastructure/scripts
./generate-infra-state.sh
# Expected: INFRA_ECS=true (covers all 4 services: api/worker/beat/web)
# Note: INFRA_APP_RUNNER no longer exists — removed as part of Step 6.4 script updates
```

---

## Step 6.9 — Update aws-deployment-status.md

Mark Phase 6 complete in [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md) with all results.

---

## Known Issues / Watchouts

| Issue | Details |
|---|---|
| Current IP changes | Check `curl -s https://api.ipify.org` and add to `admin_allowed_ips` in `terraform.tfvars` if needed |
| `DISABLE TRIGGER ALL` on RDS | Requires superuser — use `DISABLE TRIGGER USER` instead. Already fixed in migration `7b059e2e001b`. Search all future migrations for this pattern. |
| `ADD COLUMN` without `IF NOT EXISTS` | Can fail if column exists from earlier migration. Search new migrations for this. |
| GPU instance | Pending AWS vCPU quota increase request. Set `gpu_quota_approved = true` after approval. |
| ECS task definitions | `pilot/worker`, `pilot/beat` use same image as `pilot/api` with different CMD |
| `DATABASE_URL` must be `export`ed | Setting it inline (`DATABASE_URL=... alembic`) does NOT work — must `export DATABASE_URL=...` first |
| `alembic` requires venv | Use `backend/.venv/bin/alembic`, not system `alembic` |

---

## File References

| File | Purpose |
|---|---|
| `infrastructure/terraform/environments/production/terraform.tfvars` _(private)_ | Gate variables + admin IPs |
| [`infrastructure/terraform/environments/production/main.tf`](../../../infrastructure/terraform/environments/production/main.tf) | Module wiring |
| [`infrastructure/terraform/modules/compute/main.tf`](../../../infrastructure/terraform/modules/compute/main.tf) | ECS task definitions, ECR repos |
| [`infrastructure/scripts/generate-infra-state.sh`](../../../infrastructure/scripts/generate-infra-state.sh) | Updates `.infra-state.env` |
| [`backend/Dockerfile`](../../../backend/Dockerfile) | API/worker/beat image |
| [`backend/migrations/env.py`](../../../backend/migrations/env.py) | Reads `DATABASE_URL` env var |
| [`backend/alembic.ini`](../../../backend/alembic.ini) | Alembic config (hardcoded to dev; overridden by `DATABASE_URL`) |
