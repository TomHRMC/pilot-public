/**
 * Notification Bell Integration Tests — FE-B23
 *
 * Location: apps/web/src/__tests__/batch_fe_b23/notificationBell.integration.test.tsx
 *
 * Tests the full notification bell + drawer flow in the layout.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { mockInAppNotifications } from "@/mocks/handlers/b23Handlers";
import { useNotificationBellStore } from "@/features/notifications-center/store/notificationBellStore";
import { NotificationBell } from "@/features/notifications-center/components/NotificationBell";
import { NotificationDrawer } from "@/features/notifications-center/components/NotificationDrawer";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));
vi.mock("@/features/notifications-center/hooks/useNotificationSse", () => ({
  useNotificationSse: () => ({ isConnected: false }),
}));
vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: { accessToken: { toString: () => "test-tok" } },
  }),
}));

const server = setupServer(
  http.get("/api/v1/notifications/in-app/recent", () =>
    HttpResponse.json({ notifications: mockInAppNotifications }),
  ),
  http.post("/api/v1/notifications/in-app/mark-read", () =>
    HttpResponse.json({ marked: true }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  useNotificationBellStore.setState({ unreadCount: 0, drawerOpen: false });
});
afterAll(() => server.close());

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function AppShell() {
  return (
    <QueryClientProvider client={makeQc()}>
      <header data-testid="app-header">
        <NotificationBell />
      </header>
      <NotificationDrawer />
    </QueryClientProvider>
  );
}

describe("Notification Bell — Integration", () => {
  it("renders notification bell in header", () => {
    render(<AppShell />);
    expect(screen.getByTestId("app-header")).toBeInTheDocument();
    expect(screen.getByTestId("notification-bell")).toBeInTheDocument();
  });

  it("bell shows correct unread count from MSW data", async () => {
    render(<AppShell />);
    // 2 unread notifications in mockInAppNotifications (notif-001, notif-002)
    expect(await screen.findByTestId("notification-badge")).toHaveTextContent(
      "2",
    );
  });

  it("clicking bell opens notification drawer", async () => {
    render(<AppShell />);
    fireEvent.click(await screen.findByTestId("notification-bell"));
    expect(
      await screen.findByTestId("notification-drawer"),
    ).toBeInTheDocument();
  });

  it("notification items appear with body text after opening drawer", async () => {
    render(<AppShell />);
    fireEvent.click(await screen.findByTestId("notification-bell"));
    expect(
      await screen.findByText(mockInAppNotifications[0].body),
    ).toBeInTheDocument();
  });
});
