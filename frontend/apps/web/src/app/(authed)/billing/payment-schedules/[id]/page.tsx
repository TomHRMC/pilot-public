/**
 * Route: /billing/payment-schedules/[id]
 *
 * Location: apps/web/src/app/(authed)/billing/payment-schedules/[id]/page.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §1.3).
 *
 * Thin server component (Rule 9): no "use client", no data fetching.
 * Passes the scheduleId to the builder, which fetches + renders State B/C/D.
 */

import { PaymentScheduleBuilder } from "@/features/billing/components/PaymentScheduleBuilder";

interface PaymentScheduleDetailPageProps {
  params: { id: string };
}

export default function PaymentScheduleDetailPage({
  params,
}: PaymentScheduleDetailPageProps) {
  return <PaymentScheduleBuilder scheduleId={params.id} />;
}
