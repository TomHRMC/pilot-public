"""phase_mkt_b1_5_marketing_newsletter_subscriber

Revision ID: 381db126998f
Revises: 38566adaa986
Create Date: 2026-05-20 18:06:00.000000

MKT-B1.5-BE: Creates marketing_newsletter_subscriber table.
- CITEXT extension already present from B1 migration — NOT added again
- trade_interest and content_preferences use VARCHAR[] (PostgreSQL ARRAY)
- Triggers: audit only
  - guard_created_fields_immutable intentionally OMITTED: this trigger checks
    NEW.created_at, but this table uses subscribed_at (not created_at). Attaching
    the trigger would cause a PG runtime error "record new has no field created_at".
    Deviation from §13.4 2-trigger minimum is intentional and documented here.
  - set_updated_at intentionally OMITTED: no updated_at column.
"""

from alembic import op

revision = "381db126998f"
down_revision = "38566adaa986"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS marketing_newsletter_subscriber (
            id                  UUID        NOT NULL DEFAULT gen_random_uuid(),
            email               CITEXT      NOT NULL,
            trade_interest      VARCHAR[]   NULL,
            content_preferences VARCHAR[]   NULL,
            source              VARCHAR     NULL,
            utm_source          VARCHAR     NULL,
            utm_medium          VARCHAR     NULL,
            utm_campaign        VARCHAR     NULL,
            subscribed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            unsubscribed_at     TIMESTAMPTZ NULL,
            is_active           BOOLEAN     NOT NULL DEFAULT true,
            CONSTRAINT pk_marketing_newsletter_subscriber PRIMARY KEY (id),
            CONSTRAINT uq_marketing_newsletter_subscriber_email UNIQUE (email)
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_marketing_newsletter_subscriber_email
        ON public.marketing_newsletter_subscriber USING btree (email);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_marketing_newsletter_subscriber_subscribed_at
        ON public.marketing_newsletter_subscriber USING btree (subscribed_at);
    """)

    op.execute("""
        CREATE TRIGGER audit_marketing_newsletter_subscriber_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.marketing_newsletter_subscriber
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    # guard_created_fields_immutable intentionally OMITTED — table uses subscribed_at
    # (not created_at); trigger would cause "record new has no field created_at" error.
    # set_updated_at intentionally OMITTED — no updated_at column.


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS audit_marketing_newsletter_subscriber_changes
        ON public.marketing_newsletter_subscriber;
    """)
    op.execute("DROP TABLE IF EXISTS public.marketing_newsletter_subscriber;")
