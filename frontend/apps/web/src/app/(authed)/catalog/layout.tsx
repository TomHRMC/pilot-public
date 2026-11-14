/**
 * Catalog Layout — /catalog/*
 *
 * Location: apps/web/src/app/(authed)/catalog/layout.tsx
 *
 * Renders the shared tab bar for all catalog sub-routes:
 *   /catalog            → Pricebook Items
 *   /catalog/labor-rates → Labor Rate Versions
 *   /catalog/markups    → Markup % Configuration
 *   /catalog/supplier-items → Supplier Items (read-only)
 *
 * Mirrors the pattern from customers/[id]/layout.tsx (FE-B18).
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { label: "Pricebook", href: "/catalog" },
  { label: "Labor Rates", href: "/catalog/labor-rates" },
  { label: "Markups", href: "/catalog/markups" },
  { label: "Supplier Items", href: "/catalog/supplier-items" },
] as const;

export default function CatalogLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <main className="flex min-h-screen flex-col">
      {/* Page header */}
      <div className="border-b border-neutral-200 bg-white px-6 py-4">
        <h1 className="text-h1 font-medium text-neutral-900">Catalog</h1>
      </div>

      {/* Tab bar */}
      <nav
        className="flex border-b border-neutral-200 bg-white px-6"
        aria-label="Catalog tabs"
      >
        {TABS.map((tab) => {
          // Exact match for /catalog, prefix match for sub-routes
          const isActive =
            tab.href === "/catalog"
              ? pathname === "/catalog"
              : pathname.startsWith(tab.href);

          return (
            <Link
              key={tab.label}
              href={tab.href}
              className={`relative mr-6 py-3 text-body font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
                isActive
                  ? "text-brand-700 border-b-2 border-brand-600"
                  : "text-neutral-600 hover:text-neutral-900"
              }`}
              aria-current={isActive ? "page" : undefined}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {/* Tab content */}
      <div className="flex-1">{children}</div>
    </main>
  );
}
