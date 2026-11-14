# backend/services/customer_comms_service.py
"""
Customer Communication Service — B4 (A4, A21, A22, A23)

Provides the shared render function used by both the preview endpoint (A23)
and the send endpoint (A4). Ensures preview and send always render identically.

Import path:
    from services.customer_comms_service import render_communication_preview, CommunicationPreviewResult
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models.communications import CommunicationTemplate
from app.models.crm import Customer
from services.template_renderer import render_subject, render_template

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EditableVariable:
    name: str
    current_value: str | None
    description: str


@dataclass
class CommunicationPreviewResult:
    rendered_body: str
    rendered_subject: str | None  # None for SMS
    recipient_name: str
    recipient_address: str  # E.164 phone for SMS; email address for email
    actual_channel: str  # 'sms' | 'email'
    editable_variables: list[EditableVariable]
    template_id: UUID | None  # FK snapshot for the send path
    customer_preferred_channel: str  # stored preference at render time (A21 audit)
    channel_override_flag: bool  # True when channel_override differed from preference


# ---------------------------------------------------------------------------
# Template variable namespace (B4 MVP)
# ---------------------------------------------------------------------------

MVP_TEMPLATE_VARIABLES: dict[str, list[str]] = {
    # Existing 6 codes (unchanged)
    "on_my_way": ["customer_first_name", "sender_name", "eta", "site_address"],
    "running_late": ["customer_first_name", "sender_name", "minutes_late"],
    "arrived": ["customer_first_name", "sender_name"],
    "job_complete": ["customer_first_name", "sender_name"],
    "parts_delay": ["customer_first_name", "sender_name"],
    "confirm_appointment": ["customer_first_name", "date_time", "site_address"],
    # New 7 MVP codes (A94)
    "tech_assigned": ["customer_first_name", "sender_name", "date_time"],
    "invoice_sent": [
        "customer_first_name",
        "invoice_number",
        "invoice_total",
        "due_date",
    ],
    "payment_reminder": [
        "customer_first_name",
        "invoice_number",
        "amount_due",
        "due_date",
    ],
    "payment_received": ["customer_first_name", "amount_paid", "invoice_number"],
    "change_order_approval": [
        "customer_first_name",
        "sender_name",
        "change_description",
        "change_amount",
    ],
    "quote_accepted": ["customer_first_name", "quote_number"],
    "quote_expiring": ["customer_first_name", "quote_number", "expiry_date"],
}

_VARIABLE_DESCRIPTIONS: dict[str, str] = {
    "eta": "Estimated arrival time",
    "minutes_late": "Minutes behind schedule",
    "date_time": "Appointment date and time",
    "site_address": "Job site address",
}


# ---------------------------------------------------------------------------
# Core render function — called by both preview (A23) and send (A4)
# ---------------------------------------------------------------------------


def render_communication_preview(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    template_code: str,
    variables: dict[str, Any],
    channel_override: str | None = None,
    sender_name: str | None = None,
) -> CommunicationPreviewResult:
    """
    Render a communication template with the given variables.

    Pure function — no writes, no side effects.
    Called identically by the preview endpoint (A23) and the send endpoint (A4).

    Args:
        db:               Database session.
        tenant_id:        Tenant scope for template lookup.
        customer_id:      Customer whose contact details drive recipient resolution.
        template_code:    One of the 13 MVP template codes. See `customer_comm_template_type` table.
        variables:        Caller-supplied substitution variables (eta, minutes_late, etc.).
        channel_override: Optional explicit channel ('sms' | 'email'); overrides customer preference.
        sender_name:      Sender's display name for template {{ sender_name }} variable.

    Returns:
        CommunicationPreviewResult with rendered content and metadata.

    Raises:
        ValueError: If template not found, customer not found, or customer contact info
                    is missing for the requested channel.
    """
    # 1. Resolve customer
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == tenant_id)
    ).first()
    if not customer:
        raise ValueError(f"Customer {customer_id} not found in tenant {tenant_id}")

    # 2. Resolve channel
    preferred_channel: str = customer.preferred_contact_channel  # 'sms' | 'email'
    actual_channel: str = channel_override if channel_override else preferred_channel
    channel_override_flag: bool = bool(
        channel_override and channel_override != preferred_channel
    )

    # 3. Resolve recipient address
    if actual_channel == "sms":
        recipient_address = customer.mobile_phone
        if not recipient_address:
            raise ValueError(
                f"Customer {customer_id} has no mobile_phone — cannot send SMS"
            )
    else:
        recipient_address = str(customer.email) if customer.email else None
        if not recipient_address:
            raise ValueError(f"Customer {customer_id} has no email — cannot send email")

    # 4. Resolve template (tenant-specific override first; system fallback)
    template = _resolve_template(db, tenant_id, template_code, actual_channel)

    # 5. Build full variable context
    ctx: dict[str, Any] = {
        "customer_name": customer.display_name,
        "customer_first_name": customer.first_name or customer.display_name,
        "site_address": variables.get("site_address", ""),
        "eta": variables.get("eta", ""),
        "minutes_late": variables.get("minutes_late", ""),
        "date_time": variables.get("date_time", ""),
        "sender_name": sender_name or "",
    }
    # Caller values override defaults (allows eta=None to clear the default)
    for k, v in variables.items():
        ctx[k] = v if v is not None else ctx.get(k, "")

    # 6. Render body and subject
    rendered_body: str = render_template(template.body_template, ctx)
    rendered_subject: str | None = (
        render_subject(template.subject, ctx) if template.subject else None
    )

    # 7. Build editable variable list for preview UI
    #    Exclude auto-resolved variables (customer/sender) — caller cannot override these
    var_names = MVP_TEMPLATE_VARIABLES.get(template_code, [])
    auto_vars = {"customer_first_name", "sender_name", "customer_name"}
    editable_vars: list[EditableVariable] = [
        EditableVariable(
            name=v,
            current_value=str(ctx[v]) if ctx.get(v) else None,
            description=_VARIABLE_DESCRIPTIONS.get(v, v),
        )
        for v in var_names
        if v not in auto_vars
    ]

    return CommunicationPreviewResult(
        rendered_body=rendered_body,
        rendered_subject=rendered_subject,
        recipient_name=customer.display_name,
        recipient_address=recipient_address,
        actual_channel=actual_channel,
        editable_variables=editable_vars,
        template_id=template.id,
        customer_preferred_channel=preferred_channel,
        channel_override_flag=channel_override_flag,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_template(
    db: Session,
    tenant_id: UUID,
    template_code: str,
    channel: str,
) -> CommunicationTemplate:
    """
    Tenant-specific template first; fall back to system template (tenant_id IS NULL).
    Raises ValueError if no active template found.
    """
    # Tier 1: tenant-specific
    template = db.exec(
        select(CommunicationTemplate)
        .where(CommunicationTemplate.tenant_id == tenant_id)
        .where(CommunicationTemplate.template_code == template_code)
        .where(CommunicationTemplate.channel == channel)
        .where(CommunicationTemplate.is_active == True)
    ).first()

    if template:
        return template

    # Tier 2: system-level (tenant_id IS NULL)
    template = db.exec(
        select(CommunicationTemplate)
        .where(CommunicationTemplate.tenant_id == None)
        .where(CommunicationTemplate.template_code == template_code)
        .where(CommunicationTemplate.channel == channel)
        .where(CommunicationTemplate.is_active == True)
    ).first()

    if not template:
        raise ValueError(
            f"No active template found for code='{template_code}' channel='{channel}'"
        )
    return template
