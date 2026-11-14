"use client";

/**
 * NotificationBanner — Web variant
 *
 * Location: packages/ui/src/notification-banner/web/NotificationBanner.tsx
 *
 * Portal-based toast rendered in #notification-root via NotificationPortal.
 * Severity colors map to §16.6 four-class severity tokens.
 * Auto-dismiss via useEffect with setTimeout. Critical severity never auto-dismisses.
 */

import React, { useEffect } from "react";
import type { NotificationBannerWebProps } from "../types";
import { AUTO_DISMISS_MS } from "../types";

/** Map severity to Tailwind token-based color classes */
const SEVERITY_CLASSES: Record<
  string,
  { bg: string; border: string; text: string; icon: string }
> = {
  info: {
    bg: "bg-brand-50",
    border: "border-brand-200",
    text: "text-brand-800",
    icon: "text-brand-600",
  },
  success: {
    bg: "bg-margin-50",
    border: "border-margin-200",
    text: "text-margin-800",
    icon: "text-margin-600",
  },
  warning: {
    bg: "bg-alert-50",
    border: "border-alert-200",
    text: "text-alert-800",
    icon: "text-alert-600",
  },
  error: {
    bg: "bg-fault-50",
    border: "border-fault-200",
    text: "text-fault-800",
    icon: "text-fault-600",
  },
  critical: {
    bg: "bg-fault-100",
    border: "border-fault-400",
    text: "text-fault-900",
    icon: "text-fault-800",
  },
};

/**
 * NotificationBanner (web)
 *
 * @example
 * <NotificationBanner
 *   notification={item}
 *   onDismiss={dismissNotification}
 *   onNavigate={(path) => router.push(path)}
 * />
 */
export function NotificationBanner({
  notification,
  onDismiss,
  onNavigate,
}: NotificationBannerWebProps) {
  const { id, severity, title, detail, deepLinkTarget, dismissAfterMs } =
    notification;

  const autoDismissMs =
    dismissAfterMs !== undefined ? dismissAfterMs : AUTO_DISMISS_MS[severity];

  // Auto-dismiss via timer (critical = null = never)
  useEffect(() => {
    if (autoDismissMs === null) return;
    const timer = setTimeout(() => {
      onDismiss(id);
    }, autoDismissMs);
    return () => clearTimeout(timer);
  }, [id, autoDismissMs, onDismiss]);

  const classes = SEVERITY_CLASSES[severity] ?? SEVERITY_CLASSES["info"]!;

  const ariaLive =
    severity === "error" || severity === "critical" ? "assertive" : "polite";

  function handleClick() {
    if (deepLinkTarget) {
      if (onNavigate) {
        onNavigate(deepLinkTarget);
      } else {
        window.location.href = deepLinkTarget;
      }
    }
  }

  const containerRole = deepLinkTarget ? "button" : "alert";

  return (
    <div
      role={containerRole}
      aria-live={ariaLive}
      data-testid={`notification-banner-${id}`}
      className={`
        flex items-start gap-3 rounded-lg border px-4 py-3 shadow-md w-full
        ${classes.bg} ${classes.border}
        ${deepLinkTarget ? "cursor-pointer hover:opacity-90" : ""}
        transition-opacity
      `}
      onClick={deepLinkTarget ? handleClick : undefined}
      onKeyDown={
        deepLinkTarget
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") handleClick();
            }
          : undefined
      }
      tabIndex={deepLinkTarget ? 0 : undefined}
      aria-label={deepLinkTarget ? `${title} — click to view` : undefined}
    >
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold ${classes.text}`}>{title}</p>
        {detail && (
          <p className={`text-sm mt-0.5 ${classes.text} opacity-80`}>
            {detail}
          </p>
        )}
      </div>

      {/* Dismiss button */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onDismiss(id);
        }}
        aria-label={`Dismiss: ${title}`}
        className={`
          flex-shrink-0 p-1 rounded-md
          ${classes.icon} hover:opacity-70
          focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1
        `}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 16 16"
          aria-hidden="true"
        >
          <path
            d="M12 4L4 12M4 4l8 8"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  );
}
