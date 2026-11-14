/**
 * Push notification loop closure integration test — FE-B9
 *
 * Tests: escalation_resolved push → SyncOrchestrator.pull() called → cache invalidated
 */

import {
  handleEscalationResolutionPush,
  type EscalationResolutionPushPayload,
} from "../../features/offline-sync/notifications/escalationResolutionHandler";
import { QueryClient } from "@tanstack/react-query";

// Mock SyncOrchestrator
const mockPull = jest.fn().mockResolvedValue({ updated: 2 });
const mockOrchestrator = { pull: mockPull } as never;

describe("escalationResolutionHandler", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    mockPull.mockClear();
  });

  it("calls SyncOrchestrator.pull() on escalation_resolved push", async () => {
    const payload: EscalationResolutionPushPayload = {
      type: "escalation_resolved",
      issue_id: "fi-time-001",
      resolution: "resolved_in_favor_of_tech",
    };

    await handleEscalationResolutionPush(
      payload,
      mockOrchestrator,
      queryClient,
    );

    expect(mockPull).toHaveBeenCalledTimes(1);
  });

  it("invalidates field-issues-summary query after pull", async () => {
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
    const payload: EscalationResolutionPushPayload = {
      type: "escalation_resolved",
      issue_id: "fi-time-001",
      resolution: "resolved_in_favor_of_server",
    };

    await handleEscalationResolutionPush(
      payload,
      mockOrchestrator,
      queryClient,
    );

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["field-issues-summary"] }),
    );
  });

  it("invalidates field-issues query after pull", async () => {
    const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");
    const payload: EscalationResolutionPushPayload = {
      type: "escalation_resolved",
      issue_id: "fi-time-001",
      resolution: "resolved_with_action",
      job_id: "job-001",
    };

    await handleEscalationResolutionPush(
      payload,
      mockOrchestrator,
      queryClient,
    );

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["field-issues"] }),
    );
  });

  it("does NOT call pull() for non-escalation_resolved push type", async () => {
    const payload = { type: "other_event" } as never;
    await handleEscalationResolutionPush(
      payload,
      mockOrchestrator,
      queryClient,
    );
    expect(mockPull).not.toHaveBeenCalled();
  });

  it("does NOT throw when SyncOrchestrator.pull() fails", async () => {
    mockPull.mockRejectedValueOnce(new Error("Network error"));
    const payload: EscalationResolutionPushPayload = {
      type: "escalation_resolved",
      issue_id: "fi-1",
      resolution: "resolved_in_favor_of_tech",
    };

    // Should not throw
    await expect(
      handleEscalationResolutionPush(payload, mockOrchestrator, queryClient),
    ).resolves.not.toThrow();
  });
});
