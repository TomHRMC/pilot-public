"""phase_fe_1_batch_b14_subscription_tier_infrastructure

Revision ID: 2cb6b20b35d7
Revises: f308a6043aec
Create Date: 2026-05-03 12:21:51

B14/A75: Subscription Tier Infrastructure
- Creates subscription_tier table with seed data
- Creates tenant_tier_override table
- Creates tenant_subscription_usage table (composite PK)
- Adds 5 subscription columns to tenant table (3-part pattern)
- Seeds RBAC permissions: subscription.view, subscription.tier.change
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2cb6b20b35d7"
down_revision = "f308a6043aec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. CREATE subscription_tier
    # ============================================================
    op.execute("""
        CREATE TABLE subscription_tier (
            tier_id       UUID        NOT NULL DEFAULT gen_random_uuid(),
            tier_name     TEXT        NOT NULL,
            display_label TEXT        NOT NULL,
            monthly_price_cents INTEGER NOT NULL,
            is_trial      BOOLEAN     NOT NULL DEFAULT false,
            trial_duration_days INTEGER,
            max_users     INTEGER     NOT NULL,
            max_sms_segments_per_month INTEGER,
            is_active     BOOLEAN     NOT NULL DEFAULT true,
            display_order INTEGER     NOT NULL,
            stripe_price_id TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by    UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by    UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_subscription_tier PRIMARY KEY (tier_id)
        )
    """)

    op.execute("""
        CREATE INDEX ix_subscription_tier_is_active
            ON public.subscription_tier USING btree (is_active)
    """)
    op.execute("""
        CREATE INDEX ix_subscription_tier_is_trial
            ON public.subscription_tier USING btree (is_trial)
    """)

    # ============================================================
    # 2. SEED subscription_tier rows
    # Seed BEFORE creating audit trigger: subscription_tier uses tier_id UUID as PK
    # (not id). audit.log_changes() at this point in the chain has no 'unknown_'
    # fallback yet, so entity_id would be NULL — violating NOT NULL on audit.event.
    # Inserting before the trigger exists avoids this entirely.
    # ============================================================
    op.execute("""
        INSERT INTO subscription_tier
            (tier_name, display_label, monthly_price_cents, is_trial, trial_duration_days,
             max_users, is_active, display_order)
        VALUES
            ('trial',        'Trial',        0,     true,  14, 5,  true, 1),
            ('starter',      'Starter',      14900, false, NULL, 5,  true, 2),
            ('professional', 'Professional', 24900, false, NULL, 15, true, 3),
            ('enterprise',   'Enterprise',   44900, false, NULL, 50, true, 4)
    """)

    # Triggers for subscription_tier (created AFTER seed rows so audit trigger
    # does not fire on the seed INSERTs above)
    op.execute("""
        CREATE TRIGGER audit_subscription_tier_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.subscription_tier
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_subscription_tier_guard_created_immutable
            BEFORE UPDATE ON public.subscription_tier
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_subscription_tier_set_updated_at
            BEFORE UPDATE ON public.subscription_tier
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ============================================================
    # 3. ADD 5 columns to tenant (3-part pattern)
    # ============================================================

    # Part 1: Add columns as NULLABLE
    op.execute("""
        ALTER TABLE tenant
            ADD COLUMN current_subscription_tier_id UUID,
            ADD COLUMN trial_started_at TIMESTAMPTZ,
            ADD COLUMN trial_ends_at TIMESTAMPTZ,
            ADD COLUMN trial_length_days_override INTEGER,
            ADD COLUMN stripe_customer_id TEXT
    """)

    # Add FK for current_subscription_tier_id
    op.execute("""
        ALTER TABLE tenant
            ADD CONSTRAINT fk_tenant_current_subscription_tier_id
            FOREIGN KEY (current_subscription_tier_id)
            REFERENCES subscription_tier(tier_id)
            ON DELETE RESTRICT
    """)
    op.execute("""
        CREATE INDEX ix_tenant_current_subscription_tier_id
            ON public.tenant USING btree (current_subscription_tier_id)
    """)

    # Part 2: Backfill current_subscription_tier_id → trial tier
    op.execute("""
        UPDATE tenant
        SET current_subscription_tier_id = (
            SELECT tier_id FROM subscription_tier WHERE is_trial = true LIMIT 1
        )
    """)

    # Part 3: Constrain to NOT NULL
    op.execute("""
        ALTER TABLE tenant
            ALTER COLUMN current_subscription_tier_id SET NOT NULL
    """)

    # ============================================================
    # 4. CREATE tenant_tier_override
    # ============================================================
    op.execute("""
        CREATE TABLE tenant_tier_override (
            tenant_id                UUID        NOT NULL,
            override_tier_id         UUID        REFERENCES subscription_tier(tier_id) ON DELETE RESTRICT,
            override_trial_length_days INTEGER,
            override_reason          TEXT,
            set_by_operator_user_id  UUID        NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            set_at                   TIMESTAMPTZ NOT NULL,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by               UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by               UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_tenant_tier_override PRIMARY KEY (tenant_id),
            CONSTRAINT fk_tenant_tier_override_tenant_id
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT
        )
    """)

    # Triggers for tenant_tier_override
    op.execute("""
        CREATE TRIGGER audit_tenant_tier_override_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.tenant_tier_override
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_tier_override_guard_created_immutable
            BEFORE UPDATE ON public.tenant_tier_override
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_tier_override_set_updated_at
            BEFORE UPDATE ON public.tenant_tier_override
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ============================================================
    # 5. CREATE tenant_subscription_usage
    # ============================================================
    op.execute("""
        CREATE TABLE tenant_subscription_usage (
            tenant_id              UUID        NOT NULL,
            period_start           TIMESTAMPTZ NOT NULL,
            period_end             TIMESTAMPTZ NOT NULL,
            current_user_count     INTEGER     NOT NULL DEFAULT 0,
            current_sms_segment_count INTEGER  NOT NULL DEFAULT 0,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by             UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by             UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_tenant_subscription_usage PRIMARY KEY (tenant_id, period_start),
            CONSTRAINT fk_tenant_subscription_usage_tenant_id
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT
        )
    """)

    op.execute("""
        CREATE INDEX ix_tenant_subscription_usage_period_end
            ON public.tenant_subscription_usage USING btree (tenant_id, period_end DESC)
    """)

    # Triggers for tenant_subscription_usage
    op.execute("""
        CREATE TRIGGER audit_tenant_subscription_usage_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.tenant_subscription_usage
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_subscription_usage_guard_created_immutable
            BEFORE UPDATE ON public.tenant_subscription_usage
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_subscription_usage_set_updated_at
            BEFORE UPDATE ON public.tenant_subscription_usage
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ============================================================
    # 6. SEED new RBAC permissions
    # ============================================================
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["subscription.view"]'::jsonb
        WHERE code IN ('owner', 'accountant')
    """)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["subscription.tier.change"]'::jsonb
        WHERE code = 'owner'
    """)


