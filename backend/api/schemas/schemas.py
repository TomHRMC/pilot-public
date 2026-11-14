from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# Import address schema for nested site creation
from api.schemas.addresses import AddressCreate, AddressResponse


# --- Shared ---
class StatusResponse(BaseModel):
    id: UUID
    code: str
    name: str


# FIND-151-155: Typed soft-delete response (DELETE endpoints)
class SoftDeleteResponse(BaseModel):
    message: str
    id: UUID


class AddressBase(BaseModel):
    line1: str | None = None
    line2: str | None = None
    line3: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = "US"


# --- Customers ---
class CustomerCreate(BaseModel):
    type: str = "person"
    display_name: str
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    email: str | None = None
    mobile_phone: str | None = None
    # FIND-107 (B18): customer-level taxability override ('exempt' for tax-exempt orgs)
    taxability_code: str | None = None
    # DLC-1: SMS consent attestation fields
    # When True and mobile_phone is provided: triggers consent audit + double opt-in SMS.
    # Frontend must set True only when the checkbox was explicitly checked.
    sms_attestation_checked: bool = False
    # Client IP captured by the frontend — passed through to the audit log.
    # Optional; backend will use "unknown" if not provided.
    sms_consent_ip_address: str | None = None
    # B20: card-on-file requirement
    card_required: bool = False


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    type: str
    display_name: str
    first_name: str | None
    last_name: str | None
    company_name: str | None
    email: str | None
    mobile_phone: str | None
    is_active: bool
    # FIND-107 (B18): customer-level taxability override
    taxability_code: str | None = None
    # FIND-141: B11/A59 TCPA SMS consent fields — required for opt-in/opt-out UI
    sms_opted_out: bool = False
    sms_opt_out_at: AwareDatetime | None = None
    sms_opt_in_consent: bool = False
    sms_opt_in_at: AwareDatetime | None = None
    sms_opt_in_source: str | None = None
    # DLC-1: Consent attestation + verification status
    sms_verification_status: str = "unverified"
    # B20: card-on-file requirement
    card_required: bool = False


# --- Payment Methods (FIND-058) ---
class PaymentMethodCreate(BaseModel):
    """Request schema for creating a payment method via Stripe PSP token."""

    psp_payment_method_id: str  # Stripe PaymentMethod ID from frontend Stripe Elements
    payment_type_id: UUID  # Reference to payment_type lookup


class PaymentMethodResponse(BaseModel):
    """Response schema for payment method endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID | None
    tenant_id: UUID
    payment_type_id: UUID
    brand: str | None  # Card brand (Visa, Mastercard, etc.)
    psp_provider: str  # PSP provider name (stripe, etc.)
    psp_payment_method_id: str
    exp_month: int | None
    exp_year: int | None
    fingerprint: str | None  # Card fingerprint for matching
    last4: str | None  # Last 4 digits
    is_active: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


# --- Notification Preferences ---
class NotificationPreferenceResponse(BaseModel):
    """
    FIND-141: Response schema for PUT /notifications/preferences/{category_id}/{channel}.
    Replaces Dict[str, Any] so frontend codegen produces typed preference objects.
    """

    category_id: str
    channel: str
    enabled: bool
    scope: str  # 'user' | 'tenant' | 'system'


class NotificationPreferenceClearResponse(BaseModel):
    """
    FIND-141: Response schema for DELETE /notifications/preferences/{category_id}/{channel}.
    Replaces Dict[str, Any] so frontend codegen produces typed clear responses.
    """

    cleared: bool
    reverted_to_scope: str  # 'tenant' | 'system'


# --- Sites ---
class SiteCreate(BaseModel):
    customer_id: UUID
    name: str | None = None
    notes: str | None = None
    jurisdiction_code: str | None = None
    address: AddressCreate | None = None  # Optional nested address (Gap #7)
    # CLASS-B1: site_type — omit on create to get customer-type-aware default
    site_type: str | None = None


class SiteUpdate(BaseModel):
    """CLASS-B1: Mutable site fields. All optional."""

    name: str | None = None
    notes: str | None = None
    jurisdiction_code: str | None = None
    site_type: str | None = None


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    name: str | None
    notes: str | None
    jurisdiction_code: str | None
    is_active: bool
    address: AddressResponse | None = None  # Include primary address if exists (Gap #7)
    # CLASS-B1: site classification
    site_type: str | None = None


# --- Jobs ---
# CLASS-B1: Valid priority values
JOB_PRIORITY_VALUES = {"standard", "urgent", "emergency"}
# CLASS-B1: Valid site_type values
SITE_TYPE_VALUES = {"commercial", "residential", "industrial"}


class JobCreate(BaseModel):
    customer_id: UUID
    site_id: UUID
    quote_id: UUID | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
    external_calendar_event_id: str | None = None
    # We'll set a default status in the route
    # CLASS-B1: Priority and job type classification
    priority: str | None = None  # defaults to 'standard' when omitted
    job_type_id: UUID | None = None
    # JOB-UI-B1: Optional human-readable title; defaults from quote.title when job linked to quote
    title: str | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    site_id: UUID
    status_id: UUID
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    estimated_duration_minutes: int | None
    external_calendar_event_id: str | None
    actual_labor_cost_cents: int
    actual_material_cost_cents: int
    actual_profit_cents: int
    is_active: bool
    # B19: Human-readable job number + enriched detail fields
    job_number: str = ""
    status_code: str | None = None  # from job_status.code JOIN
    site_name: str | None = None  # from site.name JOIN
    customer_name: str | None = None  # from customer.display_name JOIN
    # B21: Link back to the recurrence rule that spawned this job (NULL = manually created)
    recurrence_rule_id: UUID | None = None
    # CLASS-B1: Priority and job type classification
    priority: str = "standard"
    job_type_id: UUID | None = None
    job_type_code: str | None = None  # enriched from job_type JOIN
    job_type_label: str | None = None  # enriched from job_type JOIN
    # JOB-UI-B1: Human-readable title + linked quote version
    title: str | None = None
    quote_version_id: UUID | None = None


class JobListItem(BaseModel):
    """Lightweight job representation for list views (mobile Jobs tab).

    Extended vs JobResponse: adds status_code (from job_status JOIN) and
    customer_name (from customer JOIN). Added by MOB-B1-BE.
    B19: Adds job_number.
    CLASS-B1: Adds priority, job_type_code, job_type_label.
    JOB-UI-B1: Adds title.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    site_id: UUID
    status_id: UUID
    status_code: str | None = None  # from job_status.code JOIN
    customer_name: str | None = None  # from customer.display_name JOIN
    job_number: str | None = None  # B19: from job.job_number
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
    # CLASS-B1: Priority classification
    priority: str = "standard"
    job_type_id: UUID | None = None
    job_type_code: str | None = None
    job_type_label: str | None = None
    # JOB-UI-B1: Human-readable title
    title: str | None = None


