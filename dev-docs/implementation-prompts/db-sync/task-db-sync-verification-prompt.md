# Phase 4.5 Completion Verification & Forensic Audit

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Post-Schema-Sync Verification
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
**Type:** Quality Gate - Comprehensive Verification
**Priority:** CRITICAL (Phase 4.5 sign-off requirement)

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

**Phase 4.5 is marked as COMPLETE** - all 13 tasks spanning 4 phases have been implemented:
- **Phase 1: Foundation** (Tasks 1-3) - Data types & timezone fixes ✅
- **Phase 2: Functions & Triggers** (Tasks 4-7) - PL/pgSQL logic & audit coverage ✅
- **Phase 3: Data Integrity** (Tasks 8-10) - Constraints (UNIQUE, CHECK, EXCLUDE) ✅
- **Phase 4: Advanced Indexing** (Tasks 11-13) - Performance & temporal logic ✅

**PROBLEM:** The current `verify_schema.py` script only validates the JSON schema file, NOT the actual database implementation. It checks basic requirements but doesn't verify that all 13 Phase 4.5 tasks were correctly applied to the physical database.

**YOUR MISSION:** Build a comprehensive forensic verification system that queries the actual PostgreSQL database to confirm 100% completion of all Phase 4.5 work.

---

## Completed Phase 4.5 Tasks (What You're Verifying)

### Phase 1: Foundation (March 30-31, 2026)

**Task 1: Timezone Enforcement (9 columns)**
- ✅ Fixed 9 columns to use `timestamp with time zone`
- Migration: `2026_03_30_2129-cf20e60ce5f3_fix_timezone_violations_task1.py`
- Tables: `idempotency_key`, `integration_sync_mapping`, `notification_event`, `pricebook_item_version`, `product_plan_product_feature_version`, `product_plan_version`, `quote_public_link_contact_action`, `tax_rate_version`, `tenant_markup_version`

**Task 2: Citext Conversion for User Email**
- ✅ Converted `user.email` from VARCHAR to CITEXT
- Migration: `2026_03_31_1733-c748980dbeee_convert_user_email_to_citext.py`

**Task 3: QuickBooks Identity Constraints**
- ✅ Added `UNIQUE(tenant_id, display_name)` to `customer` table
- Migration: `2026_03_31_1804-1be24f24dd6b_add_qb_identity_constraints.py`

### Phase 2: Functions & Triggers (March 31, 2026)

**Task 4: Missing PL/pgSQL Functions (3 functions + 200 triggers)**
- ✅ Created `set_updated_at()` - 82 triggers on tables with `updated_at`
- ✅ Created `guard_created_fields_immutable()` - 116 triggers protecting `created_at`/`created_by`
- ✅ Created `guard_tenant_user_platform_isolation()` - 1 trigger on `tenant_user`
- Migration: `2026_03_31_1850-6b525454c89c_add_missing_plpgsql_functions.py`

**Task 5: Function Naming Standard**
- ✅ Renamed `guard_user_endpoint_primary_email()` → `guard_user_endpoint_primary_email_fn()`
- Migration: `2026_03_31_1954-0a26d3a349c2_rename_user_endpoint_guard_function.py`

**Task 6: Audit Trigger Coverage (85 audit triggers)**
- ✅ Added 85 audit triggers across critical tables
- Migrations:
  - `2026_03_31_2011-e3783b6d2b8d_add_missing_audit_triggers.py` - 75 triggers
  - `2026_03_31_2030-6a5d362b524d_fix_audit_triggers_support_code_pk.py` - 5 triggers for code-based PKs
  - `2026_03_31_2036-3f70e1ae4474_remove_audit_triggers_from_composite_pk_.py` - 4 triggers removed

**Task 7: Operational Trigger Verification**
- ✅ Documented 293 total triggers in `trigger-inventory.md`

### Phase 3: Data Integrity (April 1, 2026)

**Task 8: Unique Constraints (4 constraints)**
- ✅ `pricebook_item(tenant_id, sku)` - `uq_pricebook_item_tenant_sku`
- ✅ `user_sso_identity(sso_provider_code, provider_user_id)` - `uq_user_sso_identity_provider_user`
- ✅ `quote_acceptance(quote_version_id, contact_id)` - `uq_quote_acceptance_version_contact`
- ✅ `contact_portal_invite(contact_id)` - Already existed from Gap 1
- Migration: `2026_04_01_1230-b78d2b0199e8_add_missing_check_constraints_task9.py` (Task 8 constraints were in earlier migrations)

