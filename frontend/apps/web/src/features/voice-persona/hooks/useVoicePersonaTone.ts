/**
 * useVoicePersonaTone — TanStack Query hook
 *
 * Location: apps/web/src/features/voice-persona/hooks/useVoicePersonaTone.ts
 *
 * Manages GET/PUT/DELETE for voice persona tone setting.
 * Composes EffectiveSettingDisplay logic (save-on-selection).
 *
 * RULE: Data export uses refetchInterval — not useOptimisticMutation.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  VoicePersonaTone,
  VoicePersonaToneEffectiveResponse,
} from "../types";

const TONE_KEY = ["settings", "voice-persona-tone"] as const;
const BASE = "/api/v1/settings";

async function fetchVoicePersonaTone(): Promise<VoicePersonaToneEffectiveResponse> {
  const res = await apiClient.get(`${BASE}/voice-persona-tone`);
  return res.data as VoicePersonaToneEffectiveResponse;
}

export function useVoicePersonaTone() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: TONE_KEY,
    queryFn: fetchVoicePersonaTone,
    staleTime: 60_000,
  });

  // PUT user override
  const setToneMutation = useMutation({
    mutationFn: async (value: VoicePersonaTone) => {
      const res = await apiClient.put(`${BASE}/voice-persona-tone`, { value });
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TONE_KEY });
    },
  });

  // DELETE user override (revert to tenant/system)
  const revertToneMutation = useMutation({
    mutationFn: async () => {
      await apiClient.delete(`${BASE}/voice-persona-tone`);
      return null;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TONE_KEY });
    },
  });

  return {
    data,
    isLoading,
    isError,
    isPending: setToneMutation.isPending || revertToneMutation.isPending,
    setTone: async (value: VoicePersonaTone) => {
      await setToneMutation.mutateAsync(value);
    },
    revertTone: async () => {
      await revertToneMutation.mutateAsync();
    },
    setError: setToneMutation.error,
  };
}
