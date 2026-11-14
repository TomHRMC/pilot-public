/**
 * QuoteDetailPage — unified owner/tech quote detail view
 *
 * Location: apps/web/src/features/quote-approval/QuoteDetailPage.tsx
 *
 * Route: /quotes/[id]
 * Role-gated components:
 *   - QuoteReviewModeBar — owner only, when status === pending_approval
 *   - QuoteApprovalActionBar — owner only
 *   - QuoteActionBar (FE-B19) — draft status actions (send, submit, convert)
 *   - Changes tab — visible when quote.has_owner_edits
 */

"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@pilot/ui/auth";
import { RoleGate, useHasPermission } from "@pilot/ui";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { useQuoteDetail } from "./hooks/useQuoteDetail";
import { useApproveWithEdits } from "@pilot/ui/hooks";
import { QuoteStatusPill } from "./components/QuoteStatusPill";
import { QuoteReviewModeBar } from "./components/QuoteReviewModeBar";
import { QuoteApprovalActionBar } from "./components/QuoteApprovalActionBar";
import { QuoteLineItemTable } from "./components/QuoteLineItemTable";
import { MarginDeltaDisplay } from "./components/MarginDeltaDisplay";
import { QuoteActivityTab } from "./components/QuoteActivityTab";
import { QuoteChangesTab } from "./components/QuoteChangesTab";
// FE-B19: quote builder action bar + line item editor for draft mode
import { QuoteActionBar } from "../quotes/components/QuoteActionBar";
import { LineItemEditor } from "../quotes/components/LineItemEditor";
// FE-B24: quote metadata edit modal for draft quotes
import { QuoteMetadataEditModal } from "../quotes/components/QuoteMetadataEditModal";
// FE-B26: create job from accepted quote
import { JobFormModal } from "../jobs/components/JobFormModal";

interface QuoteDetailPageProps {
  quoteId: string;
}

type TabId = "details" | "changes" | "activity";

