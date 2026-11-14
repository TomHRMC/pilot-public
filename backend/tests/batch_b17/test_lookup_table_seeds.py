"""
FIND-167 (S1 Critical) — Lookup table seed verification tests.

Verifies that the 4 previously-empty lookup tables now contain the correct
system-level seed rows after migration 9f8116bb6ad1.

Test plan from remediation plan FIND-167:
  - invoice_status: assert 5 rows; draft is_default=true; paid is_terminal=true
  - payment_status: assert 4 rows; pending is_default=true; succeeded is_terminal=true
  - payment_type: assert 6 rows; card, ach, venmo all is_active=true
  - qco_line_type: assert 4 rows (labor, material, misc, discount);
                   labor is_default=true; names are NOT corrupt address names

Test subfolder: tests/batch_b17/
"""

from sqlmodel import select

from app.models.billing import InvoiceStatus, PaymentStatus, PaymentType
from app.models.quoting import QcoLineType


class TestInvoiceStatusSeeds:
    """invoice_status must have 6 system rows (tenant_id IS NULL) after SD-2 adds 'partial'."""

    def test_invoice_status_has_5_system_rows(self, db_session):
        # SD-2: 'partial' added → 6 rows total (test name kept for backward compat)
        rows = db_session.exec(
            select(InvoiceStatus).where(InvoiceStatus.tenant_id == None)
        ).all()
        assert len(rows) == 6, (
            f"Expected 6 invoice_status rows (draft, issued, paid, void, writeoff, partial), "
            f"found {len(rows)}. SD-2 migration may not have run."
        )

    def test_invoice_status_draft_is_default(self, db_session):
        draft = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "draft")
        ).first()
        assert draft is not None, "invoice_status 'draft' row not found"
        assert draft.is_default is True, "'draft' must have is_default=True"
        assert draft.is_terminal is False, "'draft' must not be terminal"
        assert draft.is_active is True

    def test_invoice_status_paid_is_terminal(self, db_session):
        paid = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "paid")
        ).first()
        assert paid is not None, "invoice_status 'paid' row not found"
        assert paid.is_terminal is True, "'paid' must have is_terminal=True"
        assert paid.is_default is False

    def test_invoice_status_terminal_states(self, db_session):
        """paid, void, writeoff must all be terminal."""
        terminal_codes = {"paid", "void", "writeoff"}
        rows = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.is_terminal == True)
        ).all()
        found_codes = {r.code for r in rows}
        assert found_codes == terminal_codes, (
            f"Terminal invoice statuses mismatch. Expected {terminal_codes}, got {found_codes}"
        )

    def test_invoice_status_all_codes_present(self, db_session):
        # SD-2: 'partial' added
        rows = db_session.exec(
            select(InvoiceStatus).where(InvoiceStatus.tenant_id == None)
        ).all()
        found_codes = {r.code for r in rows}
        expected_codes = {"draft", "issued", "paid", "void", "writeoff", "partial"}
        assert found_codes == expected_codes


class TestPaymentStatusSeeds:
    """payment_status must have 5 system rows (tenant_id IS NULL) after SD-2 adds 'refunded'."""

    def test_payment_status_has_4_system_rows(self, db_session):
        # SD-2: 'refunded' added → 5 rows total (test name kept for backward compat)
        rows = db_session.exec(
            select(PaymentStatus).where(PaymentStatus.tenant_id == None)
        ).all()
        assert len(rows) == 5, (
            f"Expected 5 payment_status rows (pending, succeeded, failed, canceled, refunded), "
            f"found {len(rows)}. SD-2 migration may not have run."
        )

    def test_payment_status_pending_is_default(self, db_session):
        pending = db_session.exec(
            select(PaymentStatus)
            .where(PaymentStatus.tenant_id == None)
            .where(PaymentStatus.code == "pending")
        ).first()
        assert pending is not None, "payment_status 'pending' row not found"
        assert pending.is_default is True, "'pending' must have is_default=True"
        assert pending.is_terminal is False

    def test_payment_status_succeeded_is_terminal(self, db_session):
        succeeded = db_session.exec(
            select(PaymentStatus)
            .where(PaymentStatus.tenant_id == None)
            .where(PaymentStatus.code == "succeeded")
        ).first()
        assert succeeded is not None, "payment_status 'succeeded' row not found"
        assert succeeded.is_terminal is True, "'succeeded' must have is_terminal=True"

    def test_payment_status_terminal_states(self, db_session):
        """succeeded, failed, canceled, refunded must all be terminal (SD-2 adds refunded)."""
        terminal_codes = {"succeeded", "failed", "canceled", "refunded"}
        rows = db_session.exec(
            select(PaymentStatus)
            .where(PaymentStatus.tenant_id == None)
            .where(PaymentStatus.is_terminal == True)
        ).all()
        found_codes = {r.code for r in rows}
        assert found_codes == terminal_codes

    def test_payment_status_all_codes_present(self, db_session):
        # SD-2: 'refunded' added
        rows = db_session.exec(
            select(PaymentStatus).where(PaymentStatus.tenant_id == None)
        ).all()
        found_codes = {r.code for r in rows}
        expected_codes = {"pending", "succeeded", "failed", "canceled", "refunded"}
        assert found_codes == expected_codes


