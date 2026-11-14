/**
 * HelpDrawerHeader — FE-B16
 *
 * Location: apps/web/src/features/help/components/HelpDrawerHeader.tsx
 *
 * "Help ✕" header with History toggle icon.
 */

"use client";

import React from "react";
import type { HelpPanelView } from "../types";

interface HelpDrawerHeaderProps {
  view: HelpPanelView;
  onClose: () => void;
  onToggleHistory: () => void;
}

export function HelpDrawerHeader({
  view,
  onClose,
  onToggleHistory,
}: HelpDrawerHeaderProps) {
  return (
    <div
      className="flex items-center justify-between px-4 py-3 border-b border-neutral-200"
      data-testid="help-drawer-header"
    >
      <span className="text-sm font-semibold text-neutral-800">
        {view === "history" ? "Chat history" : "Help"}
      </span>

      <div className="flex items-center gap-2">
        {/* History toggle */}
        <button
          type="button"
          aria-label={
            view === "history" ? "Back to current chat" : "View chat history"
          }
          onClick={onToggleHistory}
          data-testid="help-history-toggle"
          className={[
            "p-1.5 rounded-md transition-colors text-sm",
            view === "history"
              ? "text-brand-600 bg-brand-50"
              : "text-neutral-400 hover:text-brand-600 hover:bg-neutral-50",
          ].join(" ")}
        >
          🕐
        </button>

        {/* Close button */}
        <button
          type="button"
          aria-label="Close help panel"
          onClick={onClose}
          data-testid="help-drawer-close"
          className="p-1.5 rounded-md text-neutral-400 hover:text-neutral-600 hover:bg-neutral-50 transition-colors text-sm"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
