# DevOps Engineer Prompt — Profile Scripts v2 + Status Dashboard + README

**Mode**: Pilot DevOps Engineer  
**Effort estimate**: 3–4 hours  
**Platform**: macOS + AWS CLI + bash  

## Files to Create or Modify

| File | Action |
|---|---|
| `infrastructure/scripts/profile-off.sh` | Modify — add `.env.profiles` write |
| `infrastructure/scripts/profile-a-marketing.sh` | Modify — add `.env.profiles` write |
| `infrastructure/scripts/profile-b-app.sh` | Modify — add `.env.profiles` write |
| `infrastructure/scripts/profile-c-full.sh` | Modify — add `.env.profiles` write; **remove Phase 2 health checks** |
| `infrastructure/scripts/profile-status.sh` | **Replace** the existing `aws-profile-status-devops-engr-prompt.md` spec — full rewrite with Expected vs Actual table |
| `infrastructure/scripts/.env.profiles` | New file (gitignored) — written by profile scripts, read by status script |
| `infrastructure/scripts/README.md` | New file — explains all scripts for operators |

---

## ⚠️ MANDATORY STOP

Before writing a single line of code, read the following files in full:

1. `infrastructure/scripts/profile-c-full.sh` — current state, patterns to preserve, Phase 2 to remove
2. `infrastructure/scripts/profile-a-marketing.sh` — reference for profile script structure
3. `infrastructure/scripts/profile-b-app.sh` — reference, especially the MODE logic
4. `infrastructure/scripts/profile-off.sh` — reference for OFF script structure
5. `infrastructure/scripts/.infra-state.env.example` — all `INFRA_*` flags and resource ID variables
6. `dev-docs/devops/aws-ops-runbook.md` — understand the operational context

---

## Part 1 — Update All 5 Profile Scripts to Write `.env.profiles`

### What `.env.profiles` Contains

Every profile script writes this file at the **very end** of its execution (after all AWS changes are issued, as the last step before exit):

```bash
# infrastructure/scripts/.env.profiles
# Written by profile scripts. Read by profile-status.sh.
# Gitignored — machine-local state.
PROFILE_SET="off"                      # one of: off | marketing | app-light | app-ai | full
PROFILE_SET_AT="2026-07-04T16:30:00Z" # ISO 8601 UTC timestamp
```

### PROFILE_SET Values (exact — do not deviate)

| Script | Argument | `PROFILE_SET` value |
|---|---|---|
| `profile-off.sh` | — | `"off"` |
| `profile-a-marketing.sh` | — | `"marketing"` |
| `profile-b-app.sh` | `light` | `"app-light"` |
| `profile-b-app.sh` | `ai` | `"app-ai"` |
| `profile-c-full.sh` | — | `"full"` |

### Write Logic (add to the END of each script, after all AWS changes)

```bash
# ── Write profile state ───────────────────────────────────────────────────────
PROFILES_STATE_FILE="$SCRIPT_DIR/.env.profiles"
PROFILE_VALUE="<value from table above>"
cat > "$PROFILES_STATE_FILE" << EOF
# Written by $(basename "$0") on $(date -u '+%Y-%m-%dT%H:%M:%SZ')
# Read by profile-status.sh to show Expected vs Actual state.
# Gitignored — do not commit.
PROFILE_SET="${PROFILE_VALUE}"
PROFILE_SET_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
EOF
echo "  Profile state written: PROFILE_SET=${PROFILE_VALUE}"
```

For `profile-b-app.sh`, the value depends on `$MODE`:
```bash
if [ "$MODE" = "light" ]; then
  PROFILE_VALUE="app-light"
else
  PROFILE_VALUE="app-ai"
fi
```

### Add `.env.profiles` to `.gitignore`

Check that `.gitignore` at the project root (or `infrastructure/scripts/.gitignore`) already ignores `.env.profiles`. If not, add it next to the existing `.infra-state.env` entry:

```
infrastructure/scripts/.infra-state.env
infrastructure/scripts/.env.profiles
```

---

## Part 2 — Modify `profile-c-full.sh`: Remove Phase 2 Health Checks

`profile-c-full.sh` currently has two phases — Phase 1 (enforce state) and Phase 2 (7 health checks). **Remove Phase 2 entirely.** The status script now owns all health verification.

