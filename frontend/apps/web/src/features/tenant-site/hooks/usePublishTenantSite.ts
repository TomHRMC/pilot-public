"use client";

/**
 * usePublishTenantSite — POST /api/v1/tenant-site/publish
 *
 * Location: apps/web/src/features/tenant-site/hooks/usePublishTenantSite.ts
 *
 * C-B16: Publishes the tenant's compliance site. Handles the 409
 * `website_overwrite_requires_confirmation` branch — the error is surfaced
 * as a typed, inspectable result so the UI can switch PublishConfirmDialog
 * to the overwrite-confirm variant. Does NOT toast-and-swallow the 409.
 *
 * The 409 payload shape (RFC 7807 + extension fields):
 *   { current_url, new_url, brand_status, ... }
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form; invalidates ["tenant-site", "config"]
 *          onSettled.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { tenantSiteKeys } from "./tenantSiteQueryKeys";

type PublishResponse = components["schemas"]["PublishResponse"];

export interface PublishVariables {
  confirmWebsiteOverwrite?: boolean;
}

/** 409 overwrite-confirm payload extracted from the Axios error response. */
export interface WebsiteOverwriteConflict {
  current_url: string;
  new_url: string;
  brand_status: string;
  [key: string]: unknown;
}

function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function usePublishTenantSite() {
  const queryClient = useQueryClient();

  return useMutation<
    PublishResponse,
    unknown,
    PublishVariables,
    { conflict?: WebsiteOverwriteConflict }
  >({
    mutationFn: async (vars: PublishVariables) => {
      try {
        const res = await apiClient.post<PublishResponse>(
          "/api/v1/tenant-site/publish",
          { confirm_website_overwrite: vars.confirmWebsiteOverwrite ?? false },
          { headers: { "Idempotency-Key": generateIdempotencyKey() } },
        );
        return res.data;
      } catch (error: unknown) {
        // Surface the 409 as a typed error — do NOT swallow it.
        // The UI reads error.response.data to switch to the overwrite dialog.
        if (isAxiosError(error) && error.response?.status === 409) {
          // Re-throw so onError fires; the component inspects the error.
        }
        throw error;
      }
    },
    onError: (error) => {
      // Extract the 409 conflict payload into context for the UI to read.
      if (isAxiosError(error) && error.response?.status === 409) {
        const data = error.response.data as Record<string, unknown>;
        if (data && (data.current_url || data.new_url || data.brand_status)) {
          // The component reads this from the error object directly.
          // We attach it as a property on the error for convenience.
          (error as Error & { conflict?: WebsiteOverwriteConflict }).conflict =
            {
              current_url: data.current_url as string,
              new_url: data.new_url as string,
              brand_status: data.brand_status as string,
              ...data,
            };
        }
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: tenantSiteKeys.config });
    },
  });
}

/**
 * Extracts the 409 overwrite-confirm conflict payload from a publish error.
 * Returns null if the error is not a 409 or doesn't carry the conflict fields.
 */
export function extractOverwriteConflict(
  error: unknown,
): WebsiteOverwriteConflict | null {
  if (!isAxiosError(error)) return null;
  if (error.response?.status !== 409) return null;
  const data = error.response?.data as Record<string, unknown> | undefined;
  if (!data) return null;
  if (!data.current_url && !data.new_url && !data.brand_status) return null;
  return {
    current_url: data.current_url as string,
    new_url: data.new_url as string,
    brand_status: data.brand_status as string,
    ...data,
  };
}
