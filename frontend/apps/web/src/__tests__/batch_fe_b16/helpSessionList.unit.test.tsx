/**
 * Help session list unit tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/helpSessionList.unit.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { HelpSessionListItem } from "../../features/help/components/HelpSessionListItem";
import { groupSessionsByRecency } from "../../features/help/hooks/useHelpSessions";
import type { HelpSessionSummary } from "../../features/help/types";

const NOW = Date.now();
const ONE_HOUR = 1000 * 60 * 60;

const todaySession: HelpSessionSummary = {
  session_id: "s-today",
  title: "Today session",
  started_at: new Date(NOW - ONE_HOUR).toISOString(),
  last_activity_at: new Date(NOW - ONE_HOUR).toISOString(),
  message_count: 3,
  outcome: "resolved",
};

const weekSession: HelpSessionSummary = {
  session_id: "s-week",
  title: "Week session",
  started_at: new Date(NOW - ONE_HOUR * 24 * 3).toISOString(),
  last_activity_at: new Date(NOW - ONE_HOUR * 24 * 3).toISOString(),
  message_count: 5,
  outcome: null,
};

const oldSession: HelpSessionSummary = {
  session_id: "s-old",
  title: "Old session",
  started_at: new Date(NOW - ONE_HOUR * 24 * 14).toISOString(),
  last_activity_at: new Date(NOW - ONE_HOUR * 24 * 14).toISOString(),
  message_count: 2,
  outcome: "escalated",
};

describe("groupSessionsByRecency", () => {
  it("groups today's session under Today", () => {
    const groups = groupSessionsByRecency([todaySession]);
    expect(groups[0].label).toBe("Today");
    expect(groups[0].sessions).toContain(todaySession);
  });

  it("groups 3-day-old session under Last 7 days", () => {
    const groups = groupSessionsByRecency([weekSession]);
    expect(groups[0].label).toBe("Last 7 days");
    expect(groups[0].sessions).toContain(weekSession);
  });

  it("groups 14-day-old session under Older", () => {
    const groups = groupSessionsByRecency([oldSession]);
    expect(groups[0].label).toBe("Older");
    expect(groups[0].sessions).toContain(oldSession);
  });

  it("returns empty array for no sessions", () => {
    expect(groupSessionsByRecency([])).toHaveLength(0);
  });
});

describe("HelpSessionListItem", () => {
  it("renders session title", () => {
    render(
      <HelpSessionListItem
        session={todaySession}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("Today session")).toBeInTheDocument();
  });

  it("renders message count", () => {
    render(
      <HelpSessionListItem
        session={todaySession}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/3 messages/)).toBeInTheDocument();
  });

  it("calls onSelect with session_id when clicked", () => {
    const onSelect = vi.fn();
    render(
      <HelpSessionListItem
        session={todaySession}
        onSelect={onSelect}
        onDelete={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("help-session-item-s-today"));
    expect(onSelect).toHaveBeenCalledWith("s-today");
  });

  it("calls onDelete with session_id when delete button is clicked", () => {
    const onDelete = vi.fn();
    render(
      <HelpSessionListItem
        session={todaySession}
        onSelect={vi.fn()}
        onDelete={onDelete}
      />,
    );
    fireEvent.click(screen.getByTestId("help-session-delete-s-today"));
    expect(onDelete).toHaveBeenCalledWith("s-today");
  });
});
