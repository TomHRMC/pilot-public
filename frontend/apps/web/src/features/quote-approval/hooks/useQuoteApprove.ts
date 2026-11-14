/**
 * useQuoteApprove / useQuoteKickback / useQuoteReject — approval mutation hooks
 *
 * Location: apps/web/src/features/quote-approval/hooks/useQuoteApprove.ts
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// ─── Approve ──────────────────────────────────────────────────────────────────

export interface ApproveRequest {
  expected_quote_version_id?: string | null;
  apply_pending_edits?: boolean;
}

export interface ApproveResponse {
  id: string;
  status: string;
  quote_version_id: string;
  approved_at: string;
}

export function useQuoteApprove(quoteId: string) {
  const queryClient = useQueryClient();
  return useMutation<ApproveResponse, unknown, ApproveRequest>({
    mutationFn: async (vars) => {
      const res = await apiClient.post(
        `/api/v1/quotes/${quoteId}/approve`,
        vars,
      );
      return res.data as ApproveResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["quotes", quoteId] });
      void queryClient.invalidateQueries({
        queryKey: ["quotes", "pending-approval"],
      });
    },
  });
}

// ─── Kickback ─────────────────────────────────────────────────────────────────

export interface KickbackLineComment {
  line_item_id: string;
  comment: string;
}

export interface KickbackRequest {
  overall_comment?: string;
  line_comments?: KickbackLineComment[];
}

export interface KickbackResponse {
  id: string;
  status: string;
  kicked_back_at: string;
}

export function useQuoteKickback(quoteId: string) {
  const queryClient = useQueryClient();
  return useMutation<KickbackResponse, unknown, KickbackRequest>({
    mutationFn: async (vars) => {
      const res = await apiClient.post(
        `/api/v1/quotes/${quoteId}/kickback`,
        vars,
      );
      return res.data as KickbackResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["quotes", quoteId] });
      void queryClient.invalidateQueries({
        queryKey: ["quotes", "pending-approval"],
      });
    },
  });
}

// ─── Reject ───────────────────────────────────────────────────────────────────

export interface RejectRequest {
  reason: string;
}

export interface RejectResponse {
  id: string;
  status: string;
  rejected_at: string;
}

export function useQuoteReject(quoteId: string) {
  const queryClient = useQueryClient();
  return useMutation<RejectResponse, unknown, RejectRequest>({
    mutationFn: async (vars) => {
      const res = await apiClient.post(
        `/api/v1/quotes/${quoteId}/reject`,
        vars,
      );
      return res.data as RejectResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["quotes", quoteId] });
      void queryClient.invalidateQueries({
        queryKey: ["quotes", "pending-approval"],
      });
    },
  });
}