**Remove:**
- The `PASS=0` / `FAIL=0` / `check_pass()` / `check_fail()` / `check_skip()` helper variables and functions
- The `# ══ PHASE 2: Health checks ══` block and all 7 checks inside it
- The `sleep 60` wait between phases
- The final summary block that prints `Results: $PASS passed / $FAIL failed`

**Keep (Phase 1 only):**
- All the state-enforcement steps (GPU → running, Bastion → running, ECS task counts, site-config.json → live)
- The confirmation prompt
- The status table printed at the end (GPU state + ECS table)

**Add** the `.env.profiles` write block (Part 1 above) after the status table, as the final step before exit.

**Update the final message** to direct the operator to run `profile-status.sh`:

```bash
echo ""
echo "=== Profile C [full] Active ==="
echo "Cost: ~\$562/month (GPU + all ECS running)"
echo ""
echo "Next step: run profile-status.sh to verify all resources have reached target state."
echo "  ./profile-status.sh"
echo ""
echo "Re-run as many times as needed until all rows show ✅."
echo "GPU boot: ~3-5 min | Ollama model load: ~5-15 min | ECS tasks: ~2-3 min"
```

**Also update** the closing message in profiles A, B, and OFF similarly — add a line pointing to `profile-status.sh` for verification:

```bash
echo ""
echo "Run ./profile-status.sh to verify current state."
```

---

## Part 3 — Create `profile-status.sh` (Full Spec)

> **This replaces the earlier spec in `aws-profile-status-devops-engr-prompt.md`.** That prompt described a simpler status display. This version uses `PROFILE_SET` from `.env.profiles` to show Expected vs Actual.

### Design Rules

1. **Read-only, no side effects** — never calls `start-instances`, `update-service`, `s3 cp`, or any mutating command
2. **No confirmation prompt** — always safe to run
3. **Sources both `.infra-state.env` AND `.env.profiles`** — if `.infra-state.env` is missing, exit with error; if `.env.profiles` is missing, set `PROFILE_SET="unknown"` and continue (expected on first run before any profile script has been run)
4. **Failed queries must not abort the script** — wrap each AWS CLI call with `2>/dev/null || echo "ERROR"`. Use `set -eo pipefail` at top but individual queries use `|| echo "UNKNOWN"` to isolate
5. **Color output** (ANSI, safe on macOS Terminal and VS Code):
   - `GREEN='\033[0;32m'` → healthy / matches expected / live
   - `YELLOW='\033[1;33m'` → stopped but expected (cost floor) / starting / unknown
   - `RED='\033[0;31m'` → error / mismatch vs expected / alarm firing
   - `NC='\033[0m'` → reset

### Expected State by Profile

This table drives the Expected vs Actual display. The script contains this as a lookup (hardcoded — these are the canonical profile definitions):

| Profile | GPU | Bastion | pilot-api | pilot-celery-worker | pilot-celery-beat | pilot-web | Site mode |
|---|---|---|---|---|---|---|---|
| `off` | stopped | stopped | 0 | 0 | 0 | 0 | coming_soon |
| `marketing` | stopped | running | 1 | 1 | 1 | 0 | live |
| `app-light` | stopped | running | 1 | 1 | 1 | 1 | live |
| `app-ai` | running | running | 2 | 2 | 1 | 1 | live |
| `full` | running | running | 2 | 2 | 1 | 1 | live |
| `unknown` | — | — | — | — | — | — | — |

### Script Structure

```
Header block → source .infra-state.env → source .env.profiles → account verify →
Section 1: Profile banner →
Section 2: Expected vs Actual table →
Section 3: Data Layer (RDS + Redis) →
Section 4: Endpoint health checks →
Section 5: CloudWatch alarms →
Section 6: Summary counts
```

#### Section 1: Profile Banner

```
=== Pilot Production Status ===
2026-07-04 16:35:00 UTC
Account: 000000000000

Active profile: app-ai  (set 8 min ago)
```

"Set N min ago" = compute diff between `PROFILE_SET_AT` and now using `python3 -c "import datetime; ..."`.
If `PROFILE_SET="unknown"` → print `⚠️  No profile has been set yet. Run one of the profile scripts first.`

#### Section 2: Expected vs Actual Table

Print a table with 5 columns: Resource | Expected | Actual | Match | Notes

For each resource, compare the expected value (from the profile lookup) against the live AWS query:

