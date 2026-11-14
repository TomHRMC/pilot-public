"""add_missing_check_constraints_task9

Revision ID: b78d2b0199e8
Revises: d7836dee815d
Create Date: 2026-04-01 12:30:07.487826+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b78d2b0199e8"
down_revision: str | None = "d7836dee815d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Task 9: Add missing CHECK constraints for data validation
    # 1. Email format validation - user table
    op.create_check_constraint(
        "user_email_format_chk",
        "user",
        "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    )

    # 2. Email format validation - user_endpoint table (conditional on channel)
    op.create_check_constraint(
        "user_endpoint_email_format_chk",
        "user_endpoint",
        "channel != 'email' OR value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    )

    # 3. Customer type enumeration
    op.create_check_constraint(
        "customer_type_chk", "customer", "type IN ('person', 'company')"
    )

    # 4. MFA channel validation
    op.create_check_constraint(
        "auth_mfa_otp_channel_chk", "auth_mfa_otp", "channel IN ('email', 'sms')"
    )

    # 5. Platform role validation (nullable)
    op.create_check_constraint(
        "user_platform_role_chk",
        "user",
        "platform_role_code IS NULL OR platform_role_code IN ('staff', 'superadmin')",
    )

    # 6. Notification outbox status enumeration
    op.create_check_constraint(
        "notification_outbox_status_chk",
        "notification_outbox",
        "status IN ('pending', 'sent', 'failed', 'cancelled')",
    )

    # 7. Webhook delivery attempt status enumeration
    op.create_check_constraint(
        "webhook_delivery_attempt_status_chk",
        "webhook_delivery_attempt",
        "status IN ('pending', 'delivered', 'failed', 'retrying')",
    )

    # 8. Integration sync conflict status enumeration
    op.create_check_constraint(
        "integration_sync_conflict_status_chk",
        "integration_sync_conflict",
        "status IN ('pending', 'resolved_keep_internal', 'resolved_keep_external')",
    )

    # 9. Connector run log status enumeration
    op.create_check_constraint(
        "connector_run_log_status_chk",
        "connector_run_log",
        "status IN ('running', 'completed', 'failed', 'cancelled')",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # Task 9: Drop CHECK constraints in reverse order
    op.drop_constraint(
        "connector_run_log_status_chk", "connector_run_log", type_="check"
    )
    op.drop_constraint(
        "integration_sync_conflict_status_chk",
        "integration_sync_conflict",
        type_="check",
    )
    op.drop_constraint(
        "webhook_delivery_attempt_status_chk", "webhook_delivery_attempt", type_="check"
    )
    op.drop_constraint(
        "notification_outbox_status_chk", "notification_outbox", type_="check"
    )
    op.drop_constraint("user_platform_role_chk", "user", type_="check")
    op.drop_constraint("auth_mfa_otp_channel_chk", "auth_mfa_otp", type_="check")
    op.drop_constraint("customer_type_chk", "customer", type_="check")
    op.drop_constraint("user_endpoint_email_format_chk", "user_endpoint", type_="check")
    op.drop_constraint("user_email_format_chk", "user", type_="check")
