/**
 * laneHelpers — Shared lane assignment utilities for dispatch board
 *
 * Location: apps/web/src/features/dispatch-board/utils/laneHelpers.ts
 *
 * DISPATCH-B1.5: Extracted from DispatchBoardLanes.tsx so both
 * DispatchBoardLanes (day-lane view) and DispatchWeekLaneView (week-lane view)
 * share the same earliest-free-slot algorithm.
 *
 * Per dispatch-b1.5-ui-design-spec.md §Implementation Notes §3
 */

// ─── Types ────────────────────────────────────────────────────────────────────

/** Minimal job shape needed by lane assignment (subset of DispatchBoardJob) */
export interface LaneJob {
  id: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
}

// ─── assignJobsToLanes ────────────────────────────────────────────────────────

/**
 * Assign jobs to lanes using earliest-free-slot collision detection.
 * Returns a Map<jobId, laneIndex> (0-based lane indices).
 *
 * Algorithm: for each job (sorted by start time), find the first lane whose
 * end time is <= the job's start time. If no lane is free, the job is not
 * assigned (overflow — callers can treat as lane 0 or skip).
 *
 * This is the canonical lane assignment function for both day-board and
 * week-lane grid. Do NOT inline a copy — always import from here.
 */
export function assignJobsToLanes<T extends LaneJob>(
  jobs: T[],
  laneCount: number,
): Map<string, number> {
  const assignment = new Map<string, number>();
  const scheduledJobs = jobs
    .filter(
      (j) =>
        j.scheduled_start_at &&
        j.scheduled_end_at &&
        j.scheduled_start_at !== "null",
    )
    .sort(
      (a, b) =>
        new Date(a.scheduled_start_at!).getTime() -
        new Date(b.scheduled_start_at!).getTime(),
    );

  const laneEndTimes: Date[] = Array.from(
    { length: laneCount },
    () => new Date(0),
  );

  for (const job of scheduledJobs) {
    const start = new Date(job.scheduled_start_at!);
    const end = new Date(job.scheduled_end_at!);
    let assignedLane = -1;
    for (let i = 0; i < laneCount; i++) {
      if ((laneEndTimes[i]?.getTime() ?? 0) <= start.getTime()) {
        assignedLane = i;
        break;
      }
    }
    if (assignedLane >= 0) {
      assignment.set(job.id, assignedLane);
      laneEndTimes[assignedLane] = end;
    }
  }

  return assignment;
}

// ─── checkLaneAvailability ────────────────────────────────────────────────────

/**
 * checkLaneAvailability — client-side lane overlap check for a proposed job
 * placement on the day-board.
 *
 * Returns `available: true` if at least one lane is free during
 * [startTime, endTime]. Used by DispatchBoardLanes to validate drops.
 *
 * NOTE: This function is only used by DispatchBoardLanes (day-board).
 * DispatchWeekLaneView uses the simpler `jobs.length >= CAPACITY_LIMIT`
 * check per cell — see dispatch-b1.5-ui-design-spec.md §Implementation
 * Notes §4.
 */
export function checkLaneAvailability(
  jobs: LaneJob[],
  laneCount: number,
  startTime: Date,
  endTime: Date,
): { available: boolean; blockedLanes: number[] } {
  const assignment = assignJobsToLanes(jobs, laneCount);

  const occupiedLanes = new Set<number>();
  for (const job of jobs) {
    if (!job.scheduled_start_at || !job.scheduled_end_at) continue;
    const jobStart = new Date(job.scheduled_start_at);
    const jobEnd = new Date(job.scheduled_end_at);
    if (jobStart < endTime && jobEnd > startTime) {
      const lane = assignment.get(job.id);
      if (lane !== undefined) occupiedLanes.add(lane);
    }
  }

  const blockedLanes = Array.from(occupiedLanes);
  const available = occupiedLanes.size < laneCount;
  return { available, blockedLanes };
}
