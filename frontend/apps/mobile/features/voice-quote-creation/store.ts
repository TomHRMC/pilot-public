/**
 * Voice Quote Creation — Zustand store
 *
 * Location: apps/mobile/features/voice-quote-creation/store.ts
 *
 * Manages ephemeral voice session UI state. Persists fieldMode to AsyncStorage.
 * Step 1 in execution order — all components read from this store.
 */

import { create } from "zustand";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { VoiceState } from "../../../../packages/ui/src/voice/types";
import type { PendingConfirmation } from "../../../../packages/ui/src/voice-confirm-turn/types";

const FIELD_MODE_KEY = "pilot:fieldMode";

export interface VoiceSessionStore {
  voiceState: VoiceState;
  currentSessionId: string | null;
  fieldMode: boolean;
  pendingConfirmation: PendingConfirmation | null;
  /** Partial transcript text for entity highlighting in real-time */
  transcriptBuffer: string;

  setVoiceState: (state: VoiceState) => void;
  setSessionId: (id: string | null) => void;
  /** Toggle field mode and persist to AsyncStorage */
  setFieldMode: (enabled: boolean) => void;
  /** Load field mode preference from AsyncStorage on app mount */
  hydrateFieldMode: () => Promise<void>;
  setPendingConfirmation: (confirmation: PendingConfirmation | null) => void;
  setTranscriptBuffer: (text: string) => void;
  reset: () => void;
}

const initialState = {
  voiceState: "idle" as VoiceState,
  currentSessionId: null,
  fieldMode: false,
  pendingConfirmation: null,
  transcriptBuffer: "",
};

export const useVoiceSessionStore = create<VoiceSessionStore>((set) => ({
  ...initialState,

  setVoiceState: (voiceState) => set({ voiceState }),

  setSessionId: (id) => set({ currentSessionId: id }),

  setFieldMode: (enabled) => {
    set({ fieldMode: enabled });
    AsyncStorage.setItem(FIELD_MODE_KEY, JSON.stringify(enabled)).catch(() => {
      // AsyncStorage write failure is non-fatal for MVP
    });
  },

  hydrateFieldMode: async () => {
    try {
      const stored = await AsyncStorage.getItem(FIELD_MODE_KEY);
      if (stored !== null) {
        set({ fieldMode: JSON.parse(stored) as boolean });
      }
    } catch {
      // No stored value — keep default false
    }
  },

  setPendingConfirmation: (confirmation) =>
    set({ pendingConfirmation: confirmation }),

  setTranscriptBuffer: (text) => set({ transcriptBuffer: text }),

  reset: () => set(initialState),
}));
