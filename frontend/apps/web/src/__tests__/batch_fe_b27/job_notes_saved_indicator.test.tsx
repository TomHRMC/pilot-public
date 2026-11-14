/**
 * FE-B27 — JobNotesTab auto-save indicator tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b27/job_notes_saved_indicator.test.tsx
 *
 * Verifies:
 * - "Blur to save" text is NOT in the DOM (idle state)
 * - "Saved ✓" renders with text-margin-600 class after successful save
 * - Footer hint text updated to "Changes save automatically when you click away."
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JobNotesTab } from "@/features/jobs/components/JobNotesTab";

// Mock hooks — no real API calls in unit tests
vi.mock("@/features/jobs/hooks/useJobNotes", () => ({
  useJobNotes: vi.fn(() => ({
    data: { notes: "Initial notes content" },
    isLoading: false,
  })),
}));

const mockMutate = vi.fn();
vi.mock("@/features/jobs/hooks/useUpdateJobNotes", () => ({
  useUpdateJobNotes: vi.fn(() => ({
    mutate: mockMutate,
    isPending: false,
  })),
}));

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderJobNotes() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <JobNotesTab jobId="job-001" />
    </QueryClientProvider>,
  );
}

describe("JobNotesTab — FE-B27 auto-save indicator (§Task 4)", () => {
  beforeEach(() => {
    mockMutate.mockReset();
  });

  it("does NOT render 'Blur to save' text in idle state", () => {
    renderJobNotes();
    expect(screen.queryByText("Blur to save")).toBeNull();
  });

  it("shows 'Saved ✓' with text-margin-600 class after successful save", async () => {
    // Simulate onSuccess callback being called by mutate
    mockMutate.mockImplementation(
      (_payload: unknown, opts: { onSuccess?: () => void }) => {
        opts?.onSuccess?.();
      },
    );

    renderJobNotes();

    const textarea = screen.getByTestId("job-notes-textarea");
    // Change text to make it differ from initial
    fireEvent.change(textarea, { target: { value: "Updated notes" } });
    fireEvent.blur(textarea);

    await waitFor(() => {
      const savedSpan = screen.getByText("Saved ✓");
      expect(savedSpan).toBeTruthy();
      expect(savedSpan.className).toContain("text-margin-600");
    });
  });

  it("renders updated footer hint text", () => {
    renderJobNotes();
    expect(
      screen.getByText("Changes save automatically when you click away."),
    ).toBeTruthy();
  });

  it("does NOT render old footer hint text", () => {
    renderJobNotes();
    expect(
      screen.queryByText(
        "Notes are saved automatically when you click away from this field.",
      ),
    ).toBeNull();
  });
});
