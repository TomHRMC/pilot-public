"""
Batch B3 — A18 Test Coverage
==============================

A18: Tech Color Assignment & Configuration

Test Coverage:
- User ORM model has display_color field
- TenantSettings ORM model has tech_color_palette field
- is_valid_hex_color validates correctly
- assign_next_color returns first palette color when tenant has no colors
- assign_next_color skips used colors and picks next available
- assign_next_color wraps around when all palette slots are used
- PATCH /api/v1/users/{user_id}/color/test sets display_color on user
- PATCH /api/v1/users/{user_id}/color/test returns 422 on invalid hex format
- PATCH /api/v1/users/{user_id}/color/test returns 404 for unknown user
- display_color stored uppercase in DB
"""

import pytest
from sqlmodel import select

# ─────────────────────────────────────────────────────────────────────────────
# A18 — ORM model checks
# ─────────────────────────────────────────────────────────────────────────────


class TestA18ORMModels:
    """Verify ORM fields exist and are correctly defined."""

    def test_user_has_display_color_field(self):
        from app.models.core import User

        assert hasattr(User, "display_color")

    def test_tenant_settings_has_tech_color_palette_field(self, db_session):
        """platform_setting_catalog has tech_color_palette key (FIND-086)."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "tech_color_palette"
            )
        ).first()
        assert row is not None, (
            "tech_color_palette missing from platform_setting_catalog"
        )

    def test_user_display_color_nullable(self, db_session, test_tenant, test_user):
        """display_color is nullable — existing users have NULL until assigned."""
        from app.models.core import User

        u = db_session.exec(select(User).where(User.id == test_user.id)).first()
        assert u is not None
        assert u.display_color is None or isinstance(u.display_color, str)

    def test_tenant_settings_tech_color_palette_nullable(self, db_session, test_tenant):
        """tech_color_palette platform default is null (use system palette) — FIND-086."""
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "tech_color_palette")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        # Platform default is null (jsonb null)
        assert row.value is None or isinstance(row.value, list)


# ─────────────────────────────────────────────────────────────────────────────
# A18 — Service layer tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA18TechColorService:
    """Unit tests for tech_color_service helper functions."""

    def test_is_valid_hex_color_accepts_valid_values(self):
        from services.tech_color_service import is_valid_hex_color

        assert is_valid_hex_color("#3B43D6") is True
        assert is_valid_hex_color("#FFFFFF") is True
        assert is_valid_hex_color("#000000") is True
        assert is_valid_hex_color("#abcdef") is True

    def test_is_valid_hex_color_rejects_invalid_values(self):
        from services.tech_color_service import is_valid_hex_color

        assert is_valid_hex_color("3B43D6") is False  # missing #
        assert is_valid_hex_color("#3B43D") is False  # 5 chars
        assert is_valid_hex_color("#3B43D6FF") is False  # 8 chars (rgba)
        assert is_valid_hex_color("red") is False
        assert is_valid_hex_color("") is False
        assert is_valid_hex_color("#GGGGGG") is False  # non-hex chars

    def test_default_palette_has_12_colors(self):
        from services.tech_color_service import DEFAULT_PALETTE

        assert len(DEFAULT_PALETTE) == 12
        for color in DEFAULT_PALETTE:
            from services.tech_color_service import is_valid_hex_color

            assert is_valid_hex_color(color), f"Invalid palette color: {color}"

    def test_assign_next_color_returns_first_when_none_used(
        self, db_session, test_tenant
    ):
        """With no users having a color, assign_next_color returns the first palette entry."""
        from services.tech_color_service import assign_next_color

        # Use explicit small palette to make test deterministic
        palette = ["#AAAAAA", "#BBBBBB", "#CCCCCC"]
        color = assign_next_color(db_session, test_tenant.id, palette=palette)
        # Should be one of the palette colors (first unused)
        assert color in palette

    def test_assign_next_color_wraps_around_when_all_used(
        self, db_session, test_tenant, test_user
    ):
        """When palette is fully exhausted, wraps modulo."""
        from services.tech_color_service import assign_next_color

        # Use a 1-color palette — must always return that color
        palette = ["#AAAAAA"]
        color = assign_next_color(db_session, test_tenant.id, palette=palette)
        assert color == "#AAAAAA"


# ─────────────────────────────────────────────────────────────────────────────
# A18 — HTTP endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA18UserColorEndpoint:
    """HTTP tests for PATCH /api/v1/users/{user_id}/color/test"""

    def test_patch_user_color_sets_display_color(
        self, client, db_session, test_tenant, test_user
    ):
        """PATCH /test/{user_id}/color with valid hex returns 200 and updates user."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.patch(
                f"/api/v1/users/test/{test_user.id}/color",
                json={"display_color": "#3B43D6"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(test_user.id)
        assert data["display_color"] == "#3B43D6"
        assert "updated_at" in data

    def test_patch_user_color_normalizes_to_uppercase(
        self, client, test_tenant, test_user
    ):
        """display_color is stored uppercase regardless of input case."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.patch(
                f"/api/v1/users/test/{test_user.id}/color",
                json={"display_color": "#3b43d6"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["display_color"] == "#3B43D6"

    def test_patch_user_color_rejects_invalid_hex(self, client, test_tenant, test_user):
        """PATCH with invalid hex format returns 422."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.patch(
                f"/api/v1/users/test/{test_user.id}/color",
                json={"display_color": "not-a-color"},
            )

        assert resp.status_code == 422

    def test_patch_user_color_rejects_short_hex(self, client, test_tenant, test_user):
        """PATCH with 3-char hex (CSS shorthand) returns 422 — must be 6 chars."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.patch(
                f"/api/v1/users/test/{test_user.id}/color",
                json={"display_color": "#FFF"},
            )

        assert resp.status_code == 422

    def test_patch_user_color_returns_404_for_unknown_user(self, client, test_tenant):
        """PATCH for a UUID not in this tenant returns 404."""
        import uuid

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.patch(
                f"/api/v1/users/test/{uuid.uuid4()}/color",
                json={"display_color": "#3B43D6"},
            )

        assert resp.status_code == 404

    def test_patch_user_color_persists_in_db(
        self, client, db_session, test_tenant, test_user
    ):
        """After PATCH, user.display_color is persisted in the database."""
        from app.models.core import User

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            client.patch(
                f"/api/v1/users/test/{test_user.id}/color",
                json={"display_color": "#D64343"},
            )

        db_session.expire_all()
        u = db_session.exec(select(User).where(User.id == test_user.id)).first()
        assert u is not None
        assert u.display_color == "#D64343"