class JobUpdate(BaseModel):
    """Request to update mutable fields on an existing job.

    All fields are optional — only send the fields you want to change.
    quote_id is intentionally excluded — quote linkage set at job creation.
    CLASS-B1: Adds priority and job_type_id.
    JOB-UI-B1: Adds title + status_code (editable with transition validation).
      Valid status codes: draft → scheduled → in_progress → completed; any → cancelled.
      Illegal backward transitions (e.g. completed → draft) return RFC 7807 422.
    """

    customer_id: UUID | None = None
    site_id: UUID | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
    # CLASS-B1: Priority and job type classification
    priority: str | None = None
    job_type_id: UUID | None = None
    # JOB-UI-B1: Human-readable title (partial update — only sent fields are changed)
    title: str | None = None
    # JOB-UI-B1: Status transition — validated against allowed forward-transitions
    status_code: str | None = None


# CLASS-B1: Job type lookup response
class JobTypeResponse(BaseModel):
    """Response for a single job type entry.

    is_tenant_override=True when this row belongs to the requesting tenant
    (i.e. the tenant row shadowed the platform default with the same code).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    label: str
    sort_order: int
    is_active: bool
    is_tenant_override: bool = False


# --- Job Costing ---
class JobTimeEntryCreate(BaseModel):
    started_at: datetime
    ended_at: datetime | None = None
    hours: float | None = None
    notes: str | None = None
    hourly_rate_cents: int | None = None  # B20/A90: Voice handlers pass burdened rate
    # User ID defaults to current user making the request

    # B7a/A37: Offline capture timestamp — send when submitting from offline queue
    client_capture_at: datetime | None = None

    # B3/A14: ETC (Estimate-to-Complete) fields — optional at clock-in, captured at clock-out
    hours_remaining_estimate: float | None = None
    hours_remaining_was_overridden: bool | None = None
    override_note: str | None = None
    quote_line_id: UUID | None = None


class JobTimeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: datetime | None
    hours: float | None
    notes: str | None
    hourly_rate_cents: int
    total_cost_cents: int

    # B3/A14: ETC fields in response
    hours_remaining_estimate: float | None = None
    hours_remaining_was_overridden: bool | None = None
    override_note: str | None = None
    quote_line_id: UUID | None = None
    etc_captured_at: datetime | None = None


class JobExpenseCreate(BaseModel):
    job_expense_category_code: str
    description: str
    vendor_name: str | None = None
    incurred_at: datetime
    cost_cents: int
    is_billable: bool = True
    # B7a/A37 + FIND-050: offline capture timestamp — send when submitting from offline queue
    client_capture_at: datetime | None = None


class JobExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    job_id: UUID
    job_expense_category_code: str
    description: str
    vendor_name: str | None
    incurred_at: datetime
    cost_cents: int
    markup_pct: float | None
    markup_amt_cents: int | None
    billable_cents: int
    is_billable: bool


# --- Change Orders ---
class ChangeOrderCreate(BaseModel):
    description: str
    # B7a/A37 + FIND-050: offline capture timestamp — send when submitting from offline queue
    client_capture_at: datetime | None = None


class ChangeOrderUpdate(BaseModel):
    description: str | None = None
    is_active: bool | None = None


class ChangeOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    job_id: UUID
    description: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    is_active: bool


# --- Change Order Lines ---
class ChangeOrderLineCreate(BaseModel):
    position: int
    qco_line_type_id: UUID
    description: str
    quantity: float = 1.0
    unit_price_cents: int = 0
    unit: str | None = None
    pricebook_item_id: UUID | None = None
    supplier_id: UUID | None = None
    supplier_item_id: UUID | None = None
    taxability_code: str | None = None


class ChangeOrderLineUpdate(BaseModel):
    position: int | None = None
    description: str | None = None
    quantity: float | None = None
    unit_price_cents: int | None = None
    unit: str | None = None
    is_active: bool | None = None


class ChangeOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    change_order_id: UUID
    position: int
    qco_line_type_id: UUID
    description: str
    quantity: float
    unit: str | None
    unit_price_cents: int
    subtotal_cents: int
    total_cents: int
    is_active: bool


# --- Catalog ---
class SupplierItemCreate(BaseModel):
    supplier_id: UUID
    sku: str
    name: str
    description: str | None = None
    uom_id: UUID
    category_id: UUID | None = None
    taxability_code: str | None = None


class SupplierItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None
    supplier_id: UUID
    sku: str
    name: str
    description: str | None
    uom_id: UUID
    is_active: bool


class PricingCacheResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    supplier_id: UUID
    sku: str
    price_cents: int
    currency: str
    expires_at: datetime


# --- Invoice Public Link (Task 1-D-3) ---
class InvoiceSendRequest(BaseModel):
    """Request body for POST /api/v1/invoices/{id}/send — generates a public payment link."""

    contact_id: UUID | None = None
    expires_in_days: int | None = 30  # default 30-day expiry; None = no expiry
    max_uses: int = 0  # 0 = unlimited


class InvoicePublicLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    contact_id: UUID | None
    # FIND-143: signed_token is the pre-hash value used in the URL path.
    # token_hash (SHA-256) is the internal DB lookup key — never expose to frontend.
    signed_token: str
    expires_at: datetime | None
    max_uses: int
    used_count: int
    status: str
    last_used_at: datetime | None
    created_at: datetime


class PublicInvoiceResponse(BaseModel):
    """Unauthenticated invoice payload returned via public token."""

    model_config = ConfigDict(from_attributes=True)

    invoice_id: UUID
    invoice_number: str
    tenant_id: UUID
    customer_id: UUID
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    balance_due_cents: int
    currency: str
    issued_at: datetime | None
    due_at: datetime | None
    customer_notes: str | None
    terms_and_conditions: str | None
    link_status: str
    link_expires_at: datetime | None


class PublicInvoicePayRequest(BaseModel):
    """Request body for POST /api/v1/public/invoices/{token}/pay."""

    amount_cents: int
    payment_method_id: UUID  # FK to payment_method table (created via PSP tokenization)
    payment_status_id: UUID  # FK to payment_status — caller supplies (e.g. 'completed')
    psp_payment_id: str | None = None  # PSP confirmation / charge ID
    reference: str | None = None  # additional external reference
    # FIND-142: capture why a partial payment is being made (required if amount < balance)
    customer_payment_comment: str | None = None


class PublicInvoicePayResponse(BaseModel):
    """Response confirming payment was recorded."""

    message: str
    invoice_id: UUID
    amount_cents: int
    balance_due_cents: int


# --- Authenticated Invoice CRUD (FIND-076) ---


class InvoiceSummary(BaseModel):
    """Summary of invoice for list response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_number: str
    customer_id: UUID
    customer_name: str | None = None  # B18 — from customer JOIN in _list_invoices_impl
    site_id: UUID
    status_id: UUID
    status_code: str
    issued_at: datetime | None
    due_at: datetime | None
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    balance_due_cents: int
    currency: str
    quote_id: UUID | None
    job_id: UUID | None
    created_at: datetime
    updated_at: datetime
    # B20: Invoice builder fields
    payment_terms: str | None = None
    billing_mode: str = "line_item"
    progress_pct: Decimal | None = None
    internal_memo: str | None = None


