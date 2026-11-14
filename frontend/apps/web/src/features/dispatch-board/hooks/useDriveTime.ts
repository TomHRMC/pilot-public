/**
 * useDriveTime — Drive-time matrix for visible job pairs
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useDriveTime.ts
 *
 * POST /api/v1/schedule/drive-times (batch request for all consecutive job pairs)
 * Results cached in TanStack Query; read-only during drag (no new API call during drag).
 *
 * Per batch-fe-b4-design.md §A.2.7
 */

import { useQuery } from "@tanstack/react-query";
import type { DriveTimeSegment } from "../types-stub";
import { apiClient } from "@pilot/shared-api";

interface DriveTimeSegmentRequest {
  from_job_id: string;
  to_job_id: string;
}

async function fetchDriveTimes(
  segments: DriveTimeSegmentRequest[],
  date: string,
): Promise<DriveTimeSegment[]> {
  if (segments.length === 0) return [];

  const res = await apiClient.post("/api/v1/schedule/drive-times", {
    segments,
    date,
  });
  const data = res.data as { segments: DriveTimeSegment[] };
  return data.segments;
}

export function useDriveTime(
  segments: DriveTimeSegmentRequest[],
  date: string,
) {
  return useQuery({
    queryKey: [
      "drive-times",
      date,
      segments.map((s) => `${s.from_job_id}-${s.to_job_id}`),
    ],
    queryFn: () => fetchDriveTimes(segments, date),
    enabled: segments.length > 0,
    staleTime: 5 * 60_000, // 5 minutes — drive times don't change frequently
  });
}
