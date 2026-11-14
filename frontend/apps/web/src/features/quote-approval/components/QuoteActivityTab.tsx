/**
 * QuoteActivityTab — audit log for quote lifecycle events
 *
 * Location: apps/web/src/features/quote-approval/components/QuoteActivityTab.tsx
 */

"use client";

import React from "react";
import { useQuoteApprovalComments } from "../hooks/useQuoteComments";
import { LoadingState } from "@pilot/ui/states";

interface QuoteActivityTabProps {
  quoteId: string;
}

export function QuoteActivityTab({ quoteId }: QuoteActivityTabProps) {
  const { data: comments, isLoading } = useQuoteApprovalComments(quoteId);

  if (isLoading) {
    return (
      <div className="py-6">
        <LoadingState type="inline" label="Loading activity..." />
      </div>
    );
  }

  if (!comments || comments.length === 0) {
    return (
      <p className="text-body text-neutral-400 italic py-4">
        No activity recorded yet.
      </p>
    );
  }

  return (
    <ol
      className="relative border-l border-neutral-200 ml-3 space-y-4"
      aria-label="Quote activity log"
    >
      {comments.map((comment) => (
        <li key={comment.id} className="ml-4">
          <div className="absolute -left-1.5 mt-1.5 w-3 h-3 rounded-full bg-neutral-400 border-2 border-white" />
          <div className="flex items-start justify-between">
            <div>
              <p className="text-body font-medium text-neutral-900">
                {comment.user_name}
                <span className="ml-1 text-caption text-neutral-400 font-normal">
                  ({comment.user_role})
                </span>
              </p>
              <p className="text-body text-neutral-600 mt-0.5">
                {comment.comment}
              </p>
              {comment.annotation_type === "line_item" &&
                comment.affected_line_item_id && (
                  <p className="text-caption text-neutral-400 mt-0.5">
                    Line item comment
                  </p>
                )}
            </div>
            <time
              className="text-caption text-neutral-400 shrink-0 ml-4"
              dateTime={comment.created_at}
              title={new Date(comment.created_at).toLocaleString()}
            >
              {new Date(comment.created_at).toLocaleDateString()}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}
