"use client";

/**
 * Notification Banner — Public API barrel
 * Location: packages/ui/src/notification-banner/index.ts
 *
 * Consumers import as:
 *   import { NotificationBanner, useNotificationQueue, NotificationQueueProvider }
 *     from '@pilot/ui/notification-banner'
 *
 * NotificationPortal is web-only and imported directly by apps/web layout:
 *   import { NotificationPortal } from '@pilot/ui/notification-banner/web/NotificationPortal'
 */

export { NotificationQueueProvider } from "./NotificationQueueProvider";
export { useNotificationQueue } from "./useNotificationQueue";

// Web is the default export. Mobile apps import from the mobile subfolder directly
// (Expo bundler resolves via package.json react-native conditional if set, or
//  the mobile app can import from @pilot/ui/notification-banner/mobile/NotificationBanner)
export { NotificationBanner } from "./web/NotificationBanner";
export { NotificationPortal } from "./web/NotificationPortal";

// Type exports
export type {
  NotificationItem,
  NotificationSeverity,
  NotificationQueueContextValue,
  NotificationBannerWebProps,
  NotificationBannerMobileProps,
  NotificationQueueProviderProps,
} from "./types";

export { AUTO_DISMISS_MS } from "./types";
