/**
 * CustomerDetailHeader — client component for customer name in layout header
 *
 * Location: apps/web/src/features/customers/components/CustomerDetailHeader.tsx
 *
 * The customers/[id]/layout.tsx is a server component; it passes customerId to
 * this client component which fetches and displays the customer name.
 */

"use client";

import { useCustomer } from "../hooks/useCustomer";

interface CustomerDetailHeaderProps {
  customerId: string;
}

export function CustomerDetailHeader({
  customerId,
}: CustomerDetailHeaderProps) {
  const { data: customer, isLoading } = useCustomer(customerId);

  if (isLoading) {
    return <span className="text-neutral-400 animate-pulse">Loading...</span>;
  }

  return <span>{customer?.display_name ?? "Customer"}</span>;
}
