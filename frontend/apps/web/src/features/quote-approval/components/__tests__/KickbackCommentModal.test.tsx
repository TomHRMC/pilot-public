/**
 * KickbackCommentModal unit tests
 *
 * Location: apps/web/src/features/quote-approval/components/__tests__/KickbackCommentModal.test.tsx
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import { KickbackCommentModal } from "../KickbackCommentModal";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  http.post("/api/v1/quotes/:id/kickback", () =>
    HttpResponse.json({
      id: "q1",
      status: "draft",
      kicked_back_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("KickbackCommentModal", () => {
  it("renders kickback modal with overall comment field", () => {
    render(
      <KickbackCommentModal quoteId="q1" lineItems={[]} onClose={vi.fn()} />,
      { wrapper },
    );
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByLabelText(/overall comment/i)).toBeTruthy();
  });

  it("submit button disabled when no comment", () => {
    render(
      <KickbackCommentModal quoteId="q1" lineItems={[]} onClose={vi.fn()} />,
      { wrapper },
    );
    expect(screen.getByTestId("kickback-submit-btn")).toBeDisabled();
  });

  it("submit button enabled after typing a comment", () => {
    render(
      <KickbackCommentModal quoteId="q1" lineItems={[]} onClose={vi.fn()} />,
      { wrapper },
    );
    fireEvent.change(screen.getByLabelText(/overall comment/i), {
      target: { value: "Please update the labor rate" },
    });
    expect(screen.getByTestId("kickback-submit-btn")).not.toBeDisabled();
  });

  it("calls onClose after successful kickback", async () => {
    const onClose = vi.fn();
    render(
      <KickbackCommentModal quoteId="q1" lineItems={[]} onClose={onClose} />,
      { wrapper },
    );
    fireEvent.change(screen.getByLabelText(/overall comment/i), {
      target: { value: "Needs revision" },
    });
    fireEvent.click(screen.getByTestId("kickback-submit-btn"));
    await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
  });

  it("closes on Escape key", () => {
    const onClose = vi.fn();
    render(
      <KickbackCommentModal quoteId="q1" lineItems={[]} onClose={onClose} />,
      { wrapper },
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });
});
