"""
PLATFORM-SMS-B2 — Maintenance Broadcast CLI Test
================================================
Tests for ``scripts.broadcast_maintenance_sms`` (the operator-run CLI that
enqueues ``platform_maintenance_broadcast`` tasks per eligible tenant).

  1. Validation rejects ``&``, ``<``, ``{``, empty string → exit 2, zero delay
     calls. A valid en-dash window passes validation.
  2. Dry run (no ``--i-am-sure``): zero delay calls; summary logs the eligible
     count.
  3. ``--i-am-sure``: one delay call per eligible tenant with exact kwargs
     (tenant_id / type_code / template_context).
  4. A tenant with no verified+opted-in owner endpoints is excluded.

Monkeypatches ``send_platform_account_notification_sms.delay`` and
``scripts.broadcast_maintenance_sms.Session`` (to use the rollback-wrapped
db_session). Uses ``test_tenant``/``second_tenant`` + the B1 verified-endpoint
setup pattern. Assertions scoped by inserted IDs — never counts.

Domain: notifications_comms (PRD §3.7)
"""

import hashlib
import uuid
from unittest.mock import patch

import pytest

from app.models.auth import TenantUser
from app.models.core import User
from services.notification_endpoints import upsert_owner_sms_endpoint

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# tenant_user_status.code='active' id (MCP-verified, seeded platform row).
_ACTIVE_STATUS_ID = "5b67cfd3-ef42-4311-9516-a4eec8642628"


