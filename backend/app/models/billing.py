import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import AwareDatetime, model_validator
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin


# --- Dictionaries & Lookups ---
class Currency(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "currency"

    code: str = Field(primary_key=True, max_length=3, min_length=3)
    name: str = Field(nullable=False)
    symbol: str = Field(nullable=False)
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


class InvoiceStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "invoice_status"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_invoice_status_tenant_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
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

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class PaymentStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "payment_status"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_payment_status_tenant_code"),
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

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class PaymentType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "payment_type"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_payment_type_tenant_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
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


# --- Billing & Invoicing ---
class Invoice(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "invoice"

    __table_args__ = (
        # NEW: Idempotency unique constraints
        UniqueConstraint(
            "tenant_id", "invoice_number", name="uq_invoice_tenant_number"
        ),
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_invoice_tenant_idempotency"
        ),
        # Standardized index names (update existing or add new):
        Index("idx_invoice_customer", "customer_id"),
        Index("idx_invoice_status_due_at", "status_id", "due_at"),
        Index("idx_invoice_created_at", text("created_at DESC")),
        Index(
            "idx_invoice_balance",
            "balance_due_cents",
            postgresql_where=text("balance_due_cents > 0"),
        ),
        # FIND-074 (B18): Composite indexes for tenant-scoped invoice queries
        Index("idx_invoice_tenant_status", "tenant_id", "status_id"),
        Index("idx_invoice_tenant_created_at", "tenant_id", text("created_at DESC")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    invoice_number: str = Field(nullable=False)

    quote_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    job_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
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
    status_id: uuid.UUID = Field(foreign_key="invoice_status.id", nullable=False)

    idempotency_key: str | None = Field(default=None)
    issued_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    due_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    subtotal_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    tax_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    total_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    balance_due_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    currency: str = Field(
        default="USD",
        max_length=3,
        sa_column=Column(
            String(3),
            ForeignKey("currency.code"),
            server_default=text("'USD'"),
            nullable=False,
            index=True,
        ),
    )
    customer_notes: str | None = Field(default=None)
    terms_and_conditions: str | None = Field(default=None)
    pdf_object_key: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # SD-06B: Invoice reminder tracking columns
    last_reminder_sent_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    reminder_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )

    # B20: Invoice builder fields
    payment_terms: str | None = Field(
        default=None,
        sa_column=Column(String(30), nullable=True),
    )
    billing_mode: str = Field(
        default="line_item",
        sa_column=Column(
            String(20), server_default=text("'line_item'"), nullable=False
        ),
    )
    progress_pct: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(5, 2), nullable=True),
    )
    internal_memo: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )

    # BILLING-B1: nullable additive FK → payment_schedule_line.id (draw invoice linkage).
    # Set on generated `progress` invoices; NULL on `line_item` invoices.
    payment_schedule_line_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("payment_schedule_line.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
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


class InvoiceLine(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "invoice_line"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('quote_line', 'change_order_line', 'ad_hoc')",
            name="invoice_line_source_type_chk",
        ),
        # NEW: Task 3 - Polymorphic source lookup composite index
        Index("idx_invoice_line_source", "source_type", "source_id"),
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
    invoice_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("invoice.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )

    source_type: str = Field(nullable=False)
    source_id: uuid.UUID | None = Field(default=None)
    position: int = Field(nullable=False)

    # PLP-FIX-1: aligned to live DB (NOT NULL) — was `uuid.UUID | None` (model↔DB drift)
    qco_line_type_id: uuid.UUID = Field(foreign_key="qco_line_type.id", index=True)
    pricebook_item_id: uuid.UUID | None = Field(
        default=None, foreign_key="pricebook_item.id", index=True
    )

    description: str = Field(nullable=False)
    quantity: float = Field(
        default=1.0,
        sa_column=Column(Numeric(12, 3), server_default=text("1"), nullable=False),
    )
    unit: str | None = Field(default=None)
    unit_price_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
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

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Payments ---
class PaymentMethod(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "payment_method"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "psp_provider",
            "psp_payment_method_id",
            name="uq_payment_method_tenant_psp",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    customer_id: uuid.UUID | None = Field(
        default=None, foreign_key="customer.id", nullable=True, index=True
    )
    payment_type_id: uuid.UUID = Field(
        foreign_key="payment_type.id", nullable=False, index=True
    )

    brand: str | None = Field(default=None)
    psp_provider: str = Field(nullable=False)
    psp_payment_method_id: str = Field(nullable=False)

    exp_month: int | None = Field(default=None)
    exp_year: int | None = Field(default=None)
    fingerprint: str | None = Field(default=None)
    billing_address_id: uuid.UUID | None = Field(
        default=None, foreign_key="address.id", index=True
    )
    name_on_account: str | None = Field(default=None)
    last4: str | None = Field(default=None)
    psp_token: str | None = Field(default=None)

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


class Payment(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "payment"

    __table_args__ = (
        # NEW: Idempotency unique constraint
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_payment_tenant_idempotency"
        ),
        # Standardized index names:
        Index("idx_payment_invoice", "invoice_id"),
        Index("idx_payment_tenant", "tenant_id"),
        Index("idx_payment_created_at", text("created_at DESC")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    invoice_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("invoice.id", ondelete="RESTRICT"), nullable=False
        ),
    )

    amount_cents: int = Field(nullable=False)
    payment_method_id: uuid.UUID = Field(
        foreign_key="payment_method.id", nullable=False, index=True
    )
    status_id: uuid.UUID = Field(
        foreign_key="payment_status.id", nullable=False, index=True
    )

    paid_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    psp_provider: str | None = Field(default=None)
    psp_payment_id: str | None = Field(default=None)
    connector_config_id: uuid.UUID | None = Field(
        default=None, foreign_key="connector_config.id", index=True
    )
    idempotency_key: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # B15/A81: Stripe Payment Intent columns
    stripe_payment_intent_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True, unique=True, index=True),
    )
    customer_payment_comment: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    amount_variance_cents: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    paid_via: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )

    # CE-1: Overpayment variance resolution tracking (record-keeping only —
    # no Stripe refund execution; SD-2 refund model is untouched).
    variance_resolution: str | None = Field(
        default=None,
        sa_column=Column(String(20), nullable=True),
    )
    variance_resolution_note: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    variance_resolved_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    variance_resolved_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=True
        ),
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


