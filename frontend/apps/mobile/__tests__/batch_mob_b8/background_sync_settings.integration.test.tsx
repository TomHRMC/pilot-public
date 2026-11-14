/**
 * background_sync_settings.integration.test.tsx — MOB-B8 Part B
 *
 * Integration tests for BackgroundSyncSettingsSection component.
 * Uses jest-expo preset + @testing-library/react-native + MSW.
 * All tests in __tests__/batch_mob_b8/ — NOT co-located with source.
 *
 * TEST-UPLIFT-1C: Converted from jest.mock("@pilot/shared-api") to MSW
 * setupServer + wildcard handlers (Rule 18). The banned apiClient mock and
 * its jest.requireMock reset logic were removed; the existing inline MSW
 * server is now the single source of mocked responses.
 */

import React from "react";
import { render, waitFor, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { MOCK_SYNC_POLICY } from "../../mocks/handlers/backgroundSyncHandlers";
import { BackgroundSyncSettingsSection } from "../../features/settings/components/BackgroundSyncSettingsSection";

// ── Required mocks ────────────────────────────────────────────────────────────

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: jest.fn(), back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
  useSegments: () => [],
}));

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/settings/background-sync-policy", () =>
    HttpResponse.json(MOCK_SYNC_POLICY),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Test wrapper ──────────────────────────────────────────────────────────────

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

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("BackgroundSyncSettingsSection", () => {
  test("test_settings_section_renders — renders without crash", async () => {
    const Wrapper = createWrapper();
    const { getByTestId } = render(
      <Wrapper>
        <BackgroundSyncSettingsSection />
      </Wrapper>,
    );

    // Wait for loading to finish
    await waitFor(() => {
      expect(getByTestId("background-sync-settings-section")).toBeTruthy();
    });
  });

  test("test_settings_shows_defaults — displays MSW mock values in read-only rows", async () => {
    const Wrapper = createWrapper();
    const { getByTestId } = render(
      <Wrapper>
        <BackgroundSyncSettingsSection />
      </Wrapper>,
    );

    await waitFor(() => {
      // wifi-only = false → "Off"
      expect(getByTestId("wifi-only-value").props.children).toBe("Off");
      // battery-floor = 20 → "20%"
      expect(getByTestId("battery-floor-value").props.children).toEqual([
        20,
        "%",
      ]);
      // sync-interval = 5 → "5 min"
      expect(getByTestId("sync-interval-value").props.children).toEqual([
        5,
        " min",
      ]);
    });
  });

  test("test_settings_toggle_enabled — pressing the toggle changes the displayed state", async () => {
    const Wrapper = createWrapper();
    const { getByTestId } = render(
      <Wrapper>
        <BackgroundSyncSettingsSection />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId("background-sync-settings-section")).toBeTruthy();
    });

    const toggle = getByTestId("background-sync-toggle");
    // MOCK_SYNC_POLICY.background_sync_enabled = true, so initial value = true
    expect(toggle.props.value).toBe(true);

    // Toggle off
    fireEvent(toggle, "valueChange", false);

    await waitFor(() => {
      expect(getByTestId("background-sync-toggle").props.value).toBe(false);
    });
  });

  test("test_settings_shows_owner_note — owner control note is visible", async () => {
    const Wrapper = createWrapper();
    const { getByTestId } = render(
      <Wrapper>
        <BackgroundSyncSettingsSection />
      </Wrapper>,
    );

    await waitFor(() => {
      const ownerNote = getByTestId("owner-note");
      expect(ownerNote).toBeTruthy();
      expect(ownerNote.props.children).toContain(
        "controlled by your account owner",
      );
    });
  });

  test("test_settings_policy_error_graceful — section renders with safe defaults on API 500", async () => {
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
        <BackgroundSyncSettingsSection />
      </Wrapper>,
    );

    // Should not throw — renders with safe defaults
    await waitFor(() => {
      expect(getByTestId("background-sync-settings-section")).toBeTruthy();
    });

    // Safe defaults: wifi-only = "Off", battery = 20%, interval = 5 min
    expect(getByTestId("wifi-only-value").props.children).toBe("Off");
    expect(getByTestId("battery-floor-value").props.children).toEqual([
      20,
      "%",
    ]);
    expect(getByTestId("sync-interval-value").props.children).toEqual([
      5,
      " min",
    ]);
  });
});
