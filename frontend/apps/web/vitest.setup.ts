import "@testing-library/jest-dom";
import { vi } from "vitest";
import { apiClient } from "@pilot/shared-api";

// ─── apiClient baseURL reset ───────────────────────────────────────────────────
//
// In the Node/jsdom test environment, NEXT_PUBLIC_API_URL is not set, so
// apiClient defaults to `http://127.0.0.1:8000`.  MSW handlers in this project
// use relative paths (`/api/v1/...`), which MSW only intercepts when the
// outgoing Axios request also uses a relative (origin-relative) URL.
//
// Resetting `defaults.baseURL` to `""` here ensures every Axios request made
// during tests uses a relative URL so MSW can intercept it correctly.
// ──────────────────────────────────────────────────────────────────────────────
apiClient.defaults.baseURL = "";

// ─── aws-amplify/auth stub ────────────────────────────────────────────────────
//
// apiClient's request interceptor calls fetchAuthSession() to attach the JWT.
// apiClient's 401 response interceptor also calls fetchAuthSession({ forceRefresh })
// to attempt a token refresh before retrying.
//
// In the test environment Amplify is not configured. Without this stub:
//   - All apiClient requests emit a warning (no JWT — backend returns 401)
//   - 401-response tests fail because the interceptor makes a network call
//     trying to refresh through Amplify, which is ECONNREFUSED.
//
// This stub makes fetchAuthSession() resolve immediately with an empty session
// (no token) in all test environments.
// ──────────────────────────────────────────────────────────────────────────────
vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: undefined,
  }),
}));

// Polyfill AccessibilityInfo for web unit tests that use RN VoiceConfirmTurn
// The real RN AccessibilityInfo only exists in native/Expo environment.
if (typeof globalThis !== "undefined") {
  // @ts-expect-error — RN global not present in jsdom
  if (!globalThis.AccessibilityInfo) {
    // @ts-expect-error — polyfill
    globalThis.AccessibilityInfo = {
      announceForAccessibility: vi.fn(),
      isScreenReaderEnabled: () => Promise.resolve(false),
      addEventListener: () => ({ remove: vi.fn() }),
    };
  }
}

// Polyfill EventSource for jsdom (not available in Node/jsdom environment)
// Dispatch board SSE hook uses native EventSource; integration tests need this stub.
// Individual hooks (useSseChannel) use eventSourceFactory injection for real unit tests.
if (typeof global.EventSource === "undefined") {
  class MockEventSource {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSED = 2;

    readyState = 1; // OPEN
    onopen: ((e: Event) => void) | null = null;
    onmessage: ((e: MessageEvent) => void) | null = null;
    onerror: ((e: Event) => void) | null = null;

    constructor(public url: string) {}

    addEventListener() {}
    removeEventListener() {}
    dispatchEvent() {
      return true;
    }
    close() {
      this.readyState = 2;
    }
  }

  // @ts-expect-error — polyfill for jsdom
  global.EventSource = MockEventSource;
}
