"""add_missing_plpgsql_functions

Revision ID: 6b525454c89c
Revises: 1be24f24dd6b
Create Date: 2026-03-31 18:50:44.200392+00:00

Implements 3 missing PL/pgSQL functions from Golden Master schema v2.6h:
1. set_updated_at() - Auto-bump updated_at on UPDATE
2. guard_created_fields_immutable() - Prevent modification of created_at/created_by
3. guard_tenant_user_platform_isolation() - Prevent platform users from being tenant users

Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Phase 2, Task 4
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "6b525454c89c"
down_revision: str | None = "1be24f24dd6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create 3 missing PL/pgSQL functions and apply triggers to all relevant tables."""

    # =========================================================================
    # FUNCTION 1: set_updated_at()
    # Purpose: Automatically bump updated_at timestamp on any UPDATE operation
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          -- Use clock_timestamp() instead of NOW() to get actual current time
          -- NOW() returns transaction start time, which can cause updated_at to go backwards
          NEW.updated_at := clock_timestamp();
          RETURN NEW;
        END;
        $$;
    """)

    # Get all tables with updated_at column and create triggers
    conn = op.get_bind()
    result = conn.execute(
        text("""
        SELECT table_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND column_name = 'updated_at'
        ORDER BY table_name
    """)
    )

    updated_at_tables = [row[0] for row in result]

    # Create triggers for all tables with updated_at
    for table_name in updated_at_tables:
        trigger_name = f"trg_{table_name}_set_updated_at"
        # Quote table name to handle reserved keywords like "user"
        quoted_table = f'"{table_name}"'
        op.execute(f"""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON {quoted_table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """)

    # =========================================================================
    # FUNCTION 2: guard_created_fields_immutable()
    # Purpose: Prevent modification of created_at and created_by after insert
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION guard_created_fields_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          has_created_by boolean;
        BEGIN
          IF TG_OP = 'UPDATE' THEN
            -- Reject attempts to change created_at
            IF NEW.created_at IS DISTINCT FROM OLD.created_at THEN
              RAISE EXCEPTION 'created_at is immutable (cannot be changed after insert)'
                USING ERRCODE = '23514',
                      HINT = 'Remove created_at from UPDATE statement';
            END IF;
            
            -- Check if table has created_by column
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns 
              WHERE table_schema = TG_TABLE_SCHEMA 
                AND table_name = TG_TABLE_NAME 
                AND column_name = 'created_by'
            ) INTO has_created_by;
            
            -- Reject attempts to change created_by (if column exists)
            IF has_created_by THEN
              -- Use dynamic SQL to check created_by value
              EXECUTE format(
                'SELECT ($1).created_by IS DISTINCT FROM ($2).created_by'
              ) USING NEW, OLD INTO has_created_by;
              
              IF has_created_by THEN
                RAISE EXCEPTION 'created_by is immutable (cannot be changed after insert)'
                  USING ERRCODE = '23514',
                        HINT = 'Remove created_by from UPDATE statement';
              END IF;
            END IF;
          END IF;
          
          RETURN NEW;
        END;
        $$;
    """)

    # Get all tables with created_at column and create triggers
    result = conn.execute(
        text("""
        SELECT table_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND column_name = 'created_at'
        ORDER BY table_name
    """)
    )

    created_at_tables = [row[0] for row in result]

    # Create triggers for all tables with created_at
    for table_name in created_at_tables:
        trigger_name = f"trg_{table_name}_guard_created_immutable"
        # Quote table name to handle reserved keywords like "user"
        quoted_table = f'"{table_name}"'
        op.execute(f"""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON {quoted_table}
            FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable()
        """)

    # =========================================================================
    # FUNCTION 3: guard_tenant_user_platform_isolation()
    # Purpose: Prevent platform users from being assigned as tenant users
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION guard_tenant_user_platform_isolation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          platform_role_code text;
        BEGIN
          IF TG_OP IN ('INSERT', 'UPDATE') THEN
            -- Check if user has platform role assigned
            SELECT u.platform_role_code INTO platform_role_code
            FROM "user" u
            WHERE u.id = NEW.user_id;
            
            IF platform_role_code IS NOT NULL THEN
              RAISE EXCEPTION 'User % has platform role % and cannot be assigned to a tenant',
                NEW.user_id, platform_role_code
                USING ERRCODE = '23514',
                      HINT = 'Platform users (staff, superadmin) cannot be tenant users';
            END IF;
          END IF;
          
          RETURN NEW;
        END;
        $$;
    """)

    # Create trigger on tenant_user table
    op.execute("""
        CREATE TRIGGER trg_tenant_user_guard_platform_biu
        BEFORE INSERT OR UPDATE ON tenant_user
        FOR EACH ROW EXECUTE FUNCTION guard_tenant_user_platform_isolation()
    """)


def downgrade() -> None:
    """Drop all triggers and functions created in upgrade."""

    # Get connection for dynamic queries
    conn = op.get_bind()

    # =========================================================================
    # Drop all set_updated_at triggers
    # =========================================================================
    result = conn.execute(
        text("""
        SELECT table_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND column_name = 'updated_at'
        ORDER BY table_name
    """)
    )

    updated_at_tables = [row[0] for row in result]

    for table_name in updated_at_tables:
        trigger_name = f"trg_{table_name}_set_updated_at"
        # Quote table name to handle reserved keywords like "user"
        quoted_table = f'"{table_name}"'
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {quoted_table}")

    # Drop set_updated_at function
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    # =========================================================================
    # Drop all guard_created_fields_immutable triggers
    # =========================================================================
    result = conn.execute(
        text("""
        SELECT table_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND column_name = 'created_at'
        ORDER BY table_name
    """)
    )

    created_at_tables = [row[0] for row in result]

    for table_name in created_at_tables:
        trigger_name = f"trg_{table_name}_guard_created_immutable"
        # Quote table name to handle reserved keywords like "user"
        quoted_table = f'"{table_name}"'
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {quoted_table}")

    # Drop guard_created_fields_immutable function
    op.execute("DROP FUNCTION IF EXISTS guard_created_fields_immutable()")

    # =========================================================================
    # Drop guard_tenant_user_platform_isolation trigger and function
    # =========================================================================
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_user_guard_platform_biu ON tenant_user"
    )
    op.execute("DROP FUNCTION IF EXISTS guard_tenant_user_platform_isolation()")
