/**
 * useStalenessRetry — Pre-Commit 409 Retry Hook
 *
 * Location: packages/ui/src/hooks/useStalenessRetry.ts
 * Exported from: packages/ui/src/hooks/index.ts + packages/ui/src/index.ts
 *
 * Established in FE-B4 (dispatch board move mutation).
 * Consumed by FE-B5 (quote approval), FE-B8 (calendar conflict resolve),
 * FE-B9 (QB conflict), FE-B10 (SMS reply).
 *
 * Pattern ref: mvp-arch.md §16.4; pilot-react-engineer-methods.md §9.3
 *
 * ⚠️ INTERFACE LOCKED — changes require downstream impact review for
 * FE-B5, FE-B8, FE-B9, FE-B10. See batch-fe-b4-design.md §F.1 §G.2.
 */

import React, { useCallback, useRef, useState } from "react";
import {
  useMutation,
  type UseMutationOptions,
  type UseMutationResult,
} from "@tanstack/react-query";
import { StalenessRefreshDialog } from "../staleness-refresh-dialog/StalenessRefreshDialog";

// ─── Types (exported for downstream consumers) ────────────────────────────────

/** The raw 409 Conflict response body from any backend endpoint using the §16.4 pattern */
export interface StalenessConflictPayload<TRefreshedState> {
  status: 409;
  title: string; // "Record updated since last view"
  detail: string; // Human-readable explanation
  refreshed_state: TRefreshedState;
}

/**
 * Options passed to useStalenessRetry.
 *
 * @template TVariables - The mutation variables type (must include a version field, e.g., expected_updated_at)
 * @template TData - The mutation success response type
 * @template TRefreshedState - The refreshed server state type returned in the 409 body
 */
export interface UseStalenessRetryOptions<TVariables, TData, TRefreshedState> {
  /** The underlying mutation function — identical signature to useMutation's mutationFn */
  mutationFn: (variables: TVariables) => Promise<TData>;

  /**
   * Called when a 409 is received with refreshed state.
   * Return updated variables for the retry attempt, or null to cancel.
   * If null, the dialog remains open awaiting user decision.
   */
  onConflict?: (
    refreshedState: TRefreshedState,
    previousVariables: TVariables,
  ) => TVariables | null;

  /**
   * Optional: override the dialog's title text.
   * Default: "This record was updated while you were working"
   */
  dialogTitle?: string;

  /**
   * Optional: custom content rendered inside the dialog above the action buttons.
   * Receives refreshed state + original variables. Used by FE-B5+ to render <DiffView>.
   * FE-B4 (dispatch board) renders a simple slot summary — no diff needed here.
   */
  renderConflictContent?: (params: {
    refreshedState: TRefreshedState;
    previousVariables: TVariables;
  }) => React.ReactNode;

  /** Any additional UseMutation options (onSuccess, onError, etc.) */
  mutationOptions?: Omit<
    UseMutationOptions<TData, unknown, TVariables>,
    "mutationFn"
  >;
}

/**
 * Return value of useStalenessRetry.
 *
 * The StalenessDialog component MUST be rendered in the same tree.
 * It is null when no staleness conflict is pending.
 */
export interface UseStalenessRetryReturn<TVariables, TData> {
  /** Call this like useMutation's mutate — staleness handling is transparent */
  mutate: (variables: TVariables) => void;

  /** Async version for use in event handlers that await the result */
  mutateAsync: (variables: TVariables) => Promise<TData>;

  /** True when a 409 was received and the dialog is open */
  isStalenessDialogOpen: boolean;

  /**
   * The dialog component. Must be rendered somewhere in the component tree.
   * Typically rendered adjacent to the trigger button.
   */
  StalenessDialog: React.FC;

  /** Forward the full TanStack Query mutation result for status tracking */
  mutation: UseMutationResult<TData, unknown, TVariables>;
}

// ─── Implementation ────────────────────────────────────────────────────────────

/**
 * Wraps any mutation that can receive a 409 Conflict (staleness check).
 * On 409, fetches refreshed state, surfaces <StalenessRefreshDialog>,
 * and allows retry with new version data.
 *
 * @example
 * const { mutate, StalenessDialog } = useStalenessRetry({
 *   mutationFn: (vars) => apiClient.post('/api/v1/schedule/jobs/123/reschedule', vars),
 *   onConflict: (refreshed, prev) => ({ ...prev, expected_updated_at: refreshed.updated_at }),
 *   renderConflictContent: ({ refreshedState }) => (
 *     <p>Current slot: {refreshedState.tech_name} at {refreshedState.start_time}</p>
 *   ),
 * });
 * // In JSX: <StalenessDialog />
 */
