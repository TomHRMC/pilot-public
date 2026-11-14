/**
 * Zustand store unit tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/store.unit.test.ts
 * Test plan §I — 6 tests
 */

// Mock AsyncStorage before imports
jest.mock("@react-native-async-storage/async-storage", () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
  removeItem: jest.fn().mockResolvedValue(undefined),
}));

import AsyncStorage from "@react-native-async-storage/async-storage";

// Import store after mocks
const {
  useVoiceSessionStore,
} = require("../../features/voice-quote-creation/store");

describe("useVoiceSessionStore", () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useVoiceSessionStore.getState().reset();
    jest.clearAllMocks();
  });

  it("initial state matches defaults", () => {
    const state = useVoiceSessionStore.getState();
    expect(state.voiceState).toBe("idle");
    expect(state.currentSessionId).toBeNull();
    expect(state.fieldMode).toBe(false);
    expect(state.pendingConfirmation).toBeNull();
    expect(state.transcriptBuffer).toBe("");
  });

  it("setVoiceState transitions state correctly", () => {
    const { setVoiceState } = useVoiceSessionStore.getState();
    setVoiceState("listening");
    expect(useVoiceSessionStore.getState().voiceState).toBe("listening");
    setVoiceState("processing");
    expect(useVoiceSessionStore.getState().voiceState).toBe("processing");
    setVoiceState("error");
    expect(useVoiceSessionStore.getState().voiceState).toBe("error");
  });

  it("setFieldMode persists to AsyncStorage", async () => {
    const { setFieldMode } = useVoiceSessionStore.getState();
    setFieldMode(true);

    expect(useVoiceSessionStore.getState().fieldMode).toBe(true);
    // AsyncStorage write is non-blocking — wait a tick
    await new Promise((r) => setTimeout(r, 0));
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      "pilot:fieldMode",
      "true",
    );
  });

  it("setPendingConfirmation sets confirmation state", () => {
    const { setPendingConfirmation } = useVoiceSessionStore.getState();
    const confirmation = {
      intentId: "intent-001",
      prompt: "Send the quote?",
      expiresAt: new Date(Date.now() + 60_000).toISOString(),
    };
    setPendingConfirmation(confirmation);
    expect(useVoiceSessionStore.getState().pendingConfirmation).toEqual(
      confirmation,
    );
  });

  it("reset returns all state to defaults", () => {
    const store = useVoiceSessionStore.getState();
    store.setVoiceState("listening");
    store.setSessionId("session-001");
    store.setFieldMode(true);
    store.setPendingConfirmation({
      intentId: "i-001",
      prompt: "test",
      expiresAt: new Date().toISOString(),
    });

    store.reset();

    const state = useVoiceSessionStore.getState();
    expect(state.voiceState).toBe("idle");
    expect(state.currentSessionId).toBeNull();
    expect(state.fieldMode).toBe(false);
    expect(state.pendingConfirmation).toBeNull();
    expect(state.transcriptBuffer).toBe("");
  });

  it("setTranscriptBuffer updates buffer for entity highlighting", () => {
    const { setTranscriptBuffer } = useVoiceSessionStore.getState();
    setTranscriptBuffer("Create a quote for Tom");
    expect(useVoiceSessionStore.getState().transcriptBuffer).toBe(
      "Create a quote for Tom",
    );
    setTranscriptBuffer("");
    expect(useVoiceSessionStore.getState().transcriptBuffer).toBe("");
  });
});
