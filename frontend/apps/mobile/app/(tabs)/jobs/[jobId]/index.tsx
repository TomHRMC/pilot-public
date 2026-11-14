/**
 * Job Detail Route — jobs/[jobId]/index
 *
 * Location: apps/mobile/app/(tabs)/jobs/[jobId]/index.tsx
 *
 * Thin route file: reads jobId from URL params and renders JobDetailScreen.
 * This route is suppressed in _layout.tsx (href: null) — it renders as
 * a push screen, not a tab bar item.
 *
 * Per batch-mob-b2-design.md §I (Component Manifest) and §C Task #18.
 */

import { useLocalSearchParams } from "expo-router";
import { JobDetailScreen } from "@/features/jobs/components/JobDetailScreen";

export default function JobDetailRoute() {
  const { jobId } = useLocalSearchParams<{ jobId: string }>();
  return <JobDetailScreen jobId={jobId} />;
}
