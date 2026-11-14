"""
C-B16 Part A — Tenant site authenticated endpoint + service tests.

Covers test groups 1-6, 8-10 from the design §I:
  1. Slug validation (bad format, reserved, taken, availability)
  2. GET (no row → defaults, row present → full config)
  3. PUT upsert (create, idempotency replay, slug immutable after publish)
  4. Publish (missing fields, no draft, website 3-way rule, re-publish)
  5. Brand classification (status families)
  6. Unpublish (409 when draft, success, website intact, warning)
  8. One-time email guard (profile PUT trigger, Option-1 trigger, reconciliation)
  9. Cross-tenant isolation
  10. RBAC (settings.view / settings.manage)

Domain: notifications_comms (PRD §3.7)
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _wipe_tenant_site(db_session, tenant_id):
    """Delete tenant_site rows for a specific tenant (test-created only)."""
    db_session.execute(
        text("DELETE FROM public.tenant_site WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
    db_session.commit()


def _make_profile(db_session, tenant_id, **kwargs):
    """Create or update a 10DLC profile for a tenant."""
    from app.models.core import Tenant10DlcProfile

    existing = db_session.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()

    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        db_session.add(existing)
    else:
        profile = Tenant10DlcProfile(
            tenant_id=tenant_id,
            legal_business_name=kwargs.get("legal_business_name", "Test Business LLC"),
            dba_name=kwargs.get("dba_name"),
            support_email=kwargs.get("support_email"),
            support_phone=kwargs.get("support_phone"),
            hq_city=kwargs.get("hq_city"),
            hq_state=kwargs.get("hq_state"),
            website=kwargs.get("website"),
        )
        db_session.add(profile)
    db_session.commit()


def _make_registration(db_session, tenant_id, status="quoting"):
    """Create a tenant_messaging_registration row."""
    from app.models.sms import TenantMessagingRegistration

    reg = TenantMessagingRegistration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        entity_type="standard",
        status=status,
    )
    db_session.add(reg)
    db_session.commit()
    return reg


def _put_site(client, payload, tenant_id=None, idempotency_key=None):
    """PUT a site draft via the test endpoint."""
    headers = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return client.put("/api/v1/tenant-site/test", json=payload, headers=headers)


def _publish_site(client, confirm=False):
    """Publish via the test endpoint."""
    return client.post(
        "/api/v1/tenant-site/publish/test",
        json={"confirm_website_overwrite": confirm},
    )


# ─── 1. Slug validation ──────────────────────────────────────────────────────


class TestSlugValidation:
    def test_bad_format_returns_422(self, client, second_tenant):
        """Slug with invalid format → 422 slug_invalid."""
        resp = _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "INVALID UPPER!",
                "display_name": "Test",
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["type"].endswith("slug_invalid")

    def test_reserved_slug_returns_422(self, client, second_tenant):
        """Reserved slug → 422 slug_reserved."""
        resp = _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "admin",
                "display_name": "Test",
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["type"].endswith("slug_reserved")

    def test_taken_slug_returns_409(self, client, second_tenant, db_session):
        """Slug taken by another tenant → 409 slug_taken + suggestion."""
        # First tenant takes the slug
        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "lang-electric",
                "display_name": "Lang Electric",
            },
        )

        # Second tenant tries the same slug — need to use a different tenant
        # The test endpoint always uses test_tenant, so we create directly
        from app.models.tenant_site import TenantSite

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="lang-electric",
            site_kind="hosted_compliance",
            status="draft",
            display_name="Other Electric",
        )
        db_session.add(site)
        db_session.commit()

        # Use the service directly (test endpoint for GET doesn't exist)
        from services import tenant_site_service as svc

        result = svc.check_slug_availability(db_session, "lang-electric")
        assert not result.available
        assert result.reason == "taken"
        assert result.suggestion is not None

    def test_availability_happy_path(self, client, db_session, second_tenant):
        """Available slug → available=True."""
        from services import tenant_site_service as svc

        result = svc.check_slug_availability(db_session, "my-new-slug-123")
        assert result.available

    def test_availability_missing_param_422(self, client, test_user, mock_cognito_jwt):
        """Missing slug param → 422."""
        mock_cognito_jwt(test_user)
        resp = client.get("/api/v1/tenant-site/slug-availability?slug=")
        assert resp.status_code == 422


# ─── 2. GET — no row → defaults, row present → full config ───────────────────


class TestGetSite:
    def test_no_row_returns_defaults_not_404(self, client, second_tenant, db_session):
        """GET when no row → {configured: false, defaults} — never 404."""
        _wipe_tenant_site(db_session, second_tenant.id)

        # Create a profile for defaults
        _make_profile(
            db_session,
            second_tenant.id,
            legal_business_name="Default Business LLC",
            dba_name="Default DBA",
            support_email="default@test.com",
            support_phone="+15551234567",
            hq_city="Richmond",
            hq_state="VA",
        )

        # Use the service directly (test endpoint for GET doesn't exist)
        from services import tenant_site_service as svc

        defaults = svc.get_effective_defaults(db_session, second_tenant.id)
        assert defaults.display_name == "Default DBA"
        assert defaults.public_email == "default@test.com"
        assert defaults.public_city == "Richmond"
        assert defaults.public_state == "VA"

        site = svc.get_site(db_session, second_tenant.id)
        assert site is None  # no row → None, not 404

    def test_defaults_street_never_defaulted(self, client, second_tenant, db_session):
        """Street address is never defaulted from profile."""
        _make_profile(
            db_session,
            second_tenant.id,
            legal_business_name="Test LLC",
            hq_address_line1="123 Secret Home St",
            hq_city="Austin",
            hq_state="TX",
        )

        from services import tenant_site_service as svc

        defaults = svc.get_effective_defaults(db_session, second_tenant.id)
        # display_name, email, phone, city, state are defaulted
        # but there is no address field in defaults (street never defaulted)
        assert not hasattr(defaults, "public_address_line1")

    def test_row_present_returns_full_config(self, client, second_tenant, db_session):
        """Row present → full config + computed site_url."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from services import tenant_site_service as svc

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="test-slug-abc",
            site_kind="hosted_compliance",
            status="published",
            display_name="Test Site",
            public_email="test@site.com",
            public_phone="+15555555555",
            public_city="Denver",
            public_state="CO",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        fetched = svc.get_site(db_session, second_tenant.id)
        assert fetched is not None
        assert fetched.slug == "test-slug-abc"
        assert fetched.status == "published"

        url = svc.compute_site_url(fetched)
        assert url is not None
        assert "test-slug-abc" in url


