"""Role-grant seed changes: grant matrix + converge idempotency.

Verifies that the ``TENANT_USER_ROLE_ROWS`` seed definition in
``migrations/scripts/seed_core.py`` grants the correct permissions to each
non-owner role, and that the converge UPDATE block is idempotent and
value-scoped (only ``permissions`` + ``updated_at`` may change on existing rows).

Covers:
- INV-D-5: office_staff gains ``communications.view`` / ``communications.send``
  (NOT ``communications.manage`` — design §G.1, owner-only thread lifecycle admin).
- INV-BUG-8: every non-owner role gains the four self-service Security-page
  codes (``mfa.enroll_self``, ``account.session.view_own``,
  ``account.session.revoke_own``, ``help_chat.delete_own_history``).
- PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): accountant gains
  ``schedule.view_all`` (read-only schedule view — jobs' technician assignments
  + read-only dispatch board). ``schedule.manage`` and ``schedule.view_own``
  are NOT granted (write stays owner/office_staff; view_own is technician-scoped).
"""

import json

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.models.auth import TenantUserRole
from migrations.scripts.seed_core import TENANT_USER_ROLE_ROWS

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SELF_SERVICE_CODES = [
    "mfa.enroll_self",
    "account.session.view_own",
    "account.session.revoke_own",
    "help_chat.delete_own_history",
]


def _role_row(code: str) -> dict:
    """Return the seed-definition dict for *code* from TENANT_USER_ROLE_ROWS."""
    for row in TENANT_USER_ROLE_ROWS:
        if row["code"] == code:
            return row
    raise KeyError(f"Role '{code}' not found in TENANT_USER_ROLE_ROWS")


# ---------------------------------------------------------------------------
# Seed-definition (array) tests — pure data, no DB needed
# ---------------------------------------------------------------------------


class TestRoleGrantMatrix:
    """Verify the permissions arrays in TENANT_USER_ROLE_ROWS match design §B.1."""

    def test_office_staff_has_communications_grants(self):
        """office_staff contains communications.view + communications.send,
        and does NOT contain communications.manage (design §G.1)."""
        perms = _role_row("office_staff")["permissions"]
        assert "communications.view" in perms
        assert "communications.send" in perms
        assert "communications.manage" not in perms

    def test_all_non_owner_roles_have_self_service_security_grants(self):
        """office_staff, technician, accountant each contain all four
        self-service Security-page codes (INV-BUG-8)."""
        for code in ("office_staff", "technician", "accountant"):
            perms = _role_row(code)["permissions"]
            for expected in _SELF_SERVICE_CODES:
                assert expected in perms, (
                    f"Role '{code}' is missing self-service grant '{expected}'"
                )

    def test_owner_unchanged_wildcard(self):
        """owner still starts with '*' and gains none of the new literal codes
        (the wildcard matches them implicitly)."""
        perms = _role_row("owner")["permissions"]
        assert perms[0] == "*"
        for code in (
            "communications.view",
            "communications.send",
            "communications.manage",
            *_SELF_SERVICE_CODES,
        ):
            assert code not in perms, (
                f"owner should rely on wildcard, not literal '{code}'"
            )

    def test_communications_manage_absent_everywhere(self):
        """communications.manage is deliberately absent from ALL non-owner roles
        (design §G.1 — thread lifecycle admin stays owner-only)."""
        for code in ("office_staff", "technician", "accountant"):
            perms = _role_row(code)["permissions"]
            assert "communications.manage" not in perms


class TestPlpFix11AccountantScheduleGrant:
    """PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): accountant gains
    ``schedule.view_all`` (read-only schedule view). ``schedule.manage`` and
    ``schedule.view_own`` are NOT granted."""

    def test_accountant_has_schedule_view_all(self):
        """accountant permissions array contains schedule.view_all."""
        perms = _role_row("accountant")["permissions"]
        assert "schedule.view_all" in perms, (
            "accountant should have schedule.view_all (PLP-FIX-11 ruling)"
        )

    def test_accountant_does_not_have_schedule_manage(self):
        """accountant must NOT have schedule.manage (write stays owner/office_staff)."""
        perms = _role_row("accountant")["permissions"]
        assert "schedule.manage" not in perms, (
            "accountant should NOT have schedule.manage (write stays "
            "owner/office_staff — design §G-Q3)"
        )

    def test_accountant_does_not_have_schedule_view_own(self):
        """accountant must NOT have schedule.view_own (technician-scoped key)."""
        perms = _role_row("accountant")["permissions"]
        assert "schedule.view_own" not in perms, (
            "accountant should NOT have schedule.view_own (technician-scoped — "
            "design §G-Q6)"
        )

    def test_office_staff_still_has_both_schedule_keys(self):
        """office_staff still holds schedule.view_all + schedule.manage
        (guard against array-edit accidents)."""
        perms = _role_row("office_staff")["permissions"]
        assert "schedule.view_all" in perms
        assert "schedule.manage" in perms

    def test_technician_still_has_view_own_not_view_all(self):
        """technician still holds schedule.view_own and NOT schedule.view_all
        (the grant didn't leak)."""
        perms = _role_row("technician")["permissions"]
        assert "schedule.view_own" in perms
        assert "schedule.view_all" not in perms


