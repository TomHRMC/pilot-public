"""
FIND-128 (S2 High) — Technician role: add voice.create, voice.view,
mobile_sync.view, mobile_sync.resolve permissions.

Verifies that the technician role in `tenant_user_role` now contains the
4 permissions required for field technicians to use voice AI and mobile sync
after migration f80aca00dc97.

Test plan from remediation plan FIND-128:
  - Assert technician role has all 4 new permissions:
      voice.create, voice.view, mobile_sync.view, mobile_sync.resolve
  - Assert nec.calculate is still present (regression guard — must not be removed)
  - Assert technician user can hit POST /api/v1/voice/sessions without 403

Implementation note: The plan references `platform_role`, but the actual live
RBAC table is `tenant_user_role`. Tests target `tenant_user_role`.

Test subfolder: tests/batch_b17/
"""

import uuid
from unittest.mock import patch

from sqlalchemy import text
from sqlmodel import Session


class TestTechnicianRolePermissionsSeeded:
    """
    FIND-128: Technician role must include voice.create, voice.view,
    mobile_sync.view, mobile_sync.resolve after migration f80aca00dc97.
    """

    def _get_technician_permissions(self, db_session: Session) -> list[str]:
        """Return the technician role permissions as a list of strings."""
        result = db_session.execute(
            text("""
                SELECT jsonb_array_elements_text(permissions) AS perm
                FROM tenant_user_role
                WHERE code = 'technician'
            """)
        ).fetchall()
        return [row[0] for row in result]

    def test_technician_has_voice_create(self, db_session: Session):
        perms = self._get_technician_permissions(db_session)
        assert "voice.create" in perms, (
            "Technician role missing voice.create — field techs cannot start voice sessions. "
            "FIND-128 migration f80aca00dc97 must have applied."
        )

    def test_technician_has_voice_view(self, db_session: Session):
        perms = self._get_technician_permissions(db_session)
        assert "voice.view" in perms, (
            "Technician role missing voice.view — field techs cannot list/resume voice sessions."
        )

    def test_technician_has_mobile_sync_view(self, db_session: Session):
        perms = self._get_technician_permissions(db_session)
        assert "mobile_sync.view" in perms, (
            "Technician role missing mobile_sync.view — field techs cannot check sync queue status."
        )

    def test_technician_has_mobile_sync_resolve(self, db_session: Session):
        perms = self._get_technician_permissions(db_session)
        assert "mobile_sync.resolve" in perms, (
            "Technician role missing mobile_sync.resolve — field techs cannot resolve their own sync conflicts."
        )

    def test_technician_still_has_nec_calculate(self, db_session: Session):
        """
        Regression guard: nec.calculate must NOT have been accidentally removed.
        Per Tom's decision 2026-05-10: intentional forward-looking permission
        for Phase 2 NEC route guards (voltage-drop, conduit-fill).
        """
        perms = self._get_technician_permissions(db_session)
        assert "nec.calculate" in perms, (
            "REGRESSION: nec.calculate was removed from the technician role. "
            "This is an intentional forward-looking permission for Phase 2 NEC routes. "
            "Do not remove it."
        )

    def test_technician_has_all_4_new_permissions(self, db_session: Session):
        """Single assertion checking all 4 FIND-128 permissions at once."""
        required = {
            "voice.create",
            "voice.view",
            "mobile_sync.view",
            "mobile_sync.resolve",
        }
        perms = set(self._get_technician_permissions(db_session))
        missing = required - perms
        assert not missing, (
            f"Technician role missing FIND-128 permissions: {sorted(missing)}. "
            "Run: alembic upgrade head"
        )

    def test_no_duplicate_permissions(self, db_session: Session):
        """The jsonb_agg(DISTINCT ...) in the migration must not produce duplicates."""
        perms = self._get_technician_permissions(db_session)
        assert len(perms) == len(set(perms)), (
            f"Technician role has duplicate permissions: "
            f"{[p for p in perms if perms.count(p) > 1]}"
        )

    def test_technician_role_exists(self, db_session: Session):
        """Sanity check: technician role row must exist."""
        result = db_session.execute(
            text("SELECT code FROM tenant_user_role WHERE code = 'technician'")
        ).fetchone()
        assert result is not None, (
            "tenant_user_role has no 'technician' row. "
            "Run: alembic upgrade head (seed_default_rbac_roles migration)"
        )


class TestTechnicianCanCallVoiceSessions:
    """
    FIND-128: Integration test — technician user must NOT get 403 on
    POST /api/v1/voice/sessions after the permission is added.

    Uses the test client with a mocked Cognito JWT so no real auth is needed.
    """

    def test_technician_not_denied_voice_sessions_post(
        self, client, db_session: Session, test_tenant
    ):
        """
        POST /api/v1/voice/sessions must not return 403 for a technician.

        The endpoint requires voice.create; technician now has it post-FIND-128.
        We mock the JWT validator so the test doesn't need a real Cognito token.
        """
        from sqlmodel import select

        from app.models.auth import TenantUser, TenantUserStatus
        from app.models.core import User

        # Create a minimal user + tenant_user with technician role
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"tech-{user_id.hex[:8]}@find128.test",
            first_name="Field",
            last_name="Tech",
        )
        db_session.add(user)
        db_session.flush()

        # TenantUserStatus is required (NOT NULL) — create or reuse active status
        status = db_session.exec(
            select(TenantUserStatus).where(
                TenantUserStatus.tenant_id == test_tenant.id,
                TenantUserStatus.code == "active",
            )
        ).first()
        if not status:
            status = TenantUserStatus(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                code="active",
                name="Active",
                is_default=True,
                is_active=True,
            )
            db_session.add(status)
            db_session.flush()

        tenant_user = TenantUser(
            id=uuid.uuid4(),
            user_id=user_id,
            tenant_id=test_tenant.id,
            role_code="technician",
            status_id=status.id,
            is_active=True,
        )
        db_session.add(tenant_user)
        db_session.flush()

        mock_claims = {
            "sub": str(user_id),
            "email": user.email,
            "custom:tenant_id": str(test_tenant.id),
        }

        with patch("core.auth.verify_cognito_jwt", return_value=mock_claims):
            response = client.post(
                "/api/v1/voice/sessions",
                headers={"Authorization": "Bearer fake-token-technician"},
                json={"session_name": "FIND-128 test session"},
            )

        assert response.status_code != 403, (
            f"Technician got 403 on POST /api/v1/voice/sessions — voice.create permission "
            f"is still missing. Status: {response.status_code}, body: {response.text}"
        )
