# Task: Database Schema Synchronization with Golden Master v2.6h

**Reference:** `dev-docs/architecture-design/db-schema-sync-technical-instruction-v1.0.md`  
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`  
**Type:** Technical Maintenance (Schema Reconciliation)

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **targeted schema synchronization task** to achieve 100% alignment between our SQLModel implementations and the Golden Master Database Schema (v2.6h JSON). This is NOT a new feature - it's surgical corrections to ensure database-level data integrity and business rule enforcement.

---

## Completed So Far

**Phase 1-A: Critical Blockers (COMPLETE - 7 tasks)**
✅ Test Endpoints, Tenant ID Fix, Idempotency, Request Tracing
✅ Database Triggers, Tax Calculations, Multi-Tenancy Tests

**Phase 1-B: Core Completeness (COMPLETE - 4 tasks)**
✅ Polymorphic Relationships, Contact Management
✅ Quote Acceptance Workflow, Voice Action Execution

**Phase 2: Background Processing Infrastructure (COMPLETE - 4 tasks)**
✅ Celery Setup & Configuration (Redis/SQS broker, Beat scheduler)
✅ Profitability Rollup Worker (16 tests, real-time job cost tracking)
✅ Notification Outbox Worker (Email verified with SendGrid, SMS deferred)
✅ Session Expiration & Cleanup (20 tests, memory leak prevention)

**Phase 3: QuickBooks Integration (COMPLETE - 4 tasks)**
✅ OAuth 2.0 Flow & Hybrid Schema Refactoring (100% functional)
✅ Sync Mapping & Upsert Logic (27 tests, bidirectional sync)
✅ Conflict Detection & Resolution (15 tests, 3 resolution strategies)
✅ Webhook Handler (13 tests, Cloud Events format)

**Test Coverage:** 339/339 passing (100% pass rate)  
**See:** `dev-docs/analysis/phase-4-5-implementation-roadmap.md` for full context

---

## Current Task: Schema Reconciliation

The AevoFab Architect has performed a gap analysis between the current codebase and the Golden Master Schema (`pilot-db-schema-v2.6h.json`) and identified **6 high-priority synchronization gaps** that require surgical fixes.

**Priority:** HIGH (Data Integrity & Business Rule Enforcement)  
**Estimated Effort:** 2-3 days  
**Design Spec:** [`dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md`]

### The 6 Gaps to Fix

| # | Entity | Issue | Impact | Complexity |
|---|--------|-------|--------|------------|
| **1** | `ContactPortalInvite` | Missing UNIQUE constraint on `contact_id` | Allows duplicate invitations per contact | LOW |
| **2** | `UserEndpoint` | No primary email guard function + triggers | "Highlander Rule" not enforced | HIGH |
| **3** | Quote/CO/Invoice | Tax recalc sums line columns, not `_tax_component` tables | Multi-jurisdiction transparency broken | HIGH |
| **4** | `NotificationDeliveryAttempt` | Missing `completed_at` and `next_attempt_after` fields | Exponential backoff retry logic blocked | LOW |
| **5** | `QuoteAcceptance` | `approved_at` is timezone-naive | Violates v2.0 "Double-Lock" standard | MEDIUM |
| **6** | `AuditEvent` | No CHECK constraint on `actor_type` | Allows invalid values (typos, malicious) | LOW |

---

## Requirements

### 1. Follow the Technical Instruction Document

**PRIMARY SOURCE:** [`dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md`]

This document provides:
- **Part 1:** Exact SQLModel code modifications for all 6 gaps
- **Part 2:** Complete Alembic migration manual tweaks (PL/pgSQL functions + triggers)
- **Part 3:** Full pytest test suite (12 tests) with test matrix
- **Part 4:** Step-by-step verification protocol

**You must follow this document exactly.** All code, SQL, and test patterns are provided.

### 2. Implementation Order

Execute in this exact sequence:

1. **SQLModel Changes** (Part 1 of tech doc)
   - Gap 1: Add `__table_args__` with UniqueConstraint to `ContactPortalInvite`
   - Gap 4: Add `completed_at` and `next_attempt_after` to `NotificationDeliveryAttempt`
   - Gap 5: Fix `QuoteAcceptance.approved_at` type hint to `AwareDatetime`
   - Gap 6: Add `__table_args__` with CheckConstraint to `AuditEvent`

2. **Generate Alembic Migration**
   ```bash
   cd backend
   alembic revision --autogenerate -m "sync_with_golden_master_v2_6h"
   ```

3. **Manual Migration Tweaks** (Part 2 of tech doc)
   - Gap 2: Add `guard_user_endpoint_primary_email()` PL/pgSQL function + 3 triggers
   - Gap 3: Add 3 PL/pgSQL functions (`recalc_quote_totals_fn()`, `recalc_change_order_totals_fn()`, `recalc_invoice_totals_fn()`) + 6 triggers
   - **CRITICAL:** Drop old triggers before creating new ones (see tech doc)

4. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

5. **Create Test Suite** (Part 3 of tech doc)
   - Create `backend/tests/test_schema_sync_v2_6h.py`
   - Copy all 12 tests from tech doc exactly as written

6. **Run Tests**
   ```bash
   cd backend && source .venv/bin/activate
   pytest backend/tests/test_schema_sync_v2_6h.py -v
   ```

7. **Verify Complete Success** (Part 4 of tech doc)
   - All ## new tests pass (new tests added in this task)
   - All ### existing non-integration tests still pass (no regression)
   - All ### total tests still pass (including integration tests)
   - Total: ###/### passing (get the ### listed in this list from the test numbers from the last task completed)

### 3. Testing Standards (CRITICAL)

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL 339 existing tests MUST still pass** (baseline cannot regress)
- **ALL 12 new tests MUST pass** (schema sync verification)
- **ALL integration tests MUST pass**
- **Target: ###/### passing (100%)** (based on the results of the last task completed)
- **Deprecation warning** (to avoid test deprecation warnings, use session.query() instead of session.exec())

**Test Execution:**
```bash
# Run existing tests first (validate baseline)
cd backend && source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v

