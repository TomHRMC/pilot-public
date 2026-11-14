/**
 * QbConflictDetailPage — /settings/integrations/quickbooks/conflicts/[id]
 *
 * Location: apps/web/src/app/(authed)/settings/integrations/quickbooks/conflicts/[id]/page.tsx
 *
 * Established FE-B9. Auth: required. Role gate: owner / operator.
 * Redirect 404 if not authorized (handled by QbConflictDetail error state).
 *
 * RULE 3: No VoiceConfirmTurn — QB voice is read-only.
 * Voice deep-link ?reason=voice_qb_blocked → NotificationBanner only (in QbConflictDetail).
 */

import React from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import { QbConflictDetail } from "@/features/quickbooks-conflict/components/QbConflictDetail";

interface QbConflictDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function QbConflictDetailPage({
  params,
}: QbConflictDetailPageProps) {
  const { id } = await params;

  return (
    <RoleGate role={["owner", "accountant"]}>
      <QbConflictDetail conflictId={id} testID="qb-conflict-detail-page" />
    </RoleGate>
  );
}
