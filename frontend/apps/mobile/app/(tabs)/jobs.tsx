/**
 * /jobs tab — Assigned jobs list
 *
 * Location: apps/mobile/app/(tabs)/jobs.tsx
 *
 * MOB-B1: Replaced 10-line stub with JobsTabScreen.
 * Shows today's assigned jobs, upcoming (7-day), and My Quotes entry.
 */

import { JobsTabScreen } from "@/features/jobs/components/JobsTabScreen";

export default function JobsTab() {
  return <JobsTabScreen />;
}
