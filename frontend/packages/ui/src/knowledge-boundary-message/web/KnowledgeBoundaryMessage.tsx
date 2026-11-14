/**
 * KnowledgeBoundaryMessage — web implementation — FE-B16
 *
 * Location: packages/ui/src/knowledge-boundary-message/web/KnowledgeBoundaryMessage.tsx
 */

import React from "react";
import type { KnowledgeBoundaryMessageProps } from "../types";

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function KnowledgeBoundaryMessage({
  content,
  timestamp,
  onEscalate,
}: KnowledgeBoundaryMessageProps) {
  return (
    <div
      data-testid="knowledge-boundary-message"
      className="bg-alert-50 border border-alert-200 text-alert-700 border-l-4 border-l-alert-400 rounded-lg p-3 my-1 max-w-[85%]"
    >
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-alert-500 text-xs font-medium">Pilot AI</span>
        <span className="text-alert-400 text-xs">&middot;</span>
        <span className="text-alert-400 text-xs">{formatTime(timestamp)}</span>
      </div>

      <p className="text-alert-700 text-sm leading-relaxed whitespace-pre-wrap">
        {content}
      </p>

      <div className="mt-3 pt-2 border-t border-alert-200">
        <button
          type="button"
          onClick={onEscalate}
          data-testid="knowledge-boundary-escalate-cta"
          className="text-brand-600 hover:text-brand-700 underline text-sm font-medium transition-colors"
        >
          Didn&apos;t find what you needed? Tell us &rarr;
        </button>
      </div>
    </div>
  );
}
