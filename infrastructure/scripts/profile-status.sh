#!/usr/bin/env bash
set -eo pipefail
# ── Profile Status Dashboard — READ ONLY ─────────────────────────────────────
# Shows Expected vs Actual state for the active profile.
# Sources .infra-state.env (resource IDs) and .env.profiles (current profile).
#
# USAGE:
#   ./profile-status.sh
#
# Safe to run at any time — no mutating AWS calls, no confirmation prompt.
# Run repeatedly until all rows show ✅.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Load infrastructure state ─────────────────────────────────────────────────
INFRA_STATE_FILE="$SCRIPT_DIR/.infra-state.env"
if [ ! -f "$INFRA_STATE_FILE" ]; then
  echo "ERROR: .infra-state.env not found."
  echo "Run first: cd infrastructure/scripts && ./generate-infra-state.sh"
  exit 1
fi
source "$INFRA_STATE_FILE"

# ── Load profile state (graceful — missing on first run before any profile) ───
PROFILES_STATE_FILE="$SCRIPT_DIR/.env.profiles"
PROFILE_SET="unknown"
PROFILE_SET_AT=""
if [ -f "$PROFILES_STATE_FILE" ]; then
  source "$PROFILES_STATE_FILE"
fi

# ── Static vars ───────────────────────────────────────────────────────────────
ACCOUNT_ID="000000000000"
REGION="us-east-1"
CLUSTER="${ECS_CLUSTER:-pilot-production}"
DOMAIN="pilotfortrades.com"

# ── Verify AWS account ────────────────────────────────────────────────────────
ACTUAL_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text \
  --region "$REGION" 2>/dev/null || echo "ERROR")
if [ "$ACTUAL_ACCOUNT" != "$ACCOUNT_ID" ]; then
  echo "ERROR: AWS account mismatch — expected $ACCOUNT_ID, got $ACTUAL_ACCOUNT"
  echo "Run: aws sso login  (or reconfigure AWS CLI credentials)"
  exit 1
fi

# ── Expected state lookup (canonical profile definitions) ─────────────────────
# Returns: GPU BASTION API WORKER BEAT WEB SITE
# Values for EC2: "running" | "stopped"
# Values for ECS: integer task count
# Values for site: "live" | "coming_soon"
get_expected() {
  case "$1" in
    off)        echo "stopped stopped 0 0 0 0 coming_soon" ;;
    marketing)  echo "stopped running 1 1 1 0 live" ;;
    app-light)  echo "stopped running 1 1 1 1 live" ;;
    app-ai)     echo "running running 2 2 1 1 live" ;;
    full)       echo "running running 2 2 1 1 live" ;;
    *)          echo "unknown unknown - - - - unknown" ;;
  esac
}

# ── "Set N ago" helper ────────────────────────────────────────────────────────
AGO_STR=""
if [ -n "$PROFILE_SET_AT" ]; then
  AGO_STR=$(python3 - "$PROFILE_SET_AT" << 'PYEOF'
import sys, datetime
try:
    set_at = datetime.datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
    now = datetime.datetime.now(datetime.timezone.utc)
    diff = int((now - set_at).total_seconds())
    if diff < 60:
        print(f'{diff} sec ago')
    elif diff < 3600:
        print(f'{diff // 60} min ago')
    else:
        print(f'{diff // 3600}h {(diff % 3600) // 60}m ago')
except Exception:
    print('')
PYEOF
  2>/dev/null || echo "")
fi

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Profile Banner
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Pilot Production Status ==="
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Account: $ACCOUNT_ID"
echo ""

if [ "$PROFILE_SET" = "unknown" ]; then
  echo -e "${YELLOW}⚠️  No profile has been set yet. Run one of the profile scripts first.${NC}"
  echo "  ./profile-off.sh"
  echo "  ./profile-a-marketing.sh"
  echo "  ./profile-b-app.sh light|ai"
  echo "  ./profile-c-full.sh"
else
  if [ -n "$AGO_STR" ]; then
    echo -e "Active profile: ${GREEN}${PROFILE_SET}${NC}  (set ${AGO_STR})"
  else
    echo -e "Active profile: ${GREEN}${PROFILE_SET}${NC}"
  fi
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Expected vs Actual Table
# ─────────────────────────────────────────────────────────────────────────────

# Parse expected values into individual variables
read -r EXP_GPU EXP_BASTION EXP_API EXP_WORKER EXP_BEAT EXP_WEB EXP_SITE \
  <<< "$(get_expected "$PROFILE_SET")"

