/**
 * SettingsSidebar — FE-B11
 *
 * Location: apps/web/src/features/settings/components/SettingsSidebar.tsx
 *
 * Settings sidebar navigation. Active group highlighted.
 * Items are role-gated per IA framework Decision 8 (hide-not-disable).
 *
 * UI-FIX-2E: Redesigned per design spec §9:
 *   - My Account group removed (now in ProfileDropdown header)
 *   - Billing standalone removed (now in ProfileDropdown menu)
 *   - Reordered: Team, Operations, Notifications, Sync & Storage, Integrations,
 *     Branding, Voice & AI, Security, Data & Privacy
 *   - "Communications" → "Branding"
 *   - "Security & MFA" → "Security"
 *   - Notifications: direct link to /settings/notifications/preferences (no sub-items)
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { CatalogEntry } from "@pilot/ui";
import { SettingsSidebarSearch } from "@pilot/ui";
import { useHasPermission } from "@pilot/ui/role-gate";
import { useRouter } from "next/navigation";

interface SidebarItem {
  label: string;
  href: string;
  subItems?: SidebarItem[];
  roleRequired?: string;
}

const SIDEBAR_ITEMS: SidebarItem[] = [
  // PLP-FIX-7: Team gated on users.view (office_staff sees it read-only;
  // manage affordances gated users.manage in TeamSettingsPage).
  { label: "Team", href: "/settings/team", roleRequired: "users.view" },
  {
    label: "Operations",
    href: "/settings/operations",
    roleRequired: "settings.tenant.write",
    subItems: [
      { label: "Margin buckets", href: "/settings/operations/margin-buckets" },
      {
        label: "Profitability rules",
        href: "/settings/operations/profitability-rules",
      },
      {
        label: "Field operations",
        href: "/settings/operations/field-operations",
      },
    ],
  },
  {
    label: "Notifications",
    href: "/settings/notifications/preferences",
    // No subItems — direct navigation to unified page (UI-FIX-2C)
  },
  {
    label: "Sync & Storage",
    href: "/settings/sync-storage",
    roleRequired: "settings.tenant.write",
    subItems: [
      {
        label: "Background sync",
        href: "/settings/sync-storage/background-sync",
      },
      {
        label: "Offline limits",
        href: "/settings/sync-storage/offline-limits",
      },
      { label: "Photos", href: "/settings/sync-storage/photos" },
      { label: "Voice capture", href: "/settings/sync-storage/voice-capture" },
    ],
  },
  {
    label: "Integrations",
    href: "/settings/integrations",
    roleRequired: "integrations.manage",
    subItems: [
      { label: "General", href: "/settings/integrations/general" },
      { label: "Calendar", href: "/settings/integrations/calendar" },
      {
        label: "QuickBooks",
        href: "/settings/integrations/quickbooks",
        subItems: [
          {
            label: "Auto-expiry & sync",
            href: "/settings/integrations/quickbooks/auto-expiry",
          },
        ],
      },
    ],
  },
  {
    label: "Branding",
    href: "/settings/communications",
    subItems: [
      {
        label: "Email Branding",
        href: "/settings/communications/email-branding",
      },
      {
        label: "SMS & 10DLC",
        href: "/settings/communications/sms-compliance",
      },
      {
        label: "Messaging Setup",
        href: "/settings/messaging",
      },
    ],
  },
  {
    label: "Website",
    href: "/settings/website",
    roleRequired: "settings.manage",
  },
  { label: "Voice & AI", href: "/settings/voice-ai" },
  { label: "Security", href: "/settings/security" },
  { label: "Data & Privacy", href: "/settings/data-privacy" },
];

interface SettingsSidebarProps {
  catalog?: CatalogEntry[];
  testID?: string;
}

export function SettingsSidebar({
  catalog = [],
  testID,
}: SettingsSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  // PLP-FIX-7: Pre-compute all distinct roleRequired permission checks
  // (hook rules: no loops/conditionals). Each distinct roleRequired value
  // gets its own useHasPermission call.
  const canUsersView = useHasPermission("users.view");
  const canSettingsTenantWrite = useHasPermission("settings.tenant.write");
  const canIntegrationsManage = useHasPermission("integrations.manage");
  const canSettingsManage = useHasPermission("settings.manage");

  const permissionMap: Record<string, boolean> = {
    "users.view": canUsersView,
    "settings.tenant.write": canSettingsTenantWrite,
    "integrations.manage": canIntegrationsManage,
    "settings.manage": canSettingsManage,
  };

  const handleNavigateToSetting = (entry: CatalogEntry) => {
    const path = `${entry.subSurfacePath}#${entry.key}`;
    router.push(path);
  };

  const isActive = (href: string) => pathname === href;
  const isAncestor = (href: string) =>
    pathname.startsWith(href) && pathname !== href;

  const renderItem = (item: SidebarItem, depth = 0) => {
    // PLP-FIX-7: Evaluate roleRequired — hide-not-disable for unauthorized items.
    if (item.roleRequired && !permissionMap[item.roleRequired]) {
      return null;
    }

    const active = isActive(item.href);
    const ancestor = isAncestor(item.href);
    const isExpanded = active || ancestor;

    return (
      <li key={item.href}>
        <Link
          href={item.href}
          className={`flex items-center rounded-md px-3 py-2 transition-colors ${
            // Depth-specific base typography
            depth === 0 ? "text-sm font-semibold" : "text-xs font-normal"
          } ${
            // Active / ancestor / default states
            active
              ? "bg-brand-50 font-medium text-brand-700"
              : ancestor
                ? "text-neutral-900 hover:bg-neutral-100"
                : depth === 0
                  ? "text-neutral-800 hover:bg-neutral-100"
                  : depth === 1
                    ? "text-neutral-600 hover:bg-neutral-100"
                    : "text-neutral-500 hover:bg-neutral-100"
          } ${
            // Depth indentation
            depth === 0 ? "" : depth === 1 ? "pl-6" : "pl-10"
          }`}
          data-testid={
            testID
              ? `${testID}-item-${item.href.replace(/\//g, "-")}`
              : undefined
          }
          aria-current={active ? "page" : undefined}
        >
          {item.label}
        </Link>

        {item.subItems && isExpanded && (
          <ul className="mt-0.5 space-y-0.5">
            {item.subItems.map((sub) => renderItem(sub, depth + 1))}
          </ul>
        )}
      </li>
    );
  };

  return (
    <nav
      aria-label="Settings navigation"
      className="flex h-full w-56 shrink-0 flex-col gap-4 overflow-y-auto py-6 pr-4"
      data-testid={testID ?? "settings-sidebar"}
    >
      {/* Search */}
      {catalog.length > 0 && (
        <div className="px-1">
          <SettingsSidebarSearch
            catalog={catalog}
            onNavigate={handleNavigateToSetting}
            testID={testID ? `${testID}-search` : "settings-sidebar-search"}
          />
        </div>
      )}

      {/* Nav items */}
      <ul className="space-y-0.5">
        {SIDEBAR_ITEMS.map((item) => renderItem(item))}
      </ul>
    </nav>
  );
}
