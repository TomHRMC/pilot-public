/**
 * Notification Preference Matrix — Types
 * Location: packages/ui/src/notification-preference-matrix/types.ts
 *
 * ⚠️ INTERFACE LOCKED after FE-B12 ships — FE-B13 uses visibleCategories to embed a subset.
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
  /** false = toggle is locked for this user/context (aria-disabled, no pointer events) */
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
  /** Full 24-cell response from GET /api/v1/notifications/preferences */
  preferences: NotificationPreferenceCell[];
  /** Category registry from GET /api/v1/notifications/categories */
  categories: NotificationCategoryRow[];
  /** Called when user toggles a cell */
  onCellChange: (
    categoryId: string,
    channel: NotificationChannel,
    enabled: boolean,
  ) => Promise<void>;
  /** Called when user reverts a row to tenant defaults */
  onRowRevert: (categoryId: string) => Promise<void>;
  /** Called when user reverts a single cell to tenant default */
  onCellRevert: (
    categoryId: string,
    channel: NotificationChannel,
  ) => Promise<void>;
  /** Page-level bulk action handlers */
  onMuteAllPush: () => Promise<void>;
  onMuteAllEmail: () => Promise<void>;
  onResetAll: () => Promise<void>;
  /** True when any mutation is pending (disables interactions during in-flight) */
  isPending?: boolean;
  /** Omit specific categories (FE-B13 onboarding embeds a subset) */
  visibleCategories?: string[];
  testID?: string;
}
