#!/usr/bin/env bash
# ============================================================
# Cosmic Ray — Tier 1: Financial Correctness
# Full tier: ~1 hr 45 min
#
# HOW TO RUN:
#   cd backend
#   bash admin_tools/cosmic-ray/run-tier-1.sh
# ============================================================

set -e
cd "$(dirname "$0")/../.."
source admin_tools/cosmic-ray/_lib.sh

TIER_NAME="Tier 1 — Financial Correctness"
SESSION_DIR="admin_tools/cosmic-ray/sessions/tier-1"

# ── Groups ────────────────────────────────────────────────────────────────────
GROUP_NAMES=( "Stripe Billing"  "SMS & Quota"  "Quote & Financial"  "Invoices & Tax" )
GROUP_TIMES=( "(~30 min)"       "(~11 min)"    "(~20 min)"          "(~45 min)"      )

GROUP_1_FILES=( "services/stripe_subscriptions.py" "services/stripe_payment_intents.py" "api/routes/webhooks_stripe.py" )
GROUP_1_TESTS=( "tests/batch_b19/test_stripe_subscription_lifecycle.py" "tests/batch_b15/test_a81_stripe_payment_intents.py" "tests/batch_b14/test_a76_stripe_webhook.py" )

GROUP_2_FILES=( "services/sms_quota.py" )
GROUP_2_TESTS=( "tests/batch_b11/test_a65_sms_quota.py" "tests/batch_b18/test_find104_sms_quota_cap_policy.py" "tests/domains/subscriptions_usage/test_sms_quota_mutation_coverage.py" )

GROUP_3_FILES=( "services/quote_service.py" "services/etc_service.py" "services/billing_rate_service.py" )
GROUP_3_TESTS=( "tests/batch_b1/test_a3_quote_discounts.py" "tests/batch_tp_b1/test_tp_b1_invoicing_payment_methods.py" "tests/batch_b3/test_a14_etc_capture.py" "tests/domains/invoicing_billing/test_billing_rate_service_mutation_coverage.py" )

GROUP_4_FILES=( "api/routes/invoices.py" "core/tax_calculation.py" "tasks/saas_billing_aggregator.py" )
GROUP_4_TESTS=( "tests/integration/test_financial_math_edge_cases.py" "tests/batch_b19/test_saas_billing_aggregator.py" "tests/batch_b20/test_a92_invoice_crud.py" )

# ── Individual Files ──────────────────────────────────────────────────────────
FILE_NAMES=(
    "stripe_subscriptions.py  "
    "stripe_payment_intents.py"
    "webhooks_stripe.py       "
    "sms_quota.py             "
    "quote_service.py         "
    "etc_service.py           "
    "billing_rate_service.py  "
    "invoices.py              "
    "tax_calculation.py       "
    "saas_billing_aggregator  "
)
FILE_TIMES=( "(~11 min)" "(~12 min)" "(~7 min)"  "(~11 min)" "(~8 min)" "(~7 min)" "(~5 min)" "(~26 min)" "(~10 min)" "(~7 min)" )
FILE_GROUP_REFS=( "(G1)" "(G1)" "(G1)" "(G2)" "(G3)" "(G3)" "(G3)" "(G4)" "(G4)" "(G4)" )

FILE_1_SRC="services/stripe_subscriptions.py";   FILE_1_GROUP=1
FILE_2_SRC="services/stripe_payment_intents.py"; FILE_2_GROUP=1
FILE_3_SRC="api/routes/webhooks_stripe.py";      FILE_3_GROUP=1
FILE_4_SRC="services/sms_quota.py";              FILE_4_GROUP=2
FILE_5_SRC="services/quote_service.py";          FILE_5_GROUP=3
FILE_6_SRC="services/etc_service.py";            FILE_6_GROUP=3
FILE_7_SRC="services/billing_rate_service.py";   FILE_7_GROUP=3
FILE_8_SRC="api/routes/invoices.py";             FILE_8_GROUP=4
FILE_9_SRC="core/tax_calculation.py";            FILE_9_GROUP=4
FILE_10_SRC="tasks/saas_billing_aggregator.py";  FILE_10_GROUP=4

# ── Run ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CR_BOLD}${CR_CYAN}  TIER 1 — FINANCIAL CORRECTNESS${CR_RESET}"
cr_main_loop
