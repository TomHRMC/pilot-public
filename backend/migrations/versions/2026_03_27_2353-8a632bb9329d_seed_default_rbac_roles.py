"""seed_default_rbac_roles

Revision ID: 8a632bb9329d
Revises: f2597a34b65b
Create Date: 2026-03-27 23:53:25.714203+00:00

RBAC Permission System - Default Roles Seeding

Purpose:
- Seed 4 default roles into tenant_user_role table
- Assign "owner" role to all existing users (backward compatibility)
- Enable permission-based access control for MVP

Roles Created:
1. Owner: Full access (*) - Primary user for solo contractors
2. Technician: Field operations (jobs, time, expenses, voice AI)
3. Office Staff: Administrative tasks (customers, quotes, sites)
4. Accountant: Read-only financial access (*.view, audit.view)

Impact:
- All existing users will be assigned "owner" role automatically
- get_current_user() now requires valid role (security enforcement)
- Routes can now use @require_permission() decorator

Security:
- Fail-safe: Users without valid role will be denied access (403)
- Tenant isolation maintained (permissions don't cross tenant boundaries)
- Permissions cached in AuthenticatedUser (no per-request DB queries)

Reference:
- Task 21: dev-docs/analysis/phase-1-5-tasks/task-21-rbac-impl-plan.md
- Gap #41: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md
- Permission module: backend/core/permissions.py
- Enhanced auth: backend/core/auth.py
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a632bb9329d"
down_revision: str | None = "f2597a34b65b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Seed default RBAC roles and assign owner role to existing users.

    Steps:
    1. Insert 4 default roles with permissions
    2. Update existing users to have "owner" role (backward compatibility)
    """

    # Step 1: Insert default roles
    # Using raw SQL to properly format JSONB permissions
    op.execute("""
        INSERT INTO tenant_user_role (code, name, description, permissions, is_default, is_active, created_at, updated_at)
        VALUES
            -- Owner Role: Full access to all tenant resources
            (
                'owner',
                'Owner',
                'Full access to all tenant resources. Recommended for solo contractors and business owners.',
                '["*", "users.manage", "users.view", "integrations.manage"]'::jsonb,
                true,
                true,
                NOW(),
                NOW()
            ),
            
            -- Technician Role: Field operations only
            (
                'technician',
                'Field Technician',
                'Can view and update jobs, log time and expenses, use voice AI for field operations.',
                '["jobs.view", "jobs.update", "time_entries.create", "time_entries.view", "time_entries.update", "expenses.create", "expenses.view", "expenses.update", "voice.use", "nec.calculate"]'::jsonb,
                false,
                true,
                NOW(),
                NOW()
            ),
            
            -- Office Staff Role: Administrative tasks
            (
                'office_staff',
                'Office Staff',
                'Manages customers, quotes, sites, and administrative tasks. Cannot access financial or job execution data.',
                '["customers.*", "quotes.*", "sites.*", "contacts.*", "addresses.*", "invoices.view", "invoices.create", "reports.view", "users.view"]'::jsonb,
                false,
                true,
                NOW(),
                NOW()
            ),
            
            -- Accountant Role: Read-only financial access
            (
                'accountant',
                'Accountant',
                'Read-only access to financial data and audit logs for compliance and bookkeeping.',
                '["*.view", "audit.view", "reports.view"]'::jsonb,
                false,
                true,
                NOW(),
                NOW()
            )
        ON CONFLICT (code) DO NOTHING;
    """)

    # Step 2: Backward compatibility - Assign "owner" role to all existing users
    # This ensures existing users can continue to access the system
    # Users who previously had NULL role_code will now have "owner" role
    op.execute("""
        UPDATE tenant_user
        SET role_code = 'owner',
            updated_at = NOW()
        WHERE role_code IS NULL OR role_code = '';
    """)


def downgrade() -> None:
    """
    Remove default roles and revert user role assignments.

    WARNING: This will break permission checks if rolled back.
    Only use for development/testing rollbacks.
    """

    # Step 1: Set user roles back to NULL (if they were owner)
    # Only affects users who were auto-assigned owner in this migration
    op.execute("""
        UPDATE tenant_user
        SET role_code = NULL,
            updated_at = NOW()
        WHERE role_code = 'owner';
    """)

    # Step 2: Delete default roles
    op.execute("""
        DELETE FROM tenant_user_role
        WHERE code IN ('owner', 'technician', 'office_staff', 'accountant');
    """)
