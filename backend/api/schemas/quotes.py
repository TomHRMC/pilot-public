from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, field_validator


# --- Quotes ---
class QuoteCreate(BaseModel):
    customer_id: UUID
    site_id: UUID
    currency: str = "USD"
    idempotency_key: str | None = None
    # FIND-096 (B19): Quote expiration timestamp; NULL = never expires
    expires_at: datetime | None = None
    # B19: Optional quote title
    title: str | None = None
    # B20: card-on-file override (None = inherit from customer.card_required)
    card_required: bool | None = None


class QuoteUpdate(BaseModel):
    status_id: UUID | None = None
    subtotal_cents: int | None = None
    tax_cents: int | None = None
    total_cents: int | None = None
    currency: str | None = None
    # FIND-096 (B19): Quote expiration timestamp; NULL = never expires
    expires_at: datetime | None = None


class QuoteListItem(BaseModel):
    """
    Lightweight schema returned by GET /api/v1/quotes (list endpoint).

    Includes denormalized status_code and customer_name for display —
    joins QuoteStatus and Customer to avoid N+1 on the list page.

    BETA-B3 companion task: BE-2 (?status= filter), BE-3 (status_code), BE-4 (customer_name)
    B19: Adds quote_number and title.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    customer_name: str | None = None  # BE-4: denormalized from Customer.display_name
    site_id: UUID
    status_id: UUID
    status_code: str | None = None  # BE-3: denormalized from QuoteStatus.code
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    # B19: Human-readable quote number + optional title
    quote_number: str | None = None
    title: str | None = None


class PaginatedQuoteListResponse(BaseModel):
    """Paginated list of quotes (UI-FIX-1C)."""

    items: list[QuoteListItem]
    total: int
    limit: int
    offset: int


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    site_id: UUID
    status_id: UUID
    status_code: str | None = (
        None  # from quote_status.code JOIN — required by QuoteStatusPill
    )
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    is_active: bool
    # B19: Human-readable quote number + optional title
    quote_number: str = ""
    title: str | None = None
    # FIND-147: A3 time-limited discount fields (all Optional)
    discount_pct: float | None = None
    discount_amount_cents: int | None = None
    discount_expires_at: datetime | None = None
    discount_applied_by_user_id: UUID | None = None
    # FIND-147: A83 customer acceptance/decline fields (all Optional)
    customer_accepted_at: datetime | None = None
    customer_acceptance_comment: str | None = None
    customer_declined_at: datetime | None = None
    customer_decline_comment: str | None = None
    customer_decline_reason: str | None = None
    customer_email_at_action: str | None = None
    # FIND-096 (B19): Quote expiration timestamp; NULL = never expires
    expires_at: datetime | None = None
    # B20: card-on-file override (None = inherit from customer.card_required)
    card_required: bool | None = None


class QuoteLineDetailResponse(BaseModel):
    """
    Line item shape returned by GET /api/v1/quotes/{quote_id}/detail.
    Includes resolved line_type code from qco_line_type join.
    PRE-WS3-FIX-01
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    customer_visible: bool
    unit_price_cents: int
    quantity: float
    total_cents: int
    line_type: str  # qco_line_type.code — e.g. 'labor', 'material', 'misc', 'discount'
    # PLP-FIX-5 (Issue 14): the FK the draft editor resolves persisted-row labels by
    qco_line_type_id: UUID


class QuoteDetailResponse(BaseModel):
    """
    Aggregated quote detail for the owner approval/review surface.

    Returned by GET /api/v1/quotes/{quote_id}/detail.
    Replaces the bare QuoteResponse for the QuoteDetailPage surface.
    PRE-WS3-FIX-01

    Fields that differ from QuoteResponse:
    - quote_number: formatted from ID (no quote_number column in DB)
    - status: status code string (not UUID)
    - customer_name, submitted_by_name: denormalized joins
    - rejected_at: derived from quote_approval_comment, not a column
    - margin_percent: computed from line unit_cost_cents
    - quote_version_id: latest active quote_version.id
    - has_owner_edits: presence of quote_pending_edit rows
    - require_approval: from SettingResolver
    - line_items: active lines with resolved line_type
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_number: str
    status: str | None
    customer_id: UUID
    customer_name: str | None
    site_id: UUID
    submitted_by_user_id: UUID | None
    submitted_by_name: str | None
    submitted_at: AwareDatetime | None
    approved_at: AwareDatetime | None
    rejected_at: AwareDatetime | None
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    margin_percent: float | None
    quote_version_id: UUID
    has_owner_edits: bool
    require_approval: bool
    line_items: list[QuoteLineDetailResponse]


# --- Quote Lines ---


class QcoLineTypeResponse(BaseModel):
    """PLP-FIX-2: response for a single QCO line-type lookup entry.

    Platform rows (tenant_id IS NULL) are visible to every tenant; a tenant
    row with the same code shadows the platform row (is_tenant_override=True).
    ``qb_item_name_hint`` is intentionally excluded — internal QB concern.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_default: bool
    is_active: bool
    is_tenant_override: bool = False


