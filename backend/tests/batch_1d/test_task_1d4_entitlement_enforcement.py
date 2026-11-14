"""
Test Suite: Feature Entitlement Enforcement Middleware  (Task 1-D-4)

Tests (A-D) as specified in the task definition:

  A. Override table GRANTS access even when usage > plan limit.
  B. Override table BLOCKS access even when usage < plan limit.
  C. Plan limit exceeded → require_permission raises 402 Payment Required.
  D. Redis caching works: DB queried once even when dependency called twice.

All DB I/O is fully mocked so the suite runs without a live database or Redis.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from services.entitlement_service import (
    _CACHE_KEY_PREFIX,
    _CACHE_TTL,
    EntitlementResult,
    check_entitlement,
    get_cached_entitlement,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
# PLP-FIX-1: repointed from "quotes_per_month" (phantom gate, removed) to a
# synthetic code — these are pure-mock framework tests, not tied to any real route.
FEATURE_CODE = "synthetic_metered_feature"


def _mock_override(
    enabled: bool = True,
    limit_quantity: int | None = None,
) -> MagicMock:
    """Factory for a TenantProductFeatureOverride mock row."""
    obj = MagicMock()
    obj.enabled = enabled
    obj.limit_quantity = limit_quantity
    return obj


def _mock_subscription(plan_code: str = "mvp_starter") -> MagicMock:
    obj = MagicMock()
    obj.product_plan_code = plan_code
    obj.is_active = True
    return obj


def _mock_feature_version(limit_quantity: int | None = 5) -> MagicMock:
    obj = MagicMock()
    obj.limit_quantity = limit_quantity
    return obj


def _mock_usage(used: int) -> MagicMock:
    obj = MagicMock()
    obj.used_quantity = used
    return obj


def _make_db_session(*first_returns) -> MagicMock:
    """
    Build a mock SQLModel Session whose exec().first() calls return the
    provided objects in the exact order supplied.

    Usage::

        db = _make_db_session(override_obj, usage_obj)   # 2-call path
        db = _make_db_session(None, sub_obj, fv_obj)     # 3-call path (no override)
        db = _make_db_session(None, sub_obj, fv_obj, usage_obj)  # 4-call path
    """
    db = MagicMock()
    items = list(first_returns)
    call_count = [0]

    def _first_side_effect():
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(items):
            return items[idx]
        return None

    exec_result = MagicMock()
    exec_result.first.side_effect = _first_side_effect
    db.exec.return_value = exec_result
    return db


# ── Test A: Override grants access even when usage > plan limit ──────────────


class TestOverrideGrantsAccess:
    """
    Test A: When tenant_product_feature_override.enabled = True and
    limit_quantity = None (unlimited), access is granted regardless of usage.
    """

    def test_override_unlimited_grants_access_when_usage_exceeds_plan(self):
        """
        Scenario:
          - Override: enabled=True, limit_quantity=None (unlimited admin grant)
          - Usage: 999  (way above any plan limit)
          - Expected: is_allowed=True, reason="override_unlimited"
        """
        # call 1 → override (enabled, no limit)  — no further DB calls needed
        db = _make_db_session(_mock_override(enabled=True, limit_quantity=None))

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is True
        assert result.reason == "override_unlimited"
        assert result.limit is None

    def test_override_custom_limit_grants_when_under_override_limit(self):
        """
        Scenario:
          - Override: enabled=True, limit_quantity=100 (generous admin override)
          - Usage row: used_quantity=3  (plan limit is irrelevant — override wins)
          - Expected: is_allowed=True, reason="override_limit_ok"

        DB call sequence when override has a limit:
          call 1 → TenantProductFeatureOverride lookup → override
          call 2 → SubscriptionUsage lookup (_get_current_usage) → usage
        """
        # call 1 → override; call 2 → usage (subscription/plan lookups skipped)
        db = _make_db_session(
            _mock_override(enabled=True, limit_quantity=100),
            _mock_usage(3),
        )

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is True
        assert result.limit == 100
        assert result.used == 3
        assert result.reason == "override_limit_ok"


# ── Test B: Override blocks access even when usage < plan limit ──────────────


class TestOverrideBlocksAccess:
    """
    Test B: When tenant_product_feature_override.enabled = False, access is
    denied regardless of current usage or plan entitlement.
    """

    def test_override_disabled_blocks_when_usage_is_zero(self):
        """
        Scenario:
          - Override: enabled=False
          - Usage: 0  (never used the feature)
          - Expected: is_allowed=False, reason="feature_disabled_by_override"
        """
        # call 1 → override (disabled) — execution stops immediately
        db = _make_db_session(_mock_override(enabled=False))

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is False
        assert result.reason == "feature_disabled_by_override"
        # Subscription & plan queries must NOT be made
        # (db.exec called exactly once for the override lookup)
        assert db.exec.call_count == 1

    def test_override_disabled_blocks_when_usage_under_plan_limit(self):
        """
        Scenario:
          - Override: enabled=False
          - Usage: 2 out of plan limit 5
          - Expected: is_allowed=False (override wins)
        """
        # Only the override call matters — rest of sequence is irrelevant
        db = _make_db_session(
            _mock_override(enabled=False),
            _mock_subscription(),
            _mock_feature_version(limit_quantity=5),
            _mock_usage(2),
        )

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is False
        assert result.reason == "feature_disabled_by_override"


# ── Test C: Plan limit exceeded → 402 via require_permission ────────────────


class TestPlanLimitExceeded:
    """
    Test C: When there is no override and usage >= plan limit_quantity,
    check_entitlement returns is_allowed=False and require_permission raises
    HTTP 402 Payment Required.
    """

    def test_check_entitlement_blocked_when_usage_equals_limit(self):
        """
        Direct unit test of check_entitlement (no FastAPI involved).

        DB call sequence (no override):
          call 1 → override lookup         → None
          call 2 → subscription lookup     → subscription
          call 3 → feature_version lookup  → feature_version
          call 4 → _get_current_usage      → usage
        """
        db = _make_db_session(
            None,  # no override
            _mock_subscription(),  # active subscription
            _mock_feature_version(limit_quantity=5),  # plan limit = 5
            _mock_usage(5),  # used = 5 (at limit)
        )

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is False
        assert result.reason == "usage_limit_exceeded"
        assert result.limit == 5
        assert result.used == 5

    def test_check_entitlement_blocked_when_usage_exceeds_limit(self):
        db = _make_db_session(
            None,
            _mock_subscription(),
            _mock_feature_version(limit_quantity=5),
            _mock_usage(9),
        )

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is False
        assert result.used == 9

    def test_require_permission_raises_402_when_entitlement_blocked(self):
        """
        Integration test: require_permission calls get_cached_entitlement and
        raises HTTPException(402) when is_allowed=False.
        """
        from core.permissions import require_permission

        blocked_result = EntitlementResult(
            is_allowed=False,
            limit=5,
            used=5,
            reason="usage_limit_exceeded",
        )

        # Build a mock AuthenticatedUser with tenant_id and permissions
        mock_user = MagicMock()
        mock_user.permissions = ["synthetic.feature", "*"]
        mock_user.role_code = "owner"
        mock_user.tenant_id = TEST_TENANT_ID

        mock_db = MagicMock()

        checker = require_permission("synthetic.feature", feature_code=FEATURE_CODE)

        with patch(
            "services.entitlement_service.get_cached_entitlement",
            return_value=blocked_result,
        ):
            with pytest.raises(HTTPException) as exc_info:
                checker.__wrapped__(mock_user, mock_db) if hasattr(
                    checker, "__wrapped__"
                ) else _invoke_permission_checker(checker, mock_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_402_PAYMENT_REQUIRED
        detail = exc_info.value.detail
        assert detail["error"] == "usage_limit_exceeded"
        assert detail["feature"] == FEATURE_CODE
        assert detail["limit"] == 5
        assert detail["used"] == 5

    def test_require_permission_raises_402_integration(self):
        """
        Calls the inner permission_checker directly (bypassing FastAPI DI).
        """
        from core.permissions import require_permission

        blocked_result = EntitlementResult(
            is_allowed=False,
            limit=5,
            used=5,
            reason="usage_limit_exceeded",
        )

        mock_user = MagicMock()
        mock_user.permissions = ["*"]
        mock_user.role_code = "owner"
        mock_user.tenant_id = TEST_TENANT_ID

        mock_db = MagicMock()

        # get the inner function from the closure
        checker_factory = require_permission(
            "synthetic.feature", feature_code=FEATURE_CODE
        )
        inner = (
            checker_factory.__wrapped__
            if hasattr(checker_factory, "__wrapped__")
            else checker_factory
        )

        # Patch at the source module — the local `from services.entitlement_service import`
        # inside permission_checker resolves against this namespace at call time.
        with patch(
            "services.entitlement_service.get_cached_entitlement",
            return_value=blocked_result,
        ):
            with pytest.raises(HTTPException) as exc_info:
                inner(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_402_PAYMENT_REQUIRED

    def test_no_active_subscription_returns_blocked(self):
        """When no active subscription row exists, feature is blocked."""
        # call 1 → override=None; call 2 → subscription=None
        db = _make_db_session(None, None)

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is False
        assert result.reason == "no_active_subscription"

    def test_feature_not_in_plan_returns_blocked(self):
        """When feature has no valid product_plan_product_feature_version row."""
        # call 1 → override=None; call 2 → subscription; call 3 → feature_version=None
        db = _make_db_session(None, _mock_subscription(), None)

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is False
        assert result.reason == "feature_not_in_plan"

    def test_unlimited_plan_feature_is_always_allowed(self):
        """limit_quantity=None on the plan feature version = unlimited."""
        # call 1 → override=None; call 2 → subscription; call 3 → feature_version (no limit)
        db = _make_db_session(
            None, _mock_subscription(), _mock_feature_version(limit_quantity=None)
        )

        result = check_entitlement(TEST_TENANT_ID, FEATURE_CODE, db)

        assert result.is_allowed is True
        assert result.limit is None
        assert result.reason == "plan_unlimited"


# ── Test D: Redis caching ────────────────────────────────────────────────────


class TestRedisCache:
    """
    Test D: Redis caching works — DB is queried once even when
    get_cached_entitlement is called twice with the same key.
    """

    def test_cache_hit_prevents_second_db_query(self):
        """
        Call get_cached_entitlement twice.  On the second call Redis should
        return the cached JSON → DB never called again.
        """
        cached_result = EntitlementResult(
            is_allowed=True,
            limit=5,
            used=2,
            reason="within_plan_limit",
        )

        mock_db = MagicMock()

        mock_redis = MagicMock()
        # First call: cache miss; second call: cache hit
        mock_redis.get.side_effect = [None, cached_result.model_dump_json()]

        with (
            patch(
                "services.entitlement_service._get_redis_client",
                return_value=mock_redis,
            ),
            patch(
                "services.entitlement_service.check_entitlement",
                return_value=cached_result,
            ) as mock_check,
        ):
            # First call → cache miss → calls check_entitlement
            result1 = get_cached_entitlement(TEST_TENANT_ID, FEATURE_CODE, mock_db)
            # Second call → cache hit → skips check_entitlement
            result2 = get_cached_entitlement(TEST_TENANT_ID, FEATURE_CODE, mock_db)

        # DB function called exactly once (cache miss on first call only)
        assert mock_check.call_count == 1

        # Both calls return consistent results
        assert result1.is_allowed is True
        assert result2.is_allowed is True

    def test_cache_set_uses_correct_key_and_ttl(self):
        """
        On a cache miss the result is stored with the correct key and TTL.
        """
        expected_result = EntitlementResult(
            is_allowed=False,
            limit=5,
            used=5,
            reason="usage_limit_exceeded",
        )
        expected_key = f"{_CACHE_KEY_PREFIX}:{TEST_TENANT_ID}:{FEATURE_CODE}"

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # always miss

        with (
            patch(
                "services.entitlement_service._get_redis_client",
                return_value=mock_redis,
            ),
            patch(
                "services.entitlement_service.check_entitlement",
                return_value=expected_result,
            ),
        ):
            get_cached_entitlement(TEST_TENANT_ID, FEATURE_CODE, MagicMock())

        # Verify setex was called with correct key and TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == _CACHE_TTL
        stored_json = json.loads(call_args[0][2])
        assert stored_json["is_allowed"] is False
        assert stored_json["reason"] == "usage_limit_exceeded"

    def test_redis_unavailable_falls_back_to_db(self):
        """
        When Redis raises an exception the code falls back to a direct DB
        call gracefully (fail-open for availability).
        """
        expected_result = EntitlementResult(
            is_allowed=True,
            limit=10,
            used=1,
            reason="within_plan_limit",
        )

        mock_redis = MagicMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")

        with (
            patch(
                "services.entitlement_service._get_redis_client",
                return_value=mock_redis,
            ),
            patch(
                "services.entitlement_service.check_entitlement",
                return_value=expected_result,
            ) as mock_check,
        ):
            result = get_cached_entitlement(TEST_TENANT_ID, FEATURE_CODE, MagicMock())

        # Should still return correct result despite Redis being down
        assert result.is_allowed is True
        assert mock_check.call_count == 1


# ── Helper: direct inner-function invocation for Test C ─────────────────────


def _invoke_permission_checker(
    checker_callable,
    mock_user,
    mock_db,
):
    """
    Invoke the inner permission_checker function returned by require_permission
    without FastAPI's dependency injection.
    """
    # require_permission returns a plain function with DI annotations.
    # We call it directly, passing the resolved deps as keyword args.
    return checker_callable(current_user=mock_user, db=mock_db)
