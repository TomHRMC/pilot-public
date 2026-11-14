/**
 * SettingsBreadcrumb — feature-local breadcrumb for Settings sub-pages
 *
 * Location: apps/web/src/features/settings/components/SettingsBreadcrumb.tsx
 *
 * PLP-FIX-5 (Issue 8): extended to accept an explicit `trail` prop for the
 * billing/payment-method pages. When `trail` is omitted, the breadcrumb
 * auto-derives from `usePathname()` (the original FE-UI-NAV-S1 behavior —
 * preserves backward compatibility with settings/layout.tsx, profile, and
 * security pages that call `<SettingsBreadcrumb />` with no props).
 *
 * Non-last trail items render as Links (brand-600, hover:underline); the last
 * item is plain neutral-500 text; separators are " / ".
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

interface SettingsBreadcrumbProps {
  /** Ordered trail; last item is the current page (no href).
   *  When omitted, auto-derives from the current pathname. */
  trail?: { label: string; href?: string }[];
}

/** Map of known settings sub-route segments to human-readable labels. */
const SEGMENT_LABELS: Record<string, string> = {
  billing: "Billing & Subscription",
  "payment-method": "Payment Method",
  "my-account": "My Account",
  profile: "Profile",
  security: "Security",
  integrations: "Integrations",
  team: "Team",
  notifications: "Notifications",
};

/** Auto-derive a breadcrumb trail from the current pathname. */
function deriveTrailFromPathname(pathname: string): {
  label: string;
  href?: string;
}[] {
  // Always start with Settings → /settings
  const trail: { label: string; href?: string }[] = [
    { label: "Settings", href: "/settings" },
  ];
  // Split into segments, skip the leading "settings" (already the root)
  const segments = pathname.split("/").filter(Boolean);
  const subSegments = segments.slice(1); // drop "settings"
  if (subSegments.length === 0) {
    // We're on /settings itself — no second crumb
    return [{ label: "Settings" }];
  }
  const label =
    SEGMENT_LABELS[subSegments.join("/")] ??
    SEGMENT_LABELS[subSegments[0]] ??
    subSegments[0].replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  trail.push({ label });
  return trail;
}

export function SettingsBreadcrumb({ trail }: SettingsBreadcrumbProps) {
  const pathname = usePathname();
  const effectiveTrail = trail ?? deriveTrailFromPathname(pathname);

  return (
    <nav aria-label="Breadcrumb" className="text-sm text-neutral-500 mb-2">
      {effectiveTrail.map((item, idx) => {
        const isLast = idx === effectiveTrail.length - 1;
        return (
          <span key={idx}>
            {isLast || !item.href ? (
              <span className="text-neutral-500">{item.label}</span>
            ) : (
              <Link href={item.href} className="text-brand-600 hover:underline">
                {item.label}
              </Link>
            )}
            {!isLast && <span aria-hidden="true"> / </span>}
          </span>
        );
      })}
    </nav>
  );
}
