"""
Task 1-A-4: Scheduling RBAC Permission Seed Tests

Verifies that the scheduling permission strings were correctly added to
the live tenant_user_role table via migration 7c521872b3b6.

  office_staff  → schedule.manage, schedule.view_all
  technician    → schedule.view_own
  owner         → "*" wildcard already covers all (verified as unchanged)
  accountant    → schedule.view_all only (PLP-FIX-11, INV-BUG-18, Tom-ruled
                  2026-09-06 — read-only schedule view: jobs' technician
                  assignments + read-only dispatch board; write stays
                  schedule.manage, owner/office_staff only)

Reference: dev-docs/analysis/frontend-pass-3-sched-feat-plan.md Task 1-A-4
"""

import pytest
from sqlmodel import select

from app.models.auth import TenantUserRole


class TestSchedulingRolePermissions:
    def _get_role(self, db_session, code: str) -> TenantUserRole | None:
        return db_session.exec(
            select(TenantUserRole).where(TenantUserRole.code == code)
        ).first()

    # ------------------------------------------------------------------
    # office_staff
    # ------------------------------------------------------------------

    def test_office_staff_has_schedule_manage(self, db_session):
        """office_staff must have schedule.manage permission."""
        role = self._get_role(db_session, "office_staff")
        assert role is not None, "office_staff role not found"
        assert "schedule.manage" in role.permissions, (
            f"Expected 'schedule.manage' in office_staff.permissions; got: {role.permissions}"
        )

    def test_office_staff_has_schedule_view_all(self, db_session):
        """office_staff must have schedule.view_all permission."""
        role = self._get_role(db_session, "office_staff")
        assert role is not None, "office_staff role not found"
        assert "schedule.view_all" in role.permissions, (
            f"Expected 'schedule.view_all' in office_staff.permissions; got: {role.permissions}"
        )

    def test_office_staff_does_not_have_schedule_view_own(self, db_session):
        """office_staff should NOT have the narrow schedule.view_own (they have view_all)."""
        role = self._get_role(db_session, "office_staff")
        assert role is not None, "office_staff role not found"
        assert "schedule.view_own" not in role.permissions, (
            "office_staff should use schedule.view_all, not schedule.view_own"
        )

    # ------------------------------------------------------------------
    # technician
    # ------------------------------------------------------------------

    def test_technician_has_schedule_view_own(self, db_session):
        """technician must have schedule.view_own permission."""
        role = self._get_role(db_session, "technician")
        assert role is not None, "technician role not found"
        assert "schedule.view_own" in role.permissions, (
            f"Expected 'schedule.view_own' in technician.permissions; got: {role.permissions}"
        )

    def test_technician_does_not_have_schedule_manage(self, db_session):
        """technician must NOT have schedule.manage (owner/office_staff only)."""
        role = self._get_role(db_session, "technician")
        assert role is not None, "technician role not found"
        assert "schedule.manage" not in role.permissions, (
            "technician should NOT have schedule.manage"
        )

    def test_technician_does_not_have_schedule_view_all(self, db_session):
        """technician must NOT have schedule.view_all (can only see own schedule)."""
        role = self._get_role(db_session, "technician")
        assert role is not None, "technician role not found"
        assert "schedule.view_all" not in role.permissions, (
            "technician should NOT have schedule.view_all"
        )

    # ------------------------------------------------------------------
    # owner — wildcard covers everything
    # ------------------------------------------------------------------

    def test_owner_has_wildcard_permission(self, db_session):
        """owner role must retain its wildcard '*' permission."""
        role = self._get_role(db_session, "owner")
        assert role is not None, "owner role not found"
        assert "*" in role.permissions, (
            f"Expected '*' wildcard in owner.permissions; got: {role.permissions}"
        )

    # ------------------------------------------------------------------
    # accountant — schedule.view_all only (PLP-FIX-11 reversal)
    # ------------------------------------------------------------------

    def test_accountant_has_schedule_view_all_only(self, db_session):
        """accountant has exactly {schedule.view_all} — no manage, no view_own.

        PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): accountant gains
        read-only schedule view. This reverses the 1E-era invariant that
        asserted zero schedule.* permissions for accountant.
        """
        role = self._get_role(db_session, "accountant")
        if role is None:
            pytest.skip("accountant role not present in this environment")
        schedule_perms = {p for p in role.permissions if p.startswith("schedule.")}
        assert schedule_perms == {"schedule.view_all"}, (
            f"accountant should have exactly {{'schedule.view_all'}}; "
            f"got: {schedule_perms}"
        )

    # ------------------------------------------------------------------
    # Idempotency: applying upgrade twice should not duplicate entries
    # ------------------------------------------------------------------

    def test_office_staff_no_duplicate_schedule_manage(self, db_session):
        """schedule.manage must appear exactly once in office_staff.permissions."""
        role = self._get_role(db_session, "office_staff")
        assert role is not None
        count = role.permissions.count("schedule.manage")
        assert count == 1, (
            f"Expected exactly 1 'schedule.manage' in office_staff; found {count}"
        )

    def test_office_staff_no_duplicate_schedule_view_all(self, db_session):
        """schedule.view_all must appear exactly once in office_staff.permissions."""
        role = self._get_role(db_session, "office_staff")
        assert role is not None
        count = role.permissions.count("schedule.view_all")
        assert count == 1, (
            f"Expected exactly 1 'schedule.view_all' in office_staff; found {count}"
        )

    def test_technician_no_duplicate_schedule_view_own(self, db_session):
        """schedule.view_own must appear exactly once in technician.permissions."""
        role = self._get_role(db_session, "technician")
        assert role is not None
        count = role.permissions.count("schedule.view_own")
        assert count == 1, (
            f"Expected exactly 1 'schedule.view_own' in technician; found {count}"
        )
