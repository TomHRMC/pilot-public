/**
 * timeHelpers — Shared time/pixel utilities for dispatch board views
 *
 * Location: apps/web/src/features/dispatch-board/utils/timeHelpers.ts
 *
 * Extracted from DispatchBoardLanes.tsx so both DispatchBoardLanes
 * and DispatchGridDayView can share the same snap/px helpers.
 *
 * Per DISPATCH-B1 design doc §I / UI spec §Implementation Notes §2
 */

/** Default board day start hour (6 AM) — expands earlier if a job starts before this */
export const DEFAULT_DAY_START_HOUR = 6;
/** Default board day end hour (18 = 6 PM) — expands later if a job ends after this */
export const DEFAULT_DAY_END_HOUR = 18;
/** Width per hour in pixels (must be on 4px grid: 80) */
export const HOUR_WIDTH_PX = 80;
/** Height of each lane/tech row (on 4px grid: 72) */
export const LANE_HEIGHT_PX = 72;
/** Lane label column width (on 4px grid: 64) */
export const LANE_LABEL_WIDTH_PX = 64;
/** Tech header column width — wider than lane label to fit tech name + avatar */
export const TECH_HEADER_WIDTH_PX = 128;

/**
 * Convert a Date to horizontal pixel offset from the viewport start.
 */
export function dateToPx(date: Date, viewStartHour: number): number {
  const hours = date.getHours() + date.getMinutes() / 60;
  return (hours - viewStartHour) * HOUR_WIDTH_PX;
}

/**
 * Convert a pixel offset back to a Date, anchored to the given base date.
 */
export function pxToDate(
  px: number,
  baseDate: Date,
  viewStartHour: number,
): Date {
  const hours = px / HOUR_WIDTH_PX + viewStartHour;
  const result = new Date(baseDate);
  result.setHours(Math.floor(hours), Math.round((hours % 1) * 60), 0, 0);
  return result;
}

/**
 * Snap a Date to the nearest 15-minute boundary.
 */
export function snapTo15Min(date: Date): Date {
  const mins = date.getMinutes();
  const snapped = Math.round(mins / 15) * 15;
  const result = new Date(date);
  result.setMinutes(snapped, 0, 0);
  return result;
}

/**
 * Compute the effective viewport start/end hours from the jobs on the board.
 * Defaults to 6am–6pm. Expands if any job starts earlier or ends later.
 *
 * Examples:
 *   Job 5am–9am  → startHour=5, endHour=18
 *   Job 7am–7pm  → startHour=6, endHour=19
 *   No jobs      → startHour=6, endHour=18
 */
export function computeViewportHours(
  jobs: Array<{
    scheduled_start_at: string | null;
    scheduled_end_at: string | null;
  }>,
): { startHour: number; endHour: number } {
  let startHour = DEFAULT_DAY_START_HOUR;
  let endHour = DEFAULT_DAY_END_HOUR;

  for (const job of jobs) {
    if (!job.scheduled_start_at || job.scheduled_start_at === "null") continue;
    if (!job.scheduled_end_at || job.scheduled_end_at === "null") continue;

    const start = new Date(job.scheduled_start_at);
    const end = new Date(job.scheduled_end_at);

    const jobStartHour = start.getHours() + start.getMinutes() / 60;
    const jobEndHour = end.getHours() + end.getMinutes() / 60;

    if (jobStartHour < startHour) startHour = Math.floor(jobStartHour);
    if (jobEndHour > endHour) endHour = Math.ceil(jobEndHour);
  }

  return { startHour, endHour };
}

/**
 * Build an array of hour labels for the time axis header.
 */
export function getHourLabels(
  viewStartHour: number,
  viewEndHour: number,
): Array<{ hour: number; label: string }> {
  const totalHours = viewEndHour - viewStartHour;
  return Array.from({ length: totalHours + 1 }, (_, i) => {
    const hour = viewStartHour + i;
    const label =
      hour === 12 ? "12 PM" : hour < 12 ? `${hour} AM` : `${hour - 12} PM`;
    return { hour, label };
  });
}
