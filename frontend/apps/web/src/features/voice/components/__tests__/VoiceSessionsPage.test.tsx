/**
 * VoiceSessionsPage unit tests — FE-B23
 *
 * Location: apps/web/src/features/voice/components/__tests__/VoiceSessionsPage.test.tsx
 */

import { render, screen } from "@testing-library/react";
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
import { VoiceSessionsPage } from "../VoiceSessionsPage";
import { mockVoiceSessions } from "@/mocks/handlers/b23Handlers";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const server = setupServer(
  http.get("/api/v1/voice/sessions/", () =>
    HttpResponse.json({
      sessions: mockVoiceSessions,
      next_cursor: null,
      has_more: false,
    }),
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

describe("VoiceSessionsPage", () => {
  it("renders session list from MSW data", async () => {
    render(<VoiceSessionsPage />, { wrapper: Wrapper });
    expect(
      await screen.findByText(mockVoiceSessions[0].title!),
    ).toBeInTheDocument();
  });

  it("+ New Session button is visible", async () => {
    render(<VoiceSessionsPage />, { wrapper: Wrapper });
    expect(await screen.findByTestId("new-session-btn")).toBeInTheDocument();
  });

  it("each session row links to /voice/[sessionId]", async () => {
    render(<VoiceSessionsPage />, { wrapper: Wrapper });
    const row = await screen.findByTestId(
      `session-row-${mockVoiceSessions[0].session_id}`,
    );
    expect(row).toHaveAttribute(
      "href",
      `/voice/${mockVoiceSessions[0].session_id}`,
    );
  });

  it("shows empty state when no sessions", async () => {
    server.use(
      http.get("/api/v1/voice/sessions/", () =>
        HttpResponse.json({ sessions: [], next_cursor: null, has_more: false }),
      ),
    );
    render(<VoiceSessionsPage />, { wrapper: Wrapper });
    expect(
      await screen.findByText("No voice sessions yet"),
    ).toBeInTheDocument();
  });
});
