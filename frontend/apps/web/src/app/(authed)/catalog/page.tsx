/**
 * /catalog — Pricebook Items (default catalog tab)
 *
 * Location: apps/web/src/app/(authed)/catalog/page.tsx
 * Thin server component — delegates to PricebookItemsPage client component.
 */

import { PricebookItemsPage } from "@/features/catalog/components/PricebookItemsPage";

export const metadata = { title: "Catalog | Pilot" };

export default function CatalogPage() {
  return <PricebookItemsPage />;
}