export function QuoteDetailPage({ quoteId }: QuoteDetailPageProps) {
  const { role } = useAuth();
  // PLP-FIX-9 (INV-BUG-9): gate LineItemEditor on quotes.update permission
  const canUpdateQuote = useHasPermission("quotes.update");
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabId>("details");
  const [editMetaOpen, setEditMetaOpen] = useState(false);
  const [createJobOpen, setCreateJobOpen] = useState(false);

  const { data: quote, isLoading, isError, error } = useQuoteDetail(quoteId);

  const isOwner = role === "owner";
  const isPendingApproval = quote?.status === "pending_approval";
  const isDraft = quote?.status === "draft";
  // 'accepted' status: customer accepted via public link — eligible for convert-to-job
  const isAccepted = quote?.status === "accepted";
  // UI-FIX-1B: approved status — owner can send to customer from detail page
  const isApproved = quote?.status === "approved";
  const showReviewMode = isOwner && isPendingApproval;

  const {
    pendingEdits,
    hasPendingEdits,
    approveWithEdits,
    approveAsIs,
    cancelAllEdits,
    revertPendingEdit,
    isApproving,
    StalenessDialog,
  } = useApproveWithEdits({
    quoteId,
    quoteVersionId: quote?.quote_version_id ?? "",
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <LoadingState type="inline" label="Loading quote..." />
      </div>
    );
  }

  if (isError || !quote) {
    return (
      <main className="p-6">
        <ErrorState
          type="network"
          title="Failed to load quote"
          description={error instanceof Error ? error.message : "Unknown error"}
          onRetry={() => window.location.reload()}
        />
      </main>
    );
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: "details", label: "Details" },
    ...(quote.has_owner_edits
      ? [{ id: "changes" as TabId, label: "Changes" }]
      : []),
    { id: "activity", label: "Activity" },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      {/* Review mode bar — shown to owner when pending approval */}
      {showReviewMode && (
        <QuoteReviewModeBar
          pendingEditCount={pendingEdits.length}
          onCancelAllEdits={cancelAllEdits}
          currentMarginPercent={quote.margin_percent}
          testID="quote-review-mode-bar"
        />
      )}

      <main className="flex flex-col gap-6 p-6 max-w-4xl mx-auto w-full pb-24">
        {/* Header */}
        {/* FE-B24: QuoteMetadataEditModal — draft quotes only */}
        {isDraft && (
          <QuoteMetadataEditModal
            quoteId={quoteId}
            currentExpiresAt={null}
            currentCurrency="USD"
            open={editMetaOpen}
            onClose={() => setEditMetaOpen(false)}
          />
        )}
        {/* FE-B26: Create Job modal — accepted quotes only */}
        <JobFormModal
          open={createJobOpen}
          onClose={() => setCreateJobOpen(false)}
          prefilledQuoteId={quoteId}
          onSuccess={() => {
            setCreateJobOpen(false);
            router.push("/jobs");
          }}
        />

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-h1 font-medium text-neutral-900">
                Quote #{quote.quote_number}
              </h1>
              <QuoteStatusPill status={quote.status} />
            </div>
            <p className="text-body text-neutral-600">
              {quote.customer_name} · Submitted by {quote.submitted_by_name}
            </p>
            {/* FE-B24: Edit metadata link — draft quotes only */}
            {isDraft && isOwner && (
              <button
                type="button"
                onClick={() => setEditMetaOpen(true)}
                className="mt-1 text-sm text-brand-600 hover:text-brand-800 underline"
                data-testid="quote-edit-metadata-btn"
              >
                Edit quote details
              </button>
            )}
            {/* FE-B26: Create Job from accepted quote — owner only */}
            {isAccepted && isOwner && (
              <RoleGate permission="jobs.create">
                <button
                  type="button"
                  onClick={() => setCreateJobOpen(true)}
                  className="mt-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
                  data-testid="create-job-from-quote-btn"
                >
                  Create Job from Quote
                </button>
              </RoleGate>
            )}
          </div>

          {isOwner && (
            <MarginDeltaDisplay
              currentMarginPercent={quote.margin_percent}
              testID="quote-margin-display"
            />
          )}
        </div>

        {/* Tabs */}
        <nav
          className="flex border-b border-neutral-200"
          role="tablist"
          aria-label="Quote detail tabs"
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`tab-panel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-body font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-neutral-600 hover:text-neutral-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab panels */}
        <div
          id="tab-panel-details"
          role="tabpanel"
          aria-labelledby="tab-details"
          hidden={activeTab !== "details"}
        >
          {/* Draft mode: show inline line item editor (add-only — no DELETE/PATCH endpoint) */}
          {isDraft ? (
            <div className="space-y-4">
              <LineItemEditor
                quoteId={quoteId}
                persistedLines={quote.line_items.map((li) => ({
                  id: li.id,
                  description: li.description,
                  quantity: li.quantity,
                  unit_price_cents: li.unit_price_cents,
                  qco_line_type_id: undefined,
                }))}
                readOnly={!canUpdateQuote}
              />
            </div>
          ) : (
            <QuoteLineItemTable
              lineItems={quote.line_items}
              pendingEdits={showReviewMode ? pendingEdits : []}
              isReviewMode={showReviewMode}
              onRevertField={showReviewMode ? revertPendingEdit : undefined}
            />
          )}
        </div>

        {quote.has_owner_edits && (
          <div
            id="tab-panel-changes"
            role="tabpanel"
            aria-labelledby="tab-changes"
            hidden={activeTab !== "changes"}
          >
            <QuoteChangesTab quoteId={quoteId} />
          </div>
        )}

        <div
          id="tab-panel-activity"
          role="tabpanel"
          aria-labelledby="tab-activity"
          hidden={activeTab !== "activity"}
        >
          <QuoteActivityTab quoteId={quoteId} />
        </div>
      </main>

      {/* Approval action bar — owner only, pending_approval status */}
      {isOwner && isPendingApproval && quote.require_approval && (
        <QuoteApprovalActionBar
          quoteId={quoteId}
          pendingEditCount={hasPendingEdits ? pendingEdits.length : 0}
          requireApproval={quote.require_approval}
          isApproving={isApproving}
          lineItems={quote.line_items}
          onApprove={approveAsIs}
          onApproveWithEdits={approveWithEdits}
          testID="quote-approval-action-bar"
        />
      )}

      {/* FE-B19 + UI-FIX-1B: Draft + Approved + Accepted action bar */}
      {(isDraft || isApproved || isAccepted) && (
        <QuoteActionBar
          quoteId={quoteId}
          status={quote.status ?? "draft"}
          customerAcceptedAt={isAccepted ? "accepted" : null}
          customerEmail={null}
          customerName={quote.customer_name ?? "Customer"}
          quoteVersionId={quote.quote_version_id ?? ""}
          testID="quote-action-bar"
        />
      )}

      {/* Staleness dialog — renders only when 409 occurs */}
      <StalenessDialog />
    </div>
  );
}
