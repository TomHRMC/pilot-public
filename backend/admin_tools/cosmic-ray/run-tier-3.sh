#!/usr/bin/env bash
# ============================================================
# Cosmic Ray — Tier 3: Core Workflow State Machines
# Full tier: ~50 min
#
# HOW TO RUN:
#   cd backend
#   bash admin_tools/cosmic-ray/run-tier-3.sh
# ============================================================

set -e
cd "$(dirname "$0")/../.."
source admin_tools/cosmic-ray/_lib.sh

TIER_NAME="Tier 3 — Core Workflow State Machines"
SESSION_DIR="admin_tools/cosmic-ray/sessions/tier-3"

# ── Groups ────────────────────────────────────────────────────────────────────
GROUP_NAMES=( "Entitlement & Limits"  "Onboarding & Dispatch" )
GROUP_TIMES=( "(~28 min)"             "(~23 min)"             )

GROUP_1_FILES=( "services/entitlement_service.py" "services/tier_limit_enforcer.py" "services/trial_management.py" )
GROUP_1_TESTS=( "tests/batch_1d/test_task_1d4_entitlement_enforcement.py" "tests/batch_b14/test_a75_subscription_tier_infrastructure.py" "tests/integration/test_entitlement_enforcement_e2e.py" )

GROUP_2_FILES=( "services/tenant_signup.py" "services/notification_resolver.py" "tasks/quote_expiration_monitor.py" )
GROUP_2_TESTS=( "tests/batch_tp_b2/test_tp_b2_quote_approval_workflow.py" "tests/batch_1d/test_task_1d1_quote_job_auto_conversion.py" "tests/batch_b14/test_a73_tenant_signup_state_machine.py" "tests/batch_tp_b3/test_tp_b3_quote_pending_edits.py" "tests/batch_b19/test_quote_expiration_monitor.py" "tests/batch_b10/test_a58_dispatcher_gate.py" "tests/batch_b10/test_a57_preference_matrix.py" )

# ── Individual Files ──────────────────────────────────────────────────────────
FILE_NAMES=( "entitlement_service.py    " "tier_limit_enforcer.py    " "trial_management.py       " "tenant_signup.py          " "notification_resolver.py  " "quote_expiration_monitor.py" )
FILE_TIMES=( "(~13 min)" "(~6 min)"  "(~9 min)"  "(~10 min)" "(~9 min)"  "(~4 min)"  )
FILE_GROUP_REFS=( "(G1)" "(G1)" "(G1)" "(G2)" "(G2)" "(G2)" )

FILE_1_SRC="services/entitlement_service.py";      FILE_1_GROUP=1
FILE_2_SRC="services/tier_limit_enforcer.py";      FILE_2_GROUP=1
FILE_3_SRC="services/trial_management.py";         FILE_3_GROUP=1
FILE_4_SRC="services/tenant_signup.py";            FILE_4_GROUP=2
FILE_5_SRC="services/notification_resolver.py";    FILE_5_GROUP=2
FILE_6_SRC="tasks/quote_expiration_monitor.py";    FILE_6_GROUP=2

# ── Run ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CR_BOLD}${CR_CYAN}  TIER 3 — CORE WORKFLOW STATE MACHINES${CR_RESET}"
cr_main_loop
