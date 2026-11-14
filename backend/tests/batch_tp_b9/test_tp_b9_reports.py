"""
TP-B9 — Reports — Test Endpoints

Coverage (one happy-path test per new /test endpoint minimum):
  1. GET /api/v1/reports/profitability/test     → get_profitability_test
  2. GET /api/v1/reports/revenue/test           → get_revenue_test
  3. GET /api/v1/reports/ar-aging/test          → get_ar_aging_test
  4. GET /api/v1/reports/tech-productivity/test → get_tech_productivity_test
  5. GET /api/v1/reports/tax-liability/test     → get_tax_liability_test
  6. GET /api/v1/reports/voice-analytics/test   → get_voice_analytics_test

Test strategy: pass date_from/date_to covering a wide range — test tenant
may have no data, but empty arrays are valid per spec. Assert response schema shape.

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 422 when date_from > date_to
"""

from unittest.mock import patch

from fastapi import status

from core.config import settings

BASE = "/api/v1/reports"
# Wide date range covering any potential test data
DATE_FROM = "2020-01-01"
DATE_TO = "2030-12-31"


# ==================== SECURITY GUARD TESTS ====================


class TestTpB9SecurityGuards:
    def test_profitability_blocked_when_disabled(self, client):
        """GET /reports/profitability/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/profitability/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_revenue_blocked_in_production(self, client):
        """GET /reports/revenue/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.get(
                    f"{BASE}/revenue/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== PROFITABILITY /test ====================


class TestTpB9Profitability:
    def test_profitability_returns_200(self, client):
        """GET /reports/profitability/test returns valid response schema."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/profitability/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "profitability"
        assert "data" in data
        assert "row_count" in data
        assert isinstance(data["data"], list)

    def test_profitability_422_invalid_date_range(self, client):
        """Returns 422 when date_from > date_to."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/profitability/test",
                    params={"date_from": "2030-12-31", "date_to": "2020-01-01"},
                )
        assert response.status_code == 422


# ==================== REVENUE /test ====================


class TestTpB9Revenue:
    def test_revenue_returns_200(self, client):
        """GET /reports/revenue/test returns valid response schema."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/revenue/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "revenue"
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_revenue_422_invalid_date_range(self, client):
        """Returns 422 when date_from > date_to."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/revenue/test",
                    params={"date_from": "2030-12-31", "date_to": "2020-01-01"},
                )
        assert response.status_code == 422


# ==================== AR AGING /test ====================


class TestTpB9ArAging:
    def test_ar_aging_returns_200(self, client):
        """GET /reports/ar-aging/test returns valid response schema."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/ar-aging/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "ar_aging"
        assert "data" in data
        assert "summary" in data
        assert isinstance(data["data"], list)


# ==================== TECH PRODUCTIVITY /test ====================


class TestTpB9TechProductivity:
    def test_tech_productivity_returns_200(self, client):
        """GET /reports/tech-productivity/test returns valid response schema."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/tech-productivity/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "tech_productivity"
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_tech_productivity_422_invalid_date_range(self, client):
        """Returns 422 when date_from > date_to."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/tech-productivity/test",
                    params={"date_from": "2030-01-01", "date_to": "2020-01-01"},
                )
        assert response.status_code == 422


# ==================== TAX LIABILITY /test ====================


class TestTpB9TaxLiability:
    def test_tax_liability_returns_200(self, client):
        """GET /reports/tax-liability/test returns valid response schema."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/tax-liability/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "tax_liability"
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_tax_liability_422_invalid_date_range(self, client):
        """Returns 422 when date_from > date_to."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/tax-liability/test",
                    params={"date_from": "2030-01-01", "date_to": "2020-01-01"},
                )
        assert response.status_code == 422


# ==================== VOICE ANALYTICS /test ====================


class TestTpB9VoiceAnalytics:
    def test_voice_analytics_returns_200(self, client):
        """GET /reports/voice-analytics/test returns valid response schema."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/voice-analytics/test",
                    params={"date_from": DATE_FROM, "date_to": DATE_TO},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "voice_analytics"
        assert "data" in data
        assert "summary" in data
        assert isinstance(data["data"], list)

    def test_voice_analytics_422_invalid_date_range(self, client):
        """Returns 422 when date_from > date_to."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{BASE}/voice-analytics/test",
                    params={"date_from": "2030-01-01", "date_to": "2020-01-01"},
                )
        assert response.status_code == 422
