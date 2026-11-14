/**
 * useNotificationPreferences — TanStack Query hook
 *
 * Location: apps/web/src/features/notification-preferences/hooks/useNotificationPreferences.ts
 *
 * Manages GET/PUT/DELETE for notification preference matrix.
 * All mutations are passed as callbacks to NotificationPreferenceMatrix.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  NotificationPreferenceCell,
  NotificationCategoryRow,
  NotificationChannel,
  NotificationPreferencesResponse,
} from "../types";

const PREFS_KEY = ["notifications", "preferences"] as const;
const CATEGORIES_KEY = ["notifications", "categories"] as const;

const BASE = "/api/v1/notifications";

// ─── Fetch functions ──────────────────────────────────────────────────────────

async function fetchPreferences(): Promise<NotificationPreferenceCell[]> {
  const res = await apiClient.get<NotificationPreferencesResponse>(
    `${BASE}/preferences`,
  );
  return res.data.preferences;
}

async function fetchCategories(): Promise<NotificationCategoryRow[]> {
  const res = await apiClient.get<{ categories: NotificationCategoryRow[] }>(
    `${BASE}/categories`,
  );
  // Backend returns { categories: [...] } — not a bare array
  return Array.isArray(res.data) ? res.data : (res.data?.categories ?? []);
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useNotificationPreferences() {
  const queryClient = useQueryClient();

  const {
    data: preferences = [],
    isLoading: prefsLoading,
    isError: prefsError,
  } = useQuery({
    queryKey: PREFS_KEY,
    queryFn: fetchPreferences,
    staleTime: 60_000,
  });

  const { data: categories = [], isLoading: catsLoading } = useQuery({
    queryKey: CATEGORIES_KEY,
    queryFn: fetchCategories,
    staleTime: 5 * 60_000,
  });

  // PUT single cell
  const cellChangeMutation = useMutation({
    mutationFn: async ({
      categoryId,
      channel,
      enabled,
    }: {
      categoryId: string;
      channel: NotificationChannel;
      enabled: boolean;
    }) => {
      const res = await apiClient.put(
        `${BASE}/preferences/${categoryId}/${channel}`,
        { enabled },
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PREFS_KEY });
    },
  });

  // DELETE single cell (revert to tenant default)
  const cellRevertMutation = useMutation({
    mutationFn: async ({
      categoryId,
      channel,
    }: {
      categoryId: string;
      channel: NotificationChannel;
    }) => {
      const res = await apiClient.delete(
        `${BASE}/preferences/${categoryId}/${channel}`,
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PREFS_KEY });
    },
  });

  // DELETE all cells for a category (row revert)
  const rowRevertMutation = useMutation({
    mutationFn: async (categoryId: string) => {
      const channels: NotificationChannel[] = ["push", "email", "in_app"];
      await Promise.all(
        channels.map((channel) =>
          apiClient.delete(`${BASE}/preferences/${categoryId}/${channel}`),
        ),
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PREFS_KEY });
    },
  });

  // POST mute-all-push-non-critical
  const muteAllPushMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`${BASE}/preferences/mute-all-push-non-critical`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PREFS_KEY });
    },
  });

  // POST mute-all-email
  const muteAllEmailMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`${BASE}/preferences/mute-all-email`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PREFS_KEY });
    },
  });

  // POST reset-to-tenant-defaults
  const resetAllMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`${BASE}/preferences/reset-to-tenant-defaults`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PREFS_KEY });
    },
  });

  const isPending =
    cellChangeMutation.isPending ||
    cellRevertMutation.isPending ||
    rowRevertMutation.isPending ||
    muteAllPushMutation.isPending ||
    muteAllEmailMutation.isPending ||
    resetAllMutation.isPending;

  return {
    preferences,
    categories,
    isLoading: prefsLoading || catsLoading,
    isError: prefsError,
    isPending,
    onCellChange: async (
      categoryId: string,
      channel: NotificationChannel,
      enabled: boolean,
    ) => {
      await cellChangeMutation.mutateAsync({ categoryId, channel, enabled });
    },
    onCellRevert: async (categoryId: string, channel: NotificationChannel) => {
      await cellRevertMutation.mutateAsync({ categoryId, channel });
    },
    onRowRevert: async (categoryId: string) => {
      await rowRevertMutation.mutateAsync(categoryId);
    },
    onMuteAllPush: async () => {
      await muteAllPushMutation.mutateAsync();
    },
    onMuteAllEmail: async () => {
      await muteAllEmailMutation.mutateAsync();
    },
    onResetAll: async () => {
      await resetAllMutation.mutateAsync();
    },
  };
}
