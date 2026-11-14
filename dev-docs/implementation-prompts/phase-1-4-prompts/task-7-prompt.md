# Task #7: Polymorphic Relationships (EntityContact & EntityAddress APIs)

Use this prompt to start implementing Task #7 from Phase 1-B.

---

## PROMPT FOR TASK #7

```
Task: Implement Gaps #6, #7, #8 - Polymorphic Relationships
Reference: dev-docs/analysis/phase-1-4-implementation-gap-analysis.md lines 125-154, 669-672

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

The database has polymorphic tables (`entity_contact` and `entity_address`) that allow flexible many-to-many relationships between entities (customers, sites, jobs) and their associated contacts/addresses. These tables exist but are completely unused - no API endpoints, no business logic, no integration with existing workflows.

## Completed So Far

✅ Gap #28A: Test Endpoints - All endpoints have /test variants for dev testing
✅ Gap #40: Fixed current_user.tenant_id - All routes use AuthenticatedUser type
✅ Gap #28B: Idempotency Handling - Middleware prevents duplicate transactions
✅ Gap #1: X-Request-ID Tracing - Request tracking with UUID validation
✅ Gap #31-33: Database Triggers - Quote totals, change order totals, user email sync
✅ Gap #11: Tax Calculations - Jurisdiction-based tax lookup with IRS-compliant rounding
✅ Gap #38: Multi-Tenancy Isolation Tests - 26 tests verify cross-tenant data protection
✅ **Phase 1-A Complete** - System safe for single-tenant pilot

## Current Task

Implement polymorphic relationship management for Contacts and Addresses. This enables the core CRM functionality needed for Mike the Solo Contractor to properly manage customer relationships, job sites, and contact points.

**Priority:** BLOCKER (Phase 1-B)  
**Estimated Effort:** 6 days  
**Design Spec:** See dev-docs/db-design/aevofab-db-process-v2.6h.md Section 2

### Gap #6: Polymorphic Entity Relationships (BLOCKER)

**Current State:** 
- `EntityContact` and `EntityAddress` tables exist but are unused
- No API endpoints to create/query these relationships
- Customer and Site creation doesn't establish any contact/address associations

**Impact:** 
- Cannot model real-world customer relationships (multiple contacts per customer)
- Cannot track site addresses for job location routing
- Cannot distinguish between billing address vs. service location
- Cannot link decision-makers to specific projects

**Example Missing Flow:**
```python
# Current behavior: Customer has direct email/phone (limited to 1 contact)
customer = Customer(email="john@example.com", mobile_phone="555-1234")

# Desired behavior: Customer can have multiple contacts with roles
customer = Customer(display_name="ABC Electrical")
# Create primary contact
contact1 = Contact(first_name="John", last_name="Doe", email="john@abc.com")
EntityContact(
    entity_type_code="customer", 
    entity_id=customer.id,
    contact_id=contact1.id,
    contact_type_code="primary",
    is_primary=True
)
# Create billing contact
contact2 = Contact(first_name="Jane", last_name="Smith", email="billing@abc.com")
EntityContact(
    entity_type_code="customer",
    entity_id=customer.id,
    contact_id=contact2.id,
    contact_type_code="billing",
    is_primary=False
)
```

### Gap #7: Site Address Management (HIGH PRIORITY)

**Current State:**
- `Site` table exists but has no address linkage
- No way to geocode job sites or calculate drive time
- `jurisdiction_code` field exists (added in Gap #11) but no structured address

**Impact:**
- Cannot perform job site routing calculations
- Cannot validate service areas
- Tax jurisdiction lookup relies on manual `jurisdiction_code` entry instead of address-based lookup

**Missing Flow:**
```python
# Site creation should automatically link an address
site = Site(customer_id=customer_id, name="Main Office")
address = Address(
    line1="123 Main St",
    city="Houston",
    state="TX",
    postal_code="77001"
)
EntityAddress(
    entity_type_code="site",
    entity_id=site.id,
    address_id=address.id,
    address_type_code="service_location",
    is_primary=True
)
```

### Gap #8: Contact Management Separate from Customer (HIGH PRIORITY)

**Current State:**
- `Contact` model exists but has no API endpoints
- Customer has direct `email` and `mobile_phone` fields (anti-pattern)
- No way to track multiple contacts per customer
- No contact role differentiation (primary, billing, technical, etc.)

**Impact:**
- Cannot model companies with multiple decision-makers
- Cannot route quote notifications to different contacts based on role
- Cannot track which contact requested which quote

**Missing Implementation:**
- Full Contact CRUD API (`/api/v1/contacts/`)
- EntityContact association endpoints
- Contact role management
- Contact search/filtering by entity

## Requirements

### 1. API Endpoints to Create

#### Contact Management (`backend/api/routes/contacts.py`)
```python
# Core CRUD
POST   /api/v1/contacts/           # Create contact
GET    /api/v1/contacts/           # List all contacts (with optional filters)
GET    /api/v1/contacts/{id}       # Get contact details
PATCH  /api/v1/contacts/{id}       # Update contact
DELETE /api/v1/contacts/{id}       # Soft delete contact

