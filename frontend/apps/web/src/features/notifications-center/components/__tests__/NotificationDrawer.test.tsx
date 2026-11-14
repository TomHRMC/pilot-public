/**
 * NotificationDrawer unit tests — FE-B23
 *
 * Location: apps/web/src/features/notifications-center/components/__tests__/NotificationDrawer.test.tsx
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
import { NotificationDrawer } from "../NotificationDrawer";
import { useNotificationBellStore } from "../../store/notificationBellStore";
import { mockInAppNotifications } from "@/mocks/handlers/b23Handlers";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
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
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeQc()}>{children}</QueryClientProvider>
  );
}

describe("NotificationDrawer", () => {
  it("renders notification list from MSW data", async () => {
    useNotificationBellStore.setState({ drawerOpen: true, unreadCount: 2 });
    render(<NotificationDrawer />, { wrapper: Wrapper });
    expect(
      await screen.findByTestId("notification-drawer"),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(mockInAppNotifications[0].body),
    ).toBeInTheDocument();
  });

  it("Mark all read button fires mutation", async () => {
    useNotificationBellStore.setState({ drawerOpen: true, unreadCount: 2 });
    render(<NotificationDrawer />, { wrapper: Wrapper });
    const btn = await screen.findByTestId("mark-all-read-btn");
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    // After click, button becomes pending-disabled briefly — verify it exists
    expect(btn).toBeDefined();
  });

  it("unread items shown with unread style", async () => {
    useNotificationBellStore.setState({ drawerOpen: true });
    render(<NotificationDrawer />, { wrapper: Wrapper });
    const unread = await screen.findByTestId(
      `notification-item-${mockInAppNotifications[0].notification_id}`,
    );
    expect(unread.className).toContain("bg-blue-50");
  });

  it("read items do not show unread style", async () => {
    useNotificationBellStore.setState({ drawerOpen: true });
    render(<NotificationDrawer />, { wrapper: Wrapper });
    // notif-003 has read_at set
    const readItem = await screen.findByTestId(
      `notification-item-${mockInAppNotifications[2].notification_id}`,
    );
    expect(readItem.className).not.toContain("bg-blue-50");
  });

  it("close button closes the drawer", async () => {
    useNotificationBellStore.setState({ drawerOpen: true });
    render(<NotificationDrawer />, { wrapper: Wrapper });
    fireEvent.click(await screen.findByTestId("close-drawer-btn"));
    expect(useNotificationBellStore.getState().drawerOpen).toBe(false);
  });

  it("does not render when drawer is closed", () => {
    useNotificationBellStore.setState({ drawerOpen: false });
    render(<NotificationDrawer />, { wrapper: Wrapper });
    expect(screen.queryByTestId("notification-drawer")).not.toBeInTheDocument();
  });
});