# Run new schema sync tests
pytest tests/test_schema_sync_v2_6h.py -v

# Run all tests together (final verification)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Test Matrix from Tech Doc:**

| Entity | Test Scenario | Expected Behavior |
|--------|---------------|-------------------|
| Financials | Multi-Component Sum | Header `tax_cents` = SUM of all `tax_component.amount_cents` for active lines |
| Financials | Component Update | Updating component `amount_cents` instantly updates parent header total |
| Financials | Component Deletion | Deleting component reduces header `tax_cents` and `total_cents` |
| Financials | Soft-Delete (`is_active`) | Setting line `is_active=false` excludes its tax components from header |
| Identity | Primary Demotion | Setting new endpoint `is_primary=true` auto-demotes old primary |
| Identity | "Highlander Rule" | Cannot delete or demote the ONLY primary email (DB exception) |

### 4. Database Standards

**Golden Master Rule:**
- The JSON schema (`pilot-db-schema-v2.6h.json`) is the **authoritative source of truth**
- If SQLModel differs from JSON → SQLModel MUST be updated to match JSON
- If database state differs from JSON → Database MUST be updated via migration
- **Exception:** Only the Architect can approve deviations from Golden Master

**Critical Design Decisions (from Tech Doc):**

1. **Preserve Existing Logic**
   - `core/db.py` already sets `app.user_id` via `SET LOCAL`
   - Audit triggers rely on this - DO NOT remove or duplicate

2. **is_active Filter Enforcement**
   - All 3 tax recalc functions MUST include `AND is_active = true` in SUM queries
   - This excludes soft-deleted line items from financial totals

3. **Timezone "Double-Lock" Standard**
   - Python: `AwareDatetime` type hint
   - SQLAlchemy: `Column(DateTime(timezone=True))`
   - PostgreSQL: `TIMESTAMPTZ`

4. **Trigger Ordering**
   - Drop old quote/CO/invoice triggers BEFORE creating new ones
   - Use exact SQL from tech doc Part 2

### 5. Code Standards

- **Follow tech doc exactly** - All code is provided, no improvisation
- **Type hints required** - Use `AwareDatetime`, not `datetime`
- **Import statements** - Add missing imports (UniqueConstraint, CheckConstraint)
- **Docstrings required** - Document all new functions
- **No feature creep** - Strictly implement the 6 gaps, nothing more

### 6. Workflow

1. **Read the Technical Instruction Document** - [`dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md`]
2. **Implement Part 1** - SQLModel changes (4 gaps)
3. **Generate migration** - `alembic revision --autogenerate`
4. **Implement Part 2** - Manual PL/pgSQL tweaks (2 gaps)
5. **Apply migration** - `alembic upgrade head`
6. **Implement Part 3** - Create test suite (12 tests)
7. **Run tests** - Must achieve 351/351 passing
8. **Update documentation** - Add "Implementation Complete" section to tech doc

### 7. Documentation Update (SIMPLIFIED)

**Unlike roadmap tasks, this schema sync work only requires updating ONE document:**

**Document to Update:** [`dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md`]

Add a new section at the end:

```markdown
---

## Implementation Complete

**Completion Date:** YYYY-MM-DD  
**Implemented By:** MVP Builder Agent  
**Test Results:** 351/351 passing (12 new + 339 existing)

### What Was Delivered

**Gap 1: ContactPortalInvite Uniqueness**
- Added UNIQUE constraint on `contact_id`
- File: `backend/app/models/auth.py` (lines XX-YY)
- Test: `test_contact_portal_invite_unique_contact_id` ✅ PASSING

**Gap 2: User Endpoint Primary Email Guard**
- Created `guard_user_endpoint_primary_email()` PL/pgSQL function
- Added 3 triggers (BEFORE INSERT/UPDATE/DELETE)
- Files: Migration `XXXX_sync_with_golden_master.py` (lines XX-YY)
- Tests: 
  - `test_user_endpoint_primary_demotion` ✅ PASSING
  - `test_user_endpoint_highlander_rule_delete` ✅ PASSING
  - `test_user_endpoint_highlander_rule_demote` ✅ PASSING

**Gap 3: Componentized Tax Recalc**
- Redesigned 3 PL/pgSQL functions (quote, CO, invoice)
- Created 6 triggers (2 per entity: line + tax_component)
- Added `is_active = true` filtering
- Files: Migration `XXXX_sync_with_golden_master.py` (lines XX-YY)
- Tests:
  - `test_quote_multi_component_sum` ✅ PASSING
  - `test_quote_component_update` ✅ PASSING
  - `test_quote_component_deletion` ✅ PASSING
  - `test_quote_soft_delete_line_recalc` ✅ PASSING

**Gap 4: NotificationDeliveryAttempt Lifecycle**
- Added `completed_at` (TIMESTAMPTZ)
- Added `next_attempt_after` (TIMESTAMPTZ)
- File: `backend/app/models/system.py` (lines XX-YY)
- Test: `test_notification_delivery_attempt_lifecycle` ✅ PASSING

**Gap 5: QuoteAcceptance Timezone Compliance**
- Changed `approved_at` from `datetime` to `AwareDatetime`
- File: `backend/app/models/quoting.py` (lines XX-YY)
- Test: `test_quote_acceptance_approved_at_timezone` ✅ PASSING

**Gap 6: AuditEvent Actor Type Constraint**
- Added CHECK constraint: `actor_type IN ('system','user','platform','external_webhook')`
- File: `backend/app/models/system.py` (lines XX-YY)
- Tests:
  - `test_audit_event_actor_type_valid` ✅ PASSING
  - `test_audit_event_actor_type_invalid` ✅ PASSING

### Migration Details

**File:** `backend/migrations/versions/YYYY_MM_DD_HHMM-XXXX_sync_with_golden_master_v2_6h.py`  
**Size:** ~XXX lines  
**Upgrade Time:** < 5 seconds  
**Downgrade:** Fully implemented and tested

### Test Coverage

**New Tests:** 12  
**Existing Tests:** 339  
**Total:** 351/351 passing (100%)

**Test File:** `backend/tests/test_schema_sync_v2_6h.py`  
**Test Execution Time:** ~X seconds

### Verification Checklist

- [x] All 6 SQLModel changes applied
- [x] Alembic migration created and applied
- [x] All 12 new tests written and passing
- [x] All 339 existing tests still passing (no regression)
- [x] Migration rollback tested and working
- [x] Documentation updated

### Production Impact

**Risk Level:** LOW  
**Downtime Required:** None (backward compatible)  
**Performance Impact:** < 5ms per database operation (measured on db.t4g.micro)  
**Cost Impact:** $0 (database-level triggers, no additional compute)

### Notes

[Add any implementation notes, issues encountered, or future considerations]
```

**That's it!** No need to update the three roadmap documents since this is technical maintenance, not feature work.

---

## Key Files to Review

### Architecture & Design
- [`dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md`] - **PRIMARY SOURCE** ⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **GOLDEN MASTER** (authoritative)
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations & schema
- `dev-docs/analysis/phase-4-5-implementation-roadmap.md` - Context (Phases 1-3 complete)

### Backend Code (Files to Modify)
- `backend/app/models/auth.py` - Gap 1: ContactPortalInvite
- `backend/app/models/system.py` - Gap 4: NotificationDeliveryAttempt, Gap 6: AuditEvent
- `backend/app/models/quoting.py` - Gap 5: QuoteAcceptance
- `backend/app/models/core.py` - Context for Gap 2: UserEndpoint (no changes)

### Migration (To Create)
- `backend/migrations/versions/YYYY_MM_DD_HHMM-*_sync_with_golden_master_v2_6h.py` - New migration file