**Task 9: Check Constraints (9 constraints)**
- ✅ `user.email` - Email format regex
- ✅ `user.platform_role_code` - Enum: staff, superadmin
- ✅ `user_endpoint.value` - Email format when channel='email'
- ✅ `customer.type` - Enum: person, company
- ✅ `auth_mfa_otp.channel` - Enum: email, sms
- ✅ `notification_outbox.status` - Enum: pending, sent, failed, cancelled
- ✅ `webhook_delivery_attempt.status` - Enum: pending, delivered, failed, retrying
- ✅ `integration_sync_conflict.status` - Enum: pending, resolved, ignored
- ✅ `connector_run_log.status` - Enum: running, completed, failed, cancelled
- Migration: `2026_04_01_1230-b78d2b0199e8_add_missing_check_constraints_task9.py`

**Task 10: Temporal Exclusion Constraints (6 constraints)**
- ✅ `tenant_markup_version` - `tmv_no_overlap`
- ✅ `supplier_item_price` - `sip_no_overlap_per_tenant`
- ✅ `tax_rate_version` - `tax_rate_version_no_overlap`
- ✅ `pricebook_item_version` - `piv_no_overlap`
- ✅ `product_plan_version` - `product_plan_version_no_overlap`
- ✅ `product_plan_product_feature_version` - `pppfv_no_overlap`
- Migration: `2026_04_01_1524-3b01a0ab356f_add_temporal_exclusion_constraints_task10.py`

### Phase 4: Advanced Indexing (April 1, 2026)

**Task 11: Partial Indexes (2 indexes)**
- ✅ `idx_invoice_balance` - Invoice aging report optimization
- ✅ `idx_job_expense_unbilled` - Unbilled expense tracking
- Migration: `2026_04_01_1626-3fb234f4af72_add_partial_indexes_for_invoice_and_.py`

**Task 12: Partial Unique Indexes (2 indexes)**
- ✅ `ux_user_email_primary` - Primary email uniqueness
- ✅ `ux_global_primary_email` - Global primary uniqueness
- Migration: `2026_04_01_1701-0a79f3e208e1_add_partial_unique_indexes_user_.py`

**Task 13: Vector Indexes (2 HNSW indexes)**
- ✅ `idx_conv_session_context_embedding` - Session similarity search
- ✅ `idx_conv_msg_embedding` - Message similarity search
- Migration: `2026_04_01_1717-df3958786958_add_vector_indexes_for_embeddings_task13.py`

**Current Test Baseline:** 572/572 tests passing (100%)

---

## ⚠️ Current Verification Gap

**What `verify_schema.py` Does:**
- ✅ Validates JSON schema structure
- ✅ Checks timestamptz compliance in JSON
- ✅ Verifies field existence in JSON
- ✅ Validates unique constraints in JSON

**What It DOESN'T Do:**
- ❌ Query the actual PostgreSQL database
- ❌ Verify PL/pgSQL functions exist
- ❌ Verify triggers are attached to tables
- ❌ Verify CHECK constraints are active
- ❌ Verify temporal exclusion constraints
- ❌ Verify indexes (partial, partial unique, vector)
- ❌ Verify column data types in actual database
- ❌ Confirm migrations were applied successfully

**Result:** The script says "PASS" but doesn't actually verify the database state.

---

## Requirements

### 1. Create Enhanced Verification System

You need to build **TWO verification tools**:

#### Tool 1: `verify_database_schema.py` (New - Forensic Database Audit)

**Purpose:** Query the actual PostgreSQL database to verify all Phase 4.5 tasks completed.

**Location:** `dev-docs/db-design/verify_database_schema.py`

**Features:**
- Uses MCP `postgres-local` server for database queries
- Verifies each of the 13 Phase 4.5 tasks
- Outputs detailed pass/fail report
- Identifies specific gaps if any task incomplete
- Generates verification report document

**Verification Checklist (What to Query):**

