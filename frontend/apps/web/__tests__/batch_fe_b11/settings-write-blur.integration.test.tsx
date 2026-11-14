/**
 * Settings blur write integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { setupServer } from "msw/node";
import {
  settingsHandlers,
  resetSettingsScenario,
} from "../../src/features/settings/mocks/settingsHandlers";
import { ProfitabilityRulesPage } from "../../src/features/settings-operations/components/ProfitabilityRulesPage";
import { createSettingsWrapper } from "../test-utils/settingsWrapper";

const server = setupServer(...settingsHandlers);

beforeEach(() => {
  server.listen({ onUnhandledRequest: "bypass" });
  resetSettingsScenario();
});
afterEach(() => {
  server.resetHandlers();
  server.close();
});

describe("Settings blur write — ProfitabilityRulesPage", () => {
  it("renders etc_variance_note_required_pct field after catalog loads", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() =>
      expect(screen.getByTestId("etc-variance-input")).toBeTruthy(),
    );
  });

  it("shows State 1 annotation when scope=system", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() =>
      expect(
        screen.getByTestId("etc-variance-input-default-annotation"),
      ).toBeTruthy(),
    );
  });

  it("fires PUT on blur and shows saved indicator", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() => screen.getByTestId("etc-variance-input-input"));

    const input = screen.getByTestId("etc-variance-input-input");
    await act(async () => {
      fireEvent.change(input, { target: { value: "15" } });
    });
    await act(async () => {
      fireEvent.blur(input);
    });

    await waitFor(
      () => expect(screen.getByTestId("etc-variance-input-saved")).toBeTruthy(),
      { timeout: 3000 },
    );
  });
});
