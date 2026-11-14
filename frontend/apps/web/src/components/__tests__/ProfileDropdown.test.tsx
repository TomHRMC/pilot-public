/**
 * ProfileDropdown — Unit Tests (UI-FIX-2E)
 *
 * Location: apps/web/src/components/__tests__/ProfileDropdown.test.tsx
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { ProfileDropdown } from "../ProfileDropdown";

// ─── Mocks ────────────────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    onClick,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    onClick?: () => void;
    className?: string;
  }) => React.createElement("a", { href, onClick, className }, children),
}));

const mockLogout = vi.fn().mockResolvedValue(undefined);
vi.mock("@/hooks/useLogout", () => ({
  useLogout: () => ({ logout: mockLogout }),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────
function makeAuth(
  overrides?: Partial<AuthContextValue["user"]>,
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "mike@example.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Mike Johnson",
      accessToken: "tok",
      ...overrides,
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderDropdown(auth = makeAuth()) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(
        AuthContext.Provider,
        { value: auth },
        React.createElement(ProfileDropdown),
      ),
    ),
  );
}

beforeEach(() => {
  mockLogout.mockClear();
});

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("ProfileDropdown — UI-FIX-2E", () => {
  describe("Initials computation", () => {
    it("uses first+last letter of displayName when two words present", () => {
      renderDropdown(makeAuth({ displayName: "Mike Johnson" }));
      expect(
        screen.getByRole("button", { name: /profile menu/i }),
      ).toHaveTextContent("MJ");
    });

    it("uses first two letters of displayName when single word", () => {
      renderDropdown(makeAuth({ displayName: "Admin" }));
      expect(
        screen.getByRole("button", { name: /profile menu/i }),
      ).toHaveTextContent("AD");
    });

    it("falls back to first letter of email when displayName is empty", () => {
      renderDropdown(makeAuth({ displayName: "", email: "zack@example.com" }));
      expect(
        screen.getByRole("button", { name: /profile menu/i }),
      ).toHaveTextContent("Z");
    });
  });

  describe("Dropdown open/close", () => {
    it("dropdown is not visible by default", () => {
      renderDropdown();
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("opens dropdown on avatar click", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.getByRole("menu")).toBeInTheDocument();
    });

    it("closes dropdown on second avatar click (toggle)", () => {
      renderDropdown();
      const btn = screen.getByRole("button", { name: /profile menu/i });
      fireEvent.click(btn);
      expect(screen.getByRole("menu")).toBeInTheDocument();
      fireEvent.click(btn);
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("closes dropdown on Escape key", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.getByRole("menu")).toBeInTheDocument();
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("closes dropdown on outside mousedown", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.getByRole("menu")).toBeInTheDocument();
      // Simulate click outside
      fireEvent.mouseDown(document.body);
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });

  describe("Dropdown menu items — FE-UI-NAV-S1: 3 items", () => {
    it("renders My Profile link to /settings/my-account/profile", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      const link = screen.getByText("My Profile").closest("a");
      expect(link).toHaveAttribute("href", "/settings/my-account/profile");
    });

    it("renders Security link to /settings/my-account/security", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      const link = screen.getByText("Security").closest("a");
      expect(link).toHaveAttribute("href", "/settings/my-account/security");
    });

    it("renders Notifications link to /settings/notifications/preferences", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      const link = screen.getByText("Notifications").closest("a");
      expect(link).toHaveAttribute(
        "href",
        "/settings/notifications/preferences",
      );
    });

    it("does NOT render Subscription link (removed in FE-UI-NAV-S1)", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.queryByText("Subscription")).not.toBeInTheDocument();
    });

    it("does NOT render Payment Method link (removed in FE-UI-NAV-S1)", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.queryByText("Payment Method")).not.toBeInTheDocument();
    });

    it("renders Sign Out button", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.getByText("Sign Out")).toBeInTheDocument();
    });
  });

  describe("Sign Out", () => {
    it("calls logout() when Sign Out is clicked", async () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      fireEvent.click(screen.getByText("Sign Out"));
      await waitFor(() => expect(mockLogout).toHaveBeenCalledTimes(1));
    });

    it("closes dropdown when Sign Out is clicked", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      fireEvent.click(screen.getByText("Sign Out"));
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });

  describe("User info display", () => {
    it("shows user displayName in dropdown header", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.getByText("Mike Johnson")).toBeInTheDocument();
    });

    it("shows user email in dropdown header", () => {
      renderDropdown();
      fireEvent.click(screen.getByRole("button", { name: /profile menu/i }));
      expect(screen.getByText("mike@example.com")).toBeInTheDocument();
    });
  });
});
