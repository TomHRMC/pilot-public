"""phase_fe_1_batch_b15_email_template_table

Revision ID: 88131acac5f1
Revises: 220cfa33d815
Create Date: 2026-05-03 13:45:43.000000

B15/A82: Create email_template table with 16-row seed data.
System-wide (no tenant_id) — one set of templates applies to all tenants.
Per-tenant customisation is handled at the branding layer (tenant_email_branding).
Uses ON CONFLICT DO NOTHING so re-running is safe if data_export_ready was seeded by B13.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "88131acac5f1"
down_revision = "220cfa33d815"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create table ──────────────────────────────────────────────────────────
    op.create_table(
        "email_template",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("template_id", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("subject_template", sa.Text(), nullable=False),
        sa.Column("body_html_template", sa.Text(), nullable=False),
        sa.Column("body_plain_template", sa.Text(), nullable=False),
        sa.Column(
            "variables", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.CheckConstraint(
            "category IN ('customer_facing', 'internal')",
            name="email_template_category_chk",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_email_template_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_email_template_updated_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("template_id", name="pk_email_template"),
    )

    op.create_index("ix_email_template_category", "email_template", ["category"])

    # ── Seed 16 rows ──────────────────────────────────────────────────────────
    # Seed BEFORE triggers are created: email_template PK is template_id (TEXT),
    # not a UUID `id` column. audit.log_changes() would derive NULL entity_id and
    # violate the NOT NULL constraint. Running the INSERT before the trigger exists
    # avoids this entirely — no DISABLE/ENABLE needed.
    op.execute("""
        INSERT INTO email_template
            (template_id, display_name, category, subject_template,
             body_html_template, body_plain_template, variables,
             is_active, created_at, updated_at)
        VALUES
            ('welcome',                    'Welcome',                          'internal',         'Welcome to Pilot for Trades', '<p>Welcome to Pilot!</p>', 'Welcome to Pilot!', '["user_name","company_name"]'::jsonb, true, now(), now()),
            ('email_verification',         'Email Verification',               'internal',         'Verify your email address', '<p>Click to verify your email.</p>', 'Click to verify your email.', '["user_name","verify_url"]'::jsonb, true, now(), now()),
            ('quote_sent',                 'Quote Sent to Customer',           'customer_facing',  'Your quote from {{company_name}}', '<p>Please review your quote.</p>', 'Please review your quote.', '["customer_name","company_name","quote_total","quote_url"]'::jsonb, true, now(), now()),
            ('quote_accepted',             'Quote Accepted Notification',      'internal',         'Customer accepted your quote', '<p>Your quote was accepted!</p>', 'Your quote was accepted!', '["customer_name","quote_id","company_name"]'::jsonb, true, now(), now()),
            ('quote_declined',             'Quote Declined Notification',      'internal',         'Customer declined your quote', '<p>Your quote was declined.</p>', 'Your quote was declined.', '["customer_name","quote_id","decline_reason"]'::jsonb, true, now(), now()),
            ('quote_expiring',             'Quote Expiring Soon',              'customer_facing',  'Your quote expires soon', '<p>Your quote expires in 3 days.</p>', 'Your quote expires in 3 days.', '["customer_name","quote_url","expires_at"]'::jsonb, true, now(), now()),
            ('invoice_sent',               'Invoice Sent to Customer',         'customer_facing',  'Invoice from {{company_name}}', '<p>Your invoice is ready.</p>', 'Your invoice is ready.', '["customer_name","company_name","invoice_total","invoice_url"]'::jsonb, true, now(), now()),
            ('payment_received_tenant',    'Payment Received (Tenant)',        'internal',         'Payment received from {{customer_name}}', '<p>Payment received!</p>', 'Payment received!', '["customer_name","amount","invoice_id"]'::jsonb, true, now(), now()),
            ('payment_received_customer',  'Payment Receipt',                  'customer_facing',  'Payment confirmation from {{company_name}}', '<p>Thank you for your payment.</p>', 'Thank you for your payment.', '["customer_name","company_name","amount","payment_date"]'::jsonb, true, now(), now()),
            ('payment_failed',             'Payment Failed',                   'customer_facing',  'Payment issue with your invoice', '<p>Your payment could not be processed.</p>', 'Your payment could not be processed.', '["customer_name","invoice_url"]'::jsonb, true, now(), now()),
            ('subscription_renewal',       'Subscription Renewal',             'internal',         'Your Pilot subscription has renewed', '<p>Your subscription renewed.</p>', 'Your subscription renewed.', '["tenant_name","plan_name","next_billing_date"]'::jsonb, true, now(), now()),
            ('subscription_payment_failed','Subscription Payment Failed',      'internal',         'Action required: subscription payment failed', '<p>Your subscription payment failed.</p>', 'Your subscription payment failed.', '["tenant_name","plan_name","update_url"]'::jsonb, true, now(), now()),
            ('trial_expiring',             'Trial Expiring Soon',              'internal',         'Your free trial ends soon', '<p>Your trial ends in {{days_remaining}} days.</p>', 'Your trial ends in {{days_remaining}} days.', '["tenant_name","days_remaining","upgrade_url"]'::jsonb, true, now(), now()),
            ('trial_expired',              'Trial Expired',                    'internal',         'Your free trial has ended', '<p>Your trial has expired.</p>', 'Your trial has expired.', '["tenant_name","upgrade_url"]'::jsonb, true, now(), now()),
            ('password_reset',             'Password Reset',                   'internal',         'Reset your Pilot password', '<p>Click to reset your password.</p>', 'Click to reset your password.', '["user_name","reset_url","expires_in"]'::jsonb, true, now(), now()),
            ('mfa_reset_by_owner',         'MFA Reset by Account Owner',       'internal',         'Your MFA has been reset', '<p>Your MFA was reset by your account owner.</p>', 'Your MFA was reset by your account owner.', '["user_name","company_name"]'::jsonb, true, now(), now())
        ON CONFLICT (template_id) DO NOTHING
    """)
    # ── Triggers (created AFTER seed so they don't fire on the seed rows) ─────
    op.execute("""
        CREATE TRIGGER audit_email_template_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.email_template
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER guard_email_template_created_immutable
        BEFORE UPDATE ON public.email_template
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER set_email_template_updated_at
        BEFORE UPDATE ON public.email_template
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS set_email_template_updated_at ON public.email_template;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS guard_email_template_created_immutable ON public.email_template;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_email_template_changes ON public.email_template;"
    )
    op.drop_index("ix_email_template_category", table_name="email_template")
    op.drop_table("email_template")
