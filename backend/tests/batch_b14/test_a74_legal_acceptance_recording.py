"""
B14/A74 — Legal Acceptance Recording tests.

Test focus cases:
1. POST /signup/{id}/legal/accept/test records acceptance with correct fields
2. Acceptance record is immutable (AppendOnlyMixin — no updated_at)
3. Multiple docs can be accepted for same tenant/user
4. GET /signup/{id}/legal/required/test returns 3 required docs
5. already_accepted = True after acceptance is recorded
6. duplicate acceptance (same document + same user) is allowed (legal audit trail)
7. invalid document_type returns 422
8. TenantLegalAcceptance stored with correct ip_address + user_agent
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.legal_acceptance import TenantLegalAcceptance
from app.models.signup import TenantSignup

# ==================== FIXTURES ====================


@pytest.fixture
def signup_tenant_for_legal(db_session, test_tenant):
    """Ensure a signup record exists for test_tenant.

    Seed-data-resilient: SD-7 Batch 3 seeds a tenant_signup row for the test tenant.
    This fixture checks for existence and skips INSERT if already present.
    guard_created_fields_immutable() trigger blocks any UPDATE on created_at,
    so merge() must NOT be used. The db_session transaction rolls back after each test.
    """
    existing = db_session.execute(
        text(
            "SELECT tenant_id FROM public.tenant_signup WHERE tenant_id = :tid LIMIT 1"
        ),
        {"tid": str(test_tenant.id)},
    ).first()
    if not existing:
        signup = TenantSignup(
            tenant_id=test_tenant.id,
            signup_state="step2_legal",
            signup_started_at=datetime.now(UTC),
            business_name=test_tenant.name,
            trade="electrical",
            business_size="solo",
            zip="10001",
            time_zone="America/New_York",
        )
        db_session.add(signup)
        db_session.commit()
    return test_tenant


# ==================== TEST CASES ====================


class TestLegalAcceptanceRecord:
    """Test cases 1-3: Record legal acceptance."""

    def test_accept_tos_creates_record(self, client, signup_tenant_for_legal):
        """POST /signup/{id}/legal/accept/test creates acceptance record."""
        now_iso = datetime.now(UTC).isoformat()
        response = client.post(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/accept/test",
            json={
                "document_type": "tos",
                "document_version_hash": "a" * 64,
                "accepted_at": now_iso,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["document_type"] == "tos"
        assert "acceptance_id" in data

    def test_accept_multiple_docs_creates_separate_records(
        self, client, db_session, signup_tenant_for_legal
    ):
        """Multiple document acceptances create separate rows."""
        now_iso = datetime.now(UTC).isoformat()
        for doc_type in ["tos", "privacy", "eula"]:
            response = client.post(
                f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/accept/test",
                json={
                    "document_type": doc_type,
                    "document_version_hash": "a" * 64,
                    "accepted_at": now_iso,
                },
            )
            assert response.status_code == 201

        records = db_session.exec(
            select(TenantLegalAcceptance).where(
                TenantLegalAcceptance.tenant_id == signup_tenant_for_legal.id
            )
        ).all()
        doc_types = {r.document_type for r in records}
        assert {"tos", "privacy", "eula"}.issubset(doc_types)

    def test_duplicate_acceptance_allowed(self, client, signup_tenant_for_legal):
        """Accepting same doc twice is allowed — creates two records for audit trail."""
        now_iso = datetime.now(UTC).isoformat()
        for _ in range(2):
            response = client.post(
                f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/accept/test",
                json={
                    "document_type": "tos",
                    "document_version_hash": "a" * 64,
                    "accepted_at": now_iso,
                },
            )
            assert response.status_code == 201

    def test_invalid_document_type_returns_422(self, client, signup_tenant_for_legal):
        """Invalid document_type returns 422."""
        response = client.post(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/accept/test",
            json={
                "document_type": "invalid_type",
                "document_version_hash": "a" * 64,
                "accepted_at": datetime.now(UTC).isoformat(),
            },
        )
        assert response.status_code == 422

    def test_acceptance_record_has_correct_fields(
        self, client, db_session, signup_tenant_for_legal
    ):
        """Acceptance record persists with correct field values."""
        version_hash = "c" * 64
        now_iso = datetime.now(UTC).isoformat()

        response = client.post(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/accept/test",
            json={
                "document_type": "eula",
                "document_version_hash": version_hash,
                "accepted_at": now_iso,
            },
        )
        assert response.status_code == 201
        acceptance_id = response.json()["acceptance_id"]

        record = db_session.exec(
            select(TenantLegalAcceptance).where(
                TenantLegalAcceptance.acceptance_id == acceptance_id
            )
        ).first()
        assert record is not None
        assert record.document_type == "eula"
        assert record.document_version_hash == version_hash
        assert record.tenant_id == signup_tenant_for_legal.id
        # AppendOnlyMixin: no updated_at column
        assert not hasattr(record, "updated_at") or not hasattr(
            TenantLegalAcceptance, "updated_at"
        )

    def test_acceptance_record_stored_with_ip_and_useragent(
        self, client, db_session, signup_tenant_for_legal
    ):
        """Acceptance record stores ip_address and user_agent."""
        response = client.post(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/accept/test",
            json={
                "document_type": "privacy",
                "document_version_hash": "b" * 64,
                "accepted_at": datetime.now(UTC).isoformat(),
            },
        )
        assert response.status_code == 201
        acceptance_id = response.json()["acceptance_id"]

        record = db_session.exec(
            select(TenantLegalAcceptance).where(
                TenantLegalAcceptance.acceptance_id == acceptance_id
            )
        ).first()
        assert record.ip_address is not None
        assert record.user_agent is not None


class TestLegalRequiredEndpoint:
    """Test cases 4-5: GET legal/required."""

    def test_required_returns_three_documents(self, client, signup_tenant_for_legal):
        """GET /signup/{id}/legal/required/test returns 3 required documents."""
        response = client.get(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/required/test"
        )
        assert response.status_code == 200
        data = response.json()
        assert "required_documents" in data
        assert len(data["required_documents"]) == 3
        doc_types = {d["document_type"] for d in data["required_documents"]}
        assert doc_types == {"tos", "privacy", "eula"}

    def test_already_accepted_reflects_accepted_status(
        self, client, signup_tenant_for_legal
    ):
        """After accepting tos, required endpoint shows already_accepted=True for tos."""
        # Accept tos
        client.post(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/accept/test",
            json={
                "document_type": "tos",
                "document_version_hash": "a" * 64,
                "accepted_at": datetime.now(UTC).isoformat(),
            },
        )

        response = client.get(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/required/test"
        )
        data = response.json()
        tos_status = next(
            d for d in data["required_documents"] if d["document_type"] == "tos"
        )
        assert tos_status["already_accepted"] is True

        # Other docs not yet accepted
        privacy_status = next(
            d for d in data["required_documents"] if d["document_type"] == "privacy"
        )
        assert privacy_status["already_accepted"] is False

    def test_required_includes_version_hash(self, client, signup_tenant_for_legal):
        """Required documents include current_version_hash."""
        response = client.get(
            f"/api/v1/signup/{signup_tenant_for_legal.id}/legal/required/test"
        )
        data = response.json()
        for doc in data["required_documents"]:
            assert "current_version_hash" in doc
            assert len(doc["current_version_hash"]) == 64