**Phase 1: Foundation**
- [ ] **Task 1:** Query `information_schema.columns` for 9 specific columns - verify all are `timestamp with time zone`
- [ ] **Task 2:** Query `information_schema.columns` for `user.email` - verify type is `citext` (udt_name = 'citext')
- [ ] **Task 3:** Query `pg_constraint` for `uq_customer_tenant_display_name` constraint

**Phase 2: Functions & Triggers**
- [ ] **Task 4:** Query `pg_proc` for 3 functions: `set_updated_at`, `guard_created_fields_immutable`, `guard_tenant_user_platform_isolation`
- [ ] **Task 4:** Query `pg_trigger` for 199 triggers (82 + 116 + 1)
- [ ] **Task 5:** Verify function named `guard_user_endpoint_primary_email_fn` exists (not old name)
- [ ] **Task 6:** Query `pg_trigger` for 85 audit triggers (naming pattern: `audit_*_changes`)
- [ ] **Task 7:** Count total triggers - expect 293 total

**Phase 3: Data Integrity**
- [ ] **Task 8:** Query `pg_constraint` for 4 unique constraints (pricebook_item, user_sso_identity, quote_acceptance, contact_portal_invite)
- [ ] **Task 9:** Query `pg_constraint` for 9 CHECK constraints on specific tables/columns
- [ ] **Task 10:** Query `pg_constraint` for 6 exclusion constraints (contype = 'x') on temporal tables

**Phase 4: Advanced Indexing**
- [ ] **Task 11:** Query `pg_indexes` for 2 partial indexes (idx_invoice_balance, idx_job_expense_unbilled)
- [ ] **Task 12:** Query `pg_indexes` for 2 partial unique indexes (ux_user_email_primary, ux_global_primary_email)
- [ ] **Task 13:** Query `pg_indexes` for 2 HNSW vector indexes (idx_conv_session_context_embedding, idx_conv_msg_embedding)

#### Tool 2: `verify_schema.py` (Enhanced - Keep Existing + Add Notes)

**Purpose:** Enhance existing JSON validator to note it only checks JSON, not database.

**Location:** `dev-docs/db-design/verify_schema.py` (existing file - enhance it)

**Enhancement:** Add note to output that recommends running `verify_database_schema.py` for full verification.

---

### 2. Implementation Details

#### Step 1: Build `verify_database_schema.py` Script

Create a comprehensive Python script that uses the MCP `postgres-local` server to query the database.

**Script Structure:**