class QuoteLineCreate(BaseModel):
    """
    Request schema for creating a quote line item.

    A28 — Multi-Line Description Guarantee:
    The `description` field has NO length cap. It is stored as VARCHAR without a
    maximum length in PostgreSQL (functionally identical to TEXT). Callers may submit
    multi-paragraph descriptions, HTML snippets, or structured text of any length.

    A24 — Line Visibility & Hierarchy fields:
    - `customer_visible`: When False, the line is internal cost-tracking only and
      hidden from the customer-facing quote view. Defaults to True.
    - `parent_line_id`: Self-referential UUID to create one level of line nesting
      (e.g., sub-items under a section). NULL for top-level lines.
    - `display_order`: Explicit ordering integer separate from `position`. Defaults to 0.
    - `is_section_header`: When True, line acts as a visual grouping divider with no
      price contribution. Section headers cannot have a parent_line_id.
    """

    position: int
    qco_line_type_id: UUID
    pricebook_item_id: UUID | None = None
    supplier_id: UUID | None = None
    supplier_item_id: UUID | None = None
    taxability_code: str | None = (
        None  # 'taxable', 'exempt', 'zero_rated' (defaults to 'taxable')
    )
    description: str  # A28: No length cap — VARCHAR(unlimited) in DB, functionally TEXT
    quantity: Decimal = Decimal("1.0")
    unit: str | None = None
    # We will fetch unit_price_cents from DB based on item, but allow override if no item
    unit_price_cents: int | None = None
    # A24: Visibility and hierarchy fields
    customer_visible: bool = True
    parent_line_id: UUID | None = None
    display_order: int = 0
    is_section_header: bool = False


class QuoteLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    position: int
    qco_line_type_id: UUID
    pricebook_item_id: UUID | None
    taxability_code: str | None
    description: str  # A28: No length cap guarantee
    quantity: Decimal
    unit: str | None
    unit_price_cents: int
    subtotal_cents: int
    tax_rate_pct: float | None  # Will auto-convert Decimal to float
    tax_amount_cents: int
    total_cents: int
    tax_jurisdiction_code: str | None
    tax_as_of: datetime | None
    tax_source: str | None
    is_active: bool
    # A24: Visibility and hierarchy fields
    customer_visible: bool
    parent_line_id: UUID | None
    display_order: int
    is_section_header: bool


# --- Quote Versions ---
class QuoteVersionCreate(BaseModel):
    # FIND-095 (B18): Presentation style for quote rendering
    presentation_style: str = "clean"

    @field_validator("presentation_style")
    @classmethod
    def validate_presentation_style(cls, v: str) -> str:
        allowed = ("clean", "line_itemed", "hybrid")
        if v not in allowed:
            raise ValueError(f"presentation_style must be one of {allowed}, got '{v}'")
        return v


class QuoteVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    version_no: int
    snapshot: dict[str, Any]
    pdf_object_key: str | None
    is_active: bool
    # FIND-095 (B18): Expose presentation_style in response for frontend codegen
    presentation_style: str


# --- Quote Public Links ---
class QuotePublicLinkCreate(BaseModel):
    # FIND-146: status_id removed — server always resolves 'active' on creation
    contact_id: UUID
    expires_at: datetime | None = None
    max_uses: int = 1


class QuotePublicLinkResponse(BaseModel):
    # This specifically returns the raw token URL
    url: str
    id: UUID
    quote_id: UUID
    contact_id: UUID
    expires_at: datetime | None
    # FIND-097: HMAC-signed token for public link verification
    signed_token: str | None = None


# FIND-162: Typed revoke-link response
class QuoteRevokeLinkResponse(BaseModel):
    id: UUID  # the QuotePublicLink.id that was revoked
    revoked_at: AwareDatetime
    status: str  # = 'revoked' — aligned with FIND-146 lifecycle


# --- Quote Conversion ---
class QuoteConvertResponse(BaseModel):
    """Response after converting an accepted quote to a job."""

    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    quote_id: UUID
    quote_status: str  # Should be "converted"
    job_status_id: UUID
    quote_version_id: UUID | None = None


# --- Quote Acceptance ---
class QuoteAcceptanceCreate(BaseModel):
    """Request body for accepting a quote"""

    accepted_by_name: str
    accepted_by_email: EmailStr  # Validates email format
    signature_url: str
    acceptance_notes: str | None = None

    # These fields are auto-captured from request, but can be overridden for testing
    ip_address: str | None = None
    user_agent: str | None = None


