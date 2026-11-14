# Infrastructure Scripts — Pilot for Trades Production-Spec Environment

> **⚠️ HIBERNATION NOTICE (2026-09-07, HIBERNATE-1):** These scripts are **dormant** until project restart.
> The AWS infrastructure they manage (VPC, ECS, RDS, Redis, NAT, ALB, GPU, bastion) has been **deeply torn down** per ADR-0020/0021.
> `.infra-state.env` is **stale** — do NOT regenerate it; `generate-infra-state.sh` re-runs at restart after `terraform apply`.
> The marketing hold page is served by a manually-recreated CloudFront distribution (ID: `EXXXXXXXXXXX1`) + S3 bucket `pilot-production-marketing`.
> DNS is now Cloudflare (not Route 53 — the R53 zone was deleted). The profile-off.sh Route 53 comment has been corrected.
> See `dev-docs/devops/aws-ops-runbook.md` §21 (Restart Runbook) for the full reactivation procedure.

## 1. Overview

These scripts manage Pilot for Trades production AWS resources from your local machine using the AWS CLI. They implement a **profile-based cost management** model: each profile enforces a specific set of running resources (EC2 instances, ECS services, site mode) suitable for a particular use case — from the ~$102/month cost floor to full Voice AI at ~$562/month. All scripts use `.infra-state.env` for live AWS resource IDs and feature flags, and write to `.env.profiles` so that `profile-status.sh` can show Expected vs Actual state at any time.

---

## 2. Prerequisites

Before running any script, verify these three requirements:

**AWS CLI authenticated as `pilot-admin`:**
```bash
aws sts get-caller-identity
# Expected output must show: "Account": "000000000000"
# If not: aws sso login  (or reconfigure credentials)
```

**`.infra-state.env` must exist:**
```bash
ls infrastructure/scripts/.infra-state.env
# If missing, regenerate it:
cd infrastructure/scripts && ./generate-infra-state.sh
```

**SSH key loaded (for RDS tunnel via bastion):**
```bash
ssh-add -l
# Should show: ~/.ssh/pilot_admin_ed25519
# If not: ssh-add ~/.ssh/pilot_admin_ed25519
```

---

## 3. Quick Start — Daily Workflow

```bash
cd infrastructure/scripts

# ── Morning: bring up app for development ─────────────────────────────────────
./profile-b-app.sh light    # UI/UX, QuickBooks, scheduling testing (no Voice AI)
# or:
./profile-b-app.sh ai       # Full Voice AI testing (GPU on — $562/month)

./profile-status.sh         # Run until all rows show ✅ (ECS: ~2-3 min, GPU: ~8-20 min)

# ── Done for the day: shut down to cost floor ──────────────────────────────────
./profile-off.sh
./profile-status.sh         # Confirm everything is shut down
```

---

## 4. Script Reference

| Script | What It Does | Est. Monthly Cost |
|---|---|---|
| `profile-off.sh` | Shuts down all stoppable resources. GPU stopped, all ECS at 0 tasks, Bastion stopped, site → `coming_soon`. Marketing site remains visible via S3/CloudFront. | ~$102 |
| `profile-a-marketing.sh` | Marketing + form processing only. GPU stopped, ECS API/Worker/Beat at 1 task each, pilot-web at 0, Bastion running, site → `live`. Serves `/api/v1/marketing/*` endpoints. | ~$148 |
| `profile-b-app.sh light` | Web + mobile app UI testing. Same as Profile A but adds `pilot-web` at 1 task. GPU stopped. | ~$170 |
| `profile-b-app.sh ai` | Full Voice AI. GPU running, all ECS at 2/2/1/1 tasks, Bastion running, site → `live`. Whisper + Ollama (llama3.1:8b) available. | ~$562 |
| `profile-c-full.sh` | Full production state — same resources as `profile-b-app.sh ai`. Use before demo sessions. Confirmation prompt enforces intent. | ~$562 |
| `profile-status.sh` | **Read-only.** Shows current state vs expected state for the active profile in a color-coded Expected vs Actual table. Also shows RDS/Redis data layer, endpoint health, and CloudWatch alarms. Always safe to run — no AWS mutations. | — |
| `generate-infra-state.sh` | Discovers live AWS resource IDs and feature flags, writes `.infra-state.env`. Run after any `terraform apply` that creates or replaces resources. | — |

---

## 5. State Files

Two generated files track infrastructure and profile state. Both are gitignored — never commit them.

