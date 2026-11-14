"""
Tax Calculation Module

Provides jurisdiction-based tax rate lookup and tax calculation with conservative (round-up) rounding
for quote lines and change order lines.

Design Reference: dev-docs/db-design/pilot-db-process-v2.6h.md Section 5.1
Gap Analysis: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md:186-198
"""

import logging
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlmodel import select

from app.models.catalog import TaxRateVersion
from app.models.crm import Site
from app.models.quoting import ChangeOrderLineTaxComponent, QuoteLineTaxComponent

logger = logging.getLogger(__name__)


def get_tax_rates_for_quote_line(
    db: Session, site_id: UUID, taxability_code: str, as_of_timestamp: datetime
) -> list[TaxRateVersion]:
    """
    Look up applicable tax rates for a quote line based on site jurisdiction.

    This function implements temporal tax rate lookup using PostgreSQL's GiST
    range operators to query rates that were valid at a specific point in time.

    Args:
        db: Database session
        site_id: ID of the site where work will be performed
        taxability_code: Item tax classification ('taxable', 'exempt', 'zero_rated')
        as_of_timestamp: Timestamp for temporal lookup (usually quote creation time)

    Returns:
        List of TaxRateVersion records (may contain multiple components like
        state + county + city taxes). Returns empty list for exempt items.

    Raises:
        ValueError: If site_id is not found in database

    Notes:
        - Uses GiST @> operator for temporal queries (valid_period contains timestamp)
        - Falls back to "US-DEFAULT" jurisdiction if site.jurisdiction_code is NULL
        - Returns empty list for 'exempt' items (0% tax)
        - If no rates found, returns empty list (caller should set tax to $0 and log warning)

    Examples:
        >>> tax_rates = get_tax_rates_for_quote_line(
        ...     db=session,
        ...     site_id=site.id,
        ...     taxability_code="taxable",
        ...     as_of_timestamp=datetime.now(UTC)
        ... )
        >>> # Returns [TaxRateVersion(jurisdiction_code="US-TX-HARRIS", rate_pct=8.25, ...)]
    """
    # Step 1: Get site from database
    site = db.get(Site, site_id)
    if not site:
        logger.warning(f"Site {site_id} not found, defaulting to 0% tax")
        return []

    # Step 2: Extract jurisdiction code (fallback to default)
    jurisdiction = site.jurisdiction_code or "US-DEFAULT"
    logger.debug(
        f"Tax lookup for site {site_id}: jurisdiction={jurisdiction}, "
        f"taxability={taxability_code}, as_of={as_of_timestamp}"
    )

    # Step 3: Handle tax-exempt items
    if taxability_code == "exempt":
        logger.debug("Item is tax-exempt, returning 0% tax")
        return []

    # Step 4: Query tax_rate_version with temporal lookup
    # Using GiST @> operator: valid_period contains as_of_timestamp
    query = select(TaxRateVersion).where(
        TaxRateVersion.jurisdiction_code == jurisdiction,
        TaxRateVersion.valid_period.contains(as_of_timestamp),
    )

    tax_rates = list(db.exec(query).all())

    if not tax_rates:
        logger.warning(
            f"No tax rates found for jurisdiction '{jurisdiction}' "
            f"as of {as_of_timestamp}. Tax will be set to $0."
        )
    else:
        logger.debug(
            f"Found {len(tax_rates)} tax rate(s) for jurisdiction '{jurisdiction}': "
            f"{[f'{r.description} ({r.rate_pct}%)' for r in tax_rates]}"
        )

    return tax_rates


