"""
C-B16 Part A — Public tenant site endpoint + Celery email task tests.

Covers test groups 7 and 11 from the design §I:
  7. Public endpoint (unknown slug → 404, draft/unpublished → 404, published → payload,
     address fields only when show_full_address, no auth needed)
  11. Celery _impl (call directly, mock SendGrid, assert already-emailed guard)

Domain: notifications_comms (PRD §3.7)
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import text

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _wipe_tenant_site(db_session, tenant_id):
    """Delete tenant_site rows for a specific tenant."""
    db_session.execute(
        text("DELETE FROM public.tenant_site WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
    db_session.commit()


def _make_published_site(
    db_session,
    tenant_id,
    slug="pub-test-slug",
    show_full_address=False,
    address_line1=None,
    postal_code=None,
):
    """Create a published site with a snapshot for public endpoint testing."""
    from app.models.tenant_site import TenantSite
    from services import tenant_site_service as svc

    site = TenantSite(
        tenant_id=tenant_id,
        slug=slug,
        site_kind="hosted_compliance",
        status="published",
        display_name="Public Test Site",
        tagline="Test tagline",
        public_email="pub@test.com",
        public_phone="+15551234567",
        public_city="Austin",
        public_state="TX",
        public_address_line1=address_line1,
        public_postal_code=postal_code,
        show_full_address=show_full_address,
        template_version="v1",
        published_at=datetime.now(UTC),
    )
    # Build snapshot
    snapshot = svc.build_snapshot(db_session, site)
    site.published_snapshot = snapshot
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


# ─── 7. Public endpoint ──────────────────────────────────────────────────────


class TestPublicEndpoint:
    def test_unknown_slug_404(self, client, db_session):
        """Unknown slug → 404 site_not_found (RFC 7807)."""
        resp = client.get("/api/v1/public/tenant-sites/nonexistent-slug-xyz")
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["type"].endswith("site_not_found")
        assert detail["status"] == 404

    def test_draft_returns_404(self, client, second_tenant, db_session):
        """Draft site → 404 (no existence leak)."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="draft-pub-test",
            site_kind="hosted_compliance",
            status="draft",
            display_name="Draft Site",
        )
        db_session.add(site)
        db_session.commit()

        resp = client.get("/api/v1/public/tenant-sites/draft-pub-test")
        assert resp.status_code == 404

    def test_unpublished_returns_404(self, client, second_tenant, db_session):
        """Unpublished site → 404 (no existence leak)."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="unpub-pub-test",
            site_kind="hosted_compliance",
            status="unpublished",
            display_name="Unpublished Site",
            published_snapshot={"slug": "unpub-pub-test", "pages": {}},
            unpublished_at=datetime.now(UTC),
        )
        db_session.add(site)
        db_session.commit()

        resp = client.get("/api/v1/public/tenant-sites/unpub-pub-test")
        assert resp.status_code == 404

    def test_published_returns_whitelisted_payload(
        self, client, second_tenant, db_session
    ):
        """Published site → whitelisted payload with pages."""
        _wipe_tenant_site(db_session, second_tenant.id)

        _make_published_site(
            db_session, second_tenant.id, slug="published-payload-test"
        )

        resp = client.get("/api/v1/public/tenant-sites/published-payload-test")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Whitelisted fields
        assert data["slug"] == "published-payload-test"
        assert data["display_name"] == "Public Test Site"
        assert data["public_email"] == "pub@test.com"
        assert data["public_phone"] == "+15551234567"
        assert data["public_city"] == "Austin"
        assert data["public_state"] == "TX"
        assert data["template_version"] == "v1"

        # Pages present
        assert "pages" in data
        assert "landing" in data["pages"]
        assert "privacy" in data["pages"]
        assert "terms" in data["pages"]

        # Landing has heading + body_paragraphs
        landing = data["pages"]["landing"]
        assert "heading" in landing
        assert "body_paragraphs" in landing
        assert len(landing["body_paragraphs"]) > 0

        # Privacy has title + body_paragraphs
        privacy = data["pages"]["privacy"]
        assert "title" in privacy
        assert "body_paragraphs" in privacy

        # No internal fields leaked
        assert "tenant_id" not in data
        assert "id" not in data
        assert "idempotency_key" not in data
        assert "website_auto_populated" not in data

    def test_address_fields_only_when_show_full_address(
        self, client, second_tenant, db_session
    ):
        """Address fields present only when show_full_address=TRUE."""
        _wipe_tenant_site(db_session, second_tenant.id)

        # Site with show_full_address=False
        _make_published_site(
            db_session,
            second_tenant.id,
            slug="no-address-test",
            show_full_address=False,
            address_line1="123 Hidden St",
            postal_code="78701",
        )

        resp = client.get("/api/v1/public/tenant-sites/no-address-test")
        assert resp.status_code == 200
        data = resp.json()
        # Address fields should NOT be in the payload
        assert data.get("public_address_line1") is None
        assert data.get("public_postal_code") is None

        # Now test with show_full_address=True
        _wipe_tenant_site(db_session, second_tenant.id)
        _make_published_site(
            db_session,
            second_tenant.id,
            slug="show-address-test",
            show_full_address=True,
            address_line1="123 Visible St",
            postal_code="78701",
        )

        resp2 = client.get("/api/v1/public/tenant-sites/show-address-test")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["public_address_line1"] == "123 Visible St"
        assert data2["public_postal_code"] == "78701"

    def test_no_auth_needed(self, client, second_tenant, db_session):
        """Public endpoint works without any auth header."""
        _wipe_tenant_site(db_session, second_tenant.id)

        _make_published_site(db_session, second_tenant.id, slug="no-auth-test")

        # No Authorization header
        resp = client.get("/api/v1/public/tenant-sites/no-auth-test")
        assert resp.status_code == 200

    def test_sms_clauses_in_privacy_and_terms(self, client, second_tenant, db_session):
        """Privacy and Terms pages contain all six SMS clause categories."""
        _wipe_tenant_site(db_session, second_tenant.id)

        _make_published_site(db_session, second_tenant.id, slug="sms-clauses-test")

        resp = client.get("/api/v1/public/tenant-sites/sms-clauses-test")
        assert resp.status_code == 200
        data = resp.json()

        # Combine all body paragraphs from privacy + terms
        all_text = " ".join(
            data["pages"]["privacy"]["body_paragraphs"]
            + data["pages"]["terms"]["body_paragraphs"]
        ).lower()

        # Check all six SMS clause categories
        assert "text message" in all_text or "sms" in all_text  # message types
        assert "5 messages per month" in all_text  # frequency/cadence
        assert "message and data rates" in all_text  # rates notice
        assert "stop" in all_text  # STOP opt-out
        assert "help" in all_text  # HELP instructions
        assert "third parties" in all_text or "third-party" in all_text  # no sharing


# ─── 11. Celery _impl ────────────────────────────────────────────────────────


class TestCeleryEmailImpl:
    def test_impl_sends_email_successfully(self, db_session, second_tenant):
        """_send_website_requirements_email_impl sends via SendGrid."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.core import Tenant10DlcProfile

        # Create a profile with support_email and no requirements_emailed_at
        profile = Tenant10DlcProfile(
            tenant_id=second_tenant.id,
            legal_business_name="Email Impl Test LLC",
            support_email="impl-test@test.com",
            support_phone="+15551234567",
            hq_city="Austin",
            hq_state="TX",
        )
        db_session.add(profile)
        db_session.commit()

        with patch("tasks.tenant_site_emails.send_email") as mock_send:
            mock_send.return_value = {"status": "sent", "error_message": None}

            from tasks.tenant_site_emails import _send_website_requirements_email_impl

            result = _send_website_requirements_email_impl(
                str(second_tenant.id), db_session
            )

            assert result["sent"] is True
            assert result["reason"] == "sent"
            assert mock_send.call_count == 1

            # Verify requirements_emailed_at was stamped
            db_session.refresh(profile)
            assert profile.requirements_emailed_at is not None

    def test_impl_already_emailed_guard(self, db_session, second_tenant):
        """_impl returns already_emailed when requirements_emailed_at is set."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.core import Tenant10DlcProfile

        # Create a profile with requirements_emailed_at already set
        profile = Tenant10DlcProfile(
            tenant_id=second_tenant.id,
            legal_business_name="Already Emailed LLC",
            support_email="already@test.com",
            requirements_emailed_at=datetime.now(UTC),
        )
        db_session.add(profile)
        db_session.commit()

        with patch("tasks.tenant_site_emails.send_email") as mock_send:
            from tasks.tenant_site_emails import _send_website_requirements_email_impl

            result = _send_website_requirements_email_impl(
                str(second_tenant.id), db_session
            )

            assert result["sent"] is False
            assert result["reason"] == "already_emailed"
            assert mock_send.call_count == 0  # no send

    def test_impl_no_profile(self, db_session, second_tenant):
        """_impl returns no_profile when no profile exists."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from tasks.tenant_site_emails import _send_website_requirements_email_impl

        result = _send_website_requirements_email_impl(
            str(second_tenant.id), db_session
        )

        assert result["sent"] is False
        assert result["reason"] == "no_profile"

    def test_impl_no_recipient_email(self, db_session, second_tenant):
        """_impl returns no_recipient_email when profile has no support_email."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.core import Tenant10DlcProfile

        profile = Tenant10DlcProfile(
            tenant_id=second_tenant.id,
            legal_business_name="No Email LLC",
            support_email=None,
        )
        db_session.add(profile)
        db_session.commit()

        from tasks.tenant_site_emails import _send_website_requirements_email_impl

        result = _send_website_requirements_email_impl(
            str(second_tenant.id), db_session
        )

        assert result["sent"] is False
        assert result["reason"] == "no_recipient_email"

    def test_impl_invalid_tenant_id(self, db_session):
        """_impl returns invalid_tenant_id for bad UUID."""
        from tasks.tenant_site_emails import _send_website_requirements_email_impl

        result = _send_website_requirements_email_impl("not-a-uuid", db_session)
        assert result["sent"] is False
        assert result["reason"] == "invalid_tenant_id"
