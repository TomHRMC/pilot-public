"""
B13/A68 — MFA Policy & Grace Period Tests.

Test focus:
- PUT /settings/tenant/mfa-required/test enables MFA policy
- Enabling MFA policy seeds mfa_grace_period_tracking rows for tenant users
- GET /users/me/mfa-status/test returns correct enrollment state
- MFA status shows grace_period_active when enrolled_at is None
- Grace period not active when user is enrolled
- mfa_grace_reminders._notify_mfa_grace_period_reminders_impl() dispatches notifications

FIND-086: TenantSettings replaced by platform_setting. Tests updated to use
PlatformSetting upsert instead of TenantSettings direct mutation.
"""

from datetime import UTC, datetime

from sqlmodel import select

from app.models.platform_setting import PlatformSetting
from app.models.security import MfaGracePeriodTracking, UserMfaMethod
from core.test_context import get_test_context
from tasks.mfa_grace_reminders import _notify_mfa_grace_period_reminders_impl


def _upsert_mfa_setting(db_session, tenant_id, key, value):
    """Helper: upsert a platform_setting row for MFA-related keys."""
    existing = db_session.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == key)
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()
    if existing:
        existing.value = value
    else:
        existing = PlatformSetting(key=key, value=value, tenant_id=tenant_id)
    db_session.add(existing)


class TestMfaPolicyEndpoint:
    def test_enable_mfa_policy(self, db_session, client, tenant_a):
        resp = client.put(
            "/api/v1/settings/tenant/mfa-required/test",
            json={"enabled": True, "grace_period_days": 7},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_mfa_required"] is True
        assert data["grace_period_days"] == 7

    def test_disable_mfa_policy(self, db_session, client, tenant_a):
        # First enable
        client.put(
            "/api/v1/settings/tenant/mfa-required/test",
            json={"enabled": True},
        )
        # Then disable
        resp = client.put(
            "/api/v1/settings/tenant/mfa-required/test",
            json={"enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_mfa_required"] is False

    def test_enabling_seeds_grace_period_rows(
        self, db_session, client, tenant_a, user_tenant_a
    ):
        resp = client.put(
            "/api/v1/settings/tenant/mfa-required/test",
            json={"enabled": True, "grace_period_days": 7},
        )
        assert resp.status_code == 200

        ctx = get_test_context()
        grace_rows = db_session.exec(
            select(MfaGracePeriodTracking).where(
                MfaGracePeriodTracking.tenant_id == ctx.tenant_id
            )
        ).all()
        assert len(grace_rows) >= 1

    def test_grace_period_days_defaults_to_7(self, db_session, client, tenant_a):
        resp = client.put(
            "/api/v1/settings/tenant/mfa-required/test",
            json={"enabled": True},
        )
        assert resp.json()["grace_period_days"] == 7


class TestMfaStatusEndpoint:
    def test_returns_empty_enrolled_methods(self, client):
        resp = client.get("/api/v1/users/me/mfa-status/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enrolled_methods"] == []
        assert data["tenant_policy_required"] is False

    def test_shows_enrolled_methods(self, db_session, client, tenant_a, user_tenant_a):
        ctx = get_test_context()
        method = UserMfaMethod(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            method_type="totp",
            enrolled_at=datetime.now(UTC),
            cognito_method_id="mock-totp",
            verification_status="verified",
        )
        db_session.add(method)
        db_session.commit()

        resp = client.get("/api/v1/users/me/mfa-status/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "totp" in data["enrolled_methods"]

    def test_grace_period_active_when_unenrolled(
        self, db_session, client, tenant_a, user_tenant_a
    ):
        ctx = get_test_context()
        grace_row = MfaGracePeriodTracking(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            grace_started_at=datetime.now(UTC),
        )
        db_session.add(grace_row)

        # Enable MFA policy via platform_setting (FIND-086)
        _upsert_mfa_setting(db_session, ctx.tenant_id, "tenant_mfa_required", True)
        _upsert_mfa_setting(
            db_session, ctx.tenant_id, "tenant_mfa_grace_period_days", 7
        )
        db_session.commit()

        resp = client.get("/api/v1/users/me/mfa-status/test")
        data = resp.json()
        assert data["grace_period_active"] is True
        assert data["tenant_policy_required"] is True


class TestMfaGraceReminderTask:
    def test_dispatches_notifications_for_unenrolled_users(
        self, db_session, tenant_a, user_tenant_a
    ):
        ctx = get_test_context()

        # Enable MFA via platform_setting (FIND-086)
        _upsert_mfa_setting(db_session, ctx.tenant_id, "tenant_mfa_required", True)
        _upsert_mfa_setting(
            db_session, ctx.tenant_id, "tenant_mfa_grace_period_days", 7
        )

        # Add grace row
        grace_row = MfaGracePeriodTracking(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            grace_started_at=datetime.now(UTC),
        )
        db_session.add(grace_row)
        db_session.commit()

        result = _notify_mfa_grace_period_reminders_impl(db_session)
        assert result["tenants_processed"] >= 1
        assert result["notifications_dispatched"] >= 1

    def test_skips_enrolled_users(self, db_session, tenant_a, user_tenant_a):
        ctx = get_test_context()
        # Enable MFA via platform_setting (FIND-086)
        _upsert_mfa_setting(db_session, ctx.tenant_id, "tenant_mfa_required", True)

        now = datetime.now(UTC)
        grace_row = MfaGracePeriodTracking(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            grace_started_at=now,
            enrolled_at=now,  # Already enrolled
        )
        db_session.add(grace_row)
        db_session.commit()

        result = _notify_mfa_grace_period_reminders_impl(db_session)
        assert result["notifications_dispatched"] == 0
