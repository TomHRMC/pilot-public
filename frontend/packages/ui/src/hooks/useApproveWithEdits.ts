/**
 * useApproveWithEdits — Approve-with-edits lifecycle hook
 *
 * Location: packages/ui/src/hooks/useApproveWithEdits.ts
 * Exported from: packages/ui/src/hooks/index.ts + packages/ui/src/index.ts
 *
 * Established in FE-B5 (quote approval workflow).
 * Manages the pending-edit staging lifecycle for owner-side quote approval.
 * Wraps the /api/v1/quotes/{id}/pending-edits CRUD endpoints.
 * Composes useStalenessRetry() for the final atomic approve call.
 *
 * ⚠️ WEB-ONLY — approval editing is an owner-side web surface.
 */

import React, { useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useStalenessRetry } from "./useStalenessRetry";

// ─── API payload types ─────────────────────────────────────────────────────────

export interface QuotePendingEditCreate {
  affected_line_item_id?: string | null;
  edit_type:
    | "field_edit"
    | "line_item_add"
    | "line_item_remove"
    | "price_override";
  field_name?: string | null;
  old_value?: string | null;
  new_value?: string | null;
}

export interface QuotePendingEditResponse {
  id: string;
  quote_id: string;
  affected_line_item_id: string | null;
  edit_type:
    | "field_edit"
    | "line_item_add"
    | "line_item_remove"
    | "price_override";
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface QuoteApproveRequest {
  expected_quote_version_id?: string | null;
  apply_pending_edits?: boolean;
}

export interface QuoteApproveResponse {
  id: string;
  status: string;
  quote_version_id: string;
  approved_at: string;
  approved_by_user_id: string;
}

// ─── Hook types ───────────────────────────────────────────────────────────────

export interface UseApproveWithEditsOptions {
  quoteId: string;
  quoteVersionId: string;
  onSuccess?: (response: QuoteApproveResponse) => void;
  onError?: (error: unknown) => void;
  /** API client function — defaults to fetch if not provided */
  apiClient?: {
    get: <T>(url: string) => Promise<T>;
    post: <T>(url: string, body?: unknown) => Promise<T>;
    patch: <T>(url: string, body?: unknown) => Promise<T>;
    delete: (url: string) => Promise<void>;
  };
}

export interface UseApproveWithEditsReturn {
  /** Stage a field-level edit. Creates or updates a quote_pending_edit row. */
  stagePendingEdit: (
    params: QuotePendingEditCreate,
  ) => Promise<QuotePendingEditResponse>;

  /** Revert a single pending edit by its edit_id. */
  revertPendingEdit: (editId: string) => Promise<void>;

  /** Cancel all pending edits for this reviewer (DELETE all). */
  cancelAllEdits: () => Promise<void>;

  /** Current pending edits for the current reviewer. */
  pendingEdits: QuotePendingEditResponse[];

  /** Whether any pending edits have been staged. */
  hasPendingEdits: boolean;

  /** Commit all pending edits and approve. Wraps useStalenessRetry(). */
  approveWithEdits: () => void;

  /** Approve without applying any edits. Also wraps useStalenessRetry(). */
  approveAsIs: () => void;

  /** True when approval mutation is in-flight. */
  isApproving: boolean;

  /** True when staging/reverting edits. */
  isStagingEdit: boolean;

