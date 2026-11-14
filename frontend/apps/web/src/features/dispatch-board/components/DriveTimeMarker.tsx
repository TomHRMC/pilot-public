/**
 * DriveTimeMarker — Drive-time visualization between consecutive jobs
 *
 * Location: apps/web/src/features/dispatch-board/components/DriveTimeMarker.tsx
 *
 * Renders a horizontal dotted line between consecutive jobs showing drive time.
 * Turns red with label when infeasible (drive time > gap).
 * "Tight" threshold: drive_time > gap * 0.8 (20% buffer — visual affordance, not business rule).
 *
 * Per batch-fe-b4-design.md §A.2.2 §G.8
 */

import React from "react";
import type { DriveTimeSegment } from "../types-stub";

interface DriveTimeMarkerProps {
  segment: DriveTimeSegment | null;
  /** Top position in pixels */
  topPx: number;
  /** Gap in seconds between the two jobs */
  gapSeconds: number;
  isLoading?: boolean;
  isUnavailable?: boolean;
}

type DriveTimeStatus =
  | "normal"
  | "tight"
  | "infeasible"
  | "loading"
  | "unavailable";

function formatMinutes(seconds: number): string {
  const mins = Math.round(seconds / 60);
  return `${mins} min`;
}

function getStatus(
  segment: DriveTimeSegment | null,
  gapSeconds: number,
  isLoading: boolean,
  isUnavailable: boolean,
): DriveTimeStatus {
  if (isUnavailable) return "unavailable";
  if (isLoading || !segment) return "loading";
  if (!segment.is_feasible || segment.drive_time_seconds > gapSeconds)
    return "infeasible";
  if (segment.drive_time_seconds > gapSeconds * 0.8) return "tight";
  return "normal";
}

/**
 * DriveTimeMarker
 *
 * Shows drive time between consecutive tech jobs inline on the grid.
 * Uses token colors only — no hardcoded hex.
 */
export function DriveTimeMarker({
  segment,
  topPx,
  gapSeconds,
  isLoading = false,
  isUnavailable = false,
}: DriveTimeMarkerProps) {
  const status = getStatus(segment, gapSeconds, isLoading, isUnavailable);

  const lineClass =
    status === "infeasible"
      ? "border-fault-600"
      : status === "tight"
        ? "border-alert-400"
        : "border-neutral-300";

  const labelClass =
    status === "infeasible"
      ? "text-fault-600"
      : status === "tight"
        ? "text-alert-600"
        : "text-neutral-400";

  const label =
    status === "loading"
      ? "…"
      : status === "unavailable"
        ? "–"
        : segment
          ? formatMinutes(segment.drive_time_seconds)
          : "–";

  const suffixLabel =
    status === "infeasible"
      ? " Infeasible"
      : status === "tight"
        ? " Tight"
        : "";

  return (
    <div
      className="absolute left-0 right-0 flex items-center pointer-events-none"
      style={{ top: `${topPx}px` }}
      aria-hidden="true"
    >
      {/* Dotted line */}
      <div className={`flex-1 border-t border-dashed ${lineClass}`} />
      {/* Label */}
      <span className={`mx-1 text-caption whitespace-nowrap ${labelClass}`}>
        🚗 {label}
        {suffixLabel && <span className="font-medium">{suffixLabel}</span>}
      </span>
      <div className={`flex-1 border-t border-dashed ${lineClass}`} />
    </div>
  );
}
