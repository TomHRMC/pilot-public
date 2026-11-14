/**
 * useCreatePhoto — Offline-first photo capture hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useCreatePhoto.ts
 *
 * Writes photo metadata to WatermelonDB and queues for S3 multipart upload.
 * Per batch-fe-b7-design.md Section A.3.1 and §15.5.
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { Photo } from "../../../database/models/Photo";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface CreatePhotoInput {
  jobId: string;
  expenseId?: string;
  localUri: string;
  mimeType: string;
  fileSizeBytes: number;
  wifiOnly?: boolean;
}

export interface UseCreatePhotoReturn {
  create: (input: CreatePhotoInput) => Promise<Photo>;
  isPending: boolean;
  error: Error | null;
}

export function useCreatePhoto(): UseCreatePhotoReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const create = useCallback(
    async (input: CreatePhotoInput): Promise<Photo> => {
      setIsPending(true);
      setError(null);
      try {
        const now = new Date();
        const photo = await database.write(async () => {
          return database.get<Photo>("photos").create((record) => {
            record.jobId = input.jobId;
            record.expenseId = input.expenseId ?? null;
            record.localUri = input.localUri;
            record.mimeType = input.mimeType;
            record.fileSizeBytes = input.fileSizeBytes;
            record.pilotPhotoId = null;
            record.uploadProgress = 0;
            record.s3SessionId = null;
            record.lastCompletedChunk = 0;
            record.wifiPending = input.wifiOnly ?? false;
            record.localSyncStatus = "pending";
            record.idempotencyKey = generateIdempotencyKey();
            record.syncError = null;
            record.retryCount = 0;
            record.clientCaptureAt = now;
          });
        });
        setIsPending(false);
        return photo;
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