# --- Paginated Response (UI-FIX-1C) ---
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated list response — all list endpoints return this shape."""

    items: list[T]
    total: int
    limit: int
    offset: int


# Concrete paginated types for OpenAPI generation (FastAPI requires concrete types)
class PaginatedCustomerResponse(PaginatedResponse[CustomerResponse]):
    pass


class PaginatedJobListResponse(PaginatedResponse[JobListItem]):
    pass


# NOTE: PaginatedCatalogResponse is defined below after PricebookItemResponse


class InvoiceListResponse(BaseModel):
    """Paginated list of invoices."""

    items: list[InvoiceSummary]
    total: int
    limit: int
    offset: int


class InvoiceLineResponse(BaseModel):
    """Individual line item in an invoice."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    source_type: str
    source_id: UUID | None
    position: int
    qco_line_type_id: UUID | None
    pricebook_item_id: UUID | None
    description: str
    quantity: float
    unit: str | None
    unit_price_cents: int
    taxability_code: str | None
    tax_rate_pct: float | None = None
    tax_basis_cents: int | None = None
    tax_amount_cents: int | None = None
    tax_jurisdiction_code: str | None = None
    tax_as_of: datetime | None = None
    tax_source: str | None = None
    subtotal_cents: int
    total_cents: int
    is_active: bool


