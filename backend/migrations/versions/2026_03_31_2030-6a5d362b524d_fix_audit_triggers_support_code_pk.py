"""fix_audit_triggers_support_code_pk

Revision ID: 6a5d362b524d
Revises: e3783b6d2b8d
Create Date: 2026-03-31 20:30:17.123456+00:00

Fix audit triggers for tables using 'code' as primary key instead of 'id'.

Context:
- The original audit.log_changes() function assumes all tables have 'id' as PK
- 16 tables use 'code' as primary key, causing trigger errors
- This migration creates audit.log_changes_code_pk() for code-based PKs
- Removes audit triggers from all 16 code-PK tables
- Re-adds triggers only to 5 important tables using the new function

Tables with code as PK (16 total):
- platform_role, tenant_user_role (IMPORTANT - role configuration)
- product_plan, product_feature (IMPORTANT - billing/features)
- sso_provider (IMPORTANT - auth configuration)
- app_service_category, app_service_provider (reference data)
- entity_type, contact_type, address_type (reference data)
- taxability_code, job_expense_category (reference data)
- currency (reference data)
- notification_channel, notification_type (reference data)
- webhook_event_type (reference data)

Strategy:
- Remove triggers from all 16 tables
- Create new audit.log_changes_code_pk() function
- Add triggers back to 5 important tables only

Reference: Phase 4.5, Task 6 - Audit Trigger Coverage
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a5d362b524d"
down_revision: str | None = "e3783b6d2b8d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Fix audit triggers for tables with code-based primary keys.

    Steps:
    1. Remove audit triggers from all 16 code-PK tables
    2. Create new audit.log_changes_code_pk() function
    3. Add triggers back to 5 important tables using new function
    """

    # ========================================================================
    # STEP 1: Remove existing (broken) audit triggers from code-PK tables
    # ========================================================================

    # Remove from 3 tables that already have (broken) triggers from first migration
    op.execute("DROP TRIGGER IF EXISTS audit_product_plan_changes ON product_plan;")
    op.execute("DROP TRIGGER IF EXISTS audit_sso_provider_changes ON sso_provider;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_user_role_changes ON tenant_user_role;"
    )

    # Note: platform_role and product_feature don't have triggers yet (will be added)

    # Remove from 11 reference/lookup tables (will NOT be re-added)
    op.execute(
        "DROP TRIGGER IF EXISTS audit_app_service_category_changes ON app_service_category;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_app_service_provider_changes ON app_service_provider;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_entity_type_changes ON entity_type;")
    op.execute("DROP TRIGGER IF EXISTS audit_contact_type_changes ON contact_type;")
    op.execute("DROP TRIGGER IF EXISTS audit_address_type_changes ON address_type;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_taxability_code_changes ON taxability_code;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_job_expense_category_changes ON job_expense_category;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_currency_changes ON currency;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_channel_changes ON notification_channel;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_type_changes ON notification_type;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_webhook_event_type_changes ON webhook_event_type;"
    )

    # ========================================================================
    # STEP 2: Create new audit function for code-based primary keys
    # ========================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_changes_code_pk()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id uuid;
            v_actor_type text;
            v_tenant_id uuid;
        BEGIN
            -- Read user_id from session variable (set by application)
            -- Falls back to system UUID if not set (background jobs, migrations)
            v_user_id := COALESCE(
                NULLIF(current_setting('app.user_id', true), '')::uuid,
                '00000000-0000-0000-0000-000000000000'::uuid
            );
            
            -- Determine actor_type based on user_id
            IF v_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
                v_actor_type := 'system';
            ELSE
                v_actor_type := 'user';
            END IF;
            
            -- Safely extract tenant_id (handles tables without tenant_id column)
            BEGIN
                v_tenant_id := COALESCE(NEW.tenant_id, OLD.tenant_id);
            EXCEPTION
                WHEN undefined_column THEN
                    v_tenant_id := NULL;
            END;
            
            -- Insert audit event record capturing the change
            INSERT INTO audit.event (
                tenant_id,
                user_id,
                actor_type,
                entity_name,
                entity_id,
                action,
                old_values,
                new_values,
                occurred_at
            ) VALUES (
                -- Tenant ID (NULL for platform-level tables)
                v_tenant_id,
                
                -- User ID from session variable or system UUID
                v_user_id,
                
                -- Actor type: 'user' or 'system'
                v_actor_type,
                
                -- Use table name as entity type
                TG_TABLE_NAME::text,
                
                -- Extract entity ID from 'code' column (primary key for these tables)
                COALESCE(NEW.code, OLD.code)::text,
                
                -- Operation type: INSERT, UPDATE, DELETE
                TG_OP,
                
                -- Old values (for UPDATE and DELETE operations)
                CASE
                    WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb
                    ELSE NULL
                END,
                
                -- New values (for INSERT and UPDATE operations)
                CASE
                    WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb
                    ELSE NULL
                END,
                
                -- Timestamp of the change
                NOW()
            );
            
            -- Return the appropriate record to allow the operation to complete
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ========================================================================
    # STEP 3: Add audit triggers to 5 important code-PK tables only
    # ========================================================================

    # IMPORTANT: Role configuration tables
    op.execute("""
        CREATE TRIGGER audit_platform_role_changes
        AFTER INSERT OR UPDATE OR DELETE ON platform_role
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_user_role_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_user_role
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();
    """)

    # IMPORTANT: Billing/subscription tables
    op.execute("""
        CREATE TRIGGER audit_product_plan_changes
        AFTER INSERT OR UPDATE OR DELETE ON product_plan
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();
    """)

    op.execute("""
        CREATE TRIGGER audit_product_feature_changes
        AFTER INSERT OR UPDATE OR DELETE ON product_feature
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();
    """)

    # IMPORTANT: Auth configuration
    op.execute("""
        CREATE TRIGGER audit_sso_provider_changes
        AFTER INSERT OR UPDATE OR DELETE ON sso_provider
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();
    """)


def downgrade() -> None:
    """
    Revert to original state (broken triggers removed, new function removed).
    """

    # Remove the 5 new triggers
    op.execute("DROP TRIGGER IF EXISTS audit_platform_role_changes ON platform_role;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_user_role_changes ON tenant_user_role;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_product_plan_changes ON product_plan;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_product_feature_changes ON product_feature;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_sso_provider_changes ON sso_provider;")

    # Remove the new function
    op.execute("DROP FUNCTION IF EXISTS audit.log_changes_code_pk();")

    # Re-add the original broken triggers (for tables that had them)
    op.execute("""
        CREATE TRIGGER audit_product_plan_changes
        AFTER INSERT OR UPDATE OR DELETE ON product_plan
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_sso_provider_changes
        AFTER INSERT OR UPDATE OR DELETE ON sso_provider
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
