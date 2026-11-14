"""
Batch B21 — FIND-159: response_model verification on POST /api/v1/quotes/{id}/save-as-template
================================================================================================

FIND-159 (S3 Medium): Verify that `POST /api/v1/quotes/{id}/save-as-template` declares
`response_model=QuoteSaveAsTemplateResponse` and returns a typed response model instance,
not a plain dict.

Verification result: CORRECT — no code changes required.
  - Decorator at quotes.py:2077 declares `response_model=QuoteSaveAsTemplateResponse`
  - Endpoint returns `QuoteSaveAsTemplateResponse(template_id=..., name=..., ...)` at line 2187
  - Schema class `QuoteSaveAsTemplateResponse` defined in api/schemas/quotes.py with 5 fields
"""

import inspect

# ─────────────────────────────────────────────────────────────────────────────
# FIND-159 — response_model decorator verification
# ─────────────────────────────────────────────────────────────────────────────


class TestFind159SaveAsTemplateResponseModel:
    """FIND-159: POST /quotes/{id}/save-as-template must declare response_model=QuoteSaveAsTemplateResponse."""

    def test_save_as_template_decorator_has_response_model(self):
        """Decorator must include response_model=QuoteSaveAsTemplateResponse."""
        import api.routes.quotes as mod

        src = inspect.getsource(mod)
        assert "response_model=QuoteSaveAsTemplateResponse" in src, (
            "quotes.py save-as-template endpoint must declare "
            "response_model=QuoteSaveAsTemplateResponse on its @router.post decorator"
        )

    def test_save_as_template_returns_typed_response_not_dict(self):
        """Endpoint must return QuoteSaveAsTemplateResponse(...), not a plain dict."""
        import api.routes.quotes as mod

        src = inspect.getsource(mod)
        assert "return QuoteSaveAsTemplateResponse(" in src, (
            "save_quote_as_template must return QuoteSaveAsTemplateResponse(...) "
            "instead of a plain dict"
        )

    def test_save_as_template_route_registered(self):
        """POST /{id}/save-as-template route must be registered on the quotes router."""
        from api.routes.quotes import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        matching = [r for r in routes if "save-as-template" in r]
        assert matching, (
            f"save-as-template route not found on quotes router. Available: {routes}"
        )

    def test_save_as_template_schema_has_required_fields(self):
        """QuoteSaveAsTemplateResponse must expose template_id, name, style, category, line_count."""
        from api.schemas.quotes import QuoteSaveAsTemplateResponse

        fields = QuoteSaveAsTemplateResponse.model_fields
        required_fields = {"template_id", "name", "style", "category", "line_count"}
        missing = required_fields - set(fields.keys())
        assert not missing, f"QuoteSaveAsTemplateResponse is missing fields: {missing}"

    def test_save_as_template_schema_instantiation(self):
        """QuoteSaveAsTemplateResponse must be instantiable with all required fields."""
        import uuid

        from api.schemas.quotes import QuoteSaveAsTemplateResponse

        tid = uuid.uuid4()
        resp = QuoteSaveAsTemplateResponse(
            template_id=tid,
            name="Panel Upgrade Template",
            style="component",
            category="electrical",
            line_count=5,
        )
        assert resp.template_id == tid
        assert resp.name == "Panel Upgrade Template"
        assert resp.style == "component"
        assert resp.category == "electrical"
        assert resp.line_count == 5

    def test_save_as_template_schema_category_optional(self):
        """QuoteSaveAsTemplateResponse must accept category=None (Optional field)."""
        import uuid

        from api.schemas.quotes import QuoteSaveAsTemplateResponse

        resp = QuoteSaveAsTemplateResponse(
            template_id=uuid.uuid4(),
            name="No-Category Template",
            style="lump_sum",
            category=None,
            line_count=0,
        )
        assert resp.category is None
