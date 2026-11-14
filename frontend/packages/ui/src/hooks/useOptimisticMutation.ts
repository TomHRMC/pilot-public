/**
 * useOptimisticMutation — Offline-write + pending badge hook
 *
 * Location: packages/ui/src/hooks/useOptimisticMutation.ts
 *
 * Established in FE-B7. Consumed by FE-B9 and FE-B12 without interface changes.
 *
 * Key design: deferToOrchestrator = true by default.
 * The hook writes locally immediately; SyncOrchestrator handles the push.
 *
 * ⚠️ Interface locked — changes require FE-B9 and FE-B12 impact review.
 *
 * Per batch-fe-b7-design.md Section F.2 and §16.8 Optimistic UI.
 */

import { useState, useCallback, useRef } from "react";

export interface UseOptimisticMutationOptions<TVariables, TLocalRecord> {
  /**
   * Write to local state immediately.
   * Called synchronously on mutate(); receives full variables.
   * Must return a record for rollback if needed.
   */
  optimisticUpdate: (variables: TVariables) => Promise<TLocalRecord>;

  /**
   * Optional: undo the optimistic write on server error.
   * Defaults to marking the local record sync_status = 'failed'.
   */
  rollbackFn?: (localRecord: TLocalRecord, error: Error) => Promise<void>;

  /**
   * The mutation function itself (e.g., apiClient call).
   * Only called when deferToOrchestrator is false and device is online.
   */
  mutationFn?: (variables: TVariables) => Promise<void>;

  /**
   * If true, skips mutationFn and defers to the SyncOrchestrator.
   * Default: true. Set false for non-offline-entity optimistic patterns.
   */
  deferToOrchestrator?: boolean;
}

export interface UseOptimisticMutationReturn<TVariables> {
  mutate: (variables: TVariables) => void;
  mutateAsync: (variables: TVariables) => Promise<void>;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  reset: () => void;
}

export function useOptimisticMutation<TVariables, TLocalRecord = unknown>(
  options: UseOptimisticMutationOptions<TVariables, TLocalRecord>,
): UseOptimisticMutationReturn<TVariables> {
  const {
    optimisticUpdate,
    rollbackFn,
    mutationFn,
    deferToOrchestrator = true,
  } = options;

  const [isPending, setIsPending] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const localRecordRef = useRef<TLocalRecord | null>(null);

  const mutateAsync = useCallback(
    async (variables: TVariables): Promise<void> => {
      setIsPending(true);
      setIsError(false);
      setError(null);

      let localRecord: TLocalRecord;

      try {
        localRecord = await optimisticUpdate(variables);
        localRecordRef.current = localRecord;
      } catch (optimisticError) {
        const err =
          optimisticError instanceof Error
            ? optimisticError
            : new Error(String(optimisticError));
        setIsError(true);
        setError(err);
        setIsPending(false);
        throw err;
      }

      if (deferToOrchestrator) {
        setIsPending(false);
        return;
      }

      if (mutationFn) {
        try {
          await mutationFn(variables);
          setIsPending(false);
        } catch (mutationError) {
          const err =
            mutationError instanceof Error
              ? mutationError
              : new Error(String(mutationError));

          if (rollbackFn && localRecordRef.current !== null) {
            try {
              await rollbackFn(localRecordRef.current, err);
            } catch {
              console.error("[useOptimisticMutation] Rollback failed:", err);
            }
          }

          setIsError(true);
          setError(err);
          setIsPending(false);
          throw err;
        }
      } else {
        setIsPending(false);
      }
    },
    [optimisticUpdate, rollbackFn, mutationFn, deferToOrchestrator],
  );

  const mutate = useCallback(
    (variables: TVariables): void => {
      void mutateAsync(variables);
    },
    [mutateAsync],
  );

  const reset = useCallback(() => {
    setIsPending(false);
    setIsError(false);
    setError(null);
    localRecordRef.current = null;
  }, []);

  return { mutate, mutateAsync, isPending, isError, error, reset };
}
