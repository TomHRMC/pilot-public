/**
 * QuoteChangesTab — shows what the owner modified (post-approval)
 *
 * Location: apps/web/src/features/quote-approval/components/QuoteChangesTab.tsx
 *
 * Tech-facing view. Only visible when quote.has_owner_edits === true.
 * Renders <DiffView variant="quote-line"> from the approval annotation data.
 */

"use client";

import React from "react";
import { DiffView } from "@pilot/ui";
import { useQuoteApprovalComments } from "../hooks/useQuoteComments";
import type { DiffLineItem, DiffField } from "@pilot/ui";
import { LoadingState } from "@pilot/ui/states";

interface QuoteChangesTabProps {
  quoteId: string;
}

export function QuoteChangesTab({ quoteId }: QuoteChangesTabProps) {
  const { data: comments, isLoading } = useQuoteApprovalComments(quoteId);

  if (isLoading) {
    return (
      <div className="py-6">
        <LoadingState type="inline" label="Loading changes..." />
      </div>
    );
  }

  if (!comments || comments.length === 0) {
    return (
      <p className="text-body text-neutral-400 italic py-4">
        No owner changes recorded for this quote.
      </p>
    );
  }

  // Build a synthetic DiffLineItem list from line_item comments
  const lineItemComments = comments.filter(
    (c) => c.annotation_type === "line_item" && c.affected_line_item_id,
  );

  if (lineItemComments.length === 0) {
    return (
      <p className="text-body text-neutral-400 italic py-4">
        No line-item changes recorded. The owner may have added a general
        comment.
      </p>
    );
  }

  const diffLineItems: DiffLineItem[] = lineItemComments.map((comment) => {
    const field: DiffField = {
      fieldName: "owner_comment",
      label: "Owner comment",
      baseValue: null,
      modifiedValue: comment.comment,
      changeType: "added",
      annotation: `Added by ${comment.user_name}`,
    };

    return {
      lineItemId: comment.affected_line_item_id!,
      label: `Line item (${comment.affected_line_item_id!.slice(0, 8)}…)`,
      customerVisible: true,
      lineChangeType: "modified" as const,
      fields: [field],
    };
  });

  return (
    <div>
      <p className="text-body text-neutral-600 mb-4">
        The owner made the following changes before approving this quote.
      </p>
      <DiffView
        variant="quote-line"
        lineItems={diffLineItems}
        testID="quote-changes-diff-view"
      />
    </div>
  );
}
