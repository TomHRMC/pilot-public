import { Platform } from "react-native";
/**
 * useOwnerArSummary — TanStack Query hook for outstanding invoice summary
 *
 * Location: apps/mobile/features/owner-tab/hooks/useOwnerArSummary.ts
 *
 * GET /api/v1/invoices/?status=sent&limit=50
 * Derives overdueCount client-side: items where due_at < today (ISO date comparison).
 * outstandingCount = response.total (server-side total for the status filter).
 *
 * Note: invoice status param is a free string; "sent" is the outstanding proxy.
 * No dollar totals displayed — InvoiceSummary has total_cents but AR section
 * shows counts only (per design doc §D.3).
 *
 * Pattern: follows useCalendarStatus.ts (staleTime, refetchInterval, enabled)
 * MOB-B5
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export const OWNER_AR_SUMMARY_QUERY_KEY = ["owner-ar-summary"] as const;

export interface InvoiceListItem {
  id: string;
  invoice_number: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  status_code: string;
  issued_at: string | null;
  due_at: string | null;
  subtotal_cents: number;
  total_cents: number;
  balance_due_cents: number;
}

export interface OwnerArSummary {
  outstandingCount: number;
  overdueCount: number; // items where due_at < today (derived client-side)
  items: InvoiceListItem[];
}

async function fetchOwnerArSummary(): Promise<OwnerArSummary> {
  const res = await apiClient.get<{ items: InvoiceListItem[]; total: number }>(
    "/api/v1/invoices/",
    { params: { status: "sent", limit: 50 } },
  );

  const todayStr = new Date().toISOString().slice(0, 10);
  const items = res.data.items;

  // Derive overdue count client-side — due_at ISO datetime vs today date string
  const overdueCount = items.filter(
    (inv) => inv.due_at !== null && inv.due_at.slice(0, 10) < todayStr,
  ).length;

  return {
    outstandingCount: res.data.total,
    overdueCount,
    items,
  };
}

export function useOwnerArSummary() {
  const isMockAuth =
    Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

  return useQuery({
    queryKey: OWNER_AR_SUMMARY_QUERY_KEY,
    queryFn: fetchOwnerArSummary,
    staleTime: 60_000, // 60 seconds
    refetchOnWindowFocus: false, // Mobile: no window focus events
    refetchInterval: 5 * 60 * 1000, // 5-minute background refresh
    retry: 1,
    enabled: !isMockAuth,
  });
}
