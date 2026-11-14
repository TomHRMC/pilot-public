/**
 * CalendarConflictDetailPage — route page for single conflict resolution
 *
 * Route: /settings/integrations/calendar/conflicts/[id]
 * Auth: Required (via (authed) layout)
 * Role Gate: owner/operator (integrations.manage maps to these roles)
 *
 * Pattern ref: design doc batch-fe-b8-design.md §A.4
 */

import React from "react";
import { RoleGate } from "@pilot/ui";
import { CalendarConflictDetail } from "@/features/calendar-conflict/components/CalendarConflictDetail";

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ reason?: string }>;
}

export default async function CalendarConflictDetailPage({
  params,
  searchParams,
}: PageProps) {
  const { id } = await params;
  const { reason } = await searchParams;
  return (
    <RoleGate role={["owner", "accountant"]}>
      <main className="mx-auto max-w-3xl space-y-6 p-6">
        <CalendarConflictDetail conflictId={id} reason={reason ?? null} />
      </main>
    </RoleGate>
  );
}
