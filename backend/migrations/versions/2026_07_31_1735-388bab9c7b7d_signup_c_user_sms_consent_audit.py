"""signup_c_user_sms_consent_audit

Revision ID: 388bab9c7b7d
Revises: 990231f963b0
Create Date: 2026-07-31 17:35:37.094870+00:00

SIGNUP-C / Pathway C: Create ``user_sms_consent_audit`` — the append-only TCPA
consent trail for Pilot→owner platform SMS notifications (account, billing &
security alerts). Mirrors ``customer_sms_consent_audit`` (DLC-1) for the owner
surface.

Design: dev-docs/architecture-design/batch-designs/batch-signup-c-design.md §B.

MCP-verified pre-state (2026-07-31):
  - ``user_sms_consent_audit`` does NOT exist.
  - Mirror source ``customer_sms_consent_audit`` has NO database triggers —
    append-only immutability is enforced at the ORM layer via AppendOnlyMixin.
    This migration adds NO triggers (matches the established pattern).
  - Mirror source action CHECK values: attested / double_opt_in_sent /
    double_opt_in_confirmed / opted_out — reused verbatim.
  - Mirror source FKs are all ON DELETE RESTRICT — reused verbatim.

upgrade(): create the table + indexes + CHECK + FKs.
downgrade(): drop the table (cascades indexes/constraints).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "388bab9c7b7d"
down_revision: str | None = "990231f963b0"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "user_sms_consent_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_endpoint_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("consent_text_hash", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column(
            "attested_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "action IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out')",
            name="user_sms_consent_audit_action_chk",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="user_sms_consent_audit_created_by_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="RESTRICT",
            name="user_sms_consent_audit_tenant_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_endpoint_id"],
            ["user_endpoint.id"],
            ondelete="RESTRICT",
            name="user_sms_consent_audit_user_endpoint_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            ondelete="RESTRICT",
            name="user_sms_consent_audit_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="user_sms_consent_audit_pkey"),
    )
    # Tenant-scoped + user-scoped lookups (mirrors the indexed FKs on the
    # customer_sms_consent_audit source table).
    op.create_index(
        "ix_user_sms_consent_audit_tenant_id",
        "user_sms_consent_audit",
        ["tenant_id"],
    )
    op.create_index(
        "ix_user_sms_consent_audit_user_id",
        "user_sms_consent_audit",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_sms_consent_audit_user_id",
        table_name="user_sms_consent_audit",
    )
    op.drop_index(
        "ix_user_sms_consent_audit_tenant_id",
        table_name="user_sms_consent_audit",
    )
    op.drop_table("user_sms_consent_audit")
