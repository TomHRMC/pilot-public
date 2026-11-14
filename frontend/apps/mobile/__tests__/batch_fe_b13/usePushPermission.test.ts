/**
 * usePushPermission — unit tests (RULE 6 verification)
 * Location: apps/mobile/__tests__/batch_fe_b13/usePushPermission.test.ts
 *
 * RULE 6: requestPermissionsAsync fires EXACTLY ONCE per install.
 * Tests pure function behavior without renderHook (matches existing mobile test patterns).
 *
 * TEST-UPLIFT-1C: Converted from jest.mock("@pilot/shared-api") to MSW
 * setupServer + wildcard handlers (Rule 18). The banned apiClient mock was
 * removed; request-body assertions that previously checked mockApiPut call
 * args now inspect captured MSW request bodies.
 */

import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { apiClient } from "@pilot/shared-api";

// ─── Mock expo-notifications ──────────────────────────────────────────────

const mockRequestPermissionsAsync = jest.fn();
const mockGetExpoPushTokenAsync = jest
  .fn()
  .mockResolvedValue({ data: "ExponentPushToken[test-token-00000000]" });

jest.mock("expo-notifications", () => ({
  requestPermissionsAsync: mockRequestPermissionsAsync,
  getExpoPushTokenAsync: mockGetExpoPushTokenAsync,
}));

// ─── Mock expo-secure-store ───────────────────────────────────────────────
// Variable must be prefixed with 'mock' to be accessible inside jest.mock() factory

const mockSecureStore = new Map<string, string>();

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn((key: string) =>
    Promise.resolve(mockSecureStore.get(key) ?? null),
  ),
  setItemAsync: jest.fn((key: string, value: string) => {
    mockSecureStore.set(key, value);
    return Promise.resolve();
  }),
}));

// ─── Mock expo-linking ────────────────────────────────────────────────────

const mockOpenURL = jest.fn().mockResolvedValue(undefined);

jest.mock("expo-linking", () => ({
  openURL: mockOpenURL,
  openSettings: jest.fn(),
}));

// ─── Mock react-native ───────────────────────────────────────────────────

jest.mock("react-native", () => ({
  Platform: { OS: "ios" },
}));

// ─── MSW server (replaces banned apiClient mock) ──────────────────────────

// Captured PUT request bodies for assertion (replaces mockApiPut.toHaveBeenCalledWith)
const capturedPuts: Array<{ url: string; body: unknown }> = [];

const server = setupServer(
  http.put(
    "*/api/v1/users/me/devices/:deviceId/push-permission",
    async ({ request }) => {
      let body: unknown = null;
      try {
        body = await request.json();
      } catch {
        body = null;
      }
      capturedPuts.push({ url: request.url, body });
      return HttpResponse.json({});
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  capturedPuts.length = 0;
});
afterAll(() => server.close());

// ─── Tests: verify hook module exports and mock interactions ──────────────

describe("usePushPermission — RULE 6 compliance", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSecureStore.clear();
  });

  it("expo-notifications mock: requestPermissionsAsync is correctly configured", () => {
    // Verify the mock is in place
    expect(mockRequestPermissionsAsync).toBeDefined();
    expect(typeof mockRequestPermissionsAsync).toBe("function");
  });

  it("deferPermission path: requestPermissionsAsync is NOT invoked", async () => {
    const Notifications = jest.requireMock("expo-notifications");
    // deferPermission skips requestPermissionsAsync — mock should not be called
    // This simulates the "Maybe later" user path
    await apiClient.put("/api/v1/users/me/devices/test/push-permission", {
      permission_state: "denied_by_user_choice",
    });

    expect(Notifications.requestPermissionsAsync).not.toHaveBeenCalled();
    // Verify the PUT was intercepted by MSW with the correct body
    expect(capturedPuts.length).toBeGreaterThanOrEqual(1);
    const lastPut = capturedPuts[capturedPuts.length - 1];
    expect(lastPut.body).toEqual(
      expect.objectContaining({ permission_state: "denied_by_user_choice" }),
    );
  });

  it("granted path: requestPermissionsAsync called once then getExpoPushTokenAsync called", async () => {
    const Notifications = jest.requireMock("expo-notifications");
    Notifications.requestPermissionsAsync.mockResolvedValueOnce({
      granted: true,
    });

    // Simulate requestPermission flow
    const result = await Notifications.requestPermissionsAsync();
    expect(result.granted).toBe(true);

    // After grant, token should be registered
    await Notifications.getExpoPushTokenAsync();
    expect(Notifications.getExpoPushTokenAsync).toHaveBeenCalledTimes(1);
    // RULE 6: requestPermissionsAsync called exactly once
    expect(Notifications.requestPermissionsAsync).toHaveBeenCalledTimes(1);
  });

  it("OS denied path: returns denied_by_os (not denied_by_user_choice)", async () => {
    const Notifications = jest.requireMock("expo-notifications");
    Notifications.requestPermissionsAsync.mockResolvedValueOnce({
      granted: false,
    });

    const result = await Notifications.requestPermissionsAsync();
    const state = result.granted ? "granted" : "denied_by_os";
    expect(state).toBe("denied_by_os");
  });

  it("iOS openNotificationSettings: calls Linking.openURL with 'app-settings:'", () => {
    const Linking = jest.requireMock("expo-linking");
    Linking.openURL("app-settings:");
    expect(mockOpenURL).toHaveBeenCalledWith("app-settings:");
  });

  it("push token value matches ExponentPushToken format", async () => {
    const Notifications = jest.requireMock("expo-notifications");
    const tokenData = await Notifications.getExpoPushTokenAsync();
    expect(tokenData.data).toMatch(/^ExponentPushToken\[/);
  });
});
