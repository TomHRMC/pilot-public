"""
Tests for B20/A89 — LOTO Confirmation Table + Configurable Voice Guard (FIND-063)

Coverage:
  TestA89LotoConfirmationSchema     — ORM model mixin + DB constraint tests
  TestA89LotoConfirmationApi        — POST/GET /api/v1/jobs/{job_id}/loto-confirmations
  TestA89VoiceGuardSettingEnabled   — Voice guard fires when loto_confirmation_required=true
  TestA89VoiceGuardSettingDisabled  — No gate when loto_confirmation_required=false (default)
  TestA89OfflineSync                — client_capture_at → server_received_at populated
  TestA89AuditTrigger               — audit.event row on INSERT
"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.ai import ConversationSession
from app.models.fulfillment import Job, JobStatus, LotoConfirmation
from services.voice_action_router import (
    confirm_loto_via_voice,
    log_time_entry_via_voice,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_ctx(user, tenant):
    return SimpleNamespace(id=user.id, tenant_id=tenant.id)


def _make_session(
    db,
    tenant_id,
    user_id,
    *,
    safety_loto_verified=False,
    active_job_id=None,
) -> ConversationSession:
    ctx = {"safety_loto_verified": safety_loto_verified}
    if active_job_id is not None:
        ctx["active_job_id"] = str(active_job_id)
    sess = ConversationSession(
        tenant_id=tenant_id,
        user_id=user_id,
        context_window_json=ctx,
        is_active=True,
        created_by=user_id,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _make_job(db, tenant_id, test_user, customer, site) -> Job:
    js = db.exec(select(JobStatus)).first()
    assert js is not None
    job = Job(
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=js.id,
        is_active=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _set_loto_required(db, tenant_id, value: bool):
    """Override loto_confirmation_required platform_setting for a specific tenant."""
    from app.models.platform_setting import PlatformSetting

    existing = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == "loto_confirmation_required")
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()
    if existing:
        db.delete(existing)
        db.commit()

    ps = PlatformSetting(
        key="loto_confirmation_required",
        value=value,
        tenant_id=tenant_id,
    )
    db.add(ps)
    db.commit()


def _clear_loto_required(db, tenant_id):
    """Remove tenant-specific loto_confirmation_required override."""
    from app.models.platform_setting import PlatformSetting

    existing = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == "loto_confirmation_required")
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()
    if existing:
        db.delete(existing)
        db.commit()


# ---------------------------------------------------------------------------
# TestA89LotoConfirmationSchema
# ---------------------------------------------------------------------------


class TestA89LotoConfirmationSchema:
    """Schema-level tests: ORM mixin, constraints, and DB triggers."""

    def test_model_inherits_append_only_mixin(self):
        """LotoConfirmation must subclass AppendOnlyMixin."""
        from app.models.mixins import AppendOnlyMixin

        assert issubclass(LotoConfirmation, AppendOnlyMixin)

    def test_model_has_no_updated_at(self):
        """AppendOnlyMixin: no updated_at column on LotoConfirmation."""
        assert not hasattr(LotoConfirmation, "updated_at")

    def test_created_at_auto_set_on_insert(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """INSERT row; assert created_at is populated by DB default."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        record = LotoConfirmation(
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            confirmed_at=datetime.now(UTC),
            created_by=test_user.id,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        assert record.created_at is not None

    def test_natural_key_dedup_prevents_duplicate_insert(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """INSERT two rows with identical (user_id, job_id, confirmed_at) must raise IntegrityError."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        ts = datetime.now(UTC)
        r1 = LotoConfirmation(
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            confirmed_at=ts,
            created_by=test_user.id,
        )
        db_session.add(r1)
        db_session.commit()

        r2 = LotoConfirmation(
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            confirmed_at=ts,  # same → natural key collision
            created_by=test_user.id,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_active_partial_index_allows_only_one_active_per_job_user(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """Two rows for same (job_id, user_id) with is_active=true must raise IntegrityError."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        now = datetime.now(UTC)

        r1 = LotoConfirmation(
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            confirmed_at=now,
            is_active=True,
            created_by=test_user.id,
        )
        db_session.add(r1)
        db_session.commit()

        # Different confirmed_at but same (job_id, user_id, is_active=True) → partial index violation
        r2 = LotoConfirmation(
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            confirmed_at=now.replace(second=(now.second + 1) % 60),
            is_active=True,
            created_by=test_user.id,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


# ---------------------------------------------------------------------------
# TestA89LotoConfirmationApi
# ---------------------------------------------------------------------------


class TestA89LotoConfirmationApi:
    """API endpoint tests for POST/GET /api/v1/jobs/{job_id}/loto-confirmations."""

    def test_post_loto_confirmation_creates_row(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        test_tenant,
        test_customer,
        test_site,
    ):
        """POST returns 201 with populated LotoConfirmationRead."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        mock_cognito_jwt(test_user)

        payload = {
            "confirmed_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        response = client.post(
            f"/api/v1/jobs/{job.id}/loto-confirmations", json=payload
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["job_id"] == str(job.id)
        assert data["user_id"] == str(test_user.id)
        assert data["is_active"] is True

    def test_post_loto_confirmation_sets_server_received_at_when_client_capture_at_provided(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        test_tenant,
        test_customer,
        test_site,
    ):
        """Submit with client_capture_at; assert server_received_at is not None on returned row."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        mock_cognito_jwt(test_user)

        payload = {
            "confirmed_at": datetime.now(UTC).isoformat(),
            "client_capture_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        response = client.post(
            f"/api/v1/jobs/{job.id}/loto-confirmations", json=payload
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["server_received_at"] is not None

    def test_post_loto_confirmation_idempotent_replay(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        test_tenant,
        test_customer,
        test_site,
    ):
        """Submit same confirmed_at twice; second call returns 200 with same row id."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        mock_cognito_jwt(test_user)
        confirmed_at = datetime.now(UTC).isoformat()
        payload = {
            "confirmed_at": confirmed_at,
            "idempotency_uuid": str(uuid.uuid4()),
        }

        r1 = client.post(f"/api/v1/jobs/{job.id}/loto-confirmations", json=payload)
        assert r1.status_code == status.HTTP_201_CREATED
        row_id = r1.json()["id"]

        r2 = client.post(f"/api/v1/jobs/{job.id}/loto-confirmations", json=payload)
        assert r2.status_code == status.HTTP_200_OK
        assert r2.json()["id"] == row_id

    def test_post_loto_confirmation_cross_tenant_job_returns_404(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        second_tenant,
    ):
        """Submit with job_id belonging to different tenant; expect 404."""
        from app.models.crm import Customer, Site

        other_customer = Customer(
            tenant_id=second_tenant.id,
            display_name=f"T2Customer {uuid.uuid4()}",
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(other_customer)
        db_session.flush()

        other_site = Site(
            tenant_id=second_tenant.id,
            customer_id=other_customer.id,
            display_name=f"T2Site {uuid.uuid4()}",
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(other_site)
        db_session.flush()

        js = db_session.exec(select(JobStatus)).first()
        other_job = Job(
            tenant_id=second_tenant.id,
            customer_id=other_customer.id,
            site_id=other_site.id,
            status_id=js.id,
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(other_job)
        db_session.commit()

        mock_cognito_jwt(test_user)
        payload = {
            "confirmed_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        response = client.post(
            f"/api/v1/jobs/{other_job.id}/loto-confirmations", json=payload
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_loto_confirmations_returns_list(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        test_tenant,
        test_customer,
        test_site,
    ):
        """POST one row; GET returns list containing that row."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        mock_cognito_jwt(test_user)

        post_payload = {
            "confirmed_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        client.post(f"/api/v1/jobs/{job.id}/loto-confirmations", json=post_payload)

        response = client.get(f"/api/v1/jobs/{job.id}/loto-confirmations")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["job_id"] == str(job.id)

    def test_get_loto_confirmations_empty_list(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        test_tenant,
        test_customer,
        test_site,
    ):
        """GET on job with no LOTO rows returns 200 with empty list."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        mock_cognito_jwt(test_user)

        response = client.get(f"/api/v1/jobs/{job.id}/loto-confirmations")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


# ---------------------------------------------------------------------------
# TestA89VoiceGuardSettingEnabled
# ---------------------------------------------------------------------------


class TestA89VoiceGuardSettingEnabled:
    """Voice guard tests when loto_confirmation_required=true."""

    @pytest.mark.asyncio
    async def test_voice_guard_blocks_log_time_entry_stop_when_loto_not_verified(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """loto_confirmation_required=true; log_time_entry with no LOTO → success=False refusal."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        sess = _make_session(
            db_session,
            test_tenant.id,
            test_user.id,
            safety_loto_verified=False,
            active_job_id=job.id,
        )

        _set_loto_required(db_session, test_tenant.id, True)
        try:
            result = await log_time_entry_via_voice(
                {"hours": "2"},
                _user_ctx(test_user, test_tenant),
                db_session,
                sess,
            )
            assert result["success"] is False
            assert "LOTO" in result["message"]
        finally:
            _clear_loto_required(db_session, test_tenant.id)

    @pytest.mark.asyncio
    async def test_voice_guard_allows_log_time_entry_stop_after_loto_confirmed(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """loto_confirmation_required=true; confirm_loto then log_time_entry → guard does not block."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        sess = _make_session(
            db_session,
            test_tenant.id,
            test_user.id,
            safety_loto_verified=False,
            active_job_id=job.id,
        )

        _set_loto_required(db_session, test_tenant.id, True)
        try:
            # Confirm LOTO first
            loto_result = await confirm_loto_via_voice(
                {}, _user_ctx(test_user, test_tenant), db_session, sess
            )
            assert loto_result["success"] is True

            # Now log time — guard should not block for LOTO
            result = await log_time_entry_via_voice(
                {"hours": "2"},
                _user_ctx(test_user, test_tenant),
                db_session,
                sess,
            )
            # If it fails it must NOT be for LOTO reason
            if not result["success"]:
                assert "LOTO" not in result.get("message", "")
        finally:
            _clear_loto_required(db_session, test_tenant.id)

    @pytest.mark.asyncio
    async def test_confirm_loto_via_voice_sets_safety_loto_verified_true(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """After confirm_loto_via_voice, session context has safety_loto_verified=True."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        sess = _make_session(
            db_session,
            test_tenant.id,
            test_user.id,
            safety_loto_verified=False,
            active_job_id=job.id,
        )

        result = await confirm_loto_via_voice(
            {}, _user_ctx(test_user, test_tenant), db_session, sess
        )
        assert result["success"] is True

        db_session.refresh(sess)
        assert sess.context_window_json.get("safety_loto_verified") is True

    @pytest.mark.asyncio
    async def test_confirm_loto_via_voice_inserts_db_row(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """After confirm_loto_via_voice, a loto_confirmation row exists in DB."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        sess = _make_session(
            db_session,
            test_tenant.id,
            test_user.id,
            active_job_id=job.id,
        )

        result = await confirm_loto_via_voice(
            {}, _user_ctx(test_user, test_tenant), db_session, sess
        )
        assert result["success"] is True

        row = db_session.exec(
            select(LotoConfirmation)
            .where(LotoConfirmation.job_id == job.id)
            .where(LotoConfirmation.user_id == test_user.id)
        ).first()
        assert row is not None
        assert row.tenant_id == test_tenant.id


# ---------------------------------------------------------------------------
# TestA89VoiceGuardSettingDisabled
# ---------------------------------------------------------------------------


class TestA89VoiceGuardSettingDisabled:
    """Voice guard absent when loto_confirmation_required=false (default)."""

    @pytest.mark.asyncio
    async def test_voice_guard_absent_when_loto_required_false(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """Default loto_confirmation_required=false; log_time_entry not blocked by LOTO guard."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        sess = _make_session(
            db_session,
            test_tenant.id,
            test_user.id,
            safety_loto_verified=False,
            active_job_id=job.id,
        )

        _clear_loto_required(db_session, test_tenant.id)

        result = await log_time_entry_via_voice(
            {"hours": "2"},
            _user_ctx(test_user, test_tenant),
            db_session,
            sess,
        )
        # Should not be blocked for LOTO reason
        if not result["success"]:
            assert "LOTO" not in result.get("message", "")

    @pytest.mark.asyncio
    async def test_confirm_loto_via_voice_still_records_row_when_setting_disabled(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """With loto_confirmation_required=false, confirm_loto_via_voice INSERT still succeeds."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        sess = _make_session(
            db_session,
            test_tenant.id,
            test_user.id,
            active_job_id=job.id,
        )
        _clear_loto_required(db_session, test_tenant.id)

        result = await confirm_loto_via_voice(
            {}, _user_ctx(test_user, test_tenant), db_session, sess
        )
        assert result["success"] is True

        row = db_session.exec(
            select(LotoConfirmation)
            .where(LotoConfirmation.job_id == job.id)
            .where(LotoConfirmation.user_id == test_user.id)
        ).first()
        assert row is not None


# ---------------------------------------------------------------------------
# TestA89OfflineSync
# ---------------------------------------------------------------------------


class TestA89OfflineSync:
    """Offline sync: client_capture_at → server_received_at pattern."""

    def test_sync_loto_confirmation_populates_server_received_at(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        test_tenant,
        test_customer,
        test_site,
    ):
        """POST with client_capture_at set; assert server_received_at is populated."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        mock_cognito_jwt(test_user)

        payload = {
            "confirmed_at": datetime.now(UTC).isoformat(),
            "client_capture_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        response = client.post(
            f"/api/v1/jobs/{job.id}/loto-confirmations", json=payload
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["server_received_at"] is not None
        assert response.json()["client_capture_at"] is not None

    def test_offline_dedup_natural_key_prevents_duplicate_on_resync(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        db_session,
        test_tenant,
        test_customer,
        test_site,
    ):
        """POST same (user_id, job_id, confirmed_at) twice (offline retry); second returns 200."""
        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        mock_cognito_jwt(test_user)

        confirmed_at = datetime.now(UTC).isoformat()
        payload = {
            "confirmed_at": confirmed_at,
            "client_capture_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        r1 = client.post(f"/api/v1/jobs/{job.id}/loto-confirmations", json=payload)
        assert r1.status_code == status.HTTP_201_CREATED

        r2 = client.post(f"/api/v1/jobs/{job.id}/loto-confirmations", json=payload)
        assert r2.status_code == status.HTTP_200_OK
        assert r2.json()["id"] == r1.json()["id"]


# ---------------------------------------------------------------------------
# TestA89AuditTrigger
# ---------------------------------------------------------------------------


class TestA89AuditTrigger:
    """Audit trigger fires on INSERT to audit.event."""

    def test_audit_trigger_fires_on_insert(
        self, db_session, test_tenant, test_user, test_customer, test_site
    ):
        """INSERT loto_confirmation; query audit.event for table_name='loto_confirmation'."""
        from app.models.system import AuditEvent

        job = _make_job(db_session, test_tenant.id, test_user, test_customer, test_site)
        record = LotoConfirmation(
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            confirmed_at=datetime.now(UTC),
            created_by=test_user.id,
        )
        db_session.add(record)
        db_session.commit()

        audit_row = db_session.exec(
            select(AuditEvent)
            .where(AuditEvent.entity_name == "loto_confirmation")
            .where(AuditEvent.entity_id == str(record.id))
        ).first()
        assert audit_row is not None
        assert audit_row.action == "INSERT"
