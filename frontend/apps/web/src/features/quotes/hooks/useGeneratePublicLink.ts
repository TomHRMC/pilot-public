/**
 * useGeneratePublicLink — mutation hook to generate a signed public link for a quote version
 *
 * Location: apps/web/src/features/quotes/hooks/useGeneratePublicLink.ts
 *
 * Endpoint: POST /api/v1/quotes/{quoteId}/versions/{versionId}/public-link
 *
 * IMPORTANT: This endpoint requires a versionId (quote_version_id from QuoteDetailResponse).
 * The mutation is ONLY called from SendQuotePreviewModal after user clicks "Confirm Send".
 * This enforces the always-preview-before-send platform pattern (mvp-arch §16.7).
 *
 * Returns: QuotePublicLinkResponse { id, quote_id, contact_id, url, expires_at, signed_token }
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export type GeneratePublicLinkInput = {
  versionId: string;
  contact_id?: string | null;
  expires_at?: string | null;
  max_uses?: number | null;
};

export type PublicLinkResponse = {
  id: string;
  quote_id: string;
  contact_id: string | null;
  url: string;
  expires_at: string | null;
  signed_token: string | null;
};

export function useGeneratePublicLink(quoteId: string) {
  return useMutation({
    mutationFn: async (
      input: GeneratePublicLinkInput,
    ): Promise<PublicLinkResponse> => {
      const { versionId, ...body } = input;
      const res = await apiClient.post(
        `/api/v1/quotes/${quoteId}/versions/${versionId}/public-link`,
        {
          contact_id: body.contact_id ?? null,
          expires_at: body.expires_at ?? null,
          ...(body.max_uses != null ? { max_uses: body.max_uses } : {}),
        },
      );
      return res.data as PublicLinkResponse;
    },
  });
}