```python
"""
AevoFab AI - Phase 4.5 Database Verification Script
====================================================
Forensic audit of actual PostgreSQL database to verify all 13 Phase 4.5 tasks completed.

This script queries the physical database (not just JSON) to confirm:
- Timezone fixes (Task 1)
- Citext conversion (Task 2)
- QuickBooks constraints (Task 3)
- PL/pgSQL functions (Task 4)
- Function naming (Task 5)
- Audit triggers (Task 6)
- Operational triggers (Task 7)
- Unique constraints (Task 8)
- Check constraints (Task 9)
- Temporal exclusion constraints (Task 10)
- Partial indexes (Task 11)
- Partial unique indexes (Task 12)
- Vector indexes (Task 13)

HOW TO RUN IT
-------------
This script requires the postgres-local MCP server to be configured.

From the project root:
    python dev-docs/db-design/verify_database_schema.py

Or use Roo Cline to run it with MCP access.
"""

import sys
from typing import List, Dict, Tuple

# Since this will be run via Roo Cline with MCP access,
# we'll structure it to output verification queries that can be run

class Phase45Verifier:
    """Verifies all Phase 4.5 Database Schema Sync tasks completed."""
    
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.successes = []
    
    def verify_task_1_timezone_columns(self) -> bool:
        """
        Task 1: Verify 9 columns use timestamp with time zone.
        
        Expected columns:
        - idempotency_key.first_seen_at
        - integration_sync_mapping.last_synced_at
        - notification_event.occurred_at
        - pricebook_item_version.recorded_at
        - product_plan_product_feature_version.recorded_at
        - product_plan_version.recorded_at
        - quote_public_link_contact_action.occurred_at
        - tax_rate_version.recorded_at
        - tenant_markup_version.recorded_at
        """
        query = """
            SELECT 
                table_name,
                column_name,
                data_type,
                CASE 
                    WHEN data_type = 'timestamp with time zone' THEN 'PASS'
                    ELSE 'FAIL: ' || data_type
                END as status
            FROM information_schema.columns
            WHERE (table_name, column_name) IN (
                ('idempotency_key', 'first_seen_at'),
                ('integration_sync_mapping', 'last_synced_at'),
                ('notification_event', 'occurred_at'),
                ('pricebook_item_version', 'recorded_at'),
                ('product_plan_product_feature_version', 'recorded_at'),
                ('product_plan_version', 'recorded_at'),
                ('quote_public_link_contact_action', 'occurred_at'),
                ('tax_rate_version', 'recorded_at'),
                ('tenant_markup_version', 'recorded_at')
            )
            AND table_schema = 'public'
            ORDER BY table_name, column_name;
        """
        # Return query for MCP execution
        return ("Task 1: Timezone Columns", query, 9)
    
    def verify_task_2_citext_email(self) -> Tuple[str, str, int]:
        """Task 2: Verify user.email is citext."""
        query = """
            SELECT 
                table_name,
                column_name,
                udt_name,
                CASE 
                    WHEN udt_name = 'citext' THEN 'PASS'
                    ELSE 'FAIL: ' || data_type || ' (udt: ' || udt_name || ')'
                END as status
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'user'
              AND column_name = 'email';
        """
        return ("Task 2: User Email Citext", query, 1)
    
    def verify_task_3_qb_constraints(self) -> Tuple[str, str, int]:
        """Task 3: Verify QuickBooks identity constraint."""
        query = """
            SELECT 
                conname as constraint_name,
                conrelid::regclass as table_name,
                pg_get_constraintdef(oid) as definition,
                'PASS' as status
            FROM pg_constraint
            WHERE conname = 'uq_customer_tenant_display_name'
              AND contype = 'u';
        """
        return ("Task 3: QuickBooks Customer Constraint", query, 1)
    
    def verify_task_4_plpgsql_functions(self) -> Tuple[str, str, int]:
        """Task 4: Verify 3 PL/pgSQL functions exist."""
        query = """
            SELECT 
                proname as function_name,
                pg_get_function_identity_arguments(oid) as arguments,
                'PASS' as status
            FROM pg_proc
            WHERE proname IN (
                'set_updated_at',
                'guard_created_fields_immutable',
                'guard_tenant_user_platform_isolation'
            )
            ORDER BY proname;
        """
        return ("Task 4: PL/pgSQL Functions", query, 3)
    
    def verify_task_4_trigger_counts(self) -> List[Tuple[str, str, int]]:
        """Task 4: Verify trigger counts (82 + 116 + 1 = 199)."""
        queries = [
            ("Task 4a: set_updated_at Triggers", """
                SELECT COUNT(*) as trigger_count, 'PASS (Expected: 82)' as status
                FROM pg_trigger t
                JOIN pg_proc p ON t.tgfoid = p.oid
                WHERE p.proname = 'set_updated_at'
                  AND NOT t.tgisinternal;
            """, 1),
            ("Task 4b: guard_created_fields_immutable Triggers", """
                SELECT COUNT(*) as trigger_count, 'PASS (Expected: 116)' as status
                FROM pg_trigger t
                JOIN pg_proc p ON t.tgfoid = p.oid
                WHERE p.proname = 'guard_created_fields_immutable'
                  AND NOT t.tgisinternal;
            """, 1),
            ("Task 4c: guard_tenant_user_platform_isolation Triggers", """
                SELECT COUNT(*) as trigger_count, 'PASS (Expected: 1)' as status
                FROM pg_trigger t
                JOIN pg_proc p ON t.tgfoid = p.oid
                WHERE p.proname = 'guard_tenant_user_platform_isolation'
                  AND NOT t.tgisinternal;
            """, 1),
        ]
        return queries
    
    def verify_task_5_function_naming(self) -> Tuple[str, str, int]:
        """Task 5: Verify function renamed with _fn suffix."""
        query = """
            SELECT 
                proname as function_name,
                'PASS' as status
            FROM pg_proc
            WHERE proname = 'guard_user_endpoint_primary_email_fn'
            UNION ALL
            SELECT 
                proname as old_function_name,
                'FAIL: Old function still exists!' as status
            FROM pg_proc
            WHERE proname = 'guard_user_endpoint_primary_email';
        """
        return ("Task 5: Function Naming Standard", query, 1)
    
    def verify_task_6_audit_triggers(self) -> Tuple[str, str, int]:
        """Task 6: Verify 85 audit triggers."""
        query = """
            SELECT COUNT(*) as audit_trigger_count, 'PASS (Expected: 85)' as status
            FROM pg_trigger
            WHERE tgname LIKE 'audit_%_changes'
              AND NOT tgisinternal;
        """
        return ("Task 6: Audit Trigger Coverage", query, 1)
    
    def verify_task_7_total_triggers(self) -> Tuple[str, str, int]:
        """Task 7: Verify ~293 total triggers."""
        query = """
            SELECT COUNT(*) as total_trigger_count, 
                   'PASS (Expected: ~293)' as status
            FROM pg_trigger
            WHERE NOT tgisinternal;
        """
        return ("Task 7: Total Operational Triggers", query, 1)
    
    def verify_task_8_unique_constraints(self) -> Tuple[str, str, int]:
        """Task 8: Verify 4 unique constraints."""
        query = """
            SELECT 
                conname as constraint_name,
                conrelid::regclass as table_name,
                'PASS' as status
            FROM pg_constraint
            WHERE conname IN (
                'uq_pricebook_item_tenant_sku',
                'uq_user_sso_identity_provider_user',
                'uq_quote_acceptance_version_contact',
                'contact_portal_invite_contact_id_key'
            )
            AND contype = 'u'
            ORDER BY conname;
        """
        return ("Task 8: Unique Constraints", query, 4)
    
    def verify_task_9_check_constraints(self) -> Tuple[str, str, int]:
        """Task 9: Verify 9 CHECK constraints."""
        query = """
            SELECT 
                conname as constraint_name,
                conrelid::regclass as table_name,
                'PASS' as status
            FROM pg_constraint
            WHERE conname IN (
                'user_email_format_chk',
                'user_platform_role_chk',
                'user_endpoint_email_format_chk',
                'customer_type_chk',
                'auth_mfa_otp_channel_chk',
                'notification_outbox_status_chk',
                'webhook_delivery_attempt_status_chk',
                'integration_sync_conflict_status_chk',
                'connector_run_log_status_chk'
            )
            AND contype = 'c'
            ORDER BY conname;
        """
        return ("Task 9: Check Constraints", query, 9)
    
    def verify_task_10_temporal_exclusion(self) -> Tuple[str, str, int]:
        """Task 10: Verify 6 temporal exclusion constraints."""
        query = """
            SELECT 
                conname as constraint_name,
                conrelid::regclass as table_name,
                'PASS' as status
            FROM pg_constraint
            WHERE conname IN (
                'tmv_no_overlap',
                'sip_no_overlap_per_tenant',
                'tax_rate_version_no_overlap',
                'piv_no_overlap',
                'product_plan_version_no_overlap',
                'pppfv_no_overlap'
            )
            AND contype = 'x'
            ORDER BY conname;
        """
        return ("Task 10: Temporal Exclusion Constraints", query, 6)
    
    def verify_task_11_partial_indexes(self) -> Tuple[str, str, int]:
        """Task 11: Verify 2 partial indexes."""
        query = """
            SELECT 
                indexname,
                tablename,
                indexdef,
                'PASS' as status
            FROM pg_indexes
            WHERE indexname IN (
                'idx_invoice_balance',
                'idx_job_expense_unbilled'
            )
            AND schemaname = 'public'
            ORDER BY indexname;
        """
        return ("Task 11: Partial Indexes", query, 2)
    
    def verify_task_12_partial_unique_indexes(self) -> Tuple[str, str, int]:
        """Task 12: Verify 2 partial unique indexes."""
        query = """
            SELECT 
                indexname,
                tablename,
                indexdef,
                'PASS' as status
            FROM pg_indexes
            WHERE indexname IN (
                'ux_user_email_primary',
                'ux_global_primary_email'
            )
            AND schemaname = 'public'
            ORDER BY indexname;
        """
        return ("Task 12: Partial Unique Indexes", query, 2)
    
    def verify_task_13_vector_indexes(self) -> Tuple[str, str, int]:
        """Task 13: Verify 2 HNSW vector indexes."""
        query = """
            SELECT 
                indexname,
                tablename,
                indexdef,
                'PASS' as status
            FROM pg_indexes
            WHERE indexname IN (
                'idx_conv_session_context_embedding',
                'idx_conv_msg_embedding'
            )
            AND schemaname = 'public'
            ORDER BY indexname;
        """
        return ("Task 13: Vector HNSW Indexes", query, 2)
    
    def generate_verification_queries(self) -> List[Tuple[str, str, int]]:
        """Generate all verification queries."""
        queries = []
        
        # Phase 1
        queries.append(self.verify_task_1_timezone_columns())
        queries.append(self.verify_task_2_citext_email())
        queries.append(self.verify_task_3_qb_constraints())
        
        # Phase 2
        queries.append(self.verify_task_4_plpgsql_functions())
        queries.extend(self.verify_task_4_trigger_counts())
        queries.append(self.verify_task_5_function_naming())
        queries.append(self.verify_task_6_audit_triggers())
        queries.append(self.verify_task_7_total_triggers())
        
        # Phase 3
        queries.append(self.verify_task_8_unique_constraints())
        queries.append(self.verify_task_9_check_constraints())
        queries.append(self.verify_task_10_temporal_exclusion())
        
        # Phase 4
        queries.append(self.verify_task_11_partial_indexes())
        queries.append(self.verify_task_12_partial_unique_indexes())
        queries.append(self.verify_task_13_vector_indexes())
        
        return queries

def main():
    """Main verification entry point."""
    print("=" * 80)
    print(" AevoFab AI - Phase 4.5 Database Verification")
    print(" Forensic Audit of Physical PostgreSQL Database")
    print("=" * 80)
    print()
    print("This script generates SQL queries to verify all 13 Phase 4.5 tasks.")
    print("These queries must be executed against the actual database using:")
    print("  - postgres-local MCP server")
    print("  - psql command line")
    print("  - DBeaver or similar tool")
    print()
    print("-" * 80)
    
    verifier = Phase45Verifier()
    queries = verifier.generate_verification_queries()
    
    print(f"\nGenerated {len(queries)} verification queries:\n")
    
    for i, (task_name, query, expected_count) in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}: {task_name}")
        print(f"Expected Result Count: {expected_count} row(s)")
        print(f"{'=' * 80}")
        print(query)
        print()
    
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Execute each query above against the database")
    print("2. Verify the result count matches expected count")
    print("3. Check the 'status' column for PASS/FAIL")
    print("4. Document any failures in a verification report")
    print()
    print("For automated execution, use Roo Cline with postgres-local MCP server.")
    print()

if __name__ == "__main__":
    main()
```