def downgrade() -> None:
    # ============================================================
    # Reverse RBAC permission seeds
    # ============================================================
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN ('"subscription.view"', '"subscription.tier.change"')
        )
        WHERE code IN ('owner', 'accountant')
    """)

    # ============================================================
    # Drop tenant_subscription_usage
    # ============================================================
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_subscription_usage_changes ON public.tenant_subscription_usage;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_subscription_usage_guard_created_immutable ON public.tenant_subscription_usage;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_subscription_usage_set_updated_at ON public.tenant_subscription_usage;"
    )
    op.execute("DROP TABLE IF EXISTS tenant_subscription_usage;")

    # ============================================================
    # Drop tenant_tier_override
    # ============================================================
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_tier_override_changes ON public.tenant_tier_override;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_tier_override_guard_created_immutable ON public.tenant_tier_override;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_tier_override_set_updated_at ON public.tenant_tier_override;"
    )
    op.execute("DROP TABLE IF EXISTS tenant_tier_override;")

    # ============================================================
    # Remove tenant columns
    # ============================================================
    op.execute("DROP INDEX IF EXISTS ix_tenant_current_subscription_tier_id;")
    op.execute("""
        ALTER TABLE tenant
            DROP CONSTRAINT IF EXISTS fk_tenant_current_subscription_tier_id,
            DROP COLUMN IF EXISTS current_subscription_tier_id,
            DROP COLUMN IF EXISTS trial_started_at,
            DROP COLUMN IF EXISTS trial_ends_at,
            DROP COLUMN IF EXISTS trial_length_days_override,
            DROP COLUMN IF EXISTS stripe_customer_id
    """)

    # ============================================================
    # Drop subscription_tier
    # ============================================================
    op.execute(
        "DROP TRIGGER IF EXISTS audit_subscription_tier_changes ON public.subscription_tier;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_subscription_tier_guard_created_immutable ON public.subscription_tier;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_subscription_tier_set_updated_at ON public.subscription_tier;"
    )
    op.execute("DROP TABLE IF EXISTS subscription_tier;")
