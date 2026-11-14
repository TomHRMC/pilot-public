/**
 * useCreateChangeOrder — Offline-first change order write hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useCreateChangeOrder.ts
 *
 * Per batch-fe-b7-design.md Section A.3.1.
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { ChangeOrder } from "../../../database/models/ChangeOrder";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface CreateChangeOrderInput {
  jobId: string;
  title: string;
  description?: string;
  totalAmountCents: number;
  status?: string;
}

export interface UseCreateChangeOrderReturn {
  create: (input: CreateChangeOrderInput) => Promise<ChangeOrder>;
  isPending: boolean;
  error: Error | null;
}

export function useCreateChangeOrder(): UseCreateChangeOrderReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const create = useCallback(
    async (input: CreateChangeOrderInput): Promise<ChangeOrder> => {
      setIsPending(true);
      setError(null);
      try {
        const now = new Date();
        const changeOrder = await database.write(async () => {
          return database.get<ChangeOrder>("change_orders").create((record) => {
            record.jobId = input.jobId;
            record.title = input.title;
            record.description = input.description ?? null;
            record.totalAmountCents = input.totalAmountCents;
            record.status = input.status ?? "draft";
            record.localSyncStatus = "pending";
            record.idempotencyKey = generateIdempotencyKey();
            record.syncError = null;
            record.retryCount = 0;
            record.clientCaptureAt = now;
          });
        });
        setIsPending(false);
        return changeOrder;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        setIsPending(false);
        throw error;
      }
    },
    [],
  );

  return { create, isPending, error };
}
