/**
 * useMyProfile unit tests (MOB-B10)
 *
 * Endpoint verified: GET/PATCH /api/v1/users/me/profile
 * Field names from UserProfileResponse: phone_number, time_zone (not phone/timezone)
 */
import { renderHook, waitFor, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { useMyProfile } from "../../features/account-settings/hooks/useMyProfile";

// ── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("../../database", () => ({
  database: {
    write: jest.fn((fn: () => unknown) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: (r: Record<string, unknown>) => void) => {
        const record = { id: "mock-id", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

// ── Mock data ───────────────────────────────────────────────────────────────

const MOCK_PROFILE = {
  id: "00000000-0000-0000-0000-000000000001",
  first_name: "Tom",
  last_name: "Owner",
  email: "dev@pilot.local",
  phone_number: "+13035550001",
  time_zone: "America/Denver",
  profile_photo_s3_key: null,
  language_preference: "en",
};

// ── Server ──────────────────────────────────────────────────────────────────

let lastPatchBody: Record<string, unknown> | null = null;

const server = setupServer(
  http.get("*/api/v1/users/me/profile", () => HttpResponse.json(MOCK_PROFILE)),
  http.patch("*/api/v1/users/me/profile", async ({ request }) => {
    lastPatchBody = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...MOCK_PROFILE, ...lastPatchBody });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  lastPatchBody = null;
});
afterAll(() => server.close());

// ── Wrapper ─────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("useMyProfile", () => {
  it("loads profile from GET /api/v1/users/me/profile — returns first_name and email", async () => {
    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.profile?.first_name).toBe("Tom");
    expect(result.current.profile?.email).toBe("dev@pilot.local");
  });

  it("updateField('first_name', 'Thomas') fires PATCH with { first_name: 'Thomas' }", async () => {
    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.updateField("first_name", "Thomas");
    });

    expect(lastPatchBody).toEqual({ first_name: "Thomas" });
  });

  it("updateField('phone_number', null) fires PATCH with { phone_number: null }", async () => {
    const { result } = renderHook(() => useMyProfile(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.updateField("phone_number", null);
    });

    expect(lastPatchBody).toEqual({ phone_number: null });
  });
});
