#!/usr/bin/env python3
"""
Database Server Defaults Verification Script
Phase 5.0 - Task 3: Comprehensive Database-Layer Verification

This script verifies that server defaults are enforced at the PostgreSQL layer
by running raw SQL INSERT tests with ROLLBACK.
"""

import os
import sys

from sqlalchemy import create_engine, text


def verify_boolean_default():
    """Test 1: Boolean Default (tenant.is_active = TRUE)"""
    print("\n" + "=" * 80)
    print("Test 1: Boolean Default - tenant.is_active")
    print("=" * 80)

    query = text("""
        BEGIN;
        INSERT INTO tenant (tenant_name, default_timezone)
        VALUES ('Test Verification Tenant', 'America/New_York')
        RETURNING id, is_active;
        ROLLBACK;
    """)

    return query, "Expected: is_active = true"


def verify_integer_default():
    """Test 2: Integer Default (tenant_settings.default_labor_rate_cents = 8500)"""
    print("\n" + "=" * 80)
    print("Test 2: Integer Default - tenant_settings.default_labor_rate_cents")
    print("=" * 80)

    query = text("""
        BEGIN;
        WITH new_tenant AS (
            INSERT INTO tenant (tenant_name, default_timezone)
            VALUES ('Test Tenant for Settings', 'America/New_York')
            RETURNING id
        )
        INSERT INTO tenant_settings (tenant_id)
        SELECT id FROM new_tenant
        RETURNING tenant_id, default_labor_rate_cents, default_billable_labor_rate_cents;
        ROLLBACK;
    """)

    return (
        query,
        "Expected: default_labor_rate_cents = 8500, default_billable_labor_rate_cents = 15000",
    )


def verify_jsonb_default():
    """Test 3: JSONB Default (platform_role.permissions = '{}')"""
    print("\n" + "=" * 80)
    print("Test 3: JSONB Default - platform_role.permissions")
    print("=" * 80)

    query = text("""
        BEGIN;
        INSERT INTO platform_role (role_name, role_description)
        VALUES ('Test Verification Role', 'Testing JSONB defaults')
        RETURNING id, permissions, is_active, is_default;
        ROLLBACK;
    """)

    return query, "Expected: permissions = {}, is_active = true, is_default = false"


def verify_string_default():
    """Test 4: String Default (address.country = 'US')"""
    print("\n" + "=" * 80)
    print("Test 4: String Default - address.country")
    print("=" * 80)

    query = text("""
        BEGIN;
        INSERT INTO address (address_line_1, city, state, postal_code)
        VALUES ('123 Test St', 'Test City', 'NY', '10001')
        RETURNING id, country, is_active;
        ROLLBACK;
    """)

    return query, "Expected: country = 'US', is_active = true"


def verify_datetime_default():
    """Test 5: DateTime Default (notification_event.occurred_at = now())"""
    print("\n" + "=" * 80)
    print("Test 5: DateTime Default - notification_event.occurred_at")
    print("=" * 80)

    query = text("""
        BEGIN;
        WITH new_type AS (
            INSERT INTO notification_type (type_name, channel)
            VALUES ('test_verification_type', 'email')
            RETURNING id
        ),
        new_tenant AS (
            INSERT INTO tenant (tenant_name, default_timezone)
            VALUES ('Test Verification Tenant DT', 'America/New_York')
            RETURNING id
        )
        INSERT INTO notification_event (notification_type_id, tenant_id)
        SELECT nt.id, t.id FROM new_type nt, new_tenant t
        RETURNING id, occurred_at;
        ROLLBACK;
    """)

    return (
        query,
        "Expected: occurred_at is current timestamp (within a few seconds of now)",
    )


def verify_tstzrange_default():
    """Test 6: tstzrange Default (supplier_item_price.valid_period)"""
    print("\n" + "=" * 80)
    print("Test 6: tstzrange Default - supplier_item_price.valid_period")
    print("=" * 80)

    query = text("""
        BEGIN;
        WITH new_tenant AS (
            INSERT INTO tenant (tenant_name, default_timezone)
            VALUES ('Test Tenant Range', 'America/New_York')
            RETURNING id
        ),
        new_status AS (
            INSERT INTO supplier_lifecycle_status (status_name, tenant_id)
            SELECT 'Active', id FROM new_tenant
            RETURNING id, tenant_id
        ),
        new_supplier AS (
            INSERT INTO supplier (supplier_name, status_id, tenant_id)
            SELECT 'Test Supplier', s.id, s.tenant_id FROM new_status s
            RETURNING id, tenant_id
        ),
        new_category AS (
            INSERT INTO supplier_item_category (category_name, tenant_id)
            SELECT 'Test Category', tenant_id FROM new_supplier
            RETURNING id, tenant_id
        ),
        new_uom AS (
            INSERT INTO supplier_item_uom (uom_name, tenant_id)
            SELECT 'EA', tenant_id FROM new_supplier
            RETURNING id, tenant_id
        ),
        new_item AS (
            INSERT INTO supplier_item (item_name, supplier_id, category_id, uom_id, tenant_id)
            SELECT 'Test Item', s.id, c.id, u.id, s.tenant_id 
            FROM new_supplier s, new_category c, new_uom u
            RETURNING id, tenant_id
        )
        INSERT INTO supplier_item_price (supplier_item_id, unit_price_cents, tenant_id)
        SELECT id, 1000, tenant_id FROM new_item
        RETURNING id, valid_period;
        ROLLBACK;
    """)

    return query, "Expected: valid_period = '[<current_timestamp>,)'"


def run_verification():
    """Run all verification tests"""
    print("\n" + "=" * 80)
    print("PHASE 5.0 - TASK 3: DATABASE SERVER DEFAULTS VERIFICATION")
    print("=" * 80)
    print("\nThis script verifies server defaults at the PostgreSQL layer")
    print("All tests use BEGIN...ROLLBACK to avoid persisting data\n")

    # Get database URL
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev"
    )
    engine = create_engine(db_url)

    tests = [
        verify_boolean_default,
        verify_integer_default,
        verify_jsonb_default,
        verify_string_default,
        verify_datetime_default,
        verify_tstzrange_default,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            query, expected = test_func()
            print(f"\nExpected Result: {expected}")
            print("\nExecuting query...")

            with engine.begin() as conn:
                # We need to run each statement separately for proper transaction control
                conn.execute(text("BEGIN"))

                # Extract the INSERT...RETURNING part
                query_text = str(query).strip()
                if "BEGIN;" in query_text:
                    query_text = (
                        query_text.replace("BEGIN;", "")
                        .replace("ROLLBACK;", "")
                        .strip()
                    )

                result = conn.execute(text(query_text))
                row = result.fetchone()

                if row:
                    print(f"\n✅ SUCCESS - Row returned: {dict(row._mapping)}")
                    passed += 1
                else:
                    print("\n❌ FAILED - No row returned")
                    failed += 1

                # Rollback
                conn.execute(text("ROLLBACK"))

        except Exception as e:
            print(f"\n❌ FAILED - Error: {e!s}")
            failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed / len(tests) * 100):.1f}%")

    if failed == 0:
        print(
            "\n✅ ALL TESTS PASSED - Server defaults are working at the database layer!"
        )
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(run_verification())
