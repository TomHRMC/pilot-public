#!/usr/bin/env bash
# ============================================================
# Cosmic Ray — Tier 2: Security / IDOR / Tenant Isolation
# Full tier: ~1 hr
#
# HOW TO RUN:
#   cd backend
#   bash admin_tools/cosmic-ray/run-tier-2.sh
# ============================================================

set -e
cd "$(dirname "$0")/../.."
source admin_tools/cosmic-ray/_lib.sh

TIER_NAME="Tier 2 — Security / IDOR / Tenant Isolation"
SESSION_DIR="admin_tools/cosmic-ray/sessions/tier-2"

# ── Groups ────────────────────────────────────────────────────────────────────
GROUP_NAMES=( "Auth & RBAC"  "Catalog & Models" )
GROUP_TIMES=( "(~17 min)"    "(~43 min)"        )

GROUP_1_FILES=( "core/permissions.py" "core/db.py" )
GROUP_1_TESTS=( "tests/batch_1a/test_1a1_cross_tenant_pricing_idor.py" "tests/batch_1a/test_1a2_pricing_cache_tenant_stamping.py" "tests/batch_b17/test_find132_tenant_scoped_db_get.py" "tests/batch_b17/test_find054_pricing_cache_idor.py" "tests/batch_1a/test_batch_1a3_rbac_sweep.py" "tests/phase_7/test_phase7_batch3_tenant_isolation.py" "tests/phase_7/test_phase7_batch4_tenant_isolation.py" "tests/phase_7/test_phase7_batch5_tenant_isolation.py" "tests/batch_b17/test_find128_technician_role_permissions.py" "tests/batch_1b/test_task_1b1_financial_fk_hard_delete_lockdown.py" )

GROUP_2_FILES=( "api/routes/catalog.py" "app/models/billing.py" )
GROUP_2_TESTS=( "tests/batch_1a/test_1a1_cross_tenant_pricing_idor.py" "tests/batch_1a/test_1a2_pricing_cache_tenant_stamping.py" "tests/batch_b17/test_find054_pricing_cache_idor.py" "tests/batch_1b/test_task_1b1_financial_fk_hard_delete_lockdown.py" "tests/batch_tp_b5/test_tp_b5_catalog_pricebook.py" )

# ── Individual Files ──────────────────────────────────────────────────────────
FILE_NAMES=( "permissions.py  " "db.py           " "catalog.py      " "billing.py      " )
FILE_TIMES=( "(~14 min)"        "(~3 min)"         "(~21 min)"        "(~22 min)"        )
FILE_GROUP_REFS=( "(G1)" "(G1)" "(G2)" "(G2)" )

FILE_1_SRC="core/permissions.py";     FILE_1_GROUP=1
FILE_2_SRC="core/db.py";              FILE_2_GROUP=1
FILE_3_SRC="api/routes/catalog.py";   FILE_3_GROUP=2
FILE_4_SRC="app/models/billing.py";   FILE_4_GROUP=2

# ── Run ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CR_BOLD}${CR_CYAN}  TIER 2 — SECURITY / IDOR / TENANT ISOLATION${CR_RESET}"
cr_main_loop