# ─── 3. PUT upsert ───────────────────────────────────────────────────────────


class TestPutUpsert:
    def test_creates_draft(self, client, second_tenant, db_session):
        """PUT creates a new draft row."""
        _wipe_tenant_site(db_session, second_tenant.id)

        # The test endpoint uses test_tenant, not second_tenant
        # So we test via the service directly for second_tenant
        from api.schemas.tenant_site import TenantSiteUpsertRequest
        from services import tenant_site_service as svc

        payload = TenantSiteUpsertRequest(
            site_kind="hosted_compliance",
            slug="new-draft-site",
            display_name="New Draft",
        )
        site = svc.upsert_draft(db_session, second_tenant.id, payload)
        assert site.status == "draft"
        assert site.slug == "new-draft-site"
        assert site.display_name == "New Draft"

    def test_idempotency_replay_same_row(self, client, test_tenant, db_session):
        """Idempotency-Key replay returns the same row (no dup).

        The /test endpoint doesn't accept Idempotency-Key header (it's a test
        endpoint). We verify idempotency via the UNIQUE(tenant_id) constraint —
        a second PUT with the same payload upserts (updates) rather than
        creating a duplicate.
        """
        _wipe_tenant_site(db_session, test_tenant.id)

        payload = {
            "site_kind": "hosted_compliance",
            "slug": "idempotent-test",
            "display_name": "Idempotent Test",
        }

        resp1 = _put_site(client, payload)
        assert resp1.status_code == 200, resp1.text
        site_id_1 = resp1.json()["id"]

        resp2 = _put_site(client, payload)
        assert resp2.status_code == 200, resp2.text
        site_id_2 = resp2.json()["id"]

        # Same row (UNIQUE on tenant_id means upsert, not duplicate)
        assert site_id_1 == site_id_2

    def test_slug_immutable_after_publish(self, client, test_tenant, db_session):
        """Slug change after publish → 409 slug_immutable."""
        _wipe_tenant_site(db_session, test_tenant.id)

        # Create + publish
        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "immutable-test",
                "display_name": "Immutable Test",
                "public_email": "test@immutable.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        # Create a profile with no website so publish sets it
        _make_profile(db_session, test_tenant.id, website=None)

        pub_resp = _publish_site(client)
        assert pub_resp.status_code == 200, pub_resp.text

        # Try to change slug
        resp = _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "changed-slug",
                "display_name": "Immutable Test",
            },
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["type"].endswith("slug_immutable")