class TestPaymentTypeSeeds:
    """payment_type must have 6 system rows (tenant_id IS NULL)."""

    def test_payment_type_has_6_system_rows(self, db_session):
        rows = db_session.exec(
            select(PaymentType).where(PaymentType.tenant_id == None)
        ).all()
        assert len(rows) == 6, f"Expected 6 payment_type rows, found {len(rows)}."

    def test_payment_type_card_is_active(self, db_session):
        card = db_session.exec(
            select(PaymentType)
            .where(PaymentType.tenant_id == None)
            .where(PaymentType.code == "card")
        ).first()
        assert card is not None, "payment_type 'card' row not found"
        assert card.is_active is True

    def test_payment_type_ach_is_active(self, db_session):
        ach = db_session.exec(
            select(PaymentType)
            .where(PaymentType.tenant_id == None)
            .where(PaymentType.code == "ach")
        ).first()
        assert ach is not None, "payment_type 'ach' row not found"
        assert ach.is_active is True

    def test_payment_type_venmo_is_active(self, db_session):
        venmo = db_session.exec(
            select(PaymentType)
            .where(PaymentType.tenant_id == None)
            .where(PaymentType.code == "venmo")
        ).first()
        assert venmo is not None, "payment_type 'venmo' row not found"
        assert venmo.is_active is True

    def test_payment_type_all_codes_present(self, db_session):
        rows = db_session.exec(
            select(PaymentType).where(PaymentType.tenant_id == None)
        ).all()
        found_codes = {r.code for r in rows}
        expected_codes = {
            "card",
            "ach",
            "wallet",
            "bank_debit",
            "manual_check",
            "venmo",
        }
        assert found_codes == expected_codes

    def test_payment_type_all_active(self, db_session):
        rows = db_session.exec(
            select(PaymentType)
            .where(PaymentType.tenant_id == None)
            .where(PaymentType.is_active == False)
        ).all()
        assert len(rows) == 0, (
            f"All payment_type rows should be active; found inactive: {[r.code for r in rows]}"
        )


class TestQcoLineTypeSeeds:
    """qco_line_type must have 5 system rows with correct non-corrupt names (SD-2 adds 'note')."""

    # Corrupt names that previously existed in schema JSON (copy-paste error of address names).
    # These must NOT appear in the seeded rows.
    CORRUPT_NAMES = {
        "billing",
        "shipping",
        "service",
        "mailing",
        "site",
        "home",
        "billing address",
        "shipping address",
        "service address",
    }

    def test_qco_line_type_has_4_system_rows(self, db_session):
        # SD-2: 'note' added → 5 rows total (test name kept for backward compat)
        rows = db_session.exec(
            select(QcoLineType).where(QcoLineType.tenant_id == None)
        ).all()
        assert len(rows) == 5, (
            f"Expected 5 qco_line_type rows (labor, material, misc, discount, note), "
            f"found {len(rows)}. SD-2 migration may not have run."
        )

    def test_qco_line_type_labor_is_default(self, db_session):
        labor = db_session.exec(
            select(QcoLineType)
            .where(QcoLineType.tenant_id == None)
            .where(QcoLineType.code == "labor")
        ).first()
        assert labor is not None, "qco_line_type 'labor' row not found"
        assert labor.is_default is True, "'labor' must have is_default=True"
        assert labor.name == "Labor", f"Expected name='Labor', got '{labor.name}'"

    def test_qco_line_type_other_rows_not_default(self, db_session):
        """Only 'labor' should be default — material, misc, discount must be non-default."""
        non_default_codes = {"material", "misc", "discount"}
        rows = db_session.exec(
            select(QcoLineType)
            .where(QcoLineType.tenant_id == None)
            .where(QcoLineType.code.in_(list(non_default_codes)))  # type: ignore[union-attr]
        ).all()
        for row in rows:
            assert row.is_default is False, (
                f"qco_line_type '{row.code}' should not be default (only 'labor' is default)"
            )

    def test_qco_line_type_all_codes_present(self, db_session):
        # SD-2: 'note' added
        rows = db_session.exec(
            select(QcoLineType).where(QcoLineType.tenant_id == None)
        ).all()
        found_codes = {r.code for r in rows}
        expected_codes = {"labor", "material", "misc", "discount", "note"}
        assert found_codes == expected_codes

    def test_qco_line_type_names_not_corrupt(self, db_session):
        """FIND-167: schema JSON had corrupt address names; verify they are NOT seeded."""
        rows = db_session.exec(
            select(QcoLineType).where(QcoLineType.tenant_id == None)
        ).all()
        for row in rows:
            assert row.name.lower() not in self.CORRUPT_NAMES, (
                f"qco_line_type '{row.code}' has corrupt address name '{row.name}'. "
                "FIND-167 seed migration used correct names (Labor, Material, Misc, Discount)."
            )

    def test_qco_line_type_correct_names(self, db_session):
        """Explicit name assertion per FIND-167 authoritative spec."""
        expected = {
            "labor": "Labor",
            "material": "Material",
            "misc": "Misc",
            "discount": "Discount",
        }
        rows = db_session.exec(
            select(QcoLineType).where(QcoLineType.tenant_id == None)
        ).all()
        found = {r.code: r.name for r in rows}
        for code, expected_name in expected.items():
            assert code in found, f"qco_line_type code '{code}' not found"
            assert found[code] == expected_name, (
                f"qco_line_type '{code}' name mismatch: expected '{expected_name}', got '{found[code]}'"
            )

    def test_qco_line_type_all_active(self, db_session):
        rows = db_session.exec(
            select(QcoLineType)
            .where(QcoLineType.tenant_id == None)
            .where(QcoLineType.is_active == False)
        ).all()
        assert len(rows) == 0, (
            f"All qco_line_type rows should be active; found inactive: {[r.code for r in rows]}"
        )
