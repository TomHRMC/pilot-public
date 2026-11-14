/**
 * useDispatchBoard — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/hooks/__tests__/useDispatchBoard.test.ts
 * Per batch-beta-v1-fixes-b5-design.md §I.1
 *
 * Verifies:
 * - Single-day call (startDate === endDate) — correct query params
 * - 4-day range — correct end_date (+3 days)
 * - Different endDate → different query key
 *
 * DISPATCH-B1.25:
 * - Commitments are carried per tech and are NOT present in the flattened jobs[].
 */

import { describe, it, expect, afterEach, beforeAll, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import {
  DISPATCH_BOARD_QUERY_KEY,
  useDispatchBoard,
} from "../useDispatchBoard";
import { MOCK_DISPATCH_BOARD_RESPONSE_B1 } from "@/mocks/handlers/dispatchBoardHandlers";

const TODAY = new Date().toISOString().slice(0, 10);

// ─── MSW server for hook tests ────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/scheduling/dispatch-board", () =>
    HttpResponse.json(MOCK_DISPATCH_BOARD_RESPONSE_B1()),
  ),
  http.get("/api/v1/jobs/", () =>
    HttpResponse.json({ items: [], total: 0, limit: 200, offset: 0 }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("DISPATCH_BOARD_QUERY_KEY", () => {
  it("produces a tuple with both dates", () => {
    const key = DISPATCH_BOARD_QUERY_KEY("2026-06-10", "2026-06-10");
    expect(key).toEqual(["dispatch-board", "2026-06-10", "2026-06-10"]);
  });

  it("single-day: startDate equals endDate — query key contains both", () => {
    const key = DISPATCH_BOARD_QUERY_KEY("2026-06-10", "2026-06-10");
    expect(key[1]).toBe("2026-06-10");
    expect(key[2]).toBe("2026-06-10");
  });

  it("4-day range: endDate is startDate+3 — distinct query key", () => {
    const singleKey = DISPATCH_BOARD_QUERY_KEY("2026-06-10", "2026-06-10");
    const fourDayKey = DISPATCH_BOARD_QUERY_KEY("2026-06-10", "2026-06-13");
    expect(fourDayKey[2]).toBe("2026-06-13");
    // Different endDate → different key → separate cache entry
    expect(fourDayKey).not.toEqual(singleKey);
  });

  it("week range: endDate is startDate+6 — distinct query key from 4-day", () => {
    const fourDayKey = DISPATCH_BOARD_QUERY_KEY("2026-06-10", "2026-06-13");
    const weekKey = DISPATCH_BOARD_QUERY_KEY("2026-06-10", "2026-06-16");
    expect(weekKey[2]).toBe("2026-06-16");
    expect(weekKey).not.toEqual(fourDayKey);
  });
});

// ─── DISPATCH-B1.25: commitment separation tests ──────────────────────────────

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return Wrapper;
}

describe("useDispatchBoard — DISPATCH-B1.25 commitment separation", () => {
  it("commitment job ID is NOT duplicated in flattened jobs[]", async () => {
    // Maria Santos has job-b30-001 as a commitment (helper) — Jake has it as primary.
    // jobs[] should contain job-b30-001 exactly once (primary only).
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const jobs = result.current.data!.jobs;
    const commitmentJobEntries = jobs.filter((j) => j.id === "job-b30-001");
    // Exactly one primary entry — NOT doubled by Maria's commitment
    expect(commitmentJobEntries).toHaveLength(1);
  });

  it("tech with commitments has commitments[] on its normalized tech object", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Maria Santos (tech-00000002) should have commitments
    const mariaTech = result.current.data!.techs.find(
      (t) => t.id === "tech-00000002-0000-0000-0000-000000000002",
    );
    expect(mariaTech).toBeDefined();
    expect(mariaTech!.commitments).toBeDefined();
    expect(mariaTech!.commitments!.length).toBeGreaterThan(0);

    // The commitment entry should carry assignment_role = "helper"
    const commitment = mariaTech!.commitments![0];
    expect(
      (commitment as unknown as { assignment_role?: string }).assignment_role,
    ).toBe("helper");
  });

  it("commitment-only tech (Alex Park) appears in techs[] with non-empty commitments", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Alex Park (tech-00000003) has no primary jobs, only commitments
    const alexTech = result.current.data!.techs.find(
      (t) => t.id === "tech-00000003-0000-0000-0000-000000000003",
    );
    expect(alexTech).toBeDefined();
    expect(alexTech!.commitments).toBeDefined();
    expect(alexTech!.commitments!.length).toBeGreaterThan(0);
  });

  it("Alex Park commitment job ID is NOT in jobs[] under Alex's tech_id", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const alexTech = result.current.data!.techs.find(
      (t) => t.id === "tech-00000003-0000-0000-0000-000000000003",
    );
    expect(alexTech).toBeDefined();

    const alexCommitmentJobIds = alexTech!.commitments!.map((c) => c.id);
    const jobsFlat = result.current.data!.jobs;

    for (const commitJobId of alexCommitmentJobIds) {
      const inJobsFlatUnderAlex = jobsFlat.some(
        (j) => j.id === commitJobId && j.tech_id === alexTech!.id,
      );
      expect(inJobsFlatUnderAlex).toBe(false);
    }
  });

  it("assignment_role 'primary' is carried on Jake's primary jobs", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Jake's primary job should have assignment_role = "primary"
    const jakeJob = result.current.data!.jobs.find(
      (j) => j.id === "job-b30-001",
    );
    expect(jakeJob).toBeDefined();
    expect(
      (jakeJob as unknown as { assignment_role?: string }).assignment_role,
    ).toBe("primary");
  });
});
