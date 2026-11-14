/**
 * Notification Center Bell — Types
 * Location: packages/ui/src/notification-center-bell/types.ts
 *
 * ⚠️ INTERFACE LOCKED after FE-B12 ships — FE-B13 embeds NotificationCenterBell.
 */

export interface InAppNotification {
  notification_id: string;
  category_id: string;
  body: string;
  deep_link_target: string;
  priority: "standard" | "critical";
  created_at: string;
  read_at: string | null;
}

export interface NotificationSseEvent {
  notification_id: string;
  category_id: string;
  body: string;
  deep_link_target: string;
  priority: "standard" | "critical";
  created_at: string;
}

export interface NotificationCenterBellProps {
  notifications: InAppNotification[];
  unreadCount: number;
  isConnected: boolean;
  onMarkRead: (notificationId: string) => Promise<void>;
  onMarkAllRead: () => Promise<void>;
  onNotificationNavigate: (deepLinkTarget: string) => void;
  testID?: string;
}

export interface UseInAppNotificationsReturn {
  notifications: InAppNotification[];
  unreadCount: number;
  isConnected: boolean;
  isBellOpen: boolean;
  openBell: () => void;
  closeBell: () => void;
  markRead: (notificationId: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}
