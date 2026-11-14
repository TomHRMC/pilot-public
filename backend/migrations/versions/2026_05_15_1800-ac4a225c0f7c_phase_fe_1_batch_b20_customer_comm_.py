"""phase_fe_1_batch_b20_customer_comm_template_type_table

Revision ID: ac4a225c0f7c
Revises: c1547415efdb
Create Date: 2026-05-15 18:00:00.000000

FIND-083 / A94 — customer_comm_template_type catalog table

Changes:
1. Create customer_comm_template_type catalog table (VARCHAR PK, StandardAuditMixin)
2. Seed 13 MVP active rows + 14 Phase 2 inactive rows (27 total)
3. Drop CHECK constraint customer_communication_template_code_chk
4. Add FK fk_comm_template_type on customer_communication.template_code
5. Drop CHECK constraint communication_template_code_chk
6. Add FK fk_communication_template_type on communication_template.template_code
7. Create 3 mandatory triggers on customer_comm_template_type
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ac4a225c0f7c"
down_revision = "c1547415efdb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Create customer_comm_template_type catalog table
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "customer_comm_template_type",
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("preferred_channel", sa.String(), nullable=True),
        sa.Column("initiator", sa.String(), server_default="tech", nullable=False),
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("send_mode", sa.String(), server_default="manual", nullable=False),
        sa.Column("trigger_event", sa.String(), nullable=True),
        sa.Column(
            "is_system", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        # StandardAuditMixin columns
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "updated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.PrimaryKeyConstraint("code"),
        sa.UniqueConstraint("slug", name="uq_customer_comm_template_type_slug"),
        sa.CheckConstraint(
            "category IN ('pre_appointment','quoting','during_job','post_job','relationship','exception')",
            name="customer_comm_template_type_category_chk",
        ),
        sa.CheckConstraint(
            "preferred_channel IS NULL OR preferred_channel IN ('sms','email','both')",
            name="customer_comm_template_type_preferred_channel_chk",
        ),
        sa.CheckConstraint(
            "initiator IN ('tech','owner','system')",
            name="customer_comm_template_type_initiator_chk",
        ),
        sa.CheckConstraint(
            "send_mode IN ('manual','automated','both')",
            name="customer_comm_template_type_send_mode_chk",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_customer_comm_template_type_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_customer_comm_template_type_updated_by",
        ),
    )

    op.create_index(
        "idx_customer_comm_template_type_is_active",
        "customer_comm_template_type",
        ["is_active"],
    )
    op.create_index(
        "idx_customer_comm_template_type_category",
        "customer_comm_template_type",
        ["category"],
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Seed 27 rows (13 MVP active + 14 Phase 2 inactive)
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        INSERT INTO customer_comm_template_type
            (code, slug, name, category, initiator, send_mode, preferred_channel, requires_approval, sort_order, is_system, is_active)
        VALUES
            -- MVP Active rows (13)
            ('on_my_way',             'on_my_way',             'On My Way',             'during_job',      'tech',   'manual',    'sms',   false, 10,  true, true),
            ('running_late',          'running_late',          'Running Late',           'during_job',      'tech',   'manual',    'sms',   false, 20,  true, true),
            ('arrived',               'arrived',               'Arrived',               'during_job',      'tech',   'manual',    'sms',   false, 30,  true, true),
            ('parts_delay',           'parts_delay',           'Parts Delay',           'during_job',      'tech',   'manual',    'sms',   false, 40,  true, true),
            ('change_order_approval', 'change_order_approval', 'Change Order Approval', 'during_job',      'owner',  'manual',    'sms',   true,  50,  true, true),
            ('job_complete',          'job_complete',          'Job Complete',          'post_job',        'tech',   'manual',    'sms',   false, 60,  true, true),
            ('invoice_sent',          'invoice_sent',          'Invoice Sent',          'post_job',        'system', 'automated', 'email', false, 70,  true, true),
            ('payment_reminder',      'payment_reminder',      'Payment Reminder',      'post_job',        'system', 'automated', 'sms',   false, 80,  true, true),
            ('payment_received',      'payment_received',      'Payment Received',      'post_job',        'system', 'automated', 'email', false, 90,  true, true),
            ('confirm_appointment',   'confirm_appointment',   'Confirm Appointment',   'pre_appointment', 'tech',   'manual',    'sms',   false, 100, true, true),
            ('tech_assigned',         'tech_assigned',         'Tech Assigned',         'pre_appointment', 'system', 'automated', 'sms',   false, 110, true, true),
            ('quote_accepted',        'quote_accepted',        'Quote Accepted',        'quoting',         'system', 'automated', 'email', false, 120, true, true),
            ('quote_expiring',        'quote_expiring',        'Quote Expiring',        'quoting',         'system', 'automated', 'email', false, 130, true, true),
            -- Phase 2 Inactive rows (14)
            ('appointment_reminder_24h',        'appointment_reminder_24h',        'Appointment Reminder 24h',        'pre_appointment', 'system', 'automated', 'sms',   false, 200, true, false),
            ('appointment_reminder_1h',         'appointment_reminder_1h',         'Appointment Reminder 1h',         'pre_appointment', 'system', 'automated', 'sms',   false, 210, true, false),
            ('quote_follow_up',                 'quote_follow_up',                 'Quote Follow Up',                 'quoting',         'system', 'automated', 'email', false, 220, true, false),
            ('quote_revised',                   'quote_revised',                   'Quote Revised',                   'quoting',         'system', 'automated', 'email', false, 230, true, false),
            ('payment_overdue',                 'payment_overdue',                 'Payment Overdue',                 'post_job',        'system', 'automated', 'sms',   false, 240, true, false),
            ('receipt',                         'receipt',                         'Receipt',                         'post_job',        'system', 'automated', 'email', false, 250, true, false),
            ('warranty_info',                   'warranty_info',                   'Warranty Info',                   'post_job',        'system', 'automated', 'email', false, 260, true, false),
            ('review_request',                  'review_request',                  'Review Request',                  'relationship',    'system', 'automated', 'sms',   false, 270, true, false),
            ('referral_request',                'referral_request',                'Referral Request',                'relationship',    'system', 'automated', 'sms',   false, 280, true, false),
            ('annual_safety_check',             'annual_safety_check',             'Annual Safety Check',             'relationship',    'system', 'automated', 'sms',   false, 290, true, false),
            ('service_anniversary',             'service_anniversary',             'Service Anniversary',             'relationship',    'system', 'automated', 'sms',   false, 300, true, false),
            ('customer_cancellation_confirmed', 'customer_cancellation_confirmed', 'Customer Cancellation Confirmed', 'exception',       'system', 'automated', 'sms',   false, 310, true, false),
            ('tech_cancellation',               'tech_cancellation',               'Tech Cancellation',               'exception',       'system', 'automated', 'sms',   false, 320, true, false),
            ('no_show',                         'no_show',                         'No Show',                         'exception',       'system', 'automated', 'sms',   false, 330, true, false)
    """)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: Drop CHECK on customer_communication.template_code, add FK
    # ─────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "customer_communication_template_code_chk",
        "customer_communication",
        type_="check",
    )
    op.create_foreign_key(
        "fk_comm_template_type",
        "customer_communication",
        "customer_comm_template_type",
        ["template_code"],
        ["code"],
        ondelete="RESTRICT",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: Drop CHECK on communication_template.template_code, add FK
    # ─────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "communication_template_code_chk",
        "communication_template",
        type_="check",
    )
    op.create_foreign_key(
        "fk_communication_template_type",
        "communication_template",
        "customer_comm_template_type",
        ["template_code"],
        ["code"],
        ondelete="RESTRICT",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: Create 3 mandatory triggers on customer_comm_template_type
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TRIGGER audit_customer_comm_template_type_changes
            AFTER INSERT OR UPDATE OR DELETE ON customer_comm_template_type
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)

    op.execute("""
        CREATE TRIGGER trg_customer_comm_template_type_guard_created_immutable
            BEFORE UPDATE ON customer_comm_template_type
            FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable()
    """)

    op.execute("""
        CREATE TRIGGER trg_customer_comm_template_type_set_updated_at
            BEFORE UPDATE ON customer_comm_template_type
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # Reverse: drop triggers
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_comm_template_type_set_updated_at ON customer_comm_template_type"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_customer_comm_template_type_guard_created_immutable ON customer_comm_template_type"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_customer_comm_template_type_changes ON customer_comm_template_type"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Reverse: drop FKs, re-add CHECK constraints on communication_template
    # ─────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "fk_communication_template_type", "communication_template", type_="foreignkey"
    )
    op.create_check_constraint(
        "communication_template_code_chk",
        "communication_template",
        "template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment')",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Reverse: drop FKs, re-add CHECK constraints on customer_communication
    # ─────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "fk_comm_template_type", "customer_communication", type_="foreignkey"
    )
    op.create_check_constraint(
        "customer_communication_template_code_chk",
        "customer_communication",
        "template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment')",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Reverse: drop indexes, seed data, table
    # ─────────────────────────────────────────────────────────────────────────
    op.drop_index(
        "idx_customer_comm_template_type_category",
        table_name="customer_comm_template_type",
    )
    op.drop_index(
        "idx_customer_comm_template_type_is_active",
        table_name="customer_comm_template_type",
    )
    op.execute("DELETE FROM customer_comm_template_type")
    op.drop_table("customer_comm_template_type")