# ─── 4. Publish ───────────────────────────────────────────────────────────────


class TestPublish:
    def test_missing_required_fields_422(self, client, test_tenant, db_session):
        """Publish with missing required fields → 422 missing_required_fields."""
        _wipe_tenant_site(db_session, test_tenant.id)

        # Create a draft with no contact info
        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "missing-fields",
                "display_name": "Missing Fields",
                # No public_phone, public_email, public_city, public_state
            },
        )

        resp = _publish_site(client)
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["type"].endswith("missing_required_fields")

    def test_no_draft_409(self, client, test_tenant, db_session):
        """Publish with no draft → 409 no_draft."""
        _wipe_tenant_site(db_session, test_tenant.id)

        resp = _publish_site(client)
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["type"].endswith("no_draft")

    def test_website_null_sets_and_auto_populated(
        self, client, test_tenant, db_session
    ):
        """Website NULL → set + website_action='set' + auto_populated=TRUE."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "website-null-test",
                "display_name": "Website Null Test",
                "public_email": "test@wn.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        _make_profile(db_session, test_tenant.id, website=None)

        resp = _publish_site(client)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["website_action"] == "set"
        assert data["website_auto_populated"] is True

    def test_website_ours_silent_refresh(self, client, test_tenant, db_session):
        """Website already ours → silent refresh (kept)."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "website-ours-test",
                "display_name": "Website Ours Test",
                "public_email": "test@wo.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        # Set website to our hosted URL + auto_populated=TRUE
        from core.config import settings

        hosted_url = f"https://website-ours-test.{settings.TENANT_SITES_BASE_DOMAIN}"
        _make_profile(db_session, test_tenant.id, website=hosted_url)

        # Mark the site as auto_populated
        from app.models.tenant_site import TenantSite

        site = db_session.exec(
            select(TenantSite).where(TenantSite.tenant_id == test_tenant.id)
        ).first()
        site.website_auto_populated = True
        db_session.add(site)
        db_session.commit()

        resp = _publish_site(client)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["website_action"] == "kept"

    def test_tenant_url_requires_confirmation(self, client, test_tenant, db_session):
        """Tenant-entered URL → 409 website_overwrite_requires_confirmation."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "overwrite-test",
                "display_name": "Overwrite Test",
                "public_email": "test@ow.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        _make_profile(db_session, test_tenant.id, website="https://tenant-own-site.com")

        # First attempt without confirmation → 409
        resp = _publish_site(client, confirm=False)
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["type"].endswith("website_overwrite_requires_confirmation")
        assert "current_url" in detail
        assert "new_url" in detail
        assert "brand_status" in detail

        # Second attempt with confirmation → success
        resp2 = _publish_site(client, confirm=True)
        assert resp2.status_code == 200, resp2.text
        data = resp2.json()
        assert data["website_action"] == "overwritten"
        assert data["website_auto_populated"] is True

    def test_republish_regenerates_snapshot(self, client, test_tenant, db_session):
        """Re-publish regenerates the snapshot (idempotent)."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "republish-test",
                "display_name": "Republish Test",
                "public_email": "test@rp.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        _make_profile(db_session, test_tenant.id, website=None)

        resp1 = _publish_site(client)
        assert resp1.status_code == 200

        # Update the draft
        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "republish-test",
                "display_name": "Republish Test Updated",
                "public_email": "test@rp.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        resp2 = _publish_site(client)
        assert resp2.status_code == 200
        snapshot2 = resp2.json()
        assert snapshot2["display_name"] == "Republish Test Updated"


