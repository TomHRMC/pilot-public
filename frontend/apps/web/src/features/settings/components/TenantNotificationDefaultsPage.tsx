"use client";

/**
 * TenantNotificationDefaultsPage — FE-UI-NAV-S1
 *
 * Location: apps/web/src/features/settings/components/TenantNotificationDefaultsPage.tsx
 *
 * Renders team-level notification defaults for the tenant.
 * Owner-only via RoleGate on the route (settings/notifications/tenant-defaults/page.tsx).
 *
 * Design spec §29.4 — no tab strip; standalone owner-only page.
 *
 * Data architecture:
 *   - Categories: GET /api/v1/notifications/categories (resolved effective defaults)
 *   - Sub-triggers: GET /api/v1/notifications/sub-triggers (forced-minimum metadata)
 *   - Tenant policies: GET /api/v1/notifications/tenant-policy (tenant overrides)
 *
 * Forced-minimum locking:
 *   Cells where any sub-trigger in the category has forced_minimum_push_uniform=true
 *   are locked (can_disable=false) — the platform guarantees those push notifications
 *   will always fire regardless of tenant or user preference. Tenants cannot override
 *   these locks, so we mirror the same visual treatment as the personal prefs page.
 *   recipient-only forced minimums (forced_minimum_push_recipient_only) are NOT locked
 *   at tenant level — they only apply at individual dispatch time.
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { NotificationPreferenceMatrix } from "@pilot/ui";
import type {
  NotificationPreferenceCell,
  NotificationCategoryRow,
  NotificationChannel,
} from "@pilot/ui";
import { useTeamNotificationDefaults } from "@/features/notification-preferences/hooks/useTeamNotificationDefaults";

// The /categories endpoint returns channel-level resolved defaults that are not
// part of the base NotificationCategoryRow type but ARE present at runtime.
interface NotificationCategoryWithChannels extends NotificationCategoryRow {
  channels?: Record<
    string,
    { effective: boolean; system_default: boolean; tenant_default: boolean }
  >;
}

interface SubTrigger {
  sub_trigger_id: string;
  category_id: string;
  display_label: string;
  forced_minimum_push_uniform: boolean;
  forced_minimum_push_recipient_only: boolean;
}

const CATEGORIES_KEY = ["notifications", "categories"] as const;
const SUB_TRIGGERS_KEY = ["notifications", "sub-triggers"] as const;

async function fetchCategories(): Promise<NotificationCategoryWithChannels[]> {
  const res = await apiClient.get<{
    categories: NotificationCategoryWithChannels[];
  }>("/api/v1/notifications/categories");
  return Array.isArray(res.data) ? res.data : (res.data?.categories ?? []);
}

async function fetchSubTriggers(): Promise<SubTrigger[]> {
  const res = await apiClient.get<{ sub_triggers: SubTrigger[] }>(
    "/api/v1/notifications/sub-triggers",
  );
  return res.data?.sub_triggers ?? [];
}

const CHANNELS: NotificationChannel[] = ["push", "email", "in_app"];

/**
 * Adapt tenant policy overrides + category system defaults into the full
 * NotificationPreferenceCell[] shape required by NotificationPreferenceMatrix.
 *
 * Resolution order per cell:
 *   1. Explicit tenant-override row (from GET /api/v1/notifications/tenant-policy)
 *   2. Effective default from GET /api/v1/notifications/categories channels.{ch}.effective
 *
 * Forced-minimum locking:
 *   Push cells for categories that have ANY sub-trigger with forced_minimum_push_uniform=true
 *   are locked (forced_minimum=true, can_disable=false). The lock is uniform — it applies
 *   regardless of which user triggers the event. Recipient-only locks are NOT shown here
 *   because they depend on runtime dispatch context, not tenant-wide configuration.
 */
