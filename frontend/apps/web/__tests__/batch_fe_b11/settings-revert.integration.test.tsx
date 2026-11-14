/**
 * Settings revert integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import {
  settingsHandlers,
  setSettingsScenario,
  resetSettingsScenario,
} from "../../src/features/settings/mocks/settingsHandlers";
import { ProfitabilityRulesPage } from "../../src/features/settings-operations/components/ProfitabilityRulesPage";
import { createSettingsWrapper } from "../test-utils/settingsWrapper";

const server = setupServer(...settingsHandlers);

beforeEach(() => {
  server.listen({ onUnhandledRequest: "bypass" });
  setSettingsScenario("tenant-overrides");
});
afterEach(() => {
  server.resetHandlers();
  server.close();
  resetSettingsScenario();
});

describe("Settings revert flow", () => {
  it("shows revert link when scope=tenant", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() =>
      expect(screen.getByTestId("etc-variance-input-revert-link")).toBeTruthy(),
    );
  });

  it("shows inline RevertToDefaultDialog on revert link click", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() => screen.getByTestId("etc-variance-input-revert-link"));

    fireEvent.click(screen.getByTestId("etc-variance-input-revert-link"));
    expect(screen.getByTestId("etc-variance-input-revert-dialog")).toBeTruthy();
  });

  it("cancelling revert returns to State 2 without DELETE", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() => screen.getByTestId("etc-variance-input-revert-link"));

    fireEvent.click(screen.getByTestId("etc-variance-input-revert-link"));
    fireEvent.click(
      screen.getByTestId("etc-variance-input-revert-dialog-cancel"),
    );

    expect(screen.queryByTestId("etc-variance-input-revert-dialog")).toBeNull();
    expect(screen.getByText("tenant override")).toBeTruthy();
  });
});
