/**
 * Job edit route — /jobs/[id]/edit
 *
 * Location: apps/web/src/app/(authed)/jobs/[id]/edit/page.tsx
 *
 * JOB-UI-B1: Thin server component. Awaits params, passes jobId to JobEditPage.
 */

import { JobEditPage } from "@/features/jobs/components/JobEditPage";

export const metadata = { title: "Edit Job | Pilot" };

interface Props {
  params: Promise<{ id: string }>;
}

export default async function JobEditRoute({ params }: Props) {
  const { id } = await params;
  return <JobEditPage jobId={id} />;
}
