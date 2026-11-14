"""phase_4_7_enhance_guard_platform_isolation_task8

Revision ID: be00bcc02754
Revises: e774cd9ebf0e
Create Date: 2026-04-08 10:02:28.145885+00:00

Phase 4.7 - Task 8: Enhance guard_tenant_user_platform_isolation() function
- Upgrade: Use explicit is_platform_user boolean check with enhanced error messages
- Downgrade: Revert to platform_role_code IS NOT NULL check
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "be00bcc02754"
down_revision: str | None = "e774cd9ebf0e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Enhance guard_tenant_user_platform_isolation() function to:
    1. Use explicit is_platform_user boolean (GENERATED column)
    2. Include user_id in error message
    3. Add ERRCODE and helpful HINT

    Security logic UNCHANGED - still prevents platform users from being tenant users.
    Only enhances error messages for better debugging.
    """
    op.execute(
        text("""
        CREATE OR REPLACE FUNCTION guard_tenant_user_platform_isolation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            is_platform bool;
        BEGIN
            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                -- Use explicit is_platform_user boolean (GENERATED column)
                SELECT is_platform_user INTO is_platform
                FROM "user"
                WHERE id = NEW.user_id;
                
                IF is_platform THEN
                    RAISE EXCEPTION 'User % is a platform user and cannot be assigned to a tenant',
                        NEW.user_id
                        USING ERRCODE = '23514',
                              HINT = 'Platform users (staff, superadmin) cannot be tenant users';
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$;
    """)
    )


def downgrade() -> None:
    """
    Revert to platform_role_code IS NOT NULL check (previous implementation).
    """
    op.execute(
        text("""
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
    )
