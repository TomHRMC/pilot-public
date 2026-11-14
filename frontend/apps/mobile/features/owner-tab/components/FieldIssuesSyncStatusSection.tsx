/**
 * FieldIssuesSyncStatusSection — Owner tab field issues status wiring
 *
 * Location: apps/mobile/features/owner-tab/components/FieldIssuesSyncStatusSection.tsx
 *
 * Established FE-B9. Inserted below CalendarSyncStatusSection on Owner tab.
 * Wires useFieldIssuesStatus() to <FieldIssuesSyncStatusRow>.
 *
 * Deep-link URL from WEB_APP_BASE_URL config constant — never hardcoded.
 * Pattern mirrors CalendarSyncStatusSection (FE-B8).
 */

import React from "react";
import { Linking } from "react-native";
import { FieldIssuesSyncStatusRow } from "@pilot/ui";
import {
  useFieldIssuesStatus,
  WEB_APP_BASE_URL,
} from "../hooks/useFieldIssuesStatus";

export function FieldIssuesSyncStatusSection() {
  const { data, isLoading } = useFieldIssuesStatus();

  const handlePress = () => {
    const url = `${WEB_APP_BASE_URL}/dashboard/approvals/field-issues`;
    void Linking.openURL(url);
  };

  return (
    <FieldIssuesSyncStatusRow
      pendingCount={data?.pending_count ?? 0}
      isLoading={isLoading}
      onPress={handlePress}
      webAppBaseUrl={WEB_APP_BASE_URL}
      testID="field-issues-sync-status-section"
    />
  );
}
