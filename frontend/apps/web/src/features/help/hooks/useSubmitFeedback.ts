/**
 * useSubmitFeedback — TanStack Query mutation — FE-B16
 *
 * Location: apps/web/src/features/help/hooks/useSubmitFeedback.ts
 *
 * POST /api/v1/feedback (A87 endpoint per design doc)
 */

import { useMutation } from "@tanstack/react-query";
import type { FeedbackSubmission, FeedbackSubmitResponse } from "../types";
import { apiClient } from "@pilot/shared-api";

async function submitFeedback(
  data: FeedbackSubmission,
): Promise<FeedbackSubmitResponse> {
  const res = await apiClient.post<FeedbackSubmitResponse>(
    `/api/v1/feedback`,
    data,
  );
  return res.data;
}

export function useSubmitFeedback() {
  return useMutation({
    mutationFn: submitFeedback,
  });
}
