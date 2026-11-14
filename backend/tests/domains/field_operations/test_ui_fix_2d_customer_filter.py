"""
UI-FIX-2D: customer_id Filter on 3 List Endpoints — Test Suite

Coverage:
  TestJobListCustomerIdFilter    — ?customer_id= on GET /api/v1/jobs/test
  TestQuoteListCustomerIdFilter  — ?customer_id= on GET /api/v1/quotes/test
  TestInvoiceListCustomerIdFilter — ?customer_id= on GET /api/v1/invoices/test

All tests use /test variants (unauthenticated) scoped to the test tenant.
Assertions are ID-scoped — never count total rows to stay resilient to seed data.
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]

JOBS_BASE = "/api/v1/jobs"
QUOTES_BASE = "/api/v1/quotes"
INVOICES_BASE = "/api/v1/invoices"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _create_customer(client, suffix: str | None = None) -> str:
    """Create a customer via test endpoint, return its id."""
    suffix = suffix or uuid.uuid4().hex[:6]
    resp = client.post(
        "/api/v1/customers/test",
        json={"display_name": f"UI-FIX-2D Customer {suffix}", "type": "person"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_site(client, customer_id: str) -> str:
    """Create a site for the given customer, return its id."""
    resp = client.post(
        "/api/v1/sites/test",
        json={"customer_id": customer_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_job(client, customer_id: str, site_id: str) -> str:
    """Create a job via test endpoint, return its id."""
    resp = client.post(
        f"{JOBS_BASE}/test",
        json={"customer_id": customer_id, "site_id": site_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_quote(client, customer_id: str, site_id: str) -> str:
    """Create a quote via test endpoint, return its id."""
    resp = client.post(
        f"{QUOTES_BASE}/test",
        json={"customer_id": customer_id, "site_id": site_id, "currency": "USD"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_invoice_from_job(client, job_id: str) -> str:
    """Create an invoice from a job via test endpoint, return its id."""
    resp = client.post(
        f"{INVOICES_BASE}/test",
        json={"job_id": job_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


class TestJobListCustomerIdFilter:
    def test_job_list_filter_by_customer_id_returns_only_matching(self, client):
        """
        With ?customer_id=<customer_a_id>, only jobs for customer A are returned.
        Jobs for customer B must NOT be in items.
        """
        # Create two customers with sites and jobs
        cust_a_id = _create_customer(client, "jobA")
        site_a_id = _create_site(client, cust_a_id)
        job_a_id = _create_job(client, cust_a_id, site_a_id)

        cust_b_id = _create_customer(client, "jobB")
        site_b_id = _create_site(client, cust_b_id)
        job_b_id = _create_job(client, cust_b_id, site_b_id)

        # Filter by customer A
        resp = client.get(f"{JOBS_BASE}/test?customer_id={cust_a_id}&limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        # Customer A's job IS in results
        assert job_a_id in item_ids, f"Expected job {job_a_id} in {item_ids}"
        # Customer B's job is NOT in results
        assert job_b_id not in item_ids, f"Unexpected job {job_b_id} in {item_ids}"

    def test_job_list_no_customer_id_returns_all_tenant_jobs(self, client):
        """
        Without ?customer_id=, both customers' jobs are returned (existing behaviour).
        """
        cust_a_id = _create_customer(client, "jobNoFilter-A")
        site_a_id = _create_site(client, cust_a_id)
        job_a_id = _create_job(client, cust_a_id, site_a_id)

        cust_b_id = _create_customer(client, "jobNoFilter-B")
        site_b_id = _create_site(client, cust_b_id)
        job_b_id = _create_job(client, cust_b_id, site_b_id)

        resp = client.get(f"{JOBS_BASE}/test?limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        # Both jobs are in results
        assert job_a_id in item_ids, f"Expected job {job_a_id} in {item_ids}"
        assert job_b_id in item_ids, f"Expected job {job_b_id} in {item_ids}"

    def test_job_list_customer_id_count_matches_filtered_total(self, client):
        """
        total in paginated response reflects filtered count, not tenant-wide count.
        """
        cust_id = _create_customer(client, "jobCount")
        site_id = _create_site(client, cust_id)
        job1_id = _create_job(client, cust_id, site_id)
        job2_id = _create_job(client, cust_id, site_id)

        resp = client.get(f"{JOBS_BASE}/test?customer_id={cust_id}&limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        assert job1_id in item_ids
        assert job2_id in item_ids
        # total must equal the number of filtered items (not total tenant jobs)
        assert data["total"] == len(data["items"]), (
            f"total={data['total']} should equal len(items)={len(data['items'])}"
        )


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------


class TestQuoteListCustomerIdFilter:
    def test_quote_list_filter_by_customer_id_returns_only_matching(self, client):
        """
        With ?customer_id=<customer_a_id>, only quotes for customer A are returned.
        Quotes for customer B must NOT be in items.
        """
        cust_a_id = _create_customer(client, "quoteA")
        site_a_id = _create_site(client, cust_a_id)
        quote_a_id = _create_quote(client, cust_a_id, site_a_id)

        cust_b_id = _create_customer(client, "quoteB")
        site_b_id = _create_site(client, cust_b_id)
        quote_b_id = _create_quote(client, cust_b_id, site_b_id)

        resp = client.get(f"{QUOTES_BASE}/test?customer_id={cust_a_id}&limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        assert quote_a_id in item_ids, f"Expected quote {quote_a_id} in {item_ids}"
        assert quote_b_id not in item_ids, (
            f"Unexpected quote {quote_b_id} in {item_ids}"
        )

    def test_quote_list_no_customer_id_returns_all_tenant_quotes(self, client):
        """
        Without ?customer_id=, all customers' quotes are returned.
        """
        cust_a_id = _create_customer(client, "quoteNoFilter-A")
        site_a_id = _create_site(client, cust_a_id)
        quote_a_id = _create_quote(client, cust_a_id, site_a_id)

        cust_b_id = _create_customer(client, "quoteNoFilter-B")
        site_b_id = _create_site(client, cust_b_id)
        quote_b_id = _create_quote(client, cust_b_id, site_b_id)

        resp = client.get(f"{QUOTES_BASE}/test?limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        assert quote_a_id in item_ids, f"Expected quote {quote_a_id} in {item_ids}"
        assert quote_b_id in item_ids, f"Expected quote {quote_b_id} in {item_ids}"

    def test_quote_list_customer_id_count_matches_filtered_total(self, client):
        """
        total in paginated response reflects filtered count.
        """
        cust_id = _create_customer(client, "quoteCount")
        site_id = _create_site(client, cust_id)
        q1_id = _create_quote(client, cust_id, site_id)
        q2_id = _create_quote(client, cust_id, site_id)

        resp = client.get(f"{QUOTES_BASE}/test?customer_id={cust_id}&limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        assert q1_id in item_ids
        assert q2_id in item_ids
        assert data["total"] == len(data["items"]), (
            f"total={data['total']} should equal len(items)={len(data['items'])}"
        )


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


class TestInvoiceListCustomerIdFilter:
    def test_invoice_list_filter_by_customer_id_returns_only_matching(self, client):
        """
        With ?customer_id=<customer_a_id>, only invoices for customer A are returned.
        Invoices for customer B must NOT be in items.
        """
        cust_a_id = _create_customer(client, "invA")
        site_a_id = _create_site(client, cust_a_id)
        job_a_id = _create_job(client, cust_a_id, site_a_id)
        inv_a_id = _create_invoice_from_job(client, job_a_id)

        cust_b_id = _create_customer(client, "invB")
        site_b_id = _create_site(client, cust_b_id)
        job_b_id = _create_job(client, cust_b_id, site_b_id)
        inv_b_id = _create_invoice_from_job(client, job_b_id)

        resp = client.get(f"{INVOICES_BASE}/test?customer_id={cust_a_id}&limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        assert inv_a_id in item_ids, f"Expected invoice {inv_a_id} in {item_ids}"
        assert inv_b_id not in item_ids, f"Unexpected invoice {inv_b_id} in {item_ids}"

    def test_invoice_list_no_customer_id_returns_all_tenant_invoices(self, client):
        """
        Without ?customer_id=, all customers' invoices are returned.
        """
        cust_a_id = _create_customer(client, "invNoFilter-A")
        site_a_id = _create_site(client, cust_a_id)
        job_a_id = _create_job(client, cust_a_id, site_a_id)
        inv_a_id = _create_invoice_from_job(client, job_a_id)

        cust_b_id = _create_customer(client, "invNoFilter-B")
        site_b_id = _create_site(client, cust_b_id)
        job_b_id = _create_job(client, cust_b_id, site_b_id)
        inv_b_id = _create_invoice_from_job(client, job_b_id)

        resp = client.get(f"{INVOICES_BASE}/test?limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        assert inv_a_id in item_ids, f"Expected invoice {inv_a_id} in {item_ids}"
        assert inv_b_id in item_ids, f"Expected invoice {inv_b_id} in {item_ids}"

    def test_invoice_list_customer_id_count_matches_filtered_total(self, client):
        """
        total in paginated response reflects filtered count.
        """
        cust_id = _create_customer(client, "invCount")
        site_id = _create_site(client, cust_id)
        job1_id = _create_job(client, cust_id, site_id)
        job2_id = _create_job(client, cust_id, site_id)
        inv1_id = _create_invoice_from_job(client, job1_id)
        inv2_id = _create_invoice_from_job(client, job2_id)

        resp = client.get(f"{INVOICES_BASE}/test?customer_id={cust_id}&limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        item_ids = [item["id"] for item in data["items"]]

        assert inv1_id in item_ids
        assert inv2_id in item_ids
        assert data["total"] == len(data["items"]), (
            f"total={data['total']} should equal len(items)={len(data['items'])}"
        )
