/**
 * PendingQuotesInboxPage — owner's pending quotes approval queue
 *
 * Location: apps/web/src/features/quote-approval/PendingQuotesInboxPage.tsx
 *
 * Route: /quotes/pending
 * Gate: owner role only
 */

"use client";

import React, { useState } from "react";
import { useAuth } from "@pilot/ui/auth";
import { EmptyState, LoadingState, ErrorState } from "@pilot/ui/states";
import {
  usePendingQuotes,
  type PendingQuoteFilters,
} from "./hooks/usePendingQuotes";
import { PendingQuoteCard } from "./components/PendingQuoteCard";
import { PendingInboxFilterBar } from "./components/PendingInboxFilterBar";

export function PendingQuotesInboxPage() {
  const { role } = useAuth();
  const [filters, setFilters] = useState<PendingQuoteFilters>({
    sortBy: "newest",
  });

  const { data, isLoading, isError, error } = usePendingQuotes(filters);

  if (role !== "owner") {
    return (
      <main className="flex min-h-screen flex-col p-6">
        <EmptyState
          type="permission-denied"
          title="Access Restricted"
          description="Only owners can access the approval inbox."
        />
      </main>
    );
  }

  return (
    <main className="flex flex-col gap-6 p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 font-medium text-neutral-900">
            Pending Approval
          </h1>
          {data && (
            <p className="text-body text-neutral-600 mt-1">
              {data.total} quote{data.total !== 1 ? "s" : ""} awaiting review
            </p>
          )}
        </div>
      </div>

      <PendingInboxFilterBar filters={filters} onFiltersChange={setFilters} />

      {isLoading && (
        <div className="py-8">
          <LoadingState
            type="inline"
            label="Loading pending quotes..."
            testID="pending-quotes-loading"
          />
        </div>
      )}

      {isError && (
        <ErrorState
          type="network"
          title="Failed to load pending quotes"
          description={error instanceof Error ? error.message : "Unknown error"}
          onRetry={() => window.location.reload()}
        />
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          type={filters.customerSearch ? "no-results" : "not-yet-set-up"}
          title={
            filters.customerSearch ? "No matching quotes" : "No pending quotes"
          }
          description={
            filters.customerSearch
              ? `No pending quotes match "${filters.customerSearch}". Try clearing your filters.`
              : "All caught up! Quotes submitted by your team will appear here when the approval workflow is active."
          }
          testID="pending-quotes-empty"
        />
      )}

      {data && data.items.length > 0 && (
        <div
          className="flex flex-col gap-3"
          role="list"
          aria-label="Pending quotes"
        >
          {data.items.map((quote) => (
            <PendingQuoteCard key={quote.id} quote={quote} />
          ))}
        </div>
      )}
    </main>
  );
}
