/**
 * Notification Preference Types — FE-B12
 *
 * Location: apps/web/src/features/notification-preferences/types.ts
 *
 * Re-exports shared types from packages/ui where they will live after lock.
 * These are also exported from packages/ui/src/notification-preference-matrix/types.ts.
 */

export type NotificationChannel = "push" | "email" | "in_app";

export type NotificationPreferenceScope =
  | "user"
  | "tenant"
  | "system"
  | "fallback";

export interface NotificationPreferenceCell {
  category_id: string;
  channel: NotificationChannel;
  enabled: boolean;
  scope: NotificationPreferenceScope;
  forced_minimum: boolean;
  /** false = toggle is locked for this user/context */
  can_disable: boolean;
}

export interface NotificationCategoryRow {
  category_id: string;
  display_label: string;
  description: string;
  display_order: number;
  category_group_id?: string;
  has_asymmetric_forced_minimum: boolean;
}

export interface NotificationPreferenceMatrixProps {
  preferences: NotificationPreferenceCell[];
  categories: NotificationCategoryRow[];
  onCellChange: (
    categoryId: string,
    channel: NotificationChannel,
    enabled: boolean,
  ) => Promise<void>;
  onRowRevert: (categoryId: string) => Promise<void>;
  onCellRevert: (
    categoryId: string,
    channel: NotificationChannel,
  ) => Promise<void>;
  onMuteAllPush: () => Promise<void>;
  onMuteAllEmail: () => Promise<void>;
  onResetAll: () => Promise<void>;
  isPending?: boolean;
  visibleCategories?: string[];
  testID?: string;
}

export interface NotificationPreferencesResponse {
  user_id: string;
  preferences: NotificationPreferenceCell[];
}