class PaymentSummaryResponse(BaseModel):
    """Payment summary embedded in InvoiceResponse — not standalone.

    CE-1: Extended with variance-resolution fields so the web overpayment
    banner can read resolution state from the invoice detail payload.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    amount_cents: int
    paid_at: datetime | None
    paid_via: str | None
    psp_provider: str | None
    customer_payment_comment: str | None
    status_id: UUID
    amount_variance_cents: int | None = None
    variance_resolution: str | None = None
    variance_resolution_note: str | None = None
    variance_resolved_at: datetime | None = None
    variance_resolved_by_user_id: UUID | None = None


class InvoiceResponse(BaseModel):
    """Full invoice detail including line items."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    tenant_id: UUID
    invoice_number: str
    customer_id: UUID
    site_id: UUID
    status_id: UUID
    status_code: str
    quote_id: UUID | None
    job_id: UUID | None
    idempotency_key: str | None
    issued_at: datetime | None
    due_at: datetime | None
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    balance_due_cents: int
    currency: str
    customer_notes: str | None
    terms_and_conditions: str | None
    pdf_object_key: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None
    lines: list[InvoiceLineResponse]
    payments: list[PaymentSummaryResponse] = []
    # B20: Invoice builder fields
    payment_terms: str | None = None
    billing_mode: str = "line_item"
    progress_pct: Decimal | None = None
    internal_memo: str | None = None
    # BILLING-B1: draw invoice linkage (set on generated `progress` invoices)
    payment_schedule_line_id: UUID | None = None


class InvoiceLineItemCreate(BaseModel):
    """A custom (ad_hoc) invoice line supplied at creation time.

    PLP-FIX-1: enables the invoice builder's custom-line UI. Lines are
    persisted as ``InvoiceLine`` rows with ``source_type='ad_hoc'``.
    """

    description: str
    quantity: Decimal = Decimal("1")
    unit: str | None = None
    unit_price_cents: int
    qco_line_type_code: str | None = None  # default 'misc' resolved in impl

    @field_validator("description")
    @classmethod
    def _description_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description must be non-empty")
        if len(v) > 500:
            raise ValueError("description must be ≤ 500 characters")
        return v

    @field_validator("quantity")
    @classmethod
    def _quantity_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v

    @field_validator("unit_price_cents")
    @classmethod
    def _price_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("unit_price_cents must be >= 0")
        return v


class InvoiceCreate(BaseModel):
    """Request to create a new invoice from quote, job, or standalone mode.

    PLP-FIX-1: added ``customer_id``/``site_id`` (standalone mode) and
    ``line_items[]`` (custom ad_hoc lines, appendable in all modes).
    """

    quote_id: UUID | None = None
    job_id: UUID | None = None
    # PLP-FIX-1: standalone mode — customer + site supplied directly
    customer_id: UUID | None = None
    site_id: UUID | None = None
    # PLP-FIX-1: custom ad_hoc lines (appended after source-derived lines)
    line_items: list[InvoiceLineItemCreate] | None = None
    customer_notes: str | None = None
    terms_and_conditions: str | None = None
    due_at: datetime | None = None
    issued_at: datetime | None = None
    idempotency_key: str | None = None
    # B20: Invoice builder fields
    payment_terms: str | None = None  # 'due_on_receipt'|'net_15'|'net_30'|'custom_date'
    billing_mode: str = "line_item"  # 'line_item'|'progress'
    progress_pct: Decimal | None = (
        None  # 0.00-100.00; required when billing_mode='progress'
    )
    internal_memo: str | None = None  # internal note, not shown on customer PDF

    @model_validator(mode="after")
    def validate_billing_mode_progress_pct(self) -> "InvoiceCreate":
        if self.billing_mode == "progress":
            if self.progress_pct is None:
                raise ValueError(
                    "progress_pct is required when billing_mode is 'progress'"
                )
            if not (0 <= self.progress_pct <= 100):
                raise ValueError("progress_pct must be between 0 and 100")
        return self


# B20: Billable items schemas for invoice builder pre-fill
class BillableTimeEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tech_name: str | None = None  # user.display_name from JOIN
    started_at: AwareDatetime
    ended_at: AwareDatetime | None = None
    hours: Decimal | None = None
    hourly_rate_cents: int
    total_cost_cents: int
    notes: str | None = None
    is_already_invoiced: bool = False  # MVP: always False for time entries


