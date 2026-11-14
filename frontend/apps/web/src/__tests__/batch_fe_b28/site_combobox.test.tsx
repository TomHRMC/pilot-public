/**
 * FE-B28 — SiteCombobox unit tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/site_combobox.test.tsx
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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
import { SiteCombobox } from "@/components/SiteCombobox";

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
  customerId: string | null;
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
        <SiteCombobox {...props} />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("SiteCombobox — FE-B28", () => {
  it("renders as disabled when customerId is null", () => {
    const onChange = vi.fn();
    renderCombobox({ customerId: null, value: "", onChange });
    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("shows 'Select a customer first' placeholder when customerId is null", () => {
    const onChange = vi.fn();
    renderCombobox({ customerId: null, value: "", onChange });
    expect(
      screen.getByPlaceholderText("Select a customer first"),
    ).toBeInTheDocument();
  });

  it("enables when customerId is provided", async () => {
    const onChange = vi.fn();
    renderCombobox({
      customerId: "c-00000001-0000-0000-0000-000000000001",
      value: "",
      onChange,
    });
    const input = screen.getByRole("combobox");
    await waitFor(() => {
      expect(input).not.toBeDisabled();
    });
  });

  it("renders combobox input field", () => {
    const onChange = vi.fn();
    renderCombobox({ customerId: null, value: "", onChange });
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("shows clear button when value is set and customerId is provided", async () => {
    const onChange = vi.fn();
    renderCombobox({
      customerId: "c-00000001-0000-0000-0000-000000000001",
      value: "some-site-id",
      onChange,
    });
    await waitFor(() => {
      expect(screen.getByLabelText("Clear site selection")).toBeInTheDocument();
    });
  });
});
