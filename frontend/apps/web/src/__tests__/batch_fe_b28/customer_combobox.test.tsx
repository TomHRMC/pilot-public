/**
 * FE-B28 — CustomerCombobox unit tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/customer_combobox.test.tsx
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { setupServer } from "msw/node";
import { handlers } from "../../mocks/handlers/index";
import { CustomerCombobox } from "@/components/CustomerCombobox";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
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

function renderCombobox(props: {
  value: string;
  onChange: (id: string) => void;
}) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthContext()}>
      <QueryClientProvider client={qc}>
        <CustomerCombobox {...props} />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("CustomerCombobox — FE-B28", () => {
  it("renders input field", async () => {
    const onChange = vi.fn();
    renderCombobox({ value: "", onChange });
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("shows customer list on focus after loading", async () => {
    const onChange = vi.fn();
    renderCombobox({ value: "", onChange });
    const input = screen.getByRole("combobox");
    await waitFor(() => expect(input).not.toBeDisabled());
    fireEvent.focus(input);
    await waitFor(() => {
      // MOCK_CUSTOMERS from customerHandlers.ts has "Smith Electrical"
      expect(screen.getByText("Smith Electrical")).toBeInTheDocument();
    });
  });

  it("filters list when user types", async () => {
    const onChange = vi.fn();
    renderCombobox({ value: "", onChange });
    const input = screen.getByRole("combobox");
    await waitFor(() => expect(input).not.toBeDisabled());
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "Smith" } });
    await waitFor(() => {
      expect(screen.getByText("Smith Electrical")).toBeInTheDocument();
    });
    expect(screen.queryByText("Johnson Home Services")).not.toBeInTheDocument();
  });

  it("calls onChange with customer_id on selection", async () => {
    const onChange = vi.fn();
    renderCombobox({ value: "", onChange });
    const input = screen.getByRole("combobox");
    await waitFor(() => expect(input).not.toBeDisabled());
    fireEvent.focus(input);
    await waitFor(() => {
      expect(screen.getByText("Smith Electrical")).toBeInTheDocument();
    });
    fireEvent.mouseDown(screen.getByText("Smith Electrical"));
    expect(onChange).toHaveBeenCalledWith(
      "c-00000001-0000-0000-0000-000000000001",
    );
  });

  it("shows 'No customers found' when filter returns 0 results", async () => {
    const onChange = vi.fn();
    renderCombobox({ value: "", onChange });
    const input = screen.getByRole("combobox");
    await waitFor(() => expect(input).not.toBeDisabled());
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "ZZZNOMATCH" } });
    await waitFor(() => {
      expect(screen.getByText("No customers found")).toBeInTheDocument();
    });
  });

  it("shows clear button when value is set", async () => {
    const onChange = vi.fn();
    renderCombobox({
      value: "c-00000001-0000-0000-0000-000000000001",
      onChange,
    });
    await waitFor(() => {
      expect(screen.getByLabelText("Clear selection")).toBeInTheDocument();
    });
  });

  it("calls onChange('') when clear button clicked", async () => {
    const onChange = vi.fn();
    renderCombobox({
      value: "c-00000001-0000-0000-0000-000000000001",
      onChange,
    });
    const clearBtn = await screen.findByLabelText("Clear selection");
    fireEvent.click(clearBtn);
    expect(onChange).toHaveBeenCalledWith("");
  });
});
