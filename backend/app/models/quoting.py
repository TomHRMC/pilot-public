import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import (
    CITEXT,
    INET,
    JSONB,
    TSTZRANGE,
    ExcludeConstraint,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
)
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, MachineLogMixin, StandardAuditMixin


# --- Dictionaries & Lookups ---
class QuoteStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_status"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_quote_status_tenant_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_terminal: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1 Task 4: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QcoLineType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "qco_line_type"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # FIND-070 (B18): QB item name hint for line type mapping at QB connect time.
    # Used to search tenant's QB Items catalog by name → resolve QB item_id per tenant.
    # NULL = use generic "Services" fallback. System rows seeded: see migration.
    qb_item_name_hint: str | None = Field(default=None)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class TaxabilityCode(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "taxability_code"

    code: str = Field(primary_key=True)
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QuoteLinkStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_link_status"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_quote_link_status_tenant_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1 Task 4: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Pricebook ---
class PricebookItem(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "pricebook_item"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_pricebook_item_tenant_sku"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    sku: str = Field(nullable=False)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)

    uom_id: uuid.UUID | None = Field(
        default=None, foreign_key="supplier_item_uom.id", index=True
    )
    taxability_code: str | None = Field(
        default=None, foreign_key="taxability_code.code", index=True
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1 Task 4: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class PricebookItemVersion(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "pricebook_item_version"
    __table_args__ = (
        # Prevent overlapping valid_period for same pricebook_item_id within a tenant
        ExcludeConstraint(
            (Column("tenant_id"), "="),
            (Column("pricebook_item_id"), "="),
            (Column("valid_period"), "&&"),
            name="piv_no_overlap",
            using="gist",
        ),
        CheckConstraint(
            "NOT isempty(valid_period)",
            name="piv_valid_period_chk",
        ),
    )

    # Uses BigInteger autoincrement for fast temporal writes
    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    pricebook_item_id: uuid.UUID = Field(
        foreign_key="pricebook_item.id", nullable=False, index=True
    )

    default_unit_price_cents: int = Field(nullable=False)
    valid_period: Any = Field(sa_column=Column(TSTZRANGE, nullable=False))
    recorded_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Phase 6.0.1 Task 4: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Quoting ---
class Quote(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote"

    __table_args__ = (
        # NEW: Idempotency unique constraint
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_quote_tenant_idempotency"
        ),
        # Standardized index names:
        Index("idx_quote_tenant", "tenant_id"),
        Index("idx_quote_customer", "customer_id"),
        Index("idx_quote_status", "status_id"),
        Index(
            "idx_quote_tenant_status_created_at",
            "tenant_id",
            "status_id",
            text("created_at DESC"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("customer.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    site_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("site.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    status_id: uuid.UUID = Field(foreign_key="quote_status.id", nullable=False)

    subtotal_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    tax_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    total_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    currency: str = Field(
        default="USD",
        max_length=3,
        sa_column=Column(
            String,
            ForeignKey("currency.code"),
            server_default=text("'USD'"),
            nullable=False,
            index=True,
        ),
    )
    idempotency_key: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # B19: Human-readable quote number — sequential, tenant-scoped (QUO-000001)
    # default_factory generates a UUID-based placeholder so direct Quote() construction
    # in tests doesn't hit the NOT NULL constraint. Production code always calls
    # _generate_quote_number() to set the canonical sequential format.
    quote_number: str = Field(
        default_factory=lambda: f"QUO-{uuid.uuid4().hex[:10].upper()}",
        sa_column=Column(String(20), nullable=False, index=True),
    )

    # B19: Optional quote title
    title: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
    )

    # Phase 6.0.1 Task 4: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )

    # A3: Time-Limited Discounts — quote-level discount columns
    discount_pct: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(5, 2), nullable=True),
    )
    discount_amount_cents: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    discount_expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    discount_applied_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )

    # A2: Quote Approval Workflow State Machine
    submitted_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    submitted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    approved_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    approved_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # B15/A83: Customer comment columns from public link accept/decline/payment
    customer_acceptance_comment: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    customer_accepted_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    customer_decline_comment: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    customer_decline_reason: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    customer_declined_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    customer_email_at_action: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )

    # FIND-096 (B19): Quote expiration timestamp; auto-transition to 'expired' status
    # when quote is 'sent' and expires_at < NOW() via daily Celery Beat task.
    # NULL = never expires (default for all existing quotes).
    expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # B20: card-on-file override (None = inherit from customer.card_required)
    card_required: bool | None = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )


class QuoteVersion(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "quote_version"
    __table_args__ = (
        UniqueConstraint(
            "quote_id", "version_no", name="uq_quote_version_quote_id_version_no"
        ),
        # NEW: Task 3 - Descending created_at for quote revision history
        Index("idx_quote_version_created_at", text("created_at DESC")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("quote.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    version_no: int = Field(nullable=False)

    snapshot: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    pdf_object_key: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # FIND-095 (B18): Presentation style for quote rendering — controls UI layout
    presentation_style: str = Field(
        default="clean",
        sa_column=Column(String, nullable=False, server_default=text("'clean'")),
    )

    # Phase 6.0.1 Task 4: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QuoteLine(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_line"
    __table_args__ = (
        # A24: Section headers cannot be children — enforce at DB level
        CheckConstraint(
            "NOT (is_section_header = TRUE AND parent_line_id IS NOT NULL)",
            name="chk_section_header_no_parent",
        ),
        # A24: Index for self-referential parent lookup
        Index("ix_quote_line_parent_line_id", "parent_line_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    position: int = Field(nullable=False)
    qco_line_type_id: uuid.UUID = Field(
        foreign_key="qco_line_type.id", nullable=False, index=True
    )
    pricebook_item_id: uuid.UUID | None = Field(
        default=None, foreign_key="pricebook_item.id", index=True
    )

    description: str = Field(nullable=False)
    quantity: Decimal = Field(
        default=Decimal("1.0"),
        sa_column=Column(Numeric(12, 3), nullable=False, server_default=text("1")),
    )
    unit: str | None = Field(default=None)
    unit_price_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    # Task 1-C-2: Cost-basis columns — store raw material/labor cost at line-creation time
    # Enables pre-sale gross margin: (unit_price_cents - unit_cost_cents)
    unit_cost_cents: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
    )
    cost_source: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )

    supplier_id: uuid.UUID | None = Field(
        default=None, foreign_key="supplier.id", index=True
    )
    supplier_item_id: uuid.UUID | None = Field(
        default=None, foreign_key="supplier_item.id", index=True
    )

    taxability_code: str | None = Field(
        default=None, foreign_key="taxability_code.code", index=True
    )
    tax_rate_pct: Decimal | None = Field(default=None, sa_column=Column(Numeric(7, 4)))
    tax_basis_cents: int | None = Field(default=None)
    tax_amount_cents: int | None = Field(default=None)
    tax_jurisdiction_code: str | None = Field(default=None)
    tax_as_of: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    tax_source: str | None = Field(default=None)

    subtotal_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    total_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # A24: Quote Line Item Schema Extension — visibility, hierarchy, ordering
    customer_visible: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    parent_line_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_line.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    display_order: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    is_section_header: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )


class QuotePublicLink(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_public_link"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    contact_id: uuid.UUID = Field(foreign_key="contact.id", nullable=False, index=True)

    token_hash: str = Field(nullable=False, unique=True)
    expires_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=text("NOW() + INTERVAL '90 days'")
        ),
    )
    max_uses: int = Field(
        default=1, sa_column=Column(Integer, server_default=text("1"), nullable=False)
    )
    used_count: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    permissions: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    status_id: uuid.UUID = Field(
        foreign_key="quote_link_status.id", nullable=False, index=True
    )
    last_used_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # B15/A80: HMAC-SHA256 signed token (distinct from legacy token_hash).
    # server_default ensures legacy INSERT statements (tests/routes) don't fail NOT NULL.
    signed_token: str | None = Field(
        default=None,
        sa_column=Column(
            String, nullable=False, server_default=text("'legacy.placeholder'")
        ),
    )
    # B15/A80: Set when tenant manually revokes the link.
    revoked_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # B15/A80: FK → user who generated the link (nullable in ORM; migration locks NOT NULL).
    created_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )

    # Phase 6.0.1 Task 4: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QuoteAcceptance(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "quote_acceptance"
    __table_args__ = (
        UniqueConstraint(
            "quote_version_id", "contact_id", name="uq_quote_acceptance_version_contact"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_version_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("quote_version.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact.id", index=True
    )  # Made optional for public link acceptances

    # Customer identity fields (required for all acceptances)
    # Email should be case-insensitive, unlimited length
    accepted_by_email: str = Field(sa_column=Column(CITEXT, nullable=False))
    # Name should be unlimited text
    accepted_by_name: str = Field(nullable=False)

    # Link to authenticated user if accepted internally
    accepted_by_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )

    # Acceptance timestamp and audit trail
    approved_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    approved_ip: str | None = Field(default=None, sa_column=Column(INET))
    approved_user_agent: str | None = Field(default=None)
    signature_url: str | None = Field(default=None)
    terms_acknowledged: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Optional customer notes (unlimited text)
    acceptance_notes: str | None = Field(default=None)

    # Link to public link if accepted via public link
    quote_public_link_id: uuid.UUID | None = Field(
        default=None, foreign_key="quote_public_link.id", index=True
    )

    # Phase 6.0.1 Task 4: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ChangeOrder(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "change_order"

    __table_args__ = (
        # NEW: Task 3 - Descending created_at for recent change orders
        Index("idx_change_order_created_at", text("created_at DESC")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    description: str = Field(nullable=False)

    subtotal_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    tax_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    total_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # B7a/A37: Offline capture timestamp — NULL means captured online
    client_capture_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # FIND-050: Server receipt timestamp — NULL=online, non-NULL=arrived via offline sync batch
    server_received_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Add to app/models/quoting.py ---


class QuoteLineTaxComponent(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "quote_line_tax_component"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_line_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_line.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    tax_rate_version_id: int = Field(
        sa_column=Column(
            BigInteger, ForeignKey("tax_rate_version.id"), nullable=False, index=True
        ),
    )

    component_code: str = Field(nullable=False)
    rate_pct: Decimal = Field(sa_column=Column(Numeric(7, 4), nullable=False))
    amount_cents: int = Field(nullable=False)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1 Task 4: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ChangeOrderLine(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "change_order_line"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    change_order_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("change_order.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    position: int = Field(nullable=False)
    qco_line_type_id: uuid.UUID = Field(
        foreign_key="qco_line_type.id", nullable=False, index=True
    )
    pricebook_item_id: uuid.UUID | None = Field(
        default=None, foreign_key="pricebook_item.id", index=True
    )

    description: str = Field(nullable=False)
    quantity: Decimal = Field(
        default=Decimal("1.0"),
        sa_column=Column(Numeric(12, 3), server_default=text("1"), nullable=False),
    )
    unit: str | None = Field(default=None)
    unit_price_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    supplier_id: uuid.UUID | None = Field(
        default=None, foreign_key="supplier.id", index=True
    )
    supplier_item_id: uuid.UUID | None = Field(
        default=None, foreign_key="supplier_item.id", index=True
    )
    taxability_code: str | None = Field(
        default=None, foreign_key="taxability_code.code", index=True
    )

    tax_rate_pct: Decimal | None = Field(default=None, sa_column=Column(Numeric(7, 4)))
    tax_basis_cents: int | None = Field(default=None)
    tax_amount_cents: int | None = Field(default=None)
    tax_jurisdiction_code: str | None = Field(default=None)
    tax_as_of: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    tax_source: str | None = Field(default=None)

    total_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    subtotal_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ChangeOrderLineTaxComponent(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "change_order_line_tax_component"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    change_order_line_id: uuid.UUID = Field(
        foreign_key="change_order_line.id", nullable=False, index=True
    )
    tax_rate_version_id: int = Field(
        sa_column=Column(
            BigInteger, ForeignKey("tax_rate_version.id"), nullable=False, index=True
        ),
    )

    component_code: str = Field(nullable=False)
    rate_pct: Decimal = Field(sa_column=Column(Numeric(7, 4), nullable=False))
    amount_cents: int = Field(nullable=False)

    # Phase 6.0.1 Task 3: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ChangeOrderAttachment(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "change_order_attachment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    change_order_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("change_order.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )

    file_name: str = Field(nullable=False)
    mime_type: str = Field(nullable=False)
    size_bytes: int = Field(nullable=False)
    object_key: str = Field(nullable=False)
    note: str | None = Field(default=None)

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QuoteMessage(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_message"

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('contact', 'tenant_user', 'system')",
            name="quote_message_action_type_chk",
        ),
        # NEW: Task 3 - Quote conversation thread composite index
        Index(
            "idx_quote_message_tenant_quote_time",
            "tenant_id",
            "quote_id",
            text("created_at DESC"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    quote_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact.id", index=True
    )

    action_type: str = Field(nullable=False)  # 'contact', 'tenant_user', 'system'
    message: str = Field(nullable=False)
    attachments: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # Phase 6.0.1 Task 4: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QplContactActionType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "qpl_contact_action_type"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "code", name="uq_qpl_contact_action_type_tenant_code"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QuotePublicLinkContactAction(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "quote_public_link_contact_action"

    __table_args__ = (
        # NEW: Task 3 - Descending created_at for quote link activity timeline
        Index("idx_qpl_action_created_at", text("created_at DESC")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_version_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_version.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    contact_id: uuid.UUID = Field(foreign_key="contact.id", nullable=False, index=True)
    qpl_contact_action_type_id: uuid.UUID = Field(
        foreign_key="qpl_contact_action_type.id", nullable=False, index=True
    )

    occurred_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    ip: str | None = Field(default=None, sa_column=Column(INET))
    user_agent: str | None = Field(default=None)
    payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # Phase 6.0.1 Task 4: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# A25: Quote Template Schema with Style and Versioning
# ─────────────────────────────────────────────────────────────────────────────


class QuoteTemplate(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_template"
    __table_args__ = (
        # A25: Prevent duplicate names within a tenant
        UniqueConstraint("tenant_id", "name", name="uq_quote_template_tenant_name"),
        CheckConstraint(
            "style IN ('component', 'deliverable', 'lump_sum')",
            name="chk_quote_template_style",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)

    # style: 'component' | 'deliverable' | 'lump_sum'
    style: str = Field(nullable=False)
    # category: 'service_call' | 'installation' | 'inspection' | NULL
    category: str | None = Field(default=None)

    # Forking / versioning
    system_template_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_template.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    forked_from_version: int | None = Field(default=None)
    current_version: int = Field(
        default=1,
        sa_column=Column(Integer, server_default=text("1"), nullable=False),
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    is_system_template: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # A25: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QuoteTemplateVersion(AppendOnlyMixin, SQLModel, table=True):
    """Immutable version history for reusable quote templates (FIND-098 / B18 / A25).

    When a template is edited, a new version snapshot is INSERT-ed here (never mutate).
    In-flight quotes pin to a specific version_no to resolve the exact line content
    from when they were created.
    """

    __tablename__ = "quote_template_version"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "version_no",
            name="uq_quote_template_version_template_version",
        ),
        Index("ix_quote_template_version_template_id", "template_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    template_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_template.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    version_no: int = Field(nullable=False)
    content_json: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    changelog: str | None = Field(default=None)

    # Override AppendOnlyMixin created_by with FK constraint (Phase 6.0.1 pattern)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class QuoteTemplateLine(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_template_line"
    __table_args__ = (
        Index("ix_quote_template_line_template_id", "quote_template_id"),
        Index("ix_quote_template_line_tenant_id", "tenant_id"),
        Index("ix_quote_template_line_parent", "parent_line_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # NULL = platform/system-template line (no owning tenant); mirrors
    # quote_template.tenant_id. Post QT-FIX-1.
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    quote_template_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_template.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    parent_line_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_template_line.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    display_order: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    qco_line_type_id: uuid.UUID = Field(
        foreign_key="qco_line_type.id", nullable=False, index=True
    )
    # description supports {variable} placeholders per B1 namespace
    description: str = Field(nullable=False)
    default_quantity: Decimal = Field(
        default=Decimal("1"),
        sa_column=Column(Numeric(12, 3), server_default=text("1"), nullable=False),
    )
    default_unit_price_cents: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    customer_visible: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    is_section_header: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # A25: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# A29: Pending Edit Storage During Owner Review
# ─────────────────────────────────────────────────────────────────────────────


class QuotePendingEdit(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "quote_pending_edit"
    __table_args__ = (
        CheckConstraint(
            "edit_type IN ('modify_line', 'add_line', 'delete_line', 'edit_notes')",
            name="chk_quote_pending_edit_type",
        ),
        Index("ix_quote_pending_edit_quote_id", "quote_id"),
        Index("ix_quote_pending_edit_editor", "editor_user_id", "quote_version_id"),
        Index("ix_quote_pending_edit_tenant", "tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    quote_version_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_version.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    editor_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    edit_type: str = Field(nullable=False)
    target_line_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_line.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    edit_payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    annotation: str | None = Field(default=None)

    # A29: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# A30: Approval Comment & Annotation System
# ─────────────────────────────────────────────────────────────────────────────


class QuoteApprovalComment(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "quote_approval_comment"
    __table_args__ = (
        CheckConstraint(
            "comment_type IN ('kickback', 'rejection', 'edit_annotation')",
            name="chk_quote_approval_comment_type",
        ),
        Index("ix_quote_approval_comment_quote_id", "quote_id"),
        Index("ix_quote_approval_comment_tenant", "tenant_id"),
        Index("ix_quote_approval_comment_version", "quote_version_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    quote_version_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_version.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    target_line_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_line.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    author_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    comment_type: str = Field(nullable=False)
    content: str = Field(nullable=False)

    # AppendOnly: only created_by (no updated_at, updated_by — append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# B15/A80 — Public Link Short Code
# ─────────────────────────────────────────────────────────────────────────────


class PublicLinkShortCode(MachineLogMixin, SQLModel, table=True):
    """
    Short-code redirect table mapping 5-8 char base62 codes to public links.

    Mixin: MachineLogMixin — short codes are entirely machine-generated;
    click tracking is automated. created_at only; no updated_at.

    link_id is polymorphic (references either quote_public_link.id or
    invoice_public_link.id based on link_type). No DB FK — enforced application-side.
    """

    __tablename__ = "public_link_short_code"
    __table_args__ = (
        CheckConstraint(
            "link_type IN ('quote', 'invoice')",
            name="public_link_short_code_link_type_chk",
        ),
    )

    short_code: str = Field(primary_key=True)

    link_type: str = Field(nullable=False)  # 'quote' | 'invoice'
    link_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, nullable=False, index=True),
    )

    click_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    last_clicked_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Pilot user who triggered short-code generation (nullable)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=True
        ),
    )
