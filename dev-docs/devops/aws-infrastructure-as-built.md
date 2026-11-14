# AWS Infrastructure As-Built — Pilot for Trades

> **⚠️ HIBERNATION NOTICE (2026-09-07, HIBERNATE-1 / ADR-0020/0021):**
> The infrastructure described below has been **deeply torn down** to a single-digit cost floor (~$1–3/mo AWS + $2 EUM TFN).
> **Destroyed**: VPC, subnets, NAT, ALB, ECS cluster/services/task defs, GPU instance, RDS, ElastiCache Redis, bastion, all CloudWatch alarms/dashboard/log groups/SNS topic, GuardDuty, Security Hub, AWS Config, all 11 Secrets Manager secrets (force-deleted), KMS CMK (PendingDeletion, deletes 2026-10-07), all ECR images, Route 53 hosted zone, S3 assets bucket, S3 config-logs bucket.
> **Kept (surviving in AWS)**: S3 marketing bucket (`pilot-production-marketing`) + CloudFront distribution (`EXXXXXXXXXXX1` / `dxxxxxxxxxxxx1.cloudfront.net` — manually recreated after TF destroy accidentally deleted the original) + OAC, ACM cert (`pilotfortrades.com` + `*.pilotfortrades.com`), Cognito user pool (`us-east-1_XXXXXXXXX` — Lambda triggers detached, falls back to COGNITO_DEFAULT; **pool and all users deleted 2026-11-14**, as was the `pilot-dev` pool — a restart recreates both and updates the pool and client IDs), ECR repo shells ×4 (empty), TF state backend (S3 + DynamoDB).
> **Deviations from design**: (1) The original CloudFront distribution (`EXXXXXXXXXXXX2`) was destroyed by the TF networking destroy (dependency chain: VPC endpoint → S3 bucket → CF distribution). A new distribution was manually recreated with a new OAC + ACM cert. Cloudflare apex/www CNAMEs updated to point to `dxxxxxxxxxxxx1.cloudfront.net`. (2) All 3 Lambda functions were destroyed (their IAM roles were destroyed by TF, making them non-functional). The `post-confirmation` Lambda's VPC ENIs blocked VPC deletion — the function was deleted to release them. At restart, `terraform apply` recreates all 3 Lambda functions + roles. (3) The VPC + 2 subnets + 1 SG remain pending async Lambda Hyperplane ENI release (AWS takes 30-60+ min; these resources cost $0 while waiting). (4) GuardDuty/Security Hub/Config were TF-managed (contrary to the design's "not in TF" note) — they were destroyed via TF + CLI disable.
> **Restart**: See [`aws-ops-runbook.md`](aws-ops-runbook.md) §21 (Restart Runbook) — operationalizes design §F.

**Version**: 1.3-hibernate
**Date**: September 7, 2026 (hibernation annotation; original content dated August 16, 2026)
**Author**: Pilot Architect (synthesized from Terraform implementation)
**Account**: HotRMC (`owner@example.com`) · Account ID: `000000000000`
**Region**: `us-east-1` (US East — N. Virginia)
**Terraform location**: `infrastructure/terraform/environments/production/`
**Deployment plan reference**: [`dev-docs/devops/aws-deployment-plan-v1.md`](aws-deployment-plan-v1.md)
**Operations reference**: [`dev-docs/devops/aws-ops-runbook.md`](aws-ops-runbook.md)

> **Purpose**: This document is the human-readable single source of truth for the deployed AWS infrastructure. Read this instead of navigating Terraform files. Update this document whenever a `terraform apply` changes the infrastructure. Use this doc to answer questions about scale, reliability, security, and cost.

---

## Table of Contents

