/**
 * FieldIssueRow unit tests — FE-B9
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { FieldIssueRow } from "./FieldIssueRow";
import type { FieldIssueQueueItem } from "../types";

const pendingIssue: FieldIssueQueueItem = {
  id: "fi-1",
  status: "pending",
  operationType: "time_entry",
  techId: "tech-1",
  techName: "Jake Torres",
  capturedAt: "2026-05-25T14:30:00Z",
  escalatedAt: "2026-05-25T14:31:00Z",
  explainerSummary: "Time entry conflict: both sides modified",
  conflictType: "modified_modified",
};

describe("FieldIssueRow", () => {
  it("renders tech name", () => {
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={pendingIssue} />
        </tbody>
      </table>,
    );
    expect(screen.getByText("Jake Torres")).toBeInTheDocument();
  });

  it("renders operation type pill with label", () => {
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={pendingIssue} />
        </tbody>
      </table>,
    );
    expect(screen.getByText("Time entry")).toBeInTheDocument();
  });

  it("renders 'Pending' status pill with correct token class", () => {
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={pendingIssue} />
        </tbody>
      </table>,
    );
    const pill = screen.getByTestId("status-pill-pending");
    expect(pill).toBeInTheDocument();
    expect(pill).toHaveTextContent("Pending");
    expect(pill.className).toContain("bg-alert-100");
    expect(pill.className).toContain("text-alert-700");
  });

  it("renders 'Auto-recovered' status pill with correct token class", () => {
    const autoRecoveredIssue = {
      ...pendingIssue,
      status: "auto_recovered" as const,
    };
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={autoRecoveredIssue} />
        </tbody>
      </table>,
    );
    const pill = screen.getByTestId("status-pill-auto_recovered");
    expect(pill).toHaveTextContent("Auto-recovered");
    expect(pill.className).toContain("bg-margin-100");
    expect(pill.className).toContain("text-margin-700");
  });

  it("renders 'Stale' status pill with correct token class", () => {
    const staleIssue = { ...pendingIssue, status: "stale" as const };
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={staleIssue} />
        </tbody>
      </table>,
    );
    const pill = screen.getByTestId("status-pill-stale");
    expect(pill).toHaveTextContent("Stale");
    expect(pill.className).toContain("bg-neutral-100");
  });

  it("renders 'Resolve →' link for pending issues", () => {
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={pendingIssue} />
        </tbody>
      </table>,
    );
    const link = screen.getByTestId("resolve-link-fi-1");
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute(
      "href",
      "/dashboard/approvals/field-issues/fi-1",
    );
  });

  it("renders 'View' link for non-pending issues", () => {
    const resolvedIssue = {
      ...pendingIssue,
      status: "auto_recovered" as const,
    };
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={resolvedIssue} />
        </tbody>
      </table>,
    );
    expect(screen.getByTestId("view-link-fi-1")).toBeInTheDocument();
  });

  it("renders explainer summary", () => {
    render(
      <table>
        <tbody>
          <FieldIssueRow issue={pendingIssue} />
        </tbody>
      </table>,
    );
    expect(screen.getByText(/Time entry conflict/)).toBeInTheDocument();
  });
});
