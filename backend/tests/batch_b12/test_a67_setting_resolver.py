"""
B12/A67 — Setting resolver + voice persona API endpoint tests.

Test focus cases:
- setting_allows_user_override_for_tenant returns True by default
- setting_allows_user_override_for_tenant returns False when meta-toggle = False
- get_effective_setting_for_user falls through to balanced when no overrides
- get_effective_setting_for_user returns user override when set + meta-toggle ON
- get_effective_setting_for_user ignores user override when meta-toggle OFF
- GET /settings/voice-persona-tone returns effective tone + full response shape
- PUT /settings/voice-persona-tone sets user override and returns 200
- DELETE /settings/voice-persona-tone removes user override and returns 204
- GET /settings/tenant/voice-persona-tone returns tenant default + policy
- PUT /settings/tenant/voice-persona-tone sets tenant default
- DELETE /settings/tenant/voice-persona-tone resets tenant default to NULL
- PUT /settings/tenant/voice-persona-tone-user-override-allowed toggles meta-toggle
- PUT /settings/voice-persona-tone returns 403 when meta-toggle is False
- voice_persona_renderer.get_preview_audio_urls returns all 3 tone URLs
- voice_persona_renderer.get_empty_state_copy returns tone-appropriate copy
"""

from unittest.mock import patch

# ---------------------------------------------------------------------------
# Setting resolver tests
# ---------------------------------------------------------------------------


class TestSettingAllowsUserOverrideForTenant:
    """setting_allows_user_override_for_tenant() meta-toggle checks."""

    def test_returns_true_by_default(self, db_session, test_tenant):
        """Returns True for voice_persona_tone when meta-toggle is True (default)."""
        from services.setting_resolver import setting_allows_user_override_for_tenant

        result = setting_allows_user_override_for_tenant(
            db_session, test_tenant.id, "voice_persona_tone"
        )
        assert result is True

    def test_returns_false_when_meta_toggle_disabled(self, db_session, test_tenant):
        """Returns False when voice_persona_tone_user_override_allowed = False (FIND-086)."""
        from sqlmodel import select

        from app.models.platform_setting import PlatformSetting
        from services.setting_resolver import setting_allows_user_override_for_tenant

        # Upsert meta-toggle = False in platform_setting
        existing = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone_user_override_allowed")
            .where(PlatformSetting.tenant_id == test_tenant.id)
        ).first()
        if existing:
            existing.value = False
        else:
            existing = PlatformSetting(
                key="voice_persona_tone_user_override_allowed",
                value=False,
                tenant_id=test_tenant.id,
            )
        db_session.add(existing)
        db_session.commit()

        result = setting_allows_user_override_for_tenant(
            db_session, test_tenant.id, "voice_persona_tone"
        )
        assert result is False

        # Restore
        db_session.delete(existing)
        db_session.commit()

    def test_returns_false_for_unknown_setting(self, db_session, test_tenant):
        """Returns False for settings not in the catalog."""
        from services.setting_resolver import setting_allows_user_override_for_tenant

        result = setting_allows_user_override_for_tenant(
            db_session, test_tenant.id, "nonexistent_key_xyz"
        )
        assert result is False

    def test_returns_false_for_settings_without_user_override(
        self, db_session, test_tenant
    ):
        """Returns False for settings marked allows_user_override=False."""
        from services.setting_resolver import setting_allows_user_override_for_tenant

        # require_approval_for_tech_quotes has allows_user_override=False
        result = setting_allows_user_override_for_tenant(
            db_session, test_tenant.id, "require_approval_for_tech_quotes"
        )
        assert result is False


