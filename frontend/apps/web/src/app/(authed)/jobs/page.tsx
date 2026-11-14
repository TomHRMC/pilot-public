/**
 * Jobs list route — /jobs
 *
 * Location: apps/web/src/app/(authed)/jobs/page.tsx
 *
 * Thin server component. All data fetching and UI in JobsPage.
 */

import { JobsPage } from "@/features/jobs/components/JobsPage";

export const metadata = { title: "Jobs | Pilot" };

export default function JobsRoute() {
  return <JobsPage />;
}
