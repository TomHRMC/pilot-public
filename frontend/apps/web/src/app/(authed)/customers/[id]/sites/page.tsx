/**
 * Customer Sites Tab — /customers/[id]/sites
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/sites/page.tsx
 *
 * Created in FE-B18 — renders SiteListPanel for this customer.
 */

import { SiteListPanel } from "@/features/customers/components/SiteListPanel";

interface CustomerSitesPageProps {
  params: Promise<{ id: string }>;
}

export default async function CustomerSitesPage({
  params,
}: CustomerSitesPageProps) {
  const { id } = await params;
  return (
    <div className="p-6">
      <SiteListPanel customerId={id} />
    </div>
  );
}
