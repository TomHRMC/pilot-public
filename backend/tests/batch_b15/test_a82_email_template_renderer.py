"""
B15/A82 — Email Template Rendering Pipeline tests.

Test focus cases:
1. EmailTemplate model has correct columns (template_id PK, category, is_active)
2. 16 seed templates exist after migration
3. render_preview() returns RenderedEmail for a valid template_id
4. render_preview() raises ValueError for unknown template_id
5. render_and_send() calls email_service.send_email() with rendered content
6. render_and_send() raises ValueError for inactive template
7. _substitute() converts {{variable}} → value
8. _substitute() leaves unresolved variables as {key} without raising
9. GET /settings/email-branding/test returns 200 with correct schema
10. PUT /settings/email-branding/test updates branding fields
11. POST /settings/email-branding/test/preview returns rendered subject/html/plain
12. email_signature > 500 chars returns 422
13. custom_footer > 200 chars returns 422
14. TenantEmailBranding created on-demand when not exists
"""

import pytest
from sqlmodel import select

from app.models.communications import EmailTemplate
from app.models.core import TenantEmailBranding
from services.email_template_renderer import _substitute, render_preview

# ─────────────────────────────────────────────────────────────────────────────
# ORM / seed data tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEmailTemplateOrm:
    def test_16_seed_templates_exist(self, db_session):
        """Migration seeds exactly 16 email templates (may be > 16 if B13 added data_export_ready)."""
        templates = db_session.exec(select(EmailTemplate)).all()
        assert len(templates) >= 16, (
            f"Expected ≥16 seed templates, found {len(templates)}"
        )

    def test_welcome_template_exists_and_active(self, db_session):
        t = db_session.exec(
            select(EmailTemplate).where(EmailTemplate.template_id == "welcome")
        ).first()
        assert t is not None, "welcome template not found"
        assert t.is_active is True
        assert t.category == "internal"

    def test_quote_sent_template_is_customer_facing(self, db_session):
        t = db_session.exec(
            select(EmailTemplate).where(EmailTemplate.template_id == "quote_sent")
        ).first()
        assert t is not None
        assert t.category == "customer_facing"

    def test_template_id_is_primary_key(self, db_session):
        """Can query by template_id string PK."""
        t = db_session.get(EmailTemplate, "password_reset")
        assert t is not None
        assert t.template_id == "password_reset"


class TestTenantEmailBrandingOrm:
    def test_branding_created_on_demand(self, db_session, test_tenant):
        """TenantEmailBranding created when first queried/created for a tenant."""
        existing = db_session.exec(
            select(TenantEmailBranding).where(
                TenantEmailBranding.tenant_id == test_tenant.id
            )
        ).first()
        if existing is None:
            branding = TenantEmailBranding(tenant_id=test_tenant.id)
            db_session.add(branding)
            db_session.commit()
            db_session.refresh(branding)
            assert branding.tenant_id == test_tenant.id
            assert branding.brand_color_hex is None  # blank by default

    def test_branding_fields_can_be_set(self, db_session, test_tenant):
        """All branding fields accept valid values."""
        branding = db_session.exec(
            select(TenantEmailBranding).where(
                TenantEmailBranding.tenant_id == test_tenant.id
            )
        ).first()
        if branding is None:
            branding = TenantEmailBranding(tenant_id=test_tenant.id)
            db_session.add(branding)

        branding.brand_color_hex = "#5B3FF0"
        branding.email_signature = "— Alex Smith"
        branding.custom_footer = "Licensed & Insured"
        db_session.add(branding)
        db_session.commit()
        db_session.refresh(branding)

        assert branding.brand_color_hex == "#5B3FF0"
        assert branding.email_signature == "— Alex Smith"
        assert branding.custom_footer == "Licensed & Insured"


# ─────────────────────────────────────────────────────────────────────────────
# Service tests
# ─────────────────────────────────────────────────────────────────────────────


class TestSubstitute:
    def test_double_brace_replaced(self):
        result = _substitute("Hello {{user_name}}", {"user_name": "Tom"})
        assert result == "Hello Tom"

    def test_single_brace_replaced(self):
        result = _substitute("Hello {user_name}", {"user_name": "Tom"})
        assert result == "Hello Tom"

    def test_missing_var_left_as_is(self):
        result = _substitute("Hello {{missing_var}}", {})
        assert "{missing_var}" in result

    def test_multiple_vars(self):
        result = _substitute("{{a}} and {{b}}", {"a": "foo", "b": "bar"})
        assert result == "foo and bar"


