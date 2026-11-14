import logging
import re
from typing import Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from core.config import settings

logger = logging.getLogger(__name__)

# Basic regex for email validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_address(email: str) -> bool:
    """
    Validate an email address format.

    Args:
        email: Email string to validate

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email))


def send_email(
    to: str, subject: str, body: str, html_body: str | None = None
) -> dict[str, Any]:
    """
    Send an email via SendGrid.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML email body

    Returns:
        Dict with status and provider_response:
        {
            "status": "sent" | "error",
            "details": dict,
            "error_message": str,
            "http_status": int,
            "retryable": bool
        }
    """
    if not validate_email_address(to):
        return {
            "status": "error",
            "details": {},
            "error_message": f"Invalid email address: {to}",
            "http_status": 400,
            "retryable": False,
        }

    # If no API key is configured (e.g. dev environment without credentials)
    if not settings.SENDGRID_API_KEY:
        logger.warning(f"SENDGRID_API_KEY not set. Mocking email send to {to}")
        return {
            "status": "sent",
            "details": {"message": "Mocked successful send"},
            "error_message": None,
            "http_status": 202,
            "retryable": False,
        }

    message = Mail(
        from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
        to_emails=to,
        subject=subject,
        plain_text_content=body,
        html_content=html_body or body,
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)

        return {
            "status": "sent",
            "details": {
                "headers": dict(response.headers),
                "body": response.body.decode("utf-8") if response.body else "",
            },
            "error_message": None,
            "http_status": response.status_code,
            "retryable": False,
        }

    except Exception as e:
        status_code = getattr(e, "status_code", 500)
        error_msg = str(e)

        # Determine if we should retry
        # 400: Bad request (invalid data) -> Don't retry
        # 401/403: Auth error -> Don't retry
        # 429: Rate limit -> Retry
        # 5xx: Server error -> Retry
        retryable = status_code == 429 or status_code >= 500

        logger.error(f"SendGrid error ({status_code}): {error_msg}")

        return {
            "status": "error",
            "details": {},
            "error_message": error_msg,
            "http_status": status_code,
            "retryable": retryable,
        }
