# ~~DevOps Engineer Prompt — `profile-status.sh`~~ SUPERSEDED

> **⚠️ This prompt is superseded by [`aws-profile-scripts-v2-devops-engr-prompt.md`](aws-profile-scripts-v2-devops-engr-prompt.md).**
> The v2 prompt covers profile script updates, `.env.profiles` state tracking, a full revised `profile-status.sh` spec with Expected vs Actual table, and the `README.md`. Do not use this file.

---

**Mode**: Pilot DevOps Engineer  
**File to create**: `infrastructure/scripts/profile-status.sh`  
**Effort estimate**: 1–2 hours  
**Platform**: macOS + AWS CLI + bash  
**Reference scripts** (study these before writing — follow their exact patterns):
- `infrastructure/scripts/profile-c-full.sh` ← primary pattern reference
- `infrastructure/scripts/profile-off.sh`
- `infrastructure/scripts/generate-infra-state.sh`

---

## ⚠️ MANDATORY STOP

Before writing a single line of code, read the following files in full:

1. `infrastructure/scripts/profile-c-full.sh` — the exact bash patterns this script must replicate
2. `infrastructure/scripts/.infra-state.env.example` — all available `INFRA_*` flags and resource ID variables
3. `dev-docs/devops/aws-ops-runbook.md` §12 (Health Checks) — the inline health check block the script is formalizing
4. `dev-docs/devops/aws-infrastructure-as-built.md` §1 and §3 — the full resource list to cover

---

## Purpose

`profile-status.sh` is a **read-only, no-side-effects** status script. It queries every Pilot for Trades production resource and prints a clean, color-coded status dashboard. It never changes any resource state.

**Run it any time to answer the question: "What is running right now and what is it costing me?"**

---

## Critical Design Rules

1. **Read-only, no side effects** — the script NEVER calls `aws ec2 start-instances`, `aws ecs update-service`, `aws s3 cp`, or any other mutating command. Status queries only.

2. **No confirmation prompt** — unlike the profile scripts, status is always safe to run. No `read -p "Proceed? (yes/no)"`.

3. **Source `.infra-state.env` exactly like the other scripts** — same pattern as `profile-c-full.sh` lines 25–33. If the file is missing, print a clear error and exit.

4. **Never hardcode resource IDs** — all IDs come from `.infra-state.env` (populated by `generate-infra-state.sh`). For resources not in `.infra-state.env` (RDS, Redis), use dynamic AWS CLI queries — see the query patterns in the runbook.

5. **Failed individual queries must NOT abort the script** — wrap each AWS CLI call in error handling so a single resource query failure prints an `ERROR` status for that row and continues. Use `|| echo "ERROR"` or `2>/dev/null || echo "UNKNOWN"` patterns. Do NOT use `set -e` for the query blocks.

6. **`check_skip()` for unprovisioned resources** — reuse the exact `check_skip()` pattern from `profile-c-full.sh`: if `INFRA_GPU=false`, GPU rows print `[NOT PROVISIONED]`. If `INFRA_ECS=false`, ECS rows print `[NOT PROVISIONED]`.

7. **Color output** — use ANSI codes (safe on macOS Terminal and VS Code integrated terminal):
   - `GREEN='\033[0;32m'`  → healthy / running / live
   - `YELLOW='\033[1;33m'` → stopped-but-expected (cost floor state) or unknown
   - `RED='\033[0;31m'`    → error / alarm / unhealthy
   - `NC='\033[0m'`        → reset

8. **`set -eo pipefail` at top** — same as other scripts, but see rule 5: individual query blocks use `|| echo "UNKNOWN"` to isolate failures.

---

## Script Structure

Follow this exact section order:

### Header Block (same pattern as other scripts)
```bash
#!/usr/bin/env bash
set -eo pipefail
# ── Profile Status: Read-Only Infrastructure Dashboard ───────────────────────
# Queries all Pilot for Trades production resources and prints current state.
# No resource state is changed. Safe to run at any time, any frequency.
# ─────────────────────────────────────────────────────────────────────────────
```

### Load `.infra-state.env` (exact pattern from profile-c-full.sh lines 25–33)

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_STATE_FILE="$SCRIPT_DIR/.infra-state.env"
if [ ! -f "$INFRA_STATE_FILE" ]; then
  echo "ERROR: .infra-state.env not found."
  echo "Run first: cd infrastructure/scripts && ./generate-infra-state.sh"
  exit 1
