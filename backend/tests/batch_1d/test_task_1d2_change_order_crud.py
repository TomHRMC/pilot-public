"""
Task 1-D-2: Change Order CRUD API Tests

Verifies endpoints under /api/v1/jobs/{id}/change-orders and
/api/v1/jobs/{id}/change-orders/{co_id}/lines:

  1. POST   /change-orders      → 201, creates ChangeOrder in DB
  2. GET    /change-orders      → 200, lists active change orders for job
  3. GET    /change-orders/{id} → 200, retrieves single change order
  4. PATCH  /change-orders/{id} → 200, updates description
  5. DELETE /change-orders/{id} → 200, soft-deletes (is_active=False)
  6. POST   /change-orders/{id}/lines → 201, creates a line; DB recalc fires
  7. GET    /change-orders/{id}/lines → 200, lists active lines
  8. PATCH  /change-orders/{id}/lines/{lid} → 200, updates line
  9. DELETE /change-orders/{id}/lines/{lid} → 200, soft-deletes line
 10. Cross-tenant isolation: 404 for foreign job_id / change_order_id

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-D-2
Batch 1-D Verification:
  - Change order line insertion triggers DB recalc_change_order_totals_fn
    and updates header totals.
"""

import uuid

from sqlmodel import select

from app.models.fulfillment import Job, JobStatus
from app.models.quoting import ChangeOrder, ChangeOrderLine, QcoLineType

# ============================================================
# Helpers
# ============================================================


def _get_or_create_job_status(db_session, code: str = "draft") -> JobStatus:
    js = db_session.exec(
        select(JobStatus).where(JobStatus.code == code, JobStatus.tenant_id.is_(None))
    ).first()
    if not js:
        js = JobStatus(
            id=uuid.uuid4(),
            code=code,
            name=code.capitalize(),
            is_default=(code == "draft"),
            is_active=True,
        )
        db_session.add(js)
        db_session.flush()
    return js


def _get_or_create_qco_line_type(db_session, code: str = "labor") -> QcoLineType:
    lt = db_session.exec(select(QcoLineType).where(QcoLineType.code == code)).first()
    if not lt:
        lt = QcoLineType(
            id=uuid.uuid4(),
            code=code,
            name=code.capitalize(),
            is_default=True,
            is_active=True,
        )
        db_session.add(lt)
        db_session.flush()
    return lt


def _create_job(
    db_session, tenant_id: uuid.UUID, customer_id: uuid.UUID, site_id: uuid.UUID
) -> Job:
    """Create a minimal Job record for test use."""
    js = _get_or_create_job_status(db_session, "draft")
    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=js.id,
        is_active=True,
    )
    db_session.add(job)
    db_session.flush()
    return job


def _create_change_order(
    db_session,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    description: str = "Add circuits",
) -> ChangeOrder:
    co = ChangeOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        description=description,
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
        is_active=True,
    )
    db_session.add(co)
    db_session.flush()
    return co


# ============================================================
# Change Order Header Tests
# ============================================================


