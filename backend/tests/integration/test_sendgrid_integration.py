"""
SendGrid Integration Tests

These tests verify the email service with real SendGrid API credentials.
They are marked with @pytest.mark.integration and @pytest.mark.requires_sendgrid
to allow selective execution.

Run with:
    pytest tests/integration/test_sendgrid_integration.py -m requires_sendgrid
    # or
    pytest tests/integration/test_sendgrid_integration.py -v
"""

import pytest

from core.config import settings
from services.email_service import send_email, validate_email_address
from services.template_renderer import render_template

# Skip all tests in this module if SendGrid is not configured
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_sendgrid,
    pytest.mark.skipif(
        not settings.SENDGRID_API_KEY, reason="SENDGRID_API_KEY not configured"
    ),
]


@pytest.fixture
def test_recipient():
    """Default test recipient email address."""
    return "owner@example.com"


def test_sendgrid_configuration():
    """Test that SendGrid is properly configured."""
    assert settings.SENDGRID_API_KEY, "SENDGRID_API_KEY must be set"
    assert settings.SENDGRID_FROM_EMAIL, "SENDGRID_FROM_EMAIL must be set"
    assert settings.SENDGRID_FROM_NAME, "SENDGRID_FROM_NAME must be set"


def test_email_validation():
    """Test email address validation logic."""
    assert validate_email_address("test@example.com") is True
    assert validate_email_address("test.name+tag@example.co.uk") is True
    assert validate_email_address("invalid-email") is False
    assert validate_email_address("@example.com") is False
    assert validate_email_address("") is False
    assert validate_email_address(None) is False


def test_send_plain_text_email(test_recipient):
    """Test sending a simple plain text email via SendGrid."""
    result = send_email(
        to=test_recipient,
        subject="[Pilot for Trades Test] Plain Text Email",
        body="This is a test email from Pilot for Trades backend.\n\nIf you received this, the SendGrid integration is working correctly!",
    )

    assert result["status"] == "sent", (
        f"Email send failed: {result.get('error_message')}"
    )
    assert result["http_status"] == 202, "SendGrid should return HTTP 202 Accepted"
    assert result["retryable"] is False
    assert result["error_message"] is None


def test_send_template_rendered_email(test_recipient):
    """Test sending an email with Jinja2 template rendering."""
    template = """
Hello {{ customer_name }},

Your quote #{{ quote_number }} for ${{ amount }} has been accepted!

Job Details:
- Site: {{ site_address }}
- Scheduled Date: {{ scheduled_date }}
- Technician: {{ technician_name }}

Thank you for choosing Pilot for Trades!

Best regards,
The Pilot for Trades Team
    """.strip()

    context = {
        "customer_name": "Mike the Contractor",
        "quote_number": "Q-12345",
        "amount": "2,450.00",
        "site_address": "123 Main St, Boston, MA",
        "scheduled_date": "March 25, 2026",
        "technician_name": "John Smith",
    }

    rendered_body = render_template(template, context)

    result = send_email(
        to=test_recipient,
        subject="[Pilot for Trades Test] Quote Accepted - Template Test",
        body=rendered_body,
    )

    assert result["status"] == "sent", (
        f"Template email send failed: {result.get('error_message')}"
    )
    assert result["http_status"] == 202
    assert result["error_message"] is None


def test_send_html_email(test_recipient):
    """Test sending an HTML formatted email."""
    html_body = """
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .header { background-color: #007bff; color: white; padding: 20px; }
        .content { padding: 20px; }
        .footer { background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Pilot for Trades - Quote Accepted</h1>
    </div>
    <div class="content">
        <p>Hello <strong>Mike</strong>,</p>
        <p>Your quote <strong>Q-12345</strong> for <strong>$2,450.00</strong> has been accepted!</p>
        <p>We'll contact you shortly to schedule the work.</p>
    </div>
    <div class="footer">
        <p>© 2026 Pilot for Trades - Electrical Job Management Platform</p>
    </div>
</body>
</html>
    """

    result = send_email(
        to=test_recipient,
        subject="[Pilot for Trades Test] HTML Email",
        body="This is the plain text fallback.",
        html_body=html_body,
    )

    assert result["status"] == "sent", (
        f"HTML email send failed: {result.get('error_message')}"
    )
    assert result["http_status"] == 202
    assert result["error_message"] is None


def test_template_rendering_with_escaping():
    """Test that HTML is escaped in templates to prevent injection."""
    template = "Hello {{ name }}"
    context = {"name": "<script>alert('XSS')</script>"}

    result = render_template(template, context)
    assert result == "Hello &lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;"


def test_template_rendering_error():
    """Test template rendering with syntax error."""
    template = "Hello {% if name %} {{ name "  # Invalid syntax
    context = {"name": "Mike"}

    with pytest.raises(ValueError, match="Failed to render template"):
        render_template(template, context)