# ---------------------------------------------------------------------------
# DB converge tests — use db_session fixture (auto-rollback)
# ---------------------------------------------------------------------------


class TestConvergeIdempotency:
    """Verify the converge UPDATE block is idempotent and value-scoped."""

    def test_converge_heals_db_rows(self, db_session: Session):
        """Running the converge UPDATE once brings each role's DB permissions
        in line with the seed definition (new codes present)."""
        for row in TENANT_USER_ROLE_ROWS:
            permissions_json = json.dumps(row["permissions"])
            db_session.execute(
                text("""
                    UPDATE public.tenant_user_role
                    SET permissions = CAST(:permissions AS jsonb), updated_at = now()
                    WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
                """),
                {"code": row["code"], "permissions": permissions_json},
            )
        db_session.commit()

        # Verify new codes present per role
        db_session.expire_all()
        office = db_session.exec(
            select(TenantUserRole).where(TenantUserRole.code == "office_staff")
        ).first()
        assert office is not None
        assert "communications.send" in office.permissions
        assert "mfa.enroll_self" in office.permissions

        for code in ("office_staff", "technician", "accountant"):
            role = db_session.exec(
                select(TenantUserRole).where(TenantUserRole.code == code)
            ).first()
            assert role is not None
            for expected in _SELF_SERVICE_CODES:
                assert expected in role.permissions, (
                    f"Role '{code}' DB row missing '{expected}' after converge"
                )

    def test_converge_is_idempotent(self, db_session: Session):
        """Running the converge UPDATE a second time updates 0 rows (no-op)."""
        # First pass — converge to seed truth
        for row in TENANT_USER_ROLE_ROWS:
            permissions_json = json.dumps(row["permissions"])
            db_session.execute(
                text("""
                    UPDATE public.tenant_user_role
                    SET permissions = CAST(:permissions AS jsonb), updated_at = now()
                    WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
                """),
                {"code": row["code"], "permissions": permissions_json},
            )
        db_session.commit()

        # Second pass — must be a no-op for every role
        total_updated = 0
        for row in TENANT_USER_ROLE_ROWS:
            permissions_json = json.dumps(row["permissions"])
            result = db_session.execute(
                text("""
                    UPDATE public.tenant_user_role
                    SET permissions = CAST(:permissions AS jsonb), updated_at = now()
                    WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
                """),
                {"code": row["code"], "permissions": permissions_json},
            )
            total_updated += result.rowcount
        db_session.commit()

        assert total_updated == 0, (
            f"Second converge pass should be a no-op (0 rows updated), "
            f"but {total_updated} row(s) were updated — permissions not stable"
        )

    def test_only_permissions_and_updated_at_change(self, db_session: Session):
        """Converge must not alter name/description/is_default/is_active
        (FIX-7 §C.1 standing rule)."""
        # Snapshot pre-converge state of all four roles
        pre_rows = {}
        for row in TENANT_USER_ROLE_ROWS:
            db_row = db_session.exec(
                select(TenantUserRole).where(TenantUserRole.code == row["code"])
            ).first()
            assert db_row is not None
            pre_rows[row["code"]] = {
                "name": db_row.name,
                "description": db_row.description,
                "is_default": db_row.is_default,
                "is_active": db_row.is_active,
            }

        # Run converge
        for row in TENANT_USER_ROLE_ROWS:
            permissions_json = json.dumps(row["permissions"])
            db_session.execute(
                text("""
                    UPDATE public.tenant_user_role
                    SET permissions = CAST(:permissions AS jsonb), updated_at = now()
                    WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
                """),
                {"code": row["code"], "permissions": permissions_json},
            )
        db_session.commit()

        # Verify non-permission columns are byte-identical
        db_session.expire_all()
        for code, pre in pre_rows.items():
            db_row = db_session.exec(
                select(TenantUserRole).where(TenantUserRole.code == code)
            ).first()
            assert db_row is not None
            assert db_row.name == pre["name"], f"name changed for '{code}'"
            assert db_row.description == pre["description"], (
                f"description changed for '{code}'"
            )
            assert db_row.is_default == pre["is_default"], (
                f"is_default changed for '{code}'"
            )
            assert db_row.is_active == pre["is_active"], (
                f"is_active changed for '{code}'"
            )
