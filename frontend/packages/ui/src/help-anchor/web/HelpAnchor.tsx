/**
 * HelpAnchor — web implementation — FE-B16
 *
 * Location: packages/ui/src/help-anchor/web/HelpAnchor.tsx
 *
 * Renders a "?" icon button. On click, opens the HelpDrawer with the
 * provided context payload.
 *
 * RULE 4: All 14 MVP contextual anchor placements use this single component.
 */

import React from "react";
import type { HelpAnchorProps } from "../types";

interface WebHelpAnchorProps extends HelpAnchorProps {
  onOpen: (payload: import("../types").HelpContextPayload) => void;
}

// sm: 16px (h-4), md: 20px (h-5) — both on 4px grid
const SIZE_CLASSES = {
  sm: "h-4 w-4 text-xs",
  md: "h-5 w-5 text-sm",
} as const;

// Inner icon sizes — on 4px grid: sm=h-3.5 (14px), md=h-4 (16px)
const ICON_CLASSES = {
  sm: "h-3.5 w-3.5 text-xs",
  md: "h-4 w-4 text-xs",
} as const;

export function HelpAnchor({
  contextPayload,
  label = "Open contextual help",
  size = "sm",
  className = "",
  testId,
  onOpen,
}: WebHelpAnchorProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onOpen(contextPayload);
  };

  return (
    <button
      type="button"
      aria-label={label}
      data-testid={testId ?? "help-anchor"}
      onClick={handleClick}
      className={[
        "inline-flex items-center justify-center rounded-full",
        "text-neutral-400 hover:text-brand-600 cursor-pointer",
        "focus:outline-none focus:ring-2 focus:ring-brand-300",
        "transition-colors duration-150",
        SIZE_CLASSES[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "flex items-center justify-center rounded-full",
          "border border-current font-semibold leading-none",
          ICON_CLASSES[size],
        ].join(" ")}
      >
        ?
      </span>
    </button>
  );
}
