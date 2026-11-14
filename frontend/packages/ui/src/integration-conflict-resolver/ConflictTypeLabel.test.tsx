/**
 * ConflictTypeLabel unit tests
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConflictTypeLabel } from "./ConflictTypeLabel";

describe("<ConflictTypeLabel>", () => {
  it("renders 'Modified ↔ Modified' for modified_modified conflict type", () => {
    render(<ConflictTypeLabel conflictType="modified_modified" />);
    expect(screen.getByText("Modified ↔ Modified")).toBeInTheDocument();
  });

  it("renders 'Deleted ↔ Modified' for deleted_modified conflict type", () => {
    render(<ConflictTypeLabel conflictType="deleted_modified" />);
    expect(screen.getByText("Deleted ↔ Modified")).toBeInTheDocument();
  });

  it("renders 'Modified ↔ Deleted' for modified_deleted conflict type", () => {
    render(<ConflictTypeLabel conflictType="modified_deleted" />);
    expect(screen.getByText("Modified ↔ Deleted")).toBeInTheDocument();
  });

  it("applies amber token classes for modified_modified", () => {
    const { container } = render(
      <ConflictTypeLabel conflictType="modified_modified" />,
    );
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-alert-100");
    expect(span?.className).toContain("text-alert-700");
    expect(span?.className).toContain("border-alert-200");
  });

  it("applies red token classes for deleted_modified", () => {
    const { container } = render(
      <ConflictTypeLabel conflictType="deleted_modified" />,
    );
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-fault-100");
    expect(span?.className).toContain("text-fault-700");
  });

  it("applies red token classes for modified_deleted", () => {
    const { container } = render(
      <ConflictTypeLabel conflictType="modified_deleted" />,
    );
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-fault-100");
    expect(span?.className).toContain("text-fault-700");
  });

  it("uses custom testID when provided", () => {
    render(
      <ConflictTypeLabel
        conflictType="modified_modified"
        testID="my-custom-label"
      />,
    );
    expect(screen.getByTestId("my-custom-label")).toBeInTheDocument();
  });

  it("uses default testID when not provided", () => {
    render(<ConflictTypeLabel conflictType="modified_modified" />);
    expect(screen.getByTestId("conflict-type-label")).toBeInTheDocument();
  });
});
