#!/usr/bin/env bash
# ============================================================
# Cosmic Ray — Tier 4: Voice AI + Integration Wiring
# Full tier: ~3 hr 15 min
#
# HOW TO RUN:
#   cd backend
#   bash admin_tools/cosmic-ray/run-tier-4.sh
# ============================================================

set -e
cd "$(dirname "$0")/../.."
source admin_tools/cosmic-ray/_lib.sh

TIER_NAME="Tier 4 — Voice AI + Integration Wiring"
SESSION_DIR="admin_tools/cosmic-ray/sessions/tier-4"

# ── Groups ────────────────────────────────────────────────────────────────────
GROUP_NAMES=( "⚠️  Voice AI Router"  "Voice Sessions"  "QuickBooks"  "SMS & Auth"  "Public Links & Dunning" )
GROUP_TIMES=( "(~75 min)"            "(~24 min)"       "(~36 min)"   "(~33 min)"   "(~20 min)"              )

GROUP_1_FILES=( "services/voice_action_router.py" )
GROUP_1_TESTS=( "tests/batch_b1/test_a31_voice_approval_intents.py" "tests/batch_b20/test_find109_voice_clock_loto.py" "tests/batch_b20/test_find110_voice_scheduling_intents.py" "tests/batch_b20/test_voice_job_and_field_intents.py" "tests/integration/test_voice_multi_turn_e2e.py" )

GROUP_2_FILES=( "services/voice_session_service.py" "api/routes/voice.py" "api/routes/voice_sessions.py" )
GROUP_2_TESTS=( "tests/batch_b2/test_a10_voice_session_handlers.py" "tests/batch_b11/test_a63_voice_sms_reply.py" "tests/integration/test_voice_multi_turn_e2e.py" )

GROUP_3_FILES=( "services/quickbooks_sync.py" "services/qb_conflict_diff.py" )
GROUP_3_TESTS=( "tests/batch_b8/test_a49_a50_qb_conflict_endpoints.py" "tests/batch_b19/test_qb_invoice_push.py" "tests/integration/test_quote_to_job_flow.py" )

GROUP_4_FILES=( "services/sms_carrier.py" "services/telnyx_sms_carrier.py" "services/sms_service.py" "core/auth.py" )
GROUP_4_TESTS=( "tests/batch_b11/test_a59_sms_carrier_adapter.py" "tests/batch_b11/test_a62_a64_a66_sms_endpoints.py" "tests/batch_b13/test_a68_mfa_policy.py" )

GROUP_5_FILES=( "services/public_link_signer.py" "tasks/dunning.py" )
GROUP_5_TESTS=( "tests/batch_b15/test_a80_public_links.py" "tests/batch_b19/test_find073_invoice_hmac_tokens.py" "tests/batch_b19/test_find097_quote_hmac_tokens.py" "tests/batch_b17/test_find148_invoice_link_tracking.py" "tests/batch_b19/test_payment_method_customer_vaulting.py" "tests/batch_b19/test_find071_overpayment_handling.py" "tests/batch_b19/test_dunning_task.py" )

# ── Individual Files ──────────────────────────────────────────────────────────
FILE_NAMES=(
    "⚠️  voice_action_router.py "
    "voice_session_service.py   "
    "voice.py (routes)          "
    "voice_sessions.py (routes) "
    "quickbooks_sync.py         "
    "qb_conflict_diff.py        "
    "sms_carrier.py             "
    "telnyx_sms_carrier.py      "
    "sms_service.py             "
    "auth.py                    "
    "public_link_signer.py      "
    "dunning.py                 "
)
FILE_TIMES=( "(~75 min)" "(~10 min)" "(~14 min)" "(~10 min)" "(~28 min)" "(~8 min)"  "(~7 min)"  "(~10 min)" "(~5 min)"  "(~11 min)" "(~8 min)"  "(~7 min)"  )
FILE_GROUP_REFS=( "(G1)" "(G2)" "(G2)" "(G2)" "(G3)" "(G3)" "(G4)" "(G4)" "(G4)" "(G4)" "(G5)" "(G5)" )

FILE_1_SRC="services/voice_action_router.py";    FILE_1_GROUP=1
FILE_2_SRC="services/voice_session_service.py";  FILE_2_GROUP=2
FILE_3_SRC="api/routes/voice.py";                FILE_3_GROUP=2
FILE_4_SRC="api/routes/voice_sessions.py";       FILE_4_GROUP=2
FILE_5_SRC="services/quickbooks_sync.py";        FILE_5_GROUP=3
FILE_6_SRC="services/qb_conflict_diff.py";       FILE_6_GROUP=3
FILE_7_SRC="services/sms_carrier.py";            FILE_7_GROUP=4
FILE_8_SRC="services/telnyx_sms_carrier.py";     FILE_8_GROUP=4
FILE_9_SRC="services/sms_service.py";            FILE_9_GROUP=4
FILE_10_SRC="core/auth.py";                      FILE_10_GROUP=4
FILE_11_SRC="services/public_link_signer.py";    FILE_11_GROUP=5
FILE_12_SRC="tasks/dunning.py";                  FILE_12_GROUP=5

# ── Run ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CR_BOLD}${CR_CYAN}  TIER 4 — VOICE AI + INTEGRATION WIRING${CR_RESET}"
echo -e "${CR_YELLOW}  ⚠  Group 1 / File 1 (Voice AI Router) takes ~75 min alone.${CR_RESET}"
cr_main_loop
