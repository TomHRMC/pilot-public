# Adding Resiliency to Tests

> **Context**: Tests run against the shared `pilot_dev` PostgreSQL database. The `db_session` fixture rolls back
> per-test, but **committed seed data from `seed_scenario_*.py` scripts is visible to all tests** for the
> lifetime of that data in the DB. Tests must never assume the DB is empty.

---

## The Core Rule

> **A test must only rely on data it creates itself — never assume the DB is empty.**

---

## Pattern 1 — "Empty List" Assertions Need a Setup Wipe

**❌ Fragile**
```python
def test_list_addresses_empty(self, client, test_tenant):
    response = client.get("/api/v1/addresses/test")
    assert response.json() == []   # FAILS when seed scripts have run
```

**✅ Resilient**
```python
def test_list_addresses_empty(self, client, test_tenant, db_session):
    # Delete child FK rows first, then parent rows
    db_session.exec(delete(EntityAddress).where(EntityAddress.tenant_id == test_tenant.id))
    db_session.exec(delete(Address).where(Address.tenant_id == test_tenant.id))
    db_session.commit()

    response = client.get("/api/v1/addresses/test")
    assert response.json() == []
```

**Rule**: Delete tenant-scoped rows at test start. Always delete **child FK rows first** (e.g. `entity_address` before `address`).

---

## Pattern 2 — Count Assertions Must Filter by Test Data

**❌ Fragile**
```python
result = db_session.exec(select(PricebookItem).where(tenant_id == test_tenant.id)).all()
assert len(result) == 2   # FAILS when seed has added 5 more items
```

**✅ Resilient**
```python
# Use unique SKUs and filter by them
item1 = PricebookItem(sku="PANEL-200A-UNIQUETEST", ...)
item2 = PricebookItem(sku="PANEL-400A-UNIQUETEST", ...)
db_session.add_all([item1, item2])
db_session.commit()

result = db_session.exec(
    select(PricebookItem).where(PricebookItem.sku.in_(["PANEL-200A-UNIQUETEST", "PANEL-400A-UNIQUETEST"]))
).all()
assert len(result) == 2
```

**Rule**: Filter counts by the specific IDs or unique keys your test created — never filter only by `tenant_id`.

---

## Pattern 3 — Fixture Names Must Be Unique vs Seeded Data

**❌ Fragile**
```python
@pytest.fixture
def test_customer(db_session, test_tenant, test_user):
    customer = Customer(display_name="John Smith", ...)  # seeded by seed_scenario_quote_to_cash
```

**✅ Resilient**
```python
@pytest.fixture
def test_customer(db_session, test_tenant, test_user):
    # Prefix with something guaranteed not to appear in seed data
    customer = Customer(display_name="ZTEST-John Smith", ...)
```

**Rule**: Use a unique prefix (e.g. `ZTEST-`, `QB-TEST-`, `ZZETAQ-`) for any fixture data that must not collide with seed data.

---

## Pattern 4 — Fuzzy Searches Must Match Exactly One Record

**❌ Fragile**
```python
result = _resolve_customer_for_voice(entities={"customer_name": "Johnson"}, ...)
# FAILS when seed has "Mary Johnson" AND fixture adds "Tom Johnson"
assert "Johnson" in result.display_name
```

**✅ Resilient**
```python
# Use fixture name unique enough to guarantee single match
customer = Customer(display_name="Zzetaq Electrician", ...)

result = _resolve_customer_for_voice(entities={"customer_name": "Zzetaq"}, ...)
assert result.id == test_customer.id
```

**Rule**: Fuzzy-search tests must use a search term that can only match the record created by the test fixture.

---

## Pattern 5 — Unique Constraint Tests Must Use Unique Identifiers

**❌ Fragile**
```python
Customer(display_name="John Smith", ...)  # already seeded → UniqueViolation on uq_customer_tenant_display_name
```

**✅ Resilient**
```python
Customer(display_name="QB Test Customer Zeta", email="qbzeta@zeta-electric-test.example.com", ...)
```

**Rule**: Any test that creates a row with a unique constraint column (e.g. `display_name`, `sku`, `email`) must use a value guaranteed to not exist in seed data.

---

## Pattern 6 — Assertion on Fixture Fields Must Use the Fixture Object

**❌ Fragile**
```python
assert "Tom Johnson" in result["recipient"]  # Hardcoded — breaks when fixture name changes
```

**✅ Resilient**
```python
assert test_customer.display_name in result["recipient"]  # Reads from the fixture object
```

---

## Quick Reference: Known Seeded Names to Avoid

The following names exist in the dev DB after running `seed_scenario_quote_to_cash.py`:

| Table | Seeded values |
|---|---|
| `customer.display_name` | `"John Smith"`, `"Jane Doe"`, `"Bob Davis"`, `"Mary Johnson"`, `"Apex Commercial LLC"`, `"Inactive Customer"` |
| `pricebook_item.sku` | `"SRV-OUTLET-STD"`, `"MAT-CB-15A"`, `"MAT-CONDUIT-EMT"`, `"SRV-PERMIT-RESI"` |

---

## FK Delete Order (Most Common)

When wiping tenant data in a test setup step, always delete **child tables before parent tables**:

```
entity_address   → address
entity_contact   → contact
quote_line       → quote
invoice_line     → invoice
job_tech_assignment → job
pricebook_item_version → pricebook_item
```

---

## When NOT to Use This Pattern

The `db_session` fixture **rolls back** all changes made within a test. You only need setup wipes when:
1. The test queries by **aggregate count** (e.g. `len(data) == 2`)
2. The test expects an **empty list** response
3. The test inserts a row with a **unique constraint** that could collide with seeded data
4. The test uses **fuzzy search** that could match multiple records
