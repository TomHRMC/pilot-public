# AWS Deployment Status Log — Pilot for Trades

**Account**: HotRMC (`000000000000`) · Region: `us-east-1`  
**Instructions**: [`aws-deployment-plan-v1.md`](aws-deployment-plan-v1.md) (read this for the HOW)  
**Infrastructure reference**: [`aws-infrastructure-as-built.md`](aws-infrastructure-as-built.md)  
**Operations**: [`aws-ops-runbook.md`](aws-ops-runbook.md)

> **How to use this document**: After completing each step in the deployment plan, record the result here. Include the date, what was done, any output values captured, and the verification result. This becomes the permanent deployment record.

---

## Phase Status Summary

| Phase | Description | Status | Date | Notes |
|---|---|---|---|---|
| Pre-Terraform | Secrets Manager, Cognito, SSH key, DNS zone file | ✅ Complete | 2026-06-30 | See Pre-Deployment section below |
| Phase 1 | Terraform Bootstrap + Networking | ✅ Complete | 2026-07-01 | Bastion: 203.0.113.12 · NAT EIP: 203.0.113.10 |
| Phase 2 | Data Layer (RDS + Redis) | ✅ Complete | 2026-07-02 | RDS: pilot-production.xxx.us-east-1.rds.amazonaws.com · Redis: pilot-production.xxx.cache.amazonaws.com |
| Phase 3 | Security (IAM + Lambda + ACM) | ✅ Complete | 2026-07-02 | Merged into Phase 2 — module.security applied as prerequisite |
| Phase 4 | Container Registry + GPU Instance | ✅ Complete | 2026-07-05 | ECR repos created · CloudFront EXXXXXXXXXXXX2 · GPU `i-0xxxxxxxxxxxxxxx1` · IP `10.0.10.36` · Whisper ✅ · Ollama + llama3.1:8b ✅ · `pilot/prod/gpu` secret live |
| Phase 5 | Marketing Site + DNS Cutover | ✅ Complete | 2026-07-02 | https://pilotfortrades.com HTTP/2 200 ✅ · ACM cert ISSUED 14 min post-cutover |
| Phase 5.5 | Infrastructure Script Hardening | ✅ Complete | 2026-07-02 | generate-infra-state.sh replaces all `<fill:>` vars; INFRA guards prevent ECS failures |
| Phase 6 | ECS Fargate Services (Backend + Web Dashboard) | ✅ Complete | 2026-07-03 | Steps 6.1–6.4 ✅ · API healthy · `pilot-web` ECS service running · `https://app.pilotfortrades.com` HTTP/2 200 |
| Post-Launch Ops | Profile Scripts v2 + Status Dashboard | ✅ Complete | 2026-07-04 | profile-status.sh created; all 5 profile scripts write .env.profiles; Phase 2 health checks removed from profile-c-full.sh |
| Post-Launch Ops | pilot-api Memory Leak Fix v1 | ✅ Complete | 2026-07-04 | /api/v1/health/celery kombu connection leak fixed; CloudWatch alarm pilot-production-ecs-api-memory resolved |
| Post-Launch Ops | pilot-api Memory Sizing + Leak Fix v2 | ✅ Complete | 2026-07-06 | Two-part fix: (1) 15s TTL cache on health endpoint (60× reduction in kombu connections); (2) `memory = 512 → 1024 MB` in Terraform (two uvicorn workers × ~200MB base consumed ~400MB at idle leaving only ~110MB headroom). Memory: 92.8% → 39.5%. Task definition: `pilot-api:4`. Alarms auto-resolving. |
| Post-Launch Ops | pilot-web ECS Health Check Fix | ✅ Complete | 2026-07-05 | Container health check removed (Fargate loopback fails in Alpine); ALB-only health check; pilot-production-web:4 deployed |
| Phase 7 | CI/CD Pipeline | ⛔ Deferred | — | Explicitly deferred post-beta. All deployments are manual per ops runbook §8. GitHub Actions OIDC role provisioned and ready — enabling CI/CD is a config step when the time comes. |
| Phase 8 | Observability + Alerting | ✅ Complete | 2026-07-05 | 9 CloudWatch alarms OK · SNS confirmed: `owner@example.com` + `tom@pilotfortrades.com` · `support@` pending (auto-expires ~2026-07-08, re-add optionally) · Budget $750/mo ✅ · 8 Cost Allocation Tags ✅ |

---

## Pre-Deployment (Completed Before Terraform)

### AWS Account & Identity
- **Date**: 2026-06-30
- **Account**: HotRMC `000000000000` (owner@example.com) — child OU under Root (`admin@example.com`)
- **Deployment IAM user**: `pilot-admin` — full admin, confirmed working
- **Verification**: `aws sts get-caller-identity` returns account `000000000000` ✅

### AWS Cognito — Production Pool
- **Date**: 2026-06-30
- **Pool**: `pilot-production` · ID: `us-east-1_XXXXXXXXX`
- **App Client**: `pilot-web-prod` · ID: `xxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Import commands** (run before first `terraform apply`):
  ```bash
  terraform import aws_cognito_user_pool.prod us-east-1_XXXXXXXXX
  terraform import aws_cognito_user_pool_client.prod_web us-east-1_XXXXXXXXX/xxxxxxxxxxxxxxxxxxxxxxxxxx
  ```
- **Status**: Pool created ✅; `pilot/prod/cognito` Secrets Manager secret populated ✅

### Secrets Manager — Secrets Created
- **Date**: 2026-06-30 to 2026-07-01

| Secret | Status | Date | Notes |
|---|---|---|---|
| `pilot/prod/cognito` | ✅ Created | 2026-06-30 | Pool ID + app client ID |
| `pilot/prod/encryption` | ✅ Created | 2026-06-30 | Fernet key — never log or print |
| `pilot/prod/sendgrid` | ✅ Created | 2026-06-30 | Key name: PilotForTrades-Prod |
| `pilot/prod/turnstile` | ✅ Created | 2026-06-30 | Cloudflare server-side secret |
| `pilot/prod/telnyx` | ✅ Created | 2026-06-30 | Profile ID: 00000000-0000-0000-0000-000000000000 |
| `pilot/prod/google-maps` | ✅ Created | 2026-06-30 | Distance Matrix API; restrict IP to NAT Gateway EIP after Phase 1 |
| `pilot/prod/db` | ⬜ Pending | — | Created by Terraform database module (Phase 2) |
| `pilot/prod/quickbooks` | ⬜ Pending | — | Needs production Intuit Developer app |
| `pilot/prod/stripe` | ⬜ Pending | — | Needs Stripe live mode activation |
| `pilot/prod/gpu` | ⬜ Pending | — | Populate after GPU instance starts (Phase 4) |
| `pilot/prod/redis` | ⬜ Pending | — | Created by Terraform database module (Phase 2) |

### DNS Zone File Export
- **Date**: 2026-07-01
- **Archive**: `dev-docs/devops/godaddy-archive/pilotfortrades.com.txt`
- **Key findings**: DKIM selector is `google._domainkey` (not `mail._domainkey`); DMARC RUA updated to `legal@pilotfortrades.com`; all records imported into Terraform `modules/security/main.tf`
- **Status**: All records in Terraform ✅; GoDaddy still authoritative ⚠️ (cutover in Phase 5)

### SSH Key Setup
- **Date**: 2026-06-30
- **Key file**: `~/.ssh/pilot_admin_ed25519` (ed25519, passphrase-protected)
- **Public key**: `ssh-ed25519 AAAA...REPLACE_WITH_YOUR_PUBLIC_KEY pilot-admin`
- **Keychain**: Added to macOS Keychain with passphrase ✅
- **home ISP IP**: `203.0.113.13` (set in `admin_allowed_ips` variable)
- **Status**: Ready for Terraform ✅

### GitHub Repository
- **URL**: `https://github.com/TomHRMC/pilot`
- **OIDC trust**: `repo:TomHRMC/pilot:*` (configured in `modules/security/main.tf`)
- **Status**: Configured in Terraform ✅

