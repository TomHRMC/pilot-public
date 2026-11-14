"""
CP-5: Dunning Cycle (SD-10 E2E Tier 1)

Tests the enhanced dunning task (SD-06B) end-to-end:
1. Overdue invoice gets reminder_count incremented when _dunning_reminders_impl is called
2. Recently-reminded invoice is skipped on second consecutive run (throttle)
3. Paid invoice is NOT dunned

The impl is called directly (not .delay()) — unit test pattern for testability.
No real email/SMS sent — outbox enqueuing only (MockCarrier).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

pytestmark = [pytest.mark.e2e]


def _get_invoice_state(engine, invoice_id: str) -> dict:
    """Helper: fetch invoice.reminder_count and invoice.last_reminder_sent_at from E2E DB."""
    from app.models.billing import Invoice

    with Session(engine) as db:
        inv = db.exec(select(Invoice).where(Invoice.id == invoice_id)).first()
        if inv is None:
            return {}
        return {
            "reminder_count": inv.reminder_count,
            "last_reminder_sent_at": inv.last_reminder_sent_at,
            "status_code": getattr(inv, "status_code", None),
        }


class TestDunningCycle:
    """Dunning task end-to-end tests against pilot_e2e_db."""

    def test_dunning_increments_reminder_count_on_overdue_invoice(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        1. Create a customer + invoice that is 3 days overdue (due_at = now - 3 days)
        2. Run _dunning_reminders_impl directly against the E2E DB session
        3. Assert: invoice.reminder_count == 1 (was 0)
        4. Assert: invoice.last_reminder_sent_at IS NOT NULL

        The impl function uses the owner's created_by field to find the notification recipient.
        We set up the invoice so its tenant has created_by = the seeded owner user.
        """
        from tasks.dunning import _dunning_reminders_impl

        unique = uuid.uuid4().hex[:8]

        # ── Setup: create customer + site ─────────────────────────────────────
        cust_resp = e2e_client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"E2E-Dunning-{unique}",
                "first_name": "E2E",
                "last_name": f"Dunning-{unique}",
                "customer_type": "person",
                "lifecycle_status_code": "active",
            },
        )
        assert cust_resp.status_code == 201, (
            f"Customer creation failed: {cust_resp.status_code} {cust_resp.text[:200]}"
        )
        customer_id = cust_resp.json()["id"]

        # Site is required for invoice.site_id NOT NULL constraint
        site_resp = e2e_client.post(
            "/api/v1/sites/test",
            json={
                "customer_id": customer_id,
                "site_name": f"E2E Dunning Site {unique}",
                "is_active": True,
            },
        )
        assert site_resp.status_code == 201, (
            f"Site creation failed: {site_resp.status_code} {site_resp.text[:200]}"
        )
        site_id = uuid.UUID(site_resp.json()["id"])

        # ── Setup: create invoice that is 3 days overdue ─────────────────────
        # Use the /test endpoint to create the invoice with overdue due_at
        from app.models.billing import Invoice, InvoiceStatus

        # Directly insert the invoice into the E2E DB with past due_at
        # We need a status that is not 'paid' — find the seeded 'issued' status
        TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
        OWNER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

        overdue_invoice_id = uuid.uuid4()
        due_at = datetime.now(UTC) - timedelta(days=3)

        with Session(e2e_engine) as db:
            # Find an issued/sent invoice status (not paid, not draft)
            # invoice_status rows are global (tenant_id IS NULL)
            issued_status = db.exec(
                select(InvoiceStatus).where(
                    InvoiceStatus.tenant_id.is_(None),
                    InvoiceStatus.code.in_(["issued", "sent", "overdue"]),
                )
            ).first()

            if issued_status is None:
                # Fall back to any non-paid status
                issued_status = db.exec(
                    select(InvoiceStatus).where(
                        InvoiceStatus.tenant_id.is_(None),
                    )
                ).first()

            assert issued_status is not None, (
                "At least one InvoiceStatus must be seeded in E2E DB for test_tenant"
            )

            invoice = Invoice(
                id=overdue_invoice_id,
                tenant_id=TEST_TENANT_ID,
                customer_id=uuid.UUID(customer_id),
                site_id=site_id,
                status_id=issued_status.id,
                invoice_number=f"E2E-DUN-{unique}",
                due_at=due_at,
                subtotal_cents=10000,
                tax_cents=0,
                total_cents=10000,
                balance_due_cents=10000,  # Still owed — triggers dunning
                reminder_count=0,
                last_reminder_sent_at=None,
                is_active=True,
            )
            db.add(invoice)
            db.commit()

        # ── Run dunning impl ─────────────────────────────────────────────────
        with Session(e2e_engine) as db:
            # Patch SMS/email to prevent real sends during dunning run
            with (
                patch("tasks.dunning._enqueue_customer_sms"),
                patch("tasks.dunning._get_customer_primary_phone", return_value=None),
            ):
                result = _dunning_reminders_impl(db)

        # The impl should have processed at least our overdue invoice
        assert result["overdue_invoices"] >= 1, (
            f"_dunning_reminders_impl should process >= 1 overdue invoice, "
            f"got: {result}"
        )

        # ── Assert invoice state ──────────────────────────────────────────────
        inv_state = _get_invoice_state(e2e_engine, str(overdue_invoice_id))
        assert inv_state, f"Invoice {overdue_invoice_id} not found in E2E DB"
        assert inv_state["reminder_count"] == 1, (
            f"Invoice reminder_count must be 1 after dunning run, "
            f"got: {inv_state['reminder_count']}"
        )
        assert inv_state["last_reminder_sent_at"] is not None, (
            "Invoice last_reminder_sent_at must be set after dunning run"
        )

    def test_dunning_skips_recently_reminded_invoice(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        An invoice that was reminded < 23 hours ago must NOT be dunned again.
        Verifies the throttle logic in _dunning_reminders_impl.
        """
        from app.models.billing import Invoice, InvoiceStatus
        from tasks.dunning import _dunning_reminders_impl

        unique = uuid.uuid4().hex[:8]
        TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

        cust_resp = e2e_client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"E2E-Throttle-{unique}",
                "first_name": "E2E",
                "last_name": f"Throttle-{unique}",
                "customer_type": "person",
                "lifecycle_status_code": "active",
            },
        )
        assert cust_resp.status_code == 201
        customer_id = cust_resp.json()["id"]

        # Site required for invoice NOT NULL constraint
        site_resp = e2e_client.post(
            "/api/v1/sites/test",
            json={
                "customer_id": customer_id,
                "site_name": f"E2E Throttle Site {unique}",
                "is_active": True,
            },
        )
        assert site_resp.status_code == 201
        site_id = uuid.UUID(site_resp.json()["id"])

        # Create an invoice that was reminded 1 hour ago (below 23h throttle)
        recently_reminded_id = uuid.uuid4()
        due_at = datetime.now(UTC) - timedelta(days=3)
        last_reminded = datetime.now(UTC) - timedelta(hours=1)

        with Session(e2e_engine) as db:
            # invoice_status rows are global (tenant_id IS NULL)
            issued_status = db.exec(
                select(InvoiceStatus).where(
                    InvoiceStatus.tenant_id.is_(None),
                )
            ).first()
            assert issued_status is not None

            invoice = Invoice(
                id=recently_reminded_id,
                tenant_id=TEST_TENANT_ID,
                customer_id=uuid.UUID(customer_id),
                site_id=site_id,
                status_id=issued_status.id,
                invoice_number=f"E2E-THROT-{unique}",
                due_at=due_at,
                subtotal_cents=10000,
                tax_cents=0,
                total_cents=10000,
                balance_due_cents=10000,
                reminder_count=1,
                last_reminder_sent_at=last_reminded,  # reminded 1 hour ago
                is_active=True,
            )
            db.add(invoice)
            db.commit()

        # Capture reminder_count BEFORE running dunning
        before_state = _get_invoice_state(e2e_engine, str(recently_reminded_id))
        assert before_state["reminder_count"] == 1

        # Run dunning impl — our invoice should be SKIPPED due to throttle
        with Session(e2e_engine) as db:
            with (
                patch("tasks.dunning._enqueue_customer_sms"),
                patch("tasks.dunning._get_customer_primary_phone", return_value=None),
            ):
                _dunning_reminders_impl(db)

        # Assert: reminder_count unchanged (still 1, not 2)
        after_state = _get_invoice_state(e2e_engine, str(recently_reminded_id))
        assert after_state["reminder_count"] == before_state["reminder_count"], (
            f"Recently-reminded invoice MUST be skipped (throttle). "
            f"reminder_count went from {before_state['reminder_count']} "
            f"to {after_state['reminder_count']}"
        )

    def test_dunning_skips_zero_balance_invoice(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        An invoice with balance_due_cents = 0 (paid) must NOT be dunned.
        Verifies the WHERE balance_due_cents > 0 filter in the dunning query.
        """
        from app.models.billing import Invoice, InvoiceStatus
        from tasks.dunning import _dunning_reminders_impl

        unique = uuid.uuid4().hex[:8]
        TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

        cust_resp = e2e_client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"E2E-Paid-{unique}",
                "first_name": "E2E",
                "last_name": f"Paid-{unique}",
                "customer_type": "person",
                "lifecycle_status_code": "active",
            },
        )
        assert cust_resp.status_code == 201
        customer_id = cust_resp.json()["id"]

        # Site required for invoice NOT NULL constraint
        site_resp = e2e_client.post(
            "/api/v1/sites/test",
            json={
                "customer_id": customer_id,
                "site_name": f"E2E Paid Site {unique}",
                "is_active": True,
            },
        )
        assert site_resp.status_code == 201
        site_id = uuid.UUID(site_resp.json()["id"])

        # Create an overdue but PAID invoice (balance_due_cents = 0)
        paid_invoice_id = uuid.uuid4()
        due_at = datetime.now(UTC) - timedelta(days=5)

        with Session(e2e_engine) as db:
            # invoice_status rows are global (tenant_id IS NULL)
            issued_status = db.exec(
                select(InvoiceStatus).where(
                    InvoiceStatus.tenant_id.is_(None),
                )
            ).first()
            assert issued_status is not None

            invoice = Invoice(
                id=paid_invoice_id,
                tenant_id=TEST_TENANT_ID,
                customer_id=uuid.UUID(customer_id),
                site_id=site_id,
                status_id=issued_status.id,
                invoice_number=f"E2E-PAID-{unique}",
                due_at=due_at,
                subtotal_cents=10000,
                tax_cents=0,
                total_cents=10000,
                balance_due_cents=0,  # PAID — must not be dunned
                reminder_count=0,
                last_reminder_sent_at=None,
                is_active=True,
            )
            db.add(invoice)
            db.commit()

        before_state = _get_invoice_state(e2e_engine, str(paid_invoice_id))
        assert before_state["reminder_count"] == 0

        # Run dunning impl
        with Session(e2e_engine) as db:
            with (
                patch("tasks.dunning._enqueue_customer_sms"),
                patch("tasks.dunning._get_customer_primary_phone", return_value=None),
            ):
                _dunning_reminders_impl(db)

        after_state = _get_invoice_state(e2e_engine, str(paid_invoice_id))
        assert after_state["reminder_count"] == 0, (
            f"Paid invoice (balance_due_cents=0) must NOT be dunned. "
            f"reminder_count went from 0 to {after_state['reminder_count']}"
        )
