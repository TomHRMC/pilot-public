"""sd4_user_endpoint_channel_chk_add_in_app_push

SD-4: Extend user_endpoint_channel_chk to allow 'in_app' and 'push' channels
in addition to the existing 'email' and 'sms' values. Required so the seed
script can insert in_app + push notification endpoints for dev/test users.

Revision ID: aaaa1f8d5138
Revises: d6eec0f5f8c9
Create Date: 2026-07-14 20:16:05

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "aaaa1f8d5138"
down_revision = "d6eec0f5f8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraint (email + sms only)
    op.drop_constraint(
        "user_endpoint_channel_chk",
        "user_endpoint",
        type_="check",
    )
    # Add new constraint (email + sms + in_app + push)
    op.create_check_constraint(
        "user_endpoint_channel_chk",
        "user_endpoint",
        "channel::text = ANY (ARRAY['email'::text, 'sms'::text, 'in_app'::text, 'push'::text])",
    )


def downgrade() -> None:
    # Restore original constraint (email + sms only)
    # NOTE: rows with channel='in_app' or channel='push' must be deleted first
    op.drop_constraint(
        "user_endpoint_channel_chk",
        "user_endpoint",
        type_="check",
    )
    op.create_check_constraint(
        "user_endpoint_channel_chk",
        "user_endpoint",
        "channel::text = ANY (ARRAY['email'::text, 'sms'::text])",
    )