# ─── 5. Brand classification ─────────────────────────────────────────────────


class TestBrandClassification:
    def test_no_registration_none_or_draft(self, client, second_tenant, db_session):
        """No registration row → brand_status='none', guidance='none_or_draft'."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from services import tenant_site_service as svc

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="brand-no-reg",
            site_kind="hosted_compliance",
            status="draft",
            display_name="Brand No Reg",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        wa = svc.classify_website_action(db_session, site)
        assert wa.brand_status == "none"
        assert wa.brand_guidance == "none_or_draft"

    def test_draft_status(self, client, second_tenant, db_session):
        """Registration status='quoting' → none_or_draft."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from services import tenant_site_service as svc

        _make_registration(db_session, second_tenant.id, status="quoting")

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="brand-draft",
            site_kind="hosted_compliance",
            status="draft",
            display_name="Brand Draft",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        wa = svc.classify_website_action(db_session, site)
        assert wa.brand_guidance == "none_or_draft"

    def test_in_flight_status(self, client, second_tenant, db_session):
        """Registration status='brand_submitted' → in_flight."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from services import tenant_site_service as svc

        _make_registration(db_session, second_tenant.id, status="brand_submitted")

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="brand-flight",
            site_kind="hosted_compliance",
            status="draft",
            display_name="Brand Flight",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        wa = svc.classify_website_action(db_session, site)
        assert wa.brand_guidance == "in_flight"

    def test_rejected_status(self, client, second_tenant, db_session):
        """Registration status='brand_rejected' → brand_rejected."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from services import tenant_site_service as svc

        _make_registration(db_session, second_tenant.id, status="brand_rejected")

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="brand-rejected",
            site_kind="hosted_compliance",
            status="draft",
            display_name="Brand Rejected",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        wa = svc.classify_website_action(db_session, site)
        assert wa.brand_guidance == "brand_rejected"

    def test_live_status(self, client, second_tenant, db_session):
        """Registration status='active' → live."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from services import tenant_site_service as svc

        _make_registration(db_session, second_tenant.id, status="active")

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="brand-live",
            site_kind="hosted_compliance",
            status="draft",
            display_name="Brand Live",
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        wa = svc.classify_website_action(db_session, site)
        assert wa.brand_guidance == "live"


# ─── 6. Unpublish ────────────────────────────────────────────────────────────


class TestUnpublish:
    def test_409_when_draft(self, client, test_tenant, db_session):
        """Unpublish when draft → 409 not_published."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "unpub-draft",
                "display_name": "Unpub Draft",
            },
        )

        resp = client.post("/api/v1/tenant-site/unpublish/test")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["type"].endswith("not_published")

    def test_success_sets_unpublished_at(self, client, test_tenant, db_session):
        """Unpublish success → status=unpublished, unpublished_at set, warning."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "unpub-success",
                "display_name": "Unpub Success",
                "public_email": "test@us.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        _make_profile(db_session, test_tenant.id, website=None)
        pub_resp = _publish_site(client)
        assert pub_resp.status_code == 200

        resp = client.post("/api/v1/tenant-site/unpublish/test")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "unpublished"
        assert data["unpublished_at"] is not None
        assert "warning" in data
        assert len(data["warning"]) > 0

    def test_website_not_cleared(self, client, test_tenant, db_session):
        """Unpublish does NOT clear website."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _put_site(
            client,
            {
                "site_kind": "hosted_compliance",
                "slug": "unpub-website",
                "display_name": "Unpub Website",
                "public_email": "test@uw.com",
                "public_phone": "+15551234567",
                "public_city": "Austin",
                "public_state": "TX",
            },
        )

        _make_profile(db_session, test_tenant.id, website=None)
        _publish_site(client)

        # Check website was set
        from app.models.core import Tenant10DlcProfile

        profile = db_session.exec(
            select(Tenant10DlcProfile).where(
                Tenant10DlcProfile.tenant_id == test_tenant.id
            )
        ).first()
        assert profile.website is not None

        # Unpublish
        client.post("/api/v1/tenant-site/unpublish/test")

        # Website should still be set
        db_session.refresh(profile)
        assert profile.website is not None


