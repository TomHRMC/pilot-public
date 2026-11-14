"""
B21: Tests for job recurrence rule CRUD endpoints.

Covers:
- Creating a rule creates rule + first job immediately
- next_job_at is advanced beyond starts_on
- IDOR: customer UUID from another tenant returns 404
- ends_on before starts_on returns 422
- List is tenant-scoped
- PATCH is_active pauses a rule
- PATCH with 'pattern' field (not in RecurrenceRuleUpdate) is ignored by schema
- DELETE soft-deletes rule (job still exists)
"""

from datetime import date, timedelta

import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


# ==================== HELPERS ====================


def _create_customer(client, display_name: str = "B21 Rule Customer"):
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


def _create_rule(
    client,
    customer_id: str,
    site_id: str,
    pattern: str = "weekly",
    starts_on: str = None,
    **extra,
):
    if starts_on is None:
        starts_on = str(date.today())
    payload = {
        "customer_id": customer_id,
        "site_id": site_id,
        "pattern": pattern,
        "starts_on": starts_on,
        **extra,
    }
    return client.post("/api/v1/job-recurrence-rules/test", json=payload)


# ==================== TESTS ====================


class TestCreateRecurrenceRule:
    def test_create_rule_creates_first_job(self, client):
        """POST /test creates rule AND first job; response includes first_job_id."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])

        resp = _create_rule(client, cust["id"], site["id"])
        assert resp.status_code == 201, resp.text
        data = resp.json()

        # Rule fields present
        assert data["id"]
        assert data["pattern"] == "weekly"
        assert data["occurrences_created"] == 1

        # First job was created
        assert data["first_job_id"] is not None

        # Verify the job exists and has recurrence_rule_id set
        job_resp = client.get(f"/api/v1/jobs/{data['first_job_id']}/test")
        assert job_resp.status_code == 200, job_resp.text
        job_data = job_resp.json()
        assert job_data["recurrence_rule_id"] == data["id"]

    def test_create_rule_sets_next_job_at(self, client):
        """next_job_at must be the NEXT occurrence, not starts_on itself."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        starts = date.today()

        resp = _create_rule(
            client, cust["id"], site["id"], pattern="weekly", starts_on=str(starts)
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()

        # next_job_at should be 7 days after starts_on, not starts_on itself
        assert data["next_job_at"] is not None
        from datetime import datetime

        next_at = datetime.fromisoformat(data["next_job_at"])
        expected_date = starts + timedelta(weeks=1)
        assert next_at.date() == expected_date

    def test_create_rule_invalid_customer_tenant(
        self, client, second_tenant, db_session
    ):
        """Customer belonging to second_tenant used in test_tenant request → 404 (IDOR)."""
        from app.models.crm import Customer, Site

        # Insert a customer directly into second_tenant
        cust2 = Customer(
            tenant_id=second_tenant.id,
            display_name="B21 IDOR Customer",
            type="person",
        )
        db_session.add(cust2)
        db_session.flush()

        site2 = Site(
            tenant_id=second_tenant.id,
            customer_id=cust2.id,
            name="B21 IDOR Site",
        )
        db_session.add(site2)
        db_session.flush()

        # Try to create rule in test_tenant using second_tenant's customer_id
        resp = _create_rule(client, str(cust2.id), str(site2.id))
        assert resp.status_code == 404, resp.text

    def test_create_rule_ends_on_before_starts_on(self, client):
        """ends_on before starts_on → 422 validation error."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        starts = date.today()
        ends = starts - timedelta(days=1)  # in the past

        resp = _create_rule(
            client, cust["id"], site["id"], starts_on=str(starts), ends_on=str(ends)
        )
        assert resp.status_code == 422, resp.text


class TestListRecurrenceRules:
    def test_list_rules_tenant_scoped(self, client):
        """Rules returned in list belong to the test_tenant only (scoped by ID)."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])

        # Create 2 rules in test_tenant
        r1 = _create_rule(client, cust["id"], site["id"])
        r2 = _create_rule(client, cust["id"], site["id"])
        assert r1.status_code == 201
        assert r2.status_code == 201
        rule1_id = r1.json()["id"]
        rule2_id = r2.json()["id"]

        list_resp = client.get("/api/v1/job-recurrence-rules/test")
        assert list_resp.status_code == 200, list_resp.text
        items = list_resp.json()["items"]
        ids = [item["id"] for item in items]
        # Both rules for this tenant are present
        assert rule1_id in ids
        assert rule2_id in ids


class TestUpdateRecurrenceRule:
    def test_update_rule_pause(self, client):
        """PATCH is_active: false pauses the rule."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        rule = _create_rule(client, cust["id"], site["id"]).json()
        rule_id = rule["id"]

        patch_resp = client.patch(
            f"/api/v1/job-recurrence-rules/{rule_id}/test",
            json={"is_active": False},
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["is_active"] is False

    def test_update_rule_immutable_pattern_ignored(self, client):
        """PATCH payload with 'pattern' field is stripped by RecurrenceRuleUpdate schema."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        rule = _create_rule(client, cust["id"], site["id"]).json()
        rule_id = rule["id"]
        original_pattern = rule["pattern"]

        # 'pattern' is not in RecurrenceRuleUpdate — extra fields are silently dropped
        patch_resp = client.patch(
            f"/api/v1/job-recurrence-rules/{rule_id}/test",
            json={"pattern": "annually", "is_active": True},
        )
        assert patch_resp.status_code == 200, patch_resp.text
        # Pattern must be unchanged
        assert patch_resp.json()["pattern"] == original_pattern


class TestDeleteRecurrenceRule:
    def test_delete_rule_soft_deletes(self, client):
        """DELETE sets is_active = false; job spawned by rule still exists."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        create_data = _create_rule(client, cust["id"], site["id"]).json()
        rule_id = create_data["id"]
        first_job_id = create_data["first_job_id"]

        del_resp = client.delete(f"/api/v1/job-recurrence-rules/{rule_id}/test")
        assert del_resp.status_code == 204, del_resp.text

        # Rule is now inactive
        get_resp = client.get(f"/api/v1/job-recurrence-rules/{rule_id}/test")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is False

        # Job still exists (not cascade-deleted)
        job_resp = client.get(f"/api/v1/jobs/{first_job_id}/test")
        assert job_resp.status_code == 200, job_resp.text
