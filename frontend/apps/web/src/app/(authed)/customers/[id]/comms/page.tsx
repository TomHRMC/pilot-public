/**
 * Customer Comms Page — /customers/[id]/comms
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/comms/page.tsx
 * Route: /customers/[id]/comms
 *
 * Owner sees all threads for this customer.
 * Tech sees only their own threads.
 *
 * RoleGate: owner / tech
 *
 * Design doc Section A.4, Decision 5a
 */

import React from "react";
import { CustomerCommsHistoryView } from "@/features/customer-comms/components/CustomerCommsHistoryView";

interface CustomerCommsPageProps {
  params: Promise<{ id: string }>;
}

export default async function CustomerCommsPage({
  params,
}: CustomerCommsPageProps) {
  const { id: customerId } = await params;
  return (
    <div className="p-6">
      <CustomerCommsHistoryView
        customerId={customerId}
        testID="customer-comms-history-view"
      />
    </div>
  );
}

export const metadata = {
  title: "Customer Communications",
};
