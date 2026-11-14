/**
 * SetLaborRateModal Unit Tests — FE-B20
 *
 * Location: apps/web/src/features/catalog/components/__tests__/SetLaborRateModal.test.tsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { SetLaborRateModal } from "../SetLaborRateModal";

// Mock the hook
vi.mock("../../hooks/useSetLaborRate", () => ({
  useSetLaborRate: vi.fn(),
}));

import { useSetLaborRate } from "../../hooks/useSetLaborRate";

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

describe("SetLaborRateModal", () => {
  const mockMutate = vi.fn();
  const mockReset = vi.fn();

  beforeEach(() => {
    mockMutate.mockClear();
    mockReset.mockClear();
    vi.mocked(useSetLaborRate).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      reset: mockReset,
    } as never);
  });

  it("does not render when open=false", () => {
    render(<SetLaborRateModal open={false} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders with skill level dropdown showing 3 seeded options", () => {
    render(<SetLaborRateModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    expect(screen.getByRole("dialog")).toBeTruthy();
    const select = screen.getByLabelText(/skill level/i) as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toContain("master");
    expect(options).toContain("journeyman");
    expect(options).toContain("apprentice");
  });

  it("shows burdened rate preview when hourly rate and burden are entered", () => {
    render(<SetLaborRateModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });

    fireEvent.change(screen.getByLabelText(/Hourly Rate/i), {
      target: { value: "100" },
    });
    fireEvent.change(screen.getByLabelText(/Burden %/i), {
      target: { value: "15" },
    });

    // Burdened rate = 100 * (1 + 0.15) = 115.00
    expect(screen.getByText(/\$115\.00\/hr/i)).toBeInTheDocument();
  });

  it("submit calls useSetLaborRate with correct payload", () => {
    render(<SetLaborRateModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });

    fireEvent.change(screen.getByLabelText(/skill level/i), {
      target: { value: "journeyman" },
    });
    fireEvent.change(screen.getByLabelText(/Hourly Rate/i), {
      target: { value: "85" },
    });
    fireEvent.change(screen.getByLabelText(/Burden %/i), {
      target: { value: "15" },
    });

    fireEvent.click(screen.getByRole("button", { name: /set rate/i }));

    expect(mockMutate).toHaveBeenCalledOnce();
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        skill_level_code: "journeyman",
        hourly_rate_cents: 8500,
        burden_pct: 0.15,
      }),
      expect.any(Object),
    );
  });

  it("cancel closes without firing mutation", () => {
    render(<SetLaborRateModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("submit button disabled when hourly rate is empty", () => {
    render(<SetLaborRateModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    const submitBtn = screen.getByRole("button", { name: /set rate/i });
    expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
  });
});