# Association management
POST   /api/v1/contacts/{id}/link-to-entity     # Link contact to customer/site/job
DELETE /api/v1/contacts/{id}/unlink-from-entity # Unlink contact from entity
GET    /api/v1/contacts/by-entity/{entity_type}/{entity_id}  # Get all contacts for an entity

# Test endpoints (unauthenticated variants)
POST   /api/v1/contacts/test
GET    /api/v1/contacts/test
GET    /api/v1/contacts/{id}/test
PATCH  /api/v1/contacts/{id}/test
DELETE /api/v1/contacts/{id}/test
```

#### Address Management (`backend/api/routes/addresses.py`)
```python
# Core CRUD
POST   /api/v1/addresses/          # Create address
GET    /api/v1/addresses/          # List all addresses
GET    /api/v1/addresses/{id}      # Get address details
PATCH  /api/v1/addresses/{id}      # Update address
DELETE /api/v1/addresses/{id}      # Soft delete address

# Association management
POST   /api/v1/addresses/{id}/link-to-entity     # Link address to customer/site/job
DELETE /api/v1/addresses/{id}/unlink-from-entity # Unlink address from entity
GET    /api/v1/addresses/by-entity/{entity_type}/{entity_id}  # Get all addresses for an entity

# Test endpoints
POST   /api/v1/addresses/test
GET    /api/v1/addresses/test
GET    /api/v1/addresses/{id}/test
PATCH  /api/v1/addresses/{id}/test
DELETE /api/v1/addresses/{id}/test
```

#### Enhanced Site Creation (`backend/api/routes/sites.py`)
```python
# Existing endpoint enhancement
POST /api/v1/sites/
# Request body should accept optional nested address:
{
  "customer_id": "uuid",
  "name": "Main Office",
  "address": {  # Optional - if provided, creates Address + EntityAddress
    "line1": "123 Main St",
    "city": "Houston",
    "state": "TX",
    "postal_code": "77001"
  }
}
```

### 2. Request/Response Schemas

#### Contact Schemas (`backend/api/schemas/contacts.py` - NEW FILE)
```python
from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional

class ContactCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_phone: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    notes: Optional[str] = None

class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_phone: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class ContactResponse(BaseModel):
    id: UUID
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    mobile_phone: Optional[str]
    locale: Optional[str]
    timezone: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str

class EntityContactLink(BaseModel):
    entity_type_code: str  # "customer" | "site" | "job"
    entity_id: UUID
    contact_type_code: str  # "primary" | "billing" | "technical"
    is_primary: bool = False

class ContactWithRelations(ContactResponse):
    """Contact with its entity associations"""
    linked_entities: list[dict]  # [{entity_type: "customer", entity_id: "...", contact_type: "primary"}]
```

#### Address Schemas (`backend/api/schemas/addresses.py` - NEW FILE)
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class AddressCreate(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class AddressUpdate(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = None

class AddressResponse(BaseModel):
    id: UUID
    line1: Optional[str]
    line2: Optional[str]
    line3: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: str
    latitude: Optional[float]
    longitude: Optional[float]
    is_active: bool
    created_at: str
    updated_at: str

class EntityAddressLink(BaseModel):
    entity_type_code: str  # "customer" | "site" | "job"
    entity_id: UUID
    address_type_code: str  # "billing" | "service_location" | "mailing"
    is_primary: bool = False

class AddressWithRelations(AddressResponse):
    """Address with its entity associations"""
    linked_entities: list[dict]  # [{entity_type: "site", entity_id: "...", address_type: "service_location"}]
```

### 3. Business Logic Rules

#### Tenant Isolation
- **CRITICAL**: All Contact and Address queries MUST filter by entities owned by the tenant
- EntityContact and EntityAddress create polymorphic links - verify entity ownership before linking
- Use test endpoints for development/testing (bypass auth but still validate structure)

#### Validation Rules
- **EntityContact**: 
  - `entity_type_code` must exist in `entity_type` table
  - `contact_type_code` must exist in `contact_type` table
  - Only one contact can be `is_primary=True` per entity
  - Cannot link same contact to same entity twice with same contact_type
  