#### Step 2: Execute Verification Queries

**Using MCP Server:**

For each query generated by the script, execute using the `mcp--postgres-local--query` tool.

**Example:**
```python
# Task 1: Timezone columns
await mcp__postgres_local__query({
    "sql": """
        SELECT 
            table_name,
            column_name,
            data_type,
            CASE 
                WHEN data_type = 'timestamp with time zone' THEN 'PASS'
                ELSE 'FAIL: ' || data_type
            END as status
        FROM information_schema.columns
        WHERE (table_name, column_name) IN (
            ('idempotency_key', 'first_seen_at'),
            -- ... (rest of Task 1 columns)
        )
        AND table_schema = 'public'
        ORDER BY table_name, column_name;
    """
})
```

#### Step 3: Generate Verification Report

Create a markdown document summarizing all verification results.

**File:** `dev-docs/analysis/phase-4.5-verification-report.md`

**Structure:**

```markdown
# Phase 4.5 Database Schema Sync - Verification Report

**Date:** YYYY-MM-DD
**Verified By:** [Your Name/Mode]
**Database:** PostgreSQL 17 (Local Development)
**Schema Version:** v2.6h

---

## Executive Summary

**Overall Status:** ✅ PASS / ❌ FAIL

**Verification Coverage:**
- Phase 1 (Foundation): X/3 tasks verified
- Phase 2 (Functions & Triggers): X/4 tasks verified
- Phase 3 (Data Integrity): X/3 tasks verified
- Phase 4 (Advanced Indexing): X/3 tasks verified

**Total:** X/13 tasks verified (Y% complete)

---

## Phase 1: Foundation

### Task 1: Timezone Enforcement ✅/❌

**Status:** PASS/FAIL
**Expected:** 9 columns with timestamp with time zone
**Actual:** X columns found

**Verification Query Result:**
| Table | Column | Data Type | Status |
|-------|--------|-----------|--------|
| idempotency_key | first_seen_at | timestamp with time zone | ✅ PASS |
| ... | ... | ... | ... |

**Issues Found:** None / [List any failures]

---

[REPEAT FOR ALL 13 TASKS]

---

## Performance Benchmarks

[Run performance queries from Phase 4]

**Invoice Aging Report:**
- Query Time: Xms
- Index Used: idx_invoice_balance
- Status: ✅ <50ms target met

---

## Conclusions & Recommendations

[Summary of findings]
[Any remediation needed]
[Sign-off for production readiness]
```