fi
source "$INFRA_STATE_FILE"
```

### Static vars (same as other scripts)
```bash
ACCOUNT_ID="000000000000"
REGION="us-east-1"
CLUSTER="${ECS_CLUSTER:-pilot-production}"
MARKETING_BUCKET="pilot-production-marketing"
DOMAIN="pilotfortrades.com"
```

### Color helper functions
```bash
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "  ${RED}❌ $1${NC}"; }
skip() { echo "  ⏳ $1 [NOT PROVISIONED]"; }
```

### Account verification (same as other scripts — exit if wrong account)
```bash
echo "=== Pilot Production Status Dashboard ==="
echo "$(date '+%Y-%m-%d %H:%M:%S %Z')"
ACTUAL_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text --region "$REGION" 2>/dev/null || echo "ERROR")
echo "Account: $ACTUAL_ACCOUNT"
[ "$ACTUAL_ACCOUNT" = "$ACCOUNT_ID" ] || { echo "ERROR: Wrong AWS account — aborting"; exit 1; }
echo ""
```

---

## Resource Sections (display in this order)

### Section 1: Infrastructure Flags
Print a compact one-line summary of what `.infra-state.env` says is provisioned:

```
── Infrastructure State (from .infra-state.env) ──────────────────────────────
  Networking: true   Database: true   Storage: true
  Bastion: true      GPU: false       ECS: true
```

### Section 2: EC2 Instances (Bastion + GPU)

**Bastion:**
- Query: `aws ec2 describe-instances --instance-ids "$BASTION_INSTANCE_ID"` → get `State.Name` and `PublicIpAddress`
- If `INFRA_BASTION=false` → `skip()`
- States: `running` → `ok()` green, `stopped` → `warn()` yellow (normal cost-saving state), anything else → `warn()` yellow

**GPU:**
- Query: `aws ec2 describe-instances --instance-ids "$GPU_INSTANCE_ID"` → get `State.Name` and `PrivateIpAddress`
- If `INFRA_GPU=false` → `skip()` with note: "GPU not yet provisioned — pending AWS vCPU quota increase"
- States: `running` → `ok()` green + show private IP, `stopped` → `warn()` yellow (normal), anything else → `warn()`

### Section 3: ECS Services

Query all four services in a single call:
```bash
aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services pilot-api pilot-celery-worker pilot-celery-beat pilot-web \
  --query 'services[*].{Name:serviceName,Desired:desiredCount,Running:runningCount,Status:status}' \
  --output json --region "$REGION"
```

For each service, display: `Name | Desired: N | Running: N | Status`

Status logic per service:
- If `INFRA_ECS=false` → `skip()` for all four
- `desired=0 AND running=0` → `warn()` yellow "scaled to 0 (cost-floor state)"
- `running >= desired AND desired > 0` → `ok()` green
- `running < desired AND desired > 0` → `err()` red "only N of N tasks running"
- Beat special rule: `desired > 1` → `err()` red "⚠️ Beat desired count > 1 — this causes duplicate task execution! Scale back to 1 immediately."

### Section 4: Data Layer (RDS + Redis)

**RDS:**
```bash
aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,MultiAZ:MultiAZ,StorageGB:AllocatedStorage}' \
  --output json --region "$REGION"
```
- `available` → `ok()` green
- `stopped` → `warn()` yellow "RDS is stopped — AWS auto-restarts after 7 days"
- anything else → `warn()` yellow + show actual status

**Redis:**
```bash
aws elasticache describe-cache-clusters \
  --cache-cluster-id pilot-production \
  --query 'CacheClusters[0].{Status:CacheClusterStatus,Node:CacheNodeType}' \
  --output json --region "$REGION"
```
- `available` → `ok()` green
- anything else → `warn()` yellow + show actual status

### Section 5: Marketing Site

Fetch `https://pilotfortrades.com/site-config.json` (silent curl, 5-second timeout):
```bash
CONFIG_MODE=$(curl -sf --max-time 5 "https://$DOMAIN/site-config.json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode','unknown'))" 2>/dev/null \
  || echo "unreachable")
```
- `live` → `ok()` green "Marketing site: live (forms active)"
- `coming_soon` → `warn()` yellow "Marketing site: coming_soon (forms offline)"
- `unreachable` → `err()` red "Marketing site unreachable"
- anything else → `warn()` yellow "Marketing site mode: $CONFIG_MODE"

Also verify `https://pilotfortrades.com` itself returns 200:
```bash
HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 5 "https://$DOMAIN" 2>/dev/null || echo "000")
```
- `200` → `ok()` green
- anything else → `err()` red "HTTP $HTTP_STATUS"

### Section 6: API + Web Dashboard Endpoints

Only query if `INFRA_ECS=true`:

**API:**
```bash
API_HTTP=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 5 "https://api.$DOMAIN/api/v1/health/celery" 2>/dev/null || echo "000")
```
- `200` → `ok()` green — also fetch and print the JSON response body (workers_active, broker_connected)
- `000` → `warn()` yellow "API unreachable (ECS may be at 0 tasks or still starting)"
- anything else → `err()` red "API returned HTTP $API_HTTP"

**Web Dashboard:**
```bash
WEB_HTTP=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 5 "https://app.$DOMAIN" 2>/dev/null || echo "000")
```
- `200` → `ok()` green
- `000` → `warn()` yellow "Web dashboard unreachable"
- anything else → `err()` red "Web dashboard returned HTTP $WEB_HTTP"

