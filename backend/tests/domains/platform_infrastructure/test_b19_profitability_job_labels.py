"""
B19: Tests for profitability report job group_label and customer_name fields.

Covers:
- group_by=job → group_label uses job_number (not UUID)
- group_by=job → customer_name field is present in response rows
"""

import re
from datetime import date, timedelta

import pytest

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]

# UUID pattern to detect if group_label is still a raw UUID
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _create_customer(client, display_name: str = "B19 Profitability Customer"):
    resp = client.post(
        "/api/v1/customers/test",
        json={"display_name": display_name, "type": "person"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_site(client, customer_id: str):
    resp = client.post("/api/v1/sites/test", json={"customer_id": customer_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_job(client, customer_id: str, site_id: str):
    resp = client.post(
        "/api/v1/jobs/test",
        json={
            "customer_id": customer_id,
            "site_id": site_id,
            "scheduled_start_at": "2026-07-01T09:00:00Z",
            "scheduled_end_at": "2026-07-01T17:00:00Z",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestProfitabilityJobGroupLabels:
    def _get_profitability(self, client, group_by: str = "job"):
        today = date.today()
        date_from = (today - timedelta(days=365)).isoformat()
        date_to = today.isoformat()
        return client.get(
            "/api/v1/reports/profitability/test",
            params={
                "date_from": date_from,
                "date_to": date_to,
                "group_by": group_by,
            },
        )

    def test_profitability_report_job_group_label_uses_job_number(self, client):
        """group_by=job → group_label does NOT look like a UUID"""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        _create_job(client, cust["id"], site["id"])

        resp = self._get_profitability(client, group_by="job")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        rows = data.get("data", [])

        # If there are rows, verify none have a UUID as group_label
        for row in rows:
            group_label = row.get("group_label", "")
            assert not _UUID_PATTERN.match(group_label), (
                f"group_label '{group_label}' looks like a UUID — "
                "expected job_number format like JOB-000001"
            )

    def test_profitability_report_job_group_includes_customer_name(self, client):
        """group_by=job → customer_name field is present in response rows"""
        cust = _create_customer(client, display_name="B19 Profitability Co")
        site = _create_site(client, cust["id"])
        _create_job(client, cust["id"], site["id"])

        resp = self._get_profitability(client, group_by="job")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        rows = data.get("data", [])

        # All rows must have a customer_name key (may be None if no scheduled data in range)
        for row in rows:
            assert "customer_name" in row, (
                f"customer_name field missing from profitability row: {row}"
            )
