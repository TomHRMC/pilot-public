/**
 * usePendingSyncItems — Queries all 7 WatermelonDB sync tables for pending items
 *
 * Location: apps/mobile/features/offline-sync/hooks/usePendingSyncItems.ts
 *
 * Returns a flat list of SyncQueueItemData across all offline-write tables:
 *   time_entries, expenses, job_notes, loto_checks, photos,
 *   change_orders, job_status_changes
 *
 * Only records with localSyncStatus IN ['pending','syncing','failed','conflict']
 * are included. Synced records are excluded.
 *
 * Used by sync/index.tsx to replace the static PLACEHOLDER_ITEMS constant.
 *
 * Per batch-mob-b2-design.md §F.3 and §G.5.
 */

import { useState, useEffect } from "react";
import { database } from "../../../database";
import { Q } from "@nozbe/watermelondb";
import type { SyncQueueItemData } from "../components/SyncQueueItem";
import type { OfflineEntityType } from "../../../database/sync/types";
import type { LocalSyncStatus } from "../../../database/models/SyncableModel";

// ── Tables to poll ────────────────────────────────────────────────────────────

const PENDING_STATUSES: LocalSyncStatus[] = [
  "pending",
  "syncing",
  "failed",
  "conflict",
];

interface SyncTableConfig {
  table: string;
  entityType: OfflineEntityType;
  getSummary: (record: Record<string, unknown>) => string;
}

const SYNC_TABLES: SyncTableConfig[] = [
  {
    table: "time_entries",
    entityType: "time_entry",
    getSummary: (r) => {
      const jobId = String(r["job_id"] ?? "");
      const startedAt = r["started_at"];
      const started =
        startedAt instanceof Date
          ? startedAt.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })
          : typeof startedAt === "number"
            ? new Date(startedAt).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })
            : String(startedAt ?? "");
      return `Time entry — ${jobId ? `Job ${jobId.slice(-6)}` : "unknown job"}${started ? ` at ${started}` : ""}`;
    },
  },
  {
    table: "expenses",
    entityType: "expense",
    getSummary: (r) => {
      const code = String(r["job_expense_category_code"] ?? "expense");
      const cents = r["cost_cents"];
      const dollars =
        typeof cents === "number" ? `$${(cents / 100).toFixed(2)}` : "";
      return `Expense — ${code}${dollars ? ` · ${dollars}` : ""}`;
    },
  },
  {
    table: "job_notes",
    entityType: "job_note",
    getSummary: (r) => {
      const content = String(r["content"] ?? "");
      return `Note — ${content.slice(0, 40)}${content.length > 40 ? "…" : ""}`;
    },
  },
  {
    table: "loto_checks",
    entityType: "loto_check",
    getSummary: (r) => {
      const checkType = String(r["check_type"] ?? "");
      return `LOTO — ${checkType}`;
    },
  },
  {
    table: "photos",
    entityType: "photo",
    getSummary: (r) => {
      const jobId = String(r["job_id"] ?? "");
      return `Photo — ${jobId ? `Job ${jobId.slice(-6)}` : "unknown job"}`;
    },
  },
  {
    table: "change_orders",
    entityType: "change_order",
    getSummary: (r) => {
      const title = String(r["title"] ?? "Change order");
      const cents = r["total_amount_cents"];
      const dollars =
        typeof cents === "number" ? ` · $${(cents / 100).toFixed(2)}` : "";
      return `${title}${dollars}`;
    },
  },
  {
    table: "job_status_changes",
    entityType: "job_status_change",
    getSummary: (r) => {
      const from = String(r["from_status"] ?? "");
      const to = String(r["to_status"] ?? "");
      return `Status — ${from} → ${to}`;
    },
  },
];

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface UsePendingSyncItemsReturn {
  items: SyncQueueItemData[];
  totalCount: number;
}

export function usePendingSyncItems(): UsePendingSyncItemsReturn {
  const [items, setItems] = useState<SyncQueueItemData[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadPending() {
      try {
        const allItems: SyncQueueItemData[] = [];

        for (const config of SYNC_TABLES) {
          const records = await database
            .get(config.table)
            .query(Q.where("sync_status", Q.oneOf(PENDING_STATUSES)))
            .fetch();

          for (const record of records) {
            const raw = record as unknown as Record<string, unknown>;
            const clientCaptureAt = raw["clientCaptureAt"];

            allItems.push({
              id: record.id,
              entityType: config.entityType,
              entitySummary: config.getSummary(raw),
              localSyncStatus:
                (raw["localSyncStatus"] as LocalSyncStatus) ?? "pending",
              clientCaptureAt:
                clientCaptureAt instanceof Date
                  ? clientCaptureAt
                  : typeof clientCaptureAt === "number"
                    ? new Date(clientCaptureAt)
                    : new Date(),
            });
          }
        }

        if (!cancelled) {
          // Sort by clientCaptureAt descending (newest first)
          allItems.sort(
            (a, b) => b.clientCaptureAt.getTime() - a.clientCaptureAt.getTime(),
          );
          setItems(allItems);
        }
      } catch {
        // Database not ready or empty — ignore
      }
    }

    void loadPending();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    items,
    totalCount: items.length,
  };
}