# --- SaaS Platform Subscriptions & Usage ---
class Subscription(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "subscription"

    __table_args__ = (
        CheckConstraint(
            "billing_interval IN ('monthly','annual')",
            name="subscription_billing_interval_chk",
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
    product_plan_code: str = Field(
        foreign_key="product_plan.code", nullable=False, index=True
    )
    status_id: uuid.UUID = Field(
        foreign_key="subscription_status.id", nullable=False, index=True
    )

    quantity_seats: int = Field(
        default=1, sa_column=Column(Integer, server_default=text("1"), nullable=False)
    )
    billing_anchor: date | None = Field(default=None, sa_column=Column(Date))

    started_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    canceled_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    psp_provider: str | None = Field(default=None)
    psp_subscription_id: str | None = Field(default=None, unique=True)
    psp_customer_id: str | None = Field(default=None)
    stripe_schedule_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )  # Stripe Subscription Schedule ID for Charter cohort tenants

    billing_interval: str = Field(
        default="monthly",
        sa_column=Column(String, server_default=text("'monthly'"), nullable=False),
    )
    trial_ends_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    renews_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    cancel_at_period_end: bool = Field(
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


class UsageLedger(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "usage_ledger"

    __table_args__ = (
        # NEW: Task 3 - Usage billing aggregation composite index
        Index(
            "idx_usage_ledger_tenant_feature",
            "tenant_id",
            "product_feature_code",
            "is_reported",
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    subscription_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("subscription.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    product_feature_code: str = Field(
        foreign_key="product_feature.code", nullable=False, index=True
    )

    occurred_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    quantity: float = Field(
        default=1.0,
        sa_column=Column(Numeric(12, 4), server_default=text("1"), nullable=False),
    )

    entity_type_code: str | None = Field(default=None)
    entity_id: uuid.UUID | None = Field(default=None)

    idempotency_key: str = Field(nullable=False, unique=True)
    is_reported: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    reported_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Cleanly renamed to contextdata to avoid Pydantic reserved keyword collisions
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Add to app/models/billing.py ---


class ProductPlan(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "product_plan"

    code: str = Field(primary_key=True)
    name: str = Field(nullable=False)
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


class ProductFeature(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "product_feature"

    code: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    unit: str = Field(nullable=False)
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


class SubscriptionStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "subscription_status"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "code", name="uq_subscription_status_tenant_code"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_billing_active: bool = Field(
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


class ProductPlanVersion(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "product_plan_version"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    product_plan_code: str = Field(
        foreign_key="product_plan.code", nullable=False, index=True
    )
    name: str = Field(nullable=False)
    price_cents: int = Field(nullable=False)

    valid_period: Any = Field(sa_column=Column(TSTZRANGE, nullable=False))
    recorded_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ProductPlanProductFeatureVersion(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "product_plan_product_feature_version"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    product_plan_code: str = Field(foreign_key="product_plan.code", nullable=False)
    product_feature_code: str = Field(
        foreign_key="product_feature.code", nullable=False, index=True
    )

    limit_quantity: int | None = Field(default=None)
    included_quantity: int | None = Field(default=None)
    overage_price_cents: int | None = Field(default=None)

    valid_period: Any = Field(sa_column=Column(TSTZRANGE, nullable=False))
    recorded_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    limit_enforcement: str = Field(
        default="block",
        sa_column=Column(String, server_default=text("'block'"), nullable=False),
    )
    overage_cap_per_period: int | None = Field(default=None)
    alert_threshold_pct: int | None = Field(default=None)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )

    @model_validator(mode="after")
    def validate_overage_price_required_when_soft(self):
        """
        Enforce: if limit_enforcement != 'block' (i.e., overages are allowed),
        overage_price_cents must be non-null.
        This prevents misconfigured plans from silently charging $0 or crashing at billing time.
        """
        if self.limit_enforcement != "block" and self.overage_price_cents is None:
            raise ValueError(
                "overage_price_cents is required when limit_enforcement != 'block'"
            )
        return self


class TenantProductFeatureOverride(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "tenant_product_feature_override"

    tenant_id: uuid.UUID = Field(primary_key=True, foreign_key="tenant.id")
    product_feature_code: str = Field(
        primary_key=True, foreign_key="product_feature.code", index=True
    )

    limit_quantity: int | None = Field(default=None)
    included_quantity: int | None = Field(default=None)
    overage_price_cents: int | None = Field(default=None)
    overage_cap_per_period: int | None = Field(default=None)
    alert_threshold_pct: int | None = Field(default=None)
    enabled: bool = Field(
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


class SubscriptionUsage(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "subscription_usage"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "product_feature_code",
            "period_start",
            "period_end",
            name="uq_subscription_usage_subscription_feature_period",
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    subscription_id: uuid.UUID = Field(foreign_key="subscription.id", nullable=False)
    product_feature_code: str = Field(
        foreign_key="product_feature.code", nullable=False, index=True
    )

    period_start: date = Field(sa_column=Column(Date, nullable=False))
    period_end: date = Field(sa_column=Column(Date, nullable=False))
    used_quantity: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
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


class PspCustomer(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "psp_customer"
    __table_args__ = (
        UniqueConstraint(
            "psp_provider", "psp_customer_id", name="uq_psp_customer_provider_id"
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
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )

    psp_provider: str = Field(nullable=False)
    psp_customer_id: str = Field(nullable=False)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class PspTransactionLog(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "psp_transaction_log"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    payment_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("payment.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    app_service_id: uuid.UUID = Field(
        foreign_key="app_service.id", nullable=False, index=True
    )

    transaction_type: str = Field(nullable=False)
    http_status: int | None = Field(default=None)
    psp_reference_id: str | None = Field(default=None, index=True)

    raw_request: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    raw_response: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    error_code: str | None = Field(default=None)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class InvoiceLineTaxComponent(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "invoice_line_tax_component"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    invoice_line_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("invoice_line.id", ondelete="RESTRICT"),
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

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Task 1-D-3: Invoice Public Payment Link ---
class InvoicePublicLink(StandardAuditMixin, SQLModel, table=True):
    """
    Secure, revocable, time-boxed link for a customer to view and pay an invoice
    without authenticating. Analogous to QuotePublicLink.
    """

    __tablename__ = "invoice_public_link"

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_invoice_public_link_token_hash"),
        Index("ix_invoice_public_link_tenant_id", "tenant_id"),
        Index("idx_invoice_public_link_invoice", "invoice_id"),
        Index("idx_invoice_public_link_contact", "contact_id"),
        CheckConstraint(
            "status IN ('active', 'revoked', 'expired')",
            name="invoice_public_link_status_chk",
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
    invoice_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("invoice.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    contact_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("contact.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )

    token_hash: str = Field(
        sa_column=Column("token_hash", String, nullable=False, unique=True)
    )
    expires_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW() + INTERVAL '90 days'"),
        ),
    )
    max_uses: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    used_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    status: str = Field(
        default="active",
        sa_column=Column(
            String,
            server_default=text("'active'"),
            nullable=False,
        ),
    )
    last_used_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
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

    # Phase 6.0.1 pattern: override audit FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# B14/A76 — Stripe Webhook Dedup Table
# Co-located in billing.py per design doc F4 resolution.
# AppendOnlyMixin: once written, never modified (immutable idempotency semantics).
class StripeWebhookEventProcessed(AppendOnlyMixin, SQLModel, table=True):
    """
    Deduplication table for Stripe webhook events.
    PK = event_id (Stripe event ID, e.g. evt_1abc...)
    Created atomically on first processing; second writes abort with duplicate detection.
    """

    __tablename__ = "stripe_webhook_event_processed"

    # id UUID for audit.log_changes() entity_id extraction
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        index=True,
    )
    event_id: str = Field(
        primary_key=True,
        nullable=False,
    )
    processed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    event_type: str = Field(
        sa_column=Column(String, nullable=False),
    )

    # AppendOnlyMixin provides created_at + created_by
    # created_by is NULL for system-initiated (webhook arrival)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- BILLING-B1: Progress Billing — Payment Schedule Orchestration ---


class PaymentSchedule(StandardAuditMixin, SQLModel, table=True):
    """BILLING-B1 §B.1 — Parent schedule orchestrating progress/milestone draws.

    One schedule per quote/job billed in draws. A deposit is simply the draw
    with ``sequence=1`` (no special column). The ``contract_total_cents`` is the
    locked total the draws must sum to on activation (reconciliation guard).
    """

    __tablename__ = "payment_schedule"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    quote_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("quote.id", ondelete="SET NULL"), nullable=True
        ),
    )
    job_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("job.id", ondelete="SET NULL"), nullable=True
        ),
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("customer.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    site_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    contract_total_cents: int = Field(nullable=False)
    status: str = Field(
        default="draft",
        sa_column=Column(String, server_default=text("'draft'"), nullable=False),
    )
    basis_default: str = Field(
        default="percent",
        sa_column=Column(String, server_default=text("'percent'"), nullable=False),
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


class PaymentScheduleLine(StandardAuditMixin, SQLModel, table=True):
    """BILLING-B1 §B.2 — A single draw on a :class:`PaymentSchedule`.

    Conditional-NOT-NULL is enforced by DB CHECK constraints (``psl_basis_amount_chk``,
    ``psl_trigger_detail_chk``) and mirrored by a Pydantic ``@model_validator`` on
    the request schema. ``sequence=1`` is the deposit by convention (no special column).
    """

    __tablename__ = "payment_schedule_line"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    payment_schedule_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("payment_schedule.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    sequence: int = Field(nullable=False)
    label: str = Field(nullable=False)
    basis: str = Field(nullable=False)
    percent: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(5, 2), nullable=True)
    )
    amount_cents: int | None = Field(default=None, nullable=True)
    trigger_type: str = Field(
        default="manual",
        sa_column=Column(String, server_default=text("'manual'"), nullable=False),
    )
    trigger_date: date | None = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )
    milestone_label: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    invoice_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("invoice.id", ondelete="SET NULL"), nullable=True
        ),
    )
    status: str = Field(
        default="pending",
        sa_column=Column(String, server_default=text("'pending'"), nullable=False),
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


# --- Carrier Fee Schedule (C-B8 / C-B9 temporal) ---
class CarrierFeeSchedule(StandardAuditMixin, SQLModel, table=True):
    """
    Operator-maintained config table for Telnyx 10DLC carrier fees.

    Telnyx has no public API for pre-transaction pricing (Q#1 resolution),
    so carrier fees are stored here and read by the quoting adapter at quote
    time. Operator can update fees via SQL without a deploy.

    C-B8 created the table; C-B9 migrated it to a temporal lookup with
    millicents precision (1 millicent = $0.00001). The GiST exclusion
    constraint prevents overlapping effective periods for the same
    (fee_code, entity_type) pair.

    C-B8 / C-B9.
    """

    __tablename__ = "carrier_fee_schedule"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('standard', 'sole_proprietor')",
            name="carrier_fee_schedule_entity_type_chk",
        ),
        # GiST exclusion constraint (uq_carrier_fee_schedule_temporal) is
        # DB-only — no ORM repr needed. It prevents overlapping tstzrange
        # periods for the same (fee_code, entity_type).
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fee_code: str = Field(sa_column=Column(String, nullable=False))
    entity_type: str = Field(sa_column=Column(String, nullable=False))
    amount_millicents: int = Field(sa_column=Column(BigInteger, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    effective_from: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    effective_to: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
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


# --- CE-1: Invoice Sign-Off Capture (mobile, offline-first) ---


class InvoiceSignoff(StandardAuditMixin, SQLModel, table=True):
    """CE-1 — Customer signature captured at invoice sign-off (mobile, offline-first).

    One active row per invoice (partial unique index uq_invoice_signoff_one_active);
    re-capture supersedes the prior row. The signature PNG lives in S3 at
    signature_object_key; the row carries metadata only.
    """

    __tablename__ = "invoice_signoff"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    invoice_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("invoice.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    signed_by_name: str = Field(sa_column=Column(String(200), nullable=False))
    signature_object_key: str = Field(sa_column=Column(String(500), nullable=False))
    terms_acknowledged: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    signed_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    client_capture_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    captured_by_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    superseded_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    idempotency_key: str | None = Field(
        default=None,
        sa_column=Column(String(100), nullable=True),
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
