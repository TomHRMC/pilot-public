/**
 * EscalationResolutionOutcome unit tests — FE-B9
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { EscalationResolutionOutcome } from "./EscalationResolutionOutcome";

describe("EscalationResolutionOutcome", () => {
  it("renders resolved_in_favor_of_tech state correctly", () => {
    render(
      <EscalationResolutionOutcome
        outcome="resolved_in_favor_of_tech"
        techName="Jake Torres"
      />,
    );
    expect(
      screen.getByTestId("escalation-outcome-resolved_in_favor_of_tech"),
    ).toBeOnTheScreen();
    expect(screen.getByText("Your data was kept")).toBeOnTheScreen();
    expect(screen.getByText(/committed your version/i)).toBeOnTheScreen();
  });

  it("renders resolved_in_favor_of_server state with 24-hour dismissal copy", () => {
    render(
      <EscalationResolutionOutcome
        outcome="resolved_in_favor_of_server"
        techName="Rosa Medina"
      />,
    );
    expect(
      screen.getByTestId("escalation-outcome-resolved_in_favor_of_server"),
    ).toBeOnTheScreen();
    expect(screen.getByText("Server version accepted")).toBeOnTheScreen();
    expect(screen.getByText(/24 hours/i)).toBeOnTheScreen();
  });

  it("renders resolved_with_action state with job-restored context", () => {
    render(
      <EscalationResolutionOutcome
        outcome="resolved_with_action"
        techName="Chris Okafor"
        jobTitle="Panel Upgrade — Ruiz"
      />,
    );
    expect(
      screen.getByTestId("escalation-outcome-resolved_with_action"),
    ).toBeOnTheScreen();
    expect(screen.getByText("Action taken — job restored")).toBeOnTheScreen();
    expect(screen.getByText(/Panel Upgrade — Ruiz/)).toBeOnTheScreen();
  });

  it("calls onDismiss when dismiss button is tapped", () => {
    const mockDismiss = jest.fn();
    render(
      <EscalationResolutionOutcome
        outcome="resolved_in_favor_of_tech"
        techName="Jake Torres"
        onDismiss={mockDismiss}
      />,
    );
    fireEvent.press(screen.getByTestId("escalation-outcome-dismiss"));
    expect(mockDismiss).toHaveBeenCalledTimes(1);
  });

  it("does NOT render dismiss button when onDismiss is not provided", () => {
    render(
      <EscalationResolutionOutcome
        outcome="resolved_in_favor_of_tech"
        techName="Jake Torres"
      />,
    );
    expect(
      screen.queryByTestId("escalation-outcome-dismiss"),
    ).not.toBeOnTheScreen();
  });

  it("renders operation type tag when provided", () => {
    render(
      <EscalationResolutionOutcome
        outcome="resolved_in_favor_of_tech"
        techName="Jake Torres"
        operationType="time_entry"
      />,
    );
    expect(screen.getByText("time entry")).toBeOnTheScreen();
  });
});
