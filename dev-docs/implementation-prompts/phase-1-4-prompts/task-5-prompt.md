# Task 5 Prompt: Implement Tax Calculation

Use this prompt to start the tax calculation implementation task.

---

## PROMPT FOR TASK 5

```
Task: Implement Gap #11 - Tax Calculation System
Reference: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md line 570

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

## Completed So Far

✅ Gap #1: X-Request-ID Tracing - All requests have trace IDs
✅ Gap #28A: Test Endpoints - All endpoints have /test variants for dev testing
✅ Gap #28B: Idempotency Handling - Middleware prevents duplicate transactions
✅ Gap #40: Fixed current_user.tenant_id - All routes use AuthenticatedUser type
✅ Gap #31-33: Database Triggers - Quote totals, change order totals, user email sync

## Current Task

**Implement Tax Calculation System (#11)**

**Priority:** 🔴 **BLOCKER**  
**Estimated Effort:** 5 days  
**Design Spec:** See dev-docs/db-design/aevofab-db-process-v2.6h.md Section 5.1

### Problem Statement

From `phase-1-4-implementation-gap-analysis.md`:

> **Design Requirement:** Section 5.1 - Tax components stored in `quote_line_tax_component`  
> **Current State:** Table exists, never populated  
> **Impact:** Quotes show incorrect totals, legal compliance issues  

### Current Behavior (BROKEN)

When creating a quote line via `POST /quotes/{id}/lines`, the system:
1. ✅ Creates the `quote_line` record with `subtotal_cents` = quantity × unit_price_cents
2. ❌ Sets `tax_amount_cents` = 0 (ALWAYS WRONG)
3. ❌ Never populates `quote_line_tax_component` table
4. ✅ Trigger recalculates quote header totals (but with wrong tax values)

### Expected Behavior (REQUIRED)

When creating a quote line, the system must:
1. Look up the site's jurisdiction code (from `site.jurisdiction_code` or default)
2. Query `tax_rate_version` matching:
   - `jurisdiction_code` = site's jurisdiction
   - `valid_period` contains quote creation timestamp (use GiST `@>` operator)
3. Calculate tax per component:
   - `tax_amount_cents` = `subtotal_cents` × (`rate_pct` / 100)
   - Round UP to nearest cent (IRS compliance)
4. Insert `quote_line_tax_component` records
5. Update `quote_line.tax_amount_cents` = sum of all components
6. Store audit fields: `tax_as_of`, `tax_jurisdiction_code`, `tax_source`
7. Let existing trigger handle quote header rollup

### The Snapshot Principle (CRITICAL)

From `aevofab-db-process-v2.6h.md`:

> **The Snapshot Principle:** Financial records (`unit_price_cents`, `tax_rate_pct`, `tax_amount_cents`) are hardcoded directly onto the lines at the moment of creation. They do not dynamically update if pricebooks change later, preserving historical accuracy.

**This means:**
- Tax rates are **snapshotted** to `quote_line` at creation time
- If tax rates change tomorrow, old quotes **must not recalculate**
- `quote_line_tax_component` provides audit trail for compliance

## Requirements

### 1. Documentation Standards
- **New docs go in dev-docs/** organized by topic:
  - `analysis/` - Gap analysis, remediation plans
  - `architecture-design/` - System architecture docs
  - `db-design/` - Database schema and process docs
  - `product-requirements/` - PRD and user stories
  - `testing-support/` - Test guides and examples
  - `api-guides/` - API usage documentation
- **Always reference the authoritative design docs:**
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations
  - `dev-docs/architecture-design/mvp-arch.md` - System architecture
  - `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap tracking
- **Create remediation plan first** (gap-11-tax-calculation-remediation-plan.md) before coding
- **Update gap analysis** when marking task complete