  /**
   * The staleness dialog component from useStalenessRetry().
   * Must be rendered in the same component tree.
   */
  StalenessDialog: React.FC;
}

// ─── Default API client using fetch ───────────────────────────────────────────

function buildDefaultApiClient() {
  const baseHeaders = { "Content-Type": "application/json" };

  return {
    get: async <T>(url: string): Promise<T> => {
      const res = await fetch(url, { headers: baseHeaders });
      if (!res.ok) {
        const error = Object.assign(new Error(res.statusText), {
          status: res.status,
          data: await res.json().catch(() => null),
        });
        throw error;
      }
      return res.json() as Promise<T>;
    },
    post: async <T>(url: string, body?: unknown): Promise<T> => {
      const res = await fetch(url, {
        method: "POST",
        headers: baseHeaders,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const error = Object.assign(new Error(res.statusText), {
          status: res.status,
          data,
        });
        throw error;
      }
      return res.json() as Promise<T>;
    },
    patch: async <T>(url: string, body?: unknown): Promise<T> => {
      const res = await fetch(url, {
        method: "PATCH",
        headers: baseHeaders,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const error = Object.assign(new Error(res.statusText), {
          status: res.status,
          data,
        });
        throw error;
      }
      return res.json() as Promise<T>;
    },
    delete: async (url: string): Promise<void> => {
      const res = await fetch(url, { method: "DELETE", headers: baseHeaders });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const error = Object.assign(new Error(res.statusText), {
          status: res.status,
          data,
        });
        throw error;
      }
    },
  };
}

// ─── Implementation ────────────────────────────────────────────────────────────

/**
 * Manages the pending-edit staging lifecycle for owner-side quote approval.
 *
 * Flow:
 * 1. Owner edits a field → stagePendingEdit() → POST /pending-edits
 * 2. DiffView renders amber tint per staged edit
 * 3. Owner clicks "Approve with N edits" → approveWithEdits()
 *    → POST /approve with apply_pending_edits: true
 *    → useStalenessRetry handles 409 if another user updated the quote
 */
export function useApproveWithEdits({
  quoteId,
  quoteVersionId,
  onSuccess,
  onError,
  apiClient: providedApiClient,
}: UseApproveWithEditsOptions): UseApproveWithEditsReturn {
  const queryClient = useQueryClient();
  const api = providedApiClient ?? buildDefaultApiClient();

  const pendingEditsQueryKey = ["quotes", quoteId, "pending-edits"] as const;

  // ─ Fetch pending edits ─────────────────────────────────────────────────────
  const { data: pendingEdits = [] } = useQuery<QuotePendingEditResponse[]>({
    queryKey: pendingEditsQueryKey,
    queryFn: () =>
      api.get<QuotePendingEditResponse[]>(
        `/api/v1/quotes/${quoteId}/pending-edits`,
      ),
    staleTime: 30_000,
  });

  // ─ Stage a pending edit ────────────────────────────────────────────────────
  const stageMutation = useMutation<
    QuotePendingEditResponse,
    unknown,
    QuotePendingEditCreate
  >({
    mutationFn: (params) =>
      api.post<QuotePendingEditResponse>(
        `/api/v1/quotes/${quoteId}/pending-edits`,
        params,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: pendingEditsQueryKey });
    },
  });

  // ─ Revert a single pending edit ───────────────────────────────────────────
  const revertMutation = useMutation<void, unknown, string>({
    mutationFn: (editId) =>
      api.delete(`/api/v1/quotes/${quoteId}/pending-edits/${editId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: pendingEditsQueryKey });
    },
  });

  // ─ Cancel all pending edits ────────────────────────────────────────────────
  const cancelAllMutation = useMutation<void, unknown, void>({
    mutationFn: () => api.delete(`/api/v1/quotes/${quoteId}/pending-edits`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: pendingEditsQueryKey });
    },
  });

  // ─ Approve (with or without edits) via useStalenessRetry ─────────────────
  const {
    mutate: approveMutate,
    StalenessDialog,
    mutation: approveMutation,
  } = useStalenessRetry<
    QuoteApproveRequest,
    QuoteApproveResponse,
    { quote_version_id: string; line_items: unknown[] }
  >({
    mutationFn: (vars: QuoteApproveRequest) =>
      api.post<QuoteApproveResponse>(`/api/v1/quotes/${quoteId}/approve`, vars),
    onConflict: () => null, // Always show dialog on conflict for approval flow
    mutationOptions: {
      onSuccess: (data: QuoteApproveResponse) => {
        void queryClient.invalidateQueries({ queryKey: ["quotes", quoteId] });
        void queryClient.invalidateQueries({
          queryKey: ["quotes", "pending-approval"],
        });
        onSuccess?.(data);
      },
      onError,
    },
  });

  const approveWithEdits = useCallback(() => {
    approveMutate({
      expected_quote_version_id: quoteVersionId,
      apply_pending_edits: true,
    });
  }, [approveMutate, quoteVersionId]);

  const approveAsIs = useCallback(() => {
    approveMutate({
      expected_quote_version_id: quoteVersionId,
      apply_pending_edits: false,
    });
  }, [approveMutate, quoteVersionId]);

  const stagePendingEdit = useCallback(
    (params: QuotePendingEditCreate) => stageMutation.mutateAsync(params),
    [stageMutation],
  );

  const revertPendingEdit = useCallback(
    (editId: string) => revertMutation.mutateAsync(editId),
    [revertMutation],
  );

  const cancelAllEdits = useCallback(
    () => cancelAllMutation.mutateAsync(),
    [cancelAllMutation],
  );

  return {
    stagePendingEdit,
    revertPendingEdit,
    cancelAllEdits,
    pendingEdits,
    hasPendingEdits: pendingEdits.length > 0,
    approveWithEdits,
    approveAsIs,
    isApproving: approveMutation.isPending,
    isStagingEdit:
      stageMutation.isPending ||
      revertMutation.isPending ||
      cancelAllMutation.isPending,
    StalenessDialog,
  };
}