class BillableExpense(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    cost_cents: int
    billable_cents: int
    is_billable: bool
    is_already_invoiced: bool  # True when job_expense.invoice_line_id IS NOT NULL
    incurred_at: AwareDatetime


class BillableItemsResponse(BaseModel):
    job_id: UUID
    job_number: str | None = None
    customer_name: str | None = None
    time_entries: list[BillableTimeEntry]
    expenses: list[BillableExpense]


class PaymentRecordRequest(BaseModel):
    """Request to record a manual payment against an invoice."""

    amount_cents: int
    paid_via: Literal["stripe", "check", "bank_transfer", "other"]
    payment_method_id: UUID
    payment_status_id: UUID
    paid_at: datetime | None = None
    reference: str | None = None
    idempotency_key: str | None = None
    comment: str | None = None


class PaymentResponse(BaseModel):
    """Response confirming payment was recorded.

    CE-1: Extended with variance-resolution fields (additive, non-breaking).
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    invoice_id: UUID
    tenant_id: UUID
    amount_cents: int
    paid_via: str
    balance_due_cents: int
    amount_variance_cents: int | None
    status_id: UUID
    paid_at: datetime | None
    idempotency_key: str | None
    created_at: datetime
    # CE-1: Overpayment variance resolution (record-keeping only)
    variance_resolution: str | None = None
    variance_resolution_note: str | None = None
    variance_resolved_at: datetime | None = None
    variance_resolved_by_user_id: UUID | None = None


class ResolveVarianceRequest(BaseModel):
    """Request body for POST /api/v1/payments/{payment_id}/resolve-variance.

    CE-1 §D.4 — record-keeping only (no Stripe refund execution).
    """

    resolution: Literal["credit", "refund_offline", "writeoff"]
    note: str | None = Field(default=None, max_length=1000)


# --- Admin: Tenant Feature Overrides (Task 1-E-1) ---


class TenantOverrideCreate(BaseModel):
    """Input schema for creating or upserting a tenant product-feature override."""

    product_feature_code: str
    limit_quantity: int | None = None
    included_quantity: int | None = None
    overage_price_cents: int | None = None
    overage_cap_per_period: int | None = None
    alert_threshold_pct: int | None = None
    enabled: bool = True


class TenantOverrideResponse(TenantOverrideCreate):
    """Output schema for a tenant product-feature override, including audit fields."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


# --- Scheduling: Conflict Detection ---


class ConflictCheckRequest(BaseModel):
    """Proposed job slot to validate for a specific technician.

    Validates:
    1. No overlap with the tech's active PTO / unavailable blocks.
    2. No overlap with the tech's other active scheduled jobs (double-booking).
    """

    tech_user_id: UUID
    proposed_start: datetime
    proposed_end: datetime
    exclude_job_id: UUID | None = (
        None  # ignore this job when checking double-booking (edit case)
    )


class ConflictDetail(BaseModel):
    """Describes a single feasibility conflict."""

    conflict_type: str  # 'availability_block' | 'double_booking'
    description: str
    conflicting_entity_id: UUID | None = None  # tech_availability.id or job.id


class ConflictCheckResponse(BaseModel):
    """Result of the feasibility check for a proposed job slot."""

    is_feasible: bool
    tech_user_id: UUID
    proposed_start: datetime
    proposed_end: datetime
    conflicts: list[ConflictDetail]


# --- Scheduling: Dispatch Board ---


class DispatchBoardJobEntry(BaseModel):
    """Minimal job summary included in the dispatch board payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    site_id: UUID
    status_id: UUID
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    estimated_duration_minutes: int | None
    external_calendar_event_id: str | None
    is_active: bool
    eta_minutes: int | None = None
    # ── DISPATCH-B1 additions ──────────────────────────────────────────────
    version: int  # optimistic lock → FE sends as expected_job_version
    primary_assignment_id: UUID | None = (
        None  # active primary JobTechAssignment.id (null = unassigned)
    )
    assignment_version: int | None = None  # → FE sends as expected_assignment_version
    job_number: str  # label (until JOB-UI-B1 adds title)
    customer_name: str | None = None  # enrichment — retires FE second-fetch
    site_name: str | None = (
        None  # site.name — dispatcher-facing label (e.g. "North Warehouse")
    )
    site_address: str | None = None  # enrichment
    title: str | None = None  # FORWARD-COMPAT: null now; JOB-UI-B1 populates
    # ── DISPATCH-B1.25 additions ───────────────────────────────────────────
    assignment_role: str | None = None  # role of THIS placement ('primary' in jobs[];
    # 'helper'/etc in commitments; None = unassigned)
    # ── CLASS-B1 additions ────────────────────────────────────────────────
    priority: str = "standard"  # from job.priority (already on the row)
    customer_type: str | None = None  # from customer.type (batch-loaded)
    site_type: str | None = None  # from site.site_type (batch-loaded)
    job_type_code: str | None = None  # from job_type batch-load
    job_type_label: str | None = None  # from job_type batch-load


class DispatchBoardTechGroup(BaseModel):
    """All jobs assigned (as primary) to a single technician within the query window.

    ``id`` / ``tech_id`` — UUID of the technician's user record (both present for
    backward compatibility; ``id`` is the canonical field the React layer reads).
    ``name`` — full name derived from ``first_name + last_name`` at query time.
    ``display_color`` — hex color for the dispatch board avatar (from ``user.display_color``).
    ``avatar_url`` — signed S3 URL or null (from ``user.profile_photo_s3_key``).
    eta_minutes_to_first_job: ETA in minutes from tech's current location to their first job
    (nullable if tech has no GPS coordinates on file).
    """

    tech_id: UUID
    id: UUID  # alias of tech_id — required by DispatchBoardTech React type
    name: str
    display_color: str | None = None
    avatar_url: str | None = None
    jobs: list[DispatchBoardJobEntry]
    # ── DISPATCH-B1.25 additions ───────────────────────────────────────────
    additional_job_commitments: list[
        DispatchBoardJobEntry
    ] = []  # non-primary assignments for this tech
    eta_minutes_to_first_job: int | None = None


class DispatchBoardResponse(BaseModel):
    """Structured payload for the dispatch board calendar view.

    ``techs``      — one entry per tech with at least one assigned job in the window.
    ``unassigned`` — jobs that have no active primary assignment in the window.
    """

    start_date: datetime
    end_date: datetime
    techs: list[DispatchBoardTechGroup]
    unassigned: list[DispatchBoardJobEntry]


# --- Scheduling: Job Schedule Update ---


class JobScheduleUpdate(BaseModel):
    """Partial update for a job's scheduling fields only.

    All fields are optional — only supplied fields are changed.
    Constraint: if either starts or end is supplied, both must be present
    and end must be after start (validated at the route layer).
    """

    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    estimated_duration_minutes: int | None = None
    external_calendar_event_id: str | None = None


# --- Scheduling: JobTechAssignment ---


class JobTechAssignmentCreate(BaseModel):
    """Assign a technician to a job.

    Upsert semantics for ``role='primary'``: the existing active primary
    assignment (if any) will be soft-deleted before the new one is created.
    """

    user_id: UUID
    role: str = "primary"  # 'primary' | 'helper'
    ordinal: int = 1
    assigned_by_user_id: UUID | None = None  # defaults to current user if None


class JobTechAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    job_id: UUID
    user_id: UUID
    assigned_by_user_id: UUID
    role: str
    ordinal: int
    assigned_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None


# --- Scheduling: TechAvailability ---


class TechAvailabilityCreate(BaseModel):
    """Request body for creating a tech availability record.

    Rules:
    - ``working_hours``: ``recurrence_rrule`` must be provided; ``starts_at``/``ends_at`` are None.
    - ``pto`` / ``unavailable``: ``starts_at`` AND ``ends_at`` must be provided; ``ends_at > starts_at``.
    """

    user_id: UUID
    availability_type: str  # 'working_hours' | 'pto' | 'unavailable'
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurrence_rrule: str | None = None
    notes: str | None = None


class TechAvailabilityUpdate(BaseModel):
    """Partial update — only supplied fields are changed."""

    availability_type: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurrence_rrule: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class TechAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID
    availability_type: str
    starts_at: datetime | None
    ends_at: datetime | None
    recurrence_rrule: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None


# --- Job Notes (FIND-064) ---


class JobNotesCreate(BaseModel):
    """Request schema for creating job notes via PUT (upsert)."""

    notes: str


class JobNotesUpdate(BaseModel):
    """Request schema for updating job notes via PUT (upsert)."""

    notes: str


class JobNotesResponse(BaseModel):
    """Response schema for job notes endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    job_id: UUID
    notes: str
    audio_object_key: str | None = None
    customer_visible: bool
    client_capture_at: AwareDatetime | None = None
    server_received_at: AwareDatetime | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    created_by: UUID | None


