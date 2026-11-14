/**
 * Invoice Sign-Off Capture Route — jobs/[jobId]/invoice-signoff
 *
 * Location: apps/mobile/app/(tabs)/jobs/[jobId]/invoice-signoff.tsx
 *
 * Thin route file: reads jobId + invoiceId from URL params and renders
 * InvoiceSignoffCaptureScreen. This route is suppressed in _layout.tsx
 * (href: null) — it renders as a push screen, not a tab bar item.
 *
 * Per batch-ce-1-mobile-ui-design-spec.md §1 (S2 route) and §8.5.
 */

import { useLocalSearchParams } from "expo-router";
import { InvoiceSignoffCaptureScreen } from "@/features/jobs/components/detail/InvoiceSignoffCaptureScreen";

export default function InvoiceSignoffRoute() {
  const { jobId, invoiceId } = useLocalSearchParams<{
    jobId: string;
    invoiceId: string;
  }>();
  return <InvoiceSignoffCaptureScreen jobId={jobId} invoiceId={invoiceId} />;
}
