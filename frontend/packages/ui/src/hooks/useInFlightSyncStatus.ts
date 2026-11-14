/**
 * useInFlightSyncStatus — Unified sync status data hook
 *
 * Location: packages/ui/src/hooks/useInFlightSyncStatus.ts
 *
 * FE-B15 (new). Single data layer for all sync surfaces except "dispatch"
 * (dispatch is locally sourced from useMutationState — no BE-B15 call).
 *
 * Responsibilities:
 *   1. Maps frontend SyncSurface names → backend path params (hyphen → underscore)
 *   2. Calls GET /api/v1/sync/{surface}/status via TanStack Query
 *   3. Maps backend state strings (underscored) → frontend SyncState (hyphenated)
 *   4. Subscribes to SSE sync_status_changed events via useSseChannel
 *      and invalidates query on matching surface event
 *   5. Returns normalized InFlightSyncStatus ready to spread as props
 *
 * Surface mapping:
 *   dispatch       → NOT SUPPORTED (throws if called; use local data)
 *   mobile-sync    → "mobile_data"
 *   calendar       → "calendar"
 *   quickbooks     → "quickbooks"
 *   background-sync → "background"
 *
 * State mapping (backend → frontend):
 *   synced_idle    → "idle"
 *   synced_pending → "synced-pending"
 *   syncing        → "syncing"
 *   sync_error     → "error"
 *   sync_paused    → "paused"
 *
 * Cache config per design doc Section C.2:
 *   staleTime: 30s, refetchInterval: 60s, refetchOnWindowFocus: true, retry: 2
 *
 * Ref: batch-fe-b15-design.md §A.3, §C.2, §D.1, §F.4, §F.6
 */

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSseChannel } from "./useSseChannel";
import type {
  SyncSurface,
  SyncState,
  PendingItem,
} from "../sync-indicator/types";

// ─── Surface → backend path param mapping ─────────────────────────────────────

/**
 * Maps frontend SyncSurface values to the backend path parameter string.
 * "dispatch" is excluded — it does not call BE-B15.
 */
const SURFACE_MAP: Record<Exclude<SyncSurface, "dispatch">, string> = {
  "mobile-sync": "mobile_data",
  calendar: "calendar",
  quickbooks: "quickbooks",
  "background-sync": "background",
};

// ─── State → frontend SyncState mapping ───────────────────────────────────────

const STATE_MAP: Record<string, SyncState> = {
  synced_idle: "idle",
  synced_pending: "synced-pending",
  syncing: "syncing",
  sync_error: "error",
  sync_paused: "paused",
};

function mapState(backendState: string): SyncState {
  return STATE_MAP[backendState] ?? "idle";
}

// ─── Response shape (from BE-B15 SyncStatusResponse) ─────────────────────────

interface SyncStatusApiResponse {
  surface: string;
  state: string;
  pending_count: number;
  pending_items: PendingItem[];
  last_sync_at: string | null;
  next_sync_at: string | null;
  manual_trigger_supported: boolean;
  resolve_target: string | null;
  amber_threshold: number;
}

// ─── Hook return type ─────────────────────────────────────────────────────────

export interface InFlightSyncStatus {
  state: SyncState;
  pendingCount: number;
  pendingItems: PendingItem[];
  lastSyncedAt: Date | undefined;
  nextSyncAt: Date | undefined;
  manualTriggerSupported: boolean;
  amberThreshold: number;
  isLoading: boolean;
  isError: boolean;
}

/** Safe idle defaults — used when endpoint errors or returns no data */
const IDLE_DEFAULTS: InFlightSyncStatus = {
  state: "idle",
  pendingCount: 0,
  pendingItems: [],
  lastSyncedAt: undefined,
  nextSyncAt: undefined,
  manualTriggerSupported: true,
  amberThreshold: 5,
  isLoading: false,
  isError: false,
};

// ─── SSE event shape ──────────────────────────────────────────────────────────

