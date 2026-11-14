"""seed_system_user_sentinel

Seeds the Pilot internal system-user sentinel row into the `user` table.

This sentinel UUID (00000000-0000-0000-0000-000000000000) is used as a
placeholder `created_by` / `updated_by` for system-generated records that have
no human author. It must exist before any FK-enforced audit columns reference it.

Must run AFTER seed_missing_lookup_tables_batch_1 (platform_role must exist).

BEFORE UPDATE triggers don't fire on INSERT, so no trigger bypass is needed.

Uses INSERT ... WHERE NOT EXISTS guard to be re-run safe even if the sentinel
already exists from a manual seed.

Revision ID: 4d035847177f
Revises: dd4ed7ed5f3b
Create Date: 2026-05-31 22:16:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4d035847177f"
down_revision = "dd4ed7ed5f3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # user has UUID `id` PK — audit.log_changes() captures it correctly.
    # BEFORE UPDATE triggers don't fire on INSERT. No session_replication_role
    # bypass needed on RDS.
    # ---------------------------------------------------------------------------

    # ---------------------------------------------------------------------------
    # user — system sentinel row
    # id = all-zeros UUID (hardcoded sentinel)
    # email is citext (USER-DEFINED) — plain string insert works fine
    # platform_role_code = NULL (this is not a platform staff user)
    # is_active = false (cannot log in)
    # email_verified_at = now() (pre-verified, no flow needed)
    # require_password_reset = false
    # mfa_enforced = false
    # All nullable audit/profile columns left NULL
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO "user" (
            id,
            email,
            first_name,
            last_name,
            is_platform_user,
            platform_role_code,
            is_active,
            email_verified_at,
            require_password_reset,
            mfa_enforced,
            created_at,
            updated_at
        )
        SELECT
            '00000000-0000-0000-0000-000000000000'::uuid,
            'system@pilot.internal',
            'Pilot',
            'System',
            false,
            NULL,
            false,
            now(),
            false,
            false,
            now(),
            now()
        WHERE NOT EXISTS (
            SELECT 1 FROM "user"
            WHERE id = '00000000-0000-0000-0000-000000000000'::uuid
        );
    """)


def downgrade() -> None:
    # Remove the sentinel row — keyed on hardcoded id, safe to delete specifically
    op.execute("""
        DELETE FROM "user"
        WHERE id = '00000000-0000-0000-0000-000000000000'::uuid;
    """)
