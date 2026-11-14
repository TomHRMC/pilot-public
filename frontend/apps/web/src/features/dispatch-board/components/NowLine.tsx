/**
 * NowLine — Current time indicator across all tech columns
 *
 * Location: apps/web/src/features/dispatch-board/components/NowLine.tsx
 *
 * Red horizontal line spanning all columns at current time.
 * Updates every 60 seconds via setInterval.
 *
 * Per batch-fe-b4-design.md §A.2.1
 */

"use client";

import React, { useEffect, useState } from "react";

interface NowLineProps {
  /** Grid start hour (default 6 = 6 AM) */
  startHour?: number;
  /** Grid end hour (default 19 = 7 PM) */
  endHour?: number;
  /** Height per hour in pixels (default 60) */
  hourHeightPx?: number;
}

function getTopPercent(
  now: Date,
  startHour: number,
  endHour: number,
): number | null {
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const startMinutes = startHour * 60;
  const endMinutes = endHour * 60;

  if (nowMinutes < startMinutes || nowMinutes > endMinutes) return null;

  return ((nowMinutes - startMinutes) / (endMinutes - startMinutes)) * 100;
}

/**
 * NowLine
 *
 * Renders a red horizontal line at the current time position on the dispatch grid.
 * Position is recalculated every 60 seconds.
 */
export function NowLine({ startHour = 6, endHour = 19 }: NowLineProps) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(interval);
  }, []);

  const topPercent = getTopPercent(now, startHour, endHour);

  if (topPercent === null) return null;

  return (
    <div
      className="absolute left-0 right-0 z-10 pointer-events-none"
      style={{ top: `${topPercent}%` }}
      aria-hidden="true"
    >
      {/* Red dot on left edge */}
      <div className="absolute -left-1.5 -translate-y-1/2 w-3 h-3 rounded-full bg-fault-600" />
      {/* Red line */}
      <div className="h-px bg-fault-600 opacity-80" />
    </div>
  );
}
