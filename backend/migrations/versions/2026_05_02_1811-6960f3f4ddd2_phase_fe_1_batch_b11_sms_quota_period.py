"""phase_fe_1_batch_b11_sms_quota_period

Revision ID: 6960f3f4ddd2
Revises: d04d7230bfb4
Create Date: 2026-05-02 18:11:08

B11/A65 — Create sms_quota_period table.
Tracks monthly SMS segment usage per tenant with EXCLUDE constraint to prevent
overlapping periods. Requires btree_gist extension (confirmed installed).

overage_segments is a GENERATED ALWAYS AS STORED column computed from
GREATEST(0, used_segments - included_segments).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6960f3f4ddd2"
down_revision = "d04d7230bfb4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE sms_quota_period (
            id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            period_start      TIMESTAMPTZ NOT NULL,
            period_end        TIMESTAMPTZ NOT NULL,
            included_segments INTEGER     NOT NULL DEFAULT 100,
            used_segments     INTEGER     NOT NULL DEFAULT 0,
            overage_segments  INTEGER     GENERATED ALWAYS AS (GREATEST(0, used_segments - included_segments)) STORED,
            cap_policy        TEXT        NOT NULL DEFAULT 'soft',
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT sms_quota_period_cap_policy_chk
                CHECK (cap_policy IN ('soft', 'hard')),
            CONSTRAINT sms_quota_period_no_overlap
                EXCLUDE USING gist (
                    tenant_id WITH =,
                    tstzrange(period_start, period_end) WITH &&
                )
        );
    """)

    op.execute("""
        CREATE INDEX idx_sms_quota_period_tenant_active
            ON sms_quota_period(tenant_id, period_start DESC);
    """)

    # Standard triggers
    op.execute("""
        CREATE TRIGGER audit_sms_quota_period_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.sms_quota_period
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_sms_quota_period_guard_created_immutable
            BEFORE UPDATE ON public.sms_quota_period
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_sms_quota_period_set_updated_at
            BEFORE UPDATE ON public.sms_quota_period
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_sms_quota_period_set_updated_at ON public.sms_quota_period;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_sms_quota_period_guard_created_immutable ON public.sms_quota_period;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_sms_quota_period_changes ON public.sms_quota_period;"
    )
    op.execute("DROP TABLE IF EXISTS sms_quota_period;")
