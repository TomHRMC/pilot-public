"use client";

/**
 * AppSidebar — Persistent left navigation for all authenticated web routes
 *
 * Location: apps/web/src/components/AppSidebar.tsx
 *
 * UI-FIX-2E: Full redesign
 *   - 9 Heroicons 2.0 outline SVG items (no emoji)
 *   - Collapsible: w-fit min-w-[160px] max-w-[200px] (expanded) / w-16 (collapsed)
 *   - No wordmark — removed entirely
 *   - Active left-border accent: border-l-2 border-brand-600
 *   - Toggle button: pill «/» at top-right border overlap (FE-UI-NAV-S1)
 *   - State persisted to localStorage via useSidebarState hook
 *   - RBAC: Reports (reports.view), Catalog (catalog.view) — hide-not-disable
 *
 * FE-UI-NAV-S1:
 *   - Width changed from fixed 16rem to w-fit min-w-[160px] max-w-[200px]
 *   - Bottom Collapse button removed
 *   - Pill «/» toggle added at top-right border overlap (absolute top-3 -right-3)
 *
 * New nav order: Dashboard, Schedule, Customers, Quotes, Jobs, Invoices,
 *               Comms, Catalog, Reports
 */

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRequiresPermission, useHasPermission } from "@pilot/ui/role-gate";
import { useSidebarState } from "@/hooks/useSidebarState";
import {
  Squares2X2Icon,
  CalendarDaysIcon,
  UsersIcon,
  DocumentTextIcon,
  WrenchScrewdriverIcon,
  BanknotesIcon,
  ChatBubbleLeftRightIcon,
  CubeIcon,
  ChartBarIcon,
  ChevronDoubleLeftIcon,
} from "@heroicons/react/24/outline";

// Use ElementType to avoid heroicons ForwardRefExoticComponent type mismatch
// across different React @types versions in the monorepo
type HeroIcon = React.ElementType<{
  className?: string;
  "aria-hidden"?: boolean | "false" | "true";
}>;

interface NavItem {
  label: string;
  href: string;
  icon: HeroIcon;
  // PLP-FIX-11: widened to string so schedule.view_all (not in the
  // PermissionKey union) can gate the Schedule nav item. Matches the
  // string-accepting signatures of useHasPermission / useRequiresPermission.
  permission?: string;
}

const NAV_ITEMS: NavItem[] = [
  // PLP-FIX-7: All nav items gated via server-authoritative permission keys
  // (design §F.3 matrix). useRequiresPermission delegates to useHasPermission
  // which reads PilotUser.permissions from GET /users/me/permissions.
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: Squares2X2Icon,
    permission: "dashboard.manage",
  },
  {
    label: "Schedule",
    href: "/schedule",
    icon: CalendarDaysIcon,
    // PLP-FIX-11 (INV-BUG-18): gate on schedule.view_all (the read key) so
    // accountant (read-only board) sees the nav item. owner/office_staff hold
    // both view_all + manage; write affordances inside the board stay gated
    // on schedule.manage. Pre-FIX-11 this was schedule.manage, which hid the
    // nav from accountant despite the view_all grant.
    permission: "schedule.view_all",
  },
  {
    label: "Customers",
    href: "/customers",
    icon: UsersIcon,
    permission: "customers.view",
  },
  {
    label: "Quotes",
    href: "/quotes",
    icon: DocumentTextIcon,
    permission: "quotes.view",
  },
  {
    label: "Jobs",
    href: "/jobs",
    icon: WrenchScrewdriverIcon,
    permission: "jobs.view",
  },
  {
    label: "Invoices",
    href: "/invoices",
    icon: BanknotesIcon,
    permission: "invoices.view",
  },
  {
    label: "Comms",
    href: "/comms",
    icon: ChatBubbleLeftRightIcon,
    // PLP-FIX-9: repointed from phantom comms.send to real BE vocabulary (communications.view)
    permission: "communications.view",
  },
  {
    label: "Catalog",
    href: "/catalog",
    icon: CubeIcon,
    permission: "catalog.view",
  },
  {
    label: "Reports",
    href: "/reports",
    icon: ChartBarIcon,
    permission: "reports.view",
  },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { isSidebarCollapsed, toggleSidebar } = useSidebarState();

  // PLP-FIX-7: Pre-compute all distinct permission checks at the top
  // (hook rules: no loops/conditionals). Each nav item's permission key
  // gets its own useRequiresPermission call.
  const canDashboard = useRequiresPermission("dashboard.manage");
  // PLP-FIX-11: Schedule nav gated on schedule.view_all (read key) so
  // accountant (read-only board) sees the nav item. useHasPermission is used
  // directly because schedule.view_all is not in the PermissionKey union.
  const canSchedule = useHasPermission("schedule.view_all");
  const canCustomers = useRequiresPermission("customers.view");
  const canQuotes = useRequiresPermission("quotes.view");
  const canJobs = useRequiresPermission("jobs.view");
  const canInvoices = useRequiresPermission("invoices.view");
  // PLP-FIX-9: repointed from phantom comms.send to real BE vocabulary (communications.view)
  const canComms = useRequiresPermission("communications.view");
  const canViewCatalog = useRequiresPermission("catalog.view");
  const canViewReports = useRequiresPermission("reports.view");

  // Map permission key → computed boolean
  // PLP-FIX-11: widened to Record<string, boolean> so schedule.view_all
  // (not in PermissionKey union) can index the map.
  const permissionGranted: Record<string, boolean> = {
    "dashboard.manage": canDashboard,
    "schedule.view_all": canSchedule,
    "customers.view": canCustomers,
    "quotes.view": canQuotes,
    "jobs.view": canJobs,
    "invoices.view": canInvoices,
    "communications.view": canComms,
    "catalog.view": canViewCatalog,
    "reports.view": canViewReports,
  };

  return (
    // FE-UI-NAV-S1: relative wrapper so pill toggle (absolute) can overlap the border
    <div className="relative shrink-0">
      <nav
        className={`flex flex-col h-full bg-white border-r border-neutral-200 overflow-hidden ${
          isSidebarCollapsed ? "w-16" : "w-fit min-w-40 max-w-[12.5rem]"
        }`}
        aria-label="Main navigation"
      >
        {/* Nav items */}
        <ul className="flex-1 py-3 space-y-0.5 px-2">
          {NAV_ITEMS.map((item) => {
            // Hide permission-gated items for roles that lack the required permission
            if (item.permission && !permissionGranted[item.permission])
              return null;

            const isActive =
              pathname === item.href || pathname.startsWith(item.href + "/");

            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  title={isSidebarCollapsed ? item.label : undefined}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex items-center gap-3 py-2 rounded-md text-sm transition-colors ${
                    isSidebarCollapsed ? "justify-center px-2" : ""
                  } ${
                    isActive
                      ? "bg-brand-50 text-brand-700 font-medium border-l-2 border-brand-600 pl-2.5"
                      : "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900 pl-3"
                  }`}
                >
                  <Icon className="w-5 h-5 shrink-0" aria-hidden="true" />
                  {!isSidebarCollapsed && (
                    <span className="truncate">{item.label}</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Pill toggle — overlaps sidebar right border (z-20 to stay above nav content) */}
      {/* FE-UI-NAV-S1: replaces the bottom Collapse button */}
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