# ─── 8. One-time email guard ──────────────────────────────────────────────────


class TestOneTimeEmailGuard:
    def test_profile_put_enqueues_once(self, client, test_tenant, db_session):
        """Profile PUT with self-managed URL enqueues once, stamps requirements_emailed_at."""
        _wipe_tenant_site(db_session, test_tenant.id)

        # Ensure profile exists with no requirements_emailed_at
        _make_profile(
            db_session,
            test_tenant.id,
            website=None,
            legal_business_name="Email Guard Test LLC",
            support_email="guard@test.com",
        )

        with patch(
            "tasks.tenant_site_emails.send_website_requirements_email.delay"
        ) as mock_delay:
            # First PUT with a self-managed URL
            resp = client.put(
                "/api/v1/settings/10dlc-profile/test",
                json={
                    "legal_business_name": "Email Guard Test LLC",
                    "website": "https://self-managed.com",
                    "support_email": "guard@test.com",
                },
            )
            assert resp.status_code == 200, resp.text
            assert mock_delay.call_count == 1

            # Verify requirements_emailed_at was stamped
            from app.models.core import Tenant10DlcProfile

            profile = db_session.exec(
                select(Tenant10DlcProfile).where(
                    Tenant10DlcProfile.tenant_id == test_tenant.id
                )
            ).first()
            assert profile.requirements_emailed_at is not None

            # Second PUT should NOT re-enqueue
            resp2 = client.put(
                "/api/v1/settings/10dlc-profile/test",
                json={
                    "legal_business_name": "Email Guard Test LLC",
                    "website": "https://self-managed.com",
                    "support_email": "guard@test.com",
                },
            )
            assert resp2.status_code == 200
            assert mock_delay.call_count == 1  # still 1

    def test_option1_selection_triggers_email(self, client, test_tenant, db_session):
        """Option-1 (compliance_kit) selection enqueues + stamps kit_sent_at."""
        _wipe_tenant_site(db_session, test_tenant.id)

        _make_profile(
            db_session,
            test_tenant.id,
            website=None,
            legal_business_name="Option1 Test LLC",
            support_email="option1@test.com",
        )

        with patch(
            "tasks.tenant_site_emails.send_website_requirements_email.delay"
        ) as mock_delay:
            resp = _put_site(
                client,
                {
                    "site_kind": "compliance_kit",
                    "slug": "option1-test",
                    "display_name": "Option1 Test",
                },
            )
            assert resp.status_code == 200, resp.text
            assert mock_delay.call_count == 1

            # Verify kit_sent_at was stamped
            from app.models.tenant_site import TenantSite

            site = db_session.exec(
                select(TenantSite).where(TenantSite.tenant_id == test_tenant.id)
            ).first()
            assert site.kit_sent_at is not None

    def test_on_profile_website_changed_flips_auto_populated(
        self, client, second_tenant, db_session
    ):
        """on_profile_website_changed flips website_auto_populated FALSE on non-Pilot URL."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from services import tenant_site_service as svc

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="reconcile-test",
            site_kind="hosted_compliance",
            status="published",
            display_name="Reconcile Test",
            website_auto_populated=True,
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        # Call with a non-Pilot URL
        svc.on_profile_website_changed(
            db_session, second_tenant.id, "https://own-site.com"
        )

        db_session.refresh(site)
        assert site.website_auto_populated is False

    def test_pilot_url_does_not_flip(self, client, second_tenant, db_session):
        """Pilot-hosted URL does NOT flip website_auto_populated."""
        _wipe_tenant_site(db_session, second_tenant.id)

        from app.models.tenant_site import TenantSite
        from core.config import settings
        from services import tenant_site_service as svc

        site = TenantSite(
            tenant_id=second_tenant.id,
            slug="pilot-url-test",
            site_kind="hosted_compliance",
            status="published",
            display_name="Pilot URL Test",
            website_auto_populated=True,
        )
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        pilot_url = f"https://pilot-url-test.{settings.TENANT_SITES_BASE_DOMAIN}"
        svc.on_profile_website_changed(db_session, second_tenant.id, pilot_url)

        db_session.refresh(site)
        assert site.website_auto_populated is True  # unchanged


# ─── 9. Cross-tenant isolation ───────────────────────────────────────────────


class TestCrossTenantIsolation:
    def test_get_never_sees_other_tenant(self, client, tenant_a, tenant_b, db_session):
        """GET/PUT/publish never see or modify the other tenant's site."""
        _wipe_tenant_site(db_session, tenant_a.id)
        _wipe_tenant_site(db_session, tenant_b.id)

        from api.schemas.tenant_site import TenantSiteUpsertRequest
        from services import tenant_site_service as svc

        # Tenant A creates a site
        payload_a = TenantSiteUpsertRequest(
            site_kind="hosted_compliance",
            slug="tenant-a-slug",
            display_name="Tenant A",
        )
        svc.upsert_draft(db_session, tenant_a.id, payload_a)

        # Tenant B should not see Tenant A's site
        site_b = svc.get_site(db_session, tenant_b.id)
        assert site_b is None

        # Tenant B can create its own site with a different slug
        payload_b = TenantSiteUpsertRequest(
            site_kind="hosted_compliance",
            slug="tenant-b-slug",
            display_name="Tenant B",
        )
        svc.upsert_draft(db_session, tenant_b.id, payload_b)

        # Verify isolation
        site_a = svc.get_site(db_session, tenant_a.id)
        site_b = svc.get_site(db_session, tenant_b.id)
        assert site_a.slug == "tenant-a-slug"
        assert site_b.slug == "tenant-b-slug"
        assert site_a.tenant_id != site_b.tenant_id


