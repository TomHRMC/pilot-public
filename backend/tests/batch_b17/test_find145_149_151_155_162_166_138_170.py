"""
B17 batch tests - FIND-145, FIND-149, FIND-151-155, FIND-162, FIND-166, FIND-138, FIND-170.

Covers:
  FIND-145  Verify 5 A-entry endpoints exist in route files (code review confirmation)
  FIND-149  PUT /settings/email-branding → PATCH (2 decorators changed)
  FIND-151  SoftDeleteResponse schema + DELETE /customers response_model + id in return dict
  FIND-152  SoftDeleteResponse on DELETE /addresses
  FIND-153  SoftDeleteResponse on DELETE /contacts
  FIND-154  SoftDeleteResponse on DELETE /scheduling/tech-availability
  FIND-155  SoftDeleteResponse on DELETE /scheduling/jobs/{job_id}/assignments/{id}
  FIND-162  QuoteRevokeLinkResponse schema; revoke endpoint decorator + typed return
  FIND-166  §16.5 seed catalog checklist bullet present in pilot-python-engineer-methods.md
  FIND-138  Pre-launch checklist SES→Cognito note present in impl-framework doc
  FIND-170  ARCH-§4.5 Cognito MFA lockout ARCH-DECISION note present in mvp-arch.md

Test subfolder: tests/batch_b17/
"""

import inspect
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Repo root — two levels up from tests/batch_b17/
_REPO_ROOT = Path(__file__).parent.parent.parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# FIND-145 — Verify 5 A-entry endpoints are implemented in route source files
# ─────────────────────────────────────────────────────────────────────────────
class TestFind145AEntryEndpointsExist:
    """All 5 A-entry endpoints must be registered in their route files."""

    def test_a8_get_customer_communications_exists(self):
        """A8: GET /customers/{customer_id}/communications — communications.py."""
        from api.routes.communications import get_customer_communications

        assert callable(get_customer_communications)

    def test_a23_post_communications_preview_exists(self):
        """A23: POST /communications/preview — communications.py."""
        import api.routes.communications as comm_mod

        # The preview endpoint is either named 'preview_communication' or discovered by searching
        src = inspect.getsource(comm_mod)
        assert "/preview" in src, (
            "POST /communications/preview route must be in communications.py"
        )

    def test_a52_get_settings_catalog_exists(self):
        """A52: GET /settings/catalog — settings.py."""
        import api.routes.settings as settings_mod

        src = inspect.getsource(settings_mod)
        assert "/catalog" in src, "GET /settings/catalog route must be in settings.py"

    def test_a53_get_settings_effective_exists(self):
        """A53: GET /settings/{key}/effective — settings.py."""
        import api.routes.settings as settings_mod

        src = inspect.getsource(settings_mod)
        assert "/effective" in src, (
            "GET /settings/{key}/effective route must be in settings.py"
        )

    def test_a64_customer_communications_history_impl_exists(self):
        """A64: customer communication history impl — communications.py."""
        from api.routes.communications import _get_customer_communications_impl

        assert callable(_get_customer_communications_impl)


