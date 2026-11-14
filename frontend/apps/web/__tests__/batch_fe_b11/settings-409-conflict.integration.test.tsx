/**
 * 409 conflict integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  getCatalogHandler,
  resetSettingsScenario,
} from "../../src/features/settings/mocks/settingsHandlers";
import { ProfitabilityRulesPage } from "../../src/features/settings-operations/components/ProfitabilityRulesPage";
import { createSettingsWrapper } from "../test-utils/settingsWrapper";

const server = setupServer(
  getCatalogHandler,
  http.put("/api/v1/settings/:key", () => {
    return HttpResponse.json(
      {
        detail: "This setting was updated by another session.",
        current_updated_at: new Date().toISOString(),
      },
      { status: 409 },
    );
  }),
);

beforeEach(() => {
  server.listen({ onUnhandledRequest: "bypass" });
  resetSettingsScenario();
});
afterEach(() => {
  server.resetHandlers();
  server.close();
});

describe("409 conflict — field reverts on staleness error", () => {
  it("field reverts to pre-edit value on 409", async () => {
    const { wrapper } = createSettingsWrapper();
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

  it("shows error state on 409", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() => screen.getByTestId("etc-variance-input-input"));

    const input = screen.getByTestId("etc-variance-input-input");
    fireEvent.change(input, { target: { value: "99" } });
    fireEvent.blur(input);

    await waitFor(
      () => expect(screen.getByTestId("etc-variance-input-error")).toBeTruthy(),
      { timeout: 3000 },
    );
  });
});
