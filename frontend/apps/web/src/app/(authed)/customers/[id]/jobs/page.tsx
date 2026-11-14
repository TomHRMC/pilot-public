/**
 * Customer Jobs Tab — /customers/[id]/jobs
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/jobs/page.tsx
 *
 * Updated in FE-B18: replaces "coming soon" with CustomerJobsList.
 * GET /api/v1/jobs/ does not support ?customer_id= filter — deferred to FE-B21.
 */

import { CustomerJobsList } from "@/features/customers/components/CustomerJobsList";

interface CustomerJobsPageProps {
  params: Promise<{ id: string }>;
}

export default async function CustomerJobsPage({
  params,
}: CustomerJobsPageProps) {
  const { id } = await params;
  return <CustomerJobsList customerId={id} />;
}
