"""phase_8_0_batch_1_indexes_tenant_auth_user

Revision ID: 522c3ca3cc9e
Revises: 760e6045deb0
Create Date: 2026-04-15 21:43:47.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "522c3ca3cc9e"
down_revision: str | None = "760e6045deb0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- user ---
    op.create_index("ix_user_platform_role_code", "user", ["platform_role_code"])

    # --- user_preference ---
    op.create_index("ix_user_preference_tenant_id", "user_preference", ["tenant_id"])

    # --- tenant_user ---
    op.create_index("ix_tenant_user_role_code", "tenant_user", ["role_code"])
    op.create_index("ix_tenant_user_status_id", "tenant_user", ["status_id"])
    op.create_index("ix_tenant_user_suspended_by", "tenant_user", ["suspended_by"])

    # --- tenant_user_invite ---
    op.create_index(
        "ix_tenant_user_invite_invited_by", "tenant_user_invite", ["invited_by"]
    )

    # --- password_policy ---
    op.create_index("ix_password_policy_tenant_id", "password_policy", ["tenant_id"])

    # --- auth_refresh_token ---
    op.create_index(
        "ix_auth_refresh_token_tenant_id", "auth_refresh_token", ["tenant_id"]
    )
    op.create_index("ix_auth_refresh_token_user_id", "auth_refresh_token", ["user_id"])

    # --- auth_password_reset ---
    op.create_index(
        "ix_auth_password_reset_user_id", "auth_password_reset", ["user_id"]
    )
    op.create_index(
        "ix_auth_password_reset_contact_id", "auth_password_reset", ["contact_id"]
    )

    # --- auth_email_verification ---
    op.create_index(
        "ix_auth_email_verification_user_id", "auth_email_verification", ["user_id"]
    )
    op.create_index(
        "ix_auth_email_verification_contact_id",
        "auth_email_verification",
        ["contact_id"],
    )

    # --- auth_mfa_otp ---
    op.create_index("ix_auth_mfa_otp_user_id", "auth_mfa_otp", ["user_id"])
    op.create_index("ix_auth_mfa_otp_contact_id", "auth_mfa_otp", ["contact_id"])
    op.create_index(
        "ix_auth_mfa_otp_user_endpoint_id", "auth_mfa_otp", ["user_endpoint_id"]
    )

    # --- auth_password_history ---
    op.create_index(
        "ix_auth_password_history_user_id", "auth_password_history", ["user_id"]
    )
    op.create_index(
        "ix_auth_password_history_contact_id", "auth_password_history", ["contact_id"]
    )

    # --- auth_api_token ---
    op.create_index("ix_auth_api_token_tenant_id", "auth_api_token", ["tenant_id"])
    op.create_index("ix_auth_api_token_user_id", "auth_api_token", ["user_id"])

    # --- auth_jwk ---
    op.create_index("ix_auth_jwk_tenant_id", "auth_jwk", ["tenant_id"])
    op.create_index("ix_auth_jwk_jwk_status_id", "auth_jwk", ["jwk_status_id"])

    # --- idempotency_key ---
    op.create_index("ix_idempotency_key_tenant_id", "idempotency_key", ["tenant_id"])
    op.create_index("ix_idempotency_key_user_id", "idempotency_key", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_platform_role_code", table_name="user")
    op.drop_index("ix_user_preference_tenant_id", table_name="user_preference")
    op.drop_index("ix_tenant_user_role_code", table_name="tenant_user")
    op.drop_index("ix_tenant_user_status_id", table_name="tenant_user")
    op.drop_index("ix_tenant_user_suspended_by", table_name="tenant_user")
    op.drop_index("ix_tenant_user_invite_invited_by", table_name="tenant_user_invite")
    op.drop_index("ix_password_policy_tenant_id", table_name="password_policy")
    op.drop_index("ix_auth_refresh_token_tenant_id", table_name="auth_refresh_token")
    op.drop_index("ix_auth_refresh_token_user_id", table_name="auth_refresh_token")
    op.drop_index("ix_auth_password_reset_user_id", table_name="auth_password_reset")
    op.drop_index("ix_auth_password_reset_contact_id", table_name="auth_password_reset")
    op.drop_index(
        "ix_auth_email_verification_user_id", table_name="auth_email_verification"
    )
    op.drop_index(
        "ix_auth_email_verification_contact_id", table_name="auth_email_verification"
    )
    op.drop_index("ix_auth_mfa_otp_user_id", table_name="auth_mfa_otp")
    op.drop_index("ix_auth_mfa_otp_contact_id", table_name="auth_mfa_otp")
    op.drop_index("ix_auth_mfa_otp_user_endpoint_id", table_name="auth_mfa_otp")
    op.drop_index(
        "ix_auth_password_history_user_id", table_name="auth_password_history"
    )
    op.drop_index(
        "ix_auth_password_history_contact_id", table_name="auth_password_history"
    )
    op.drop_index("ix_auth_api_token_tenant_id", table_name="auth_api_token")
    op.drop_index("ix_auth_api_token_user_id", table_name="auth_api_token")
    op.drop_index("ix_auth_jwk_tenant_id", table_name="auth_jwk")
    op.drop_index("ix_auth_jwk_jwk_status_id", table_name="auth_jwk")
    op.drop_index("ix_idempotency_key_tenant_id", table_name="idempotency_key")
    op.drop_index("ix_idempotency_key_user_id", table_name="idempotency_key")
