# Batch B1 — Quote Core Design Document

**Batch**: B1  
**Name**: Quote Core  
**Version**: 1.0  
**Date**: April 30, 2026  
**Author**: Pilot Architect  
**Source Ledger**: `frontend-backend-mvp-additions-latest.md` v6.1 (frozen)  
**Implementation Plan**: `pilot-app-mvp-backend-impl-plan.md §6.B1`  
**Prerequisite Batches**: None  
**Unlocks**: All quote-related voice grammar (A31, this batch); approval workflow; template system  
**Estimated Effort**: 28–41 days  
**Test Subfolder**: `tests/batch_b1/`

---

## Input Read Summary

All six required reads were completed before authoring this document:

| Read | Source | Key Findings |
|:---|:---|:---|
| READ 1 | `§6.B1` impl plan | 10 items in execution order; load-bearing schema A24 must be first |
| READ 2 | Additions ledger A24–A31, A2, A3, A25–A27 | Full authoritative detail per item |
| READ 3 | `mvp-arch.md` v5 §6, §14, §16 | Patterns: confirm-as-turn §16.3/§6.6; quote version immutability §14.4; 3-part migration §16.2 Step 2 |
| READ 4 | `pilot-python-engineer-methods.md` §16–22 | §16.2 Step 2 migration pattern; §17 Celery patterns; §18 SSE; §20 staleness check; §21 three-tier resolver |
| READ 5 | postgres-local MCP (live DB) | Verified all target tables; confirmed missing columns; identified `quote_status` seeds |
| READ 6 | `quoting.py`, `quotes.py`, `voice_action_router.py`, `permissions.py`, `db_models_map.md`, `app_model_import.md` | Real function signatures, model fields, import paths, INTENT_HANDLERS pattern |

---

## A. MIGRATION PLAN

### Pre-Migration Column Verification (MCP Results)

**`quote_line` table — current columns confirmed:**
`id`, `tenant_id`, `quote_id`, `position`, `qco_line_type_id`, `pricebook_item_id`, `description` (`character varying`, no length cap), `quantity`, `unit`, `unit_price_cents`, `unit_cost_cents`, `cost_source`, `supplier_id`, `supplier_item_id`, `taxability_code`, `tax_rate_pct`, `tax_basis_cents`, `tax_amount_cents`, `tax_jurisdiction_code`, `tax_as_of`, `tax_source`, `subtotal_cents`, `total_cents`, `is_active`, `created_at`, `updated_at`, `created_by`, `updated_by`

**Columns NOT yet present on `quote_line`** (confirmed new):
- `customer_visible` ✅ NEW
- `parent_line_id` ✅ NEW
- `display_order` ✅ NEW
- `is_section_header` ✅ NEW

**`quote_line.description` field**: `character varying` with `character_maximum_length = NULL` — no length cap. No TEXT migration required. A28 is a verification-only item (0 migration needed).

**`quote` table — current columns confirmed:**
`id`, `tenant_id`, `customer_id`, `site_id`, `status_id`, `subtotal_cents`, `tax_cents`, `total_cents`, `currency`, `idempotency_key`, `is_active`, `created_at`, `updated_at`, `created_by`, `updated_by`

**Columns NOT yet present on `quote`** (confirmed new):
- `submitted_by_user_id` ✅ NEW (A2)
- `submitted_at` ✅ NEW (A2)
- `approved_by_user_id` ✅ NEW (A2)
- `approved_at` ✅ NEW (A2)
- `discount_pct` ✅ NEW (A3)
- `discount_amount_cents` ✅ NEW (A3)
- `discount_expires_at` ✅ NEW (A3)
- `discount_applied_by_user_id` ✅ NEW (A3)

**`quote_status` table — existing system codes confirmed:**
`draft` (default), `pending` (Pending Review), `sent`, `accepted`, `rejected`, `expired`, `converted`

**Missing status codes** (confirmed new for B1):
- `pending_approval` ✅ NEW (A2)
- `approved` ✅ NEW (A2)

**`tenant_settings` table — current columns confirmed:**
`tenant_id`, `default_labor_rate_cents`, `default_billable_labor_rate_cents`, `default_quote_validity_days`, `default_invoice_terms_days`

**Columns NOT yet present on `tenant_settings`** (confirmed new):
- `require_approval_for_tech_quotes` ✅ NEW (A2)
- `max_discount_pct_owner` ✅ NEW (A3)

---

### Migration 1 — A24: Quote Line Item Schema Extension

**Migration name**: `phase_fe_1_batch_b1_quote_line_visibility_hierarchy`  
**Pattern**: 3-part migration (nullable → backfill → NOT NULL) for `customer_visible`, `display_order`, `is_section_header`. `parent_line_id` stays nullable by design.

**New columns on `quote_line`**:

| Column | Type | Nullable | Default | FK | Notes |
|:---|:---|:---|:---|:---|:---|
| `customer_visible` | `BOOLEAN` | NOT NULL | `TRUE` | — | Hidden lines are internal cost-tracking |
| `parent_line_id` | `UUID` | NULL | — | `quote_line(id) ON DELETE RESTRICT` | Self-referential; depth ≤ 1 |
| `display_order` | `INT` | NOT NULL | 0 (backfill) | — | Explicit ordering separate from position |
| `is_section_header` | `BOOLEAN` | NOT NULL | `FALSE` | — | Visual grouping divider, no price |

**New constraints**:
```sql
-- Section headers cannot be children
ALTER TABLE quote_line ADD CONSTRAINT chk_section_header_no_parent
  CHECK (NOT (is_section_header = TRUE AND parent_line_id IS NOT NULL));
```

**New indexes**:
```sql
CREATE INDEX ix_quote_line_parent_line_id ON quote_line(parent_line_id);
```