function adaptPoliciesToCells(
  policies: Array<{ category_id: string; channel: string; enabled: boolean }>,
  categories: NotificationCategoryWithChannels[],
  forcedUniformCategories: Set<string>,
): NotificationPreferenceCell[] {
  // Build a lookup of explicit tenant overrides
  const overrideMap = new Map<string, boolean>();
  for (const p of policies) {
    if (CHANNELS.includes(p.channel as NotificationChannel)) {
      overrideMap.set(`${p.category_id}:${p.channel}`, p.enabled);
    }
  }

  // For every category × channel combination, produce a cell.
  const cells: NotificationPreferenceCell[] = [];
  for (const cat of categories) {
    for (const ch of CHANNELS) {
      const key = `${cat.category_id}:${ch}`;
      const hasOverride = overrideMap.has(key);
      const effectiveFromCat = cat.channels?.[ch]?.effective ?? false;

      // Lock push cells whose category has a uniform forced-minimum sub-trigger.
      // These push notifications will fire regardless of any tenant/user setting.
      const isForced =
        ch === "push" && forcedUniformCategories.has(cat.category_id);

      cells.push({
        category_id: cat.category_id,
        channel: ch,
        enabled: isForced
          ? true
          : hasOverride
            ? (overrideMap.get(key) ?? effectiveFromCat)
            : effectiveFromCat,
        scope: isForced
          ? ("system" as const)
          : hasOverride
            ? ("tenant" as const)
            : ("system" as const),
        forced_minimum: isForced,
        can_disable: !isForced,
      });
    }
  }
  return cells;
}

export function TenantNotificationDefaultsPage() {
  const [showConfirm, setShowConfirm] = useState(false);

  const {
    policies,
    isLoading: policiesLoading,
    error,
    isPending,
    onCellChange,
    onCellRevert,
    reset,
    isResetting,
  } = useTeamNotificationDefaults();

  const { data: categories = [], isLoading: catsLoading } = useQuery({
    queryKey: CATEGORIES_KEY,
    queryFn: fetchCategories,
    staleTime: 5 * 60_000,
  });

  const { data: subTriggers = [], isLoading: subTriggersLoading } = useQuery({
    queryKey: SUB_TRIGGERS_KEY,
    queryFn: fetchSubTriggers,
    staleTime: 10 * 60_000, // Sub-triggers are platform-defined — rarely changes
  });

  // Build a set of category IDs that have uniform forced-minimum push sub-triggers.
  // These push cells are locked in the matrix (can_disable=false).
  const forcedUniformCategories = new Set(
    subTriggers
      .filter((st) => st.forced_minimum_push_uniform)
      .map((st) => st.category_id),
  );

  const isLoading = policiesLoading || catsLoading || subTriggersLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
        Failed to load team notification defaults. Please refresh the page.
      </div>
    );
  }

  const cells = adaptPoliciesToCells(
    policies,
    categories,
    forcedUniformCategories,
  );

  // Stub handlers for bulk actions (tenant policy endpoint doesn't have mute-all variants)
  const noopAsync = async () => {};

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-semibold text-neutral-900">
          Team notification defaults
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Set the default notification preferences for new team members.
          Individual users can override their own settings from their profile
          menu.
        </p>
      </div>

      <NotificationPreferenceMatrix
        preferences={cells}
        categories={categories}
        onCellChange={async (categoryId, channel, enabled) => {
          await onCellChange(categoryId, channel, enabled);
        }}
        onCellRevert={async (categoryId, channel) => {
          await onCellRevert(categoryId, channel);
        }}
        onRowRevert={async () => {
          // No row-level revert for tenant policy in this iteration
        }}
        onMuteAllPush={noopAsync}
        onMuteAllEmail={noopAsync}
        onResetAll={async () => {
          setShowConfirm(true);
        }}
        isPending={isPending}
        testID="tenant-notification-matrix"
      />

      {/* Reset to system defaults action */}
      <div className="mt-4">
        {showConfirm ? (
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-neutral-600">
              Reset all to system defaults?
            </span>
            <button
              type="button"
              onClick={() => {
                reset();
                setShowConfirm(false);
              }}
              disabled={isResetting}
              className="text-sm bg-fault-600 text-white rounded-md px-4 py-2 hover:bg-fault-700 disabled:opacity-50 transition-colors"
            >
              {isResetting ? "Resetting…" : "Confirm reset"}
            </button>
            <button
              type="button"
              onClick={() => setShowConfirm(false)}
              className="text-sm border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 hover:bg-neutral-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowConfirm(true)}
            className="text-sm text-fault-600 hover:text-fault-700 hover:underline"
          >
            Reset all to system defaults
          </button>
        )}
      </div>
    </div>
  );
}
