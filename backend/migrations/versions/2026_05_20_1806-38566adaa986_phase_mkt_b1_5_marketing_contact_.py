"""phase_mkt_b1_5_marketing_contact_submission

Revision ID: 38566adaa986
Revises: fc735b4c9839
Create Date: 2026-05-20 18:06:00.000000

MKT-B1.5-BE: Creates marketing_contact_submission table.
- CITEXT extension already present from B1 migration — NOT added again
- Triggers: audit + guard_created_immutable
- Trigger set_updated_at intentionally OMITTED (no updated_at column — would cause PG error)
"""

from alembic import op

revision = "38566adaa986"
down_revision = "fc735b4c9839"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS marketing_contact_submission (
            id              UUID        NOT NULL DEFAULT gen_random_uuid(),
            name            VARCHAR     NOT NULL,
            email           CITEXT      NOT NULL,
            company         VARCHAR     NULL,
            trade           VARCHAR     NULL,
            subject         VARCHAR     NOT NULL,
            message         TEXT        NOT NULL,
            source_page     VARCHAR     NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            is_read         BOOLEAN     NOT NULL DEFAULT false,
            CONSTRAINT pk_marketing_contact_submission PRIMARY KEY (id)
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_marketing_contact_submission_email
        ON public.marketing_contact_submission USING btree (email);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_marketing_contact_submission_created_at
        ON public.marketing_contact_submission USING btree (created_at);
    """)

    op.execute("""
        CREATE TRIGGER audit_marketing_contact_submission_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.marketing_contact_submission
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_marketing_contact_submission_guard_created_immutable
        BEFORE UPDATE ON public.marketing_contact_submission
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)
    # Trigger 3 (set_updated_at) intentionally omitted — no updated_at column.


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_marketing_contact_submission_guard_created_immutable
        ON public.marketing_contact_submission;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS audit_marketing_contact_submission_changes
        ON public.marketing_contact_submission;
    """)
    op.execute("DROP TABLE IF EXISTS public.marketing_contact_submission;")
