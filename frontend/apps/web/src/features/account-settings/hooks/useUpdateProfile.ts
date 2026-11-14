/**
 * useUpdateProfile — TanStack Query hook
 *
 * Location: apps/web/src/features/account-settings/hooks/useUpdateProfile.ts
 *
 * Profile fields use SettingControl saveMode='blur' — each field saves independently.
 *
 * Field name mapping:
 *   API response  → frontend UserProfile
 *   id            → user_id
 *   phone_number  → phone
 *   time_zone     → timezone
 *
 *   ProfileUpdateRequest → API UserProfilePatchRequest
 *   phone         → phone_number
 *   timezone      → time_zone
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { UserProfile, ProfileUpdateRequest } from "../types";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";

const PROFILE_KEY = ["users", "me", "profile"] as const;
const BASE = "/api/v1/users/me/profile";

/** Normalize snake_case API response to frontend UserProfile shape. */
function normalizeProfile(raw: Record<string, unknown>): UserProfile {
  return {
    user_id: (raw.id as string) ?? "",
    first_name: (raw.first_name as string) ?? "",
    last_name: (raw.last_name as string) ?? "",
    email: (raw.email as string) ?? "",
    phone: (raw.phone_number as string | null) ?? null,
    timezone: (raw.time_zone as string) ?? "America/New_York",
    language: (raw.language_preference as string) ?? "en",
    avatar_url: (raw.profile_photo_s3_key as string | null) ?? null,
  };
}

/** Map frontend ProfileUpdateRequest field names to API UserProfilePatchRequest names. */
function toApiPatchRequest(
  data: ProfileUpdateRequest,
): Record<string, unknown> {
  const patch: Record<string, unknown> = {};
  if ("first_name" in data) patch.first_name = data.first_name;
  if ("last_name" in data) patch.last_name = data.last_name;
  if ("phone" in data) patch.phone_number = data.phone;
  if ("timezone" in data) patch.time_zone = data.timezone;
  if ("language" in data) patch.language_preference = data.language;
  return patch;
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const tenantId = user?.tenantId ?? "";
  const roleCode = user?.role ?? "";

  const {
    data: profile,
    isLoading,
    isError,
  } = useQuery({
    queryKey: [...PROFILE_KEY, tenantId],
    queryFn: async (): Promise<UserProfile> => {
      const res = await apiClient.get<Record<string, unknown>>(BASE);
      return normalizeProfile(res.data);
    },
    enabled: !!tenantId && !!roleCode,
    staleTime: 5 * 60_000,
  });

  const updateMutation = useMutation({
    mutationFn: async (data: ProfileUpdateRequest): Promise<UserProfile> => {
      const res = await apiClient.patch<Record<string, unknown>>(
        BASE,
        toApiPatchRequest(data),
      );
      return normalizeProfile(res.data);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData([...PROFILE_KEY, tenantId], updated);
    },
  });

  return {
    profile,
    isLoading,
    isError,
    updateProfile: async (data: ProfileUpdateRequest) => {
      await updateMutation.mutateAsync(data);
    },
    isPending: updateMutation.isPending,
    updateError: updateMutation.error,
  };
}