# ── Query GPU ─────────────────────────────────────────────────────────────────
if [ "$INFRA_GPU" = "true" ] && [ -n "$GPU_INSTANCE_ID" ]; then
  ACT_GPU=$(aws ec2 describe-instances --instance-ids "$GPU_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")
else
  ACT_GPU="not-provisioned"
fi

# ── Query Bastion ─────────────────────────────────────────────────────────────
if [ "$INFRA_BASTION" = "true" ] && [ -n "$BASTION_INSTANCE_ID" ]; then
  ACT_BASTION=$(aws ec2 describe-instances --instance-ids "$BASTION_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")
else
  ACT_BASTION="not-provisioned"
fi

# ── Query ECS (single call, parse with python3) ───────────────────────────────
ECS_JSON="[]"
if [ "$INFRA_ECS" = "true" ]; then
  ECS_JSON=$(aws ecs describe-services \
    --cluster "$CLUSTER" \
    --services pilot-api pilot-celery-worker pilot-celery-beat pilot-web \
    --query 'services[*].{Name:serviceName,Desired:desiredCount,Running:runningCount}' \
    --output json --region "$REGION" 2>/dev/null || echo "[]")
fi

# Extract a single integer field for a named ECS service
# Returns -1 if service not found (not provisioned yet)
ecs_field() {
  # $1=service name  $2=Desired|Running
  python3 - "$ECS_JSON" "$1" "$2" << 'PYEOF'
import sys, json
try:
    data = json.loads(sys.argv[1])
    svc  = sys.argv[2]
    fld  = sys.argv[3]
    for s in data:
        if s.get('Name') == svc:
            print(int(s.get(fld, -1)))
            sys.exit(0)
    print(-1)
except Exception:
    print(-1)
PYEOF
}

ACT_API_DESIRED=$(ecs_field "pilot-api"           "Desired")
ACT_API_RUNNING=$(ecs_field "pilot-api"           "Running")
ACT_WRK_DESIRED=$(ecs_field "pilot-celery-worker" "Desired")
ACT_WRK_RUNNING=$(ecs_field "pilot-celery-worker" "Running")
ACT_BEAT_DESIRED=$(ecs_field "pilot-celery-beat"  "Desired")
ACT_BEAT_RUNNING=$(ecs_field "pilot-celery-beat"  "Running")
ACT_WEB_DESIRED=$(ecs_field "pilot-web"           "Desired")
ACT_WEB_RUNNING=$(ecs_field "pilot-web"           "Running")

# ── Query site mode ───────────────────────────────────────────────────────────
ACT_SITE=$(curl -s --max-time 5 "https://$DOMAIN/site-config.json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode','unknown'))" \
  2>/dev/null || echo "unreachable")

# ── Row counters for summary ──────────────────────────────────────────────────
MATCH_COUNT=0
MISMATCH_COUNT=0
UNPROVISIONED_COUNT=0

# ── Column widths (fixed — no dynamic data in printf format strings) ──────────
echo "── Resource State ────────────────────────────────────────────────────────────"
printf "%-26s %-14s %-18s %-6s %s\n" "Resource" "Expected" "Actual" "Status" "Notes"
echo "──────────────────────────────────────────────────────────────────────────────"

# ── GPU row ───────────────────────────────────────────────────────────────────
GPU_STATUS_ICON=""
GPU_NOTES=""
GPU_ACT_DISPLAY="$ACT_GPU"

if [ "$INFRA_GPU" != "true" ] || [ -z "$GPU_INSTANCE_ID" ]; then
  GPU_STATUS_ICON="⚠️"
  GPU_NOTES="not provisioned (Phase 4)"
  GPU_ACT_DISPLAY="not-prov"
  ((UNPROVISIONED_COUNT++)) || true
elif [ "$PROFILE_SET" = "unknown" ]; then
  GPU_STATUS_ICON="⚠️"
  GPU_NOTES="no profile set"
  ((UNPROVISIONED_COUNT++)) || true
elif [ "$ACT_GPU" = "$EXP_GPU" ]; then
  GPU_STATUS_ICON="✅"
  ((MATCH_COUNT++)) || true
elif [ "$ACT_GPU" = "pending" ]; then
  GPU_STATUS_ICON="🔄"
  GPU_NOTES="booting (~3-5 min); Ollama loads 5-15 min after boot"
  ((MISMATCH_COUNT++)) || true
elif [ "$ACT_GPU" = "stopping" ]; then
  GPU_STATUS_ICON="🔄"
  GPU_NOTES="stopping..."
  ((MISMATCH_COUNT++)) || true
else
  GPU_STATUS_ICON="❌"
  ((MISMATCH_COUNT++)) || true
