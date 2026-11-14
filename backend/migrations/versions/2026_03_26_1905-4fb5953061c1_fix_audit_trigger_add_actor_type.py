"""fix_audit_trigger_add_actor_type

Revision ID: 4fb5953061c1
Revises: 82440f318c2c
Create Date: 2026-03-26 19:05:27.123456+00:00

CRITICAL FIX: Add missing actor_type field to audit.log_changes() trigger function.

Root Cause:
- AuditEvent model has NOT NULL constraint on actor_type field (line 228 in models/system.py)
- Original trigger function (82440f318c2c) did not include actor_type in INSERT statement
- This caused all existing tests to fail with: "null value in column 'actor_type' violates not-null constraint"

Impact:
- 119 existing tests failing (baseline was 339 passing)
- All data mutations were blocked by the trigger error

Fix:
- Drop and recreate audit.log_changes() function with actor_type field
- Set actor_type = 'user' for authenticated users
- Set actor_type = 'system' for background jobs (when user_id is system UUID)

Testing:
- Run full test suite to verify 339+ tests pass again
- Task 20 tests should pass with this fix

Reference: dev-docs/testing-support/task-20-test-audit-logging-fixes.md
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4fb5953061c1"
down_revision: str | None = "82440f318c2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Fix the audit.log_changes() trigger function to include actor_type field.

    This is a critical fix that resolves the NOT NULL constraint violation
    that was breaking all existing tests.
    """

    # Drop and recreate the function with actor_type field
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_changes()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id uuid;
            v_actor_type text;
        BEGIN
            -- Read user_id from session variable (set by application)
            -- Falls back to system UUID if not set (background jobs, migrations)
            v_user_id := COALESCE(
                NULLIF(current_setting('app.user_id', true), '')::uuid,
                '00000000-0000-0000-0000-000000000000'::uuid
            );
            
            -- Determine actor_type based on user_id
            -- If system UUID, then it's a system action
            -- Otherwise, it's a user action
            IF v_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
                v_actor_type := 'system';
            ELSE
                v_actor_type := 'user';
            END IF;
            
            -- Insert audit event record capturing the change
            INSERT INTO audit.event (
                tenant_id,
                user_id,
                actor_type,     -- *** CRITICAL FIX: Added this field ***
                entity_name,
                entity_id,
                action,
                old_values,
                new_values,
                occurred_at
            ) VALUES (
                -- Extract tenant_id from the row (NEW for INSERT/UPDATE, OLD for DELETE)
                COALESCE(NEW.tenant_id, OLD.tenant_id),
                
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
            -- DELETE operations need OLD, INSERT/UPDATE need NEW
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """
    Revert to the original broken version (for rollback purposes).

    Note: This downgrade recreates the broken version without actor_type,
    so it will cause the same test failures if rolled back.
    """

    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Insert audit event record capturing the change
            INSERT INTO audit.event (
                tenant_id,
                user_id,
                entity_name,
                entity_id,
                action,
                old_values,
                new_values,
                occurred_at
            ) VALUES (
                -- Extract tenant_id from the row (NEW for INSERT/UPDATE, OLD for DELETE)
                COALESCE(NEW.tenant_id, OLD.tenant_id),
                
                -- Read user_id from session variable (set by application)
                -- Falls back to system UUID (00000000-0000-0000-0000-000000000000) if not set
                -- This handles background jobs and migrations that don't have a user context
                COALESCE(
                    NULLIF(current_setting('app.user_id', true), '')::uuid,
                    '00000000-0000-0000-0000-000000000000'::uuid
                ),
                
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
            -- DELETE operations need OLD, INSERT/UPDATE need NEW
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)
