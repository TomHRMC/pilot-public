/**
 * useSignupLegalAccept — Legal acceptance mutation hook
 *
 * Location: apps/web/src/features/signup/hooks/useSignupLegalAccept.ts
 *
 * RULE 7: Legal acceptance is an IMMUTABLE audit record.
 * Before calling this mutation, check if the document is already_accepted=true
 * in the GET /legal/required response. If so, do NOT re-POST.
 *
 * This hook provides a helper that checks beforehand and skips the POST
 * if the server already has an acceptance record for the document.
 */

"use client";

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  LegalAcceptRequest,
  LegalAcceptResponse,
  LegalRequiredResponse,
  LegalDocumentType,
} from "../types";

interface UseLegalAcceptParams {
  tenantId: string;
}

interface AcceptDocumentsParams {
  documents: Array<{
    documentType: LegalDocumentType;
    versionHash: string;
  }>;
  /** Pass the required documents response to check already_accepted (RULE 7) */
  requiredDocuments: LegalRequiredResponse;
}

export function useSignupLegalAccept({ tenantId }: UseLegalAcceptParams) {
  return useMutation({
    mutationFn: async ({
      documents,
      requiredDocuments,
    }: AcceptDocumentsParams): Promise<LegalAcceptResponse[]> => {
      const results: LegalAcceptResponse[] = [];

      for (const doc of documents) {
        // RULE 7: Check if already accepted — skip POST if so
        const existingDoc = requiredDocuments.required_documents.find(
          (rd) => rd.document_type === doc.documentType,
        );

        if (existingDoc?.already_accepted) {
          // Already recorded — do not re-POST (immutable audit record)
          continue;
        }

        const body: LegalAcceptRequest = {
          document_type: doc.documentType,
          document_version_hash: doc.versionHash,
          accepted_at: new Date().toISOString(),
        };

        const response = await apiClient.post<LegalAcceptResponse>(
          `/api/v1/signup/${tenantId}/legal/accept`,
          body,
        );
        results.push(response.data);
      }

      return results;
    },
  });
}