fi
printf "%-26s %-14s %-18s %-6s %s\n" \
  "GPU (g4dn.xlarge)" "$EXP_GPU" "$GPU_ACT_DISPLAY" "$GPU_STATUS_ICON" "$GPU_NOTES"

# ── Bastion row ───────────────────────────────────────────────────────────────
BASTION_STATUS_ICON=""
BASTION_NOTES=""
BASTION_ACT_DISPLAY="$ACT_BASTION"

if [ "$INFRA_BASTION" != "true" ] || [ -z "$BASTION_INSTANCE_ID" ]; then
  BASTION_STATUS_ICON="⚠️"
  BASTION_NOTES="not provisioned"
  BASTION_ACT_DISPLAY="not-prov"
  ((UNPROVISIONED_COUNT++)) || true
elif [ "$PROFILE_SET" = "unknown" ]; then
  BASTION_STATUS_ICON="⚠️"
  BASTION_NOTES="no profile set"
  ((UNPROVISIONED_COUNT++)) || true
elif [ "$ACT_BASTION" = "$EXP_BASTION" ]; then
  BASTION_STATUS_ICON="✅"
  ((MATCH_COUNT++)) || true
elif [ "$ACT_BASTION" = "pending" ] || [ "$ACT_BASTION" = "stopping" ]; then
  BASTION_STATUS_ICON="🔄"
  BASTION_NOTES="transitioning..."
  ((MISMATCH_COUNT++)) || true
else
  BASTION_STATUS_ICON="❌"
  ((MISMATCH_COUNT++)) || true
fi
printf "%-26s %-14s %-18s %-6s %s\n" \
  "Bastion" "$EXP_BASTION" "$BASTION_ACT_DISPLAY" "$BASTION_STATUS_ICON" "$BASTION_NOTES"

# ── ECS row helper ────────────────────────────────────────────────────────────
# Arguments: display_label exp_count desired_count running_count service_name
ecs_row() {
  local lbl="$1"
  local exp="$2"
  local desired="$3"
  local running="$4"
  local svc="$5"

  local icon notes act_display exp_display

  # Format expected display
  if [ "$exp" = "0" ]; then
    exp_display="0 tasks"
  elif [ "$exp" = "1" ]; then
    exp_display="1 task"
  elif [ "$exp" = "-" ]; then
    exp_display="—"
  else
    exp_display="${exp} tasks"
  fi

  if [ "$INFRA_ECS" != "true" ]; then
    act_display="not-prov"
    icon="⚠️"
    notes="ECS not provisioned (Phase 6)"
    ((UNPROVISIONED_COUNT++)) || true
  elif [ "$PROFILE_SET" = "unknown" ]; then
    act_display="${desired} desired"
    icon="⚠️"
    notes="no profile set"
    ((UNPROVISIONED_COUNT++)) || true
  elif [ "$desired" = "-1" ]; then
    act_display="unknown"
    icon="⚠️"
    notes="could not query ECS"
    ((MISMATCH_COUNT++)) || true
  elif [ "$desired" = "$exp" ]; then
    # desiredCount matches expected
    if [ "$exp" = "0" ] && [ "$running" = "0" ]; then
      act_display="0 tasks"
      icon="✅"
      notes="(cost-floor state)"
      ((MATCH_COUNT++)) || true
    elif [ "$running" = "$exp" ]; then
      act_display="${running} tasks"
      icon="✅"
      notes=""
      ((MATCH_COUNT++)) || true
    else
      act_display="${running}/${desired} running"
      icon="🔄"
      notes="still starting — check CloudWatch logs"
      ((MISMATCH_COUNT++)) || true
    fi
  else
    # desiredCount doesn't match expected
    act_display="${running}/${desired} tasks"
    icon="❌"
    notes="desired=${desired}, expected=${exp}"
    ((MISMATCH_COUNT++)) || true
  fi

  printf "%-26s %-14s %-18s %-6s %s\n" "$lbl" "$exp_display" "$act_display" "$icon" "$notes"

  # Beat danger check — desiredCount > 1 is catastrophic
  if [ "$svc" = "pilot-celery-beat" ] && [ "$INFRA_ECS" = "true" ] && \
     [ "$desired" != "-1" ] && [ "$desired" -gt 1 ] 2>/dev/null; then
    printf "%-26s %s\n" "" "⚠️ DANGER: Beat must never exceed 1 — causes duplicate task execution!"
  fi
}

