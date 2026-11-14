"""
UP-1 (Part A): Tests for the WIP (Work-In-Progress) report endpoint.

Covers (per design doc §G):
  1. ETC present — has_etc=true, etc_cost_cents = round(hours * rate)
  2. ETC absent — has_etc=false, etc_cost_cents=0, projected=actual
  3. Latest ETC wins — two time entries, max etc_captured_at used
  4. No quote — budget/margin/deviation null, row still present
  5. Over budget — budget_deviation_pct < 0, counted in summary
  6. Below margin target — 0 < margin < target, below_margin_target=true
  7. Status filter — only scheduled/in_progress appear; completed excluded
  8. Decimal rounding — ROUND_HALF_UP verified with .5 cent boundary
  9. Invalid sort — 422 RFC 7807 Problem Details
 10. Tenant isolation — second_tenant job absent from test tenant rows

Domain: platform_infrastructure (PRD §3.8)
"""

import pytest
from sqlalchemy import text

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers — all use the conftest `client` fixture (never module-level TestClient)
# ---------------------------------------------------------------------------


def _create_customer(client, display_name: str = "WIP Test Customer"):
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


def _create_job(
    client,
    customer_id: str,
    site_id: str,
    quote_id: str | None = None,
    title: str = "WIP Test Job",
):
    payload: dict = {
        "customer_id": customer_id,
        "site_id": site_id,
        "scheduled_start_at": "2026-07-15T09:00:00Z",
        "scheduled_end_at": "2026-07-15T17:00:00Z",
        "title": title,
    }
    if quote_id:
        payload["quote_id"] = quote_id
    resp = client.post("/api/v1/jobs/test", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _set_job_status(db_session, job_id: str, status_code: str):
    """Set a job's status directly via SQL.

    Uses direct status_id update rather than the PATCH endpoint, because the
    forward-transition validation (draft → scheduled → in_progress → completed)
    adds complexity unrelated to the WIP report being tested. We set status_id
    directly to the platform-level job_status row matching the given code.
    """
    from sqlalchemy import text as sa_text

    db_session.execute(
        sa_text(
            "UPDATE job SET status_id = "
            "(SELECT id FROM job_status WHERE code = :code) "
            "WHERE id = :jid"
        ),
        {"code": status_code, "jid": job_id},
    )
    db_session.commit()


def _create_quote(client, customer_id: str, site_id: str):
    resp = client.post(
        "/api/v1/quotes/test",
        json={"customer_id": customer_id, "site_id": site_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_time_entry(
    client,
    job_id: str,
    *,
    started_at: str,
    ended_at: str,
    hours_remaining_estimate: float | None = None,
    hourly_rate_cents: int | None = None,
):
    """Create a time entry. etc_captured_at is set to ended_at by the impl."""
    payload: dict = {"started_at": started_at, "ended_at": ended_at}
    if hours_remaining_estimate is not None:
        payload["hours_remaining_estimate"] = hours_remaining_estimate
    if hourly_rate_cents is not None:
        payload["hourly_rate_cents"] = hourly_rate_cents
    resp = client.post(f"/api/v1/jobs/{job_id}/time-entries/test", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _set_job_costs(db_session, job_id: str, labor_cents: int, material_cents: int):
    """Directly set actual_labor_cost_cents and actual_material_cost_cents.

    These columns are maintained by the profitability_rollup Celery task,
    not writable via the API. We set them via SQL for deterministic test data.
    """
    db_session.execute(
        text(
            "UPDATE job SET actual_labor_cost_cents = :labor, "
            "actual_material_cost_cents = :material WHERE id = :jid"
        ),
        {"labor": labor_cents, "material": material_cents, "jid": job_id},
    )
    db_session.commit()


def _set_quote_total(db_session, quote_id: str, total_cents: int):
    """Directly set quote.total_cents for deterministic budget values."""
    db_session.execute(
        text("UPDATE quote SET total_cents = :total WHERE id = :qid"),
        {"total": total_cents, "qid": quote_id},
    )
    db_session.commit()


def _get_wip(client, **params):
    """Call the /reports/wip/test endpoint with optional query params."""
    return client.get("/api/v1/reports/wip/test", params=params)


def _find_row(rows: list[dict], job_id: str) -> dict | None:
    """Find a specific job's row in the WIP response by job_id."""
    for r in rows:
        if r["job_id"] == job_id:
            return r
    return None


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


class TestWipReport:
    """Tests for GET /api/v1/reports/wip (and /test twin)."""

    # --- Case 1: ETC present ---
    def test_etc_present(self, client, db_session, test_tenant):
        """Job with a recent time entry (non-null ETC) → has_etc=true,
        etc_cost_cents = round(hours * rate), projected = actual + etc."""
        cust = _create_customer(client, "ETC Present Co")
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        _set_job_status(db_session, job["id"], "scheduled")
        _set_job_costs(db_session, job["id"], labor_cents=10000, material_cents=5000)

        # ETC: 6.5 hours remaining * 2000 cents/hr = 13000 cents
        _create_time_entry(
            client,
            job["id"],
            started_at="2026-07-15T09:00:00Z",
            ended_at="2026-07-15T10:00:00Z",
            hours_remaining_estimate=6.5,
            hourly_rate_cents=2000,
        )

        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        row = _find_row(resp.json()["rows"], job["id"])
        assert row is not None, "Job not found in WIP rows"
        assert row["has_etc"] is True
        assert row["etc_cost_cents"] == 13000  # 6.5 * 2000 = 13000
        assert row["actual_cost_cents"] == 15000  # 10000 + 5000
        assert row["projected_cost_cents"] == 28000  # 15000 + 13000

    # --- Case 2: ETC absent ---
    def test_etc_absent(self, client, db_session, test_tenant):
        """Active job with no ETC time entry → has_etc=false, etc_cost=0,
        projected_cost == actual_cost."""
        cust = _create_customer(client, "ETC Absent Co")
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        _set_job_status(db_session, job["id"], "scheduled")
        _set_job_costs(db_session, job["id"], labor_cents=8000, material_cents=2000)

        # No time entry created → no ETC
        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        row = _find_row(resp.json()["rows"], job["id"])
        assert row is not None
        assert row["has_etc"] is False
        assert row["etc_cost_cents"] == 0
        assert row["projected_cost_cents"] == 10000  # == actual_cost

    # --- Case 3: Latest ETC wins ---
    def test_latest_etc_wins(self, client, db_session, test_tenant):
        """Two time entries with different etc_captured_at → the row uses
        the one with the max etc_captured_at."""
        cust = _create_customer(client, "Latest ETC Co")
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        _set_job_status(db_session, job["id"], "in_progress")
        _set_job_costs(db_session, job["id"], labor_cents=5000, material_cents=0)

        # First ETC entry (earlier ended_at → earlier etc_captured_at)
        _create_time_entry(
            client,
            job["id"],
            started_at="2026-07-10T09:00:00Z",
            ended_at="2026-07-10T10:00:00Z",
            hours_remaining_estimate=10.0,
            hourly_rate_cents=1000,
        )
        # Second ETC entry (later ended_at → later etc_captured_at)
        _create_time_entry(
            client,
            job["id"],
            started_at="2026-07-12T09:00:00Z",
            ended_at="2026-07-12T10:00:00Z",
            hours_remaining_estimate=3.0,
            hourly_rate_cents=1000,
        )

        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        row = _find_row(resp.json()["rows"], job["id"])
        assert row is not None
        assert row["has_etc"] is True
        # Latest ETC: 3.0 * 1000 = 3000 (not 10.0 * 1000 = 10000)
        assert row["etc_cost_cents"] == 3000
        assert row["etc_hours_remaining"] == 3.0

    # --- Case 4: No quote ---
    def test_no_quote(self, client, db_session, test_tenant):
        """Job with quote_id=NULL → budget/margin/deviation null, row present."""
        cust = _create_customer(client, "No Quote Co")
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])  # no quote_id
        _set_job_status(db_session, job["id"], "scheduled")
        _set_job_costs(db_session, job["id"], labor_cents=7000, material_cents=3000)

        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        row = _find_row(resp.json()["rows"], job["id"])
        assert row is not None
        assert row["quoted_budget_cents"] is None
        assert row["projected_margin_pct"] is None
        assert row["budget_deviation_pct"] is None
        assert row["below_margin_target"] is False
        assert row["actual_cost_cents"] == 10000

    # --- Case 5: Over budget ---
    def test_over_budget(self, client, db_session, test_tenant):
        """projected_cost > budget → budget_deviation_pct < 0,
        counted in summary.jobs_over_budget_count."""
        cust = _create_customer(client, "Over Budget Co")
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])
        _set_quote_total(db_session, quote["id"], 20000)  # budget = 20000

        job = _create_job(client, cust["id"], site["id"], quote_id=quote["id"])
        _set_job_status(db_session, job["id"], "in_progress")
        # actual = 15000, ETC = 10000 → projected = 25000 > 20000 budget
        _set_job_costs(db_session, job["id"], labor_cents=10000, material_cents=5000)
        _create_time_entry(
            client,
            job["id"],
            started_at="2026-07-15T09:00:00Z",
            ended_at="2026-07-15T10:00:00Z",
            hours_remaining_estimate=5.0,
            hourly_rate_cents=2000,  # 5 * 2000 = 10000
        )

        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        row = _find_row(data["rows"], job["id"])
        assert row is not None
        assert row["projected_cost_cents"] == 25000
        assert row["quoted_budget_cents"] == 20000
        assert row["budget_deviation_pct"] is not None
        assert row["budget_deviation_pct"] < 0
        # (20000 - 25000) / 20000 * 100 = -25.0
        assert row["budget_deviation_pct"] == -25.0
        # Summary should count this job as over budget
        assert data["summary"]["jobs_over_budget_count"] >= 1

    # --- Case 6: Below margin target ---
    def test_below_margin_target(self, client, db_session, test_tenant):
        """0 < projected_margin_pct < target_pct → below_margin_target=true,
        counted in summary.jobs_below_margin_target_count."""
        cust = _create_customer(client, "Below Target Co")
        site = _create_site(client, cust["id"])
        quote = _create_quote(client, cust["id"], site["id"])
        _set_quote_total(db_session, quote["id"], 100000)  # budget = 100000

        job = _create_job(client, cust["id"], site["id"], quote_id=quote["id"])
        _set_job_status(db_session, job["id"], "scheduled")
        # actual = 85000, no ETC → projected = 85000
        # margin = (100000 - 85000) / 100000 * 100 = 15.0
        # target is 20 (platform default) → 15 < 20 → below target
        _set_job_costs(db_session, job["id"], labor_cents=60000, material_cents=25000)

        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        row = _find_row(data["rows"], job["id"])
        assert row is not None
        assert row["projected_margin_pct"] == 15.0
        assert row["below_margin_target"] is True
        assert data["summary"]["jobs_below_margin_target_count"] >= 1

    # --- Case 7: Status filter ---
    def test_status_filter_excludes_terminal(self, client, db_session, test_tenant):
        """Only scheduled/in_progress jobs appear by default; a completed job
        does NOT appear."""
        cust = _create_customer(client, "Status Filter Co")
        site = _create_site(client, cust["id"])

        # Active job (scheduled)
        active_job = _create_job(client, cust["id"], site["id"], title="Active Job")
        _set_job_status(db_session, active_job["id"], "scheduled")

        # Completed job (terminal — should NOT appear)
        completed_job = _create_job(
            client, cust["id"], site["id"], title="Completed Job"
        )
        _set_job_status(db_session, completed_job["id"], "scheduled")
        _set_job_status(db_session, completed_job["id"], "in_progress")
        _set_job_status(db_session, completed_job["id"], "completed")

        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        rows = resp.json()["rows"]

        # Active job should be present
        assert _find_row(rows, active_job["id"]) is not None
        # Completed job should NOT be present
        assert _find_row(rows, completed_job["id"]) is None

    # --- Case 8: Decimal rounding (ROUND_HALF_UP) ---
    def test_decimal_rounding_half_up(self, client, db_session, test_tenant):
        """Fractional hours_remaining_estimate with a rate producing a .5 cent
        → ROUND_HALF_UP verified (rounds up, not banker's rounding)."""
        cust = _create_customer(client, "Decimal Rounding Co")
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        _set_job_status(db_session, job["id"], "scheduled")
        _set_job_costs(db_session, job["id"], labor_cents=0, material_cents=0)

        # 0.5 hours * 3 cents/hr = 1.5 cents
        # ROUND_HALF_UP → 2 cents (banker's rounding would give 2 as well for 1.5)
        # Use 1.5 hours * 3 cents = 4.5 → ROUND_HALF_UP = 5, banker's = 4
        _create_time_entry(
            client,
            job["id"],
            started_at="2026-07-15T09:00:00Z",
            ended_at="2026-07-15T10:00:00Z",
            hours_remaining_estimate=1.5,
            hourly_rate_cents=3,  # 1.5 * 3 = 4.5 → ROUND_HALF_UP = 5
        )

        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        row = _find_row(resp.json()["rows"], job["id"])
        assert row is not None
        # 1.5 * 3 = 4.5 → ROUND_HALF_UP rounds to 5 (banker's would round to 4)
        assert row["etc_cost_cents"] == 5

    # --- Case 9: Invalid sort → 422 RFC 7807 ---
    def test_invalid_sort_returns_422(self, client, test_tenant):
        """?sort=bogus → 422 with RFC 7807 Problem Details.

        FastAPI wraps HTTPException(detail=dict) as {"detail": {...}},
        so the RFC 7807 fields are under body["detail"].
        """
        resp = _get_wip(client, sort="bogus")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["type"].startswith("https://")
        assert "title" in detail
        assert detail["status"] == 422
        assert "detail" in detail

    def test_invalid_order_returns_422(self, client, test_tenant):
        """?order=sideways → 422 RFC 7807."""
        resp = _get_wip(client, order="sideways")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["status"] == 422
        assert detail["type"].startswith("https://")

    def test_invalid_status_code_returns_422(self, client, test_tenant):
        """?status=bogus_code → 422 RFC 7807."""
        resp = _get_wip(client, status="bogus_code")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["status"] == 422
        assert detail["type"].startswith("https://")

    # --- Case 10: Tenant isolation ---
    def test_tenant_isolation(self, client, db_session, test_tenant, second_tenant):
        """Insert an active job in second_tenant; call /wip/test (which uses
        the canonical test tenant) → the second_tenant job is absent."""
        import uuid

        from sqlmodel import select

        from app.models.crm import Customer, CustomerType
        from app.models.fulfillment import Job, JobStatus

        # Create a customer + job directly in second_tenant (not via /test endpoints,
        # which always use the canonical test tenant)
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=second_tenant.id,
            display_name=f"Second Tenant Cust {uuid.uuid4()}",
            type=CustomerType.person,
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()

        # Need a site for second_tenant
        from app.models.crm import Site

        site = Site(
            id=uuid.uuid4(),
            tenant_id=second_tenant.id,
            customer_id=customer.id,
            site_name="Second Tenant Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()

        # Get the 'scheduled' job status (platform-level)
        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.code == "scheduled")
        ).first()
        assert job_status is not None, "scheduled job_status not seeded"

        second_job = Job(
            id=uuid.uuid4(),
            tenant_id=second_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=job_status.id,
            job_number=f"JOB-ST-{uuid.uuid4().hex[:8].upper()}",
            is_active=True,
            actual_labor_cost_cents=99999,
            actual_material_cost_cents=0,
        )
        db_session.add(second_job)
        db_session.commit()

        # Call /wip/test — uses canonical test tenant (...0001)
        resp = _get_wip(client)
        assert resp.status_code == 200, resp.text
        rows = resp.json()["rows"]

        # The second_tenant job must NOT appear
        assert _find_row(rows, str(second_job.id)) is None

    # --- Bonus: response structure validation ---
    def test_response_structure(self, client, test_tenant):
        """Verify the response has the expected top-level keys and types."""
        resp = _get_wip(client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "wip"
        assert "generated_at" in data
        assert "margin_target_pct" in data
        assert "row_count" in data
        assert "summary" in data
        assert "rows" in data
        assert isinstance(data["rows"], list)
        assert isinstance(data["summary"], dict)

        summary = data["summary"]
        for key in (
            "active_job_count",
            "total_actual_cost_cents",
            "total_quoted_budget_cents",
            "total_projected_cost_cents",
            "jobs_over_budget_count",
            "jobs_below_margin_target_count",
        ):
            assert key in summary, f"Missing summary key: {key}"

    def test_generated_at_is_utc_aware(self, client, test_tenant):
        """generated_at must be a timezone-aware UTC datetime (Rule 7)."""
        resp = _get_wip(client)
        assert resp.status_code == 200
        generated_at = resp.json()["generated_at"]
        # ISO 8601 with timezone offset (e.g. ...Z or +00:00)
        assert generated_at.endswith("Z") or "+00:00" in generated_at, (
            f"generated_at is not UTC-aware: {generated_at}"
        )

    def test_sort_by_actual_cost_desc(self, client, db_session, test_tenant):
        """Verify sorting works: sort=actual_cost_cents, order=desc."""
        cust = _create_customer(client, "Sort Test Co")
        site = _create_site(client, cust["id"])

        job_low = _create_job(client, cust["id"], site["id"], title="Low Cost")
        _set_job_status(db_session, job_low["id"], "scheduled")
        _set_job_costs(db_session, job_low["id"], labor_cents=1000, material_cents=0)

        job_high = _create_job(client, cust["id"], site["id"], title="High Cost")
        _set_job_status(db_session, job_high["id"], "scheduled")
        _set_job_costs(db_session, job_high["id"], labor_cents=50000, material_cents=0)

        resp = _get_wip(client, sort="actual_cost_cents", order="desc")
        assert resp.status_code == 200
        rows = resp.json()["rows"]

        # Find the positions of our two jobs
        low_idx = next(
            (i for i, r in enumerate(rows) if r["job_id"] == job_low["id"]), None
        )
        high_idx = next(
            (i for i, r in enumerate(rows) if r["job_id"] == job_high["id"]), None
        )
        assert low_idx is not None and high_idx is not None
        # High cost should come before low cost in desc order
        assert high_idx < low_idx