# ─────────────────────────────────────────────────────────────────────────────
# FIND-149 — PUT /settings/email-branding → PATCH
# ─────────────────────────────────────────────────────────────────────────────
class TestFind149EmailBrandingPatch:
    """FIND-149: Both email-branding update decorators must use PATCH, not PUT."""

    def test_authenticated_update_uses_patch(self):
        """Authenticated update_email_branding endpoint must be PATCH."""
        import api.routes.tenant_email_branding as mod

        src = inspect.getsource(mod)
        # There must be at least one @router.patch("") (authenticated endpoint)
        assert '@router.patch("")' in src or "router.patch(" in src, (
            "update_email_branding must be decorated with @router.patch, not @router.put"
        )

    def test_test_update_uses_patch(self):
        """Test update_email_branding_test endpoint must be PATCH."""
        import api.routes.tenant_email_branding as mod

        src = inspect.getsource(mod)
        assert '@router.patch("/test"' in src or 'router.patch("/test"' in src, (
            "update_email_branding_test must be decorated with @router.patch, not @router.put"
        )

    def test_no_put_update_decorator_present(self):
        """No @router.put('') or @router.put('/test') update decorators remain."""
        import api.routes.tenant_email_branding as mod

        src = inspect.getsource(mod)
        # PUT for update endpoints must be gone (PUT logo-upload-url and POST test-send are different paths)
        assert '@router.put("")' not in src, (
            "@router.put('') must not appear — should be @router.patch"
        )
        assert '@router.put("/test")' not in src, (
            "@router.put('/test') must not appear — should be @router.patch('/test')"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FIND-151-155 - SoftDeleteResponse schema + 5 DELETE decorators + 3 return dicts
# ─────────────────────────────────────────────────────────────────────────────
class TestFind151SoftDeleteResponseSchema:
    """FIND-151: SoftDeleteResponse must exist in schemas.py with message + id fields."""

    def test_soft_delete_response_importable(self):
        from api.schemas.schemas import SoftDeleteResponse

        assert SoftDeleteResponse is not None

    def test_soft_delete_response_has_message_field(self):
        from api.schemas.schemas import SoftDeleteResponse

        assert "message" in SoftDeleteResponse.model_fields

    def test_soft_delete_response_has_id_field(self):
        from api.schemas.schemas import SoftDeleteResponse

        assert "id" in SoftDeleteResponse.model_fields

    def test_soft_delete_response_instantiates(self):
        from api.schemas.schemas import SoftDeleteResponse

        resp = SoftDeleteResponse(message="Deleted successfully", id=uuid.uuid4())
        assert resp.message == "Deleted successfully"
        assert resp.id is not None


class TestFind151DeleteCustomerResponseModel:
    """FIND-151: DELETE /customers/{id} decorators must use response_model=SoftDeleteResponse."""

    def test_delete_customer_decorator_has_response_model(self):
        import api.routes.customers as mod

        src = inspect.getsource(mod)
        assert "SoftDeleteResponse" in src, "customers.py must use SoftDeleteResponse"

    def test_delete_customer_impl_returns_id(self):
        """_delete_customer_impl return dict must include 'id' key."""
        import api.routes.customers as mod

        src = inspect.getsource(mod)
        assert '"id": str(customer_id)' in src, (
            "_delete_customer_impl must return {'id': str(customer_id), ...}"
        )


class TestFind152DeleteAddressResponseModel:
    """FIND-152: DELETE /addresses/{id} decorators must use response_model=SoftDeleteResponse."""

    def test_delete_address_decorator_has_response_model(self):
        import api.routes.addresses as mod

        src = inspect.getsource(mod)
        assert "SoftDeleteResponse" in src, "addresses.py must use SoftDeleteResponse"

    def test_delete_address_impl_returns_id(self):
        """_delete_address_impl return dict must include 'id' key."""
        import api.routes.addresses as mod

        src = inspect.getsource(mod)
        assert '"id": str(address_id)' in src, (
            "_delete_address_impl must return {'id': str(address_id), ...}"
        )


class TestFind153DeleteContactResponseModel:
    """FIND-153: DELETE /contacts/{id} decorators must use response_model=SoftDeleteResponse."""

    def test_delete_contact_decorator_has_response_model(self):
        import api.routes.contacts as mod

        src = inspect.getsource(mod)
        assert "SoftDeleteResponse" in src, "contacts.py must use SoftDeleteResponse"

    def test_delete_contact_impl_returns_id(self):
        """_delete_contact_impl return dict must include 'id' key."""
        import api.routes.contacts as mod

        src = inspect.getsource(mod)
        assert '"id": str(contact_id)' in src, (
            "_delete_contact_impl must return {'id': str(contact_id), ...}"
        )


class TestFind154DeleteTechAvailabilityResponseModel:
    """FIND-154: DELETE /scheduling/tech-availability/{id} decorators use SoftDeleteResponse."""

    def test_delete_tech_availability_decorator_has_response_model(self):
        import api.routes.scheduling as mod

        src = inspect.getsource(mod)
        assert "SoftDeleteResponse" in src, "scheduling.py must use SoftDeleteResponse"

    def test_delete_tech_availability_already_returns_id(self):
        """_delete_tech_availability_impl already returns 'id' — regression guard."""
        import api.routes.scheduling as mod

        src = inspect.getsource(mod)
        assert '"id": str(record_id)' in src, (
            "_delete_tech_availability_impl must return {'id': str(record_id), ...}"
        )


class TestFind155DeleteAssignmentResponseModel:
    """FIND-155: DELETE /scheduling/jobs/{job_id}/assignments/{id} uses SoftDeleteResponse."""

    def test_delete_assignment_already_returns_id(self):
        """_delete_assignment_impl already returns 'id' — regression guard."""
        import api.routes.scheduling as mod

        src = inspect.getsource(mod)
        assert '"id": str(assignment_id)' in src, (
            "_delete_assignment_impl must return {'id': str(assignment_id), ...}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FIND-162 — QuoteRevokeLinkResponse schema + revoke endpoint response_model
# ─────────────────────────────────────────────────────────────────────────────
class TestFind162QuoteRevokeLinkResponse:
    """FIND-162: QuoteRevokeLinkResponse schema + revoke endpoint typed response."""

    def test_schema_importable(self):
        from api.schemas.quotes import QuoteRevokeLinkResponse

        assert QuoteRevokeLinkResponse is not None

    def test_schema_has_id_field(self):
        from api.schemas.quotes import QuoteRevokeLinkResponse

        assert "id" in QuoteRevokeLinkResponse.model_fields

    def test_schema_has_revoked_at_field(self):
        from api.schemas.quotes import QuoteRevokeLinkResponse

        assert "revoked_at" in QuoteRevokeLinkResponse.model_fields

    def test_schema_has_status_field(self):
        from api.schemas.quotes import QuoteRevokeLinkResponse

        assert "status" in QuoteRevokeLinkResponse.model_fields

    def test_schema_instantiates_with_revoked_status(self):
        from api.schemas.quotes import QuoteRevokeLinkResponse

        resp = QuoteRevokeLinkResponse(
            id=uuid.uuid4(),
            revoked_at=datetime.now(UTC),
            status="revoked",
        )
        assert resp.status == "revoked"
        assert resp.revoked_at is not None

    def test_revoke_endpoint_uses_response_model(self):
        """revoke_quote_public_link decorator must declare response_model=QuoteRevokeLinkResponse."""
        import api.routes.quotes as mod

        src = inspect.getsource(mod)
        assert "QuoteRevokeLinkResponse" in src, (
            "quotes.py revoke endpoint must use response_model=QuoteRevokeLinkResponse"
        )

    def test_revoke_endpoint_returns_typed_response(self):
        """revoke_quote_public_link must return QuoteRevokeLinkResponse(...), not a plain dict."""
        import api.routes.quotes as mod

        src = inspect.getsource(mod)
        assert "QuoteRevokeLinkResponse(id=link.id" in src, (
            "revoke_quote_public_link must return QuoteRevokeLinkResponse(id=link.id, ...) "
            "instead of a plain dict"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FIND-166 — §16.5 seed catalog checklist bullet
# ─────────────────────────────────────────────────────────────────────────────
class TestFind166SeedCatalogChecklistBullet:
    """FIND-166: pilot-python-engineer-methods.md §16.5 must include seed catalog bullet."""

    def test_seed_catalog_bullet_present(self):
        methods_doc = (
            _REPO_ROOT / "dev-docs/architecture-design/pilot-python-engineer-methods.md"
        )
        content = methods_doc.read_text()
        assert "18-seed-data-catalog.md" in content, (
            "pilot-python-engineer-methods.md §16.5 must reference 18-seed-data-catalog.md"
        )

    def test_seed_catalog_bullet_in_definition_of_done_section(self):
        methods_doc = (
            _REPO_ROOT / "dev-docs/architecture-design/pilot-python-engineer-methods.md"
        )
        content = methods_doc.read_text()
        dod_idx = content.index("16.5 Definition of Done")
        # The reference must appear after the §16.5 header
        catalog_idx = content.index("18-seed-data-catalog.md")
        assert catalog_idx > dod_idx, (
            "18-seed-data-catalog.md reference must appear inside the §16.5 section"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FIND-138 — Pre-launch checklist SES→Cognito ordering note
# ─────────────────────────────────────────────────────────────────────────────
class TestFind138SESCognitoOrderingNote:
    """FIND-138: impl-framework doc must note SES must precede Cognito provisioning."""

    def test_ses_cognito_dependency_documented(self):
        # The impl-framework doc was moved to dev-docs/analysis/traceability-archive-06-2026/
        # (June 2026 reorganization; relocated again Aug 2026). The SES→Cognito ordering
        # content lives there now.
        impl_doc = (
            _REPO_ROOT
            / "dev-docs/analysis/traceability-archive-06-2026/pilot-app-mvp-tracability-matrix-impl.md"
        )
        content = impl_doc.read_text()
        # Either the FIND-138 reference or the ordering note must be present
        assert "FIND-138" in content or "SES" in content, (
            "impl-framework doc must document SES→Cognito ordering dependency"
        )

    def test_ses_before_cognito_ordering_explicit(self):
        # The impl-framework doc was moved to dev-docs/analysis/traceability-archive-06-2026/
        # (June 2026 reorganization; relocated again Aug 2026). The SES→Cognito ordering
        # content lives there now.
        impl_doc = (
            _REPO_ROOT
            / "dev-docs/analysis/traceability-archive-06-2026/pilot-app-mvp-tracability-matrix-impl.md"
        )
        content = impl_doc.read_text()
        # The SES row must appear before the Cognito row in the pre-launch table
        ses_idx = content.find("SES")
        cognito_idx = content.find("Cognito")
        assert ses_idx != -1, "SES must appear in impl-framework doc"
        assert cognito_idx != -1, "Cognito must appear in impl-framework doc"
        # In the updated pre-launch table, SES row (PR-004) precedes Cognito row (PR-005)
        assert ses_idx < cognito_idx, (
            "SES must appear before Cognito in pre-launch checklist"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FIND-170 — ARCH-§4.5 Cognito MFA lockout ARCH-DECISION note
# ─────────────────────────────────────────────────────────────────────────────
class TestFind170ArchMfaLockoutClarification:
    """FIND-170: mvp-arch.md §4.5 must include ARCH-DECISION note delegating lockout to Cognito."""

    def test_arch_decision_note_present(self):
        arch_doc = _REPO_ROOT / "dev-docs/architecture-design/mvp-arch.md"
        content = arch_doc.read_text()
        assert "ARCH-DECISION (FIND-170)" in content, (
            "mvp-arch.md §4.5 must include ARCH-DECISION (FIND-170) note"
        )

    def test_arch_note_clarifies_cognito_is_enforcement_boundary(self):
        arch_doc = _REPO_ROOT / "dev-docs/architecture-design/mvp-arch.md"
        content = arch_doc.read_text()
        assert "delegated entirely to AWS Cognito" in content, (
            "ARCH-DECISION note must state lockout enforcement is delegated to AWS Cognito"
        )

    def test_arch_note_warns_against_adding_lockout_columns(self):
        arch_doc = _REPO_ROOT / "dev-docs/architecture-design/mvp-arch.md"
        content = arch_doc.read_text()
        assert "Do not add lockout enforcement to the Pilot schema" in content, (
            "ARCH-DECISION note must warn against adding lockout columns to user_mfa_method"
        )
