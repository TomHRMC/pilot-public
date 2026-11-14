/**
 * Settings search integration test — FE-B11
 *
 * Typing "margin" → synonym match → "Margin bucket thresholds" result with path shown
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SettingsSidebarSearch } from "@pilot/ui";
import type { CatalogEntry } from "@pilot/ui";

const MOCK_CATALOG: CatalogEntry[] = [
  {
    key: "margin_bucket_boundaries",
    label: "Margin bucket thresholds",
    description:
      "Percentage boundaries that define margin performance buckets.",
    subSurfacePath: "/settings/operations/margin-buckets",
    dataType: "array",
    validationRules: {},
    systemDefault: [10, 20, 30],
    currentEffectiveValue: [10, 20, 30],
    currentScope: "system",
    revertible: false,
    requiresRole: null,
    allowsUserOverride: false,
  },
  {
    key: "low_margin_threshold_pct",
    label: "Low-margin alert threshold",
    description: "Jobs below this margin % trigger a low-margin alert.",
    subSurfacePath: "/settings/operations/margin-buckets",
    dataType: "integer",
    validationRules: { min: 0, max: 100 },
    systemDefault: 15,
    currentEffectiveValue: 15,
    currentScope: "system",
    revertible: false,
    requiresRole: null,
    allowsUserOverride: false,
  },
];

describe("SettingsSidebarSearch", () => {
  it("shows matching results when typing", async () => {
    const onNavigate = vi.fn();
    render(
      <SettingsSidebarSearch
        catalog={MOCK_CATALOG}
        onNavigate={onNavigate}
        testID="sidebar-search"
      />,
    );

    fireEvent.change(screen.getByTestId("sidebar-search-input"), {
      target: { value: "margin" },
    });

    await waitFor(() =>
      expect(screen.getByTestId("sidebar-search-dropdown")).toBeTruthy(),
    );
    expect(screen.getByText("Margin bucket thresholds")).toBeTruthy();
  });

  it("shows path breadcrumb in results", async () => {
    const onNavigate = vi.fn();
    render(
      <SettingsSidebarSearch
        catalog={MOCK_CATALOG}
        onNavigate={onNavigate}
        testID="sidebar-search"
      />,
    );

    fireEvent.change(screen.getByTestId("sidebar-search-input"), {
      target: { value: "margin" },
    });

    await waitFor(() => screen.getByTestId("sidebar-search-dropdown"));
    // Path: "Operations > Margin Buckets"
    expect(screen.getAllByText(/Operations/i).length).toBeGreaterThan(0);
  });

  it("calls onNavigate when result clicked", async () => {
    const onNavigate = vi.fn();
    render(
      <SettingsSidebarSearch
        catalog={MOCK_CATALOG}
        onNavigate={onNavigate}
        testID="sidebar-search"
      />,
    );

    fireEvent.change(screen.getByTestId("sidebar-search-input"), {
      target: { value: "margin" },
    });

    await waitFor(() =>
      screen.getByTestId("sidebar-search-result-margin_bucket_boundaries"),
    );
    fireEvent.click(
      screen.getByTestId("sidebar-search-result-margin_bucket_boundaries"),
    );
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ key: "margin_bucket_boundaries" }),
    );
  });

  it("shows 'No settings found' when no match", async () => {
    render(
      <SettingsSidebarSearch
        catalog={MOCK_CATALOG}
        onNavigate={vi.fn()}
        testID="sidebar-search"
      />,
    );

    fireEvent.change(screen.getByTestId("sidebar-search-input"), {
      target: { value: "zzznomatch" },
    });

    await waitFor(() =>
      expect(screen.getByTestId("sidebar-search-no-results")).toBeTruthy(),
    );
  });
});