```
── Resource State ────────────────────────────────────────────────────────────
Resource              Expected      Actual        Status    Notes
──────────────────────────────────────────────────────────────────────────────
GPU (g4dn.xlarge)     running       running       ✅
Bastion               running       running       ✅
ECS pilot-api         2 tasks       2 tasks       ✅
ECS pilot-celery-wrkr 2 tasks       2 tasks       ✅
ECS pilot-celery-beat 1 task        1 task        ✅
ECS pilot-web         1 task        0 tasks       ❌        Still starting (2 min ago)
Site mode             live          live          ✅
──────────────────────────────────────────────────────────────────────────────
```

**Color rules for Status column:**
- `✅` green — actual matches expected
- `❌` red — actual does not match expected (e.g., 0 tasks when 1 expected)
- `⚠️` yellow — resource not provisioned yet (`INFRA_GPU=false`, `INFRA_ECS=false`, etc.)
- `🔄` yellow — transitional state (EC2 `pending`/`stopping`, ECS `runningCount < desiredCount` but `desiredCount` correct)

**Notes column hints:**
- If GPU is `pending` (starting): "Booting... (~3-5 min). Ollama needs 5-15 min after boot."
- If GPU is `stopping`: "Stopping..."
- If ECS `runningCount < desiredCount`: "Still starting — check CloudWatch logs"
- If ECS `desiredCount=0` and expected=0: "(cost-floor state)"
- If Beat `desiredCount > 1`: "⚠️ DANGER: Beat must never exceed 1 — causes duplicate task execution!"

**AWS queries for actual state:**

```bash
# GPU state
GPU_STATE=$(aws ec2 describe-instances --instance-ids "$GPU_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")

# Bastion state
BASTION_STATE=$(aws ec2 describe-instances --instance-ids "$BASTION_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")

# ECS services — single call for all 4
ECS_JSON=$(aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services pilot-api pilot-celery-worker pilot-celery-beat pilot-web \
  --query 'services[*].{Name:serviceName,Desired:desiredCount,Running:runningCount}' \
  --output json --region "$REGION" 2>/dev/null || echo "[]")

# Site config mode
SITE_MODE=$(curl -sf --max-time 5 "https://$DOMAIN/site-config.json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode','unknown'))" \
  2>/dev/null || echo "unreachable")
```

Use `python3` to parse `ECS_JSON` for individual service values.

#### Section 3: Data Layer

Simple status queries — not part of the Expected vs Actual table (these are always-on services):

```
── Data Layer ────────────────────────────────────────────────────────────────
RDS PostgreSQL    available     db.t4g.micro   Multi-AZ: true    ✅
ElastiCache Redis available     cache.t4g.micro                  ✅
```

```bash
RDS_STATUS=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].DBInstanceStatus' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")

REDIS_STATUS=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id pilot-production \
  --query 'CacheClusters[0].CacheClusterStatus' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")
```

- `available` → ✅ green
- `stopped` → ⚠️ yellow "RDS stopped — auto-restarts after 7 days"
- anything else → ⚠️ yellow + show actual status

#### Section 4: Endpoint Health Checks

Only perform HTTP checks if `INFRA_ECS=true` AND the relevant service has `desiredCount > 0`. Otherwise print `[SKIPPED — service at 0 tasks]`.

```
── Endpoint Health ────────────────────────────────────────────────────────────
API health          https://api.pilotfortrades.com/api/v1/health/celery
  HTTP 200          ✅
  workers_active: 1   broker_connected: true   scheduled_tasks: 0

Web dashboard       https://app.pilotfortrades.com
  HTTP 200          ✅

Marketing site      https://pilotfortrades.com
  HTTP 200          ✅
```

```bash
# API health — fetch both status code and body
API_HTTP=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 8 \
  "https://api.$DOMAIN/api/v1/health/celery" 2>/dev/null || echo "000")
API_BODY=$(curl -sf --max-time 8 \
  "https://api.$DOMAIN/api/v1/health/celery" 2>/dev/null || echo "{}")

# Parse body fields (graceful — defaults to "?" if missing)
WORKERS_ACTIVE=$(echo "$API_BODY" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('workers_active','?'))" 2>/dev/null || echo "?")
BROKER_CONNECTED=$(echo "$API_BODY" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('broker_connected','?'))" 2>/dev/null || echo "?")
SCHEDULED_TASKS=$(echo "$API_BODY" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('scheduled_tasks','?'))" 2>/dev/null || echo "?")
```