---

## Phase 1 — Terraform Bootstrap & Networking

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 1`](aws-deployment-plan-v1.md)
**Status**: ✅ Complete

### Step 1.1 — Terraform State Backend (S3 + DynamoDB)
- **Date completed**: 2026-07-01
- **Bucket created**: `pilot-terraform-state-000000000000` (account ID suffix required — plain name was taken globally)
- **DynamoDB table**: `pilot-terraform-locks`
- **Result**: ✅ Complete

### Step 1.2 — Terraform files (already written by DevOps engineer)
- **Status**: ✅ Complete — all modules in `infrastructure/terraform/`

### Step 1.3 — terraform init + plan

```bash
cd infrastructure/terraform/environments/production
terraform init
# Expected: "Terraform has been successfully initialized!"

terraform plan
# Review output carefully — record counts below
```

- **Date**: 2026-07-01
- **`terraform init` result**: ✅ Successful (after fixing HCL syntax errors in monitoring/main.tf + database/main.tf, gpu_userdata.sh, and backend.tf)
- **`terraform plan` result**: ✅ **Plan: 153 to add, 0 to change, 0 to destroy**
- **Fixes applied during plan debugging**:
  - `modules/monitoring/main.tf`: Dashboard widget semicolons → newlines (HCL syntax)
  - `modules/monitoring/main.tf`: `statistic = "p95"` → `extended_statistic = "p95"` (percentiles use different field)
  - `modules/database/main.tf`: `maintenance_window "Sun:..."` → `"sun:08:00-sun:09:00"` (lowercase + full format required)
  - `modules/database/main.tf`: Removed `at_rest_encryption_enabled` from `aws_elasticache_cluster` (not a valid argument)
  - `modules/compute/gpu_userdata.sh`: `${COMPOSE_VERSION}` → `$${COMPOSE_VERSION}` (escape Terraform templatefile interpolation)
  - `environments/production/backend.tf`: `dynamodb_table` → `use_lockfile = true` (deprecated parameter)
  - `environments/production/terraform.tfvars`: Created with `admin_allowed_ips` + `gpu_ami_id = "ami-0f0b6b3b68fb709eb"` (Deep Learning AMI AL2023)

**⚠️ BEFORE APPLYING — Cognito import required**: The plan will CREATE a new Cognito user pool unless the existing pool is imported first. See Step 3.2.

> After reviewing the plan output, proceed to Step 1.4.

### Step 1.4 — Apply Networking Module (VPC, Subnets, NAT, Security Groups, Bastion)

```bash
terraform apply -target=module.networking
```

- **Date**: 2026-07-01
- **Result**: ✅ Complete
- **Fixes applied**: security group em dashes → hyphens; bastion root volume 8GB → 30GB (AL2023 AMI min)
- **Terraform outputs captured**:
  - `bastion_public_ip`: **`203.0.113.12`** ← static Elastic IP
  - `nat_gateway_eip`: **`203.0.113.11`** ← NAT Gateway outbound IP

### Step 1.5 — Update `~/.ssh/config` with Bastion IP

Add to `~/.ssh/config`:
```
Host pilot-bastion
  HostName 203.0.113.12
  User ec2-user
  IdentityFile ~/.ssh/pilot_admin_ed25519
  StrictHostKeyChecking no
```

- **Date updated**: ⬜ Pending

### Step 1.6 — Update Google Maps API Key IP Restriction

- Google Cloud Console → APIs & Services → Credentials → `PilotForTrades-Prod` key → Edit
- Application restrictions → IP addresses → Add `203.0.113.10`
- **Date updated**: ⬜ Pending

### Step 1.7 — Verify Bastion SSH Access

```bash
ssh pilot-bastion
# Expected: Amazon Linux 2023 shell prompt
```

- **Date**: ⬜ Pending
- **Result**: ⬜

---

## Phase 2 — Data Layer (RDS + Redis)

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 2`](aws-deployment-plan-v1.md)
**Status**: ✅ Complete
**Date**: 2026-07-02
**Dependencies**: Phase 1 networking ✅

### Step 2.1 — Cognito Import

- **Date**: 2026-07-02
- **`terraform import module.security.aws_cognito_user_pool.prod`**: ✅
- **`terraform import module.security.aws_cognito_user_pool_client.prod_web`**: ✅
- **Also imported**: 6 pre-existing Secrets Manager secrets (cognito, encryption, turnstile, sendgrid, telnyx, google-maps)
- **`terraform plan -target=module.security` — Cognito shows no changes**: ✅
- **Fixes applied**:
  - Added `lifecycle.ignore_changes` to Cognito pool (name, lambda_config, schema, username_configuration, user_pool_add_ons)
  - Added `lifecycle.ignore_changes` to app client (generate_secret, name)
  - Removed `aws_acm_certificate_validation.wildcard` waiter (blocks on DNS validation until Phase 5 NS cutover)
  - Fixed DKIM TXT record split (two ≤255-char entries, exact split at char 237 of key)
  - Fixed all RDS parameter group `apply_method` to `pending-reboot` for static params
  - Replaced `data.aws_route53_zone.main` in `module.compute` with `var.route53_zone_id` variable
  - Fixed ECR lifecycle policy `for_each` to use `toset(local.ecr_repos)` static keys

### Step 2.2 — Apply Security Module

- **Date**: 2026-07-02
- **Result**: ✅ Complete — Apply complete! Resources: 2 added, 0 changed, 0 destroyed
- **Terraform outputs captured**:
  - `route53_nameservers`:
    - `ns-XXX.awsdns-XX.com`
    - `ns-XXX.awsdns-XX.org`
    - `ns-XXX.awsdns-XX.co.uk`
    - `ns-XXX.awsdns-XX.net`
  - `github_actions_role_arn`: `arn:aws:iam::000000000000:role/pilot-production-github-actions`
