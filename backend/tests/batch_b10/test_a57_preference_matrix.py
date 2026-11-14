"""
A57 — Preference Matrix Endpoints + In-App Banner Tests
tests/batch_b10/test_a57_preference_matrix.py

Test focus cases:
  1. GET /preferences returns 24-cell matrix (8 categories × 3 channels)
  2. scope is 'system' for cells with no user/tenant override
  3. PUT /preferences/{category_id}/{channel} upserts a user preference
  4. scope is 'user' after setting user override
  5. DELETE /preferences/{category_id}/{channel} reverts to system/tenant default
  6. PUT /tenant-policy/{category_id}/{channel} sets tenant override
  7. DELETE /tenant-policy/{category_id}/{channel} reverts to system default
  8. POST /preferences/mute-all-push-non-critical skips forced-minimum categories
  9. POST /preferences/mute-all-email mutes all 8 categories
  10. POST /preferences/reset-to-tenant-defaults clears all user preferences
  11. Resolver: four-tier resolution chain resolves in priority order
  12. Resolver: forced-minimum push uniform → always True
  13. Resolver: forced-minimum push recipient-only → True only for originating user
  14. InAppNotification ORM — create and mark-read flow
  15. GET /in-app/recent returns bell panel + unread count
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import delete

from app.models.system import (
    InAppNotification,
    NotificationPreference,
)
from services.notification_resolver import (
    get_effective_preference,
    should_deliver,
)

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-2: GET preferences — 24-cell matrix
# ─────────────────────────────────────────────────────────────────────────────


def test_get_preferences_returns_24_cells(client: TestClient):
    """Matrix endpoint returns exactly 24 cells (8 categories × 3 channels)."""
    response = client.get("/api/v1/notifications/test/preferences")
    assert response.status_code == 200
    data = response.json()
    assert "preferences" in data
    assert len(data["preferences"]) == 24


def test_get_preferences_cells_have_required_fields(client: TestClient):
    """Each cell has category_id, channel, enabled, scope, forced_minimum, can_disable."""
    response = client.get("/api/v1/notifications/test/preferences")
    for cell in response.json()["preferences"]:
        assert "category_id" in cell
        assert "channel" in cell
        assert "enabled" in cell
        assert "scope" in cell
        assert "forced_minimum" in cell
        assert "can_disable" in cell


def test_get_preferences_default_scope_is_system(client: TestClient, db_session):
    """Without any overrides, scope is 'system' or 'fallback'.

    B17-fix: Clear any pre-existing user-level NotificationPreference rows for
    the canonical test tenant/user before asserting. A prior test run may have
    left committed rows that cause scope='user' and break this assertion.
    """
    import uuid as _uuid

    from core.config import settings

    test_tenant_id = _uuid.UUID(settings.TEST_TENANT_ID)
    test_user_id = _uuid.UUID(settings.TEST_USER_ID)

    # Remove any lingering user-level overrides for the test user
    db_session.exec(
        delete(NotificationPreference).where(
            NotificationPreference.tenant_id == test_tenant_id,
            NotificationPreference.user_id == test_user_id,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/notifications/test/preferences")
    for cell in response.json()["preferences"]:
        assert cell["scope"] in ("system", "fallback", "tenant")


# ─────────────────────────────────────────────────────────────────────────────
# Tests 3-5: PUT/DELETE user preferences
# ─────────────────────────────────────────────────────────────────────────────


def test_set_user_preference_returns_user_scope(
    client: TestClient, db_session, test_tenant
):
    """PUT /preferences sets a user override and returns scope='user'."""
    response = client.put(
        "/api/v1/notifications/test/preferences/sync_conflicts/email",
        json={"enabled": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "user"
    assert data["enabled"] is False
    assert data["category_id"] == "sync_conflicts"
    assert data["channel"] == "email"


def test_get_preferences_reflects_user_override(
    client: TestClient, db_session, test_tenant
):
    """After setting a user preference, GET matrix reflects the new value."""
    # Set email for sync_conflicts to False
    client.put(
        "/api/v1/notifications/test/preferences/sync_conflicts/email",
        json={"enabled": False},
    )

    response = client.get("/api/v1/notifications/test/preferences")
    prefs = {
        (p["category_id"], p["channel"]): p for p in response.json()["preferences"]
    }
    cell = prefs[("sync_conflicts", "email")]
    assert cell["enabled"] is False
    assert cell["scope"] == "user"


def test_clear_user_preference_reverts_scope(
    client: TestClient, db_session, test_tenant
):
    """DELETE /preferences clears user override and reverts to system/tenant."""
    # First set it
    client.put(
        "/api/v1/notifications/test/preferences/sync_conflicts/email",
        json={"enabled": False},
    )
    # Then clear it
    response = client.delete(
        "/api/v1/notifications/test/preferences/sync_conflicts/email"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cleared"] is True
    assert data["reverted_to_scope"] in ("system", "tenant")


def test_set_preference_invalid_category_returns_404(client: TestClient):
    """PUT with a non-existent category_id returns 404."""
    response = client.put(
        "/api/v1/notifications/test/preferences/nonexistent_category/email",
        json={"enabled": False},
    )
    assert response.status_code == 404


def test_set_preference_invalid_channel_returns_400(client: TestClient):
    """PUT with an invalid channel returns 400."""
    response = client.put(
        "/api/v1/notifications/test/preferences/sync_conflicts/carrier_pigeon",
        json={"enabled": False},
    )
    assert response.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Tests 6-7: Tenant policy endpoints
# ─────────────────────────────────────────────────────────────────────────────


def test_set_tenant_policy_returns_tenant_scope(
    client: TestClient, db_session, test_tenant
):
    """PUT /tenant-policy sets tenant override."""
    response = client.put(
        "/api/v1/notifications/test/tenant-policy/billing/push",
        json={"enabled": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "tenant"
    assert data["enabled"] is True

    # Cleanup
    client.delete("/api/v1/notifications/test/tenant-policy/billing/push")


def test_clear_tenant_policy_reverts_to_system(
    client: TestClient, db_session, test_tenant
):
    """DELETE /tenant-policy clears the tenant override."""
    client.put(
        "/api/v1/notifications/test/tenant-policy/billing/push", json={"enabled": True}
    )
    response = client.delete("/api/v1/notifications/test/tenant-policy/billing/push")
    assert response.status_code == 200
    assert response.json()["reverted_to_scope"] == "system"


# ─────────────────────────────────────────────────────────────────────────────
# Tests 8-10: Bulk mute operations
# ─────────────────────────────────────────────────────────────────────────────


def test_mute_all_push_non_critical_returns_count(
    client: TestClient, db_session, test_tenant
):
    """POST /preferences/mute-all-push-non-critical returns muted_count."""
    response = client.post(
        "/api/v1/notifications/test/preferences/mute-all-push-non-critical"
    )
    assert response.status_code == 200
    data = response.json()
    assert "muted_count" in data
    # Should skip categories with forced-minimum (field_issues, system_announcements)
    # and recipient-only (job_activity, customer_activity) = 4 skipped, 4 muted
    assert data["muted_count"] == 4


def test_mute_all_email_mutes_all_8(client: TestClient, db_session, test_tenant):
    """POST /preferences/mute-all-email mutes all 8 categories."""
    response = client.post("/api/v1/notifications/test/preferences/mute-all-email")
    assert response.status_code == 200
    data = response.json()
    assert data["muted_count"] == 8


def test_reset_to_tenant_defaults_clears_user_prefs(
    client: TestClient, db_session, test_tenant
):
    """POST /preferences/reset-to-tenant-defaults clears all user overrides."""
    # Set some preferences first
    client.post("/api/v1/notifications/test/preferences/mute-all-email")

    response = client.post(
        "/api/v1/notifications/test/preferences/reset-to-tenant-defaults"
    )
    assert response.status_code == 200
    data = response.json()
    assert "cleared_count" in data
    assert data["cleared_count"] >= 8


# ─────────────────────────────────────────────────────────────────────────────
# Tests 11-13: notification_resolver three-tier chain
# ─────────────────────────────────────────────────────────────────────────────


def test_resolver_tier1_user_level_wins(db_session, test_tenant, test_user):
    """User-level preference wins over system default."""
    # System default for quote_approvals/push is TRUE (from migration seed)
    # Resilience: delete any existing seeded preference for this category+channel
    # before inserting — seed data may have pre-set this row (Rule 16).
    db_session.exec(
        delete(NotificationPreference).where(
            NotificationPreference.tenant_id == test_tenant.id,
            NotificationPreference.user_id == test_user.id,
            NotificationPreference.category_id == "quote_approvals",
            NotificationPreference.channel == "push",
        )
    )
    db_session.commit()

    pref = NotificationPreference(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="quote_approvals",
        channel="push",
        enabled=False,
    )
    db_session.add(pref)
    db_session.commit()

    result = get_effective_preference(
        db_session, test_tenant.id, test_user.id, "quote_approvals", "push"
    )
    assert result is False

    db_session.delete(pref)
    db_session.commit()


def test_resolver_tier4_system_default_applies_when_no_overrides(
    db_session, test_tenant, test_user
):
    """System default is used when no user/tenant/policy overrides exist.

    Resilience: seed_test_tenant.py may have inserted user-level preference
    rows for the owner user. Delete them for the two categories under test
    before asserting system-default behaviour (Rule 16).
    """
    # Delete any seeded user preferences for the categories we're testing
    for cat, ch in [("sync_conflicts", "push"), ("quote_approvals", "push")]:
        db_session.exec(
            delete(NotificationPreference).where(
                NotificationPreference.tenant_id == test_tenant.id,
                NotificationPreference.user_id == test_user.id,
                NotificationPreference.category_id == cat,
                NotificationPreference.channel == ch,
            )
        )
    db_session.commit()

    # sync_conflicts/push system default is FALSE (from migration seed)
    result = get_effective_preference(
        db_session, test_tenant.id, test_user.id, "sync_conflicts", "push"
    )
    assert result is False

    # quote_approvals/push system default is TRUE
    result = get_effective_preference(
        db_session, test_tenant.id, test_user.id, "quote_approvals", "push"
    )
    assert result is True


def test_resolver_forced_minimum_uniform_overrides_false(
    db_session, test_tenant, test_user
):
    """forced_minimum_push_uniform=True on a sub-trigger → always deliver."""
    # Set user preference push=False for field_issues
    pref = NotificationPreference(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="field_issues",
        channel="push",
        enabled=False,
    )
    db_session.add(pref)
    db_session.commit()

    # Base = False (user preference), but forced_minimum_push_uniform=True for field_issues.all
    result = should_deliver(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="field_issues",
        channel="push",
        sub_trigger_id="field_issues.all",
        recipient_user_id_originating=test_user.id,
    )
    assert result is True

    db_session.delete(pref)
    db_session.commit()


def test_resolver_forced_minimum_recipient_only_applies_to_originating(
    db_session, test_tenant, test_user
):
    """forced_minimum_push_recipient_only=True → override ONLY for originating user."""
    other_user_id = uuid.uuid4()

    # Resilience: delete any seeded preference for this user+category+channel
    # before inserting our own (Rule 16).
    db_session.exec(
        delete(NotificationPreference).where(
            NotificationPreference.tenant_id == test_tenant.id,
            NotificationPreference.user_id == test_user.id,
            NotificationPreference.category_id == "job_activity",
            NotificationPreference.channel == "push",
        )
    )
    db_session.commit()

    # Set user preference push=False for job_activity
    pref = NotificationPreference(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="job_activity",
        channel="push",
        enabled=False,
    )
    db_session.add(pref)
    db_session.commit()

    # For originating user: forced-minimum should override → True
    result_originating = should_deliver(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="job_activity",
        channel="push",
        sub_trigger_id="job_activity.assignment",
        recipient_user_id_originating=test_user.id,  # originating user = same
    )
    assert result_originating is True

    # For a different user (not originating): preference respected → False
    result_other = should_deliver(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="job_activity",
        channel="push",
        sub_trigger_id="job_activity.assignment",
        recipient_user_id_originating=other_user_id,  # different user
    )
    assert result_other is False

    db_session.delete(pref)
    db_session.commit()


def test_resolver_non_push_channel_no_forced_minimum(
    db_session, test_tenant, test_user
):
    """Forced-minimum only applies to push. Email always follows resolved preference."""
    pref = NotificationPreference(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="field_issues",
        channel="email",
        enabled=False,
    )
    db_session.add(pref)
    db_session.commit()

    # Even with a forced-minimum sub-trigger, email respects the preference
    result = should_deliver(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="field_issues",
        channel="email",
        sub_trigger_id="field_issues.all",
        recipient_user_id_originating=test_user.id,
    )
    assert result is False

    db_session.delete(pref)
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Tests 14-15: InAppNotification ORM + mark-read + recent
# ─────────────────────────────────────────────────────────────────────────────


def test_in_app_notification_create_and_mark_read(
    db_session, test_tenant, test_user, client: TestClient
):
    """Create an InAppNotification and mark it read via API."""
    notif = InAppNotification(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        category_id="job_activity",
        body="You have been assigned to a new job.",
        deep_link_target="/jobs/uuid",
        priority="standard",
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    assert notif.read_at is None

    # Mark as read
    response = client.post(
        "/api/v1/notifications/test/in-app/mark-read",
        # FIND-169: notification_id → id on InAppNotification
        json={"notification_ids": [str(notif.id)]},
    )
    assert response.status_code == 200
    assert response.json()["marked_count"] == 1

    db_session.refresh(notif)
    assert notif.read_at is not None


def test_in_app_recent_returns_list_and_unread_count(
    db_session, test_tenant, test_user, client: TestClient
):
    """GET /in-app/recent returns notifications list and unread_count."""
    # Create 2 unread notifications
    for i in range(2):
        db_session.add(
            InAppNotification(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                category_id="customer_activity",
                body=f"Message {i}",
                deep_link_target=f"/customers/{i}",
                priority="standard",
            )
        )
    db_session.commit()

    response = client.get("/api/v1/notifications/test/in-app/recent")
    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
    assert "unread_count" in data
    assert data["unread_count"] >= 2
    assert len(data["notifications"]) >= 2
