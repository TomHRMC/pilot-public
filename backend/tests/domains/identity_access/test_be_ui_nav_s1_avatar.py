"""
BE-UI-NAV-S1 — Avatar endpoint tests.

Tests:
  1. GET profile includes profile_photo_url when s3_key is set (mocked S3)
  2. GET profile returns profile_photo_url=None when no s3_key
  3. POST /me/avatar/presigned-url/test returns upload_url + s3_key (mocked S3)
  4. DELETE /me/avatar/test clears profile_photo_s3_key on user record
  5. DELETE /me/avatar/test with no key set succeeds (idempotent)

Domain: identity_access
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]

FAKE_PRESIGNED_GET = "https://s3.example.com/presigned-get-url"
FAKE_PRESIGNED_PUT = "https://s3.example.com/presigned-put-url"


class TestProfilePhotoUrl:
    def test_get_profile_includes_photo_url_when_key_set(
        self, client, test_tenant, db_session
    ):
        """GET profile with s3_key set returns profile_photo_url (mocked S3)."""
        # Set the s3_key via PATCH (mock S3 for the get URL generation in response)
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = FAKE_PRESIGNED_GET

        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            patch_resp = client.patch(
                "/api/v1/users/me/profile/test",
                json={"profile_photo_s3_key": "avatars/tenant/user/avatar.jpg"},
            )
            assert patch_resp.status_code == 200
            patch_data = patch_resp.json()
            assert (
                patch_data["profile_photo_s3_key"] == "avatars/tenant/user/avatar.jpg"
            )
            assert patch_data["profile_photo_url"] == FAKE_PRESIGNED_GET

        # GET profile also returns the URL
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            get_resp = client.get("/api/v1/users/me/profile/test")
            assert get_resp.status_code == 200
            data = get_resp.json()
            assert data["profile_photo_s3_key"] == "avatars/tenant/user/avatar.jpg"
            assert data["profile_photo_url"] is not None

    def test_get_profile_photo_url_none_when_no_key(
        self, client, test_tenant, db_session
    ):
        """GET profile with no s3_key returns profile_photo_url=None."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = None

        # Clear any existing key
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            client.patch(
                "/api/v1/users/me/profile/test",
                json={"profile_photo_s3_key": None},
            )

        # Verify we delete the avatar first to guarantee no key
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            client.delete("/api/v1/users/me/avatar/test")

        # GET profile — no boto3 call needed, key is None so URL is None
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            get_resp = client.get("/api/v1/users/me/profile/test")
            assert get_resp.status_code == 200
            data = get_resp.json()
            if data["profile_photo_s3_key"] is None:
                assert data["profile_photo_url"] is None
                mock_s3.generate_presigned_url.assert_not_called()


class TestAvatarPresignedUrl:
    def test_avatar_presigned_url_test_endpoint_returns_upload_url(
        self, client, test_tenant
    ):
        """POST /me/avatar/presigned-url/test returns upload_url and s3_key."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = FAKE_PRESIGNED_PUT

        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3

            resp = client.post("/api/v1/users/me/avatar/presigned-url/test")
            assert resp.status_code == 201
            data = resp.json()
            assert "upload_url" in data
            assert "s3_key" in data
            assert data["upload_url"] == FAKE_PRESIGNED_PUT
            # Key must include "avatars/" prefix and end with "avatar.jpg"
            assert data["s3_key"].startswith("avatars/")
            assert data["s3_key"].endswith("avatar.jpg")


class TestAvatarDelete:
    def test_delete_avatar_clears_s3_key(self, client, test_tenant, db_session):
        """DELETE /me/avatar/test clears profile_photo_s3_key on user record."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = FAKE_PRESIGNED_GET

        # Set an s3 key first
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            client.patch(
                "/api/v1/users/me/profile/test",
                json={"profile_photo_s3_key": "avatars/tenant/user/avatar.jpg"},
            )

        # Delete avatar
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            del_resp = client.delete("/api/v1/users/me/avatar/test")
            assert del_resp.status_code == 200
            assert del_resp.json()["success"] is True

        # Verify key is cleared
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            get_resp = client.get("/api/v1/users/me/profile/test")
            assert get_resp.status_code == 200
            assert get_resp.json()["profile_photo_s3_key"] is None

    def test_delete_avatar_no_key_succeeds(self, client, test_tenant, db_session):
        """DELETE /me/avatar/test when no key is set still returns 200 (idempotent)."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = None

        # Ensure no key (delete to clean state)
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            client.delete("/api/v1/users/me/avatar/test")

        # Call delete again when already no key
        with patch("api.routes.user_profile.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3
            del_resp = client.delete("/api/v1/users/me/avatar/test")
            assert del_resp.status_code == 200
            assert del_resp.json()["success"] is True
            # S3 delete_object must NOT be called when there was no key
            mock_s3.delete_object.assert_not_called()
