/**
 * states/types — unit tests for FTU_DEFAULTS
 * Location: packages/ui/src/states/types.test.ts
 */

import { describe, it, expect } from "vitest";
import {
  FTU_DEFAULTS,
  EMPTY_STATE_DEFAULTS,
  ERROR_STATE_DEFAULTS,
} from "./types";
import type { FTUSurface, EmptyStateType, ErrorStateType } from "./types";

const FTU_SURFACES: FTUSurface[] = [
  "dashboard",
  "quotes",
  "schedule",
  "customers",
  "invoices",
  "reports",
  "comms",
  "settings",
];

const EMPTY_STATE_TYPES: EmptyStateType[] = [
  "no-data",
  "no-results",
  "not-yet-set-up",
  "permission-denied",
  "filtered-empty",
];

const ERROR_STATE_TYPES: ErrorStateType[] = [
  "network",
  "server",
  "validation",
  "permission",
];

describe("FTU_DEFAULTS", () => {
  it.each(FTU_SURFACES)("surface '%s' has non-empty heading", (surface) => {
    expect(FTU_DEFAULTS[surface].heading.length).toBeGreaterThan(0);
  });

  it.each(FTU_SURFACES)("surface '%s' has non-empty body", (surface) => {
    expect(FTU_DEFAULTS[surface].body.length).toBeGreaterThan(0);
  });

  it.each(FTU_SURFACES)("surface '%s' has non-empty ctaLabel", (surface) => {
    expect(FTU_DEFAULTS[surface].ctaLabel.length).toBeGreaterThan(0);
  });

  it.each(FTU_SURFACES)(
    "surface '%s' has non-empty ctaPath starting with '/'",
    (surface) => {
      expect(FTU_DEFAULTS[surface].ctaPath.startsWith("/")).toBe(true);
    },
  );
});

describe("EMPTY_STATE_DEFAULTS", () => {
  it.each(EMPTY_STATE_TYPES)("type '%s' has non-empty title", (type) => {
    expect(EMPTY_STATE_DEFAULTS[type].title.length).toBeGreaterThan(0);
  });

  it.each(EMPTY_STATE_TYPES)("type '%s' has non-empty description", (type) => {
    expect(EMPTY_STATE_DEFAULTS[type].description.length).toBeGreaterThan(0);
  });
});

describe("ERROR_STATE_DEFAULTS", () => {
  it.each(ERROR_STATE_TYPES)("type '%s' has non-empty title", (type) => {
    expect(ERROR_STATE_DEFAULTS[type].title.length).toBeGreaterThan(0);
  });

  it.each(ERROR_STATE_TYPES)("type '%s' has non-empty description", (type) => {
    expect(ERROR_STATE_DEFAULTS[type].description.length).toBeGreaterThan(0);
  });
});