- **KMS key created**: ✅ (`alias/pilot-production`, key ID: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1`)
- **Secrets Manager shells created** (`pilot/prod/db`, `pilot/prod/redis`): ✅
- **Route 53 hosted zone created**: ✅ (zone ID: `ZXXXXXXXXXXXXXXXXXXXX`)
- **Route 53 DNS records created** (MX, SPF, DKIM, DMARC, ACM validation CNAMEs): ✅
- **ACM cert status**: PENDING_VALIDATION — `arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx2` (validates after Phase 5 GoDaddy NS cutover)
- **IAM roles created** (ECS task, ECS execution, Lambda, App Runner, GitHub Actions OIDC): ✅

### Step 2.3 — Apply Database Module

- **Date**: 2026-07-02
- **Result**: ✅ Complete — Apply complete! Resources: 3 added, 1 changed, 1 destroyed (16m31s for RDS Multi-AZ)
- **Terraform outputs captured**:
  - `rds_endpoint`: `pilot-production.xxx.us-east-1.rds.amazonaws.com` *(sensitive — do not commit)*
  - `redis_endpoint`: `pilot-production.xxx.cache.amazonaws.com` *(sensitive — do not commit)*
- **`pilot/prod/db` secret populated**: ✅ (host, username, password, dbname, url)
- **`pilot/prod/redis` secret populated**: ✅ (host, port, broker_url, result_url, rate_url)

### Step 2.4 — Verify RDS via SSH Tunnel

- **Date**: 2026-07-02
- **Result**: ✅ Connected via SSH tunnel through bastion
- **PostgreSQL version**: `17.9` ✅
- **`max_connections`**: `100` ✅
- **pgvector extension**: ⬜ not yet installed (correct — added by Alembic migration in Phase 6)

### Step 2.5 — Confirm Google Maps API Key IP Restriction

- **NAT Gateway EIP**: `203.0.113.10` (confirmed Phase 1 — already added ✅)
- **Date confirmed**: 2026-07-01 ✅

---

## Phase 3 — Security (IAM + Lambda + ACM)

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 3`](aws-deployment-plan-v1.md)
**Status**: ⚠️ Merged into Phase 2 — execute as Phase 2 Steps 2.1–2.2

> **Note**: Phase 3's `terraform apply -target=module.security` is a **prerequisite for Phase 2** (the database module depends on security module outputs). The correct execution sequence — Cognito import → `module.security` apply → `module.database` apply — is documented and tracked under Phase 2 Steps 2.1, 2.2, and 2.3 above. There is no separate `terraform apply -target=module.security` step here; it runs as Phase 2 Step 2.2.
>
> All outputs from `module.security` (`route53_nameservers`, `github_actions_role_arn`, ACM cert ARN) are captured under Phase 2 Step 2.2 results above.

### Outputs to capture after Phase 2 Step 2.2 completes

- **`route53_nameservers`**: `<fill after terraform apply -target=module.security>` ← needed for GoDaddy cutover in Phase 5
- **`github_actions_role_arn`**: `<fill>` ← embed in `.github/workflows/deploy-production.yml`
- **ACM certificate status**: PENDING (validates automatically after GoDaddy NS cutover in Phase 5)

---

## Phase 4 — Container Registry + GPU Instance

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 4`](aws-deployment-plan-v1.md)
**Status**: ✅ Complete (GPU gated pending AWS vCPU quota increase)
**Date**: 2026-07-02

### Step 4.1 — module.compute (ECR + ALB + ECS cluster + CloudFront)

- **Date**: 2026-07-02
- **Result**: ✅ Apply complete
- **Terraform outputs captured**:
  - `ecr_api_url`: `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api`
  - `ecr_worker_url`: `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/worker`
  - `ecr_beat_url`: `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/beat`
  - `ecr_web_url`: `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web`
  - `cloudfront_distribution_id`: `EXXXXXXXXXXXX2`
  - `gpu_private_ip`: `null` — GPU gated by `gpu_quota_approved = false`
  - `app_runner_service_url`: `null` — App Runner gated by `ecr_images_available = false`
- **Gated resources** (set variables to `true` after prerequisites met):
  - `gpu_quota_approved = true` — after AWS Service Quotas approves G instance vCPU increase
  - `ecr_images_available = true` — after Phase 6 first docker push
  - `acm_cert_validated = true` — after Phase 5 GoDaddy NS cutover

### Step 4.2 — module.storage (S3 buckets)

- **Date**: 2026-07-02
- **Result**: ✅ Apply complete
- **Buckets created**:
  - `pilot-production-assets-000000000000` (KMS-encrypted, versioned, private)
  - `pilot-production-marketing` (AES256, versioned, CloudFront OAC policy)

### Step 4.3 — module.monitoring (CloudWatch + GuardDuty + Security Hub + SNS)

- **Date**: 2026-07-02
- **Result**: ✅ Apply complete
- **Outputs**:
  - `sns_alarm_topic_arn`: `arn:aws:sns:us-east-1:000000000000:pilot-production-alarms`
- **⚠️ ACTION REQUIRED**: Check email `support@pilotfortrades.com` for SNS subscription confirmation email — must click link to activate alarm notifications

### Step 4.4 — GPU Instance

- **Date**: 2026-07-05
- **Status**: ✅ Complete
- **Action taken**: AWS Service Quotas approved 4 vCPUs for G+VT instances → Set `gpu_quota_approved = true` in `terraform.tfvars` → `terraform apply -target=module.compute`
- **GPU AMI**: `ami-0f1af563a991b2513` (Deep Learning AMI AL2023, 64-bit x86, us-east-1)
- **Instance ID**: `i-0xxxxxxxxxxxxxxx1`
- **GPU private IP**: `10.0.10.36`
- **NVIDIA GPU**: Tesla T4, 15360 MiB VRAM
- **Bootstrap**: [`gpu_userdata.sh`](../../infrastructure/terraform/modules/compute/gpu_userdata.sh) ran on first boot — Docker Compose v2 installed, `/models` EBS mounted, `pilot-whisper` + `pilot-ollama` containers started, `pilot-gpu.service` systemd registered for auto-restart
- **Verification results (2026-07-05)**:
  - `pilot-whisper` container: `Up`, `http://localhost:8080/health` → `OK` ✅
  - `pilot-ollama` container: `Up`, `http://localhost:11434/api/tags` → `['llama3.1:8b']` ✅
  - `llama3.1:8b` model: pulled (4.9 GB) and available ✅
  - VRAM at rest: `0 MiB used / 14913 MiB free` — models load into VRAM on first inference request (expected)
  - Projected VRAM under load: ~1.5 GB (Whisper) + ~4.7 GB (Ollama) = ~6.2 GB / 16 GB T4

> **Note on Ollama Docker healthcheck**: Container shows `unhealthy` status in `docker ps` because the healthcheck pings `http://localhost:11434` (root endpoint) which returns `Ollama is running` as plain text — not a JSON 200 that curl `-f` interprets as success. The API itself is fully functional (`/api/tags`, `/api/generate` both work). This is a cosmetic issue in the healthcheck definition only.

### Step 4.5 — Populate `pilot/prod/gpu` Secret

- **Date**: 2026-07-05
- **Status**: ✅ Complete
- **Secret ARN**: `arn:aws:secretsmanager:us-east-1:000000000000:secret:pilot/prod/gpu-XXXXXX`
- **GPU private IP**: `10.0.10.36`
- **Secret value set**:
  ```json
  {
    "whisper_url": "http://10.0.10.36:8080/v1",
    "ollama_url": "http://10.0.10.36:11434/api"
  }
  ```
- **ECS redeployments triggered**: `pilot-api` + `pilot-celery-worker` force-new-deployment → tasks now consume real GPU URLs from Secrets Manager ✅
- **`INFRA_GPU`**: Flipped to `"true"` in `.infra-state.env` via `generate-infra-state.sh` ✅

