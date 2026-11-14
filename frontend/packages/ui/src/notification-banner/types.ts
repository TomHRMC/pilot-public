/**
 * Notification Banner — Shared Types
 *
 * Location: packages/ui/src/notification-banner/types.ts
 *
 * Types for the cross-platform notification queue system.
 * The notification severity maps directly to §16.6 four-class severity pattern.
 */

export type NotificationSeverity =
  | "info" // Informational; auto-dismiss 6s
  | "success" // Action succeeded; auto-dismiss 6s
  | "warning" // Needs attention; auto-dismiss 6s
  | "error" // Recoverable error; auto-dismiss 12s
  | "critical"; // Requires explicit user dismiss — NO auto-dismiss

export interface NotificationItem {
  /** Unique ID for this notification; used for dedup and dismiss targeting */
  id: string;
  severity: NotificationSeverity;
  /** Bold title line */
  title: string;
  /** Optional second-line detail */
  detail?: string;
  /**
   * When provided, the entire banner is clickable and navigates to this path.
   * Matches the `deep_link_target` field from BE-B10/A57 SSE payload.
   */
  deepLinkTarget?: string;
  /**
   * Override auto-dismiss duration in ms.
   * Defaults: info/success/warning = 6000; error = 12000; critical = never
   */
  dismissAfterMs?: number;
  /** Timestamp the notification was created (for queue ordering) */
  createdAt: Date;
}

export interface NotificationQueueContextValue {
  /** Current queue of visible notifications (max 3 shown) */
  notifications: NotificationItem[];
  /** Inject a new notification into the queue */
  addNotification: (item: Omit<NotificationItem, "createdAt">) => void;
  /** Dismiss a specific notification by ID */
  dismissNotification: (id: string) => void;
  /** Dismiss all visible notifications */
  dismissAll: () => void;
}

// ── Web-specific props ───────────────────────────────────────────────────────

export interface NotificationBannerWebProps {
  notification: NotificationItem;
  onDismiss: (id: string) => void;
  /**
   * Navigation callback — called when user clicks banner with deepLinkTarget.
   * Surfaces pass their router's push/navigate function here.
   * Defaults to window.location.href assignment if not provided.
   */
  onNavigate?: (path: string) => void;
}

// ── Mobile-specific props ────────────────────────────────────────────────────

export interface NotificationBannerMobileProps {
  notification: NotificationItem;
  onDismiss: (id: string) => void;
  onNavigate?: (path: string) => void;
}

// ── Provider props ───────────────────────────────────────────────────────────

export interface NotificationQueueProviderProps {
  children?: React.ReactNode;
  /**
   * Maximum visible notifications in the queue.
   * Default: 3. When exceeded, oldest is auto-dismissed.
   */
  maxVisible?: number;
}

// ── Auto-dismiss defaults per severity ──────────────────────────────────────

export const AUTO_DISMISS_MS: Record<NotificationSeverity, number | null> = {
  info: 6000,
  success: 6000,
  warning: 6000,
  error: 12000,
  critical: null, // Never auto-dismiss
};