# --- Category-Specific Markup Management (B20/A90) ---


class TenantMarkupVersionCreate(BaseModel):
    """Request schema for creating/updating a markup version via temporal supersession.

    Implements the temporal versioning pattern:
    - When creating/updating a markup for a category, the new effective_from date
      closes the current active row and opens a new period.
    - The GIST exclusion constraint prevents overlapping periods.
    """

    job_expense_category_code: str  # FK → job_expense_category.code; must exist
    markup_pct: float  # Required; e.g., 20.0 = 20%
    markup_amt_cents: int | None = None  # Optional flat markup in cents
    effective_from: AwareDatetime  # UTC datetime; lower bound for new row; closes current row's upper

    @field_validator("markup_pct")
    @classmethod
    def validate_markup_pct(cls, v: float) -> float:
        """Ensure markup percentage is non-negative."""
        if v < 0:
            raise ValueError("markup_pct cannot be negative")
        return v

    @field_validator("effective_from")
    @classmethod
    def validate_effective_from(cls, v: AwareDatetime) -> AwareDatetime:
        """Ensure effective_from is not more than 90 days in the past."""
        now = datetime.now(v.tzinfo) if v.tzinfo else datetime.now()
        lookback_limit = now - timedelta(days=90)
        if v < lookback_limit:
            raise ValueError("effective_from cannot be more than 90 days in the past")
        return v


class TenantMarkupVersionResponse(BaseModel):
    """Response schema for a single markup version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: UUID
    job_expense_category_code: str
    markup_pct: float  # Numeric(7,4) — e.g., 20.0 = 20%
    markup_amt_cents: int | None = None  # Flat markup in cents; None if not set
    valid_period_lower: AwareDatetime  # Lower bound of tstzrange (always inclusive '[')
    valid_period_upper: AwareDatetime | None = (
        None  # Upper bound; None = open (infinity)
    )
    recorded_at: AwareDatetime
    created_by: UUID | None = None


class TenantMarkupVersionListResponse(BaseModel):
    """Response schema for listing active markups."""

    items: list[TenantMarkupVersionResponse]
    total: int


class TenantMarkupVersionHistoryResponse(BaseModel):
    """Response schema for markup history (audit trail)."""

    category_code: str
    items: list[TenantMarkupVersionResponse]
    total: int


# --- LOTO Confirmation (B20/A89) ---


class LotoConfirmationCreate(BaseModel):
    """Request schema for creating a LOTO confirmation event (online or offline sync).

    B20/A89: confirmed_at is the canonical confirmation time supplied by the client.
    client_capture_at is the device-side timestamp (offline pattern).
    idempotency_uuid is the client-side dedup UUID.
    """

    confirmed_at: AwareDatetime
    client_capture_at: AwareDatetime | None = None
    idempotency_uuid: UUID


class LotoConfirmationRead(BaseModel):
    """Response schema for LOTO confirmation records."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    job_id: UUID
    user_id: UUID
    confirmed_at: AwareDatetime
    client_capture_at: AwareDatetime | None = None
    server_received_at: AwareDatetime | None = None
    is_active: bool
    created_at: AwareDatetime


