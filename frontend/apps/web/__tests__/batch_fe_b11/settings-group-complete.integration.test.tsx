/**
 * Save-on-group-complete integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import {
  settingsHandlers,
  resetSettingsScenario,
} from "../../src/features/settings/mocks/settingsHandlers";
import { QbAutoExpirySyncPage } from "../../src/features/settings/components/QbAutoExpirySyncPage";
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

describe("Save-on-group-complete — QB invoice group", () => {
  it("shows QB invoice toggle after catalog loads", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<QbAutoExpirySyncPage />, { wrapper });
    await waitFor(() =>
      expect(screen.getByTestId("qb-invoice-auto-expire-toggle")).toBeTruthy(),
    );
  });

  it("direction field appears when toggle enabled", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<QbAutoExpirySyncPage />, { wrapper });
    await waitFor(() => screen.getByTestId("qb-invoice-auto-expire-toggle"));

    fireEvent.click(screen.getByTestId("qb-invoice-auto-expire-toggle"));
    await waitFor(() =>
      expect(screen.getByTestId("qb-invoice-direction-select")).toBeTruthy(),
    );
  });

  it("shows incomplete indicator after toggle ON without direction", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<QbAutoExpirySyncPage />, { wrapper });
    await waitFor(() => screen.getByTestId("qb-invoice-auto-expire-toggle"));

    fireEvent.click(screen.getByTestId("qb-invoice-auto-expire-toggle"));

    await waitFor(() =>
      expect(
        screen.getByTestId("invoice-group-indicator-incomplete"),
      ).toBeTruthy(),
    );
  });

  it("group shows saved indicator when direction selected", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<QbAutoExpirySyncPage />, { wrapper });
    await waitFor(() => screen.getByTestId("qb-invoice-auto-expire-toggle"));

    fireEvent.click(screen.getByTestId("qb-invoice-auto-expire-toggle"));
    await waitFor(() => screen.getByTestId("qb-invoice-direction-select"));

    fireEvent.change(screen.getByTestId("qb-invoice-direction-select"), {
      target: { value: "accept_remote" },
    });

    await waitFor(
      () =>
        expect(
          screen.getByTestId("invoice-group-indicator-saved"),
        ).toBeTruthy(),
      { timeout: 3000 },
    );
  });
});
