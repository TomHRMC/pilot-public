/**
 * Customer Quotes Tab — /customers/[id]/quotes
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/quotes/page.tsx
 *
 * Updated in FE-B18: replaces "coming soon" with CustomerQuotesList.
 * GET /api/v1/quotes/ does not support ?customer_id= filter — deferred to FE-B19.
 */

import { CustomerQuotesList } from "@/features/customers/components/CustomerQuotesList";

interface CustomerQuotesPageProps {
  params: Promise<{ id: string }>;
}

export default async function CustomerQuotesPage({
  params,
}: CustomerQuotesPageProps) {
  const { id } = await params;
  return <CustomerQuotesList customerId={id} />;
}
