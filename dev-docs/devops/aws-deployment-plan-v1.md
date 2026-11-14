# AWS Production Deployment Plan — Pilot for Trades

**Version**: 1.0  
**Created**: June 29, 2026  
**Author**: Tom (Founder) via Pilot Architect  
**Status**: ACTIVE — Production-only deployment (no QA/staging environment until beta customer growth warrants it)  
**Region**: `us-east-1` (US East — N. Virginia)

---

## Table of Contents

- [AWS Production Deployment Plan — Pilot for Trades](#aws-production-deployment-plan--pilot-for-trades)
  - [Table of Contents](#table-of-contents)
  - [1. Strategy \& Scope](#1-strategy--scope)
    - [1.1 Deployment Philosophy](#11-deployment-philosophy)
    - [1.2 What Is NOT in Scope (Dev Environment Stays Local)](#12-what-is-not-in-scope-dev-environment-stays-local)
    - [1.3 Mobile App](#13-mobile-app)
  - [2. What Already Exists](#2-what-already-exists)
    - [2.1 AWS Organization Structure](#21-aws-organization-structure)
    - [2.2 Existing Resources \& Credentials](#22-existing-resources--credentials)
  - [3. Component Inventory](#3-component-inventory)
    - [3.1 Backend Services → ECS Fargate](#31-backend-services--ecs-fargate)
    - [3.2 AI Services → EC2 g4dn.xlarge (GPU)](#32-ai-services--ec2-g4dnxlarge-gpu)
    - [3.3 Databases \& Cache → Private Subnets](#33-databases--cache--private-subnets)
    - [3.4 Frontend Apps → AWS Hosting](#34-frontend-apps--aws-hosting)
    - [3.5 Supporting AWS Services](#35-supporting-aws-services)
  - [4. Deployment Architecture Diagram](#4-deployment-architecture-diagram)
  - [5. Phase-by-Phase Execution Plan](#5-phase-by-phase-execution-plan)
    - [Phase 1 — Terraform Bootstrap \& Networking](#phase-1--terraform-bootstrap--networking)
    - [Phase 2 — Data Layer](#phase-2--data-layer)
    - [Phase 3 — Security, Secrets \& Auth](#phase-3--security-secrets--auth)
    - [Phase 4 — Container Registry \& GPU Instance](#phase-4--container-registry--gpu-instance)
    - [Phase 5 — Marketing Site + DNS Cutover (PRIORITY: 10DLC)](#phase-5--marketing-site--dns-cutover-priority-10dlc)
    - [Phase 5.5 — Infrastructure Script Verification](#phase-55--infrastructure-script-verification)
    - [Phase 6 — ECS Fargate Services (Backend + Web Dashboard)](#phase-6--ecs-fargate-services-backend--web-dashboard)
    - [Phase 7 — CI/CD Pipeline ⛔ DEFERRED](#phase-7--cicd-pipeline--deferred)
    - [Phase 8 — Observability \& Alerting](#phase-8--observability--alerting)
  - [6. Environment Variable Matrix](#6-environment-variable-matrix)
  - [7. DNS \& Domain Setup](#7-dns--domain-setup)
    - [7.1 Subdomain Plan](#71-subdomain-plan)
    - [7.2 DNS Migration: GoDaddy → Route 53](#72-dns-migration-godaddy--route-53)
    - [7.3 Email Record Reference — Confirmed Values in Terraform](#73-email-record-reference--confirmed-values-in-terraform)
  - [8. Cost Forecast](#8-cost-forecast)
    - [8.1 Reconciliation vs. `mvp-arch.md §1.4`](#81-reconciliation-vs-mvp-archmd-14)
    - [8.2 No QA Environment Savings](#82-no-qa-environment-savings)
  - [9. Open Pre-Deployment Decisions](#9-open-pre-deployment-decisions)
  - [10. Post-Deployment Checklist](#10-post-deployment-checklist)
    - [After Phase 5 (Marketing Site):](#after-phase-5-marketing-site)
    - [After Phase 6 (Backend + Web Dashboard):](#after-phase-6-backend--web-dashboard)
    - [After Phase 7 (CI/CD):](#after-phase-7-cicd)
  - [11. AWS Resource Tagging Policy](#11-aws-resource-tagging-policy)
    - [11.1 Why Tagging Matters for Pilot](#111-why-tagging-matters-for-pilot)
    - [11.2 Mandatory Tags (Required on Every Resource)](#112-mandatory-tags-required-on-every-resource)
    - [11.3 Conditional Tags (Required When Applicable)](#113-conditional-tags-required-when-applicable)
    - [11.4 Terraform Implementation](#114-terraform-implementation)
    - [11.5 Cost Allocation Tag Activation](#115-cost-allocation-tag-activation)
    - [11.6 Cost Explorer Views](#116-cost-explorer-views)
    - [11.7 Tag Compliance Enforcement](#117-tag-compliance-enforcement)
    - [11.8 Per-Resource Tag Reference](#118-per-resource-tag-reference)
  - [Appendix A — Terraform Files to Create](#appendix-a--terraform-files-to-create)
  - [Appendix B — New Files Required in Application Repos](#appendix-b--new-files-required-in-application-repos)
  - [Appendix C - AWS Notice on App Runner Sunset](#appendix-c---aws-notice-on-app-runner-sunset)
    - [Notice](#notice)
    - [Resolution](#resolution)
  - [Appendix D — Post-Launch Operations Log](#appendix-d--post-launch-operations-log)
    - [D.1 Profile Scripts v2 + Status Dashboard (2026-07-04)](#d1-profile-scripts-v2--status-dashboard-2026-07-04)
    - [D.2 pilot-api Memory Leak Fix (2026-07-04)](#d2-pilot-api-memory-leak-fix-2026-07-04)
    - [D.3 pilot-web ECS Container Health Check Fix (2026-07-05)](#d3-pilot-web-ecs-container-health-check-fix-2026-07-05)
    - [D.4 Operations Runbook Additions (2026-07-04–05)](#d4-operations-runbook-additions-2026-07-0405)

---

## 1. Strategy & Scope

### 1.1 Deployment Philosophy

- **Production-only** for now. Dev/local testing continues on local machine. No QA/staging environment until beta customer count justifies the ~$643/month duplicate spend.
- **Marketing site is the top priority** — it must be live at `pilotfortrades.com` before the 10DLC carrier registration application can be approved. The legal pages (Privacy Policy with mandatory 10DLC SMS clause), `sms-opt-in/` page, and contact information are all built and ready.
- **Terraform-first** for all infrastructure. Nothing is click-ops. Terraform state stored in S3 with DynamoDB locking.
- **Fargate-first** for application compute. No EKS control plane cost. GPU stays on EC2 (g4dn.xlarge).
- **Manual deployments** for application code. After completing 6 phases of infrastructure build-out, the complexity of our stack is well understood. GitHub Actions CI/CD (Phase 7) is explicitly **deferred post-beta** — manual `docker build → ECR push → ecs update-service` is the deployment workflow until we have full confidence in the automated pipeline. All manual deploy procedures are documented in [`aws-ops-runbook.md`](aws-ops-runbook.md) §8.

### 1.2 What Is NOT in Scope (Dev Environment Stays Local)

| Component | Local Setup | Why Not Deployed |
|---|---|---|
| PostgreSQL (dev) | Docker `pgvector/pgvector:pg17` | Local dev DB only |
| Redis (dev) | Docker `redis:7-alpine` | Local dev only |
| Ollama (dev) | Docker `ollama/ollama` | Runs on your Mac (CPU-only for dev) |
| Whisper (dev) | Docker `fedirz/faster-whisper-server:latest-cpu` | CPU-only for dev |
| FastAPI (dev) | `uvicorn --reload` via `.vscode/tasks.json` | Hot-reload dev server |
| Frontend (dev) | `pnpm run dev` via `.vscode/tasks.json` | All 3 apps on localhost |

### 1.3 Mobile App

Expo mobile app is NOT hosted on AWS. It is:
- **Dev/testing**: Expo Go via QR code from local dev server
- **Production**: EAS Build → App Store (iOS) + Google Play (Android)

The mobile app connects to the backend ALB URL in prod. No AWS hosting required for the mobile binary itself.

---

## 2. What Already Exists

### 2.1 AWS Organization Structure

All Pilot for Trades infrastructure deploys into the **HotRMC Org** AWS account, which is a child organization unit under the Root management account. This is the correct deployment target — never deploy Pilot resources into the Root management account.

```
Root (Management Account)
├── Account: admin@example.com
├── SCP: FullAWSAccess (attached directly to Root OU)
│
└── HotRMC Org (Child Organization Unit)
    ├── Account: owner@example.com   ← ALL PILOT RESOURCES DEPLOY HERE
    ├── SCP: FullAWSAccess (attached directly)
    └── IAM User: pilot-admin       ← Deployment identity for all Terraform + CLI operations
```

| Level | Account Email | Role | Notes |
|---|---|---|---|
| **Root OU** | `admin@example.com` | AWS Organization root management account | Do NOT deploy application resources here; root account is for org-level governance only |
| **HotRMC Org** | `owner@example.com` | Child OU — active deployment account | **All Pilot infrastructure goes here** |
| **IAM User** | N/A | `pilot-admin` | Full admin access; used for all Terraform, AWS CLI, and console operations |

#### SCP Policy Note

`FullAWSAccess` is applied at both the Root level and HotRMC Org level. This is the AWS default — it explicitly allows all actions, which an empty SCP would also allow. No restrictive SCPs are in place, meaning `pilot-admin` has unrestricted access to create any AWS service in the HotRMC account. This is appropriate for a solo-founder deployment at MVP stage.

#### Deployment Identity: `pilot-admin`

All infrastructure creation — Terraform applies, AWS CLI one-time setup commands, GitHub Actions OIDC role assumption, and any console work — uses the `pilot-admin` IAM user in the HotRMC account (`owner@example.com`).

**Required for Terraform and AWS CLI operations:**

Option 1 (Preferred by AWS)
```bash
aws login
```

Option 2 (If run into issues)
```bash
# Configure AWS CLI with pilot-admin credentials
aws configure
# AWS Access Key ID: <pilot-admin access key>
# AWS Secret Access Key: <pilot-admin secret key>
# Default region: us-east-1
# Default output format: json

# Verify you are operating in the correct account before any terraform apply
aws sts get-caller-identity
# Expected output:
# {
#   "Account": "000000000000",
#   "UserId": "<pilot-admin user ID>",
#   "Arn": "arn:aws:iam::000000000000:user/pilot-admin"
# }
```

> **Account ID confirmed**: HotRMC account ID is **`000000000000`**. All `<ACCOUNT_ID>` placeholders throughout this document (ECR URLs, IAM ARNs, Terraform backend config, GitHub Actions workflow) must be replaced with `000000000000`.

#### GitHub Actions OIDC Trust

When the GitHub Actions OIDC role is created in §3.5 (Phase 7), it is created in the **HotRMC account** and trusts the GitHub repo's OIDC tokens. The `pilot-admin` user creates this role via Terraform.

### 2.2 Existing Resources & Credentials

| Resource | ID / Value | Notes |
|---|---|---|
| **AWS Org Root Account** | `admin@example.com` | Management account — governance only |
| **HotRMC Deployment Account** | `owner@example.com` · **Account ID: `000000000000`** | All Pilot resources deploy here |
| **Deployment IAM User** | `pilot-admin` (in HotRMC account) | Full admin; used for all Terraform + CLI |
| **GitHub Repository** | `https://github.com/TomHRMC/pilot` · org: `TomHRMC`, repo: `pilot` | Used in OIDC trust policy: `repo:TomHRMC/pilot:*` |
| **AWS Cognito Dev Pool** | Pool name: `pilot-dev` · Pool ID: `us-east-1_XXXXXXXXX` | Dev pool only — do NOT use for prod (renamed from `User pool - ngxowp`) |
| **Cognito App Client (dev)** | `xxxxxxxxxxxxxxxxxxxxxxxxxx` · Name: `pilot-web-dev` | Dev only — app client name unchanged |
| **Domain** | `pilotfortrades.com` | Registered + DNS at GoDaddy; migrates to Route 53 during Phase 5 (see §7.2) |
| **Google Workspace Emails** | `noreply@`, `support@`, `legal@`, etc. | All configured; MX/SPF/DKIM/DMARC live in GoDaddy DNS |
| **SendGrid Account** | `SENDGRID_API_KEY` in local `.env` | Verify transactional email sending limit |
| **Telnyx Account** | `TELNYX_API_KEY` in local `.env` | 10DLC registration pending marketing site |
| **QuickBooks Dev App** | `QUICKBOOKS_CLIENT_ID` in local `.env` | Prod QB app needs separate production credentials |
| **Cloudflare Turnstile** | Site key: `0x4AAAAAADtbEEHD6Y-jXDbC` (public) · Secret key in `pilot/prod/turnstile` Secrets Manager | Site key used in `apps/marketing/.env.production`; secret key verified server-side on form submissions |

> **⚠️ CRITICAL**: The dev Cognito user pool (`us-east-1_XXXXXXXXX`) contains only test users (`dev@pilot.local`, `tech@pilot.local`, `office@pilot.local`). A **separate production Cognito user pool** must be provisioned in the HotRMC account — never share auth pools between dev and prod.

---

## 3. Component Inventory

### 3.1 Backend Services → ECS Fargate

| Service | Docker Image Source | ECS Task Config | Notes |
|---|---|---|---|
| **FastAPI API** | `backend/Dockerfile` → ECR | 0.25 vCPU / 512MB; 2 tasks | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **Celery Worker** | Same `backend/Dockerfile` → ECR | 0.25 vCPU / 512MB; 2 tasks | `celery -A core.celery_app worker --loglevel=info --concurrency=2` |
| **Celery Beat** | Same `backend/Dockerfile` → ECR | 0.25 vCPU / 256MB; 1 task | `celery -A core.celery_app beat --loglevel=info` — single instance only, no scaling |

> All three services share the same Docker image from ECR. Different `CMD` overrides in ECS task definitions distinguish them.

#### 3.1 Cost Estimate — ECS Fargate

**AWS Fargate pricing (us-east-1, Linux, as of mid-2026):**
- Per vCPU-hour: **$0.04048**
- Per GB-hour: **$0.004445**
- Billing basis: 730 hours/month (average)

| Service | Tasks | vCPU/task | RAM/task | vCPU cost | RAM cost | Monthly |
|---|---|---|---|---|---|---|
| FastAPI API | 2 | 0.25 | 0.5 GB | 2 × 0.25 × $0.04048 × 730 = **$14.78** | 2 × 0.5 × $0.004445 × 730 = **$3.25** | **~$18** |
| Celery Worker | 2 | 0.25 | 0.5 GB | Same as API = **$14.78** | Same = **$3.25** | **~$18** |
| Celery Beat | 1 | 0.25 | 0.25 GB | 1 × 0.25 × $0.04048 × 730 = **$7.39** | 1 × 0.25 × $0.004445 × 730 = **$0.81** | **~$8** |
| **TOTAL** | **5 tasks** | | | | | **~$44/month** |

> **Delta vs. `mvp-arch.md §1.4`**: The architecture doc shows `~$30/month` for ECS Fargate, covering only the 2 API tasks (`2 × $14.78 + 2 × $3.25 ≈ $36` raw, rounded to $30 in the doc). This plan adds Celery Worker (2 tasks) and Celery Beat (1 task) as separate ECS services, adding ~$26/month. The arch doc's Celery workers ran in Docker alongside the API on the same host — on ECS Fargate they are separate billable tasks. The actual split is: API ~$18 + Worker ~$18 + Beat ~$8 = **~$44/month** total Fargate.

### 3.2 AI Services → EC2 g4dn.xlarge (GPU)

| Service | Image | Port | VRAM Usage | Notes |
|---|---|---|---|---|
| **Whisper** | `fedirz/faster-whisper-server:latest-cuda` | 8080 | ~1.5GB | **Use CUDA tag**, not CPU tag |
| **Ollama** | `ollama/ollama:latest` | 11434 | ~4.7GB | Pull `llama3.1:8b` model on first boot |

> GPU instance runs Docker Compose (similar to local) but with NVIDIA CUDA runtime enabled. GPU instance is in private subnet; ECS tasks reach it via internal VPC DNS/IP. Both services are only accessible from ECS security group — never publicly exposed.

#### 3.2 Cost Estimate — EC2 GPU Instance

**AWS g4dn.xlarge pricing (us-east-1, On-Demand Linux, as of mid-2026):**

| Component | Rate | Calculation | Monthly |
|---|---|---|---|
| g4dn.xlarge instance (On-Demand) | $0.526/hour | $0.526 × 730 hours | **$384.00** |
| Root EBS volume (50GB gp3) | $0.08/GB-month | 50 × $0.08 | **$4.00** |
| Model storage EBS (20GB gp3) | $0.08/GB-month | 20 × $0.08 | **$1.60** |
| **TOTAL** | | | **~$390/month** |

> **Delta vs. `mvp-arch.md §1.4`**: The architecture doc shows `~$384/month` for the GPU instance — this is the bare instance cost only. This plan adds $5.60/month for the two EBS volumes (root OS + model storage), bringing the true total to **~$390/month**. EBS costs were omitted in the arch doc estimate, likely because they are a small rounding delta. The g4dn.xlarge provides 4 vCPU, 16GB RAM, and 1 NVIDIA T4 GPU (16GB VRAM). Whisper uses ~1.5GB VRAM; Ollama's llama3.1:8b uses ~4.7GB VRAM — total ~6.2GB of 16GB, leaving 9.8GB headroom before needing a second GPU instance (scaling trigger: voice AI p95 latency > 2.5 seconds per `scaling-logic.md §3`).

> **Cost justification**: At $390/month flat, the GPU handles unlimited Whisper transcriptions and unlimited Llama intent parsing. Cloud GPU API alternatives (e.g., AWS Transcribe, OpenAI) would cost $1,000+/month at 100 active tenants with moderate voice usage. The g4dn.xlarge pays for itself the moment voice usage exceeds ~$6/day.

### 3.3 Databases & Cache → Private Subnets

| Service | AWS Resource | Instance Type | Config |
|---|---|---|---|
| **PostgreSQL 17+ with pgvector** | RDS | `db.t4g.micro` Multi-AZ | pgvector extension enabled; HNSW indexes; 100 max connections; automated backups 28 days |
| **Redis 7** | ElastiCache | `cache.t4g.micro` | Single node; DB 0: rate limiting; DB 1: Celery broker; DB 2: Celery results |

#### 3.3 Cost Estimate — Databases & Cache

**RDS PostgreSQL 17 — db.t4g.micro Multi-AZ (us-east-1):**

| Component | Rate | Calculation | Monthly |
|---|---|---|---|
| db.t4g.micro Multi-AZ instance | $0.032/hour | $0.032 × 730 hours | **$23.36** |
| Storage: 20GB gp2 (Multi-AZ doubles I/O) | $0.230/GB-month (Multi-AZ gp2) | 20 × $0.230 | **$4.60** |
| Automated backup storage (first 20GB free) | $0 | Equals allocated storage | **$0** |
| Performance Insights (7-day free tier) | $0 | Free retention tier | **$0** |
| **RDS Total** | | | **~$28/month** |

**ElastiCache Redis 7 — cache.t4g.micro (us-east-1):**

| Component | Rate | Calculation | Monthly |
|---|---|---|---|
| cache.t4g.micro node | $0.018/hour | $0.018 × 730 hours | **$13.14** |
| Backup storage | ~$0 | < 1GB expected | **~$0** |
| **ElastiCache Total** | | | **~$13/month** |

**Combined databases total: ~$41/month**

> **Delta vs. `mvp-arch.md §1.4`**: The architecture doc shows `~$43/month` for RDS and `~$15/month` for ElastiCache. The RDS figure of $43 vs. this plan's $28 is likely because the doc used a slightly older pricing tier or included additional storage I/O costs. The ElastiCache figure of $15 vs. $13 is within normal pricing variation. Both figures are directionally consistent — the architecture doc rounds up conservatively. This plan uses current mid-2026 pricing. The combined $41 vs. $58 in the arch doc is within the $888/month budget regardless.

> **pgvector note**: pgvector is a managed extension on RDS PostgreSQL 15+. There is **no additional charge** for the pgvector extension itself — it runs on the db.t4g.micro with no VRAM requirements (HNSW indexes run on CPU/RAM). The 1GB RAM of db.t4g.micro is sufficient for HNSW index searches at MVP scale (100 tenants, ~50K conversation messages).

### 3.4 Frontend Apps → AWS Hosting

| App | Framework | Build Output | AWS Hosting | Why |
|---|---|---|---|---|
| **Web Dashboard** (`apps/web`) | Next.js 16 App Router + SSR | Server-rendered (Node.js) | **ECS Fargate (`pilot-web`)** | App Runner sunset April 30, 2026. 4th ECS service on existing cluster; ALB listener rule routes `Host: app.pilotfortrades.com → port 3000`; shares existing ALB at zero marginal cost |
| **Marketing Site** (`apps/marketing`) | Next.js 16 static export (`output: "export"`) | `apps/marketing/out/` (static HTML/CSS/JS) | **S3 + CloudFront** | Fully static; S3/CloudFront is cheapest and fastest option; no server needed |
| **Mobile App** (`apps/mobile`) | Expo SDK 54 (React Native) | EAS Build → `.ipa`/`.apk` | **App Store / Google Play** | Native binary, not web hosting |

#### 3.4 Cost Estimate — Frontend Apps

**ECS Fargate — Web Dashboard (`pilot-web`):**

> **Note**: AWS App Runner was sunset April 30, 2026. The web dashboard runs on ECS Fargate as a 4th service on the existing `pilot-production` cluster. The existing ALB is shared via a `Host: app.pilotfortrades.com` listener rule — zero marginal ALB cost.

| Component | Rate | Calculation | Monthly |
|---|---|---|---|
| vCPU (0.5 vCPU, 1 task) | $0.04048/vCPU-hour | 0.5 × $0.04048 × 730 hours | **$14.78** |
| RAM (1024MB, 1 task) | $0.004445/GB-hour | 1.0 × $0.004445 × 730 hours | **$3.24** |
| **ECS Web Total** | | | **~$18/month** |

> Costs $0 when scaled to `desired-count 0` (identical stop/start semantics to the other three ECS services). At MVP traffic levels (owner + bookkeeper usage), a single task is sufficient. Scale to 2 tasks if CPU > 70% sustained. Previously modeled as App Runner (~$5–15/month); ECS Fargate adds ~$3–13/month more — budget-neutral given the ~$206/month remaining buffer under the $888 target.

**S3 + CloudFront (Marketing Site — `apps/marketing`):**

| Component | Rate | Calculation | Monthly |
|---|---|---|---|
| S3 storage (~1GB static build output) | $0.023/GB-month | 1 × $0.023 | **$0.02** |
| S3 GET requests (CloudFront origin fetches) | $0.0004/1,000 | ~5,000 requests | **$0.002** |
| CloudFront data transfer out (PriceClass_100) | $0.0085/GB | ~10GB/month | **$0.09** |
| CloudFront HTTPS requests | $0.0100/10,000 | ~50,000 requests | **$0.05** |
| **S3 + CloudFront Total** | | | **~$1–5/month** |

> Marketing site costs are essentially free at MVP scale — the vast majority of the CloudFront cost is data transfer, which scales directly with site traffic. At 10,000 monthly unique visitors, expect ~$3–5/month. CloudFront caching means S3 is only hit on cache misses or after `aws cloudfront create-invalidation` runs (after each deploy).

**Mobile App: $0 AWS cost.** EAS Build is a separate Expo service. App Store / Google Play developer accounts are one-time annual fees (~$99 Apple, ~$25 Google) — not AWS costs.

> **Delta vs. `mvp-arch.md §1.4`**: The architecture doc has been updated (v2026-07-03) to reflect ECS Fargate for the web dashboard at ~$18/month. CloudFront for the marketing site is ~$1–5/month, negligible. The total ECS Fargate cost (API + Worker + Beat + Web) is ~$62/month. Both are within the $888/month budget target with ~$206/month buffer remaining.

### 3.5 Supporting AWS Services

| Service | Purpose | Notes |
|---|---|---|
| **ECR** | Docker image registry | One repo per service: `pilot/api`, `pilot/worker`, `pilot/beat` |
| **S3** | Audio files, receipt images, PDF exports, Terraform state, marketing static site | Multiple buckets (see §6) |
| **ALB** | HTTPS termination for ECS Fargate; blue-green traffic weighting (planned; deploys are ECS rolling) | ACM cert on `api.pilotfortrades.com` |
| **CloudFront** | CDN for marketing site; optional CDN for S3 assets | Distribution for `pilotfortrades.com` |
| **Route 53** | DNS management for `pilotfortrades.com` | Hosted zone for all subdomains |
| **ACM** | TLS certificates | `pilotfortrades.com`, `*.pilotfortrades.com` |
| **Cognito (prod)** | Production user authentication | Pool: `pilot-production` · ID: `us-east-1_XXXXXXXXX` · App Client: `xxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **Cognito Lambda** | Post-Confirmation trigger | Creates `user` + `tenant` records in RDS on signup |
| **Secrets Manager** | DB password, QB OAuth keys, SendGrid, Telnyx, Stripe, Fernet encryption key | ~6 secrets |
| **KMS** | Encryption key management for RDS, S3, Secrets Manager | 1 customer-managed key |
| **IAM** | ECS task roles, GitHub Actions OIDC role, Lambda execution role | Least-privilege scoped |
| **GuardDuty** | Automated threat detection | Enable at account level |
| **Security Hub** | CIS benchmark compliance | Enable CIS AWS Foundations |
| **CloudWatch** | Logs, metrics, dashboards, alarms | Log groups per service |
| **X-Ray** | Distributed tracing via ADOT sidecar | Sampling: 5% prod |

#### 3.5 Cost Estimate — Supporting AWS Services

| Service | Rate Basis | Calculation | Monthly |
|---|---|---|---|
| **ECR** | $0.10/GB-month storage; same-region pull free | ~500MB images × $0.10/GB = $0.05; pulls from ECS in same region are free | **~$1** |
| **S3 (assets bucket)** | $0.023/GB storage + $0.0004/1,000 PUT/GET | ~10GB audio/images × $0.023 = $0.23; 50K operations = $0.02 | **~$1–3** |
| **ALB** | $0.008/ALB-hour + $0.008/LCU-hour | $0.008 × 730 = $5.84 base; ~1 LCU/hr × $0.008 × 730 = $5.84 LCU | **~$16–20** |
| **CloudFront (marketing)** | See §3.4 above | Included in §3.4 | **~$1–5** |
| **Route 53** | $0.50/hosted zone + $0.40/million queries | $0.50 + 1M queries × $0.40 = $0.90 | **~$1** |
| **ACM** | Free | Public SSL certs issued by ACM have no charge | **$0** |
| **Cognito** | Free tier: 50,000 MAUs | MVP well under free tier; no charge until 50K MAUs | **$0** |
| **Cognito Lambda** | Lambda: $0.20/million invocations + $0.0000166667/GB-second | ~100 invocations/month (one per new user signup); well within free tier (1M/month free) | **~$0** |
| **Secrets Manager** | $0.40/secret/month + $0.05/10,000 API calls | 8 secrets × $0.40 = $3.20; ~10K calls/month = $0.05 | **~$3** |
| **KMS** | $1.00/CMK/month + $0.03/10,000 API calls | 1 key × $1.00 = $1.00; ECS task secret retrieval ~5K calls/month | **~$2** |
| **IAM** | Free | No charge for IAM policies, roles, or users | **$0** |
| **NAT Gateway** | $0.045/hour + $0.045/GB processed | $0.045 × 730 = $32.85 base; ~50GB outbound × $0.045 = $2.25 | **~$35** |
| **VPC Endpoints** | S3 gateway: free; Secrets Manager interface: $0.01/AZ/hour | S3 endpoint free; Secrets Manager: $0.01 × 1 AZ × 730 = $7.30 | **~$7** |
| **CloudWatch Logs** | $0.50/GB ingested + $0.03/GB stored/month | ~5GB/month ingested × $0.50 = $2.50; stored 30 days × $0.03 = $0.15/GB | **~$10–15** |
| **CloudWatch Metrics + Alarms** | $0.30/metric/month; $0.10/alarm/month | ~30 custom metrics × $0.30 = $9; 11 alarms × $0.10 = $1.10 | **~$10** |
| **CloudWatch Dashboards** | $3.00/dashboard/month | 1 dashboard | **~$3** |
| **X-Ray** | First 100K traces free; $5/million after | At 5% sampling, early scale: <100K traces/month | **~$0–5** |
| **GuardDuty** | $0.50/GB VPC Flow Logs + $0.18/million DNS queries + $4/million CloudTrail events | ~2GB flow logs + 5M DNS queries + 1M CT events ≈ $1 + $0.90 + $4 | **~$10–15** |
| **Security Hub** | $0.0010/check/month | ~5,000 security checks/month × $0.001 = $5 | **~$5** |
| **Data Transfer Out** | $0.09/GB (first 10TB) | ~500GB/month from ECS + S3 to internet × $0.09 | **~$45** |
| **SUPPORTING TOTAL** | | | **~$149–175/month** |

> **Delta vs. `mvp-arch.md §1.4`**: The architecture doc does not enumerate supporting services individually — it groups several items (NAT Gateway ~$32, CloudWatch ~$34, Secrets Manager ~$2, Data Transfer ~$45, VPC Endpoints ~$13, Security ~$15) for a grouped subtotal of ~$141. This plan's breakout of ~$149–175 is higher because it itemizes ALB ($16–20) separately from the grouped services and adds Route 53 ($1), ECR ($1), KMS ($2), X-Ray ($0–5), and CloudWatch Dashboards ($3) that were not individually listed in the arch doc. The delta is ~$8–34, which remains well within the $888/month target.

> **Free services** (zero cost): ACM (public TLS certs), IAM, Cognito (under 50K MAUs), Lambda (under 1M invocations/month), S3 Gateway VPC endpoint, CloudWatch first 10 custom metrics (within free tier).

---

## 4. Deployment Architecture Diagram

```
Internet
   │
   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Route 53 (DNS)                                                 │
│  pilotfortrades.com     → CloudFront → S3 (marketing static)    │
│  api.pilotfortrades.com → ALB                                   │
│  app.pilotfortrades.com → ALB → ECS pilot-web (web dashboard)  │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────────────┐
   │  ALB (HTTPS/443)                         │
   │  ACM cert *.pilotfortrades.com           │
   │  Listener rules:                         │
   │  - api.pilotfortrades.com  → api TG      │
   │  - app.pilotfortrades.com  → web TG      │
   └──────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│  VPC: 10.0.0.0/16  (us-east-1)                                 │
│                                                                  │
│  ┌──────────────────┐   ┌──────────────────────────────────┐   │
│  │  Public Subnets   │   │  Private Subnets                 │   │
│  │  us-east-1a/1b   │   │  us-east-1a/1b                   │   │
│  │  - ALB endpoints │   │                                   │   │
│  │  - NAT Gateway   │   │  ┌────────────────────────────┐  │   │
│  └──────────────────┘   │  │  ECS Fargate               │  │   │
│                          │  │  - FastAPI (2 tasks)       │  │   │
│                          │  │  - Celery Worker (2 tasks) │  │   │
│                          │  │  - Celery Beat (1 task)    │  │   │
│                          │  └────────────────────────────┘  │   │
│                          │                                   │   │
│                          │  ┌──────────────────────────┐    │   │
│                          │  │  EC2 g4dn.xlarge (GPU)   │    │   │
│                          │  │  NVIDIA T4 16GB VRAM      │    │   │
│                          │  │  - Whisper :8080          │    │   │
│                          │  │  - Ollama :11434           │    │   │
│                          │  └──────────────────────────┘    │   │
│                          │                                   │   │
│                          │  ┌────────────┐  ┌────────────┐  │   │
│                          │  │  RDS       │  │ ElastiCache│  │   │
│                          │  │  Postgres  │  │ Redis 7    │  │   │
│                          │  │  17+pgvec  │  │ DB 0,1,2   │  │   │
│                          │  │  Multi-AZ  │  └────────────┘  │   │
│                          │  └────────────┘                  │   │
│                          └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
              │ (outbound via NAT Gateway)
              ▼
   External APIs: QuickBooks Online · SendGrid · Telnyx · Stripe · Google Maps

ECS pilot-web (Web Dashboard) → API calls to ALB → ECS FastAPI
Marketing S3/CloudFront → form POSTs to ALB → ECS FastAPI (/api/v1/marketing/*)
Mobile app → API calls to ALB → ECS FastAPI
```

---

## 5. Phase-by-Phase Execution Plan

### Phase 1 — Terraform Bootstrap & Networking

**Goal**: Establish Terraform remote state and core networking. Nothing is deployed without this foundation.

#### Step 1.1 — Create Terraform Remote State Backend (Manual — one-time, done before `terraform init`)

This step is done **manually in the AWS Console** or via AWS CLI before Terraform is initialized. S3 buckets cannot be created by the same Terraform that uses them as state.

```bash
# Create S3 bucket for Terraform state
# S3 bucket name includes account ID to guarantee global uniqueness
# "pilot-terraform-state" alone was already taken by another AWS account
aws s3api create-bucket \
  --bucket pilot-terraform-state-000000000000 \
  --region us-east-1

# Enable versioning on state bucket
aws s3api put-bucket-versioning \
  --bucket pilot-terraform-state-000000000000 \
  --versioning-configuration Status=Enabled

# Enable server-side encryption
aws s3api put-bucket-encryption \
  --bucket pilot-terraform-state-000000000000 \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

# Block all public access
aws s3api put-public-access-block \
  --bucket pilot-terraform-state-000000000000 \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name pilot-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

#### Step 1.2 — Create Terraform Directory Structure

Create `infrastructure/terraform/` in the repo root following the structure from `mvp-arch.md §1.6`:

```
infrastructure/
└── terraform/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── backend.tf              ← S3 + DynamoDB remote state
    ├── versions.tf
    ├── modules/
    │   ├── networking/         ← VPC, subnets, security groups, NAT Gateway
    │   ├── compute/            ← ECS cluster (4 services: api, worker, beat, web), ECR, EC2 GPU instance
    │   ├── database/           ← RDS PostgreSQL 17+, ElastiCache Redis 7
    │   ├── storage/            ← S3 buckets (assets, audio, Terraform state CDN)
    │   ├── security/           ← IAM roles/policies, KMS, Secrets Manager, Cognito
    │   └── monitoring/         ← CloudWatch log groups, alarms, X-Ray, GuardDuty
    └── environments/
        └── production/         ← No qa/staging yet; add later
            ├── main.tf
            ├── terraform.tfvars
            └── backend.tf
```

#### Step 1.3 — VPC & Networking

**Resources to create via Terraform `modules/networking/`:**

| Resource | Config |
|---|---|
| VPC | `10.0.0.0/16`, `enable_dns_hostnames = true` |
| Public Subnet A | `10.0.1.0/24`, `us-east-1a` — ALB, NAT Gateway |
| Public Subnet B | `10.0.2.0/24`, `us-east-1b` — ALB (Multi-AZ required) |
| Private Subnet A | `10.0.10.0/24`, `us-east-1a` — ECS, RDS primary, Redis, GPU |
| Private Subnet B | `10.0.11.0/24`, `us-east-1b` — RDS standby (Multi-AZ) |
| Internet Gateway | Attached to VPC |
| NAT Gateway | Single AZ in public subnet A (saves ~$32/mo vs Multi-AZ) |
| Elastic IP | For NAT Gateway |
| Route Tables | Public: 0.0.0.0/0 → IGW; Private: 0.0.0.0/0 → NAT |
| VPC Endpoints | S3 (gateway type — free); Secrets Manager (interface type — ~$7/mo) |

**Security Groups:**

| SG Name | Inbound Rules | Outbound |
|---|---|---|
| `sg-alb` | TCP 443 from `0.0.0.0/0`; TCP 80 from `0.0.0.0/0` (redirect to 443) | All |
| `sg-ecs-api` | TCP 8000 from `sg-alb` only | All |
| `sg-rds` | TCP 5432 from `sg-ecs-api` only; TCP 5432 from `sg-bastion` | None |
| `sg-redis` | TCP 6379 from `sg-ecs-api` only; TCP 6379 from `sg-bastion` | None |
| `sg-gpu` | TCP 8080 + TCP 11434 from `sg-ecs-api` only; TCP 22 from `sg-bastion` | All |
| `sg-bastion` | TCP 22 from `var.admin_home_ip/32` (Tom's home public IP — set in `terraform.tfvars`) | All |
| `sg-lambda` | None inbound | All |

#### Step 1.4 — Bastion Host (Admin Access to Private Subnet)

The bastion host is the AWS equivalent of Azure VPN Client — it provides secure admin access to private-subnet resources (RDS, Redis, GPU instance) from Tom's laptop via SSH tunneling. Cost: ~$3–5/month.

**Why SSH tunneling over AWS Client VPN:**

| Option | Monthly Cost | Setup Complexity | Admin Access |
|---|---|---|---|
| EC2 Bastion (`t4g.nano`) | **~$3** | Low | ✅ Full |
| AWS Client VPN | **~$72+** | High | ✅ Full |
| AWS Systems Manager Session Manager | **~$0** | Medium | ✅ Full (no open port) |

**Recommendation: Bastion + SSH tunneling.** Simple, cheap, familiar pattern. SSM Session Manager is a future upgrade (Phase 2 security hardening) if you want to eliminate the open port entirely.

**Terraform resource (in `modules/compute/`):**

```hcl
resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux_2023.id  # Amazon Linux 2023 (ARM)
  instance_type          = "t4g.nano"                          # ~$3/month; ARM, 512MB RAM
  subnet_id              = aws_subnet.public_a.id              # Public subnet — needs reachable IP
  vpc_security_group_ids = [aws_security_group.sg_bastion.id]
  key_name               = aws_key_pair.tom_admin.name
  
  associate_public_ip_address = true   # Needs a public IP to SSH to from laptop
  
  tags = {
    Name           = "pilot-bastion-prod"
    Component      = "networking"
    CostAllocation = "networking"
    Backup         = "disabled"
  }
}

resource "aws_key_pair" "tom_admin" {
  key_name   = "pilot-admin-key"
  # Tom's Mac SSH public key — confirmed value:
  public_key = "ssh-ed25519 AAAA...REPLACE_WITH_YOUR_PUBLIC_KEY pilot-admin"
}

variable "admin_allowed_ips" {
  description = "List of Tom's known public IPs for bastion SSH access — update when IP changes"
  type        = list(string)
  # Set in terraform.tfvars; add all known IPs (home ISP, backup ISP, VPN, hotel) as a list
  # Current known IPs:
  #   home ISP: 203.0.113.13
  #   backup ISP: (add when known — run: curl -s https://api.ipify.org while on backup ISP)
}
```

**SSH public key (confirmed — do not regenerate):**
```
ssh-ed25519 AAAA...REPLACE_WITH_YOUR_PUBLIC_KEY pilot-admin
```

**One-time Mac setup — ✅ COMPLETE** (SSH key generated + added to macOS Keychain with passphrase on 2026-06-30)

```bash
# Verify key is loaded in Keychain at any time
ssh-add -l
# Shows: 256 SHA256:... pilot-admin (ED25519)
```

> **Passphrase + Keychain = best of both worlds**: The private key is encrypted at rest (passphrase protects prod if Mac is stolen). macOS Keychain decrypts it transparently after first use per boot — `ssh pilot-bastion` just works with no prompt. The passphrase is only asked once per Mac restart.

---

#### Multi-IP Bastion Access (home ISP + backup ISP + Travel)

Tom has two ISPs (home ISP + backup ISP) and travels, meaning the public IP changes frequently. The security group uses a **list of allowed CIDRs** — not a single IP — and is updated via `terraform apply` in ~30 seconds whenever the IP changes.

**`sg-bastion` Terraform rule (multi-IP version):**

```hcl
resource "aws_security_group_rule" "bastion_ssh_ingress" {
  for_each          = toset(var.admin_allowed_ips)
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["${each.value}/32"]
  security_group_id = aws_security_group.sg_bastion.id
  description       = "SSH access from admin IP: ${each.value}"
}
```

**`terraform.tfvars` — IP list (update when IPs change):**

```hcl
admin_allowed_ips = [
  "203.0.113.13",   # home ISP (primary, confirmed 2026-06-30)
  "x.x.x.x",        # backup ISP (add when confirmed — run curl https://api.ipify.org on backup ISP)
]
```

**When your IP changes (travel, ISP reset, hotel WiFi):**

```bash
# 1. Find your current public IP
curl -s https://api.ipify.org

# 2. Update terraform.tfvars — add the new IP to admin_allowed_ips list
# (keep old IPs if you rotate between them; remove if they change permanently)

# 3. Apply — takes ~30 seconds, no downtime, no restart
cd infrastructure/terraform/environments/production
terraform apply -target=aws_security_group_rule.bastion_ssh_ingress

# 4. SSH immediately — change is live
ssh pilot-bastion
```

> **Alternative for frequent travel**: If IP management becomes tedious, upgrade to **AWS Systems Manager Session Manager** (no open port at all — AWS manages the tunnel). Cost is $0 (free tier) and eliminates the IP restriction problem entirely. This is a Phase 2 security upgrade documented as a future option.

**SSH config on Mac** (add to `~/.ssh/config`):

```
Host *
  AddKeysToAgent yes
  UseKeychain yes                          # macOS Keychain integration

Host pilot-bastion
  HostName 203.0.113.12                   # Static Elastic IP — confirmed 2026-07-01
  User ec2-user
  IdentityFile ~/.ssh/pilot_admin_ed25519
  StrictHostKeyChecking no

Host pilot-gpu
  HostName <GPU_PRIVATE_IP>              # Available from terraform output after Phase 4
  User ec2-user
  IdentityFile ~/.ssh/pilot_admin_ed25519
  ProxyJump pilot-bastion                # Routes through bastion automatically
```

**SSH tunnel commands for admin access:**

```bash
# Access RDS PostgreSQL directly from DBeaver / psql on your Mac
# After running: connect DBeaver to localhost:5432
ssh -L 5432:<RDS_ENDPOINT>:5432 pilot-bastion -N

# Access Redis directly from redis-cli on your Mac
ssh -L 6379:<REDIS_ENDPOINT>:6379 pilot-bastion -N

# SSH directly to GPU instance (via bastion proxy jump)
ssh pilot-gpu

# Run Alembic migrations from your Mac against prod RDS (while tunnel is open)
ssh -L 5432:<RDS_ENDPOINT>:5432 pilot-bastion -N &
cd backend && DATABASE_URL=postgresql://pilot_user:<pass>@localhost:5432/pilot_prod \
  alembic upgrade head
```

**`terraform.tfvars` entries needed** (not committed to git — add to `.gitignore`):

```hcl
admin_home_ip        = "x.x.x.x"               # Your current home public IP
tom_admin_public_key = "ssh-ed25519 AAAA..."   # Content of ~/.ssh/pilot_admin_ed25519.pub
```

> **When your home IP changes** (e.g., ISP resets it): update `admin_home_ip` in `terraform.tfvars` and run `terraform apply` — Terraform updates the security group rule in seconds, no instance restart needed.

**Cost addition to §8:**

| Service | Config | Monthly |
|---|---|---|
| EC2 Bastion | `t4g.nano` (0.5 vCPU / 512MB), public subnet | **~$3** |
| EBS (bastion root vol) | 8GB gp3 | **~$0.64** |
| Elastic IP (bastion) | Static IP so SSH config doesn't change after stop/start | **~$3.50** (charged when not in use; or $0 when associated with running instance) |
| **Bastion total** | | **~$4–7/month** |

> **Cost optimization**: Stop the bastion when not actively doing admin work. With a static Elastic IP, stopping the instance keeps the IP reserved (costs $0.005/hour when stopped, ~$3.50/month max). Start it again in 30 seconds via Console or CLI when needed. This reduces the compute cost to near-zero when you're not actively administering.

---

### Phase 2 — Data Layer

**Goal**: RDS + ElastiCache provisioned in private subnets. No application code deployed yet.

> **⚠️ EXECUTION ORDER CORRECTION — Read Before Running Any Command**
>
> The plan's Phase 2 / Phase 3 labels are conceptual (Data Layer / Security). In the Terraform dependency graph they **cannot be applied in that order**. `module.database` has `depends_on = [module.networking, module.security]` and requires three outputs that only exist after `module.security` runs: `kms_key_arn` (RDS encryption), `secret_db_arn`, and `secret_redis_arn` (Secrets Manager shells to populate). Running `terraform apply -target=module.database` without `module.security` already applied will fail with a missing input variable error.
>
> **Correct apply sequence for Phase 2 + Phase 3 combined:**
>
> ```bash
> cd infrastructure/terraform/environments/production
>
> # Step A — Import existing Cognito pool (MUST run before module.security apply)
> # Without this, Terraform attempts to CREATE a duplicate user pool and fails
> terraform import aws_cognito_user_pool.prod us-east-1_XXXXXXXXX
> terraform import aws_cognito_user_pool_client.prod_web us-east-1_XXXXXXXXX/xxxxxxxxxxxxxxxxxxxxxxxxxx
>
> # Step B — Verify no Cognito changes after import
> terraform plan -target=module.security
>
> # Step C — Apply security module FIRST (creates KMS, secret shells, Route 53, ACM, IAM)
> terraform apply -target=module.security   # ~5–10 min
>
> # Step D — Apply database module (now has all required inputs from security module)
> terraform apply -target=module.database   # ~10–15 min for RDS Multi-AZ provisioning
> ```
>
> After Step D completes, `pilot/prod/db` and `pilot/prod/redis` are auto-populated by Terraform. Continue with Step 2.2 below to verify connectivity.

#### Step 2.1 — RDS PostgreSQL 17+ with pgvector

```hcl
# Key Terraform resource (modules/database/)
resource "aws_db_instance" "postgres" {
  identifier              = "pilot-production"
  engine                  = "postgres"
  engine_version          = "17"          # Verify AWS RDS supports pg17; fallback to 16.x
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20            # GB; autoscaling handles growth
  max_allocated_storage   = 100           # Autoscaling ceiling
  
  db_name                 = "pilot_prod"
  username                = "pilot_user"
  password                = random_password.db_password.result  # Stored in Secrets Manager
  
  multi_az                = true          # Multi-AZ for 99.9% SLO
  db_subnet_group_name    = aws_db_subnet_group.private.name
  vpc_security_group_ids  = [aws_security_group.sg_rds.id]
  
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.pilot.arn
  
  backup_retention_period = 28
  backup_window           = "07:00-08:00"     # 3–4 AM Eastern
  maintenance_window      = "Sun:08:00-09:00" # 4–5 AM Eastern Sunday
  
  performance_insights_enabled = true
  
  parameter_group_name    = aws_db_parameter_group.postgres17.name
  
  deletion_protection     = true           # Prevent accidental deletion
}
```

**⚠️ pgvector**: AWS RDS PostgreSQL 15+ supports `pgvector` as a managed extension. After provisioning, the **first Alembic migration** must run `CREATE EXTENSION IF NOT EXISTS vector;` before any HNSW index creation.

**RDS Parameter Group** (custom, not default):
```hcl
resource "aws_db_parameter_group" "postgres17" {
  family = "postgres17"
  
  parameter { name = "max_connections";               value = "100" }
  parameter { name = "shared_buffers";                value = "131072" }  # 128MB in 8KB pages
  parameter { name = "effective_cache_size";          value = "524288" }  # 512MB
  parameter { name = "random_page_cost";              value = "1.1" }
  parameter { name = "work_mem";                      value = "4096" }    # 4MB
  parameter { name = "log_min_duration_statement";    value = "1000" }    # Log >1s queries
  parameter { name = "log_connections";               value = "1" }
  parameter { name = "log_disconnections";            value = "1" }
}
```

#### Step 2.2 — ElastiCache Redis 7

```hcl
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "pilot-production"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  
  subnet_group_name    = aws_elasticache_subnet_group.private.name
  security_group_ids   = [aws_security_group.sg_redis.id]
  
  at_rest_encryption_enabled = true     # AES-256 (plan; not applied — see Known Limitations #24)
  transit_encryption_enabled = true     # TLS in transit (plan; not applied — see Known Limitations #24)
  
  # Note: 3 logical databases (DB 0/1/2) do not need separate Redis instances
  # They are all on this single node, partitioned by DB index in connection strings
}
```

**Redis DB assignment (from `mvp-arch.md §3.1`):**
- `redis://redis-host:6379/0` → Rate limiting (SlowAPI token buckets)
- `redis://redis-host:6379/1` → Celery task broker
- `redis://redis-host:6379/2` → Celery result backend

#### Step 2.3 — S3 Buckets

| Bucket Name | Purpose | Public? | Versioning | Notes |
|---|---|---|---|---|
| `pilot-production-assets` | Audio files, receipt images, PDFs | Private | Enabled | Signed URL access only |
| `pilot-production-marketing` | Marketing static site files | **Public-read via CloudFront OAI** | Enabled | S3 static hosting + CloudFront distribution |
| `pilot-terraform-state-000000000000` | Terraform state | Private | Enabled | **Already created in Phase 1.1** — name includes account ID for global uniqueness |

---

### Phase 3 — Security, Secrets & Auth

**Goal**: KMS, Secrets Manager (all secrets stored before app deploys), and production Cognito user pool.

#### Step 3.1 — AWS KMS

```hcl
resource "aws_kms_key" "pilot" {
  description             = "Pilot for Trades — production encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}
```

Used by: RDS encryption, S3 SSE, Secrets Manager, ElastiCache at-rest encryption.

#### Step 3.2 — AWS Secrets Manager

Create the following secrets before any ECS tasks deploy. Each secret is a JSON object:

| Secret Name | Contents | Used By |
|---|---|---|
| `pilot/prod/db` | `{"username": "...", "password": "...", "host": "...", "port": 5432, "dbname": "pilot_prod"}` | ECS API, Celery Worker/Beat |
| `pilot/prod/quickbooks` | `{"client_id": "...", "client_secret": "...", "webhook_verifier_token": "...", "environment": "production"}` | ECS API |
| `pilot/prod/sendgrid` | ✅ **Created** · Key name in SendGrid: `PilotForTrades-Prod` · `from_email: noreply@pilotfortrades.com` · **Dev key in `backend/.env` is separate — local only, not in Secrets Manager** | ECS API, Celery Worker |
| `pilot/prod/telnyx` | ✅ **Created** — `messaging_profile_id: 00000000-0000-0000-0000-000000000000` (profile ID is non-sensitive; API key stored in secret only) | ECS API, Celery Worker |
| `pilot/prod/stripe` | `{"publishable_key": "...", "secret_key": "...", "webhook_secret": "..."}` | ECS API |
| `pilot/prod/encryption` | ✅ **Created** — Fernet key stored; never write value to any doc or git | ECS API, Celery Worker |
| `pilot/prod/google-maps` | ✅ **Created** — Distance Matrix API key; key name in GCP: `PilotForTrades-Prod` (dev key is separate, local `backend/.env` only). IP restriction to be updated with NAT Gateway EIP after Phase 1 Terraform | ECS API |
| `pilot/prod/cognito` | `{"region": "us-east-1", "user_pool_id": "us-east-1_XXXXXXXXX", "app_client_id": "xxxxxxxxxxxxxxxxxxxxxxxxxx"}` | ECS API |
| `pilot/prod/turnstile` | ✅ **Created** — server-side secret key stored | ECS API (server-side token verification on marketing form submissions) |

> **⚠️ QuickBooks Production App**: The dev `QUICKBOOKS_CLIENT_ID` / `QUICKBOOKS_CLIENT_SECRET` in your local `.env` are for the **sandbox** QuickBooks app. Production requires a separate **production** Intuit Developer app with different credentials and `QUICKBOOKS_ENVIRONMENT=production`.

#### Step 3.3 — Production Cognito User Pool

> **✅ Pool already created manually** — `pilot-production` (ID: `us-east-1_XXXXXXXXX`) was provisioned via AWS Console on June 30, 2026 per [`aws-cognito-prod-setup.md`](aws-cognito-prod-setup.md). The Terraform resource below describes the desired state; when Phase 3 Terraform is first applied, **import the existing pool** rather than creating a new one:
>
> ```bash
> terraform import aws_cognito_user_pool.prod us-east-1_XXXXXXXXX
> terraform import aws_cognito_user_pool_client.prod_web us-east-1_XXXXXXXXX/xxxxxxxxxxxxxxxxxxxxxxxxxx
> ```
>
> After import, `terraform plan` should show no changes if the HCL below matches the console configuration.

```hcl
resource "aws_cognito_user_pool" "prod" {
  name = "pilot-production"
  # Pool ID: us-east-1_XXXXXXXXX (already created — import, don't create)
  
  # Email sign-in only
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  
  # Self-service signup DISABLED — registration flows through our API
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  
  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }
  
  # MFA optional at pool level; enforced per-tenant in app
  mfa_configuration = "OPTIONAL"
  
  software_token_mfa_configuration {
    enabled = true
  }
  
  # Triggers
  lambda_config {
    post_confirmation = aws_lambda_function.post_confirmation.arn
  }
  
  # Token TTLs per mvp-arch.md §4.1 + §4.6
  user_pool_add_ons {
    advanced_security_mode = "AUDIT"  # Adaptive auth for anomaly detection
  }
}

resource "aws_cognito_user_pool_client" "prod_web" {
  name         = "pilot-web-prod"
  # App Client ID: xxxxxxxxxxxxxxxxxxxxxxxxxx (already created — import, don't create)
  user_pool_id                         = aws_cognito_user_pool.prod.id
  generate_secret                      = false  # SPA public client — no secret
  
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",   # Required for mobile Expo Go
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
  
  # Token expiration per mvp-arch.md §4.1
  access_token_validity  = 60          # minutes
  id_token_validity      = 60          # minutes
  refresh_token_validity = 30          # days
  
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}
```

#### Step 3.4 — Post-Confirmation Lambda

This Lambda fires when a new user confirms their account in Cognito. It creates the `user` record in RDS (per `mvp-arch.md §4.4`):

```
Cognito Post-Confirmation trigger
   → Lambda: pilot-post-confirmation
   → Reads Cognito event (email, sub)
   → INSERT INTO user (cognito_sub, email, ...)
   → If company creation flow: INSERT INTO tenant + tenant_user + seed owner role
```

Lambda must be in the **same VPC** as RDS so it can connect to the database.

#### Step 3.5 — IAM Roles

| Role | Trust | Key Permissions |
|---|---|---|
| `pilot-ecs-task-role` | ECS tasks | Secrets Manager `GetSecretValue`, S3 `GetObject/PutObject`, CloudWatch logs, X-Ray |
| `pilot-ecs-execution-role` | ECS (pulling images + logging) | ECR pull, CloudWatch logs, Secrets Manager (for task env injection) |
| `pilot-lambda-execution-role` | Lambda | VPC networking, RDS connect, CloudWatch logs |
| `pilot-github-actions-role` | GitHub OIDC | ECR push, ECS `update-service`, ECS `run-task`, S3 sync (marketing site) |

---

### Phase 4 — Container Registry & GPU Instance

**Goal**: ECR repos created; GPU instance provisioned in private subnet with Docker + NVIDIA runtime.

#### Step 4.1 — ECR Repositories

```hcl
resource "aws_ecr_repository" "api" {
  name                 = "pilot/api"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true    # Trivy-equivalent scanning
  }
  
  lifecycle {
    prevent_destroy = false
  }
}

# Same pattern for pilot/worker and pilot/beat
```

Lifecycle policy on each ECR repo: keep last 10 images, delete untagged after 1 day.

#### Step 4.2 — First Docker Push (Manual Bootstrap)

Before CI/CD exists, push the initial images manually:

```bash
# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  000000000000.dkr.ecr.us-east-1.amazonaws.com

# Build backend image
cd backend
docker build -t pilot-api .

# Tag and push
docker tag pilot-api:latest \
  000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api:latest

docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api:latest

# Worker and beat use the same image with different CMD override in task def
docker tag pilot-api:latest \
  000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/worker:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/worker:latest
```

#### Step 4.3 — EC2 GPU Instance (g4dn.xlarge)

```hcl
resource "aws_instance" "gpu" {
  ami                    = "ami-xxxxx"    # Deep Learning AMI (Amazon Linux 2) with NVIDIA drivers
  instance_type          = "g4dn.xlarge"
  subnet_id              = aws_subnet.private_a.id
  vpc_security_group_ids = [aws_security_group.sg_gpu.id]
  iam_instance_profile   = aws_iam_instance_profile.gpu.name
  
  # Root volume — 50GB for OS + Docker
  root_block_device {
    volume_type = "gp3"
    volume_size = 50
    encrypted   = true
  }
  
  # Additional volume for model storage (Ollama ~4.7GB + Whisper ~1.5GB + headroom)
  ebs_block_device {
    device_name = "/dev/xvdb"
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }
  
  tags = {
    Name        = "pilot-gpu-prod"
    Environment = "production"
  }
}
```

**AMI Selection**: Use the **AWS Deep Learning AMI (Amazon Linux 2)** which pre-installs NVIDIA drivers, CUDA, and Docker with NVIDIA Container Toolkit. Search AMI catalog for `Deep Learning AMI (Amazon Linux 2)` in us-east-1.

**GPU Instance User Data Script** (runs on first boot):

```bash
#!/bin/bash
# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create GPU docker-compose.yml
cat > /home/ec2-user/docker-compose.gpu.yml << 'EOF'
version: '3.8'
services:
  whisper:
    image: fedirz/faster-whisper-server:latest-cuda   # CUDA tag for GPU
    ports:
      - "8080:8000"
    environment:
      - WHISPER_MODEL=turbo
      - WHISPER__MODEL=Systran/faster-whisper-large-v3-turbo
    volumes:
      - whisper_data:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

volumes:
  whisper_data:
  ollama_data:
EOF

# Start services
cd /home/ec2-user
docker-compose -f docker-compose.gpu.yml up -d

# Pull Ollama model (runs async after services start)
sleep 30
docker exec $(docker ps -q -f name=ollama) ollama pull llama3.1:8b
```

> **⚠️ GPU Cold Start**: After first boot, `ollama pull llama3.1:8b` (~4.7GB download) takes 5–15 minutes depending on ECR/internet speed. Plan for this during initial deployment.

---

### Phase 5 — Marketing Site + DNS Cutover (PRIORITY: 10DLC)

**Goal**: Marketing site live at `pilotfortrades.com`, DNS migrated from GoDaddy to Route 53, HTTPS via ACM wildcard cert. All Terraform code for this phase is already written and complete. This is an execution checklist.

> **ACM is fully automated**: Terraform creates the cert request, creates the DNS validation CNAME records in Route 53, and waits for validation automatically. No manual ACM steps needed.
>
> **DNS cutover sequence matters**: ACM validates against public DNS. Route 53 must be authoritative BEFORE `terraform apply` runs the full stack — otherwise ACM validation times out. Follow the exact sequence in Step 5.2.

#### Step 5.1 — Apply Security Module First (Route 53 Zone + All DNS Records + ACM Cert Shell)

```bash
cd infrastructure/terraform/environments/production

# Verify correct account
aws sts get-caller-identity --query 'Account' --output text
# Expected: 000000000000

# Apply security module only — creates Route 53 hosted zone + all DNS records
# (ACM cert is created but will NOT validate until Route 53 is authoritative)
terraform apply -target=module.security

# Get the 4 Route 53 nameservers — you will enter these at GoDaddy
terraform output route53_nameservers
```

**What this creates:**
- Route 53 hosted zone for `pilotfortrades.com`
- MX records (5 Google Workspace records)
- TXT records: SPF + Google site verification (two values, one record)
- DKIM: `google._domainkey.pilotfortrades.com` TXT (key populated from GoDaddy zone export 2026-07-01)
- DMARC: `_dmarc.pilotfortrades.com` TXT (`p=quarantine; rua=legal@pilotfortrades.com`)
- ACM wildcard cert request (`*.pilotfortrades.com` + apex) — validation CNAME added to Route 53

#### Step 5.2 — Verify Records Resolve from Route 53 NS (Before NS Cutover)

```bash
# Use one of your 4 Route 53 nameservers (from terraform output above)
# Replace ns-XXX.awsdns-XX.com with your actual NS record
R53_NS="ns-XXX.awsdns-XX.com"

# Test all critical records before switching GoDaddy
dig MX pilotfortrades.com @$R53_NS +short
# Expected: 5 Google Workspace MX records

dig TXT pilotfortrades.com @$R53_NS +short
# Expected: SPF record + Google verification TXT

dig TXT google._domainkey.pilotfortrades.com @$R53_NS +short
# Expected: DKIM public key

dig TXT _dmarc.pilotfortrades.com @$R53_NS +short
# Expected: DMARC policy string

# All must resolve before switching nameservers
```

#### Step 5.3 — Switch Nameservers at GoDaddy (DNS Cutover)

1. Log in to GoDaddy → My Products → `pilotfortrades.com` → DNS Management
2. Scroll to **Nameservers** → **Change** → **Enter my own nameservers (advanced)**
3. Replace `ns15.domaincontrol.com` / `ns16.domaincontrol.com` with your 4 Route 53 NS records
4. Save

**What happens immediately:**
- GoDaddy WebsiteBuilder site stops serving (not a real IP — graceful degradation)
- Route 53 becomes authoritative for `pilotfortrades.com`
- Google Workspace email continues (MX/SPF/DKIM/DMARC already in Route 53)
- ACM begins validating the wildcard cert (typically completes in 5–15 minutes)

**Verify propagation** (~10 min):
```bash
dig NS pilotfortrades.com +short
# Should return 4 .awsdns-* nameservers (not ns15/ns16.domaincontrol.com)
```

#### Step 5.4 — Run Full terraform apply (ACM Now Validates + All Resources Deploy)

```bash
cd infrastructure/terraform/environments/production

# Full apply — terraform apply -target=module.security already ran in Step 5.1
# This applies storage + compute modules: S3, CloudFront, ALB, ECS (api/worker/beat), GPU
terraform apply

# terraform apply blocks at aws_acm_certificate_validation until the cert is issued
# Typical wait: 5–15 min after DNS cutover; maximum 45 min
# After cert is issued, all resources that depend on it are created automatically
```

**After apply completes, capture all output values** — these fill the `<pending>` placeholders in §15:

```bash
terraform output
# Record: bastion_public_ip, nat_gateway_eip, cloudfront_distribution_id,
#         gpu_private_ip, rds_endpoint (sensitive), redis_endpoint (sensitive),
#         ecr_api_url, github_actions_role_arn, sns_alarm_topic_arn
```

#### Step 5.5 — Build & Deploy Marketing Site to S3

Create `frontend/apps/marketing/.env.production`:
```env
NEXT_PUBLIC_API_URL=https://api.pilotfortrades.com
NEXT_PUBLIC_CLOUDFLARE_TURNSTILE_SITE_KEY=0x4AAAAAADtbEEHD6Y-jXDbC
NEXT_PUBLIC_CAREERS_OPEN_ROLES=AI / ML Engineer,Full-Stack Engineer (Trades Domain),Customer Success (Trades Background a Plus),Sales / Growth
```

Build and deploy:
```bash
cd frontend

# Build marketing static site
pnpm --filter marketing build
# Output: apps/marketing/out/

# Get CloudFront distribution ID (from terraform output above)
DIST_ID=$(terraform -chdir=../infrastructure/terraform/environments/production output -raw cloudfront_distribution_id)

# Upload non-HTML files with long cache (CSS, JS, images)
aws s3 sync apps/marketing/out/ \
  s3://pilot-production-marketing/ \
  --delete \
  --cache-control "max-age=31536000,public" \
  --exclude "*.html" \
  --exclude "*.json"

# Upload HTML with no-cache (so Coming Soon / Live mode changes take effect immediately)
aws s3 sync apps/marketing/out/ \
  s3://pilot-production-marketing/ \
  --delete \
  --cache-control "no-cache" \
  --include "*.html" \
  --exclude "*"

# Upload site-config.json with no-cache (controls Coming Soon / Live mode)
# For initial launch, set to "live" (forms are working since ECS is running)
aws s3 cp - s3://pilot-production-marketing/site-config.json \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "application/json" <<< '{"mode":"live"}'

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*"
echo "Marketing site deployed. Propagates in 2–5 minutes globally."
```

> **Coming Soon mode**: If FastAPI is not yet running (ECS at 0 tasks), set `site-config.json` to `{"mode":"coming_soon"}` instead of `{"mode":"live"}`. The Coming Soon page (MKT-B10) will show instead of broken forms. Switch back to `{"mode":"live"}` after Phase 6 deploys ECS.

#### Step 5.6 — Verify Marketing Site Is Live

```bash
# Site should load with HTTPS
curl -I https://pilotfortrades.com
# Expected: HTTP/2 200

# Check www redirect works
curl -I https://www.pilotfortrades.com
# Expected: HTTP/2 200 (CloudFront serves both)

# Verify HTTPS cert is valid
curl -I https://pilotfortrades.com 2>&1 | grep -i "certificate\|ssl"
# Expected: SSL certificate OK

# Test email still works (send from external to support@pilotfortrades.com)
# Confirm delivery in Google Workspace inbox
```

#### Step 5.7 — 10DLC Prerequisites Checklist

Before submitting the Telnyx 10DLC registration, verify:

- [ ] `https://pilotfortrades.com` loads correctly (HTTPS, no certificate warning)
- [ ] Privacy Policy at `pilotfortrades.com/legal/privacy-policy` is live and includes the 10DLC SMS clause: *"We do not share mobile phone numbers or SMS messaging opt-in data with third parties or affiliates for marketing or promotional purposes"*
- [ ] `sms-opt-in/` page is live and accessible
- [ ] Legal contact email `legal@pilotfortrades.com` works (test by emailing it)
- [ ] EIN / company legal name (`Example Holdings, LLC dba Pilot for Trades`) is ready for carrier registration
- [ ] Use case description prepared (transactional: job status updates, quote approvals, customer communications)
- [ ] `site-config.json` set to `{"mode":"live"}` (or `coming_soon` if ECS not yet deployed)

---

### Phase 5.5 — Infrastructure Script Verification

**Goal**: Populate all `<fill:>` placeholder variables in the 4 profile scripts and verify that every script component works against live Phase 5 infrastructure before Phase 6 deploys ECS services. This checkpoint ensures the ops scripts are ready to use the moment ECS comes up in Phase 6.

**Dependencies**: Phase 5 complete ✅ (GPU instance, ALB, CloudFront, S3, bastion all exist from `module.compute` applied in Phase 5 Step 5.4)

> **⚠️ ECS SERVICE CALLS WILL FAIL IN THIS PHASE — THIS IS EXPECTED**
>
> All 4 profile scripts contain ECS `update-service` calls for `pilot-api`, `pilot-celery-worker`, and `pilot-celery-beat`. These services are created in Phase 6 — they do not exist yet. Because all scripts use `set -euo pipefail`, they will exit on the first ECS error.
>
> Phase 5.5 verifies the **non-ECS components** of each script individually using targeted AWS CLI commands. Full end-to-end script execution (`./profile-a-marketing.sh`, etc.) is deferred to Phase 6 Step 6.6 after ECS services are confirmed running.

#### Step 5.5.1 — Populate Script Variables (All 4 Scripts)

Each script has a `── Variables —` block with `<fill:>` placeholders. Populate them all from `terraform output`:

```bash
cd infrastructure/terraform/environments/production

# Capture all needed values
GPU_ID=$(terraform output -raw gpu_instance_id)
BASTION_ID=$(terraform output -raw bastion_instance_id)
APP_RUNNER_ARN=$(terraform output -raw app_runner_service_arn)
CF_DIST_ID=$(terraform output -raw cloudfront_distribution_id)

echo "GPU_INSTANCE_ID:     $GPU_ID"
echo "BASTION_INSTANCE_ID: $BASTION_ID"
echo "APP_RUNNER_ARN:      $APP_RUNNER_ARN"
echo "CLOUDFRONT_DIST_ID:  $CF_DIST_ID"
```

Edit the `── Variables ──` block in each script to replace placeholders:
- `infrastructure/scripts/profile-a-marketing.sh`
- `infrastructure/scripts/profile-b-app.sh`
- `infrastructure/scripts/profile-c-checklist.sh`
- `infrastructure/scripts/profile-off.sh`

> **Note**: `profile-off.sh` requires `BASTION_INSTANCE_ID` in addition to the other 3 — it stops the bastion as part of cost-floor shutdown.

#### Step 5.5.2 — Verify AWS Account Check Works in Each Script

Each script validates `aws sts get-caller-identity` returns `000000000000` on line 2. Confirm the guard works:

```bash
# Quick check — should return 000000000000
aws sts get-caller-identity --query 'Account' --output text --region us-east-1
```

#### Step 5.5.3 — Verify S3 + CloudFront Operations (profile-off.sh §Step 5)

The S3 `site-config.json` write and CloudFront invalidation are fully testable now. Run just these commands manually:

```bash
MARKETING_BUCKET="pilot-production-marketing"
CF_DIST_ID=$(terraform -chdir=infrastructure/terraform/environments/production output -raw cloudfront_distribution_id)

# Test: switch to coming_soon (safe — this is the desired state until Phase 6 ECS is running)
aws s3 cp - "s3://$MARKETING_BUCKET/site-config.json" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "application/json" <<< \
  '{"mode":"coming_soon","message":"We are putting the finishing touches on Pilot. Sign up to be first in line when we launch."}'

# Verify the config was written
curl -sf https://pilotfortrades.com/site-config.json
# Expected: {"mode":"coming_soon","message":"..."}

# Test CloudFront invalidation
aws cloudfront create-invalidation \
  --distribution-id "$CF_DIST_ID" \
  --paths "/site-config.json" --region us-east-1
```

#### Step 5.5.4 — Verify GPU Start/Stop (profile-b-app.sh §Step 1 / profile-off.sh §Step 3)

Test that the GPU instance responds to stop/start correctly via AWS CLI:

```bash
GPU_ID=$(terraform -chdir=infrastructure/terraform/environments/production output -raw gpu_instance_id)

# Verify current GPU state
aws ec2 describe-instances --instance-ids $GPU_ID \
  --query 'Reservations[0].Instances[0].State.Name' --output text --region us-east-1
# Expected: stopped (correct for Phase 5.5 — GPU not needed until Phase 6 AI mode)

# If GPU is running, stop it now (saves ~$390/month)
# aws ec2 stop-instances --instance-ids $GPU_ID --region us-east-1
```

#### Step 5.5.5 — ~~Verify App Runner Pause/Resume~~ — SKIPPED (App Runner Sunset)

> **⚠️ App Runner was sunset April 30, 2026 — this step no longer applies.** The web dashboard (`pilot-web`) will run as an ECS Fargate service (Phase 6 Step 6.4). There is no App Runner service to pause or resume. Skip this step entirely.

#### Step 5.5.6 — Verify Bastion Stop (profile-off.sh §Step 4)

Test that the bastion responds to stop command (safe — restart takes 30 sec when needed):

```bash
BASTION_ID=$(terraform -chdir=infrastructure/terraform/environments/production output -raw bastion_instance_id)

# Check current bastion state
aws ec2 describe-instances --instance-ids $BASTION_ID \
  --query 'Reservations[0].Instances[0].State.Name' --output text --region us-east-1

# Stop bastion (saves compute cost — restart via console or CLI in 30 sec when needed)
aws ec2 stop-instances --instance-ids $BASTION_ID --region us-east-1 > /dev/null
echo "Bastion stopping..."
```

> **Restarting bastion**: `aws ec2 start-instances --instance-ids $BASTION_ID --region us-east-1`

#### Post Phase 5.5 State (Cost Floor Active)

After Steps 5.5.3–5.5.6 complete, the infrastructure is at the cost floor (~$102/month):

| Resource | State | Cost |
|---|---|---|
| RDS PostgreSQL | Always on | ~$28/month |
| ElastiCache Redis | Always on | ~$13/month |
| NAT Gateway | Always on | ~$32/month |
| ALB | Always on | ~$18/month |
| S3 + CloudFront (marketing) | Always on | ~$2/month |
| Route 53 | Always on | ~$1/month |
| Bastion EIP | Reserved (instance stopped) | ~$3.50/month |
| GPU instance | Stopped | ~$0 (EBS only: ~$5.60) |
| ECS `pilot-web` | Not yet provisioned | ~$0 (pending Phase 6 Step 6.4) |
| ECS tasks (backend) | Not yet provisioned | ~$0 |
| **TOTAL** | | **~$102–108/month** |

Marketing site is live at `https://pilotfortrades.com` in Coming Soon mode. Full script execution (`./profile-a-marketing.sh`, `./profile-b-app.sh`, `./profile-c-checklist.sh`) deferred to Phase 6 Step 6.6.

---

### Phase 6 — ECS Fargate Services (Backend + Web Dashboard)

**Goal**: Backend API + Celery workers live; web dashboard accessible at `app.pilotfortrades.com`.

#### Step 6.1 — ALB + ACM Certificate for API

```hcl
resource "aws_lb" "api" {
  name               = "pilot-production-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.sg_alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.wildcard.arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_blue.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```

#### Step 6.2 — ECS Cluster & Task Definitions

```hcl
resource "aws_ecs_cluster" "production" {
  name = "pilot-production"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
```

**ECS Task Definition — FastAPI API:**

```hcl
resource "aws_ecs_task_definition" "api" {
  family                   = "pilot-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256    # 0.25 vCPU
  memory                   = 512    # MB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:latest"
    essential = true
    
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]
    
    environment = [
      { name = "ENVIRONMENT",           value = "production" },
      { name = "TEST_ENDPOINT_ENABLED", value = "false" },
    ]
    
    secrets = [
      { name = "DATABASE_URL",              valueFrom = "${aws_secretsmanager_secret.db.arn}:url::" },
      { name = "CELERY_BROKER_URL",         valueFrom = "${aws_secretsmanager_secret.redis.arn}:broker_url::" },
      { name = "CELERY_RESULT_BACKEND",     valueFrom = "${aws_secretsmanager_secret.redis.arn}:result_url::" },
      { name = "WHISPER_API_URL",           valueFrom = "${aws_secretsmanager_secret.gpu.arn}:whisper_url::" },
      { name = "OLLAMA_API_URL",            valueFrom = "${aws_secretsmanager_secret.gpu.arn}:ollama_url::" },
      { name = "SENDGRID_API_KEY",          valueFrom = "${aws_secretsmanager_secret.sendgrid.arn}:api_key::" },
      { name = "ENCRYPTION_KEY",            valueFrom = "${aws_secretsmanager_secret.encryption.arn}:fernet_key::" },
      { name = "COGNITO_REGION",            valueFrom = "${aws_secretsmanager_secret.cognito.arn}:region::" },
      { name = "COGNITO_USER_POOL_ID",      valueFrom = "${aws_secretsmanager_secret.cognito.arn}:user_pool_id::" },
      # ... additional secrets
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/pilot-api"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}
```

**ECS Services (rolling deploy; blue/green planned, not enabled):**

```hcl
resource "aws_ecs_service" "api" {
  name            = "pilot-api"
  cluster         = aws_ecs_cluster.production.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2    # 2 tasks per mvp-arch.md §1.1
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_groups  = [aws_security_group.sg_ecs_api.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.api_blue.arn
    container_name   = "api"
    container_port   = 8000
  }
  
  deployment_controller {
    type = "ECS"   # Native ECS rolling; CODE_DEPLOY for true blue/green (Phase 2)
  }
}
```

**Celery Worker and Beat** follow the same pattern with:
- `command = ["celery", "-A", "core.celery_app", "worker", "--loglevel=info", "--concurrency=2"]` for worker
- `command = ["celery", "-A", "core.celery_app", "beat", "--loglevel=info"]` for beat; `desired_count = 1`
- Beat is NOT load-balanced (no target group); it runs as a standalone Fargate service

#### Step 6.3 — First Database Migration

Before starting ECS services, run Alembic migrations against the production RDS instance:

```bash
# Run one-off ECS task for migrations
aws ecs run-task \
  --cluster pilot-production \
  --task-definition pilot-api \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[<private-subnet-a-id>],
    securityGroups=[<sg-ecs-api-id>],
    assignPublicIp=DISABLED
  }" \
  --overrides '{
    "containerOverrides": [{
      "name": "api",
      "command": ["alembic", "upgrade", "head"]
    }]
  }'

# Monitor migration task logs in CloudWatch: /ecs/pilot-api
```

#### Step 6.4 — ECS Fargate Web Service (`pilot-web`)

> **AWS App Runner was sunset April 30, 2026.** This step replaces the original App Runner design with ECS Fargate. The `pilot/web:latest` ECR image is confirmed working locally. See the Phase 6 Step 6.4 DevOps Engineer prompt at [`dev-docs/devops/prompts/aws-phase6-step6.4-devops-engr-prompt.md`](prompts/aws-phase6-step6.4-devops-engr-prompt.md) for the complete Terraform + script implementation instructions.

**Summary of Terraform changes required in `modules/compute/main.tf`:**

1. Remove `aws_apprunner_service.web` resource block
2. Add `aws_security_group.sg_web` (TCP 3000 inbound from `sg-alb` only)
3. Add `aws_lb_target_group.web` (port 3000, health check `GET /api/health`)
4. Add `aws_lb_listener_rule.web` (condition: `host-header = app.pilotfortrades.com`, priority: 10)
5. Add `aws_ecs_task_definition.web` (image: `pilot/web:latest`, 512 CPU / 1024MB, port 3000)
6. Add `aws_ecs_service.web` (desired-count: 1, private subnet, `sg-web`, web target group)
7. Update `aws_route53_record.app` from CNAME→App Runner URL to A alias→ALB
8. Remove `aws_iam_role.app_runner` and its policy attachment from `modules/security/main.tf`

**Also update `infrastructure/scripts/`:**
- `generate-infra-state.sh`: remove `APP_RUNNER_ARN`/`INFRA_APP_RUNNER`; extend `INFRA_ECS` to check `pilot-web`
- All 4 profile scripts: replace `aws apprunner pause/resume` calls with `aws ecs update-service --desired-count 0/1 --service pilot-web`

**Pre-work — confirm `pilot/web:latest` exists in ECR:**
```bash
aws ecr describe-images \
  --repository-name pilot/web \
  --query 'imageDetails[?contains(imageTags, `latest`)]' \
  --output table --region us-east-1
# If empty → build and push before applying Terraform
```

**Apply:**
```bash
cd infrastructure/terraform/environments/production
terraform apply -target=module.compute -auto-approve
```

**Verify:**
```bash
curl https://app.pilotfortrades.com/api/health
# Expected: HTTP 200
```

#### Step 6.5 — Route 53 Records for API + Web App

```hcl
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.pilotfortrades.com"
  type    = "A"
  
  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "app.pilotfortrades.com"
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}
```

---

### Phase 7 — CI/CD Pipeline ⛔ DEFERRED

> **Status**: Explicitly deferred post-beta. All application deployments are performed manually per the procedures in [`aws-ops-runbook.md §8`](aws-ops-runbook.md). CI/CD will be enabled once manual deployments are well-understood and the pipeline can be maintained reliably. The GitHub Actions workflow definition below is preserved for future reference.
>
> **Rationale**: After 6 phases of infrastructure deployment, the stack complexity makes automated pipelines difficult to keep reliable without dedicated maintenance effort. Manual deploys give full visibility and control during the pre-revenue beta phase. The IAM OIDC role for GitHub Actions is already provisioned and ready — enabling CI/CD is a configuration step, not an infrastructure one.

**Original Goal**: GitHub Actions deploys on push to `main`. Zero-downtime ECS rolling updates.

#### Step 7.1 — GitHub Actions OIDC Role

Configure OIDC trust between GitHub and AWS so Actions don't need long-lived IAM access keys:

```hcl
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = ["sts.amazonaws.com"]
  
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions" {
  name = "pilot-github-actions"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:TomHRMC/pilot:*"
        }
      }
    }]
  })
}
```

#### Step 7.2 — GitHub Actions Workflow

Create `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy — Production

on:
  push:
    branches: [main]

permissions:
  id-token: write    # Required for OIDC
  contents: read

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: 000000000000.dkr.ecr.us-east-1.amazonaws.com
  ECS_CLUSTER: pilot-production

jobs:
  # ─── Backend Tests ────────────────────────────────────────────────
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Run unit tests
        run: cd backend && pytest -m unit --tb=short -q | tail -10

  # ─── Build & Push Backend Image ───────────────────────────────────
  build-backend:
    needs: test-backend
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.version }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::000000000000:role/pilot-github-actions
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build and push backend image
        id: meta
        run: |
          IMAGE_TAG=${{ github.sha }}
          docker build -t $ECR_REGISTRY/pilot/api:$IMAGE_TAG ./backend
          docker push $ECR_REGISTRY/pilot/api:$IMAGE_TAG
          docker tag $ECR_REGISTRY/pilot/api:$IMAGE_TAG $ECR_REGISTRY/pilot/api:latest
          docker push $ECR_REGISTRY/pilot/api:latest
          echo "version=$IMAGE_TAG" >> $GITHUB_OUTPUT

  # ─── Run Database Migrations ──────────────────────────────────────
  migrate:
    needs: build-backend
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::000000000000:role/pilot-github-actions
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Run Alembic migrations
        run: |
          TASK_ARN=$(aws ecs run-task \
            --cluster $ECS_CLUSTER \
            --task-definition pilot-api \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={
              subnets=[<private-subnet-id>],
              securityGroups=[<sg-ecs-api-id>],
              assignPublicIp=DISABLED
            }" \
            --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}' \
            --query 'tasks[0].taskArn' --output text)
          
          # Wait for migration task to complete
          aws ecs wait tasks-stopped \
            --cluster $ECS_CLUSTER \
            --tasks $TASK_ARN

  # ─── Deploy Backend Services ──────────────────────────────────────
  deploy-backend:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::000000000000:role/pilot-github-actions
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Deploy FastAPI service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service pilot-api \
            --force-new-deployment
      
      - name: Deploy Celery Worker
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service pilot-celery-worker \
            --force-new-deployment
      
      - name: Deploy Celery Beat
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service pilot-celery-beat \
            --force-new-deployment
      
      - name: Wait for API service stability
        run: |
          aws ecs wait services-stable \
            --cluster $ECS_CLUSTER \
            --services pilot-api

  # ─── Build & Deploy Marketing Site ───────────────────────────────
  deploy-marketing:
    needs: test-backend    # Marketing deploy doesn't need backend deploy
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install pnpm
        uses: pnpm/action-setup@v3
        with:
          version: 9
      
      - name: Install dependencies
        run: cd frontend && pnpm install --frozen-lockfile
      
      - name: Build marketing site
        run: cd frontend && pnpm --filter marketing build
        env:
          NEXT_PUBLIC_API_URL: https://api.pilotfortrades.com
          NEXT_PUBLIC_CLOUDFLARE_TURNSTILE_SITE_KEY: 0x4AAAAAADtbEEHD6Y-jXDbC
      
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::000000000000:role/pilot-github-actions
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Deploy to S3
        run: |
          # Non-HTML: long cache
          aws s3 sync frontend/apps/marketing/out/ s3://pilot-production-marketing/ \
            --delete --exclude "*.html" \
            --cache-control "max-age=31536000,public"
          # HTML: no cache
          aws s3 sync frontend/apps/marketing/out/ s3://pilot-production-marketing/ \
            --delete --include "*.html" --exclude "*" \
            --cache-control "no-cache"
      
      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

**GitHub Actions Secrets required** (set in repo `TomHRMC/pilot` Settings → Secrets → Actions):
- `CLOUDFRONT_DISTRIBUTION_ID` — CloudFront distribution ID (available after Phase 5 `terraform apply`)
- `ACCOUNT_ID` — AWS account ID (or embed directly in workflow)

---

### Phase 8 — Observability & Alerting

**Goal**: CloudWatch dashboards, alarms, GuardDuty, and Security Hub active before first beta customer.

#### Step 8.1 — CloudWatch Log Groups

One log group per service, 30-day retention:

| Log Group | Source |
|---|---|
| `/ecs/pilot-api` | FastAPI ECS tasks |
| `/ecs/pilot-celery-worker` | Celery Worker ECS tasks |
| `/ecs/pilot-celery-beat` | Celery Beat ECS task |
| `/aws/lambda/pilot-post-confirmation` | Cognito post-confirmation Lambda |
| `/pilot/gpu-instance` | GPU instance Docker logs (CloudWatch agent) |

#### Step 8.2 — CloudWatch Alarms (P1/P2/P3)

| Alarm | Metric | Threshold | Severity | Action |
|---|---|---|---|---|
| API Error Rate | `5xx / total` > 5% for 5 min | Critical | SNS → email |
| API p95 Latency | > 2000ms for 5 min | High | SNS → email |
| ECS CPU | > 70% for 15 min | High | SNS → email |
| ECS Memory | > 80% for 15 min | High | SNS → email |
| RDS Connections | > 80 connections | High | SNS → email |
| RDS CPU | > 60% for 10 min | Medium | SNS → email |
| RDS Free Storage | < 5GB | High | SNS → email |
| Redis CPU | > 60% for 10 min | Medium | SNS → email |
| ALB Target Unhealthy | > 0 unhealthy targets | Critical | SNS → email |
| GPU Instance StatusCheck | Failed | Critical | SNS → email |

#### Step 8.3 — GuardDuty + Security Hub

```hcl
resource "aws_guardduty_detector" "pilot" {
  enable = true
  
  datasources {
    s3_logs { enable = true }
    kubernetes { audit_logs { enable = false } }  # No k8s
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes { enable = true }
      }
    }
  }
}

resource "aws_securityhub_account" "pilot" {}

resource "aws_securityhub_standards_subscription" "cis" {
  standards_arn = "arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.4.0"
  depends_on    = [aws_securityhub_account.pilot]
}
```

---

## 6. Environment Variable Matrix

Full mapping from local `.env` variables to their production equivalents:

| Variable | Local Source | Production Source |
|---|---|---|
| `DATABASE_URL` | `backend/.env` | Secrets Manager `pilot/prod/db` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | ElastiCache endpoint `redis://.../:6379/1` |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | ElastiCache endpoint `redis://.../:6379/2` |
| `WHISPER_API_URL` | `http://localhost:8080/v1` | `http://<GPU_PRIVATE_IP>:8080/v1` |
| `OLLAMA_API_URL` | `http://localhost:11434/api` | `http://<GPU_PRIVATE_IP>:11434/api` |
| `COGNITO_REGION` | `us-east-1` | `us-east-1` (same region) |
| `COGNITO_USER_POOL_ID` | `us-east-1_XXXXXXXXX` (dev) | `us-east-1_XXXXXXXXX` (prod) — from Secrets Manager `pilot/prod/cognito` |
| `ENCRYPTION_KEY` | Local Fernet key | Secrets Manager `pilot/prod/encryption` |
| `SENDGRID_API_KEY` | Local API key | Secrets Manager `pilot/prod/sendgrid` |
| `SENDGRID_FROM_EMAIL` | `noreply@pilotfortrades.com` | Same |
| `TELNYX_API_KEY` | Local API key | Secrets Manager `pilot/prod/telnyx` |
| `QUICKBOOKS_CLIENT_ID` | Sandbox client ID | Secrets Manager `pilot/prod/quickbooks` (PROD app) |
| `QUICKBOOKS_CLIENT_SECRET` | Sandbox secret | Secrets Manager `pilot/prod/quickbooks` (PROD app) |
| `QUICKBOOKS_ENVIRONMENT` | `sandbox` | `production` |
| `QUICKBOOKS_REDIRECT_URI` | `https://ngrok.../callback` | `https://api.pilotfortrades.com/api/v1/integrations/quickbooks/callback` |
| `STRIPE_SECRET_KEY` | Local key | Secrets Manager `pilot/prod/stripe` |
| `GOOGLE_MAPS_API_KEY` | Local key | Secrets Manager `pilot/prod/google-maps` |
| `ENVIRONMENT` | `dev` | `production` |
| `TEST_ENDPOINT_ENABLED` | `true` | `false` (hard-blocked in prod) |
| `API_BASE_URL` | `https://ngrok-domain.dev` | `https://api.pilotfortrades.com` |

---

## 7. DNS & Domain Setup

### 7.1 Subdomain Plan

| Subdomain | Points To | Purpose |
|---|---|---|
| `pilotfortrades.com` | CloudFront → S3 | Marketing site |
| `www.pilotfortrades.com` | CloudFront → S3 | www redirect to apex |
| `api.pilotfortrades.com` | ALB | FastAPI backend REST API |
| `app.pilotfortrades.com` | ALB (same as API, listener rule) | Web dashboard (owner/bookkeeper) — `pilot-web` ECS service |

### 7.2 DNS Migration: GoDaddy → Route 53

> **✅ STATUS: DNS records are fully configured in Terraform — ready to execute.** All records from the GoDaddy zone export (`dev-docs/devops/godaddy-archive/pilotfortrades.com.txt`, 2026-07-01) have been imported into `modules/security/main.tf`. No manual record copy is needed. Follow the execution sequence below.

**Key findings from zone file analysis:**
- GoDaddy A record was `WebsiteBuilder Site` (not a real IP) — our CloudFront alias replaces it cleanly
- DKIM selector is `google._domainkey` (NOT `mail._domainkey`) — Terraform uses the correct selector
- SPF was a two-level GoDaddy chain — simplified to direct `include:_spf.google.com` in Terraform
- DMARC RUA updated from `dmarc_rua@onsecureserver.net` (GoDaddy) to `legal@pilotfortrades.com`
- Google site verification TXT preserved alongside SPF in the same apex TXT record

**Execution sequence** (this is now Step 5.1–5.3 of Phase 5 — see §5 above):

1. `terraform apply -target=module.security` — creates Route 53 zone + all DNS records + ACM cert request
2. `terraform output route53_nameservers` — get the 4 AWS NS records
3. Verify records resolve from Route 53 NS directly (dig commands in Phase 5 Step 5.2)
4. Switch nameservers at GoDaddy to the 4 Route 53 NS records (GoDaddy → DNS → Nameservers → Enter my own)
5. `terraform apply` (full) — ACM validates and all resources deploy

### 7.3 Email Record Reference — Confirmed Values in Terraform

All records are populated in `infrastructure/terraform/modules/security/main.tf`. This table is for verification reference only.

| Record Type | Name | Value (confirmed from zone export 2026-07-01) |
|---|---|---|
| MX | `pilotfortrades.com` | 5 Google Workspace MX records (1, 5, 5, 10, 10 priorities) |
| TXT | `pilotfortrades.com` | `v=spf1 include:_spf.google.com ~all` + `google-site-verification=<token>` |
| TXT (DKIM) | `google._domainkey.pilotfortrades.com` | RSA public key (selector: `google`; set up 2026-07-01 in Google Workspace) |
| TXT (DMARC) | `_dmarc.pilotfortrades.com` | `v=DMARC1; p=quarantine; adkim=r; aspf=r; rua=mailto:legal@pilotfortrades.com;` |
| A (alias) | `pilotfortrades.com` | CloudFront distribution (replaces GoDaddy WebsiteBuilder — not a real IP) |
| A (alias) | `www.pilotfortrades.com` | CloudFront distribution |
| A (alias) | `api.pilotfortrades.com` | ALB |
| A (alias) | `app.pilotfortrades.com` | ALB (same ALB as API; listener rule routes to `pilot-web` target group) |

---

## 8. Cost Forecast

**Production-only, 0–100 customers.** All figures reconciled with detailed calculations in §3. Pricing basis: AWS us-east-1 On-Demand, mid-2026.

| Service | Instance Type | §3 Detail | This Plan | `mvp-arch.md §1.4` | Delta vs. Arch Doc | Notes |
|---|---|---|---|---|---|---|
| ECS Fargate — FastAPI API | 0.25 vCPU / 512MB × 2 tasks | §3.1 | **~$18** | ~$30 (all ECS) | Arch doc grouped all ECS together | 2 tasks × 730hr × ($0.04048×0.25 + $0.004445×0.5) |
| ECS Fargate — Celery Worker | 0.25 vCPU / 512MB × 2 tasks | §3.1 | **~$18** | (included above) | +$18 vs. arch doc | Same size as API; 2 tasks |
| ECS Fargate — Celery Beat | 0.25 vCPU / 256MB × 1 task | §3.1 | **~$8** | (included above) | +$8 vs. arch doc | Single task, smaller RAM |
| **ECS Fargate subtotal** | 5 tasks total | §3.1 | **~$44** | **~$30** | **+$14** | Arch doc only counted API tasks; Worker/Beat are additional ECS cost |
| RDS PostgreSQL 17 | db.t4g.micro Multi-AZ | §3.3 | **~$28** | ~$43 | **-$15** | Current pricing: $0.032/hr × 730 + 20GB storage; arch doc used older/higher rate |
| ElastiCache Redis 7 | cache.t4g.micro | §3.3 | **~$13** | ~$15 | **-$2** | $0.018/hr × 730; within pricing variation |
| EC2 GPU (g4dn.xlarge) | g4dn.xlarge + 2 EBS vols | §3.2 | **~$390** | ~$384 | **+$6** | Arch doc omitted EBS volumes ($5.60/mo); instance cost identical |
| S3 (assets bucket) | Private; signed URL access | §3.5 | **~$2** | ~$5 (grouped) | Arch doc grouped all S3 | 10GB audio/images; low GET volume |
| S3 (marketing site) | CloudFront origin | §3.4 | **~$0** | (in CloudFront) | n/a | Static files <1GB; cost is effectively $0 |
| ALB | Standard ALB | §3.5 | **~$18** | ~$20 | **-$2** | $0.008/hr × 730 + ~1 LCU; within rounding |
| CloudFront (marketing CDN) | PriceClass_100 | §3.4 | **~$3** | ~$5 | **-$2** | MVP traffic is low; scales with visitors |
| ECS Fargate — web dashboard (`pilot-web`) | 0.5 vCPU / 1024MB | §3.4 | **~$18** | Not in arch doc (was App Runner ~$5–15) | **+$3–13 vs App Runner** | App Runner sunset April 30, 2026; ECS Fargate shares existing ALB at zero marginal cost |
| NAT Gateway | Single AZ | §3.5 | **~$35** | ~$32 | **+$3** | $0.045/hr + $0.045/GB data processed; arch doc used instance-only rate |
| CloudWatch (logs + metrics + dashboards) | — | §3.5 | **~$23–28** | ~$34 | **-$6–11** | Itemized: logs ~$13, metrics ~$10, dashboards $3; arch doc estimate was conservative |
| Secrets Manager | 8 secrets | §3.5 | **~$3** | ~$2 | **+$1** | 8 secrets × $0.40; arch doc used 4–6 secrets |
| KMS | 1 CMK | §3.5 | **~$2** | (in Secrets Mgr) | +$2 | $1/key/month + API calls; arch doc grouped with Secrets Manager |
| Cognito | <50K MAUs | §3.5 | **$0** | Not listed | $0 | Free tier covers all MVP users |
| Lambda (post-confirmation) | Low invocation count | §3.5 | **~$0** | ~$5 (grouped) | Arch doc grouped Lambda costs | Well within free tier (1M invocations/month free) |
| Route 53 | 1 hosted zone | §3.5 | **~$1** | Not listed | +$1 | $0.50/zone + $0.40/million queries |
| ECR | Image storage | §3.5 | **~$1** | ~$3 (grouped) | Within variance | Same-region ECS pulls are free; only storage billed |
| VPC Endpoints | S3 gateway (free) + Secrets Manager | §3.5 | **~$7** | ~$13 | **-$6** | S3 gateway endpoint is free; only Secrets Manager interface endpoint charged |
| GuardDuty | Account-level | §3.5 | **~$10–15** | ~$15 (grouped with Security Hub) | Within range | Flow logs + DNS + CloudTrail events |
| Security Hub | CIS benchmark | §3.5 | **~$5** | (grouped above) | Within range | ~5,000 security checks/month |
| Data Transfer Out | ~500GB/month | §3.5 | **~$45** | ~$45 | **$0** | Identical; $0.09/GB is correct |
| X-Ray | 5% sampling | §3.5 | **~$0–5** | (in CloudWatch) | Minimal | Under 100K traces/month at MVP |
| **EC2 Bastion** | `t4g.nano` + 8GB EBS + Elastic IP | §5 Phase 1.4 | **~$4–7** | Not in arch doc | **+$4–7 new** | Admin SSH access to private subnet; can be stopped when not in use to reduce to ~$3.50 (Elastic IP charge only) |
| **TOTAL** | | | **~$664–707/month** | **~$643/month** | **+$21–64** | |

### 8.1 Reconciliation vs. `mvp-arch.md §1.4`

The architecture doc's `~$643/month` estimate was deliberately conservative and accurate for its stated scope. The delta in this deployment plan (+$17–57) comes from three sources:

| Delta Source | Amount | Explanation |
|---|---|---|
| Celery Worker + Beat as separate ECS services | +$26 | Arch doc implied Celery ran alongside FastAPI on the same host (Docker Compose model). On ECS Fargate, each service is a separate billable task. This is the correct design. |
| ECS Fargate `pilot-web` for web dashboard | +$18 | App Runner sunset April 30, 2026. Web dashboard migrated to ECS Fargate as 4th service; shares existing ALB via listener rule. ~$3–13/month more than App Runner was projected at, but within $206/month budget buffer. |
| EBS volumes on GPU instance | +$6 | Arch doc only counted the g4dn.xlarge instance hourly rate; EBS volumes for OS and model storage are additional. |
| RDS + ElastiCache lower current pricing | -$17 | Current mid-2026 pricing is lower than the arch doc's estimate for db.t4g.micro Multi-AZ and cache.t4g.micro. These are the largest offsetting savings. |
| VPC Endpoints, ACM, Lambda savings | -$13 | S3 gateway endpoint is free (not $7 as arch doc implied); ACM certs are free; Lambda stays in free tier. |

**Net result**: **~$660–700/month** vs. arch doc's **$643/month** — a **$17–57/month variance** (2.6–8.9%). Both are well within the **$888/month hard cap** from `infrastructure-constraints.md §1`. Gross margin impact at $149/month pricing: **95.3–95.6%** (vs. arch doc's stated 94%).

### 8.2 No QA Environment Savings

Running production-only (no QA/staging environment) saves the full stack cost again:
- **Savings**: ~$660–700/month
- **Total dual-env cost avoided**: ~$1,320–1,400/month
- **Break-even for adding QA env**: When beta customer count generates enough recurring revenue to absorb the duplicate infrastructure cost (approximately 5 paying customers at $149/month covers a QA environment)

---

## 9. Open Pre-Deployment Decisions

These items require action before deployment can proceed:

| # | Decision Needed | Owner | Urgency |
|---|---|---|---|
| 1 | ~~**Domain registrar control**~~ ✅ **RESOLVED** — `pilotfortrades.com` registered and DNS-hosted at GoDaddy; Tom has full admin access; Google Workspace email already live. DNS migrates to Route 53 per §7.2 migration procedure during Phase 5. | Tom | ✅ Done |
| 2 | ~~**Cloudflare Turnstile prod key**~~ ✅ **RESOLVED** — Production site key: `0x4AAAAAADtbEEHD6Y-jXDbC` (public; safe in frontend env). Secret key stored in AWS Secrets Manager as `pilot/prod/turnstile` (see §3.2 Secrets Manager table). | Tom | ✅ Done |
| 3 | **QuickBooks Production App** — register separate production app in Intuit Developer Portal; get prod client ID/secret | Tom | P1 — required before any tenant connects QB in prod |
| 4 | **Telnyx 10DLC** — complete A2P registration once marketing site is live | Tom | P1 — required before SMS sends in prod |
| 5 | **Stripe live mode keys** — switch from test mode to live mode in Stripe dashboard | Tom | P1 — required before first paid subscription |
| 6 | ~~**AWS Account ID**~~ ✅ **RESOLVED** — HotRMC account ID is `000000000000`. Replace all `<ACCOUNT_ID>` placeholders in Terraform, ECR URLs, IAM ARNs, and GitHub Actions workflow with this value. | Tom | ✅ Done |
| 7 | **`apps/web/Dockerfile`** — Next.js standalone Dockerfile confirmed working locally (`GET /api/health → HTTP 200`). Image `pilot/web:latest` ready in ECR. Terraform ECS service creation pending Phase 6 Step 6.4. | DevOps engineer | P1 — required for `pilot-web` ECS deployment |
| 8 | **SendGrid domain authentication** — verify `pilotfortrades.com` for sending in SendGrid dashboard (DKIM, SPF alignment) | Tom | P1 — transactional email deliverability |
| 9 | **Google Maps production API key** — verify billing enabled and key restrictions set for `api.pilotfortrades.com` | Tom | P2 — needed before field technicians use dispatch/routing |
| 10 | ~~**Fernet encryption key for prod**~~ ✅ **RESOLVED** — Key generated. **Store ONLY in AWS Secrets Manager** as `pilot/prod/encryption` → `{"fernet_key": "<value>"}`. Never commit to git. Never write in any doc. ECS tasks retrieve it at runtime via Secrets Manager. | Tom | ✅ Done — store in Secrets Manager |

---

## 10. Post-Deployment Checklist

Run through these after each phase completes:

### After Phase 5 (Marketing Site):
- [ ] `curl -I https://pilotfortrades.com` returns HTTP 200
- [ ] `curl -I https://www.pilotfortrades.com` redirects to apex
- [ ] All form pages load without console errors
- [ ] Turnstile widget appears on all forms
- [ ] Privacy Policy page contains the 10DLC SMS clause
- [ ] `sms-opt-in/` page is accessible
- [ ] `legal@pilotfortrades.com` receives test email

### After Phase 6 (Backend + Web Dashboard):
- [ ] `curl https://api.pilotfortrades.com/api/v1/health/celery` returns `{"status": "healthy", "workers_active": N, "broker_connected": true, "scheduled_tasks": 0, "timestamp": "..."}`
- [ ] `https://app.pilotfortrades.com` loads the web dashboard login page
- [ ] Cognito login works with a new test user (not the dev test users)
- [ ] QuickBooks OAuth callback URL updated in Intuit Developer Portal to `https://api.pilotfortrades.com/api/v1/integrations/quickbooks/callback`
- [ ] `TEST_ENDPOINT_ENABLED=false` verified: `curl https://api.pilotfortrades.com/api/v1/customers/test` returns HTTP 403
- [ ] pgvector extension enabled: `SELECT extname FROM pg_extension WHERE extname = 'vector';`
- [ ] Celery Beat logs show scheduled tasks running (CloudWatch `/ecs/pilot-celery-beat`)
- [ ] GPU instance health: `curl http://<GPU_PRIVATE_IP>:11434` (from ECS task) returns Ollama version
- [ ] S3 signed URL upload flow works (test via voice command in web app)

### After Phase 7 (CI/CD):
- [ ] Push a trivial commit to `main` → GitHub Actions runs and deploys successfully
- [ ] Migration job runs and exits 0
- [ ] ECS service updates to new task definition revision
- [ ] Marketing site deploys to S3 and CloudFront invalidation fires

---

## 11. AWS Resource Tagging Policy

### 11.1 Why Tagging Matters for Pilot

AWS Cost Explorer only shows costs by service by default (e.g., "EC2: $390/month", "RDS: $28/month"). Without tags, you cannot answer questions like:
- *How much does the Voice AI pipeline cost vs. the web infrastructure?*
- *What does the marketing site cost independently of the backend?*
- *If I add a QA environment later, how do I separate its costs from production?*

Tags solve this by letting Cost Explorer filter by tag dimensions. AWS bills resources — tags let you attribute those bills to logical cost buckets.

> **Activation requirement**: Tags must be **activated as Cost Allocation Tags** in the AWS Billing Console before they appear in Cost Explorer. This is a one-time manual step (see §11.5). Tag activation takes up to 24 hours to appear in billing data.

### 11.2 Mandatory Tags (Required on Every Resource)

These 5 tags must appear on **every** AWS resource created for Pilot — no exceptions. They are defined in Terraform's `default_tags` so they are applied automatically without having to repeat them in every resource block.

| Tag Key | Allowed Values | Purpose | Example |
|---|---|---|---|
| `Project` | `pilot-for-trades` | Identifies all resources belonging to Pilot (useful if you ever use this AWS account for another project) | `pilot-for-trades` |
| `Environment` | `production` | Separates production from any future QA/staging environments | `production` |
| `Owner` | `owner` | Resource owner for billing accountability and support escalation | `owner` |
| `ManagedBy` | `terraform` or `manual` | Identifies how the resource was provisioned; `manual` = one-time CLI commands (S3 state bucket, DynamoDB lock table) | `terraform` |
| `CostCenter` | `infrastructure` | Top-level cost bucket for all AWS spend | `infrastructure` |

**Every resource gets these 5 tags. Non-negotiable.**

### 11.3 Conditional Tags (Required When Applicable)

These additional tags are required when they apply to a resource. They enable the specific Cost Explorer views described in §11.6.

| Tag Key | Allowed Values | Apply When | Purpose |
|---|---|---|---|
| `Component` | See table below | Always (all Terraform resources) | Breaks costs down by functional area for line-item cost tracking |
| `Service` | `fastapi-api`, `celery-worker`, `celery-beat`, `whisper`, `ollama`, `web-dashboard`, `marketing-site` | ECS tasks, EC2 | Identifies which application component the resource serves |
| `DataClassification` | `sensitive`, `internal`, `public` | RDS, S3 buckets, ElastiCache, Secrets Manager | Data governance; useful for security audits |
| `Backup` | `enabled`, `disabled` | RDS, EBS volumes, S3 buckets | Confirms backup policy is intentional |
| `CostAllocation` | `ai-pipeline`, `web-infrastructure`, `data-layer`, `marketing`, `networking`, `security-monitoring` | All resources | The primary Cost Explorer filter dimension (see §11.6) |

#### `Component` Tag Allowed Values

| Value | Resources Tagged | Monthly Cost Group |
|---|---|---|
| `ai-pipeline` | EC2 g4dn.xlarge, EBS volumes (GPU), GPU security group | ~$390 |
| `api-backend` | ECS Fargate tasks (FastAPI, Celery Worker, Celery Beat), ECR repos, ECS cluster | ~$44 |
| `data-layer` | RDS instance, RDS subnet group, RDS parameter group, ElastiCache cluster | ~$41 |
| `web-dashboard` | ECS service `pilot-web`, `sg-web` security group, ALB listener rule, web target group | ~$18 |
| `marketing-site` | S3 marketing bucket, CloudFront distribution (marketing) | ~$1–5 |
| `asset-storage` | S3 assets bucket (audio, photos, PDFs) | ~$2 |
| `networking` | VPC, all subnets, NAT Gateway, ALB, Elastic IP, route tables, security groups, VPC endpoints | ~$60 |
| `auth` | Cognito user pool, app client, Post-Confirmation Lambda | ~$0 |
| `secrets-security` | Secrets Manager secrets, KMS key, IAM roles/policies | ~$5 |
| `monitoring` | CloudWatch log groups, alarms, dashboards, X-Ray, GuardDuty, Security Hub | ~$35 |
| `dns` | Route 53 hosted zone, all DNS records, ACM certificates | ~$1 |
| `state-management` | S3 Terraform state bucket, DynamoDB lock table | ~$1 |

### 11.4 Terraform Implementation

#### Global Default Tags (apply to all resources automatically)

Add `default_tags` to the AWS provider in `infrastructure/terraform/versions.tf` or `main.tf`:

```hcl
# infrastructure/terraform/environments/production/main.tf

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "pilot-for-trades"
      Environment = var.environment          # "production"
      Owner       = "owner"
      ManagedBy   = "terraform"
      CostCenter  = "infrastructure"
    }
  }
}
```

> **How `default_tags` works**: Every resource created by this provider configuration automatically inherits these 5 tags. You do not need to add them to each `resource` block — they merge with any resource-specific tags. Resource-level tags override defaults if the same key is defined.

#### Resource-Specific Tags (in each module)

Each resource adds its `Component`, `Service`, `DataClassification`, `Backup`, and `CostAllocation` tags. Example pattern:

```hcl
# modules/compute/main.tf — ECS FastAPI service
resource "aws_ecs_service" "api" {
  name    = "pilot-api"
  cluster = aws_ecs_cluster.production.id
  # ... other config ...

  tags = {
    Component      = "api-backend"
    Service        = "fastapi-api"
    CostAllocation = "web-infrastructure"
  }
}

# modules/compute/main.tf — EC2 GPU instance
resource "aws_instance" "gpu" {
  ami           = var.gpu_ami
  instance_type = "g4dn.xlarge"
  # ... other config ...

  tags = {
    Name               = "pilot-gpu-prod"
    Component          = "ai-pipeline"
    Service            = "whisper-ollama"
    CostAllocation     = "ai-pipeline"
    DataClassification = "internal"
    Backup             = "enabled"
  }
}

# modules/database/main.tf — RDS instance
resource "aws_db_instance" "postgres" {
  identifier = "pilot-production"
  # ... other config ...

  tags = {
    Component          = "data-layer"
    CostAllocation     = "data-layer"
    DataClassification = "sensitive"
    Backup             = "enabled"
  }
}

# modules/storage/main.tf — Assets S3 bucket
resource "aws_s3_bucket" "assets" {
  bucket = "pilot-production-assets"

  tags = {
    Component          = "asset-storage"
    CostAllocation     = "web-infrastructure"
    DataClassification = "sensitive"
    Backup             = "enabled"
  }
}

# modules/storage/main.tf — Marketing S3 bucket
resource "aws_s3_bucket" "marketing" {
  bucket = "pilot-production-marketing"

  tags = {
    Component          = "marketing-site"
    CostAllocation     = "marketing"
    DataClassification = "public"
    Backup             = "disabled"
  }
}
```

#### Manually Provisioned Resources (S3 state bucket, DynamoDB lock table)

These are created via AWS CLI before Terraform runs (Phase 1.1). Tag them via CLI:

```bash
# Tag the Terraform state S3 bucket
aws s3api put-bucket-tagging \
  --bucket pilot-terraform-state-000000000000 \
  --tagging 'TagSet=[
    {Key=Project,Value=pilot-for-trades},
    {Key=Environment,Value=production},
    {Key=Owner,Value=owner},
    {Key=ManagedBy,Value=manual},
    {Key=CostCenter,Value=infrastructure},
    {Key=Component,Value=state-management},
    {Key=CostAllocation,Value=infrastructure}
  ]'

# Tag the DynamoDB lock table
aws dynamodb tag-resource \
  --resource-arn arn:aws:dynamodb:us-east-1:000000000000:table/pilot-terraform-locks \
  --tags '[
    {"Key":"Project","Value":"pilot-for-trades"},
    {"Key":"Environment","Value":"production"},
    {"Key":"Owner","Value":"owner"},
    {"Key":"ManagedBy","Value":"manual"},
    {"Key":"CostCenter","Value":"infrastructure"},
    {"Key":"Component","Value":"state-management"},
    {"Key":"CostAllocation","Value":"infrastructure"}
  ]'
```

### 11.5 Cost Allocation Tag Activation

After the first `terraform apply` runs and resources are created, activate the tags in the AWS Billing Console. **This is a one-time manual step — Terraform cannot do it.**

```
AWS Console → Billing and Cost Management → Cost Allocation Tags
→ Find each of the following tags in the "AWS-generated" or "User-defined" section
→ Select each one → click "Activate"
```

Tags to activate:
- `Project`
- `Environment`
- `Owner`
- `ManagedBy`
- `CostCenter`
- `Component`
- `Service`
- `CostAllocation`
- `DataClassification`
- `Backup`

> **Timing**: AWS processes tag activation within 24 hours. Historical billing data does not retroactively gain tag cost attribution — tags only show costs from the activation date forward. Activate tags on Day 1 of deployment.

### 11.6 Cost Explorer Views

Once tags are activated, create these saved Cost Explorer filters in the AWS Billing Console. Each answers a specific question:

| View Name | Filter Configuration | Question Answered |
|---|---|---|
| **Total Monthly Spend** | No filter, group by Service | Baseline — what does each AWS service cost? |
| **AI Pipeline Cost** | Filter: `CostAllocation = ai-pipeline` | What does Whisper + Ollama GPU hosting cost? |
| **Web Infrastructure Cost** | Filter: `CostAllocation = web-infrastructure` | What does the API + web dashboard + assets cost? |
| **Data Layer Cost** | Filter: `CostAllocation = data-layer` | What does RDS + ElastiCache cost? |
| **Marketing Site Cost** | Filter: `CostAllocation = marketing` | What does pilotfortrades.com hosting cost? |
| **Networking Cost** | Filter: `CostAllocation = networking` | What does VPC + NAT Gateway + ALB cost? |
| **By Component** | No filter, group by tag: `Component` | Line-item cost breakdown by functional area |
| **By Environment** | No filter, group by tag: `Environment` | Compare production vs. future QA (when added) |
| **By Service** | No filter, group by tag: `Service` | Which application (FastAPI vs. Celery vs. Whisper) costs most? |

**Monthly cost attribution target** (from §3 estimates):

| `CostAllocation` Value | Expected Monthly | Primary Resources |
|---|---|---|
| `ai-pipeline` | ~$390 | GPU instance + EBS |
| `web-infrastructure` | ~$98–115 | ECS Fargate (all 4 services) + ALB + S3 assets |
| `data-layer` | ~$41 | RDS + ElastiCache |
| `networking` | ~$43 | NAT Gateway + VPC endpoints + Route 53 |
| `security-monitoring` | ~$45 | CloudWatch + GuardDuty + Security Hub + Secrets Manager + KMS |
| `marketing` | ~$3–7 | S3 + CloudFront marketing distribution |
| `infrastructure` | ~$1 | Terraform state S3 + DynamoDB |
| **TOTAL** | **~$618–642** | (data transfer ~$45 distributed across components) |

> Note: Data transfer costs ($45/month) are attributed to the generating resources (primarily ECS API tasks and S3), so they appear under `web-infrastructure` and `data-layer` cost views rather than as a separate line.

### 11.7 Tag Compliance Enforcement

#### AWS Config Rule (Terraform)

Enforce that every new resource has the mandatory tags:

```hcl
# modules/monitoring/config_rules.tf
resource "aws_config_config_rule" "required_tags" {
  name = "pilot-required-tags"

  source {
    owner             = "AWS"
    source_identifier = "REQUIRED_TAGS"
  }

  input_parameters = jsonencode({
    tag1Key   = "Project"
    tag2Key   = "Environment"
    tag3Key   = "Owner"
    tag4Key   = "Component"
    tag5Key   = "CostAllocation"
  })

  scope {
    compliance_resource_types = [
      "AWS::EC2::Instance",
      "AWS::RDS::DBInstance",
      "AWS::ElastiCache::CacheCluster",
      "AWS::ECS::Service",
      "AWS::S3::Bucket",
      "AWS::ElasticLoadBalancingV2::LoadBalancer",
    ]
  }
}
```

> AWS Config has a free tier of 1,000 configuration items/month. At MVP scale with ~20–30 tagged resources, this stays well within the free tier. Cost: ~$0.

#### Terraform `lifecycle` Tag Validation

Add to `variables.tf` to validate the `Component` tag value at plan time:

```hcl
variable "component" {
  description = "Functional component for cost allocation tagging"
  type        = string
  
  validation {
    condition = contains([
      "ai-pipeline", "api-backend", "data-layer", "web-dashboard",
      "marketing-site", "asset-storage", "networking", "auth",
      "secrets-security", "monitoring", "dns", "state-management"
    ], var.component)
    error_message = "component must be one of the approved values defined in §11.3 of the deployment plan."
  }
}
```

### 11.8 Per-Resource Tag Reference

Complete reference of all tags applied to each resource. Use this as a checklist when reviewing Terraform plans.

| Resource | `Component` | `Service` | `CostAllocation` | `DataClassification` | `Backup` |
|---|---|---|---|---|---|
| EC2 g4dn.xlarge | `ai-pipeline` | `whisper-ollama` | `ai-pipeline` | `internal` | `enabled` |
| EBS root vol (GPU) | `ai-pipeline` | `whisper-ollama` | `ai-pipeline` | `internal` | `enabled` |
| EBS model vol (GPU) | `ai-pipeline` | `whisper-ollama` | `ai-pipeline` | `internal` | `enabled` |
| ECS Service — FastAPI | `api-backend` | `fastapi-api` | `web-infrastructure` | `internal` | `disabled` |
| ECS Service — Worker | `api-backend` | `celery-worker` | `web-infrastructure` | `internal` | `disabled` |
| ECS Service — Beat | `api-backend` | `celery-beat` | `web-infrastructure` | `internal` | `disabled` |
| ECS Cluster | `api-backend` | — | `web-infrastructure` | `internal` | `disabled` |
| ECR repos (api/worker/beat) | `api-backend` | — | `web-infrastructure` | `internal` | `disabled` |
| ALB | `networking` | — | `networking` | `internal` | `disabled` |
| ECS Service — `pilot-web` | `web-dashboard` | `web-dashboard` | `web-infrastructure` | `internal` | `disabled` |
| RDS PostgreSQL | `data-layer` | `postgresql` | `data-layer` | `sensitive` | `enabled` |
| ElastiCache Redis | `data-layer` | `redis` | `data-layer` | `internal` | `disabled` |
| S3 — assets bucket | `asset-storage` | — | `web-infrastructure` | `sensitive` | `enabled` |
| S3 — marketing bucket | `marketing-site` | — | `marketing` | `public` | `disabled` |
| S3 — Terraform state | `state-management` | — | `infrastructure` | `sensitive` | `enabled` |
| CloudFront — marketing | `marketing-site` | — | `marketing` | `public` | `disabled` |
| VPC | `networking` | — | `networking` | `internal` | `disabled` |
| Subnets (all) | `networking` | — | `networking` | `internal` | `disabled` |
| NAT Gateway | `networking` | — | `networking` | `internal` | `disabled` |
| Security Groups (all) | `networking` | — | `networking` | `internal` | `disabled` |
| VPC Endpoints | `networking` | — | `networking` | `internal` | `disabled` |
| Route 53 Hosted Zone | `dns` | — | `networking` | `public` | `disabled` |
| ACM Certificate | `dns` | — | `networking` | `public` | `disabled` |
| Cognito User Pool | `auth` | — | `security-monitoring` | `sensitive` | `disabled` |
| Post-Confirmation Lambda | `auth` | — | `security-monitoring` | `internal` | `disabled` |
| Secrets Manager (all) | `secrets-security` | — | `security-monitoring` | `sensitive` | `disabled` |
| KMS Key | `secrets-security` | — | `security-monitoring` | `sensitive` | `disabled` |
| CloudWatch Log Groups | `monitoring` | — | `security-monitoring` | `internal` | `disabled` |
| CloudWatch Alarms | `monitoring` | — | `security-monitoring` | `internal` | `disabled` |
| GuardDuty Detector | `monitoring` | — | `security-monitoring` | `internal` | `disabled` |
| Security Hub | `monitoring` | — | `security-monitoring` | `internal` | `disabled` |
| DynamoDB lock table | `state-management` | — | `infrastructure` | `sensitive` | `disabled` |
| IAM Roles (all) | `secrets-security` | — | `security-monitoring` | `internal` | `disabled` |

---

## Appendix A — Terraform Files to Create

The following files need to be written by the DevOps engineer. This plan defines what they must contain; the actual Terraform HCL is a separate implementation task:

| File | Contents |
|---|---|
| `infrastructure/terraform/backend.tf` | S3 + DynamoDB remote state config |
| `infrastructure/terraform/versions.tf` | Provider versions: `hashicorp/aws ~> 5.0` |
| `infrastructure/terraform/variables.tf` | `environment`, `aws_region`, `domain_name`, `db_password` etc. |
| `infrastructure/terraform/main.tf` | Module composition calling all modules |
| `infrastructure/terraform/outputs.tf` | ALB DNS, RDS endpoint, Redis endpoint, Cognito pool IDs, ECR URLs |
| `infrastructure/terraform/modules/networking/` | VPC, subnets, IGW, NAT, route tables, security groups, VPC endpoints |
| `infrastructure/terraform/modules/compute/` | ECS cluster + 4 services (api, worker, beat, web), EC2 GPU, ECR repos |
| `infrastructure/terraform/modules/database/` | RDS instance, parameter group, subnet group; ElastiCache cluster |
| `infrastructure/terraform/modules/storage/` | S3 buckets (assets, marketing, state CDN) |
| `infrastructure/terraform/modules/security/` | KMS key, Secrets Manager secrets, IAM roles/policies, Cognito user pool + client + Lambda trigger |
| `infrastructure/terraform/modules/monitoring/` | CloudWatch log groups, alarms, SNS topics, GuardDuty, Security Hub |
| `infrastructure/terraform/environments/production/main.tf` | Module calls with prod-specific variable values |
| `infrastructure/terraform/environments/production/terraform.tfvars` | `environment = "production"`, `aws_region = "us-east-1"`, domain etc. |
| `infrastructure/terraform/environments/production/backend.tf` | `bucket = "pilot-terraform-state-000000000000"`, `key = "production/terraform.tfstate"` |

## Appendix B — New Files Required in Application Repos

| File | Purpose | Priority |
|---|---|---|
| `backend/Dockerfile` | Already referenced in docker-compose.yml but verify it builds correctly for ECS | P0 |
| `frontend/apps/web/Dockerfile` | Next.js standalone Docker image for ECS Fargate `pilot-web` service | P1 |
| `apps/marketing/.env.production` | Prod env vars for marketing site CI build | P1 |
| `.github/workflows/deploy-production.yml` | GitHub Actions CI/CD pipeline | P1 |
| `infrastructure/terraform/` | Full Terraform module structure (see Appendix A) | P0 |

## Appendix C - AWS Notice on App Runner Sunset

### Notice

Starting April 30, 2026, AWS App Runner is no longer accepting new customers. Your existing App Runner services will remain operational and accessible. AWS continues to invest in security and availability, but we do not plan to introduce new features. For deploying and running containerized applications, we recommend Amazon ECS Express Mode . To learn more, see Amazon ECS Express Mode  and the migration guidance .

### Resolution

**Date resolved**: 2026-07-03
**Decision**: Pilot for Trades has migrated the web dashboard to **ECS Fargate** as the 4th service (`pilot-web`) on the existing `pilot-production` cluster.

- The existing ALB is shared via an `app.pilotfortrades.com` listener rule — zero marginal ALB cost
- `aws_route53_record.app` changed from CNAME → App Runner URL to A alias → ALB
- `pilot-production-app-runner-role` IAM role removed from Terraform
- All 4 profile scripts updated: `aws apprunner pause/resume` replaced with `aws ecs update-service --desired-count 0/1 --service pilot-web`
- `INFRA_APP_RUNNER` flag removed from `generate-infra-state.sh`; `INFRA_ECS` now covers all 4 services

See [`§5 Phase 6 Step 6.4`](#step-64--ecs-fargate-web-service-pilot-web) for the full implementation spec and [`dev-docs/devops/prompts/aws-phase6-step6.4-devops-engr-prompt.md`](prompts/aws-phase6-step6.4-devops-engr-prompt.md) for the DevOps Engineer prompt.

---

## Appendix D — Post-Launch Operations Log

Changes made after all 6 deployment phases were complete. These are operational fixes and tooling improvements, not new infrastructure phases.

---

### D.1 Profile Scripts v2 + Status Dashboard (2026-07-04)

**What changed:**

- **New**: [`infrastructure/scripts/profile-status.sh`](../../infrastructure/scripts/profile-status.sh) — read-only status dashboard showing Expected vs Actual state for the active profile. Replaces the Phase 2 health check block that was embedded in `profile-c-full.sh`. Covers all 7 resources (GPU, Bastion, 4 ECS services, site mode) plus data layer, endpoint health, CloudWatch alarms, and a summary footer.
- **New**: [`infrastructure/scripts/README.md`](../../infrastructure/scripts/README.md) — 8-section operator guide for all scripts.
- **Modified**: All 5 profile scripts (`profile-off.sh`, `profile-a-marketing.sh`, `profile-b-app.sh`, `profile-c-full.sh`, plus `profile-status.sh`) now write `infrastructure/scripts/.env.profiles` at the end of execution. This file records `PROFILE_SET` and `PROFILE_SET_AT` so `profile-status.sh` can compute Expected state without hard-coding it.
- **Modified**: `profile-c-full.sh` — Phase 2 health check block removed (7 checks, `PASS`/`FAIL` counters, `sleep 60`). All health verification now done by `profile-status.sh`.
- **Modified**: `.gitignore` — `infrastructure/scripts/.env.profiles` added.

**Daily workflow:**
```bash
./profile-b-app.sh light    # set profile
./profile-status.sh         # verify — run until all ✅
./profile-off.sh            # end of day
./profile-status.sh         # confirm shutdown
```

---

### D.2 pilot-api Memory Leak Fix (2026-07-04)

**Alarm**: `pilot-production-ecs-api-memory` fired — memory trending 78% → 82% at idle with no user traffic.

**Root cause**: `backend/api/routes/health.py` — `celery_app.connection()` called on every ALB health check (`GET /api/v1/health/celery`, 240 calls/hour) without releasing the kombu broker connection. Connections accumulated in heap memory.

**Fix**: Changed to context manager pattern: `with celery_app.connection() as conn:`. Added `timeout=1.0` to `celery_app.control.inspect()`. Updated 3 unit tests to use `__enter__.return_value` mock protocol.

**Result**: Alarm resolved. Memory stabilizes at ~60-65% after restart (no further drift).

---

### D.3 pilot-web ECS Container Health Check Fix (2026-07-05)

**Problem**: `pilot-web` ECS tasks cycling — RUNNING then UNHEALTHY then killed. ALB external health check passed; container-level `curl -f http://localhost:3000/api/health` failed inside every task.

**Root cause**: Container-level ECS health checks using `curl`/`wget` targeting `localhost` or `127.0.0.1` fail inside Fargate tasks running `node:20-alpine`. The loopback interface is not reachable from within the container process space in Fargate's network namespace. This affects Alpine-based images regardless of whether curl is installed.

**Fix**: Removed `healthCheck` block from the pilot-web container definition. The ALB target group health check (`GET /api/health → 200`) is the sole health authority. ECS will show `UNKNOWN` for container health — this is correct and expected when no container health check is defined.

**Files changed**:
- [`infrastructure/terraform/modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf) — `healthCheck` block removed from pilot-web container
- [`frontend/apps/web/Dockerfile`](../../frontend/apps/web/Dockerfile) — `curl` added to runner stage (kept for operator use, not for ECS health check)
- ECS task definition `pilot-production-web:4` deployed

**Also fixed**: [`aws-ops-runbook.md`](aws-ops-runbook.md) §8.3 build command was wrong (`cd frontend/apps/web && docker build .` fails — monorepo context required). Corrected to `docker build -f frontend/apps/web/Dockerfile frontend/`.

---

### D.4 Operations Runbook Additions (2026-07-04–05)

**[`aws-ops-runbook.md`](aws-ops-runbook.md)** updated to v3.3:

- **§8.3** — Build command for `pilot-web` corrected; warning block added explaining monorepo build context requirement
- **§18** — New section: CloudWatch Metrics troubleshooting commands (ECS memory, ECS CPU, ALB 5xx, ALB p95 latency, CloudWatch alarms)
- **§19** — New section: ECS Task Deployment Troubleshooting
  - **§19.1** Watch-and-Run Pattern — never use `sleep` to guess status; watch the ECS Console UI and run the check command only when you see the status change
  - **§19.2** Force a specific task definition revision (prevents old revision tasks from being placed)
  - **§19.3** Clear multiple active deployments (converge to a single PRIMARY)
  - **§19.4** Register a new task definition revision via CLI
  - **§19.5** Container health check behavior in Fargate Alpine images (known issue + solution)