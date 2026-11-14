/**
 * useCreateInvoiceSignoff — Offline-first invoice sign-off write hook
 *
 * Location: apps/mobile/features/offline-sync/hooks/useCreateInvoiceSignoff.ts
 *
 * Mirrors useCreateJobNote.ts exactly: writes a WatermelonDB invoice_signoffs
 * row with localSyncStatus="pending", a generated idempotencyKey, and
 * clientCaptureAt. The sync engine pushes to
 * POST /api/v1/invoices/{invoice_id}/signoff on reconnect.
 *
 * The base64 PNG travels inline in the payload (design §G-R5 — ~20–60KB,
 * no presigned-PUT round-trip). Save always succeeds locally; the user
 * never waits on connectivity.
 *
 * Per batch-ce-1-design.md §F.2 and §E (§15 Offline Ops Contract).
 */

import { useCallback, useState } from "react";
import { database } from "../../../database";
import type { InvoiceSignoff } from "../../../database/models/InvoiceSignoff";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface CreateInvoiceSignoffInput {
  invoiceId: string;
  signedByName: string;
  termsAcknowledged: true;
  signaturePngBase64: string;
  capturedBy: string;
}

export interface UseCreateInvoiceSignoffReturn {
  create: (input: CreateInvoiceSignoffInput) => Promise<InvoiceSignoff>;
  isPending: boolean;
  error: Error | null;
}

export function useCreateInvoiceSignoff(): UseCreateInvoiceSignoffReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const create = useCallback(
    async (input: CreateInvoiceSignoffInput): Promise<InvoiceSignoff> => {
      setIsPending(true);
      setError(null);
      try {
        const now = new Date();
        const signoff = await database.write(async () => {
          return database
            .get<InvoiceSignoff>("invoice_signoffs")
            .create((record) => {
              record.invoiceId = input.invoiceId;
              record.signedByName = input.signedByName;
              record.termsAcknowledged = input.termsAcknowledged;
              record.signaturePngBase64 = input.signaturePngBase64;
              record.capturedBy = input.capturedBy;
              record.localSyncStatus = "pending";
              record.idempotencyKey = generateIdempotencyKey();
              record.syncError = null;
              record.retryCount = 0;
              record.clientCaptureAt = now;
            });
        });
        setIsPending(false);
        return signoff;
      } catch (err) {
        const writeError = err instanceof Error ? err : new Error(String(err));
        setError(writeError);
        setIsPending(false);
        throw writeError;
      }
    },
    [],
  );

  return { create, isPending, error };
}
