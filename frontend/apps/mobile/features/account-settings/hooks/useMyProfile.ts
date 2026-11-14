/**
 * useMyProfile — Mobile hook for GET + PATCH /api/v1/users/me/profile
 *
 * MOB-B10: Profile settings screen
 * Endpoint verified in openapi_schema_map.md — correct path is /api/v1/users/me/profile
 */
import { apiClient } from "@pilot/shared-api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export const MY_PROFILE_QUERY_KEY = ["users", "me", "profile"] as const;

// UserProfileResponse shape from GET /api/v1/users/me/profile
// Verified against openapi_schema_map.md §GET /api/v1/users/me/profile
export interface UserProfile {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string | null;
  time_zone: string;
  profile_photo_s3_key: string | null;
  language_preference: string | null;
}

interface UseMyProfileReturn {
  profile: UserProfile | undefined;
  isLoading: boolean;
  isError: boolean;
  updateField: (field: string, value: string | null) => Promise<void>;
  isPending: boolean;
  updateError: Error | null;
}

export function useMyProfile(): UseMyProfileReturn {
  const queryClient = useQueryClient();

  const {
    data: profile,
    isLoading,
    isError,
  } = useQuery({
    queryKey: MY_PROFILE_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/users/me/profile");
      return res.data as UserProfile;
    },
    staleTime: 60_000,
  });

  const {
    mutateAsync: updateProfileMutation,
    isPending,
    error: updateError,
  } = useMutation({
    mutationFn: async (fields: Partial<UserProfile>) => {
      const res = await apiClient.patch("/api/v1/users/me/profile", fields);
      return res.data as UserProfile;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: MY_PROFILE_QUERY_KEY });
    },
  });

  async function updateField(field: string, value: string | null) {
    await updateProfileMutation({ [field]: value } as Partial<UserProfile>);
  }

  return {
    profile,
    isLoading,
    isError,
    updateField,
    isPending,
    updateError: updateError as Error | null,
  };
}
