/**
 * Conflict Resolution Detail Route
 *
 * Location: apps/mobile/app/(tabs)/(home)/sync/conflict/[conflictId].tsx
 *
 * Route: (tabs)/(home)/sync/conflict/[conflictId]
 * Auth: Required (tech role)
 * Param: conflictId — ID of the conflict from BE-B7b
 *
 * Receives conflictId from route params; loads conflict detail from
 * GET /api/v1/mobile-sync/conflicts/{id} and renders ConflictResolutionScreen.
 *
 * Per batch-fe-b7-design.md Section C and Section A.3.3.
 */

import React, { useCallback } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { RoleGate } from "@pilot/ui";
import { ConflictResolutionScreen } from "../../../../../features/offline-sync/components/ConflictResolutionScreen";
import { apiClient } from "@pilot/shared-api";
import { useSyncQueueStore } from "../../../../../features/offline-sync/store";

export default function ConflictResolutionRoute(): React.ReactElement {
  const { conflictId } = useLocalSearchParams<{ conflictId: string }>();
  const router = useRouter();
  const { setActiveConflictId } = useSyncQueueStore();

  const handleResolved = useCallback(() => {
    setActiveConflictId(null);
    // Navigate back to sync queue
    router.back();
  }, [router, setActiveConflictId]);

  // Adapt the shared apiClient to the ConflictResolutionScreen's minimal interface
  const conflictApiClient = {
    get: async (url: string) => {
      const response = await (
        apiClient as unknown as {
          get: (url: string) => Promise<{ data: unknown }>;
        }
      ).get(url);
      return response;
    },
    post: async (url: string, data: unknown) => {
      const response = await (
        apiClient as unknown as {
          post: (url: string, data: unknown) => Promise<{ data: unknown }>;
        }
      ).post(url, data);
      return response;
    },
  };

  if (!conflictId) {
    return <></>;
  }

  return (
    <RoleGate role="technician">
      <ConflictResolutionScreen
        conflictId={conflictId}
        apiClient={conflictApiClient}
        onResolved={handleResolved}
        testID="conflict-resolution-route"
      />
    </RoleGate>
  );
}