export function useStalenessRetry<TVariables, TData, TRefreshedState>(
  options: UseStalenessRetryOptions<TVariables, TData, TRefreshedState>,
): UseStalenessRetryReturn<TVariables, TData> {
  const {
    mutationFn,
    onConflict,
    dialogTitle,
    renderConflictContent,
    mutationOptions,
  } = options;

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const conflictPayloadRef =
    useRef<StalenessConflictPayload<TRefreshedState> | null>(null);
  const previousVariablesRef = useRef<TVariables | null>(null);

  const mutation = useMutation<TData, unknown, TVariables>({
    ...mutationOptions,
    mutationFn: async (variables: TVariables) => {
      try {
        return await mutationFn(variables);
      } catch (err: unknown) {
        // Check if this is a 409 staleness conflict
        const error = err as {
          status?: number;
          response?: { status?: number; data?: unknown };
          data?: unknown;
        };
        const status = error?.status ?? error?.response?.status;
        const body = (error?.data ?? error?.response?.data) as
          | StalenessConflictPayload<TRefreshedState>
          | undefined;

        if (status === 409 && body?.refreshed_state !== undefined) {
          conflictPayloadRef.current = body;
          previousVariablesRef.current = variables;

          // Per §G.2: call onConflict immediately on 409.
          // If it returns non-null variables → auto-retry without dialog interaction.
          // If it returns null → open dialog for explicit user decision.
          if (onConflict) {
            const retryVars = onConflict(body.refreshed_state, variables);
            if (retryVars !== null) {
              // Auto-retry with updated variables — no dialog needed
              return mutationFn(retryVars);
            }
          }

          // No onConflict, or onConflict returned null → show dialog
          setDialogOpen(true);
          throw new StalenessError(body);
        }

        throw err;
      }
    },
    onSuccess: (data: TData, variables: TVariables, context: unknown) => {
      setDialogOpen(false);
      conflictPayloadRef.current = null;
      previousVariablesRef.current = null;
      // TanStack Query v5: onSuccess takes (data, variables, context, mutation)
      // We pass undefined for the mutation param as it's not needed here
      mutationOptions?.onSuccess?.(
        data,
        variables,
        context,
        undefined as never,
      );
    },
  });

  const handleRetry = useCallback(async () => {
    const payload = conflictPayloadRef.current;
    const prevVars = previousVariablesRef.current;

    if (!payload || !prevVars) return;

    let retryVariables: TVariables | null = prevVars;

    if (onConflict) {
      retryVariables = onConflict(payload.refreshed_state, prevVars);
    }

    if (retryVariables === null) {
      // onConflict returned null — keep dialog open for manual decision
      return;
    }

    setIsRetrying(true);
    try {
      await mutation.mutateAsync(retryVariables);
      setDialogOpen(false);
    } finally {
      setIsRetrying(false);
    }
  }, [mutation, onConflict]);

  const handleCancel = useCallback(() => {
    setDialogOpen(false);
    conflictPayloadRef.current = null;
    previousVariablesRef.current = null;
  }, []);

  // Build the dialog component — bound to this hook's state
  const StalenessDialog: React.FC = useCallback(() => {
    const payload = conflictPayloadRef.current;
    const prevVars = previousVariablesRef.current;

    const childContent =
      renderConflictContent && payload && prevVars
        ? renderConflictContent({
            refreshedState: payload.refreshed_state,
            previousVariables: prevVars,
          })
        : undefined;

    return React.createElement(
      StalenessRefreshDialog,
      {
        isOpen: dialogOpen,
        onRetry: handleRetry,
        onCancel: handleCancel,
        title: dialogTitle,
        isRetrying,
      },
      childContent,
    );
  }, [
    dialogOpen,
    handleRetry,
    handleCancel,
    dialogTitle,
    isRetrying,
    renderConflictContent,
  ]);

  const mutate = useCallback(
    (variables: TVariables) => {
      mutation.mutate(variables);
    },
    [mutation],
  );

  const mutateAsync = useCallback(
    (variables: TVariables) => {
      return mutation.mutateAsync(variables);
    },
    [mutation],
  );

  return {
    mutate,
    mutateAsync,
    isStalenessDialogOpen: dialogOpen,
    StalenessDialog,
    mutation,
  };
}

// ─── Internal error type ───────────────────────────────────────────────────────

/** Sentinel error type so callers can distinguish 409 staleness from other errors */
export class StalenessError<TRefreshedState> extends Error {
  readonly payload: StalenessConflictPayload<TRefreshedState>;

  constructor(payload: StalenessConflictPayload<TRefreshedState>) {
    super(payload.detail || "Record updated since last view");
    this.name = "StalenessError";
    this.payload = payload;
  }
}