---

### 3. Implementation Order

Execute in this exact sequence:

1. **Create `verify_database_schema.py` Script**
   - Location: `dev-docs/db-design/verify_database_schema.py`
   - Generate all verification queries
   - Run the script to output queries

2. **Execute Verification Queries Using MCP**
   - Use `mcp--postgres-local--query` tool
   - Run each of the ~20 queries
   - Record results for each task

3. **Analyze Results**
   - Check if expected counts match actual
   - Identify any FAIL statuses
   - Note any missing constraints/indexes/functions

4. **Generate Verification Report**
   - Create `dev-docs/analysis/phase-4.5-verification-report.md`
   - Document all findings
   - Mark overall pass/fail status

5. **Enhance Existing `verify_schema.py`**
   - Add note about database verification
   - Recommend running `verify_database_schema.py`

6. **Run Performance Benchmarks**
   - Execute EXPLAIN ANALYZE queries
   - Verify index usage
   - Confirm performance targets met

7. **Update Project Plan**
   - Mark verification complete in `phase-4.5-db-schema-sync-to-design-plan.md`
   - Add link to verification report

---

### 4. Test Requirements

**⚠️ NO NEW TESTS REQUIRED**

This is a verification task, not an implementation task. You're auditing existing work, not creating new database changes.

**Verification Steps:**
1. Execute SQL queries against database
2. Compare results to expected values
3. Document pass/fail status
4. Generate comprehensive report

