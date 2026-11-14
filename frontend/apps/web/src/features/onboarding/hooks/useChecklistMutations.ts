/**
 * useChecklistMutations — Optimistic skip / hide / dismiss mutations
 *
 * Location: apps/web/src/features/onboarding/hooks/useChecklistMutations.ts
 *
 * Design doc §16.8 optimistic update pattern: item updates immediately;
 * pending badge until server confirms; failed → rollback with retry.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { CHECKLIST_QUERY_KEY } from "./useOnboardingChecklist";
import type {
  OnboardingChecklistState,
  SkippableChecklistItem,
} from "../types";

export function useChecklistMutations(tenantId: string) {
  const queryClient = useQueryClient();

  /** Skip a skippable checklist item — optimistic update */
  const skipItem = useMutation({
    mutationFn: (item: SkippableChecklistItem) =>
      apiClient
        .put(`/api/v1/tenants/${tenantId}/onboarding/checklist/skip/${item}`)
        .then((r) => r.data),

    onMutate: async (item: SkippableChecklistItem) => {
      await queryClient.cancelQueries({
        queryKey: CHECKLIST_QUERY_KEY(tenantId),
      });
      const previous = queryClient.getQueryData<OnboardingChecklistState>(
        CHECKLIST_QUERY_KEY(tenantId),
      );
      queryClient.setQueryData<OnboardingChecklistState>(
        CHECKLIST_QUERY_KEY(tenantId),
        (old) => {
          if (!old) return old;
          const skippedKey = `${item}Skipped` as keyof OnboardingChecklistState;
          return { ...old, [skippedKey]: true };
        },
      );
      return { previous };
    },

    onError: (_err, _item, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(CHECKLIST_QUERY_KEY(tenantId), ctx.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: CHECKLIST_QUERY_KEY(tenantId),
      });
    },
  });

  /** Hide checklist (collapses to compact pill) — optimistic */
  const hideChecklist = useMutation({
    mutationFn: (hidden: boolean) =>
      apiClient
        .put(`/api/v1/tenants/${tenantId}/onboarding/checklist/hidden`, {
          hidden,
        })
        .then((r) => r.data),

    onMutate: async (hidden: boolean) => {
      await queryClient.cancelQueries({
        queryKey: CHECKLIST_QUERY_KEY(tenantId),
      });
      const previous = queryClient.getQueryData<OnboardingChecklistState>(
        CHECKLIST_QUERY_KEY(tenantId),
      );
      queryClient.setQueryData<OnboardingChecklistState>(
        CHECKLIST_QUERY_KEY(tenantId),
        (old) => (old ? { ...old, checklistHidden: hidden } : old),
      );
      return { previous };
    },

    onError: (_err, _hidden, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(CHECKLIST_QUERY_KEY(tenantId), ctx.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: CHECKLIST_QUERY_KEY(tenantId),
      });
    },
  });

  /** Permanently dismiss checklist — optimistic */
  const dismissChecklist = useMutation({
    mutationFn: () =>
      apiClient
        .put(`/api/v1/tenants/${tenantId}/onboarding/checklist/dismissed`)
        .then((r) => r.data),

    onMutate: async () => {
      await queryClient.cancelQueries({
        queryKey: CHECKLIST_QUERY_KEY(tenantId),
      });
      const previous = queryClient.getQueryData<OnboardingChecklistState>(
        CHECKLIST_QUERY_KEY(tenantId),
      );
      queryClient.setQueryData<OnboardingChecklistState>(
        CHECKLIST_QUERY_KEY(tenantId),
        (old) => (old ? { ...old, checklistDismissedPermanently: true } : old),
      );
      return { previous };
    },

    onError: (_err, _v, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(CHECKLIST_QUERY_KEY(tenantId), ctx.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: CHECKLIST_QUERY_KEY(tenantId),
      });
    },
  });

  return { skipItem, hideChecklist, dismissChecklist };
}
