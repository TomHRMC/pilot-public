"""phase_fe_1_batch_b10_notification_preference_in_app

Revision ID: ebb44d137b27
Revises: 3c02a7d21470
Create Date: 2026-05-02 15:31:19

Scope (A57):
  - CREATE TABLE notification_preference (user/tenant preference overrides)
  - CREATE TABLE in_app_notification (bell panel records, AppendOnly)
  - Partial unique indexes for NULL-safe uniqueness on both tables
  - Standard 3-trigger sets on both tables

Note: Seed INSERTs performed BEFORE audit trigger attachment (same pattern as
Migration 1) because audit.log_changes() expects NEW.id as entity_id, which
works correctly here since both tables use uuid PKs.
"""

from alembic import op

# revision identifiers
revision = "ebb44d137b27"
down_revision = "3c02a7d21470"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL app.user_id = '00000000-0000-0000-0000-000000000000'")

    # ──────────────────────────────────────────────────────────────
    # 1. CREATE TABLE notification_preference
    # ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE notification_preference (
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by  UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by  UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            id          UUID NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL,
            user_id     UUID,
            category_id TEXT NOT NULL,
            channel     TEXT NOT NULL,
            enabled     BOOLEAN NOT NULL,
            CONSTRAINT pk_notification_preference PRIMARY KEY (id),
            CONSTRAINT fk_notif_pref_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT,
            CONSTRAINT fk_notif_pref_user
                FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT fk_notif_pref_category
                FOREIGN KEY (category_id)
                REFERENCES notification_category(category_id) ON DELETE RESTRICT,
            CONSTRAINT chk_notif_pref_channel
                CHECK (channel IN ('push', 'email', 'in_app'))
        )
    """)

    op.execute("""
        CREATE INDEX ix_notif_pref_tenant_user
        ON notification_preference (tenant_id, user_id)
    """)
    op.execute("""
        CREATE INDEX ix_notif_pref_category_channel
        ON notification_preference (category_id, channel)
    """)

    # Partial unique indexes (NULL != NULL in standard UNIQUE)
    op.execute("""
        CREATE UNIQUE INDEX uq_notif_pref_user_level
        ON notification_preference (tenant_id, user_id, category_id, channel)
        WHERE user_id IS NOT NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_notif_pref_tenant_level
        ON notification_preference (tenant_id, category_id, channel)
        WHERE user_id IS NULL
    """)

    # Triggers for notification_preference
    op.execute("""
        CREATE TRIGGER audit_notification_preference_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.notification_preference
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_preference_guard_created_immutable
        BEFORE UPDATE ON public.notification_preference
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_notification_preference_set_updated_at
        BEFORE UPDATE ON public.notification_preference
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ──────────────────────────────────────────────────────────────
    # 2. CREATE TABLE in_app_notification
    # ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE in_app_notification (
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            notification_id UUID NOT NULL DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            user_id         UUID NOT NULL,
            category_id     TEXT NOT NULL,
            body            TEXT NOT NULL,
            deep_link_target TEXT NOT NULL,
            priority        TEXT NOT NULL DEFAULT 'standard',
            read_at         TIMESTAMPTZ,
            CONSTRAINT pk_in_app_notification PRIMARY KEY (notification_id),
            CONSTRAINT fk_in_app_notif_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT,
            CONSTRAINT fk_in_app_notif_user
                FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT fk_in_app_notif_category
                FOREIGN KEY (category_id)
                REFERENCES notification_category(category_id) ON DELETE RESTRICT,
            CONSTRAINT chk_in_app_notif_priority
                CHECK (priority IN ('standard', 'critical'))
        )
    """)

    # Partial index for unread count (bell badge) query
    op.execute("""
        CREATE INDEX ix_in_app_notif_user_unread
        ON in_app_notification (tenant_id, user_id, created_at DESC)
        WHERE read_at IS NULL
    """)

    # Full index for recent-50 bell panel list
    op.execute("""
        CREATE INDEX ix_in_app_notif_user_created
        ON in_app_notification (tenant_id, user_id, created_at DESC)
    """)

    # Triggers — AppendOnly so NO updated_at trigger; no immutable guard needed
    op.execute("""
        CREATE TRIGGER audit_in_app_notification_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.in_app_notification
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_in_app_notification_guard_created_immutable
        BEFORE UPDATE ON public.in_app_notification
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    op.execute("SET LOCAL app.user_id = '00000000-0000-0000-0000-000000000000'")

    # Drop in_app_notification
    op.execute(
        "DROP TRIGGER IF EXISTS trg_in_app_notification_guard_created_immutable ON in_app_notification"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_in_app_notification_changes ON in_app_notification"
    )
    op.execute("DROP TABLE IF EXISTS in_app_notification")

    # Drop notification_preference
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_preference_set_updated_at ON notification_preference"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_preference_guard_created_immutable ON notification_preference"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_preference_changes ON notification_preference"
    )
    op.execute("DROP TABLE IF EXISTS notification_preference")
