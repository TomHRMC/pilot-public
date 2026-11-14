"""dlc_b4_sms_brand_prefix

DLC-B4: Prefix all system SMS communication templates with "Pilot for Trades: "
so the platform is the perceived sender per 10DLC campaign CXXXXXX resubmission
requirement (Telnyx rejection fix, 2026-07-27).

Scope:
  - channel = 'sms'
  - tenant_id IS NULL  (system/platform templates only; never touches tenant overrides)
  - Idempotent: NOT LIKE guard prevents double-prefix on re-run

Also adds the missing 'recurring_job_scheduled' SMS template row (present in DB
from seed but absent from seed_core.py COMMUNICATION_TEMPLATE_ROWS — fixed in
seed_core.py as part of this batch).

Revision ID: 3131f106f1b9
Revises: dc2e62a12b1e
Create Date: 2026-07-27 18:22:25.297204+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3131f106f1b9"
down_revision: str | None = "dc2e62a12b1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    # SET LOCAL so the change is scoped to this transaction only.
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Prefix all system SMS templates.
    # NOT LIKE guard makes this idempotent — re-running upgrade never double-prefixes.
    op.execute("""
        UPDATE public.communication_template
        SET body_template = 'Pilot for Trades: ' || body_template
        WHERE channel = 'sms'
          AND tenant_id IS NULL
          AND body_template NOT LIKE 'Pilot for Trades:%';
    """)

    # Insert the missing 'recurring_job_scheduled' SMS system template if not present.
    # This row exists in the live DB (seeded previously) but was absent from
    # seed_core.py COMMUNICATION_TEMPLATE_ROWS — backfilled here for prod safety.
    op.execute(f"""
        INSERT INTO public.communication_template (
            id, tenant_id, template_code, channel,
            subject, body_template, is_active,
            created_at, updated_at, created_by, updated_by
        )
        SELECT
            gen_random_uuid(),
            NULL,
            'recurring_job_scheduled',
            'sms',
            NULL,
            'Pilot for Trades: Hi {{{{customer_name}}}}, your scheduled {{{{service_description}}}} with {{{{company_name}}}} is confirmed for {{{{scheduled_date}}}} at {{{{scheduled_time}}}}. Reply STOP to opt out.',
            true,
            now(), now(),
            '{_SYSTEM_USER_ID}'::uuid,
            '{_SYSTEM_USER_ID}'::uuid
        WHERE NOT EXISTS (
            SELECT 1 FROM public.communication_template
            WHERE template_code = 'recurring_job_scheduled'
              AND channel = 'sms'
              AND tenant_id IS NULL
        );
    """)


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Strip the prefix from all system SMS templates where it is present.
    op.execute("""
        UPDATE public.communication_template
        SET body_template = substring(body_template FROM length('Pilot for Trades: ') + 1)
        WHERE channel = 'sms'
          AND tenant_id IS NULL
          AND body_template LIKE 'Pilot for Trades:%';
    """)