0. [How to Maintain This Document](#0-how-to-maintain-this-document)
1. [Infrastructure Summary](#1-infrastructure-summary)
2. [Network Architecture](#2-network-architecture)
3. [Compute Layer](#3-compute-layer)
4. [Data Layer](#4-data-layer)
5. [Security Architecture](#5-security-architecture)
6. [Monitoring & Alerting](#6-monitoring--alerting)
7. [DNS & TLS](#7-dns--tls)
8. [Cost Analysis](#8-cost-analysis)
9. [Scalability Assessment](#9-scalability-assessment)
10. [Reliability & Disaster Recovery](#10-reliability--disaster-recovery)
11. [Known Gaps & Phase 2 Upgrades](#11-known-gaps--phase-2-upgrades)
12. [GPU Service Discovery — Private IP Problem & Solution](#12-gpu-service-discovery--private-ip-problem--solution)
13. [DNS Migration: GoDaddy → Route 53 Timing](#13-dns-migration-godaddy--route-53-timing)
14. [Zero-Downtime Release Strategy](#14-zero-downtime-release-strategy)
15. [Key Resource IDs & Endpoints](#15-key-resource-ids--endpoints)

---

## 0. How to Maintain This Document

> **Who owns this**: The DevOps Engineer updates this document. The Pilot Architect reviews major structural changes. No other role should modify it.

### 0.1 When to Update

This document must be updated **every time** any of the following occur:

| Trigger | Sections to Update |
|---|---|
| `terraform apply` adds, removes, or changes any resource | §1 summary table, the affected layer section (§2–§7), §15 Key IDs |
| A new secret is populated in Secrets Manager | §5 Secrets Manager table |
| A CloudWatch alarm is added, changed, or removed | §6 Monitoring table + alarm count |
| DNS records change (add, update, delete) | §7 DNS table |
| An ECS task definition revision is deployed | §3 Compute table (task def revision number) |
| A Known Gap is resolved | §11 — move it to the "Resolved gaps" note |
| The GPU is replaced (new instance ID or IP) | §3 GPU table, §12, §15 Key IDs, confirm `pilot/prod/gpu` secret |
| Monthly cost estimate changes materially (>$20) | §1 summary table + §8 Cost Analysis |
| A new phase completes in `aws-deployment-status.md` | Cross-check all sections that phase touched |

### 0.2 How to Update (Step-by-Step)

1. **Open both files side by side**: [`aws-deployment-status.md`](aws-deployment-status.md) (the log of what was done) and this file (the current state).
2. **Identify the delta**: Find the most recent completed step in the deployment log. Compare it to the corresponding section in this document.
3. **Update this document**:
   - Change status indicators: `⬜ Pending` → `✅ Live` or `⚠️ Placeholder`
   - Fill in `<pending>` values in §15 with actual IDs/ARNs/endpoints
   - Update the `**Version**` and `**Date**` fields in the header
4. **Commit both files together**: The deployment log and this as-built doc should always be committed in the same PR/commit so the historical record and the current state stay in sync.
5. **Never delete historical context**: When a gap is resolved, move it to the "Resolved gaps" note in §11 rather than deleting it. When a resource is replaced, note the old ID with a ~~strikethrough~~ and add the new one.

### 0.3 AWS Organizations & Account Hierarchy

All Pilot infrastructure lives in the **workload** account (`000000000000`) inside the HotRMC OU. Understanding this hierarchy is essential for interpreting AWS billing emails, Cost Allocation Tags, and Free Tier alerts — which often reference the management account ID (`000000000001`), not the Pilot deployment account.

```
Root
├── ID: r-xxxxxxxx
├── ARN: arn:aws:organizations::000000000001:root/o-xxxxxxxxxx/r-xxxxxxxx
│
├── Management account  ← Management / Payer Account (DO NOT deploy resources here)
│   ├── Account ID: 000000000001
│   ├── ARN: arn:aws:organizations::000000000001:account/o-xxxxxxxxxx/000000000001
│   ├── Org path: o-xxxxxxxxxx/r-xxxxxxxx/000000000001/
│   └── Login: admin@example.com (root credentials — use only for billing/org/Cost Allocation Tag activation)
│
└── HotRMC Org  ← Organizational Unit
    ├── OU ID: ou-xxxx-xxxxxxxx
    ├── ARN: arn:aws:organizations::000000000002:ou/o-xxxxxxxxxx/ou-xxxx-xxxxxxxx
    ├── Org path: o-xxxxxxxxxx/r-xxxxxxxx/ou-xxxx-xxxxxxxx/
    │
    └── Workload account  ← ⭐ ALL PILOT INFRASTRUCTURE LIVES HERE
        ├── Account ID: 000000000000
        ├── ARN: arn:aws:organizations::000000000001:account/o-xxxxxxxxxx/000000000000
        ├── Org path: o-xxxxxxxxxx/r-xxxxxxxx/ou-xxxx-xxxxxxxx/000000000000/
        ├── Login: owner@example.com (root login for this account)
        └── IAM User: pilot-admin (day-to-day deployments; full admin permissions)
```

**Key operational rules**:
- All `terraform apply`, ECR pushes, ECS deploys, and Secrets Manager operations run as `pilot-admin` in account `000000000000`.
- The management account (`000000000001`) is used **only** for: billing console, Cost Allocation Tag activation (requires root org account), and AWS Organizations management. Never deploy Pilot resources into `000000000001`.
- AWS Free Tier alerts, Budget alerts, and some billing emails will show account `000000000001` (the payer/management account) as the sender — this does not mean the alert applies to Pilot infra in `000000000000`. Always check which account ID the metric/resource belongs to.

### 0.4 Version History

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 1.0 | 2026-07-01 | Pilot Architect | Initial as-built document synthesized from Terraform implementation |
| 1.1 | 2026-07-10 | Pilot DevOps Engineer | Synced all fields from deployment-status.md through Phase 8 (2026-07-05/06); added Section 0; updated §1 summary, §3 pilot-web status, §5 secrets, §6 alarms (9→11 + full names + states), §6 log groups (added pilot-production-web), §6 CloudWatch Free Tier alert note, §7 DNS (GoDaddy cutover complete + NS + ACM ISSUED), §11 Known Gaps (resolved items removed), §15 Key IDs (all `<pending>` values filled) |
| 1.2 | 2026-07-10 | Pilot DevOps Engineer | Added §0.3 AWS Organizations & Account Hierarchy; clarified CloudWatch Free Tier alert source (management account 000000000001 vs Pilot account 000000000000) |
| 1.3 | 2026-08-16 | Pilot DevOps Engineer | MFA-WIRE-1 (Step 0): added Cognito SNS role `CognitoSNSRole-pilot-production` + inline policy + pool `sms_configuration` (§5 Cognito table, §5 IAM Roles table); added SNS SMS account posture (sandboxed, no origination number, MonthlySpendLimit=$1); added `device_configuration` to pool `ignore_changes`; SMS delivery smokes BLOCKED on AWS Support |

### 0.5 Relationship to Other DevOps Docs

```
aws-deployment-status.md   ← Chronological log: WHAT was done, WHEN, and any issues
aws-infrastructure-as-built.md  ← Current state snapshot: WHAT IS running RIGHT NOW  ← YOU ARE HERE
aws-ops-runbook.md         ← HOW to operate: start/stop, deploy, SSH tunnel, profile scripts
aws-deployment-plan-v1.md  ← HOW infrastructure was designed: rationale and original plan
```

**Rule**: If `aws-deployment-status.md` shows a step as ✅ Complete and this document still shows it as ⬜ Pending, this document is out of date and must be updated before the next deploy.

---

## 1. Infrastructure Summary

### What Is Running

| Layer | Service | Config | Monthly Cost |
|---|---|---|---|
| **Networking** | VPC `10.0.0.0/16` | 2 public + 2 private subnets across us-east-1a/1b | Fixed floor |
| **Networking** | NAT Gateway | Single AZ (us-east-1a) — saves $32/mo vs Multi-AZ | ~$35 |
| **Networking** | ALB | HTTPS termination; blue-green traffic weighting (planned; deploys are ECS rolling) | ~$18 |
| **Networking** | Bastion Host | `t4g.nano` + Elastic IP; SSH jump host for admin | ~$4–7 |
| **Compute** | ECS Fargate — FastAPI API | 2 tasks × 0.25 vCPU / 1024MB (bumped from 512MB 2026-07-06 — see §3) | ~$22 |
| **Compute** | ECS Fargate — Celery Worker | 2 tasks × 0.25 vCPU / 512MB | ~$18 |
| **Compute** | ECS Fargate — Celery Beat | 1 task × 0.25 vCPU / 512MB (min 512 for 256 CPU units) | ~$8 |
| **Compute** | EC2 GPU | `g4dn.xlarge` NVIDIA T4 16GB VRAM; Whisper + Ollama | ~$390 |
| **Compute** | ECS Fargate — `pilot-web` | 1 task × 0.5 vCPU / 1024MB; Next.js SSR; port 3000; ALB listener `app.pilotfortrades.com` ✅ Live | ~$18 |
| **Data** | RDS PostgreSQL 17 | `db.t4g.micro` Multi-AZ; 20GB gp2; pgvector | ~$28 |
| **Data** | ElastiCache Redis 7 | `cache.t4g.micro`; 3 logical DBs | ~$13 |
| **Storage** | S3 — Assets | Private; audio, photos, PDFs; signed URL access | ~$2 |
| **Storage** | S3 — Marketing | Public via CloudFront OAC; static site | ~$0 |
| **Storage** | CloudFront | Marketing CDN; PriceClass_100 (US+EU) | ~$3 |
| **Security** | KMS | 1 customer-managed key (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1`); annual rotation | ~$1 |
| **Security** | Secrets Manager | 11 secrets; all KMS-encrypted | ~$4 |
| **Security** | Cognito | Production pool `pilot-production` | $0 (<50K MAUs) |
| **Security** | Lambda | Post-Confirmation trigger (creates user/tenant in RDS) | ~$0 |
| **Security** | Lambda | Post-Authentication trigger (new-device sign-in alert, PLATFORM-SMS-B2) | ~$0 |
| **Security** | Lambda | Custom Email Sender trigger (branded auth emails via SendGrid, COGNITO-EMAIL-1) | ~$0 |
| **Security** | Route 53 | Hosted zone `ZXXXXXXXXXXXXXXXXXXXX`; all DNS records; **authoritative as of 2026-07-02** | ~$1 |
| **Monitoring** | CloudWatch | Log groups, **11 alarms**, 1 dashboard | ~$28 |
| **Monitoring** | GuardDuty | Threat detection; S3 + EBS malware scan | ~$12 |
| **Monitoring** | Security Hub | CIS + AWS Foundational benchmarks | ~$5 |
| **Monitoring** | AWS Config | Tag compliance rule; required-tags enforcement | ~$0 |
| **TOTAL** | | | **~$664–707/month** |

---

## 2. Network Architecture

### VPC Layout

```
VPC: 10.0.0.0/16  (pilot-production-vpc)
│
├── Public Subnets (internet-facing)
│   ├── public-a: 10.0.1.0/24  (us-east-1a)  ← ALB, NAT Gateway, Bastion
│   └── public-b: 10.0.2.0/24  (us-east-1b)  ← ALB (Multi-AZ requirement)
│
└── Private Subnets (no direct internet)
    ├── private-a: 10.0.10.0/24  (us-east-1a)  ← ECS tasks, RDS primary, Redis, GPU, Lambda
    └── private-b: 10.0.11.0/24  (us-east-1b)  ← RDS standby (Multi-AZ)
```

**Internet flow:**
- Inbound: `Internet → ALB (public subnets) → ECS tasks (private subnets)`
- Outbound: `ECS tasks (private subnets) → NAT Gateway (public subnet) → Internet`
- S3 traffic: `ECS tasks → VPC Gateway Endpoint → S3` (bypasses NAT; free)
- Secrets Manager: `ECS tasks → VPC Interface Endpoint → Secrets Manager` (bypasses NAT; ~$7/mo)

### Security Groups — Strict Least Privilege

| Security Group | Inbound | Purpose |
|---|---|---|
| `sg-alb` | TCP 443 + 80 from `0.0.0.0/0` | ALB — internet-facing |
| `sg-ecs-api` | TCP 8000 from `sg-alb` only | ECS FastAPI tasks — only ALB can reach the app |
| `sg-rds` | TCP 5432 from `sg-ecs-api` + `sg-bastion` + `sg-lambda` | RDS — only app tasks and admin tunnel |
| `sg-redis` | TCP 6379 from `sg-ecs-api` + `sg-bastion` | Redis — only app tasks and admin tunnel |
| `sg-gpu` | TCP 8080 (Whisper) + TCP 11434 (Ollama) from `sg-ecs-api`; TCP 22 from `sg-bastion` | GPU — only ECS can call AI APIs |
| `sg-bastion` | TCP 22 from Tom's known IPs (per-IP rules via `admin_allowed_ips` list) | SSH jump host — Tom's IPs only |
| `sg-lambda` | None inbound | Lambda — outbound only (reaches RDS for post-confirm trigger + Redis for post-auth broker enqueue) |
| `sg-vpce` | TCP 443 from `10.0.10.0/24` + `10.0.11.0/24` | VPC Interface Endpoints |

### Admin Access Pattern

```
Tom's Mac (SSH key: pilot_admin_ed25519)
   ↓ SSH
Bastion (t4g.nano, public subnet, Elastic IP)
   ↓ SSH tunnel / ProxyJump
RDS PostgreSQL (private subnet, port 5432)
Redis          (private subnet, port 6379)
GPU instance   (private subnet, SSH + Whisper/Ollama)
```

---

## 3. Compute Layer

### ECS Fargate Services

All three services share the same Docker image from ECR. Different `command` overrides distinguish them.

| Service | ECS Service Name | Task Definition | Desired Count | Health Check |
|---|---|---|---|---|
| **FastAPI API** | `pilot-api` | `pilot-api:5` (0.25 vCPU / 1024MB — bumped from 512MB 2026-07-06; two uvicorn workers × ~200MB baseline consumed ~400MB at idle leaving only ~110MB headroom in 512MB) | 2 | ALB: `/api/v1/health/celery` every 30s; 3 pass = healthy |
| **Celery Worker** | `pilot-celery-worker` | `pilot-celery-worker` (0.25 vCPU / 512MB) | 2 | None (not load-balanced) |
| **Celery Beat** | `pilot-celery-beat` | `pilot-celery-beat` (0.25 vCPU / 256MB) | **1 always** | None |

> **⚠️ Beat safety**: Celery Beat is intentionally limited to exactly 1 instance and uses `deployment_minimum_healthy_percent = 0` + `deployment_maximum_percent = 100` — this ensures old Beat stops before new Beat starts, preventing dual-scheduler split-brain (duplicate QB syncs, duplicate emails, etc.).

**Deployment safety:**
- `deployment_circuit_breaker { enable = true; rollback = true }` — ECS auto-rolls back on failed health checks
- `deployment_minimum_healthy_percent = 100` (API + Worker) — old task stays alive until new task proves healthy
- `health_check_grace_period_seconds = 90` — FastAPI gets 90 seconds to start before ALB judges it

**`FORWARDED_ALLOW_IPS=*` on `pilot-api` (SIGNUP-GA-B1 hotfix, 2026-07-30):**
The `pilot-api` container env var `FORWARDED_ALLOW_IPS=*` tells uvicorn's `ProxyHeadersMiddleware` to trust the ALB's `X-Forwarded-Proto: https` header from any peer IP. Without this, uvicorn only trusts forwarded headers from `127.0.0.1` (the default), but behind the ALB the peer is a VPC IP (e.g. `10.0.2.131`), so the header was ignored and FastAPI's 307 redirects used `http://` instead of `https://` — causing browser Mixed Content blocks on the web signup. Safe because the ALB is the sole ingress and `sg-web`/`sg-alb` restrict who can reach the container. Do not set this on any service that is internet-facing without a proxy in front.

**Telnyx env vars on all ECS task definitions (TELNYX-INT-1, 2026-08-09):**
The `common_secrets` block in `infrastructure/terraform/modules/compute/main.tf` injects 4 Telnyx-related env vars into all 3 task definitions (`pilot-api`, `pilot-celery-worker`, `pilot-celery-beat`):
- `SMS_CARRIER=telnyx` (plain env var) — selects `TelnyxSmsCarrier` via the `get_sms_carrier()` factory. Without it, prod defaults to `mock` (`MockSmsCarrier`) and silently no-ops all SMS.
- `TELNYX_10DLC_MOCK=false` (plain env var) — explicitly set on all 3 task defs per the §19.6 addendum (2026-08-10). Previously intentionally absent (unset = live mode), but a baked `.env` reached prod on 2026-08-10 and silently flipped the worker to mock mode (see aws-ops-runbook.md §19.7). Explicit `false` closes the fall-through vector.
- `TELNYX_API_KEY` (secret: `api_key`) — Telnyx v2 SDK auth.
- `TELNYX_PUBLIC_KEY` (secret: `public_key`) — Ed25519 webhook signature verification.
- `TELNYX_MESSAGING_PROFILE_ID` (secret: `messaging_profile_id`) — outbound message routing.
- `PILOT_PLATFORM_SMS_NUMBER` (secret: `platform_sms_number`) — Pilot's shared Pathway-C FROM number (read by `sms_compliance_platform.py`).

> **Mode-toggle parity (§19.6 addendum, 2026-08-10)**: all 3 backend task definitions now carry explicit values for every mode-toggle env var — `SMS_CARRIER=telnyx`, `TELNYX_10DLC_MOCK=false`, `TEST_ENDPOINT_ENABLED=false`, `ENVIRONMENT=production`. No toggle is left to fall through to code defaults or a baked `.env`.

**ECS Cluster**: `pilot-production` (Container Insights enabled)
**ECR Repos**: `pilot/api`, `pilot/worker`, `pilot/beat`, `pilot/web` — lifecycle policy: keep last 10 tagged, delete untagged after 1 day

### EC2 GPU Instance (AI Pipeline)

| Attribute | Value |
|---|---|
| **Instance type** | `g4dn.xlarge` |
| **GPU** | NVIDIA T4, 16GB VRAM |
| **vCPU / RAM** | 4 vCPU / 16GB RAM |
| **AMI** | Deep Learning AMI (Amazon Linux 2023, ARM) — auto-selected via `data.aws_ami` |
| **Subnet** | `private-a` (10.0.10.0/24) — never publicly exposed |
| **Root volume** | 50GB gp3 encrypted (OS + Docker layers) |
| **Model volume** | 20GB gp3 encrypted (`delete_on_termination = false` — models persist across instance stops) |
| **Services** | Whisper `faster-whisper-server:latest-cuda` → port 8080; Ollama `ollama/ollama:latest` → port 11434 |
| **Model** | `llama3.1:8b` (~4.7GB VRAM); Whisper `Systran/faster-whisper-large-v3` per `gpu_userdata.sh` (local/beta testing used the `large-v3-turbo` variant); both fit well within the 16GB T4 |
| **Boot time** | 3–5 min instance + 5–15 min Ollama model load from EBS |
| **IAM profile** | SSM Managed Instance Core + CloudWatch Agent policy |

> GPU models persist on the 20GB EBS volume when the instance is stopped. Subsequent starts load from disk — no re-download.

### ECS Fargate — Web Dashboard (`pilot-web`)

> **AWS App Runner was sunset April 30, 2026.** The web dashboard (`pilot-web`) runs as the 4th ECS Fargate service on the existing `pilot-production` cluster, sharing the existing ALB via a `Host: app.pilotfortrades.com` listener rule — zero marginal ALB cost. ECR image `pilot/web:latest` deployed and serving production traffic.

| Attribute | Value |
|---|---|
| **ECS Service Name** | `pilot-web` |
| **Cluster** | `pilot-production` (same as API/Worker/Beat) |
| **Image** | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest` |
| **CPU / Memory** | 512 units (0.5 vCPU) / 1024MB |
| **Port** | `3000` |
| **Health check** | ALB-only: HTTP `GET /api/health` every 30s; 3 passes = healthy (container health check removed — Fargate loopback fails in Alpine; see Issues Log 2026-07-04) |
| **Security group** | `sg-web` (`sg-0xxxxxxxxxxxxxxxx`) — TCP 3000 inbound from `sg-alb` only |
| **ALB routing** | Listener rule priority 10: `Host: app.pilotfortrades.com → web target group` · TG ARN: `arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/pilot-production-web/xxxxxxxxxxxxxxxx` |
| **URL** | `app.pilotfortrades.com` (Route 53 A alias `ZXXXXXXXXXXXXXXXXXXXX_app.pilotfortrades.com_A` → ALB) |
| **Scale to stop** | `desired-count 0` → $0 Fargate billing |
| **Task definition** | `pilot-production-web:4` |
| **Status** | ✅ Live — `https://app.pilotfortrades.com` HTTP/2 200 (deployed 2026-07-03; health check fix deployed 2026-07-05) |

### Application Load Balancer

| Attribute | Value |
|---|---|
| **Name** | `pilot-production-alb` |
| **Subnets** | public-a + public-b (Multi-AZ required) |
| **TLS Policy** | `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.3 preferred) |
| **Certificate** | ACM wildcard `*.pilotfortrades.com` |
| **HTTP** | Port 80 → 301 redirect to HTTPS |
| **Target groups** | `api-blue` + `api-green` (blue/green pattern provisioned; deploys are ECS rolling and the green group receives no traffic) |
| **Deletion protection** | Enabled |

---

## 4. Data Layer

### RDS PostgreSQL 17

| Attribute | Value |
|---|---|
| **Identifier** | `pilot-production` |
| **Engine** | PostgreSQL 17 |
| **Instance class** | `db.t4g.micro` (2 vCPU / 1GB RAM) |
| **Storage** | 20GB gp2; autoscaling ceiling 100GB |
| **Multi-AZ** | ✅ Enabled — standby in us-east-1b |
| **Extensions** | pgvector (enable via `CREATE EXTENSION IF NOT EXISTS vector` in first migration) |
| **Max connections** | 100 (parameter group; SQLAlchemy pool: 5 + max overflow 10) |
| **Encryption** | KMS CMK (`alias/pilot-production`) |
| **Backup** | 28-day automated backups; final snapshot on deletion |
| **Backup window** | 07:00–08:00 UTC (3–4 AM Eastern) |
| **Maintenance** | Sundays 08:00–09:00 UTC (4–5 AM Eastern) |
| **Deletion protection** | ✅ Enabled |
| **Performance Insights** | Enabled; 7-day free retention tier |
| **Slow query log** | > 1000ms |
| **DB name** | `pilot_prod` |
| **Username** | `pilot_user` |
| **Password** | Randomly generated 32-char (stored in `pilot/prod/db` Secrets Manager) |

**Custom Parameter Group settings** (tuned for `db.t4g.micro`):

| Parameter | Value | Notes |
|---|---|---|
| `max_connections` | 100 | Hard ceiling for t4g.micro |
| `shared_buffers` | 131072 (128MB) | 12.5% of 1GB RAM |
| `effective_cache_size` | 393216 (384MB) | Conservative for 1GB |
| `random_page_cost` | 1.1 | SSD-optimized |
| `work_mem` | 4096 (4MB) | Per operation; safe for 100 connections |
| `log_min_duration_statement` | 1000ms | Log slow queries |

### ElastiCache Redis 7

| Attribute | Value |
|---|---|
| **Cluster ID** | `pilot-production` |
| **Engine** | Redis 7.1 |
| **Node type** | `cache.t4g.micro` |
| **At-rest encryption** | ❌ Not enabled (single-node cluster; Known Limitations #24) |
| **Transit encryption** | ❌ Disabled for MVP (would require `rediss://` URLs; Phase 2) |
| **Logical databases** | DB 0: Rate limiting; DB 1: Celery broker; DB 2: Celery results |
| **Connection strings** | `redis://<host>:6379/0`, `/1`, `/2` (stored in `pilot/prod/redis` Secrets Manager) |

### S3 Buckets

| Bucket | Purpose | Public? | Versioning | Notes |
|---|---|---|---|---|
| `pilot-production-assets` | Audio, photos, PDFs | Private; signed URL access | Enabled | Tenant data — sensitive |
| `pilot-production-marketing` | Static marketing site | Via CloudFront OAC only | Enabled | Public content |
| `pilot-production-config-logs-000000000000` | AWS Config delivery | Private | Enabled | Auto-created by Config recorder |

---

## 5. Security Architecture

### Cognito User Pool (Production)

| Attribute | Value |
|---|---|
| **Pool name** | `pilot-production` |
| **Pool ID** | `us-east-1_XXXXXXXXX` |
| **App Client ID** | `xxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **App Client name** | `pilot-web-prod` (SPA — no client secret) |
| **Sign-in** | Email only (case-insensitive) |
| **Self-registration** | **Enabled (self-sign-up, ADR-0011)** — clients call Cognito `SignUp` (email+password) via Amplify; email verification required before the Post-Confirmation trigger fires. Rate-limited + Turnstile-guarded at the `/sign-up` edge. |
| **MFA** | Optional (enforced per-tenant in application layer) |
| **Auth flows** | `USER_SRP_AUTH` (web) + `USER_PASSWORD_AUTH` (mobile Expo Go) + `ALLOW_REFRESH_TOKEN_AUTH` |
| **Token TTLs** | Access: 60 min; ID: 60 min; Refresh: 30 days |
| **Post-Confirmation trigger** | Lambda `pilot-production-post-confirmation` — **deployed 3-path router** (SIGNUP-GA-1): Path 1 existing user → no-op; Path 2 pending invite → attach; Path 3 new owner → create tenant+user. Wired manually via CLI (lambda_config in `ignore_changes`). |
| **Post-Authentication trigger** | Lambda `pilot-production-post-authentication` — **deployed** (PLATFORM-SMS-B2, ADR-0013): fires on every successful auth, gates on `newDeviceUsed`, enqueues Sample 3 (new-device alert) to the Redis broker. Wired manually via CLI alongside Post-Confirmation (whole-block overwrite — both triggers in one call). |
| **CustomEmailSender trigger** | Lambda `pilot-production-custom-email-sender` — **deployed** (COGNITO-EMAIL-1, ✅ LIVE 2026-09-03): Cognito invokes this Lambda instead of sending its own auth emails. Decrypts the KMS-encrypted code via the **AWS Encryption SDK** (envelope encryption — NOT raw `kms:Decrypt`), renders a branded template, sends via SendGrid (`noreply@pilotfortrades.com`). `email_sending_account` stays `COGNITO_DEFAULT` (trigger bypasses it). Wired manually via CLI alongside Post-Confirmation + Post-Authentication (all three triggers + KMSKeyID in one call). 512 MB memory; dedicated IAM role (no VPC, no RDS). Rollback: detach trigger (one CLI call restoring the prior two-trigger LambdaConfig). |
| **Device tracking** | **Enabled — "Always remember"** (PLATFORM-SMS-B2): `ChallengeRequiredOnNewDevice=false`, `DeviceOnlyRememberedOnUserPrompt=false`. Populates `newDeviceUsed` for the Post-Authentication gate. Now in `lifecycle.ignore_changes` (MFA-WIRE-1) — set via CLI, Terraform does not manage it. |
| **SmsConfiguration** | **✅ Configured (MFA-WIRE-1, 2026-08-16)** — `SnsCallerArn = arn:aws:iam::000000000000:role/CognitoSNSRole-pilot-production`, `ExternalId = pilot-prod-cognito-sms`, `SnsRegion = us-east-1`. Terraform-managed in `modules/security/main.tf`. Previously absent (pool shipped without it — SMS MFA OTPs could not be delivered). |
| **Advanced security** | AUDIT mode |

### KMS Encryption

All encrypted resources use a single customer-managed key (`alias/pilot-production`):
- RDS at-rest encryption
- S3 bucket encryption (server-side)
- Secrets Manager secret encryption
- EBS volumes (GPU + bastion)

Annual key rotation is enabled.

### Secrets Manager

11 secrets, all KMS-encrypted, all with 30-day recovery window:

| Secret Name | Contents | Status |
|---|---|---|
| `pilot/prod/db` | DB credentials + connection URL (auto-populated by Terraform database module) | ✅ Populated |
| `pilot/prod/redis` | Redis connection URLs for DB 0, 1, 2 (auto-populated by Terraform) | ✅ Populated |
| `pilot/prod/cognito` | `region`, `user_pool_id`, `app_client_id` (populated by Terraform) | ✅ Populated |
| `pilot/prod/sendgrid` | `api_key` (PilotForTrades-Prod), `from_email` | ✅ Populated via Console |
| `pilot/prod/telnyx` | `api_key`, `messaging_profile_id`, `public_key`, `platform_sms_number` | ✅ Populated via Console |
| `pilot/prod/encryption` | Fernet key (AES-128-CBC + HMAC for QB OAuth token encryption) | ✅ Populated via Console |
| `pilot/prod/google-maps` | Distance Matrix API key | ✅ Populated via Console |
| `pilot/prod/turnstile` | Cloudflare Turnstile server-side secret key | ✅ Populated via Console |
| `pilot/prod/gpu` | `{"whisper_url": "http://10.0.10.36:8080/v1", "ollama_url": "http://10.0.10.36:11434/api"}` · ARN: `arn:aws:secretsmanager:us-east-1:000000000000:secret:pilot/prod/gpu-XXXXXX` | ✅ Populated 2026-07-05 |
| `pilot/prod/quickbooks` | Production QB app credentials | ⚠️ Placeholder values — QB sync disabled pending Intuit prod app |
| `pilot/prod/stripe` | Live mode keys + webhook secret | ⚠️ Placeholder values — Stripe features disabled pending live mode activation |

### IAM Roles

| Role | Used By | Key Permissions |
|---|---|---|
| `pilot-production-ecs-task-role` | Running ECS containers | Secrets Manager (11 secrets), KMS decrypt, S3 assets r/w, X-Ray |
| `pilot-production-ecs-execution-role` | ECS task startup | ECR pull, CloudWatch logs, Secrets Manager (for env injection) |
| ~~`pilot-production-app-runner-role`~~ | ~~App Runner~~ | **Removed** — App Runner sunset April 30, 2026; role no longer needed |
| `pilot-production-lambda-execution-role` | Post-Confirmation + Post-Authentication Lambdas | VPC access, RDS + Redis secrets (least-privilege ARN scoping), KMS |
| `pilot-production-custom-email-sender-role` | Custom Email Sender Lambda (COGNITO-EMAIL-1) | **Dedicated role** — least-privilege: `secretsmanager:GetSecretValue` on `pilot/prod/sendgrid` only; `kms:Decrypt` on `aws_kms_key.pilot` only; CloudWatch Logs. No VPC, no RDS access (self-contained handler, design §B) |
| `pilot-production-github-actions` | GitHub Actions OIDC | ECR push, ECS deploy, S3 marketing deploy, CloudFront invalidate |
| `pilot-production-gpu-instance-role` | GPU EC2 instance | SSM (for Session Manager access), CloudWatch Agent |
| `CognitoSNSRole-pilot-production` | Cognito user pool (SMS MFA delivery) | `sns:Publish` (inline policy `cognito-sns-sms-publish`, resource `*` — SNS phone-number SMS has no resource-level scoping). Trust: `cognito-idp.amazonaws.com` assume gated by `sts:ExternalId = pilot-prod-cognito-sms`. **MFA-WIRE-1 (2026-08-16)**. |
| `pilot-production-config-role` | AWS Config recorder | Config service policy |

**GitHub OIDC trust**: `repo:TomHRMC/pilot:*` — only the `TomHRMC/pilot` repository can assume the deploy role. No long-lived access keys in GitHub.

### SNS SMS Account Posture (MFA-WIRE-1)

The Cognito→SNS SMS delivery path is wired (role + `SmsConfiguration`), but the SNS SMS account itself cannot send any SMS yet. Posture as of 2026-08-16:

| Attribute | Value | Impact |
|---|---|---|
| `IsInSandbox` | `true` | SNS SMS only delivers to verified sandbox numbers |
| Origination numbers | **none** (`list-origination-numbers` → empty) | **No SMS can be sent at all** — even `create-sms-sandbox-phone-number` fails with `No origination entities available to send` |
| `MonthlySpendLimit` | `$1` (account default) | Cannot be raised while sandboxed — AWS rejects any value > 1 with "reach out to support" |
| Sandbox verified numbers | none (a prior `+14105550123` was `Pending`, never verified — deleted during MFA-WIRE-1; re-add blocked by the origination gap) | — |

**Smoke evidence**: none — SMS delivery smokes (direct `sns publish` + Cognito→SNS OTP) are **BLOCKED** on a single AWS Support case (SNS SMS production access). The infrastructure wiring is verified live via `describe-user-pool` (2026-08-16T21:46Z). See [`aws-cognito-prod-setup.md`](aws-cognito-prod-setup.md) → "MFA-WIRE-1 — Cognito SMS Delivery" for the post-unblock smoke procedure.

---

## 6. Monitoring & Alerting

### CloudWatch Alarms (11 total)

All alarms send to SNS topic → email to `tom@pilotfortrades.com` (primary; `owner@example.com` removed 2026-07-05).

| Alarm | Metric | Threshold | Severity | Period | State |
|---|---|---|---|---|---|
| `pilot-production-api-error-rate` | ALB 5xx / total requests | > 5% for 3 × 5min | Critical | 5 min | ✅ OK |
| `pilot-production-api-p95-latency` | ALB TargetResponseTime p95 | > 2000ms for 3 × 5min | High | 5 min | ✅ OK |
| `pilot-production-alb-unhealthy-hosts` | ALB UnHealthyHostCount | > 0 for 2 × 5min | Critical | 5 min | ✅ OK |
| `pilot-production-ecs-api-cpu` | ECS CPU (pilot-api service) | > 70% × 3 periods | High | 5 min | ✅ OK |
| `pilot-production-ecs-api-memory` | ECS Memory (pilot-api service) | > 80% × 3 periods | High | 5 min | ✅ OK |
| `pilot-production-ecs-api-memory-critical-90` | ECS Memory (pilot-api service) | > 90% × 1 period | Critical | 5 min | ✅ OK |
| `pilot-production-rds-connections` | RDS DatabaseConnections | > 80 of 100 max for 2 × 5min | High | 5 min | ✅ OK |
| `pilot-production-rds-cpu` | RDS CPUUtilization | > 60% for 2 × 5min | Medium | 5 min | ✅ OK |
| `pilot-production-rds-free-storage` | RDS FreeStorageSpace | < 5GB for 1 × 5min | High | 5 min | ✅ OK |
| `pilot-production-redis-cpu` | ElastiCache CPUUtilization | > 60% for 2 × 5min | Medium | 5 min | ✅ OK |
| `pilot-production-gpu-status-check` | EC2 StatusCheckFailed | > 0 for 2 × 1min | Critical | 1 min | ✅ OK |

> **ECS API memory escalation ladder**: `ecs-api-memory` (>80% for 15 min) → investigate → `ecs-api-memory-critical-90` (>90% for 5 min) → act immediately. The API idled at 92.8% in 512MB before the 2026-07-06 resize to 1024MB; current idle is ~39.5%.
>
> **GPU alarm**: Uses `treat_missing_data = notBreaching` (changed from `breaching` — EC2 `StatusCheckFailed` takes ~2 min to start publishing; `breaching` caused a false alarm on first apply 2026-07-05).

### CloudWatch Log Groups (30-day retention)

| Log Group | Source |
|---|---|
| `/ecs/pilot-api` | FastAPI ECS tasks |
| `/ecs/pilot-celery-worker` | Celery Worker ECS tasks |
| `/ecs/pilot-celery-beat` | Celery Beat ECS task |
| `/ecs/pilot-production-web` | `pilot-web` Next.js ECS tasks |
| `/aws/lambda/pilot-production-post-confirmation` | Post-Confirmation Lambda |
| `/aws/lambda/pilot-production-post-authentication` | Post-Authentication Lambda (PLATFORM-SMS-B2) |
| `/aws/lambda/pilot-production-custom-email-sender` | Custom Email Sender Lambda (COGNITO-EMAIL-1) |
| `/pilot/gpu-instance` | GPU instance Docker logs (CloudWatch Agent) |

> ⚠️ **CloudWatch Free Tier**: The account is at **8.97 / 10 free custom metrics** as of 2026-07-06 (AWS alert email received 2026-07-10). Each CloudWatch alarm consumes one metric slot against the Free Tier limit. With 11 alarms active, the account will exceed the 10-metric Free Tier once all alarm metrics are tracked. See §8 for cost impact and §0 for mitigation guidance.

### CloudWatch Dashboard

`pilot-production-overview` — 6 widgets:
- ALB: Request count + 5xx errors
- ALB: p95 latency
- ECS: CPU utilization (API + Worker)
- ECS: Memory utilization (API + Worker)
- RDS: Connections + CPU
- RDS: Free storage

### Security Services

| Service | Configuration |
|---|---|
| **GuardDuty** | Enabled; S3 logs + EBS malware scan on GPU and bastion on threat detection |
| **Security Hub** | CIS AWS Foundations Benchmark v1.4.0 + AWS Foundational Security Best Practices v1.0.0 |
| **AWS Config** | Recording all resource types; delivery to `pilot-production-config-logs-*` S3; required-tags rule enforces 5 mandatory tags |

---

## 7. DNS & TLS

### Route 53 Hosted Zone

Zone: `pilotfortrades.com` · Zone ID: `ZXXXXXXXXXXXXXXXXXXXX` — **✅ Route 53 is now authoritative** (GoDaddy → Route 53 NS cutover completed 2026-07-02). NS propagation confirmed globally within ~1 minute of cutover.

**Nameservers (active)**:
- `ns-XXX.awsdns-XX.com`
- `ns-XXX.awsdns-XX.org`
- `ns-XXX.awsdns-XX.co.uk`
- `ns-XXX.awsdns-XX.net`

**Live DNS Records in Route 53**:

| Record | Type | Points To | Status |
|---|---|---|---|
| `pilotfortrades.com` | A (alias) | CloudFront `EXXXXXXXXXXXX2` (marketing site) | ✅ Live |
| `www.pilotfortrades.com` | A (alias) | CloudFront `EXXXXXXXXXXXX2` | ✅ Live |
| `api.pilotfortrades.com` | A (alias) | ALB `pilot-production-alb` | ✅ Live |
| `app.pilotfortrades.com` | A (alias) | ALB `pilot-production-alb` (Host-header rule → `pilot-web` TG) | ✅ Live — deployed 2026-07-03 |
| `pilotfortrades.com` | MX | 5 Google Workspace MX records | ✅ Live |
| `pilotfortrades.com` | TXT | SPF + Google site-verification | ✅ Live |
| `google._domainkey.pilotfortrades.com` | TXT | Google Workspace DKIM (selector: `google`; split two-chunk at char 237) | ✅ Live |
| `_dmarc.pilotfortrades.com` | TXT | `v=DMARC1; p=quarantine; rua=mailto:legal@pilotfortrades.com` | ✅ Live |

### ACM Certificate

Wildcard certificate `*.pilotfortrades.com` + apex `pilotfortrades.com` — **✅ ISSUED** (validated ~14 minutes after GoDaddy NS cutover 2026-07-02).
**ARN**: `arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx2`
Issued in `us-east-1` (required for CloudFront). DNS validation records automatically added to Route 53 by Terraform.
TLS policy: `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.3 preferred, TLS 1.2 minimum).

### p4tsites.com — Tenant-Sites Domain (C-B16-OPS, ADR-0014)

**Cutover date**: 2026-08-26 · **Registrar**: Cloudflare ($10.46/yr) · **DNS**: Cloudflare (no Route 53 hosted zone — ADR-0014)

**ACM Certificate** (Terraform-managed in [`modules/security/main.tf`](../../infrastructure/terraform/modules/security/main.tf) `aws_acm_certificate.p4tsites`):
- **ARN**: `arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Domains**: `p4tsites.com` + `*.p4tsites.com` (wildcard SAN)
- **Status**: ✅ ISSUED (2026-08-26 — validated via Cloudflare DNS CNAME)
- **Validation**: DNS CNAME created manually in Cloudflare (no `aws_acm_certificate_validation` resource — same posture as the pilotfortrades wildcard)

**ALB SNI Listener Certificate** (Terraform-managed in [`modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf) `aws_lb_listener_certificate.p4tsites`):
- Attached to the shared ALB HTTPS listener (`aws_lb_listener.https[0]`) as a second certificate (SNI)
- The ALB presents this cert when the SNI hostname matches `*.p4tsites.com`

**ALB Host-Header Rule** (Terraform-managed in [`modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf) `aws_lb_listener_rule.tenant_sites`):
- **Priority**: 15 (after web rule at 10, before any catch-all API rule)
- **Condition**: `Host: *.p4tsites.com`
- **Action**: forward → `pilot-web` target group
- No apex/www ALB rule — the apex redirect lives at the Cloudflare edge (§G-11, ADR-0014)

**Cloudflare DNS Records** (manual console — documented in [`aws-ops-runbook.md`](aws-ops-runbook.md) §17.1):

| Record | Type | Target | Proxy | Purpose |
|---|---|---|---|---|
| `_<validation-name>` | CNAME | `_<validation-value>.acm-validations.aws.` | DNS-only (gray) | ACM cert validation |
| `*` | CNAME | `pilot-production-alb-xxxxxxxxxx.us-east-1.elb.amazonaws.com` | DNS-only (gray) | Wildcard → ALB (tenant sites) |
| `@` | AAAA | `100::` | Proxied (orange) | Apex placeholder (edge redirect) |
| `www` | AAAA | `100::` | Proxied (orange) | www placeholder (edge redirect) |
| `@` | TXT | `v=spf1 -all` | — | Mail lockdown |
| `_dmarc` | TXT | `v=DMARC1; p=reject` | — | DMARC reject |

**Cloudflare Redirect Rule**: `p4tsites.com` + `www.p4tsites.com` → 301 → `https://pilotfortrades.com` (edge redirect; tenant subdomains pass through untouched)

**Task-Def Env Vars** (Terraform-managed in [`modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf)):
- `pilot-api`: `TENANT_SITES_BASE_DOMAIN=p4tsites.com` (rev 8)
- `pilot-celery-worker`: `TENANT_SITES_BASE_DOMAIN=p4tsites.com` (rev 5)
- `pilot-web`: `NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com` (rev 6) — also inlined at image build time via Dockerfile `ARG NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com`
- `pilot-web`: `TENANT_SITES_DOMAIN=p4tsites.com` (TS-BUG-1, 2026-08-26) — non-public **runtime** var read by `src/proxy.ts` (Node.js runtime); also set as Dockerfile builder ARG + runner-stage ENV default. Belt-and-suspenders behind the proxy's hard-coded multi-domain fallback.

**App-layer host handling (TS-BUG-1, 2026-08-26)**: the `pilot-web` tenant-site host rewrite lives in [`frontend/apps/web/src/proxy.ts`](../../frontend/apps/web/src/proxy.ts) (Next.js 16 convention — `middleware.ts` deprecated). It reads the client `Host` header **directly** (`request.headers.get("host")`) because `request.nextUrl.hostname` does NOT reflect the original Host behind the ALB (confirmed root cause of the slug-URL login wall across 3 deploy iterations). The ALB preserves the client Host header — never introduce host-rewriting at the ALB or Cloudflare layer. **App-level canary** (closes the C-B16-OPS canary gap): `curl -sI https://<slug>.p4tsites.com/` → 200 + `x-middleware-rewrite: /sites/<slug>/` — a 307 to `/dashboard` means the proxy did not rewrite (app-layer fault, not ALB). See ops runbook §17.1.

**Cost impact**: +$0.87/mo (domain registration amortized; ACM cert free; ALB rule zero marginal; no Route 53 hosted zone). Baseline ~$888 → ~$888.87/mo.

---

## 8. Cost Analysis

### Current Monthly Estimate (at ~$664–707/month)

See [`aws-deployment-plan-v1.md §8`](aws-deployment-plan-v1.md) for full itemized breakdown.

**Largest cost drivers:**

| Service | Monthly | % of Total | Can Stop? |
|---|---|---|---|
| **GPU (g4dn.xlarge)** | ~$390 | 58% | ✅ Yes — `profile-off.sh` or A/B light |
| **NAT Gateway** | ~$35 | 5% | ❌ No — private subnet needs outbound internet |
| **RDS** | ~$28 | 4% | ⚠️ Not recommended (7-day auto-restart) |
| **Data Transfer** | ~$45 | 7% | Scales with customer usage |
| **ECS Fargate (all 4 services)** | ~$62 | ~9% | ✅ Yes — scale to 0 tasks (`pilot-web` included) |

**Profile cost savings:**
- Stopping the GPU saves ~$390/month (~58% of total)
- Scaling all ECS services to 0 saves ~$62/month (API + Worker + Beat + Web)

---

## 9. Scalability Assessment

### Current Capacity (MVP — 0–100 Customers)

| Component | Current Size | Bottleneck Point | Scaling Action |
|---|---|---|---|
| **FastAPI ECS** | 2 tasks × 0.25 vCPU / 512MB | CPU > 70% for 15 min | Add 2 tasks; change `ecs_api_desired_count` variable |
| **Celery Worker** | 2 tasks × 0.25 vCPU / 512MB | CPU > 70% for 15 min | Add 2 tasks; change `ecs_worker_desired_count` |
| **RDS** | db.t4g.micro (1GB RAM, 2 vCPU) | 100 connections or storage at 80% | Enable storage autoscaling first; upgrade class if connection-limited |
| **Redis** | cache.t4g.micro | Redis CPU > 60% sustained | Upgrade to cache.t4g.small |
| **GPU** | g4dn.xlarge (T4, 16GB VRAM) | Voice AI p95 > 2.5s due to queue depth | Add second g4dn.xlarge + ALB distribution |
| **SSE connections** | 1 thread per active dispatch board | ~200 concurrent connections | Add Redis Pub/Sub fan-out layer |

### Scaling Triggers (from `scaling-logic.md`)

| Trigger | Metric | Action |
|---|---|---|
| ECS scale out | CPU > 70% OR Memory > 80% for 3 × 5-min periods | Add 2 tasks (Terraform variable change + apply) |
| RDS storage autoscale | 80% of allocated storage | Automatic (configured up to 100GB ceiling) |
| RDS class upgrade | Connection count > 80 OR CPU > 60% sustained | Upgrade to db.t4g.small (~$57/mo) |
| GPU second instance | Voice AI p95 > 2.5 seconds | Second g4dn.xlarge + ALB weight split |

### Projected Costs at Scale

| Milestone | Customers | Est. Monthly | Cost/Customer |
|---|---|---|---|
| **MVP** | 0–100 | ~$664–707 | $6.64–7.07 |
| **Growth** | ~500 | ~$1,100–1,200 | $2.20–2.40 |
| **Scale** | ~1,000 | ~$1,800–2,000 | $1.80–2.00 |

---

## 10. Reliability & Disaster Recovery

### Availability Design

| Component | Redundancy | SLO Contribution |
|---|---|---|
| **ALB** | Multi-AZ by design | AWS SLA: 99.99% |
| **ECS Fargate** | 2 tasks across us-east-1a/1b (awsvpc networking) | Rolling deploy; circuit breaker auto-rollback |
| **RDS** | Multi-AZ (primary us-east-1a; standby us-east-1b) | AWS SLA: 99.95%; auto-failover in <2 min |
| **Redis** | Single node (no Multi-AZ at cache.t4g.micro) | Single point of failure for rate limiting + Celery |
| **GPU** | Single instance | Single point of failure for Voice AI |
| **NAT Gateway** | Single AZ (intentional cost trade-off) | Failure = private subnet loses internet |

**Overall SLO target**: 99.9% (43 min/month downtime budget)

**Weak points** (acceptable for MVP):
1. Redis is a single node — an ElastiCache failure stops Celery and rate limiting. Phase 2: upgrade to cluster mode.
2. GPU is a single instance — a hardware failure stops Voice AI. Phase 2: second g4dn.xlarge.
3. NAT Gateway is single AZ — failure in us-east-1a stops all private-subnet outbound traffic. Phase 2: redundant NAT in us-east-1b.

### Backup & Recovery

| Component | Backup Frequency | Retention | Recovery Method |
|---|---|---|---|
| **RDS** | Daily automated backup | 28 days | RDS point-in-time restore |
| **RDS** | Weekly manual snapshot | Indefinite | Restore from snapshot |
| **S3 — Assets** | Versioning enabled | 30 days delete marker | S3 versioned restore |
| **RDS final snapshot** | On deletion | Indefinite | `pilot-production-final-snapshot` |
| **GPU EBS (models)** | `delete_on_termination = false` | Until manually deleted | Models persist across stop/start |

**Recovery Objectives**:
- **RTO** (Recovery Time Objective): 4 hours
- **RPO** (Recovery Point Objective): 1 hour (limited by automated backup frequency; 24-hour backup window)

### Deployment Safety

- **ECS circuit breaker**: Auto-rollback on health check failure
- **`deployment_minimum_healthy_percent = 100`**: Zero-downtime rolling deploys
- **`deletion_protection = true`** on RDS: Cannot accidentally delete the database via Terraform
- **Terraform state**: S3 bucket `pilot-terraform-state-000000000000` + DynamoDB `pilot-terraform-locks` (prevents concurrent applies; bucket name includes account ID for global uniqueness)

---

## 11. Known Gaps & Phase 2 Upgrades

### Security Gaps (acceptable for MVP)

| Gap | Risk | Phase 2 Fix |
|---|---|---|
| Redis transit encryption disabled | Internal VPC traffic is unencrypted | Enable `transit_encryption_enabled = true`; update connection strings to `rediss://` |
| Username/password DB auth | Long-lived credential in Secrets Manager | IAM Database Authentication |
| ~~Lambda placeholder code~~ | ~~Post-confirmation trigger is a stub~~ | **RESOLVED (SIGNUP-GA-1, ADR-0011)** — real 3-path router deployed; trigger wired via CLI. |

### Infrastructure Gaps

| Gap | Impact | Fix |
|---|---|---|
| `pilot/prod/quickbooks` — placeholder only | QB integration disabled | Register production Intuit Developer app; replace placeholder with real `client_id`/`client_secret` |
| `pilot/prod/stripe` — placeholder only | Subscriptions/billing disabled | Activate Stripe live mode; replace placeholder with real `sk_live_`/`pk_live_`/`whsec_` values |
| ~~Cognito Lambda trigger not configured~~ | ~~Users confirmed in Cognito but no DB records created~~ | **RESOLVED (SIGNUP-GA-1)** — trigger wired via CLI (`aws cognito-idp update-user-pool`); see aws-ops-runbook.md §14.5. |
| Marketing site `site-config.json` still `coming_soon` | Marketing forms/live mode not active | Run Step 6.5 switch after confirming ECS stable |
| CI/CD Pipeline (Phase 7) deferred | Manual deployments only | Enable GitHub Actions OIDC workflow after 3+ stable manual deploys (infra and role already provisioned) |
| CloudWatch approaching Free Tier metric limit | ~9 of 10 free metrics used; 11 alarms deployed | Review §6 note; Free Tier limit is 10 custom metrics — at ~$0.30/extra metric/month, cost impact is minimal (~$0.30–1.00/mo) |

> **Resolved gaps** (removed from list): `pilot/prod/gpu` ✅ populated 2026-07-05 · DKIM/DMARC records ✅ in Route 53 and live · GoDaddy NS cutover ✅ complete 2026-07-02 · `pilot-web` ECS service ✅ live 2026-07-03 · `pilot/prod/db` + `pilot/prod/redis` ✅ auto-populated by Terraform

---

## 12. GPU Service Discovery — Private IP Problem & Solution

### Current State (MVP)

The GPU instance runs Whisper and Ollama as Docker containers in the private subnet. ECS tasks reach them using the GPU's **private IP address**, which is stored in `pilot/prod/gpu` Secrets Manager:
```json
{"whisper_url": "http://10.0.10.X:8080/v1", "ollama_url": "http://10.0.10.X:11434/api"}
```

**Will the private IP change?**

| Action | IP Change? | Notes |
|---|---|---|
| `profile-off.sh` → stop GPU → `profile-b.sh` → start GPU | ❌ No change | Stop/start preserves the private IP for instances in the same subnet |
| Terminate the instance and create a new one | ✅ IP changes | Terraform `aws_instance` replacement assigns a new IP |
| Change subnet or VPC | ✅ IP changes | Instance must be in same subnet to retain IP |

**For normal stop/start operations (profile scripts)**: the private IP is stable. No action needed.

**When would the IP change?** Only if the Terraform `aws_instance.gpu` resource is replaced (e.g., changing `instance_type`, AMI, or subnet). In that case, update `pilot/prod/gpu` Secrets Manager manually and force a new ECS deployment.

### Phase 2: Internal Route 53 DNS (Scalability Fix)

When Voice AI needs to scale to a second GPU instance, the private IP approach breaks — there's no single address to connect to. The correct architecture is an **internal Route 53 private hosted zone** that gives the GPU fleet a stable DNS name:

**Phase 2 Terraform additions:**
```hcl
# Private hosted zone — only resolvable inside the VPC
resource "aws_route53_zone" "internal" {
  name = "internal.pilotfortrades.com"
  vpc {
    vpc_id = aws_vpc.main.id
  }
}

# GPU fleet DNS record — update when IPs change; ECS resolves at connection time
resource "aws_route53_record" "gpu" {
  zone_id = aws_route53_zone.internal.zone_id
  name    = "gpu.internal.pilotfortrades.com"
  type    = "A"
  ttl     = 30  # Short TTL so ECS picks up new IPs quickly
  records = [var.gpu_private_ip]  # Or list of IPs for multiple GPUs
}
```

ECS task environment changes to use DNS instead of IP:
```
WHISPER_API_URL = http://gpu.internal.pilotfortrades.com:8080/v1
OLLAMA_API_URL  = http://gpu.internal.pilotfortrades.com:11434/api
```

For two GPU instances with load distribution, add an **internal Network Load Balancer (NLB)** in front of both, and point the DNS record at the NLB. The NLB distributes Whisper + Ollama requests across both instances. NLB cost: ~$16/month — worth it when Voice AI queue depth triggers the scaling threshold (p95 > 2.5s).

**MVP action**: Keep current private IP approach. Update `pilot/prod/gpu` secret after any GPU instance replacement. Note in runbook.

---

## 13. DNS Migration: GoDaddy → Route 53 Timing

### Should We Cut Over Now?

**Yes — cut over now.** Here is why and how:

**Current state**: Route 53 hosted zone exists with all correct records (CloudFront alias for marketing site, ALB alias for API, MX/SPF for Google Workspace). GoDaddy nameservers are still authoritative — Route 53 records exist but don't serve DNS queries yet.

**Why it's safe now**:
- The marketing site is already on S3/CloudFront. Route 53 `pilotfortrades.com → CloudFront` is the correct record and will serve the site correctly the moment Route 53 becomes authoritative.
- GoDaddy's existing records point to the same values (the marketing site was already live).
- The only risk is email outage if DKIM/DMARC records aren't in Route 53 before switching.

**Pre-cutover checklist (do these FIRST):**

**Step 1: Uncomment DKIM and DMARC in Terraform**

In `infrastructure/terraform/modules/security/main.tf`, find the commented-out blocks and populate them with exact values from GoDaddy:

```bash
# Get current DKIM value from GoDaddy DNS management UI
# Then edit modules/security/main.tf — uncomment dkim and dmarc records
# Fill in the exact values from GoDaddy

# Apply to Route 53 (before NS switch)
cd infrastructure/terraform/environments/production
terraform apply -target=module.security
```

**Step 2: Verify DKIM/DMARC resolve from Route 53 NS**
```bash
# Get your Route 53 nameservers
terraform output route53_nameservers

# Test DKIM resolves (use one of your Route 53 NS records)
dig CNAME mail._domainkey.pilotfortrades.com @ns-XXX.awsdns-XX.com
# Should return the Google DKIM value
```

**Step 3: Reduce GoDaddy TTLs to 600 (48 hours before cutover)**
```
GoDaddy → DNS Management → all records → TTL = 600 seconds
```

**Step 4: Switch nameservers at GoDaddy**
```
GoDaddy → My Products → pilotfortrades.com → DNS → Nameservers → Enter my own
→ Enter all 4 Route 53 NS records from Step 2
→ Save
```

**Step 5: Verify post-cutover (send test email)**
```bash
# NS should now resolve to AWS
dig NS pilotfortrades.com +short
# Should return 4 .awsdns-* nameservers

# Send test email from external account to support@pilotfortrades.com
# Confirm delivery to Google Workspace inbox
```

**After cutover**: All future DNS changes happen in Terraform only (no more GoDaddy DNS management). GoDaddy keeps domain registration — no transfer needed.

---

## 14. Zero-Downtime Release Strategy

### Current Implementation

The ECS services are configured for rolling zero-downtime deploys:

```
deployment_minimum_healthy_percent = 100  # Old task stays alive until new task is healthy
deployment_maximum_percent         = 200  # ECS can run 200% tasks during transition
deployment_circuit_breaker {
  enable   = true
  rollback = true  # Auto-rollback if health checks fail
}
health_check_grace_period_seconds = 90   # FastAPI has 90s to start
```

**Deploy sequence for application code** (no DB schema change):
```
GitHub push to main
   ↓
GitHub Actions: Run unit tests (pytest -m unit)
   ↓
GitHub Actions: Build Docker image → push to ECR
   ↓
GitHub Actions: Run Alembic migrations (ECS one-off task)
   ↓
GitHub Actions: aws ecs update-service --force-new-deployment (API + Worker + Beat)
   ↓
ECS starts new task → ALB health check passes 3× → ECS drains old task
   ↓
aws ecs wait services-stable (blocks CI/CD until all tasks healthy)
   ↓
Deploy complete — zero downtime
```

**Rollback** (if health checks fail):
- ECS circuit breaker auto-reverts to previous task definition in < 2 minutes
- Manual rollback: `aws ecs update-service --task-definition pilot-api:PREVIOUS_REVISION`

### The Critical Risk: Database Migrations

The hardest part of zero-downtime deploys is **database migrations**. The GitHub Actions workflow runs Alembic BEFORE deploying new application code — which means the old code runs against the new schema for a brief window.

**This works only if migrations follow the expand-contract pattern:**

| Migration Type | Zero-Downtime Safe? | Why |
|---|---|---|
| Add nullable column | ✅ Yes | Old code ignores new column |
| Add NOT NULL column with default | ✅ Yes | Old code ignores; default fills it |
| Add NOT NULL column, no default | ❌ No | Old code INSERTs will fail (missing column value) |
| Add index | ✅ Yes | Transparent to application |
| Rename column | ❌ No | Old code still references old name |
| Drop column | ❌ No | Old code still tries to SELECT old column |
| Add table | ✅ Yes | Old code ignores new table |
| Drop table | ❌ No | Old code may still reference it |
| Change column type (compatible) | ⚠️ Maybe | e.g., VARCHAR(100) → VARCHAR(200): safe |
| Change column type (incompatible) | ❌ No | Old code sends wrong type |

**The expand-contract pattern for breaking changes:**

When a migration would break the currently-running code, split it into two deploys:

```
Deploy 1 — Expand: Add new column/table; keep old structure; code reads both
Deploy 2 — Contract: Remove old column/table; code only uses new structure
```

Example — renaming `customer.name` to `customer.display_name`:
```
Deploy 1 migration: ALTER TABLE customer ADD COLUMN display_name TEXT;
Deploy 1 code: Write to both columns; read from new column; fallback to old
   ↓ (run for a release; all data backfilled)
Deploy 2 migration: ALTER TABLE customer DROP COLUMN name;
Deploy 2 code: Read/write only display_name
```

### Celery Beat Deployment (Special Case)

Beat must never run as dual instances — it would fire every scheduled task twice:

```hcl
# In modules/compute/main.tf — Beat uses opposite deployment strategy:
deployment_minimum_healthy_percent = 0    # Old Beat STOPS before new Beat starts
deployment_maximum_percent         = 100  # At most 1 Beat running at any time
```

This means Beat has a brief (5–30 second) gap during deploys where no scheduler is running. This is acceptable — Celery workers will catch up on any queued tasks. The alternative (allowing 2 Beats simultaneously) causes far worse problems (duplicate emails, duplicate QB syncs).

### ECS Fargate Web Dashboard Deployment (`pilot-web`)

The `pilot-web` service deploys via ECS rolling deploy — identical pattern to `pilot-api`:

```
GitHub push → GitHub Actions: build pilot/web image → ECR push
  ↓
aws ecs update-service --cluster pilot-production --service pilot-web --force-new-deployment
  ↓
ECS starts new task → ALB health check /api/health passes 3× → ECS drains old task
  ↓
aws ecs wait services-stable
```

Stop/start: `desired-count 0` stops billing; `desired-count 1` resumes (takes 2–3 min to pass health checks).

### Marketing Site Deployment

S3 + CloudFront — atomic, zero-downtime by nature:
```bash
# New files uploaded to S3 (atomic object replacement)
aws s3 sync apps/marketing/out/ s3://pilot-production-marketing/ --delete

# CloudFront invalidation — old cached pages expire; new pages served
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

No rolling deploy needed — S3 static files don't have versions in flight.

---

## 15. Key Resource IDs & Endpoints

> Fill in `<pending>` values after `terraform apply` runs and `terraform output` is executed.

| Resource | ID / Value | Notes |
|---|---|---|
| **AWS Account** | `000000000000` (HotRMC) | All resources in this account |
| **Region** | `us-east-1` | All resources |
| **Cognito Pool ID** | `us-east-1_XXXXXXXXX` | Production pool |
| **Cognito App Client ID** | `xxxxxxxxxxxxxxxxxxxxxxxxxx` | Public SPA client |
| **Cognito SNS Role ARN** | `arn:aws:iam::000000000000:role/CognitoSNSRole-pilot-production` | SMS MFA delivery (MFA-WIRE-1, 2026-08-16); ExternalId `pilot-prod-cognito-sms` |
| **GitHub OIDC repo** | `TomHRMC/pilot` | CI/CD trust boundary |
| **Bastion Elastic IP** | `203.0.113.12` | Static; add to `~/.ssh/config` as `pilot-bastion` HostName |
| **Bastion Instance ID** | `i-0xxxxxxxxxxxxxxx2` | Auto-discovered by `generate-infra-state.sh` via EC2 name tag |
| **NAT Gateway EIP** | `203.0.113.10` | Added to Google Maps API key IP allowlist ✅ |
| **Route 53 Zone ID** | `ZXXXXXXXXXXXXXXXXXXXX` | Used in Terraform + AWS CLI zone references |
| **Route 53 Nameservers** | `ns-XXX.awsdns-XX.com` · `ns-XXX.awsdns-XX.org` · `ns-XXX.awsdns-XX.co.uk` · `ns-XXX.awsdns-XX.net` | Set at GoDaddy 2026-07-02; Route 53 is now authoritative |
| **ACM Certificate ARN** | `arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx2` | Wildcard `*.pilotfortrades.com`; status ISSUED |
| **RDS Endpoint** | `pilot-production.xxx.us-east-1.rds.amazonaws.com` *(sensitive)* | SSH tunnel: use port **5433** (Docker owns 5432 locally): `ssh -f -N -L 5433:<endpoint>:5432 pilot-bastion` |
| **Redis Endpoint** | `pilot-production.xxx.cache.amazonaws.com` *(sensitive)* | SSH tunnel: `ssh -L 6379:<endpoint>:6379 pilot-bastion -N` |
| **GPU Instance ID** | `i-0xxxxxxxxxxxxxxx1` | Auto-discovered by `generate-infra-state.sh` |
| **GPU Private IP** | `10.0.10.36` | `pilot/prod/gpu` secret populated ✅; stop/start preserves this IP |
| **`pilot-web` ECS Service** | `pilot-web` | Service ARN: `arn:aws:ecs:us-east-1:000000000000:service/pilot-production/pilot-web`; task def `pilot-production-web:4` |
| **CloudFront Distribution ID** | `EXXXXXXXXXXXX2` | Set as GitHub Actions secret `CLOUDFRONT_DISTRIBUTION_ID` |
| **GitHub Actions Role ARN** | `arn:aws:iam::000000000000:role/pilot-production-github-actions` | Embed in `.github/workflows/deploy-production.yml` |
| **KMS Key ID** | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1` | Alias `alias/pilot-production`; used for all encryption |
| **ECR API URL** | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api` | Current tag: `latest` (`pilot-api:4` — `memory=1024MB`) |
| **ECR Worker URL** | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/worker` | Shares same image digest as API |
| **ECR Beat URL** | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/beat` | Shares same image digest as API |
| **ECR Web URL** | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web` | Next.js app; `pilot-production-web:4` |
| **SNS Alarm Topic ARN** | `arn:aws:sns:us-east-1:000000000000:pilot-production-alarms` | Subscribed: `tom@pilotfortrades.com` ✅ |
| **Terraform State Bucket** | `pilot-terraform-state-000000000000` | Key: `production/terraform.tfstate` |
| **Terraform Lock Table** | `pilot-terraform-locks` | DynamoDB; last apply: 2026-07-06 (`pilot-api` memory resize) |

### Getting All Output Values at Once

```bash
cd infrastructure/terraform/environments/production
terraform output
# Sensitive values: terraform output -raw rds_endpoint
```
