/**
 * QbConflictQueuePage — /settings/integrations/quickbooks/conflicts
 *
 * Location: apps/web/src/app/(authed)/settings/integrations/quickbooks/conflicts/page.tsx
 *
 * Established FE-B9. Fourth tab on QB integration settings (alongside Connection/Mapping/Sync log).
 * Auth: required. Role gate: operator (integrations.manage maps to operator in PilotRole).
 *
 * NOTE: InFlightSyncIndicator surface="quickbooks" is rendered INSIDE QbConflictQueue (RULE I.1).
 * This follows design doc §I.1 — surface="quickbooks" locked for FE-B15 consumption.
 */

import React from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import { QbConflictQueue } from "@/features/quickbooks-conflict/components/QbConflictQueue";

export const metadata = {
  title: "QuickBooks Conflicts | Pilot",
  description: "Review and resolve QuickBooks sync conflicts",
};

export default function QbConflictQueuePage() {
  return (
    <RoleGate role={["owner", "accountant"]}>
      <div className="bg-neutral-50 min-h-screen px-4 py-6 sm:px-6 lg:px-8">
        <QbConflictQueue testID="qb-conflict-queue-page" />
      </div>
    </RoleGate>
  );
}
