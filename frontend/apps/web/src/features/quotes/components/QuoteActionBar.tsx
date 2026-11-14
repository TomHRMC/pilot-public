/**
 * QuoteActionBar — context-aware action bar for quote detail page
 *
 * Location: apps/web/src/features/quotes/components/QuoteActionBar.tsx
 *
 * Shows different buttons based on quote status and user role (RBAC via RoleGate).
 *
 * Status → actions:
 *   draft + owner/operator  → "Send to Customer" | "Submit for Approval" (tech)
 *   draft + tech            → "Submit for Approval"
 *   sent + customer_accepted_at set → "Convert to Job" (owner/operator)
 */

"use client";

import React, { useState } from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import { useSubmitForApproval } from "../hooks/useSubmitForApproval";
import { useConvertQuote } from "../hooks/useConvertQuote";
import { useGeneratePublicLink } from "../hooks/useGeneratePublicLink";
import { SendQuotePreviewModal } from "./SendQuotePreviewModal";

interface QuoteActionBarProps {
  quoteId: string;
  status: string;
  customerAcceptedAt?: string | null;
  customerEmail?: string | null;
  customerName: string;
  /** quote_version_id from QuoteDetailResponse — required for public-link generation */
  quoteVersionId: string;
  testID?: string;
}

export function QuoteActionBar({
  quoteId,
  status,
  customerAcceptedAt,
  customerEmail = null,
  customerName,
  quoteVersionId,
  testID,
}: QuoteActionBarProps) {
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const submitMutation = useSubmitForApproval(quoteId);
  const convertMutation = useConvertQuote(quoteId);
  const publicLinkMutation = useGeneratePublicLink(quoteId);

  const isDraft = status === "draft";
  const isSent = status === "sent";
  const isAccepted = Boolean(customerAcceptedAt);
  const isApproved = status === "approved";

  if (!isDraft && !isApproved && !(isSent && isAccepted)) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-neutral-200 px-6 py-4 flex items-center justify-end gap-3 shadow-lg"
      data-testid={testID}
    >
      {/* Draft actions */}
      {isDraft && (
        <>
          {/* Tech: submit for approval */}
          <RoleGate permission="quote.submit_for_approval">
            <button
              type="button"
              onClick={() => void submitMutation.mutateAsync()}
              disabled={submitMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
            >
              {submitMutation.isPending ? "Submitting…" : "Submit for Approval"}
            </button>
          </RoleGate>

          {/* Owner/Operator: send directly to customer */}
          <RoleGate permission="quotes.edit">
            <button
              type="button"
              onClick={() => setShowPreviewModal(true)}
              disabled={publicLinkMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
            >
              Send to Customer
            </button>
          </RoleGate>
        </>
      )}

      {/* Approved: owner/operator sends to customer */}
      {isApproved && (
        <RoleGate permission="quotes.edit">
          <button
            type="button"
            onClick={() => setShowPreviewModal(true)}
            disabled={publicLinkMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
            data-testid="send-to-customer-approved-btn"
          >
            Send to Customer
          </button>
        </RoleGate>
      )}

      {/* Sent + accepted: convert to job */}
      {isSent && isAccepted && (
        <RoleGate permission="quotes.edit">
          <button
            type="button"
            onClick={() => void convertMutation.mutateAsync()}
            disabled={convertMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-margin-600 rounded-md hover:bg-margin-700 transition-colors disabled:opacity-50"
          >
            {convertMutation.isPending ? "Converting…" : "Convert to Job"}
          </button>
        </RoleGate>
      )}

      {/* Always-preview-before-send modal */}
      <SendQuotePreviewModal
        open={showPreviewModal}
        quoteId={quoteId}
        customerEmail={customerEmail}
        customerName={customerName}
        onClose={() => setShowPreviewModal(false)}
        onConfirm={() => {
          // Confirm Send triggers public-link generation — never pre-emptive
          void publicLinkMutation
            .mutateAsync({ versionId: quoteVersionId })
            .then(() => {
              setShowPreviewModal(false);
            });
        }}
        isConfirming={publicLinkMutation.isPending}
      />
    </div>
  );
}
