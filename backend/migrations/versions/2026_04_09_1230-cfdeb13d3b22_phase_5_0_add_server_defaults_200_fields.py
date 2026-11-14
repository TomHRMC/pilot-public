"""phase_5_0_add_server_defaults_200_fields

Revision ID: cfdeb13d3b22
Revises: ad336fcaabf3
Create Date: 2026-04-09 12:30:24.419146+00:00

Description:
Systematic fix for "Sweeping Missing Defaults Bug" - adds server_default to
200 fields across 78 tables to align physical database with Golden Master JSON.

Reference:
- Analysis: dev-docs/analysis/phase-5.0-db-schema-sync-6-analysis.md
- Checklist: dev-docs/db-design/required-defaults-columns-json.md
- Plan: dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cfdeb13d3b22"
down_revision: str | None = "ad336fcaabf3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # =====================================================
    # CORE MODELS (backend/app/models/core.py)
    # Expected: 15 fields across multiple tables
    # =====================================================

    # Table: tenant (1 field)
    op.alter_column(
        "tenant",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: tenant_settings (4 fields)
    op.alter_column(
        "tenant_settings",
        "default_labor_rate_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("8500"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_settings",
        "default_billable_labor_rate_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("15000"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_settings",
        "default_quote_validity_days",
        existing_type=sa.Integer(),
        server_default=sa.text("30"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_settings",
        "default_invoice_terms_days",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    # Table: customer (2 fields)
    op.alter_column(
        "customer",
        "type",
        existing_type=sa.String(),
        server_default=sa.text("'person'"),
        existing_nullable=False,
    )

    op.alter_column(
        "customer",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: site (1 field)
    op.alter_column(
        "site",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: supplier (1 field)
    op.alter_column(
        "supplier",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: app_service_category (1 field)
    op.alter_column(
        "app_service_category",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: app_service_provider (1 field)
    op.alter_column(
        "app_service_provider",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: app_service (1 field)
    op.alter_column(
        "app_service",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: contact (1 field)
    op.alter_column(
        "contact",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: address (2 fields)
    op.alter_column(
        "address",
        "country",
        existing_type=sa.String(),
        server_default=sa.text("'US'"),
        existing_nullable=False,
    )

    op.alter_column(
        "address",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # =====================================================
    # AUTH MODELS (backend/app/models/auth.py)
    # Expected: 14 fields across multiple tables
    # =====================================================

    # Table: platform_role (3 fields)
    op.alter_column(
        "platform_role",
        "permissions",
        existing_type=postgresql.JSONB(),
        server_default=sa.text("'{}'::jsonb"),
        existing_nullable=False,
    )

    op.alter_column(
        "platform_role",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "platform_role",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: user (6 fields)
    op.alter_column(
        "user",
        "is_platform_user",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "failed_login_count",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "require_password_reset",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "mfa_enforced",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "preferred_mfa_channel",
        existing_type=sa.String(),
        server_default=sa.text("'email'"),
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: user_endpoint (4 fields)
    op.alter_column(
        "user_endpoint",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "user_endpoint",
        "verification_status",
        existing_type=sa.String(),
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )

    op.alter_column(
        "user_endpoint",
        "consent_status",
        existing_type=sa.String(),
        server_default=sa.text("'unknown'"),
        existing_nullable=False,
    )

    op.alter_column(
        "user_endpoint",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: user_preference (1 field)
    op.alter_column(
        "user_preference",
        "preferences",
        existing_type=postgresql.JSONB(),
        server_default=sa.text("'{}'::jsonb"),
        existing_nullable=False,
    )

    # =====================================================
    # TENANT USER MODELS (backend/app/models/tenant_user.py)
    # Expected: 9 fields across multiple tables
    # =====================================================

    # Table: tenant_user_role (3 fields)
    op.alter_column(
        "tenant_user_role",
        "permissions",
        existing_type=postgresql.JSONB(),
        server_default=sa.text("'{}'::jsonb"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_role",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_role",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: tenant_user_status (2 fields)
    op.alter_column(
        "tenant_user_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: tenant_user (1 field)
    op.alter_column(
        "tenant_user",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: tenant_user_invite (1 field)
    op.alter_column(
        "tenant_user_invite",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: tenant_domain (1 field)
    op.alter_column(
        "tenant_domain",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: tenant_user_notification_pref (3 fields)
    op.alter_column(
        "tenant_user_notification_pref",
        "allow_in_app",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_notification_pref",
        "allow_email",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_notification_pref",
        "is_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # =====================================================
    # REFERENCE DATA MODELS (backend/app/models/reference_data.py)
    # Expected: 30 fields across multiple tables
    # =====================================================

    # Table: customer_lifecycle_status (2 fields)
    op.alter_column(
        "customer_lifecycle_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "customer_lifecycle_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: site_lifecycle_status (2 fields)
    op.alter_column(
        "site_lifecycle_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "site_lifecycle_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: supplier_lifecycle_status (2 fields)
    op.alter_column(
        "supplier_lifecycle_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_lifecycle_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: quote_status (3 fields)
    op.alter_column(
        "quote_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: job_status (3 fields)
    op.alter_column(
        "job_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "job_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "job_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: entity_type (1 field - is_default MISSING from DB)
    op.alter_column(
        "entity_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: contact_type (2 fields)
    op.alter_column(
        "contact_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "contact_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: entity_contact (1 field)
    op.alter_column(
        "entity_contact",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    # Table: address_type (2 fields)
    op.alter_column(
        "address_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "address_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: entity_address (2 fields)
    op.alter_column(
        "entity_address",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "entity_address",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: qco_line_type (2 fields)
    op.alter_column(
        "qco_line_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "qco_line_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: taxability_code (1 field)
    op.alter_column(
        "taxability_code",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: quote_link_status (2 fields)
    op.alter_column(
        "quote_link_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_link_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: qpl_contact_action_type (2 fields)
    op.alter_column(
        "qpl_contact_action_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "qpl_contact_action_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: job_expense_category (2 fields)
    op.alter_column(
        "job_expense_category",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "job_expense_category",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: invoice_status (3 fields)
    op.alter_column(
        "invoice_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # =====================================================
    # QUOTE & JOB MODELS (backend/app/models/quote.py & job.py)
    # Expected: 39 fields across multiple tables
    # =====================================================

    # Table: quote (5 fields)
    op.alter_column(
        "quote",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "tax_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "currency",
        existing_type=sa.String(),
        server_default=sa.text("'USD'"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: quote_version (1 field)
    op.alter_column(
        "quote_version",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: quote_line (5 fields)
    op.alter_column(
        "quote_line",
        "quantity",
        existing_type=sa.Integer(),
        server_default=sa.text("1"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "unit_price_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: quote_public_link (2 fields)
    op.alter_column(
        "quote_public_link",
        "max_uses",
        existing_type=sa.Integer(),
        server_default=sa.text("1"),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_public_link",
        "used_count",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    # Table: quote_public_link_contact_action (1 field)
    op.alter_column(
        "quote_public_link_contact_action",
        "occurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: quote_acceptance (2 fields)
    op.alter_column(
        "quote_acceptance",
        "approved_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    op.alter_column(
        "quote_acceptance",
        "terms_acknowledged",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: job (4 fields)
    op.alter_column(
        "job",
        "actual_labor_cost_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "job",
        "actual_material_cost_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "job",
        "actual_profit_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "job",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: job_notes (1 field)
    op.alter_column(
        "job_notes",
        "customer_visible",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    # Table: tenant_markup_version (2 fields)
    op.alter_column(
        "tenant_markup_version",
        "valid_period",
        existing_type=postgresql.TSTZRANGE(),
        server_default=sa.text("tstzrange(now(), null, '[)')"),
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_markup_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: job_expense (2 fields)
    op.alter_column(
        "job_expense",
        "incurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    op.alter_column(
        "job_expense",
        "is_billable",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: job_assignment (2 fields)
    op.alter_column(
        "job_assignment",
        "is_lead",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "job_assignment",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: change_order (4 fields)
    op.alter_column(
        "change_order",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "change_order",
        "tax_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "change_order",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "change_order",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: change_order_line (5 fields)
    op.alter_column(
        "change_order_line",
        "quantity",
        existing_type=sa.Integer(),
        server_default=sa.text("1"),
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "unit_price_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # =====================================================
    # INVOICE & PAYMENT MODELS (backend/app/models/invoice.py & payment.py)
    # Expected: 16 fields across multiple tables
    # =====================================================

    # Table: invoice (6 fields)
    op.alter_column(
        "invoice",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "tax_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "balance_due_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "currency",
        existing_type=sa.String(),
        server_default=sa.text("'USD'"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: invoice_line (5 fields)
    op.alter_column(
        "invoice_line",
        "quantity",
        existing_type=sa.Integer(),
        server_default=sa.text("1"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "unit_price_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: invoice_line_tax_component (1 field - ADD NEW COLUMN)
    op.add_column(
        "invoice_line_tax_component",
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )

    # Table: payment_status (3 fields)
    op.alter_column(
        "payment_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "payment_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "payment_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: payment (1 field)
    op.alter_column(
        "payment",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # =====================================================
    # PRICING MODELS (backend/app/models/pricing.py)
    # Expected: 18 fields across multiple tables
    # =====================================================

    # Table: currency (1 field)
    op.alter_column(
        "currency",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: payment_type (1 field)
    op.alter_column(
        "payment_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: supplier_item_category (1 field)
    op.alter_column(
        "supplier_item_category",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: supplier_item_uom (2 fields)
    op.alter_column(
        "supplier_item_uom",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item_uom",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: supplier_item (1 field)
    op.alter_column(
        "supplier_item",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: supplier_item_price (2 fields)
    op.alter_column(
        "supplier_item_price",
        "currency",
        existing_type=sa.String(),
        server_default=sa.text("'USD'"),
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item_price",
        "valid_period",
        existing_type=postgresql.TSTZRANGE(),
        server_default=sa.text("tstzrange(now(), null, '[)')"),
        existing_nullable=False,
    )

    # Table: pricing_cache (1 field)
    op.alter_column(
        "pricing_cache",
        "currency",
        existing_type=sa.String(),
        server_default=sa.text("'USD'"),
        existing_nullable=False,
    )

    # Table: tax_rate_version (1 field)
    op.alter_column(
        "tax_rate_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: pricebook_item (1 field)
    op.alter_column(
        "pricebook_item",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: pricebook_item_version (1 field)
    op.alter_column(
        "pricebook_item_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: product_plan (1 field)
    op.alter_column(
        "product_plan",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: product_plan_version (1 field)
    op.alter_column(
        "product_plan_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: discount_version (1 field)
    op.alter_column(
        "discount_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: product_feature (1 field)
    op.alter_column(
        "product_feature",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: product_plan_product_feature_version (2 fields)
    op.alter_column(
        "product_plan_product_feature_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    op.alter_column(
        "product_plan_product_feature_version",
        "limit_enforcement",
        existing_type=sa.String(),
        server_default=sa.text("'block'"),
        existing_nullable=False,
    )

    # =====================================================
    # SUBSCRIPTION MODELS (backend/app/models/subscription.py)
    # Expected: 11 fields across multiple tables
    # =====================================================

    # Table: tenant_product_feature_override (1 field)
    op.alter_column(
        "tenant_product_feature_override",
        "enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: subscription_status (1 field)
    op.alter_column(
        "subscription_status",
        "is_billing_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: subscription (5 fields)
    op.alter_column(
        "subscription",
        "quantity_seats",
        existing_type=sa.Integer(),
        server_default=sa.text("1"),
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "started_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "billing_interval",
        existing_type=sa.String(),
        server_default=sa.text("'monthly'"),
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "cancel_at_period_end",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: subscription_usage (1 field)
    op.alter_column(
        "subscription_usage",
        "used_quantity",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    # Table: usage_ledger (3 fields)
    op.alter_column(
        "usage_ledger",
        "occurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    op.alter_column(
        "usage_ledger",
        "quantity",
        existing_type=sa.Integer(),
        server_default=sa.text("1"),
        existing_nullable=False,
    )

    op.alter_column(
        "usage_ledger",
        "is_reported",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    # =====================================================
    # NOTIFICATION MODELS (backend/app/models/notification.py)
    # Expected: 20 fields across multiple tables
    # =====================================================

    # Table: notification_channel (1 field)
    op.alter_column(
        "notification_channel",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: notification_type (1 field)
    op.alter_column(
        "notification_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: contact_endpoint (4 fields)
    op.alter_column(
        "contact_endpoint",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "contact_endpoint",
        "consent_status",
        existing_type=sa.String(),
        server_default=sa.text("'unknown'"),
        existing_nullable=False,
    )

    op.alter_column(
        "contact_endpoint",
        "verification_status",
        existing_type=sa.String(),
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )

    op.alter_column(
        "contact_endpoint",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: contact_notification_pref (3 fields)
    op.alter_column(
        "contact_notification_pref",
        "allow_sms",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "contact_notification_pref",
        "allow_email",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    op.alter_column(
        "contact_notification_pref",
        "is_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: tenant_notification_default (1 field)
    op.alter_column(
        "tenant_notification_default",
        "default_is_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: notification_template (1 field)
    op.alter_column(
        "notification_template",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: notification_event (1 field)
    op.alter_column(
        "notification_event",
        "occurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: notification_outbox (3 fields)
    op.alter_column(
        "notification_outbox",
        "status",
        existing_type=sa.String(),
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )

    op.alter_column(
        "notification_outbox",
        "attempt_count",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "notification_outbox",
        "priority",
        existing_type=sa.Integer(),
        server_default=sa.text("5"),
        existing_nullable=False,
    )

    # Table: notification_delivery_attempt (1 field - retryable MISSING from DB)
    op.alter_column(
        "notification_delivery_attempt",
        "attempted_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: auth_refresh_token (1 field)
    op.alter_column(
        "auth_refresh_token",
        "issued_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: sso_provider (1 field)
    op.alter_column(
        "sso_provider",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: auth_mfa_otp (1 field)
    op.alter_column(
        "auth_mfa_otp",
        "attempt_count",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    # Table: auth_password_history (1 field)
    op.alter_column(
        "auth_password_history",
        "changed_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # =====================================================
    # SECURITY & WEBHOOK MODELS (backend/app/models/security.py & webhook.py)
    # Expected: 13 fields across multiple tables
    # =====================================================

    # Table: jwk_status (2 fields)
    op.alter_column(
        "jwk_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    op.alter_column(
        "jwk_status",
        "is_signable",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    # Table: idempotency_key (2 fields)
    op.alter_column(
        "idempotency_key",
        "first_seen_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    op.alter_column(
        "idempotency_key",
        "status",
        existing_type=sa.String(),
        server_default=sa.text("'in_progress'"),
        existing_nullable=False,
    )

    # Table: webhook_endpoint (1 field)
    op.alter_column(
        "webhook_endpoint",
        "enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: webhook_event_type (1 field)
    op.alter_column(
        "webhook_event_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: webhook_event (1 field)
    op.alter_column(
        "webhook_event",
        "signature_valid",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )

    # Table: webhook_delivery_attempt (3 fields)
    op.alter_column(
        "webhook_delivery_attempt",
        "attempt_no",
        existing_type=sa.Integer(),
        server_default=sa.text("1"),
        existing_nullable=False,
    )

    op.alter_column(
        "webhook_delivery_attempt",
        "status",
        existing_type=sa.String(),
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )

    op.alter_column(
        "webhook_delivery_attempt",
        "requested_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # =====================================================
    # INTEGRATION MODELS (backend/app/models/integration.py)
    # Expected: 8 fields across multiple tables
    # =====================================================

    # Table: integration_credential (1 field)
    op.alter_column(
        "integration_credential",
        "connection_status",
        existing_type=sa.String(),
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )

    # Table: integration_sync_mapping (2 fields)
    op.alter_column(
        "integration_sync_mapping",
        "sync_preference",
        existing_type=sa.String(),
        server_default=sa.text("'aevofab_master'"),
        existing_nullable=False,
    )

    op.alter_column(
        "integration_sync_mapping",
        "last_synced_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Table: integration_sync_conflict (1 field)
    op.alter_column(
        "integration_sync_conflict",
        "status",
        existing_type=sa.String(),
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )

    # Table: integration_sync_log (2 fields)
    op.alter_column(
        "integration_sync_log",
        "records_processed",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    op.alter_column(
        "integration_sync_log",
        "records_failed",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    # =====================================================
    # CONNECTOR MODELS (backend/app/models/connector.py)
    # Expected: 6 fields across multiple tables
    # =====================================================

    # Table: connector_config (3 fields)
    op.alter_column(
        "connector_config",
        "mode",
        existing_type=sa.String(),
        server_default=sa.text("'api'"),
        existing_nullable=False,
    )

    op.alter_column(
        "connector_config",
        "enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    op.alter_column(
        "connector_config",
        "failure_count",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    # Table: connector_run_log (3 fields)
    op.alter_column(
        "connector_run_log",
        "started_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    op.alter_column(
        "connector_run_log",
        "status",
        existing_type=sa.String(),
        server_default=sa.text("'running'"),
        existing_nullable=False,
    )

    op.alter_column(
        "connector_run_log",
        "items_fetched",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )

    # =====================================================
    # VOICE AI MODELS (backend/app/models/voice.py)
    # Expected: 3 fields across multiple tables
    # =====================================================

    # Table: conversation_session (2 fields)
    op.alter_column(
        "conversation_session",
        "status",
        existing_type=sa.String(),
        server_default=sa.text("'active'"),
        existing_nullable=False,
    )

    op.alter_column(
        "conversation_session",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    # Table: voice_command_log (1 field)
    op.alter_column(
        "voice_command_log",
        "is_successful",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Reverse order from upgrade for safety

    # VOICE AI MODELS - ROLLBACK
    op.alter_column(
        "voice_command_log",
        "is_successful",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "conversation_session",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "conversation_session",
        "status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    # CONNECTOR MODELS - ROLLBACK
    op.alter_column(
        "connector_run_log",
        "items_fetched",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "connector_run_log",
        "status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "connector_run_log",
        "started_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "connector_config",
        "failure_count",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "connector_config",
        "enabled",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "connector_config",
        "mode",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    # INTEGRATION MODELS - ROLLBACK
    op.alter_column(
        "integration_sync_log",
        "records_failed",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "integration_sync_log",
        "records_processed",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "integration_sync_conflict",
        "status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "integration_sync_mapping",
        "last_synced_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "integration_sync_mapping",
        "sync_preference",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "integration_credential",
        "connection_status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    # SECURITY & WEBHOOK MODELS - ROLLBACK
    op.alter_column(
        "webhook_delivery_attempt",
        "requested_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "webhook_delivery_attempt",
        "status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "webhook_delivery_attempt",
        "attempt_no",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "webhook_event",
        "signature_valid",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "webhook_event_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "webhook_endpoint",
        "enabled",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "idempotency_key",
        "status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "idempotency_key",
        "first_seen_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "jwk_status",
        "is_signable",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "jwk_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    # NOTIFICATION MODELS - ROLLBACK
    op.alter_column(
        "auth_password_history",
        "changed_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "auth_mfa_otp",
        "attempt_count",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "sso_provider",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "auth_refresh_token",
        "issued_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_delivery_attempt",
        "attempted_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_outbox",
        "priority",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_outbox",
        "attempt_count",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_outbox",
        "status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_event",
        "occurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_template",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_notification_default",
        "default_is_enabled",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_notification_pref",
        "is_enabled",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_notification_pref",
        "allow_email",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_notification_pref",
        "allow_sms",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_endpoint",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_endpoint",
        "verification_status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_endpoint",
        "consent_status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_endpoint",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "notification_channel",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    # SUBSCRIPTION MODELS - ROLLBACK
    op.alter_column(
        "usage_ledger",
        "is_reported",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "usage_ledger",
        "quantity",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "usage_ledger",
        "occurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "subscription_usage",
        "used_quantity",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "cancel_at_period_end",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "billing_interval",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "started_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "subscription",
        "quantity_seats",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "subscription_status",
        "is_billing_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_product_feature_override",
        "enabled",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    # PRICING MODELS - ROLLBACK
    op.alter_column(
        "product_plan_product_feature_version",
        "limit_enforcement",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "product_plan_product_feature_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "product_feature",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "discount_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "product_plan_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "product_plan",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "pricebook_item_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "pricebook_item",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tax_rate_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "pricing_cache",
        "currency",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item_price",
        "valid_period",
        existing_type=postgresql.TSTZRANGE(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item_price",
        "currency",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item_uom",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item_uom",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_item_category",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "payment_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "currency",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    # INVOICE & PAYMENT MODELS - ROLLBACK
    op.alter_column(
        "payment",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "payment_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "payment_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "payment_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.drop_column("invoice_line_tax_component", "is_active")

    op.alter_column(
        "invoice_line",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "unit_price_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_line",
        "quantity",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "currency",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "balance_due_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "tax_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    # QUOTE & JOB MODELS - ROLLBACK
    op.alter_column(
        "change_order_line",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "unit_price_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order_line",
        "quantity",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order",
        "tax_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "change_order",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_assignment",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_assignment",
        "is_lead",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_expense",
        "is_billable",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_expense",
        "incurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_markup_version",
        "recorded_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_markup_version",
        "valid_period",
        existing_type=postgresql.TSTZRANGE(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_notes",
        "customer_visible",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job",
        "actual_profit_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job",
        "actual_material_cost_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job",
        "actual_labor_cost_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_acceptance",
        "terms_acknowledged",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_acceptance",
        "approved_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_public_link_contact_action",
        "occurred_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_public_link",
        "used_count",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_public_link",
        "max_uses",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "unit_price_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_line",
        "quantity",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_version",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "currency",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "total_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "tax_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote",
        "subtotal_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    # REFERENCE DATA MODELS - ROLLBACK
    op.alter_column(
        "invoice_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "invoice_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_expense_category",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_expense_category",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "qpl_contact_action_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "qpl_contact_action_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_link_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_link_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "taxability_code",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "qco_line_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "qco_line_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "entity_address",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "entity_address",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "address_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "address_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "entity_contact",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact_type",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "entity_type",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "job_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "quote_status",
        "is_terminal",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_lifecycle_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier_lifecycle_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "site_lifecycle_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "site_lifecycle_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "customer_lifecycle_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "customer_lifecycle_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    # TENANT USER MODELS - ROLLBACK
    op.alter_column(
        "tenant_user_notification_pref",
        "is_enabled",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_notification_pref",
        "allow_email",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_notification_pref",
        "allow_in_app",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_domain",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_invite",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_status",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_status",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_role",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_role",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_user_role",
        "permissions",
        existing_type=postgresql.JSONB(),
        server_default=None,
        existing_nullable=False,
    )

    # AUTH MODELS - ROLLBACK
    op.alter_column(
        "user_preference",
        "preferences",
        existing_type=postgresql.JSONB(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user_endpoint",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user_endpoint",
        "consent_status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user_endpoint",
        "verification_status",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user_endpoint",
        "is_primary",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "preferred_mfa_channel",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "mfa_enforced",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "require_password_reset",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "failed_login_count",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "user",
        "is_platform_user",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "platform_role",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "platform_role",
        "is_default",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "platform_role",
        "permissions",
        existing_type=postgresql.JSONB(),
        server_default=None,
        existing_nullable=False,
    )

    # CORE MODELS - ROLLBACK
    op.alter_column(
        "address",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "address",
        "country",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "contact",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "app_service",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "app_service_provider",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "app_service_category",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "supplier",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "site",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "customer",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "customer",
        "type",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_settings",
        "default_invoice_terms_days",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_settings",
        "default_quote_validity_days",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_settings",
        "default_billable_labor_rate_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant_settings",
        "default_labor_rate_cents",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "tenant",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )
