/**
 * useConfirmLoto — Offline-first LOTO check confirmation hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useConfirmLoto.ts
 *
 * Per batch-fe-b7-design.md Section A.3.1.
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { LotoCheck } from "../../../database/models/LotoCheck";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface ConfirmLotoInput {
  jobId: string;
  checkType: string;
  confirmedAt?: Date;
  gpsLat?: number;
  gpsLng?: number;
}

export interface UseConfirmLotoReturn {
  confirm: (input: ConfirmLotoInput) => Promise<LotoCheck>;
  isPending: boolean;
  error: Error | null;
}

export function useConfirmLoto(): UseConfirmLotoReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const confirm = useCallback(
    async (input: ConfirmLotoInput): Promise<LotoCheck> => {
      setIsPending(true);
      setError(null);
      try {
        const now = new Date();
        const check = await database.write(async () => {
          return database.get<LotoCheck>("loto_checks").create((record) => {
            record.jobId = input.jobId;
            record.checkType = input.checkType;
            record.confirmedAt = input.confirmedAt ?? now;
            record.gpsLat = input.gpsLat ?? null;
            record.gpsLng = input.gpsLng ?? null;
            record.localSyncStatus = "pending";
            record.idempotencyKey = generateIdempotencyKey();
            record.syncError = null;
            record.retryCount = 0;
            record.clientCaptureAt = now;
          });
        });
        setIsPending(false);
        return check;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        setIsPending(false);
        throw error;
      }
    },
    [],
  );

  return { confirm, isPending, error };
}
