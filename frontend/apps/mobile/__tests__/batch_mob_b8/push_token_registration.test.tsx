/**
 * push_token_registration.test.tsx — MOB-B8 Part B
 *
 * Tests for usePushTokenRegistration hook.
 * Uses jest-expo preset + @testing-library/react-native.
 * All tests in __tests__/batch_mob_b8/ — NOT co-located with source.
 *
 * TEST-UPLIFT-1C: Converted from jest.mock("@pilot/shared-api") to MSW
 * setupServer + wildcard handlers (Rule 18). The banned apiClient mock was
 * removed; request-body assertions that previously checked mockApiPost call
 * args now inspect captured MSW request bodies.
 */

import React from "react";
import { render, waitFor } from "@testing-library/react-native";
import { View } from "react-native";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { MOCK_PUSH_TOKEN_RESPONSE } from "../../mocks/handlers/backgroundSyncHandlers";

// ── Test component that uses the hook ─────────────────────────────────────────

import { usePushTokenRegistration } from "../../hooks/usePushTokenRegistration";

// ── Required mocks ────────────────────────────────────────────────────────────

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: jest.fn(), back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
  useSegments: () => [],
}));

const mockGetPermissionsAsync = jest.fn();
const mockGetExpoPushTokenAsync = jest.fn();
jest.mock("expo-notifications", () => ({
  getPermissionsAsync: () => mockGetPermissionsAsync(),
  getExpoPushTokenAsync: () => mockGetExpoPushTokenAsync(),
}));

const mockGetItem = jest.fn();
const mockSetItem = jest.fn();
jest.mock("@react-native-async-storage/async-storage", () => ({
  getItem: (key: string) => mockGetItem(key),
  setItem: (key: string, value: string) => mockSetItem(key, value),
}));

function TestComponent() {
  usePushTokenRegistration();
  return <View testID="test-root" />;
}

// ── MSW server ────────────────────────────────────────────────────────────────

// Captured request bodies for assertion (replaces mockApiPost.toHaveBeenCalledWith)
const capturedPosts: { url: string; body: unknown }[] = [];

const server = setupServer(
  http.post("*/api/v1/mobile/push-tokens", async ({ request }) => {
    let body: unknown = null;
    try {
      body = await request.json();
    } catch {
      body = null;
    }
    capturedPosts.push({ url: request.url, body });
    return HttpResponse.json(MOCK_PUSH_TOKEN_RESPONSE, { status: 200 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  mockGetPermissionsAsync.mockReset();
  mockGetExpoPushTokenAsync.mockReset();
  mockGetItem.mockReset();
  mockSetItem.mockReset();
  capturedPosts.length = 0;
});
afterAll(() => server.close());

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("usePushTokenRegistration", () => {
  test("test_push_token_registration_calls_api — registers token with correct payload", async () => {
    mockGetPermissionsAsync.mockResolvedValue({ status: "granted" });
    mockGetExpoPushTokenAsync.mockResolvedValue({
      data: "ExponentPushToken[test]",
    });
    mockGetItem.mockResolvedValue("existing-device-id-001");

    render(<TestComponent />);

    await waitFor(() => {
      expect(capturedPosts.length).toBeGreaterThanOrEqual(1);
    });

    const lastPost = capturedPosts[capturedPosts.length - 1];
    expect(lastPost.body).toEqual(
      expect.objectContaining({
        push_token: "ExponentPushToken[test]",
        device_id: "existing-device-id-001",
      }),
    );
  });

  test("test_push_token_skips_when_no_permission — no API call when permission denied", async () => {
    mockGetPermissionsAsync.mockResolvedValue({ status: "denied" });

    render(<TestComponent />);

    // Give the async effect time to run
    await waitFor(() => {
      expect(mockGetPermissionsAsync).toHaveBeenCalled();
    });

    expect(capturedPosts).toHaveLength(0);
  });

  test("test_push_token_silent_on_error — component renders without crash on 500", async () => {
    mockGetPermissionsAsync.mockResolvedValue({ status: "granted" });
    mockGetExpoPushTokenAsync.mockResolvedValue({
      data: "ExponentPushToken[test]",
    });
    mockGetItem.mockResolvedValue("device-id");

    // Override to return 500
    server.use(
      http.post("*/api/v1/mobile/push-tokens", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Server Error",
            status: 500,
            detail: "500 Internal Server Error",
          },
          { status: 500 },
        ),
      ),
    );

    // Should not throw
    const { getByTestId } = render(<TestComponent />);

    await waitFor(() => {
      expect(getByTestId("test-root")).toBeTruthy();
    });
  });

  test("test_push_token_device_id_is_stable — uses existing device ID from AsyncStorage", async () => {
    mockGetPermissionsAsync.mockResolvedValue({ status: "granted" });
    mockGetExpoPushTokenAsync.mockResolvedValue({
      data: "ExponentPushToken[abc]",
    });
    // Simulate an existing stable device ID already stored
    mockGetItem.mockResolvedValue("stable-device-id-from-storage");

    render(<TestComponent />);

    await waitFor(() => {
      expect(capturedPosts.length).toBeGreaterThanOrEqual(1);
    });

    const lastPost = capturedPosts[capturedPosts.length - 1];
    expect(lastPost.body).toEqual(
      expect.objectContaining({
        device_id: "stable-device-id-from-storage",
      }),
    );

    // SetItem should NOT be called since ID already existed
    expect(mockSetItem).not.toHaveBeenCalled();
  });
});
