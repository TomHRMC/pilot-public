/**
 * Customer Overview Tab — /customers/[id]
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/page.tsx
 *
 * Overview tab content. Shell (breadcrumb + tab bar) is in layout.tsx.
 * Updated in FE-B18: replaces "coming soon" placeholder with CustomerOverviewTab.
 */

import { CustomerOverviewTab } from "@/features/customers/components/CustomerOverviewTab";

interface CustomerOverviewPageProps {
  params: Promise<{ id: string }>;
}

export default async function CustomerOverviewPage({
  params,
}: CustomerOverviewPageProps) {
  const { id } = await params;
  return <CustomerOverviewTab customerId={id} />;
}
