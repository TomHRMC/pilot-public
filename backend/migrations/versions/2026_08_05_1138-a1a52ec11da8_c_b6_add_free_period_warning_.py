"""c_b6_add_free_period_warning_notification_type

Revision ID: a1a52ec11da8
Revises: e18834169e23
Create Date: 2026-08-05 11:38:42.973219+00:00

C-B6: Adds the `free_period_warning` notification_type + 3 platform-level
notification_template rows (email/push/in_app) for the Charter free-period
notification schedule. Also adds the `tenant` entity_type row required by
NotificationEvent.entity_type_code (FK) for free-period events.

All inserts are idempotent (ON CONFLICT DO NOTHING) and wrapped in
SET LOCAL session_replication_role = 'replica' to bypass triggers.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1a52ec11da8"
down_revision: str | None = "e18834169e23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Add `tenant` entity_type (required FK target for NotificationEvent.entity_type_code)
    op.execute(
        sa.text(
            """
            INSERT INTO public.entity_type (code, name, is_active, is_default, created_at, updated_at)
            VALUES ('tenant', 'Tenant', true, false, NOW(), NOW())
            ON CONFLICT (code) DO NOTHING
            """
        )
    )

    # 2. Add `free_period_warning` notification_type (platform-level, tenant_id IS NULL)
    op.execute(
        sa.text(
            """
            INSERT INTO public.notification_type
                (code, tenant_id, audience, name, description, is_active, created_at, updated_at)
            VALUES
                ('free_period_warning', NULL, 'tenant', 'Free Period Warning',
                 'Fired on the Charter free-period notification schedule (T-30/14/7/3/1/0)',
                 true, NOW(), NOW())
            ON CONFLICT (code) DO NOTHING
            """
        )
    )

    # 3. Add 3 platform-level notification_template rows (email/push/in_app)
    #    Body copy uses {expiry_date} placeholder rendered by the dispatch helper.
    op.execute(
        sa.text(
            """
            INSERT INTO public.notification_template
                (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active, created_at, updated_at)
            VALUES
                (gen_random_uuid(), NULL, 'free_period_warning', 'email', 'en',
                 'Your Pilot free period ends soon',
                 'Your Pilot for Trades free period ends on {expiry_date}. Add a payment method in Settings → Subscription & Billing to keep your account running past that date.',
                 true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO public.notification_template
                (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active, created_at, updated_at)
            VALUES
                (gen_random_uuid(), NULL, 'free_period_warning', 'push', 'en',
                 'Your Pilot free period ends soon',
                 'Free period ends {expiry_date}. Add a payment method to avoid interruption.',
                 true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO public.notification_template
                (id, tenant_id, notification_type_code, channel, locale, subject, body, is_active, created_at, updated_at)
            VALUES
                (gen_random_uuid(), NULL, 'free_period_warning', 'in_app', 'en',
                 'Your Pilot free period ends soon',
                 'Your free period ends on {expiry_date}. Add a payment method to keep your account running.',
                 true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        )
    )

    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute(
        sa.text(
            "DELETE FROM public.notification_template "
            "WHERE notification_type_code = 'free_period_warning' AND tenant_id IS NULL;"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM public.notification_type "
            "WHERE code = 'free_period_warning' AND tenant_id IS NULL;"
        )
    )
    # NOTE: `tenant` entity_type is intentionally NOT removed in downgrade.
    # It is a generic lookup row that may be referenced by other notification_event
    # rows; removing it would violate the FK if any such rows exist.
    op.execute("SET LOCAL session_replication_role = 'origin';")
