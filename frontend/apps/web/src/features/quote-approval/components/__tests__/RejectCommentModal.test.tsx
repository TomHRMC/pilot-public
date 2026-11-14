/**
 * RejectCommentModal unit tests
 *
 * Location: apps/web/src/features/quote-approval/components/__tests__/RejectCommentModal.test.tsx
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
import { RejectCommentModal } from "../RejectCommentModal";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  http.post("/api/v1/quotes/:id/reject", () =>
    HttpResponse.json({
      id: "q1",
      status: "rejected",
      rejected_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("RejectCommentModal", () => {
  it("renders dialog with reason textarea", () => {
    render(<RejectCommentModal quoteId="q1" onClose={vi.fn()} />, { wrapper });
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByLabelText(/reason for rejection/i)).toBeTruthy();
  });

  it("submit button disabled when reason is empty", () => {
    render(<RejectCommentModal quoteId="q1" onClose={vi.fn()} />, { wrapper });
    expect(screen.getByTestId("reject-submit-btn")).toBeDisabled();
  });

  it("submit button enabled after typing reason", () => {
    render(<RejectCommentModal quoteId="q1" onClose={vi.fn()} />, { wrapper });
    fireEvent.change(screen.getByLabelText(/reason for rejection/i), {
      target: { value: "Price is too high" },
    });
    expect(screen.getByTestId("reject-submit-btn")).not.toBeDisabled();
  });

  it("calls onClose after successful reject", async () => {
    const onClose = vi.fn();
    render(<RejectCommentModal quoteId="q1" onClose={onClose} />, { wrapper });
    fireEvent.change(screen.getByLabelText(/reason for rejection/i), {
      target: { value: "Over budget" },
    });
    fireEvent.click(screen.getByTestId("reject-submit-btn"));
    await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
  });
});