Display:
- HTTP 200 → ✅ green + show `workers_active`, `broker_connected`, `scheduled_tasks`
- HTTP 000 → ⚠️ yellow "unreachable (service may be at 0 tasks or still starting)"
- other HTTP → ❌ red "HTTP $API_HTTP"

#### Section 5: CloudWatch Alarms

```
── CloudWatch Alarms ─────────────────────────────────────────────────────────
  ✅ No alarms firing
```

```bash
ALARM_COUNT=$(aws cloudwatch describe-alarms \
  --state-value ALARM \
  --alarm-name-prefix "pilot-production" \
  --query 'length(MetricAlarms)' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")
```

- `0` → ✅ green "No alarms firing"
- integer > 0 → ❌ red — list each alarm name and state reason
- `UNKNOWN` → ⚠️ yellow "Could not query alarms"

#### Section 6: Summary Footer

```
══════════════════════════════════════════════════════════════════════════════
Profile: app-ai | Set: 8 min ago
  ✅  7  resources match expected state
  ❌  1  resources do not match (pilot-web still starting)
  ⚠️   0  resources not yet provisioned

All resources match → System ready for use.
  (or)
1 resource(s) not at target state → re-run ./profile-status.sh in 60 seconds.
══════════════════════════════════════════════════════════════════════════════
```

Exit code: always `0` — status is informational.

---

## Part 4 — Create `infrastructure/scripts/README.md`

Create this file to explain the scripts directory to any operator (including future-Tom after time away). The README must cover:

### Required Sections

1. **Overview** — one paragraph explaining that these scripts manage Pilot for Trades production AWS resources. All scripts use `.infra-state.env` for resource IDs and `.env.profiles` to track current profile.

2. **Prerequisites** — what you need before running any script:
   - AWS CLI authenticated as `pilot-admin` (verify: `aws sts get-caller-identity`)
   - `.infra-state.env` must exist (run `./generate-infra-state.sh` after any `terraform apply` if missing)
   - SSH key `~/.ssh/pilot_admin_ed25519` loaded (verify: `ssh-add -l`)

3. **Quick Start** — the most common daily workflow:
   ```bash
   # Morning: bring up app for development
   ./profile-b-app.sh light    # or: ./profile-b-app.sh ai (for Voice AI)
   ./profile-status.sh         # run until all ✅

   # Done for the day: shut down to cost floor
   ./profile-off.sh
   ./profile-status.sh         # confirm everything shut down
   ```

4. **Script Reference Table** — one row per script:

| Script | What It Does | Estimated Monthly Cost |
|---|---|---|
| `profile-off.sh` | Shuts down all stoppable resources. GPU stopped, ECS at 0, Bastion stopped, site → coming_soon | ~$102 |
| `profile-a-marketing.sh` | Marketing + form processing. GPU stopped, ECS API/Worker/Beat at 1 task, Web=0, Bastion running, site → live | ~$148 |
| `profile-b-app.sh light` | Web + mobile UI testing. Same as A but adds pilot-web at 1 task | ~$170 |
| `profile-b-app.sh ai` | Full Voice AI. GPU running, all ECS at 2/2/1/1, Bastion running | ~$562 |
| `profile-c-full.sh` | Full production state (same resources as B ai). Use before customer-facing sessions | ~$562 |
| `profile-status.sh` | **Read-only.** Shows current state vs expected state for active profile. Run repeatedly until all ✅ | — |
| `generate-infra-state.sh` | Discovers live AWS resource IDs and writes `.infra-state.env`. Run after any `terraform apply`. | — |

5. **State Files** — explain the two generated files:
   - `.infra-state.env` — resource IDs and infrastructure flags. Written by `generate-infra-state.sh`. Gitignored.
   - `.env.profiles` — current profile name and when it was set. Written by profile scripts. Gitignored. Read by `profile-status.sh`.

6. **When to Run `generate-infra-state.sh`** — run after any `terraform apply` that creates or replaces resources. Required after GPU instance is provisioned for the first time.

7. **Cost Reference** — brief table of profile costs and the $102/month floor. Point to `dev-docs/devops/aws-ops-runbook.md` for the full runbook.

