"""
FIND-158 (S4 Low) — Rename DELETE /settings/{key} → DELETE /settings/{key}/tenant-override

Rationale: symmetry with DELETE /{key}/user-override; architecturally accurate after
FIND-086 (platform_setting row is physically deleted, not NULLed).

Test subfolder: tests/batch_b18/
"""

import inspect
from unittest.mock import patch


class TestFind158DeleteTenantOverridePathRename:
    """FIND-158: DELETE /{key}/tenant-override path must be registered; old /{key} must be gone."""

    def test_old_delete_key_path_returns_405_or_404(self, client):
        """DELETE /settings/test/{key} (old path) must no longer exist — returns 404 or 405."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.delete("/api/v1/settings/test/background_sync_enabled")
        # Old path is gone — FastAPI returns 405 (method not allowed) if parameterised
        # path still matches GET, or 404 if no route at all
        assert response.status_code in (404, 405), (
            f"Old DELETE /settings/test/{{key}} path should be 404/405, got {response.status_code}"
        )

    def test_new_delete_tenant_override_path_is_registered(self, client):
        """DELETE /settings/test/{key}/tenant-override must be reachable (route must exist)."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            # First create an override so there is something to delete
            client.put(
                "/api/v1/settings/test/require_approval_for_tech_quotes",
                json={"value": True},
            )
            # Now delete it via the new path
            response = client.delete(
                "/api/v1/settings/test/require_approval_for_tech_quotes/tenant-override"
            )
        # Valid catalog key with existing override → 200 (reverts to system default)
        assert response.status_code in (200, 204), (
            f"New DELETE /settings/test/{{key}}/tenant-override should succeed, got {response.status_code}"
        )

    def test_delete_unknown_key_via_new_path_returns_404(self, client):
        """DELETE /settings/test/nonexistent_key/tenant-override returns 404 (not 500)."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.delete(
                "/api/v1/settings/test/this_key_does_not_exist_xyz/tenant-override"
            )
        assert response.status_code == 404

    def test_decorator_registered_at_tenant_override_path(self):
        """settings.py route source must contain /{key}/tenant-override path string."""
        import api.routes.settings as mod

        src = inspect.getsource(mod)
        assert "/{key}/tenant-override" in src or "/tenant-override" in src, (
            "settings.py must register DELETE /{key}/tenant-override"
        )

    def test_decorator_does_not_contain_old_bare_key_delete(self):
        """settings.py must not register DELETE /{key} bare path (only PUT uses it)."""
        import api.routes.settings as mod

        src = inspect.getsource(mod)
        # The old delete path was @router.delete("/{key}") — confirm it's gone
        # (user-override and tenant-override paths are fine)
        # We check by looking for the bare pattern without suffix
        lines = src.splitlines()
        bare_delete_lines = [
            l for l in lines if "router.delete(" in l and '"/{key}"' in l
        ]
        assert len(bare_delete_lines) == 0, (
            f"Found bare @router.delete('/{{key}}') — must be renamed to /tenant-override: {bare_delete_lines}"
        )

    def test_symmetry_user_override_and_tenant_override_paths_both_present(self):
        """Both /user-override and /tenant-override DELETE paths must exist in settings.py."""
        import api.routes.settings as mod

        src = inspect.getsource(mod)
        assert "/user-override" in src, (
            "DELETE /{key}/user-override path must still exist"
        )
        assert "/tenant-override" in src, (
            "DELETE /{key}/tenant-override path must exist (FIND-158)"
        )
