/**
 * /jobs/recurring — Recurring Jobs route
 *
 * Location: apps/web/src/app/(authed)/jobs/recurring/page.tsx
 *
 * FE-B31: Thin server component — no "use client", no data fetching.
 * All logic lives in RecurringJobsPage feature component.
 */

import { RecurringJobsPage } from "@/features/jobs/components/RecurringJobsPage";

export default function RecurringJobsRoute() {
  return <RecurringJobsPage />;
}
