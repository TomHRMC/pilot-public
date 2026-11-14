/**
 * Unrouted Message Assign Page — /settings/integrations/sms/unrouted/[id]
 *
 * Location: apps/web/src/app/(authed)/settings/integrations/sms/unrouted/[id]/page.tsx
 *
 * RULE 6: RoleGate — integrations.manage (owner/accountant) only.
 *
 * Design doc Decision 6, Section A.2.3, A.4
 */

import React from "react";
import Link from "next/link";
import { UnroutedMessageAssignForm } from "@/features/sms-unrouted/components/UnroutedMessageAssignForm";
import { UNROUTED_MESSAGES } from "@/features/customer-comms/mocks/customerCommsFixtures";

interface UnroutedAssignPageProps {
  params: Promise<{ id: string }>;
}

export default async function UnroutedMessageAssignPage({
  params,
}: UnroutedAssignPageProps) {
  const { id } = await params;

  // In production, this would fetch from server. For MVP, use the fixture
  // to match the MSW pattern. The actual data is provided by the API.
  // This Server Component shells the form Client Component.
  const message = UNROUTED_MESSAGES.find((m) => m.unrouted_id === id);

  if (!message) {
    return (
      <div className="px-6 py-4 max-w-lg mx-auto">
        <div className="text-body text-fault-600 text-center py-12">
          Unrouted message not found. It may have already been assigned.
        </div>
        <div className="text-center mt-4">
          <Link
            href="/settings/integrations/sms/unrouted"
            className="text-brand-600 hover:text-brand-800"
          >
            ← Back to unrouted queue
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-4 max-w-lg mx-auto">
      <div className="mb-6">
        <Link
          href="/settings/integrations/sms/unrouted"
          className="text-caption text-neutral-600 hover:text-neutral-900 flex items-center gap-1 mb-4"
        >
          ← Back to unrouted queue
        </Link>
        <h1 className="text-h2 font-medium text-neutral-900">
          Assign Message to Customer
        </h1>
        <p className="text-body text-neutral-600 mt-1">
          Link this message to an existing customer and assign a technician to
          manage the conversation.
        </p>
      </div>

      {/* RULE 6: This page is owner-only. RoleGate enforced at route level. */}
      <UnroutedMessageAssignForm message={message} testID="assign-form" />
    </div>
  );
}

export const metadata = {
  title: "Assign Unrouted Message",
};
