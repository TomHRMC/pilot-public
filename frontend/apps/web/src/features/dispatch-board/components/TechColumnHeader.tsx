/**
 * TechColumnHeader — Tech avatar + name + color dot
 *
 * Location: apps/web/src/features/dispatch-board/components/TechColumnHeader.tsx
 *
 * Per batch-fe-b4-design.md §A.2.1
 * Tech color dot uses data-driven dynamic style (the one legitimate inline style —
 * display_color comes from the API, not hardcoded).
 */

import React from "react";
import type { DispatchBoardTech } from "../types-stub";

interface TechColumnHeaderProps {
  tech: DispatchBoardTech;
  jobCount: number;
}

/**
 * TechColumnHeader
 *
 * Renders the header for a tech's column on the dispatch board.
 * The color dot uses the API-provided display_color hex value as
 * an inline style — this is the only legitimate use of a dynamic inline
 * style in this surface (data-driven, not hardcoded).
 */
export function TechColumnHeader({ tech, jobCount }: TechColumnHeaderProps) {
  const initials = tech.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="flex flex-col items-center gap-1 py-2 px-2 border-b border-neutral-200">
      {/* Avatar */}
      <div className="relative">
        {tech.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={tech.avatar_url}
            alt={tech.name}
            className="w-8 h-8 rounded-full object-cover"
          />
        ) : (
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-white text-caption font-medium"
            /* Data-driven color from API — the ONE legitimate inline style use */
            style={{ backgroundColor: tech.display_color ?? undefined }}
            aria-hidden="true"
          >
            {initials}
          </div>
        )}
        {/* Color dot indicator */}
        <span
          className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white"
          style={{ backgroundColor: tech.display_color ?? undefined }}
          aria-hidden="true"
        />
      </div>

      {/* Name */}
      <span className="text-caption font-medium text-neutral-900 text-center leading-tight">
        {tech.name.split(" ")[0]}
      </span>

      {/* Job count */}
      <span className="text-caption text-neutral-400">
        {jobCount} {jobCount === 1 ? "job" : "jobs"}
      </span>
    </div>
  );
}
