/**
 * useRemoveMfaMethod — MFA-WIRE-1 Part B (design §D.3, spec §8 row 6)
 *
 * Location: apps/web/src/features/account-settings/hooks/useRemoveMfaMethod.ts
 *
 * TanStack Query v5 `useMutation` wrapping
 *   DELETE /api/v1/users/me/mfa/methods/{method_id}
 *
 * - Uses `apiClient` from `@pilot/shared-api` (Rule 2 — new code must use apiClient).
 * - Sends the `X-Cognito-Access-Token` header (design §G-Q1) fetched via the
 *   shared `getCognitoAccessToken()` helper in `apps/web/src/lib/cognito-token.ts`.
 *   The token is in-memory only — never logged, never persisted.
 * - On 204 → invalidates `["users", "me", "mfa-status"]` so the card list refetches.
 * - Exposes the RFC 7807 `code` from the error response body for the banner-routing
 *   logic in `MfaMethodCardList` (spec §5.2). Uses `isAxiosError` to safely read
 *   `error.response?.data?.code`.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import { getCognitoAccessToken } from "../../../lib/cognito-token";

export const MFA_STATUS_QUERY_KEY = ["users", "me", "mfa-status"] as const;

export interface UseRemoveMfaMethodResult {
  mutate: (methodId: string) => void;
  mutateAsync: (methodId: string) => Promise<void>;
  isPending: boolean;
  isError: boolean;
  /** The RFC 7807 `code` from the error response body, or null. */
  errorCode: string | null;
  /** The human-readable detail from the error response body, or null. */
  errorDetail: string | null;
  error: Error | null;
  reset: () => void;
}

export function useRemoveMfaMethod(): UseRemoveMfaMethodResult {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (methodId: string) => {
      const accessToken = await getCognitoAccessToken();
      await apiClient.delete(`/api/v1/users/me/mfa/methods/${methodId}`, {
        headers: {
          "X-Cognito-Access-Token": accessToken ?? "",
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: MFA_STATUS_QUERY_KEY,
      });
    },
  });

  // Extract RFC 7807 `code` and `detail` from the axios error response
  let errorCode: string | null = null;
  let errorDetail: string | null = null;
  if (mutation.error && isAxiosError(mutation.error)) {
    const data = mutation.error.response?.data as
      | { code?: string; detail?: string }
      | undefined;
    errorCode = data?.code ?? null;
    errorDetail = data?.detail ?? null;
  }

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isError: mutation.isError,
    errorCode,
    errorDetail,
    error: mutation.error,
    reset: mutation.reset,
  };
}
