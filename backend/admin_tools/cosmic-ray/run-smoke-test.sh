#!/usr/bin/env bash
# ============================================================
# Cosmic Ray — Smoke Test
# Fastest single file from each tier to verify tooling.
# ~3–11 min per file.
#
# HOW TO RUN:
#   cd backend
#   bash admin_tools/cosmic-ray/run-smoke-test.sh
# ============================================================

set -e
cd "$(dirname "$0")/../.."
source admin_tools/cosmic-ray/_lib.sh

TIER_NAME="Smoke Test"
SESSION_DIR="admin_tools/cosmic-ray/sessions/smoke"

# ── Groups (one-file groups, one per tier) ────────────────────────────────────
GROUP_NAMES=( "Billing Rate Service (T1)"  "DB Helpers (T2)"  "Quote Expiry Task (T3)"  "Dunning Task (T4)" )
GROUP_TIMES=( "(~5 min)"                   "(~3 min)"         "(~4 min)"                "(~7 min)"          )

GROUP_1_FILES=( "services/billing_rate_service.py" )
GROUP_1_TESTS=( "tests/batch_b3/test_a14_etc_capture.py" "tests/batch_tp_b1/test_tp_b1_invoicing_payment_methods.py" )

GROUP_2_FILES=( "core/db.py" )
GROUP_2_TESTS=( "tests/batch_b17/test_find132_tenant_scoped_db_get.py" "tests/phase_7/test_phase7_batch3_tenant_isolation.py" )

GROUP_3_FILES=( "tasks/quote_expiration_monitor.py" )
GROUP_3_TESTS=( "tests/batch_b19/test_quote_expiration_monitor.py" "tests/batch_tp_b2/test_tp_b2_quote_approval_workflow.py" )

GROUP_4_FILES=( "tasks/dunning.py" )
GROUP_4_TESTS=( "tests/batch_b19/test_dunning_task.py" )

# ── Individual Files (same 4, listed for direct file selection) ───────────────
FILE_NAMES=( "billing_rate_service.py  " "db.py                  " "quote_expiration_monitor" "dunning.py             " )
FILE_TIMES=( "(~5 min)"                  "(~3 min)"                "(~4 min)"                 "(~7 min)"               )
FILE_GROUP_REFS=( "(G1)" "(G2)" "(G3)" "(G4)" )

FILE_1_SRC="services/billing_rate_service.py";     FILE_1_GROUP=1
FILE_2_SRC="core/db.py";                           FILE_2_GROUP=2
FILE_3_SRC="tasks/quote_expiration_monitor.py";    FILE_3_GROUP=3
FILE_4_SRC="tasks/dunning.py";                     FILE_4_GROUP=4

# ── Run ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CR_BOLD}${CR_CYAN}  COSMIC RAY — SMOKE TEST${CR_RESET}"
echo -e "${CR_DIM}  Fastest single file from each tier. Groups and Files are identical here.${CR_RESET}"
cr_main_loop
