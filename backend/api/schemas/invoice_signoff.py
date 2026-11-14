"""CE-1 — Pydantic schemas for invoice sign-off capture + context.

Design doc: dev-docs/architecture-design/batch-designs/batch-ce-1-design.md §D.
All schemas are Pydantic v2 (ConfigDict, field_validator, model_dump).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Module constant — concise work-acceptance + payment-acknowledgement sentence
# used when invoice.terms_and_conditions is NULL (design §D.1).
DEFAULT_SIGNOFF_TERMS: str = (
    "I acknowledge the work described on this invoice has been completed "
    "and agree to pay the total amount due."
)


class InvoiceSignoffCreateRequest(BaseModel):
    """Request body for POST /api/v1/invoices/{invoice_id}/signoff."""

    signed_by_name: str = Field(min_length=1, max_length=200)
    terms_acknowledged: Literal[True]
    signature_png_base64: str = Field(min_length=1)
    client_capture_at: datetime | None = None


class InvoiceSignoffSummary(BaseModel):
    """Summary of a sign-off — used in signoff-context responses."""

    model_config = ConfigDict(from_attributes=True)

    signoff_id: UUID
    signed_by_name: str
    signed_at: datetime


class InvoiceSignoffResponse(BaseModel):
    """Full sign-off response with presigned signature URL."""

    model_config = ConfigDict(from_attributes=True)

    signoff_id: UUID
    invoice_id: UUID
    signed_by_name: str
    signed_at: datetime
    client_capture_at: datetime | None
    captured_by_user_id: UUID
    signature_url: str


class SignoffContextInvoice(BaseModel):
    """One invoice in the signoff-context response."""

    model_config = ConfigDict(from_attributes=True)

    invoice_id: UUID
    invoice_number: str
    status: str
    total_cents: int
    balance_due_cents: int
    currency: str
    terms_text: str
    active_signoff: InvoiceSignoffSummary | None


class SignoffContextResponse(BaseModel):
    """Response for GET /api/v1/jobs/{job_id}/signoff-context."""

    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    customer_display_name: str
    invoices: list[SignoffContextInvoice]


class InvoiceSignoffDetailResponse(BaseModel):
    """Response for GET /api/v1/invoices/{invoice_id}/signoff.

    Includes superseded_count for the invoice's sign-off history.
    """

    model_config = ConfigDict(from_attributes=True)

    signoff: InvoiceSignoffResponse | None
    superseded_count: int
