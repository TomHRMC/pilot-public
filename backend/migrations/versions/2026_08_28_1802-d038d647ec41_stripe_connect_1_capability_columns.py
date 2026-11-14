"""stripe_connect_1_capability_columns

STRIPE-CONNECT-1 — Tenant Stripe Connect capability columns + notification
types/templates for disconnect + dispute owner notifications.

DDL: two nullable BOOLEAN columns on ``tenant``:
  - stripe_connect_charges_enabled
  - stripe_connect_payouts_enabled
These persist the connected-account capability state locally so the public
invoice hot path (``GET /public/invoices/{token}``) can render the
``card_payments_enabled`` / ``payment_unavailable_reason`` fields without a
live Stripe call. The 402 guard on the POST remains the hard backstop.

Data (idempotent, ``SET LOCAL session_replication_role = 'replica'``):
  - 2 ``notification_type`` rows: ``stripe_connect_disconnected``,
    ``stripe_dispute_opened`` (``ON CONFLICT DO NOTHING``).
  - 6 ``notification_template`` rows (2 types × email/in_app/push,
    ``tenant_id NULL``, ``WHERE NOT EXISTS``-guarded) — byte-identical to
    ``seed_platform.py`` (design §F.4).
  - Backfill: ``UPDATE tenant SET … = true, true WHERE
    stripe_connect_account_id IS NOT NULL`` (safe default — the first
    ``account.updated`` / ``/status`` refresh corrects any false positive;
    design §G Q3). No-op in dev today (0 connected tenants).

See: dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md §B

Revision ID: d038d647ec41
Revises: b1f8b5f00f33
Create Date: 2026-08-28 18:02:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d038d647ec41"
down_revision = "b1f8b5f00f33"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────────────────
# Notification template copy — byte-identical to seed_platform.py (design §F.4)
# ─────────────────────────────────────────────────────────────────────────────

# stripe_connect_disconnected
_DISCONNECT_EMAIL_SUBJECT = "[Payments] Stripe account disconnected"
_DISCONNECT_EMAIL_BODY = (
    "Your Stripe Connect account for {{tenant_name}} has been disconnected. "
    "Card payments on invoice links are paused, and customers now see "
    "manual-payment instructions. Reconnect in Settings → Payment Method."
)
_DISCONNECT_INAPP_SUBJECT = _DISCONNECT_EMAIL_SUBJECT
_DISCONNECT_INAPP_BODY = (
    "Stripe account disconnected for {{tenant_name}}. "
    "Card payments paused — reconnect in Settings → Payment Method."
)
_DISCONNECT_PUSH_SUBJECT = _DISCONNECT_EMAIL_SUBJECT
_DISCONNECT_PUSH_BODY = "Stripe disconnected — card payments paused. Tap to reconnect."

# stripe_dispute_opened
_DISPUTE_EMAIL_SUBJECT = "[Payments] A customer disputed a payment"
_DISPUTE_EMAIL_BODY = (
    "A customer has disputed a payment of {{amount}} on invoice "
    "{{invoice_link}}. The dispute respond-by date is {{respond_by}}. "
    "Respond in your Stripe dashboard — Pilot does not handle dispute "
    "resolution in-app."
)
_DISPUTE_INAPP_SUBJECT = _DISPUTE_EMAIL_SUBJECT
_DISPUTE_INAPP_BODY = (
    "A customer disputed a payment of {{amount}} on invoice "
    "{{invoice_link}}. Respond by {{respond_by}} in your Stripe dashboard."
)
_DISPUTE_PUSH_SUBJECT = _DISPUTE_EMAIL_SUBJECT
_DISPUTE_PUSH_BODY = (
    "Payment disputed ({{amount}}). Respond in your Stripe dashboard by {{respond_by}}."
)


def upgrade() -> None:
    # ── DDL: two nullable BOOLEAN columns on tenant ──────────────────────────
    op.execute(
        "ALTER TABLE tenant ADD COLUMN IF NOT EXISTS "
        "stripe_connect_charges_enabled BOOLEAN NULL;"
    )
    op.execute(
        "ALTER TABLE tenant ADD COLUMN IF NOT EXISTS "
        "stripe_connect_payouts_enabled BOOLEAN NULL;"
    )

    # ── Data: notification types + templates (idempotent) ────────────────────
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. notification_type: stripe_connect_disconnected (code PK) — idempotent
    op.execute(
        """
        INSERT INTO notification_type
            (code, name, audience, is_active, created_at, updated_at)
        VALUES
            ('stripe_connect_disconnected', 'Stripe Connect Disconnected',
             'tenant', true, now(), now())
        ON CONFLICT DO NOTHING;
        """
    )

    # 2. notification_type: stripe_dispute_opened (code PK) — idempotent
    op.execute(
        """
        INSERT INTO notification_type
            (code, name, audience, is_active, created_at, updated_at)
        VALUES
            ('stripe_dispute_opened', 'Stripe Dispute Opened',
             'tenant', true, now(), now())
        ON CONFLICT DO NOTHING;
        """
    )

    # 3. Six notification_template rows (2 types × email/in_app/push,
    #    tenant_id NULL, locale 'en') — each guarded by WHERE NOT EXISTS.
    _insert_template(
        "stripe_connect_disconnected",
        "email",
        _DISCONNECT_EMAIL_SUBJECT,
        _DISCONNECT_EMAIL_BODY,
    )
    _insert_template(
        "stripe_connect_disconnected",
        "in_app",
        _DISCONNECT_INAPP_SUBJECT,
        _DISCONNECT_INAPP_BODY,
    )
    _insert_template(
        "stripe_connect_disconnected",
        "push",
        _DISCONNECT_PUSH_SUBJECT,
        _DISCONNECT_PUSH_BODY,
    )
    _insert_template(
        "stripe_dispute_opened",
        "email",
        _DISPUTE_EMAIL_SUBJECT,
        _DISPUTE_EMAIL_BODY,
    )
    _insert_template(
        "stripe_dispute_opened",
        "in_app",
        _DISPUTE_INAPP_SUBJECT,
        _DISPUTE_INAPP_BODY,
    )
    _insert_template(
        "stripe_dispute_opened",
        "push",
        _DISPUTE_PUSH_SUBJECT,
        _DISPUTE_PUSH_BODY,
    )

    # 4. Backfill: existing connected tenants get true/true (safe default —
    #    corrected by the first account.updated / /status refresh; design §G Q3).
    op.execute(
        """
        UPDATE tenant
        SET stripe_connect_charges_enabled = true,
            stripe_connect_payouts_enabled = true,
            updated_at = now()
        WHERE stripe_connect_account_id IS NOT NULL
          AND stripe_connect_charges_enabled IS NULL;
        """
    )


def _insert_template(type_code: str, channel: str, subject: str, body: str) -> None:
    """Insert a notification_template row, idempotent on the natural key."""
    op.execute(
        f"""
        INSERT INTO notification_template
            (id, tenant_id, notification_type_code, channel, locale,
             subject, body, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), NULL, '{type_code}',
               '{channel}', 'en',
               '{_esc(subject)}', '{_esc(body)}', true, now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM notification_template
            WHERE notification_type_code = '{type_code}'
              AND channel = '{channel}'
              AND locale = 'en'
              AND tenant_id IS NULL
        );
        """
    )


def _esc(s: str) -> str:
    """Escape single quotes for safe embedding in SQL string literals."""
    return s.replace("'", "''")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Reverse 3: delete the 6 templates (value-scoped — 2 type codes only)
    op.execute(
        """
        DELETE FROM notification_template
        WHERE notification_type_code IN
              ('stripe_connect_disconnected', 'stripe_dispute_opened')
          AND tenant_id IS NULL;
        """
    )

    # Reverse 1+2: delete the 2 notification_type rows (value-scoped)
    op.execute(
        """
        DELETE FROM notification_type
        WHERE code IN ('stripe_connect_disconnected', 'stripe_dispute_opened');
        """
    )

    # Reverse DDL: drop both columns
    op.execute(
        "ALTER TABLE tenant DROP COLUMN IF EXISTS stripe_connect_payouts_enabled;"
    )
    op.execute(
        "ALTER TABLE tenant DROP COLUMN IF EXISTS stripe_connect_charges_enabled;"
    )
