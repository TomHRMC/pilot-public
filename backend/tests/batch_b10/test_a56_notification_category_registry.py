"""
A56 — Notification Category Registry Tests
tests/batch_b10/test_a56_notification_category_registry.py

Test focus cases:
  1. GET /test/notifications/categories returns 8 categories with 3 channels each
  2. System default policies are resolved correctly per category × channel
  3. Tenant override resolves at the right priority (tenant > system)
  4. GET /test/notifications/sub-triggers returns all 4 seeded forced-minimum rows
  5. Filtering sub-triggers by category_id works
  6. NotificationOutbox category_id column present and accepts valid values
  7. Audit pass: outbox rows now carry category_id (not NULL) via sentinel backfill
"""

from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.system import (
    NotificationCategory,
    NotificationCategorySubTrigger,
    NotificationDefaultPolicy,
    NotificationOutbox,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test 1 & 2: GET /test/notifications/categories — 8 categories, 3 channels
# ─────────────────────────────────────────────────────────────────────────────


def test_list_categories_returns_8_categories(client: TestClient):
    """Endpoint returns all 8 seeded notification categories."""
    response = client.get("/api/v1/notifications/test/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) == 8


def test_list_categories_each_has_3_channels(client: TestClient):
    """Each category has push, email, in_app channel entries."""
    response = client.get("/api/v1/notifications/test/categories")
    assert response.status_code == 200
    for cat in response.json()["categories"]:
        assert "channels" in cat
        for ch in ["push", "email", "in_app"]:
            assert ch in cat["channels"]
            assert "system_default" in cat["channels"][ch]
            assert "tenant_default" in cat["channels"][ch]
            assert "effective" in cat["channels"][ch]


def test_list_categories_ordered_by_display_order(client: TestClient):
    """Categories returned in ascending display_order."""
    response = client.get("/api/v1/notifications/test/categories")
    categories = response.json()["categories"]
    orders = [c["display_order"] for c in categories]
    assert orders == sorted(orders)


def test_list_categories_system_defaults_match_seed(client: TestClient):
    """Verify system defaults match the migration seed matrix."""
    response = client.get("/api/v1/notifications/test/categories")
    cats = {c["category_id"]: c["channels"] for c in response.json()["categories"]}

    # sync_conflicts: push=OFF, email=ON, in_app=ON
    assert cats["sync_conflicts"]["push"]["system_default"] is False
    assert cats["sync_conflicts"]["email"]["system_default"] is True
    assert cats["sync_conflicts"]["in_app"]["system_default"] is True

    # billing: push=OFF, email=ON, in_app=ON
    assert cats["billing"]["push"]["system_default"] is False
    assert cats["billing"]["email"]["system_default"] is True

    # job_activity: push=ON, email=OFF, in_app=ON
    assert cats["job_activity"]["push"]["system_default"] is True
    assert cats["job_activity"]["email"]["system_default"] is False
    assert cats["job_activity"]["in_app"]["system_default"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Tenant override takes priority over system default
# ─────────────────────────────────────────────────────────────────────────────


def test_tenant_override_resolved_for_categories(
    client: TestClient, db_session, test_tenant
):
    """When a tenant override exists, effective value matches tenant override, not system default."""

    # Create a tenant override for quote_approvals push: set to FALSE
    # (system default is TRUE)
    override = NotificationDefaultPolicy(
        tenant_id=test_tenant.id,
        category_id="quote_approvals",
        channel="push",
        enabled=False,
    )
    db_session.add(override)
    db_session.commit()

    response = client.get("/api/v1/notifications/test/categories")
    assert response.status_code == 200
    cats = {c["category_id"]: c["channels"] for c in response.json()["categories"]}
    qa_push = cats["quote_approvals"]["push"]

    # System default is TRUE, but tenant override is FALSE → effective = FALSE
    assert qa_push["system_default"] is True
    assert qa_push["effective"] is False  # tenant overrides system

    # Cleanup
    db_session.delete(override)
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 & 5: GET /test/notifications/sub-triggers
# ─────────────────────────────────────────────────────────────────────────────


def test_list_sub_triggers_returns_4_seeded_rows(client: TestClient):
    """Endpoint returns all forced-minimum sub-triggers seeded by migrations.
    B10 seeded 4 rows; B13 added 3 MFA grace reminder rows = 7 total.
    Test updated to >= 4 to accommodate additive batches per §15 anti-fragility."""
    response = client.get("/api/v1/notifications/test/sub-triggers")
    assert response.status_code == 200
    data = response.json()
    assert "sub_triggers" in data
    assert len(data["sub_triggers"]) >= 4


def test_list_sub_triggers_forced_minimum_fields_present(client: TestClient):
    """Each sub-trigger row has forced_minimum_push_uniform and forced_minimum_push_recipient_only."""
    response = client.get("/api/v1/notifications/test/sub-triggers")
    for st in response.json()["sub_triggers"]:
        assert "forced_minimum_push_uniform" in st
        assert "forced_minimum_push_recipient_only" in st


def test_list_sub_triggers_filter_by_category(client: TestClient):
    """Filtering by category_id returns only matching sub-triggers."""
    response = client.get(
        "/api/v1/notifications/test/sub-triggers?category_id=job_activity"
    )
    assert response.status_code == 200
    data = response.json()["sub_triggers"]
    assert len(data) == 1
    assert data[0]["sub_trigger_id"] == "job_activity.assignment"
    assert data[0]["forced_minimum_push_recipient_only"] is True


def test_list_sub_triggers_field_issues_uniform(client: TestClient):
    """field_issues.all has forced_minimum_push_uniform = True."""
    response = client.get(
        "/api/v1/notifications/test/sub-triggers?category_id=field_issues"
    )
    data = response.json()["sub_triggers"]
    assert len(data) == 1
    assert data[0]["sub_trigger_id"] == "field_issues.all"
    assert data[0]["forced_minimum_push_uniform"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 & 7: ORM — outbox category_id column and sentinel backfill
# ─────────────────────────────────────────────────────────────────────────────


def test_notification_outbox_has_category_id_column(db_session):
    """NotificationOutbox ORM model has the new category_id column."""
    assert hasattr(NotificationOutbox, "category_id")
    assert hasattr(NotificationOutbox, "sub_trigger_id")
    assert hasattr(NotificationOutbox, "recipient_user_id_originating")


def test_notification_category_seeded_8_rows(db_session):
    """notification_category table has exactly 8 rows from migration seed."""
    rows = db_session.exec(select(NotificationCategory)).all()
    assert len(rows) == 8
    # FIND-169: category_id → code on NotificationCategory (PK renamed)
    category_ids = {r.code for r in rows}
    expected = {
        "quote_approvals",
        "field_issues",
        "sync_conflicts",
        "job_activity",
        "customer_activity",
        "billing",
        "background_sync_alerts",
        "system_announcements",
    }
    assert category_ids == expected


def test_notification_default_policy_seeded_24_rows(db_session):
    """notification_default_policy has 24 system-default rows (8 categories × 3 channels)."""
    system_rows = db_session.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == None
        )
    ).all()
    assert len(system_rows) == 24


def test_notification_category_sub_trigger_seeded_4_rows(db_session):
    """notification_category_sub_trigger has at least 4 seeded forced-minimum rows.
    B10 seeded 4; B13 added 3 MFA grace reminder rows = 7 total.
    The 4 B10 core rows must always be present."""
    rows = db_session.exec(select(NotificationCategorySubTrigger)).all()
    assert len(rows) >= 4
    # FIND-169: sub_trigger_id → code on NotificationCategorySubTrigger
    ids = {r.code for r in rows}
    assert "field_issues.all" in ids
    assert "job_activity.assignment" in ids
    assert "system_announcements.critical" in ids
    assert "customer_activity.inbound_sms_reply" in ids