class QuoteAcceptanceResponse(BaseModel):
    """Response after accepting a quote"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_version_id: UUID
    contact_id: UUID | None = None

    accepted_by_name: str
    accepted_by_email: str
    accepted_by_user_id: UUID | None = None

    approved_at: datetime
    approved_ip: str | None = None
    approved_user_agent: str | None = None
    signature_url: str | None = None
    acceptance_notes: str | None = None

    quote_public_link_id: UUID | None = None
    quote_status: str  # New status of the quote (e.g., "Accepted")


# --- A29: Pending Edit Storage ---


class QuotePendingEditCreate(BaseModel):
    """Request body for creating a pending edit during owner review."""

    edit_type: str  # modify_line | add_line | delete_line | edit_notes
    target_line_id: UUID | None = None
    edit_payload: dict
    annotation: str | None = None


class QuotePendingEditUpdate(BaseModel):
    """Request body for updating an existing pending edit."""

    edit_payload: dict | None = None
    annotation: str | None = None


class QuotePendingEditResponse(BaseModel):
    """Response for a pending edit row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    quote_version_id: UUID
    editor_user_id: UUID
    edit_type: str
    target_line_id: UUID | None
    edit_payload: dict
    annotation: str | None
    created_at: datetime


# --- A30: Approval Comment ---


class QuoteApprovalCommentResponse(BaseModel):
    """Response for a quote approval comment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    quote_version_id: UUID
    target_line_id: UUID | None
    author_user_id: UUID
    comment_type: str  # kickback | rejection | edit_annotation
    content: str
    created_at: datetime


class QuoteKickbackRequest(BaseModel):
    """Request body for kicking back a pending_approval quote to draft."""

    expected_quote_version_id: UUID | None = None
    overall_comment: str | None = None
    line_comments: list[dict] | None = (
        None  # [{"target_line_id": UUID, "content": str}]
    )


class QuoteKickbackResponse(BaseModel):
    """Response after kicking back a quote."""

    quote_id: UUID
    status: str  # 'draft'
    comment_count: int


# --- A3: Time-Limited Discounts ---


class QuoteApplyDiscountRequest(BaseModel):
    """Request body for applying a discount to a quote."""

    discount_pct: Decimal  # required — percentage (e.g., 10.00 = 10%)
    discount_expires_at: datetime | None = None  # optional expiry
    expected_quote_version_id: UUID | None = None  # staleness check


class QuoteApplyDiscountResponse(BaseModel):
    """Response after applying a discount to a quote."""

    quote_id: UUID
    discount_pct: Decimal
    discount_amount_cents: int
    discount_expires_at: datetime | None
    new_version_id: UUID


# --- A27: Save Quote as Template ---


class QuoteSaveAsTemplateRequest(BaseModel):
    """Request body for saving a quote as a reusable template."""

    name: str
    category: str | None = None
    style: str | None = None  # Defaults to 'component' if not specified


class QuoteSaveAsTemplateResponse(BaseModel):
    """Response after saving a quote as a template."""

    template_id: UUID
    name: str
    style: str
    category: str | None
    line_count: int


# --- A2: Quote Approval Workflow ---


class QuoteSubmitForApprovalResponse(BaseModel):
    """Response after a technician submits a quote for approval."""

    quote_id: UUID
    status: str  # 'pending_approval'
    submitted_at: datetime
    submitted_by_user_id: UUID


class QuoteApproveRequest(BaseModel):
    """Request body for approving a quote (staleness check)."""

    expected_quote_version_id: UUID | None = None


class QuoteApproveResponse(BaseModel):
    """Response after an owner approves a quote."""

    quote_id: UUID
    status: str  # 'approved'
    approved_at: datetime
    approved_by_user_id: UUID


class QuoteRejectRequest(BaseModel):
    """Request body for rejecting a quote (requires a comment)."""

    expected_quote_version_id: UUID | None = None
    overall_comment: str  # Required — rejection must have a reason


class QuoteRejectResponse(BaseModel):
    """Response after an owner rejects a quote."""

    quote_id: UUID
    status: str  # 'rejected'


# --- Quote View Analytics / Read Receipts (Task 1-E-2) ---


class QuoteAnalyticsEvent(BaseModel):
    """A single quote-link contact action event in the analytics timeline."""

    model_config = ConfigDict(from_attributes=True)

    action_name: str
    contact_name: str | None = None
    occurred_at: AwareDatetime
    ip_address: str | None = None
    user_agent: str | None = None


class QuoteAnalyticsResponse(BaseModel):
    """Wrapper containing the full sorted analytics timeline for a quote."""

    events: list[QuoteAnalyticsEvent]
