"""phase_fe_1_batch_b13_mfa_policy_settings

Revision ID: 7b059e2e001b
Revises: f34992b63714
Create Date: 2026-05-02 19:47:58

A68: Add MFA policy columns to tenant_settings.
Uses 3-part additive pattern (nullable → backfill → constrain) for boolean and integer.
Also seeds notification sub-trigger IDs for MFA grace period reminders.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7b059e2e001b"
down_revision = "f34992b63714"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Part 1: Add columns as NULLABLE (IF NOT EXISTS for RDS idempotency) ---
    op.execute("""
        ALTER TABLE tenant_settings
            ADD COLUMN IF NOT EXISTS tenant_mfa_required BOOLEAN,
            ADD COLUMN IF NOT EXISTS tenant_mfa_required_grace_period_starts_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS tenant_mfa_grace_period_days INTEGER
    """)

    # --- Part 2: Backfill existing rows ---
    op.execute("""
        UPDATE tenant_settings
            SET tenant_mfa_required = false,
                tenant_mfa_grace_period_days = 7
        WHERE tenant_mfa_required IS NULL
    """)

    # --- Part 3: Set NOT NULL + DEFAULT for boolean and integer (grace period stays nullable) ---
    op.execute("""
        ALTER TABLE tenant_settings
            ALTER COLUMN tenant_mfa_required SET NOT NULL,
            ALTER COLUMN tenant_mfa_required SET DEFAULT false,
            ALTER COLUMN tenant_mfa_grace_period_days SET NOT NULL,
            ALTER COLUMN tenant_mfa_grace_period_days SET DEFAULT 7
    """)

    # Seed notification sub-triggers for MFA grace period reminders (F4 decision)
    # Columns confirmed via MCP: sub_trigger_id (text PK), category_id, display_label,
    # forced_minimum_push_uniform, forced_minimum_push_recipient_only
    # Disable audit trigger during seeding: sub_trigger_id is TEXT, not UUID,
    # so audit.log_changes() cannot derive entity_id (UUID) — would fail NOT NULL constraint.
    # RDS note: "DISABLE TRIGGER ALL" requires superuser; "DISABLE TRIGGER USER" disables
    # only user-defined triggers (sufficient here — RI constraint triggers not relevant).
    op.execute("ALTER TABLE notification_category_sub_trigger DISABLE TRIGGER USER")
    op.execute("""
        INSERT INTO notification_category_sub_trigger
            (sub_trigger_id, category_id, display_label,
             forced_minimum_push_uniform, forced_minimum_push_recipient_only)
        VALUES
            ('mfa_grace_reminder_gentle', 'system_announcements',
             'MFA Grace Reminder (Gentle — Days 0-3)', false, false),
            ('mfa_grace_reminder_urgent', 'system_announcements',
             'MFA Grace Reminder (Urgent — Days 4-6)', false, false),
            ('mfa_grace_reminder_critical', 'system_announcements',
             'MFA Grace Reminder (Critical — Day 7)', true, true)
        ON CONFLICT (sub_trigger_id) DO NOTHING
    """)
    op.execute("ALTER TABLE notification_category_sub_trigger ENABLE TRIGGER USER")


def downgrade() -> None:
    # Remove seeded sub-triggers
    op.execute("""
        DELETE FROM notification_category_sub_trigger
        WHERE sub_trigger_id IN (
            'mfa_grace_reminder_gentle',
            'mfa_grace_reminder_urgent',
            'mfa_grace_reminder_critical'
        )
    """)
    op.execute("""
        ALTER TABLE tenant_settings
            DROP COLUMN IF EXISTS tenant_mfa_required,
            DROP COLUMN IF EXISTS tenant_mfa_required_grace_period_starts_at,
            DROP COLUMN IF EXISTS tenant_mfa_grace_period_days
    """)
