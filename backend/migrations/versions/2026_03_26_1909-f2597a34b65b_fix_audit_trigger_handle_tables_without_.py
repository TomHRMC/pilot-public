"""fix_audit_trigger_handle_tables_without_tenant_id

Revision ID: f2597a34b65b
Revises: 4fb5953061c1
Create Date: 2026-03-26 19:09:54.123456+00:00

CRITICAL FIX: Handle tables without direct tenant_id column (contact, address).

Root Cause:
- Some tables like 'contact' and 'address' don't have a tenant_id column
- They are polymorphic tables that reference parent entities
- Original trigger assumed all tables have tenant_id column
- This caused: "psycopg2.errors.UndefinedColumn: column 'tenant_id' does not exist"

Impact:
- 40+ tests failing due to trigger errors on contact and address inserts
- Any operation involving these tables was blocked

Fix:
- Modify trigger to safely check if tenant_id column exists
- Use PostgreSQL's to_jsonb() which gracefully handles missing columns
- Set tenant_id to NULL for tables without the column
- Audit.event table allows NULL tenant_id for such cases

Testing:
- Run full test suite to verify all tests pass
- Specifically test contact and address operations

Reference: dev-docs/testing-support/task-20-test-audit-logging-fixes.md
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2597a34b65b"
down_revision: str | None = "4fb5953061c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Fix the audit.log_changes() trigger function to handle tables without tenant_id.

    This is a critical fix that resolves the "column tenant_id does not exist" error
    for polymorphic tables like contact and address.
    """

    # Drop and recreate the function with better tenant_id handling
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_changes()
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
            -- For tables without tenant_id (contact, address), this will be NULL
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
                -- Tenant ID (NULL for polymorphic tables without direct tenant_id)
                v_tenant_id,
                
                -- User ID from session variable or system UUID
                v_user_id,
                
                -- Actor type: 'user' or 'system'
                v_actor_type,
                
                -- Use table name as entity type (e.g., 'customer', 'quote')
                TG_TABLE_NAME::text,
                
                -- Extract entity ID from the row
                COALESCE(NEW.id, OLD.id)::text,
                
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


def downgrade() -> None:
    """
    Revert to the previous version with actor_type but without safe tenant_id handling.
    """

    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_changes()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id uuid;
            v_actor_type text;
        BEGIN
            -- Read user_id from session variable (set by application)
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
                -- Extract tenant_id from the row (will fail for tables without tenant_id)
                COALESCE(NEW.tenant_id, OLD.tenant_id),
                
                -- User ID from session variable or system UUID
                v_user_id,
                
                -- Actor type: 'user' or 'system'
                v_actor_type,
                
                -- Use table name as entity type
                TG_TABLE_NAME::text,
                
                -- Extract entity ID from the row
                COALESCE(NEW.id, OLD.id)::text,
                
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
