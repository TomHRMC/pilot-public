/**
 * CustomerDetailTabs — client component for the customer detail tab bar
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/_components/CustomerDetailTabs.tsx
 *
 * Uses usePathname() to highlight the active tab with the same brand-50
 * backlight pattern used in SettingsSidebar and the main left navigation.
 * Active state: bg-brand-50 text-brand-700 border-b-2 border-brand-600
 * Inactive state: text-neutral-600 hover:text-neutral-900
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useHasPermission } from "@pilot/ui";

// PLP-FIX-9 (INV-BUG-12): Comms tab is permission-gated on communications.view.
// The tab array is computed inside the component so useHasPermission can run.
const BASE_TABS = [
  { label: "Overview", href: "" },
  { label: "Sites", href: "/sites" },
  { label: "Jobs", href: "/jobs" },
  { label: "Quotes", href: "/quotes" },
  { label: "Invoices", href: "/invoices" },
] as const;

const COMMS_TAB = { label: "Comms", href: "/comms" } as const;

interface CustomerDetailTabsProps {
  customerId: string;
}

export function CustomerDetailTabs({ customerId }: CustomerDetailTabsProps) {
  const pathname = usePathname();
  // PLP-FIX-9 (INV-BUG-12): Comms tab gated on communications.view (hide-not-disable)
  const canViewComms = useHasPermission("communications.view");
  const base = `/customers/${customerId}`;
  const TABS = canViewComms
    ? [...BASE_TABS.slice(0, 4), COMMS_TAB, BASE_TABS[4]]
    : [...BASE_TABS];

  const isActive = (tabHref: string) => {
    const fullHref = `${base}${tabHref}`;
    // Overview tab: exact match on /customers/[id]
    if (tabHref === "") {
      return pathname === base || pathname === `${base}/`;
    }
    // Other tabs: exact match or sub-path match
    return pathname === fullHref || pathname.startsWith(`${fullHref}/`);
  };

  return (
    <nav
      className="flex border-b border-neutral-200 bg-white px-6"
      aria-label="Customer tabs"
    >
      {TABS.map((tab) => {
        const active = isActive(tab.href);
        return (
          <Link
            key={tab.label}
            href={`${base}${tab.href}`}
            aria-current={active ? "page" : undefined}
            className={`relative mr-6 py-3 text-body font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
              active
                ? "border-b-2 border-brand-600 bg-brand-50 px-2 text-brand-700"
                : "text-neutral-600 hover:text-neutral-900"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
