"""phase_fe_1_batch_b12_voice_persona_settings

Revision ID: 4c262bd92137
Revises: 8ed92ad6e08f
Create Date: 2026-05-02 18:59:27.000000

B12/A67 — Voice Persona Tone Renderer + Per-User Resolution

Adds two columns to tenant_settings:
  - voice_persona_tone (TEXT, nullable): tenant default tone.
    NULL resolves to system default 'balanced' at runtime.
    Check constraint: conservative | balanced | playful
  - voice_persona_tone_user_override_allowed (BOOLEAN, NOT NULL, default TRUE):
    Meta-toggle; when FALSE the resolver ignores user-tier overrides for this key.
    Existing user overrides in user_setting_override are preserved (not deleted).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4c262bd92137"
down_revision = "8ed92ad6e08f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add voice_persona_tone as nullable TEXT with check constraint
    op.execute("""
        ALTER TABLE tenant_settings
        ADD COLUMN voice_persona_tone TEXT NULL;
    """)

    op.execute("""
        ALTER TABLE tenant_settings
        ADD CONSTRAINT tenant_settings_voice_persona_tone_chk
        CHECK (
            voice_persona_tone IS NULL
            OR voice_persona_tone IN ('conservative', 'balanced', 'playful')
        );
    """)

    # Add meta-toggle as NOT NULL BOOLEAN with server default TRUE
    # Server default TRUE so all existing tenants automatically allow user override
    op.execute("""
        ALTER TABLE tenant_settings
        ADD COLUMN voice_persona_tone_user_override_allowed BOOLEAN NOT NULL DEFAULT TRUE;
    """)

    # Seed RBAC permissions for voice persona tone (B12/A67)
    # All roles get voice_persona_tone.user_override.edit (gated by meta-toggle at runtime)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["voice_persona_tone.tenant_default.edit", "voice_persona_tone.user_override_policy.edit", "voice_persona_tone.user_override.edit"]'::jsonb
        WHERE code = 'owner'
          AND NOT (permissions @> '["voice_persona_tone.user_override.edit"]'::jsonb)
    """)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["voice_persona_tone.user_override.edit"]'::jsonb
        WHERE code IN ('technician', 'accountant', 'office_staff')
          AND NOT (permissions @> '["voice_persona_tone.user_override.edit"]'::jsonb)
    """)


def downgrade() -> None:
    # Remove RBAC permissions
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN (
                '"voice_persona_tone.tenant_default.edit"',
                '"voice_persona_tone.user_override_policy.edit"',
                '"voice_persona_tone.user_override.edit"'
            )
        )
        WHERE code IN ('owner', 'technician', 'accountant', 'office_staff')
    """)

    op.execute("""
        ALTER TABLE tenant_settings
        DROP CONSTRAINT IF EXISTS tenant_settings_voice_persona_tone_chk;
    """)

    op.execute("""
        ALTER TABLE tenant_settings
        DROP COLUMN IF EXISTS voice_persona_tone_user_override_allowed;
    """)

    op.execute("""
        ALTER TABLE tenant_settings
        DROP COLUMN IF EXISTS voice_persona_tone;
    """)
