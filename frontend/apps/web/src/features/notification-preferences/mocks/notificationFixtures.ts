/**
 * Notification Preference Fixtures — FE-B12
 *
 * Location: apps/web/src/features/notification-preferences/mocks/notificationFixtures.ts
 *
 * Fixture data for MSW handlers covering:
 *  - GET /api/v1/notifications/categories
 *  - GET /api/v1/notifications/preferences
 *  - PUT /api/v1/notifications/preferences/{category_id}/{channel}
 *  - GET /api/v1/notifications/in-app/recent
 *  - POST /api/v1/notifications/in-app/mark-read
 *  - SSE event payloads
 */

import type {
  NotificationCategoryRow,
  NotificationPreferenceCell,
  NotificationChannel,
} from "../types";
import type { InAppNotification } from "../../notifications-center/types";

// Re-export for test convenience
export type {
  NotificationCategoryRow,
  NotificationPreferenceCell,
  NotificationChannel,
};

// ─── Category Registry ────────────────────────────────────────────────────────

export const NOTIFICATION_CATEGORIES: NotificationCategoryRow[] = [
  {
    category_id: "job_activity",
    display_label: "Job activity",
    description: "Updates when jobs are created, scheduled, or completed.",
    display_order: 1,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "quote_approvals",
    display_label: "Quote approvals",
    description: "When a quote is approved, rejected, or needs your action.",
    display_order: 2,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "customer_activity",
    display_label: "Customer activity",
    description:
      "Messages and activity from customers in active conversations.",
    display_order: 3,
    has_asymmetric_forced_minimum: true,
  },
  {
    category_id: "payment_received",
    display_label: "Payment received",
    description: "When an invoice is paid or a payment is recorded.",
    display_order: 4,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "team_updates",
    display_label: "Team updates",
    description:
      "When team members are added, removed, or have schedule changes.",
    display_order: 5,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "system_alerts",
    display_label: "System alerts",
    description: "Critical platform alerts and maintenance notices.",
    display_order: 6,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "qb_sync",
    display_label: "QuickBooks sync",
    description: "When QuickBooks sync succeeds, fails, or needs attention.",
    display_order: 7,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "voice_ai",
    display_label: "Voice AI",
    description: "When a voice quote is processed or requires review.",
    display_order: 8,
    has_asymmetric_forced_minimum: false,
  },
];

// ─── Preference Matrix (24 cells: 8 categories × 3 channels) ─────────────────

/**
 * Full 24-cell matrix with realistic fixture data:
 * - customer_activity push: forced_minimum, can_disable: false (for tech-as-tech context)
 * - system_alerts all: forced_minimum
 * - some cells user-overridden (scope: 'user')
 * - remaining cells at tenant or system default
 */
export const NOTIFICATION_PREFERENCES: NotificationPreferenceCell[] = [
  // job_activity
  {
    category_id: "job_activity",
    channel: "push",
    enabled: true,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "job_activity",
    channel: "email",
    enabled: false,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "job_activity",
    channel: "in_app",
    enabled: true,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
  // quote_approvals
  {
    category_id: "quote_approvals",
    channel: "push",
    enabled: true,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "quote_approvals",
    channel: "email",
    enabled: true,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "quote_approvals",
    channel: "in_app",
    enabled: true,
    scope: "system",
    forced_minimum: false,
    can_disable: true,
  },
  // customer_activity — push is forced minimum (can't disable when you're the tech)
  {
    category_id: "customer_activity",
    channel: "push",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  {
    category_id: "customer_activity",
    channel: "email",
    enabled: false,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "customer_activity",
    channel: "in_app",
    enabled: true,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
  // payment_received
  {
    category_id: "payment_received",
    channel: "push",
    enabled: true,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "payment_received",
    channel: "email",
    enabled: true,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "payment_received",
    channel: "in_app",
    enabled: true,
    scope: "system",
    forced_minimum: false,
    can_disable: true,
  },
  // team_updates
  {
    category_id: "team_updates",
    channel: "push",
    enabled: false,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "team_updates",
    channel: "email",
    enabled: true,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "team_updates",
    channel: "in_app",
    enabled: true,
    scope: "system",
    forced_minimum: false,
    can_disable: true,
  },
  // system_alerts — all forced minimum
  {
    category_id: "system_alerts",
    channel: "push",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  {
    category_id: "system_alerts",
    channel: "email",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  {
    category_id: "system_alerts",
    channel: "in_app",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  // qb_sync
  {
    category_id: "qb_sync",
    channel: "push",
    enabled: true,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "qb_sync",
    channel: "email",
    enabled: false,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "qb_sync",
    channel: "in_app",
    enabled: true,
    scope: "system",
    forced_minimum: false,
    can_disable: true,
  },
  // voice_ai
  {
    category_id: "voice_ai",
    channel: "push",
    enabled: true,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "voice_ai",
    channel: "email",
    enabled: false,
    scope: "system",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "voice_ai",
    channel: "in_app",
    enabled: true,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
];

// ─── Preference write success response factory ────────────────────────────────

export function makePrefWriteSuccess(
  categoryId: string,
  channel: NotificationChannel,
  enabled: boolean,
) {
  return {
    category_id: categoryId,
    channel,
    enabled,
    scope: "user" as const,
  };
}

// ─── In-app notification history (last 50) ────────────────────────────────────

export const RECENT_NOTIFICATIONS: InAppNotification[] = [
  {
    notification_id: "notif-001",
    category_id: "job_activity",
    body: "Job #J-1042 has been completed by Mike T.",
    deep_link_target: "/jobs/J-1042",
    priority: "standard",
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    read_at: null,
  },
  {
    notification_id: "notif-002",
    category_id: "quote_approvals",
    body: 'Quote #Q-882 "Electrical Panel Upgrade" was approved.',
    deep_link_target: "/quotes/Q-882",
    priority: "standard",
    created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    read_at: null,
  },
  {
    notification_id: "notif-003",
    category_id: "payment_received",
    body: "Payment of $2,400 received for Invoice #I-774.",
    deep_link_target: "/invoices/I-774",
    priority: "standard",
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    read_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
  },
  {
    notification_id: "notif-004",
    category_id: "system_alerts",
    body: "Scheduled maintenance: 2am–4am EST Saturday.",
    deep_link_target: "/settings",
    priority: "critical",
    created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    read_at: null,
  },
  {
    notification_id: "notif-005",
    category_id: "voice_ai",
    body: 'Voice quote processed: "Main panel + 4 circuits" — review required.',
    deep_link_target: "/quotes/new?from_voice=true",
    priority: "standard",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    read_at: new Date(Date.now() - 23 * 60 * 60 * 1000).toISOString(),
  },
];

// ─── SSE notification event payload ──────────────────────────────────────────

export const SSE_NOTIFICATION_EVENT = {
  notification_id: "notif-sse-001",
  category_id: "job_activity",
  body: "New job #J-1043 assigned to you.",
  deep_link_target: "/jobs/J-1043",
  priority: "standard" as const,
  created_at: new Date().toISOString(),
};

// ─── Notification history fixture (GET /in-app/recent response) ───────────────

export const RECENT_NOTIFICATIONS_RESPONSE = {
  notifications: RECENT_NOTIFICATIONS,
  total: RECENT_NOTIFICATIONS.length,
};
