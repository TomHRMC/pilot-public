/**
 * CreateCustomerModal unit tests — FE-B18
 *
 * Location: apps/web/src/features/customers/components/__tests__/CreateCustomerModal.test.tsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { CreateCustomerModal } from "../CreateCustomerModal";

// Mock useCreateCustomer
vi.mock("../../hooks/useCreateCustomer", () => ({
  useCreateCustomer: vi.fn(),
}));

import { useCreateCustomer } from "../../hooks/useCreateCustomer";

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

describe("CreateCustomerModal", () => {
  beforeEach(() => {
    vi.mocked(useCreateCustomer).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      reset: vi.fn(),
    } as never);
  });

  it("does not render when open=false", () => {
    render(<CreateCustomerModal open={false} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders modal with form when open=true", () => {
    render(<CreateCustomerModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    expect(screen.getByRole("dialog")).toBeTruthy();
    // Use heading role to disambiguate from the submit button "Add Customer" text
    expect(screen.getByRole("heading", { name: /add customer/i })).toBeTruthy();
    expect(screen.getByLabelText(/display name/i)).toBeTruthy();
  });

  it("calls onClose when backdrop clicked", () => {
    const onClose = vi.fn();
    render(<CreateCustomerModal open={true} onClose={onClose} />, {
      wrapper: Wrapper,
    });
    // Click the backdrop (aria-hidden overlay)
    const backdrop = document.querySelector('[aria-hidden="true"]')!;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when X button clicked", () => {
    const onClose = vi.fn();
    render(<CreateCustomerModal open={true} onClose={onClose} />, {
      wrapper: Wrapper,
    });
    fireEvent.click(screen.getByLabelText(/close modal/i));
    expect(onClose).toHaveBeenCalled();
  });

  it("submit button disabled when display_name is empty", () => {
    render(<CreateCustomerModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    const submit = screen.getByTestId("customer-form-submit");
    expect((submit as HTMLButtonElement).disabled).toBe(true);
  });

  it("calls useCreateCustomer.mutate when form submitted", () => {
    const mutate = vi.fn();
    vi.mocked(useCreateCustomer).mockReturnValue({
      mutate,
      isPending: false,
      reset: vi.fn(),
    } as never);

    render(<CreateCustomerModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });

    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "New Customer" },
    });
    fireEvent.click(screen.getByTestId("customer-form-submit"));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ display_name: "New Customer" }),
      expect.any(Object),
    );
  });

  it("shows submitting state when isPending=true", () => {
    vi.mocked(useCreateCustomer).mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
      reset: vi.fn(),
    } as never);

    render(<CreateCustomerModal open={true} onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });
    expect(screen.getByTestId("customer-form-submit").textContent).toContain(
      "Saving",
    );
  });
});
