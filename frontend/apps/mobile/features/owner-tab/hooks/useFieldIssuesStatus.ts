import { Platform } from "react-native";
/**
 * useFieldIssuesStatus (mobile) — TanStack Query hook for field issues summary
 *
 * Location: apps/mobile/features/owner-tab/hooks/useFieldIssuesStatus.ts
 *
 * Established FE-B9. Consumed by FieldIssuesSyncStatusSection.
 * GET /api/v1/owner/field-issues/summary
 * Cache: 60s staleTime — owner tab badge count
 *
 * Uses apiClient (JWT-intercepted). Fails gracefully with retry: 0
 * so a missing/unimplemented backend endpoint doesn't spam the console.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export const FIELD_ISSUES_SUMMARY_QUERY_KEY = ["field-issues-summary"] as const;

// ─── Config constants — never hardcoded ───────────────────────────────────────

/** Deep-link URL to the web field issues resolution surface */
export const FIELD_ISSUES_WEB_URL = process.env.EXPO_PUBLIC_WEB_APP_URL
  ? `${process.env.EXPO_PUBLIC_WEB_APP_URL}/dashboard/approvals/field-issues`
  : "https://app.pilotfortrades.com/dashboard/approvals/field-issues";

/** Base URL for field issues (without path — passed to status row as webAppBaseUrl) */
export const WEB_APP_BASE_URL =
  process.env.EXPO_PUBLIC_WEB_APP_URL ?? "https://app.pilotfortrades.com";

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface FieldIssuesSummary {
  pending_count: number;
}

// ─── API fetcher ──────────────────────────────────────────────────────────────

async function fetchFieldIssuesSummary(): Promise<FieldIssuesSummary> {
  const res = await apiClient.get<FieldIssuesSummary>(
    "/api/v1/owner/field-issues/summary",
  );
  return res.data;
}

// ─── Hook ──────────────────────────────────────────────────────────────────────

export function useFieldIssuesStatus() {
  const isMockAuth =
    Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

  return useQuery({
    queryKey: FIELD_ISSUES_SUMMARY_QUERY_KEY,
    queryFn: fetchFieldIssuesSummary,
    staleTime: 60_000, // 60 seconds
    refetchOnWindowFocus: false, // Mobile: no window focus events
    refetchInterval: 5 * 60 * 1000, // 5-minute background refresh
    retry: 0, // Don't retry — endpoint may not be implemented yet in backend
    // In mock auth mode there is no real Cognito session — skip the fetch entirely
    enabled: !isMockAuth,
  });
}
