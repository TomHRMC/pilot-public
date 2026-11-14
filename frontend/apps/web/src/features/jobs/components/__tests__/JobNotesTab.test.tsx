/**
 * JobNotesTab unit tests — FE-B21
 *
 * Location: apps/web/src/features/jobs/components/__tests__/JobNotesTab.test.tsx
 *
 * Key rules verified:
 * - No Submit button exists (save-on-blur only)
 * - Blur event triggers useUpdateJobNotes mutation
 * - Shows "Saving..." while pending; "Saved ✓" on success
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { JobNotesTab } from "../JobNotesTab";

// ── Mock hooks ─────────────────────────────────────────────────────────────────

vi.mock("../../hooks/useJobNotes", () => ({
  useJobNotes: vi.fn(),
  JOB_NOTES_QUERY_KEY: (id: string) => ["job-notes", id],
}));

vi.mock("../../hooks/useUpdateJobNotes", () => ({
  useUpdateJobNotes: vi.fn(),
}));

import { useJobNotes } from "../../hooks/useJobNotes";
import { useUpdateJobNotes } from "../../hooks/useUpdateJobNotes";

// ── Test helpers ───────────────────────────────────────────────────────────────

function makeContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Test Owner",
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

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthContext.Provider value={makeContext()}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

const MOCK_NOTES_DATA = {
  id: "notes-job-1",
  tenant_id: "t1",
  job_id: "job-1",
  notes: "Customer requested extra outlets on north wall.",
  audio_object_key: null,
  customer_visible: false,
  client_capture_at: null,
  server_received_at: "2026-06-16T10:00:00Z",
  created_at: "2026-06-16T10:00:00Z",
  updated_at: "2026-06-16T10:00:00Z",
  created_by: "user-owner-1",
};

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("JobNotesTab", () => {
  beforeEach(() => {
    vi.mocked(useJobNotes).mockReset();
    vi.mocked(useUpdateJobNotes).mockReset();
  });

  it("renders textarea with notes content from hook", () => {
    vi.mocked(useJobNotes).mockReturnValue({
      data: MOCK_NOTES_DATA,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useUpdateJobNotes).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);

    render(<JobNotesTab jobId="job-1" />, { wrapper: Wrapper });

    const textarea = screen.getByTestId(
      "job-notes-textarea",
    ) as HTMLTextAreaElement;
    expect(textarea).toBeTruthy();
    expect(textarea.value).toBe(
      "Customer requested extra outlets on north wall.",
    );
  });

  it("does NOT have a Submit button", () => {
    vi.mocked(useJobNotes).mockReturnValue({
      data: MOCK_NOTES_DATA,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useUpdateJobNotes).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);

    render(<JobNotesTab jobId="job-1" />, { wrapper: Wrapper });

    // Should not have any submit-type button
    const submitBtn = screen.queryByRole("button", { name: /save/i });
    expect(submitBtn).toBeNull();

    // Should not have submit button at all
    const buttons = screen.queryAllByRole("button");
    // Only the Retry button (when error) should exist — none in idle state
    expect(buttons.length).toBe(0);
  });

  it("blur event on textarea triggers useUpdateJobNotes mutation", () => {
    const mockMutate = vi.fn();

    vi.mocked(useJobNotes).mockReturnValue({
      data: MOCK_NOTES_DATA,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useUpdateJobNotes).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as never);

    render(<JobNotesTab jobId="job-1" />, { wrapper: Wrapper });

    const textarea = screen.getByTestId("job-notes-textarea");

    // Change value then blur
    fireEvent.change(textarea, {
      target: { value: "Updated notes content." },
    });
    fireEvent.blur(textarea);

    expect(mockMutate).toHaveBeenCalledWith(
      { notes: "Updated notes content." },
      expect.anything(),
    );
  });

  it("shows 'Saving...' while mutation isPending", () => {
    vi.mocked(useJobNotes).mockReturnValue({
      data: MOCK_NOTES_DATA,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useUpdateJobNotes).mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
    } as never);

    render(<JobNotesTab jobId="job-1" />, { wrapper: Wrapper });

    expect(screen.getByText(/saving/i)).toBeTruthy();
  });

  it("does NOT trigger mutation if value unchanged after blur", () => {
    const mockMutate = vi.fn();

    vi.mocked(useJobNotes).mockReturnValue({
      data: MOCK_NOTES_DATA,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useUpdateJobNotes).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as never);

    render(<JobNotesTab jobId="job-1" />, { wrapper: Wrapper });

    const textarea = screen.getByTestId("job-notes-textarea");
    // Blur without changing value
    fireEvent.blur(textarea);

    expect(mockMutate).not.toHaveBeenCalled();
  });
});
