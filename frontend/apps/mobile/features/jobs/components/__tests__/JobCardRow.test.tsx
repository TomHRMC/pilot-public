/**
 * JobCardRow unit tests (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/components/__tests__/JobCardRow.test.tsx
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { JobCardRow } from "../JobCardRow";
import type { JobListItem } from "../../job-types";

function makeJob(overrides: Partial<JobListItem> = {}): JobListItem {
  return {
    id: "job-001",
    tenant_id: "tenant-001",
    customer_id: "cust-abcdef12",
    site_id: "site-001",
    status_id: "status-001",
    status_code: "scheduled",
    customer_name: "Acme Electric",
    scheduled_start_at: "2026-06-05T09:00:00Z",
    scheduled_end_at: "2026-06-05T12:00:00Z",
    estimated_duration_minutes: 180,
    ...overrides,
  };
}

describe("JobCardRow", () => {
  it("renders customer_name when provided", () => {
    render(
      <JobCardRow
        job={makeJob({ customer_name: "Acme Electric" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("Acme Electric")).toBeTruthy();
  });

  it("falls back to truncated customer_id when customer_name is null", () => {
    render(
      <JobCardRow
        job={makeJob({ customer_name: null, customer_id: "abcdef1234567890" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("abcdef12…")).toBeTruthy();
  });

  it("renders scheduled time range", () => {
    render(
      <JobCardRow
        job={makeJob({
          scheduled_start_at: "2026-06-05T09:00:00Z",
          scheduled_end_at: "2026-06-05T12:00:00Z",
        })}
        onPress={() => {}}
      />,
    );
    // Time format depends on locale — just verify it contains AM/PM
    const timeText = screen.getByText(/AM|PM/);
    expect(timeText).toBeTruthy();
  });

  it("renders 'No time set' when scheduled_start_at is null", () => {
    render(
      <JobCardRow
        job={makeJob({ scheduled_start_at: null })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("No time set")).toBeTruthy();
  });

  it("renders Scheduled status pill for 'scheduled' status_code", () => {
    render(
      <JobCardRow
        job={makeJob({ status_code: "scheduled" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("Scheduled")).toBeTruthy();
  });

  it("renders In Progress status pill for 'in_progress' status_code", () => {
    render(
      <JobCardRow
        job={makeJob({ status_code: "in_progress" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("In Progress")).toBeTruthy();
  });

  it("renders Completed status pill for 'completed' status_code", () => {
    render(
      <JobCardRow
        job={makeJob({ status_code: "completed" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("Completed")).toBeTruthy();
  });

  it("renders Unknown for null status_code", () => {
    render(
      <JobCardRow job={makeJob({ status_code: null })} onPress={() => {}} />,
    );
    expect(screen.getByText("Unknown")).toBeTruthy();
  });

  it("renders duration when estimated_duration_minutes is provided", () => {
    render(
      <JobCardRow
        job={makeJob({ estimated_duration_minutes: 180 })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("~3h")).toBeTruthy();
  });

  it("does not render duration when estimated_duration_minutes is null", () => {
    render(
      <JobCardRow
        job={makeJob({ estimated_duration_minutes: null })}
        onPress={() => {}}
      />,
    );
    expect(screen.queryByText(/h$/)).toBeNull();
  });

  it("calls onPress with job.id when tapped", () => {
    const onPress = jest.fn();
    render(<JobCardRow job={makeJob()} onPress={onPress} testID="job-card" />);
    fireEvent.press(screen.getByTestId("job-card"));
    expect(onPress).toHaveBeenCalledWith("job-001");
  });
});
