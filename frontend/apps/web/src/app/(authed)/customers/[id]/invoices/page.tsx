/**
 * Customer Invoices Tab — /customers/[id]/invoices
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/invoices/page.tsx
 *
 * Updated in FE-B18: replaces "coming soon" with CustomerInvoicesList.
 * GET /api/v1/invoices/ does not support ?customer_id= filter — deferred to FE-B22.
 */

import { CustomerInvoicesList } from "@/features/customers/components/CustomerInvoicesList";

interface CustomerInvoicesPageProps {
  params: Promise<{ id: string }>;
}

export default async function CustomerInvoicesPage({
  params,
}: CustomerInvoicesPageProps) {
  const { id } = await params;
  return <CustomerInvoicesList customerId={id} />;
}