interface SyncStatusChangedEvent {
  surface: string;
  state: string;
  pending_count: number;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Returns live sync status for the given surface from BE-B15.
 *
 * "dispatch" surface is NOT supported — dispatch uses local mutation state.
 * Calling this hook with surface="dispatch" returns idle defaults with a
 * console.warn. All React hooks are called unconditionally; the query is
 * disabled for dispatch via the `enabled` flag.
 *
 * @example
 * // In QbConflictQueue:
 * const syncStatus = useInFlightSyncStatus("quickbooks");
 * <InFlightSyncIndicator surface="quickbooks" {...syncStatus} onResolve={handleResolve} />
 */
export function useInFlightSyncStatus(
  surface: SyncSurface,
): InFlightSyncStatus {
  const queryClient = useQueryClient();

  const isDispatch = surface === "dispatch";
  // For dispatch, use a safe no-op backend surface (query is disabled anyway)
  const backendSurface = isDispatch
    ? "calendar"
    : SURFACE_MAP[surface as Exclude<SyncSurface, "dispatch">];

  // ── TanStack Query — disabled for dispatch ────────────────────────────────

  const { data, isLoading, isError } = useQuery<SyncStatusApiResponse, Error>({
    queryKey: ["sync-status", surface],
    queryFn: async () => {
      const res = await fetch(`/api/v1/sync/${backendSurface}/status`);
      if (!res.ok) {
        throw new Error(
          `Sync status endpoint returned ${res.status} for surface ${surface}`,
        );
      }
      return res.json() as Promise<SyncStatusApiResponse>;
    },
    enabled: !isDispatch,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    retry: 2,
  });

  // ── SSE invalidation — disabled for dispatch ──────────────────────────────

  const handleSseMessage = useCallback(
    (message: { data: string }) => {
      if (isDispatch) return;
      try {
        const event = JSON.parse(message.data) as
          | { event?: string; data?: SyncStatusChangedEvent }
          | SyncStatusChangedEvent;

        // Handle both wrapped { event, data } and flat payload shapes
        let payload: SyncStatusChangedEvent | undefined;
        if (
          "event" in event &&
          event.event === "sync_status_changed" &&
          "data" in event
        ) {
          payload = event.data as SyncStatusChangedEvent;
        } else if ("surface" in event) {
          payload = event as SyncStatusChangedEvent;
        }

        if (payload && payload.surface === backendSurface) {
          void queryClient.invalidateQueries({
            queryKey: ["sync-status", surface],
          });
        }
      } catch {
        // Ignore malformed SSE messages
      }
    },
    [queryClient, surface, backendSurface, isDispatch],
  );

  useSseChannel({
    path: "/api/v1/sync/stream",
    onMessage: handleSseMessage,
    enabled: !isDispatch,
    fallbackToPollingMs: 60_000,
    pollFn: () => {
      void queryClient.invalidateQueries({
        queryKey: ["sync-status", surface],
      });
    },
  });

  // ── Dispatch early return (hooks already called above) ────────────────────

  if (isDispatch) {
    console.warn(
      "[useInFlightSyncStatus] surface='dispatch' is locally sourced. " +
        "Use useMutationState instead. Returning idle defaults.",
    );
    return IDLE_DEFAULTS;
  }

  // ── Error degradation — return idle defaults ──────────────────────────────

  if (isError || !data) {
    if (isError) {
      console.warn(
        `[useInFlightSyncStatus] Endpoint error for surface '${surface}'. ` +
          "Falling back to idle defaults.",
      );
    }
    return {
      ...IDLE_DEFAULTS,
      isLoading,
      isError,
    };
  }

  // ── Map response to normalized InFlightSyncStatus ─────────────────────────

  // background-sync does not support manual trigger (OS-scheduled)
  const manualTriggerSupported =
    surface === "background-sync" ? false : data.manual_trigger_supported;

  return {
    state: mapState(data.state),
    pendingCount: data.pending_count,
    pendingItems: data.pending_items ?? [],
    lastSyncedAt: data.last_sync_at ? new Date(data.last_sync_at) : undefined,
    nextSyncAt: data.next_sync_at ? new Date(data.next_sync_at) : undefined,
    manualTriggerSupported,
    amberThreshold: data.amber_threshold,
    isLoading,
    isError,
  };
}
