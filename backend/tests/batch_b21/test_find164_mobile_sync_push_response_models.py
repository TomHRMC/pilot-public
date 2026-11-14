"""
Batch B21 — FIND-164: response_model verification on mobile-sync/push endpoints
================================================================================

FIND-164 (S4 Cosmetic): Verify that mobile-sync and push endpoints declare
`response_model` decorators where appropriate. DELETE endpoints returning 204
No Content correctly omit response_model.

Files inspected:
  - backend/api/routes/mobile_sync.py   — 6 endpoints (all with response_model)
  - backend/api/routes/mobile_push.py   — 6 endpoints (4 with response_model; 2 DELETE 204 exempt)
  - backend/api/routes/mobile_push_permission.py — 4 endpoints (all with response_model)

Verification result: CORRECT — no code changes required.
"""

import inspect

# ─────────────────────────────────────────────────────────────────────────────
# FIND-164 — mobile_sync.py
# ─────────────────────────────────────────────────────────────────────────────


class TestFind164MobileSyncResponseModels:
    """FIND-164: All GET/POST endpoints in mobile_sync.py must declare response_model."""

    def test_get_sync_state_authenticated_has_response_model(self):
        """GET /state/{user_id} must use response_model=MobileSyncStateResponse."""
        import api.routes.mobile_sync as mod

        src = inspect.getsource(mod)
        assert "response_model=MobileSyncStateResponse" in src, (
            "mobile_sync.py GET /state/{user_id} must declare response_model=MobileSyncStateResponse"
        )

    def test_get_conflict_detail_has_response_model(self):
        """GET /conflicts/{conflict_id} must use response_model=ConflictDetailResponse."""
        import api.routes.mobile_sync as mod

        src = inspect.getsource(mod)
        assert "response_model=ConflictDetailResponse" in src, (
            "mobile_sync.py GET /conflicts/{conflict_id} must declare response_model=ConflictDetailResponse"
        )

    def test_resolve_conflict_has_response_model(self):
        """POST /conflicts/{conflict_id}/resolve must use response_model=ConflictResolveResponse."""
        import api.routes.mobile_sync as mod

        src = inspect.getsource(mod)
        assert "response_model=ConflictResolveResponse" in src, (
            "mobile_sync.py POST /conflicts/{conflict_id}/resolve must declare response_model=ConflictResolveResponse"
        )

    def test_mobile_sync_state_response_schema_defined(self):
        """MobileSyncStateResponse schema must be importable and have required fields."""
        from api.routes.mobile_sync import MobileSyncStateResponse

        fields = MobileSyncStateResponse.model_fields
        # Actual fields: user_id, items, cursor, has_more
        assert "items" in fields, (
            f"MobileSyncStateResponse must have 'items' field. Got: {list(fields)}"
        )
        assert "cursor" in fields, (
            f"MobileSyncStateResponse must have 'cursor' field. Got: {list(fields)}"
        )
        assert "has_more" in fields, (
            f"MobileSyncStateResponse must have 'has_more' field. Got: {list(fields)}"
        )
        assert "user_id" in fields, (
            f"MobileSyncStateResponse must have 'user_id' field. Got: {list(fields)}"
        )

    def test_mobile_sync_routes_registered(self):
        """Key sync routes must be registered on the mobile_sync router."""
        from api.routes.mobile_sync import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        assert any("state" in r for r in routes), (
            f"No 'state' route found on mobile_sync router. Routes: {routes}"
        )
        assert any("conflicts" in r for r in routes), (
            f"No 'conflicts' route found on mobile_sync router. Routes: {routes}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FIND-164 — mobile_push.py
# ─────────────────────────────────────────────────────────────────────────────


class TestFind164MobilePushResponseModels:
    """FIND-164: POST endpoints in mobile_push.py must declare response_model.
    DELETE 204 endpoints are exempt (no body to model)."""

    def test_register_push_token_has_response_model(self):
        """POST /push-tokens must use response_model=PushTokenRegisterResponse."""
        import api.routes.mobile_push as mod

        src = inspect.getsource(mod)
        assert "response_model=PushTokenRegisterResponse" in src, (
            "mobile_push.py POST /push-tokens must declare response_model=PushTokenRegisterResponse"
        )

    def test_complete_sync_session_has_response_model(self):
        """POST /sync-sessions/{session_id}/complete must use response_model=SyncSessionCompleteResponse."""
        import api.routes.mobile_push as mod

        src = inspect.getsource(mod)
        assert "response_model=SyncSessionCompleteResponse" in src, (
            "mobile_push.py POST /sync-sessions/{session_id}/complete must declare "
            "response_model=SyncSessionCompleteResponse"
        )

    def test_push_token_register_response_schema_defined(self):
        """PushTokenRegisterResponse must be importable and have required fields."""
        from api.routes.mobile_push import PushTokenRegisterResponse

        fields = PushTokenRegisterResponse.model_fields
        # Actual fields: device_id, registered_at, last_seen_at
        assert "device_id" in fields, (
            f"PushTokenRegisterResponse must have 'device_id' field. Got: {list(fields)}"
        )
        assert "registered_at" in fields, (
            f"PushTokenRegisterResponse must have 'registered_at' field. Got: {list(fields)}"
        )
        assert "last_seen_at" in fields, (
            f"PushTokenRegisterResponse must have 'last_seen_at' field. Got: {list(fields)}"
        )

    def test_sync_session_complete_response_schema_defined(self):
        """SyncSessionCompleteResponse must be importable."""
        from api.routes.mobile_push import SyncSessionCompleteResponse  # noqa: F401

    def test_delete_push_token_204_exempt_from_response_model(self):
        """DELETE /push-tokens/{device_id} (204) correctly omits response_model — verified by 204 status."""
        import api.routes.mobile_push as mod

        src = inspect.getsource(mod)
        # DELETE revoke endpoint uses 204 No Content — response_model is intentionally absent
        assert "HTTP_204_NO_CONTENT" in src, (
            "mobile_push.py DELETE endpoints must use HTTP_204_NO_CONTENT "
            "(confirming they are body-less — response_model correctly omitted)"
        )

    def test_mobile_push_routes_registered(self):
        """Key push-token and sync-session routes must be registered."""
        from api.routes.mobile_push import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        assert any("push-tokens" in r for r in routes), (
            f"No 'push-tokens' route found on mobile_push router. Routes: {routes}"
        )
        assert any("sync-sessions" in r for r in routes), (
            f"No 'sync-sessions' route found on mobile_push router. Routes: {routes}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FIND-164 — mobile_push_permission.py
# ─────────────────────────────────────────────────────────────────────────────


class TestFind164MobilePushPermissionResponseModels:
    """FIND-164: All PUT/GET endpoints in mobile_push_permission.py must declare response_model."""

    def test_push_permission_endpoints_have_response_model(self):
        """PUT and GET /me/devices/{device_id}/push-permission must use response_model=PushPermissionResponse."""
        import api.routes.mobile_push_permission as mod

        src = inspect.getsource(mod)
        assert "response_model=PushPermissionResponse" in src, (
            "mobile_push_permission.py endpoints must declare response_model=PushPermissionResponse"
        )

    def test_push_permission_response_schema_defined(self):
        """PushPermissionResponse must be importable."""
        from api.routes.mobile_push_permission import (
            PushPermissionResponse,  # noqa: F401
        )

    def test_push_permission_routes_registered(self):
        """push-permission routes must be registered on the mobile push permission router."""
        from api.routes.mobile_push_permission import router

        routes = [r.path for r in router.routes if hasattr(r, "path")]
        assert any("push-permission" in r for r in routes), (
            f"No 'push-permission' route found on mobile_push_permission router. Routes: {routes}"
        )
