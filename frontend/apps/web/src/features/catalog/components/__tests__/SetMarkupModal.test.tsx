/**
 * SetMarkupModal Unit Tests — FE-B20
 *
 * Location: apps/web/src/features/catalog/components/__tests__/SetMarkupModal.test.tsx
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
  beforeEach,
} from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { SetMarkupModal } from "../SetMarkupModal";

// Mock the mutation hook
vi.mock("../../hooks/useSetMarkup", () => ({
  useSetMarkup: vi.fn(),
}));

import { useSetMarkup } from "../../hooks/useSetMarkup";

// MSW server for job-expense-categories
const server = setupServer(
  http.get("*/api/v1/job-expense-categories", () =>
    HttpResponse.json({
      categories: [
        { code: "materials", label: "Materials" },
        { code: "equipment", label: "Equipment" },
        { code: "permits", label: "Permits" },
      ],
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthContext.Provider value={makeContext()}>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: {
              queries: { retry: false },
              mutations: { retry: false },
            },
          })
        }
      >
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("SetMarkupModal", () => {
  const mockMutate = vi.fn();
  const mockReset = vi.fn();

  beforeEach(() => {
    mockMutate.mockClear();
    mockReset.mockClear();
    vi.mocked(useSetMarkup).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      reset: mockReset,
    } as never);
  });

  it("does not render when open=false", () => {
    render(<SetMarkupModal open={false} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders modal with category dropdown when open=true", () => {
    render(<SetMarkupModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByRole("heading", { name: /set markup/i })).toBeTruthy();
    expect(screen.getByLabelText(/category/i)).toBeTruthy();
  });

  it("category dropdown has fallback options immediately (before API resolves)", () => {
    render(<SetMarkupModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    // Fallback categories are shown synchronously before API response
    const select = screen.getByLabelText(/category/i) as HTMLSelectElement;
    expect(select).toBeTruthy();
    // At least one option must be present (fallback or loaded)
    expect(select.options.length).toBeGreaterThan(0);
  });

  it("submit calls useSetMarkup with { job_expense_category_code, markup_pct }", async () => {
    render(<SetMarkupModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });

    // Wait for the modal to be interactive
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeTruthy();
    });

    fireEvent.change(screen.getByLabelText(/category/i), {
      target: { value: "equipment" },
    });
    fireEvent.change(screen.getByLabelText(/Markup %/i), {
      target: { value: "15" },
    });

    // Submit via form element to avoid button targeting ambiguity
    const form = screen.getByRole("dialog").querySelector("form")!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledOnce();
    });

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        job_expense_category_code: "equipment",
        markup_pct: 15,
      }),
      expect.any(Object),
    );
  });

  it("cancel closes without firing mutation", async () => {
    render(<SetMarkupModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /cancel/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("submit button disabled when markup_pct is empty", async () => {
    render(<SetMarkupModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeTruthy();
    });
    // Find the last button with "Set Markup" text (the submit one)
    const buttons = screen.getAllByRole("button");
    const submitBtn = buttons.find((b) =>
      b.textContent?.toLowerCase().includes("set markup"),
    );
    expect(submitBtn).toBeTruthy();
    expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
  });
});