ecs_row "ECS pilot-api"         "$EXP_API"    "$ACT_API_DESIRED"  "$ACT_API_RUNNING"  "pilot-api"
ecs_row "ECS pilot-celery-wrkr" "$EXP_WORKER" "$ACT_WRK_DESIRED"  "$ACT_WRK_RUNNING"  "pilot-celery-worker"
ecs_row "ECS pilot-celery-beat" "$EXP_BEAT"   "$ACT_BEAT_DESIRED" "$ACT_BEAT_RUNNING" "pilot-celery-beat"
ecs_row "ECS pilot-web"         "$EXP_WEB"    "$ACT_WEB_DESIRED"  "$ACT_WEB_RUNNING"  "pilot-web"

# ── Site mode row ─────────────────────────────────────────────────────────────
SITE_ICON=""
SITE_NOTES=""

if [ "$PROFILE_SET" = "unknown" ]; then
  SITE_ICON="⚠️"
  SITE_NOTES="no profile set"
  ((UNPROVISIONED_COUNT++)) || true
elif [ "$ACT_SITE" = "$EXP_SITE" ]; then
  SITE_ICON="✅"
  ((MATCH_COUNT++)) || true
elif [ "$ACT_SITE" = "unreachable" ]; then
  SITE_ICON="⚠️"
  SITE_NOTES="could not reach $DOMAIN"
  ((MISMATCH_COUNT++)) || true
else
  SITE_ICON="❌"
  ((MISMATCH_COUNT++)) || true
fi
printf "%-26s %-14s %-18s %-6s %s\n" "Site mode" "$EXP_SITE" "$ACT_SITE" "$SITE_ICON" "$SITE_NOTES"

echo "──────────────────────────────────────────────────────────────────────────────"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Data Layer
# ─────────────────────────────────────────────────────────────────────────────
echo "── Data Layer ────────────────────────────────────────────────────────────────"

RDS_STATUS=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].DBInstanceStatus' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")

RDS_CLASS=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].DBInstanceClass' \
  --output text --region "$REGION" 2>/dev/null || echo "unknown")

RDS_MULTI_AZ=$(aws rds describe-db-instances \
  --db-instance-identifier pilot-production \
  --query 'DBInstances[0].MultiAZ' \
  --output text --region "$REGION" 2>/dev/null || echo "unknown")

if [ "$RDS_STATUS" = "available" ]; then
  RDS_ICON="✅"
  RDS_NOTE=""
elif [ "$RDS_STATUS" = "stopped" ]; then
  RDS_ICON="⚠️"
  RDS_NOTE="  RDS stopped — auto-restarts after 7 days"
else
  RDS_ICON="⚠️"
  RDS_NOTE="  status: $RDS_STATUS"
fi
printf "  %-18s %-12s  %-16s Multi-AZ: %-6s %s %s\n" \
  "RDS PostgreSQL" "$RDS_STATUS" "$RDS_CLASS" "$RDS_MULTI_AZ" "$RDS_ICON" "$RDS_NOTE"

REDIS_STATUS=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id pilot-production \
  --query 'CacheClusters[0].CacheClusterStatus' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")

REDIS_NODE=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id pilot-production \
  --query 'CacheClusters[0].CacheNodeType' \
  --output text --region "$REGION" 2>/dev/null || echo "unknown")

if [ "$REDIS_STATUS" = "available" ]; then
  REDIS_ICON="✅"
  REDIS_NOTE=""
else
  REDIS_ICON="⚠️"
  REDIS_NOTE="  status: $REDIS_STATUS"
fi
printf "  %-18s %-12s  %-16s                 %s %s\n" \
  "ElastiCache Redis" "$REDIS_STATUS" "$REDIS_NODE" "$REDIS_ICON" "$REDIS_NOTE"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: Endpoint Health Checks
# ─────────────────────────────────────────────────────────────────────────────
echo "── Endpoint Health ───────────────────────────────────────────────────────────"

# ── API health ────────────────────────────────────────────────────────────────
if [ "$INFRA_ECS" != "true" ]; then
  echo "  API health       [SKIPPED — ECS not provisioned]"
elif [ "$ACT_API_DESIRED" = "0" ] || [ "$ACT_API_DESIRED" = "-1" ]; then
  echo "  API health       [SKIPPED — service at 0 tasks]"