# ============================================================================
# FIND-171: Pricebook Item CRUD + Temporal Price Management
# ============================================================================


class PricebookItemCurrentPriceResponse(BaseModel):
    """Response schema for a single pricebook_item_version row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    default_unit_price_cents: int
    valid_period_lower: datetime | None = None  # lower bound of tstzrange
    valid_period_upper: datetime | None = None  # upper bound (None = open-ended)
    recorded_at: datetime


class PricebookItemResponse(BaseModel):
    """Response schema for a pricebook_item row with optional current price."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    sku: str
    name: str
    description: str | None = None
    uom_id: UUID | None = None
    taxability_code: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    current_price: PricebookItemCurrentPriceResponse | None = None


class PaginatedCatalogResponse(PaginatedResponse[PricebookItemResponse]):
    """Paginated pricebook items response (UI-FIX-1C)."""

    pass


class PricebookItemCreate(BaseModel):
    """Request schema for POST /api/v1/catalog/pricebook."""

    sku: str
    name: str
    description: str | None = None
    uom_id: UUID | None = None
    taxability_code: str | None = None
    initial_price_cents: int  # required; initial price in cents
    effective_from: datetime | None = None  # defaults to now() if omitted


class PricebookItemPatch(BaseModel):
    """Request schema for PATCH /api/v1/catalog/pricebook/{item_id}."""

    name: str | None = None
    description: str | None = None
    taxability_code: str | None = None
    is_active: bool | None = None
    # sku is intentionally excluded — immutable after creation


class PricebookItemPriceCreate(BaseModel):
    """Request schema for POST /api/v1/catalog/pricebook/{item_id}/price."""

    unit_price_cents: int  # required; new price in cents
    effective_from: datetime  # required; UTC-aware datetime


# --- Stripe Connect (UI-FIX-2F) ---
class StripeConnectStatusResponse(BaseModel):
    """Response for GET /api/v1/settings/billing/stripe-connect/status"""

    connected: bool
    account_id: str | None = None  # Stripe acct_XXX (shown masked in UI)
    account_name: str | None = None  # From stripe.Account.retrieve()
    charges_enabled: bool = False  # True once onboarding is complete
    payouts_enabled: bool = False  # True once bank account is added


class StripeConnectOnboardResponse(BaseModel):
    """Response for POST /api/v1/settings/billing/stripe-connect/onboard"""

    account_link_url: str  # Stripe-hosted URL — frontend redirects browser here
    expires_at: int  # Unix timestamp — Account Link expires in ~10 min


class StripeConnectDisconnectResponse(BaseModel):
    """Response for DELETE /api/v1/settings/billing/stripe-connect"""

    disconnected: bool = True
    message: str = (
        "Stripe account disconnected. Customers will see manual payment instructions."
    )


# ============================================================================
# BILLING-B1: Payment Schedule Orchestration (progress / milestone billing)
# ============================================================================


class PaymentScheduleLineCreate(BaseModel):
    """Request schema for a single draw on a payment schedule.

    Conditional-NOT-NULL is enforced by a ``@model_validator`` mirroring the DB
    CHECKs (``psl_basis_amount_chk``, ``psl_trigger_detail_chk``) so a bad
    basis/trigger combo returns a clean 422 before hitting the DB constraint.
    """

    sequence: int
    label: str
    basis: Literal["percent", "fixed_amount"]
    percent: Decimal | None = None
    amount_cents: int | None = None
    trigger_type: Literal["manual", "date", "milestone"] = "manual"
    trigger_date: date | None = None
    milestone_label: str | None = None

    @model_validator(mode="after")
    def validate_basis_amount(self) -> "PaymentScheduleLineCreate":
        """Mirror psl_basis_amount_chk: percent↔percent set, fixed_amount↔amount_cents set."""
        if self.basis == "percent":
            if self.percent is None or self.amount_cents is not None:
                raise ValueError(
                    "When basis='percent', percent must be set and amount_cents must be null."
                )
            if not (Decimal("0") <= self.percent <= Decimal("100")):
                raise ValueError("percent must be between 0 and 100")
        elif self.basis == "fixed_amount":
            if self.amount_cents is None or self.percent is not None:
                raise ValueError(
                    "When basis='fixed_amount', amount_cents must be set and percent must be null."
                )
            if self.amount_cents < 0:
                raise ValueError("amount_cents cannot be negative")
        return self

    @model_validator(mode="after")
    def validate_trigger_detail(self) -> "PaymentScheduleLineCreate":
        """Mirror psl_trigger_detail_chk: trigger_type drives which detail is required."""
        if self.trigger_type == "date" and self.trigger_date is None:
            raise ValueError("trigger_date is required when trigger_type='date'")
        if self.trigger_type == "milestone" and not self.milestone_label:
            raise ValueError(
                "milestone_label is required when trigger_type='milestone'"
            )
        if self.trigger_type == "manual" and (
            self.trigger_date is not None or self.milestone_label is not None
        ):
            raise ValueError(
                "trigger_date and milestone_label must be null when trigger_type='manual'"
            )
        return self