### Section 7: CloudWatch Alarms

```bash
ALARMS=$(aws cloudwatch describe-alarms \
  --state-value ALARM \
  --alarm-name-prefix "pilot-production" \
  --query 'MetricAlarms[*].AlarmName' \
  --output text --region "$REGION" 2>/dev/null || echo "")
```
- No alarms → `ok()` green "No CloudWatch alarms firing"
- Any alarms → `err()` red — list each alarm name on its own line

### Section 8: Inferred Profile + Estimated Cost

Based on what's running, deduce the current profile and compute estimated monthly cost:

**Profile inference logic** (check in order — first match wins):

| Condition | Inferred Profile | Est. Monthly |
|---|---|---|
| All ECS at 0 AND GPU stopped/not-provisioned AND Bastion stopped | **OFF (Cost Floor)** | ~$102 |
| API=1, Worker=1, Beat=1, Web=0, GPU stopped, Bastion running | **A: Marketing Only** | ~$148 |
| API=1, Worker=1, Beat=1, Web=1, GPU stopped, Bastion running | **B: Light (UI only)** | ~$170 |
| API=2, Worker=2, Beat=1, Web=1, GPU running, Bastion running | **B: AI / C: Beta** | ~$562 |
| Any other combination | **Custom (mixed state)** | ~$??? |

Display the inferred profile with color (yellow for OFF, green for A/B/C) and estimated monthly cost.

```
── Inferred Profile ──────────────────────────────────────────────────────────
  ⚠️  Profile: OFF (Cost Floor)
  Estimated monthly: ~$102
  To activate a profile: ./profile-a-marketing.sh | ./profile-b-app.sh light | etc.
```

---

## Final Summary Block

```
══════════════════════════════════════════════════════════════════════════════
Pilot Production Status — <TIMESTAMP>
  Resources checked: N
  ✅ Healthy: N    ⚠️ Warning: N    ❌ Error: N    ⏳ Not provisioned: N
══════════════════════════════════════════════════════════════════════════════
```

Exit code: `0` always (status is informational — errors are displayed, not thrown).

---

## File Permissions + Placement

```bash
# Script location
infrastructure/scripts/profile-status.sh

# Make executable
chmod +x infrastructure/scripts/profile-status.sh
```

---

## Runbook Update

After creating the script, add `profile-status.sh` to the existing §3 "Profile Commands — Quick Reference" section in `dev-docs/devops/aws-ops-runbook.md`:

```bash
# ── Status: Read-only dashboard of all resources ──────────────────────────────
./infrastructure/scripts/profile-status.sh
# → Shows current state of all resources, inferred profile, and estimated monthly cost
# → Read-only — does not change any resource state
# → Safe to run at any time
```

---

## Verification

After writing the script, run these checks yourself before marking complete:

```bash
# 1. Syntax check
bash -n infrastructure/scripts/profile-status.sh
echo "Syntax OK"

# 2. Confirm script is executable
ls -la infrastructure/scripts/profile-status.sh

# 3. Verify .infra-state.env exists (run generate-infra-state.sh first if not)
ls infrastructure/scripts/.infra-state.env

# 4. Dry-run against live AWS (requires aws CLI authenticated as pilot-admin)
./infrastructure/scripts/profile-status.sh
# Expected: full dashboard output with no bash errors

# 5. Verify it makes no changes — after running, confirm nothing was modified:
# - ECS desired counts unchanged
# - S3 site-config.json unchanged
# - No EC2 start/stop calls in AWS Console activity
```

---

## Definition of Done

- [ ] `profile-status.sh` created at `infrastructure/scripts/profile-status.sh`
- [ ] `chmod +x` applied
- [ ] `bash -n` syntax check passes
- [ ] Sources `.infra-state.env` using exact same pattern as `profile-c-full.sh`
- [ ] All 8 resource sections implemented with correct color coding
- [ ] `check_skip()` / `skip()` guards on GPU, ECS, and Bastion for unprovisiond resources
- [ ] Individual AWS CLI query failures print ERROR for that row and do not abort the script
- [ ] No mutating AWS CLI calls anywhere in the script
- [ ] No confirmation prompt
- [ ] Inferred profile + estimated monthly cost displayed
- [ ] Final summary block with counts
- [ ] Exit code always `0`
- [ ] `aws-ops-runbook.md` §3 updated with `profile-status.sh` entry
- [ ] Script tested against live AWS and output verified correct

---

## Completion Summary

When done, paste the following completion summary format:

```
## Completion Summary — profile-status.sh

**Date**: <date>
**Script location**: infrastructure/scripts/profile-status.sh
**Lines of code**: ~N
**Sections implemented**: 8/8
**Runbook updated**: §3 ✅

**Test run output** (paste first 20 lines):
<paste here>

**Verified no mutations**: ✅ (confirmed via AWS Console — no resource state changes)
```
