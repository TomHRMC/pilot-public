/**
 * QuoteApprovalActionBar — bottom action bar for quote approval
 *
 * Location: apps/web/src/features/quote-approval/components/QuoteApprovalActionBar.tsx
 *
 * Approve, Approve with N edits, Kick back, Reject.
 * RBAC-gated to owner role. Hidden when require_approval=false.
 */

"use client";

import React, { useState } from "react";
import { KickbackCommentModal } from "./KickbackCommentModal";
import { RejectCommentModal } from "./RejectCommentModal";
import type { QuoteLineItem } from "../hooks/useQuoteDetail";

interface QuoteApprovalActionBarProps {
  quoteId: string;
  pendingEditCount: number;
  requireApproval: boolean;
  isApproving: boolean;
  lineItems?: QuoteLineItem[];
  onApprove: () => void;
  onApproveWithEdits: () => void;
  testID?: string;
}

export function QuoteApprovalActionBar({
  quoteId,
  pendingEditCount,
  requireApproval,
  isApproving,
  lineItems = [],
  onApprove,
  onApproveWithEdits,
  testID,
}: QuoteApprovalActionBarProps) {
  const [showKickback, setShowKickback] = useState(false);
  const [showReject, setShowReject] = useState(false);

  if (!requireApproval) return null;

  const hasPendingEdits = pendingEditCount > 0;

  return (
    <>
      <div
        data-testid={testID ?? "quote-approval-action-bar"}
        className="fixed bottom-0 left-0 right-0 bg-white border-t border-neutral-200 px-6 py-4 flex items-center justify-end gap-3 shadow-lg"
        role="toolbar"
        aria-label="Quote approval actions"
      >
        {/* Reject — leftmost, destructive */}
        <button
          type="button"
          onClick={() => setShowReject(true)}
          disabled={isApproving}
          className="px-4 py-2 text-body font-medium text-fault-600 border border-fault-400 rounded-md hover:bg-fault-50 disabled:opacity-50 transition-colors"
          aria-label="Reject this quote"
          data-testid="reject-btn"
        >
          Reject
        </button>

        {/* Kick back */}
        <button
          type="button"
          onClick={() => setShowKickback(true)}
          disabled={isApproving}
          className="px-4 py-2 text-body font-medium text-alert-800 border border-alert-400 rounded-md hover:bg-alert-50 disabled:opacity-50 transition-colors"
          aria-label="Kick back to technician with comments"
          data-testid="kickback-btn"
        >
          Kick Back
        </button>

        {/* Approve / Approve with edits */}
        {hasPendingEdits ? (
          <button
            type="button"
            onClick={onApproveWithEdits}
            disabled={isApproving}
            className="px-4 py-2 text-body font-medium text-white bg-brand-600 hover:bg-brand-800 rounded-md disabled:opacity-50 transition-colors"
            aria-label={`Approve quote with ${pendingEditCount} pending edit${pendingEditCount !== 1 ? "s" : ""}`}
            data-testid="approve-with-edits-btn"
          >
            {isApproving
              ? "Approving…"
              : `Approve with ${pendingEditCount} edit${pendingEditCount !== 1 ? "s" : ""}`}
          </button>
        ) : (
          <button
            type="button"
            onClick={onApprove}
            disabled={isApproving}
            className="px-4 py-2 text-body font-medium text-white bg-brand-600 hover:bg-brand-800 rounded-md disabled:opacity-50 transition-colors"
            aria-label="Approve this quote as-is"
            data-testid="approve-btn"
          >
            {isApproving ? "Approving…" : "Approve"}
          </button>
        )}
      </div>

      {showKickback && (
        <KickbackCommentModal
          quoteId={quoteId}
          lineItems={lineItems}
          onClose={() => setShowKickback(false)}
        />
      )}

      {showReject && (
        <RejectCommentModal
          quoteId={quoteId}
          onClose={() => setShowReject(false)}
        />
      )}
    </>
  );
}
