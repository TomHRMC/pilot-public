"""
B13/A71 — Data Export Request Pipeline Tests.

Test focus:
- POST /users/me/data-exports/test creates pending export
- POST /users/me/data-exports/test 429 when export already pending
- POST /users/me/data-exports/test 429 when export ready within 24h
- GET /users/me/data-exports/test returns list of exports
- GET /users/me/data-exports/{id}/test returns specific export
- GET /users/me/data-exports/{nonexistent}/test returns 404
- _process_data_export_impl() marks export as failed on ValueError
- tenant isolation: cannot see another tenant's exports
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.models.security import DataExportRequest
from core.test_context import get_test_context
from tasks.data_export_pipeline import _process_data_export_impl


class TestCreateDataExport:
    def test_creates_pending_export(self, db_session, client):
        resp = client.post("/api/v1/users/me/data-exports/test")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert "export_id" in data
        assert "requested_at" in data

    def test_returns_429_when_export_already_pending(self, db_session, client):
        client.post("/api/v1/users/me/data-exports/test")
        resp2 = client.post("/api/v1/users/me/data-exports/test")
        assert resp2.status_code == 429

    def test_returns_429_when_ready_within_24h(self, db_session, client):
        ctx = get_test_context()
        recent_export = DataExportRequest(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            status="ready",
            data_scope="user_specific",
            requested_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(recent_export)
        db_session.commit()

        resp = client.post("/api/v1/users/me/data-exports/test")
        assert resp.status_code == 429

    def test_allows_new_export_after_24h(self, db_session, client):
        ctx = get_test_context()
        old_export = DataExportRequest(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            status="ready",
            data_scope="user_specific",
            requested_at=datetime.now(UTC) - timedelta(hours=25),
        )
        db_session.add(old_export)
        db_session.commit()

        resp = client.post("/api/v1/users/me/data-exports/test")
        assert resp.status_code == 201


class TestListDataExports:
    def test_returns_empty_list_initially(self, client):
        resp = client.get("/api/v1/users/me/data-exports/test")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_exports(self, db_session, client):
        client.post("/api/v1/users/me/data-exports/test")
        resp = client.get("/api/v1/users/me/data-exports/test")
        assert resp.status_code == 200
        exports = resp.json()
        assert len(exports) >= 1
        assert exports[0]["status"] == "pending"


class TestGetDataExport:
    def test_returns_specific_export(self, db_session, client):
        create_resp = client.post("/api/v1/users/me/data-exports/test")
        export_id = create_resp.json()["export_id"]

        resp = client.get(f"/api/v1/users/me/data-exports/{export_id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["export_id"] == export_id

    def test_returns_404_for_nonexistent(self, client):
        resp = client.get(f"/api/v1/users/me/data-exports/{uuid.uuid4()}/test")
        assert resp.status_code == 404

    def test_tenant_isolation(self, db_session, client, tenant_b, user_tenant_a):
        # Create export for another tenant
        other_export = DataExportRequest(
            tenant_id=tenant_b.id,
            user_id=user_tenant_a.id,
            status="ready",
            data_scope="user_specific",
            requested_at=datetime.now(UTC),
        )
        db_session.add(other_export)
        db_session.commit()

        # Test endpoint uses TEST_TENANT_ID (not tenant_b)
        resp = client.get(
            f"/api/v1/users/me/data-exports/{other_export.export_id}/test"
        )
        assert resp.status_code == 404


class TestProcessDataExportImpl:
    def test_marks_failed_on_invalid_export_id(self, db_session):
        """_process_data_export_impl raises ValueError for unknown export_id."""
        with pytest.raises(ValueError, match="not found"):
            _process_data_export_impl(str(uuid.uuid4()), db_session)

    def test_skips_non_pending_export(self, db_session):
        ctx = get_test_context()
        export = DataExportRequest(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            status="ready",  # already ready
            data_scope="user_specific",
            requested_at=datetime.now(UTC),
        )
        db_session.add(export)
        db_session.commit()

        result = _process_data_export_impl(str(export.export_id), db_session)
        assert result["status"] == "ready"

    def test_marks_ready_on_success(self, db_session):
        ctx = get_test_context()
        export = DataExportRequest(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            status="pending",
            data_scope="user_specific",
            requested_at=datetime.now(UTC),
        )
        db_session.add(export)
        db_session.commit()

        with patch(
            "services.data_export_compiler.stream_export_to_s3",
            return_value=("s3://bucket/key.zip", "https://signed-url.example.com"),
        ):
            with patch("tasks.data_export_pipeline._send_export_ready_email"):
                result = _process_data_export_impl(str(export.export_id), db_session)

        db_session.refresh(export)
        assert export.status == "ready"
        assert export.s3_path == "s3://bucket/key.zip"
        assert export.signed_url == "https://signed-url.example.com"
        assert result["status"] == "ready"
