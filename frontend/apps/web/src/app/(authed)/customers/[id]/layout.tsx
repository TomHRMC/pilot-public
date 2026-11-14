/**
 * Customer Detail Layout — /customers/[id]/*
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/layout.tsx
 *
 * Renders the shared shell (breadcrumb + tab bar) for all customer
 * sub-routes: overview | sites | jobs | quotes | comms | invoices.
 *
 * Updated in FE-B18:
 * - "Sites" tab added between Overview and Jobs.
 * - Hardcoded "Customer" heading replaced with CustomerDetailHeader client component.
 */

import Link from "next/link";
import { CustomerDetailHeader } from "@/features/customers/components/CustomerDetailHeader";
import { CustomerDetailTabs } from "./_components/CustomerDetailTabs";

export default async function CustomerDetailLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <main className="flex min-h-screen flex-col">
      {/* Page header */}
      <div className="border-b border-neutral-200 bg-white px-6 py-4">
        <div className="flex items-center gap-2 text-caption text-neutral-400">
          <Link href="/customers" className="hover:text-neutral-600">
            Customers
          </Link>
          <span>/</span>
          <span className="text-neutral-600">
            <CustomerDetailHeader customerId={id} />
          </span>
        </div>
        <h1 className="mt-1 text-h1 font-medium text-neutral-900">
          <CustomerDetailHeader customerId={id} />
        </h1>
      </div>

      {/* Tab bar — client component for active state highlighting */}
      <CustomerDetailTabs customerId={id} />

      {/* Tab content */}
      <div className="flex-1">{children}</div>
    </main>
  );
}