else
  echo "  API health       https://api.${DOMAIN}/api/v1/health/celery"
  # Use -s (no fail-on-error) so we capture the real HTTP code without || interference
  API_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 \
    "https://api.${DOMAIN}/api/v1/health/celery" 2>/dev/null)
  [ -z "$API_HTTP" ] && API_HTTP="000"
  API_BODY=$(curl -s --max-time 8 \
    "https://api.${DOMAIN}/api/v1/health/celery" 2>/dev/null || echo "{}")

  WORKERS_ACTIVE=$(echo "$API_BODY" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('workers_active','?'))" 2>/dev/null || echo "?")
  BROKER_CONNECTED=$(echo "$API_BODY" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('broker_connected','?'))" 2>/dev/null || echo "?")
  SCHEDULED_TASKS=$(echo "$API_BODY" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('scheduled_tasks','?'))" 2>/dev/null || echo "?")

  if [ "$API_HTTP" = "200" ]; then
    echo "    HTTP $API_HTTP   ✅"
    echo "    workers_active: ${WORKERS_ACTIVE}   broker_connected: ${BROKER_CONNECTED}   scheduled_tasks: ${SCHEDULED_TASKS}"
  elif [ "$API_HTTP" = "000" ]; then
    echo "    ⚠️  unreachable (service may be at 0 tasks or still starting)"
  else
    echo "    ❌ HTTP $API_HTTP"
  fi
fi
echo ""

# ── Web dashboard ─────────────────────────────────────────────────────────────
if [ "$INFRA_ECS" != "true" ]; then
  echo "  Web dashboard    [SKIPPED — ECS not provisioned]"
elif [ "$ACT_WEB_DESIRED" = "0" ] || [ "$ACT_WEB_DESIRED" = "-1" ]; then
  echo "  Web dashboard    [SKIPPED — service at 0 tasks]"
else
  echo "  Web dashboard    https://app.${DOMAIN}"
  WEB_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 \
    "https://app.${DOMAIN}" 2>/dev/null)
  [ -z "$WEB_HTTP" ] && WEB_HTTP="000"
  if [ "$WEB_HTTP" = "200" ]; then
    echo "    HTTP $WEB_HTTP   ✅"
  elif [ "$WEB_HTTP" = "000" ]; then
    echo "    ⚠️  unreachable (service may be at 0 tasks or still starting)"
  else
    echo "    ❌ HTTP $WEB_HTTP"
  fi
fi
echo ""

# ── Marketing site (always check — S3/CloudFront) ────────────────────────────
echo "  Marketing site   https://${DOMAIN}"
MKT_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 \
  "https://${DOMAIN}" 2>/dev/null)
[ -z "$MKT_HTTP" ] && MKT_HTTP="000"
if [ "$MKT_HTTP" = "200" ]; then
  echo "    HTTP $MKT_HTTP   ✅"
elif [ "$MKT_HTTP" = "000" ]; then
  echo "    ⚠️  unreachable"
else
  echo "    ❌ HTTP $MKT_HTTP"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: CloudWatch Alarms
# ─────────────────────────────────────────────────────────────────────────────
echo "── CloudWatch Alarms ─────────────────────────────────────────────────────────"

ALARM_COUNT=$(aws cloudwatch describe-alarms \
  --state-value ALARM \
  --alarm-name-prefix "pilot-production" \
  --query 'length(MetricAlarms)' \
  --output text --region "$REGION" 2>/dev/null || echo "UNKNOWN")

if [ "$ALARM_COUNT" = "0" ]; then
  echo "  ✅ No alarms firing"
elif [ "$ALARM_COUNT" = "UNKNOWN" ]; then
  echo "  ⚠️  Could not query alarms"
else
  echo "  ❌ $ALARM_COUNT alarm(s) firing:"
  aws cloudwatch describe-alarms \
    --state-value ALARM \
    --alarm-name-prefix "pilot-production" \
    --query 'MetricAlarms[*].{Alarm:AlarmName,Reason:StateReason}' \
    --output table --region "$REGION" 2>/dev/null || echo "  (could not retrieve alarm details)"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: Summary Footer
# ─────────────────────────────────────────────────────────────────────────────
echo "══════════════════════════════════════════════════════════════════════════════"
if [ -n "$AGO_STR" ]; then
  echo "Profile: ${PROFILE_SET} | Set: ${AGO_STR}"
else
  echo "Profile: ${PROFILE_SET}"
fi
echo "  ✅  ${MATCH_COUNT}  resources match expected state"
echo "  ❌  ${MISMATCH_COUNT}  resources do not match"
echo "  ⚠️   ${UNPROVISIONED_COUNT}  resources not yet provisioned"
echo ""

TOTAL_PROBLEMS=$((MISMATCH_COUNT + UNPROVISIONED_COUNT))
if [ "$TOTAL_PROBLEMS" = "0" ] && [ "$MATCH_COUNT" -gt 0 ]; then
  echo "All resources match → System ready for use."
else
  echo "${MISMATCH_COUNT} resource(s) not at target state → re-run ./profile-status.sh in 60 seconds."
fi
echo "══════════════════════════════════════════════════════════════════════════════"
echo ""

exit 0
