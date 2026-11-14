/**
 * /catalog/supplier-items — Supplier Items (read-only)
 *
 * Location: apps/web/src/app/(authed)/catalog/supplier-items/page.tsx
 * Thin server component — delegates to SupplierItemsPage client component.
 */

import { SupplierItemsPage } from "@/features/catalog/components/SupplierItemsPage";

export const metadata = { title: "Supplier Items | Catalog | Pilot" };

export default function SupplierItemsRoute() {
  return <SupplierItemsPage />;
}