---

## Phase 5 — Marketing Site + DNS Cutover

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 5`](aws-deployment-plan-v1.md)
**Status**: ✅ Complete
**Date**: 2026-07-02

### Step 5.1 — Verify Route 53 DNS records (pre-cutover check)

- **Date**: 2026-07-02
- **MX resolves correctly**: ✅ (5 Google Workspace records)
- **SPF resolves correctly**: ✅ (`v=spf1 include:_spf.google.com ~all`)
- **DKIM resolves correctly**: ✅ (two-chunk key, split at char 237)
- **DMARC resolves correctly**: ✅ (`p=quarantine; rua=mailto:legal@pilotfortrades.com`)

### Step 5.2 — GoDaddy Nameserver Cutover

- **Date**: 2026-07-02
- **Old NS**: `ns15.domaincontrol.com` / `ns16.domaincontrol.com`
- **New NS**: ns-XXX.awsdns-XX.com · ns-XXX.awsdns-XX.org · ns-XXX.awsdns-XX.co.uk · ns-XXX.awsdns-XX.net
- **Cutover completed**: ✅
- **NS propagation**: Confirmed globally within ~1 minute

### Step 5.3 — ACM Cert Validation

- **Date**: 2026-07-02
- **ACM cert status**: ✅ **ISSUED** (~14 minutes after GoDaddy NS cutover)
- **ACM cert ARN**: `arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx2`
- **Validation CNAME resolved**: ✅ (confirmed before validation completed)

### Step 5.4 — Set acm_cert_validated=true + terraform apply

- **Date**: 2026-07-02
- **`acm_cert_validated = true`** set in `terraform.tfvars` ✅
- **`terraform apply -target=module.compute`**: ✅
- **ALB HTTPS listener**: ✅ Created (port 443, TLS 1.3, ACM cert)
- **CloudFront cert updated**: ✅ Default cert → ACM cert, sni-only, TLSv1.2_2021
- **CloudFront aliases**: ✅ `pilotfortrades.com` + `www.pilotfortrades.com`

### Step 5.5 — Deploy Marketing Site to S3

- **Date**: 2026-07-02
- **S3 sync**: ✅ (`frontend/apps/marketing/out/` → `s3://pilot-production-marketing/`)
- **`site-config.json` mode**: `coming_soon` (switch to `live` after Phase 6 ECS running)
- **CloudFront invalidation**: ✅ `IXXXXXXXXXXXXXXXXXXXXXXXXX`
- **Distribution ID**: `EXXXXXXXXXXXX2`

### Step 5.6 — Verify Marketing Site Live

- **Date**: 2026-07-02
- **`https://pilotfortrades.com`**: ✅ HTTP/2 200
- **`https://www.pilotfortrades.com`**: ✅ HTTP/2 200
- **HTTPS (valid cert)**: ✅ ACM cert, TLSv1.2_2021
- **Email test (external → support@pilotfortrades.com)**: ⬜ Pending manual test

### Step 5.7 — 10DLC Checklist

- [x] `https://pilotfortrades.com` loads correctly
- [ ] Privacy Policy with 10DLC clause — verify page accessible
- [ ] `sms-opt-in/` page accessible
- [ ] `legal@pilotfortrades.com` working — send test email
- [ ] EIN + legal name ready
- [ ] 10DLC registration submitted to Telnyx on: `<date>`

---

## Phase 5.5 — Infrastructure Script Hardening

**Reference**: [`dev-docs/devops/prompts/aws-phase55-script-hardening-prompt.md`](prompts/aws-phase55-script-hardening-prompt.md)
**Status**: ✅ Complete
**Date**: 2026-07-02

> **Approach changed**: Instead of manually filling `<fill:>` placeholders, a `generate-infra-state.sh` script dynamically discovers all resource IDs from live AWS state and writes `.infra-state.env`. All 4 profile scripts source this file at startup.

### Step 5.5.1 — generate-infra-state.sh Created and Run

```bash
cd infrastructure/scripts
./generate-infra-state.sh
```

- **Date**: 2026-07-02
- **`infrastructure/scripts/generate-infra-state.sh`**: ✅ created + `chmod +x`
- **`infrastructure/scripts/.infra-state.env.example`**: ✅ created (committed reference)
- **`infrastructure/scripts/.infra-state.env`**: ✅ generated (gitignored)
- **`.gitignore`**: ✅ updated with `infrastructure/scripts/.infra-state.env`

**Current `.infra-state.env` values (Phase 5 state):**
```
INFRA_NETWORKING="true"
INFRA_DATABASE="true"
INFRA_STORAGE="true"
INFRA_BASTION="true"   (BASTION_INSTANCE_ID=i-0xxxxxxxxxxxxxxx2)
INFRA_GPU="false"       (pending AWS vCPU quota — Phase 4)
INFRA_ECS="false"       (pending Phase 6 — covers api/worker/beat/web when all 4 ACTIVE)
CLOUDFRONT_DIST_ID="EXXXXXXXXXXXX2"
```

### Step 5.5.2 — All 4 Profile Scripts Modified

- **`profile-a-marketing.sh`**: ✅ `── Variables ──` block → `source .infra-state.env`; GPU/AppRunner/ECS/CloudFront guards added
- **`profile-b-app.sh`**: ✅ `── Variables ──` block → `source .infra-state.env`; GPU/AppRunner/ECS/CloudFront guards added
- **`profile-c-checklist.sh`**: ✅ `── Variables ──` block → `source .infra-state.env`; all guards + check_skip() for unprovisioned resources
- **`profile-off.sh`**: ✅ `── Variables ──` block → `source .infra-state.env`; GPU/AppRunner/ECS/Bastion/CloudFront guards added
- **All scripts**: `set -euo pipefail` → `set -eo pipefail` (removed `-u` for safe env var handling)

### Step 5.5.3 — Documentation Updated

- **`aws-ops-runbook.md`**: ✅ New `## 10. Infrastructure State Management` section added (when to run, flag table, resource ID table, [SKIP] behavior)
- **`aws-infrastructure-as-built.md`**: ✅ Known output values filled in (CloudFront, GitHub Actions ARN, SNS ARN, Bastion ID); `generate-infra-state.sh` noted as source

### Step 5.5.4 — Verification

Run after Phase 6 ECS deployment:
```bash
cd infrastructure/scripts
./generate-infra-state.sh   # re-run to pick up new ECS + App Runner resources
./profile-off.sh            # verify runs end-to-end, ECS blocks skip gracefully
./profile-a-marketing.sh    # verify marketing site flow
```

---

## Phase 6 — ECS Fargate Services (Backend + Web Dashboard)

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 6`](aws-deployment-plan-v1.md)
**Status**: 🔄 In Progress
**Dependencies**: Phase 2 (RDS + Redis) ✅, Phase 4 (ECR + GPU) ✅

### Step 6.1 — DB Reset + Full Migration Clean Run (Idempotency Proof)

**Date**: 2026-07-02
**Status**: ✅ Complete — full clean-run idempotency confirmed, `9b3f7ea49606` (head)

#### Correct Commands (with bastion SSH tunnel)

```bash
# Step 1 — Open SSH tunnel to RDS via bastion
# Uses -f (background) -N (no command) so it runs in background
# The bastion routes: localhost:5432 → VPC private → RDS:5432
RDS_EP="pilot-production.xxx.us-east-1.rds.amazonaws.com"
ssh -f -N -L 5432:${RDS_EP}:5432 pilot-bastion -o StrictHostKeyChecking=no