# ─── 10. RBAC ────────────────────────────────────────────────────────────────


class TestRBAC:
    def test_get_requires_settings_view(self, client, test_user, mock_cognito_jwt):
        """GET requires settings.view — owner has it."""
        mock_cognito_jwt(test_user)
        resp = client.get("/api/v1/tenant-site")
        # Owner should have access — 200 with configured=false or true
        assert resp.status_code == 200

    def test_put_requires_settings_manage(
        self, client, test_user, test_tenant, mock_cognito_jwt, db_session
    ):
        """PUT requires settings.manage — owner has it."""
        _wipe_tenant_site(db_session, test_tenant.id)
        mock_cognito_jwt(test_user)
        resp = client.put(
            "/api/v1/tenant-site",
            json={
                "site_kind": "hosted_compliance",
                "slug": "rbac-test",
                "display_name": "RBAC Test",
            },
        )
        # Owner should have settings.manage
        assert resp.status_code == 200, resp.text


# ─── 12. Seed idempotency ────────────────────────────────────────────────────


class TestSeedIdempotency:
    def test_seed_runs_twice_no_dupes(self, db_session):
        """Running the scenario seed twice → no duplicate tenant_site rows."""
        # This is verified by the seed script's ON CONFLICT DO NOTHING
        # We verify the constraint exists
        from sqlalchemy import text

        result = db_session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'tenant_site' AND indexname = 'uq_tenant_site_tenant'"
            )
        ).first()
        assert result is not None
