/**
 * useChangeJobStatus — Offline-first job status change hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useChangeJobStatus.ts
 *
 * Per batch-fe-b7-design.md Section A.3.1.
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { JobStatusChange } from "../../../database/models/JobStatusChange";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface ChangeJobStatusInput {
  jobId: string;
  fromStatus: string;
  toStatus: string;
  changedAt?: Date;
  notes?: string;
}

export interface UseChangeJobStatusReturn {
  change: (input: ChangeJobStatusInput) => Promise<JobStatusChange>;
  isPending: boolean;
  error: Error | null;
}

export function useChangeJobStatus(): UseChangeJobStatusReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const change = useCallback(
    async (input: ChangeJobStatusInput): Promise<JobStatusChange> => {
      setIsPending(true);
      setError(null);
      try {
        const now = new Date();
        const statusChange = await database.write(async () => {
          return database
            .get<JobStatusChange>("job_status_changes")
            .create((record) => {
              record.jobId = input.jobId;
              record.fromStatus = input.fromStatus;
              record.toStatus = input.toStatus;
              record.changedAt = input.changedAt ?? now;
              record.notes = input.notes ?? null;
              record.localSyncStatus = "pending";
              record.idempotencyKey = generateIdempotencyKey();
              record.syncError = null;
              record.retryCount = 0;
              record.clientCaptureAt = now;
            });
        });
        setIsPending(false);
        return statusChange;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        setIsPending(false);
        throw error;
      }
    },
    [],
  );

  return { change, isPending, error };
}
