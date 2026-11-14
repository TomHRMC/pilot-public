"""phase_mkt_b1_marketing_waitlist_signup

Revision ID: fc735b4c9839
Revises: a688e8f4f8ed
Create Date: 2026-05-19 22:29:00.000000

MKT-B1-BE: Creates the marketing_waitlist_signup table for public waitlist form submissions.
- Email stored as CITEXT for case-insensitive uniqueness (no UNIQUE on login email, just for dedup)
- No tenant_id — this is a public unauthenticated table
- No created_by / updated_by FKs — no auth context on submission
- Trigger #1: audit_marketing_waitlist_signup_changes (audit.log_changes)
- Trigger #2: trg_marketing_waitlist_signup_guard_created_immutable (guard_created_fields_immutable)
- Trigger #3: trg_marketing_waitlist_signup_set_updated_at (set_updated_at) — table has no
  updated_at column so this is a no-op trigger; included to satisfy schema diff tooling.
  NOTE: Actually OMITTING trigger #3 because the table has no updated_at column — the
  set_updated_at() function references NEW.updated_at which would cause a runtime ERROR.
  This deviation is intentional and noted here. schema_diff tooling must be configured to
  accept this exception for tables without updated_at.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fc735b4c9839"
down_revision = "a688e8f4f8ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent CITEXT extension (already installed, but explicit for safety)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    op.execute("""
        CREATE TABLE IF NOT EXISTS marketing_waitlist_signup (
            id              UUID            NOT NULL DEFAULT gen_random_uuid(),
            email           CITEXT          NOT NULL,
            trade           VARCHAR         NOT NULL,
            company_size    VARCHAR         NOT NULL,
            source          VARCHAR         NOT NULL,
            utm_source      VARCHAR         NULL,
            utm_medium      VARCHAR         NULL,
            utm_campaign    VARCHAR         NULL,
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            converted_at    TIMESTAMPTZ     NULL,
            is_active       BOOLEAN         NOT NULL DEFAULT true,
            CONSTRAINT pk_marketing_waitlist_signup PRIMARY KEY (id),
            CONSTRAINT uq_marketing_waitlist_signup_email UNIQUE (email)
        );
    """)

    # Indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_marketing_waitlist_signup_email
        ON public.marketing_waitlist_signup USING btree (email);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_marketing_waitlist_signup_created_at
        ON public.marketing_waitlist_signup USING btree (created_at);
    """)

    # Trigger #1: Audit changes
    op.execute("""
        CREATE TRIGGER audit_marketing_waitlist_signup_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.marketing_waitlist_signup
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Trigger #2: Guard created_at / created_by immutability
    op.execute("""
        CREATE TRIGGER trg_marketing_waitlist_signup_guard_created_immutable
        BEFORE UPDATE ON public.marketing_waitlist_signup
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)

    # NOTE: Trigger #3 (set_updated_at) is intentionally OMITTED.
    # The marketing_waitlist_signup table has no updated_at column.
    # The public.set_updated_at() function references NEW.updated_at and would
    # cause a PostgreSQL runtime error if attached to this table.
    # Deviation from §13.4 3-trigger standard is intentional and documented here.


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_marketing_waitlist_signup_guard_created_immutable
        ON public.marketing_waitlist_signup;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS audit_marketing_waitlist_signup_changes
        ON public.marketing_waitlist_signup;
    """)
    op.execute("DROP TABLE IF EXISTS public.marketing_waitlist_signup;")
