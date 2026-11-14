# Batch B1–B12 Mixin Audit Report

**Date**: 2026-05-03  
**Trigger**: Post-B13 discovery that the architect design prompt omitted mixin assignment requirements.  
**Scope**: All tables added in batches B1–B12. Pre-existing tables (pre-B1 baseline) are out of scope.  
**Method**: Live DB column query via postgres-local MCP (all tables, all four mixin columns) cross-referenced against each batch's new table list and design doc.

---

## Summary

| Finding | Count |
|:---|:---:|
| ✅ Correct — full `StandardAuditMixin` | 22 |
| ✅ Correct — `AppendOnlyMixin` (intentional append-only) | 5 |
| ✅ Correct — `MachineLogMixin` or machine-log style (intentional) | 2 |
| ⚠️ Gap — missing `created_by`/`updated_by` on mutable table | 3 |
| 🔴 Gap — missing ALL audit columns | 2 |

**All B13 tables are confirmed CORRECT** in the live DB (remediation migrations were applied — §H of `batch-b13-design.md` documents what was fixed).

---

## ✅ Correct Tables (no action needed)

### StandardAuditMixin — full `created_at`, `updated_at`, `created_by`, `updated_by`

| Table | Batch |
|:---|:---|
| `quote_template` | B1 |
| `quote_template_line` | B1 |
| `quote_pending_edit` | B1 |
| `user_dashboard_widget` | B5 |
| `mobile_sync_owner_escalation` | B7b |
| `sync_conflict_classification_matrix` | B7b |
| `mobile_device_push_token` | B8 |
| `user_setting_override` | B9 |
| `notification_category` | B10 |
| `notification_category_sub_trigger` | B10 |
| `notification_default_policy` | B10 |
| `notification_preference` | B10 |
| `tenant_notification_default` | B10 |
| `tenant_user_notification_pref` | B10 |
| `customer_communication_thread` | B11 |
| `tenant_phone_number` | B11 |
| `user_mfa_method` | B13 |
| `mfa_grace_period_tracking` | B13 |
| `user_session_history` | B13 |
| `user_session_metadata` | B13 |
| `data_export_request` | B13 |

### AppendOnlyMixin — `created_at` + `created_by` only (intentional; records are never updated)

| Table | Batch | Rationale |
|:---|:---|:---|
| `quote_approval_comment` | B1 | Comments are immutable once created |
| `voice_feedback` | B2 | Feedback is submitted once; never edited |
| `mobile_sync_event` | B7a | Sync events are an append-only log |
| `in_app_notification` | B10 | Notifications are created once and only `read_at` changes (domain column) |
| `user_mfa_recovery_code` | B13 | Recovery codes are generated once; `used_at` is a domain column |

### MachineLogMixin — `created_at` only (intentional; pure system events)

| Table | Batch | Rationale |
|:---|:---|:---|
| `mobile_sync_session` | B8 | System-generated session record; no human actor. Only `created_at` defined in B8 design. |

---

## ⚠️ Gaps Requiring Remediation

### Gap Type 1 — Has `created_at` + `updated_at` but missing `created_by` + `updated_by`

These tables are mutable and have time-tracking columns but are missing the actor columns. For machine-managed tables the columns will always be `NULL` at runtime, but project convention is to include them for schema consistency and audit completeness.

| Table | Batch | Assessment | Action |
|:---|:---|:---|:---|
| `customer_communication_message` | B11 | **High priority.** Outbound messages ARE user-authored — `created_by` should be populated with the sending user. This is a functional gap, not just a convention gap. | Add `created_by UUID NULL`, `updated_by UUID NULL` |
| `customer_communication_unrouted` | B11 | Medium. System-created on inbound receipt — `created_by` will always be NULL. But schema convention requires the column. | Add `created_by UUID NULL`, `updated_by UUID NULL` |
| `sms_quota_period` | B11 | Low. Machine-managed quota periods created by Celery task. `created_by` will always be NULL. | Add `created_by UUID NULL`, `updated_by UUID NULL` |
| `mobile_push_rate_limit` | B8 | Low. Machine-managed rate limit record. `created_by` will always be NULL. | Add `created_by UUID NULL`, `updated_by UUID NULL` |

### Gap Type 2 — Missing ALL audit columns

| Table | Batch | Assessment | Action |
|:---|:---|:---|:---|
| `customer_communication_message_read_state` | B11 | **High priority.** This is a join table `(message_id, user_id, read_at)` with NO audit columns. The B11 design explicitly omitted them. However, `AppendOnlyMixin` is the minimum standard — `created_at` and `created_by` should be present. `read_at` serves the same semantic purpose as `created_at` but is named differently. | Add `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by UUID NULL`. `read_at` can remain as a domain alias or be removed in favor of `created_at`. |
| `mobile_sync_event_audit` | B8 | **Medium.** The B8 design explicitly called this "append-only" and defined `resolved_at TIMESTAMPTZ NOT NULL DEFAULT now()` as the creation timestamp. But it's named `resolved_at`, not `created_at`. The AppendOnlyMixin requires `created_at`. `resolved_at` effectively IS `created_at` but naming breaks convention and would confuse the `guard_created_fields_immutable` trigger. | Add `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by UUID NULL` (backfill from `resolved_at`). Keep `resolved_at` as domain column. |

