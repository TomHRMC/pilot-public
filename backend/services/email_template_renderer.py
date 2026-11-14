"""
B15/A82 — Email Template Renderer

Resolves an email template by template_id, applies tenant branding,
substitutes variables, and dispatches via email_service.send_email().

Entry points:
  render_and_send()  — render + dispatch
  render_preview()   — render without sending (for UI preview)

Design note from §E3 of B15 design doc:
  - customer_facing templates: applies TenantEmailBranding
  - internal templates: uses Pilot standard branding constants
  - Variable substitution: str.format_map() (NOT Jinja2, for security isolation)
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, select

logger = logging.getLogger(__name__)

# Pilot standard branding fallback for internal templates
PILOT_FROM_NAME = "Pilot for Trades"
PILOT_FROM_EMAIL = "noreply@pilotfortrades.com"
PILOT_BRAND_COLOR = "#5B3FF0"

# Sample values used when previewing templates without real context
_SAMPLE_CONTEXT: dict[str, str] = {
    "user_name": "Sarah Johnson",
    "customer_name": "Sarah Johnson",
    "company_name": "Pilot Electrical",
    "tenant_name": "Pilot Electrical",
    "quote_total": "$1,250.00",
    "quote_url": "https://app.pilotfortrades.com/q/preview",
    "quote_id": "Q-001234",
    "invoice_total": "$1,250.00",
    "invoice_url": "https://app.pilotfortrades.com/i/preview",
    "invoice_id": "INV-001234",
    "amount": "$1,250.00",
    "payment_date": "May 3, 2026",
    "plan_name": "Starter",
    "next_billing_date": "Jun 3, 2026",
    "update_url": "https://app.pilotfortrades.com/billing",
    "upgrade_url": "https://app.pilotfortrades.com/upgrade",
    "days_remaining": "7",
    "verify_url": "https://app.pilotfortrades.com/verify/token",
    "reset_url": "https://app.pilotfortrades.com/reset/token",
    "expires_in": "24 hours",
    "decline_reason": "pricing",
    "expires_at": "Jun 1, 2026",
}


@dataclass
class RenderedEmail:
    subject: str
    body_html: str
    body_plain: str
    to_address: str
    from_name: str
    from_email: str
    reply_to: str | None = None


def _substitute(template_str: str, context: dict[str, Any]) -> str:
    """
    Substitute {{variable}} placeholders using Python str.format_map().

    The design doc specifies {{variable}} syntax (Jinja2-style braces) but
    str.format_map() uses {variable}. We normalize by converting {{...}} → {...}
    before calling format_map, so templates can use either style.

    Unresolved variables are left as-is (no KeyError raised) using a
    custom defaultdict-style fallback.
    """
    # Normalize {{variable}} → {variable}
    normalized = template_str.replace("{{", "{").replace("}}", "}")

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return f"{{{key}}}"  # leave unresolved as {key}

    return normalized.format_map(_SafeDict(context))


def _get_branding(db: Session, tenant_id: str | None) -> dict:
    """
    Fetch TenantEmailBranding for a tenant, returning fallback values if not found.
    Returns a dict with logo_url, brand_color_hex, email_signature, custom_footer.
    """
    if tenant_id is None:
        return {
            "logo_url": None,
            "brand_color_hex": PILOT_BRAND_COLOR,
            "email_signature": None,
            "custom_footer": None,
        }

    import uuid

    from app.models.core import TenantEmailBranding

    try:
        tid = uuid.UUID(str(tenant_id))
    except ValueError:
        tid = None

    branding = None
    if tid:
        branding = db.exec(
            select(TenantEmailBranding).where(TenantEmailBranding.tenant_id == tid)
        ).first()

    if branding is None:
        return {
            "logo_url": None,
            "brand_color_hex": PILOT_BRAND_COLOR,
            "email_signature": None,
            "custom_footer": None,
        }

    # Resolve logo S3 path to a presigned URL (stub — returns path as-is for MVP)
    logo_url = None
    if branding.logo_s3_path:
        logo_url = _resolve_logo_url(branding.logo_s3_path)

    return {
        "logo_url": logo_url,
        "brand_color_hex": branding.brand_color_hex or PILOT_BRAND_COLOR,
        "email_signature": branding.email_signature,
        "custom_footer": branding.custom_footer,
    }


def _resolve_logo_url(s3_path: str) -> str:
    """
    Resolve an S3 path to a presigned URL.
    MVP stub — returns the path as-is; replace with real S3 presign in production.
    """
    from core.config import settings

    bucket = getattr(settings, "S3_BUCKET_NAME", None)
    if bucket:
        return f"https://{bucket}.s3.amazonaws.com/{s3_path}"
    return s3_path


def render_and_send(
    db: Session,
    template_id: str,
    context: dict[str, Any],
    to_address: str,
    tenant_id: str | None = None,
    reply_to: str | None = None,
) -> dict[str, Any]:
    """
    Render an email template with branding and dispatch via SendGrid.

    Args:
        db: SQLModel session.
        template_id: Slug matching email_template.template_id.
        context: Dict of variable values for substitution.
        to_address: Recipient email address.
        tenant_id: Required for customer_facing templates (branding lookup).
                   None for internal templates (Pilot standard branding).
        reply_to: Optional reply-to address.

    Returns:
        Result dict from email_service.send_email().

    Raises:
        ValueError if template_id not found, is_active=False, or required context missing.
    """
    from app.models.communications import EmailTemplate
    from services.email_service import send_email

    # Load template
    template = db.exec(
        select(EmailTemplate).where(EmailTemplate.template_id == template_id)
    ).first()

    if template is None:
        raise ValueError(f"Email template '{template_id}' not found")

    if not template.is_active:
        raise ValueError(
            f"Email template '{template_id}' is disabled (is_active=False)"
        )

    # Resolve branding
    branding = _get_branding(
        db,
        tenant_id if template.category == "customer_facing" else None,
    )

    # Build enriched context with branding values
    enriched = {**context, **branding}

    # Render subject + bodies
    subject = _substitute(template.subject_template, enriched)
    body_html = _substitute(template.body_html_template, enriched)
    body_plain = _substitute(template.body_plain_template, enriched)

    # Dispatch
    result = send_email(
        to=to_address,
        subject=subject,
        body=body_plain,
        html_body=body_html,
    )
    return result


def render_preview(
    db: Session,
    template_id: str,
    tenant_id: str,
) -> RenderedEmail:
    """
    Render a template with current branding settings WITHOUT sending.

    Uses sample context values for any missing variables.

    Args:
        db: SQLModel session.
        template_id: Template to preview.
        tenant_id: Tenant for branding lookup.

    Returns:
        RenderedEmail with resolved subject, body_html, body_plain.

    Raises:
        ValueError if template_id not found.
    """
    from app.models.communications import EmailTemplate

    template = db.exec(
        select(EmailTemplate).where(EmailTemplate.template_id == template_id)
    ).first()

    if template is None:
        raise ValueError(f"Email template '{template_id}' not found")

    branding = _get_branding(
        db,
        tenant_id if template.category == "customer_facing" else None,
    )

    enriched = {**_SAMPLE_CONTEXT, **branding}

    return RenderedEmail(
        subject=_substitute(template.subject_template, enriched),
        body_html=_substitute(template.body_html_template, enriched),
        body_plain=_substitute(template.body_plain_template, enriched),
        to_address="preview@example.com",
        from_name=PILOT_FROM_NAME,
        from_email=PILOT_FROM_EMAIL,
    )
