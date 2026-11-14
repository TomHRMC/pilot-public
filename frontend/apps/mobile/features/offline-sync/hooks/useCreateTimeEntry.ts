/**
 * useCreateTimeEntry — Offline-first time entry write hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useCreateTimeEntry.ts
 *
 * Writes to WatermelonDB with localSyncStatus = 'pending' and a generated
 * idempotency_key. SyncOrchestrator handles the server push.
 *
 * Pattern per batch-fe-b7-design.md Section A.3.1:
 *   1. Write to WatermelonDB with localSyncStatus = 'pending'
 *   2. Generate idempotency_key UUID at capture time (never changes across retries)
 *   3. TanStack Query cache NOT used — WatermelonDB is source of truth
 *   4. Returns { create, isPending, error } matching useOptimisticMutation shape
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { TimeEntry } from "../../../database/models/TimeEntry";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface CreateTimeEntryInput {
  jobId: string;
  userId: string;
  startedAt: Date;
  endedAt?: Date;
  hours?: number;
  notes?: string;
  checkInLat?: number;
  checkInLng?: number;
  hourlyRateCents?: number;
  hoursRemainingEstimate?: number;
  quoteLineId?: string;
}

export interface UseCreateTimeEntryReturn {
  create: (input: CreateTimeEntryInput) => Promise<TimeEntry>;
  isPending: boolean;
  error: Error | null;
}

export function useCreateTimeEntry(): UseCreateTimeEntryReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const create = useCallback(
    async (input: CreateTimeEntryInput): Promise<TimeEntry> => {
      setIsPending(true);
      setError(null);

      try {
        const idempotencyKey = generateIdempotencyKey();
        const now = new Date();

        const entry = await database.write(async () => {
          return database.get<TimeEntry>("time_entries").create((record) => {
            record.jobId = input.jobId;
            record.userId = input.userId;
            record.startedAt = input.startedAt;
            record.endedAt = input.endedAt ?? null;
            record.hours = input.hours ?? null;
            record.notes = input.notes ?? null;
            record.checkInLat = input.checkInLat ?? null;
            record.checkInLng = input.checkInLng ?? null;
            record.hourlyRateCents = input.hourlyRateCents ?? null;
            record.hoursRemainingEstimate =
              input.hoursRemainingEstimate ?? null;
            record.quoteLineId = input.quoteLineId ?? null;
            // Sync control fields (localSyncStatus to avoid WatermelonDB built-in collision)
            record.localSyncStatus = "pending";
            record.idempotencyKey = idempotencyKey;
            record.syncError = null;
            record.retryCount = 0;
            record.clientCaptureAt = now;
          });
        });

        setIsPending(false);
        return entry;
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
