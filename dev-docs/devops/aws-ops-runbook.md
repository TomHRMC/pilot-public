# AWS Operations Runbook — Pilot for Trades

> **Snapshot note:** historical working document, published as last edited during the build and not maintained. Statuses and figures below reflect that date; for current, checked figures see [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../diligence/README.md). The product was never released and never carried customer traffic.

**Version**: 3.8
**Updated**: 2026-08-27
**Author**: Tom (Founder)  
**Account**: HotRMC (`000000000000`) · Region: `us-east-1`  
**Purpose**: Step-by-step operational procedures for every common task — start here, copy the commands, run them.

> **How to use this runbook**: Jump to the section you need. Every section is self-contained with all commands and dynamic variable lookups. **Variables are never hardcoded** — each section shows how to pull the live value from AWS before using it, so the commands stay correct even if resource IDs change.

---

## Table of Contents

- [AWS Operations Runbook — Pilot for Trades](#aws-operations-runbook--pilot-for-trades)
  - [Table of Contents](#table-of-contents)
  - [1. Cost Floor — What Always Runs](#1-cost-floor--what-always-runs)
  - [2. The Four Operating Profiles](#2-the-four-operating-profiles)
    - [Profile OFF: Cost Floor](#profile-off-cost-floor)
    - [Profile A: Marketing Only](#profile-a-marketing-only)
    - [Profile B: Web App + Mobile App](#profile-b-web-app--mobile-app)
    - [Profile C: Beta Customer Pre-Launch](#profile-c-beta-customer-pre-launch)
    - [Profile Comparison Table](#profile-comparison-table)
  - [3. Profile Commands — Quick Reference](#3-profile-commands--quick-reference)
  - [4. Coming Soon Mode — Marketing Site Toggle](#4-coming-soon-mode--marketing-site-toggle)
    - [Manual Toggle (if needed without running a full profile script)](#manual-toggle-if-needed-without-running-a-full-profile-script)
  - [5. Individual Resource Start/Stop Reference](#5-individual-resource-startstop-reference)
    - [ECS Services (FastAPI, Celery Worker, Celery Beat, Web Dashboard)](#ecs-services-fastapi-celery-worker-celery-beat-web-dashboard)
    - [GPU Instance (Whisper + Ollama)](#gpu-instance-whisper--ollama)
    - [RDS PostgreSQL](#rds-postgresql)
  - [6. Bastion Host — Starting, Stopping, and Connecting](#6-bastion-host--starting-stopping-and-connecting)
    - [Start the Bastion](#start-the-bastion)
    - [Stop the Bastion](#stop-the-bastion)
    - [Check Bastion Status](#check-bastion-status)
    - [SSH Config (`~/.ssh/config`)](#ssh-config-sshconfig)
    - [Persistent Tunnels with `autossh` (Recommended for Long Admin Sessions)](#persistent-tunnels-with-autossh-recommended-for-long-admin-sessions)
    - [Connect to Bastion](#connect-to-bastion)
    - [Update Your IP When It Changes (home ISP / Travel / Hotel WiFi)](#update-your-ip-when-it-changes-home-isp--travel--hotel-wifi)
  - [7. GPU Instance Management](#7-gpu-instance-management)
    - [Getting GPU Private IP (for SSH config or secret updates)](#getting-gpu-private-ip-for-ssh-config-or-secret-updates)
    - [Verifying AI Services Are Ready](#verifying-ai-services-are-ready)
    - [GPU Logs (via bastion)](#gpu-logs-via-bastion)
    - [Update `pilot/prod/gpu` Secret After GPU Instance Replacement](#update-pilotprodgpu-secret-after-gpu-instance-replacement)
  - [8. Manual Application Deployments](#8-manual-application-deployments)
    - [8.1 Deploy Backend API (FastAPI)](#81-deploy-backend-api-fastapi)
    - [8.2 Deploy Celery Worker + Beat (same image as API)](#82-deploy-celery-worker--beat-same-image-as-api)
    - [8.3 Deploy Web Dashboard (pilot-web)](#83-deploy-web-dashboard-pilot-web)
    - [8.4 Deploy Marketing Site](#84-deploy-marketing-site)
  - [9. Database Operations](#9-database-operations)
    - [9.1 Open SSH Tunnel for Direct DB Access (VS Code / psql)](#91-open-ssh-tunnel-for-direct-db-access-vs-code--psql)
    - [Check / Kill Existing Tunnels](#check--kill-existing-tunnels)
    - [9.2 Run Alembic Migrations Against Production](#92-run-alembic-migrations-against-production)
    - [9.3 Reset Database (no customer data — dev migrations only)](#93-reset-database-no-customer-data--dev-migrations-only)
    - [9.4 Run a Raw SQL Query Against Production](#94-run-a-raw-sql-query-against-production)
    - [9.5 DB Backup \& Restore (Dev → Prod Schema Sync)](#95-db-backup--restore-dev--prod-schema-sync)
    - [9.6 Run Seed Scripts Against Production](#96-run-seed-scripts-against-production)
    - [9.7 Prod Migration Sync — Full Workflow (Dev ↔ Prod Version Parity)](#97-prod-migration-sync--full-workflow-dev--prod-version-parity)
    - [9.8 Remove a Test / Abandoned Signup (Prod)](#98-remove-a-test--abandoned-signup-prod)
    - [9.9 Remove an Invited Employee (Prod) — Invite-Accept Teardown for Email Reuse](#99-remove-an-invited-employee-prod--invite-accept-teardown-for-email-reuse)
    - [Redis Tunnel (for redis-cli debugging)](#redis-tunnel-for-redis-cli-debugging)
  - [10. AWS Secrets Manager — Audit and Update](#10-aws-secrets-manager--audit-and-update)
    - [10.1 List All Pilot Secrets](#101-list-all-pilot-secrets)
    - [10.2 Read a Secret Value](#102-read-a-secret-value)
    - [10.3 Update a Secret Value](#103-update-a-secret-value)
    - [10.4 Full Secrets Audit Checklist](#104-full-secrets-audit-checklist)
    - [10.5 Dump All Secrets (Names Only or Full Values)](#105-dump-all-secrets-names-only-or-full-values)
  - [11. View Application Logs (CloudWatch)](#11-view-application-logs-cloudwatch)
    - [Tail Logs Live](#tail-logs-live)
    - [Filter Logs (last hour)](#filter-logs-last-hour)
    - [ECS Task-Level Logs (for a specific running task)](#ecs-task-level-logs-for-a-specific-running-task)
  - [12. Health Checks — Verify Everything Is Running](#12-health-checks--verify-everything-is-running)
  - [13. Cost Monitoring](#13-cost-monitoring)
    - [Quick Cost Check (This Month)](#quick-cost-check-this-month)
    - [Profile Cost Summary](#profile-cost-summary)
  - [14. Terraform Operations — Updating Infrastructure](#14-terraform-operations--updating-infrastructure)
    - [14.1 Standard Update Process](#141-standard-update-process)
    - [14.2 Targeted Applies](#142-targeted-applies)
    - [14.3 Module Ownership Reference](#143-module-ownership-reference)
    - [14.4 Common Update Scenarios](#144-common-update-scenarios)
    - [14.5 Resources That Require Extra Steps](#145-resources-that-require-extra-steps)
    - [14.6 Secrets Manager Decision Framework](#146-secrets-manager-decision-framework)
    - [14.7 Phase 2 Security Upgrade: IAM Database Authentication](#147-phase-2-security-upgrade-iam-database-authentication)
  - [15. Infrastructure State Management](#15-infrastructure-state-management)
    - [What It Is](#what-it-is)
    - [When to Run `generate-infra-state.sh`](#when-to-run-generate-infra-statesh)
    - [Feature Flags Written to `.infra-state.env`](#feature-flags-written-to-infra-stateenv)
    - [Resource IDs Written](#resource-ids-written)
  - [18. CloudWatch Metrics — Troubleshooting Commands](#18-cloudwatch-metrics--troubleshooting-commands)
    - [18.1 ECS Memory Utilization (all services)](#181-ecs-memory-utilization-all-services)
    - [18.2 ECS CPU Utilization (all services)](#182-ecs-cpu-utilization-all-services)
    - [18.3 ALB HTTP 5xx Errors and Request Count](#183-alb-http-5xx-errors-and-request-count)
    - [18.4 ALB Target Response Time (p95 Latency)](#184-alb-target-response-time-p95-latency)
    - [18.5 CloudWatch Alarms — Current State and History](#185-cloudwatch-alarms--current-state-and-history)
  - [16. Rollback Procedures](#16-rollback-procedures)
  - [17. Certificate and DNS Rotation](#17-certificate-and-dns-rotation)
    - [17.1 p4tsites.com — Cloudflare DNS + ACM Cert (C-B16-OPS, ADR-0014)](#171-p4tsitescom--cloudflare-dns--acm-cert-c-b16-ops-adr-0014)
  - [19. ECS Task Deployment Troubleshooting](#19-ecs-task-deployment-troubleshooting)
    - [19.1 Watch-and-Run Pattern (no sleep)](#191-watch-and-run-pattern-no-sleep)
    - [19.2 Force a Specific Task Definition Revision](#192-force-a-specific-task-definition-revision)
    - [19.3 Clear Multiple Active Deployments](#193-clear-multiple-active-deployments)
    - [19.4 Register a New Task Definition Revision](#194-register-a-new-task-definition-revision)
    - [19.5 Container Health Check Behavior in Fargate Alpine Images](#195-container-health-check-behavior-in-fargate-alpine-images)
    - [19.6 Post-Deploy: Sync ALL Services + Deploy Canary (the last step of EVERY deploy)](#196-post-deploy-sync-all-services--deploy-canary-the-last-step-of-every-deploy)
    - [19.7 Docker Images Must Never Contain `.env` (`.dockerignore` ≠ `.gitignore`)](#197-docker-images-must-never-contain-env-dockerignore--gitignore)
  - [20. Manual E2E Test Execution](#20-manual-e2e-test-execution)
    - [20.1 Overview — Harness Architecture](#201-overview--harness-architecture)
    - [20.2 Pre-Launch Checklist — When to Run](#202-pre-launch-checklist--when-to-run)
    - [20.3 Tier 1 — pytest Integration Tests (Isolated DB)](#203-tier-1--pytest-integration-tests-isolated-db)
    - [20.4 Tier 2 — Playwright Web Smoke Tests (Requires Live Stack)](#204-tier-2--playwright-web-smoke-tests-requires-live-stack)
    - [20.5 CI/CD Note — GitHub Actions (Phase 7, Deferred)](#205-cicd-note--github-actions-phase-7-deferred)
  - [17.2 Cloudflare DNS Zone Inventories (HIBERNATE-1)](#172-cloudflare-dns-zone-inventories-hibernate-1)
  - [21. Restart Runbook (HIBERNATE-1 → Reactivation)](#21-restart-runbook-hibernate-1--reactivation)

---

## 1. Cost Floor — What Always Runs

These services **cannot be cost-effectively stopped**. They are your fixed monthly floor regardless of which profile is active.

| Service | Why It Can't Stop | Monthly Cost |
|---|---|---|
| **RDS PostgreSQL** | AWS auto-restarts after 7 days; data must persist; migrations require running instance | **~$28** |
| **ElastiCache Redis** | No stop feature — only delete (destroys data); minimal cost not worth disruption | **~$13** |
| **NAT Gateway** | Required for all private-subnet outbound internet; no selective stop | **~$32** |
| **ALB** | Required for any API traffic; no stop feature | **~$18** |
| **S3 + CloudFront (marketing)** | Static files; near-zero cost; always serving | **~$2** |
| **Route 53 Hosted Zone** | DNS must always resolve | **~$1** |
| **Bastion Elastic IP** | Static IP reservation; billed even when stopped | **~$3.50** |
| **CloudWatch (base)** | Log retention, minimum metrics | **~$5** |
| **FLOOR TOTAL** | | **~$102/month** |

> **The GPU instance (~$390/month) is your biggest lever.** Stopping it when not needed is the single highest-impact cost action you can take.

---

## 2. The Four Operating Profiles

All four profile scripts are **fully atomic** — each one independently enforces its complete desired service state from any prior state. Run any script from any starting condition; it converges to the correct target without manual pre-steps.

### Profile OFF: Cost Floor
**Use when**: Not actively developing or testing. Saving maximum cost overnight/weekends.

**Desired state enforced:**
- ⛔ GPU (g4dn.xlarge) → **stopped**
- ⛔ ECS pilot-web → **0 tasks**
- ⛔ ECS pilot-api → **0 tasks**
- ⛔ ECS pilot-celery-worker → **0 tasks**
- ⛔ ECS pilot-celery-beat → **0 tasks**
- ⛔ Bastion → **stopped**
- 🌐 `site-config.json` → `{"mode":"coming_soon","message":"..."}`

**Monthly cost: ~$102** (cost floor only)

---

### Profile A: Marketing Only
**Use when**: Collecting leads, testing form submissions, reviewing legal/pricing pages. No app or AI features needed.

**Desired state enforced (from any prior state):**
- ⛔ GPU (g4dn.xlarge) → **stopped** (if running, stops it)
- ⛔ ECS pilot-web → **0 tasks**
- ✅ ECS pilot-api → **1 task**
- ✅ ECS pilot-celery-worker → **1 task**
- ✅ ECS pilot-celery-beat → **1 task**
- 🌐 `site-config.json` → `{"mode":"live"}`

**Monthly cost: ~$148** ($102 floor + ~$20 API task + ~$9 worker + ~$8 beat + ~$7 bastion running)

---

### Profile B: Web App + Mobile App
**Use when**: Developing or testing the web dashboard, mobile app, or Voice AI features.

#### `light` (~$170/month) — No GPU
**Desired state enforced:**
- ⛔ GPU → **stopped** (if running, stops it)
- ✅ ECS pilot-web → **1 task**
- ✅ ECS pilot-api → **1 task**
- ✅ ECS pilot-celery-worker → **1 task**
- ✅ ECS pilot-celery-beat → **1 task**
- 🌐 `site-config.json` → `{"mode":"live"}`

#### `ai` (~$562/month) — GPU Running
**Desired state enforced:**
- ✅ GPU → **running** (if stopped, starts it)
- ✅ ECS pilot-web → **1 task**
- ✅ ECS pilot-api → **2 tasks**
- ✅ ECS pilot-celery-worker → **2 tasks**
- ✅ ECS pilot-celery-beat → **1 task**
- 🌐 `site-config.json` → `{"mode":"live"}`

---

### Profile C: Beta Customer Pre-Launch
**Use when**: Beta customers are about to access the product. Enforces full production-equivalent state, then runs 7 health checks.

**Monthly cost: ~$562** (same resource set as `B ai`)

---

### Profile Comparison Table

| Component | OFF | A: Marketing | B light: UI only | B ai: Full AI | C: Beta |
|---|---|---|---|---|---|
| RDS + Redis | ✅ On | ✅ On | ✅ On | ✅ On | ✅ On |
| NAT + ALB | ✅ On | ✅ On | ✅ On | ✅ On | ✅ On |
| FastAPI ECS | ⛔ 0 tasks | ✅ 1 task | ✅ 1 task | ✅ 2 tasks | ✅ 2 tasks |
| Celery Worker | ⛔ 0 tasks | ✅ 1 task | ✅ 1 task | ✅ 2 tasks | ✅ 2 tasks |
| Celery Beat | ⛔ 0 tasks | ✅ 1 task | ✅ 1 task | ✅ 1 task | ✅ 1 task |
| GPU (g4dn.xlarge) | ⛔ Stopped | ⛔ Stopped | ⛔ Stopped | ✅ Running | ✅ Running |
| ECS pilot-web | ⛔ 0 tasks | ⛔ 0 tasks | ✅ 1 task | ✅ 1 task | ✅ 1 task |
| Bastion | ⛔ Stopped | ✅ Running | ✅ Running | ✅ Running | ✅ Running |
| Marketing site | ✅ Coming Soon | ✅ Live + forms | ✅ Live + forms | ✅ Live + forms | ✅ Live + forms |
| Voice AI | ❌ No | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Est. Monthly** | **~$102** | **~$148** | **~$170** | **~$562** | **~$562–667** |

---

## 3. Profile Commands — Quick Reference

All scripts are located at `infrastructure/scripts/`. Run from the repo root or from `infrastructure/scripts/`.

```bash
# ── Profile OFF: Shutdown to cost floor ──────────────────────────────────────
./infrastructure/scripts/profile-off.sh
# → Stops GPU, bastion, scales all ECS to 0 (api/worker/beat/web), sets site → coming_soon

# ── Profile A: Marketing only ─────────────────────────────────────────────────
./infrastructure/scripts/profile-a-marketing.sh
# → Stops GPU, scales pilot-web to 0, scales API/Worker/Beat ECS to 1/1/1, sets site → live

# ── Profile B: Web app + mobile app ──────────────────────────────────────────
./infrastructure/scripts/profile-b-app.sh light      # No GPU. ~$170/month
./infrastructure/scripts/profile-b-app.sh ai         # GPU on. ~$562/month
./infrastructure/scripts/profile-b-app.sh --help     # Show options

# ── Profile C: Beta customer pre-launch ──────────────────────────────────────
./infrastructure/scripts/profile-c-full.sh
# → Enforces B-ai state, waits 60s, then runs 7 health checks
# → Exits code 1 if any check fails; safe to re-run
```

> **All scripts require confirmation (`yes/no`) before executing.** They all validate the AWS account (`000000000000`) before making any changes.

---

## 4. Coming Soon Mode — Marketing Site Toggle

The marketing site at `pilotfortrades.com` reads a config file on every page load and switches between two modes:

| Mode | What visitors see | When |
|---|---|---|
| `live` | Full marketing site — all pages, all forms working | Profiles A, B, C |
| `coming_soon` | Brand hero page, no nav, no forms, `mailto:sales@` CTA | Profile OFF |

### Manual Toggle (if needed without running a full profile script)

```bash
# Pull the distribution ID dynamically — never hardcode it
CLOUDFRONT_DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, 'pilotfortrades.com')].Id" \
  --output text --region us-east-1)
MARKETING_BUCKET="pilot-production-marketing"

# Switch TO coming_soon (e.g., emergency maintenance)
aws s3 cp - "s3://$MARKETING_BUCKET/site-config.json" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "application/json" <<< \
  '{"mode":"coming_soon","message":"We are performing scheduled maintenance. Back shortly."}'
aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DIST_ID" --paths "/site-config.json" --region us-east-1

# Switch BACK to live
aws s3 cp - "s3://$MARKETING_BUCKET/site-config.json" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "application/json" <<< '{"mode":"live"}'
aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DIST_ID" --paths "/site-config.json" --region us-east-1
```

> **CloudFront invalidation is required** every time the file changes. Without it, CloudFront may serve the cached version for up to 24 hours.

---

## 5. Individual Resource Start/Stop Reference

### ECS Services (FastAPI, Celery Worker, Celery Beat, Web Dashboard)

```bash
# View all four service states at once
aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-api pilot-celery-worker pilot-celery-beat pilot-web \
  --query 'services[*].{Name:serviceName,Running:runningCount,Desired:desiredCount,Status:status}' \
  --output table --region us-east-1

# Scale API to 0 (stop) / 1 / 2
aws ecs update-service --cluster pilot-production --service pilot-api --desired-count 0 --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-api --desired-count 1 --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-api --desired-count 2 --region us-east-1

# Scale Celery Worker
aws ecs update-service --cluster pilot-production --service pilot-celery-worker --desired-count 0 --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-celery-worker --desired-count 1 --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-celery-worker --desired-count 2 --region us-east-1

# Scale Celery Beat (only ever 0 or 1 — never 2+)
aws ecs update-service --cluster pilot-production --service pilot-celery-beat --desired-count 0 --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-celery-beat --desired-count 1 --region us-east-1

# Scale Web Dashboard
aws ecs update-service --cluster pilot-production --service pilot-web --desired-count 0 --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-web --desired-count 1 --region us-east-1
```

> **⚠️ Beat warning**: Celery Beat must run as exactly 1 instance — never 2+. Running multiple Beat instances causes duplicate scheduled task execution (duplicate emails, QB syncs, etc.).

> **ECS costs $0 at `desired-count 0`**: Fargate only bills for running tasks. The service definition remains in place; set desired count back to start.

---

### GPU Instance (Whisper + Ollama)

```bash
# Get GPU instance ID dynamically
GPU_INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-gpu" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text --region us-east-1)
echo "GPU: $GPU_INSTANCE_ID"

# Stop (saves ~$390/month; EBS still billed ~$5.60/mo)
aws ec2 stop-instances --instance-ids "$GPU_INSTANCE_ID" --region us-east-1

# Start (takes 3-5 min to boot + 5-15 min for Ollama model to load)
aws ec2 start-instances --instance-ids "$GPU_INSTANCE_ID" --region us-east-1

# Check status
aws ec2 describe-instances --instance-ids "$GPU_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text --region us-east-1
```

---

### RDS PostgreSQL

> **Do not stop RDS** unless absolutely necessary. AWS auto-restarts stopped RDS instances after 7 days — surprising and disruptive.

```bash
# Status
aws rds describe-db-instances --db-instance-identifier pilot-production \
  --query 'DBInstances[0].DBInstanceStatus' --output text --region us-east-1

# Stop (will auto-restart after 7 days!)
aws rds stop-db-instance --db-instance-identifier pilot-production --region us-east-1

# Start RDS
aws rds start-db-instance --db-instance-identifier pilot-production --region us-east-1
```

---

## 6. Bastion Host — Starting, Stopping, and Connecting

The bastion is a `t4g.nano` EC2 instance with a static Elastic IP (`203.0.113.12`). It provides the jump host for SSH tunnels to RDS, Redis, and the GPU instance. It is **stopped when not needed** to save compute cost (~$3/month); the Elastic IP remains reserved ($3.50/month) whether it's running or not.

### Start the Bastion

```bash
# Get bastion instance ID dynamically
BASTION_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-bastion" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text --region us-east-1)
echo "Bastion: $BASTION_ID"

# Start it
aws ec2 start-instances --instance-ids "$BASTION_ID" --region us-east-1

# Wait until running (takes ~60 seconds)
aws ec2 wait instance-running --instance-ids "$BASTION_ID" --region us-east-1
echo "Bastion is running — SSH ready at 203.0.113.12"
```

### Stop the Bastion

```bash
BASTION_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-bastion" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text --region us-east-1)

aws ec2 stop-instances --instance-ids "$BASTION_ID" --region us-east-1
echo "Bastion stopping... (Elastic IP 203.0.113.12 remains reserved)"
```

### Check Bastion Status

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-bastion" \
  --query 'Reservations[0].Instances[0].{State:State.Name,PublicIP:PublicIpAddress,InstanceId:InstanceId}' \
  --output table --region us-east-1
```

### SSH Config (`~/.ssh/config`)

This config should already be in place. Verify or add it:

> **⚠️ SSH tunnel drop fix (2026-07-05)**: Added `ServerAliveInterval` and `ServerAliveCountMax` to prevent macOS from dropping idle tunnels after a few minutes. Without these, the TCP idle timeout silently kills the SSH connection. With them, SSH sends a keepalive packet every 60 seconds — the tunnel stays open until you explicitly kill it.

```
Host *
  AddKeysToAgent yes
  UseKeychain yes
  ServerAliveInterval 60        # Send keepalive every 60s — prevents idle drop
  ServerAliveCountMax 10        # Retry 10 times before giving up (10 min tolerance)

Host pilot-bastion
  HostName 203.0.113.12               # Static Elastic IP — never changes
  User ec2-user
  IdentityFile ~/.ssh/pilot_admin_ed25519
  StrictHostKeyChecking no
  ServerAliveInterval 60
  ServerAliveCountMax 10

Host pilot-gpu
  HostName <GPU_PRIVATE_IP>           # Update after each GPU instance replacement
  User ec2-user
  IdentityFile ~/.ssh/pilot_admin_ed25519
  ProxyJump pilot-bastion             # Routes automatically through bastion
  ServerAliveInterval 60
  ServerAliveCountMax 10
```

### Persistent Tunnels with `autossh` (Recommended for Long Admin Sessions)

`autossh` wraps `ssh` and **automatically reconnects** if the tunnel drops — useful during long Terraform applies, Alembic migrations, or GPU monitoring sessions. Install once, then use instead of `ssh -f -N`.

> **⚠️ Known issue (2026-08-09)**: `autossh` can wedge into a state where the parent process stays alive but its SSH child dies and is never respawned — leaving **no listener on the forwarded port** even though `ps` shows autossh "running." This happens when the SSH child exits (auth failure, network blip) and autossh's retry loop stalls. The pre-flight check below detects and fixes this. **Always run the pre-flight before starting a tunnel.**

#### One-time install (macOS Homebrew)

```bash
brew install autossh
```

#### Step 1 — Pre-flight: clear any hung / locked tunnel processes

Run this **every time** before starting a tunnel. It detects the wedged state (autossh alive but no SSH child / no listener) and force-kills stale processes so the new tunnel starts clean.

```bash
# ── 1a. List current autossh + ssh tunnel processes ──────────────────────────
echo "── Existing tunnel processes ──"
ps aux | grep -E "autossh|ssh -f -N -L" | grep -v grep || echo "(none running)"

# ── 1b. Check if port 5433 has a live listener ───────────────────────────────
echo "── Port 5433 listener ──"
lsof -nP -iTCP:5433 -sTCP:LISTEN 2>/dev/null || echo "NOTHING on 5433"

# ── 1c. Kill all autossh processes (SIGTERM first) ────────────────────────────
pkill autossh 2>/dev/null && echo "Sent SIGTERM to autossh processes" || echo "No autossh to SIGTERM"
sleep 1

# ── 1d. Force-kill any that survived SIGTERM (the wedged-state fix) ───────────
#   macOS quirk: pkill autossh sometimes leaves a stuck parent that ignores
#   SIGTERM. kill -9 is the only way to clear it. This is safe — autossh has
#   no state to corrupt; the next start recreates everything.
STUCK_PIDS=$(pgrep autossh)
if [ -n "$STUCK_PIDS" ]; then
  echo "Force-killing stuck autossh PIDs: $STUCK_PIDS"
  echo "$STUCK_PIDS" | xargs kill -9 2>/dev/null
  sleep 1
fi

# ── 1e. Kill any orphaned ssh tunnel children (port-forward only) ────────────
pkill -f "ssh -f -N -L" 2>/dev/null && echo "Killed orphaned ssh tunnels" || echo "No orphaned ssh tunnels"

# ── 1f. Verify clean slate ───────────────────────────────────────────────────
echo "── Post-cleanup verify ──"
ps aux | grep -E "autossh|ssh -f -N -L" | grep -v grep && echo "⚠️ STILL RUNNING — investigate" || echo "✅ Clean slate"
lsof -nP -iTCP:5433 -sTCP:LISTEN 2>/dev/null && echo "⚠️ 5433 STILL BOUND" || echo "✅ Port 5433 free"
```

#### Step 2 — Verify prerequisites (bastion running + SSH key loaded)

```bash
# ── 2a. Bastion must be running ───────────────────────────────────────────────
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-bastion" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text --region us-east-1
# Expected: running   ← if "stopped", start it first (see §6 "Start the Bastion")

# ── 2b. SSH key must be loaded in the agent ───────────────────────────────────
#   autossh runs SSH in the background (-f) where it CANNOT prompt for a
#   passphrase. If the key isn't loaded, the SSH child dies instantly and
#   autossh wedges — this is the #1 cause of the "no listener" state.
ssh-add -l | grep -q "pilot-admin" && echo "✅ Key loaded" || {
  echo "❌ Key not in agent — loading now (may prompt for passphrase)..."
  ssh-add --apple-use-keychain ~/.ssh/pilot_admin_ed25519
}
```

#### Step 3 — Start the RDS persistent tunnel (local 5433 → RDS 5432)

```bash
# ── 3a. Get RDS endpoint dynamically ──────────────────────────────────────────
RDS_EP=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text --region us-east-1)
echo "RDS endpoint: $RDS_EP"

# ── 3b. Start autossh (background, auto-reconnect) ────────────────────────────
#   -M 0              → disable autossh monitoring port (ServerAliveInterval handles keepalives)
#   -f                → fork into background after auth succeeds
#   -N                → no remote command (port forward only)
#   ExitOnForwardFailure=yes → exit immediately if the port forward can't bind
#   ConnectTimeout=15 → fail fast if bastion is unreachable (don't wedge)
autossh -M 0 -f -N \
  -o "ServerAliveInterval=60" \
  -o "ServerAliveCountMax=10" \
  -o "ExitOnForwardFailure=yes" \
  -o "ConnectTimeout=15" \
  -L 5433:${RDS_EP}:5432 pilot-bastion
echo "autossh started (exit code: $?)"
```

#### Step 4 — Verify the tunnel is actually listening (do not skip)

This is the critical step that catches the wedged state. **A running autossh process does NOT mean the tunnel works** — you must confirm a listener is bound and the port accepts connections.

```bash
# ── 4a. Confirm a process is listening on 5433 ────────────────────────────────
sleep 2   # give autossh ~2s to establish the SSH child + bind the port
echo "── Listener on 5433 ──"
lsof -nP -iTCP:5433 -sTCP:LISTEN 2>/dev/null && echo "✅ Listener bound" || echo "Listener NOT bound"

# lsof -nP -iTCP:5433 -sTCP:LISTEN 2>/dev/null && echo "✅ Listener bound" || {
#   echo "❌ NO LISTENER — autossh wedged. Run Step 1 (pre-flight) then Step 3 again."
#   exit 1
# }

# ── 4b. Confirm the port accepts TCP connections ──────────────────────────────
echo "── TCP connect test ──"
nc -z -w5 127.0.0.1 5433 && echo "✅ Port 5433 reachable" || echo "❌ Port 5433 closed"

# ── 4c. Confirm PostgreSQL responds through the tunnel (end-to-end) ───────────
echo "── PostgreSQL handshake ──"
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT version();" 2>&1 | head -2
# Expected: "PostgreSQL 16.x ..." → tunnel is fully functional ✅
```

> **VS Code PostgreSQL extension**: Once Step 4 passes, connect with Host `127.0.0.1`, Port `5433`, Database `pilot_prod`, User `pilot_user`. See §9.1 for full settings.

#### Step 5 — (Optional) Start the Redis persistent tunnel (local 6380 → Redis 6379)

```bash
REDIS_EP=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id pilot-production \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text --region us-east-1)

autossh -M 0 -f -N \
  -o "ServerAliveInterval=60" \
  -o "ServerAliveCountMax=10" \
  -o "ExitOnForwardFailure=yes" \
  -o "ConnectTimeout=15" \
  -L 6380:${REDIS_EP}:6379 pilot-bastion
echo "Redis tunnel started: 127.0.0.1:6380 → ${REDIS_EP}:6379"

# Verify
sleep 2
lsof -nP -iTCP:6380 -sTCP:LISTEN 2>/dev/null && echo "✅ Redis listener bound" || echo "❌ NO LISTENER on 6380"
nc -z -w5 127.0.0.1 6380 && echo "✅ Port 6380 reachable" || echo "❌ Port 6380 closed"
```

#### Stopping tunnels

```bash
# ── Kill all persistent tunnels (autossh + orphaned ssh children) ─────────────
pkill autossh 2>/dev/null; sleep 1
pgrep autossh | xargs kill -9 2>/dev/null   # force-kill any wedged parents
pkill -f "ssh -f -N -L" 2>/dev/null          # kill orphaned ssh children
echo "All tunnels closed"

# ── Kill only the RDS tunnel (preserve Redis) ─────────────────────────────────
RDS_EP=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text --region us-east-1)
pkill -f "5433:${RDS_EP}:5432" && echo "RDS tunnel killed"

# ── Check what's running ─────────────────────────────────────────────────────
ps aux | grep -E "autossh|ssh -f -N -L" | grep -v grep
```

#### Quick health check (run anytime to confirm tunnels are alive)

```bash
echo "── Processes ──"
ps aux | grep -E "autossh|ssh -f -N -L" | grep -v grep || echo "(no tunnels running)"
echo "── Port 5433 (RDS) ──"
lsof -nP -iTCP:5433 -sTCP:LISTEN 2>/dev/null && nc -z -w3 127.0.0.1 5433 && echo "✅ RDS tunnel OK" || echo "❌ RDS tunnel DOWN"
echo "── Port 6380 (Redis) ──"
lsof -nP -iTCP:6380 -sTCP:LISTEN 2>/dev/null && nc -z -w3 127.0.0.1 6380 && echo "✅ Redis tunnel OK" || echo "❌ Redis tunnel DOWN"
```

> **`-M 0` explained**: Disables autossh's built-in monitoring port (not needed when `ServerAliveInterval` is set — SSH itself handles keepalives). This avoids port conflicts.
>
> **When to use plain `ssh -f -N` vs `autossh`**: Use `ssh -f -N` for quick one-off commands (e.g., one Alembic migration run). Use `autossh` when you need the tunnel open for 30+ minutes or across multiple commands in a session.
>
> **Why `kill -9` is sometimes needed**: macOS's `pkill autossh` sends SIGTERM, but a wedged autossh parent (SSH child dead, retry loop stalled) can ignore it. `kill -9` is the only reliable way to clear it. This is safe — autossh is stateless; the next start recreates everything from scratch.

### Connect to Bastion

```bash
# Simple SSH to bastion (must be running first)
ssh pilot-bastion
# Expected: Amazon Linux 2023 shell prompt

# Verify your SSH key is loaded
ssh-add -l
# Expected: 256 SHA256:... pilot-admin (ED25519)
# If not: ssh-add --apple-use-keychain ~/.ssh/pilot_admin_ed25519
```

### Update Your IP When It Changes (home ISP / Travel / Hotel WiFi)

```bash
# 1. Get your current public IP
curl -s https://api.ipify.org
# Example: 203.0.113.13

# 2. Update infrastructure/terraform/environments/production/terraform.tfvars
#    Edit: admin_allowed_ips = ["203.0.113.13", "<NEW_IP>"]

# 3. Apply only the bastion security group rule (fast — ~30 seconds)
cd infrastructure/terraform/environments/production
terraform apply -target=module.networking.aws_security_group_rule.bastion_ssh_ingress
cd ../../../..

# 4. Reconnect
ssh pilot-bastion
```

---

## 7. GPU Instance Management

### Getting GPU Private IP (for SSH config or secret updates)

```bash
GPU_PRIVATE_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-gpu" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text --region us-east-1)
echo "GPU private IP: $GPU_PRIVATE_IP"
```

### Verifying AI Services Are Ready

```bash
# SSH through bastion to GPU (both must be running)
ssh pilot-gpu

# On GPU: check Whisper is running
curl -s http://localhost:8080/health
# Expected: {"status":"ok"} or version info

# On GPU: check Ollama is running and model is loaded
curl -s http://localhost:11434/api/tags | python3 -m json.tool
# Expected: JSON with "llama3.1:8b" in the model list

# On GPU: check Docker containers are up
docker ps
# Expected: whisper and ollama containers running
```

### GPU Logs (via bastion)

```bash
ssh pilot-gpu "docker compose logs --tail=50 whisper"
ssh pilot-gpu "docker compose logs --tail=50 ollama"

# Follow live
ssh pilot-gpu "docker compose logs -f whisper"
ssh pilot-gpu "docker compose logs -f ollama"

# Restart AI services without rebooting
ssh pilot-gpu "docker compose restart whisper"
ssh pilot-gpu "docker compose restart ollama"
```

### Update `pilot/prod/gpu` Secret After GPU Instance Replacement

If the GPU instance is **replaced** (not just stopped/started), the private IP changes and the secret must be updated:

```bash
# Get new private IP
GPU_PRIVATE_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-gpu" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text --region us-east-1)

# Update the secret
aws secretsmanager put-secret-value \
  --secret-id "pilot/prod/gpu" \
  --secret-string "{\"whisper_url\": \"http://${GPU_PRIVATE_IP}:8080/v1\", \"ollama_url\": \"http://${GPU_PRIVATE_IP}:11434/api\"}" \
  --region us-east-1
echo "Updated pilot/prod/gpu with new IP: $GPU_PRIVATE_IP"

# Force ECS to pick up the new secret value
aws ecs update-service --cluster pilot-production --service pilot-api \
  --force-new-deployment --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-celery-worker \
  --force-new-deployment --region us-east-1
```

---

## 8. Manual Application Deployments

> **CI/CD status**: GitHub Actions CI/CD is explicitly deferred post-beta. All application deployments use the manual procedures in this section. See `aws-deployment-plan-v1.md §1.1` for the rationale.

All deploy procedures follow the same pattern:
1. Pull dynamic vars from AWS (never hardcode account IDs or resource IDs)
2. Authenticate to ECR
3. Build image with `--platform linux/amd64` (required — Mac is arm64; ECS Fargate is x86_64)
4. Push to ECR
5. Force a new ECS deployment
6. Verify health

---

### 8.1 Deploy Backend API (FastAPI)

The `pilot-api`, `pilot-celery-worker`, and `pilot-celery-beat` services all run the same Docker image from `backend/Dockerfile`. Build once, tag for all three repos.

```bash
# ── Step 1: Pull dynamic vars ──────────────────────────────────────────────────
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION="us-east-1"
ECR_BASE="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Account: $AWS_ACCOUNT  |  ECR: $ECR_BASE"
# Verify: should show 000000000000

# ── Step 2: Authenticate to ECR ───────────────────────────────────────────────
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${ECR_BASE}"

# ── Step 3: Build the image (linux/amd64 required for ECS Fargate) ────────────
cd <repo>
docker build --platform linux/amd64 --no-cache -t pilot-api ./backend

# ── Step 4: Tag for all three backend repos ───────────────────────────────────
docker tag pilot-api:latest "${ECR_BASE}/pilot/api:latest"
docker tag pilot-api:latest "${ECR_BASE}/pilot/worker:latest"
docker tag pilot-api:latest "${ECR_BASE}/pilot/beat:latest"

# ── Step 5: Push all three ────────────────────────────────────────────────────
docker push "${ECR_BASE}/pilot/api:latest"
docker push "${ECR_BASE}/pilot/worker:latest"
docker push "${ECR_BASE}/pilot/beat:latest"

echo "ECR push complete"

# ── Step 6: Force new deployments ─────────────────────────────────────────────
# Run migrations BEFORE redeploying the API (see §9.2)

AWS_REGION="us-east-1"
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-api \
  --force-new-deployment \
  --no-cli-pager \
  --region "$AWS_REGION"

AWS_REGION="us-east-1"
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-celery-worker \
  --force-new-deployment \
  --no-cli-pager \
  --region "$AWS_REGION"

AWS_REGION="us-east-1"
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-celery-beat \
  --force-new-deployment \
  --no-cli-pager \
  --region "$AWS_REGION"

echo "ECS deployments triggered — takes ~3-5 min for health checks"

# To redeploy and FORCE the task-definition version
# First get the latest revision number
for fam in pilot-api pilot-celery-worker pilot-celery-beat pilot-production-web; do echo "=== $fam latest revision ==="; aws ecs describe-task-definition --task-definition "$fam" --query 'taskDefinition.{Revision:revision,Status:status}' --region us-east-1; echo; done

# Then replace the :# in each of the task-definitions below to the latest from above report
aws ecs update-service --cluster pilot-production --service pilot-api \
  --task-definition pilot-api:10 --force-new-deployment --no-cli-pager --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-celery-worker \
  --task-definition pilot-celery-worker:6 --force-new-deployment --no-cli-pager --region us-east-1
aws ecs update-service --cluster pilot-production --service pilot-celery-beat \
  --task-definition pilot-celery-beat:5 --force-new-deployment --no-cli-pager --region us-east-1

# ── Step 7: Wait for API to stabilize ─────────────────────────────────────────
aws ecs wait services-stable \
  --cluster pilot-production \
  --services pilot-api \
  --region "$AWS_REGION"
echo "pilot-api is stable ✅"

# ── Step 8: Verify ────────────────────────────────────────────────────────────
curl -sf https://api.pilotfortrades.com/api/v1/health/celery
# Expected: {"status":"healthy","workers_active":...}
```

> **Note**: `pilot-celery-worker` and `pilot-celery-beat` do not have ALB health checks, so `ecs wait services-stable` only waits on `pilot-api`. The worker and beat reach stable state shortly after.

---

#### 8.1.1 Deploy API Only

```bash
cd <repo>

AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION="us-east-1"
ECR_BASE="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
echo "Account: $AWS_ACCOUNT  |  ECR: $ECR_BASE"
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${ECR_BASE}"
docker build --platform linux/amd64 -t pilot-api ./backend

docker tag pilot-api:latest "${ECR_BASE}/pilot/api:latest"
docker push "${ECR_BASE}/pilot/api:latest"

AWS_REGION="us-east-1"
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-api \
  --force-new-deployment \
  --no-cli-pager \
  --region "$AWS_REGION"
```

---

### 8.2 Deploy Celery Worker + Beat (same image as API)

If you only need to redeploy workers (not API), push to the worker/beat repos and force their deployments independently:

```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION="us-east-1"
ECR_BASE="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build + push (only if image changed)
cd <repo>

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${ECR_BASE}"

docker build --platform linux/amd64 -t pilot-api ./backend
docker tag pilot-api:latest "${ECR_BASE}/pilot/worker:latest"
docker tag pilot-api:latest "${ECR_BASE}/pilot/beat:latest"
docker push "${ECR_BASE}/pilot/worker:latest"
docker push "${ECR_BASE}/pilot/beat:latest"

# Redeploy
aws ecs update-service --cluster pilot-production --service pilot-celery-worker \
  --force-new-deployment --no-cli-pager --region "$AWS_REGION"
aws ecs update-service --cluster pilot-production --service pilot-celery-beat \
  --force-new-deployment --no-cli-pager --region "$AWS_REGION"
echo "Worker and Beat redeployment triggered"
```

---

### 8.3 Deploy Web Dashboard (pilot-web)

The web dashboard is a Next.js standalone server (`frontend/apps/web/Dockerfile`), deployed as the `pilot-web` ECS service. It has its **own** ECR repo (`pilot/web`) and is **not** the same image as the backend.

> **⚠️ Build context must be `frontend/` — not `frontend/apps/web/`**
> The Dockerfile COPYs workspace packages (`packages/shared-api/`, `packages/ui/`, `packages/typescript-config/`, etc.) that only exist relative to the `frontend/` monorepo root. Running `docker build .` from inside `frontend/apps/web/` will fail at the first `COPY packages/` instruction.

```bash
# ── Step 1: Pull dynamic vars ──────────────────────────────────────────────────
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION="us-east-1"
ECR_BASE="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ── Step 2: Authenticate to ECR ───────────────────────────────────────────────
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${ECR_BASE}"

# ── Step 3: Build web image ────────────────────────────────────────────────────
# IMPORTANT: Run from the REPO ROOT (not from inside frontend/apps/web/).
# Build context is frontend/ so all workspace packages are reachable.
cd <repo>

# NEXT_PUBLIC_* vars are baked into the JS bundle at Next.js build time.
# They CANNOT be injected at runtime — they MUST be passed as --build-arg here.
# Omitting them produces "Auth UserPool not configured" on the production login page.
docker build --platform linux/amd64 --no-cache \
  --build-arg NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX \
  --build-arg NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx \
  --build-arg NEXT_PUBLIC_COGNITO_REGION=us-east-1 \
  --build-arg NEXT_PUBLIC_API_URL=https://api.pilotfortrades.com \
  --build-arg NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com \
  -f frontend/apps/web/Dockerfile \
  -t pilot-web:latest \
  frontend/
# TS-BUG-1: use --no-cache if the proxy.ts or middleware-related code changed
# to avoid stale Docker build cache layers that may have old env vars baked in.
#   docker build --platform linux/amd64 --no-cache ... (same args as above)

# ── Step 4: Tag and push ───────────────────────────────────────────────────────
docker tag pilot-web:latest "${ECR_BASE}/pilot/web:latest"
docker push "${ECR_BASE}/pilot/web:latest"

# ── Step 5: Force new deployment ──────────────────────────────────────────────
# this option uses the current version for deployment
AWS_REGION="us-east-1"
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-web \
  --force-new-deployment \
  --no-cli-pager \
  --region "$AWS_REGION"

# this option uses the "forced" version in the task-definition flag
AWS_REGION="us-east-1"
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-web \
  --task-definition pilot-production-web:8 \
  --force-new-deployment \
  --no-cli-pager \
  --region "$AWS_REGION"

echo "pilot-web redeployment triggered — takes ~2-3 min for health checks"

# ── Step 6: Wait and verify ────────────────────────────────────────────────────
AWS_REGION="us-east-1"
aws ecs wait services-stable \
  --cluster pilot-production \
  --services pilot-web \
  --region "$AWS_REGION"
echo "pilot-web is stable ✅"

curl -sf https://app.pilotfortrades.com/api/health
# Expected: {"status":"ok","service":"pilot-web"}
```

---

#### 8.3.1 Deploy Web Only

```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION="us-east-1"
ECR_BASE="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${ECR_BASE}"
cd <repo>
docker build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX \
  --build-arg NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx \
  --build-arg NEXT_PUBLIC_COGNITO_REGION=us-east-1 \
  --build-arg NEXT_PUBLIC_API_URL=https://api.pilotfortrades.com \
  -f frontend/apps/web/Dockerfile \
  -t pilot-web:latest \
  frontend/

docker tag pilot-web:latest "${ECR_BASE}/pilot/web:latest"
docker push "${ECR_BASE}/pilot/web:latest"

aws ecs update-service \
  --cluster pilot-production \
  --service pilot-web \
  --force-new-deployment \
  --no-cli-pager \
  --region "$AWS_REGION"
```

---

### 8.4 Deploy Marketing Site

The marketing site is a Next.js **static export** (`apps/marketing/out/`), hosted on S3 with CloudFront as CDN. No Docker image — just a static file sync.

```bash
# ── Step 1: Pull dynamic vars ──────────────────────────────────────────────────
CLOUDFRONT_DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, 'pilotfortrades.com')].Id" \
  --output text --region us-east-1)
MARKETING_BUCKET="pilot-production-marketing"

echo "CloudFront: $CLOUDFRONT_DIST_ID  |  Bucket: $MARKETING_BUCKET"

# ── Step 2: Build static export ───────────────────────────────────────────────
# Must build from the frontend folder within the pilot main folder
cd <repo>/frontend

NEXT_PUBLIC_CLOUDFLARE_TURNSTILE_SITE_KEY=0x4AAAAAADtbEEHD6Y-jXDbC \
NEXT_PUBLIC_API_URL=https://api.pilotfortrades.com \
NEXT_PUBLIC_CAREERS_OPEN_ROLES="AI / ML Engineer,Full-Stack Engineer (Trades Domain),Customer Success (Trades Background a Plus),Sales / Growth" \
pnpm --filter marketing run build
# Output: apps/marketing/out/
# return to the main pilot folder
cd <repo>

# ── Step 3: Sync static assets (long-lived cache — hashed filenames) ──────────
aws s3 sync apps/marketing/out/ "s3://${MARKETING_BUCKET}/" \
  --delete \
  --cache-control "max-age=31536000,public" \
  --exclude "*.html" \
  --region us-east-1

# ── Step 4: Sync HTML files (no-cache — content changes without hash change) ──
aws s3 sync apps/marketing/out/ "s3://${MARKETING_BUCKET}/" \
  --cache-control "no-cache" \
  --exclude "*" \
  --include "*.html" \
  --region us-east-1

# ── Step 5: Upload site-config.json ───────────────────────────────────────────
# Use "live" when ECS is running; "coming_soon" when ECS is at 0 tasks
aws s3 cp - "s3://${MARKETING_BUCKET}/site-config.json" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "application/json" \
  --region us-east-1 <<< '{"mode":"live"}'

# ── Step 6: Invalidate CloudFront cache ───────────────────────────────────────
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DIST_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' --output text)
echo "Invalidation started: $INVALIDATION_ID"

# ── Step 7: Poll until CloudFront invalidation completes (~2-5 min) ───────────
echo "Waiting for CloudFront propagation..."
aws cloudfront wait invalidation-completed \
  --distribution-id "$CLOUDFRONT_DIST_ID" \
  --id "$INVALIDATION_ID"
echo "CloudFront propagation complete ✅"

# ── Step 8: Verify ────────────────────────────────────────────────────────────
curl -sI https://pilotfortrades.com | head -3
# Expected: HTTP/2 200
```

---

## 9. Database Operations

> **⚠️ Port 5433 always — never 5432 for the PROD tunnel.**  
> Docker (local dev) owns `*:5432` when running. The SSH tunnel for PROD always uses local port **5433** to avoid conflicts.

### 9.1 Open SSH Tunnel for Direct DB Access (VS Code / psql)

Use this tunnel for **VS Code with the PostgreSQL extension**, DBeaver, or any direct SQL access. The tunnel maps your local `127.0.0.1:5433` → RDS `5432` through the bastion.

**The bastion must be running before opening a tunnel.** See §6 if it's stopped.

```bash
# ── Step 1: Get RDS endpoint dynamically ──────────────────────────────────────
RDS_EP=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text --region us-east-1)
echo "RDS endpoint: $RDS_EP"

# ── Step 2: Open SSH tunnel (background, non-blocking) ────────────────────────
# LOCAL port 5433 → RDS port 5432 (via bastion)
# Port 5433 is used because Docker owns localhost:5432 when running locally
ssh -f -N -L 5433:${RDS_EP}:5432 pilot-bastion
echo "Tunnel open: 127.0.0.1:5433 → ${RDS_EP}:5432"

# ── Step 3: Verify tunnel is active ───────────────────────────────────────────
nc -z 127.0.0.1 5433 && echo "Tunnel ready ✅" || echo "Tunnel failed ❌"

# ── Step 4: Get DB password from Secrets Manager ──────────────────────────────
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' \
  --output text \
  --region us-east-1 | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
# Password is in memory only — not written to disk or history

# ── VS Code PostgreSQL extension connection settings ──────────────────────────
echo ""
echo "VS Code PostgreSQL extension settings:"
echo "  Host:     127.0.0.1"
echo "  Port:     5433"
echo "  Database: pilot_prod"
echo "  Username: pilot_user"
echo "  Password: (fetched above — paste from \$DB_PASS)"

# ── Step 5: Quick psql verification ──────────────────────────────────────────
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT version();"

# ── Step 6: Close tunnel when done ────────────────────────────────────────────
pkill -f "5433:${RDS_EP}:5432"
echo "Tunnel closed"
```

> **VS Code PostgreSQL Extension tip**: Once the tunnel is open, add a new connection in VS Code with the settings above. The connection persists in VS Code's sidebar. To reconnect next time, just re-open the tunnel (steps 1–3) and click reconnect in VS Code — no need to re-enter credentials.

### Check / Kill Existing Tunnels

```bash
# List all open SSH tunnels
ps aux | grep "ssh -f -N -L" | grep -v grep

# Kill all port-forwarding SSH tunnels (clean slate)
pkill -f "ssh -f -N -L" && echo "All tunnels closed" || echo "No tunnels running"

# Kill only the RDS tunnel
RDS_EP=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text --region us-east-1)
pkill -f "5433:${RDS_EP}:5432"
```

#### `postgres-prod` MCP Server (Roo Code) — SSL Required

The `postgres-prod` MCP server (used by Roo Code agents for read-only prod verification) connects through this same tunnel. Two failure modes seen 2026-08-09 and their fixes:

1. **`no pg_hba.conf entry for host "10.0.x.x", user "mcp_readonly", database "pilot_prod", no encryption`** — RDS enforces SSL; the MCP connection string had no `sslmode`. Fix: the connection string in `.roo/mcp.json` must include an SSL parameter.
2. **`self-signed certificate in certificate chain`** — after adding `sslmode=require`, cert verification fails because the tunnel host is `127.0.0.1` while the cert belongs to the RDS endpoint. Fix: use `sslmode=no-verify` (encryption without cert verification — safe because the SSH tunnel itself is the secure transport).

Correct config in `.roo/mcp.json`:

```json
"postgres-prod": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-postgres",
    "postgresql://mcp_readonly:<password>@localhost:5433/pilot_prod?sslmode=no-verify"
  ]
}
```

The `mcp_readonly` role must exist with SELECT grants + default privileges — see §9.5.6b. Verify privileges any time with `admin-tools/audit_mcp_readonly_privs.sql`.

---

### 9.2 Run Alembic Migrations Against Production

**Always run migrations BEFORE forcing a new ECS deployment** when deploying code with schema changes.

```bash
# ── Prerequisites: bastion running + tunnel open on port 5433 ─────────────────
# See §9.1 above to open the tunnel first

# ── Step 1: Verify tunnel is ready ────────────────────────────────────────────
nc -z 127.0.0.1 5433 && echo "Tunnel ready ✅" || echo "Open tunnel first — see §9.1"

# ── Step 2: Get DB password ────────────────────────────────────────────────────
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' \
  --output text \
  --region us-east-1 | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# ── Step 3: Set DATABASE_URL pointing to tunnel port 5433 ─────────────────────
# Note: alembic.ini hardcodes dev db; migrations/env.py overrides when DATABASE_URL is set
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5433/pilot_prod"

# ── Step 4: Run migrations ─────────────────────────────────────────────────────
cd backend
.venv/bin/alembic upgrade head 2>&1 | tee /tmp/alembic-migration-prod.txt

# ── Step 5: Verify current revision ───────────────────────────────────────────
.venv/bin/alembic current
# Should show the latest migration hash (head)

# ── Step 6: Verify pgvector is installed ──────────────────────────────────────
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
# Expected: vector | 0.8.1 (or newer)

# ── Step 7: Post-migration seed verification ───────────────────────────────────
# seed_core.py / seed_platform.py are the authoritative source for Group A/B
# data. Re-run them (idempotent — ON CONFLICT DO NOTHING) to catch any drift,
# then spot-check counts. Full procedure: §9.6.
python migrations/scripts/seed_core.py
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_core.py --mode inspect

# ── Step 8: Clean up ──────────────────────────────────────────────────────────
unset DATABASE_URL
RDS_EP=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text --region us-east-1)
pkill -f "5433:${RDS_EP}:5432"
echo "Migrations complete. Tunnel closed."
```

---

### 9.3 Reset Database (no customer data — dev migrations only)

**⚠️ DESTRUCTIVE — only run when there is no customer data and you need a clean slate.**

```bash
# Open tunnel on port 5433 (see §9.1)
# Fetch password (see §9.2 step 2)

# Drop and recreate all schemas
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" << 'EOF'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO pilot_user;
DROP SCHEMA IF EXISTS audit CASCADE;
EOF

# Re-run migrations from scratch
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"
cd backend
.venv/bin/alembic upgrade head 2>&1 | tee /tmp/alembic-migration-prod-reset.txt
unset DATABASE_URL
echo "DB reset complete"
```

---

### 9.4 Run a Raw SQL Query Against Production

For ad-hoc queries, quick data checks, or seed data operations:

```bash
# Open tunnel (§9.1) and fetch password (§9.2 step 2) first, then:

PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT count(*) FROM tenant;"

# For multi-line queries:
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" << 'EOF'
SELECT
  t.name AS tenant,
  count(u.id) AS user_count,
  t.created_at
FROM tenant t
LEFT JOIN "user" u ON u.tenant_id = t.id
GROUP BY t.id, t.name, t.created_at
ORDER BY t.created_at DESC;
EOF
```

### 9.5 DB Backup & Restore (Dev → Prod Schema Sync)

Backups are stored in `archive/db-backups/` (gitignored). There are two subdirectories:
- `archive/db-backups/schema-only/` — schema-only dumps (no data), used for syncing the dev schema to prod
- `archive/db-backups/` (root) — full dev DB dumps (schema + data), used for point-in-time recovery

> **When to use this section**: when Alembic migrations are broken or the prod schema has drifted significantly behind dev, and you need to sync the prod schema from dev without running migrations. Also use it for routine dev DB backups before major changes.

#### 9.5.1 — Schema-only dump (dev → file)

Dumps the dev DB schema (tables, indexes, functions, triggers, extensions) **without any data**. Use this when you need to sync the prod schema from dev.

```bash
# From the repo root — dumps to archive/db-backups/schema-only/
mkdir -p archive/db-backups/schema-only
pg_dump -h localhost -U pilot_user -s -x -O pilot_dev \
  > archive/db-backups/schema-only/schema_dump_$(date +%Y%m%d_%H%M%S).sql
```

Flags:
- `-s` — schema only (no data)
- `-x` — no privileges/ownership (so it can be applied by a different user on prod)
- `-O` — no owner (same reason — prevents `ALTER OWNER` statements that would fail on prod)

#### 9.5.2 — Full dev DB dump (schema + data)

Dumps the entire dev DB including all seed data. Use this for point-in-time backups before major changes.

```bash
# From the repo root — dumps to archive/db-backups/
pg_dump -h localhost -U pilot_user -d pilot_dev \
  > archive/db-backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 9.5.3 — Wipe prod DB (before applying a fresh schema)

> ⚠️ **Destructive** — drops ALL tables, functions, and extensions on prod. Only do this when there is no prod data to preserve. The prod RDS instance has `deletion_protection = true` (the instance itself is safe), but this drops everything **inside** the database.

##### 9.5.3a - Wipe using command line

```bash
# Prerequisites: bastion running + SSH tunnel open on port 5433 (see §9.1)
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# Drop all tables, functions, and extensions (cascade)
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" << 'EOF'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO pilot_user;
GRANT ALL ON SCHEMA public TO public;
EOF
```

##### 9.5.3b - Wipe using VS Code PostgreSQL Extension

**Prerequisites:**
- bastion running
- SSH tunnel open on port 5433 (see §9.1)
- VS Code PostgreSQL extension connected to prod (see §9.1 connection settings)

Open a new query in the VS Code PostgreSQL extension (connected to `pilot_prod`) and run:

```sql
-- ⚠️ Destructive — drops ALL tables, functions, and extensions in the public schema.
-- DROP SCHEMA CASCADE also drops the pgvector extension if installed in public.
-- Re-enable pgvector after applying the schema (see §9.5.5).
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO pilot_user;
GRANT ALL ON SCHEMA public TO public;
```

> **Verify the wipe**: run `SELECT count(*) FROM pg_tables WHERE schemaname = 'public';` — should return `0`.

#### 9.5.4 — Apply dev schema dump to prod

Restores the schema-only dump (from §9.5.1) onto the wiped prod DB.

##### 9.5.4a - Apply using command line

```bash
# Prerequisites: tunnel open on 5433 + schema dump file from §9.5.1
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

SCHEMA_DUMP="archive/db-backups/schema-only/schema_dump_20260730_115152.sql"

PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -f "$SCHEMA_DUMP"
```

##### 9.5.4b - Apply using VS Code PostgreSQL extension

**Prerequisites:**
- bastion running
- SSH tunnel open on port 5433 (see §9.1)
- VS Code PostgreSQL extension connected to prod (see §9.1 connection settings)
- Schema dump file from §9.5.1 (e.g. `archive/db-backups/schema-only/schema_dump_YYYYMMDD_HHMMSS.sql`)

The VS Code PostgreSQL extension can run a `.sql` file directly against the connected database:

1. In VS Code, open the schema dump file: `File → Open File → archive/db-backups/schema-only/schema_dump_YYYYMMDD_HHMMSS.sql`
2. In the VS Code PostgreSQL extension sidebar, ensure you're connected to the **prod** database (`pilot_prod` on `127.0.0.1:5433`)
3. Right-click in the open `.sql` file editor → **Run Query** (or `Cmd+Shift+E` / the "Execute" button)
   - The extension runs the entire file against the connected database
4. Watch the output panel for errors — a clean run shows no errors (warnings about `ALTER OWNER` are OK if the dump used `-O`)

> **Alternative if the file is too large**: the VS Code extension may struggle with very large `.sql` files. In that case, use the command-line approach (§9.5.4a) instead — `psql -f` handles large files reliably.

> **Verify the apply**: after running, execute this query in the extension to confirm tables were created:
> ```sql
> SELECT count(*) FROM pg_tables WHERE schemaname = 'public';
> SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public';
> ```
> Then verify pgvector (see §9.5.5).

#### 9.5.5 — Verify pgvector extension on prod

After applying the schema dump, verify the `vector` extension is enabled (required for AI/embedding features):

```bash
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

If the extension is missing, install it (see [`postgresql-ext-setup-to-prod.md`](postgresql-ext-setup-to-prod.md)):

```bash
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 9.5.5b — Stamp alembic version on prod

The schema-only dump (`pg_dump -s`) creates the `alembic_version` table but does **not** insert the current revision row. Without stamping, a future `alembic upgrade head` would try to replay all migrations from scratch (which would fail — tables already exist).

```bash
# Prerequisites: tunnel open on 5433 + schema applied (§9.5.4) + pgvector verified (§9.5.5)
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"

cd backend
source .venv/bin/activate

# Stamp the current head revision without running any migrations
alembic stamp head

# Verify
alembic current
# Should show: 44b3427a0e57 (head)

# Also verify via SQL
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT version_num FROM alembic_version;"
# Should show: 44b3427a0e57
```

#### 9.5.6 — Run seed scripts against prod

After the schema is applied, run the **Group A + Group B** seed scripts only (lookup tables + platform config). These are idempotent — every INSERT uses `ON CONFLICT DO NOTHING`, so they are safe to run on a populated DB.

> ⚠️ **Do NOT run Group C (`seed_test_tenant.py`) or Group D (`seed_scenario_*.py`) against prod.** Those create a test tenant, synthetic users, and demo scenario data (customers, jobs, quotes, SMS threads). Prod tenants arrive via the signup flow, not seed scripts. See [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §3 for the Data Group Model.

```bash
# Prerequisites: tunnel open on 5433 + schema applied (see §9.5.5)
# Set DATABASE_URL to the prod tunnel for the seed scripts
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"

# Run Group A + B seed scripts (from backend/ dir)
cd backend
source .venv/bin/activate
python migrations/scripts/seed_core.py        # Group A: 34+ lookup tables
python migrations/scripts/seed_platform.py     # Group B: product plans + subscription statuses + notification templates

# Verify Group A + B data (NOT tenant/tenant_user_role — those are Group C, not seeded in prod)
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT count(*) AS subscription_tiers FROM subscription_tier;
      SELECT count(*) AS product_plans FROM product_plan;
      SELECT count(*) AS notification_templates FROM notification_template;
      SELECT count(*) AS job_statuses FROM job_status;
      SELECT count(*) AS quote_statuses FROM quote_status;"
```

> ⚠️ **Migration-embedded seed data is NOT restored by a schema-only dump + `alembic stamp`** (discovered in the 2026-08-09 prod sync). Older migrations contain seed INSERTs (e.g. `f7f30492c3e4` platform settings, `b1bd90914b77` communication templates) that never execute on a stamped DB. The seed scripts are the recovery path and must own every Group A/B row — after running them, verify the counts below AND diff `platform_setting_catalog` / `platform_setting` / `communication_template` against dev. Going forward, new lookup/platform seed rows belong in the seed scripts (Architect rule §11.5), not embedded in migrations.

**Expected counts** (Group A + B only, verified 2026-08-09):

| Table | Rows |
|:---|---:|
| `subscription_tier` | 4 |
| `product_plan` | 3 |
| `notification_template` | 30 |
| `notification_type` | 10 |
| `job_status` | 5 |
| `quote_status` | 10 |
| `platform_setting_catalog` | 48 |
| `platform_setting` (tenant_id NULL) | 48 |
| `communication_template` | 17 |

If any count is 0, the corresponding seed script failed — check its stdout for errors. The authoritative expected-counts list is [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §4 — keep this table in sync with it.

#### 9.5.6b — Recreate `mcp_readonly` role + default privileges

A schema-only `pg_dump` restore does **not** carry roles or grants. If the `mcp_readonly` role was dropped (or default privileges are missing), the `postgres-prod` MCP server fails even with a healthy tunnel. Run this after every §9.5 schema-restore workflow:

```bash
# Check whether the role exists and what it can read
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -f admin-tools/audit_mcp_readonly_privs.sql
# Checks: role exists + CONNECT, schema USAGE, per-table SELECT coverage,
# and default privileges for future tables.

# If the role is missing or grants are incomplete, recreate as pilot_user:
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" << 'EOF'
CREATE ROLE mcp_readonly LOGIN PASSWORD '<strong-password>' CONNECTION LIMIT 5;
GRANT CONNECT ON DATABASE pilot_prod TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT USAGE ON SCHEMA audit TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO mcp_readonly;
-- Critical: future tables created by later migrations stay readable
ALTER DEFAULT PRIVILEGES FOR ROLE pilot_user IN SCHEMA public
  GRANT SELECT ON TABLES TO mcp_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE pilot_user IN SCHEMA audit
  GRANT SELECT ON TABLES TO mcp_readonly;
EOF
```

> **Why the `ALTER DEFAULT PRIVILEGES` lines matter**: without them, every future table-creating migration silently breaks MCP reads on the new tables until grants are re-run.

#### 9.5.7 - Alembic Migration

```bash
# Prerequisites: tunnel open on 5433 + schema applied (see §9.5.5)
# Set DATABASE_URL to the prod tunnel for the seed scripts
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"

# Run alembic migrations
cd backend
source .venv/bin/activate

# Run the triple verify process
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current
```

#### 9.5.8 — Full workflow: sync dev schema to prod (clean slate)

Complete end-to-end procedure when prod needs a fresh schema from dev (no data to preserve):

```bash
# 1. Open the prod tunnel (see §9.1)
RDS_EP=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text --region us-east-1)
ssh -f -N -L 5433:${RDS_EP}:5432 pilot-bastion

# 2. Dump the dev schema
mkdir -p archive/db-backups/schema-only
pg_dump -h localhost -U pilot_user -s -x -O pilot_dev \
  > archive/db-backups/schema-only/schema_dump_$(date +%Y%m%d_%H%M%S).sql

# 3. Fetch the prod password
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' --output text --region us-east-1 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# 4. Wipe prod
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" << 'EOF'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO pilot_user;
GRANT ALL ON SCHEMA public TO public;
EOF

# 5. Apply the dev schema dump
SCHEMA_DUMP=$(ls -t archive/db-backups/schema-only/schema_dump_*.sql | head -1)
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -f "$SCHEMA_DUMP"

# 6. Verify pgvector
PGPASSWORD="$DB_PASS" psql \
  "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

# 7. Stamp alembic version (schema-only dump creates the table but not the version row)
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"
cd backend
source .venv/bin/activate
alembic stamp head
alembic current  # Should show: 44b3427a0e57 (head)

# 8. Run seed scripts (Group A + B only — NOT seed_test_tenant or seed_scenario_*)
python migrations/scripts/seed_core.py        # Group A: lookup tables
python migrations/scripts/seed_platform.py     # Group B: plans + statuses + notification templates
python migrations/scripts/seed_core.py --mode inspect   # verify — see §9.5.6 expected counts

# 8b. Recreate mcp_readonly role + default privileges (schema restore drops grants)
# See §9.5.6b — required for the postgres-prod MCP server to work

# 9. Close the tunnel when done
pkill -f "5433:${RDS_EP}:5432"
```

### 9.6 Run Seed Scripts Against Production

Standalone procedure for syncing Group A (lookup) + Group B (platform config) seed data to prod — e.g. after a migration batch that added seed rows, or to repair drift. The scripts are idempotent (`ON CONFLICT DO NOTHING`), safe on a populated DB.

> ⚠️ **Group A + B only.** Never run `seed_test_tenant.py` (Group C) or `seed_scenario_*.py` (Group D) against prod. See [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §3.

> **DB-MGMT-1 / ADR-0016 (2026-08-18):** The env-aware seed system is now live. For the full per-env provisioning runbook, migration-sync runbook, and environment-value matrix, see [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §7.5–§7.7. The prod converge orchestrator (`seed_prod_db.py`) replaces the manual `seed_core.py` + `seed_platform.py` commands below — it adds typed confirmation (`PILOT-PROD-SEED`), Stripe key preflight, and `--stripe-mode` enforcement. The manual procedure below remains valid for ad-hoc converge.

```bash
# ── Prerequisites: bastion running + tunnel open on port 5433 (see §9.1) ──────
nc -z 127.0.0.1 5433 && echo "Tunnel ready ✅" || echo "Open tunnel first — see §9.1"

# ── Step 1: Get DB password ────────────────────────────────────────────────────
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' \
  --output text \
  --region us-east-1 | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# ── Step 2: Set DATABASE_URL pointing to tunnel port 5433 ─────────────────────
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@localhost:5433/pilot_prod"

# ── Step 3: Run the seed scripts ───────────────────────────────────────────────
cd backend
source .venv/bin/activate
python migrations/scripts/seed_core.py        # Group A: lookup tables
python migrations/scripts/seed_platform.py     # Group B: plans + statuses + notification templates

# ── Step 4: Verify ─────────────────────────────────────────────────────────────
python migrations/scripts/seed_core.py --mode inspect
# Spot-check counts against the §9.5.6 expected-counts table
# (authoritative list: backend/README-seed-data.md §4)

# ── Step 5: Clean up ───────────────────────────────────────────────────────────
unset DATABASE_URL
echo "Seed sync complete."
```

---

### 9.7 Prod Migration Sync — Full Workflow (Dev ↔ Prod Version Parity)

End-to-end procedure for bringing prod to the same Alembic head as dev using real migrations (the preferred path — the §9.5 schema-restore is the fallback for broken/drifted migration chains). First used 2026-08-09 to sync prod `990231f963b0` → dev head `7f57c3f5f15c` (9 migrations).

**Step 1 — Get the current revision from each DB:**

```bash
# Dev (local Docker DB)
cd backend && source .venv/bin/activate
alembic current    # dev revision

# Prod (tunnel on 5433 + DB_PASS from §9.2 step 2)
export DATABASE_URL="postgresql://pilot_user:${DB_PASS}@127.0.0.1:5433/pilot_prod"
alembic current    # prod revision
alembic heads      # the target head
unset DATABASE_URL
```

**Step 2 — Have the Architect analyze the pending chain before running anything.** Give the Pilot Architect this prompt:

> Our alembic versions are out of sync. dev: `<dev-head>`, prod: `<prod-rev>`. Inventory the migration chain between them (revision order, single/multiple heads), risk-review each pending migration (data-affecting UPDATEs, NOT NULL additions, new tables, embedded seed INSERTs), confirm downgrades exist, and tell me whether it's safe to run `alembic upgrade head` against prod.

The Architect reads the migration files directly and flags anything data-affecting (e.g. PK renames, tier pricing updates) so you know what the migration will change before it runs.

**Step 3 — Back up prod.** Take an RDS manual snapshot (fastest, point-in-time recoverable):

```bash
aws rds create-db-snapshot \
  --db-instance-identifier pilot-production \
  --db-snapshot-identifier "pilot-prod-pre-migration-$(date +%Y%m%d-%H%M)" \
  --region us-east-1
```

**Step 4 — Run the migration** per §9.2 (tunnel → `DATABASE_URL` → `alembic upgrade head` → verify `alembic current` shows the dev head).

**Step 5 — Post-migration seed verification** per §9.2 Step 7 / §9.6: re-run `seed_core.py` + `seed_platform.py` (idempotent) and spot-check counts.

**Step 6 — Validate app health** (migrations run BEFORE redeploying the API): confirm ECS services are stable, then run the Tier 1 test gate after the redeploy. After the redeploy, run the full §19.6 service sync + deploy canary — the migration-verify step in §19.6 references this workflow as its prerequisite.

---

### 9.8 Remove a Test / Abandoned Signup (Prod)

**When**: A signup wizard run needs a clean redo (E2E testing, abandoned partial signup). **Scope warning**: this procedure covers signups that stopped **before wizard completion** (no Stripe subscription, no business data). If the signup COMPLETED (steps 4–5 ran: Stripe customer/subscription, charter number, seeded defaults), **STOP — escalate to the Architect**; the blast radius includes Stripe objects and tenant business data.

> ⚠️ **Deleting `tenant_signup` alone is never sufficient** — it leaves FK-referencing orphans (`tenant_user`, `user_endpoint`, consent audit, `user`, `tenant`) and a stranded Cognito account.

**Step 0 — Set the tenant ID once (server-side session variable).** Uses `SET` + `current_setting()` — plain SQL that works **identically in psql, the VS Code PostgreSQL extension, and DataGrip** (do NOT use psql `\set`/`\gset` backslash commands — GUI clients misread `:name` as bind parameters and prompt for values). The variable lives for the duration of your connection/session, so run all steps in the same window/connection.

```sql
-- get the tenant ID that you want to delete first
select * from public.tenant_signup;
```

```sql
-- Set once per cleanup; everything downstream reads it via current_setting()
SET app.cleanup_tid = '<tenant_signup_id>';   -- ← the tenant_signup.tenant_id to remove
```

**Step 1 — Identify the signup and confirm it is pre-completion:**

```sql
SELECT ts.tenant_id, ts.signup_state, ts.signup_completed_at, t.name, t.is_active
FROM public.tenant_signup ts JOIN public.tenant t ON t.id = ts.tenant_id
WHERE ts.tenant_id = current_setting('app.cleanup_tid')::uuid;
-- Safe to proceed only if signup_completed_at IS NULL.
```

**Step 2 — Map the blast radius.** Capture the user_id from the result row manually into a second variable (one value to copy — shown in the result grid):

```sql
SELECT tu.user_id, u.email FROM public.tenant_user tu
JOIN public."user" u ON u.id = tu.user_id
WHERE tu.tenant_id = current_setting('app.cleanup_tid')::uuid;
-- Confirm this is the account you expect, then set the user id:
SET app.cleanup_uid = '<paste user_id from the row above>';   -- single quotes, not backticks

-- All of these must return 0 (completed signups will NOT):
SELECT 'subscription' AS tbl, count(*) FROM public.subscription WHERE tenant_id = current_setting('app.cleanup_tid')::uuid
UNION ALL SELECT 'customer', count(*) FROM public.customer WHERE tenant_id = current_setting('app.cleanup_tid')::uuid
UNION ALL SELECT 'notification_preference', count(*) FROM public.notification_preference WHERE tenant_id = current_setting('app.cleanup_tid')::uuid
UNION ALL SELECT 'tenant_legal_acceptance', count(*) FROM public.tenant_legal_acceptance WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;
-- NOTE: tenant_legal_acceptance is EXPECTED to be >0 (legal-docs step) — it's in the delete list.
-- The others must be 0.
```

**Step 3 — Delete in FK-safe order** (single transaction; any FK violation → STOP, report the constraint name). **If you see "transaction is currently aborted"**: a statement inside the txn already failed and the client showed only the tail — issue `ROLLBACK;`, then re-run the deletes **one at a time** to surface the real error. Known blocker discovered 2026-08-09: `tenant_legal_acceptance` rows (legal-docs step, RESTRICT FKs to tenant + user) — covered by the third delete below.

> ⚠️ The `SET LOCAL session_replication_role = 'replica'` line is **required**: the `guard_user_endpoint_primary_email_fn` trigger otherwise blocks deleting the user's last primary email endpoint ("Cannot delete the only primary email endpoint for this user"). That guard exists to protect live accounts; a full teardown intentionally bypasses it. This is the same bypass pattern the Alembic data migrations use. (Requires the `pilot_user` role's trigger-bypass privilege — if you get `permission denied to set parameter`, run via the RDS master user or ask the Architect.) **`SET LOCAL` is transaction-scoped**: at `COMMIT` (or `ROLLBACK`), `session_replication_role` automatically reverts to the session default (`origin`, all triggers enabled) — nothing is left disabled. Keep the transaction limited to exactly these deletes, since the bypass suppresses ALL triggers while it's active.

```sql
BEGIN;
SET LOCAL session_replication_role = 'replica';   -- bypass app guard triggers for this txn only
DELETE FROM public.user_sms_consent_audit WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;
DELETE FROM public.user_endpoint        WHERE user_id   = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.tenant_legal_acceptance WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;  -- legal-docs acceptances (RESTRICT FK to tenant + user)
DELETE FROM public.tenant_user          WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;
DELETE FROM public.tenant_signup        WHERE tenant_id = current_setting('app.cleanup_tid')::uuid;
DELETE FROM public."user"               WHERE id        = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.tenant               WHERE id        = current_setting('app.cleanup_tid')::uuid;
COMMIT;
```

**Audit note**: with the trigger bypass active, these deletes are **not** recorded in `audit_log` (the `audit.log_changes` triggers are suppressed along with the guard). Acceptable for a test-account teardown; for any real-customer scenario, escalate instead of deleting.

**Step 4 — Delete the Cognito user** (or the next signup with the same email resolve-or-attaches to a Cognito account with no RDS row behind it):

```bash
# Use the email returned by the Step 2 lookup query
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username <email-from-step-2> --region us-east-1
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username owner@example.com --region us-east-1
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username owner@example.com --region us-east-1
```

**Alternative to deletion**: an abandoned signup can usually be **resumed** — the wizard state machine (`tenant_signup.signup_state`) supports re-entry, and `POST /api/v1/signup/{tenant_id}/phone/send-optin` re-fires the SMS double opt-in for an `opted_in`/`pending` endpoint. Delete only when a clean full-wizard rerun is the goal.

> First used 2026-08-09 (pre-Step-3 SMS test cleanup, tenant `fa5af0b9-…`, stopped at `step3_phone` — 6 rows + Cognito user).

---

### 9.9 Remove an Invited Employee (Prod) — Invite-Accept Teardown for Email Reuse

**When**: an invite was **accepted** end-to-end (Cognito `SignUp` → Lambda Path 2 attach) and the email must be freed for a fresh invite — e.g. re-running the TEAM-INVITE prod smoke with the same inboxes. **Scope**: removes the invitee's `user` / `tenant_user` / `user_endpoint` rows, the accepted `tenant_user_invite` row, the Cognito pool entry, and corrects `tenant_subscription_usage.current_user_count` (−1). The tenant, the owner, and all business data stay untouched.

> ⚠️ **Test accounts only.** The Step-2 blast-radius query must show the user owns **zero** rows outside the Lambda-created trio (`user_endpoint`, `tenant_user`) and the auth/session/MFA tables. Any business-data row (jobs, time entries, expenses, assignments…) → **STOP — escalate to the Architect**; deleting a working employee corrupts audit + business history.
>
> **Pending (unaccepted) invites don't need this procedure** — Revoke from Settings → Team and re-invite (the 2026-09-03 hot-fix made revoked-email re-invite an upsert). Only an *accepted* invite pins the email via the `user` row + Cognito account.

**Step 0 — Set variables once per session** (same `SET` + `current_setting()` pattern as §9.8 — one invitee per run, all steps in one connection):

**TOM - NOTE:** All of the below SQL and CLI is located in: <repo>/dev-docs/devops/aws-ops-runbook-sect-9.9.sql
**Use**: You can just use the SQL file as it is easier to run.

```sql
-- ① Look up both IDs from the invitee email (run this first, paste the values below):
SELECT u.id AS user_id, tu.tenant_id, t.name AS tenant_name, tu.role_code
FROM public."user" u
JOIN public.tenant_user tu ON tu.user_id = u.id
JOIN public.tenant t ON t.id = tu.tenant_id
WHERE u.email = '<invitee email>';

-- ② Set once per cleanup; everything downstream reads them via current_setting()
SET app.cleanup_uid   = '<user_id from the query above>';
SET app.cleanup_email = '<invitee email>';
SET app.cleanup_tid   = '<tenant_id from the query above>';
```

**Step 1 — Confirm the attach + capture the Cognito username:**

```sql
SELECT u.id, u.email, tu.role_code, tu.joined_at
FROM public."user" u JOIN public.tenant_user tu ON tu.user_id = u.id
WHERE u.id = current_setting('app.cleanup_uid')::uuid
  AND tu.tenant_id = current_setting('app.cleanup_tid')::uuid;
-- Expect exactly 1 row. The email column is the Cognito --username for Step 5.
```

**Step 2 — Blast radius.** Expect `tenant_user` = 1, `user_endpoint` = 1, everything else 0 (auth/MFA/session rows may be >0 if the account logged in — those are in the Step-3 delete list). **STOP on any business-table row.**

```sql
WITH me AS (SELECT current_setting('app.cleanup_uid')::uuid AS uid)
SELECT 'user_endpoint' AS tbl, count(*) FROM public.user_endpoint WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'tenant_user', count(*) FROM public.tenant_user WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_mfa_method', count(*) FROM public.user_mfa_method WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_mfa_recovery_code', count(*) FROM public.user_mfa_recovery_code WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'mfa_grace_period_tracking', count(*) FROM public.mfa_grace_period_tracking WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'auth_refresh_token', count(*) FROM public.auth_refresh_token WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'auth_password_history', count(*) FROM public.auth_password_history WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'auth_api_token', count(*) FROM public.auth_api_token WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'auth_password_reset', count(*) FROM public.auth_password_reset WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'auth_email_verification', count(*) FROM public.auth_email_verification WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'auth_mfa_otp', count(*) FROM public.auth_mfa_otp WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_session_history', count(*) FROM public.user_session_history WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_session_metadata', count(*) FROM public.user_session_metadata WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_preference', count(*) FROM public.user_preference WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_setting_override', count(*) FROM public.user_setting_override WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_dashboard_widget', count(*) FROM public.user_dashboard_widget WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'user_sms_consent_audit', count(*) FROM public.user_sms_consent_audit WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'notification_preference', count(*) FROM public.notification_preference WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'in_app_notification', count(*) FROM public.in_app_notification WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'notification_outbox', count(*) FROM public.notification_outbox WHERE recipient_user_id = (SELECT uid FROM me)
UNION ALL SELECT 'tenant_legal_acceptance', count(*) FROM public.tenant_legal_acceptance WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'conversation_session', count(*) FROM public.conversation_session WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'help_chat_session', count(*) FROM public.help_chat_session WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'idempotency_key', count(*) FROM public.idempotency_key WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'job_tech_assignment', count(*) FROM public.job_tech_assignment WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'job_time_entry', count(*) FROM public.job_time_entry WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'job_expense', count(*) FROM public.job_expense WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'tech_availability', count(*) FROM public.tech_availability WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'loto_confirmation', count(*) FROM public.loto_confirmation WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'mobile_sync_session', count(*) FROM public.mobile_sync_session WHERE user_id = (SELECT uid FROM me)
UNION ALL SELECT 'mobile_device_push_token', count(*) FROM public.mobile_device_push_token WHERE user_id = (SELECT uid FROM me)
ORDER BY tbl;
```

**Step 3 — Delete in FK-safe order** (single transaction; any FK violation → STOP, report the constraint name). Same trigger-bypass requirement as §9.8: `guard_user_endpoint_primary_email_fn` otherwise blocks deleting the only primary email endpoint. `SET LOCAL` is transaction-scoped — nothing stays disabled after COMMIT.

```sql
BEGIN;
SET LOCAL session_replication_role = 'replica';
DELETE FROM public.user_mfa_method           WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.user_mfa_recovery_code    WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.mfa_grace_period_tracking WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.auth_refresh_token        WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.auth_password_history     WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.auth_api_token            WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.auth_password_reset       WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.auth_email_verification   WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.auth_mfa_otp              WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.user_session_history      WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.user_session_metadata     WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.user_endpoint             WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.tenant_user               WHERE user_id = current_setting('app.cleanup_uid')::uuid;
DELETE FROM public.tenant_user_invite        WHERE tenant_id = current_setting('app.cleanup_tid')::uuid
  AND email = current_setting('app.cleanup_email');
DELETE FROM public."user"                    WHERE id = current_setting('app.cleanup_uid')::uuid;
UPDATE public.tenant_subscription_usage
   SET current_user_count = GREATEST(current_user_count - 1, 0), updated_at = now()
 WHERE tenant_id = current_setting('app.cleanup_tid')::uuid AND period_end >= now();
COMMIT;
```

**Audit note**: same as §9.8 — with the trigger bypass these deletes are **not** recorded in `audit_log`. Acceptable for test accounts; never use for a real customer employee.

**Step 4 — Verify the email is free (DB side):**

```sql
SELECT count(*) FROM public."user" WHERE email = current_setting('app.cleanup_email');               -- 0
SELECT count(*) FROM public.tenant_user_invite WHERE email = current_setting('app.cleanup_email');   -- 0
```

**Step 5 — Delete the Cognito user** (mandatory both directions: skip this and the fresh `SignUp` hits `UsernameExistsException`; delete Cognito but not the DB rows and the Path-2 attach fails on the `user.email` unique constraint — swallowed by the never-raise invariant, stranding a confirmed Cognito user with no RDS rows):

```bash
USER_EMAIL="owner@example.com"
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username $USER_EMAIL --region us-east-1
```

**Step 6 — Verify the Cognito delete** (`admin-get-user` on a deleted user exits non-zero with `UserNotFoundException`; any other outcome means the delete didn't take — do NOT proceed to a fresh invite until this prints OK):

```bash
USER_EMAIL="owner@example.com"
aws cognito-idp admin-get-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username $USER_EMAIL --region us-east-1 2>&1 \
  | grep -q "UserNotFoundException" \
  && echo "OK: $USER_EMAIL is gone from the pool" \
  || echo "STILL EXISTS or lookup errored — investigate before re-inviting"
```

> First used 2026-09-04 (TEAM-INVITE smoke re-run prep, Lang Electric, the author's test tenant): removed technician `owner@example.com` + office_staff `admin@example.com` (2 accepted invites; usage counter 2 → 0; 2 Cognito users) — both accounts had zero rows outside the Lambda-created trio.

---

### Redis Tunnel (for redis-cli debugging)

```bash
REDIS_EP=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id pilot-production \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text --region us-east-1)
echo "Redis endpoint: $REDIS_EP"

# Open tunnel (local 6380 → Redis 6379, avoiding local Redis on 6379)
ssh -f -N -L 6380:${REDIS_EP}:6379 pilot-bastion
echo "Redis tunnel: 127.0.0.1:6380"

# Connect
redis-cli -h 127.0.0.1 -p 6380
# Inside redis-cli: KEYS * | INFO keyspace

# Close
pkill -f "6380:${REDIS_EP}:6379"
```

---

## 10. AWS Secrets Manager — Audit and Update

All production secrets live under the `pilot/prod/` prefix. This section shows how to list, read, and update them.

### 10.1 List All Pilot Secrets

```bash
# List all secrets with their status
aws secretsmanager list-secrets \
  --filters Key=name,Values="pilot/prod/" \
  --query 'SecretList[*].{Name:Name,Description:Description,LastChanged:LastChangedDate}' \
  --output table \
  --region us-east-1
```

Expected output — all 11 secrets should be listed:

| Secret Name | Contents | Expected Status |
|---|---|---|
| `pilot/prod/db` | DB credentials + URL (auto-populated by Terraform) | ✅ Populated |
| `pilot/prod/redis` | Redis connection URLs for DB 0, 1, 2 | ✅ Populated |
| `pilot/prod/cognito` | `region`, `user_pool_id`, `app_client_id` | ✅ Populated |
| `pilot/prod/sendgrid` | `api_key`, `from_email` | ✅ Populated |
| `pilot/prod/telnyx` | `api_key`, `messaging_profile_id`, `public_key`, `platform_sms_number` | ✅ Populated |
| `pilot/prod/encryption` | Fernet encryption key | ✅ Populated |
| `pilot/prod/google-maps` | Distance Matrix API key | ✅ Populated |
| `pilot/prod/turnstile` | Cloudflare Turnstile server-side secret key | ✅ Populated |
| `pilot/prod/gpu` | `whisper_url`, `ollama_url` | ⚠️ Populate after GPU starts |
| `pilot/prod/quickbooks` | Production QB app credentials | ⚠️ Pending Intuit prod app |
| `pilot/prod/stripe` | Live mode keys + webhook secret | ✅ Active (August 4, 2026 — C-B3) |

---

### 10.2 Read a Secret Value

```bash
# Read any secret — returns the full JSON value
aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/stripe" \
  --query 'SecretString' \
  --output text \
  --region us-east-1 | python3 -m json.tool

# Read a single field from a secret
aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/db" \
  --query 'SecretString' \
  --output text \
  --region us-east-1 | python3 -c "import sys,json; print(json.load(sys.stdin)['host'])"

# Quick audit — check all pilot/prod secrets exist and have a current version
for secret in pilot/prod/db pilot/prod/redis pilot/prod/cognito pilot/prod/sendgrid \
              pilot/prod/telnyx pilot/prod/encryption pilot/prod/google-maps \
              pilot/prod/turnstile pilot/prod/gpu pilot/prod/quickbooks pilot/prod/stripe; do
  STATUS=$(aws secretsmanager describe-secret \
    --secret-id "$secret" \
    --query 'length(SecretVersionsToStages)' \
    --output text \
    --region us-east-1 2>/dev/null && echo "✅ EXISTS" || echo "❌ MISSING")
  echo "$secret: $STATUS"
done
```

---

### 10.3 Update a Secret Value

```bash
# Read all of the stripe secrets to start
aws secretsmanager get-secret-value --secret-id "pilot/prod/stripe" --query 'SecretString' --output text --region us-east-1

# Update a single secret entirely (but you need to replace all fields)
# NOT ALLOWED to insert \ characters inside of a '' string
aws secretsmanager put-secret-value \
  --secret-id "pilot/prod/stripe" \
  --secret-string '{ "publishable_key":"<existing/new>",
  "secret_key":"<existing/new>",
  "webhook_secret":"<existing/new>",
  "connect_platform_key":"<existing/new>",
  "connect_webhook_secret":"<existing/new>" }' \
  --region us-east-1

# Add or update a single field in an existing secret (preserves other fields)
# Step 1: Get current value
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/telnyx" \
  --query 'SecretString' --output text --region us-east-1)

# Step 2: Merge the new field using python3
UPDATED=$(echo "$CURRENT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
d['api_key'] = 'NEW_KEY_VALUE_HERE'
print(json.dumps(d))
")

# Step 3: Write back
aws secretsmanager put-secret-value \
  --secret-id "pilot/prod/telnyx" \
  --secret-string "$UPDATED" \
  --region us-east-1
echo "pilot/prod/telnyx api_key updated"

# After updating any secret referenced by ECS, force a new deployment:
aws ecs update-service --cluster pilot-production --service pilot-api \
  --force-new-deployment --no-cli-pager --region us-east-1
```
---

#### 10.3.1 Adding a Key to an Existing Secret

```bash
# Get the telnyx secret key value
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id "pilot/prod/telnyx" \
  --query 'SecretString' --output text --region us-east-1)

# Add a new key value to the secret value to create the secret-string
UPDATED=$(echo "$CURRENT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
d['platform_sms_number'] = '+15555550100'
print(json.dumps(d))
")

# Add a new key value to the secret, in this case the `platform_sms_number`
aws secretsmanager put-secret-value \
  --secret-id "pilot/prod/telnyx" \
  --secret-string "$UPDATED" \
  --region us-east-1
echo "pilot/prod/telnyx platform_sms_number added"
```

---

### 10.4 Full Secrets Audit Checklist

Run this before beta launch to verify all secrets are populated with real (not placeholder) values:

```bash
#!/bin/bash
# Full secrets audit — run before beta launch
REGION="us-east-1"

echo "=== Pilot Production Secrets Audit ==="
echo ""

check_secret() {
  local secret_id="$1"
  local expected_key="$2"
  local description="$3"

  VALUE=$(aws secretsmanager get-secret-value \
    --secret-id "$secret_id" \
    --query 'SecretString' --output text \
    --region "$REGION" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('${expected_key}', 'MISSING'))" 2>/dev/null)

  if [ "$VALUE" = "MISSING" ] || [ -z "$VALUE" ]; then
    echo "❌ $secret_id ($description): MISSING or empty"
  elif [[ "$VALUE" == *"placeholder"* ]] || [[ "$VALUE" == *"PLACEHOLDER"* ]] || [[ "$VALUE" == *"localhost"* ]]; then
    echo "⚠️  $secret_id ($description): PLACEHOLDER value — needs real value"
  else
    echo "✅ $secret_id ($description): populated"
  fi
}

check_secret "pilot/prod/db" "host" "RDS connection"
check_secret "pilot/prod/db" "password" "RDS password"
check_secret "pilot/prod/redis" "broker_url" "Redis Celery broker"
check_secret "pilot/prod/cognito" "user_pool_id" "Cognito pool"
check_secret "pilot/prod/sendgrid" "api_key" "SendGrid API key"
check_secret "pilot/prod/telnyx" "api_key" "Telnyx API key"
check_secret "pilot/prod/encryption" "fernet_key" "Fernet encryption key"
check_secret "pilot/prod/google-maps" "api_key" "Google Maps API key"
check_secret "pilot/prod/turnstile" "secret_key" "Cloudflare Turnstile"
check_secret "pilot/prod/gpu" "whisper_url" "GPU Whisper URL"
check_secret "pilot/prod/quickbooks" "client_id" "QuickBooks client ID"
check_secret "pilot/prod/stripe" "secret_key" "Stripe secret key"

echo ""
echo "=== Audit complete ==="
```

---

### 10.5 Dump All Secrets (Names Only or Full Values)

One-shot audit of every `pilot/prod/` secret — names + key names only (safe to paste/share), or full values (sensitive — terminal only, never commit or paste into chat/logs).

```bash
# ── Option A: Names + key names only (NO values — safe for audits) ────────────
aws secretsmanager list-secrets \
  --filters Key=name,Values="pilot/prod/" \
  --query 'SecretList[*].Name' --output text --region us-east-1 \
| tr '\t' '\n' | while read -r s; do
    KEYS=$(aws secretsmanager get-secret-value --secret-id "$s" \
      --query 'SecretString' --output text --region us-east-1 \
      | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
    print(', '.join(d.keys()))
except json.JSONDecodeError:
    print('(plain-text secret — no keys)')
")
    echo "$s: $KEYS"
  done

# ── Option B: Full dump — every secret with ALL key/value pairs ───────────────
# ⚠️ SENSITIVE: prints live credentials to the terminal (e.g. telnyx
# platform_sms_number, stripe secret_key, db password). Do not redirect into
# the repo, screenshots, or chat. Prefer Option A unless you need the values.
aws secretsmanager list-secrets \
  --filters Key=name,Values="pilot/prod/" \
  --query 'SecretList[*].Name' --output text --region us-east-1 \
| tr '\t' '\n' | while read -r s; do
    echo "=== $s ==="
    aws secretsmanager get-secret-value --secret-id "$s" \
      --query 'SecretString' --output text --region us-east-1 \
      | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    print(f'  (raw): {raw}')
else:
    for k, v in d.items():
        print(f'  {k}: {v}')
"
  done

# ── Option C: Same as B, but redact values (show first 4 chars + length) ──────
aws secretsmanager list-secrets \
  --filters Key=name,Values="pilot/prod/" \
  --query 'SecretList[*].Name' --output text --region us-east-1 \
| tr '\t' '\n' | while read -r s; do
    echo "=== $s ==="
    aws secretsmanager get-secret-value --secret-id "$s" \
      --query 'SecretString' --output text --region us-east-1 \
      | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    print(f'  (raw): {raw[:4]}... ({len(raw)} chars)')
else:
    for k, v in d.items():
        v = str(v)
        print(f'  {k}: {v[:4]}... ({len(v)} chars)')
"
  done
```

Expected Option A output — all 11 secrets with **every** key listed (e.g. telnyx shows `api_key, messaging_profile_id, public_key, platform_sms_number`; Option B prints the actual values including the SMS number):

| Secret | Keys |
|---|---|
| `pilot/prod/db` | username, password, host, port, dbname, url (Terraform-populated superset) |
| `pilot/prod/redis` | connection URLs (DB 0/1/2) |
| `pilot/prod/cognito` | region, user_pool_id, app_client_id |
| `pilot/prod/sendgrid` | api_key, from_email |
| `pilot/prod/telnyx` | api_key, messaging_profile_id, public_key, platform_sms_number |
| `pilot/prod/encryption` | fernet_key |
| `pilot/prod/google-maps` | api_key |
| `pilot/prod/turnstile` | secret_key |
| `pilot/prod/gpu` | whisper_url, ollama_url |
| `pilot/prod/quickbooks` | QB app credentials |
| `pilot/prod/stripe` | publishable_key, secret_key, webhook_secret |

---

## 11. View Application Logs (CloudWatch)

### Tail Logs Live

```bash
# FastAPI API logs
aws logs tail /ecs/pilot-api --follow --region us-east-1

# Celery Worker logs
aws logs tail /ecs/pilot-celery-worker --follow --region us-east-1

# Celery Beat logs (scheduled task execution)
aws logs tail /ecs/pilot-celery-beat --follow --region us-east-1

# Web dashboard logs
aws logs tail /ecs/pilot-production-web --follow --region us-east-1
```

### Filter Logs (last hour)

```bash
# Get API errors from the last hour
aws logs filter-log-events \
  --log-group-name /ecs/pilot-api \
  --start-time $(python3 -c "import time; print(int((time.time() - 3600) * 1000))") \
  --filter-pattern "ERROR" \
  --region us-east-1 | python3 -m json.tool | grep message

# Get Celery task failures from the last 24 hours
aws logs filter-log-events \
  --log-group-name /ecs/pilot-celery-worker \
  --start-time $(python3 -c "import time; print(int((time.time() - 86400) * 1000))") \
  --filter-pattern "FAILURE" \
  --region us-east-1
```

### ECS Task-Level Logs (for a specific running task)

```bash
# Get list of running task ARNs for the API service
aws ecs list-tasks \
  --cluster pilot-production \
  --service-name pilot-api \
  --query 'taskArns' \
  --output table --region us-east-1

# Get the log stream name for a specific task
TASK_ARN="arn:aws:ecs:us-east-1:000000000000:task/pilot-production/TASK_ID"
aws logs tail /ecs/pilot-api --log-stream-names "ecs/api/$(echo $TASK_ARN | cut -d'/' -f3)" \
  --follow --region us-east-1
```

---

## 12. Health Checks — Verify Everything Is Running

Use this section to confirm the full stack is healthy before a demo, beta customer access, or after any change.

```bash
echo "=== Pilot Production Health Check ==="

# ── ECS Service Status ──────────────────────────────────────────────────────────
echo ""
echo "── ECS Services ──"
aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-api pilot-celery-worker pilot-celery-beat pilot-web \
  --query 'services[*].{Name:serviceName,Desired:desiredCount,Running:runningCount,Status:status}' \
  --output table --region us-east-1

# ── API Health ──────────────────────────────────────────────────────────────────
echo ""
echo "── API Health ──"
curl -sf https://api.pilotfortrades.com/api/v1/health/celery | python3 -m json.tool

# ── Web Dashboard Health ────────────────────────────────────────────────────────
echo ""
echo "── Web Dashboard ──"
curl -sI https://app.pilotfortrades.com | head -1

# ── Marketing Site ──────────────────────────────────────────────────────────────
echo ""
echo "── Marketing Site ──"
curl -sI https://pilotfortrades.com | head -1

# ── RDS Status ──────────────────────────────────────────────────────────────────
echo ""
echo "── RDS ──"
aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,MultiAZ:MultiAZ}' \
  --output table --region us-east-1

# ── Redis Status ────────────────────────────────────────────────────────────────
echo ""
echo "── Redis ──"
aws elasticache describe-cache-clusters \
  --cache-cluster-id pilot-production \
  --query 'CacheClusters[0].{Status:CacheClusterStatus,Node:CacheNodeType}' \
  --output table --region us-east-1

# ── Bastion Status ──────────────────────────────────────────────────────────────
echo ""
echo "── Bastion ──"
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-bastion" \
  --query 'Reservations[0].Instances[0].{State:State.Name,IP:PublicIpAddress}' \
  --output table --region us-east-1

# ── GPU Status ──────────────────────────────────────────────────────────────────
echo ""
echo "── GPU ──"
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pilot-production-gpu" \
  --query 'Reservations[0].Instances[0].{State:State.Name,PrivateIP:PrivateIpAddress}' \
  --output table --region us-east-1

echo ""
echo "=== Health check complete ==="
```

---

## 13. Cost Monitoring

### Quick Cost Check (This Month)

```bash
# Total spend this month
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --query 'ResultsByTime[0].Total.BlendedCost' \
  --region us-east-1

# Cost breakdown by AWS service this month
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups[*].{Service:Keys[0],Cost:Metrics.BlendedCost.Amount}' \
  --output table \
  --region us-east-1
```

### Profile Cost Summary

| Profile | Script | Approximate Monthly | When to Use |
|---|---|---|---|
| **OFF** (cost floor) | `profile-off.sh` | ~$102 | Overnight, weekends, idle periods |
| **A: Marketing Only** | `profile-a-marketing.sh` | ~$148 | Lead collection, form testing |
| **B light: UI only** | `profile-b-app.sh light` | ~$170 | Web/mobile UI testing, no Voice AI |
| **B ai: Full AI** | `profile-b-app.sh ai` | ~$562 | Voice AI development and testing |
| **C: Beta Customers** | `profile-c-full.sh` | ~$562–667 | Beta launch, real customer access |

> **Pre-revenue default**: Keep the system at Profile OFF or Profile A most of the time.
> Switch to B `light` for UI testing. Switch to B `ai` only when testing Voice AI specifically.

---

## 14. Terraform Operations — Updating Infrastructure

> **Terraform is for infrastructure, not application deploys.** ECS task definitions are updated by pushing a new Docker image + `force-new-deployment`. Terraform manages the cluster, services, security groups, RDS, and everything else — but not application code.

### 14.1 Standard Update Process

```bash
# 1. Always work from the production environment directory
cd infrastructure/terraform/environments/production

# 2. Verify you are in the right account before touching anything
aws sts get-caller-identity --query 'Account' --output text
# Expected: 000000000000

# 3. Preview what will change — READ THIS OUTPUT CAREFULLY
terraform plan

# 4. Apply the changes
terraform apply

# 5. If the apply registered NEW task definition revisions (any change to
#    modules/compute): sync ALL services to the latest revision — Terraform
#    registers the new revision but does NOT always force services onto it.
#    See §19.6 for the full procedure + one-liner.
```

> **⚠️ Stale-revision trap (bit us 2026-08-09)**: a `terraform apply` that changes env/secrets in `modules/compute` registers new task-definition revisions, but services keep running their **old** revision until explicitly updated. The result: new env vars silently absent in prod (e.g. `PILOT_PLATFORM_SMS_NUMBER` missing → all platform SMS silently skipped). **Always run the §19.6 sync check after any compute-module apply.**

> **`terraform plan` is the most important step.** Lines prefixed with `+` create resources; `~` modify; `-` destroy. Never skip it.

---

### 14.2 Targeted Applies

`-target` applies changes to only one module or resource, leaving everything else untouched:

```bash
# Update only the bastion security group rules (e.g., new admin IP)
terraform apply -target=module.networking.aws_security_group_rule.bastion_ssh_ingress

# Update only CloudWatch alarms
terraform apply -target=module.monitoring

# Update only ECS task definitions / services
terraform apply -target=module.compute

# Update only database config
terraform apply -target=module.database
```

---

### 14.3 Module Ownership Reference

| Resource to Add/Change | Module to Edit |
|---|---|
| New S3 bucket | `modules/storage/` |
| New CloudFront distribution | `modules/compute/` |
| New/changed security group or rule | `modules/networking/` |
| New IAM role, policy, or permission | `modules/security/` |
| New Secrets Manager secret (shell) | `modules/security/` |
| New ACM certificate | `modules/security/` |
| New Route 53 record | `modules/security/` |
| New CloudWatch alarm or log group | `modules/monitoring/` |
| New ECS service or task definition | `modules/compute/` |
| New EC2 instance | `modules/compute/` |
| New RDS parameter group | `modules/database/` |
| New ElastiCache config | `modules/database/` |

---

### 14.4 Common Update Scenarios

**Add your backup ISP or travel IP to bastion access:**
```bash
# 1. Get your current public IP
curl -s https://api.ipify.org

# 2. Edit environments/production/terraform.tfvars:
#    admin_allowed_ips = ["203.0.113.13", "<NEW_IP>"]

# 3. Targeted apply — takes ~30 seconds
cd infrastructure/terraform/environments/production
terraform apply -target=module.networking.aws_security_group_rule.bastion_ssh_ingress
```

**Add a new environment variable to ECS tasks:**
```bash
# 1. Edit modules/compute/main.tf — add to the environment block in the task definition

# 2. Apply compute module
terraform apply -target=module.compute

# 3. Force ECS to use the new task definition revision
aws ecs update-service --cluster pilot-production --service pilot-api \
  --force-new-deployment --region us-east-1
```

**Add a new Secrets Manager secret:**
```bash
# 1. Add aws_secretsmanager_secret resource to modules/security/main.tf
# 2. Add the ARN to modules/security/outputs.tf
# 3. Wire the ARN into the ECS task secrets list in modules/compute/main.tf
# 4. Add the ARN to the IAM policy (ecs_task_secrets) in modules/security/main.tf
# 5. terraform plan → terraform apply
# 6. Populate the secret value via CLI:
aws secretsmanager put-secret-value \
  --secret-id "pilot/prod/new-secret" \
  --secret-string '{"key": "value"}' --region us-east-1
```

**Scale up ECS tasks (e.g., when beta customers grow):**
```bash
# Option A: Via Terraform (permanent change — survives profile script runs)
# 1. Edit environments/production/variables.tf:
#    ecs_api_desired_count    = 4   (was 2)
#    ecs_worker_desired_count = 4   (was 2)
# 2. Apply
terraform apply -target=module.compute

# Option B: Via CLI (temporary — profile scripts will override this)
aws ecs update-service --cluster pilot-production --service pilot-api \
  --desired-count 4 --region us-east-1
```

**Wait for ECS to be stable (after any apply or deployment):**
```bash
aws ecs wait services-stable \
  --cluster pilot-production \
  --services pilot-api pilot-celery-worker pilot-celery-beat \
  --region us-east-1
echo "All ECS services stable and healthy ✅"
```

---

### 14.5 Resources That Require Extra Steps

| Change | Extra Step Required |
|---|---|
| Cognito user pool | `terraform import aws_cognito_user_pool.prod <pool-id>` first — already done (`us-east-1_XXXXXXXXX`) |
| RDS parameter changes | Some parameters require an RDS reboot to take effect |
| New ACM certificate | DNS validation takes 5–30 min after `terraform apply` |
| `pilot/prod/db` secret value | Automatically populated by the database module — do not manually edit |
| Any new secret value | Always populate manually via Console or CLI — Terraform creates the shell only |
| GPU instance replacement | 15+ min for boot + model download; update `pilot/prod/gpu` secret afterward (see §7) |
| **Post-Confirmation Lambda** (SIGNUP-GA-1) | **Run `build-post-confirmation-lambda.sh` before `terraform plan`**; wire the Cognito trigger via CLI after `apply` (see below) |
| **Post-Authentication Lambda** (PLATFORM-SMS-B2) | **Run `build-post-authentication-lambda.sh` before `terraform plan`**; enable device tracking + wire BOTH Cognito triggers via CLI after `apply` (see below) |
| **Custom Email Sender Lambda** (COGNITO-EMAIL-1) | **Run `build-custom-email-sender-lambda.sh` before `terraform plan`**; wire ALL THREE Cognito triggers + KMSKeyID via CLI after `apply` (see below). `email_sending_account` stays `COGNITO_DEFAULT` — the trigger bypasses it |
| **Cognito SmsConfiguration** (MFA-WIRE-1) | No build step — pure IAM + pool config. Plan must show **exactly 3 deltas** (role create, policy create, pool in-place update). ⚠️ `device_configuration` is now in `ignore_changes` (set via CLI in PLATFORM-SMS-B2). SMS delivery smokes blocked on AWS Support (SNS sandbox + no origination number) — see below |

#### Post-Confirmation Lambda — Build, Deploy, and Wire the Trigger (SIGNUP-GA-1)

The Post-Confirmation Lambda (`pilot-production-post-confirmation`) is a 3-path router that provisions RDS rows on Cognito confirmation (ADR-0011). Its package includes Linux-compiled wheels (psycopg2-binary, sqlalchemy, sqlmodel, pydantic, pgvector) + the handler source + the `app/models` tree. boto3/botocore are NOT packaged (pre-bundled in the Lambda runtime).

**Step 1 — Build the package** (run from repo root, before `terraform plan`):

```bash
./infrastructure/scripts/build-post-confirmation-lambda.sh
```

This populates `infrastructure/terraform/modules/security/build/post_confirmation/`. The Terraform `data.archive_file.post_confirmation` zips it at plan/apply time. The build dir is gitignored.

**Step 2 — Review the plan** (auth-critical — review with Tom before apply):

```bash
cd infrastructure/terraform/environments/production
terraform plan
```

Expected diffs:
- `aws_lambda_function.post_confirmation`: `source_code_hash` changes (new package); env vars `DB_SECRET_ARN`, `COGNITO_USER_POOL_ID`, `ENVIRONMENT` unchanged.
- `aws_cognito_user_pool.prod`: `allow_admin_create_user_only: true → false` (the **only** pool diff — no force-replacements).
- `aws_lambda_permission.cognito_post_confirmation`: unchanged.

> ⚠️ If the plan shows a pool **force-replacement** or unexpected diffs → **STOP and ask Tom**. A pool replacement would destroy all users.

**Step 3 — Apply**:

```bash
terraform apply
```

**Step 4 — Wire the Post-Confirmation trigger** (manual — `lambda_config` is in `ignore_changes`):

> ⚠️ **Full-carry rule — THREE reset-prone blocks**: `update-user-pool` RESETS any of these three omitted blocks to empty — `lambda_config`, `device_configuration`, and **`auto_verified_attributes`** (the third confirmed 2026-09-04: a lambda-only wiring call silently disabled all Cognito email verification — SignUps created users but sent no codes for ~19 h; resend fails with "Auto verification not turned on"). Every `update-user-pool` call must carry ALL THREE blocks at their current live values, with every live trigger inside `--lambda-config`. The historical PostConfirmation-only command that used to live here is superseded — use the canonical full-carry command in **§14.5 Step 5** for any wiring change today.

```bash
# Verify current config first (don't clobber triggers/blocks)
aws cognito-idp describe-user-pool \
  --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.{LC: LambdaConfig, Device: DeviceConfiguration, AutoVerified: AutoVerifiedAttributes}'
```

> `update-user-pool` overwrites the **entire** `LambdaConfig` block. If the describe shows other triggers configured, include them all in the same `--lambda-config` call.

**Step 5 — Verify**:

```bash
# Lambda code SHA changed + env vars present
aws lambda get-function --function-name pilot-production-post-confirmation \
  --query 'Configuration.[CodeSha256, Environment.Variables]'

# Pool: self-registration enabled + triggers attached + reset-prone blocks intact
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.{SelfReg: AdminCreateUserConfig.AllowAdminCreateUserOnly, LC: LambdaConfig, AutoVerified: AutoVerifiedAttributes, Device: DeviceConfiguration}'
# Expect: SelfReg false; LC = ALL live triggers (+ KMSKeyID); AutoVerified ["email"];
#         Device tracking on / always-remember. Any null or missing trigger → STOP,
#         restore via the §14.5 Step 5 full-carry command, then re-verify.
```

**Rollback** (if self-sign-up or the Lambda misbehaves):

```bash
# Re-close self-registration immediately (existing users/login unaffected)
cd infrastructure/terraform/environments/production
# Edit modules/security/main.tf: allow_admin_create_user_only = true
terraform apply -target=aws_cognito_user_pool.prod
```

#### Post-Authentication Lambda — Build, Deploy, and Wire the Trigger (PLATFORM-SMS-B2)

The Post-Authentication Lambda (`pilot-production-post-authentication`) fires on every successful Cognito authentication (after MFA) and gates on `event.request.newDeviceUsed` — populated only because device tracking is set to "Always remember" (ADR-0013 / Pathway C). On a new-device sign-in it enqueues the existing B1 task (`send_platform_account_notification_sms`) directly to the Redis broker via a minimal Celery producer (kombu transport). Its package includes Linux-compiled wheels (psycopg2-binary, sqlalchemy, sqlmodel, pydantic, pgvector, **celery**) + the handler source + the `app/models` tree. boto3/botocore are NOT packaged (pre-bundled in the Lambda runtime).

**Step 1 — Build the package** (run from repo root, before `terraform plan`):

```bash
./infrastructure/scripts/build-post-authentication-lambda.sh
```

This populates `infrastructure/terraform/modules/security/build/post_authentication/`. The Terraform `data.archive_file.post_authentication` zips it at plan/apply time. The build dir is gitignored.

**Step 2 — Review the plan** (auth-critical — review with Tom before apply):

```bash
cd infrastructure/terraform/environments/production
terraform plan
```

Expected diffs (6 resources):
- `aws_lambda_function.post_authentication`: CREATE (python3.12, 30s timeout, 256 MB, VPC, env vars `DB_SECRET_ARN` + `REDIS_SECRET_ARN` + `COGNITO_USER_POOL_ID` + `ENVIRONMENT`).
- `aws_lambda_permission.cognito_post_authentication`: CREATE (Cognito invoke rights).
- `aws_iam_role_policy.lambda_rds`: UPDATE (redis secret ARN added to the `Resource` list — least-privilege widening per secret-management-policy §4).
- `aws_cloudwatch_log_group.lambda_post_authentication`: CREATE (`/aws/lambda/pilot-production-post-authentication`).
- `aws_security_group.sg_redis`: UPDATE (one ingress rule added — 6379 from `sg-lambda`).
- `data.archive_file.post_authentication`: read during apply.

> ⚠️ If the plan shows a pool **force-replacement**, ECS desired_count changes, or unexpected diffs → **STOP and ask Tom**. Use a targeted apply to avoid scaling ECS services or re-deploying the live Post-Confirmation Lambda.

**Step 3 — Apply** (targeted to the 6 SMS-B2 resources to avoid drift):

```bash
terraform apply \
  -target=module.security.aws_lambda_function.post_authentication \
  -target=module.security.aws_lambda_permission.cognito_post_authentication \
  -target=module.security.aws_iam_role_policy.lambda_rds \
  -target=module.security.data.archive_file.post_authentication \
  -target=module.monitoring.aws_cloudwatch_log_group.lambda_post_authentication \
  -target=module.networking.aws_security_group.sg_redis
```

**Step 4 — Enable device tracking + wire triggers** (manual — `lambda_config` is in `ignore_changes`):

> ⚠️ **Whole-block overwrite warning — THREE reset-prone blocks**: `update-user-pool` replaces the ENTIRE `LambdaConfig` and RESETS `--device-configuration` and `--auto-verified-attributes` to empty when omitted (2026-08-16: a device-only call cleared `LambdaConfig`, detaching both triggers; 2026-09-04: a lambda-only call cleared `AutoVerifiedAttributes` — SignUps sent no verification codes for ~19 h). ONE call must carry all live triggers + `KMSKeyID` + device config + `--auto-verified-attributes email`.

```bash
# Current full-carry form (supersedes the original 2-trigger command — the live
# trigger set since COGNITO-EMAIL-1 is THREE triggers + KMSKeyID):
POST_CONFIRM_ARN=$(aws lambda get-function --function-name pilot-production-post-confirmation \
  --query 'Configuration.FunctionArn' --output text)
POST_AUTH_ARN=$(aws lambda get-function --function-name pilot-production-post-authentication \
  --query 'Configuration.FunctionArn' --output text)
CES_ARN="arn:aws:lambda:us-east-1:000000000000:function:pilot-production-custom-email-sender"
KMS_ARN="arn:aws:kms:us-east-1:000000000000:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1"

aws cognito-idp update-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config "PostConfirmation=${POST_CONFIRM_ARN},PostAuthentication=${POST_AUTH_ARN},CustomEmailSender={LambdaArn=${CES_ARN},LambdaVersion=V1_0},KMSKeyID=${KMS_ARN}"

# Verify — ALL of: 3 triggers + KMSKeyID; device tracking on, always-remember; AutoVerified ["email"]
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.{LC: LambdaConfig, Device: DeviceConfiguration, AutoVerified: AutoVerifiedAttributes}'
# Any null or missing trigger → restore immediately (§14.5 Step 5 command) and STOP.
```

**Step 5 — Smoke test** (see [`batch-platform-sms-b2-devops-prompt.md`](prompts/batch-platform-sms-b2-devops-prompt.md) Task 7):
1. Precondition: a test owner whose `user_endpoint` sms row is `consent_status='opted_in'` + `verification_status='verified'`.
2. Sign in from a **new device context** (fresh incognito window / new browser profile) via the normal web login (complete MFA if enrolled).
3. Within ~1 minute: the owner's phone receives the Sample 3 SMS — verbatim: `Pilot for Trades: New sign-in to your account from a new device. If this wasn't you, secure your account now. Reply STOP to opt out.`
4. Confirm the trail: `/aws/lambda/pilot-production-post-authentication` shows the `newDeviceUsed` gate pass + enqueue line; the Celery worker logs show the `send_platform_account_notification_sms` send.
5. **Negative**: sign in again from the same browser → no SMS (device now remembered; Lambda logs show the gate returning early).

**Operational heads-up**: when device tracking flips on, each user's **first** sign-in per device reads as "new" and fires the alert once per owner endpoint; it settles as devices are remembered. Expected — not a defect.

**Rollback** (detach the Post-Authentication trigger, leave the function deployed but inert):

```bash
# ⚠️ Full-carry rule applies to rollbacks too — carry auto-verify + device + every
#    trigger that must STAY attached (here: PostConfirmation + CustomEmailSender + KMSKeyID):
aws cognito-idp update-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config "PostConfirmation=${POST_CONFIRM_ARN},CustomEmailSender={LambdaArn=${CES_ARN},LambdaVersion=V1_0},KMSKeyID=${KMS_ARN}"
# Optionally also disable tracking (still carry auto-verify + full lambda-config in the same call):
#   --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=true
```

---

#### Cognito SmsConfiguration — Plan, Apply, Verify (MFA-WIRE-1)

The production pool shipped without an `SmsConfiguration` (no SNS role), so SMS MFA OTPs could never be delivered. MFA-WIRE-1 (Step 0) added the SNS IAM role + `sms_configuration` block to the security module. This is a pure IAM + pool-config change — no Lambda build step.

**Step 1 — Plan gate (the three-deltas-only rule)**:

```bash
cd infrastructure/terraform/environments/production
aws sts get-caller-identity --query 'Account' --output text  # → 000000000000
terraform plan -target=module.security
```

The plan **MUST** show exactly:
1. `+ aws_iam_role.cognito_sns` (create)
2. `+ aws_iam_role_policy.cognito_sns_publish` (create)
3. `~ aws_cognito_user_pool.prod` (update in-place — `+ sms_configuration { ... }`)

**If anything else appears → STOP.** Pool replacement is an immediate stop (`deletion_protection = ACTIVE`). `lambda_config` and `device_configuration` diffs must not appear (both are in `ignore_changes`).

> **`device_configuration` in `ignore_changes`** (added MFA-WIRE-1): the pool's device tracking was set manually via CLI during PLATFORM-SMS-B2. Without this ignore entry, Terraform treats it as drift and plans to remove it — which would break the Post-Authentication new-device alert gate. Same treatment as `lambda_config`.

**Step 2 — Apply**:

```bash
terraform apply -target=module.security -auto-approve
# Expect: 2 added, 1 changed, 0 destroyed
```

**Step 3 — Verify wiring**:

```bash
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX \
  --query 'UserPool.SmsConfiguration.{SnsCallerArn: SnsCallerArn, ExternalId: ExternalId, SnsRegion: SnsRegion}'
# Expect: SnsCallerArn = arn:aws:iam::000000000000:role/CognitoSNSRole-pilot-production
#         ExternalId  = pilot-prod-cognito-sms
#         SnsRegion   = us-east-1
```

**Step 4 — SMS delivery smokes (⏳ BLOCKED on AWS Support)**:

The SNS SMS account is sandboxed with **no origination number**, so no SMS can be sent yet — not even the sandbox verification code. The smokes (direct `sns publish` + Cognito→SNS OTP) are blocked until Tom opens an AWS Support case for SNS SMS production access. See [`aws-cognito-prod-setup.md`](aws-cognito-prod-setup.md) → "MFA-WIRE-1 — Cognito SMS Delivery" for the full blocked-task list and the post-unblock smoke commands.

> **Rollback**: Cognito has no detach for `SmsConfiguration` once set. The config is inert unless a user enables SMS MFA. Keep the block in Terraform state — removing it causes a perpetual plan diff. Fix forward via Terraform; do not delete the IAM role (would re-break SMS delivery, caught by Part A's 503 `sms_delivery_not_configured`).

#### Custom Email Sender Lambda — Build, Deploy, and Wire the Trigger (COGNITO-EMAIL-1)

The Custom Email Sender Lambda (`pilot-production-custom-email-sender`) replaces Cognito's default auth email sending (`COGNITO_DEFAULT` — 50/day cap, no DKIM/SPF control, spam placement) with branded SendGrid delivery. Cognito invokes the Lambda with a KMS-encrypted code → the Lambda decrypts via the **AWS Encryption SDK** (envelope encryption — NOT raw `kms:Decrypt`), renders a branded template, and sends via SendGrid (`noreply@pilotfortrades.com`). Covers `SignUp` / `ResendCode` / `ForgotPassword` / `VerifyUserAttribute` / `UpdateUserAttribute` / `AdminCreateUser`.

**⚠️ Key implementation notes** (discovered during 2026-09-03 prod smoke):
- Cognito uses the **AWS Encryption SDK** to encrypt the code (envelope format), NOT raw `kms:Encrypt`. The handler must use `aws_encryption_sdk.EncryptionSDKClient` + a KMS keyring — raw `kms.decrypt()` fails with `InvalidCiphertextException`.
- The SDK v4.x defaults to `CommitmentPolicy.REQUIRE_ENCRYPT_REQUIRE_DECRYPT` which rejects Cognito's uncommitted messages (Algorithm ID 888). Use `CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT`.
- The `pilot/prod/sendgrid` secret uses JSON key `api_key` (not `SENDGRID_API_KEY`).

Its package includes `sendgrid==6.11.0` + `aws-encryption-sdk==4.0.6` + `aws-cryptographic-material-providers==1.11.3` (+ transitive deps) + `handler.py` + `templates.py`. Self-contained — NO `app/models` bundle (design §B: auth path must not depend on RDS). boto3/botocore and other runtime-provided packages are stripped after install. 512 MB memory (the Encryption SDK + cryptography library has a larger footprint).

**Step 1 — Build the package**:

```bash
./infrastructure/scripts/build-custom-email-sender-lambda.sh
# Verify: handler.py, templates.py, sendgrid/, aws_encryption_sdk/, cryptography/
# NO boto3/, NO app/
```

**Step 2 — Plan-gate** (review with Tom before apply):

```bash
cd infrastructure/terraform/environments/production
terraform plan -target=module.security -target=module.monitoring
# Expect: ONLY adds (Lambda, role, policies, permission, alarm, log group)
# ZERO changes to aws_cognito_user_pool.prod, ZERO replacements
# Any pool modification or replacement → STOP and tell Tom
```

**Step 3 — Apply**:

```bash
terraform apply -target=module.security.aws_lambda_function.custom_email_sender \
  -target=module.security.aws_iam_role.custom_email_sender \
  -target=module.security.aws_iam_role_policy.custom_email_sender \
  -target=module.security.aws_lambda_permission.cognito_custom_email_sender \
  -target=module.monitoring.aws_cloudwatch_log_group.lambda_custom_email_sender \
  -target=module.monitoring.aws_cloudwatch_metric_alarm.custom_email_sender_errors \
  -auto-approve
```

**Step 4 — Verify the Lambda** (pre-wiring):

```bash
aws lambda get-function-configuration --function-name pilot-production-custom-email-sender \
  --query '{State: State, Runtime: Runtime, Memory: MemorySize, Env: Environment.Variables}'
# Expect: Active, python3.12, 512, SENDGRID_SECRET_ARN + KMS_KEY_ARN present

aws lambda get-policy --function-name pilot-production-custom-email-sender \
  --query 'Policy' --output text | python3 -c "import sys,json; print(json.load(sys.stdin))"
# Expect: cognito-idp.amazonaws.com invoke permission
```

**Step 5 — Wire the trigger** (manual CLI — ONE call, ALL triggers + KMSKeyID + device + auto-verify):

`update-user-pool` **replaces the entire LambdaConfig map** and **resets `--device-configuration` and `--auto-verified-attributes` to empty when omitted** — the three reset-prone blocks. Omitting an existing trigger ARN silently detaches it; omitting `--auto-verified-attributes email` silently disables ALL Cognito email verification — SignUps then send no codes and resend fails with "Auto verification not turned on" (incident 2026-09-03/04: the original lambda-only version of this command did exactly that — ~19 h dead window, found during TEAM-INVITE-1 prod testing). This full-carry form is the canonical command for EVERY `update-user-pool` call on this pool — carry ALL FIVE elements in ONE call:

```bash
POOL=us-east-1_XXXXXXXXX
PC_ARN="arn:aws:lambda:us-east-1:000000000000:function:pilot-production-post-confirmation"
PA_ARN="arn:aws:lambda:us-east-1:000000000000:function:pilot-production-post-authentication"
CES_ARN="arn:aws:lambda:us-east-1:000000000000:function:pilot-production-custom-email-sender"
KMS_ARN="arn:aws:kms:us-east-1:000000000000:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1"

aws cognito-idp update-user-pool --user-pool-id $POOL --region us-east-1 \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config \
  "PostConfirmation=${PC_ARN},PostAuthentication=${PA_ARN},CustomEmailSender={LambdaArn=${CES_ARN},LambdaVersion=V1_0},KMSKeyID=${KMS_ARN}"

# Verify — EXPECT: all three triggers + KmsKeyId; AutoVerified ["email"];
# DeviceConfiguration tracking on / always-remember; EmailSendingAccount still
# null (COGNITO_DEFAULT); SmsConfiguration unchanged
aws cognito-idp describe-user-pool --user-pool-id $POOL --region us-east-1 \
  --query 'UserPool.{LC: LambdaConfig, AutoVerified: AutoVerifiedAttributes, Device: DeviceConfiguration, Email: EmailSendingAccount, Sms: SmsConfiguration}'
```

If the verify shows a missing prior trigger, `AutoVerified: null`, `Device: null`, or Sms drift → re-run the full-carry command above immediately (it doubles as the restore command) and STOP.

**Step 6 — Smokes** (Tom-assisted):

1. **ForgotPassword** (safest first): prod login → Forgot password → branded email arrives in inbox (not spam) → Gmail Show original → `SPF: PASS`, `DKIM: PASS` (pilotfortrades.com).
2. **ResendCode**: trigger resend → second branded email arrives.
3. **SignUp**: fresh Gmail `+` alias → invite → branded verification email → code works.
4. **Alarm sanity**: `aws cloudwatch describe-alarms --alarm-names pilot-production-custom-email-sender-errors` → State `OK`.

**Step 7 — Rollback** (config-only, <1 min):

```bash
# Detach the CustomEmailSender trigger — Cognito falls back to COGNITO_DEFAULT.
# ⚠️ Full-carry rule still applies: carry auto-verify + device + the remaining
#    triggers, or the rollback silently wipes them (the three reset-prone blocks).
aws cognito-idp update-user-pool --user-pool-id us-east-1_XXXXXXXXX --region us-east-1 \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config "PostConfirmation=${PC_ARN},PostAuthentication=${PA_ARN}"
# The Lambda stays deployed, dormant. email_sending_account never changed.
```

---

### 14.6 Secrets Manager Decision Framework

AWS ECS has two ways to pass config into a running container:

| | AWS ECS | Security |
|---|---|---|
| **Plain env vars** | `environment {}` block in task definition | Visible in AWS Console; never use for secrets |
| **Secret refs** | `secrets {}` block → Secrets Manager | Fetched at container start; encrypted; audited |

**Decision rule — one question:**

> **"Would this value cause damage if accidentally logged or if the task definition JSON was leaked?"**
>
> - **Yes → Secrets Manager** (fetched via `secrets {}` block)
> - **No → Plain environment variable** (`environment {}` block)

---

### 14.7 Phase 2 Security Upgrade: IAM Database Authentication

> **Deferred post-beta.** Current approach (username/password in Secrets Manager) is secure for MVP. IAM Auth eliminates long-lived database credentials entirely.

**When to implement**: SOC 2 compliance or enterprise customer requirements.

**What it requires**:
1. `iam_database_authentication_enabled = true` on RDS (Terraform + brief RDS reboot)
2. `GRANT rds_iam TO pilot_app_user;` in PostgreSQL
3. FastAPI SQLAlchemy factory updated to call `boto3.client('rds').generate_db_auth_token()`
4. `rds-db:connect` permission added to ECS task IAM role
5. Remove password from `pilot/prod/db` (keep host/port/dbname)

---

## 15. Infrastructure State Management

### What It Is

The 4 profile scripts need live AWS resource IDs to operate. `generate-infra-state.sh` dynamically discovers them and writes `.infra-state.env` — sourced by all 4 scripts at startup. This means no hardcoded resource IDs in the scripts.

```
infrastructure/scripts/
├── generate-infra-state.sh     ← queries Terraform + EC2/ECS, writes .infra-state.env
├── .infra-state.env            ← GENERATED (gitignored); sourced by all 4 profile scripts
├── .infra-state.env.example    ← committed reference (shows all flags when fully provisioned)
├── profile-a-marketing.sh
├── profile-b-app.sh
├── profile-c-full.sh
└── profile-off.sh
```

### When to Run `generate-infra-state.sh`

Run after **any `terraform apply`** that creates or replaces resources:

```bash
cd infrastructure/scripts
./generate-infra-state.sh
```

Specifically run after:
- GPU instance provisioned (`gpu_quota_approved = true`) → `INFRA_GPU` flips to `true`
- Any resource is destroyed and recreated (new instance IDs)

### Feature Flags Written to `.infra-state.env`

| Flag | Phase | Meaning |
|---|---|---|
| `INFRA_NETWORKING` | 1 | VPC, subnets, NAT Gateway, security groups, bastion EIP |
| `INFRA_DATABASE` | 2 | RDS PostgreSQL + ElastiCache Redis |
| `INFRA_STORAGE` | 4+5 | S3 buckets + CloudFront distribution |
| `INFRA_BASTION` | 1 | Bastion EC2 instance |
| `INFRA_GPU` | 4 | g4dn.xlarge GPU instance (requires AWS vCPU quota increase) |
| `INFRA_ECS` | 6 | ECS cluster + all 4 services (pilot-api/worker/beat/web) ACTIVE |

### Resource IDs Written

| Variable | Source | Used By |
|---|---|---|
| `GPU_INSTANCE_ID` | EC2 describe by name tag `pilot-production-gpu` | profile-b (ai mode), profile-c, profile-off |
| `BASTION_INSTANCE_ID` | EC2 describe by name tag `pilot-production-bastion` | profile-off |
| `CLOUDFRONT_DIST_ID` | `terraform output cloudfront_distribution_id` | all 4 scripts (site-config invalidation) |
| `ECS_CLUSTER` | `terraform output ecs_cluster_name` | all 4 scripts (ECS update-service) |

---

## 18. CloudWatch Metrics — Troubleshooting Commands

Use these commands to diagnose issues from the CLI — same approach used to identify and resolve the `pilot-api` memory incidents (July 2026):

**2026-07-06 incident root causes (two compounding issues):**
1. **Kombu broadcast consumer leak**: `celery_app.control.inspect()` in `/api/v1/health/celery` opened a new Redis pub/sub fanout channel on every ALB health check (240/hr × 2 tasks). Python's GC could not reclaim objects as fast as they accumulated in a 512 MB heap. Fix: 15-second in-process TTL cache in [`backend/api/routes/health.py`](../../backend/api/routes/health.py) — reduces `inspect()` calls from 240/hr to ~4/hr (60× reduction).
2. **Undersized task definition**: Two uvicorn `--workers 2` processes each load ~200 MB of Python imports at startup = ~400 MB baseline. In a 512 MB task only ~110 MB of headroom remained. Fix: `memory = 1024` in [`infrastructure/terraform/modules/compute/main.tf`](../../infrastructure/terraform/modules/compute/main.tf) for `pilot-api` (task definition rev:4). Idle utilization dropped from 92.8% → 39.5%.

> **Time window tip**: Adjust `--start-time` to control how far back you look. All examples use `python3` to avoid `date -v` vs `date --date` macOS/Linux incompatibilities.

---

### 18.1 ECS Memory Utilization (all services)

**When to use**: Memory alarm firing, OOM-kill suspected, task restarting repeatedly, steady growth over time.

```bash
REGION="us-east-1"
CLUSTER="pilot-production"

# Helper — start time N minutes ago
ago() { python3 -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=$1)).strftime('%Y-%m-%dT%H:%M:%SZ'))"; }

# ── Memory % for a specific service (last 2 hours, 5-min intervals) ───────────
SERVICE="pilot-api"   # change to: pilot-celery-worker | pilot-celery-beat | pilot-web

aws cloudwatch get-metric-statistics \
  --namespace "AWS/ECS" \
  --metric-name "MemoryUtilization" \
  --dimensions Name=ClusterName,Value="$CLUSTER" Name=ServiceName,Value="$SERVICE" \
  --start-time "$(ago 120)" \
  --end-time "$(ago 0)" \
  --period 300 \
  --statistics Average Maximum \
  --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,Avg:Average,Max:Maximum}' \
  --output table --region "$REGION"

# ── Quick current snapshot — all 4 services (last 5 minutes) ─────────────────
for svc in pilot-api pilot-celery-worker pilot-celery-beat pilot-web; do
  MEM=$(aws cloudwatch get-metric-statistics \
    --namespace "AWS/ECS" \
    --metric-name "MemoryUtilization" \
    --dimensions Name=ClusterName,Value="$CLUSTER" Name=ServiceName,Value="$svc" \
    --start-time "$(ago 10)" \
    --end-time "$(ago 0)" \
    --period 600 \
    --statistics Average \
    --query 'Datapoints[0].Average' \
    --output text --region "$REGION" 2>/dev/null || echo "N/A")
  printf "  %-30s %s%%\n" "$svc" "$MEM"
done
```

**Interpreting results**:
- Steady slow climb (1-5%/hr at idle) → likely a resource leak (unclosed connections, unbounded in-memory cache) — check recent code changes and endpoint patterns in logs
- Sudden spike → likely a burst of requests or a large data processing task — check logs for the spike window
- Plateau at 35-45% → normal idle for FastAPI + SQLAlchemy connection pool on 1024 MB (`pilot-api` task definition rev:4 as of 2026-07-06). If memory climbs past 80% at idle with no user traffic, check for new endpoint patterns that create per-request OS-level objects (Kombu consumers, SQLAlchemy sessions, etc.)

---

### 18.2 ECS CPU Utilization (all services)

**When to use**: API feels slow, tasks are timing out, high latency on ALB, CPU alarm firing.

```bash
REGION="us-east-1"
CLUSTER="pilot-production"
ago() { python3 -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=$1)).strftime('%Y-%m-%dT%H:%M:%SZ'))"; }

# ── CPU % for pilot-api (last 1 hour, 5-min intervals) ────────────────────────
aws cloudwatch get-metric-statistics \
  --namespace "AWS/ECS" \
  --metric-name "CPUUtilization" \
  --dimensions Name=ClusterName,Value="$CLUSTER" Name=ServiceName,Value=pilot-api \
  --start-time "$(ago 60)" \
  --end-time "$(ago 0)" \
  --period 300 \
  --statistics Average Maximum \
  --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,Avg:Average,Max:Maximum}' \
  --output table --region "$REGION"

# ── Quick CPU snapshot — all 4 services ───────────────────────────────────────
for svc in pilot-api pilot-celery-worker pilot-celery-beat pilot-web; do
  CPU=$(aws cloudwatch get-metric-statistics \
    --namespace "AWS/ECS" \
    --metric-name "CPUUtilization" \
    --dimensions Name=ClusterName,Value="$CLUSTER" Name=ServiceName,Value="$svc" \
    --start-time "$(ago 10)" \
    --end-time "$(ago 0)" \
    --period 600 \
    --statistics Average \
    --query 'Datapoints[0].Average' \
    --output text --region "$REGION" 2>/dev/null || echo "N/A")
  printf "  %-30s %s%%\n" "$svc" "$CPU"
done
```

**Context**: `pilot-api` task definition allocates 256 CPU units = 0.25 vCPU. Average idle CPU should be ~1-3%. Spikes to 100% on startup are normal (FastAPI/Gunicorn init). Sustained CPU > 80% at load = bottleneck; bump to 512 or 1024 CPU units via Terraform.

---

### 18.3 ALB HTTP 5xx Errors and Request Count

**When to use**: Users reporting errors, API health check failing, investigating error bursts, checking if traffic is reaching the service.

```bash
REGION="us-east-1"
ago() { python3 -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=$1)).strftime('%Y-%m-%dT%H:%M:%SZ'))"; }

# ── Get ALB name dynamically ───────────────────────────────────────────────────
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?contains(LoadBalancerName, 'pilot')].LoadBalancerArn" \
  --output text --region "$REGION")

# Extract the suffix used as CloudWatch dimension (everything after the first /)
ALB_DIM=$(echo "$ALB_ARN" | sed 's|.*:loadbalancer/||')
echo "ALB dimension: $ALB_DIM"

# ── HTTP 5xx error count (last 1 hour, 1-min resolution) ──────────────────────
aws cloudwatch get-metric-statistics \
  --namespace "AWS/ApplicationELB" \
  --metric-name "HTTPCode_Target_5XX_Count" \
  --dimensions Name=LoadBalancer,Value="$ALB_DIM" \
  --start-time "$(ago 60)" \
  --end-time "$(ago 0)" \
  --period 60 \
  --statistics Sum \
  --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,Errors:Sum}' \
  --output table --region "$REGION"

# ── Total request count (last 1 hour) — confirms traffic is reaching ALB ──────
aws cloudwatch get-metric-statistics \
  --namespace "AWS/ApplicationELB" \
  --metric-name "RequestCount" \
  --dimensions Name=LoadBalancer,Value="$ALB_DIM" \
  --start-time "$(ago 60)" \
  --end-time "$(ago 0)" \
  --period 300 \
  --statistics Sum \
  --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,Requests:Sum}' \
  --output table --region "$REGION"
```

**What to look for**:
- Zero `RequestCount` → traffic not reaching ALB (DNS issue, CloudFront misconfigured, or service at 0 tasks)
- 5xx count climbing → application errors; check `aws logs tail /ecs/pilot-api --follow` concurrently
- 503s specifically → ECS tasks are unhealthy or target group has no healthy targets

---

### 18.4 ALB Target Response Time (p95 Latency)

**When to use**: API feels slow, investigating performance degradation, verifying the p95 < 1s design-target SLO.

```bash
REGION="us-east-1"
ago() { python3 -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=$1)).strftime('%Y-%m-%dT%H:%M:%SZ'))"; }

ALB_ARN=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?contains(LoadBalancerName, 'pilot')].LoadBalancerArn" \
  --output text --region "$REGION")
ALB_DIM=$(echo "$ALB_ARN" | sed 's|.*:loadbalancer/||')

# ── p95 response time (last 1 hour, 5-min intervals) ─────────────────────────
# p99 and p50 also available — change p95 to p99 or p50
aws cloudwatch get-metric-statistics \
  --namespace "AWS/ApplicationELB" \
  --metric-name "TargetResponseTime" \
  --dimensions Name=LoadBalancer,Value="$ALB_DIM" \
  --start-time "$(ago 60)" \
  --end-time "$(ago 0)" \
  --period 300 \
  --extended-statistics "p95" \
  --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,p95_sec:ExtendedStatistics.p95}' \
  --output table --region "$REGION"

# ── Average response time (simpler — no extended statistics) ──────────────────
aws cloudwatch get-metric-statistics \
  --namespace "AWS/ApplicationELB" \
  --metric-name "TargetResponseTime" \
  --dimensions Name=LoadBalancer,Value="$ALB_DIM" \
  --start-time "$(ago 60)" \
  --end-time "$(ago 0)" \
  --period 300 \
  --statistics Average Maximum \
  --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,Avg_sec:Average,Max_sec:Maximum}' \
  --output table --region "$REGION"
```

**SLO reference**: p95 < 1s is a design-target SLO only; deploys are ECS rolling, and no canary rollback is automated. In steady state, FastAPI health endpoints should respond < 200ms average. Response times > 500ms average suggest DB query issues, connection pool exhaustion, or CPU saturation.

---

### 18.5 CloudWatch Alarms — Current State and History

**When to use**: `profile-status.sh` shows a firing alarm, you want to know when it fired and why.

```bash
REGION="us-east-1"

# ── All alarms prefixed with pilot-production — current state ─────────────────
aws cloudwatch describe-alarms \
  --alarm-name-prefix "pilot-production" \
  --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue,Reason:StateReason,UpdatedAt:StateUpdatedTimestamp}' \
  --output table --region "$REGION"

# ── Only ALARM state (firing) ─────────────────────────────────────────────────
aws cloudwatch describe-alarms \
  --alarm-name-prefix "pilot-production" \
  --state-value ALARM \
  --query 'MetricAlarms[*].{Name:AlarmName,Threshold:Threshold,Reason:StateReason}' \
  --output table --region "$REGION"

# ── Alarm state history — when did it last fire and when did it recover? ───────
ALARM_NAME="pilot-production-ecs-api-memory"   # change to whichever alarm you're investigating

aws cloudwatch describe-alarm-history \
  --alarm-name "$ALARM_NAME" \
  --history-item-type StateUpdate \
  --start-date "$(python3 -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ'))")" \
  --query 'AlarmHistoryItems[*].{Time:Timestamp,Summary:HistorySummary}' \
  --output table --region "$REGION"

# ── Alarm detail — what metric, what threshold, how many datapoints ────────────
aws cloudwatch describe-alarms \
  --alarm-names "$ALARM_NAME" \
  --query 'MetricAlarms[0].{Metric:MetricName,Namespace:Namespace,Threshold:Threshold,EvalPeriods:EvaluationPeriods,DatapointsToAlarm:DatapointsToAlarm,Period:Period,Statistic:Statistic,State:StateValue,Reason:StateReason}' \
  --output table --region "$REGION"
```

**Reading alarm history**: Each alarm transition (OK → ALARM → OK) is recorded. The `Summary` field shows the datapoints that crossed the threshold and when. Use this to correlate alarm timing with a deployment, a code change, or a traffic spike.

**All pilot-production alarms**:
| Alarm | Metric | Threshold | What it means |
|---|---|---|---|
| `pilot-production-ecs-api-memory` | ECS MemoryUtilization (pilot-api) | > 80% for 3 periods | FastAPI task approaching 512 MB hard limit |
| `pilot-production-ecs-worker-memory` | ECS MemoryUtilization (pilot-celery-worker) | > 80% for 3 periods | Celery worker memory pressure |
| `pilot-production-ecs-api-cpu` | ECS CPUUtilization (pilot-api) | > 80% for 3 periods | API CPU-bound; may need more CPU units |
| `pilot-production-rds-connections` | RDS DatabaseConnections | > 80 | Too many DB connections; check pool sizing |
| `pilot-production-rds-storage` | RDS FreeStorageSpace | < 5 GB | Disk nearly full; expand or clean up |

---

## 16. Rollback Procedures

> **Future content** — This section will cover:
> - Rolling back an ECS service to a previous task definition revision (`aws ecs update-service --task-definition pilot-api:N`)
> - Rolling back a failed Alembic migration (`alembic downgrade -1`)
> - Restoring RDS from a point-in-time snapshot
> - Reverting a bad marketing site deploy (prior S3 object versions)

---

## 17. Certificate and DNS Rotation

> **Future content** — This section will cover:
> - ACM wildcard cert renewal (automatic — but how to verify and force if needed)
> - Adding a new subdomain to Route 53 + ACM SAN
> - Updating the ALB listener certificate
> - Rotating DKIM keys in Google Workspace + updating Route 53 TXT record

---

### 17.1 p4tsites.com — Cloudflare DNS + ACM Cert (C-B16-OPS, ADR-0014)

**Domain**: `p4tsites.com` — registered via **Cloudflare** ($10.46/yr; Cloudflare is the project registrar of record for new domains). DNS lives in Cloudflare (no Route 53 hosted zone for this domain). Terraform manages the AWS side only (ACM cert + ALB listener cert + host-header rule); Cloudflare-side records/rules are **manual console steps** documented here (no Cloudflare TF provider in Phase 1).

**Wildcard posture (ADR-0014 — binding)**:
- Wildcard `*.p4tsites.com` CNAME → ALB DNS name — **DNS-only (gray cloud)**. Never proxied. Proxied wildcard breaks SlowAPI per-IP accuracy and the ISR/Redis cache contract.
- Apex + `www` — **proxied (orange cloud)** — exist only to power the edge 301 redirect.
- No mail ever from this domain: SPF `v=spf1 -all` + DMARC `p=reject`.

**Cloudflare console records** (in the `p4tsites.com` zone):

| # | Type | Name | Target | Proxy | Purpose |
|---|---|---|---|---|---|
| 1 | `CNAME` | `_<validation-name>` | `_<validation-value>.acm-validations.aws.` | DNS-only (gray) | ACM cert validation (apex + wildcard share this record) |
| 2 | `CNAME` | `*` | `pilot-production-alb-xxxxxxxxxx.us-east-1.elb.amazonaws.com` | DNS-only (gray) | Wildcard → ALB (tenant sites) |
| 3 | `AAAA` | `@` | `100::` | Proxied (orange) | Apex placeholder (powers edge redirect) |
| 4 | `AAAA` | `www` | `100::` | Proxied (orange) | www placeholder (powers edge redirect) |
| 5 | `TXT` | `@` | `v=spf1 -all` | — | Mail lockdown (no mail from this domain) |
| 6 | `TXT` | `_dmarc` | `v=DMARC1; p=reject` | — | DMARC reject (mail lockdown) |

**Cloudflare Redirect Rule** (Rules → Redirect Rules):
- **Name**: `p4tsites-to-pilotfortrades`
- **When** (custom filter expression): `(http.host eq "p4tsites.com") or (http.host eq "www.p4tsites.com")`
- **Then**: Static URL → `https://pilotfortrades.com` · Status `301` · Preserve query string = **off**
- This redirect executes at the Cloudflare edge — never reaches the ALB. Only matches the exact apex/www hostnames; tenant subdomains (`*.p4tsites.com`) pass through untouched.

**Adding a tenant site** (zero DNS work per tenant): the wildcard CNAME + ALB host rule + ACM wildcard cert cover all `*.p4tsites.com` subdomains. A tenant publishes in the web app (Settings → Website → Publish) — no DNS, no cert, no ALB rule changes needed.

**Verify ACM cert status**:
```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:000000000000:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
  --region us-east-1 --query 'Certificate.Status' --no-cli-pager
# Expected: "ISSUED"
```

**Verify ALB host rule is live** (the `*.p4tsites.com` → pilot-web TG rule):
```bash
ALB_DNS="pilot-production-alb-xxxxxxxxxx.us-east-1.elb.amazonaws.com"
curl -k -s -o /dev/null -w "%{http_code}" -H "Host: anything.p4tsites.com" "https://${ALB_DNS}/api/health"
# Expected: 200 (pilot-web serving on *.p4tsites.com via the host-header rule)
# The -k flag is needed because the ALB DNS doesn't match the *.p4tsites.com SNI cert.
```

**Verify the app-level host rewrite (MANDATORY companion canary — TS-BUG-1, 2026-08-26)**: the ALB canary above proves *routing* only — it does NOT prove the Next.js proxy rewrote the host. This gap is exactly what let the slug-URL login wall ship. The app-level canary:
```bash
curl -sI https://<published-slug>.p4tsites.com/ | grep -iE "HTTP/|x-middleware-rewrite"
# Expected: HTTP/2 200 + x-middleware-rewrite: /sites/<published-slug>/
# A 307 to /dashboard (→ /login) means the proxy did NOT rewrite — app-layer fault, not ALB.
```
App-layer note: [`frontend/apps/web/src/proxy.ts`](../../frontend/apps/web/src/proxy.ts) (Next.js 16 convention — `middleware.ts` deprecated) reads the client `Host` header **directly** (`request.headers.get("host")`) because `request.nextUrl.hostname` is not reliable behind the ALB (TS-BUG-1 root cause; react-engineer rule §37). The ALB preserves the client Host header — never add host-rewriting at the ALB or Cloudflare layer.

**Verify apex redirect** (Cloudflare edge):
```bash
curl -s -o /dev/null -w "%{http_code} redirect:%{redirect_url}" https://p4tsites.com
# Expected: 301 redirect:https://pilotfortrades.com/
curl -s -o /dev/null -w "%{http_code} redirect:%{redirect_url}" https://www.p4tsites.com
# Expected: 301 redirect:https://pilotfortrades.com/
```

---

## 19. ECS Task Deployment Troubleshooting

Operational patterns learned from production incidents. Use these when ECS tasks are cycling, health checks are failing, or deployments are stuck.

---

### 19.1 Watch-and-Run Pattern (no sleep)

> **Rule**: Never use `sleep N` to "guess" when an ECS task status will change. Instead, watch the AWS Console UI and run the status check command **only when you see the status change in the UI**. This avoids false negatives from timing mismatches and means you're always checking at the right moment.

**Operator workflow:**

1. Start the command in the terminal — ready to run but **do not press Enter yet**
2. Watch the ECS Console → Services → `pilot-web` → Tasks tab
3. When the UI shows the status you expect (e.g., task goes from PENDING to RUNNING, or health changes from Unknown to Healthy/Unhealthy), **then** run the command

**Status check command — run on demand:**

```bash
echo "=== ECS task status at $(date -u '+%H:%M:%S UTC') ===" && \
for TASK in $(aws ecs list-tasks --cluster pilot-production --service-name pilot-web \
  --desired-status RUNNING --query 'taskArns[*]' --output text --region us-east-1 2>/dev/null); do
  aws ecs describe-tasks --cluster pilot-production --tasks "$TASK" \
    --query "tasks[0].{Health:healthStatus,Status:lastStatus,TaskDef:taskDefinitionArn,Started:startedAt}" \
    --output json --region us-east-1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
rev=d['TaskDef'].split(':')[-1]
print(f'  rev{rev}  Health:{d[\"Health\"]}  Status:{d[\"Status\"]}  Started:{d[\"Started\"]}')
" 2>/dev/null
done && \
echo "" && \
echo "=== ALB target health ===" && \
aws elbv2 describe-target-health \
  --target-group-arn "arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/pilot-production-web/xxxxxxxxxxxxxxxx" \
  --query 'TargetHealthDescriptions[*].{IP:Target.Id,State:TargetHealth.State}' \
  --output table --region us-east-1
```

> **Note**: `macOS does not have `watch`**. Do not use `watch -n 5 '...'` — it is not installed by default. Use the watch-and-run pattern above instead.

---

### 19.2 Force a Specific Task Definition Revision

When ECS keeps launching tasks from an old revision (e.g., `rev:1` instead of `rev:4`), explicitly pin the service to the desired revision:

```bash
# Check which task definition each deployment is using
aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-web \
  --query 'services[0].{TaskDef:taskDefinition,Deployments:deployments[*].{Status:status,TaskDef:taskDefinition,Running:runningCount,Desired:desiredCount}}' \
  --output json --region us-east-1 | python3 -m json.tool

# Force a specific revision — replaces any stale deployments
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-web \
  --task-definition "pilot-production-web:4" \
  --force-new-deployment \
  --no-cli-pager \
  --region us-east-1 | python3 -c "
import sys,json
svc=json.load(sys.stdin)['service']
print(f'TaskDef pinned to: {svc[\"taskDefinition\"]}')
print(f'Primary deployment: {svc[\"deployments\"][0][\"taskDefinition\"]}')
"
```

> **Why this happens**: ECS can have multiple concurrent `ACTIVE` deployments (from previous `force-new-deployment` calls) that compete with the `PRIMARY` deployment. Each active deployment has its own task replacement loop. Always check `deployments[*]` when tasks seem to start on the wrong revision.

---

### 19.3 Clear Multiple Active Deployments

When `describe-services` shows multiple deployments (e.g., `PRIMARY` on rev:4, `ACTIVE` on rev:1, `ACTIVE` on rev:3), forcing a new deployment on the desired revision cancels the stale ones:

```bash
# Show all current deployments
aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-web \
  --query 'services[0].deployments[*].{Status:status,TaskDef:taskDefinition,Running:runningCount,Desired:desiredCount,State:rolloutState}' \
  --output table --region us-east-1

# Cancel stale deployments by forcing the desired revision
# ECS will drain tasks from ACTIVE deployments and converge to the new PRIMARY
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-web \
  --task-definition "pilot-production-web:4" \
  --force-new-deployment \
  --no-cli-pager \
  --region us-east-1 > /dev/null
echo "Stale deployments cancelled — ECS will converge to rev:4"
```

The old `ACTIVE` deployments will drain and their `Desired` count will drop to 0. Only the new `PRIMARY` deployment remains.

---

### 19.4 Register a New Task Definition Revision

When you need to change a container health check, environment variable, or image without a full Terraform apply:

```bash
# Step 1: Export current task definition as JSON
TASK_DEF=$(aws ecs describe-task-definition \
  --task-definition "pilot-production-web:1" \
  --query 'taskDefinition' \
  --output json --region us-east-1)

# Step 2: Modify the JSON with python3 (example: remove healthCheck)
NEW_TASK_DEF=$(echo "$TASK_DEF" | python3 -c "
import sys, json
td = json.load(sys.stdin)
# Example: remove container health check
del td['containerDefinitions'][0]['healthCheck']
# Remove non-editable fields before re-registering
for key in ['taskDefinitionArn','revision','status','requiresAttributes',
            'placementConstraints','compatibilities','registeredAt','registeredBy']:
    td.pop(key, None)
print(json.dumps(td))
")

# Step 3: Register the new revision
aws ecs register-task-definition \
  --cli-input-json "$NEW_TASK_DEF" \
  --query 'taskDefinition.{Revision:revision,Family:family}' \
  --output json --region us-east-1 | python3 -m json.tool

# Step 4: Update service to use the new revision
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-web \
  --task-definition "pilot-production-web:NEW_REVISION" \
  --force-new-deployment \
  --no-cli-pager \
  --region us-east-1 > /dev/null
echo "Service updated ✅"
```

> **Important**: Always update the corresponding Terraform resource (`modules/compute/main.tf`) to match, or the next `terraform apply` will revert your change. The task definition registered via CLI and the Terraform definition must stay in sync.

---

### 19.5 Container Health Check Behavior in Fargate Alpine Images

**Known behavior (2026-07-05)**: Container-level health checks using `curl` or `wget` targeting `localhost:PORT` or `127.0.0.1:PORT` **fail inside Fargate tasks running Alpine Linux** (`node:20-alpine` base), even when:
- `curl` is installed in the image (`apk add curl`)
- `wget` is used as an alternative
- `127.0.0.1` is used instead of `localhost` (to bypass IPv6)
- The Next.js server is confirmed listening and healthy (ALB external check passes)

**Root cause**: Fargate's network namespace isolation affects loopback interface connectivity within Alpine containers. The loopback (`127.0.0.1` / `::1`) is not reachable from the container's process space in the same way as a standard Docker environment.

**Solution**: Remove the container-level health check and rely solely on the ALB target group health check. The ALB probe (HTTP from the load balancer to the container's private IP) works correctly and is the authoritative health signal.

```bash
# Verify ALB is the sole health check (correct for pilot-web)
aws ecs describe-task-definition \
  --task-definition "pilot-production-web:4" \
  --query 'taskDefinition.containerDefinitions[0].healthCheck' \
  --output json --region us-east-1
# Expected output: null (no container health check)

# Verify ALB target is healthy
aws elbv2 describe-target-health \
  --target-group-arn "arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/pilot-production-web/xxxxxxxxxxxxxxxx" \
  --query 'TargetHealthDescriptions[*].{IP:Target.Id,State:TargetHealth.State}' \
  --output table --region us-east-1
# Expected: healthy
```

**What "UNKNOWN" health status means in ECS console**: When `healthCheck` is `null` in the task definition, ECS reports the container health as `UNKNOWN` permanently. This is **correct and expected** — it means "no container health check defined." The task will not be killed for health reasons. ALB unhealthy threshold still applies.

**This fix is persisted in Terraform** — `modules/compute/main.tf` has the `healthCheck` block removed for the pilot-web container. Future `terraform apply` will not re-add it.

---

### 19.6 Post-Deploy: Sync ALL Services + Deploy Canary (the last step of EVERY deploy)

> **This section is the post-build half of one deploy flow.** The full flow is:
> 1. **Build + push images** — §8.1 (backend: one build → `pilot/api`, `pilot/worker`, `pilot/beat`) + §8.3 (web: `frontend/` build context + Cognito build-args)
> 2. **Image hygiene check** — §19.7 (run on the fresh image **before** any push)
> 3. **Migration verify** — §9.2 / §9.7 (prod `alembic current` == repo head, **before** the service sync)
> 4. **Service sync** — this section (Step 1 below)
> 5. **Deploy canary** — this section (the 5-check block at the end)
>
> **Branch model**: this repo has no `main` branch — it uses `dev`/`qa`/`demo`/`prod`. Builds come from the latest dev/feature branch that represents the code to deploy. Record the branch + commit SHA before building.

**When**: After **every** `terraform apply` touching `module.compute`, every manual task-definition registration (§19.4), and every image push. Make this the last step of every deploy — no exceptions (see Founder-Period Deploy Policy below).

**Why (real incident, 2026-08-09)**: Terraform `apply` registers new task-definition revisions but does **not** force services onto them. During the TELNYX-INT-1 deploy, `pilot-api` stayed on rev 5 (latest was 6), `pilot-celery-beat` on rev 1 (latest 3), and `pilot-celery-worker` on rev 2 (latest 3). The new Telnyx env vars (`SMS_CARRIER=telnyx`, `PILOT_PLATFORM_SMS_NUMBER`) were absent in the running containers, so the production double-opt-in SMS **silently never sent** — no error anywhere, just a missing audit row. Symptom was found via prod DB (`user_sms_consent_audit` had `attested` but no `double_opt_in_sent`), not via logs.

> **⚠️ `:latest` tagging means revision parity ≠ image parity** (discovered 2026-08-25, INT-BUG-1). ECR images are tagged `:latest`; a task-def revision points at the tag, not a digest. A `--force-new-deployment` pulls whatever `:latest` is *at that moment* — so if no fresh image was pushed, even a "successful" sync runs the old code, and the revision-number loop below cannot see it. **Always build + push fresh images (§8.1/§8.3) before the sync**, and verify image-digest parity in the canary (check 1 below). Rollback corollary: pinning a service to a *prior revision* does not roll back code under `:latest` — re-push the prior known-good digest as `:latest` first (digests are recorded at every deploy for exactly this).

#### Migration-Verify Step (non-skippable — run BEFORE the service sync)

After any `terraform apply` touching `module.compute` **or** any deploy carrying a new migration: tunnel → `alembic current` on prod must equal repo head **before** the service sync below. See §9.2 / §9.7 for the full procedure. If prod is behind head → **STOP** — return to the Architect for a chain review before applying anything. If prod is at head but was stamped (not upgraded), run the row-level verify per §9.6 to confirm migration-embedded seed rows actually exist — `alembic_version == head` proves the revision marker, not the data.

#### Step 1 — Sync all services (copy-paste: one script, one-at-a-time order, automatic steady-state + verification)

This script syncs all four services one at a time (`pilot-celery-worker` → `pilot-celery-beat` → `pilot-api` → `pilot-web`), waiting for steady state between each, then verifies revision parity + image-digest parity + startup logs. **Paste the entire block into your terminal and let it run.**

```bash
#!/bin/bash
# ── §19.6 Service Sync + Verification (one at a time) ──────────────
# Prerequisites: fresh images already pushed (§8.1/§8.3), hygiene check passed
# (§19.7), migration verified (§9.2/§9.7). Run from repo root.
set -euo pipefail
AWS_REGION="us-east-1"
CLUSTER="pilot-production"

# ── ECR :latest digests (captured post-push — used for digest-parity check) ────
ECR_DIGESTS=$(aws ecr describe-images --repository-name pilot/api --image-ids imageTag=latest --query 'imageDetails[0].imageDigest' --output text --region "$AWS_REGION")
WEB_ECR_DIGEST=$(aws ecr describe-images --repository-name pilot/web --image-ids imageTag=latest --query 'imageDetails[0].imageDigest' --output text --region "$AWS_REGION")

# ── Helper: verify a single service (revision + digest + logs) ─────────────────
verify_service() {
  local SVC="$1"
  local EXPECTED_DIGEST="$2"

  # Revision parity
  local FAMILY=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SVC" \
    --query 'services[0].taskDefinition' --output text --region "$AWS_REGION")
  local RUNNING_REV=$(echo "$FAMILY" | grep -o '[0-9]*$')
  local FAMILY_NAME=$(echo "$FAMILY" | sed 's|.*/||; s|:[0-9]*$||')
  local LATEST_REV=$(aws ecs describe-task-definition --task-definition "$FAMILY_NAME" \
    --query 'taskDefinition.revision' --output text --region "$AWS_REGION")
  local REV_STATUS=$([ "$RUNNING_REV" = "$LATEST_REV" ] && echo "✅" || echo "⚠️ STALE")

  # Image-digest parity
  local TASK_ARN=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name "$SVC" \
    --desired-status RUNNING --query 'taskArns[0]' --output text --region "$AWS_REGION")
  local RUNNING_DIGEST=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
    --query 'tasks[0].containers[0].imageDigest' --output text --region "$AWS_REGION")
  local DIGEST_STATUS=$([ "$RUNNING_DIGEST" = "$EXPECTED_DIGEST" ] && echo "✅" || echo "⚠️ DIGEST MISMATCH")

  echo "  $SVC: rev $FAMILY_NAME:$RUNNING_REV/$LATEST_REV $REV_STATUS  |  digest $DIGEST_STATUS"
  echo "    ECR:     $EXPECTED_DIGEST"
  echo "    Running: $RUNNING_DIGEST"

  # Startup log spot-check (last 10 min, no ERROR/template-loader failures)
  local LOG_GROUP="/ecs/$SVC"
  local SINCE=$(python3 -c "import time; print(int((time.time() - 600) * 1000))")
  local ERRORS=$(aws logs filter-log-events --log-group-name "$LOG_GROUP" \
    --start-time "$SINCE" --filter-pattern "ERROR" \
    --query 'events[*].message' --output text --region "$AWS_REGION" 2>/dev/null | head -5)
  if [ -n "$ERRORS" ]; then
    echo "    ⚠️ ERROR lines in startup logs (last 10 min):"
    echo "$ERRORS" | sed 's/^/      /'
  else
    echo "    ✅ No ERROR lines in startup logs (last 10 min)"
  fi
}

# ── Sync each service: update → wait for stable → verify ───────────────────────
# One-at-a-time order: worker → beat → api → web (workers stable first, API last
# among backend, web last)
SERVICES=("pilot-celery-worker" "pilot-celery-beat" "pilot-api" "pilot-web")

for SVC in "${SERVICES[@]}"; do
  # Determine the ECR digest for this service (api/worker/beat share the backend image)
  if [ "$SVC" = "pilot-web" ]; then
    EXPECTED_DIGEST="$WEB_ECR_DIGEST"
  else
    EXPECTED_DIGEST="$ECR_DIGESTS"
  fi

  echo ""
  echo "━━━ Syncing $SVC ━━━"
  aws ecs update-service --cluster "$CLUSTER" --service "$SVC" \
    --force-new-deployment --no-cli-pager --region "$AWS_REGION" > /dev/null
  echo "  Triggered — waiting for steady state..."
  aws ecs wait services-stable --cluster "$CLUSTER" --services "$SVC" --region "$AWS_REGION"
  echo "  ✅ $SVC stable"
  verify_service "$SVC" "$EXPECTED_DIGEST"
done

# ── Final revision loop (all 4 must show ✅ current) ───────────────────────────
echo ""
echo "━━━ Final Revision Check ━━━"
for SVC in pilot-api pilot-celery-worker pilot-celery-beat pilot-web; do
  FAMILY=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SVC" \
    --query 'services[0].taskDefinition' --output text --region "$AWS_REGION")
  RUNNING_REV=$(echo "$FAMILY" | grep -o '[0-9]*$')
  FAMILY_NAME=$(echo "$FAMILY" | sed 's|.*/||; s|:[0-9]*$||')
  LATEST_REV=$(aws ecs describe-task-definition --task-definition "$FAMILY_NAME" \
    --query 'taskDefinition.revision' --output text --region "$AWS_REGION")
  STATUS=$([ "$RUNNING_REV" = "$LATEST_REV" ] && echo "✅ current" || echo "⚠️ STALE")
  echo "  $SVC: running=$FAMILY_NAME:$RUNNING_REV latest=$FAMILY_NAME:$LATEST_REV $STATUS"
done

echo ""
echo "━━━ Service sync complete — now run the Deploy Canary below ━━━"
```

> **Note**: `pilot-web` (the Next.js service) is included in the loop — its family name is `pilot-production-web` in some revisions; the script handles this automatically via `describe-services`.

> **Addendum (2026-08-10)**: prod task definitions must set **explicit values for every mode-toggle env var** — `SMS_CARRIER`, `TELNYX_10DLC_MOCK`, `TEST_ENDPOINT_ENABLED`, `ENVIRONMENT`. Any toggle left unset in the task def falls through to code defaults (or worse, historically, to a baked `.env` — see §19.7) and can silently flip behavior. When a new toggle env var is added to the codebase, adding it explicitly to the Terraform container `environment` lists is part of the same change.

#### Deploy Canary (run as the last step of EVERY deploy — no exceptions)

After the service sync above, run all 5 checks. Any check fails → **STOP**: roll back manually before any second attempt (pin the service to the prior task-definition revision; §16 lists the steps but was never written up in full); escalate to the Architect.

| # | Check | Command / assertion | Pass condition |
|---|---|---|---|
| 1 | Revision + image-digest sync | Step 1 final loop (all 4 ✅ current) **+** each running task digest == ECR `:latest` digest | All 4 services ✅ current + all digests match |
| 2 | API health | `curl -sf https://api.pilotfortrades.com/api/v1/health/celery` | HTTP 200, `"status":"healthy"` |
| 3 | OpenAPI sentinel paths | Verify against repo `backend/openapi.json` (see below) | All sentinel paths present |
| 4 | Migration parity | `alembic current` on prod (tunnel, §9.2) == repo `alembic heads` | Revisions match |
| 5 | Image hygiene | `docker run --rm --entrypoint sh pilot-web:latest -c 'ls /app/.env 2>&1'` (§19.7) — use `pilot-web:latest` for the web image, `pilot-api:latest` for the backend image (these are the local Docker tags from §8.1/§8.3 build commands) | "No such file or directory" |

> **Check 3 — OpenAPI sentinel paths (prod-correct method)**: the live `/openapi.json` endpoint is **intentionally disabled in production** (`openapi_url=None` in [`backend/app/main.py`](../../backend/app/main.py) — no API surface exposure until developer onboarding). Instead, verify the sentinel paths against the repo's committed `backend/openapi.json` (manually generated for dev), combined with the image-digest parity from check 1 as proof the deployed image matches that code:
>
> ```bash
> python3 -c "
> import json
> with open('backend/openapi.json') as f:
>     spec=json.load(f)
> need=['/api/v1/signup/{tenant_id}/phone/consent','/api/v1/signup/{tenant_id}/phone/send-optin','/api/v1/tenant-site','/api/v1/public/tenant-sites/{slug}','/api/v1/invoices/{invoice_id}/signoff','/api/v1/jobs/{job_id}/signoff-context','/api/v1/users/me/mfa-status','/api/v1/settings/tenant/mfa-required']
> missing=[p for p in need if p not in spec['paths']]
> print('MISSING:',missing) if missing else print('✅ all sentinels present')
> "
> ```

**OpenAPI Sentinel List** (maintained here — extend on each shipped batch that adds API surface):

| Sentinel path | Proves deployed batch |
|---|---|
| `/api/v1/signup/{tenant_id}/phone/consent` + `/api/v1/signup/{tenant_id}/phone/send-optin` | PLATFORM-SMS-B1 (double opt-in) |
| `/api/v1/tenant-site` + `/api/v1/public/tenant-sites/{slug}` | C-B16 (tenant sites) |
| `/api/v1/invoices/{invoice_id}/signoff` + `/api/v1/jobs/{job_id}/signoff-context` | CE-1 (sign-off) |
| `/api/v1/users/me/mfa-status` + `/api/v1/settings/tenant/mfa-required` | MFA-WIRE-1 |

> **Maintenance note**: extend this list on each shipped batch that adds API surface. Add the new sentinel paths to the `need` list in the check 3 assertion above.

#### Quick-Verify Scripts (run anytime to check deployment health)

These standalone scripts verify the same things the §19.6 canary checks, but can be run independently at any time — before a deploy, after a deploy, or during incident triage.

**Script 1 — Revision + image-digest parity (all 4 services)**:

```bash
#!/bin/bash
# ── Revision + Digest Parity Check (all 4 ECS services) ────────────────────────
# Run from repo root. Verifies every service is on the latest task-def revision
# AND the running image digest matches ECR :latest.
AWS_REGION="us-east-1"
CLUSTER="pilot-production"

ECR_API_DIGEST=$(aws ecr describe-images --repository-name pilot/api --image-ids imageTag=latest --query 'imageDetails[0].imageDigest' --output text --region "$AWS_REGION")
ECR_WEB_DIGEST=$(aws ecr describe-images --repository-name pilot/web --image-ids imageTag=latest --query 'imageDetails[0].imageDigest' --output text --region "$AWS_REGION")

echo "━━━ Revision + Digest Parity ━━━"
for SVC in pilot-api pilot-celery-worker pilot-celery-beat pilot-web; do
  FAMILY=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SVC" \
    --query 'services[0].taskDefinition' --output text --region "$AWS_REGION")
  RUNNING_REV=$(echo "$FAMILY" | grep -o '[0-9]*$')
  FAMILY_NAME=$(echo "$FAMILY" | sed 's|.*/||; s|:[0-9]*$||')
  LATEST_REV=$(aws ecs describe-task-definition --task-definition "$FAMILY_NAME" \
    --query 'taskDefinition.revision' --output text --region "$AWS_REGION")
  REV_STATUS=$([ "$RUNNING_REV" = "$LATEST_REV" ] && echo "✅" || echo "⚠️ STALE")

  TASK_ARN=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name "$SVC" \
    --desired-status RUNNING --query 'taskArns[0]' --output text --region "$AWS_REGION" 2>/dev/null)
  if [ "$TASK_ARN" = "None" ] || [ -z "$TASK_ARN" ]; then
    echo "  $SVC: $REV_STATUS rev | ⚠️ NO RUNNING TASK"
  else
    RUNNING_DIGEST=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
      --query 'tasks[0].containers[0].imageDigest' --output text --region "$AWS_REGION" 2>/dev/null || echo "unknown")
    if [ "$SVC" = "pilot-web" ]; then EXPECTED="$ECR_WEB_DIGEST"; else EXPECTED="$ECR_API_DIGEST"; fi
    DIGEST_STATUS=$([ "$RUNNING_DIGEST" = "$EXPECTED" ] && echo "✅" || echo "⚠️ MISMATCH")
    echo "  $SVC: $REV_STATUS rev ($RUNNING_REV/$LATEST_REV) | $DIGEST_STATUS digest"
  fi
done
```

**Script 2 — Full deploy canary (5 checks)**:

```bash
#!/bin/bash
# ── Deploy Canary (5 checks) — run after every deploy ──────────────────────────
# Run from repo root. All 5 must pass.
AWS_REGION="us-east-1"
CLUSTER="pilot-production"
ALB_DNS="pilot-production-alb-xxxxxxxxxx.us-east-1.elb.amazonaws.com"

echo "━━━ Deploy Canary — 5 Checks ━━━"

# Check 1: Revision + digest (uses Script 1 above — paste it here or run separately)
echo "Check 1: See Script 1 above for revision + digest parity"

# Check 2: API health
echo "Check 2: API health"
curl -sf https://api.pilotfortrades.com/api/v1/health/celery && echo " ✅" || echo " ❌ FAIL"

# Check 3: OpenAPI sentinel paths
echo "Check 3: OpenAPI sentinel paths"
python3 -c "
import json
with open('backend/openapi.json') as f: spec=json.load(f)
need=['/api/v1/signup/{tenant_id}/phone/consent','/api/v1/signup/{tenant_id}/phone/send-optin','/api/v1/tenant-site','/api/v1/public/tenant-sites/{slug}','/api/v1/invoices/{invoice_id}/signoff','/api/v1/jobs/{job_id}/signoff-context','/api/v1/users/me/mfa-status','/api/v1/settings/tenant/mfa-required']
missing=[p for p in need if p not in spec['paths']]
print('  ✅ all sentinels present') if not missing else print('  ❌ MISSING:',missing)
"

# Check 4: Migration parity (requires SSH tunnel — see §9.2)
echo "Check 4: Migration parity (requires SSH tunnel to prod RDS)"
echo "  Run: cd backend && alembic current  (with tunnel up) — must match repo head"

# Check 5: Image hygiene
echo "Check 5: Image hygiene"
docker run --rm --entrypoint sh pilot-web:latest -c 'ls /app/.env 2>&1' | grep -q "No such file" && echo "  ✅ PASS" || echo "  ❌ FAIL"
```

**Script 3 — ALB host-rule canary (C-B16 tenant-sites)**:

```bash
#!/bin/bash
# ── ALB Host-Rule Canary (*.p4tsites.com → pilot-web) ──────────────────────────
ALB_DNS="pilot-production-alb-xxxxxxxxxx.us-east-1.elb.amazonaws.com"
echo "━━━ ALB Host-Rule Canary ━━━"
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Host: anything.p4tsites.com" "https://${ALB_DNS}/api/health")
BODY=$(curl -k -sf -H "Host: anything.p4tsites.com" "https://${ALB_DNS}/api/health" 2>/dev/null || echo "FAILED")
echo "  HTTP $HTTP_CODE | Body: $BODY"
[ "$HTTP_CODE" = "200" ] && echo "  → ✅ PASS" || echo "  → ❌ FAIL"
# The -k flag is needed because the ALB DNS doesn't match the *.p4tsites.com SNI cert.
```

---

#### Founder-Period Deploy Policy (codified — plan §3 standing policy)

- **Manual deploys retained through the founder beta** — no CI/CD auto-deploy work (GitHub Actions deferred to Phase 7, §20.5).
- **Off-hours only · one deploy at a time · announced** — Tom posts before start + after canary passes.
- **Every deploy ends with the service sync (Step 1) + canary (5 checks)** — no exceptions.
- **Migrations run BEFORE the service sync** (§9 principle) — the new image's fail-loud loaders fail on boot if their seed rows are absent; the additive chain is forward-compatible with the old image, so syncing services first risks downtime.
- **Record the deploy commit SHA + ECR digests at every deploy** — needed for the `:latest` rollback corollary (re-push the prior known-good digest as `:latest`).

#### Cross-references

- **§8.1** — backend image build + push (one build → `pilot/api`, `pilot/worker`, `pilot/beat`)
- **§8.3** — web image build + push (`frontend/` build context + Cognito build-args)
- **§9.2 / §9.7** — prod Alembic procedure + full migration-sync workflow (the migration-verify step above)
- **§16** — rollback procedures (an outline only: pin the service to the prior task-def revision; `:latest` rollback corollary above)
- **§19.7** — image hygiene check (run on the fresh image before any push)

---

### 19.7 Docker Images Must Never Contain `.env` (`.dockerignore` ≠ `.gitignore`)

**Incident (2026-08-10)**: the backend Dockerfile's `COPY . .` shipped the local dev `backend/.env` into the production images at `/app/.env` because no `.dockerignore` existed — `.gitignore` has **zero effect** on Docker build contexts; only `.dockerignore` filters `COPY`. Pydantic settings precedence (real env vars > `.env` file) meant ECS task-def values won for anything explicitly set, but any variable **absent** from the task def silently fell through to dev values — this is how `TELNYX_10DLC_MOCK=true` (set in a local `.env` during TELNYX-INT-1 testing) reached the prod worker. The baked file also carried live third-party credentials (SendGrid, QuickBooks, Telnyx dev key, Turnstile; all rotated after discovery — see PROVENANCE.md), `TEST_ENDPOINT_ENABLED=true`, and `ENVIRONMENT=dev` — the latter two were saved only by explicit task-def overrides.

**Fix (landed 2026-08-10)**: `backend/.dockerignore` excludes `.env`, `.env.*` (except `!.env.example`), `.venv/`, caches, `celerybeat-schedule*`, `tests/`, `prompts/`, `admin_tools/`.

**Verify after any Dockerfile or build-context change:**

```bash
# Canonical one-liner (TEST-UPLIFT-1A, 2026-08-27) — checks both default images:
./admin-tools/check_image_hygiene.sh
# Or check specific images:
./admin-tools/check_image_hygiene.sh pilot-api:latest pilot-web:latest pilot-celery_worker:latest
# Exit 0 = all clean; exit 1 = violation found.
```

**Raw form (for transparency — what the script runs under the hood):**

```bash
# Use the local Docker image tag from the §8.1/§8.3 build commands:
#   pilot-web:latest  — for the web dashboard image (from §8.3: -t pilot-web:latest)
#   pilot-api:latest  — for the backend image (from §8.1: -t pilot-api:latest)
docker run --rm --entrypoint sh pilot-web:latest -c 'ls /app/.env 2>&1'
# Expected: No such file or directory
```

**If it ever recurs**: rebuild with the `.dockerignore` in place → push → `--force-new-deployment` → **rotate any third-party credentials present in the baked file** (image layers persist in ECR until the digests are deleted via `aws ecr batch-delete-image`). **Exception**: never blind-rotate `ENCRYPTION_KEY` — first confirm which key prod actually resolves; rotating a key that encrypted live data makes it undecryptable.

**TEST-UPLIFT-1A (2026-08-27)**: The `check_image_hygiene.sh` script caught stale local `pilot-celery_worker:latest` / `pilot-celery_beat:latest` tags (May 19 builds, pre-`.dockerignore`) with `/app/.env` baked in. Tom rebuilt + deployed all 4 images to ECR on 2026-08-27 — ECR images (api, worker, beat, web) all pass clean. The local stale tags still point at old image IDs; `docker pull` from ECR or a local rebuild updates them. Prod is clean.

---

## 20. Manual E2E Test Execution

> **CI/CD status**: GitHub Actions CI/CD is deferred to Phase 7 (post-beta). The nightly E2E workflow (`.github/workflows/e2e-nightly.yml`) exists but does **not** run automatically until Phase 7 secrets are configured. Use the manual procedures in this section before beta launches, major deploys, or any change that touches the quote-to-cash, SMS, or invoicing flows.

---

### 20.1 Overview — Harness Architecture

The E2E harness has two independent tiers. Each tier has its own prerequisites, run procedure, and pass/fail definition. **Run Tier 1 first — it requires no live AWS stack.**

| Tier | Tool | Target | DB | Prerequisite |
|---|---|---|---|---|
| **Tier 1** | `pytest` + `httpx` | FastAPI directly (no browser) | Isolated `pilot_e2e_db` (Docker, port 5433) | Docker running locally |
| **Tier 2** | Playwright | Web browser → app.pilotfortrades.com | Production (read-only seed checks) | Profile B `light` or higher; `pnpm` installed |

**Key files**:
- [`docker-compose.e2e.yml`](../../docker-compose.e2e.yml) — isolated Postgres (port 5433) + Redis (port 6380) for Tier 1
- `backend/.env.e2e` _(private)_ — Tier 1 env config (`SMS_CARRIER=mock`, Stripe test keys)
- [`backend/tests/e2e/`](../../backend/tests/e2e/) — 5 critical path Tier 1 test files
- [`frontend/apps/web/src/__tests__/e2e/`](../../frontend/apps/web/src/__tests__/e2e/) — 5 Playwright specs

**Critical paths covered**:

| CP | Scenario | Tier 1 | Tier 2 |
|---|---|---|---|
| CP-1 | Auth + Tenant Isolation (login, RBAC, cross-tenant 404) | ✅ | ✅ |
| CP-2 | Quote-to-Cash (create quote → send → accept → invoice → pay) | ✅ | ✅ (smoke) |
| CP-3 | Dispatch + Field Sync (create job → assign → time entry → expense → complete) | ✅ | ✅ (smoke) |
| CP-4 | Customer SMS Thread (outbound → inbound reply → unread count) | ✅ | ✅ (smoke) |
| CP-5 | Dunning Cycle (overdue invoice → reminder task → throttle → paid) | ✅ | ✅ (smoke) |

> **Tier 2 scope note**: Playwright specs are UI smoke tests — they verify that key pages render with seeded data and interaction states are correct. They are **not** full workflow E2E tests (no real Stripe charges, no real SMS). Full workflow automation for external-API flows requires Phase 7 CI/CD + sandbox credentials.

---

### 20.2 Pre-Launch Checklist — When to Run

Run the full E2E suite manually in these situations:

| Trigger | Tier 1 | Tier 2 | Notes |
|---|---|---|---|
| Before beta customer access (Profile C) | ✅ Required | ✅ Required | Both tiers must pass before flipping Profile C |
| After any backend batch deploy | ✅ Required | Optional | Tier 1 catches API regressions |
| After any frontend batch deploy | Optional | ✅ Required | Tier 2 catches UI regressions |
| After Alembic migration runs in production | ✅ Required | — | Schema changes can silently break queries |
| Weekly during active beta development | ✅ Required | ✅ Required | Prevent regression accumulation |

---

### 20.3 Tier 1 — pytest Integration Tests (Isolated DB)

Tier 1 runs entirely locally — no AWS access needed. It spins up isolated Docker services (Postgres port 5433, Redis port 6380), seeds the E2E DB, and runs `pytest` with the `--e2e` marker.

**Prerequisites**:
- Docker Desktop running locally
- Python virtualenv active: `source backend/.venv/bin/activate`
- `backend/.env.e2e` file exists with valid test credentials

```bash
# ── Step 1: Start isolated E2E Docker services (separate from local dev stack) ──
# Note: Uses docker-compose.e2e.yml — does NOT conflict with docker-compose.yml
# Postgres on port 5433; Redis on port 6380
docker compose -f docker-compose.e2e.yml up -d

# Verify they are healthy before proceeding
docker compose -f docker-compose.e2e.yml ps
# Expected: Both postgres-e2e and redis-e2e show "healthy" or "running"

# ── Step 2: Seed the E2E database ─────────────────────────────────────────────
cd backend
source .venv/bin/activate

# Apply migrations to the E2E DB (uses .env.e2e which points to port 5433)
DATABASE_URL=$(grep DATABASE_URL .env.e2e | cut -d= -f2) \
  .venv/bin/alembic upgrade head 2>&1 | tail -5

# Seed E2E data (Groups A + B + C + D)
python tests/e2e/seed_e2e_db.py
# Expected last line: "E2E DB seeded successfully ✅"

# ── Step 3: Run the 5 critical path tests ─────────────────────────────────────
pytest -m e2e --tb=short -v 2>&1 | tee /tmp/e2e-tier1-run.txt

# ── Step 4: Review results ────────────────────────────────────────────────────
tail -20 /tmp/e2e-tier1-run.txt
# PASS gate: 0 failed, all 5 critical paths reported

# ── Step 5: Run a specific critical path only (if debugging one scenario) ──────
pytest -m e2e -v tests/e2e/cp2_quote_to_cash/ --tb=long

# ── Step 6: Tear down isolated services when done ─────────────────────────────
docker compose -f docker-compose.e2e.yml down
echo "E2E services stopped"
```

**Pass / fail definition**:
- ✅ PASS: `0 failed` across all 5 CP test files
- ❌ FAIL: Any failure in CP-1 or CP-2 blocks a beta launch (auth + billing are P0)
- ⚠️ WARN: Any failure in CP-3 through CP-5 should be investigated before launch

**Troubleshooting**:

```bash
# E2E DB port already in use (conflict with local dev stack tunnel)
lsof -i :5433
# Kill the conflicting process, then restart docker compose -f docker-compose.e2e.yml up -d

# seed_e2e_db.py fails — reset and retry
docker compose -f docker-compose.e2e.yml down -v   # wipes DB volume
docker compose -f docker-compose.e2e.yml up -d
python tests/e2e/seed_e2e_db.py

# Inspect E2E DB directly (useful when a test fails on a query)
PGPASSWORD=e2e_password psql "host=127.0.0.1 port=5433 dbname=pilot_e2e user=pilot_user" \
  -c "SELECT count(*) FROM tenant;"
```

---

### 20.4 Tier 2 — Playwright Web Smoke Tests (Requires Live Stack)

Tier 2 runs against the live web dashboard at `app.pilotfortrades.com`. The stack must be at **Profile B `light`** or higher before running Playwright.

**Prerequisites**:
- Profile B `light` or higher is active (see §3): `./infrastructure/scripts/profile-b-app.sh light`
- Health checks pass (see §12): `curl -sf https://api.pilotfortrades.com/api/v1/health/celery`
- `pnpm` installed globally and `frontend/` dependencies installed
- Production seed data present (Group C + D — these are the seeded fixtures Playwright reads)

```bash
# ── Step 1: Verify the stack is live ──────────────────────────────────────────
curl -sf https://app.pilotfortrades.com/api/health | python3 -m json.tool
# Expected: {"status":"ok","service":"pilot-web"}

curl -sf https://api.pilotfortrades.com/api/v1/health/celery | python3 -m json.tool
# Expected: {"status":"healthy","workers_active":...}

# ── Step 2: Install Playwright browsers (first time only) ─────────────────────
cd frontend
pnpm --filter web exec playwright install chromium
# Installs Chromium browser binary — only needed once per machine

# ── Step 3: Run the 5 Playwright specs ────────────────────────────────────────
pnpm --filter web exec playwright test \
  src/__tests__/e2e/cp1_auth_rbac.playwright.ts \
  src/__tests__/e2e/cp2_quote_to_cash.playwright.ts \
  src/__tests__/e2e/cp3_dispatch_field_sync.playwright.ts \
  src/__tests__/e2e/cp4_customer_sms.playwright.ts \
  src/__tests__/e2e/cp5_dunning_cycle.playwright.ts \
  --reporter=list 2>&1 | tee /tmp/e2e-tier2-run.txt

# ── Step 4: View HTML report (optional — opens browser) ───────────────────────
pnpm --filter web exec playwright show-report

# ── Step 5: Run a single spec in headed mode (for debugging) ──────────────────
pnpm --filter web exec playwright test \
  src/__tests__/e2e/cp2_quote_to_cash.playwright.ts \
  --headed --slowMo=500
```

**Pass / fail definition**:
- ✅ PASS: All 5 specs pass (Playwright exit code 0)
- ❌ FAIL: Any failure in `cp1_auth_rbac` blocks beta launch (authentication is P0)
- ⚠️ WARN: Failures in cp2–cp5 indicate seeded data is missing or a page component regressed

**What Tier 2 does NOT test**:
- Real Stripe charges (W-05): Playwright reaches the invoice page but does not click a "Pay Now" Stripe link
- Real SMS sends (W-01): Verifies the SMS UI renders; does not invoke Telnyx
- Voice AI (W-06): Not covered by any Playwright spec

---

### 20.5 CI/CD Note — GitHub Actions (Phase 7, Deferred)

The nightly workflow file [`/.github/workflows/e2e-nightly.yml`](../../.github/workflows/e2e-nightly.yml) exists and is syntactically valid. It is currently **inactive** because the following GitHub Actions secrets are not yet configured:

| Secret | Used For | Status |
|---|---|---|
| `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | ECR pull + ECS health check in CI | ⏳ Phase 7 |
| `E2E_DB_PASSWORD` | Isolated Postgres in CI runner | ⏳ Phase 7 |
| `STRIPE_TEST_SECRET_KEY` | Stripe test-mode calls in Tier 1 | ⏳ Phase 7 |
| `TELNYX_API_KEY` (mock bypass) | SMS_CARRIER=mock; no real key needed | ✅ Not required (mock) |

**Do not configure these secrets until Phase 7 CI/CD work begins.** Until then, run the E2E suite manually using the procedures in §20.3 and §20.4 before any launch-gate decision.

---

## 17.2 Cloudflare DNS Zone Inventories (HIBERNATE-1)

> **Context**: DNS management moved from GoDaddy/Route 53 to Cloudflare (2026-09-07). The committed zone exports are the authoritative DNS inventory for restart recreation.

### pilotfortrades.com zone

**Export file**: `dev-docs/devops/godaddy-cloudflare-archive/pilotfortrades.com/cloudlflare-pilotfortrades.com.txt` _(private)_ (filename typo preserved as-committed)

**NS**: `raina.ns.cloudflare.com` / `viddy.ns.cloudflare.com`

| Record | Type | Target | HIBERNATE-1 Action |
|---|---|---|---|
| `@` (apex) | CNAME | `dxxxxxxxxxxxx1.cloudfront.net` (DNS-only) | Updated — was `dxxxxxxxxxxxx2.cloudfront.net` (old dist destroyed) |
| `www` | CNAME | `dxxxxxxxxxxxx1.cloudfront.net` (DNS-only) | Updated — same as apex |
| `api` | CNAME | ALB | **DELETED** — NXDOMAIN |
| `app` | CNAME | ALB | **DELETED** — NXDOMAIN |
| `_<validation-name>` | CNAME | ACM validation | KEPT — cert renewal |
| `emXXXX` | CNAME | SendGrid | KEPT |
| `s1._domainkey` | CNAME | SendGrid DKIM | KEPT |
| `s2._domainkey` | CNAME | SendGrid DKIM | KEPT |
| MX ×5 | MX | Google Workspace | KEPT |
| SPF/DKIM/DMARC/site-verification TXT | TXT | various | KEPT |

### p4tsites.com zone

**Export file**: `dev-docs/devops/godaddy-cloudflare-archive/p4sites.com/cloudflare-p4tsites.com.txt` _(private)_ (folder typo preserved as-committed)

| Record | Type | Target | HIBERNATE-1 Action |
|---|---|---|---|
| `*` (wildcard) | CNAME | ALB | **DELETED** — NXDOMAIN |
| `@` / `www` | AAAA | `100::` (proxied) | KEPT — edge redirect |
| `_<validation-name>` | CNAME | ACM validation | KEPT |
| SPF/DMARC TXT | TXT | lockdown | KEPT |

### Restart DNS recreation

At restart, recreate the 3 deleted records from the zone exports:
1. `api.pilotfortrades.com` CNAME → new ALB DNS name
2. `app.pilotfortrades.com` CNAME → new ALB DNS name
3. `*.p4tsites.com` CNAME → new ALB DNS name

Also update apex/www CNAMEs if the CloudFront distribution is recreated by `terraform apply` (the manually-created distribution `EXXXXXXXXXXX1` / `dxxxxxxxxxxxx1.cloudfront.net` will be replaced by the TF-managed one).

---

## 21. Restart Runbook (HIBERNATE-1 → Reactivation)

> **Operationalizes**: [`batch-hibernate-1-design.md`](../architecture-design/batch-designs/batch-hibernate-1-design.md) §F (Restart Contract)
> **Estimate**: ~1 working day
> **Prerequisites**: Tom's external secret backups (1Password/age), the `dbbackups/` pair, the committed Cloudflare zone exports, the TF state backend intact.
> **Update (2026-11-14)**: both Cognito user pools were deleted. Terraform recreates the prod pool with new IDs (update the pool and client IDs in Secrets Manager and the web/mobile env files, re-attach the Lambda triggers); recreate the dev pool and test users per `aws-cognito-dev-setup-prod-mirror.md`. Allow an extra hour or two.

### Step 1 — Terraform apply (full)

```bash
cd infrastructure/terraform/environments/production
# First: restore the deletion-protection flags toggled in Task 6
#   compute/main.tf: enable_deletion_protection = true
#   database/main.tf: deletion_protection = true, skip_final_snapshot = false
#   monitoring/main.tf: prevent_destroy = true (Config bucket)
terraform init
terraform plan    # review — expect full recreate (VPC, subnets, NAT, ALB, ECS, RDS, Redis, etc.)
terraform apply
```

**Note**: The manually-created CloudFront distribution (`EXXXXXXXXXXX1`) will conflict with the TF-managed one. Before `terraform apply`, either:
- Import the manual distribution into TF state: `terraform import module.compute.aws_cloudfront_distribution.marketing EXXXXXXXXXXX1`, OR
- Delete the manual distribution and let TF create a fresh one (update Cloudflare CNAMEs to the new domain)

**RDS comes back EMPTY** (ADR-0016 model — no snapshot restore).

### Step 2 — Secrets re-entry

TF re-creates the 11 secret containers (values empty). Tom re-enters all values from his external backup:
- `pilot/prod/database` — DB URL (new password from TF's `random_password`)
- `pilot/prod/redis` — Redis URLs
- `pilot/prod/sendgrid` — API key (may need rotation if backup is stale)
- `pilot/prod/telnyx` — API key + public key + messaging profile ID + platform SMS number
- `pilot/prod/stripe` — secret/publishable/webhook/connect keys
- `pilot/prod/quickbooks` — client ID/secret/webhook verifier
- `pilot/prod/encryption` — Fernet key
- `pilot/prod/cognito` — user pool ID
- `pilot/prod/google_maps` — API key
- `pilot/prod/turnstile` — secret key
- `pilot/prod/gpu` — GPU URLs (update with new private IP)

### Step 3 — ECR rebuild + push (all 4 images)

```bash
# API
cd backend && docker build -t pilot/api .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 000000000000.dkr.ecr.us-east-1.amazonaws.com
docker tag pilot/api:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/api:latest

# Worker, Beat — same pattern (multi-stage Dockerfile in backend/)
# Web
cd frontend && pnpm --filter web build
cd apps/web && docker build -t pilot/web .
docker tag pilot/web:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
```

### Step 4 — Database provisioning

```bash
# Via bastion SSH tunnel (after bastion is running)
python provision_schema.py
alembic upgrade head
python seed_prod_db.py --mode seed --stripe-mode test
# Optional: targeted restore from dbbackups/backup_20260907_082049.sql
```

### Step 5 — GPU start

```bash
cd infrastructure/scripts && ./generate-infra-state.sh
# GPU userdata re-pulls Whisper/Ollama to fresh /models (~15-20 min)
# Update pilot/prod/gpu secret with new private IP if changed
```

### Step 6 — Cognito Lambda re-attach

Full-carry `update-user-pool` call (§14.5) — re-attaches all 3 Lambda triggers + new KMS CMK ARN:

```bash
aws cognito-idp update-user-pool --user-pool-id us-east-1_XXXXXXXXX --region us-east-1 \
  --auto-verified-attributes email \
  --device-configuration ChallengeRequiredOnNewDevice=false,DeviceOnlyRememberedOnUserPrompt=false \
  --lambda-config '{"PostConfirmation":"arn:aws:lambda:us-east-1:000000000000:function:pilot-production-post-confirmation","PostAuthentication":"arn:aws:lambda:us-east-1:000000000000:function:pilot-production-post-authentication","CustomEmailSender":{"LambdaVersion":"V1_0","LambdaArn":"arn:aws:lambda:us-east-1:000000000000:function:pilot-production-custom-email-sender"},"KMSKeyID":"<NEW_KMS_KEY_ARN>"}'
```

Verify: branded-email smoke (ForgotPassword) + DKIM/SPF check.

### Step 7 — Profile scripts + smoke

```bash
cd infrastructure/scripts && ./generate-infra-state.sh
./profile-b-app.sh light    # smoke (no Voice AI)
./profile-status.sh         # all rows ✅
```

### Step 8 — DNS recreation

In Cloudflare console, recreate the 3 deleted records from the §17.2 zone exports:
1. `api.pilotfortrades.com` CNAME → new ALB DNS (DNS-only)
2. `app.pilotfortrades.com` CNAME → new ALB DNS (DNS-only)
3. `*.p4tsites.com` CNAME → new ALB DNS (DNS-only)

If TF recreated the CloudFront distribution, update apex/www CNAMEs to the new CF domain.

### Step 9 — Marketing site (optional)

Either keep the hold page (default) or redeploy the Next.js export:
```bash
cd frontend && pnpm --filter marketing build
aws s3 sync apps/marketing/out/ s3://pilot-production-marketing/ --delete --region us-east-1
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*" --region us-east-1
# Remove the CloudFront 403/404 error response mapping if switching to full site
```

### Step 10 — Third-party reactivation

- Telnyx: re-provision numbers + campaign re-association
- Stripe: re-enable test webhook endpoints (Stripe auto-disables failing endpoints)
- Google Maps: un-restrict key if restricted during hiatus
- GitHub: re-enable deploy workflows if disabled

### Step 11 — Smoke + cost verification

- §19.6 deploy canary + founder-path smoke
- Cost Explorer week-1 check against the ~$888 MVP baseline
- Remove the `pilot-hibernation-floor` budget if desired