- **EntityAddress**:
  - `entity_type_code` must exist in `entity_type` table
  - `address_type_code` must exist in `address_type` table
  - Only one address can be `is_primary=True` per entity per address_type
  - Cannot link same address to same entity twice with same address_type

#### Site Address Auto-Creation
- When creating a Site with nested `address` data:
  1. Create Address record
  2. Create Site record
  3. Create EntityAddress linking them with `address_type_code='service_location'` and `is_primary=True`
- All 3 operations must succeed or rollback (transaction)

### 4. Testing Requirements

Create `backend/tests/test_contacts.py` with minimum 15 tests:
- Contact CRUD operations (create, list, get, update, delete)
- Contact-to-Customer linking via EntityContact
- Contact-to-Site linking via EntityContact
- Primary contact enforcement (only one is_primary per entity)
- Tenant isolation (User A cannot see User B's contacts)
- Test endpoints work without authentication

Create `backend/tests/test_addresses.py` with minimum 15 tests:
- Address CRUD operations (create, list, get, update, delete)
- Address-to-Site linking via EntityAddress
- Address-to-Customer linking via EntityAddress
- Primary address enforcement per address_type
- Tenant isolation
- Test endpoints work without authentication

Enhance `backend/tests/test_phase2.py`:
- Add test for Site creation with nested address
- Verify EntityAddress is created automatically
- Verify address appears in Site response

### 5. Database Considerations

**DO NOT create new migrations** - all tables already exist:
- `contact` - Line 109-126 of crm.py
- `address` - Line 128-145 of crm.py
- `entity_contact` - Line 148-159 of crm.py
- `entity_address` - Line 161-172 of crm.py
- `contact_type` - Line 52-59 of crm.py (lookup table)
- `address_type` - Line 42-49 of crm.py (lookup table)
- `entity_type` - Defined in core.py

**Reference Data Needed:**
Ensure `entity_type` table has these codes:
- `customer`
- `site`
- `job`
- `quote`

Ensure `contact_type` table has:
- `primary`
- `billing`
- `technical`
- `decision_maker`

Ensure `address_type` table has:
- `billing`
- `service_location`
- `mailing`
- `shipping`

Check existing seed data in `backend/migrations/seed_test_data.py` and add if missing.

### 6. Documentation Standards
- **New docs go in dev-docs/** organized by topic
- **Create remediation plan first**: `dev-docs/analysis/gap-6-7-8-polymorphic-relationships-remediation-plan.md`
- **Reference authoritative design docs:**
  - `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Section 2 (Polymorphic Relationships)
  - `dev-docs/architecture-design/mvp-arch.md` - CRM module architecture
- **Update gap analysis** when marking tasks complete

### 7. Testing Standards
- **Tests are MANDATORY** - No code without tests
- **Run existing tests first:** `cd backend && source .venv/bin/activate && pytest tests/`
- **All existing tests must pass** (currently 129/129 passing)
- **Create new test files:** `test_contacts.py`, `test_addresses.py`
- **Minimum 30+ new tests total**
- **Test coverage required:**
  - CRUD operations for both Contact and Address
  - EntityContact linking/unlinking
  - EntityAddress linking/unlinking
  - Tenant isolation for polymorphic queries
  - Site address auto-creation
  - Validation rules (primary enforcement, duplicate prevention)
  - Test endpoints (unauthenticated access)

### 8. Code Standards
- **Follow existing patterns** - Check `backend/api/routes/customers.py` for CRUD pattern
- **Type hints required** - Use `AuthenticatedUser` for authenticated endpoints
- **Error handling** - RFC 7807 format (see existing routes)
- **Shared implementation pattern** - Use `_impl()` functions like customers.py
- **Test endpoints** - All routes need `/test` suffix variants
- **Docstrings required** - Document all functions/classes
- **No feature creep** - Strictly follow 80/20 MVP prioritization

### 9. Workflow

1. **Read the gap analysis** (lines 125-154)
2. **Review design specs** (db-process-v2.6h.md Section 2, mvp-arch.md)
3. **Create remediation plan** document with detailed implementation steps
4. **Review existing models** in backend/app/models/crm.py (already done above)
5. **Implement** following the plan:
   a. Create schema files (contacts.py, addresses.py)
   b. Create route files (contacts.py, addresses.py)
   c. Enhance sites.py for nested address creation
   d. Register routes in `backend/api/routes/__init__.py`
   e. Add reference data seeding if needed
6. **Write tests** alongside implementation
7. **Run all tests** - Must pass before completion
8. **Update documentation** - Mark gaps #6, #7, #8 as RESOLVED

## Key Files to Review

### Architecture
- `dev-docs/architecture-design/mvp-arch.md` - CRM module design
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Section 2 (Polymorphic Relationships)
- `dev-docs/analysis/phase-1-4-implementation-gap-analysis.md` - Gaps #6, #7, #8

### Backend Code
- `backend/app/models/crm.py` - All CRM models (Customer, Site, Contact, Address, EntityContact, EntityAddress)
- `backend/api/routes/customers.py` - Example CRUD pattern to follow
- `backend/api/routes/sites.py` - Will need enhancement for nested address
- `backend/core/` - Core utilities (auth, db, middleware)
- `backend/tests/conftest.py` - Test fixtures
- `backend/tests/test_phase2.py` - Existing CRM tests

### Existing Tests
Run to establish baseline:
```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
# Should see: 129 passed
```

## Success Criteria

- [ ] Remediation plan created and approved
- [ ] Contact CRUD API implemented with all endpoints
- [ ] Address CRUD API implemented with all endpoints  
- [ ] EntityContact linking/unlinking endpoints working
- [ ] EntityAddress linking/unlinking endpoints working
- [ ] Site creation accepts nested address and creates EntityAddress automatically
- [ ] Reference data seeded (entity_type, contact_type, address_type)
- [ ] All existing tests pass (129/129)
- [ ] New test_contacts.py created with 15+ tests passing
- [ ] New test_addresses.py created with 15+ tests passing
- [ ] Enhanced test_phase2.py with site address tests
- [ ] Tenant isolation verified for all polymorphic queries
- [ ] Test endpoints working for dev/testing
- [ ] Documentation updated
- [ ] Gaps #6, #7, #8 marked RESOLVED in phase-1-4-implementation-gap-analysis.md
- [ ] Code follows existing patterns and standards

## Questions to Ask Before Starting

1. Have I read gaps #6, #7, #8 in the gap analysis thoroughly?
2. Have I reviewed Section 2 of aevofab-db-process-v2.6h.md (Polymorphic Relationships)?
3. Do I understand the difference between Contact (entity) vs EntityContact (association)?
4. Do I understand the difference between Address (entity) vs EntityAddress (association)?
5. Have I reviewed the existing Customer CRUD pattern to replicate?
6. What reference data needs to be seeded?
7. How will tenant isolation work for polymorphic queries?

## Questions During Implementation

1. Am I following the customers.py pattern for CRUD operations?
2. Are all queries filtering by tenant ownership (via entity_id → customer_id → tenant_id)?
3. Am I enforcing the "only one is_primary" rule correctly?
4. Are all tests passing including existing ones?
5. Am I documenting as I go?
6. Is the Site nested address creation atomic (transaction-safe)?

## 80/20 MVP Considerations

**IN SCOPE for MVP:**
- Basic Contact CRUD (single contractor needs basic contact tracking)
- Basic Address CRUD (job sites need addresses)
- Site-to-Address linking (critical for job routing)
- Customer-to-Contact linking (track decision-makers)
- Primary contact/address designation

**OUT OF SCOPE for MVP (defer to Phase 1-C or later):**
- Contact deduplication logic
- Address geocoding automation (can be added later via TaxJar/Google Maps API)
- Contact merge/split operations
- Advanced contact searching (fuzzy match, phone normalization)
- Contact history/activity timeline
- Bulk contact import

**For Mike the Solo Contractor:**
- He needs to track 2-3 contacts per commercial customer (decision-maker, billing, on-site contact)
- He needs job site addresses for routing and tax jurisdiction lookup
- He doesn't need enterprise contact management features
- Keep the API simple and focused on these core use cases

## Notes

- **Polymorphic pattern**: `entity_type_code` + `entity_id` allows flexible associations without rigid foreign keys
- **Tenant isolation is tricky**: Must traverse entity_id → customer_id → tenant_id for Contact/Address queries
- **Primary enforcement**: Only one contact/address can be `is_primary=True` per entity (per type for addresses)
- **Test endpoints critical**: Enable frontend development without Cognito setup
- **Site enhancement is gentle**: Don't break existing Site creation - nested address is optional
- **Reference data**: Ensure lookup tables are seeded (entity_type, contact_type, address_type)

## Phase 1-B Context

This is Task #7 of Phase 1-B. Completing this task enables:
- Proper customer relationship modeling (multiple contacts)
- Job site address tracking (routing, tax lookup)
- Foundation for Quote acceptance workflow (contact signatures)
- Foundation for Voice AI context ("send quote to the billing contact")

After this task, the next priorities are:
- Task #8: Quote Acceptance Workflow (#13)
- Task #9: Voice Action Execution (#17)
- Task #10: Context Window Management (#18)

```

## Usage

1. Copy the prompt section above
2. Start new development session
3. Create remediation plan first
4. Implement following the plan
5. Run tests continuously
6. Update gap analysis when complete
