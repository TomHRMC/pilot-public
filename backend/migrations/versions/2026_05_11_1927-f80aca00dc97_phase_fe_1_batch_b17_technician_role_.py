"""phase_fe_1_batch_b17_technician_role_voice_sync_permissions

FIND-128 (S2 High): Add voice.create, voice.view, mobile_sync.view, and
mobile_sync.resolve permissions to the technician role.

Context:
  - voice.create: required by POST /api/v1/voice/sessions — without it, techs
    get 403 on every voice AI session start
  - voice.view: required by GET /api/v1/voice/sessions — without it, techs
    cannot list or resume existing sessions (breaks multi-turn context)
  - mobile_sync.view: required by GET /api/v1/mobile/sync — without it, techs
    cannot check their sync queue status on-device
  - mobile_sync.resolve: required by POST /api/v1/mobile/sync/conflicts/{id}/resolve
    — without it, techs cannot resolve their own offline sync conflicts

  nec.calculate: INTENTIONALLY kept — forward-looking permission for Phase 2
  NEC route guards (calculate_voltage_drop, calculate_conduit_fill). Currently
  orphaned (no active require_permission guard uses it), but kept per Tom's
  decision 2026-05-10 to avoid a separate future migration.

Implementation note: The plan entry references `platform_role` table, but the
actual RBAC roles table is `tenant_user_role`. This migration targets
`tenant_user_role` which is the live table containing the technician role row.

Revision ID: f80aca00dc97
Revises: 9f8116bb6ad1
Create Date: 2026-05-11 19:27:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f80aca00dc97"
down_revision = "9f8116bb6ad1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use jsonb || operator to merge new permissions into the existing array.
    # ON CONFLICT: if the permission already exists in the array, jsonb union
    # via || may produce duplicates — use array-distinct via subquery to deduplicate.
    # Simpler: use jsonb_agg(DISTINCT elem) over the combined array.
    op.execute("""
        UPDATE tenant_user_role
        SET permissions = (
            SELECT jsonb_agg(DISTINCT perm ORDER BY perm)
            FROM jsonb_array_elements_text(
                permissions || '["voice.create","voice.view","mobile_sync.view","mobile_sync.resolve"]'::jsonb
            ) AS perm
        ),
        updated_at = now()
        WHERE code = 'technician';
    """)


def downgrade() -> None:
    # Remove only the 4 permissions added by this migration.
    # Preserves any other permissions already on the technician role.
    op.execute("""
        UPDATE tenant_user_role
        SET permissions = (
            SELECT jsonb_agg(perm ORDER BY perm)
            FROM jsonb_array_elements_text(permissions) AS perm
            WHERE perm NOT IN ('voice.create', 'voice.view', 'mobile_sync.view', 'mobile_sync.resolve')
        ),
        updated_at = now()
        WHERE code = 'technician';
    """)
