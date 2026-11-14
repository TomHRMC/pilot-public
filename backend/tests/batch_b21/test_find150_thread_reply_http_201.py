"""
Batch B21 — FIND-150: HTTP 201 fix on POST /api/v1/communications/threads/{id}/reply
======================================================================================

FIND-150 (S3 Medium): `POST /api/v1/communications/threads/{thread_id}/reply` was
returning HTTP 200 instead of 201. Sending a reply creates a new message resource —
201 Created is the correct status code per RFC 7231.

Fix applied: Added `status_code=status.HTTP_201_CREATED` to both decorators
(authenticated + test) in `backend/api/routes/communications_threads.py`.
"""

import inspect

# ─────────────────────────────────────────────────────────────────────────────
# FIND-150 — HTTP 201 fix on thread reply endpoint
# ─────────────────────────────────────────────────────────────────────────────


class TestFind150ThreadReplyHttp201:
    """FIND-150: POST /threads/{thread_id}/reply must return HTTP 201 Created."""

    def test_authenticated_reply_endpoint_has_status_201(self):
        """Authenticated POST /threads/{thread_id}/reply decorator must declare status_code=201."""
        import api.routes.communications_threads as mod

        src = inspect.getsource(mod)
        # The fix adds HTTP_201_CREATED to both reply decorators
        assert "HTTP_201_CREATED" in src, (
            "communications_threads.py reply endpoint must declare "
            "status_code=status.HTTP_201_CREATED"
        )

    def test_test_reply_endpoint_has_status_201(self):
        """Test variant POST /threads/test/{thread_id}/reply must also declare status_code=201."""
        from api.routes.communications_threads import router

        # Find all routes with 'reply' in path and verify they have status_code 201
        reply_routes = [
            r for r in router.routes if hasattr(r, "path") and "reply" in r.path
        ]
        assert reply_routes, "No 'reply' routes found on communications_threads router"

        for route in reply_routes:
            assert hasattr(route, "status_code"), (
                f"Route {route.path} has no status_code attribute"
            )
            assert route.status_code == 201, (
                f"Route {route.path} must return 201 Created, got {route.status_code}"
            )

    def test_reply_route_registered(self):
        """POST /threads/{thread_id}/reply route must be registered."""
        from api.routes.communications_threads import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        assert any("reply" in r for r in routes), (
            f"No 'reply' route found on communications_threads router. Routes: {routes}"
        )

    def test_reply_response_model_still_present(self):
        """response_model=ReplyResponse must still be declared after the 201 fix."""
        import api.routes.communications_threads as mod

        src = inspect.getsource(mod)
        assert "response_model=ReplyResponse" in src, (
            "communications_threads.py reply endpoint must still declare "
            "response_model=ReplyResponse after the 201 status_code fix"
        )

    def test_reply_response_schema_importable(self):
        """ReplyResponse must be importable from communications_threads."""
        from api.routes.communications_threads import ReplyResponse  # noqa: F401
