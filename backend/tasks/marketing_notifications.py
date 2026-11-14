"""
Marketing email notification tasks.

MKT-B1-BE:   send_waitlist_confirmation
MKT-B1.5-BE: send_contact_confirmation, send_newsletter_confirmation

Pattern: Direct send_email() call — no tenant context, no notification_outbox.
Same pattern as send_feedback_email in tasks/help_corpus.py.
"""

import base64
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.celery_app import celery_app
from core.config import settings
from services.email_service import send_email

logger = logging.getLogger(__name__)


# ─── Unsubscribe token helpers ────────────────────────────────────────────────


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_newsletter_unsubscribe_token(email: str) -> str:
    """
    Generate an HMAC-SHA256 signed unsubscribe token for a newsletter subscriber.

    Token format: base64url(payload_json).base64url(hmac_sig)
    Payload: {"email": str, "expiration": ISO-8601-str}
    TTL: 90 days
    Secret: settings.NEWSLETTER_UNSUBSCRIBE_SECRET

    Returns:
        URL-safe signed token string.
    """
    secret = settings.NEWSLETTER_UNSUBSCRIBE_SECRET
    expires_at = datetime.now(UTC) + timedelta(days=90)
    payload = {"email": email, "expiration": expires_at.isoformat()}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


# ─── send_waitlist_confirmation ───────────────────────────────────────────────