# Verify tunnel is working
nc -z localhost 5432 && echo "Tunnel ready ✅"

# Step 2 — Fetch DB password from Secrets Manager
export DB_PASS=$(aws secretsmanager get-secret-value --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# Step 3 — Run Alembic using venv (DATABASE_URL must be exported, not inline)
# Note: alembic.ini has sqlalchemy.url hardcoded to dev db; migrations/env.py
# overrides it when DATABASE_URL env var is set (added 2026-07-02)
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5432/pilot_prod"
cd backend
.venv/bin/alembic upgrade head 2>&1 | tee /tmp/alembic-migration-prod.txt

# Verify current revision
.venv/bin/alembic current

# Verify pgvector installed
PGPASSWORD="$DB_PASS" psql "host=localhost port=5432 dbname=pilot_prod user=pilot_user" \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

# Step 4 — Close SSH tunnel when done
pkill -f "5432:${RDS_EP}"
```

#### To Reset DB and Re-run From Scratch (no customer data yet)

```bash
# Open tunnel first (see Step 1 above), then:
PGPASSWORD="$DB_PASS" psql "host=localhost port=5432 dbname=pilot_prod user=pilot_user" << 'EOF'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO pilot_user;
DROP SCHEMA IF EXISTS audit CASCADE;
EOF

# Re-run migrations
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5432/pilot_prod"
cd backend && .venv/bin/alembic upgrade head 2>&1 | tee /tmp/alembic-migration-prod-reset.txt
```

#### SSH Tunnel Quick Reference

```bash
# Open tunnel (background, non-blocking)
ssh -f -N -L 5432:${RDS_EP}:5432 pilot-bastion

# Check if tunnel is open
nc -z localhost 5432 && echo "open" || echo "closed"
ps aux | grep "5432:pilot-production"

# Kill tunnel
pkill -f "5432:pilot-production.xxx"
```

#### Migration Fixes Applied (RDS compatibility)

Two bugs found in migration `7b059e2e001b_phase_fe_1_batch_b13_mfa_policy_settings.py`:
1. `DISABLE TRIGGER ALL` → `DISABLE TRIGGER USER` — RDS requires superuser for ALL; USER is sufficient for user-defined triggers
2. `ADD COLUMN` → `ADD COLUMN IF NOT EXISTS` — columns already existed from initial schema (`17aa292ece75`)

#### Clean-Run Results (2026-07-02)

- **Migration result**: ✅ All migrations applied clean from scratch
- **Schema version**: `9b3f7ea49606` (head)
- **pgvector**: `vector 0.8.1` ✅
- **Schemas**: `public` (all application tables) + `audit` (audit trail)
- **Table count**: 183 tables in `public`
- **Idempotency**: ✅ Confirmed — full DROP + recreate + all migrations ran without errors

#### Issues Encountered and Resolved (Clean-Run Session)

| Issue | Root Cause | Resolution |
|---|---|---|
| `NotNullViolation: null value in column "entity_id"` in migration `88131acac5f1` | `SET LOCAL session_replication_role = 'replica'` requires superuser on RDS — silently failed, audit trigger fired on seed INSERT, `email_template` has `TEXT` PK (not UUID), `audit.log_changes()` expected `entity_id` | Python engineer fixed migration: seed INSERT now runs before audit trigger is created |
| `DuplicateTable: relation "email_template" already exists` on retry | `SET LOCAL session_replication_role = 'replica'` broke transactional DDL boundary on RDS — `CREATE TABLE` DDL from the failed migration was partially committed (orphaned table) while Alembic version stayed at `220cfa33d815` | Dropped orphaned table via raw SQL (`DROP TABLE IF EXISTS email_template CASCADE`) — safe, no customer data |
| `FATAL: password authentication failed` connecting to `localhost:5432` | Docker owns port 5432 (`com.docker` binding `*:postgresql`) — SSH tunnel was either pre-empted or `nc -z` was testing Docker not RDS | Reopened tunnel on port `5433` (`ssh -f -N -L 5433:<RDS>:5432 pilot-bastion`); used `127.0.0.1:5433` in all subsequent commands |

#### ⚠️ Important: Always Use Port 5433 for PROD RDS Tunnel

Docker (local dev) owns `*:5432` when running. Always use port `5433` for the PROD SSH tunnel:
```bash
RDS_EP="pilot-production.xxx.us-east-1.rds.amazonaws.com"
ssh -f -N -L 5433:${RDS_EP}:5432 pilot-bastion
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"
```

### Step 6.2 — Docker Build + ECR Push (3 of 4 images)

**Date**: 2026-07-02
**Status**: ✅ 3 of 4 images pushed — `pilot/web` blocked pending React engineer Dockerfile

#### Terraform Bug Fixed

**`pilot/api` task definition was missing `command` override** — the Dockerfile default CMD is `celery worker`, which would have launched the API container as a Celery worker instead of a FastAPI server. Fixed in [`infrastructure/terraform/modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf):
```hcl
command = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

#### Build Details

- **Platform**: `linux/amd64` (required — Mac is arm64; ECS Fargate is x86_64)
- **Base image**: `python:3.14.3-slim`
- **Built from**: `backend/Dockerfile`
- **Image size**: 567MB
- **Same image digest** (`<digest>`) tagged for all 3 backend ECR repos

#### ECR Push Results

| Image | ECR Repo | Tag | Pushed At | Size | Status |
|---|---|---|---|---|---|
| pilot-api | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api` | `latest` | 2026-07-02 16:09 ET | 567MB | ✅ |
| pilot-worker | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/worker` | `latest` | 2026-07-02 16:12 ET | 567MB | ✅ |
| pilot-beat | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/beat` | `latest` | 2026-07-02 16:14 ET | 567MB | ✅ |
| pilot-web | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web` | — | — | — | ⬜ Blocked |

#### ⚠️ `ecr_images_available` NOT YET SET — Waiting on `pilot/web`

`ecr_images_available` gates ECS backend services. The `pilot/web` image is built and confirmed working locally. Before creating the `pilot-web` ECS service (Step 6.4), confirm `pilot/web:latest` exists in ECR:

```bash
aws ecr describe-images --repository-name pilot/web \
  --query 'imageDetails[?contains(imageTags, `latest`)]' \
  --output table --region us-east-1
```

**`apps/web/Dockerfile`**: Confirmed working locally (`GET /api/health → HTTP 200`). Image is ready for ECR push.

#### Step 6.2 Remaining — After `pilot/web` Dockerfile is ready

```bash
# 1. Build + push pilot/web
cd frontend/apps/web
docker build --platform linux/amd64 -t pilot-web .
docker tag pilot-web:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest

# 2. Set gate variable in terraform.tfvars:
#    ecr_images_available = true

