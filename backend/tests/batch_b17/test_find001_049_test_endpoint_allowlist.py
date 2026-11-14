"""
FIND-001 through FIND-049 (S4 Low post-review) — Test endpoint env-var guard
must use an ALLOWLIST pattern, not a blocklist.

Guard implementation: core/config.py::is_test_endpoint_allowed()
  return settings.TEST_ENDPOINT_ENABLED and settings.ENVIRONMENT in ['dev', 'qa']

This is an allowlist: only 'dev' and 'qa' are explicitly permitted. Any other
environment value — including unknown future names like 'uat', 'test', 'demo',
'staging', 'prod' — is hard-blocked automatically.

Test plan from remediation plan FIND-001–049:
  - ENVIRONMENT=demo, TEST_ENDPOINT_ENABLED=true → 403
  - ENVIRONMENT=prod → 403
  - ENVIRONMENT=test (unknown name) → 403
  - ENVIRONMENT=dev, TEST_ENDPOINT_ENABLED=false → 403
  - ENVIRONMENT=qa, TEST_ENDPOINT_ENABLED=true → 200 without JWT
  - ENVIRONMENT=dev, TEST_ENDPOINT_ENABLED=true → 200 without JWT

Architecture reference: ARCH-§7.2 updated 2026-05-11 to allowlist spec.

Test subfolder: tests/batch_b17/
"""

from unittest.mock import patch

# ---------------------------------------------------------------------------
# Unit tests: is_test_endpoint_allowed() — allowlist logic
# ---------------------------------------------------------------------------


class TestIsTestEndpointAllowedUnit:
    """
    Unit tests for core/config.py::is_test_endpoint_allowed().
    Tests the allowlist logic directly without going through HTTP.
    """

    def test_demo_env_enabled_returns_false(self):
        """ENVIRONMENT=demo + TEST_ENDPOINT_ENABLED=true → blocked (not in allowlist)."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "demo"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is False, (
                "ENVIRONMENT=demo must be blocked — not in allowlist ('dev', 'qa')"
            )

    def test_prod_env_returns_false(self):
        """ENVIRONMENT=production → blocked regardless of TEST_ENDPOINT_ENABLED."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "production"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is False

    def test_staging_env_returns_false(self):
        """ENVIRONMENT=staging → blocked."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "staging"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is False

    def test_unknown_test_env_returns_false(self):
        """ENVIRONMENT=test (unknown name not in allowlist) → blocked."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "test"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is False, (
                "ENVIRONMENT=test must be blocked — 'test' is not in the allowlist ('dev', 'qa'). "
                "Allowlist prevents unknown env names from accidentally getting access."
            )

    def test_uat_env_returns_false(self):
        """ENVIRONMENT=uat (future env name) → blocked by allowlist."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "uat"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is False

    def test_dev_env_disabled_returns_false(self):
        """ENVIRONMENT=dev + TEST_ENDPOINT_ENABLED=false → blocked."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "dev"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", False),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is False

    def test_qa_env_enabled_returns_true(self):
        """ENVIRONMENT=qa + TEST_ENDPOINT_ENABLED=true → allowed."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "qa"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is True

    def test_dev_env_enabled_returns_true(self):
        """ENVIRONMENT=dev + TEST_ENDPOINT_ENABLED=true → allowed."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "dev"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            from core.config import is_test_endpoint_allowed

            assert is_test_endpoint_allowed() is True


# ---------------------------------------------------------------------------
# HTTP integration: GET /api/v1/catalog/pricing-cache/test — representative endpoint
# ---------------------------------------------------------------------------


class TestTestEndpointHttp403Blocked:
    """
    HTTP-level tests: a representative /test endpoint returns 403 when guard blocks.
    Uses GET /api/v1/catalog/pricing-cache/test as the test vehicle.
    """

    def test_demo_env_returns_403(self, client):
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "demo"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            response = client.get("/api/v1/catalog/pricing-cache/test")
        assert response.status_code == 403, (
            f"Expected 403 for ENVIRONMENT=demo, got {response.status_code}"
        )

    def test_prod_env_returns_403(self, client):
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "production"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            response = client.get("/api/v1/catalog/pricing-cache/test")
        assert response.status_code == 403

    def test_unknown_test_env_returns_403(self, client):
        """ENVIRONMENT=test (unknown) must be hard-blocked — not auto-allowed."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "test"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            response = client.get("/api/v1/catalog/pricing-cache/test")
        assert response.status_code == 403, (
            f"ENVIRONMENT='test' must return 403 (not in allowlist). Got {response.status_code}"
        )

    def test_dev_disabled_returns_403(self, client):
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "dev"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", False),
        ):
            response = client.get("/api/v1/catalog/pricing-cache/test")
        assert response.status_code == 403

    def test_qa_enabled_returns_200_no_jwt(self, client, test_tenant):
        """ENVIRONMENT=qa + TEST_ENDPOINT_ENABLED=true → 200 without JWT."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "qa"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            response = client.get("/api/v1/catalog/pricing-cache/test")
        assert response.status_code == 200, (
            f"ENVIRONMENT=qa + TEST_ENDPOINT_ENABLED=true must return 200 (no JWT). "
            f"Got {response.status_code}: {response.text}"
        )

    def test_dev_enabled_returns_200_no_jwt(self, client, test_tenant):
        """ENVIRONMENT=dev + TEST_ENDPOINT_ENABLED=true → 200 without JWT."""
        from core.config import settings

        with (
            patch.object(settings, "ENVIRONMENT", "dev"),
            patch.object(settings, "TEST_ENDPOINT_ENABLED", True),
        ):
            response = client.get("/api/v1/catalog/pricing-cache/test")
        assert response.status_code == 200, (
            f"ENVIRONMENT=dev + TEST_ENDPOINT_ENABLED=true must return 200 (no JWT). "
            f"Got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# Structural: verify guard uses allowlist not blocklist
# ---------------------------------------------------------------------------


class TestAllowlistImplementationIsCorrect:
    """
    Verifies the guard code in config.py uses an allowlist pattern.
    This is a structural assertion that the fix hasn't been accidentally reverted.
    """

    def test_is_test_endpoint_allowed_uses_allowlist(self):
        """
        The RETURN STATEMENT must use `ENVIRONMENT in [...]` (allowlist), not
        `ENVIRONMENT not in [...]` (blocklist). Docstring content is not checked.
        """
        import inspect

        from core.config import is_test_endpoint_allowed

        src = inspect.getsource(is_test_endpoint_allowed)

        # Extract only the return statement line
        return_lines = [
            line.strip()
            for line in src.splitlines()
            if line.strip().startswith("return")
        ]
        assert return_lines, "is_test_endpoint_allowed must have a return statement"
        return_stmt = " ".join(return_lines)

        # Must use ENVIRONMENT in [...] allowlist pattern in the return statement
        assert "ENVIRONMENT in" in return_stmt, (
            f"Return statement must use 'ENVIRONMENT in [...]' (allowlist). Got: {return_stmt}"
        )

        # Must NOT use a blocklist pattern in the return statement
        assert "ENVIRONMENT not in" not in return_stmt, (
            f"Return statement must NOT use 'ENVIRONMENT not in' (blocklist). Got: {return_stmt}"
        )

        # Must have both 'dev' and 'qa' in the allowlist
        assert "dev" in return_stmt and "qa" in return_stmt, (
            f"Allowlist must explicitly contain both 'dev' and 'qa'. Got: {return_stmt}"
        )