@celery_app.task(
    name="send_waitlist_confirmation",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_waitlist_confirmation(
    self,
    email: str,
    trade: str,
    company_size: str,
    source: str,
    position: int,
) -> dict[str, Any]:
    """
    Send confirmation email to waitlist subscriber + admin notification.

    Triggered by POST /api/v1/marketing/waitlist after successful DB insert.
    Uses direct send_email() call — no tenant context required.

    Args:
        email: Subscriber's email address.
        trade: Trade vertical (electrical, plumbing, hvac, other).
        company_size: Company size bucket (solo, 2-5, 6-10, 10+).
        source: Page/section where the form was submitted.
        position: The subscriber's position in the waitlist.
    """
    try:
        # 1. Confirmation email to subscriber
        confirmation_body = (
            f"<h2>You're on the list! 🎉</h2>"
            f"<p>Thanks for joining the Pilot for Trades waitlist. "
            f"You're <strong>#{position}</strong> in line.</p>"
            f"<p>We'll email you the moment we open early access for {trade} contractors.</p>"
            f"<p>— The Pilot for Trades Team</p>"
        )
        subscriber_result = send_email(
            to=email,
            subject="You're on the Pilot for Trades waitlist!",
            body=confirmation_body,
        )

        # 2. Admin notification to support
        admin_body = (
            f"<h3>New Waitlist Signup</h3>"
            f"<ul>"
            f"<li><strong>Email:</strong> {email}</li>"
            f"<li><strong>Trade:</strong> {trade}</li>"
            f"<li><strong>Company Size:</strong> {company_size}</li>"
            f"<li><strong>Source:</strong> {source}</li>"
            f"<li><strong>Position:</strong> #{position}</li>"
            f"</ul>"
        )
        admin_result = send_email(
            to=settings.SALES_EMAIL_ADDR,
            subject=f"New waitlist signup: {email} ({trade})",
            body=admin_body,
        )

        return {
            "status": "sent",
            "subscriber_result": subscriber_result,
            "admin_result": admin_result,
        }

    except Exception as exc:
        logger.error("send_waitlist_confirmation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# ─── send_contact_confirmation ────────────────────────────────────────────────


@celery_app.task(
    name="send_contact_confirmation",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_contact_confirmation(
    self,
    name: str,
    email: str,
    subject: str,
    message: str,
    source_page: str | None = None,
    company: str | None = None,
    trade: str | None = None,
) -> dict[str, Any]:
    """
    Send full submission details to support + confirmation to submitter.

    Triggered by POST /api/v1/marketing/contact after successful DB insert.

    Args:
        name: Submitter's name.
        email: Submitter's email address.
        subject: Contact form subject.
        message: Contact form message body.
        source_page: Optional page where the form was submitted.
        company: Optional company name.
        trade: Optional trade vertical.
    """
    try:
        # 1. Admin notification to support with full details
        company_line = (
            f"<li><strong>Company:</strong> {company}</li>" if company else ""
        )
        trade_line = f"<li><strong>Trade:</strong> {trade}</li>" if trade else ""
        source_line = (
            f"<li><strong>Source page:</strong> {source_page}</li>"
            if source_page
            else ""
        )

        admin_body = (
            f"<h3>New Contact Form Submission</h3>"
            f"<ul>"
            f"<li><strong>Name:</strong> {name}</li>"
            f"<li><strong>Email:</strong> {email}</li>"
            f"<li><strong>Subject:</strong> {subject}</li>"
            f"{company_line}"
            f"{trade_line}"
            f"{source_line}"
            f"</ul>"
            f"<h4>Message:</h4>"
            f"<p>{message}</p>"
        )
        admin_result = send_email(
            to=settings.CONTACT_US_EMAIL_ADDR,
            subject=f"Contact form: {subject} — from {name} <{email}>",
            body=admin_body,
        )

        # 2. Confirmation email to submitter
        confirmation_body = (
            f"<h2>We got your message, {name}!</h2>"
            f"<p>Thanks for reaching out to Pilot for Trades. "
            f"We received your message about <strong>{subject}</strong> "
            f"and will respond within 24 hours.</p>"
            f"<p>— The Pilot for Trades Team</p>"
        )
        submitter_result = send_email(
            to=email,
            subject="We received your message — Pilot for Trades",
            body=confirmation_body,
        )

        return {
            "status": "sent",
            "admin_result": admin_result,
            "submitter_result": submitter_result,
        }

    except Exception as exc:
        logger.error("send_contact_confirmation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# ─── send_newsletter_confirmation ────────────────────────────────────────────


@celery_app.task(
    name="send_newsletter_confirmation",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_newsletter_confirmation(
    self,
    email: str,
    trade_interest: list[str] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """
    Send confirmation email to newsletter subscriber + admin notification.

    Triggered by POST /api/v1/marketing/newsletter after successful DB insert.
    Includes a one-click unsubscribe link using a signed HMAC token.

    Args:
        email: Subscriber's email address.
        trade_interest: Optional list of trade verticals the subscriber is interested in.
        source: Optional source where they subscribed (footer, blog, etc.).
    """
    try:
        # Generate signed unsubscribe token (90-day TTL)
        unsubscribe_token = generate_newsletter_unsubscribe_token(email)
        unsubscribe_url = (
            f"{settings.MARKETING_SITE_BASE_URL}/unsubscribe?token={unsubscribe_token}"
        )

        # Build trade interest line if provided
        trade_line = ""
        if trade_interest:
            trade_display = ", ".join(trade_interest)
            trade_line = (
                f"<p>You'll receive content about: <strong>{trade_display}</strong></p>"
            )

        # 1. Confirmation email to subscriber
        confirmation_body = (
            f"<h2>You're subscribed to Pilot for Trades updates! 📬</h2>"
            f"<p>Here's what you'll get:</p>"
            f"<ul>"
            f"<li>Trade tips and best practices for the electrical, plumbing, and HVAC trades</li>"
            f"<li>NEC code updates and compliance guides</li>"
            f"<li>Product updates and early access announcements</li>"
            f"<li>Business insights for solo contractors</li>"
            f"</ul>"
            f"{trade_line}"
            f"<p>— The Pilot for Trades Team</p>"
            f"<hr/>"
            f'<p style="font-size: 12px; color: #666;">'
            f'Don\'t want these emails? <a href="{unsubscribe_url}">Unsubscribe here</a>.</p>'
        )

        subscriber_result = send_email(
            to=email,
            subject="You're subscribed to Pilot for Trades updates",
            body=confirmation_body,
        )

        # 2. Admin notification to newsletter@
        trade_interest_display = (
            ", ".join(trade_interest) if trade_interest else "not specified"
        )
        source_display = source or "not specified"
        admin_body = (
            f"<h3>New Newsletter Subscriber</h3>"
            f"<ul>"
            f"<li><strong>Email:</strong> {email}</li>"
            f"<li><strong>Trade Interest:</strong> {trade_interest_display}</li>"
            f"<li><strong>Source:</strong> {source_display}</li>"
            f"</ul>"
        )
        admin_result = send_email(
            to=settings.NEWSLETTER_EMAIL_ADDR,
            subject=f"New newsletter subscriber: {email}",
            body=admin_body,
        )

        return {
            "status": "sent",
            "subscriber_result": subscriber_result,
            "admin_result": admin_result,
        }

    except Exception as exc:
        logger.error("send_newsletter_confirmation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# ─── send_application_confirmation ───────────────────────────────────────────


@celery_app.task(
    name="send_application_confirmation",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_application_confirmation(
    self,
    name: str,
    email: str,
    role: str,
    linkedin_url: str | None,
    portfolio_url: str | None,
    why_interested: str,
) -> dict[str, Any]:
    """
    Send job application details to careers@ + confirmation to applicant.
    Triggered by POST /api/v1/marketing/application.
    """
    try:
        # 1. Admin notification to careers@
        portfolio_line = (
            f"<li><strong>Portfolio / GitHub:</strong> {portfolio_url}</li>"
            if portfolio_url
            else ""
        )
        linkedin_line = (
            f"<li><strong>LinkedIn:</strong> {linkedin_url}</li>"
            if linkedin_url
            else ""
        )
        admin_body = (
            f"<h3>New Job Application</h3>"
            f"<ul>"
            f"<li><strong>Name:</strong> {name}</li>"
            f"<li><strong>Email:</strong> {email}</li>"
            f"<li><strong>Role:</strong> {role}</li>"
            f"{linkedin_line}"
            f"{portfolio_line}"
            f"</ul>"
            f"<h4>Why are you interested in joining our team?</h4>"
            f"<p>{why_interested}</p>"
        )
        admin_result = send_email(
            to=settings.CAREERS_EMAIL_ADDR,
            subject=f"New application: {role} — {name} <{email}>",
            body=admin_body,
        )

        # 2. Confirmation to applicant
        confirmation_body = (
            f"<h2>We got your application, {name}!</h2>"
            f"<p>Thanks for applying to the <strong>{role}</strong> role at Pilot for Trades.</p>"
            f"<p>We review every application personally. If your experience is a fit, "
            f"you'll hear from us directly at this email address.</p>"
            f"<p>— Tom Lang, Founder<br>Pilot for Trades</p>"
        )
        applicant_result = send_email(
            to=email,
            subject="Your Pilot for Trades application — received",
            body=confirmation_body,
        )

        return {
            "status": "sent",
            "admin_result": admin_result,
            "applicant_result": applicant_result,
        }

    except Exception as exc:
        logger.error("send_application_confirmation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
