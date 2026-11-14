import { WipReportPage } from "@/features/wip/components/WipReportPage";

/**
 * /reports/wip — Thin server component route (Rule 9)
 *
 * Location: apps/web/src/app/(authed)/reports/wip/page.tsx
 *
 * No "use client", no data fetching, no logic.
 * All client-side data fetching happens inside WipReportPage via apiClient + TanStack Query.
 */
export default function Page() {
  return <WipReportPage />;
}
