/**
 * /catalog/markups — Markup % Configuration
 *
 * Location: apps/web/src/app/(authed)/catalog/markups/page.tsx
 * Thin server component — delegates to MarkupsPage client component.
 */

import { MarkupsPage } from "@/features/catalog/components/MarkupsPage";

export const metadata = { title: "Markups | Catalog | Pilot" };

export default function MarkupsRoute() {
  return <MarkupsPage />;
}
