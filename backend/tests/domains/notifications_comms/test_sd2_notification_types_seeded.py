"""
SD-2 Tests: notification_type seeded rows verification.

Verifies that all 6 new notification_type codes added by SD-2 migration
exist in the DB with correct audience and is_active values.

Domain: notifications_comms (PRD §3.7)
"""

import pytest
from sqlmodel import Session, select

from app.models.system import NotificationType

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# All 6 new codes added by SD-2
SD2_NOTIFICATION_TYPE_CODES = [
    "job_assigned",
    "schedule_changed",
    "qb_sync_conflict",
    "qb_conflict_pre_warning",
    "gps_variance_alert",
    "system_template_updated",
]


class TestSd2NotificationTypesSeeded:
    """SD-2: Verify all 6 new notification_type codes are seeded."""

    def test_all_6_new_codes_exist(self, db_session: Session):
        """All 6 SD-2 notification types must be present with tenant_id IS NULL."""
        rows = db_session.exec(
            select(NotificationType).where(
                NotificationType.code.in_(SD2_NOTIFICATION_TYPE_CODES),
                NotificationType.tenant_id == None,
            )
        ).all()
        found_codes = {r.code for r in rows}
        missing = set(SD2_NOTIFICATION_TYPE_CODES) - found_codes
        assert not missing, (
            f"Missing notification_type rows (SD-2 migration not applied?): {missing}"
        )

    def test_all_6_have_tenant_audience(self, db_session: Session):
        """All 6 SD-2 notification types must have audience='tenant'."""
        rows = db_session.exec(
            select(NotificationType).where(
                NotificationType.code.in_(SD2_NOTIFICATION_TYPE_CODES),
                NotificationType.tenant_id == None,
            )
        ).all()
        wrong_audience = [r.code for r in rows if r.audience != "tenant"]
        assert not wrong_audience, (
            f"notification_type rows with wrong audience (expected 'tenant'): {wrong_audience}"
        )

    def test_all_6_are_active(self, db_session: Session):
        """All 6 SD-2 notification types must have is_active=True."""
        rows = db_session.exec(
            select(NotificationType).where(
                NotificationType.code.in_(SD2_NOTIFICATION_TYPE_CODES),
                NotificationType.tenant_id == None,
            )
        ).all()
        inactive = [r.code for r in rows if not r.is_active]
        assert not inactive, f"notification_type rows with is_active=False: {inactive}"

    @pytest.mark.parametrize("code", SD2_NOTIFICATION_TYPE_CODES)
    def test_each_code_exists_individually(self, db_session: Session, code: str):
        """Each SD-2 notification type exists individually (parametrized for clear output)."""
        row = db_session.exec(
            select(NotificationType).where(
                NotificationType.code == code,
                NotificationType.tenant_id == None,
            )
        ).first()
        assert row is not None, (
            f"notification_type '{code}' not seeded — run SD-2 migration or seed_core.py"
        )
        assert row.audience == "tenant"
        assert row.is_active is True
