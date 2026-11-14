/**
 * Route: /billing/payment-schedules/new
 *
 * Location: apps/web/src/app/(authed)/billing/payment-schedules/new/page.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §1.3).
 *
 * Thin server component (Rule 9): no "use client", no data fetching.
 * Reads ?quote_id= / ?job_id= query params and passes them to the builder.
 * The builder handles State A (empty) → create flow.
 */

import { PaymentScheduleBuilder } from "@/features/billing/components/PaymentScheduleBuilder";

interface NewPaymentSchedulePageProps {
  searchParams: {
    quote_id?: string;
    job_id?: string;
    customer_id?: string;
    site_id?: string;
    contract_total_cents?: string;
    customer_name?: string;
    site_label?: string;
  };
}

export default function NewPaymentSchedulePage({
  searchParams,
}: NewPaymentSchedulePageProps) {
  const contractTotalCents = searchParams.contract_total_cents
    ? parseInt(searchParams.contract_total_cents, 10)
    : undefined;

  return (
    <PaymentScheduleBuilder
      mode="new"
      quoteId={searchParams.quote_id}
      jobId={searchParams.job_id}
      customerId={searchParams.customer_id}
      siteId={searchParams.site_id}
      contractTotalCents={
        Number.isNaN(contractTotalCents) ? undefined : contractTotalCents
      }
      customerName={searchParams.customer_name}
      siteLabel={searchParams.site_label}
    />
  );
}
