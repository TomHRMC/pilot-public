/**
 * RBAC integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import {
  settingsHandlers,
  resetSettingsScenario,
} from "../../src/features/settings/mocks/settingsHandlers";
import { ProfitabilityRulesPage } from "../../src/features/settings-operations/components/ProfitabilityRulesPage";
import { BackgroundSyncPage } from "../../src/features/settings-sync-storage/components/BackgroundSyncPage";
import { FieldOperationsPage } from "../../src/features/settings-operations/components/FieldOperationsPage";
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

describe("Settings RBAC — component rendering", () => {
  it("ProfitabilityRulesPage renders without error", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<ProfitabilityRulesPage />, { wrapper });
    await waitFor(() =>
      expect(screen.getByTestId("profitability-rules-page")).toBeTruthy(),
    );
  });

  it("BackgroundSyncPage renders sync section", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<BackgroundSyncPage />, { wrapper });
    await waitFor(() =>
      expect(screen.getByTestId("background-sync-page")).toBeTruthy(),
    );
  });

  it("FieldOperationsPage renders labor rate preset", async () => {
    const { wrapper } = createSettingsWrapper();
    render(<FieldOperationsPage />, { wrapper });
    await waitFor(() =>
      expect(screen.getByTestId("field-operations-page")).toBeTruthy(),
    );
  });
});
