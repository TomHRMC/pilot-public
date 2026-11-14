"""C-B16 Part A — One-time website requirements email Celery task.

Two-layer pattern (business logic testable without a worker):
    _send_website_requirements_email_impl(tenant_id, db) → dict
    send_website_requirements_email(tenant_id) → dict  (Celery entry point)

Body: website-requirements summary + Requirements Guide PDF link +
(when profile data exists) pre-merged Privacy/Terms kit text (single content path).

One-time guard: the task re-checks requirements_emailed_at IS NULL defensively
and returns {"sent": False, "reason": "already_emailed"} when stamped (race safety).

No Beat schedule. No resend endpoint (§G-19).
"""

import logging
from typing import Any

from sqlmodel import select

from app.models.core import Tenant10DlcProfile
from core.celery_app import celery_app
from core.db import get_db
from services.email_service import send_email
from services.tenant_site_service import get_effective_defaults, render_kit_text

logger = logging.getLogger(__name__)

# Requirements Guide PDF link (§G-20 — static committed asset)
REQUIREMENTS_GUIDE_URL = (
    "https://app.pilotfortrades.com/resources/tenant-website-requirements-v1.pdf"
)


def _send_website_requirements_email_impl(tenant_id: str, db) -> dict[str, Any]:
    """Pure logic — injected Session. Sends via SendGrid.

    Returns:
        {"sent": bool, "reason": str}
    """
    from uuid import UUID

    try:
        tid = UUID(str(tenant_id))
    except (ValueError, TypeError):
        return {"sent": False, "reason": "invalid_tenant_id"}

    # Fetch the profile
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tid)
    ).first()

    if not profile:
        return {"sent": False, "reason": "no_profile"}

    # Defensive one-time guard — re-check requirements_emailed_at
    already_emailed = getattr(profile, "requirements_emailed_at", None)
    if already_emailed is not None:
        return {"sent": False, "reason": "already_emailed"}

    # Determine recipient — use support_email or legal_business_name contact
    recipient = profile.support_email
    if not recipient:
        logger.warning(
            "Cannot send requirements email for tenant %s — no support_email",
            tenant_id,
        )
        return {"sent": False, "reason": "no_recipient_email"}

    # Build email body
    defaults = get_effective_defaults(db, tid)
    business_name = defaults.display_name or "Your Business"

    # Plain text body
    body_parts: list[str] = [
        f"Hello {business_name},",
        "",
        "To complete your 10DLC SMS campaign registration, your business website "
        "must meet The Campaign Registry (TCR) requirements. This email summarizes "
        "what you need and provides a downloadable guide with worked examples.",
        "",
        "Key Requirements:",
        "- A live, publicly accessible website URL",
        "- An 'About' page or section showing your business identity",
        "- A 'Contact' page or section with phone and/or email",
        "- A 'Privacy Policy' page with SMS-specific disclosures",
        "- A 'Terms of Service' page with SMS-specific disclosures",
        "",
        "SMS Privacy/Terms Disclosures Must Include:",
        "- Message types (appointment confirmations, service updates, account alerts)",
        "- Message frequency (typically no more than 5 messages per month)",
        "- Message and data rates may apply notice",
        "- STOP opt-out instructions",
        "- HELP instructions",
        "- Statement that mobile information is not shared with third parties "
        "for marketing or promotional purposes",
        "",
        "Download the full Requirements Guide (PDF):",
        REQUIREMENTS_GUIDE_URL,
        "",
    ]

    # Append pre-merged Privacy/Terms kit text when profile data exists
    try:
        kit_text = render_kit_text(db, tid)
        if kit_text:
            body_parts.append("Pre-merged Privacy Policy and Terms of Service:")
            body_parts.append("")
            body_parts.append(kit_text)
    except Exception:
        logger.warning(
            "Could not render kit text for tenant %s — sending summary only",
            tenant_id,
        )

    body_parts.append("— The Pilot for Trades Team")

    plain_body = "\n".join(body_parts)

    # HTML body
    html_parts: list[str] = [
        f"<h2>Hello {business_name},</h2>",
        "<p>To complete your 10DLC SMS campaign registration, your business website "
        "must meet The Campaign Registry (TCR) requirements. This email summarizes "
        "what you need and provides a downloadable guide with worked examples.</p>",
        "<h3>Key Requirements:</h3>",
        "<ul>",
        "<li>A live, publicly accessible website URL</li>",
        "<li>An 'About' page or section showing your business identity</li>",
        "<li>A 'Contact' page or section with phone and/or email</li>",
        "<li>A 'Privacy Policy' page with SMS-specific disclosures</li>",
        "<li>A 'Terms of Service' page with SMS-specific disclosures</li>",
        "</ul>",
        "<h3>SMS Privacy/Terms Disclosures Must Include:</h3>",
        "<ul>",
        "<li>Message types (appointment confirmations, service updates, account alerts)</li>",
        "<li>Message frequency (typically no more than 5 messages per month)</li>",
        "<li>Message and data rates may apply notice</li>",
        "<li>STOP opt-out instructions</li>",
        "<li>HELP instructions</li>",
        "<li>Statement that mobile information is not shared with third parties "
        "for marketing or promotional purposes</li>",
        "</ul>",
        f"<p><strong>Download the full Requirements Guide (PDF):</strong><br>"
        f'<a href="{REQUIREMENTS_GUIDE_URL}">{REQUIREMENTS_GUIDE_URL}</a></p>',
    ]

    try:
        kit_text = render_kit_text(db, tid)
        if kit_text:
            # Escape for HTML
            safe_kit = kit_text.replace("&", "&").replace("<", "<").replace(">", ">")
            html_parts.append(
                f"<h3>Pre-merged Privacy Policy and Terms of Service:</h3>"
                f"<pre>{safe_kit}</pre>"
            )
    except Exception:
        pass

    html_parts.append("<p>— The Pilot for Trades Team</p>")
    html_body = "\n".join(html_parts)

    # Send via SendGrid
    result = send_email(
        to=recipient,
        subject="Your 10DLC Website Requirements Guide — Pilot for Trades",
        body=plain_body,
        html_body=html_body,
    )

    if result.get("status") == "sent":
        # Stamp requirements_emailed_at (defensive — the enqueue site may have
        # already stamped it; this is the race-safety net)
        from core.datetime_utils import safe_now_utc

        if getattr(profile, "requirements_emailed_at", None) is None:
            profile.requirements_emailed_at = safe_now_utc()  # type: ignore[attr-defined]
            db.add(profile)
            db.commit()

        return {"sent": True, "reason": "sent"}
    else:
        return {
            "sent": False,
            "reason": f"send_failed: {result.get('error_message', 'unknown')}",
        }


@celery_app.task(
    name="send_website_requirements_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_website_requirements_email(self, tenant_id: str) -> dict[str, Any]:
    """Celery entry point — creates its own session, calls _impl.

    No business logic here — all logic is in _send_website_requirements_email_impl.
    """
    try:
        with next(get_db()) as db:
            return _send_website_requirements_email_impl(tenant_id, db)
    except Exception as exc:
        logger.error(
            "send_website_requirements_email failed for tenant %s: %s",
            tenant_id,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc)
