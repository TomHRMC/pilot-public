/**
 * useChangePassword — mutation hook
 *
 * Location: apps/web/src/features/account-settings/hooks/useChangePassword.ts
 *
 * RULE: Uses useFormSaveStrategy({ mode: 'explicit' }) — three-field explicit-save form.
 * RULE: On success: fields clear + success NotificationBanner fires.
 * RULE: Other-device 401 handling relies on FE-B2's session-expired interceptor.
 *       FE-B12 does NOT build a new cross-device invalidation mechanism.
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

const BASE = "/api/v1/auth";

interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

interface ChangePasswordResult {
  success: boolean;
}

async function changePassword(
  payload: ChangePasswordPayload,
): Promise<ChangePasswordResult> {
  try {
    await apiClient.post(`${BASE}/password`, payload);
    return { success: true };
  } catch (err: unknown) {
    // Extract backend detail message from Axios error response body so the
    // component can make field-level routing decisions.
    // Without this, component only sees "Request failed with status code 401"
    // and cannot detect wrong-current-password vs other errors.
    const axiosErr = err as {
      response?: { data?: { detail?: string } };
      message?: string;
    };
    const detail = axiosErr?.response?.data?.detail;
    if (detail) {
      throw new Error(detail);
    }
    throw err;
  }
}

export function useChangePassword() {
  const mutation = useMutation({
    mutationFn: changePassword,
  });

  return {
    changePassword: async (payload: ChangePasswordPayload) => {
      await mutation.mutateAsync(payload);
    },
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error: mutation.error,
    reset: mutation.reset,
  };
}