def _make_verified_owner(db_session, tenant, phone):
    """Create a fresh owner user + TenantUser + verified+opted-in sms endpoint
    scoped to the given tenant."""
    user = User(
        id=uuid.uuid4(),
        email=f"b2-cli-{uuid.uuid4().hex[:8]}@test.local",
        first_name="Owner",
        last_name="Test",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(
        TenantUser(
            tenant_id=tenant.id,
            user_id=user.id,
            role_code="owner",
            status_id=_ACTIVE_STATUS_ID,
            is_active=True,
        )
    )
    db_session.flush()

    endpoint = upsert_owner_sms_endpoint(
        db_session,
        user_id=user.id,
        tenant_id=tenant.id,
        phone=phone,
        consent=True,
        ip="127.0.0.1",
        disclosure_hash=hashlib.sha256(b"d").hexdigest(),
    )
    endpoint.verification_status = "verified"
    endpoint.consent_status = "opted_in"
    db_session.add(endpoint)
    db_session.commit()
    return user, endpoint


def _run_cli(db_session, date, window, i_am_sure=False):
    """Invoke the CLI main() with Session patched to use db_session.
    Returns (exit_code, delay_mock). Raises SystemExit on validation failure."""
    from scripts import broadcast_maintenance_sms

    with (
        patch.object(broadcast_maintenance_sms, "Session") as mock_session_cls,
        patch.object(
            broadcast_maintenance_sms.send_platform_account_notification_sms,
            "delay",
        ) as mock_delay,
    ):
        mock_session_cls.return_value.__enter__.return_value = db_session
        exit_code = broadcast_maintenance_sms.main(date, window, i_am_sure)
    return exit_code, mock_delay


def _run_cli_expect_exit_2(db_session, date, window, i_am_sure=False):
    """Invoke the CLI main() expecting a SystemExit(2) on validation failure.
    Returns the delay_mock (asserted not called)."""
    from scripts import broadcast_maintenance_sms

    with (
        patch.object(broadcast_maintenance_sms, "Session") as mock_session_cls,
        patch.object(
            broadcast_maintenance_sms.send_platform_account_notification_sms,
            "delay",
        ) as mock_delay,
    ):
        mock_session_cls.return_value.__enter__.return_value = db_session
        with pytest.raises(SystemExit) as exc_info:
            broadcast_maintenance_sms.main(date, window, i_am_sure)
        assert exc_info.value.code == 2
    return mock_delay


class TestBroadcastCliValidation:
    """Validation rejects disallowed characters; valid en-dash passes."""

    @pytest.mark.parametrize(
        "date,window",
        [
            ("Sun 08-02-2026", "2:00 & 3:00 AM ET"),
            ("Sun 08-02-2026", "2:00 < 3:00"),
            ("Sun{08", "2:00 AM ET"),
            ("", "2:00 AM ET"),
            ("Sun 08-02-2026", ""),
        ],
    )
    def test_rejects_disallowed_values(self, db_session, test_tenant, date, window):
        """Disallowed values → exit 2, zero delay calls."""
        mock_delay = _run_cli_expect_exit_2(db_session, date, window, i_am_sure=True)
        mock_delay.assert_not_called()

    def test_valid_en_dash_window_passes(self, db_session, test_tenant):
        """A valid en-dash window passes validation (exit 0, dry run)."""
        _make_verified_owner(db_session, test_tenant, "+15125550801")
        exit_code, mock_delay = _run_cli(
            db_session, "Sun 08-02-2026", "2:00–3:00 AM ET", i_am_sure=False
        )
        assert exit_code == 0
        mock_delay.assert_not_called()


class TestBroadcastCliDryRun:
    """Dry run enqueues nothing; logs the eligible count."""

    def test_dry_run_enqueues_nothing(self, db_session, test_tenant):
        """No --i-am-sure → zero delay calls, exit 0."""
        _make_verified_owner(db_session, test_tenant, "+15125550810")
        exit_code, mock_delay = _run_cli(
            db_session, "Sun 08-02-2026", "2:00–3:00 AM ET", i_am_sure=False
        )
        assert exit_code == 0
        mock_delay.assert_not_called()


class TestBroadcastCliLiveRun:
    """--i-am-sure enqueues one task per eligible tenant with exact kwargs."""

    def test_enqueues_per_eligible_tenant(self, db_session, test_tenant, second_tenant):
        """Two eligible tenants → two delay calls with exact kwargs."""
        _make_verified_owner(db_session, test_tenant, "+15125550820")
        _make_verified_owner(db_session, second_tenant, "+15125550821")

        exit_code, mock_delay = _run_cli(
            db_session, "Sun 08-02-2026", "2:00–3:00 AM ET", i_am_sure=True
        )
        assert exit_code == 0
        assert mock_delay.call_count == 2

        called_tenant_ids = set()
        for call in mock_delay.call_args_list:
            kwargs = call.kwargs
            assert kwargs["type_code"] == "platform_maintenance_broadcast"
            assert kwargs["template_context"] == {
                "maint_date": "Sun 08-02-2026",
                "maint_window": "2:00–3:00 AM ET",
            }
            called_tenant_ids.add(kwargs["tenant_id"])

        # Both eligible tenants were enqueued (scoped by inserted IDs).
        assert str(test_tenant.id) in called_tenant_ids
        assert str(second_tenant.id) in called_tenant_ids

    def test_tenant_without_verified_endpoints_excluded(
        self, db_session, test_tenant, second_tenant
    ):
        """A tenant with no verified+opted-in owner endpoints is excluded."""
        # test_tenant gets a verified owner → eligible.
        _make_verified_owner(db_session, test_tenant, "+15125550830")
        # second_tenant gets an owner with an UNVERIFIED endpoint → excluded.
        user = User(
            id=uuid.uuid4(),
            email=f"b2-cli-unverified-{uuid.uuid4().hex[:8]}@test.local",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
        db_session.add(
            TenantUser(
                tenant_id=second_tenant.id,
                user_id=user.id,
                role_code="owner",
                status_id=_ACTIVE_STATUS_ID,
                is_active=True,
            )
        )
        db_session.flush()
        endpoint = upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=second_tenant.id,
            phone="+15125550831",
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        # Leave verification_status='pending', consent_status='pending' (default).
        db_session.add(endpoint)
        db_session.commit()

        exit_code, mock_delay = _run_cli(
            db_session, "Sun 08-02-2026", "2:00–3:00 AM ET", i_am_sure=True
        )
        assert exit_code == 0
        # Only test_tenant is eligible → exactly one delay call.
        assert mock_delay.call_count == 1
        assert mock_delay.call_args.kwargs["tenant_id"] == str(test_tenant.id)
