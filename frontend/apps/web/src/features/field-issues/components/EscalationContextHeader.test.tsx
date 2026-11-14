/**
 * EscalationContextHeader unit tests — FE-B9
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { EscalationContextHeader } from "./EscalationContextHeader";
import { timeEntryModifiedModifiedDetail } from "../mocks/fieldIssuesFixtures";

describe("EscalationContextHeader", () => {
  it("renders explainer copy VERBATIM from server (RULE 4)", () => {
    render(<EscalationContextHeader issue={timeEntryModifiedModifiedDetail} />);
    expect(screen.getByTestId("explainer-copy")).toHaveTextContent(
      timeEntryModifiedModifiedDetail.explainerCopy,
    );
  });

  it("renders tech identity row with tech name", () => {
    render(<EscalationContextHeader issue={timeEntryModifiedModifiedDetail} />);
    expect(screen.getByTestId("tech-identity-row")).toBeInTheDocument();
    expect(screen.getByText("Jake Torres")).toBeInTheDocument();
  });

  it("renders last-active time when techLastActiveAt is set", () => {
    render(<EscalationContextHeader issue={timeEntryModifiedModifiedDetail} />);
    expect(screen.getByText(/Last active/)).toBeInTheDocument();
  });

  it("renders collapsed timestamp details by default", () => {
    render(<EscalationContextHeader issue={timeEntryModifiedModifiedDetail} />);
    expect(screen.queryByTestId("timestamps-detail")).not.toBeInTheDocument();
  });

  it("expands timestamp details on toggle click", () => {
    render(<EscalationContextHeader issue={timeEntryModifiedModifiedDetail} />);
    fireEvent.click(screen.getByTestId("timestamps-toggle"));
    expect(screen.getByTestId("timestamps-detail")).toBeInTheDocument();
  });

  it("renders capturedAt, syncAttemptedAt, escalatedAt in expanded view", () => {
    render(<EscalationContextHeader issue={timeEntryModifiedModifiedDetail} />);
    fireEvent.click(screen.getByTestId("timestamps-toggle"));
    expect(screen.getByText("Captured offline")).toBeInTheDocument();
    expect(screen.getByText("Sync attempted")).toBeInTheDocument();
    expect(screen.getByText("Escalated")).toBeInTheDocument();
  });

  it("renders tech initials as avatar", () => {
    render(<EscalationContextHeader issue={timeEntryModifiedModifiedDetail} />);
    expect(screen.getByText("JT")).toBeInTheDocument(); // Jake Torres initials
  });
});
