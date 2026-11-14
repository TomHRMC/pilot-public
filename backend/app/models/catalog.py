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
    Numeric,
    String,
    UniqueConstraint,
    func,
    literal,
    text,
)
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin


class SupplierLifecycleStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "supplier_lifecycle_status"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "code", name="uq_supplier_lifecycle_status_tenant_code"
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

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class Supplier(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "supplier"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    name: str = Field(nullable=False)
    website: str | None = Field(default=None)
    api_auth_type: str | None = Field(default=None)
    api_base_url: str | None = Field(default=None)

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    lifecycle_status_id: uuid.UUID | None = Field(
        default=None, foreign_key="supplier_lifecycle_status.id", index=True
    )

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class SupplierItemCategory(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "supplier_item_category"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "code", name="uq_supplier_item_category_tenant_code"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class SupplierItemUom(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "supplier_item_uom"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_supplier_item_uom_tenant_code"),
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

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class SupplierItem(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "supplier_item"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "supplier_id",
            "sku",
            name="uq_supplier_item_tenant_supplier_sku",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    supplier_id: uuid.UUID = Field(
        foreign_key="supplier.id", nullable=False, index=True
    )

    sku: str = Field(nullable=False, index=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)

    uom_id: uuid.UUID = Field(
        foreign_key="supplier_item_uom.id", nullable=False, index=True
    )
    category_id: uuid.UUID | None = Field(
        default=None, foreign_key="supplier_item_category.id", index=True
    )
    taxability_code: str | None = Field(
        default=None, foreign_key="taxability_code.code", index=True
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class SupplierItemPrice(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "supplier_item_price"

    __table_args__ = (
        # Phase 6.0 Task 2: GiST exclusion constraint for temporal overlap prevention
        # NULL-safe overlap prevention (for tenant-agnostic pricing)
        ExcludeConstraint(
            (Column("supplier_item_id"), "="),
            (
                func.coalesce(
                    Column("tenant_id"),
                    literal(
                        "00000000-0000-0000-0000-000000000000", type_=SQLAlchemyUUID
                    ),
                ),
                "=",
            ),
            (Column("valid_period"), "&&"),
            name="exclude_supplier_item_price_period_overlap",
            using="gist",
        ),
        CheckConstraint(
            "NOT isempty(valid_period)",
            name="sip_valid_period_chk",
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    supplier_item_id: uuid.UUID = Field(
        foreign_key="supplier_item.id", nullable=False, index=True
    )

    unit_price: float = Field(sa_column=Column(Numeric(19, 4), nullable=False))
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
    valid_period: Any = Field(
        sa_column=Column(
            TSTZRANGE,
            server_default=text("tstzrange(now(), null, '[)')"),
            nullable=False,
        )
    )

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class PricingCache(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "pricing_cache"

    __table_args__ = (
        # Task 1-A-2 (Remediation): PostgreSQL 17 NULLS NOT DISTINCT unique constraint.
        # Treats NULL tenant_id as equal for uniqueness — so only one global price
        # (tenant_id IS NULL) per (supplier_id, sku) can exist, while each tenant
        # may have its own private negotiated price for the same SKU.
        # DDL: UNIQUE NULLS NOT DISTINCT (supplier_id, sku, tenant_id)
        # Note: Constraint is created raw via migration c3d4e5f6a7b8 to emit NULLS NOT DISTINCT;
        # declared here only so Alembic tracks its name without re-creating it.
        UniqueConstraint(
            "supplier_id",
            "sku",
            "tenant_id",
            name="uq_pricing_cache_supplier_sku_tenant",
        ),
        # Index to support efficient tenant-scoped cache reads
        Index("idx_pricing_cache_tenant", "tenant_id"),
    )

    # Surrogate PK (bigserial) — supports one global + N tenant-specific prices per SKU.
    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )

    supplier_id: uuid.UUID = Field(
        foreign_key="supplier.id", nullable=False, index=True
    )
    sku: str = Field(nullable=False, index=True)

    # Task 1-A-2: Tenant stamping.
    # NULL  = global/shared price — accessible to all tenants (e.g., distributor list price).
    # UUID  = private negotiated price for that tenant only (e.g., volume discount).
    #
    # SECURITY: All cache reads MUST filter:
    #   tenant_id IS NULL OR tenant_id = current_tenant.id
    # with ORDER BY tenant_id NULLS LAST so tenant-specific prices take precedence.
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=True,
            index=False,  # covered by idx_pricing_cache_tenant above
        ),
    )

    price_cents: int = Field(nullable=False)
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
    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class TenantMarkupVersion(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "tenant_markup_version"

    __table_args__ = (
        CheckConstraint(
            "NOT isempty(valid_period)",
            name="tmv_valid_period_chk",
        ),
        CheckConstraint(
            "(markup_pct IS NOT NULL) OR (markup_amt_cents IS NOT NULL)",
            name="tmv_markup_presence_chk",
        ),
        # NEW: Task 3 - Markup history by category composite index
        Index("idx_tenant_markup_category", "tenant_id", "job_expense_category_code"),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    job_expense_category_code: str = Field(
        foreign_key="job_expense_category.code", nullable=False
    )

    markup_pct: float = Field(sa_column=Column(Numeric(7, 4), nullable=False))
    markup_amt_cents: int | None = Field(default=None)
    valid_period: Any = Field(
        sa_column=Column(
            TSTZRANGE,
            server_default=text("tstzrange(now(), null, '[)')"),
            nullable=False,
        )
    )
    recorded_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Phase 6.0.1: Override audit field with FK constraint (append-only/versioned table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class TaxRateVersion(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "tax_rate_version"

    __table_args__ = (
        CheckConstraint(
            "NOT isempty(valid_period)",
            name="tax_rate_version_valid_period_chk",
        ),
        # Task 1-C-7: GiST constraint hardened to include taxability_code so a single
        # jurisdiction can hold concurrent rates for 'taxable' vs 'exempt' categories
        # (required in states that tax labor and materials differently).
        # Replaces: EXCLUDE USING gist (jurisdiction_code WITH =, valid_period WITH &&)
        # DDL managed by migration — declared here for Alembic tracking only.
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    jurisdiction_code: str = Field(nullable=False, index=True)
    description: str | None = Field(default=None)

    # Task 1-C-6: QB Tax Agency ID — maps this jurisdiction to a QB Online Tax Agency
    external_tax_agency_id: str | None = Field(
        default=None,
        sa_column=Column(String(100), nullable=True),
    )

    # Task 1-C-7: Taxability discriminator — 'taxable' | 'exempt' | 'zero_rated'.
    # Enables a single jurisdiction to hold simultaneous different rates for
    # labor vs. materials (required in states where these are taxed differently).
    # FK enforces referential integrity against the taxability_code lookup table.
    taxability_code: str = Field(
        default="taxable",
        foreign_key="taxability_code.code",
        nullable=False,
        index=True,
    )

    rate_pct: Decimal = Field(sa_column=Column(Numeric(7, 4), nullable=False))
    valid_period: Any = Field(sa_column=Column(TSTZRANGE, nullable=False))
    recorded_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class LaborRateVersion(AppendOnlyMixin, SQLModel, table=True):
    """
    Labor Rate Version — Catalog-managed burdened labor rates by skill tier.

    Task 1-C-8: Provides a versioned, tenant-scoped catalog of burdened labor
    rates keyed by skill tier (e.g., 'apprentice', 'journeyman', 'master').
    Rates include an overhead burden percentage so quote line creation can
    accurately compute total labor cost without manual burden calculation.

    GiST exclusion constraint prevents overlapping effective periods for the
    same (tenant_id, skill_level_code) pair — enforced via migration DDL.
    """

    __tablename__ = "labor_rate_version"

    __table_args__ = (
        CheckConstraint(
            "NOT isempty(valid_period)",
            name="labor_rate_version_valid_period_chk",
        ),
        # GiST exclusion: one active rate per tenant + skill level at any moment.
        # DDL managed by migration — declared here for Alembic tracking only.
        # EXCLUDE USING GIST (tenant_id WITH =, skill_level_code WITH =, valid_period WITH &&)
        Index("ix_labor_rate_version_tenant_skill", "tenant_id", "skill_level_code"),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=False,  # covered by ix_labor_rate_version_tenant_skill
        )
    )

    # Skill tier discriminator — plain varchar (no lookup table).
    # Expected values: 'apprentice', 'journeyman', 'master', 'foreman', etc.
    skill_level_code: str = Field(nullable=False)

    # Hourly rate in cents (integer arithmetic avoids float precision errors)
    hourly_rate_cents: int = Field(nullable=False)

    # Overhead burden as a fraction (e.g., 0.3000 = 30% burden on base rate)
    burden_pct: Decimal = Field(sa_column=Column(Numeric(7, 4), nullable=False))

    valid_period: Any = Field(
        sa_column=Column(
            TSTZRANGE,
            server_default=text("tstzrange(now(), null, '[)')"),
            nullable=False,
        )
    )
    recorded_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Audit fields (AppendOnlyMixin supplies created_at)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class DiscountVersion(AppendOnlyMixin, SQLModel, table=True):
    """
    Discount Version - Temporal versioning for plan discounts

    Tracks discount codes with temporal validity periods. Can be global (tenant_id=NULL)
    or tenant-specific. Uses either percentage off or fixed amount off.
    """

    __tablename__ = "discount_version"
    __table_args__ = (
        # Check constraint - ensure either pct_off OR amount_off_cents is set, not both
        CheckConstraint(
            "(pct_off IS NOT NULL AND amount_off_cents IS NULL) OR "
            "(pct_off IS NULL AND amount_off_cents IS NOT NULL)",
            name="discount_version_value_check",
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    code: str = Field(nullable=False)
    pct_off: Decimal | None = Field(default=None, sa_column=Column(Numeric(6, 3)))
    amount_off_cents: int | None = Field(default=None)
    valid_period: Any = Field(sa_column=Column(TSTZRANGE, nullable=False))
    recorded_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Phase 6.0.1: Audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