def calculate_tax_components(
    subtotal_cents: int,
    tax_rates: list[TaxRateVersion],
    quote_line_id: UUID | None = None,
    component_class: type = QuoteLineTaxComponent,
    tenant_id: UUID | None = None,
) -> tuple[int, list[QuoteLineTaxComponent | ChangeOrderLineTaxComponent]]:
    """
    Calculate tax amount and create tax component records with round-up rounding.

    This function applies each tax rate component to the subtotal, rounds UP to the
    nearest cent (a conservative choice; sales-tax rounding rules vary by state), and creates audit trail records.

    Args:
        subtotal_cents: Line item subtotal before tax (in cents)
        tax_rates: List of applicable tax rates from get_tax_rates_for_quote_line()
        quote_line_id: ID to link components (optional, can be set after creation)
        component_class: QuoteLineTaxComponent or ChangeOrderLineTaxComponent

    Returns:
        Tuple of:
            - total_tax_amount_cents (int): Sum of all tax components
            - list of tax component records (unsaved, caller must add to session)

    Notes:
        - Round UP each component using Decimal.ROUND_CEILING (conservative; rules vary by state)
        - Use Decimal type for precision to avoid floating point errors
        - Creates one component per tax rate (e.g., state + county + city)
        - Component records are created but not saved to database

    Examples:
        >>> # Calculate 8.25% tax on $100.00 subtotal
        >>> tax_rates = [TaxRateVersion(rate_pct=8.25, jurisdiction_code="US-TX-HARRIS")]
        >>> total_tax, components = calculate_tax_components(
        ...     subtotal_cents=10000,
        ...     tax_rates=tax_rates,
        ...     quote_line_id=line.id
        ... )
        >>> print(total_tax)  # 825 cents = $8.25
        >>> print(components[0].amount_cents)  # 825

        >>> # Multi-component tax: 6% state + 1.5% county + 0.75% city
        >>> tax_rates = [
        ...     TaxRateVersion(rate_pct=6.0, jurisdiction_code="US-TX-STATE"),
        ...     TaxRateVersion(rate_pct=1.5, jurisdiction_code="US-TX-COUNTY"),
        ...     TaxRateVersion(rate_pct=0.75, jurisdiction_code="US-TX-CITY")
        ... ]
        >>> total_tax, components = calculate_tax_components(10000, tax_rates)
        >>> print(total_tax)  # 825 cents (600 + 150 + 75)
        >>> print(len(components))  # 3 components
    """
    components = []
    total_tax_cents = 0

    # Handle zero tax case (no rates or exempt item)
    if not tax_rates:
        logger.debug("No tax rates provided, tax amount will be $0")
        return 0, []

    logger.debug(
        f"Calculating tax on subtotal ${subtotal_cents / 100:.2f} "
        f"with {len(tax_rates)} rate component(s)"
    )

    for tax_rate in tax_rates:
        # Calculate tax for this component using Decimal for precision
        subtotal_dollars = Decimal(subtotal_cents) / Decimal(100)
        rate_decimal = Decimal(str(tax_rate.rate_pct)) / Decimal(100)
        tax_amount_dollars = subtotal_dollars * rate_decimal

        # Round UP to nearest cent (conservative; rules vary by state)
        tax_amount_dollars_rounded = tax_amount_dollars.quantize(
            Decimal("0.01"), rounding=ROUND_CEILING
        )
        tax_amount_cents = int(tax_amount_dollars_rounded * 100)

        logger.debug(
            f"  Component: {tax_rate.jurisdiction_code} @ {tax_rate.rate_pct}% = "
            f"${tax_amount_cents / 100:.2f} (rounded up from ${tax_amount_dollars:.4f})"
        )

        # Create component record
        component = component_class(
            tenant_id=tenant_id,
            quote_line_id=quote_line_id
            if component_class == QuoteLineTaxComponent
            else None,
            change_order_line_id=quote_line_id
            if component_class == ChangeOrderLineTaxComponent
            else None,
            tax_rate_version_id=tax_rate.id,
            component_code=tax_rate.jurisdiction_code,
            rate_pct=float(tax_rate.rate_pct),
            amount_cents=tax_amount_cents,
        )
        components.append(component)
        total_tax_cents += tax_amount_cents

    logger.debug(
        f"Total tax calculated: ${total_tax_cents / 100:.2f} "
        f"({len(components)} component(s))"
    )

    return total_tax_cents, components


def calculate_combined_tax_rate(tax_rates: list[TaxRateVersion]) -> float:
    """
    Calculate the combined tax rate percentage from multiple rate components.

    Args:
        tax_rates: List of tax rate components

    Returns:
        Sum of all rate_pct values (e.g., 8.25 for 8.25% combined tax)

    Examples:
        >>> tax_rates = [
        ...     TaxRateVersion(rate_pct=6.0),
        ...     TaxRateVersion(rate_pct=1.5),
        ...     TaxRateVersion(rate_pct=0.75)
        ... ]
        >>> combined = calculate_combined_tax_rate(tax_rates)
        >>> print(combined)  # 8.25
    """
    if not tax_rates:
        return 0.0

    return sum(rate.rate_pct for rate in tax_rates)


def get_jurisdiction_code_from_rates(tax_rates: list[TaxRateVersion]) -> str | None:
    """
    Extract jurisdiction code from tax rates for audit trail.

    Args:
        tax_rates: List of tax rate components

    Returns:
        Jurisdiction code from first rate, or None if no rates

    Notes:
        For multi-component taxes (state + county + city), this returns the
        first component's jurisdiction. Full breakdown is in tax_component table.
    """
    if not tax_rates:
        return None

    return tax_rates[0].jurisdiction_code
