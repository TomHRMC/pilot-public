/**
 * Unrouted Message Queue Page — /settings/integrations/sms/unrouted
 *
 * Location: apps/web/src/app/(authed)/settings/integrations/sms/unrouted/page.tsx
 *
 * RULE 6: RoleGate — integrations.manage (owner/accountant) only.
 * Tech role cannot see this surface.
 *
 * Design doc Decision 6, Section A.2.3, A.4
 */

import React from "react";
import { UnroutedMessageQueue } from "@/features/sms-unrouted/components/UnroutedMessageQueue";

export default function UnroutedMessageQueuePage() {
  return (
    <div className="px-6 py-4 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-h2 font-medium text-neutral-900">
          Unrouted Messages
        </h1>
        <p className="text-body text-neutral-600 mt-1">
          These messages arrived from phone numbers not yet linked to a customer
          conversation. Assign each to a customer and technician to create a
          thread.
        </p>
      </div>

      {/* RULE 6: This page is owner-only. RoleGate enforced at route level. */}
      <UnroutedMessageQueue testID="unrouted-message-queue" />
    </div>
  );
}

export const metadata = {
  title: "Unrouted SMS Messages",
};
