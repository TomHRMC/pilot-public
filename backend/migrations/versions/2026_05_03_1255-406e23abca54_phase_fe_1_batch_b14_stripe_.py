"""phase_fe_1_batch_b14_stripe_subscription_webhook

Revision ID: 406e23abca54
Revises: d41e1505e201
Create Date: 2026-05-03 12:55:07

B14/A76: Stripe Webhook Dedup Table + RBAC
- Creates stripe_webhook_event_processed table (AppendOnlyMixin, TEXT PK = Stripe event_id)
- No new RBAC permissions needed (webhook endpoints are public + signature-verified)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "406e23abca54"
down_revision = "d41e1505e201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. CREATE stripe_webhook_event_processed (AppendOnlyMixin — 2 triggers)
    # TEXT PK — Stripe event IDs are strings (evt_1abc...)
    # id UUID added for audit.log_changes() entity_id extraction
    # ============================================================
    op.execute("""
        CREATE TABLE stripe_webhook_event_processed (
            id           UUID        NOT NULL DEFAULT gen_random_uuid(),
            event_id     TEXT        NOT NULL,
            processed_at TIMESTAMPTZ NOT NULL,
            event_type   TEXT        NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by   UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_stripe_webhook_event_processed PRIMARY KEY (event_id),
            CONSTRAINT uq_stripe_webhook_event_processed_id UNIQUE (id)
        )
    """)

    # AppendOnlyMixin: 2 triggers (audit + immutable guard — NO updated_at trigger)
    op.execute("""
        CREATE TRIGGER audit_stripe_webhook_event_processed_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.stripe_webhook_event_processed
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_stripe_webhook_event_processed_guard_created_immutable
            BEFORE UPDATE ON public.stripe_webhook_event_processed
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_stripe_webhook_event_processed_changes ON public.stripe_webhook_event_processed;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_stripe_webhook_event_processed_guard_created_immutable ON public.stripe_webhook_event_processed;"
    )
    op.execute("DROP TABLE IF EXISTS stripe_webhook_event_processed;")
