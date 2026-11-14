"use client";

/**
 * OperatorSidebar — Persistent left navigation for /operator/* routes
 *
 * Location: apps/web/src/components/operator/OperatorSidebar.tsx
 *
 * C-B15 Part B: Mirrors AppSidebar collapse conventions (pill toggle,
 * useSidebarState, active left-border accent) so the two shells feel
 * like one product. Shares the same localStorage key (pilot.sidebar.collapsed)
 * with AppSidebar per the design decision (spec §3.3/§14.8).
 *
 * Nav items:
 *   1. Cohort Dashboard (/operator/cohort) — active
 *   2. More operator tools — disabled placeholder (coming soon)
 *
 * RULE 5: zero hex codes. RULE 15: WCAG 2.2 AA.
 */

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSidebarState } from "@/hooks/useSidebarState";
import {
  Squares2X2Icon,
  EllipsisHorizontalCircleIcon,
  ChevronDoubleLeftIcon,
} from "@heroicons/react/24/outline";

type HeroIcon = React.ElementType<{
  className?: string;
  "aria-hidden"?: boolean | "false" | "true";
}>;

export function OperatorSidebar() {
  const pathname = usePathname();
  const { isSidebarCollapsed, toggleSidebar } = useSidebarState();

  const cohortHref = "/operator/cohort";
  const isCohortActive =
    pathname === cohortHref || pathname.startsWith(cohortHref + "/");

  const CohortIcon: HeroIcon = Squares2X2Icon;
  const PlaceholderIcon: HeroIcon = EllipsisHorizontalCircleIcon;

  return (
    <div className="relative shrink-0">
      <nav
        className={`flex flex-col h-full bg-white border-r border-neutral-200 overflow-hidden ${
          isSidebarCollapsed ? "w-16" : "w-fit min-w-40 max-w-[12.5rem]"
        }`}
        aria-label="Operator navigation"
      >
        <ul className="flex-1 py-3 space-y-0.5 px-2">
          {/* Item 1 — Cohort Dashboard (active) */}
          <li>
            <Link
              href={cohortHref}
              title={isSidebarCollapsed ? "Cohort Dashboard" : undefined}
              aria-current={isCohortActive ? "page" : undefined}
              className={`flex items-center gap-3 py-2 rounded-md text-sm transition-colors ${
                isSidebarCollapsed ? "justify-center px-2" : ""
              } ${
                isCohortActive
                  ? "bg-brand-50 text-brand-700 font-medium border-l-2 border-brand-600 pl-2.5"
                  : "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900 pl-3"
              }`}
            >
              <CohortIcon className="w-5 h-5 shrink-0" aria-hidden="true" />
              {!isSidebarCollapsed && (
                <span className="truncate">Cohort Dashboard</span>
              )}
            </Link>
          </li>

          {/* Item 2 — More operator tools (disabled placeholder) */}
          <li>
            <div
              aria-disabled="true"
              title="More operator tools coming soon"
              className={`flex items-center gap-3 py-2 text-sm text-neutral-400 cursor-not-allowed ${
                isSidebarCollapsed ? "justify-center px-2" : "pl-3"
              }`}
            >
              <PlaceholderIcon
                className="w-5 h-5 shrink-0 text-neutral-300"
                aria-hidden="true"
              />
              {!isSidebarCollapsed && (
                <span className="truncate">
                  More operator tools{" "}
                  <span className="text-caption text-neutral-400">
                    Coming soon
                  </span>
                </span>
              )}
            </div>
          </li>
        </ul>
      </nav>

      {/* Pill toggle — identical to AppSidebar */}
      <button
        type="button"
        onClick={toggleSidebar}
        aria-label={
          isSidebarCollapsed ? "Expand navigation" : "Collapse navigation"
        }
        title={isSidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
        className="absolute top-3 -right-3 z-20 flex items-center justify-center w-6 h-6 rounded-full bg-white border border-neutral-200 shadow-sm hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
      >
        <ChevronDoubleLeftIcon
          className={`w-3 h-3 text-neutral-500 transition-transform duration-200 ease-in-out ${
            isSidebarCollapsed ? "rotate-180" : "rotate-0"
          }`}
          aria-hidden="true"
        />
      </button>
    </div>
  );
}