**New triggers (mandatory per §13.4 of methods doc)**:
```sql
CREATE TRIGGER audit_quote_line_changes
  AFTER INSERT OR DELETE OR UPDATE ON public.quote_line
  FOR EACH ROW EXECUTE FUNCTION audit.log_changes();

CREATE TRIGGER trg_quote_line_guard_created_immutable
  BEFORE UPDATE ON public.quote_line
  FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();

CREATE TRIGGER trg_quote_line_set_updated_at
  BEFORE UPDATE ON public.quote_line
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

> Note: Existing triggers on `quote_line` may already exist. Use `CREATE OR REPLACE TRIGGER` or verify with `SELECT tgname FROM pg_trigger WHERE tgrelid = 'quote_line'::regclass` before writing migration.

---

### Migration 2 — A28: Description Verification

**Migration name**: None required  
**Result**: `quote_line.description` is `character varying` with no cap — functionally identical to `TEXT` in PostgreSQL. The ORM model field `description: str = Field(nullable=False)` in `backend/app/models/quoting.py` has no explicit `sa_column`, so PostgreSQL stores it as VARCHAR without a cap. **No migration needed.**

**A28 action**: Update `QuoteLineCreate` schema docstring to document the no-length-cap guarantee. No DDL change.

---

### Migration 3 — A2: Quote Approval State Machine

**Migration name**: `phase_fe_1_batch_b1_quote_approval_state_machine`

**New `quote_status` seed rows**:
```sql
-- New status codes (tenant_id = NULL = system-wide)
INSERT INTO quote_status (id, tenant_id, code, name, is_terminal, is_default, is_active)
VALUES
  (gen_random_uuid(), NULL, 'pending_approval', 'Pending Approval', FALSE, FALSE, TRUE),
  (gen_random_uuid(), NULL, 'approved', 'Approved', FALSE, FALSE, TRUE);
```

**New columns on `quote`**:

| Column | Type | Nullable | Default | FK | Notes |
|:---|:---|:---|:---|:---|:---|
| `submitted_by_user_id` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | Tech who submitted |
| `submitted_at` | `TIMESTAMPTZ` | NULL | — | — | Submission timestamp |
| `approved_by_user_id` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | Owner/accountant who approved |
| `approved_at` | `TIMESTAMPTZ` | NULL | — | — | Approval timestamp |

**New column on `tenant_settings`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `require_approval_for_tech_quotes` | `BOOLEAN` | NOT NULL | `TRUE` | ON = require approval; OFF = tech quotes go directly to sent |

**3-part migration pattern** for `tenant_settings` backfill:
```sql
-- Part 1: Add nullable
ALTER TABLE tenant_settings ADD COLUMN require_approval_for_tech_quotes BOOLEAN NULL;
-- Part 2: Backfill existing rows
UPDATE tenant_settings SET require_approval_for_tech_quotes = TRUE WHERE require_approval_for_tech_quotes IS NULL;
-- Part 3: Lock NOT NULL
ALTER TABLE tenant_settings ALTER COLUMN require_approval_for_tech_quotes SET NOT NULL;
ALTER TABLE tenant_settings ALTER COLUMN require_approval_for_tech_quotes SET DEFAULT TRUE;
```

---

### Migration 4 — A3: Time-Limited Discounts

**Migration name**: `phase_fe_1_batch_b1_quote_discount_fields`

**New columns on `quote`**:

| Column | Type | Nullable | Default | FK | Notes |
|:---|:---|:---|:---|:---|:---|
| `discount_pct` | `NUMERIC(5,2)` | NULL | — | — | Percentage discount applied |
| `discount_amount_cents` | `INT` | NULL | — | — | Computed discount in cents |
| `discount_expires_at` | `TIMESTAMPTZ` | NULL | — | — | Celery task transitions to expired |
| `discount_applied_by_user_id` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | Who applied the discount |

**New column on `tenant_settings`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `max_discount_pct_owner` | `NUMERIC(5,2)` | NOT NULL | `15.00` | Cap for discount_pct validation |

**3-part migration pattern** for `tenant_settings` backfill:
```sql
ALTER TABLE tenant_settings ADD COLUMN max_discount_pct_owner NUMERIC(5,2) NULL;
UPDATE tenant_settings SET max_discount_pct_owner = 15.00 WHERE max_discount_pct_owner IS NULL;
ALTER TABLE tenant_settings ALTER COLUMN max_discount_pct_owner SET NOT NULL;
ALTER TABLE tenant_settings ALTER COLUMN max_discount_pct_owner SET DEFAULT 15.00;
```

---

### Migration 5 — A25: Quote Template Schema

**Migration name**: `phase_fe_1_batch_b1_quote_template_schema`

**New table: `quote_template`**:

| Column | Type | Nullable | Default | FK | Notes |
|:---|:---|:---|:---|:---|:---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | PK | |
| `tenant_id` | `UUID` | NULL | — | `tenant(id) ON DELETE RESTRICT` | NULL = system template |
| `name` | `TEXT` | NOT NULL | — | — | |
| `description` | `TEXT` | NULL | — | — | |
| `style` | `TEXT` | NOT NULL | — | — | `component | deliverable | lump_sum` CHECK |
| `category` | `TEXT` | NULL | — | — | `service_call | installation | inspection | null` |
| `system_template_id` | `UUID` | NULL | — | `quote_template(id) ON DELETE RESTRICT` | When a tenant fork, refs the source system template |
| `forked_from_version` | `INT` | NULL | — | — | Version of system template at fork time |
| `current_version` | `INT` | NOT NULL | `1` | — | Increments on each update |
| `is_active` | `BOOLEAN` | NOT NULL | `TRUE` | — | |
| `is_system_template` | `BOOLEAN` | NOT NULL | `FALSE` | — | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | — | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | — | |
| `created_by` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | |
| `updated_by` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | |

**Constraints on `quote_template`**:
```sql
CHECK (style IN ('component', 'deliverable', 'lump_sum'))
UNIQUE (tenant_id, name)  -- prevent duplicate names within a tenant
```

**New table: `quote_template_line`**:

| Column | Type | Nullable | Default | FK | Notes |
|:---|:---|:---|:---|:---|:---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | PK | |
| `tenant_id` | `UUID` | NOT NULL | — | `tenant(id) ON DELETE RESTRICT` | Matches parent template's tenant_id context |
| `quote_template_id` | `UUID` | NOT NULL | — | `quote_template(id) ON DELETE RESTRICT` | |
| `parent_line_id` | `UUID` | NULL | — | `quote_template_line(id) ON DELETE RESTRICT` | Mirrors quote_line hierarchy |
| `display_order` | `INT` | NOT NULL | `0` | — | |
| `qco_line_type_id` | `UUID` | NOT NULL | — | `qco_line_type(id)` | |
| `description` | `TEXT` | NOT NULL | — | — | Supports `{variable}` placeholders |
| `default_quantity` | `NUMERIC(12,3)` | NOT NULL | `1` | — | |
| `default_unit_price_cents` | `INT` | NOT NULL | `0` | — | |
| `customer_visible` | `BOOLEAN` | NOT NULL | `TRUE` | — | |
| `is_section_header` | `BOOLEAN` | NOT NULL | `FALSE` | — | |
| `is_active` | `BOOLEAN` | NOT NULL | `TRUE` | — | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | — | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | — | |
| `created_by` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | |
| `updated_by` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | |

**Indexes on `quote_template_line`**:
```sql
CREATE INDEX ix_quote_template_line_template_id ON quote_template_line(quote_template_id);
CREATE INDEX ix_quote_template_line_tenant_id ON quote_template_line(tenant_id);
CREATE INDEX ix_quote_template_line_parent ON quote_template_line(parent_line_id);
```

**Seed data** (in migration upgrade):
```sql
-- Three system templates — tenant_id = NULL, is_system_template = TRUE
INSERT INTO quote_template (id, tenant_id, name, style, category, is_active, is_system_template, current_version)
VALUES
  (gen_random_uuid(), NULL, 'Service Call Basic', 'component', 'service_call', TRUE, TRUE, 1),
  (gen_random_uuid(), NULL, 'Installation Standard', 'deliverable', 'installation', TRUE, TRUE, 1),
  (gen_random_uuid(), NULL, 'Fixed Bid Simple', 'lump_sum', NULL, TRUE, TRUE, 1);