---

### 5. Database Query Tools

**You have access to the postgres-local MCP server:**

```python
# Example: Verify timezone columns
await mcp__postgres_local__query({
    "sql": "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE ..."
})
```

Use this tool to:
- Execute all verification queries
- Count triggers, functions, constraints
- Verify index existence
- Check column data types
- Validate constraint definitions

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING VERIFICATION AS DONE:**

- [ ] **`verify_database_schema.py` script created** with all 13 task queries
- [ ] **All ~20 verification queries executed** against actual database
- [ ] **Results recorded** for each of 13 tasks (pass/fail status)
- [ ] **Verification report created** at `dev-docs/analysis/phase-4.5-verification-report.md`
- [ ] **Phase 1 verified:** 3/3 tasks (timezone, citext, QB constraints)
- [ ] **Phase 2 verified:** 4/4 tasks (functions, triggers, naming, audit)
- [ ] **Phase 3 verified:** 3/3 tasks (unique, check, exclusion constraints)
- [ ] **Phase 4 verified:** 3/3 tasks (partial, partial unique, vector indexes)
- [ ] **Performance benchmarks run** (aging report, unbilled expenses, vector search)
- [ ] **Overall pass/fail status determined** (100% = PASS, <100% = document gaps)
- [ ] **Project plan updated** with verification completion status
- [ ] **Existing `verify_schema.py` enhanced** with database verification note

**Expected Outcome:**
- ✅ **13/13 tasks verified as complete (100%)**
- ✅ **All constraints, functions, triggers, indexes confirmed active**
- ✅ **Performance targets met (<50ms for partials, <100ms for vectors)**
- ✅ **Verification report documents 100% Phase 4.5 completion**

---

## Key Files to Create/Modify

### New Files to Create

1. `dev-docs/db-design/verify_database_schema.py` - **Forensic database audit script** ⭐
2. `dev-docs/analysis/phase-4.5-verification-report.md` - **Verification results document** ⭐

