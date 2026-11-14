/**
 * useCreateJobNote — Offline-first job note write hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useCreateJobNote.ts
 *
 * Per batch-fe-b7-design.md Section A.3.1.
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { JobNote } from "../../../database/models/JobNote";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface CreateJobNoteInput {
  jobId: string;
  createdBy: string;
  content: string;
  noteType?: string;
}

export interface UseCreateJobNoteReturn {
  create: (input: CreateJobNoteInput) => Promise<JobNote>;
  isPending: boolean;
  error: Error | null;
}

export function useCreateJobNote(): UseCreateJobNoteReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const create = useCallback(
    async (input: CreateJobNoteInput): Promise<JobNote> => {
      setIsPending(true);
      setError(null);
      try {
        const now = new Date();
        const note = await database.write(async () => {
          return database.get<JobNote>("job_notes").create((record) => {
            record.jobId = input.jobId;
            record.createdBy = input.createdBy;
            record.content = input.content;
            record.noteType = input.noteType ?? null;
            record.localSyncStatus = "pending";
            record.idempotencyKey = generateIdempotencyKey();
            record.syncError = null;
            record.retryCount = 0;
            record.clientCaptureAt = now;
          });
        });
        setIsPending(false);
        return note;
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