---

## Remediation Migration Plan

Six remediation migrations — all additive, no data risk, all columns nullable or with `DEFAULT now()`.

### Migration naming convention

```
phase_fe_1_batch_b{N}_fix_{table}_audit_mixin
```

### Migrations in recommended order

| # | Migration Name | Table | Columns to Add |
|:---|:---|:---|:---|
| 1 | `phase_fe_1_batch_b11_fix_customer_communication_message_audit_mixin` | `customer_communication_message` | `created_by UUID NULL`, `updated_by UUID NULL` |
| 2 | `phase_fe_1_batch_b11_fix_customer_communication_unrouted_audit_mixin` | `customer_communication_unrouted` | `created_by UUID NULL`, `updated_by UUID NULL` |
| 3 | `phase_fe_1_batch_b11_fix_sms_quota_period_audit_mixin` | `sms_quota_period` | `created_by UUID NULL`, `updated_by UUID NULL` |
| 4 | `phase_fe_1_batch_b11_fix_customer_communication_message_read_state_audit_mixin` | `customer_communication_message_read_state` | `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by UUID NULL` |
| 5 | `phase_fe_1_batch_b8_fix_mobile_push_rate_limit_audit_mixin` | `mobile_push_rate_limit` | `created_by UUID NULL`, `updated_by UUID NULL` |
| 6 | `phase_fe_1_batch_b8_fix_mobile_sync_event_audit_audit_mixin` | `mobile_sync_event_audit` | `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by UUID NULL` (backfill `created_at` from `resolved_at`) |

### Migration pattern for Gap Type 1 (add `created_by` + `updated_by` only)

```python
def upgrade() -> None:
    op.add_column('{table}', sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('{table}', sa.Column('updated_by', sa.UUID(), nullable=True))
    # No FK constraint on created_by/updated_by (matches rest of codebase)
    # No triggers to add — existing updated_at trigger already installed

def downgrade() -> None:
    op.drop_column('{table}', 'updated_by')
    op.drop_column('{table}', 'created_by')
```

### Migration pattern for Gap Type 2 (add `created_at` + `created_by`)

```python
def upgrade() -> None:
    # 1. Add nullable
    op.add_column('{table}', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('{table}', sa.Column('created_by', sa.UUID(), nullable=True))

    # 2. Backfill (use domain timestamp if available, else now())
    op.execute("UPDATE {table} SET created_at = resolved_at")  # mobile_sync_event_audit
    # OR: op.execute("UPDATE {table} SET created_at = now()")  # customer_communication_message_read_state

    # 3. Lock NOT NULL
    op.alter_column('{table}', 'created_at', nullable=False)

    # 4. Install AppendOnly triggers
    op.execute("""
        CREATE TRIGGER audit_{table}_changes
        AFTER INSERT OR UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_{table}_guard_created_immutable
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_{table}_guard_created_immutable ON {table};")
    op.execute("DROP TRIGGER IF EXISTS audit_{table}_changes ON {table};")
    op.drop_column('{table}', 'created_by')
    op.drop_column('{table}', 'created_at')
```

---

## Out-of-Scope (Pre-B1 Baseline Tables)

The following tables have partial mixin columns (e.g., AppendOnly or MachineLog pattern) and were present before B1 started. They are **not** B1–B12 additions and are excluded from this audit's remediation scope:

`auth_api_token`, `auth_email_verification`, `auth_jwk`, `auth_mfa_otp`, `auth_password_history`, `auth_password_reset`, `auth_refresh_token`, `calendar_sync_log`, `change_order_line_tax_component`, `connector_run_log`, `contact_portal_invite`, `conversation_message`, `discount_version`, `idempotency_key`, `integration_sync_log`, `invoice_line`, `invoice_line_tax_component`, `jwk_status`, `labor_rate_version`, `notification_delivery_attempt`, `notification_event`, `pricebook_item_version`, `pricing_cache`, `product_plan_product_feature_version`, `product_plan_version`, `psp_transaction_log`, `quote_acceptance`, `quote_line_tax_component`, `quote_public_link_contact_action`, `quote_version`, `supplier_item_price`, `tax_rate_version`, `tenant_markup_version`, `usage_ledger`, `voice_command_log`, `voice_feedback` (pre-B2 pattern), `webhook_delivery_attempt`, `webhook_endpoint`, `webhook_event`, `webhook_event_type`.

These tables may benefit from a separate baseline audit in a future cleanup batch, but that is a distinct scope from the B1–B12 additions review.