### 2. Testing Standards
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:** `cd backend && source .venv/bin/activate && pytest tests/ -v`
- **All existing tests must pass** before new code is merged (currently 91 tests)
- **Create new test file:** `backend/tests/test_tax_calculation.py`
- **Test coverage required:**
  - Unit tests for tax calculation logic
  - Integration tests for quote line creation with tax
  - Edge cases: exempt items, multi-jurisdiction, rounding
  - Test both authenticated and /test endpoints
- **Use existing fixtures:** See `backend/tests/conftest.py`

### 3. Code Standards
- **Follow existing patterns** - Check similar implementations first
- **Type hints required** - Use AuthenticatedUser, not User
- **Error handling** - RFC 7807 format (see existing routes)
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization

### 4. Database Standards
- **DO NOT hallucinate schema** - Always read backend/app/models/*.py first
- **Use Alembic migrations** for schema changes (if needed)
- **Respect tenant isolation** - All queries filter by tenant_id
- **Follow ORM patterns** - Use SQLModel/SQLAlchemy correctly
- **Use GiST temporal queries** - For valid_period lookups

### 5. Workflow
1. **Read the gap analysis** to understand the issue
2. **Review design specs** (db-process-v2.6h.md Section 5.1)
3. **Create remediation plan** document with detailed tasks
4. **Get approval** on the plan before coding
5. **Implement** following the plan step-by-step
6. **Write tests** alongside implementation
7. **Run all tests** - Must pass before completion (91+ tests)
8. **Update documentation** - Mark gap as RESOLVED
9. **Commit** with descriptive message

## Key Files to Review

### Architecture & Design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Section 5.1 (Immutable Financial Snapshots)
- `dev-docs/architecture-design/mvp-arch.md` - Overall system design
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Line 186-198 (Gap #11 details)

### Database Models (READ THESE FIRST)
- `backend/app/models/catalog.py` - TaxRateVersion model
- `backend/app/models/quoting.py` - TaxabilityCode model
- `backend/app/models/quoting.py` - QuoteLineTaxComponent model
- `backend/app/models/quoting.py` - QuoteLine model (see tax fields)
- `backend/app/models/crm.py` - Site model (jurisdiction_code field)

### Current Implementation
- `backend/api/routes/quotes.py` - Quote line creation (needs tax logic)
- `backend/tests/test_quotes.py` - Existing quote tests (will need updates)

### Reference Examples
- `backend/core/idempotency.py` - Middleware pattern example
- `backend/migrations/versions/2026_03_17_1451-a4d2659a2921_*.py` - Database trigger examples
- `dev-docs/analysis/gap-31-33-database-triggers-remediation-plan.md` - Recent remediation plan example

## Technical Specifications

### MVP Tax Calculation Logic

For MVP, implement **simple jurisdiction-based tax lookup**. Advanced features (TaxJar API, address-based rates) are out of scope.

#### 1. Tax Rate Lookup Algorithm

```python
def get_tax_rate_for_quote_line(
    db: Session,
    site_id: UUID,
    taxability_code: str,
    as_of_timestamp: datetime
) -> List[TaxRateVersion]:
    """
    Look up applicable tax rates for a quote line.
    
    Args:
        db: Database session
        site_id: Site where work will be performed
        taxability_code: 'taxable', 'exempt', 'zero_rated'
        as_of_timestamp: Quote creation time (for temporal lookup)
    
    Returns:
        List of TaxRateVersion records (may be multiple components like state+county+city)
    
    Notes:
        - If taxability_code is 'exempt', return empty list (0% tax)
        - Use GiST @> operator for temporal queries
        - Site jurisdiction is sourced from site.jurisdiction_code (e.g., 'US-TX-HARRIS')
    """
    # Step 1: Get site jurisdiction
    site = db.get(Site, site_id)
    if not site:
        raise ValueError(f"Site {site_id} not found")
    
    jurisdiction = site.jurisdiction_code or "US-DEFAULT"  # Fallback to default
    
    # Step 2: Handle tax-exempt items
    if taxability_code == "exempt":
        return []
    
    # Step 3: Query tax_rate_version with temporal lookup
    query = select(TaxRateVersion).where(
        TaxRateVersion.jurisdiction_code == jurisdiction,
        TaxRateVersion.valid_period.contains(as_of_timestamp)  # GiST operator
    )
    
    tax_rates = db.exec(query).all()
    return tax_rates
```

#### 2. Tax Component Calculation

```python
def calculate_tax_components(
    db: Session,
    quote_line: QuoteLine,
    tax_rates: List[TaxRateVersion]
) -> Tuple[int, List[QuoteLineTaxComponent]]:
    """
    Calculate tax amount and create tax component records.
    
    Args:
        db: Database session
        quote_line: The quote line being taxed
        tax_rates: List of applicable tax rates
    
    Returns:
        Tuple of (total_tax_amount_cents, list_of_tax_components)
    
    Notes:
        - Round UP each component (IRS compliance)
        - Use Decimal for precision, convert to int at the end
    """
    from decimal import Decimal, ROUND_CEILING
    
    components = []
    total_tax_cents = 0
    
    for tax_rate in tax_rates:
        # Calculate tax for this component
        subtotal = Decimal(quote_line.subtotal_cents) / Decimal(100)
        rate = Decimal(str(tax_rate.rate_pct)) / Decimal(100)
        tax_amount = subtotal * rate
        
        # Round UP to nearest cent (IRS requirement)
        tax_amount_cents = int(tax_amount.quantize(Decimal('0.01'), rounding=ROUND_CEILING) * 100)
        
        # Create component record
        component = QuoteLineTaxComponent(
            quote_line_id=quote_line.id,
            tax_rate_version_id=tax_rate.id,
            component_code=tax_rate.jurisdiction_code,
            rate_pct=float(tax_rate.rate_pct),
            amount_cents=tax_amount_cents
        )
        components.append(component)
        total_tax_cents += tax_amount_cents
    
    return total_tax_cents, components
```

#### 3. Integration Point

Modify `_create_quote_line_impl()` to call tax calculation:

```python
def _create_quote_line_impl(
    quote_id: UUID,
    line_in: QuoteLineCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteLine:
    # ... existing validation ...
    
    # Calculate subtotal
    subtotal_cents = int(Decimal(str(line_in.quantity)) * line_in.unit_price_cents)
    
    # NEW: Calculate tax
    quote = db.get(Quote, quote_id)
    taxability = line_in.taxability_code or "taxable"
    
    tax_rates = get_tax_rate_for_quote_line(
        db=db,
        site_id=quote.site_id,
        taxability_code=taxability,
        as_of_timestamp=datetime.now(UTC)
    )
    
    total_tax_cents, tax_components = calculate_tax_components(
        db=db,
        quote_line=quote_line,  # Pass partially constructed line
        tax_rates=tax_rates
    )
    
    # Update quote line with tax values
    quote_line.tax_amount_cents = total_tax_cents
    quote_line.tax_rate_pct = sum(rate.rate_pct for rate in tax_rates)  # Combined rate
    quote_line.tax_as_of = datetime.now(UTC)
    quote_line.tax_jurisdiction_code = tax_rates[0].jurisdiction_code if tax_rates else None
    quote_line.tax_source = "internal_lookup"  # vs "taxjar_api" for future
    quote_line.total_cents = subtotal_cents + total_tax_cents
    
    # Save quote line first to get ID
    db.add(quote_line)
    db.flush()  # Get ID without committing
    
    # Save tax components
    for component in tax_components:
        component.quote_line_id = quote_line.id  # Now we have the ID
        db.add(component)
    
    db.commit()
    db.refresh(quote_line)
    
    # Trigger will auto-update quote header totals
    return quote_line
```

### MVP Scope Decisions

#### IN SCOPE (Must Implement)
- ✅ Jurisdiction-based tax rate lookup via `tax_rate_version`
- ✅ Temporal tax rate queries (GiST `@>` operator)
- ✅ Tax component creation in `quote_line_tax_component`
- ✅ Snapshot principle enforcement (hardcoded values)
- ✅ Support for `taxable`, `exempt`, `zero_rated` taxability codes
- ✅ IRS-compliant rounding (round UP)
- ✅ Audit trail fields (tax_as_of, tax_jurisdiction_code, tax_source)
- ✅ Both authenticated and /test endpoints
- ✅ Comprehensive test coverage

#### OUT OF SCOPE (Defer to Phase 2+)
- ❌ TaxJar/Avalara API integration (use `tax_source='taxjar_api'` later)
- ❌ Address-based tax rate resolution (geocoding)
- ❌ Sales tax exemption certificates
- ❌ Multi-currency tax calculations
- ❌ Tax holiday support
- ❌ Reverse charge VAT (international)

#### Default Behavior for MVP
- If `site.jurisdiction_code` is NULL, use `"US-DEFAULT"` jurisdiction
- If no tax rates found, set `tax_amount_cents = 0` (log warning)
- If `taxability_code` is NULL on quote line, default to `"taxable"`

## Success Criteria

- [ ] Remediation plan created: `dev-docs/analysis/gap-11-tax-calculation-remediation-plan.md`
- [ ] Tax rate lookup function implemented with temporal queries
- [ ] Tax component calculation with IRS-compliant rounding
- [ ] Quote line creation integrates tax calculation (authenticated endpoint)
- [ ] Quote line creation integrates tax calculation (/test endpoint)
- [ ] Change order lines also support tax calculation (if time permits)
- [ ] All existing tests pass (91 tests minimum)
- [ ] New test file created: `backend/tests/test_tax_calculation.py`
- [ ] Test coverage:
  - [ ] Basic taxable item (8.25% tax)
  - [ ] Tax-exempt item (0% tax)
  - [ ] Multi-component tax (state 6% + county 1.5% + city 0.75%)
  - [ ] Rounding edge case (ensure rounds UP)
  - [ ] Missing jurisdiction (uses default)
  - [ ] Historical tax rate lookup (temporal query)
  - [ ] Test endpoint with tax calculation
- [ ] Documentation updated:
  - [ ] Gap #11 marked RESOLVED in phase-1-4-implementation-gap-analysis.md
  - [ ] Line 570 marked complete
- [ ] Code follows existing patterns and standards
- [ ] Commit with message: `feat: implement gap #11 - tax calculation system`

## Questions to Ask

### Before starting:
1. Have I read the gap analysis entry thoroughly? (Lines 186-198)
2. Have I reviewed Section 5.1 of the process document?
3. Do I understand the Snapshot Principle?
4. Have I examined the TaxRateVersion, TaxabilityCode, and QuoteLineTaxComponent models?
5. What existing code can I reference for patterns?

### During implementation:
1. Am I following the existing quote line creation pattern?
2. Are all tests passing after my changes?
3. Have I tested both authenticated and /test endpoints?
4. Is my tax calculation using IRS-compliant rounding?
5. Am I documenting as I go?

### Before completion:
1. Did I create the remediation plan first?
2. Are all 91+ tests passing?
3. Did I add comprehensive test coverage for tax scenarios?
4. Did I update the gap analysis to mark Gap #11 as RESOLVED?
5. Is the code aligned with 80/20 MVP priorities?

## Example Task Flow

```bash
# 1. Review the gap analysis details
cat dev-docs/analysis/phase-1-4-implementation-gap-analysis.md | grep -A 20 "Gap #11"

# 2. Check the database models
cat backend/app/models/catalog.py | grep -A 15 "class TaxRateVersion"
cat backend/app/models/quoting.py | grep -A 15 "class QuoteLineTaxComponent"

# 3. Run existing tests to establish baseline
cd backend && source .venv/bin/activate
pytest tests/ -v
# Should see: 91 passed

# 4. Create remediation plan document
# Create dev-docs/analysis/gap-11-tax-calculation-remediation-plan.md

# 5. Implement tax calculation functions in new module
# Create backend/core/tax_calculation.py

# 6. Integrate into quote line creation
# Modify backend/api/routes/quotes.py

# 7. Create comprehensive tests
# Create backend/tests/test_tax_calculation.py

# 8. Run all tests
pytest tests/ -v
# Should see: 100+ passed (91 existing + new tax tests)

# 9. Update gap analysis
# Mark Gap #11 as RESOLVED with ✅ status

# 10. Commit
git add .
git commit -m "feat: implement gap #11 - tax calculation system

- Add tax rate lookup with temporal queries
- Calculate tax components with IRS-compliant rounding
- Integrate into quote line and change order line creation
- Add comprehensive test coverage (15+ tests)
- Update gap analysis to mark #11 as RESOLVED

Resolves: Gap #11 (BLOCKER)
Tests: 106/106 passing
"
```

## Data Seeding Requirements

For testing, you'll need sample tax rate data. Add to `migrations/seed_test_data.py`:

```python
# Sample Tax Rates for Testing
tax_rates = [
    {
        "jurisdiction_code": "US-TX-HARRIS",
        "description": "Harris County, TX Combined Rate",
        "rate_pct": 8.25,
        "valid_period": "[2024-01-01,)",  # Open-ended
    },
    {
        "jurisdiction_code": "US-CA-LA",
        "description": "Los Angeles County, CA",
        "rate_pct": 9.5,
        "valid_period": "[2024-01-01,)",
    },
    {
        "jurisdiction_code": "US-DEFAULT",
        "description": "Default US Sales Tax",
        "rate_pct": 6.0,
        "valid_period": "[2020-01-01,)",
    },
]

# Taxability Codes
taxability_codes = [
    {"code": "taxable", "name": "Taxable", "description": "Standard sales tax applies"},
    {"code": "exempt", "name": "Tax Exempt", "description": "No sales tax"},
    {"code": "zero_rated", "name": "Zero-Rated", "description": "0% tax rate (different from exempt for reporting)"},
]
```

## Notes

- **MVP Focus:** Follow dev-docs/product-requirements/mvp-prd.md for scope
- **80/20 Rule:** See .roo/rules-mvp-builder/80-20-prioritization.md
- **Mike the Solo Contractor:** Our primary persona - keep it simple!
- **No Enterprise Features:** Multi-currency, international VAT, complex exemptions are out of scope
- **Financial Accuracy:** This is a BLOCKER because incorrect tax = legal liability
- **IRS Compliance:** Always round UP when splitting tax across items

## References

### Design Documents
- `aevofab-db-process-v2.6h.md` - Section 5.1
- `phase-1-4-implementation-gap-analysis.md` - Lines 186-198, 570

### Database Schema
- TaxRateVersion: Temporal tax rate storage with GiST constraints
- QuoteLineTaxComponent: Audit trail for multi-component taxes
- TaxabilityCode: Item-level tax treatment classification

### Similar Implementations
- Markup calculation in `backend/api/routes/jobs.py`
- Temporal queries in markup version lookup
- Snapshot principle in quote line creation

### External Resources (Post-MVP)
- TaxJar API: https://developers.taxjar.com/api/reference/
- IRS Rounding Rules: Publication 1178
- Multi-jurisdictional tax: https://www.salestaxinstitute.com/
```

---

## Usage

1. Copy the prompt section above
2. Start new Roo Coder session in **Code mode** (not Architect)
3. Paste the full prompt
4. The AI will have complete context to implement tax calculations

---

## Deliverables Checklist

After completion, verify:

- [ ] `backend/core/tax_calculation.py` - New module with tax functions
- [ ] `backend/api/routes/quotes.py` - Updated with tax integration
- [ ] `backend/tests/test_tax_calculation.py` - 15+ comprehensive tests
- [ ] `dev-docs/analysis/gap-11-tax-calculation-remediation-plan.md` - Detailed plan
- [ ] `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gap #11 marked RESOLVED
- [ ] `backend/migrations/seed_test_data.py` - Tax rate sample data
- [ ] All 106+ tests passing
- [ ] Git commit with descriptive message