class PaymentScheduleLineUpdate(BaseModel):
    """Partial update for a draw (draft-only). All fields optional."""

    sequence: int | None = None
    label: str | None = None
    basis: Literal["percent", "fixed_amount"] | None = None
    percent: Decimal | None = None
    amount_cents: int | None = None
    trigger_type: Literal["manual", "date", "milestone"] | None = None
    trigger_date: date | None = None
    milestone_label: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_basis_amount(self) -> "PaymentScheduleLineUpdate":
        """Same conditional-NOT-NULL as create, but only when fields are supplied."""
        if self.basis == "percent":
            if self.amount_cents is not None:
                raise ValueError("amount_cents must be null when basis='percent'")
        elif self.basis == "fixed_amount":
            if self.percent is not None:
                raise ValueError("percent must be null when basis='fixed_amount'")
        # Cross-field consistency when both basis and the amount field are supplied
        if self.basis == "percent" and self.percent is not None:
            if not (Decimal("0") <= self.percent <= Decimal("100")):
                raise ValueError("percent must be between 0 and 100")
        if self.basis == "fixed_amount" and self.amount_cents is not None:
            if self.amount_cents < 0:
                raise ValueError("amount_cents cannot be negative")
        return self

    @model_validator(mode="after")
    def validate_trigger_detail(self) -> "PaymentScheduleLineUpdate":
        if self.trigger_type == "date" and self.trigger_date is None:
            raise ValueError("trigger_date is required when trigger_type='date'")
        if self.trigger_type == "milestone" and not self.milestone_label:
            raise ValueError(
                "milestone_label is required when trigger_type='milestone'"
            )
        return self


class PaymentScheduleLineResponse(BaseModel):
    """Response schema for a single draw, including the computed resolved amount."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    tenant_id: UUID
    payment_schedule_id: UUID
    sequence: int
    label: str
    basis: str
    percent: Decimal | None = None
    amount_cents: int | None = None
    trigger_type: str
    trigger_date: date | None = None
    milestone_label: str | None = None
    invoice_id: UUID | None = None
    status: str
    is_active: bool
    # Computed: percent resolved against contract_total_cents, or the fixed amount_cents
    resolved_amount_cents: int = 0


class PaymentScheduleCreate(BaseModel):
    """Request to create a draft payment schedule with optional inline draws."""

    quote_id: UUID | None = None
    job_id: UUID | None = None
    customer_id: UUID
    site_id: UUID
    contract_total_cents: int
    basis_default: Literal["percent", "fixed_amount"] = "percent"
    lines: list[PaymentScheduleLineCreate] = []
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def validate_quote_or_job(self) -> "PaymentScheduleCreate":
        """At least one of quote_id or job_id must be provided (XOR not required)."""
        if self.quote_id is None and self.job_id is None:
            raise ValueError("At least one of quote_id or job_id must be provided")
        if self.contract_total_cents < 0:
            raise ValueError("contract_total_cents cannot be negative")
        return self


class PaymentScheduleUpdate(BaseModel):
    """Draft-only header edit (contract_total_cents, basis_default)."""

    contract_total_cents: int | None = None
    basis_default: Literal["percent", "fixed_amount"] | None = None

    @model_validator(mode="after")
    def validate_total(self) -> "PaymentScheduleUpdate":
        if self.contract_total_cents is not None and self.contract_total_cents < 0:
            raise ValueError("contract_total_cents cannot be negative")
        return self


class PaymentScheduleActivateRequest(BaseModel):
    """Empty body model for POST /payment-schedules/{id}/activate (forward-compat)."""

    pass


class DrawInvoiceGenerateRequest(BaseModel):
    """Request body for POST /payment-schedules/{id}/lines/{line_id}/generate-invoice."""

    idempotency_key: str | None = None


class PaymentScheduleResponse(BaseModel):
    """Full schedule response with lines + computed reconciliation totals."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    tenant_id: UUID
    quote_id: UUID | None = None
    job_id: UUID | None = None
    customer_id: UUID
    site_id: UUID
    contract_total_cents: int
    status: str
    basis_default: str
    is_active: bool
    lines: list[PaymentScheduleLineResponse] = []
    # Computed: sum of active lines' resolved amounts
    scheduled_total_cents: int = 0
    # Computed: contract_total_cents - scheduled_total_cents (must be 0 to activate)
    residual_cents: int = 0


class PaymentScheduleListItem(BaseModel):
    """Lightweight schedule summary for list views."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    tenant_id: UUID
    quote_id: UUID | None = None
    job_id: UUID | None = None
    customer_id: UUID
    site_id: UUID
    contract_total_cents: int
    status: str
    basis_default: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaymentScheduleListResponse(BaseModel):
    """Paginated list of payment schedules."""

    items: list[PaymentScheduleListItem]
    total: int
    limit: int
    offset: int
