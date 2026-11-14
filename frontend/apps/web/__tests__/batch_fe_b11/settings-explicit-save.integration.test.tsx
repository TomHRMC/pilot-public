/**
 * Explicit Save integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import {
  settingsHandlers,
  resetSettingsScenario,
} from "../../src/features/settings/mocks/settingsHandlers";
import { MarginBucketsPage } from "../../src/features/settings-operations/components/MarginBucketsPage";
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

describe("Explicit Save — MarginBucketsPage", () => {
  it("Save button is disabled when boundary array is not monotonically ascending", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<MarginBucketsPage />, { wrapper });
    await waitFor(() => screen.getByTestId("boundary-input-0"));

    fireEvent.change(screen.getByTestId("boundary-input-0"), {
      target: { value: "25" },
    });

    const saveBtn = screen.getByTestId(
      "margin-boundaries-save-btn",
    ) as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("Save button is enabled when boundaries are strictly ascending", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<MarginBucketsPage />, { wrapper });
    await waitFor(() => screen.getByTestId("boundary-input-0"));

    fireEvent.change(screen.getByTestId("boundary-input-0"), {
      target: { value: "10" },
    });
    fireEvent.change(screen.getByTestId("boundary-input-1"), {
      target: { value: "20" },
    });
    fireEvent.change(screen.getByTestId("boundary-input-2"), {
      target: { value: "35" },
    });

    await waitFor(() => {
      const saveBtn = screen.getByTestId(
        "margin-boundaries-save-btn",
      ) as HTMLButtonElement;
      expect(saveBtn.disabled).toBe(false);
    });
  });
});
