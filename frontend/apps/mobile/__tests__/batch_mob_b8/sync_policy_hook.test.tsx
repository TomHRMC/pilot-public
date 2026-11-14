/**
 * sync_policy_hook.test.tsx — MOB-B8 Part B
 *
 * Tests for useSyncPolicy hook.
 * Uses jest-expo preset + @testing-library/react-native.
 * All tests in __tests__/batch_mob_b8/ — NOT co-located with source.
 *
 * TEST-UPLIFT-1C: Converted from jest.mock("@pilot/shared-api") to MSW
 * setupServer + wildcard handlers (Rule 18). The banned apiClient mock and
 * its jest.requireMock reset logic were removed; the existing inline MSW
 * server is now the single source of mocked responses.
 */

import React from "react";
import { render, waitFor } from "@testing-library/react-native";
import { View, Text } from "react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { MOCK_SYNC_POLICY } from "../../mocks/handlers/backgroundSyncHandlers";
import {
  useSyncPolicy,
  SYNC_POLICY_QUERY_KEY,
} from "../../features/settings/hooks/useSyncPolicy";

// ── Required mocks ────────────────────────────────────────────────────────────

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: jest.fn(), back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
  useSegments: () => [],
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// Test component that exposes hook state via testID
function SyncPolicyConsumer() {
  const { data, isLoading, isError } = useSyncPolicy();
  return (
    <View>
      <Text testID="loading">{isLoading ? "loading" : "done"}</Text>
      <Text testID="error">{isError ? "error" : "ok"}</Text>
      <Text testID="wifi-only">
        {String(data?.background_sync_wifi_only ?? "none")}
      </Text>
      <Text testID="battery-floor">
        {String(data?.background_sync_battery_floor_pct ?? "none")}
      </Text>
      <Text testID="interval">
        {String(data?.background_sync_push_interval_minutes ?? "none")}
      </Text>
    </View>
  );
}

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/settings/background-sync-policy", () =>
    HttpResponse.json(MOCK_SYNC_POLICY),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useSyncPolicy", () => {
  test("test_sync_policy_returns_data — returns mock policy from apiClient", async () => {
    const Wrapper = createWrapper();
    const { getByTestId } = render(
      <Wrapper>
        <SyncPolicyConsumer />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId("loading").props.children).toBe("done");
    });

    expect(getByTestId("wifi-only").props.children).toBe("false");
    expect(getByTestId("battery-floor").props.children).toBe(
      String(MOCK_SYNC_POLICY.background_sync_battery_floor_pct),
    );
    expect(getByTestId("interval").props.children).toBe(
      String(MOCK_SYNC_POLICY.background_sync_push_interval_minutes),
    );
  });

  test("test_sync_policy_loading_state — isLoading is true before data arrives", async () => {
    // Delay the response to observe loading state
    server.use(
      http.get("*/api/v1/settings/background-sync-policy", async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return HttpResponse.json(MOCK_SYNC_POLICY);
      }),
    );

    const Wrapper = createWrapper();
    const { getByTestId } = render(
      <Wrapper>
        <SyncPolicyConsumer />
      </Wrapper>,
    );

    // Immediately after render — should be loading
    expect(getByTestId("loading").props.children).toBe("loading");

    // After resolution — should be done
    await waitFor(() => {
      expect(getByTestId("loading").props.children).toBe("done");
    });
  });

  test("test_sync_policy_error_state — isError is true on 500, does not throw", async () => {
    server.use(
      http.get("*/api/v1/settings/background-sync-policy", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Server Error",
            status: 500,
            detail: "server error",
          },
          { status: 500 },
        ),
      ),
    );

    const Wrapper = createWrapper();
    const { getByTestId } = render(
      <Wrapper>
        <SyncPolicyConsumer />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId("loading").props.children).toBe("done");
    });

    expect(getByTestId("error").props.children).toBe("error");
  });

  test("test_sync_policy_stale_time — query key matches expected constant", () => {
    // Verify the query key is ['background-sync-policy'] as designed
    expect(SYNC_POLICY_QUERY_KEY).toEqual(["background-sync-policy"]);
  });
});

// Re-export SYNC_POLICY_QUERY_KEY from handlers for import in test file 1
export { SYNC_POLICY_QUERY_KEY };
