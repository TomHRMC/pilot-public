/**
 * notificationBellStore — Zustand store for notification bell
 *
 * Location: apps/web/src/features/notifications-center/store/notificationBellStore.ts
 *
 * Global singleton for bell unread count + drawer open state.
 * Not persisted — ephemeral UI state.
 */

import { create } from "zustand";

interface NotificationBellStore {
  unreadCount: number;
  setUnreadCount: (count: number) => void;
  incrementUnread: () => void;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  toggleDrawer: () => void;
}

export const useNotificationBellStore = create<NotificationBellStore>(
  (set) => ({
    unreadCount: 0,
    setUnreadCount: (count: number) => set({ unreadCount: count }),
    incrementUnread: () =>
      set((state) => ({ unreadCount: state.unreadCount + 1 })),
    drawerOpen: false,
    setDrawerOpen: (open: boolean) => set({ drawerOpen: open }),
    toggleDrawer: () => set((state) => ({ drawerOpen: !state.drawerOpen })),
  }),
);