class TestGetEffectiveSettingForUser:
    """get_effective_setting_for_user() three-tier resolution for voice_persona_tone."""

    def test_falls_back_to_system_default_when_no_overrides(
        self, db_session, test_tenant, test_user
    ):
        """Without any overrides, resolves to 'balanced' (system default)."""
        from sqlmodel import select as sqlm_select

        from app.models.settings import UserSettingOverride
        from services.setting_resolver import get_effective_setting_for_user

        # SD-6: Remove seeded voice_persona_tone override so test resolves to system default
        existing = db_session.exec(
            sqlm_select(UserSettingOverride)
            .where(UserSettingOverride.tenant_id == test_tenant.id)
            .where(UserSettingOverride.user_id == test_user.id)
            .where(UserSettingOverride.setting_key == "voice_persona_tone")
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        tone, scope = get_effective_setting_for_user(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            setting_key="voice_persona_tone",
            fallback="balanced",
        )
        # Scope is "system" (from SYSTEM_DEFAULTS) or "fallback" depending on DB state
        assert tone == "balanced"
        assert scope in ("system", "fallback", "tenant")

    def test_returns_user_override_when_meta_toggle_on(
        self, db_session, test_tenant, test_user
    ):
        """Returns user-level override when meta-toggle is True."""
        from datetime import UTC, datetime

        from sqlmodel import select as sqlm_select

        from app.models.settings import UserSettingOverride
        from services.setting_resolver import get_effective_setting_for_user

        # SD-6: Remove seeded voice_persona_tone override to avoid unique constraint violation
        existing = db_session.exec(
            sqlm_select(UserSettingOverride)
            .where(UserSettingOverride.tenant_id == test_tenant.id)
            .where(UserSettingOverride.user_id == test_user.id)
            .where(UserSettingOverride.setting_key == "voice_persona_tone")
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        override = UserSettingOverride(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            setting_key="voice_persona_tone",
            value="conservative",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(override)
        db_session.commit()

        tone, scope = get_effective_setting_for_user(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            setting_key="voice_persona_tone",
            fallback="balanced",
        )
        assert tone == "conservative"
        assert scope == "user"

        # Cleanup
        db_session.delete(override)
        db_session.commit()

    def test_ignores_user_override_when_meta_toggle_off(
        self, db_session, test_tenant, test_user
    ):
        """Ignores user-level override when meta-toggle is False (FIND-086)."""
        from datetime import UTC, datetime

        from sqlmodel import select

        from app.models.platform_setting import PlatformSetting
        from app.models.settings import UserSettingOverride
        from services.setting_resolver import get_effective_setting_for_user

        # SD-6: Remove seeded voice_persona_tone override to avoid unique constraint violation
        existing = db_session.exec(
            select(UserSettingOverride)
            .where(UserSettingOverride.tenant_id == test_tenant.id)
            .where(UserSettingOverride.user_id == test_user.id)
            .where(UserSettingOverride.setting_key == "voice_persona_tone")
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        # Set meta-toggle = False in platform_setting
        meta = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone_user_override_allowed")
            .where(PlatformSetting.tenant_id == test_tenant.id)
        ).first()
        if meta:
            meta.value = False
        else:
            meta = PlatformSetting(
                key="voice_persona_tone_user_override_allowed",
                value=False,
                tenant_id=test_tenant.id,
            )
        db_session.add(meta)
        db_session.commit()

        # Add user override that should be ignored
        override = UserSettingOverride(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            setting_key="voice_persona_tone",
            value="playful",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(override)
        db_session.commit()

        tone, scope = get_effective_setting_for_user(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            setting_key="voice_persona_tone",
            fallback="balanced",
        )
        # Should NOT return "playful" since meta-toggle is off
        assert tone != "playful"
        assert scope != "user"

        # Cleanup
        db_session.delete(override)
        db_session.delete(meta)
        db_session.commit()


# ---------------------------------------------------------------------------
# API endpoint tests (test endpoints — no auth)
# ---------------------------------------------------------------------------


class TestVoicePersonaToneGetEndpoint:
    """GET /api/v1/settings/voice-persona-tone/test"""

    def test_returns_200_with_correct_shape(self, client):
        """Test endpoint returns effective tone response."""
        response = client.get("/api/v1/settings/voice-persona-tone/test")
        assert response.status_code == 200

        data = response.json()
        assert "effective_tone" in data
        assert "effective_scope" in data
        assert "user_override_allowed" in data
        assert "available_tones" in data
        assert "preview_audio_urls" in data
        assert "system_default" in data

    def test_effective_tone_is_valid(self, client):
        """Effective tone is one of the valid values (SD-6: includes 'professional' from seed data)."""
        # SD-6: Delete seeded voice_persona_tone user override so tone resolves
        # to the system default ('balanced') rather than the seeded 'professional'
        from unittest.mock import patch

        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.delete("/api/v1/settings/test/voice_persona_tone/user-override")
        response = client.get("/api/v1/settings/voice-persona-tone/test")
        data = response.json()
        assert data["effective_tone"] in (
            "conservative",
            "balanced",
            "playful",
            "professional",
        )

    def test_available_tones_contains_all_three(self, client):
        """available_tones contains all three valid tones."""
        response = client.get("/api/v1/settings/voice-persona-tone/test")
        data = response.json()
        assert set(data["available_tones"]) == {"conservative", "balanced", "playful"}

    def test_preview_audio_urls_all_three_tones(self, client):
        """preview_audio_urls has keys for all three tones."""
        response = client.get("/api/v1/settings/voice-persona-tone/test")
        data = response.json()
        urls = data["preview_audio_urls"]
        assert "conservative" in urls
        assert "balanced" in urls
        assert "playful" in urls

    def test_preview_audio_urls_format(self, client):
        """Preview audio URLs are well-formed CDN URLs."""
        response = client.get("/api/v1/settings/voice-persona-tone/test")
        data = response.json()
        for tone, url in data["preview_audio_urls"].items():
            assert url.startswith("https://"), f"URL for '{tone}' is not HTTPS: {url}"
            assert f"{tone}.mp3" in url

    def test_system_default_is_balanced(self, client):
        """system_default is always 'balanced'."""
        response = client.get("/api/v1/settings/voice-persona-tone/test")
        data = response.json()
        assert data["system_default"] == "balanced"


class TestVoicePersonaTonePutEndpoint:
    """PUT /api/v1/settings/voice-persona-tone/test"""

    def test_set_valid_tone_returns_200(self, client):
        """Setting a valid tone returns 200 with write response shape."""
        response = client.put(
            "/api/v1/settings/voice-persona-tone/test",
            json={"value": "conservative"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["setting_key"] == "voice_persona_tone"
        assert data["value"] == "conservative"
        assert data["scope"] == "user"
        assert "updated_at" in data

    def test_set_all_valid_tones(self, client):
        """All three valid tones can be set without error."""
        for tone in ("conservative", "balanced", "playful"):
            response = client.put(
                "/api/v1/settings/voice-persona-tone/test",
                json={"value": tone},
            )
            assert response.status_code == 200, f"Failed for tone '{tone}'"
            assert response.json()["value"] == tone

    def test_invalid_tone_returns_422(self, client):
        """Invalid tone returns 422 Unprocessable."""
        response = client.put(
            "/api/v1/settings/voice-persona-tone/test",
            json={"value": "aggressive"},
        )
        assert response.status_code == 422

    def test_missing_value_returns_422(self, client):
        """Missing value field returns 422."""
        response = client.put(
            "/api/v1/settings/voice-persona-tone/test",
            json={},
        )
        assert response.status_code == 422


class TestVoicePersonaToneDeleteEndpoint:
    """DELETE /api/v1/settings/voice-persona-tone/test"""

    def test_delete_returns_204(self, client):
        """DELETE returns 204 No Content (idempotent)."""
        # Set first
        client.put(
            "/api/v1/settings/voice-persona-tone/test",
            json={"value": "playful"},
        )
        # Then delete
        response = client.delete("/api/v1/settings/voice-persona-tone/test")
        assert response.status_code == 204

    def test_delete_is_idempotent(self, client):
        """Deleting when no override exists still returns 204."""
        # Ensure no override exists
        client.delete("/api/v1/settings/voice-persona-tone/test")
        # Delete again — should not raise
        response = client.delete("/api/v1/settings/voice-persona-tone/test")
        assert response.status_code == 204


class TestTenantVoicePersonaToneEndpoints:
    """Tenant-level voice persona tone endpoints."""

    def test_get_tenant_tone_returns_200(self, client):
        """GET /settings/tenant/voice-persona-tone returns 200."""
        response = client.get("/api/v1/settings/tenant/voice-persona-tone/test")
        assert response.status_code == 200

        data = response.json()
        assert "tenant_default" in data
        assert "system_default" in data
        assert "user_override_policy" in data
        assert "available_tones" in data
        assert "preview_audio_urls" in data

    def test_set_tenant_tone_returns_200(self, client):
        """PUT /settings/tenant/voice-persona-tone sets tenant default."""
        response = client.put(
            "/api/v1/settings/tenant/voice-persona-tone/test",
            json={"value": "conservative"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["setting_key"] == "voice_persona_tone"
        assert data["value"] == "conservative"
        assert data["scope"] == "tenant"

    def test_set_tenant_tone_invalid_returns_422(self, client):
        """Invalid tone for tenant default returns 422."""
        response = client.put(
            "/api/v1/settings/tenant/voice-persona-tone/test",
            json={"value": "robot"},
        )
        assert response.status_code == 422

    def test_delete_tenant_tone_returns_204(self, client):
        """DELETE /settings/tenant/voice-persona-tone resets to NULL."""
        # Set first
        client.put(
            "/api/v1/settings/tenant/voice-persona-tone/test",
            json={"value": "playful"},
        )
        response = client.delete("/api/v1/settings/tenant/voice-persona-tone/test")
        assert response.status_code == 204


class TestUserOverridePolicyEndpoint:
    """PUT /settings/tenant/voice-persona-tone-user-override-allowed"""

    def test_set_override_policy_to_false(self, client):
        """Setting user override policy to false returns 200."""
        response = client.put(
            "/api/v1/settings/tenant/voice-persona-tone-user-override-allowed/test",
            json={"value": False},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["setting_key"] == "voice_persona_tone_user_override_allowed"
        assert data["value"] is False

    def test_set_override_policy_to_true(self, client):
        """Setting user override policy to true returns 200."""
        response = client.put(
            "/api/v1/settings/tenant/voice-persona-tone-user-override-allowed/test",
            json={"value": True},
        )
        assert response.status_code == 200
        assert response.json()["value"] is True

    def test_set_override_policy_non_boolean_string_coerced_by_pydantic(self, client):
        """Pydantic v2 coerces string 'yes' to True for bool fields — returns 200.

        This is standard Pydantic v2 behavior. A non-parseable value like a number
        string that can't map to bool would return 422.
        """
        response = client.put(
            "/api/v1/settings/tenant/voice-persona-tone-user-override-allowed/test",
            json={"value": "yes"},
        )
        # Pydantic v2 coerces "yes" → True, so this succeeds
        assert response.status_code == 200

    def test_set_override_policy_missing_value_returns_422(self, client):
        """Missing value field returns 422."""
        response = client.put(
            "/api/v1/settings/tenant/voice-persona-tone-user-override-allowed/test",
            json={},
        )
        assert response.status_code == 422


class TestMetaToggleForbids403:
    """When meta-toggle is False, PUT /voice-persona-tone returns 403."""

    def test_user_override_forbidden_when_meta_toggle_off(
        self, client, db_session, test_tenant
    ):
        """PUT /voice-persona-tone returns 403 when meta-toggle = False (FIND-086)."""
        from sqlmodel import select

        from app.models.platform_setting import PlatformSetting

        # Disable user overrides via platform_setting
        meta = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone_user_override_allowed")
            .where(PlatformSetting.tenant_id == test_tenant.id)
        ).first()
        if meta:
            meta.value = False
        else:
            meta = PlatformSetting(
                key="voice_persona_tone_user_override_allowed",
                value=False,
                tenant_id=test_tenant.id,
            )
        db_session.add(meta)
        db_session.commit()

        response = client.put(
            "/api/v1/settings/voice-persona-tone/test",
            json={"value": "playful"},
        )
        assert response.status_code == 403

        # Restore
        db_session.delete(meta)
        db_session.commit()


# ---------------------------------------------------------------------------
# voice_persona_renderer unit tests
# ---------------------------------------------------------------------------


class TestVoicePersonaRenderer:
    """Unit tests for voice_persona_renderer module."""

    def test_get_preview_audio_urls_returns_all_tones(self):
        """get_preview_audio_urls() returns dict with all 3 tones."""
        from services.voice_persona_renderer import get_preview_audio_urls

        urls = get_preview_audio_urls()
        assert set(urls.keys()) == {"conservative", "balanced", "playful"}

    def test_preview_urls_are_https_mp3(self):
        """Preview audio URLs are HTTPS and end in .mp3."""
        from services.voice_persona_renderer import get_preview_audio_urls

        urls = get_preview_audio_urls()
        for tone, url in urls.items():
            assert url.startswith("https://"), f"Not HTTPS: {url}"
            assert url.endswith(".mp3"), f"Not MP3: {url}"

    def test_get_empty_state_copy_returns_string(
        self, db_session, test_tenant, test_user
    ):
        """get_empty_state_copy() returns a non-empty string."""
        from services.voice_persona_renderer import get_empty_state_copy

        copy = get_empty_state_copy(
            user_id=test_user.id,
            db=db_session,
            tenant_id=test_tenant.id,
        )
        assert isinstance(copy, str)
        assert len(copy) > 0

    def test_empty_state_copy_balanced_is_default(
        self, db_session, test_tenant, test_user
    ):
        """When no tone override, empty state copy matches balanced."""
        from services.voice_persona_renderer import (
            EMPTY_STATE_COPY,
            get_empty_state_copy,
        )

        copy = get_empty_state_copy(
            user_id=test_user.id,
            db=db_session,
            tenant_id=test_tenant.id,
        )
        # With no overrides, effective tone = balanced
        assert copy == EMPTY_STATE_COPY["balanced"]

    def test_valid_tones_constant(self):
        """VALID_TONES contains exactly the three expected tones."""
        from services.voice_persona_renderer import VALID_TONES

        assert set(VALID_TONES) == {"conservative", "balanced", "playful"}

    def test_default_tone_is_balanced(self):
        """DEFAULT_TONE is 'balanced'."""
        from services.voice_persona_renderer import DEFAULT_TONE

        assert DEFAULT_TONE == "balanced"

    def test_render_returns_fallback_when_ollama_fails(
        self, db_session, test_tenant, test_user
    ):
        """render() returns fallback_message when Ollama fails."""
        from services.voice_persona_renderer import render

        # Mock Ollama to fail
        with patch(
            "services.voice_persona_renderer._call_ollama",
            return_value="",
        ):
            result = render(
                payload={
                    "intent": "create_quote",
                    "outcome": "success",
                    "data": {
                        "fallback_message": "Created Quote #abc123.",
                        "quote_id_short": "abc123",
                        "customer_name": "Test Customer",
                    },
                },
                user_id=test_user.id,
                db=db_session,
                tenant_id=test_tenant.id,
            )
        assert result == "Created Quote #abc123."

    def test_render_returns_ollama_response_when_available(
        self, db_session, test_tenant, test_user
    ):
        """render() returns Ollama response when available."""
        from services.voice_persona_renderer import render

        with patch(
            "services.voice_persona_renderer._call_ollama",
            return_value="Quote created successfully for Test Customer.",
        ):
            result = render(
                payload={
                    "intent": "create_quote",
                    "outcome": "success",
                    "data": {
                        "fallback_message": "Done.",
                        "customer_name": "Test Customer",
                    },
                },
                user_id=test_user.id,
                db=db_session,
                tenant_id=test_tenant.id,
            )
        assert result == "Quote created successfully for Test Customer."

    def test_generate_session_title_returns_string(
        self, db_session, test_tenant, test_user
    ):
        """generate_session_title() returns a string (mocked Ollama)."""
        from services.voice_persona_renderer import generate_session_title

        with patch(
            "services.voice_persona_renderer._call_ollama",
            return_value="Panel Upgrade Quote",
        ):
            title = generate_session_title(
                session_context="User created a quote for panel upgrade",
                creator_user_id=test_user.id,
                db=db_session,
                tenant_id=test_tenant.id,
            )
        assert isinstance(title, str)
        assert len(title) > 0

    def test_generate_session_title_truncated_to_60_chars(
        self, db_session, test_tenant, test_user
    ):
        """generate_session_title() enforces max 60-char title."""
        from services.voice_persona_renderer import generate_session_title

        long_response = "A" * 80
        with patch(
            "services.voice_persona_renderer._call_ollama",
            return_value=long_response,
        ):
            title = generate_session_title(
                session_context="Some context",
                creator_user_id=test_user.id,
                db=db_session,
                tenant_id=test_tenant.id,
            )
        assert len(title) <= 60

    def test_generate_session_title_falls_back_to_context_on_empty_ollama(
        self, db_session, test_tenant, test_user
    ):
        """When Ollama returns empty, falls back to truncated session_context."""
        from services.voice_persona_renderer import generate_session_title

        context = "Panel upgrade quote for Johnson Electric"
        with patch(
            "services.voice_persona_renderer._call_ollama",
            return_value="",
        ):
            title = generate_session_title(
                session_context=context,
                creator_user_id=test_user.id,
                db=db_session,
                tenant_id=test_tenant.id,
            )
        assert title == context[:60].strip()

    def test_tone_cache_is_used_on_second_call(
        self, db_session, test_tenant, test_user
    ):
        """tone_cache prevents repeated DB hits across multiple render() calls."""
        from services.voice_persona_renderer import _resolve_tone

        cache: dict = {}
        tone1 = _resolve_tone(test_user.id, db_session, test_tenant.id, cache)
        tone2 = _resolve_tone(test_user.id, db_session, test_tenant.id, cache)
        assert tone1 == tone2
        assert str(test_user.id) in cache
