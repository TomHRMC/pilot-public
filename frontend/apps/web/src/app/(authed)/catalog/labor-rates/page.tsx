/**
 * /catalog/labor-rates — Labor Rate Versions
 *
 * Location: apps/web/src/app/(authed)/catalog/labor-rates/page.tsx
 * Thin server component — delegates to LaborRatesPage client component.
 */

import { LaborRatesPage } from "@/features/catalog/components/LaborRatesPage";

export const metadata = { title: "Labor Rates | Catalog | Pilot" };

export default function LaborRatesRoute() {
  return <LaborRatesPage />;
}
