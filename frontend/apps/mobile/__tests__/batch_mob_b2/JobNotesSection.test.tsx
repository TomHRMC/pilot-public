/**
 * JobNotesSection unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/JobNotesSection.test.tsx
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { JobNotesSection } from "../../features/jobs/components/detail/JobNotesSection";

const mockCreate = jest.fn().mockResolvedValue({});

jest.mock("../../features/offline-sync/hooks/useCreateJobNote", () => ({
  useCreateJobNote: () => ({
    create: mockCreate,
    isPending: false,
    error: null,
  }),
}));

jest.mock("../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

const JOB_ID = "job-today-001";
const USER_ID = "tech-user-001";
const TODAY = new Date().toISOString().slice(0, 10);

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId/notes", () => {
    return HttpResponse.json({
      id: "notes-001",
      tenant_id: "tenant-001",
      job_id: JOB_ID,
      notes: "Found additional wiring issue near panel.",
      audio_object_key: null,
      customer_visible: false,
      client_capture_at: `${TODAY}T09:30:00Z`,
      server_received_at: `${TODAY}T09:30:05Z`,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe("JobNotesSection", () => {
  it("pre-populates text area from API fixture notes", async () => {
    render(
      <JobNotesSection
        jobId={JOB_ID}
        userId={USER_ID}
        testID="notes-section"
      />,
      { wrapper },
    );

    await waitFor(() => {
      const input = screen.getByTestId("job-notes-input");
      expect(input.props.value).toBe(
        "Found additional wiring issue near panel.",
      );
    });
  });

  it("calls create() with jobId, createdBy, and content on Save", async () => {
    render(
      <JobNotesSection
        jobId={JOB_ID}
        userId={USER_ID}
        testID="notes-section"
      />,
      { wrapper },
    );

    // Wait for pre-population
    await waitFor(() => {
      expect(screen.getByTestId("job-notes-input").props.value).toBe(
        "Found additional wiring issue near panel.",
      );
    });

    // Edit the notes
    fireEvent.changeText(
      screen.getByTestId("job-notes-input"),
      "Updated notes for the job.",
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId("save-notes-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId: JOB_ID,
          createdBy: USER_ID,
          content: "Updated notes for the job.",
        }),
      );
    });
  });

  it("handles 404 gracefully — starts with empty text area", async () => {
    server.use(
      http.get("*/api/v1/jobs/:jobId/notes", () => {
        return HttpResponse.json({ detail: "Not found" }, { status: 404 });
      }),
    );

    render(
      <JobNotesSection
        jobId={JOB_ID}
        userId={USER_ID}
        testID="notes-section"
      />,
      { wrapper },
    );

    await waitFor(() => {
      const input = screen.getByTestId("job-notes-input");
      // Empty string or undefined for value — both acceptable for empty state
      expect(input.props.value ?? "").toBe("");
    });
  });
});