class TestChangeOrderCRUD:
    """Tests for POST/GET/PATCH/DELETE on the change order header."""

    def test_create_change_order_201(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Happy path: create a change order → 201 with correct fields."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        db_session.commit()

        resp = client.post(
            f"/api/v1/jobs/{job.id}/change-orders/test",
            json={"description": "Add 20A circuit for HVAC"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()

        assert body["job_id"] == str(job.id)
        assert body["tenant_id"] == str(test_tenant.id)
        assert body["description"] == "Add 20A circuit for HVAC"
        assert body["subtotal_cents"] == 0
        assert body["total_cents"] == 0
        assert body["is_active"] is True

        # Verify DB record
        co = db_session.exec(
            select(ChangeOrder).where(ChangeOrder.id == uuid.UUID(body["id"]))
        ).first()
        assert co is not None
        assert co.job_id == job.id

    def test_list_change_orders_200(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """GET list returns only active change orders for the job."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co1 = _create_change_order(db_session, test_tenant.id, job.id, "CO #1")
        co2 = _create_change_order(db_session, test_tenant.id, job.id, "CO #2")
        co_inactive = _create_change_order(
            db_session, test_tenant.id, job.id, "inactive CO"
        )
        co_inactive.is_active = False
        db_session.commit()

        resp = client.get(f"/api/v1/jobs/{job.id}/change-orders/test")
        assert resp.status_code == 200, resp.text
        ids = [item["id"] for item in resp.json()]
        assert str(co1.id) in ids
        assert str(co2.id) in ids
        assert str(co_inactive.id) not in ids

    def test_get_change_order_200(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """GET single change order returns correct data."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        db_session.commit()

        resp = client.get(f"/api/v1/jobs/{job.id}/change-orders/{co.id}/test")
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == str(co.id)
        assert resp.json()["description"] == "Add circuits"

    def test_update_change_order_200(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """PATCH description updates the record."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id, "Original scope")
        db_session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/test",
            json={"description": "Updated scope — panel upgrade"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["description"] == "Updated scope — panel upgrade"

        db_session.refresh(co)
        assert co.description == "Updated scope — panel upgrade"

    def test_delete_change_order_soft_delete(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """DELETE soft-deletes the change order (is_active=False)."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        db_session.commit()

        resp = client.delete(f"/api/v1/jobs/{job.id}/change-orders/{co.id}/test")
        assert resp.status_code == 200, resp.text
        assert "deactivated" in resp.json()["message"].lower()

        db_session.refresh(co)
        assert co.is_active is False

    def test_delete_excluded_from_list(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """After soft-delete, the CO no longer appears in the list."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id, "To be deleted")
        db_session.commit()

        client.delete(f"/api/v1/jobs/{job.id}/change-orders/{co.id}/test")

        resp = client.get(f"/api/v1/jobs/{job.id}/change-orders/test")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(co.id) not in ids

    def test_get_nonexistent_co_returns_404(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """A non-existent change order ID returns 404."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        db_session.commit()

        resp = client.get(f"/api/v1/jobs/{job.id}/change-orders/{uuid.uuid4()}/test")
        assert resp.status_code == 404, resp.text

    def test_create_co_on_nonexistent_job_returns_404(self, client, db_session):
        """Creating a change order for a non-existent job returns 404."""
        resp = client.post(
            f"/api/v1/jobs/{uuid.uuid4()}/change-orders/test",
            json={"description": "phantom job CO"},
        )
        assert resp.status_code == 404, resp.text


# ============================================================
# Change Order Line Tests
# ============================================================


class TestChangeOrderLineCRUD:
    """Tests for POST/GET/PATCH/DELETE on change order lines."""

    def test_create_line_201(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Happy path: create a line → 201, subtotal/total computed from qty × price."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        lt = _get_or_create_qco_line_type(db_session, "labor")
        db_session.commit()

        resp = client.post(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(lt.id),
                "description": "Install 20A breaker",
                "quantity": 2.0,
                "unit_price_cents": 5000,
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()

        assert body["change_order_id"] == str(co.id)
        assert body["description"] == "Install 20A breaker"
        assert body["unit_price_cents"] == 5000
        # subtotal = 2 × 5000 = 10000
        assert body["subtotal_cents"] == 10000
        assert body["total_cents"] == 10000

    def test_line_insertion_triggers_header_recalc(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        Batch 1-D Verification: inserting a line fires recalc_change_order_totals_fn
        and updates the change_order header subtotal_cents / total_cents.
        """
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        lt = _get_or_create_qco_line_type(db_session, "material")
        db_session.commit()

        assert co.subtotal_cents == 0

        client.post(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(lt.id),
                "description": "12/2 Romex 100ft",
                "quantity": 3.0,
                "unit_price_cents": 4000,
            },
        )

        db_session.refresh(co)
        # DB trigger recalc_change_order_totals_fn should have updated header
        assert co.subtotal_cents == 12000
        assert co.total_cents == 12000

    def test_list_lines_200(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """GET lines returns active lines in position order."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        lt = _get_or_create_qco_line_type(db_session, "labor")
        db_session.commit()

        # Create two lines via API
        client.post(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test",
            json={
                "position": 2,
                "qco_line_type_id": str(lt.id),
                "description": "Line B",
                "unit_price_cents": 1000,
            },
        )
        client.post(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(lt.id),
                "description": "Line A",
                "unit_price_cents": 2000,
            },
        )

        resp = client.get(f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test")
        assert resp.status_code == 200, resp.text
        lines = resp.json()
        assert len(lines) == 2
        # Should be ordered by position ascending
        positions = [l["position"] for l in lines]
        assert positions == sorted(positions)

    def test_update_line_recalcs_subtotal(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """PATCH with new quantity recalculates subtotal/total on the line."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        lt = _get_or_create_qco_line_type(db_session, "labor")
        db_session.commit()

        create_resp = client.post(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(lt.id),
                "description": "Work",
                "quantity": 1.0,
                "unit_price_cents": 10000,
            },
        )
        line_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/{line_id}/test",
            json={"quantity": 4.0},
        )
        assert patch_resp.status_code == 200, patch_resp.text
        body = patch_resp.json()
        # 4 × 10000 = 40000
        assert body["subtotal_cents"] == 40000
        assert body["total_cents"] == 40000

    def test_delete_line_soft_delete(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """DELETE line soft-deletes it (is_active=False) and removes from list."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        lt = _get_or_create_qco_line_type(db_session, "labor")
        db_session.commit()

        create_resp = client.post(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(lt.id),
                "description": "To delete",
                "unit_price_cents": 500,
            },
        )
        line_id = create_resp.json()["id"]

        del_resp = client.delete(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/{line_id}/test"
        )
        assert del_resp.status_code == 200, del_resp.text
        assert "deactivated" in del_resp.json()["message"].lower()

        # Should not appear in list anymore
        list_resp = client.get(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/test"
        )
        ids = [l["id"] for l in list_resp.json()]
        assert line_id not in ids

        # DB record has is_active = False
        line = db_session.exec(
            select(ChangeOrderLine).where(ChangeOrderLine.id == uuid.UUID(line_id))
        ).first()
        assert line is not None
        assert line.is_active is False

    def test_get_nonexistent_line_returns_404(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """A non-existent line ID on PATCH returns 404."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        co = _create_change_order(db_session, test_tenant.id, job.id)
        db_session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.id}/change-orders/{co.id}/lines/{uuid.uuid4()}/test",
            json={"description": "ghost line"},
        )
        assert resp.status_code == 404, resp.text

    def test_create_line_on_nonexistent_co_returns_404(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Creating a line on a non-existent change order returns 404."""
        job = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)
        lt = _get_or_create_qco_line_type(db_session, "labor")
        db_session.commit()

        resp = client.post(
            f"/api/v1/jobs/{job.id}/change-orders/{uuid.uuid4()}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(lt.id),
                "description": "orphan",
                "unit_price_cents": 100,
            },
        )
        assert resp.status_code == 404, resp.text


# ============================================================
# Tenant Isolation (IDOR Protection)
# ============================================================


class TestChangeOrderTenantIsolation:
    """Cross-tenant IDOR protection: foreign job/CO IDs always return 404."""

    def test_cannot_access_change_order_on_foreign_job(
        self, client, db_session, test_tenant, test_customer, test_site, tenant_b
    ):
        """
        A change order belonging to tenant_b's job is invisible to the
        test-context tenant (tenant_a / test_tenant).
        """
        from app.models.crm import Customer, Site

        # Build a minimal customer+site+job under tenant_b
        cust_b = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            display_name="Tenant B Customer",
            type="company",
            is_active=True,
        )
        db_session.add(cust_b)
        db_session.flush()

        site_b = Site(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            customer_id=cust_b.id,
            is_active=True,
        )
        db_session.add(site_b)
        db_session.flush()

        js = _get_or_create_job_status(db_session, "draft")
        job_b = Job(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            customer_id=cust_b.id,
            site_id=site_b.id,
            status_id=js.id,
            is_active=True,
        )
        db_session.add(job_b)
        db_session.flush()

        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="Tenant B private CO",
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
            is_active=True,
        )
        db_session.add(co_b)
        db_session.commit()

        # Test context authenticates as test_tenant (NOT tenant_b).
        # Accessing job_b's job_id should 404 because it belongs to tenant_b.
        resp = client.get(f"/api/v1/jobs/{job_b.id}/change-orders/test")
        assert resp.status_code == 404, resp.text

    def test_cannot_access_foreign_co_directly(
        self, client, db_session, test_tenant, test_customer, test_site, tenant_b
    ):
        """
        Even if the job_id belongs to test_tenant, a co_id from tenant_b
        returns 404 — not tenant_b's data.
        """
        job_a = _create_job(db_session, test_tenant.id, test_customer.id, test_site.id)

        # Create a CO directly under tenant_b (different job)
        js = _get_or_create_job_status(db_session, "draft")
        from app.models.crm import Customer, Site

        cust_b = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            display_name="B",
            type="company",
            is_active=True,
        )
        db_session.add(cust_b)
        db_session.flush()
        site_b = Site(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            customer_id=cust_b.id,
            is_active=True,
        )
        db_session.add(site_b)
        db_session.flush()
        job_b = Job(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            customer_id=cust_b.id,
            site_id=site_b.id,
            status_id=js.id,
            is_active=True,
        )
        db_session.add(job_b)
        db_session.flush()
        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="B CO",
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
            is_active=True,
        )
        db_session.add(co_b)
        db_session.commit()

        # Try to access co_b using job_a's ID — should 404
        resp = client.get(f"/api/v1/jobs/{job_a.id}/change-orders/{co_b.id}/test")
        assert resp.status_code == 404, resp.text