# 3. Apply compute module (creates ECS services + App Runner)
cd infrastructure/terraform/environments/production
terraform apply -target=module.compute -auto-approve
```

### Step 6.3 — ECS Services Running + API Health Check

**Date**: 2026-07-02
**Status**: ✅ All ECS services at desired capacity and API returning healthy

#### ECS Service State (confirmed 2026-07-02 23:16 ET)

| Service | Desired | Running | Status |
|---|---|---|---|
| `pilot-api` | 2 | 2 | ✅ ACTIVE |
| `pilot-celery-worker` | 2 | 2 | ✅ ACTIVE |
| `pilot-celery-beat` | 1 | 1 | ✅ ACTIVE |

#### API Health Check (live)

```bash
curl https://api.pilotfortrades.com/api/v1/health/celery
# Response:
{
  "status": "healthy",
  "workers_active": 2,
  "broker_connected": true,
  "scheduled_tasks": 0,
  "timestamp": "2026-07-02T23:16:09.557657Z"
}
```

#### Issues Encountered and Resolved During ECS Launch

| Issue | Root Cause | Resolution |
|---|---|---|
| ECS tasks failed with `ResourceInitializationError` on `pilot/prod/stripe` | Secret shell had no `AWSCURRENT` version — was listed as "Pending" in pre-deployment checklist | Populated `pilot/prod/stripe` with placeholder values via AWS CLI |
| Same error on `pilot/prod/quickbooks` and `pilot/prod/gpu` | Same — both were empty secret shells | Populated both with placeholder values |
| ECS deployment circuit breaker tripped — stopped retrying | Secrets were fixed but circuit breaker had already declared failure | Ran `aws ecs update-service --force-new-deployment` on all 3 services |
| ALB health check `Target.ResponseCodeMismatch` | Health check path `/api/v1/health` doesn't exist — only `/api/v1/health/celery` | Updated both blue+green target group health check paths via AWS CLI + Terraform |
| ALB target group Terraform fix | Both `api_blue` and `api_green` TGs had wrong path | Fixed in [`modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf) |

#### ⚠️ Placeholder Secrets — Must Be Updated Before Beta Launch

| Secret | Current State | Action Required |
|---|---|---|
| `pilot/prod/stripe` | Placeholder keys — Stripe features disabled | Activate Stripe live mode; get real `sk_live_` / `pk_live_` / `whsec_` values |
| `pilot/prod/quickbooks` | Placeholder values — QB sync disabled | Activate QuickBooks production app; get real `client_id` / `client_secret` |
| `pilot/prod/gpu` | Localhost placeholders — Voice AI disabled | Populate after GPU instance launches (Phase 4 GPU approval) |

### Step 6.4 — ECS Fargate Web Service (`pilot-web`)

**Date**: 2026-07-03
**Status**: ✅ Complete

**Background**: AWS App Runner was sunset April 30, 2026. The `pilot/web:latest` ECR image was confirmed working. Architecture redesign: `pilot-web` runs as the 4th ECS Fargate service on the existing `pilot-production` cluster, sharing the existing ALB via a `Host: app.pilotfortrades.com` listener rule at priority 10.

**DevOps Engineer prompt**: [`dev-docs/devops/prompts/aws-phase6-step6.4-devops-engr-prompt.md`](prompts/aws-phase6-step6.4-devops-engr-prompt.md)

#### Terraform Resources Created

| Resource | ID / ARN |
|---|---|
| `aws_security_group.sg_web` | `sg-0xxxxxxxxxxxxxxxx` |
| `aws_lb_target_group.web` | `arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/pilot-production-web/xxxxxxxxxxxxxxxx` |
| `aws_lb_listener_rule.web` | `arn:aws:elasticloadbalancing:us-east-1:000000000000:listener-rule/app/pilot-production-alb/xxxxxxxxxxxxxxxx/xxxxxxxxxxxxxxxx/xxxxxxxxxxxxxxxx` |
| `aws_ecs_task_definition.web` | `pilot-production-web` |
| `aws_ecs_service.web` | `arn:aws:ecs:us-east-1:000000000000:service/pilot-production/pilot-web` |
| `aws_cloudwatch_log_group.web` | `/ecs/pilot-production-web` |
| `aws_route53_record.app` | `ZXXXXXXXXXXXXXXXXXXXX_app.pilotfortrades.com_A` (A alias → ALB) |

#### Terraform Resources Removed

| Resource | Reason |
|---|---|
| `aws_apprunner_service.web` | App Runner sunset April 30, 2026 |
| `aws_iam_role.app_runner` | No longer needed |
| `aws_iam_role_policy_attachment.app_runner_ecr` | No longer needed |

#### Issues Encountered

| Issue | Resolution |
|---|---|
| Stale Terraform state lock from previous session (ID: `00000000-0000-0000-0000-000000000000`) | Force-unlocked with `terraform force-unlock -force` |
| SG description contained em dash (`—`) — AWS rejects non-ASCII in SG descriptions | Changed to ASCII hyphen (`-`) and re-applied |

#### Verification Results (2026-07-03)

```bash
curl -sI https://app.pilotfortrades.com | head -1
# HTTP/2 200 ✅

curl -sf https://app.pilotfortrades.com/api/health
# {"status":"ok","service":"pilot-web"} ✅

./generate-infra-state.sh
# INFRA_ECS=true (all 4 services: pilot-api, pilot-celery-worker, pilot-celery-beat, pilot-web) ✅
# INFRA_APP_RUNNER no longer present ✅
```

- **Terraform applied**: ✅ (2026-07-03 — 8 resources added, 2 destroyed)
- **`pilot-web` ECS service ACTIVE**: ✅ (Running=1, Desired=1)
- **`app.pilotfortrades.com` DNS**: ✅ (A alias → ALB, replacing old CNAME)
- **`app.pilotfortrades.com` HTTP/2 200**: ✅
- **`/api/health` JSON response**: ✅

### Step 6.5 — Marketing Site switch to Live Mode

After ECS is confirmed healthy, switch marketing site from Coming Soon to Live:

```bash
DIST_ID=$(terraform output -raw cloudfront_distribution_id)
aws s3 cp - s3://pilot-production-marketing/site-config.json \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "application/json" <<< '{"mode":"live"}'
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/site-config.json"
```

- **Date**: —
- **Marketing forms working**: ⬜

### Step 6.6 — Update Profile Script Variables

After all resources are provisioned, update variable placeholders in all profile scripts:

```bash
# Get values
GPU_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-gpu" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)
BASTION_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-bastion" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)
DIST_ID=$(terraform output -raw cloudfront_distribution_id)

echo "GPU_INSTANCE_ID: $GPU_ID"
echo "BASTION_INSTANCE_ID: $BASTION_ID"
echo "CLOUDFRONT_DIST_ID: $DIST_ID"
```

> **Note**: `APP_RUNNER_ARN` has been removed — App Runner is sunset. `INFRA_APP_RUNNER` flag removed from `generate-infra-state.sh` as part of Step 6.4 DevOps Engineer work.

Fill these into `infrastructure/scripts/profile-*.sh` (replace all `<fill: ...>` placeholders):

- **GPU_INSTANCE_ID**: `<fill>`
- **BASTION_INSTANCE_ID**: `<fill>`
- **CLOUDFRONT_DIST_ID**: `<fill>`
- **Date updated**: —

---

