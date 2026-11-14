/**
 * Optimistic UI integration test — FE-B11
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

describe("Optimistic UI — settings write", () => {
  it("shows saved indicator after successful save", async () => {
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

  it("input reverts to original value on save failure", async () => {
    const { wrapper } = createSettingsWrapper();
    const { http, HttpResponse } = await import("msw");
    server.use(
      http.put("/api/v1/settings/:key", () =>
        HttpResponse.json({ detail: "Server error." }, { status: 500 }),
      ),
    );

    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() => screen.getByTestId("etc-variance-input-input"));

    const input = screen.getByTestId(
      "etc-variance-input-input",
    ) as HTMLInputElement;
    const originalValue = input.value;

    fireEvent.change(input, { target: { value: "99" } });
    fireEvent.blur(input);

    await waitFor(() => expect(input.value).toBe(originalValue), {
      timeout: 3000,
    });
  });
});