### Tests (To Create)
- `backend/tests/test_schema_sync_v2_6h.py` - New test file (12 tests)
- `backend/tests/conftest.py` - Review for existing fixtures

### Infrastructure Context
- `.roo/rules-aevofab-architect/infrastructure-constraints.md` - Cost limits ($1k/mo cap)
- `.roo/rules-aevofab-architect/scaling-logic.md` - Resource scaling triggers

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] All 6 SQLModel changes implemented exactly as specified in tech doc
- [ ] Alembic migration created with autogenerate
- [ ] Manual PL/pgSQL functions and triggers added to migration
- [ ] Migration applied successfully (`alembic upgrade head`)
- [ ] All 12 new tests written and passing (from tech doc Part 3)
- [ ] **ALL 339 existing tests still passing** (no regression)
- [ ] **Total: 351/351 tests passing (100%)**
- [ ] Migration rollback tested (`alembic downgrade -1` then `upgrade head`)
- [ ] Tech doc updated with "Implementation Complete" section
- [ ] No deviations from Golden Master JSON schema

**Zero Tolerance Policy:**
- **Any failing test = INCOMPLETE**
- **Test pass rate MUST be 100% (351/351)**
- If tests fail after 10+ attempts, create detailed fix document (but mark task incomplete)

---

## Questions to Ask

**Before starting:**
1. Have I read the Technical Instruction Document thoroughly?
2. Do I understand the Golden Master Rule (JSON schema = authority)?
3. Have I reviewed the 6 gaps and their complexity levels?
4. Do I have the correct test fixtures available in conftest.py?

**During implementation:**
1. Am I following the tech doc code examples exactly?
2. Are ALL 351 tests passing (12 new + 339 existing)?
3. Did I drop old triggers before creating new ones (Gap 3)?
4. Am I preserving the existing `app.user_id` logic (don't duplicate)?

**After implementation:**
1. Do I have 100% test pass rate (351/351)?
2. Have I updated the tech doc with implementation results?
3. Can the migration be rolled back cleanly?
4. Have I verified against the Golden Master JSON?

---

## Example Task Flow

```bash
# 1. Read the tech doc
cat dev-docs/analysis/db-schema-vs-design/db-schema-sync-technical-instruction-v1.0.md

# 2. Check current models
ls -la backend/app/models/
cat backend/app/models/auth.py | grep -A 15 "class ContactPortalInvite"
cat backend/app/models/system.py | grep -A 20 "class NotificationDeliveryAttempt"
cat backend/app/models/system.py | grep -A 30 "class AuditEvent"
cat backend/app/models/quoting.py | grep -A 30 "class QuoteAcceptance"

# 3. Run baseline tests (should be 339 passing)
cd backend && source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 4. Implement SQLModel changes (Part 1 of tech doc)
# [modify backend/app/models/*.py files]

# 5. Generate migration
alembic revision --autogenerate -m "sync_with_golden_master_v2_6h"

# 6. Add manual PL/pgSQL tweaks (Part 2 of tech doc)
# [edit generated migration file]

# 7. Apply migration
alembic upgrade head

# 8. Create test file (Part 3 of tech doc)
# [create backend/tests/test_schema_sync_v2_6h.py]

# 9. Run new tests
pytest tests/test_schema_sync_v2_6h.py -v

# 10. Run ALL tests (verify no regression)
pytest tests/ -v

# 11. Verify 351/351 passing
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# 12. Test migration rollback
alembic downgrade -1
alembic upgrade head

# 13. Update tech doc with results
# [add "Implementation Complete" section]
```

---

## Notes

- **Schema Sync is Technical Maintenance:** This is NOT a new feature - it's ensuring our implementation matches the design spec
- **Golden Master Authority:** The JSON schema is the single source of truth - deviations require Architect approval
- **Zero Regression Policy:** All 339 existing tests MUST still pass after changes
- **Cost Impact:** $0 - Database triggers execute in < 5ms, no additional compute needed
- **Production Safe:** All changes are backward compatible, no downtime required
- **Rollback Tested:** Every `upgrade()` must have a working `downgrade()` implementation

**If you get stuck:**
- The tech doc has ALL code examples - copy/paste is encouraged
- Each gap has a clear complexity level (LOW/MEDIUM/HIGH)
- Start with the LOW complexity gaps first (Gaps 1, 4, 6)
- Ask for clarification if anything is unclear

---

**Ready to Begin!** 🚀

Start by reading the Technical Instruction Document, then implement the 6 gaps in the order specified. All code, SQL, and tests are provided - follow the document precisely for fastest completion.