8. **Troubleshooting** — short list:
   - "Wrong AWS account" → run `aws sso login` or reconfigure CLI credentials
   - ".infra-state.env not found" → run `./generate-infra-state.sh`
   - "GPU not provisioned" → AWS vCPU quota increase required; see deployment status doc
   - "ECS tasks not reaching running" → check CloudWatch logs: `aws logs tail /ecs/pilot-api --follow`
   - "SSH tunnel not working" → ensure bastion is running and your IP is in `terraform.tfvars`

---

## Implementation Order

Complete in this sequence (each step depends on the previous):

1. **Part 1**: Add `.env.profiles` write block to all 5 profile scripts
2. **Part 2**: Remove Phase 2 health checks from `profile-c-full.sh`; add `profile-status.sh` pointer message to all 5 scripts
3. **Part 3**: Create `profile-status.sh`
4. **Part 4**: Create `README.md`
5. **Verify**: Run all 4 gitignore checks, bash syntax checks, and a live test run

---

## Verification Checklist

Run these before marking complete:

```bash
# 1. Syntax check all modified scripts
bash -n infrastructure/scripts/profile-off.sh
bash -n infrastructure/scripts/profile-a-marketing.sh
bash -n infrastructure/scripts/profile-b-app.sh
bash -n infrastructure/scripts/profile-c-full.sh
bash -n infrastructure/scripts/profile-status.sh
echo "All syntax checks passed"

# 2. Verify .env.profiles is gitignored
grep -r "\.env\.profiles" .gitignore infrastructure/scripts/.gitignore 2>/dev/null
# Should show at least one match

# 3. Verify .env.profiles does NOT exist in git tracking
git ls-files infrastructure/scripts/.env.profiles
# Should return nothing (empty)

# 4. Live test — set a profile and check status
cd infrastructure/scripts
./profile-a-marketing.sh   # answer "yes" to proceed
cat .env.profiles          # verify PROFILE_SET="marketing" and timestamp

./profile-status.sh        # verify profile banner shows "marketing (set N sec ago)"
                           # verify Expected vs Actual table shows correct expected values for marketing profile

# 5. Verify Phase 2 is removed from profile-c-full.sh
grep -n "PASS=" infrastructure/scripts/profile-c-full.sh
# Should return nothing (Phase 2 removed)

grep -n "sleep 60" infrastructure/scripts/profile-c-full.sh
# Should return nothing (sleep removed)
```

---

## Definition of Done

- [ ] `.env.profiles` written at end of all 5 profile scripts with correct `PROFILE_SET` value and timestamp
- [ ] `profile-b-app.sh` writes `app-light` or `app-ai` depending on `$MODE` argument
- [ ] Phase 2 health checks (and `sleep 60`) removed from `profile-c-full.sh`
- [ ] All 5 scripts print "Run ./profile-status.sh to verify state" at the end
- [ ] `.env.profiles` added to `.gitignore`
- [ ] `profile-status.sh` created with all 6 sections: profile banner, Expected vs Actual table, data layer, endpoint health, CloudWatch alarms, summary footer
- [ ] `profile-status.sh` sources `.env.profiles` (graceful if missing — sets `PROFILE_SET="unknown"`)
- [ ] Expected vs Actual table shows correct expected state for all 5 profile values
- [ ] Beat `desiredCount > 1` triggers red danger warning
- [ ] API health check uses `/api/v1/health/celery` endpoint, parses and displays `workers_active`, `broker_connected`, `scheduled_tasks`
- [ ] `profile-status.sh` exit code always `0`
- [ ] `README.md` created with all 8 required sections
- [ ] All bash syntax checks pass
- [ ] Live test: run one profile script, verify `.env.profiles` content, run `profile-status.sh`, verify Expected vs Actual output is correct

---

## Completion Summary

When done, paste:

```
## Completion Summary — Profile Scripts v2 + Status Dashboard + README

**Date**: <date>
**Scripts modified**: profile-off.sh, profile-a-marketing.sh, profile-b-app.sh, profile-c-full.sh
**Scripts created**: profile-status.sh
**Files created**: infrastructure/scripts/README.md, infrastructure/scripts/.env.profiles (gitignored)

**Test run — profile-status.sh output after running profile-a-marketing.sh**:
<paste first 30 lines>

**Syntax checks**: ✅ all 5 scripts pass `bash -n`
**Gitignore confirmed**: ✅ .env.profiles not tracked
**Phase 2 removed from profile-c-full.sh**: ✅
```
