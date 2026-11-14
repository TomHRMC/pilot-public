"""
Platform SMS Template Loader — PLATFORM-SMS-B1 / Pathway C
==========================================================
Single DB content path for all Pilot→tenant-owner platform SMS bodies.

The ``notification_template`` rows loaded here are **campaign-locked** — they
were registered verbatim with Telnyx under campaign ``CXXXXXX`` (approved
2026-08-07). Editing a body requires a Telnyx portal resubmission; see
``dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md``
§6 (samples) / §8 (auto-replies) for the §6↔§8 code-match rule (error 806).

This loader is **fail-loud by design** (design §G-1): a missing or inactive
campaign-locked template raises ``PlatformSmsTemplateMissingError`` and sends
nothing. A silent hardcoded fallback would recreate the two-path problem and
defer error-806 discovery to production.

Sync ``def`` throughout (Rule 21). Direct ``select()`` on
``NotificationTemplate`` — NOT preference-gated, NOT tenant-scoped.

Callers:
    - ``tasks/sms_compliance_platform.py`` (double opt-in)
    - ``api/routes/webhooks_sms.py`` (STOP/START/HELP auto-replies)
    - ``tasks/sms_platform_notifications.py`` (account notifications)
"""

import logging

from sqlmodel import Session, select

from app.models.system import NotificationTemplate

logger = logging.getLogger(__name__)


class PlatformSmsTemplateMissingError(RuntimeError):
    """Raised when a campaign-locked platform SMS template row is missing or inactive.

    Never swallow: a missing compliance template means the environment is
    mis-seeded or the row was edited — fail loud, send nothing.
    """


def get_platform_sms_body(db: Session, type_code: str) -> str:
    """
    Load the system-default (tenant_id IS NULL) sms-channel
    ``notification_template`` body for ``type_code``.

    Direct lookup — NOT preference-gated, NOT tenant-scoped. Raises
    ``PlatformSmsTemplateMissingError`` if no active row exists.

    Args:
        db:        Active DB session (sync).
        type_code: The ``notification_type.code`` (e.g.
                   ``"platform_sms_double_optin"``).

    Returns:
        The verbatim campaign-locked SMS body string.

    Raises:
        PlatformSmsTemplateMissingError: If no active system sms template
            row exists for ``type_code``.
    """
    # SQLModel == None (not `is None`) for NULL comparison in WHERE clauses.
    template = db.exec(
        select(NotificationTemplate).where(
            NotificationTemplate.notification_type_code == type_code,
            NotificationTemplate.channel == "sms",
            NotificationTemplate.tenant_id == None,
            NotificationTemplate.is_active == True,
        )
    ).first()

    if template is None:
        logger.error(
            "get_platform_sms_body: no active system sms template for "
            "type_code=%r — environment is mis-seeded or row was edited. "
            "Run alembic upgrade head + seed_platform.py.",
            type_code,
        )
        raise PlatformSmsTemplateMissingError(
            f"No active system sms notification_template for "
            f"type_code='{type_code}'. The environment is mis-seeded or the "
            f"campaign-locked row was edited/deactivated. "
            f"Run: alembic upgrade head && python migrations/scripts/seed_platform.py"
        )

    return template.body