**`.infra-state.env`** — Resource IDs and infrastructure flags:
```bash
GPU_INSTANCE_ID="i-0xxxxxxxxxxxxxxxxx"
BASTION_INSTANCE_ID="i-0xxxxxxxxxxxxxxxxx"
CLOUDFRONT_DIST_ID="XXXXXXXXXXXXX"
ECS_CLUSTER="pilot-production"
INFRA_NETWORKING="true"
INFRA_DATABASE="true"
INFRA_STORAGE="true"
INFRA_BASTION="true"
INFRA_GPU="true"       # false until AWS vCPU quota approved
INFRA_ECS="true"       # false until Phase 6 ECS deployment
```
Written by `generate-infra-state.sh`. Required by all profile scripts at startup.

**`.env.profiles`** — Active profile name and timestamp:
```bash
PROFILE_SET="app-light"                 # one of: off | marketing | app-light | app-ai | full
PROFILE_SET_AT="2026-07-04T16:30:00Z"  # ISO 8601 UTC
```
Written by each profile script at the end of execution. Read by `profile-status.sh` to determine Expected state.

---

## 6. When to Run `generate-infra-state.sh`

Run after any `terraform apply` that creates or replaces infrastructure:

- After initial Terraform deployment (any phase)
- After GPU instance is provisioned for the first time (Phase 4 — requires AWS vCPU quota approval for `p4d.24xlarge` or `g4dn.xlarge`)
- After ECS services are deployed (Phase 6)
- If `.infra-state.env` is missing or shows stale resource IDs

```bash
cd infrastructure/scripts
./generate-infra-state.sh
cat .infra-state.env   # verify IDs look correct
```

---

## 7. Cost Reference

| Profile | GPU | ECS Tasks | Monthly Cost |
|---|---|---|---|
| off | stopped | 0 / 0 / 0 / 0 | ~$102 |
| marketing | stopped | 1 API / 1 Worker / 1 Beat / 0 Web | ~$148 |
| app-light | stopped | 1 / 1 / 1 / 1 | ~$170 |
| app-ai / full | running | 2 / 2 / 1 / 1 | ~$562 |

**Cost floor breakdown (~$102/month):** RDS PostgreSQL ~$28 · ElastiCache Redis ~$13 · NAT Gateway ~$32 · ALB ~$18 · S3 + CloudFront ~$2 · Route 53 ~$1 · Bastion EIP (reserved) ~$3.50

The GPU (`g4dn.xlarge`) accounts for ~$390/month when running — always stop it when not actively testing Voice AI.

For the full operational runbook including SSH tunnel setup, log access, and deployment procedures:
```
dev-docs/devops/aws-ops-runbook.md
```

---

## 8. Troubleshooting

**"Wrong AWS account" error on script startup**
```bash
aws sso login
# or reconfigure:
aws configure --profile pilot-admin
```

**".infra-state.env not found"**
```bash
cd infrastructure/scripts && ./generate-infra-state.sh
```

**"GPU not provisioned" (INFRA_GPU=false)**
AWS vCPU quota increase is required for `g4dn.xlarge`. See deployment status doc:
`dev-docs/devops/aws-deployment-status.md`. Submit quota request via AWS Service Quotas console for `Running On-Demand G and VT instances` in `us-east-1`.

**"ECS tasks not reaching running state"**
```bash
# Tail logs for the failing service:
aws logs tail /ecs/pilot-api --follow --region us-east-1
aws logs tail /ecs/pilot-celery-worker --follow --region us-east-1
aws logs tail /ecs/pilot-web --follow --region us-east-1
```
Check CloudWatch alarms and ECS task stopped reasons:
```bash
aws ecs describe-tasks --cluster pilot-production \
  --tasks $(aws ecs list-tasks --cluster pilot-production --service-name pilot-api \
    --desired-status STOPPED --query 'taskArns[0]' --output text) \
  --query 'tasks[0].stoppedReason' --output text --region us-east-1
```

**"SSH tunnel to RDS not working"**
1. Confirm bastion is running: `profile-status.sh` or `profile-b-app.sh light`
2. Confirm your IP is in `terraform.tfvars` under `allowed_ssh_cidr_blocks`
3. Confirm SSH key is loaded: `ssh-add ~/.ssh/pilot_admin_ed25519`
4. Tunnel command: `ssh -L 5432:pilot-production.xxxx.us-east-1.rds.amazonaws.com:5432 pilot-bastion -N`

**`profile-status.sh` shows "No profile has been set yet"**
Run any profile script first (e.g., `./profile-b-app.sh light`) — this creates `.env.profiles`.
