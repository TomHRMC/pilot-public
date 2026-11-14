/**
 * ConflictResolutionScreen — Full-screen conflict resolution UI
 *
 * Location: apps/mobile/features/offline-sync/components/ConflictResolutionScreen.tsx
 *
 * Used for `requires_review` severity class conflicts only.
 * NEVER shown for auto_apply or safe_to_apply (handled silently by conflict-handlers.ts).
 *
 * Layout (per spec §11):
 *   - ConflictExplainer (focus set here on mount)
 *   - ConflictVersionCard × 2 (local and server versions with DiffView)
 *   - ConflictActionBar (use my version / use server / send to owner)
 *
 * Accessibility: role="main", aria-label="Sync conflict", focus set to explainer on mount.
 *
 * Per batch-fe-b7-design.md Section A.3.3 and §16.8.
 */

import React, { useCallback, useRef } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  AccessibilityInfo,
  findNodeHandle,
  ActivityIndicator,
} from "react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { colors, spacing } from "@pilot/ui/tokens";
import { ConflictExplainer } from "./ConflictExplainer";
import { ConflictVersionCard } from "./ConflictVersionCard";
import { ConflictActionBar } from "./ConflictActionBar";
import { EscalationStatusRow } from "@pilot/ui";
import type { OfflineEntityType } from "../../../database/sync/types";
import type { DiffField } from "@pilot/ui";

interface ConflictDetail {
  id: string;
  entity_type: OfflineEntityType;
  entity_summary: string;
  severity_class: "requires_review";
  local_version: Record<string, unknown>;
  server_version: Record<string, unknown>;
  field_diffs: {
    field_name: string;
    label: string;
    base_value: unknown;
    modified_value: unknown;
    change_type: "unchanged" | "modified" | "added" | "removed";
  }[];
}

interface ConflictResolutionScreenProps {
  conflictId: string;
  /** Injected apiClient for data fetching */
  apiClient: {
    get: (url: string) => Promise<{ data: unknown }>;
    post: (url: string, data: unknown) => Promise<{ data: unknown }>;
  };
  onResolved: () => void;
  testID?: string;
}

export function ConflictResolutionScreen({
  conflictId,
  apiClient,
  onResolved,
  testID,
}: ConflictResolutionScreenProps): React.ReactElement {
  const queryClient = useQueryClient();
  const explainerRef = useRef<View>(null);
  const [escalationCreated, setEscalationCreated] = React.useState(false);
  const [selectedPerspective, setSelectedPerspective] = React.useState<
    "local" | "server" | null
  >(null);

  // Fetch conflict detail from backend
  const { data: conflict, isLoading } = useQuery({
    queryKey: ["conflict", conflictId],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/mobile-sync/conflicts/${conflictId}`,
      );
      return response.data as ConflictDetail;
    },
  });

  // Set focus to explainer on mount for accessibility
  React.useEffect(() => {
    const timer = setTimeout(() => {
      if (explainerRef.current) {
        const handle = findNodeHandle(explainerRef.current);
        if (handle) {
          AccessibilityInfo.setAccessibilityFocus(handle);
        }
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [conflict]);

  // Resolve conflict mutation
  const resolveMutation = useMutation({
    mutationFn: async (resolution: "use_local" | "use_server") => {
      await apiClient.post(
        `/api/v1/mobile-sync/conflicts/${conflictId}/resolve`,
        {
          resolution,
        },
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["conflict", conflictId],
      });
      onResolved();
    },
  });

  // Escalate to owner mutation
  const escalateMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(
        `/api/v1/mobile-sync/conflicts/${conflictId}/resolve`,
        {
          resolution: "escalate_to_owner",
        },
      );
    },
    onSuccess: () => {
      setEscalationCreated(true);
    },
  });

  const handleUseLocal = useCallback(() => {
    setSelectedPerspective("local");
    resolveMutation.mutate("use_local");
  }, [resolveMutation]);

  const handleUseServer = useCallback(() => {
    setSelectedPerspective("server");
    resolveMutation.mutate("use_server");
  }, [resolveMutation]);

  const handleEscalate = useCallback(() => {
    escalateMutation.mutate();
  }, [escalateMutation]);

  const isLoading_ = resolveMutation.isPending || escalateMutation.isPending;

  if (isLoading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.brand[400]} />
      </SafeAreaView>
    );
  }

  if (!conflict) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <Text style={styles.errorText}>Conflict not found</Text>
      </SafeAreaView>
    );
  }

  // Build DiffField arrays for local and server perspectives
  const localFields: DiffField[] = conflict.field_diffs.map((d) => ({
    fieldName: d.field_name,
    label: d.label,
    baseValue: d.base_value as string | number | boolean | null,
    modifiedValue: d.modified_value as string | number | boolean | null,
    changeType: d.change_type,
  }));

  const serverFields: DiffField[] = conflict.field_diffs.map((d) => ({
    fieldName: d.field_name,
    label: d.label,
    baseValue: d.base_value as string | number | boolean | null,
    modifiedValue: d.modified_value as string | number | boolean | null,
    changeType: d.change_type === "unchanged" ? "unchanged" : "modified",
  }));

  return (
    <SafeAreaView
      style={styles.container}
      testID={testID ?? "conflict-resolution-screen"}
      accessibilityLabel="Sync conflict"
    >
      {/* Escalation confirmation (after escalate_to_owner) */}
      {escalationCreated && (
        <EscalationStatusRow
          entityType={
            conflict.entity_type === "voice_audio"
              ? "job_note"
              : conflict.entity_type
          }
          entitySummary={conflict.entity_summary}
          status="pending"
          escalatedAt={new Date().toISOString()}
          webDeepLink="https://pilotfortrades.com/sync/escalations"
          testID="escalation-status-row"
        />
      )}

      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
      >
        {/* Conflict explainer with ref for a11y focus */}
        <View ref={explainerRef}>
          <ConflictExplainer
            entityType={conflict.entity_type}
            entitySummary={conflict.entity_summary}
            testID="conflict-explainer"
          />
        </View>

        {/* Version comparison cards */}
        <View style={styles.versions}>
          <ConflictVersionCard
            perspective="local"
            entityType={conflict.entity_type}
            fieldDiffs={localFields}
            isSelected={selectedPerspective === "local"}
            testID="local-version-card"
          />

          <ConflictVersionCard
            perspective="server"
            entityType={conflict.entity_type}
            fieldDiffs={serverFields}
            isSelected={selectedPerspective === "server"}
            testID="server-version-card"
          />
        </View>
      </ScrollView>

      {/* Action bar (sticky at bottom) */}
      {!escalationCreated && (
        <ConflictActionBar
          onUseLocal={handleUseLocal}
          onUseServer={handleUseServer}
          onEscalate={handleEscalate}
          isLoading={isLoading_}
          testID="conflict-action-bar"
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[900],
  },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.neutral[900],
  },
  errorText: {
    color: colors.fault[400],
  },
  scrollView: {
    flex: 1,
  },
  versions: {
    padding: spacing[4],
    gap: spacing[4],
  },
});
