/**
 * useCreateExpense — Offline-first expense write hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useCreateExpense.ts
 *
 * Per batch-fe-b7-design.md Section A.3.1.
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { Expense } from "../../../database/models/Expense";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface CreateExpenseInput {
  jobId: string;
  userId: string;
  jobExpenseCategoryCode: string;
  costCents: number;
  description?: string;
  isBillable: boolean;
  incurredAt: Date;
}

export interface UseCreateExpenseReturn {
  create: (input: CreateExpenseInput) => Promise<Expense>;
  isPending: boolean;
  error: Error | null;
}

export function useCreateExpense(): UseCreateExpenseReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const create = useCallback(
    async (input: CreateExpenseInput): Promise<Expense> => {
      setIsPending(true);
      setError(null);
      try {
        const now = new Date();
        const expense = await database.write(async () => {
          return database.get<Expense>("expenses").create((record) => {
            record.jobId = input.jobId;
            record.userId = input.userId;
            record.jobExpenseCategoryCode = input.jobExpenseCategoryCode;
            record.costCents = input.costCents;
            record.description = input.description ?? null;
            record.isBillable = input.isBillable;
            record.incurredAt = input.incurredAt;
            record.localSyncStatus = "pending";
            record.idempotencyKey = generateIdempotencyKey();
            record.syncError = null;
            record.retryCount = 0;
            record.clientCaptureAt = now;
          });
        });
        setIsPending(false);
        return expense;
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
