"""sd08_update_email_and_notification_template_copy

Revision ID: 4a2fbda323db
Revises: fb896203a21a
Create Date: 2026-07-06 22:04:45.000000

SD-08: Replace stub email_template copy (5 customer-facing templates) and
       placeholder notification_template body strings (9 rows) with approved v1 copy.

No schema changes — data migration only.

email_template column names (MCP-verified 2026-07-06):
  template_id (PK text), subject_template, body_html_template, body_plain_template,
  variables (jsonb), is_active, created_at, updated_at

notification_template column names (MCP-verified 2026-07-06):
  id (UUID), notification_type_code, channel, locale, subject, body, is_active,
  created_at, updated_at
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "4a2fbda323db"
down_revision: str = "fb896203a21a"
branch_labels = None
depends_on = None

# ── Approved email template copy (SD-08) ─────────────────────────────────────

_INVOICE_SENT_SUBJECT = (
    "Invoice from {{company_name}} \u2014 ${{invoice_total}} due {{due_date}}"
)
_INVOICE_SENT_HTML = (
    "<p>Hi {{customer_name}},</p>\n\n"
    "<p>Your invoice from <strong>{{company_name}}</strong> is ready to view and pay online.</p>\n\n"
    '<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">\n'
    "  <tr>\n"
    '    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Invoice total</td>\n'
    '    <td style="padding:8px 0;font-weight:600;text-align:right;">${{invoice_total}}</td>\n'
    "  </tr>\n"
    "  <tr>\n"
    '    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Due date</td>\n'
    '    <td style="padding:8px 0;text-align:right;">{{due_date}}</td>\n'
    "  </tr>\n"
    "</table>\n\n"
    '<p style="margin:24px 0;">\n'
    '  <a href="{{invoice_url}}" style="background:#2563eb;color:#ffffff;padding:12px 24px;'
    'border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Pay Invoice \u2192</a>\n'
    "</p>\n\n"
    '<p style="color:#6b7280;font-size:13px;">You can pay securely online by credit card or bank transfer. '
    "No account required.</p>\n\n"
    '<p style="color:#6b7280;font-size:13px;">Questions? Reply to this email or contact us at '
    '<a href="mailto:support@{{company_domain}}">support@{{company_domain}}</a>.</p>\n\n'
    "<p>Thank you,<br><strong>{{company_name}}</strong></p>\n\n"
    '<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email \u2014 '
    "contact support@pilotfortrades.com for help.</p>"
)
_INVOICE_SENT_PLAIN = (
    "Hi {{customer_name}},\n\n"
    "Your invoice from {{company_name}} is ready.\n\n"
    "Invoice total: ${{invoice_total}}\n"
    "Due date: {{due_date}}\n\n"
    "Pay online: {{invoice_url}}\n\n"
    "You can pay securely by credit card or bank transfer. No account required.\n\n"
    "Questions? Contact us at support@{{company_domain}}.\n\n"
    "Thank you,\n{{company_name}}"
)
_INVOICE_SENT_VARS = '["customer_name","company_name","invoice_total","invoice_url","due_date","company_domain"]'

_QUOTE_SENT_SUBJECT = "Your quote from {{company_name}} \u2014 ${{quote_total}}"
_QUOTE_SENT_HTML = (
    "<p>Hi {{customer_name}},</p>\n\n"
    "<p><strong>{{company_name}}</strong> has sent you a quote for your review.</p>\n\n"
    '<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">\n'
    "  <tr>\n"
    '    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Quote total</td>\n'
    '    <td style="padding:8px 0;font-weight:600;text-align:right;">${{quote_total}}</td>\n'
    "  </tr>\n"
    "</table>\n\n"
    '<p style="margin:24px 0;">\n'
    '  <a href="{{quote_url}}" style="background:#2563eb;color:#ffffff;padding:12px 24px;'
    'border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Review Your Quote \u2192</a>\n'
    "</p>\n\n"
    '<p style="color:#6b7280;font-size:13px;">You can review the full details, ask questions, '
    "and accept or decline online. No account required.</p>\n\n"
    "<p>Thank you for considering us,<br><strong>{{company_name}}</strong></p>\n\n"
    '<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email \u2014 '
    "contact support@pilotfortrades.com for help.</p>"
)
_QUOTE_SENT_PLAIN = (
    "Hi {{customer_name}},\n\n"
    "{{company_name}} has sent you a quote for your review.\n\n"
    "Quote total: ${{quote_total}}\n\n"
    "Review your quote online: {{quote_url}}\n\n"
    "You can review the full details, ask questions, and accept or decline. No account required.\n\n"
    "Thank you,\n{{company_name}}"
)
_QUOTE_SENT_VARS = '["customer_name","company_name","quote_total","quote_url"]'

_PAYMENT_RECEIVED_SUBJECT = (
    "Payment confirmed \u2014 ${{amount}} received by {{company_name}}"
)
_PAYMENT_RECEIVED_HTML = (
    "<p>Hi {{customer_name}},</p>\n\n"
    "<p>We\u2019ve received your payment. Here\u2019s your receipt.</p>\n\n"
    '<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">\n'
    "  <tr>\n"
    '    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Amount paid</td>\n'
    '    <td style="padding:8px 0;font-weight:600;text-align:right;">${{amount}}</td>\n'
    "  </tr>\n"
    "  <tr>\n"
    '    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Payment date</td>\n'
    '    <td style="padding:8px 0;text-align:right;">{{payment_date}}</td>\n'
    "  </tr>\n"
    "  <tr>\n"
    '    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Paid to</td>\n'
    '    <td style="padding:8px 0;text-align:right;">{{company_name}}</td>\n'
    "  </tr>\n"
    "</table>\n\n"
    '<p style="color:#6b7280;font-size:13px;">Please keep this email as your receipt. '
    "If you have any questions about this payment, contact us at "
    '<a href="mailto:support@{{company_domain}}">support@{{company_domain}}</a>.</p>\n\n'
    "<p>Thank you for your business,<br><strong>{{company_name}}</strong></p>\n\n"
    '<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email \u2014 '
    "contact support@pilotfortrades.com for help.</p>"
)
_PAYMENT_RECEIVED_PLAIN = (
    "Hi {{customer_name}},\n\n"
    "We\u2019ve received your payment. Here\u2019s your receipt.\n\n"
    "Amount paid: ${{amount}}\n"
    "Payment date: {{payment_date}}\n"
    "Paid to: {{company_name}}\n\n"
    "Please keep this email as your receipt. Questions? Contact us at support@{{company_domain}}.\n\n"
    "Thank you for your business,\n{{company_name}}"
)
_PAYMENT_RECEIVED_VARS = (
    '["customer_name","company_name","amount","payment_date","company_domain"]'
)

_QUOTE_EXPIRING_SUBJECT = "Your quote from {{company_name}} expires {{expires_at}}"
_QUOTE_EXPIRING_HTML = (
    "<p>Hi {{customer_name}},</p>\n\n"
    "<p>Just a heads up \u2014 your quote from <strong>{{company_name}}</strong> is expiring soon.</p>\n\n"
    '<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">\n'
    "  <tr>\n"
    '    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Quote expires</td>\n'
    '    <td style="padding:8px 0;font-weight:600;text-align:right;">{{expires_at}}</td>\n'
    "  </tr>\n"
    "</table>\n\n"
    '<p style="margin:24px 0;">\n'
    '  <a href="{{quote_url}}" style="background:#2563eb;color:#ffffff;padding:12px 24px;'
    'border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">View Quote \u2192</a>\n'
    "</p>\n\n"
    '<p style="color:#6b7280;font-size:13px;">If you\u2019d like to move forward, accept the quote before '
    "it expires. If you need more time or have questions, just reply and let us know.</p>\n\n"
    "<p>Thank you,<br><strong>{{company_name}}</strong></p>\n\n"
    '<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email \u2014 '
    "contact support@pilotfortrades.com for help.</p>"
)
_QUOTE_EXPIRING_PLAIN = (
    "Hi {{customer_name}},\n\n"
    "Your quote from {{company_name}} is expiring soon.\n\n"
    "Quote expires: {{expires_at}}\n\n"
    "View quote: {{quote_url}}\n\n"
    "If you\u2019d like to move forward, accept the quote before it expires. "
    "If you need more time or have questions, just reach out.\n\n"
    "Thank you,\n{{company_name}}"
)
_QUOTE_EXPIRING_VARS = '["customer_name","quote_url","expires_at"]'

_PAYMENT_FAILED_SUBJECT = (
    "Action needed \u2014 payment issue on your invoice from {{company_name}}"
)
_PAYMENT_FAILED_HTML = (
    "<p>Hi {{customer_name}},</p>\n\n"
    "<p>We weren\u2019t able to process your payment for your recent invoice from "
    "<strong>{{company_name}}</strong>. This can happen when a card expires, has insufficient funds, "
    "or the bank blocks the charge.</p>\n\n"
    '<p style="margin:24px 0;">\n'
    '  <a href="{{invoice_url}}" style="background:#dc2626;color:#ffffff;padding:12px 24px;'
    'border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Retry Payment \u2192</a>\n'
    "</p>\n\n"
    '<p style="color:#6b7280;font-size:13px;">You can retry with the same card or use a different '
    "payment method online. No account required.</p>\n\n"
    '<p style="color:#6b7280;font-size:13px;">If you need help or believe this is a mistake, '
    'contact us at <a href="mailto:support@{{company_domain}}">support@{{company_domain}}</a> '
    "and we\u2019ll sort it out quickly.</p>\n\n"
    "<p>Thank you,<br><strong>{{company_name}}</strong></p>\n\n"
    '<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email \u2014 '
    "contact support@pilotfortrades.com for help.</p>"
)
_PAYMENT_FAILED_PLAIN = (
    "Hi {{customer_name}},\n\n"
    "We weren\u2019t able to process your payment for your recent invoice from {{company_name}}.\n\n"
    "This can happen when a card expires, has insufficient funds, or the bank blocks the charge.\n\n"
    "Retry payment: {{invoice_url}}\n\n"
    "You can retry with the same card or use a different payment method. No account required.\n\n"
    "If you need help, contact us at support@{{company_domain}}.\n\n"
    "Thank you,\n{{company_name}}"
)
_PAYMENT_FAILED_VARS = '["customer_name","invoice_url","company_name","company_domain"]'


def upgrade() -> None:
    conn = op.get_bind()

    op.execute("SET LOCAL session_replication_role = 'replica';")

    # ── Update 5 customer-facing email_template rows ─────────────────────────
    conn.execute(
        sa.text("""
            UPDATE public.email_template SET
                subject_template = :subject,
                body_html_template = :html,
                body_plain_template = :plain,
                variables = CAST(:vars AS jsonb),
                updated_at = NOW()
            WHERE template_id = 'invoice_sent'
        """),
        {
            "subject": _INVOICE_SENT_SUBJECT,
            "html": _INVOICE_SENT_HTML,
            "plain": _INVOICE_SENT_PLAIN,
            "vars": _INVOICE_SENT_VARS,
        },
    )

    conn.execute(
        sa.text("""
            UPDATE public.email_template SET
                subject_template = :subject,
                body_html_template = :html,
                body_plain_template = :plain,
                variables = CAST(:vars AS jsonb),
                updated_at = NOW()
            WHERE template_id = 'quote_sent'
        """),
        {
            "subject": _QUOTE_SENT_SUBJECT,
            "html": _QUOTE_SENT_HTML,
            "plain": _QUOTE_SENT_PLAIN,
            "vars": _QUOTE_SENT_VARS,
        },
    )

    conn.execute(
        sa.text("""
            UPDATE public.email_template SET
                subject_template = :subject,
                body_html_template = :html,
                body_plain_template = :plain,
                variables = CAST(:vars AS jsonb),
                updated_at = NOW()
            WHERE template_id = 'payment_received_customer'
        """),
        {
            "subject": _PAYMENT_RECEIVED_SUBJECT,
            "html": _PAYMENT_RECEIVED_HTML,
            "plain": _PAYMENT_RECEIVED_PLAIN,
            "vars": _PAYMENT_RECEIVED_VARS,
        },
    )

    conn.execute(
        sa.text("""
            UPDATE public.email_template SET
                subject_template = :subject,
                body_html_template = :html,
                body_plain_template = :plain,
                variables = CAST(:vars AS jsonb),
                updated_at = NOW()
            WHERE template_id = 'quote_expiring'
        """),
        {
            "subject": _QUOTE_EXPIRING_SUBJECT,
            "html": _QUOTE_EXPIRING_HTML,
            "plain": _QUOTE_EXPIRING_PLAIN,
            "vars": _QUOTE_EXPIRING_VARS,
        },
    )

    conn.execute(
        sa.text("""
            UPDATE public.email_template SET
                subject_template = :subject,
                body_html_template = :html,
                body_plain_template = :plain,
                variables = CAST(:vars AS jsonb),
                updated_at = NOW()
            WHERE template_id = 'payment_failed'
        """),
        {
            "subject": _PAYMENT_FAILED_SUBJECT,
            "html": _PAYMENT_FAILED_HTML,
            "plain": _PAYMENT_FAILED_PLAIN,
            "vars": _PAYMENT_FAILED_VARS,
        },
    )

    # ── Update 9 notification_template rows ───────────────────────────────────
    notification_updates = [
        {
            "type_code": "customer_communication_sent",
            "channel": "email",
            "body": "A customer communication was sent to {{customer_name}} via {{channel}}.",
        },
        {
            "type_code": "customer_communication_sent",
            "channel": "in_app",
            "body": "Message sent to {{customer_name}}.",
        },
        {
            "type_code": "customer_communication_sent",
            "channel": "push",
            "body": "Message sent to {{customer_name}}.",
        },
        {
            "type_code": "dunning_reminder",
            "channel": "email",
            "body": (
                "Invoice {{invoice_number}} for {{customer_name}} is {{days_overdue}} days overdue. "
                "Balance due: ${{amount_due}}. Review and follow up in Pilot."
            ),
        },
        {
            "type_code": "dunning_reminder",
            "channel": "in_app",
            "body": "Invoice {{invoice_number}} is {{days_overdue}} days overdue \u2014 ${{amount_due}} outstanding.",
        },
        {
            "type_code": "dunning_reminder",
            "channel": "push",
            "body": "Overdue invoice: {{invoice_number}} \u2014 ${{amount_due}} outstanding.",
        },
        {
            "type_code": "quote_accepted",
            "channel": "email",
            "body": (
                "{{customer_name}} accepted your quote. "
                "Log in to Pilot to create a job and schedule the work."
            ),
        },
        {
            "type_code": "quote_accepted",
            "channel": "in_app",
            "body": "{{customer_name}} accepted your quote.",
        },
        {
            "type_code": "quote_accepted",
            "channel": "push",
            "body": "New quote acceptance from {{customer_name}}.",
        },
    ]

    for row in notification_updates:
        conn.execute(
            sa.text("""
                UPDATE public.notification_template
                SET body = :body, updated_at = NOW()
                WHERE notification_type_code = :type_code
                  AND channel = :channel
                  AND tenant_id IS NULL
            """),
            row,
        )


def downgrade() -> None:
    conn = op.get_bind()

    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Restore original stub email templates
    stub_templates = [
        {
            "template_id": "invoice_sent",
            "subject": "Invoice from {{company_name}}",
            "html": "<p>Your invoice is ready.</p>",
            "plain": "Your invoice is ready.",
            "vars": '["customer_name","company_name","invoice_total","invoice_url"]',
        },
        {
            "template_id": "quote_sent",
            "subject": "Your quote from {{company_name}}",
            "html": "<p>Please review your quote.</p>",
            "plain": "Please review your quote.",
            "vars": '["customer_name","company_name","quote_total","quote_url"]',
        },
        {
            "template_id": "payment_received_customer",
            "subject": "Payment confirmation from {{company_name}}",
            "html": "<p>Thank you for your payment.</p>",
            "plain": "Thank you for your payment.",
            "vars": '["customer_name","company_name","amount","payment_date"]',
        },
        {
            "template_id": "quote_expiring",
            "subject": "Your quote expires soon",
            "html": "<p>Your quote expires in 3 days.</p>",
            "plain": "Your quote expires in 3 days.",
            "vars": '["customer_name","quote_url","expires_at"]',
        },
        {
            "template_id": "payment_failed",
            "subject": "Payment issue with your invoice",
            "html": "<p>Your payment could not be processed.</p>",
            "plain": "Your payment could not be processed.",
            "vars": '["customer_name","invoice_url"]',
        },
    ]

    for t in stub_templates:
        conn.execute(
            sa.text("""
                UPDATE public.email_template SET
                    subject_template = :subject,
                    body_html_template = :html,
                    body_plain_template = :plain,
                    variables = CAST(:vars AS jsonb),
                    updated_at = NOW()
                WHERE template_id = :template_id
            """),
            t,
        )

    # Restore placeholder notification template bodies
    notification_restores = [
        {
            "type_code": "customer_communication_sent",
            "channel": "email",
            "body": "This is a placeholder customer_communication_sent notification via email.",
        },
        {
            "type_code": "customer_communication_sent",
            "channel": "in_app",
            "body": "This is a placeholder customer_communication_sent notification via in_app.",
        },
        {
            "type_code": "customer_communication_sent",
            "channel": "push",
            "body": "This is a placeholder customer_communication_sent notification via push.",
        },
        {
            "type_code": "dunning_reminder",
            "channel": "email",
            "body": "This is a placeholder dunning_reminder notification via email.",
        },
        {
            "type_code": "dunning_reminder",
            "channel": "in_app",
            "body": "This is a placeholder dunning_reminder notification via in_app.",
        },
        {
            "type_code": "dunning_reminder",
            "channel": "push",
            "body": "This is a placeholder dunning_reminder notification via push.",
        },
        {
            "type_code": "quote_accepted",
            "channel": "email",
            "body": "This is a placeholder quote_accepted notification via email.",
        },
        {
            "type_code": "quote_accepted",
            "channel": "in_app",
            "body": "This is a placeholder quote_accepted notification via in_app.",
        },
        {
            "type_code": "quote_accepted",
            "channel": "push",
            "body": "This is a placeholder quote_accepted notification via push.",
        },
    ]

    for row in notification_restores:
        conn.execute(
            sa.text("""
                UPDATE public.notification_template
                SET body = :body, updated_at = NOW()
                WHERE notification_type_code = :type_code
                  AND channel = :channel
                  AND tenant_id IS NULL
            """),
            row,
        )
