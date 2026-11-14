/**
 * useCheckConflicts — Preview-only conflict check (no side effects)
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useCheckConflicts.ts
 *
 * POST /api/v1/scheduling/jobs/{id}/check-conflicts
 * Called before confirming a move to show ConflictPreviewPane.
 * No side effects — does NOT execute the move.
 *
 * DISPATCH-B1: Rewritten to the real /scheduling endpoint and real request shape.
 * Uses mapConflictResponse to adapt the backend response to ConflictPreviewPane shape.
 *
 * Per DISPATCH-B1 design doc §D.3
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { CheckConflictsResponse } from "../types-stub";
import {
  mapConflictResponse,
  type RawCheckConflictsResponse,
} from "../utils/mapConflictResponse";

/** Request body for POST /api/v1/scheduling/jobs/{id}/check-conflicts */
export interface CheckConflictsRealRequest {
  tech_user_id: string;
  scheduled_start_at: string; // ISO 8601
  scheduled_end_at: string; // ISO 8601
}

async function checkConflictsFn(
  jobId: string,
  req: CheckConflictsRealRequest,
): Promise<CheckConflictsResponse> {
  const res = await apiClient.post<RawCheckConflictsResponse>(
    `/api/v1/scheduling/jobs/${jobId}/check-conflicts`,
    req,
  );
  return mapConflictResponse(res.data);
}

export function useCheckConflicts() {
  return useMutation({
    mutationFn: ({
      jobId,
      request,
    }: {
      jobId: string;
      request: CheckConflictsRealRequest;
    }) => checkConflictsFn(jobId, request),
  });
}
