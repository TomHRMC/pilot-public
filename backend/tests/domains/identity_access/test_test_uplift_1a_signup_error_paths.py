"""TEST-UPLIFT-1A — Signup error-path coverage (§C.1 priority burn-down #8).

Covers:
  - PUT /api/v1/signup/{tenant_id}/step2 → 404 unknown tenant (RFC 7807)

The signup step2 404 was found returning a plain string detail — fixed in
this batch to the RFC 7807 dict shape (Rule 8).
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


class TestSignupStep2ErrorPaths:
    """PUT /api/v1/signup/{tenant_id}/step2 — error paths."""

    def test_step2_404_unknown_tenant_rfc7807(
        self, client, test_tenant, test_user, mock_cognito_jwt
    ):
        """404 for a tenant UUID with no signup record — RFC 7807 body."""
        mock_cognito_jwt(test_user)
        fake_tenant_id = uuid.uuid4()

        resp = client.put(
            f"/api/v1/signup/{fake_tenant_id}/step2",
            json={},
        )

        assert resp.status_code == 404
        problem = resp.json()["detail"]
        assert problem["type"] == "https://errors.pilotfortrades.com/not-found"
        assert problem["title"] == "Signup record not found"
        assert problem["status"] == 404
        assert "No signup record found" in problem["detail"]
