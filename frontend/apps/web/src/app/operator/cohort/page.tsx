/**
 * Cohort Dashboard route — /operator/cohort
 *
 * Location: apps/web/src/app/operator/cohort/page.tsx
 *
 * C-B11 Part B: Thin server component — no "use client", no data fetching.
 * All logic lives in the CohortDashboardClient feature component.
 *
 * This route is NOT under (authed)/ — it is a platform-level route with its
 * own minimal layout (no tenant shell, no nav sidebar). Auth gating is handled
 * by RequireAuth inside CohortDashboardClient.
 */

import { CohortDashboardClient } from "@/components/operator/cohort/CohortDashboardClient";

export default function CohortDashboardPage() {
  return <CohortDashboardClient />;
}