### Existing Files to Update

1. `dev-docs/db-design/verify_schema.py` - Add note about database verification
2. `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Mark verification complete

### Files to Reference

- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master
- `dev-docs/db-design/trigger-inventory.md` - Trigger documentation
- All 13 migration files from Phase 4.5 tasks

---

## Expected Verification Results

### Phase 1: Foundation (3 Tasks)

**Task 1: Timezone Enforcement**
- Expected: 9 rows returned, all with `data_type = 'timestamp with time zone'`
- Status column: All should show 'PASS'

**Task 2: Citext Email**
- Expected: 1 row returned
- `udt_name = 'citext'` (not 'varchar')
- Status: 'PASS'

**Task 3: QuickBooks Constraints**
- Expected: 1 row returned
- Constraint name: `uq_customer_tenant_display_name`
- Type: 'u' (unique)
- Status: 'PASS'

### Phase 2: Functions & Triggers (4 Tasks)

**Task 4: PL/pgSQL Functions**
- Expected: 3 rows (functions: set_updated_at, guard_created_fields_immutable, guard_tenant_user_platform_isolation)
- All should exist in pg_proc

**Task 4a-c: Trigger Counts**
- set_updated_at: 82 triggers
- guard_created_fields_immutable: 116 triggers
- guard_tenant_user_platform_isolation: 1 trigger

**Task 5: Function Naming**
- Expected: 1 row with new name, 0 rows with old name
- New: `guard_user_endpoint_primary_email_fn`
- Old: `guard_user_endpoint_primary_email` (should NOT exist)

**Task 6: Audit Triggers**
- Expected: Count = 85
- Pattern: `audit_%_changes`

**Task 7: Total Triggers**
- Expected: Count ~293 (exact count may vary slightly)

### Phase 3: Data Integrity (3 Tasks)

**Task 8: Unique Constraints**
- Expected: 4 rows
- All constraint names found in pg_constraint

**Task 9: Check Constraints**
- Expected: 9 rows
- All constraint names found, type = 'c'

**Task 10: Temporal Exclusion Constraints**
- Expected: 6 rows
- All constraint names found, type = 'x'
- Tables: tenant_markup_version, supplier_item_price, tax_rate_version, pricebook_item_version, product_plan_version, product_plan_product_feature_version

### Phase 4: Advanced Indexing (3 Tasks)

**Task 11: Partial Indexes**
- Expected: 2 rows
- idx_invoice_balance: `WHERE balance_due_cents > 0`
- idx_job_expense_unbilled: `WHERE is_billable = true AND invoice_line_id IS NULL`

**Task 12: Partial Unique Indexes**
- Expected: 2 rows
- ux_user_email_primary: `WHERE channel = 'email' AND is_primary = true`
- ux_global_primary_email: `WHERE is_primary = true`

**Task 13: Vector Indexes**
- Expected: 2 rows
- idx_conv_session_context_embedding: USING hnsw
- idx_conv_msg_embedding: USING hnsw

---

## Notes

- **MCP Server Required:** Use `postgres-local` MCP server for all database queries
- **Read-Only Verification:** This task does NOT modify the database
- **Forensic Audit:** We're confirming work already done, not implementing new changes
- **Report Critical:** The verification report is the primary deliverable
- **100% Target:** All 13 tasks should verify as complete
- **Performance Matters:** Benchmark queries should show index usage and <100ms times

**If Gaps Found:**
- Document specific failures in verification report
- Note which migration may need re-application
- Recommend remediation steps
- Mark overall verification as INCOMPLETE until fixed

**If All Pass:**
- Document 100% completion
- Mark Phase 4.5 as production-ready
- Sign off on schema sync completion
- Proceed to Phase 5 (application features)

---

**Ready to Begin!** 🚀

1. 🔧 Create `verify_database_schema.py` script
2. 🔍 Execute all verification queries via MCP
3. 📊 Record pass/fail results for each task
4. 📝 Generate comprehensive verification report
5. ✅ Update project plan with verification status
6. 🎉 Confirm 100% Phase 4.5 completion

Remember: You're auditing existing work, not implementing new changes. The goal is to prove all 13 tasks were correctly applied to the physical database!
