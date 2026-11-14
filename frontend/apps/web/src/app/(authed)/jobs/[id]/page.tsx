/**
 * Job detail route — /jobs/[id]
 *
 * Location: apps/web/src/app/(authed)/jobs/[id]/page.tsx
 *
 * Thin server component. Awaits params, passes jobId to JobDetailPage.
 */

import { JobDetailPage } from "@/features/jobs/components/JobDetailPage";

export const metadata = { title: "Job Detail | Pilot" };

interface Props {
  params: Promise<{ id: string }>;
}

export default async function JobDetailRoute({ params }: Props) {
  const { id } = await params;
  return <JobDetailPage jobId={id} />;
}
