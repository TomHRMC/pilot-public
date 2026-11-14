/**
 * Invoice Detail Route — /invoices/[id]
 *
 * Location: apps/web/src/app/(authed)/invoices/[id]/page.tsx
 *
 * Thin server component — all logic in InvoiceDetailPage ("use client").
 * FE-B22: resolves the 404 that existed before this batch.
 */

import { InvoiceDetailPage } from "@/features/invoices/components/InvoiceDetailPage";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function InvoiceDetailRoute({ params }: Props) {
  const { id } = await params;
  return <InvoiceDetailPage invoiceId={id} />;
}

export const metadata = { title: "Invoice | Pilot" };
