/**
 * useAvatarUpload — FE-UI-NAV-S1
 *
 * Location: apps/web/src/features/settings/hooks/useAvatarUpload.ts
 *
 * Two-step avatar upload flow:
 *   1. POST /api/v1/users/me/avatar/presigned-url → { upload_url, s3_key }
 *   2. PUT upload_url with JPEG blob (direct S3 upload — raw fetch permitted
 *      per Rule 2 exception: this is NOT an /api/v1/ call, it's an S3 endpoint)
 *   3. PATCH /api/v1/users/me/profile { profile_photo_s3_key: s3_key }
 *
 * Endpoint confirmed in openapi_schema_map.md (post pnpm sync-api-types).
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// TODO: replace with @pilot/shared-types once BE-UI-NAV-S1 generates the type
interface PresignedUrlResponse {
  upload_url: string;
  s3_key: string;
}

export function useAvatarUpload() {
  return useMutation({
    mutationFn: async (croppedBlob: Blob) => {
      // Step 1: Get presigned S3 upload URL from our backend
      const { data } = await apiClient.post<PresignedUrlResponse>(
        "/api/v1/users/me/avatar/presigned-url",
      );

      // Step 2: Upload blob directly to S3 via presigned URL
      // Raw fetch is permitted here — this is NOT an /api/v1/ call,
      // it's a direct PUT to an S3 presigned URL (no JWT required)
      await fetch(data.upload_url, {
        method: "PUT",
        body: croppedBlob,
        headers: { "Content-Type": "image/jpeg" },
      });

      // Step 3: Persist the S3 key to the user profile
      await apiClient.patch("/api/v1/users/me/profile", {
        profile_photo_s3_key: data.s3_key,
      });

      return data.s3_key;
    },
    retry: false,
  });
}

export function useAvatarDelete() {
  return useMutation({
    mutationFn: async () => {
      // TODO: endpoint DELETE /api/v1/users/me/avatar — pending BE-UI-NAV-S1
      // MSW stub returns { success: true }
      await apiClient.delete("/api/v1/users/me/avatar");
    },
    retry: false,
  });
}