## Phase 7 — CI/CD Pipeline

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 7`](aws-deployment-plan-v1.md)
**Status**: ⛔ Deferred — manual deployments only

> **Decision (2026-07-03)**: CI/CD via GitHub Actions is explicitly deferred post-beta. After 6 phases of infrastructure deployment, the complexity of the stack makes automated pipelines hard to keep reliable without dedicated maintenance effort. Manual deployments per the ops runbook §8 are the standard workflow. The GitHub Actions OIDC role (`pilot-production-github-actions`) is provisioned and ready; enabling CI/CD is a configuration step (no new infrastructure required) when the time comes.
>
> **When to revisit**: After reaching first paying customers and feeling confident in the manual deploy workflow. Suggested trigger: 3+ successful manual deploy cycles without issues.
>
> **What is already in place** (no work needed when resuming):
> - IAM OIDC role: `arn:aws:iam::000000000000:role/pilot-production-github-actions` ✅
> - GitHub Actions workflow file: `.github/workflows/deploy-production.yml` (written in plan, ready to enable)
> - `CLOUDFRONT_DISTRIBUTION_ID` = `EXXXXXXXXXXXX2` (already known)
> - ECR repos and ECS clusters: fully operational ✅
>
> See [`aws-ops-runbook.md §8`](aws-ops-runbook.md) for all manual deployment procedures.

---

## Phase 8 — Observability + Alerting

**Reference**: [`aws-deployment-plan-v1.md §5 Phase 8`](aws-deployment-plan-v1.md)
**Status**: 🔄 Partial — see step details below

### Step 8.1 — Confirm SNS Email Subscription

- **Date**: 2026-07-05
- **SNS topic ARN**: `arn:aws:sns:us-east-1:000000000000:pilot-production-alarms`

| Subscriber | Status | Notes |
|---|---|---|
| `tom@pilotfortrades.com` | ✅ Confirmed | **Primary alarm address** — added manually via console; Terraform-managed (`var.alarm_email`) after 2026-07-05 apply |
| `owner@example.com` | ❌ Deleted | Removed — `tom@pilotfortrades.com` is the preferred address |
| `support@pilotfortrades.com` | ⚠️ `PendingConfirmation` | AWS SNS confirmation email never arrived (Google Workspace filtering). Not re-adding after expiry — `tom@pilotfortrades.com` is the canonical address going forward. Auto-expires ~2026-07-08. |

> **Terraform**: `alarm_email = "tom@pilotfortrades.com"` set in `terraform.tfvars` and `variables.tf` default updated. `aws_sns_topic_subscription.email` in [`modules/monitoring/main.tf`](../../infrastructure/terraform/modules/monitoring/main.tf) now manages this subscription.

#### CloudWatch Alarms — Live State (2026-07-05)

11 alarms total — final state 2026-07-05:

| Alarm | Threshold | Eval Periods | State |
|-------|-----------|-------------|-------|
| `pilot-production-alb-unhealthy-hosts` | >0 unhealthy | 2 × 5min | ✅ OK |
| `pilot-production-api-error-rate` | >5% 5xx | 3 × 5min | ✅ OK |
| `pilot-production-api-p95-latency` | >2000ms | 3 × 5min | ✅ OK |
| `pilot-production-ecs-api-cpu` | >70% | 3 × 5min | ✅ OK |
| `pilot-production-ecs-api-memory` | >80% for 15min | 3 × 5min | ✅ OK |
| `pilot-production-ecs-api-memory-critical-90` | >90% for 5min | 1 × 5min | ✅ OK |
| `pilot-production-gpu-status-check` | StatusCheck fail | 2 × 1min | ✅ OK |
| `pilot-production-rds-connections` | >80 | 2 × 5min | ✅ OK |
| `pilot-production-rds-cpu` | >60% | 2 × 5min | ✅ OK |
| `pilot-production-rds-free-storage` | <5GB | 1 × 5min | ✅ OK |
| `pilot-production-redis-cpu` | >60% | 2 × 5min | ✅ OK |

> **ECS API memory escalation ladder**: `ecs-api-memory` (>80% for 15 min) → investigate → `ecs-api-memory-critical-90` (>90% for 5 min) → act immediately, force-redeploy or scale.
> 70% and 75% warning alarms created and immediately removed 2026-07-05 — `pilot-api` idles at 70–78% in light mode (1 task / 512MB), placing those thresholds inside the normal operating range.
>
> **GPU status check**: `treat_missing_data = notBreaching` — EC2 `StatusCheckFailed` metric takes ~2 min to start publishing; `breaching` caused false-alarm on first apply (fixed 2026-07-05).

### Step 8.2 — Activate Cost Allocation Tags

- **Date**: 2026-07-05
- **Status**: ✅ Complete — activated via Root account console (`admin@example.com`)
- **Note**: CLI activation not possible from linked/member accounts — `UpdateCostAllocationTagsStatus` returns `AccessDeniedException` for non-root accounts. Required console login as Root org account.
- **Tags activated**:
  - [x] `Project`
  - [x] `Environment`
  - [x] `Owner`
  - [x] `ManagedBy`
  - [x] `CostCenter`
  - [x] `Component`
  - [x] `Service`
  - [x] `CostAllocation`

### Step 8.3 — Set AWS Budget Alert

- **Date**: 2026-07-05
- **Status**: ✅ Complete — created via CLI
- **Budget name**: `pilot-production-monthly`
- **Budget amount**: $750/month
- **Alert thresholds**:
  - 80% actual ($600) → email `support@pilotfortrades.com`
  - 100% actual ($750) → email `support@pilotfortrades.com`

---

## Pre-Load-Testing Action Items

> Items identified during deployment that are deferred until load testing begins.

| Item | Current State | Action Required | Trigger |
|------|--------------|-----------------|---------|
| **ECS `pilot-api` task memory** | ✅ **Resolved 2026-07-06** — `memory = 1024 MB` applied via `terraform apply -target=module.compute`; `pilot-api:4` deployed. Idle utilization: ~39.5% (was 92.8%). 80% and 90% alarms auto-resolving. Root cause: two uvicorn workers × ~200MB Python heap base = ~400MB at idle leaving only ~110MB headroom; compounded by kombu broadcast consumer leak from ALB health checks at 240/hr (fixed with 15s TTL cache on `/api/v1/health/celery`). | No further action needed. | — |

---

## Issues Log

| Date | Phase/Step | Issue | Resolution | Status |
|---|---|---|---|---|
| 2026-07-02 | Phase 4 Step 4.1 | GPU AMI architecture mismatch — `ami-0f0b6b3b68fb709eb` is arm64, g4dn.xlarge is x86_64 | Corrected to `ami-0f1af563a991b2513` (64-bit x86) | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.1 | GPU vCPU limit 0 — g4dn.xlarge requires Service Quota increase | Added `gpu_quota_approved` variable; GPU gated until quota approved | ⬜ Pending quota |
| 2026-07-02 | Phase 4 Step 4.1 | ECS service `depends_on = [aws_lb_listener.https]` blocked creation (count=0 resource) | Changed to `depends_on = [aws_lb_listener.http_redirect, aws_lb.api]` | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.1 | ECS services blocked — ECR images don't exist yet | Added `ecr_images_available` variable; backend services gated until Phase 6 docker push | ✅ Resolved |
| 2026-07-02 | Phase 6 Step 6.4 | AWS App Runner sunset April 30, 2026 — new services cannot be created | Architecture redesign: `pilot-web` ECS Fargate service on existing cluster; ALB listener rule (priority 10, `Host: app.pilotfortrades.com`) | ✅ Resolved |
| 2026-07-03 | Phase 6 Step 6.4 | Stale Terraform state lock from 2026-07-02 session | `terraform force-unlock -force 00000000-0000-0000-0000-000000000000` | ✅ Resolved |
| 2026-07-03 | Phase 6 Step 6.4 | AWS SG description rejected non-ASCII em dash character | Changed `—` to `-` in `sg_web` description | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.1 | CloudFront + ALB HTTPS listener require validated ACM cert | Added `acm_cert_validated` variable; gated until Phase 5 DNS cutover | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.1 | ECR lifecycle `for_each = aws_ecr_repository.repos` caused unknown-value error during apply | Changed to `toset(local.ecr_repos)` with `each.key` | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.1 | Fargate beat task `memory = 256` invalid (min 512 for 256 CPU) | Changed to `memory = 512` | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.2 | `pilot-production-assets` bucket name taken globally | Renamed to `pilot-production-assets-000000000000` (account ID suffix) | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.3 | CloudWatch dashboard widgets missing `region` field | Added `region = var.aws_region` to all metric widget properties | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.3 | Security Hub standards subscription timeout (3 min) | Extended timeout to `10m` | ✅ Resolved |
| 2026-07-02 | Phase 4 Step 4.3 | Config logs S3 bucket `must be replaced` due to `data.aws_caller_identity.account_id` "known after apply" | Added `lifecycle.ignore_changes = [bucket]` + `prevent_destroy = true` | ✅ Resolved |
| 2026-07-02 | Phase 2 Step 2.1 | Cognito import failed — resource address wrong (used `aws_cognito_user_pool.prod` instead of `module.security.aws_cognito_user_pool.prod`) | Used full module path for import | ✅ Resolved |
| 2026-07-02 | Phase 2 Step 2.1 | `data.aws_route53_zone.main` in `module.compute` caused import to fail (zone not created yet) | Replaced data source with `var.route53_zone_id` passed from `module.security` | ✅ Resolved |
| 2026-07-02 | Phase 2 Step 2.1 | Cognito pool forced replacement — name mismatch (`"pilot - prod"` vs `"pilot-production"`) and `user_pool_add_ons` ESSENTIALS tier error | Added `lifecycle.ignore_changes` for `name`, `user_pool_add_ons`, `lambda_config`, `schema` | ✅ Resolved |
| 2026-07-02 | Phase 2 Step 2.2 | `aws_acm_certificate_validation.wildcard` hung indefinitely (~9 min) | Removed validation waiter; cert stays PENDING until Phase 5 GoDaddy NS cutover | ✅ Resolved |
| 2026-07-02 | Phase 2 Step 2.2 | DKIM TXT record `CharacterStringTooLong` — 410-char value exceeds 255-char DNS limit | Split into two list entries at char 237 of key (prefix `v=DKIM1; k=rsa; p=` = 18 chars) | ✅ Resolved |
| 2026-07-02 | Phase 2 Step 2.3 | RDS parameter group error: `cannot use immediate apply method for static parameter` | Changed `max_connections`, `shared_buffers`, `log_connections`, `log_disconnections`, `log_min_duration_statement` to `apply_method = "pending-reboot"` | ✅ Resolved |
| 2026-07-02 | Phase 2 Step 2.3 | ECR lifecycle policy `for_each = aws_ecr_repository.repos` caused unknown-value error | Changed to `for_each = toset(local.ecr_repos)` with `each.key` | ✅ Resolved |
| 2026-07-02 | Phase 6 Step 6.1 | `NotNullViolation: entity_id` in migration `88131acac5f1` — `SET LOCAL session_replication_role = 'replica'` requires superuser on RDS; audit trigger fired on seed INSERT of `email_template` (TEXT PK, not UUID) | Python engineer fixed migration: seed INSERT now runs before audit trigger is created | ✅ Resolved |
| 2026-07-02 | Phase 6 Step 6.1 | `DuplicateTable: email_template` on retry — broken transactional DDL boundary from `session_replication_role` left orphaned table; Alembic version stayed at `220cfa33d815` | Dropped orphaned table via raw SQL before retrying alembic | ✅ Resolved |
| 2026-07-02 | Phase 6 Step 6.1 | `FATAL: password auth failed` on localhost:5432 — Docker owns `*:5432`; SSH tunnel was pre-empted | Reopened RDS tunnel on port `5433`; use `127.0.0.1:5433` always when Docker is running | ✅ Resolved |
| 2026-07-04 | Post-Launch | `pilot-production-ecs-api-memory` CloudWatch alarm firing — `pilot-api` memory trending 78%→82% at idle | Root cause: `celery_app.connection()` in `/api/v1/health/celery` leaked broker connections on every ALB health check (240/hr). Fixed with `with celery_app.connection() as conn:` context manager + `timeout=1.0` on inspect. Deployed new image. Alarm resolved. | ✅ Resolved |
| 2026-07-06 | Post-Launch | `pilot-api` memory at 92.8% — both `ecs-api-memory` (80%) and `ecs-api-memory-critical-90` (90%) alarms firing | **Two compounding root causes**: (1) Kombu broadcast consumer leak: 240 health check calls/hr each opened a new Redis pub/sub channel; 15s TTL cache in `health.py` reduces to ~4/hr. (2) Task undersized: two uvicorn workers × ~200MB base = ~400MB idle baseline in a 512MB task (only ~110MB headroom). **Fix**: cache patch deployed (`pilot-api:3`), then `memory = 1024` in Terraform + `pilot-api:4` deployed. Memory: 92.8% → 39.5%. | ✅ Resolved |
| 2026-07-04 | Post-Launch | `pilot-web` ECS tasks failing container health check — `curl -f http://localhost:3000/api/health` failing inside Fargate Alpine container | curl/wget loopback connections fail in Fargate network namespace regardless of address (`localhost`, `127.0.0.1`). ALB external check works. Fix: removed `healthCheck` block from task definition; deployed `pilot-production-web:4`; updated `modules/compute/main.tf`. Service reached steady state. | ✅ Resolved |
| 2026-07-04 | Post-Launch | `aws-ops-runbook.md` §8.3 build command incorrect — `cd frontend/apps/web && docker build .` fails because Dockerfile requires monorepo root as build context | Corrected to `docker build -f frontend/apps/web/Dockerfile frontend/` from repo root; added warning block explaining the requirement | ✅ Resolved |

---

## Terraform State

| Item | Value |
|---|---|
| **State bucket** | `pilot-terraform-state-000000000000` |
| **State key** | `production/terraform.tfstate` |
| **Lock table** | `pilot-terraform-locks` |
| **Last apply** | `2026-07-06 — pilot-api memory incident` · `module.compute` applied · `pilot-api` task definition bumped to `memory = 1024 MB` · `pilot-api:4` active · idle memory 39.5% |
| **Terraform version** | `>= 1.7.0` |
| **AWS provider version** | `~> 5.0` |
