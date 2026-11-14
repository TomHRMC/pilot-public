"use client";

/**
 * SettingsIndexPage — FE-UI-NAV-S1
 *
 * Location: apps/web/src/features/settings/components/SettingsIndexPage.tsx
 *
 * Full settings index — 3-section, 3-column icon+description card grid.
 * Stripe/Clio pattern (Option 3 — design spec §17, §29.3).
 *
 * RBAC:
 *   - Personal section: all roles
 *   - Workspace section: settings.tenant.write (owner, operator)
 *   - Integrations & System: some cards gated individually
 *
 * Design spec §29.3 (Notifications card in Workspace, owner only):
 *   - Notifications card → /settings/notifications/tenant-defaults
 *   - Personal notifications → ProfileDropdown → /settings/notifications/preferences
 */

import Link from "next/link";
import { RoleGate } from "@pilot/ui/role-gate";
import type { PermissionKey } from "@pilot/ui/role-gate";
import {
  UserCircleIcon,
  ShieldCheckIcon,
  UsersIcon,
  AdjustmentsHorizontalIcon,
  BellIcon,
  SwatchIcon,
  GlobeAltIcon,
  MicrophoneIcon,
  ArrowsRightLeftIcon,
  CloudArrowUpIcon,
  LockClosedIcon,
  CreditCardIcon,
} from "@heroicons/react/24/outline";

// Reuse the same HeroIcon type as AppSidebar
type HeroIcon = React.ElementType<{
  className?: string;
  "aria-hidden"?: boolean | "false" | "true";
}>;

interface SettingsCard {
  label: string;
  icon: HeroIcon;
  description: string;
  href: string;
  permission?: PermissionKey;
}

interface SettingsSection {
  title: string;
  permission?: PermissionKey; // gates entire section via RoleGate
  cards: SettingsCard[];
}

// Design spec §29.3 — confirmed section/card layout
// FE-UI-NAV-S1 post-ship: Notifications added to Personal section for
// discoverability parity with ProfileDropdown (My Profile, Security, Notifications).
const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    title: "Personal",
    cards: [
      {
        label: "Profile & Account",
        icon: UserCircleIcon,
        description: "Your name, email, photo, and account preferences",
        href: "/settings/my-account/profile",
      },
      {
        label: "Security",
        icon: ShieldCheckIcon,
        description: "Password, MFA enrollment, and active sessions",
        href: "/settings/my-account/security",
      },
      {
        label: "Notifications",
        icon: BellIcon,
        description:
          "Your personal notification preferences for email, SMS, and push",
        href: "/settings/notifications/preferences",
      },
    ],
  },
  {
    // PLP-FIX-7: Section-level gate removed — each card is individually gated
    // so office_staff (who holds users.view but not settings.tenant.write)
    // can see the Team card. Operations/Sync/Website stay hidden via their
    // own card-level permissions matching the prod grant table.
    title: "Workspace",
    cards: [
      {
        label: "Team",
        icon: UsersIcon,
        description: "Manage team members, roles, and permissions",
        href: "/settings/team",
        // PLP-FIX-7: Team card gated on users.view (office_staff sees it
        // read-only; manage affordances gated users.manage in TeamSettingsPage).
        permission: "users.view",
      },
      {
        label: "Billing & Subscription",
        icon: CreditCardIcon,
        description:
          "View your plan, usage, and manage how customers pay invoices",
        href: "/settings/billing",
        permission: "billing.view",
      },
      {
        label: "Operations",
        icon: AdjustmentsHorizontalIcon,
        description:
          "Margin buckets, profitability rules, and field operation defaults",
        href: "/settings/operations",
        // PLP-FIX-7: Operations gated on settings.tenant.write (owner, accountant)
        permission: "settings.tenant.write",
      },
      {
        label: "Notifications",
        icon: BellIcon,
        description:
          "Set default notification preferences for new team members",
        href: "/settings/notifications/tenant-defaults",
        // PLP-FIX-7: Tenant notification defaults gated on settings.tenant.write
        permission: "settings.tenant.write",
      },
      {
        label: "Branding",
        icon: SwatchIcon,
        description: "Email branding, SMS compliance, and 10DLC registration",
        href: "/settings/communications",
        // PLP-FIX-7: Branding gated on settings.tenant.write
        permission: "settings.tenant.write",
      },
      {
        label: "Website",
        icon: GlobeAltIcon,
        description:
          "Your public business website — required for SMS (10DLC) compliance",
        href: "/settings/website",
        permission: "settings.manage",
      },
      {
        label: "Voice & AI",
        icon: MicrophoneIcon,
        description: "Voice capture settings and AI transcription preferences",
        href: "/settings/voice-ai",
        // PLP-FIX-7: Voice & AI gated on settings.tenant.write
        permission: "settings.tenant.write",
      },
    ],
  },
  {
    title: "Integrations & System",
    cards: [
      {
        label: "Integrations",
        icon: ArrowsRightLeftIcon,
        description: "Connect QuickBooks, calendar, and third-party apps",
        href: "/settings/integrations",
        permission: "integrations.manage",
      },
      {
        label: "Sync & Storage",
        icon: CloudArrowUpIcon,
        description:
          "Background sync, offline data limits, photos, and voice file storage",
        href: "/settings/sync-storage",
        permission: "settings.tenant.write",
      },
      {
        label: "Data & Privacy",
        icon: LockClosedIcon,
        description: "Data export, retention policies, and privacy settings",
        href: "/settings/data-privacy",
      },
    ],
  },
];

function SettingsCardItem({ card }: { card: SettingsCard }) {
  const Icon = card.icon;
  const content = (
    <Link
      href={card.href}
      className="group block bg-white border border-neutral-200 rounded-lg p-5 shadow-sm hover:shadow-md hover:border-brand-200 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      <div className="flex items-center gap-3">
        <Icon className="w-5 h-5 text-brand-500 shrink-0" aria-hidden="true" />
        <span className="text-sm font-semibold text-brand-600 group-hover:text-brand-700">
          {card.label}
        </span>
      </div>
      <p className="mt-2 text-sm text-neutral-500 leading-relaxed">
        {card.description}
      </p>
    </Link>
  );

  if (card.permission) {
    return <RoleGate permission={card.permission}>{content}</RoleGate>;
  }
  return content;
}

export function SettingsIndexPage() {
  return (
    <div className="bg-neutral-50 flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-neutral-900">Settings</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manage your account, workspace, and integrations
          </p>
        </div>

        {/* Sections */}
        {SETTINGS_SECTIONS.map((section) => {
          const sectionContent = (
            <div key={section.title} className="mt-8 first:mt-0">
              <div className="pb-2 mb-6 border-b border-neutral-200">
                <h2 className="text-lg font-semibold text-neutral-900">
                  {section.title}
                </h2>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-10 lg:grid-cols-2 md:grid-cols-1">
                {section.cards.map((card) => (
                  <SettingsCardItem key={card.href} card={card} />
                ))}
              </div>
            </div>
          );

          if (section.permission) {
            return (
              <RoleGate key={section.title} permission={section.permission}>
                {sectionContent}
              </RoleGate>
            );
          }
          return sectionContent;
        })}
      </div>
    </div>
  );
}