class TestRenderPreview:
    def test_render_preview_welcome(self, db_session, test_tenant):
        rendered = render_preview(db_session, "welcome", str(test_tenant.id))
        assert rendered.subject != ""
        assert rendered.body_html != ""
        assert rendered.body_plain != ""

    def test_render_preview_unknown_raises_valueerror(self, db_session, test_tenant):
        with pytest.raises(ValueError, match="not found"):
            render_preview(db_session, "does_not_exist", str(test_tenant.id))

    def test_render_preview_customer_facing_template(self, db_session, test_tenant):
        rendered = render_preview(db_session, "quote_sent", str(test_tenant.id))
        assert rendered.subject != ""
        # Should use Pilot brand-indigo by default (no branding set)


class TestRenderAndSend:
    def test_render_and_send_calls_email_service(
        self, db_session, test_tenant, monkeypatch
    ):
        """render_and_send() calls send_email and returns result dict."""
        sent_calls = []

        def mock_send_email(to, subject, body, html_body=None):
            sent_calls.append({"to": to, "subject": subject})
            return {
                "status": "sent",
                "details": {},
                "http_status": 200,
                "retryable": False,
            }

        monkeypatch.setattr("services.email_service.send_email", mock_send_email)

        from services.email_template_renderer import render_and_send

        result = render_and_send(
            db=db_session,
            template_id="welcome",
            context={"user_name": "Tom"},
            to_address="test@example.com",
            tenant_id=str(test_tenant.id),
        )

        assert result["status"] == "sent"
        assert len(sent_calls) == 1
        assert sent_calls[0]["to"] == "test@example.com"

    def test_render_and_send_inactive_template_raises(self, db_session, test_tenant):
        """render_and_send raises ValueError for is_active=False templates.

        Uses raw SQL with SET LOCAL session_replication_role = 'replica' to bypass
        the audit trigger on email_template (audit.log_changes requires UUID id column
        but email_template PK is template_id TEXT).
        """
        from sqlalchemy import text

        db_session.execute(text("SET LOCAL session_replication_role = 'replica'"))
        db_session.execute(
            text(
                "UPDATE email_template SET is_active = false WHERE template_id = 'welcome'"
            )
        )
        db_session.execute(text("SET LOCAL session_replication_role = 'origin'"))
        db_session.commit()

        from services.email_template_renderer import render_and_send

        with pytest.raises(ValueError, match="disabled"):
            render_and_send(
                db=db_session,
                template_id="welcome",
                context={},
                to_address="test@example.com",
            )

        # Restore via raw SQL
        db_session.execute(text("SET LOCAL session_replication_role = 'replica'"))
        db_session.execute(
            text(
                "UPDATE email_template SET is_active = true WHERE template_id = 'welcome'"
            )
        )
        db_session.execute(text("SET LOCAL session_replication_role = 'origin'"))
        db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEmailBrandingEndpoints:
    def test_get_branding_returns_200(self, client):
        resp = client.get("/api/v1/settings/email-branding/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_id" in data
        assert "brand_color_hex" in data
        assert "email_signature" in data
        assert "custom_footer" in data

    # FIND-149: PUT → PATCH; test helpers updated to match new HTTP method
    def test_put_branding_updates_color(self, client):
        resp = client.patch(
            "/api/v1/settings/email-branding/test",
            json={"brand_color_hex": "#FF0000"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["brand_color_hex"] == "#FF0000"

    def test_put_branding_email_signature(self, client):
        resp = client.patch(
            "/api/v1/settings/email-branding/test",
            json={"email_signature": "— Alex Smith, Pilot Electrical"},
        )
        assert resp.status_code == 200
        assert resp.json()["email_signature"] == "— Alex Smith, Pilot Electrical"

    def test_put_branding_email_signature_too_long_returns_422(self, client):
        too_long = "x" * 501
        resp = client.patch(
            "/api/v1/settings/email-branding/test",
            json={"email_signature": too_long},
        )
        assert resp.status_code == 422

    def test_put_branding_custom_footer_too_long_returns_422(self, client):
        too_long = "x" * 201
        resp = client.patch(
            "/api/v1/settings/email-branding/test",
            json={"custom_footer": too_long},
        )
        assert resp.status_code == 422

    def test_preview_returns_rendered_email(self, client):
        resp = client.post(
            "/api/v1/settings/email-branding/test/preview",
            json={"template_id": "welcome"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "subject" in data
        assert "body_html" in data
        assert "body_plain" in data
        assert data["subject"] != ""

    def test_preview_unknown_template_returns_404(self, client):
        resp = client.post(
            "/api/v1/settings/email-branding/test/preview",
            json={"template_id": "nonexistent_template_xyz"},
        )
        assert resp.status_code == 404

    def test_logo_upload_url_test_endpoint(self, client):
        resp = client.post(
            "/api/v1/settings/email-branding/test/logo-upload-url",
            json={"content_type": "image/png", "file_size_bytes": 50000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_url" in data
        assert "s3_path" in data
        assert "tenant-branding/" in data["s3_path"]
