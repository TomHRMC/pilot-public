"""
FIND-104 (S2 High) — sms_quota_cap_policy setting via platform_setting.

Deliverables:
  1. Migration: seed platform_setting_catalog + platform_setting (NULL tenant = 'soft')
  2. Code: _DEFAULT_CAP_POLICY removed; check_quota() uses get_effective_setting()
  3. Tests: 'soft' resolves, 'hard' resolves, new tenant defaults to 'soft'

Test coverage:
  1. Catalog: sms_quota_cap_policy entry exists in platform_setting_catalog
  2. Default: get_effective_setting resolves 'soft' for new tenant (no override)
  3. Code: _DEFAULT_CAP_POLICY no longer exists in sms_quota module
  4. Integration: check_quota with 'soft' allows overage
  5. Integration: check_quota with 'hard' blocks when over quota

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

# ─────────────────────────────────────────────────────────────────────────────
# 1. Catalog entry exists
# ─────────────────────────────────────────────────────────────────────────────


class TestFind104CatalogEntry:
    def test_sms_quota_cap_policy_in_catalog(self, db_session):
        from sqlmodel import select

        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "sms_quota_cap_policy"
            )
        ).first()

        assert row is not None, (
            "sms_quota_cap_policy must be seeded in platform_setting_catalog"
        )
        assert row.tenant_editable is True, (
            "sms_quota_cap_policy must be tenant-editable"
        )
        assert row.allowed_values is not None
        allowed = row.allowed_values if isinstance(row.allowed_values, list) else []
        assert "soft" in allowed and "hard" in allowed, (
            f"allowed_values must contain 'soft' and 'hard', got {allowed}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Default setting resolves to 'soft'
# ─────────────────────────────────────────────────────────────────────────────


class TestFind104DefaultSetting:
    def test_new_tenant_defaults_to_soft(self, db_session, test_tenant):
        """A tenant with no override sees 'soft' from platform default."""
        from services.setting_resolver import get_effective_setting

        val, scope = get_effective_setting(
            db_session, test_tenant.id, "sms_quota_cap_policy", fallback="soft"
        )
        assert val == "soft", (
            f"sms_quota_cap_policy must default to 'soft', got '{val}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Code: hardcoded constant removed
# ─────────────────────────────────────────────────────────────────────────────


class TestFind104HardcodeRemoved:
    def test_default_cap_policy_constant_removed(self):
        """_DEFAULT_CAP_POLICY must be removed from sms_quota module (FIND-104)."""
        import services.sms_quota as sms_quota_module

        assert not hasattr(sms_quota_module, "_DEFAULT_CAP_POLICY"), (
            "_DEFAULT_CAP_POLICY constant must be removed from sms_quota.py (FIND-104)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4-5. Integration: check_quota respects resolved cap policy
# ─────────────────────────────────────────────────────────────────────────────


def _make_quota_period(db_session, tenant_id, used, included, cap_policy):
    """Create a minimal SmsQuotaPeriod for testing."""
    from datetime import UTC, datetime

    from app.models.sms import SmsQuotaPeriod

    now = datetime.now(UTC)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    import calendar

    last_day = calendar.monthrange(now.year, now.month)[1]
    end = start.replace(day=last_day, hour=23, minute=59, second=59)

    period = SmsQuotaPeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        period_start=start,
        period_end=end,
        included_segments=included,
        used_segments=used,
        cap_policy=cap_policy,
    )
    db_session.add(period)
    db_session.commit()
    return period


def _make_customer(db_session, tenant_id):
    from app.models.crm import Customer

    now = datetime.now(UTC)
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        type="person",
        display_name=f"SMS Test {uuid.uuid4().hex[:6]}",
        sms_opted_out=False,
        preferred_contact_channel="sms",
        sms_opt_in_consent=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


class TestFind104CheckQuotaIntegration:
    """Integration tests: check_quota respects the resolved cap policy."""

    def test_soft_cap_allows_overage(self, db_session, test_tenant):
        """With cap_policy='soft' and quota exceeded, send is allowed (overage=True)."""
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=100, included=100, cap_policy="soft"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is True, (
            "cap_policy='soft' must allow send even when quota exceeded"
        )
        assert result.overage is True, (
            "cap_policy='soft' must flag overage=True when quota exceeded"
        )

    def test_hard_cap_blocks_when_quota_exceeded(self, db_session, test_tenant):
        """With cap_policy='hard' and quota exceeded, send is blocked."""
        from services.sms_quota import check_quota

        customer = _make_customer(db_session, test_tenant.id)
        _make_quota_period(
            db_session, test_tenant.id, used=100, included=100, cap_policy="hard"
        )

        result = check_quota(
            db_session, test_tenant.id, customer.id, requested_segments=1
        )

        assert result.allowed is False, (
            "cap_policy='hard' must block send when quota is exceeded"
        )
        assert result.blocked_reason == "monthly_quota_reached", (
            f"blocked_reason must be 'monthly_quota_reached', got '{result.blocked_reason}'"
        )