```

**Triggers** on both `quote_template` and `quote_template_line`: audit, immutable guard, updated_at sync (per §13.4 pattern).

---

### Migration 6 — A26 + A27: No New Tables Required

A26 (Celery task) and A27 (API endpoint) operate on existing tables. No DDL migration needed for A26 or A27 independently. Both are code-only additions that consume the `quote_template` and `quote_template_line` tables from Migration 5.

---

### Migration 7 — A29: Pending Edit Storage

**Migration name**: `phase_fe_1_batch_b1_quote_pending_edit`

**New table: `quote_pending_edit`**:

| Column | Type | Nullable | Default | FK | Notes |
|:---|:---|:---|:---|:---|:---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | PK | |
| `tenant_id` | `UUID` | NOT NULL | — | `tenant(id) ON DELETE RESTRICT` | |
| `quote_id` | `UUID` | NOT NULL | — | `quote(id) ON DELETE RESTRICT` | |
| `quote_version_id` | `UUID` | NOT NULL | — | `quote_version(id) ON DELETE RESTRICT` | The version being reviewed |
| `editor_user_id` | `UUID` | NOT NULL | — | `user(id) ON DELETE RESTRICT` | The owner doing the editing |
| `edit_type` | `TEXT` | NOT NULL | — | — | `modify_line | add_line | delete_line | edit_notes` CHECK |
| `target_line_id` | `UUID` | NULL | — | `quote_line(id) ON DELETE RESTRICT` | For modify/delete; null for add |
| `edit_payload` | `JSONB` | NOT NULL | — | — | Proposed change as JSON |
| `annotation` | `TEXT` | NULL | — | — | Optional per-edit explanation |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | — | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | — | |
| `created_by` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | |
| `updated_by` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | |

**Constraints**:
```sql
CHECK (edit_type IN ('modify_line', 'add_line', 'delete_line', 'edit_notes'))
```

**Indexes**:
```sql
CREATE INDEX ix_quote_pending_edit_quote_id ON quote_pending_edit(quote_id);
CREATE INDEX ix_quote_pending_edit_editor ON quote_pending_edit(editor_user_id, quote_version_id);
CREATE INDEX ix_quote_pending_edit_tenant ON quote_pending_edit(tenant_id);
```

**Triggers**: audit, immutable guard, updated_at sync.

---

### Migration 8 — A30: Approval Comment & Annotation System

**Migration name**: `phase_fe_1_batch_b1_quote_approval_comment`

**New table: `quote_approval_comment`**:

| Column | Type | Nullable | Default | FK | Notes |
|:---|:---|:---|:---|:---|:---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | PK | |
| `tenant_id` | `UUID` | NOT NULL | — | `tenant(id) ON DELETE RESTRICT` | |
| `quote_id` | `UUID` | NOT NULL | — | `quote(id) ON DELETE RESTRICT` | |
| `quote_version_id` | `UUID` | NOT NULL | — | `quote_version(id) ON DELETE RESTRICT` | Which version this comment is anchored to |
| `target_line_id` | `UUID` | NULL | — | `quote_line(id) ON DELETE RESTRICT` | NULL = overall comment |
| `author_user_id` | `UUID` | NOT NULL | — | `user(id) ON DELETE RESTRICT` | |
| `comment_type` | `TEXT` | NOT NULL | — | — | `kickback | rejection | edit_annotation` CHECK |
| `content` | `TEXT` | NOT NULL | — | — | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | — | AppendOnly — no updated_at |
| `created_by` | `UUID` | NULL | — | `user(id) ON DELETE RESTRICT` | |

**Mixin note**: Use `AppendOnlyMixin` (provides only `created_at`, `created_by`) — comments are never updated, only created. This matches the audit-trail semantics.

**Constraints**:
```sql
CHECK (comment_type IN ('kickback', 'rejection', 'edit_annotation'))
```

**Indexes**:
```sql
CREATE INDEX ix_quote_approval_comment_quote_id ON quote_approval_comment(quote_id);
CREATE INDEX ix_quote_approval_comment_tenant ON quote_approval_comment(tenant_id);
CREATE INDEX ix_quote_approval_comment_version ON quote_approval_comment(quote_version_id);
```

**Triggers**: audit, immutable guard only (no updated_at trigger on append-only table).

---

### Migration Summary Table

| # | Migration Name | Tables | Items |
|:---|:---|:---|:---|
| 1 | `phase_fe_1_batch_b1_quote_line_visibility_hierarchy` | `quote_line` (4 cols) | A24 |
| 2 | *(none — verification only)* | — | A28 |
| 3 | `phase_fe_1_batch_b1_quote_approval_state_machine` | `quote_status` (seed), `quote` (4 cols), `tenant_settings` (1 col) | A2 |
| 4 | `phase_fe_1_batch_b1_quote_discount_fields` | `quote` (4 cols), `tenant_settings` (1 col) | A3 |
| 5 | `phase_fe_1_batch_b1_quote_template_schema` | `quote_template` (new), `quote_template_line` (new) | A25 |
| 6 | *(code-only)* | — | A26, A27 |
| 7 | `phase_fe_1_batch_b1_quote_pending_edit` | `quote_pending_edit` (new) | A29 |
| 8 | `phase_fe_1_batch_b1_quote_approval_comment` | `quote_approval_comment` (new) | A30 |

---

## B. EXECUTION ORDER

| # | Item | Rationale | Est. Days |
|:---|:---|:---|:---:|
| 1 | **A24** — Quote Line Item Schema Extension | Load-bearing schema change. `customer_visible`, `parent_line_id`, `display_order`, `is_section_header` must exist before any other quote work. A25 templates mirror this structure; A29 pending edits reference `quote_line(id)`. | 3–4 |
| 2 | **A28** — Multi-Line Description Verification | Done in A24 migration context. MCP confirmed `description` is VARCHAR with no cap — effectively TEXT. Zero migration. Document guarantee in schema blueprint. Update `QuoteLineCreate` schema docstring. | 0.5 |
| 3 | **A2** — Quote Approval Workflow State Machine | Core state machine. Must exist before A29 (`quote_pending_edit` requires `pending_approval` state existence) and A30 (kickback/reject endpoints are approval-state transitions). Adds `pending_approval` + `approved` status codes, new quote columns, tenant setting. | 3–5 |
| 4 | **A25** — Quote Template Schema with Style and Versioning | Depends on A24 (template lines mirror `quote_line` structure including `customer_visible`, `display_order`, `is_section_header`). Name-disambiguates `quote_template` vs. `communication_template`. Seeds 3 system templates. | 5–7 |
| 5 | **A26** — System Template Update Notification Flow | Depends on A25 (`forked_from_version` + `current_version` comparison logic). Nightly Celery Beat task. Dedup pattern per `(tenant_id, system_template_id, system_template_version)`. | 2–3 |
| 6 | **A27** — Save Quote as Template | Depends on A25 schema (creates `quote_template_line` rows). Variable namespace must align with A4 (B4) comms templates. RBAC: `quote_template.create` owner/accountant only. | 3–4 |
| 7 | **A3** — Time-Limited Discounts with Margin Cap | Uses A2's quote version immutability pattern (apply-discount creates a new `quote_version`) and A24's line item structure. Celery Beat task for discount expiry. | 2–3 |
| 8 | **A29** — Pending Edit Storage During Owner Review | Depends on A2 (`pending_approval` state existence). New `quote_pending_edit` table. Atomic apply-with-edits logic creates new `quote_version` + transitions state. | 4–5 |
| 9 | **A30** — Approval Comment & Annotation System | Depends on A29 (comment type `edit_annotation` ties to pending edits; kickback endpoint requires comments). New `quote_approval_comment` table. Kickback and reject atomic endpoints. | 3–4 |
| 10 | **A31** — Voice Intent Grammar for Approval Actions | Depends on A2 state machine + A29/A30 endpoints. Adds `approve_quote`, `reject_quote`, `kickback_quote`, `list_pending_quotes` to `voice_action_router.py`. Confirm-as-turn for `approve_quote` and `kickback_quote`. | 2–3 |

---

## C. NEW API ENDPOINTS

### A2 — Quote Approval Workflow

**`POST /api/v1/quotes/{id}/submit-for-approval`**
- Auth: JWT required
- Permission: `quote.submit_for_approval` (technician role)
- Request body: `{}` (no body — action on existing quote)
- Response `200`: `{ "quote_id": UUID, "status": "pending_approval", "submitted_at": TIMESTAMPTZ, "submitted_by_user_id": UUID }`
- 404: Quote not found for tenant
- 422: Quote not in `draft` status
- 403: User lacks `quote.submit_for_approval`
- Side effects: Creates `notification_outbox` record (push + email to owner on new pending quote). Fires only when `require_approval_for_tech_quotes = TRUE`.

**`POST /api/v1/quotes/{id}/approve`**
- Auth: JWT required
- Permission: `quote.approve` (owner, accountant)
- Request body: `{ "expected_quote_version_id": UUID }` (staleness check)
- Response `200`: `{ "quote_id": UUID, "status": "approved", "approved_at": TIMESTAMPTZ, "approved_by_user_id": UUID, "quote_version_id": UUID }`
- 404: Quote not found
- 409: Staleness conflict — quote was modified since last view (`{ "type": "stale-state", "refreshed": QuoteResponse }`)
- 422: Quote not in `pending_approval` status

**`POST /api/v1/quotes/{id}/approve-with-edits`**
- Auth: JWT required
- Permission: `quote.approve` (owner, accountant)
- Request body: `{ "expected_quote_version_id": UUID }` (staleness check)
- Response `200`: `{ "quote_id": UUID, "status": "approved", "new_version_id": UUID, "applied_edits_count": INT }`
- Atomic: applies all pending edits from `quote_pending_edit` for `editor_user_id`, creates new `quote_version`, deletes pending edit rows, transitions status to `approved`
- 422: No pending edits found for this user
- 409: Staleness

**`POST /api/v1/quotes/{id}/reject`**
- Auth: JWT required
- Permission: `quote.approve` (owner, accountant)
- Request body: `{ "expected_quote_version_id": UUID, "overall_comment": TEXT (required) }`
- Response `200`: `{ "quote_id": UUID, "status": "rejected", "comment_id": UUID }`
- Atomic: creates `quote_approval_comment` (type=`rejection`), transitions status to `rejected`
- 422: `overall_comment` missing or empty

**`POST /api/v1/quotes/{id}/kickback`**
- Auth: JWT required
- Permission: `quote.approve` (owner, accountant)
- Request body: `{ "expected_quote_version_id": UUID, "overall_comment": TEXT (optional), "line_comments": [{ "target_line_id": UUID, "content": TEXT }] (optional) }`
- Validation: at least one of `overall_comment` or `line_comments` required
- Response `200`: `{ "quote_id": UUID, "status": "draft", "comment_count": INT }`
- Atomic: creates `quote_approval_comment` rows, transitions status to `draft`

---

### A3 — Time-Limited Discounts

**`POST /api/v1/quotes/{id}/apply-discount`**
- Auth: JWT required
- Permission: `quote.apply_discount` (owner, accountant)
- Request body: `{ "discount_pct": NUMERIC (required), "discount_expires_at": TIMESTAMPTZ (optional), "expected_quote_version_id": UUID }`
- Response `201`: `{ "quote_id": UUID, "discount_pct": NUMERIC, "discount_amount_cents": INT, "discount_expires_at": TIMESTAMPTZ, "new_version_id": UUID }`
- 400: `discount_pct > tenant.max_discount_pct_owner`
- 422: Discount already applied to quote
- Creates new `quote_version` (immutability pattern), sets discount columns on `quote`

---

### A25 — Quote Templates

**`GET /api/v1/quote-templates`**
- Auth: JWT required
- Permission: `quotes.view`
- Query params: `style`, `category`, `system_only: bool`, `tenant_only: bool`
- Response: `[{ "id": UUID, "name": TEXT, "style": TEXT, "category": TEXT, "is_system_template": BOOL, "current_version": INT, "tenant_id": UUID|null }]`

**`POST /api/v1/quote-templates`**
- Auth: JWT required
- Permission: `quote_template.create`
- Request body: `{ "name": TEXT, "style": TEXT, "category": TEXT|null, "lines": [QuoteTemplateLineCreate] }`
- Response `201`: Full template with lines

**`POST /api/v1/quote-templates/{id}/fork`**
- Auth: JWT required
- Permission: `quote_template.fork_system`
- Request body: `{ "name": TEXT (optional override) }`
- Response `201`: New tenant-owned copy with `system_template_id` and `forked_from_version` populated

**`POST /api/v1/quote-templates/{id}/disable`**
- Auth: JWT required
- Permission: `quote_template.edit`
- Response `200`: `{ "id": UUID, "is_active": false }`

**`POST /api/v1/quotes/from-template/{template_id}`**
- Auth: JWT required
- Permission: `quotes.create`
- Request body: `{ "customer_id": UUID, "site_id": UUID, "variable_overrides": { "customer_name": TEXT, ... } }`
- Response `201`: `QuoteResponse` — new quote instantiated with template lines

---

### A27 — Save Quote as Template

**`POST /api/v1/quotes/{id}/save-as-template`**
- Auth: JWT required
- Permission: `quote_template.create`
- Request body: `{ "name": TEXT, "category": TEXT|null, "style": TEXT|null (defaults to quote's implied style) }`
- Response `201`: `QuoteTemplateResponse` — new `quote_template` + `quote_template_line` rows
- Side effects: replaces customer-specific values with template variables per variable namespace

---

### A29 — Pending Edit Storage

**`GET /api/v1/quotes/{id}/pending-edits`**
- Auth: JWT required
- Permission: `quote.approve`
- Response: list of `quote_pending_edit` rows for the current user + this quote version

**`POST /api/v1/quotes/{id}/pending-edits`**
- Auth: JWT required
- Permission: `quote.approve`
- Request body: `{ "edit_type": TEXT, "target_line_id": UUID|null, "edit_payload": JSONB, "annotation": TEXT|null }`
- Response `201`: `QuotePendingEditResponse`

**`PATCH /api/v1/quotes/{id}/pending-edits/{edit_id}`**
- Auth: JWT required
- Permission: `quote.approve`
- Request body: `{ "edit_payload": JSONB|null, "annotation": TEXT|null }`
- Response `200`: Updated `QuotePendingEditResponse`

**`DELETE /api/v1/quotes/{id}/pending-edits/{edit_id}`**
- Auth: JWT required
- Permission: `quote.approve`
- Response `200`: `{ "deleted": true }`

**`DELETE /api/v1/quotes/{id}/pending-edits`**
- Auth: JWT required
- Permission: `quote.approve`
- Response `200`: `{ "deleted_count": INT }`

---

### A30 — Approval Comments

**`GET /api/v1/quotes/{id}/comments`**
- Auth: JWT required
- Permission: `quotes.view`
- Response: all `quote_approval_comment` rows for this quote, ordered `created_at DESC`

---

### A31 — Voice Intents (additions to voice route — no new HTTP paths)

Voice intents are added to `backend/services/voice_action_router.py` — they are invoked via the existing `POST /api/v1/voice/command` endpoint. Not new HTTP paths but new entries in `INTENT_HANDLERS`.

---

## D. PATTERN REUSE DECISIONS

### §1.5 Shared Module: No New Shared Modules Established in B1

B1 does not establish any of the §1.5 shared utilities (staleness check is established in B3/A19; three-tier resolver in B9/A53). B1 items use inline patterns per the "first use" rule — the shared utility pattern propagates from B3 onward.

**Exception**: B1/A2 does establish the canonical quote state machine transition logic. This should be extracted into `services/quote_service.py` as `transition_quote_status(quote_id, new_status, db, user, required_current_status)` so A29 (approve-with-edits) and A30 (kickback, reject) call a single authoritative transition function rather than each duplicating the status lookup + update.

---

### Pattern from `mvp-arch.md §16.3` — Confirm-as-Turn (A31)

**Applies to**: A31 `approve_quote`, `kickback_quote` voice handlers  
**Pattern**: Handler writes pending-confirmation state to `conversation_session.context_window_json.pending_confirmation` before executing. Next affirmative turn commits.

```python
# In voice_action_router.py — approve_quote handler
async def approve_quote_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    Handle: "Approve the Johnson panel quote"
    Entities: { "quote_identifier": "Johnson panel" }
    Pattern: §16.3 confirm-as-turn (arch doc) + §6.6 (methods doc)
    """
    # 1. Resolve quote from identifier
    # 2. Write pending_confirmation to context_window_json
    # 3. Return confirmation prompt — do NOT execute approval
    # Next turn: if affirmative → call _approve_quote_impl
```

**Section references**:
- `mvp-arch.md §16.3` — Confirm-as-Turn for Destructive Voice Actions
- `mvp-arch.md §6.6` — Confirm-as-Turn (Voice AI chapter)
- `pilot-python-engineer-methods.md §16.2 Step 4` — test coverage pattern

---

### Pattern from `mvp-arch.md §7.9` — Pre-Commit Staleness Check (A2, A29)

**Applies to**: `POST /api/v1/quotes/{id}/approve`, `POST /api/v1/quotes/{id}/approve-with-edits`, `POST /api/v1/quotes/{id}/reject`, `POST /api/v1/quotes/{id}/kickback`  
**Pattern**: All write endpoints in the approval flow accept `expected_quote_version_id`. If the live `quote_version.id` doesn't match, return 409 with refreshed state.

**Note**: The shared `utils/staleness_check.py` utility (established in B3/A19 per §1.5 table) does NOT yet exist. B1 implements this inline in `services/quote_service.py::assert_quote_version_not_stale()`. When B3 creates `utils/staleness_check.py`, B1's inline implementation should be refactored to call the utility — this is a soft refactor, not a blocking dependency.

**Inline implementation for B1**:
```python
# services/quote_service.py
def assert_quote_version_not_stale(
    expected_version_id: UUID | None,
    quote_id: UUID,
    db: Session,
    tenant_id: UUID,
) -> None:
    """
    Raise 409 if the client's expected_quote_version_id doesn't match
    the latest version on the live quote.

    B1 inline implementation. Refactor to call utils/staleness_check.py
    when B3 establishes that module.
    """
    if expected_version_id is None:
        return
    latest = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == quote_id)
        .where(QuoteVersion.tenant_id == tenant_id)
        .order_by(QuoteVersion.version_no.desc())
    ).first()
    if latest and latest.id != expected_version_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/stale-state",
                "title": "Quote Updated",
                "status": 409,
                "detail": "This quote was updated since you last viewed it.",
                "current_version_id": str(latest.id),
            },
        )
```

---

### Pattern from `mvp-arch.md §14.4` — Quote Version Immutability (A2, A3, A29)

**Applies to**: Every operation that modifies quote data  
**Pattern**: No mutation of existing `quote_line` or `quote` financial data. Every edit (apply-discount, approve-with-edits) creates a new `quote_version` snapshot before returning.

**Method `_create_quote_version_impl`** in `backend/api/routes/quotes.py` is already implemented and callable. A29's `approve-with-edits` endpoint calls this after applying pending edits.

---

### Pattern from `pilot-python-engineer-methods.md §17` — Celery Tasks (A3, A26)

**Applies to**:
- A3: `expire_quote_discounts` (Celery Beat task — daily) — transitions quotes with `discount_expires_at <= now()` to reset discount columns
- A26: `notify_system_template_updates` (Celery Beat task — daily at 6:00 AM per arch doc §3.2) — checks `forked_from_version < current_version` on system templates

Both use **§17.1 Periodic Poll Task pattern** (no bind, no retry):
```python
@celery_app.task(name="expire_quote_discounts")
def expire_quote_discounts() -> Dict[str, int]: ...

@celery_app.task(name="notify_system_template_updates")
def notify_system_template_updates() -> Dict[str, int]: ...
```

**Registration**: Both tasks require:
1. Module added to `imports` in `backend/core/celery_app.py`
2. Beat schedule entry added

---

### Pattern from `pilot-python-engineer-methods.md §16.2 Step 2` — 3-Part Migration (A24, A2, A3)

**Applies to**: A24 (`customer_visible`, `display_order`, `is_section_header`) and tenant_settings additions in A2 and A3 — all add NOT NULL columns to tables with existing rows.

**Template** (per §16.2 Step 2):
```python
def upgrade() -> None:
    # Part 1: Add nullable
    op.add_column('table', sa.Column('new_col', sa.Boolean(), nullable=True))
    # Part 2: Backfill existing rows
    op.execute("UPDATE table SET new_col = <default> WHERE new_col IS NULL")
    # Part 3: Lock NOT NULL
    op.alter_column('table', 'new_col', nullable=False)
```

---

### RBAC Permissions — B1 Items

All new permissions below are seeded in their respective migration `upgrade()` functions via `INSERT INTO platform_role` permission updates (NOT in the original role seed migration):

| Permission | Roles | Items Using |
|:---|:---|:---|
| `quote.submit_for_approval` | `technician` | A2 submit endpoint |
| `quote.approve` | `owner`, `accountant` | A2 approve/reject/kickback endpoints, A29 pending edits |
| `quote.apply_discount` | `owner`, `accountant` | A3 apply-discount endpoint |
| `quote_template.create` | `owner`, `accountant` | A25 create, A27 save-as-template |
| `quote_template.edit` | `owner`, `accountant` | A25 disable, A25 update |
| `quote_template.fork_system` | `owner`, `accountant` | A25 fork endpoint |

These permissions are defined in `backend/core/permissions.py` (method `has_permission` with wildcard support) and enforced via `require_permission()` dependency injection.

---

## E. SHARED MODULE INTERFACES

### `services/quote_service.py` (NEW in B1)

This module is established in B1 to consolidate quote state machine logic. Later batches (B4, B11) that interact with quote status should import from here.

```python
# backend/services/quote_service.py
"""
Quote domain business logic — state machine, version management,
approval workflow coordination.

Established: B1
Consumed by: B1 (A2, A29, A30, A31), future batches touching quote status
"""

import uuid
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from app.models.quoting import Quote, QuoteApprovalComment, QuotePendingEdit, QuoteStatus, QuoteVersion
from core.auth import AuthenticatedUser
from core.test_context import TestUserContext
from fastapi import HTTPException, status
from sqlmodel import Session, select


def transition_quote_status(
    quote: Quote,
    new_status_code: str,
    db: Session,
    tenant_id: UUID,
    actor_user_id: Optional[UUID] = None,
) -> Quote:
    """
    Transition a quote to a new status code. Validates the code exists for the tenant.

    Args:
        quote: The Quote ORM object to update (must be fetched and tenant-verified by caller)
        new_status_code: Target status code string (e.g., 'pending_approval', 'approved', 'draft')
        db: Database session
        tenant_id: Current tenant UUID for status lookup scoping
        actor_user_id: Optional UUID of the user performing the transition (for audit)

    Returns:
        Updated Quote with new status_id committed to DB

    Raises:
        HTTPException 500: If the target status code does not exist in quote_status table
    """
    ...


def assert_quote_version_not_stale(
    expected_version_id: Optional[UUID],
    quote_id: UUID,
    db: Session,
    tenant_id: UUID,
) -> None:
    """
    Raise HTTP 409 if client's expected_quote_version_id doesn't match live latest version.

    B1 inline implementation of the pre-commit staleness check pattern (arch §7.9, §16.4).
    Refactor callers to use utils/staleness_check.py when B3 establishes that module.

    Args:
        expected_version_id: UUID the client expects to be the latest. None = skip check.
        quote_id: UUID of the quote to check
        db: Database session
        tenant_id: Current tenant UUID for IDOR protection

    Raises:
        HTTPException 409: With current_version_id in detail payload
    """
    ...


def apply_pending_edits_to_quote(
    quote: Quote,
    editor_user_id: UUID,
    db: Session,
    tenant_id: UUID,
) -> tuple[Quote, int]:
    """
    Atomically apply all pending edits for editor_user_id on this quote.

    Business logic:
    1. Fetch all quote_pending_edit rows for (quote.id, quote.latest_version_id, editor_user_id)
    2. Apply each edit_payload to the current quote_line set (in DB)
    3. Create a new quote_version snapshot capturing the applied state
    4. Delete all consumed quote_pending_edit rows
    5. Return updated quote + count of applied edits

    Args:
        quote: Quote ORM object (must be in 'pending_approval' status)
        editor_user_id: UUID of the approving owner/accountant
        db: Database session
        tenant_id: Current tenant UUID

    Returns:
        Tuple of (updated Quote, applied_edit_count)

    Raises:
        HTTPException 422: No pending edits found for this user on this quote version
    """
    ...


def get_quote_pending_approval_summary(
    tenant_id: UUID,
    db: Session,
) -> list[dict]:
    """
    Read-only: return summary of all quotes in pending_approval status for a tenant.
    Used by A31 voice intent list_pending_quotes.

    Returns:
        List of dicts: [{ "quote_id": UUID, "customer_name": str, "total_cents": int,
                          "submitted_by": str, "submitted_at": datetime }]
    """
    ...
```

**File path**: `backend/services/quote_service.py`

---

### `tasks/quote_discount_expiry.py` (NEW in B1)

```python
# backend/tasks/quote_discount_expiry.py
"""
Celery task: expire time-limited quote discounts at their discount_expires_at timestamp.

Registered in: core/celery_app.py
Beat schedule: daily at 7:00 AM UTC (after nightly cleanup tasks)
Pattern: §17.1 Periodic Poll Task (no bind, no retry)
"""
from typing import Dict
from core.celery_app import celery_app


@celery_app.task(name="expire_quote_discounts")
def expire_quote_discounts() -> Dict[str, int]:
    """
    Find quotes with discount_expires_at <= now() and clear discount fields.
    Creates a new quote_version to preserve the discounted state in history.

    Returns:
        {"expired": int} — count of quotes whose discounts were expired
    """
    ...
```

**File path**: `backend/tasks/quote_discount_expiry.py`

---

### `tasks/system_template_notifier.py` (NEW in B1 — pre-registered in arch doc §3.2)

```python
# backend/tasks/system_template_notifier.py
"""
Celery task: notify tenants whose forked templates are behind the current system version.

Registered in: core/celery_app.py (task name 'notify_system_template_updates')
Beat schedule: daily at 6:00 AM UTC (per arch doc §3.2)
Pattern: §17.1 Periodic Poll Task (no bind, no retry)
"""
from typing import Dict
from core.celery_app import celery_app


@celery_app.task(name="notify_system_template_updates")
def notify_system_template_updates() -> Dict[str, int]:
    """
    For each tenant template with system_template_id set,
    compare forked_from_version to the system template's current_version.
    If behind: create notification_outbox entry. Dedup per (tenant_id, system_template_id, version).

    Returns:
        {"notified": int} — count of notification_outbox rows created
    """
    ...
```

**File path**: `backend/tasks/system_template_notifier.py`

---

### `tasks/quote_pending_edit_cleanup.py` (NEW in B1)

```python
# backend/tasks/quote_pending_edit_cleanup.py
"""
Celery task: expire quote_pending_edit rows older than 24 hours.

Beat schedule: daily at 3:00 AM UTC
Pattern: §17.1 Periodic Poll Task (no bind, no retry)
"""
from typing import Dict
from core.celery_app import celery_app


@celery_app.task(name="cleanup_expired_quote_pending_edits")
def cleanup_expired_quote_pending_edits() -> Dict[str, int]:
    """
    Delete quote_pending_edit rows where updated_at < now() - 24h
    and the parent quote is still in 'pending_approval' status
    (if the quote moved to 'approved' the edits were already deleted).

    Returns:
        {"deleted": int}
    """
    ...
```

**File path**: `backend/tasks/quote_pending_edit_cleanup.py`

---

## F. OPEN QUESTIONS RESOLVED

### Q1: Does `pending` in `quote_status` equal `pending_approval`?

**Observation**: Live DB has `code='pending'` (`name='Pending Review'`). The B1 state machine requires `pending_approval`.

**Resolution**: They are distinct. `pending` (existing) appears to be a legacy or generic state used by the current acceptance flow in `quotes.py` where `status_obj.code not in ["draft", "sent", "pending"]`. **Do not rename `pending`** — it may be in use. Add `pending_approval` as a new distinct status code via seed in Migration 3. The tech-submit flow uses `pending_approval`; the existing `pending` code should be audited for consumers and either deprecated or retained as-is.

**Decision**: Retain `pending` as-is. Add `pending_approval` and `approved` as new system status codes.

---

### Q2: Should A3 discount be a new `quote_line` type or columns on `quote`?

**Observation**: The ledger spec for A3 says "new quote line item type: `discount_line` (or extend existing line items with `is_discount` flag)."

**Resolution**: Columns on `quote` (not a new line type). Rationale: (1) discount is a quote-level concept applied by an owner, not a line-item cost; (2) quote version immutability means the discount is captured in the `quote_version.snapshot` JSON alongside all lines at the moment of snapshotting; (3) adding a `discount_line` row to `quote_line` would require special-case handling in all line-rendering, tax calculation, and profitability rollup code paths — column approach is simpler for MVP. The `discount_amount_cents` column on `quote` captures the computed discount; the `subtotal_cents` and `total_cents` are updated to reflect the discounted total.

---

### Q3: What variable namespace applies to `quote_template_line.description` placeholders?

**Observation**: A27 defines the template variable namespace but notes it must "match existing variable conventions used by communication templates (Pass 2 A4) where overlapping." A4 is implemented in B4, not B1.

**Resolution**: B1 adopts the following B1-scoped namespace for `quote_template_line` descriptions. B4 will extend/align `communication_template` to match the overlapping subset:

```
{customer_name}        — full customer name from customer.name
{customer_first_name}  — first token of customer name  
{site_address}         — site.address_line_1
{site_city_state_zip}  — site city + state + zip
{job_date}             — job.scheduled_start_at formatted as local date
{quote_date}           — quote.created_at formatted as local date
```

These six variables are the B1 template namespace. B4 (`communication_template`) uses a subset of these plus `{eta}`, `{minutes_late}`. No breaking conflict; both use `{customer_name}` identically. Cross-reference before B4 implementation to confirm alignment.

---

### Q4: Where does `require_approval_for_tech_quotes` live — `tenant_settings` or a new settings table?

**Observation**: The live `tenant_settings` table contains scalar operational settings. B9 introduces a full three-tier settings resolver. B1 predates B9.

**Resolution**: Add `require_approval_for_tech_quotes` as a column on the existing `tenant_settings` table (confirmed schema pattern). The B9 settings resolver will later wrap all `tenant_settings` columns via the catalog. This is the established pattern for pre-B9 settings. The column defaults to `TRUE` (approval required) which is the safe default for multi-user tenants.

---

### Q5: Should `QuoteLine` description be migrated from `character varying` to `TEXT`?

**MCP Result**: `description` on `quote_line` is `character varying` with `character_maximum_length = NULL`. In PostgreSQL, `VARCHAR` with no length limit is stored identically to `TEXT`. The ORM model (`str = Field(nullable=False)`) without `sa_column=Column(Text())` will default to `VARCHAR` without a cap via SQLModel inference.

**Resolution**: **No migration needed.** The field already has no length constraint. The A28 verification is complete: `quote_line.description` accepts multi-line text of any length. Document this in the schema blueprint JSON update. Optionally change the ORM field to use `sa_column=Column(Text())` for semantic clarity — this is a code-only change with zero DDL impact (same storage in PostgreSQL).

---

### Q6: Confirm `quote_version` snapshot includes new A24 fields

**Resolution**: The snapshot is built in `_create_quote_version_impl` at `backend/api/routes/quotes.py` using `line.model_dump(mode="json")`. Once A24 columns are added to the `QuoteLine` ORM model, `model_dump()` automatically includes them in the snapshot. **No special handling needed** — the snapshot is a live model dump. The A24 migration (Migration 1) + ORM model update is sufficient.

---

### Q7: How does A31 voice handle `approve_quote` when `require_approval_for_tech_quotes = OFF`?

**Resolution**: When `require_approval_for_tech_quotes = OFF`, tech quotes go directly from `draft → sent` without `pending_approval`. In this case, the `list_pending_quotes` voice handler returns "No quotes are pending your approval." The `approve_quote` handler resolves the quote, checks status, and if the quote is already `sent` or `approved`, returns "That quote doesn't need your approval" as a disambiguation response. No error. This handles the toggle correctly without special-casing the voice layer.

---

### Q8: Does the A27 save-as-template endpoint need to handle `quote_version_id` or the latest live lines?

**Resolution**: Save-as-template operates on the **live `quote_line` rows** (not a frozen snapshot), because the owner is saving the current editable state as a template, not a historical version. This means the endpoint queries `quote_line` directly filtered by `quote_id` and `is_active = TRUE`. The generated template lines reflect the quote's current state at save time.

---

## G. EXTERNAL DEPENDENCY STATUS

### B1 has no external dependency blockers.

All B1 items (A24, A28, A2, A25, A26, A27, A3, A29, A30, A31) are implemented entirely within the Pilot backend:
- No Stripe integration required
- No Telnyx/SMS required
- No SendGrid required
- No OpenAI/embedding required
- No 10DLC registration required
- Ollama (local GPU) is used by A31 voice handler but is already operational per existing infrastructure

### Mock Strategy for A26 Notification Dispatch

A26's `notify_system_template_updates` task creates `notification_outbox` entries. In development/testing, the `notification_outbox` rows are created but the `poll_pending_notifications` task (which dispatches emails/push) is not required to be running for the task test to pass. Tests assert row creation in `notification_outbox`, not actual email delivery.

### Pre-Batch Action Items for Tom

None required before B1 implementation begins. B1 is a pure backend batch with zero external dependencies.

### Future External Dependency Awareness

The template variable `{customer_name}` in A27 quote templates will eventually be used in PDF rendering for customer-facing output. If PDF generation uses a third-party service (not in scope for B1), that integration comes later. B1 only defines the template storage schema and the substitution variable namespace — it does not implement PDF rendering.

---

## Appendix: State Machine Diagram

```
[draft]
   │
   ├── (tech submits) → require_approval=ON  ──→ [pending_approval]
   │                                                     │
   │                                                     ├── (owner approves) ──→ [approved] ──→ [sent] ──→ [accepted] ──→ [converted]
   │                                                     │                                                    │
   │                                                     │                                                 [declined]
   │                                                     │                                                 [expired]
   │                                                     ├── (owner approves-with-edits) ──→ [approved] ──→ (same as above)
   │                                                     │
   │                                                     ├── (owner kickbacks) ──→ [draft]
   │                                                     │
   │                                                     └── (owner rejects) ──→ [rejected] (terminal)
   │
   └── (owner submits OR require_approval=OFF) ──→ [sent] ──→ [accepted] ──→ [converted]
                                                              │
                                                           [declined]
                                                           [expired]
```

**Terminal states**: `rejected`, `accepted`, `expired`, `converted`, `declined`  
**Discount-applied states**: Discount can be applied in `draft`, `pending_approval`, `approved`, or `sent` — creates a new version in all cases.

---

*Design document complete. All six reads performed. All seven sections populated. No open questions left unresolved.*
