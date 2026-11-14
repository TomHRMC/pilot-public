"""phase_fe_1_batch_b11_communication_threading

Revision ID: d04d7230bfb4
Revises: 73457342d2d5
Create Date: 2026-05-02 17:21:25

B11/A60 — Create customer_communication_thread, customer_communication_message,
and customer_communication_unrouted tables.

Also adds thread_id FK column to the existing customer_communication table (B4 backfill).
Depends on Migration 2 (tenant_phone_number must exist before thread FK).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d04d7230bfb4"
down_revision = "73457342d2d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── customer_communication_thread ──────────────────────────────────────
    op.execute("""
        CREATE TABLE customer_communication_thread (
            id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id               UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            customer_id             UUID        NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
            tech_id                 UUID        NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            tenant_phone_number_id  UUID        NOT NULL REFERENCES tenant_phone_number(id) ON DELETE RESTRICT,
            status                  TEXT        NOT NULL DEFAULT 'active',
            first_message_at        TIMESTAMPTZ NOT NULL,
            last_message_at         TIMESTAMPTZ NOT NULL,
            message_count           INTEGER     NOT NULL DEFAULT 0,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by              UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by              UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT customer_communication_thread_status_chk
                CHECK (status IN ('active', 'archived'))
        );
    """)

    # Routing key: unique active thread per (tenant, customer, tech, phone)
    op.execute("""
        CREATE UNIQUE INDEX uq_comm_thread_routing_key
            ON customer_communication_thread(tenant_id, customer_id, tech_id, tenant_phone_number_id)
            WHERE status = 'active';
    """)

    op.execute("""
        CREATE INDEX idx_comm_thread_tenant_id   ON customer_communication_thread(tenant_id);
        CREATE INDEX idx_comm_thread_customer_id ON customer_communication_thread(customer_id);
        CREATE INDEX idx_comm_thread_tech_id     ON customer_communication_thread(tech_id);
        CREATE INDEX idx_comm_thread_last_msg    ON customer_communication_thread(tenant_id, last_message_at DESC);
    """)

    op.execute("""
        CREATE TRIGGER audit_customer_communication_thread_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication_thread
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_thread_guard_created_immutable
            BEFORE UPDATE ON public.customer_communication_thread
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_thread_set_updated_at
            BEFORE UPDATE ON public.customer_communication_thread
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)

    # ── customer_communication_message ─────────────────────────────────────
    op.execute("""
        CREATE TABLE customer_communication_message (
            id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            thread_id           UUID        NOT NULL REFERENCES customer_communication_thread(id) ON DELETE RESTRICT,
            direction           TEXT        NOT NULL,
            channel             TEXT        NOT NULL DEFAULT 'sms',
            body                TEXT        NOT NULL,
            segment_count       INTEGER     NOT NULL DEFAULT 1,
            status              TEXT        NOT NULL DEFAULT 'pending_send',
            carrier_message_id  TEXT        NULL,
            sent_at             TIMESTAMPTZ NULL,
            delivered_at        TIMESTAMPTZ NULL,
            received_at         TIMESTAMPTZ NULL,
            composition_method  TEXT        NULL,
            template_id         UUID        NULL REFERENCES communication_template(id) ON DELETE SET NULL,
            voice_audio_id      BIGINT      NULL REFERENCES voice_command_log(id) ON DELETE SET NULL,
            audit_user_id       UUID        NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT customer_communication_message_direction_chk
                CHECK (direction IN ('outbound', 'inbound')),
            CONSTRAINT customer_communication_message_channel_chk
                CHECK (channel IN ('sms')),
            CONSTRAINT customer_communication_message_status_chk
                CHECK (status IN ('pending_send', 'sent', 'delivered', 'failed', 'received')),
            CONSTRAINT customer_communication_message_composition_method_chk
                CHECK (composition_method IS NULL OR
                       composition_method IN ('template', 'free_form_text', 'free_form_voice'))
        );
    """)

    op.execute("""
        CREATE INDEX idx_comm_message_thread_id ON customer_communication_message(thread_id);
        CREATE INDEX idx_comm_message_status    ON customer_communication_message(thread_id, status);
        CREATE INDEX idx_comm_message_direction ON customer_communication_message(thread_id, direction, received_at DESC);
    """)

    op.execute("""
        CREATE TRIGGER audit_customer_communication_message_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication_message
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_message_guard_created_immutable
            BEFORE UPDATE ON public.customer_communication_message
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_message_set_updated_at
            BEFORE UPDATE ON public.customer_communication_message
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)

    # ── customer_communication_unrouted ────────────────────────────────────
    op.execute("""
        CREATE TABLE customer_communication_unrouted (
            id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            from_number         TEXT        NOT NULL,
            to_number           TEXT        NOT NULL,
            body                TEXT        NOT NULL,
            carrier_message_id  TEXT        NULL,
            received_at         TIMESTAMPTZ NOT NULL,
            parked_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at         TIMESTAMPTZ NULL,
            resolved_by         UUID        NULL REFERENCES "user"(id) ON DELETE SET NULL,
            resolved_thread_id  UUID        NULL REFERENCES customer_communication_thread(id) ON DELETE SET NULL,
            status              TEXT        NOT NULL DEFAULT 'parked',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT customer_communication_unrouted_status_chk
                CHECK (status IN ('parked', 'assigned', 'dismissed'))
        );
    """)

    op.execute("""
        CREATE INDEX idx_comm_unrouted_tenant_id ON customer_communication_unrouted(tenant_id, status);
        CREATE INDEX idx_comm_unrouted_parked_at ON customer_communication_unrouted(tenant_id, parked_at DESC);
    """)

    op.execute("""
        CREATE TRIGGER audit_customer_communication_unrouted_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication_unrouted
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_unrouted_guard_created_immutable
            BEFORE UPDATE ON public.customer_communication_unrouted
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_unrouted_set_updated_at
            BEFORE UPDATE ON public.customer_communication_unrouted
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)

    # ── B4 Coexistence: add thread_id FK to existing customer_communication ─
    op.execute("""
        ALTER TABLE customer_communication
            ADD COLUMN thread_id UUID NULL
                REFERENCES customer_communication_thread(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    # Remove B4 coexistence column first
    op.execute("ALTER TABLE customer_communication DROP COLUMN IF EXISTS thread_id;")

    # Drop unrouted
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_unrouted_set_updated_at ON public.customer_communication_unrouted;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_unrouted_guard_created_immutable ON public.customer_communication_unrouted;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_customer_communication_unrouted_changes ON public.customer_communication_unrouted;"
    )
    op.execute("DROP TABLE IF EXISTS customer_communication_unrouted;")

    # Drop messages
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_message_set_updated_at ON public.customer_communication_message;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_message_guard_created_immutable ON public.customer_communication_message;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_customer_communication_message_changes ON public.customer_communication_message;"
    )
    op.execute("DROP TABLE IF EXISTS customer_communication_message;")

    # Drop threads (last — others have FKs to it)
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_thread_set_updated_at ON public.customer_communication_thread;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_communication_thread_guard_created_immutable ON public.customer_communication_thread;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_customer_communication_thread_changes ON public.customer_communication_thread;"
    )
    op.execute("DROP TABLE IF EXISTS customer_communication_thread;")
